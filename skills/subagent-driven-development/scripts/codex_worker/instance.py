"""Session-scoped daemon identity and lifecycle management."""
import hashlib
import errno
import json
import os
import shlex
import signal
import socket
import stat
import subprocess
import tempfile
import time
import uuid
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence
from urllib.parse import urlsplit

from .commands import (CountEvidence, DaemonStatusResponse, DaemonStopResponse, FacadeFault,
                       FacadeFaultCode, InstanceSource, InstanceView,
                       MetricAvailability, RestartServiceResponse, ServiceReadinessResponse,
                       ServiceStatusResponse)
from .models import (ActiveInventory, MaintenanceResult, RpcFault, WorkerImpact)
from .path_security import unsafe_ancestor
from .rpc import _socket_accepts_connections
from .service_domain import (DEFAULT_PUBLIC_LISTENER, MigrationState,
                             MigrationStatusView, ServiceConfig, ServicePaths,
                             derive_service_paths, validate_public_listener)


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
    which: Callable[[str], Optional[str]] = field(default=lambda executable: executable)
    expected_version: Optional[str] = None


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


_unsafe_ancestor = unsafe_ancestor  # Compatibility re-export for existing internal consumers.


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

    def _compatible(self, result: dict) -> bool:
        return (self.deps.expected_version is None
                or result.get("worker_version") == self.deps.expected_version)

    def status(self) -> DaemonStatusResponse:
        try:
            result = self._probe()
        except Exception as exc:
            return self._status_response("failed", last_error={"reason": type(exc).__name__})
        if result is None:
            return self._status_response("stopped")
        if not self._compatible(result):
            return self._status_response("failed", last_error={
                "reason": "worker_version_mismatch",
                "expected_version": self.deps.expected_version,
                "actual_version": result.get("worker_version"),
            })
        return self._status_response("ready", result)

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
            known_ids={"name": None, "session_id": None,
                       "thread_id": None, "turn_id": None},
            next_actions=[
                {"command": "/bin/ls -ld %s" % shlex.quote(str(path)),
                 "reason": "Inspect the runtime path without changing it"},
                {"command": "/usr/bin/tail -n 100 %s" % shlex.quote(str(paths.log_path)),
                 "reason": "Inspect the daemon log without changing it"},
            ],
        )

    def _require_external_codex(self) -> None:
        """Refuse a new spawn when the external Codex CLI is absent."""
        if self.deps.which(self.deps.codex_bin) is not None:
            return
        raise self._start_fault(
            "codex_not_found",
            cause={
                "type": "FileNotFoundError",
                "message": (
                    "external '%s' executable was not found on PATH; install the Codex CLI "
                    "and verify it with '%s --version'" % (self.deps.codex_bin, self.deps.codex_bin)
                ),
            },
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
                if self._compatible(ready):
                    return self._status_response("ready", ready)
                self.stop()
            _write_metadata(self.deps.paths, self.identity)
            stale_socket = _verified_socket(self.deps.paths.socket_path,
                                             FacadeFaultCode.DAEMON_START_FAILED)
            if stale_socket is not None:
                if _socket_accepts_connections(str(self.deps.paths.socket_path)):
                    raise _lifecycle_fault(FacadeFaultCode.DAEMON_START_FAILED,
                                           "socket_peer_active", self.deps.paths.socket_path)
                _unlink_verified_socket(self.deps.paths.socket_path, stale_socket,
                                        FacadeFaultCode.DAEMON_START_FAILED)
            self._require_external_codex()
            try:
                process = self.deps.spawn(self._serve_argv(), str(self.deps.paths.log_path))
            except Exception as exc:
                raise self._start_fault("spawn_failed", cause=self._cause(exc)) from exc
            deadline = self.deps.monotonic() + 2.0
            while True:
                ready = self._probe()
                if ready is not None and self._compatible(ready):
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
                remaining_pid = next(pid for pid in (
                    before.get("daemon_pid"), before.get("codex_pid")) if _pid_alive(pid))
                raise FacadeFault(FacadeFaultCode.DAEMON_STOP_FAILED, "Codex worker daemon did not stop",
                                  "daemon_stop_failed", True, details={"reason": "stop_timeout",
                                  "deadline_seconds": 2.0, "daemon_pid": before.get("daemon_pid"),
                                  "codex_pid": before.get("codex_pid"), "durable_state": "preserved",
                                  "socket_path": str(self.deps.paths.socket_path)},
                                  known_ids={"name": None, "session_id": None,
                                             "thread_id": None,
                                             "turn_id": None},
                                  next_actions=[{
                                      "command": "/bin/ps -p %d" % remaining_pid,
                                      "reason": "Inspect the exact remaining owned process",
                                  }, {
                                      "command": "/usr/bin/tail -n 100 %s" % shlex.quote(
                                          str(self.deps.paths.log_path)),
                                      "reason": "Inspect the exact daemon log before retrying",
                                  }])
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


def _terminate_spawned_generation(process: Any) -> None:
    """Terminate only the exact Popen generation created by this manager."""
    if not isinstance(process, subprocess.Popen) or process.poll() is not None:
        return
    pid = process.pid
    try:
        if os.getpgid(pid) == pid:
            os.killpg(pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=2.0)
    except ProcessLookupError:
        return


@dataclass(frozen=True)
class ServiceDeps:
    """Injected process boundary for the one global managed service."""
    paths: ServicePaths
    launcher: str
    codex_bin: str
    spawn: Callable[[Sequence[str], str], Any]
    rpc_call: Callable[[str, str, dict, Optional[float]], dict]
    monotonic: Callable[[], float]
    wait: Callable[[float], None] = field(default=time.sleep)
    which: Callable[[str], Optional[str]] = field(default=lambda executable: executable)
    expected_version: Optional[str] = None
    listener_available: Optional[Callable[[str], bool]] = None
    pid_alive: Callable[[Any], bool] = field(default=_pid_alive)
    terminate_spawn: Callable[[Any], None] = field(
        default=_terminate_spawned_generation)

    def __post_init__(self) -> None:
        if not isinstance(self.paths, ServicePaths):
            raise TypeError("paths must be ServicePaths")
        if self.listener_available is None:
            object.__setattr__(self, "listener_available", _listener_available)


def _listener_available(listener: str) -> bool:
    """Probe bindability without connecting to or interpreting an unknown peer."""
    parsed = urlsplit(listener)
    rows = socket.getaddrinfo(parsed.hostname, parsed.port, type=socket.SOCK_STREAM)
    probes = []
    seen = set()
    try:
        for family, socktype, protocol, _, address in rows:
            key = (family, socktype, protocol, address)
            if key in seen:
                continue
            seen.add(key)
            probe = socket.socket(family, socktype, protocol)
            probes.append(probe)
            try:
                probe.bind(address)
            except OSError as exc:
                if exc.errno == errno.EADDRINUSE:
                    return False
                # The gateway remains the authority for non-collision bind errors.
                return True
        return True
    finally:
        for probe in probes:
            probe.close()


def _empty_migration() -> dict:
    return MigrationStatusView(MigrationState.INCOMPLETE, False, 0, 0, 0, [], []).to_dict()


def _service_exposure(listener: str) -> str:
    from urllib.parse import urlsplit
    import ipaddress
    host = urlsplit(listener).hostname or ""
    if host.lower() == "localhost":
        return "loopback"
    try:
        return "loopback" if ipaddress.ip_address(host).is_loopback else "non_loopback"
    except ValueError:
        return "non_loopback"


def _stopped_service_status(listener: str, version: str, workers: WorkerImpact,
                            migration: dict) -> ServiceStatusResponse:
    inventory = ActiveInventory()
    return ServiceStatusResponse(
        "stopped", version, None, None, listener, _service_exposure(listener), "none",
        "codex --remote %s" % shlex.quote(listener),
        CountEvidence(workers.to_dict()["total_count"], "codex-worker registry",
                      MetricAvailability.DERIVED, workers.to_dict()),
        CountEvidence(0, "codex app-server inventory", MetricAvailability.DERIVED,
                      inventory.to_dict()),
        migration, "preserved")


class ServiceManager:
    """Concurrency-safe client supervisor for the sole machine-local service."""
    def __init__(self, deps: ServiceDeps):
        if not isinstance(deps, ServiceDeps):
            raise TypeError("deps must be ServiceDeps")
        self.deps = deps

    @property
    def expected_version(self) -> str:
        if not self.deps.expected_version:
            raise ValueError("expected service version must be configured")
        return self.deps.expected_version

    def _read_config(self) -> Optional[ServiceConfig]:
        path = self.deps.paths.config_path
        try:
            metadata = os.lstat(path)
        except FileNotFoundError:
            return None
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or unsafe_ancestor(path.parent) is not None):
            raise FacadeFault(
                FacadeFaultCode.DAEMON_START_FAILED,
                "Global service configuration is unsafe", "daemon_start_failed",
                details={"reason": "unsafe_service_config", "path": str(path),
                         "durable_state": "preserved"})
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return ServiceConfig.from_dict(value)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise FacadeFault(
                FacadeFaultCode.DAEMON_START_FAILED,
                "Global service configuration is invalid", "daemon_start_failed",
                details={"reason": "invalid_service_config", "path": str(path),
                         "durable_state": "preserved"}) from exc

    def _write_config_once(self, config: ServiceConfig) -> None:
        if self.deps.paths.config_path.exists() or self.deps.paths.config_path.is_symlink():
            existing = self._read_config()
            if existing != config:
                raise FacadeFault(
                    FacadeFaultCode.SERVICE_CONFIG_CONFLICT,
                    "Global service listener is already configured",
                    "service_config_conflict",
                    details={"configured_listener": existing.listener if existing else None,
                             "requested_listener": config.listener,
                             "durable_state": "preserved"},
                    next_actions=[{"command": "codex-worker daemon status",
                                   "reason": "Inspect the fixed global listener"}])
            return
        _mkdir_owner_only(self.deps.paths.durable_dir)
        fd, temporary = tempfile.mkstemp(
            prefix=".service-config-", dir=str(self.deps.paths.durable_dir))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config.to_dict(), handle, separators=(",", ":"), sort_keys=True)
                handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, self.deps.paths.config_path)
            directory_fd = os.open(str(self.deps.paths.durable_dir), os.O_RDONLY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
        except BaseException:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
            raise

    @staticmethod
    def _result(response: dict) -> dict:
        if not isinstance(response, dict):
            raise ValueError("service returned a non-object response")
        if "error" in response:
            error = response["error"]
            try:
                raise FacadeFault.from_dict(error)
            except FacadeFault:
                raise
            except ValueError as exc:
                raise ValueError("service returned a malformed fault") from exc
        result = response.get("result", response)
        if not isinstance(result, dict):
            raise ValueError("service returned a non-object result")
        return result

    def _probe(self) -> Optional[ServiceStatusResponse]:
        try:
            response = self.deps.rpc_call(
                str(self.deps.paths.rpc_socket), "service/status", {}, 30.0)
        except (OSError, RpcFault) as exc:
            if isinstance(exc, RpcFault) and exc.kind not in (
                    "daemon_unavailable", "daemon_stopped"):
                raise
            return None
        try:
            return ServiceStatusResponse.from_dict(self._result(response))
        except FacadeFault:
            raise
        except (TypeError, ValueError) as exc:
            raise FacadeFault(
                FacadeFaultCode.CODEX_PROTOCOL_ERROR,
                "Global service returned malformed status", "codex_protocol_error",
                details={"reason": type(exc).__name__,
                         "socket_path": str(self.deps.paths.rpc_socket)}) from exc

    def _probe_readiness(self) -> Optional[ServiceReadinessResponse]:
        try:
            response = self.deps.rpc_call(
                str(self.deps.paths.rpc_socket), "service/readiness", {}, 0.2)
        except (OSError, RpcFault) as exc:
            if isinstance(exc, RpcFault) and exc.kind not in (
                    "daemon_unavailable", "daemon_stopped"):
                raise
            return None
        try:
            return ServiceReadinessResponse.from_dict(self._result(response))
        except FacadeFault:
            raise
        except (TypeError, ValueError) as exc:
            raise FacadeFault(
                FacadeFaultCode.CODEX_PROTOCOL_ERROR,
                "Global service returned malformed readiness",
                "codex_protocol_error",
                details={"reason": type(exc).__name__,
                         "socket_path": str(self.deps.paths.rpc_socket)}) from exc

    def status(self) -> ServiceStatusResponse:
        status = self._probe()
        if status is not None:
            return status
        config = self._read_config()
        listener = config.listener if config is not None else DEFAULT_PUBLIC_LISTENER
        workers = self._durable_workers()
        migration = self._durable_migration()
        return _stopped_service_status(
            listener, config.worker_version if config is not None else self.expected_version,
            workers, migration)

    def readiness(self) -> Optional[ServiceReadinessResponse]:
        """Probe strict managed liveness without enumerating worker inventory."""
        return self._probe_readiness()

    def _durable_migration(self) -> dict:
        path = self.deps.paths.migration_path
        if not path.exists() and not path.is_symlink():
            return _empty_migration()
        try:
            from .migration import (LegacyMigrationDeps, LegacyMigrationError,
                                    LegacyMigrator)
            migrator = LegacyMigrator(LegacyMigrationDeps(
                self.deps.paths, self.deps.paths.durable_dir.parent / "instances"))
            ledger = migrator._read_ledger(optional=False)
            if ledger is None:
                raise ValueError("migration ledger unexpectedly absent")
            return ledger[0].to_dict()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise FacadeFault(
                FacadeFaultCode.CODEX_PROTOCOL_ERROR,
                "Durable migration status is invalid", "codex_protocol_error",
                details={"reason": "invalid_migration_ledger",
                         "path": str(path), "durable_state": "preserved"}) from exc

    def _conflict(self, configured: str, requested: str) -> FacadeFault:
        return FacadeFault(
            FacadeFaultCode.SERVICE_CONFIG_CONFLICT,
            "Requested listener differs from the live global service",
            "service_config_conflict",
            details={"configured_listener": configured, "requested_listener": requested,
                     "durable_state": "preserved"},
            next_actions=[{"command": "codex-worker daemon status",
                           "reason": "Inspect the fixed global listener"},
                          {"command": "codex-worker daemon restart --app-server-listen %s" % shlex.quote(requested),
                           "reason": "Change the listener only through supervised maintenance"}])

    def ensure_running(self, listener: Optional[str] = None) -> ServiceStatusResponse:
        requested = validate_public_listener(listener) if listener is not None else None
        try:
            with acquire_start_lock(self.deps.paths.start_lock):
                return self._ensure_running_locked(requested)
        except UnsafePathError as exc:
            raise FacadeFault(FacadeFaultCode.DAEMON_START_FAILED,
                              "Global service path is unsafe", "daemon_start_failed",
                              details={"reason": exc.reason, "path": str(exc.path),
                                       "durable_state": "preserved"}) from exc

    def _ensure_running_locked(
            self, requested: Optional[str], replacement: bool = False
    ) -> ServiceStatusResponse:
        ready = self._probe_readiness()
        if ready is not None:
            if ready.status != "ready":
                raise FacadeFault(
                    FacadeFaultCode.DAEMON_START_FAILED,
                    "Global service is not exactly ready", "daemon_start_failed",
                    details={"reason": "service_not_ready", "status": ready.status,
                             "durable_state": "preserved"})
            effective = requested or ready.listener
            if ready.listener != effective:
                raise self._conflict(ready.listener, effective)
            if ready.service_version == self.expected_version and not replacement:
                return ready
            before = ready
            impact = self._parse_maintenance(self._result(self.deps.rpc_call(
                str(self.deps.paths.rpc_socket), "service/restart",
                {"listener": ready.listener, "force": False}, 30.0)), "restart")
            if impact.status == "refused":
                raise self._busy(impact)
            self._await_stopped(before)
        previous = self._read_config()
        if replacement:
            effective = requested or (previous.listener if previous is not None
                                      else DEFAULT_PUBLIC_LISTENER)
            config = ServiceConfig(effective, self.expected_version, str(uuid.uuid4()))
        elif previous is None:
            config = ServiceConfig(requested or DEFAULT_PUBLIC_LISTENER,
                                   self.expected_version, str(uuid.uuid4()))
        elif requested is not None and previous.listener != requested:
            raise self._conflict(previous.listener, requested)
        elif previous.worker_version != self.expected_version:
            config = ServiceConfig(previous.listener, self.expected_version,
                                   str(uuid.uuid4()))
        else:
            config = previous
        return self._launch_locked(config, previous)

    def _address_in_use(self, listener: str) -> FacadeFault:
        parsed = urlsplit(listener)
        port = parsed.port
        alternate_port = port + 1 if port is not None and port < 65535 else 4501
        host = ("[%s]" % parsed.hostname
                if parsed.hostname and ":" in parsed.hostname else parsed.hostname)
        alternate = "ws://%s:%d" % (host, alternate_port)
        return FacadeFault(
            FacadeFaultCode.ADDRESS_IN_USE,
            "Configured app-server listener is already in use", "address_in_use",
            details={"listener": listener, "durable_state": "preserved"},
            next_actions=[{
                "command": "codex-worker daemon start --app-server-listen %s" %
                           shlex.quote(alternate),
                "reason": "Retry explicitly on the deterministic alternate listener",
            }])

    def _launch_locked(self, config: ServiceConfig,
                       previous: Optional[ServiceConfig]) -> ServiceStatusResponse:
        if self.deps.which(self.deps.codex_bin) is None:
            raise FacadeFault(
                FacadeFaultCode.DAEMON_START_FAILED, "Codex executable was not found",
                "daemon_start_failed", details={"reason": "codex_not_found",
                                                 "durable_state": "preserved"})
        try:
            available = self.deps.listener_available(config.listener)
        except OSError as exc:
            raise FacadeFault(
                FacadeFaultCode.DAEMON_START_FAILED,
                "Configured listener could not be resolved or probed",
                "daemon_start_failed", details={"reason": "listener_probe_failed",
                                                 "listener": config.listener,
                                                 "cause": type(exc).__name__,
                                                 "durable_state": "preserved"}) from exc
        if not available:
            raise self._address_in_use(config.listener)
        receipt = self.deps.paths.rpc_socket.parent / (
            "start-%s.json" % config.generation_id)
        if receipt.exists() or receipt.is_symlink():
            raise FacadeFault(
                FacadeFaultCode.DAEMON_START_FAILED,
                "Global service startup receipt path is occupied", "daemon_start_failed",
                details={"reason": "unsafe_startup_receipt", "path": str(receipt),
                         "durable_state": "preserved"})
        try:
            process = self.deps.spawn(
                self._serve_argv(config, receipt), str(self.deps.paths.log_path))
        except OSError as exc:
            raise FacadeFault(
                FacadeFaultCode.DAEMON_START_FAILED,
                "Global service process could not be spawned", "daemon_start_failed",
                details={"reason": "spawn_failed", "cause": type(exc).__name__,
                         "log_path": str(self.deps.paths.log_path),
                         "durable_state": "preserved"}) from exc
        deadline = self.deps.monotonic() + 2.0
        while True:
            try:
                status = self._probe_readiness()
            except BaseException:
                self.deps.terminate_spawn(process)
                raise
            if status is not None:
                if status.listener != config.listener:
                    self.deps.terminate_spawn(process)
                    raise self._conflict(status.listener, config.listener)
                if status.service_version != self.expected_version:
                    self.deps.terminate_spawn(process)
                    raise FacadeFault(
                        FacadeFaultCode.TOOL_VERSION_MISMATCH,
                        "Global service version did not match the installed command",
                        "tool_version_mismatch",
                        details={"expected_version": self.expected_version,
                                 "actual_version": status.service_version})
                current = self._read_config()
                try:
                    if current != config:
                        if previous is None: self._write_config_once(config)
                        elif current == previous: self._replace_config(config)
                        else: raise self._conflict(current.listener, config.listener)
                except BaseException:
                    self.deps.terminate_spawn(process)
                    raise
                if status.status != "ready":
                    raise FacadeFault(
                        FacadeFaultCode.DAEMON_START_FAILED,
                        "Global service is not exactly ready", "daemon_start_failed",
                        details={"reason": "service_not_ready", "status": status.status,
                                 "durable_state": "preserved"})
                return status
            exited = (process is not None and hasattr(process, "poll")
                      and process.poll() is not None)
            timed_out = self.deps.monotonic() >= deadline
            if exited or timed_out:
                if timed_out and not exited:
                    self.deps.terminate_spawn(process)
                if self._startup_collision(receipt, config.listener):
                    raise self._address_in_use(config.listener)
                # The gateway's actual bind is authoritative.  Re-probing only after
                # that attempt preserves collision typing across the preflight gap.
                try:
                    available_after = self.deps.listener_available(config.listener)
                except OSError as exc:
                    raise FacadeFault(
                        FacadeFaultCode.DAEMON_START_FAILED,
                        "Configured listener could not be reprobed",
                        "daemon_start_failed",
                        details={"reason": "listener_probe_failed",
                                 "listener": config.listener,
                                 "cause": type(exc).__name__,
                                 "durable_state": "preserved"}) from exc
                if not available_after:
                    raise self._address_in_use(config.listener)
                reason = "child_exited" if exited else "readiness_timeout"
                raise FacadeFault(
                    FacadeFaultCode.DAEMON_START_FAILED,
                    "Global service process exited before readiness" if exited
                    else "Global service did not become ready",
                    "daemon_start_failed", retryable=not exited,
                    details={"reason": reason,
                             "exit_code": process.poll() if exited else None,
                             "durable_state": "preserved"})
            self.deps.wait(0.01)

    def _startup_collision(self, path: Path, listener: str) -> bool:
        if not path.exists() and not path.is_symlink():
            return False
        verified = None
        try:
            metadata = os.lstat(str(path))
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) != 0o600):
                return False
            verified = metadata
            value = json.loads(path.read_text(encoding="utf-8"))
            return value == {"kind": "address_in_use", "listener": listener}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False
        finally:
            try:
                current = os.lstat(str(path))
                if (verified is not None
                        and (current.st_dev, current.st_ino) == (
                            verified.st_dev, verified.st_ino)):
                    os.unlink(str(path))
            except FileNotFoundError:
                pass

    def _replace_config(self, config: ServiceConfig) -> None:
        path = self.deps.paths.config_path
        temporary = path.with_name(".%s.%s" % (path.name, uuid.uuid4().hex))
        fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config.to_dict(), handle, separators=(",", ":"), sort_keys=True)
                handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            os.replace(str(temporary), path)
            directory_fd = os.open(str(path.parent), os.O_RDONLY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
        except BaseException:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
            raise

    def _serve_argv(self, config: ServiceConfig, receipt: Path) -> Sequence[str]:
        paths = self.deps.paths
        return [self.deps.launcher, "--socket", str(paths.rpc_socket), "daemon", "serve",
                "--state", str(paths.registry_path), "--codex-bin", self.deps.codex_bin,
                "--app-server-listen", config.listener,
                "--generation", config.generation_id,
                "--startup-receipt", str(receipt)]

    def _await_stopped(self, before) -> None:
        deadline = self.deps.monotonic() + 2.0
        while True:
            endpoint_exists = (self.deps.paths.rpc_socket.exists()
                               or self.deps.paths.rpc_socket.is_symlink())
            live = any(self.deps.pid_alive(pid)
                       for pid in (before.pid, before.app_server_pid))
            if self._probe_readiness() is None and not endpoint_exists and not live:
                return
            if self.deps.monotonic() >= deadline:
                raise FacadeFault(
                    FacadeFaultCode.DAEMON_STOP_FAILED,
                    "Global service did not stop after guarded maintenance",
                    "daemon_stop_failed", retryable=True,
                    details={"reason": "stop_timeout", "durable_state": "preserved"})
            self.deps.wait(0.01)

    def _parse_maintenance(self, value: dict, action: str) -> MaintenanceResult:
        try:
            result = MaintenanceResult.from_dict(value)
            if result.action != action:
                raise ValueError("maintenance action did not match request")
            return result
        except (TypeError, ValueError) as exc:
            raise FacadeFault(
                FacadeFaultCode.CODEX_PROTOCOL_ERROR,
                "Global service returned malformed maintenance impact",
                "codex_protocol_error", details={"reason": type(exc).__name__}) from exc

    @staticmethod
    def _busy(result: MaintenanceResult) -> FacadeFault:
        return FacadeFault(
            FacadeFaultCode.SERVICE_BUSY, "Global service has active work", "service_busy",
            details={"active": [item.to_dict() for item in result.inventory.items],
                     "workers": result.workers.to_dict()},
            next_actions=[{"command": "codex-worker daemon status",
                           "reason": "Inspect active global work"}])

    def stop(self, force: bool = False) -> dict:
        if type(force) is not bool: raise ValueError("force must be bool")
        with acquire_start_lock(self.deps.paths.start_lock):
            before = self._probe()
            if before is None:
                return MaintenanceResult.completed(
                    "stop", ActiveInventory(), force, workers=self._durable_workers()).to_dict()
            result = self._parse_maintenance(self._result(self.deps.rpc_call(
                str(self.deps.paths.rpc_socket), "service/stop", {"force": force}, 30.0)),
                "stop")
            if result.status == "refused": raise self._busy(result)
            self._await_stopped(before)
            return result.to_dict()

    def restart(self, listener: Optional[str] = None, force: bool = False) -> dict:
        if type(force) is not bool: raise ValueError("force must be bool")
        with acquire_start_lock(self.deps.paths.start_lock):
            current = self._probe()
            configured = self._read_config()
            requested = validate_public_listener(
                listener or (current.listener if current is not None else
                             configured.listener if configured is not None
                             else DEFAULT_PUBLIC_LISTENER))
            impact = MaintenanceResult.completed(
                "restart", ActiveInventory(), force, requested,
                self._durable_workers())
            if current is not None:
                impact = self._parse_maintenance(self._result(self.deps.rpc_call(
                    str(self.deps.paths.rpc_socket), "service/restart",
                    {"listener": requested, "force": force}, 30.0)), "restart")
                if impact.status == "refused": raise self._busy(impact)
                self._await_stopped(current)
            self._ensure_running_locked(requested, replacement=True)
            status = self._probe()
            if status is None:
                raise FacadeFault(
                    FacadeFaultCode.DAEMON_START_FAILED,
                    "Global service stopped before public status projection",
                    "daemon_start_failed", details={"reason": "status_unavailable",
                                                     "durable_state": "preserved"})
            return RestartServiceResponse(impact.to_dict(), status).to_dict()

    def _durable_workers(self) -> WorkerImpact:
        path = self.deps.paths.registry_path
        if not path.exists() and not path.is_symlink():
            return WorkerImpact()
        try:
            from .registry import RegistryError, SessionRegistry
            records = SessionRegistry.read_existing(path).list()
            return WorkerImpact([], sorted(record.name for record in records
                                           if record.name is not None))
        except (OSError, TypeError, ValueError) as exc:
            raise FacadeFault(
                FacadeFaultCode.REGISTRY_ERROR,
                "Durable worker registry is invalid", "registry_error",
                details={"reason": "invalid_registry", "path": str(path),
                         "durable_state": "preserved"}) from exc
