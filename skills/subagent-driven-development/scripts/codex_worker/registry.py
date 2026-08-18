"""Crash-safe, owner-only session registry."""
import datetime
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import List, Optional, Sequence

from .models import IdentifierSelector, SessionRecord


class RegistryError(ValueError):
    pass


class RegistryConflict(RegistryError):
    pass


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def session_to_dict(record: SessionRecord):
    return record.to_dict()


def _record(data):
    if not isinstance(data, dict):
        raise RegistryError("session record must be an object")
    required = {"session_id", "thread_id", "cwd", "created_at", "updated_at", "name", "model", "effort"}
    if set(data) != required:
        raise RegistryError("session record has incorrect fields")
    if any(not isinstance(data[key], str) or not data[key] for key in ("session_id", "thread_id", "cwd", "created_at", "updated_at")):
        raise RegistryError("session record required fields must be strings")
    if any(data[key] is not None and not isinstance(data[key], str) for key in ("name", "model", "effort")):
        raise RegistryError("session annotations must be strings or null")
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
    data = dict(data)
    data["cwd"] = canonical_cwd
    try:
        return SessionRecord.from_dict(data)
    except ValueError as exc:
        raise RegistryError(str(exc)) from exc


class SessionRegistry:
    SCHEMA_VERSION = 1

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._records = self._load()

    def _load(self) -> List[SessionRecord]:
        if not self.path.exists():
            return []
        stat = os.lstat(self.path)
        if not os.path.isfile(self.path) or stat.st_uid != os.getuid():
            raise RegistryError("registry must be an owner-owned regular file")
        try:
            os.chmod(self.path, 0o600)
        except OSError as exc:
            raise RegistryError("registry permissions could not be hardened") from exc
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise RegistryError("invalid registry JSON") from exc
        if (not isinstance(payload, dict) or set(payload) != {"schema_version", "sessions"}
                or type(payload.get("schema_version")) is not int
                or payload.get("schema_version") != self.SCHEMA_VERSION
                or not isinstance(payload.get("sessions"), list)):
            raise RegistryError("unsupported registry schema")
        records = [_record(item) for item in payload["sessions"]]
        if len({r.session_id for r in records}) != len(records) or len({r.thread_id for r in records}) != len(records):
            raise RegistryConflict("duplicate session or thread identifier")
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
        except BaseException:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise

    def list(self) -> List[SessionRecord]:
        with self._lock:
            return list(self._records)

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

    def create(self, thread_id: str, cwd: str, name: Optional[str], model: Optional[str], effort: Optional[str], session_id: Optional[str] = None) -> SessionRecord:
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
        for label, value in (("name", name), ("model", model), ("effort", effort)):
            if value is not None and (not isinstance(value, str) or not value):
                raise RegistryError(label + " must be a non-empty string or null")
        if session_id is not None and (not isinstance(session_id, str) or not session_id):
            raise RegistryError("session_id must be a non-empty UUID")
        sid = session_id if session_id is not None else str(uuid.uuid4())
        try:
            uuid.UUID(sid)
        except ValueError as exc:
            raise RegistryError("session_id must be a UUID") from exc
        with self._lock:
            if any(r.session_id == sid or r.thread_id == thread_id for r in self._records):
                raise RegistryConflict("duplicate session or thread identifier")
            now = _now()
            record = SessionRecord(sid, thread_id, canonical_cwd, now, now, name, model, effort)
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
            updated = SessionRecord(current.session_id, current.thread_id, current.cwd, current.created_at, _now(), current.name, model, effort)
            records = [updated if r.session_id == session_id else r for r in self._records]
            self._save_locked(records)
            self._records = records
            return updated
