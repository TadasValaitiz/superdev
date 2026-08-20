"""Session-scoped daemon identity and lifecycle management."""
import hashlib
import json
import os
import shlex
import stat
import tempfile
import time
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .commands import (DaemonStatusResponse, DaemonStopResponse, FacadeFault,
                       FacadeFaultCode, InstanceSource, InstanceView)
from .models import RpcFault
from .rpc import _socket_accepts_connections


def validate_instance_id(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError("instance must be a non-empty string of at most 512 characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("instance must not contain control characters")
    return value


@dataclass(frozen=True)
class InstanceIdentity:
    source: InstanceSource
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, InstanceSource):
            raise ValueError("source must be an InstanceSource")
        object.__setattr__(self, "value", validate_instance_id(self.value))

    @property
    def key_hash(self) -> str:
        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InstancePaths:
    durable_dir: Path
    socket_path: Path
    registry_path: Path
    log_path: Path
    metadata_path: Path
    lock_path: Path
    callback_path: Path
    callback_artifact_dir: Path


@dataclass(frozen=True)
class InstanceDeps:
    paths: InstancePaths
    launcher: str
    codex_bin: str
    spawn: Callable[[Sequence[str], str], Any]
    rpc_call: Callable[[str, str, dict, Optional[float]], dict]
    monotonic: Callable[[], float]
    wait: Callable[[float], None] = field(default=time.sleep)


def resolve_instance(explicit: Optional[str], env: Mapping[str, str]) -> InstanceIdentity:
    candidates = ((InstanceSource.FLAG, explicit),
                  (InstanceSource.ENVIRONMENT, env.get("CODEX_WORKER_INSTANCE")),
                  (InstanceSource.CLAUDE_SESSION, env.get("CLAUDE_CODE_SESSION_ID")),
                  (InstanceSource.DEFAULT, "default"))
    source, value = next((source, value) for source, value in candidates if value)
    return InstanceIdentity(source, validate_instance_id(value))


def derive_instance_paths(identity: InstanceIdentity, platform: str, state_home: Path,
                          temp_root: Path, uid: int) -> InstancePaths:
    if not isinstance(platform, str) or not platform:
        raise ValueError("platform must be a non-empty string")
    if type(uid) is not int or uid < 0:
        raise ValueError("uid must be a non-negative integer")
    key_hash = identity.key_hash
    durable_dir = Path(state_home) / "superdev" / "codex-worker" / "instances" / key_hash
    runtime_dir = Path(temp_root) / ("scw-%s-%s" % (uid, key_hash[:20]))
    return InstancePaths(durable_dir, runtime_dir / "s", durable_dir / "registry.json",
                         durable_dir / "daemon.log", durable_dir / "instance.json",
                         runtime_dir / "l", durable_dir / "callbacks.json",
                         durable_dir / "callback-artifacts")


def _owner_regular(path: Path, mode: int) -> bool:
    try:
        data = os.lstat(path)
    except OSError:
        return False
    return (stat.S_ISREG(data.st_mode) and data.st_uid == os.getuid()
            and stat.S_IMODE(data.st_mode) == mode)


def _safe_directory(path: Path) -> bool:
    try:
        data = os.lstat(path)
    except OSError:
        return False
    return (stat.S_ISDIR(data.st_mode) and data.st_uid == os.getuid()
            and stat.S_IMODE(data.st_mode) == 0o700)


def _unsafe_ancestor(path: Path) -> Optional[Path]:
    """Accept owner-only ancestors and sticky system temp ancestors, never links."""
    absolute = Path(os.path.abspath(str(path)))
    current = Path(absolute.anchor)
    controlled = False
    shared_sticky = False
    for component in absolute.parts[1:]:
        current = current / component
        try:
            data = os.lstat(current)
        except OSError:
            return current
        if stat.S_ISLNK(data.st_mode):
            if current.parent != Path(absolute.anchor) or data.st_uid != 0:
                return current
            try:
                data = os.stat(current)
            except OSError:
                return current
        mode = stat.S_IMODE(data.st_mode)
        sticky = bool(mode & stat.S_ISVTX)
        shared = sticky and bool(mode & 0o022)
        if (not stat.S_ISDIR(data.st_mode)
                or mode & 0o022 and not sticky):
            return current
        if data.st_uid == os.getuid():
            controlled = True
        elif shared:
            shared_sticky = True
            controlled = False
        elif data.st_uid != 0 or controlled or shared_sticky:
            return current
    return None


def _safe_ancestor(path: Path) -> bool:
    return _unsafe_ancestor(path) is None


class UnsafePathError(RuntimeError):
    def __init__(self, reason: str, path: Path):
        self.reason = reason
        self.path = Path(path)
        super().__init__("%s: %s" % (reason, path))


def _safe_nearest_ancestor(path: Path) -> bool:
    current = Path(path)
    while True:
        try:
            os.lstat(current)
        except FileNotFoundError:
            if current.parent == current:
                return False
            current = current.parent
            continue
        except OSError:
            return False
        return _safe_ancestor(current)


def _mkdir_owner_only(path: Path) -> None:
    if path.exists() or path.is_symlink():
        unsafe = _unsafe_ancestor(path)
        if unsafe is not None:
            raise UnsafePathError("unsafe_ancestor", unsafe)
        if not _safe_directory(path):
            raise UnsafePathError("unsafe_directory", path)
        return
    parent = path.parent
    if not parent.exists():
        _mkdir_owner_only(parent)
    else:
        unsafe = _unsafe_ancestor(parent)
        if unsafe is not None:
            raise UnsafePathError("unsafe_parent", unsafe)
    try:
        path.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError:
        pass
    if not _safe_directory(path):
        raise UnsafePathError("unsafe_directory", path)


def _metadata_payload(identity: InstanceIdentity) -> dict:
    return {"source": identity.source.value, "value": identity.value,
            "key_hash": identity.key_hash}


def _write_metadata(paths: InstancePaths, identity: InstanceIdentity) -> None:
    _mkdir_owner_only(paths.durable_dir)
    if paths.metadata_path.exists() or paths.metadata_path.is_symlink():
        if not _owner_regular(paths.metadata_path, 0o600):
            raise UnsafePathError("unsafe_instance_metadata", paths.metadata_path)
    fd, temporary = tempfile.mkstemp(prefix="instance.", dir=str(paths.durable_dir))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(_metadata_payload(identity), handle, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, paths.metadata_path)
        if not _owner_regular(paths.metadata_path, 0o600):
            raise UnsafePathError("unsafe_instance_metadata", paths.metadata_path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def load_managed_identity(state_path: Path) -> Optional[InstanceIdentity]:
    """Return verified owner-only identity for a managed registry, else ``None``."""
    registry_path = Path(state_path)
    metadata_path = registry_path.parent / "instance.json"
    if (not _safe_ancestor(registry_path.parent)
            or not _safe_directory(registry_path.parent)
            or not _owner_regular(metadata_path, 0o600)):
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"source", "value", "key_hash"}:
            return None
        identity = InstanceIdentity(InstanceSource(data["source"]), validate_instance_id(data["value"]))
        if data["key_hash"] != identity.key_hash or registry_path.parent.name != identity.key_hash:
            return None
        return identity
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


@contextmanager
def acquire_start_lock(lock_path: Path, timeout: float = 2.0):
    _mkdir_owner_only(lock_path.parent)
    if lock_path.exists() or lock_path.is_symlink():
        if not _owner_regular(lock_path, 0o600):
            raise UnsafePathError("unsafe_start_lock", lock_path)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(lock_path), flags, 0o600)
    try:
        if not _owner_regular(lock_path, 0o600):
            os.fchmod(fd, 0o600)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise UnsafePathError("unsafe_start_lock", lock_path)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise UnsafePathError("start_lock_timeout", lock_path)
                time.sleep(0.01)
        after = os.lstat(lock_path)
        if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
            raise UnsafePathError("start_lock_changed", lock_path)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _lifecycle_fault(code: FacadeFaultCode, reason: str, socket_path: Path) -> FacadeFault:
    stopping = code == FacadeFaultCode.DAEMON_STOP_FAILED
    return FacadeFault(
        code,
        "Codex worker daemon could not be stopped safely" if stopping
        else "Codex worker daemon could not be started safely",
        "daemon_stop_failed" if stopping else "daemon_start_failed",
        details={"reason": reason, "socket_path": str(socket_path),
                 "durable_state": "preserved"},
    )


def _verified_socket(path: Path, code: FacadeFaultCode):
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _lifecycle_fault(code, "unsafe_socket", path) from exc
    if (not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600):
        raise _lifecycle_fault(code, "unsafe_socket", path)
    return metadata


def _unlink_verified_socket(path: Path, expected: Any, code: FacadeFaultCode) -> None:
    if _socket_accepts_connections(str(path)):
        raise _lifecycle_fault(code, "socket_peer_active", path)
    try:
        current = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise _lifecycle_fault(code, "unsafe_socket", path) from exc
    if ((current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino)
            or not stat.S_ISSOCK(current.st_mode)
            or current.st_uid != os.getuid()
            or stat.S_IMODE(current.st_mode) != 0o600):
        raise _lifecycle_fault(code, "socket_changed", path)
    os.unlink(path)


class InstanceManager:
    def __init__(self, deps: InstanceDeps, identity: Optional[InstanceIdentity] = None):
        self.deps = deps
        self.identity = identity or load_managed_identity(deps.paths.registry_path)
        if self.identity is None:
            raise ValueError("a verified instance identity is required")

    def _view(self) -> InstanceView:
        paths = self.deps.paths
        return InstanceView(self.identity.value, self.identity.source, str(paths.durable_dir),
                            str(paths.socket_path), str(paths.log_path))

    def _probe(self) -> Optional[dict]:
        try:
            response = self.deps.rpc_call(str(self.deps.paths.socket_path), "daemon/status", {}, 0.2)
            result = response.get("result", response)
            return result if result.get("ready") is True else None
        except OSError:
            return None
        except RpcFault as exc:
            if exc.kind == "daemon_unavailable":
                return None
            raise

    def _status_response(self, status: str, result: Optional[dict] = None,
                         last_error: Optional[dict] = None) -> DaemonStatusResponse:
        result = result or {}
        return DaemonStatusResponse(self._view(), status, result.get("daemon_pid"),
                                    result.get("codex_pid"), result.get("session_count", 0),
                                    result if status == "ready" else None, last_error)

    def status(self) -> DaemonStatusResponse:
        try:
            result = self._probe()
        except Exception as exc:
            return self._status_response("failed", last_error={"reason": type(exc).__name__})
        return self._status_response("ready", result) if result is not None else self._status_response("stopped")

    def _serve_argv(self) -> Sequence[str]:
        paths = self.deps.paths
        return [self.deps.launcher, "--socket", str(paths.socket_path), "daemon", "serve",
                "--state", str(paths.registry_path), "--codex-bin", self.deps.codex_bin]

    @staticmethod
    def _cause(exc: BaseException) -> dict:
        return {"type": type(exc).__name__, "message": str(exc)}

    def _start_fault(self, reason: str, offending_path: Optional[Path] = None,
                     cause: Optional[dict] = None, retryable: bool = False) -> FacadeFault:
        paths = self.deps.paths
        path = paths.socket_path if offending_path is None else Path(offending_path)
        selected = shlex.quote(self.identity.value)
        return FacadeFault(
            FacadeFaultCode.DAEMON_START_FAILED,
            "Codex worker daemon could not be started safely",
            "daemon_start_failed",
            retryable=retryable,
            details={
                "reason": reason,
                "cause": cause,
                "socket_path": str(paths.socket_path),
                "offending_path": str(path),
                "log_path": str(paths.log_path),
                "durable_state": "preserved",
            },
            known_ids={"instance": self.identity.value, "name": None,
                       "session_id": None, "thread_id": None, "turn_id": None},
            next_actions=[
                {"command": "codex-worker --instance %s daemon status" % selected,
                 "reason": "Inspect the selected managed instance"},
                {"command": "/bin/ls -ld %s" % shlex.quote(str(path)),
                 "reason": "Inspect the runtime path without changing it"},
                {"command": "/usr/bin/tail -n 100 %s" % shlex.quote(str(paths.log_path)),
                 "reason": "Inspect the daemon log without changing it"},
            ],
        )

    def ensure_running(self) -> DaemonStatusResponse:
        try:
            return self._ensure_running()
        except FacadeFault as exc:
            if exc.code != FacadeFaultCode.DAEMON_START_FAILED:
                raise
            details = exc.details if isinstance(exc.details, dict) else {}
            path = details.get("offending_path", details.get("socket_path"))
            raise self._start_fault(
                details.get("reason", "startup_failed"),
                Path(path) if isinstance(path, str) else self.deps.paths.socket_path,
                details.get("cause") if isinstance(details.get("cause"), dict) else None,
                exc.retryable,
            ) from exc
        except (UnsafePathError, OSError) as exc:
            offending_path = getattr(
                exc, "path", getattr(exc, "filename", None) or self.deps.paths.lock_path,
            )
            reason = getattr(exc, "reason", type(exc).__name__)
            cause = None if isinstance(exc, UnsafePathError) else self._cause(exc)
            raise self._start_fault(reason, Path(offending_path), cause) from exc

    def _ensure_running(self) -> DaemonStatusResponse:
        with acquire_start_lock(self.deps.paths.lock_path):
            ready = self._probe()
            if ready is not None:
                return self._status_response("ready", ready)
            _write_metadata(self.deps.paths, self.identity)
            stale_socket = _verified_socket(self.deps.paths.socket_path,
                                             FacadeFaultCode.DAEMON_START_FAILED)
            if stale_socket is not None:
                if _socket_accepts_connections(str(self.deps.paths.socket_path)):
                    raise _lifecycle_fault(FacadeFaultCode.DAEMON_START_FAILED,
                                           "socket_peer_active", self.deps.paths.socket_path)
                _unlink_verified_socket(self.deps.paths.socket_path, stale_socket,
                                        FacadeFaultCode.DAEMON_START_FAILED)
            try:
                process = self.deps.spawn(self._serve_argv(), str(self.deps.paths.log_path))
            except Exception as exc:
                raise self._start_fault("spawn_failed", cause=self._cause(exc)) from exc
            deadline = self.deps.monotonic() + 2.0
            while True:
                ready = self._probe()
                if ready is not None:
                    return self._status_response("ready", ready)
                if getattr(process, "poll", lambda: None)() is not None:
                    reason = "child_exited"; break
                if self.deps.monotonic() >= deadline:
                    reason = "readiness_timeout"; break
                self.deps.wait(0.01)
            raise self._start_fault(reason, retryable=True)

    def stop(self) -> DaemonStopResponse:
        if (not _safe_nearest_ancestor(self.deps.paths.durable_dir)
                or not _safe_nearest_ancestor(self.deps.paths.socket_path.parent)):
            raise _lifecycle_fault(FacadeFaultCode.DAEMON_STOP_FAILED, "unsafe_parent",
                                   self.deps.paths.socket_path)
        before = self._probe()
        if before is None:
            return DaemonStopResponse(self._view(), "stopped", "stopped", None, None,
                                      "preserved", 0)
        observed_socket = _verified_socket(self.deps.paths.socket_path,
                                           FacadeFaultCode.DAEMON_STOP_FAILED)
        try:
            self.deps.rpc_call(str(self.deps.paths.socket_path), "daemon/shutdown", {}, 2.0)
        except Exception:
            pass
        deadline = self.deps.monotonic() + 2.0
        while any(_pid_alive(pid) for pid in (before.get("daemon_pid"), before.get("codex_pid"))):
            if self.deps.monotonic() >= deadline:
                raise FacadeFault(FacadeFaultCode.DAEMON_STOP_FAILED, "Codex worker daemon did not stop",
                                  "daemon_stop_failed", True, details={"reason": "stop_timeout",
                                  "deadline_seconds": 2.0, "daemon_pid": before.get("daemon_pid"),
                                  "codex_pid": before.get("codex_pid"), "durable_state": "preserved",
                                  "socket_path": str(self.deps.paths.socket_path)},
                                  next_actions=[{"command": "codex-worker daemon status", "reason": "Inspect the remaining daemon state"},
                                                {"command": "codex-worker daemon stop", "reason": "Retry graceful shutdown"}])
            self.deps.wait(0.01)
        if observed_socket is not None:
            _unlink_verified_socket(self.deps.paths.socket_path, observed_socket,
                                    FacadeFaultCode.DAEMON_STOP_FAILED)
        return DaemonStopResponse(self._view(), "ready", "stopped", before.get("daemon_pid"),
                                  before.get("codex_pid"), "preserved", before.get("session_count", 0))


def _pid_alive(pid: Any) -> bool:
    if type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
