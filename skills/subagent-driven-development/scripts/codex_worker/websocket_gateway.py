"""Transparent one-to-one WebSocket gateway with a shared maintenance gate."""
import json
import threading
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterator, Optional, Protocol, Set, Tuple
from urllib.parse import urlsplit

from .service_domain import validate_public_listener
from .websocket_transport import MAX_FRAME_BYTES, MAX_INCOMING_QUEUE, TextConnection


DRAIN_ALLOWED_REQUESTS = frozenset({"thread/list", "thread/read", "turn/interrupt"})

# MEASURED from Codex 0.150.1 ClientRequest.json. The fixture set-equality guard makes
# upstream additions visible; unknown methods still fail closed during drain.
CURRENT_CLIENT_REQUEST_METHODS = frozenset({
    "account/login/cancel", "account/login/start", "account/logout",
    "account/rateLimitResetCredit/consume", "account/rateLimits/read", "account/read",
    "account/sendAddCreditsNudgeEmail", "account/usage/read",
    "account/workspaceMessages/read", "app/installed", "app/list", "app/read",
    "command/exec", "command/exec/resize", "command/exec/terminate", "command/exec/write",
    "config/batchWrite", "config/mcpServer/reload", "config/read", "config/value/write",
    "configRequirements/read", "experimentalFeature/enablement/set",
    "experimentalFeature/list", "externalAgentConfig/detect", "externalAgentConfig/import",
    "externalAgentConfig/import/readHistories", "externalAgentConfig/import/recordHistory",
    "feedback/upload", "fs/copy", "fs/createDirectory", "fs/getMetadata",
    "fs/readDirectory", "fs/readFile", "fs/remove", "fs/unwatch", "fs/watch",
    "fs/writeFile", "fuzzyFileSearch", "hooks/list", "initialize", "marketplace/add",
    "marketplace/remove", "marketplace/upgrade", "mcpServer/oauth/login",
    "mcpServer/resource/read", "mcpServer/tool/call", "mcpServerStatus/list", "model/list",
    "modelProvider/capabilities/read", "permissionProfile/list", "plugin/install",
    "plugin/installed", "plugin/list", "plugin/read", "plugin/share/checkout",
    "plugin/share/delete", "plugin/share/list", "plugin/share/save",
    "plugin/share/updateTargets", "plugin/skill/read", "plugin/uninstall", "review/start",
    "skills/config/write", "skills/extraRoots/set", "skills/list",
    "thread/approveGuardianDeniedAction", "thread/archive", "thread/compact/start",
    "thread/delete", "thread/fork", "thread/goal/clear", "thread/goal/get",
    "thread/goal/set", "thread/inject_items", "thread/list", "thread/loaded/list",
    "thread/metadata/update", "thread/name/set", "thread/read", "thread/resume",
    "thread/rollback", "thread/section/move", "thread/shellCommand", "thread/start",
    "thread/unarchive", "thread/unsubscribe", "threadSection/create",
    "threadSection/delete", "threadSection/list", "threadSection/update", "turn/interrupt",
    "turn/start", "turn/steer", "windowsSandbox/readiness", "windowsSandbox/setupStart",
})


class FrameClass(str, Enum):
    RESPONSE = "response"
    ALLOWED = "allowed"
    BLOCKED = "blocked"


class ServiceBusyError(RuntimeError):
    def __init__(self, method: str):
        self.method = method
        super().__init__("service is draining; request blocked: %s" % method)


_LEASE_AUTHORITY = object()


class DrainLease:
    """Short-lived authorization issued only while one exact gate is drained."""

    def __init__(self, authority: object, gate_token: object):
        if authority is not _LEASE_AUTHORITY:
            raise TypeError("DrainLease values are issued by ServiceMaintenanceGate")
        self._gate_token = gate_token
        self._live = True

    def _expire(self) -> None:
        self._live = False


class ServiceMaintenanceGate:
    """Exclude new mutations and settle forwarded work before maintenance inventory."""

    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._draining = False
        self._active_mutations = 0
        self._gate_token = object()
        self._lease = None  # type: Optional[DrainLease]

    @property
    def draining(self) -> bool:
        with self._condition:
            return self._draining

    @property
    def active_mutations(self) -> int:
        with self._condition:
            return self._active_mutations

    @contextmanager
    def mutation(self, method: str) -> Iterator[None]:
        if not isinstance(method, str) or not method:
            raise ValueError("mutation method must be non-empty")
        with self._condition:
            if self._draining:
                raise ServiceBusyError(method)
            self._active_mutations += 1
        try:
            yield
        finally:
            with self._condition:
                self._active_mutations -= 1
                if self._active_mutations < 0:
                    raise AssertionError("maintenance mutation accounting underflow")
                if self._active_mutations == 0:
                    self._condition.notify_all()

    @contextmanager
    def drain(self) -> Iterator[DrainLease]:
        with self._condition:
            while self._draining:
                self._condition.wait()
            self._draining = True
            while self._active_mutations:
                self._condition.wait()
            lease = DrainLease(_LEASE_AUTHORITY, self._gate_token)
            self._lease = lease
        try:
            yield lease
        finally:
            with self._condition:
                if self._lease is lease:
                    self._lease = None
                lease._expire()
                self._draining = False
                self._condition.notify_all()

    def authorize(self, lease: object) -> None:
        with self._condition:
            if (not isinstance(lease, DrainLease)
                    or lease._gate_token is not self._gate_token
                    or not lease._live
                    or self._lease is not lease
                    or not self._draining
                    or self._active_mutations != 0):
                raise PermissionError("a live drain lease from this maintenance gate is required")


def classify_frontend_frame(value: object) -> FrameClass:
    if not isinstance(value, dict):
        return FrameClass.BLOCKED
    method = value.get("method")
    if method is None and _request_key(value.get("id")) is not None:
        has_result = "result" in value
        has_error = "error" in value
        if has_result != has_error:
            return FrameClass.RESPONSE
    if isinstance(method, str) and method in DRAIN_ALLOWED_REQUESTS:
        return FrameClass.ALLOWED
    return FrameClass.BLOCKED


class BackendConnector(Protocol):
    def __call__(self, endpoint: str, max_frame_bytes: int,
                 max_queue: int) -> TextConnection:
        ...


class GatewayServer(Protocol):
    def serve_forever(self) -> None:
        ...

    def shutdown(self) -> None:
        ...


class ServerBinder(Protocol):
    def __call__(self, handler: object, host: str, port: int,
                 max_frame_bytes: int, max_queue: int) -> GatewayServer:
        ...


@dataclass(frozen=True)
class GatewayDeps:
    connect_backend: BackendConnector
    bind_server: ServerBinder


def _default_backend_connect(endpoint: str, max_frame_bytes: int,
                             max_queue: int) -> TextConnection:
    from websockets.sync.client import unix_connect

    if not endpoint.startswith("unix://"):
        raise ValueError("gateway backend must be a private unix:// endpoint")
    return unix_connect(
        endpoint[len("unix://"):],
        uri="ws://localhost/rpc",
        max_size=max_frame_bytes,
        max_queue=max_queue,
        compression=None,
    )


def _default_bind_server(handler: object, host: str, port: int,
                         max_frame_bytes: int, max_queue: int) -> GatewayServer:
    from websockets.sync.server import serve

    return serve(
        handler,
        host,
        port,
        max_size=max_frame_bytes,
        max_queue=max_queue,
    )


def default_gateway_deps() -> GatewayDeps:
    return GatewayDeps(_default_backend_connect, _default_bind_server)


def _request_key(value: object) -> Optional[Tuple[str, object]]:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    return (type(value).__name__, value)


@dataclass
class _Bridge:
    frontend: TextConnection
    backend: TextConnection
    pending: Dict[Tuple[str, object], AbstractContextManager]
    lock: threading.RLock
    closed: bool = False


class WebSocketGateway:
    """Bind one exact public endpoint and bridge each frontend to one backend."""

    def __init__(self, listener: str, private_endpoint: str,
                 gate: ServiceMaintenanceGate,
                 deps: Optional[GatewayDeps] = None):
        self.listener = validate_public_listener(listener)
        if not isinstance(private_endpoint, str) or not private_endpoint.startswith("unix://"):
            raise ValueError("private endpoint must be unix://")
        if not isinstance(gate, ServiceMaintenanceGate):
            raise TypeError("gate must be ServiceMaintenanceGate")
        self.private_endpoint = private_endpoint
        self.gate = gate
        self._deps = deps or default_gateway_deps()
        self._lock = threading.RLock()
        self._server = None  # type: Optional[GatewayServer]
        self._server_thread = None  # type: Optional[threading.Thread]
        self._bridges = set()  # type: Set[int]
        self._bridge_values = {}  # type: Dict[int, _Bridge]
        self._ready = False

    @property
    def ready(self) -> bool:
        with self._lock:
            return self._ready

    def start(self) -> None:
        with self._lock:
            if self._ready:
                return
        parsed = urlsplit(self.listener)
        host = parsed.hostname
        port = parsed.port
        if host is None or port is None:
            raise ValueError("listener must have host and port")
        # The bind call is the collision authority. OSError propagates; no peer is
        # inspected, signalled, unlinked, trusted, or replaced and no port fallback exists.
        server = self._deps.bind_server(
            self._handle_frontend, host, port, MAX_FRAME_BYTES, MAX_INCOMING_QUEUE)
        thread = threading.Thread(
            target=server.serve_forever,
            name="codex-websocket-gateway",
            daemon=True,
        )
        with self._lock:
            self._server = server
            self._server_thread = thread
            self._ready = True
        thread.start()

    def _handle_frontend(self, frontend: TextConnection) -> None:
        try:
            backend = self._deps.connect_backend(
                self.private_endpoint, MAX_FRAME_BYTES, MAX_INCOMING_QUEUE)
        except Exception:
            try:
                frontend.close()
            except Exception:
                pass
            return
        bridge = _Bridge(frontend, backend, {}, threading.RLock())
        identity = id(bridge)
        with self._lock:
            self._bridges.add(identity)
            self._bridge_values[identity] = bridge
        frontend_thread = threading.Thread(
            target=self._pump_frontend,
            args=(bridge,),
            name="codex-gateway-frontend",
            daemon=True,
        )
        backend_thread = threading.Thread(
            target=self._pump_backend,
            args=(bridge,),
            name="codex-gateway-backend",
            daemon=True,
        )
        frontend_thread.start()
        backend_thread.start()
        frontend_thread.join()
        self._close_bridge(identity, bridge)
        backend_thread.join(timeout=1.0)

    def _pump_frontend(self, bridge: _Bridge) -> None:
        try:
            while True:
                frame = bridge.frontend.recv()
                self._forward_frontend(bridge, frame)
        except Exception:
            return
        finally:
            # Wake the opposite pump. The handler owns final accounting/cleanup.
            try:
                bridge.backend.close()
            except Exception:
                pass

    def _forward_frontend(self, bridge: _Bridge, frame: object) -> None:
        if (not isinstance(frame, str)
                or len(frame.encode("utf-8")) > MAX_FRAME_BYTES):
            self._send_fault(bridge.frontend, None, "invalid_request", -32600, None)
            return
        try:
            value = json.loads(frame)
        except (TypeError, ValueError):
            self._send_fault(bridge.frontend, None, "invalid_request", -32600, None)
            return
        if not isinstance(value, dict):
            self._send_fault(bridge.frontend, None, "invalid_request", -32600, None)
            return
        if "id" in value and _request_key(value.get("id")) is None:
            self._send_fault(bridge.frontend, None, "invalid_request", -32600, None)
            return
        frame_class = classify_frontend_frame(value)
        if frame_class in (FrameClass.RESPONSE, FrameClass.ALLOWED):
            bridge.backend.send(frame)
            return
        method = value.get("method")
        if not isinstance(method, str) or not method:
            self._send_fault(bridge.frontend, value.get("id"), "invalid_request", -32600, None)
            return
        key = _request_key(value.get("id")) if "id" in value else None
        if key is not None:
            with bridge.lock:
                if key in bridge.pending:
                    self._send_fault(
                        bridge.frontend, value.get("id"), "invalid_request", -32600, None)
                    return
        context = self.gate.mutation(method)
        try:
            context.__enter__()
        except ServiceBusyError:
            self._send_fault(bridge.frontend, value.get("id"), "service_busy", -32040, method)
            return
        if key is not None:
            # Publish accounting before forwarding so a fast backend response can't
            # outrun registration and strand the maintenance gate.
            with bridge.lock:
                bridge.pending[key] = context
        try:
            bridge.backend.send(frame)
            if key is None:
                context.__exit__(None, None, None)
        except BaseException:
            with bridge.lock:
                retained = key is not None and bridge.pending.get(key) is context
                if retained:
                    bridge.pending.pop(key, None)
            if retained or key is None:
                context.__exit__(None, None, None)
            raise

    @staticmethod
    def _send_fault(frontend: TextConnection, request_id: object, kind: str,
                    code: int, method: Optional[str]) -> None:
        data = {"kind": kind, "retryable": kind == "service_busy"}
        if method is not None:
            data["method"] = method
        frontend.send(json.dumps({
            "id": request_id if _request_key(request_id) is not None else None,
            "error": {
                "code": code,
                "message": "service is draining" if kind == "service_busy" else "invalid request",
                "data": data,
            },
        }, separators=(",", ":")))

    def _pump_backend(self, bridge: _Bridge) -> None:
        try:
            while True:
                frame = bridge.backend.recv()
                if not isinstance(frame, str):
                    raise ValueError("backend frame must be text")
                if len(frame.encode("utf-8")) > MAX_FRAME_BYTES:
                    raise ValueError("backend frame exceeded limit")
                try:
                    value = json.loads(frame)
                except (TypeError, ValueError):
                    value = None
                if isinstance(value, dict) and value.get("method") is None:
                    key = _request_key(value.get("id"))
                    if key is not None:
                        with bridge.lock:
                            context = bridge.pending.pop(key, None)
                        if context is not None:
                            context.__exit__(None, None, None)
                bridge.frontend.send(frame)
        except Exception:
            return
        finally:
            # A backend-first close must not strand the frontend pump or its mutation tokens.
            try:
                bridge.frontend.close()
            except Exception:
                pass

    def _close_bridge(self, identity: int, bridge: _Bridge) -> None:
        with bridge.lock:
            if bridge.closed:
                return
            bridge.closed = True
            pending = list(bridge.pending.values())
            bridge.pending.clear()
        for context in pending:
            context.__exit__(None, None, None)
        for connection in (bridge.frontend, bridge.backend):
            try:
                connection.close()
            except Exception:
                pass
        with self._lock:
            self._bridges.discard(identity)
            self._bridge_values.pop(identity, None)

    def close(self) -> None:
        with self._lock:
            server = self._server
            thread = self._server_thread
            bridges = list(self._bridge_values.items())
            self._server = None
            self._server_thread = None
            self._ready = False
        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass
        for identity, bridge in bridges:
            self._close_bridge(identity, bridge)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
