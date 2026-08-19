"""Session-scoped daemon identity and lifecycle management."""
import hashlib
import json
import os
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
    runtime_dir = Path(temp_root) / ("superdev-cw-%s" % uid) / key_hash[:6]
    return InstancePaths(durable_dir, runtime_dir / "worker.sock", durable_dir / "registry.json",
                         durable_dir / "daemon.log", durable_dir / "instance.json",
                         runtime_dir / "start.lock")


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


def _safe_ancestor(path: Path) -> bool:
    """Accept owner-only ancestors and sticky system temp ancestors, never links."""
    current = Path(path).resolve()
    while True:
        try:
            data = os.lstat(current)
        except OSError:
            return False
        mode = stat.S_IMODE(data.st_mode)
        if not stat.S_ISDIR(data.st_mode) or stat.S_ISLNK(data.st_mode):
            return False
        if mode & 0o022 and not (mode & stat.S_ISVTX):
            return False
        if current.parent == current:
            return True
        current = current.parent


def _mkdir_owner_only(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if not _safe_directory(path):
            raise RuntimeError("unsafe directory %s" % path)
        return
    parent = path.parent
    if not parent.exists():
        _mkdir_owner_only(parent)
    elif not _safe_ancestor(parent):
        raise RuntimeError("unsafe controlled parent %s" % parent)
    try:
        path.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError:
        pass
    if not _safe_directory(path):
        raise RuntimeError("unsafe directory %s" % path)


def _metadata_payload(identity: InstanceIdentity) -> dict:
    return {"source": identity.source.value, "value": identity.value,
            "key_hash": identity.key_hash}


def _write_metadata(paths: InstancePaths, identity: InstanceIdentity) -> None:
    _mkdir_owner_only(paths.durable_dir)
    if paths.metadata_path.exists() or paths.metadata_path.is_symlink():
        if not _owner_regular(paths.metadata_path, 0o600):
            raise RuntimeError("unsafe instance metadata")
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
            raise RuntimeError("instance metadata permissions could not be hardened")
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
    if not _safe_directory(registry_path.parent) or not _owner_regular(metadata_path, 0o600):
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
            raise RuntimeError("unsafe instance start lock")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(lock_path), flags, 0o600)
    try:
        if not _owner_regular(lock_path, 0o600):
            os.fchmod(fd, 0o600)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise RuntimeError("unsafe instance start lock")
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("timed out waiting for instance start lock")
                time.sleep(0.01)
        after = os.lstat(lock_path)
        if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
            raise RuntimeError("instance start lock changed during acquisition")
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


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

    def ensure_running(self) -> DaemonStatusResponse:
        with acquire_start_lock(self.deps.paths.lock_path):
            ready = self._probe()
            if ready is not None:
                return self._status_response("ready", ready)
            _write_metadata(self.deps.paths, self.identity)
            try:
                process = self.deps.spawn(self._serve_argv(), str(self.deps.paths.log_path))
            except Exception as exc:
                raise FacadeFault(FacadeFaultCode.DAEMON_START_FAILED, "Codex worker daemon failed to start",
                                  "daemon_start_failed", details={"log_path": str(self.deps.paths.log_path),
                                                                  "reason": type(exc).__name__}) from exc
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
            raise FacadeFault(FacadeFaultCode.DAEMON_START_FAILED, "Codex worker daemon did not become ready",
                              "daemon_start_failed", True, details={"log_path": str(self.deps.paths.log_path),
                                                                     "reason": reason})

    def stop(self) -> DaemonStopResponse:
        before = self._probe()
        if before is None:
            return DaemonStopResponse(self._view(), "stopped", "stopped", None, None,
                                      "preserved", 0)
        try:
            observed_socket = os.lstat(self.deps.paths.socket_path)
            if not stat.S_ISSOCK(observed_socket.st_mode) or observed_socket.st_uid != os.getuid():
                raise RuntimeError("unsafe socket")
        except FileNotFoundError:
            observed_socket = None
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
        try:
            metadata = os.lstat(self.deps.paths.socket_path)
            if observed_socket is not None and (metadata.st_dev, metadata.st_ino) != (observed_socket.st_dev, observed_socket.st_ino):
                raise RuntimeError("socket changed during shutdown")
            if stat.S_ISSOCK(metadata.st_mode) and metadata.st_uid == os.getuid(): os.unlink(self.deps.paths.socket_path)
        except FileNotFoundError:
            pass
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
