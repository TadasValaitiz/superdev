"""Crash-safe, owner-only session registry."""
import copy
import datetime
import json
import os
import stat
import tempfile
import threading
import uuid
import re
import shlex
from pathlib import Path
from typing import List, Optional, Sequence

from .models import IdentifierSelector, JsonObject, SessionRecord, validate_thread_config
from .service_domain import MigrationStatusView

_WORKER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RegistryError(ValueError):
    pass


class RegistryConflict(RegistryError):
    pass


class LegacyNameConflict(RegistryConflict):
    """A globally ambiguous legacy name with explicit, non-destructive recovery."""
    kind = "legacy_name_conflict"

    def __init__(self, name: str, candidates: List[dict]):
        self.name = name
        self.candidates = [dict(candidate) for candidate in candidates]
        self.next_actions = [
            {"command": "codex-worker migration resolve --name %s --thread %s" %
             (shlex.quote(name), shlex.quote(candidate["thread_id"])),
             "reason": "Select this preserved legacy thread for the global name"}
            for candidate in self.candidates
        ]
        super().__init__("legacy worker name is conflicted: %s" % name)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def session_to_dict(record: SessionRecord):
    return record.to_dict()


def _record(data, schema_version=3):
    if not isinstance(data, dict):
        raise RegistryError("session record must be an object")
    v1_fields = {"session_id", "thread_id", "cwd", "created_at", "updated_at", "name", "model", "effort"}
    v2_fields = v1_fields | {"tier", "access"}
    expected = {1: v1_fields, 2: v2_fields}.get(schema_version, v2_fields | {"config"})
    if set(data) != expected:
        raise RegistryError("session record has incorrect fields")
    if any(not isinstance(data[key], str) or not data[key] for key in ("session_id", "thread_id", "cwd", "created_at", "updated_at")):
        raise RegistryError("session record required fields must be strings")
    if any(data.get(key) is not None and not isinstance(data.get(key), str) for key in ("name", "model", "effort", "tier", "access")):
        raise RegistryError("session annotations must be strings or null")
    if data.get("name") is not None and not _WORKER_NAME_RE.fullmatch(data["name"]):
        raise RegistryError("worker name is invalid")
    if data.get("tier") not in (None, "medium", "very-smart") or data.get("access") not in (None, "full", "read_only"):
        raise RegistryError("common policy is invalid")
    if not Path(data["cwd"]).is_absolute():
        raise RegistryError("cwd must be absolute")
    try:
        uuid.UUID(data["session_id"])
    except (ValueError, AttributeError, TypeError):
        raise RegistryError("session_id must be a UUID")
    try:
        canonical_cwd = str(Path(data["cwd"]).resolve(strict=True))
    except (OSError, RuntimeError):
        raise RegistryError("cwd must be an existing directory")
    if not os.path.isdir(canonical_cwd):
        raise RegistryError("cwd must be absolute")
    try:
        validate_thread_config(data.get("config"))
    except ValueError as exc:
        raise RegistryError(str(exc)) from exc
    data = dict(data)
    data.setdefault("tier", None)
    data.setdefault("access", None)
    data["cwd"] = canonical_cwd
    try:
        return SessionRecord.from_dict(data)
    except ValueError as exc:
        raise RegistryError(str(exc)) from exc


class SessionRegistry:
    SCHEMA_VERSION = 3

    def __init__(self, path, migration_path=None):
        self.path = Path(path)
        self.migration_path = (Path(migration_path) if migration_path is not None
                               else self.path.parent / "migration.json")
        self._lock = threading.RLock()
        self._records = self._load()

    @classmethod
    def read_existing(cls, path):
        """Load an owner-only registry without chmod, creation, or any other write."""
        value = cls.__new__(cls)
        value.path = Path(path)
        value.migration_path = value.path.parent / "migration.json"
        value._lock = threading.RLock()
        metadata = os.lstat(value.path)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600):
            raise RegistryError("registry must be an owner-owned mode-0600 regular file")
        raw = value.path.read_bytes()
        if not raw:
            raise RegistryError("existing registry must not be empty")
        value._records = value._decode(raw)
        return value

    @classmethod
    def publish_snapshot(cls, path, records: Sequence[SessionRecord],
                         migration_path=None):
        """Atomically publish without creating an empty first-write authority."""
        value = cls.__new__(cls)
        value.path = Path(path)
        value.migration_path = (Path(migration_path) if migration_path is not None
                                else value.path.parent / "migration.json")
        value._lock = threading.RLock()
        value._records = []
        if value.path.exists() or value.path.is_symlink():
            metadata = os.lstat(value.path)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o600):
                raise RegistryError(
                    "registry must be an owner-owned mode-0600 regular file")
        value.replace_all(records)
        return value

    def _load(self) -> List[SessionRecord]:
        if not self.path.exists():
            self._save_locked([])
            return []
        metadata = os.lstat(self.path)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise RegistryError("registry must be an owner-owned regular file")
        try:
            os.chmod(self.path, 0o600)
        except OSError as exc:
            raise RegistryError("registry permissions could not be hardened") from exc
        try:
            raw = self.path.read_bytes()
            if not raw:
                self._save_locked([])
                return []
        except (OSError, ValueError, TypeError) as exc:
            raise RegistryError("invalid registry JSON at %s; expected schema versions 1, 2, or 3" % self.path) from exc
        return self._decode(raw)

    def _decode(self, raw: bytes) -> List[SessionRecord]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise RegistryError("invalid registry JSON at %s; expected schema versions 1, 2, or 3" % self.path) from exc
        if (not isinstance(payload, dict) or set(payload) != {"schema_version", "sessions"}
                or type(payload.get("schema_version")) is not int
                or payload.get("schema_version") not in (1, 2, self.SCHEMA_VERSION)
                or not isinstance(payload.get("sessions"), list)):
            raise RegistryError("unsupported registry schema at %s; expected schema versions 1, 2, or 3" % self.path)
        try:
            records = [_record(item, payload["schema_version"]) for item in payload["sessions"]]
        except RegistryError as exc:
            raise RegistryError("invalid registry record at %s; expected schema versions 1, 2, or 3: %s" % (self.path, exc)) from exc
        names = [r.name for r in records if r.name is not None]
        if (len({r.session_id for r in records}) != len(records) or len({r.thread_id for r in records}) != len(records)
                or len(set(names)) != len(names)):
            raise RegistryConflict("duplicate session, thread, or worker name identifier")
        return records

    def _save_locked(self, records: Sequence[SessionRecord]) -> None:
        parent = self.path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError:
            pass
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name + ".", dir=str(parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"schema_version": self.SCHEMA_VERSION, "sessions": [session_to_dict(x) for x in records]}, handle)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, str(self.path))
            directory_fd = os.open(
                str(parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except PermissionError as exc:
            if os.path.exists(temp_name):
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
            raise RegistryError("registry write permission denied at %s" % self.path) from exc
        except BaseException:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise

    def list(self) -> List[SessionRecord]:
        with self._lock:
            return list(self._records)

    def replace_all(self, records: Sequence[SessionRecord]) -> None:
        """Atomically publish one fully validated authoritative snapshot."""
        validated = []
        for record in records:
            if not isinstance(record, SessionRecord):
                raise RegistryError("registry snapshot entries must be SessionRecord values")
            validated.append(_record(record.to_dict(), self.SCHEMA_VERSION))
        names = [record.name for record in validated if record.name is not None]
        if (len({record.session_id for record in validated}) != len(validated)
                or len({record.thread_id for record in validated}) != len(validated)
                or len(set(names)) != len(names)):
            raise RegistryConflict("duplicate session, thread, or worker name identifier")
        with self._lock:
            self._save_locked(validated)
            self._records = list(validated)

    def try_resolve(self, selector: IdentifierSelector) -> Optional[SessionRecord]:
        with self._lock:
            matches = [r for r in self._records if (r.session_id == selector.session_id if selector.kind == "session" else r.thread_id == selector.thread_id)]
            if len(matches) > 1:
                raise RegistryConflict("identifier resolves ambiguously")
            return matches[0] if matches else None

    def resolve(self, selector: IdentifierSelector) -> SessionRecord:
        record = self.try_resolve(selector)
        if record is None:
            raise RegistryError("unknown session")
        return record

    def create_worker(self, thread_id: str, cwd: str, name: str, tier: Optional[str], model: str, effort: str, access: str, session_id: Optional[str] = None,
                      config: Optional[JsonObject] = None) -> SessionRecord:
        return self._create(thread_id, cwd, name, tier, model, effort, access, session_id, config)

    def create(self, thread_id: str, cwd: str, name: Optional[str], model: Optional[str], effort: Optional[str], session_id: Optional[str] = None) -> SessionRecord:
        return self._create(thread_id, cwd, name, None, model, effort, None, session_id)

    def _create(self, thread_id: str, cwd: str, name: Optional[str], tier: Optional[str], model: Optional[str], effort: Optional[str], access: Optional[str], session_id: Optional[str] = None,
                config: Optional[JsonObject] = None) -> SessionRecord:
        if not isinstance(thread_id, str) or not thread_id:
            raise RegistryError("thread_id must be a non-empty string")
        if not isinstance(cwd, str) or not cwd:
            raise RegistryError("cwd must be a non-empty string")
        if not Path(cwd).is_absolute():
            raise RegistryError("cwd must be absolute")
        try:
            canonical_cwd = str(Path(cwd).resolve(strict=True))
        except (OSError, RuntimeError) as exc:
            raise RegistryError("cwd must be an existing directory") from exc
        if not os.path.isdir(canonical_cwd):
            raise RegistryError("cwd must be an existing directory")
        for label, value in (("name", name), ("tier", tier), ("model", model), ("effort", effort), ("access", access)):
            if value is not None and (not isinstance(value, str) or not value):
                raise RegistryError(label + " must be a non-empty string or null")
        if name is not None and not _WORKER_NAME_RE.fullmatch(name):
            raise RegistryError("name must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
        if tier not in (None, "medium", "very-smart") or access not in (None, "full", "read_only"):
            raise RegistryError("common policy is invalid")
        try:
            validate_thread_config(config)
        except ValueError as exc:
            raise RegistryError(str(exc)) from exc
        if session_id is not None and (not isinstance(session_id, str) or not session_id):
            raise RegistryError("session_id must be a non-empty UUID")
        sid = session_id if session_id is not None else str(uuid.uuid4())
        try:
            uuid.UUID(sid)
        except ValueError as exc:
            raise RegistryError("session_id must be a UUID") from exc
        with self._lock:
            if any(r.session_id == sid or r.thread_id == thread_id or (name is not None and r.name == name) for r in self._records):
                raise RegistryConflict("duplicate session, thread, or worker name identifier")
            now = _now()
            record = SessionRecord(sid, thread_id, canonical_cwd, now, now, name, model, effort, tier, access,
                                   copy.deepcopy(config))
            records = self._records + [record]
            self._save_locked(records)
            self._records = records
            return record

    def update_annotations(self, session_id: str, model: Optional[str] = None, effort: Optional[str] = None) -> SessionRecord:
        if not isinstance(session_id, str) or not session_id:
            raise RegistryError("session_id must be a non-empty UUID")
        for label, value in (("model", model), ("effort", effort)):
            if value is not None and (not isinstance(value, str) or not value):
                raise RegistryError(label + " must be a non-empty string or null")
        with self._lock:
            current = self.resolve(IdentifierSelector(session_id=session_id))
            updated = SessionRecord(current.session_id, current.thread_id, current.cwd, current.created_at, _now(), current.name, model, effort, current.tier, current.access,
                                    current.config)
            records = [updated if r.session_id == session_id else r for r in self._records]
            self._save_locked(records)
            self._records = records
            return updated

    def resolve_name(self, name: str) -> SessionRecord:
        if not isinstance(name, str) or not name:
            raise RegistryError("name must be a non-empty string")
        conflict = self._migration_conflict(name)
        if conflict is not None:
            raise LegacyNameConflict(name, conflict)
        with self._lock:
            matches = [record for record in self._records if record.name == name]
            if len(matches) > 1:
                raise RegistryConflict("worker name resolves ambiguously")
            if not matches:
                raise RegistryError("unknown worker name")
            return matches[0]

    def _migration_conflict(self, name: str) -> Optional[List[dict]]:
        path = self.migration_path
        if not path.exists():
            return None
        try:
            metadata = os.lstat(path)
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o600):
                raise RegistryError("migration ledger must be owner-owned mode-0600")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(payload, dict)
                    or set(payload) != {"version", "status", "resolutions"}
                    or payload["version"] != 1
                    or not isinstance(payload["resolutions"], list)):
                raise ValueError("invalid migration ledger")
            status = MigrationStatusView.from_dict(payload["status"])
        except (OSError, ValueError, TypeError) as exc:
            raise RegistryError("invalid migration ledger") from exc
        for conflict in status.conflicts:
            if conflict.name == name:
                return [{"source_path": candidate.source_path,
                         "source_digest": candidate.source_digest,
                         "session_id": candidate.session_id,
                         "thread_id": candidate.thread_id}
                        for candidate in conflict.candidates]
        return None
