"""Lifecycle composition for one global Codex worker service generation."""
import ipaddress
import errno
import os
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol, Sequence
from urllib.parse import urlsplit

from .commands import StrictModel
from .models import JsonObject
from .path_security import unsafe_ancestor
from .service_domain import ServiceConfig, ServicePaths
from .websocket_gateway import DrainLease, ServiceMaintenanceGate, WebSocketGateway
from .websocket_transport import CodexConnection, codex_child_env


PRIVATE_SOCKET_TIMEOUT = 5.0
_LIFECYCLE_ISSUER = object()


class OwnedProcess(Protocol):
    pid: int

    def poll(self) -> Optional[int]:
        ...

    def terminate(self) -> None:
        ...

    def wait(self, timeout: Optional[float] = None) -> int:
        ...

    def kill(self) -> None:
        ...


class SpawnCodex(Protocol):
    def __call__(self, argv: Sequence[str], cwd: str,
                 env: Mapping[str, str]) -> OwnedProcess:
        ...


class CreateConnection(Protocol):
    def __call__(self, endpoint: str,
                 on_notification: Callable[[JsonObject], None],
                 approval_handler: Optional[Callable[[JsonObject], JsonObject]]) -> CodexConnection:
        ...


class CreateGateway(Protocol):
    def __call__(self, listener: str, endpoint: str,
                 gate: ServiceMaintenanceGate) -> WebSocketGateway:
        ...


@dataclass(frozen=True)
class GlobalWorkerServiceDeps:
    spawn_codex: SpawnCodex
    create_connection: CreateConnection
    create_gateway: CreateGateway
    get_process_group: Callable[[int], int] = os.getpgid
    current_process_group: Callable[[], int] = os.getpgrp
    signal_process_group: Callable[[int, int], None] = os.killpg
    process_group_exists: Callable[[int], bool] = lambda pgid: _process_group_exists(pgid)


class ListenerExposure(str, Enum):
    LOOPBACK = "loopback"
    NON_LOOPBACK = "non_loopback"


class GatewayAuthentication(str, Enum):
    NONE = "none"


@dataclass(frozen=True)
class GlobalWorkerServiceStatus(StrictModel):
    ready: bool
    listener: str
    worker_version: str
    codex_pid: Optional[int]
    private_codex_socket: str
    exposure: ListenerExposure
    authentication: GatewayAuthentication

    def __post_init__(self) -> None:
        super().__post_init__()
        if type(self.ready) is not bool:
            raise ValueError("ready must be bool")
        if not self.listener or not self.worker_version:
            raise ValueError("listener and worker_version must be non-empty")
        if self.codex_pid is not None and (type(self.codex_pid) is not int or self.codex_pid <= 0):
            raise ValueError("codex_pid must be positive when present")
        if not Path(self.private_codex_socket).is_absolute():
            raise ValueError("private_codex_socket must be absolute")


@dataclass(frozen=True)
class _ServiceLifecycle:
    """Private composition capability consumed by Task 3's maintenance coordinator."""

    _service: "GlobalWorkerService"
    _gate: ServiceMaintenanceGate

    def __init__(self, issuer: object, service: "GlobalWorkerService",
                 gate: ServiceMaintenanceGate):
        if issuer is not _LIFECYCLE_ISSUER:
            raise TypeError("service lifecycle capabilities are internally composed")
        object.__setattr__(self, "_service", service)
        object.__setattr__(self, "_gate", gate)

    @property
    def gate(self) -> ServiceMaintenanceGate:
        return self._gate

    def terminate_owned(self, lease: DrainLease) -> None:
        self._gate.authorize(lease)
        self._service._terminate_resources()


def _spawn_codex(argv: Sequence[str], cwd: str,
                 env: Mapping[str, str]) -> OwnedProcess:
    return subprocess.Popen(
        list(argv),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=cwd,
        env=dict(env),
        start_new_session=True,
    )


def _process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        if exc.errno == errno.EPERM:
            return True
        raise


def _create_connection(endpoint: str,
                       on_notification: Callable[[JsonObject], None],
                       approval_handler: Optional[Callable[[JsonObject], JsonObject]]) -> CodexConnection:
    return CodexConnection(endpoint, on_notification, approval_handler)


def _create_gateway(listener: str, endpoint: str,
                    gate: ServiceMaintenanceGate) -> WebSocketGateway:
    return WebSocketGateway(listener, endpoint, gate)


def default_service_deps() -> GlobalWorkerServiceDeps:
    return GlobalWorkerServiceDeps(_spawn_codex, _create_connection, _create_gateway)


def _verify_private_socket(path: Path, uid: int) -> os.stat_result:
    value = os.lstat(str(path))
    if not stat.S_ISSOCK(value.st_mode):
        raise PermissionError("private Codex path is not a Unix socket")
    if value.st_uid != uid:
        raise PermissionError("private Codex socket is not owned by the service user")
    if stat.S_IMODE(value.st_mode) & 0o077:
        raise PermissionError("private Codex socket must be owner-only")
    return value


def _ensure_owner_directory(path: Path) -> None:
    """Create and harden one directory without traversing symlink components."""
    if not path.is_absolute():
        raise ValueError("service directory must be absolute")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        try:
            value = os.lstat(str(current))
        except FileNotFoundError:
            unsafe = unsafe_ancestor(current.parent)
            if unsafe is not None:
                raise PermissionError("unsafe service directory ancestor: %s" % unsafe)
            current.mkdir(mode=0o700)
            value = os.lstat(str(current))
            if value.st_uid != os.getuid():
                raise PermissionError("created service directory is not owner-owned")
            os.chmod(str(current), 0o700)
        else:
            unsafe = unsafe_ancestor(current)
            if unsafe is not None:
                raise PermissionError("unsafe service directory ancestor: %s" % unsafe)
            if stat.S_ISLNK(value.st_mode):
                # The shared policy permits only a leading root-owned platform alias.
                continue
            if not stat.S_ISDIR(value.st_mode):
                raise PermissionError(
                    "service directory path must contain only real directories")
    value = os.lstat(str(path))
    if not stat.S_ISDIR(value.st_mode) or value.st_uid != os.getuid():
        raise PermissionError("service directory must be a real owner-owned directory")
    os.chmod(str(path), 0o700)
    if stat.S_IMODE(os.lstat(str(path)).st_mode) != 0o700:
        raise PermissionError("service directory must be owner-only")


class GlobalWorkerService:
    """Own the private Codex authority and public gateway for one generation."""

    def __init__(
            self,
            paths: ServicePaths,
            config: ServiceConfig,
            on_notification: Callable[[JsonObject], None],
            approval_handler: Optional[Callable[[JsonObject], JsonObject]] = None,
            deps: Optional[GlobalWorkerServiceDeps] = None,
            codex_argv: Sequence[str] = ("codex",)):
        if not isinstance(paths, ServicePaths):
            raise TypeError("paths must be ServicePaths")
        if not isinstance(config, ServiceConfig):
            raise TypeError("config must be ServiceConfig")
        if not callable(on_notification):
            raise ValueError("on_notification must be callable")
        if not codex_argv:
            raise ValueError("codex_argv must not be empty")
        self.paths = paths
        self.config = config
        self._on_notification = on_notification
        self._approval_handler = approval_handler
        self._deps = deps or default_service_deps()
        self._codex_argv = tuple(codex_argv)
        self._worker_version = config.worker_version
        self._maintenance_gate = ServiceMaintenanceGate()
        self._lifecycle_capability = _ServiceLifecycle(
            _LIFECYCLE_ISSUER, self, self._maintenance_gate)
        self._process = None  # type: Optional[OwnedProcess]
        self._owned_pgid = None  # type: Optional[int]
        self._connection = None  # type: Optional[CodexConnection]
        self._gateway = None  # type: Optional[WebSocketGateway]
        self._private_socket_identity = None  # type: Optional[os.stat_result]

    @property
    def private_endpoint(self) -> str:
        return "unix://%s" % self.paths.private_codex_socket

    def start(self) -> GlobalWorkerServiceStatus:
        if self.status().ready:
            return self.status()
        self._prepare_paths()
        if self.paths.private_codex_socket.exists() or self.paths.private_codex_socket.is_symlink():
            raise FileExistsError("private Codex socket already exists; refusing to unlink it")
        gateway = self._deps.create_gateway(
            self.config.listener, self.private_endpoint, self._maintenance_gate)
        try:
            # Bind the exact public authority before the child exists. A public collision
            # therefore cannot spawn, kill, trust, or otherwise disturb another peer.
            gateway.start()
            self._gateway = gateway
            argv = self._codex_argv + (
                "app-server", "--listen", self.private_endpoint,
            )
            process = self._deps.spawn_codex(
                argv, str(self.paths.durable_dir), codex_child_env())
            self._process = process
            self._owned_pgid = self._pin_process_group(process)
            self._wait_private_socket(process)
            connection = self._deps.create_connection(
                self.private_endpoint, self._on_notification, self._approval_handler)
            self._connection = connection
            if not gateway.ready or process.poll() is not None:
                raise RuntimeError("service components did not remain ready")
            return self.status()
        except BaseException:
            self._rollback_start(gateway)
            raise

    def _prepare_paths(self) -> None:
        _ensure_owner_directory(self.paths.durable_dir)
        runtime_dir = self.paths.private_codex_socket.parent
        _ensure_owner_directory(runtime_dir)

    def _wait_private_socket(self, process: OwnedProcess) -> None:
        deadline = time.monotonic() + PRIVATE_SOCKET_TIMEOUT
        while True:
            if self.paths.private_codex_socket.exists() or self.paths.private_codex_socket.is_symlink():
                self._private_socket_identity = _verify_private_socket(
                    self.paths.private_codex_socket, os.getuid())
                return
            if process.poll() is not None:
                raise RuntimeError("Codex exited before creating its private socket")
            if time.monotonic() >= deadline:
                raise TimeoutError("Codex private socket did not become ready")
            time.sleep(0.01)

    def status(self) -> GlobalWorkerServiceStatus:
        process = self._process
        gateway = self._gateway
        ready = bool(
            process is not None
            and process.poll() is None
            and self._connection is not None
            and gateway is not None
            and gateway.ready
        )
        return GlobalWorkerServiceStatus(
            ready=ready,
            listener=self.config.listener,
            worker_version=self._worker_version,
            codex_pid=process.pid if process is not None and process.poll() is None else None,
            private_codex_socket=str(self.paths.private_codex_socket),
            exposure=self._listener_exposure(),
            authentication=GatewayAuthentication.NONE,
        )

    def _listener_exposure(self) -> ListenerExposure:
        host = urlsplit(self.config.listener).hostname
        if host is not None and host.lower() == "localhost":
            return ListenerExposure.LOOPBACK
        try:
            address = ipaddress.ip_address(host or "")
        except ValueError:
            return ListenerExposure.NON_LOOPBACK
        return (ListenerExposure.LOOPBACK if address.is_loopback
                else ListenerExposure.NON_LOOPBACK)

    def _lifecycle_for_composition(self) -> _ServiceLifecycle:
        """Return the private capability wired only into Task 3 lifecycle composition."""
        return self._lifecycle_capability

    def _rollback_start(self, gateway: WebSocketGateway) -> None:
        if self._gateway is None:
            try:
                gateway.close()
            except Exception:
                pass
        self._terminate_resources(suppress_errors=True)

    def _pin_process_group(self, process: OwnedProcess) -> int:
        pid = process.pid
        try:
            pgid = self._deps.get_process_group(pid)
            current = self._deps.current_process_group()
            if (type(pid) is not int or pid <= 1 or type(pgid) is not int
                    or pgid != pid or pgid <= 1 or pgid == current):
                raise PermissionError("Codex process group is not a new owned session")
            return pgid
        except BaseException:
            self._terminate_unpinned_process(process)
            raise

    @staticmethod
    def _terminate_unpinned_process(process: OwnedProcess) -> None:
        if process.poll() is not None:
            process.wait(timeout=0)
            return
        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)

    def _terminate_owned_process_group(
            self, process: OwnedProcess, pgid: Optional[int]) -> None:
        if pgid is None:
            self._terminate_unpinned_process(process)
            return
        if pgid <= 1 or pgid == self._deps.current_process_group():
            raise PermissionError("refusing unsafe Codex process group")
        if process.poll() is None:
            current = self._deps.get_process_group(process.pid)
            if current != pgid or current != process.pid:
                raise PermissionError("Codex process group identity changed")
        self._deps.signal_process_group(pgid, signal.SIGTERM)
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass
        if self._deps.process_group_exists(pgid):
            self._deps.signal_process_group(pgid, signal.SIGKILL)
        deadline = time.monotonic() + 2.0
        while self._deps.process_group_exists(pgid) and time.monotonic() < deadline:
            time.sleep(0.01)
        if self._deps.process_group_exists(pgid):
            raise RuntimeError("owned Codex process group remained live")
        if process.poll() is None:
            process.wait(timeout=2.0)

    def _terminate_resources(self, suppress_errors: bool = False) -> None:
        gateway = self._gateway
        connection = self._connection
        process = self._process
        owned_pgid = self._owned_pgid
        private_socket_identity = self._private_socket_identity
        self._gateway = None
        self._connection = None
        self._process = None
        self._owned_pgid = None
        self._private_socket_identity = None
        errors = []
        if gateway is not None:
            try:
                gateway.close()
            except Exception as exc:
                errors.append(exc)
        if connection is not None:
            try:
                connection.close()
            except Exception as exc:
                errors.append(exc)
        if process is not None and process.poll() is None:
            try:
                self._terminate_owned_process_group(process, owned_pgid)
            except Exception as exc:
                errors.append(exc)
        elif process is not None and owned_pgid is not None:
            try:
                self._terminate_owned_process_group(process, owned_pgid)
            except Exception as exc:
                errors.append(exc)
        private_socket = self.paths.private_codex_socket
        if private_socket.exists() or private_socket.is_symlink():
            try:
                current = _verify_private_socket(private_socket, os.getuid())
                if (private_socket_identity is None
                        or (current.st_dev, current.st_ino) != (
                            private_socket_identity.st_dev,
                            private_socket_identity.st_ino)):
                    raise PermissionError(
                        "private Codex socket changed after readiness")
                os.unlink(str(private_socket))
            except Exception as exc:
                errors.append(exc)
        if errors and not suppress_errors:
            raise errors[0]
