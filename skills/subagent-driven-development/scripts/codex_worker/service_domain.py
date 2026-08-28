"""Global Codex worker service value objects and pure path derivation."""
import ipaddress
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlsplit

from .commands import StrictModel, validate_worker_name


DEFAULT_PUBLIC_LISTENER = "ws://127.0.0.1:4500"


class MigrationState(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"


class MigrationOutcome(str, Enum):
    IMPORTED = "imported"
    DEDUPLICATED = "deduplicated"
    CONFLICTED = "conflicted"


@dataclass(frozen=True)
class ServicePaths:
    durable_dir: Path
    rpc_socket: Path
    private_codex_socket: Path
    start_lock: Path
    registry_path: Path
    config_path: Path
    migration_path: Path
    log_path: Path
    callback_path: Path
    callback_artifact_dir: Path

    def __post_init__(self) -> None:
        for value in (
                self.durable_dir, self.rpc_socket, self.private_codex_socket,
                self.start_lock, self.registry_path, self.config_path,
                self.migration_path, self.log_path, self.callback_path,
                self.callback_artifact_dir):
            if not isinstance(value, Path) or not value.is_absolute():
                raise ValueError("service paths must be absolute Path values")


@dataclass(frozen=True)
class ServiceConfig(StrictModel):
    listener: str
    worker_version: str
    generation_id: str

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_public_listener(self.listener)
        if not self.worker_version or any(character.isspace()
                                          for character in self.worker_version):
            raise ValueError("worker_version must be a non-empty exact version")
        try:
            uuid.UUID(self.generation_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("generation_id must be a UUID") from exc


@dataclass(frozen=True)
class AttachView(StrictModel):
    listener: str
    thread_id: str
    attach_command: str
    resume_command: str

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_public_listener(self.listener)
        if not all((self.thread_id, self.attach_command, self.resume_command)):
            raise ValueError("attach identity and commands must be non-empty")


@dataclass(frozen=True)
class LegacyCandidate(StrictModel):
    source_path: str
    source_digest: str
    name: Optional[str]
    session_id: str
    thread_id: str
    cwd: str
    created_at: str
    updated_at: str
    model: Optional[str]
    effort: Optional[str]
    tier: Optional[str]
    access: Optional[str]

    def __post_init__(self) -> None:
        super().__post_init__()
        if not Path(self.source_path).is_absolute():
            raise ValueError("source_path must be absolute")
        if (len(self.source_digest) != 64
                or any(character not in "0123456789abcdef"
                       for character in self.source_digest)):
            raise ValueError("source_digest must be lowercase sha256")
        if self.name is not None:
            validate_worker_name(self.name)
        try:
            uuid.UUID(self.session_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("session_id must be a UUID") from exc
        if not self.thread_id or not Path(self.cwd).is_absolute():
            raise ValueError("candidate thread and cwd must be valid")
        if not self.created_at or not self.updated_at:
            raise ValueError("candidate timestamps must be non-empty")
        if self.tier not in (None, "medium", "very-smart"):
            raise ValueError("candidate tier is invalid")
        if self.access not in (None, "full", "read_only"):
            raise ValueError("candidate access is invalid")


@dataclass(frozen=True)
class LegacyConflict(StrictModel):
    name: str
    candidates: List[LegacyCandidate]
    source_digests: List[str]

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_worker_name(self.name)
        if not self.candidates:
            raise ValueError("legacy conflict requires candidates")
        if any(candidate.name != self.name for candidate in self.candidates):
            raise ValueError("legacy conflict candidate name mismatch")
        expected = sorted({candidate.source_digest for candidate in self.candidates})
        if self.source_digests != expected:
            raise ValueError("legacy conflict source digests must be complete and sorted")


@dataclass(frozen=True)
class MigrationSourceView(StrictModel):
    source_path: str
    source_digest: str
    name: Optional[str]
    session_id: str
    thread_id: str
    outcome: MigrationOutcome

    def __post_init__(self) -> None:
        super().__post_init__()
        if not Path(self.source_path).is_absolute():
            raise ValueError("source_path must be absolute")
        if (len(self.source_digest) != 64
                or any(character not in "0123456789abcdef"
                       for character in self.source_digest)):
            raise ValueError("source_digest must be lowercase sha256")
        if self.name is not None:
            validate_worker_name(self.name)
        try:
            uuid.UUID(self.session_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("session_id must be a UUID") from exc
        if not self.thread_id:
            raise ValueError("thread_id must be non-empty")


@dataclass(frozen=True)
class MigrationStatusView(StrictModel):
    status: MigrationState
    ready: bool
    imported_count: int
    deduplicated_count: int
    conflict_count: int
    sources: List[MigrationSourceView]
    conflicts: List[LegacyConflict]

    def __post_init__(self) -> None:
        super().__post_init__()
        for field_name in ("imported_count", "deduplicated_count", "conflict_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError("migration counts must be non-negative integers")
        if self.ready != (self.status == MigrationState.COMPLETE):
            raise ValueError("migration readiness requires a complete ledger")
        if self.conflict_count != len(self.conflicts):
            raise ValueError("conflict_count must match conflicts")
        if self.imported_count != sum(
                source.outcome == MigrationOutcome.IMPORTED for source in self.sources):
            raise ValueError("imported_count must match source outcomes")
        if self.deduplicated_count != sum(
                source.outcome == MigrationOutcome.DEDUPLICATED for source in self.sources):
            raise ValueError("deduplicated_count must match source outcomes")
        names = [conflict.name for conflict in self.conflicts]
        if names != sorted(names) or len(names) != len(set(names)):
            raise ValueError("migration conflicts must be uniquely sorted")


def derive_service_paths(platform: str, state_home: Path, temp_root: Path,
                         uid: int) -> ServicePaths:
    """Derive the one machine-local service layout without ambient session state."""
    if not isinstance(platform, str) or not platform:
        raise ValueError("platform must be a non-empty string")
    if type(uid) is not int or uid < 0:
        raise ValueError("uid must be a non-negative integer")
    durable_dir = Path(state_home)
    runtime_root = Path(temp_root)
    if not durable_dir.is_absolute() or not runtime_root.is_absolute():
        raise ValueError("state and temp roots must be absolute")
    durable_dir = durable_dir / "superdev" / "codex-worker" / "service"
    runtime_dir = runtime_root / ("scw-%d-global" % uid)
    return ServicePaths(
        durable_dir=durable_dir,
        rpc_socket=runtime_dir / "s",
        private_codex_socket=runtime_dir / "c",
        start_lock=runtime_dir / "l",
        registry_path=durable_dir / "registry.json",
        config_path=durable_dir / "service.json",
        migration_path=durable_dir / "migration.json",
        log_path=durable_dir / "daemon.log",
        callback_path=durable_dir / "callbacks.json",
        callback_artifact_dir=durable_dir / "callback-artifacts",
    )


def validate_public_listener(value: str) -> str:
    """Return an exact connectable public WebSocket listener or refuse it."""
    if (not isinstance(value, str) or not value or value != value.strip()
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
            or not value.startswith("ws://")):
        raise ValueError("listener must be ws://HOST:PORT")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("listener must contain a valid port") from exc
    if (parsed.scheme != "ws" or parsed.username is not None
            or parsed.password is not None or parsed.hostname is None
            or parsed.path or parsed.query or parsed.fragment or port is None
            or port < 1 or port > 65535):
        raise ValueError("listener must be a connectable ws://HOST:PORT")
    host = parsed.hostname
    if not host or host == "*":
        raise ValueError("listener host must be connectable")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and address.is_unspecified:
        raise ValueError("listener host must not be unspecified")
    # A non-IP hostname is valid. Reject only URL-delimiter ambiguity.
    if address is None and any(character in host for character in "/@?#"):
        raise ValueError("listener host is invalid")
    return value
