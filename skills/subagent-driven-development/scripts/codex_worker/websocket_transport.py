"""Initialized, bounded JSON-RPC transport over one Codex WebSocket connection."""
import itertools
import json
import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol

from .models import JsonObject


MAX_FRAME_BYTES = 4 * 1024 * 1024
MAX_INCOMING_QUEUE = 16
MAX_READ_RETRIES = 2
MAX_INITIALIZE_RECONNECTS = 1
OVERLOAD_CODE = -32001

IDEMPOTENT_READ_METHODS = frozenset({
    "account/rateLimits/read",
    "account/read",
    "account/usage/read",
    "account/workspaceMessages/read",
    "app/list",
    "app/read",
    "config/read",
    "configRequirements/read",
    "experimentalFeature/list",
    "hooks/list",
    "mcpServer/resource/read",
    "mcpServerStatus/list",
    "model/list",
    "modelProvider/capabilities/read",
    "permissionProfile/list",
    "plugin/list",
    "plugin/read",
    "plugin/share/list",
    "plugin/skill/read",
    "skills/list",
    "thread/goal/get",
    "thread/list",
    "thread/loaded/list",
    "thread/read",
    "thread/turns/list",
})

APPROVAL_METHODS = frozenset({
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
    "item/tool/requestUserInput",
    "item/permissions/requestApproval",
})


class TextConnection(Protocol):
    def send(self, frame: str) -> None:
        ...

    def recv(self, timeout: Optional[float] = None) -> object:
        ...

    def close(self) -> None:
        ...


class ConnectionFactory(Protocol):
    def __call__(self, endpoint: str, max_frame_bytes: int,
                 max_queue: int) -> TextConnection:
        ...


class Sleep(Protocol):
    def __call__(self, delay: float) -> None:
        ...


class Jitter(Protocol):
    def __call__(self, delay: float) -> float:
        ...


@dataclass(frozen=True)
class CodexConnectionDeps:
    connect: ConnectionFactory
    sleep: Sleep
    jitter: Jitter


class CodexCallError(RuntimeError):
    def __init__(self, kind: str, method: str, details: Optional[JsonObject] = None):
        self.kind = kind
        self.method = method
        self.details = details
        message = "%s: %s" % (method, kind)
        if details and isinstance(details.get("message"), str):
            message += ": " + details["message"]
        super().__init__(message)

    @classmethod
    def from_response(cls, method: str, error: Any):
        details = dict(error) if isinstance(error, dict) else {"message": str(error)}
        kind = "upstream_busy" if details.get("code") == OVERLOAD_CODE else "upstream_error"
        return cls(kind, method, details)


class CodexTransportError(CodexCallError):
    def __init__(self, kind: str = "transport_error", method: str = "transport",
                 details: Optional[JsonObject] = None):
        super().__init__(kind, method, details)


def default_approval_response(method: str) -> JsonObject:
    if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
        return {"decision": "decline"}
    if method == "item/tool/requestUserInput":
        return {"answers": {}}
    if method == "item/permissions/requestApproval":
        return {"permissions": {}}
    return {}


def is_decline(method: str, result: JsonObject) -> bool:
    if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
        return result.get("decision") in ("decline", "cancel")
    if method == "item/tool/requestUserInput":
        return not result.get("answers")
    if method == "item/permissions/requestApproval":
        return not result.get("permissions")
    return True


class CodexMethodAdapter:
    """Protocol-independent Codex convenience methods implemented through ``call``."""

    def call(self, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: float = 120.0) -> JsonObject:
        raise NotImplementedError

    def list_models(self) -> List[JsonObject]:
        data = self.call("model/list", {}).get("data", [])
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise CodexCallError("protocol_error", "model/list", {"message": "data must be a list"})
        return data

    def start_thread(self, cwd: str, model: Optional[str] = None,
                     sandbox: str = "workspace-write",
                     allow_provider_model_fallback: Optional[bool] = None) -> JsonObject:
        params = {
            "cwd": cwd,
            "approvalPolicy": "never",
            "sandbox": sandbox,
            "serviceName": "superdev_codex_worker",
        }  # type: Dict[str, Any]
        if model is not None:
            params["model"] = model
        if allow_provider_model_fallback is not None:
            params["allowProviderModelFallback"] = allow_provider_model_fallback
        return self.call("thread/start", params)

    def resume_thread(self, thread_id: str, approval_policy: str = "never",
                      sandbox: str = "workspace-write") -> JsonObject:
        return self.call("thread/resume", {
            "threadId": thread_id,
            "approvalPolicy": approval_policy,
            "sandbox": sandbox,
        })

    def start_turn(self, thread_id: str, prompt: str, model: Optional[str] = None,
                   effort: Optional[str] = None,
                   sandbox_policy: Optional[JsonObject] = None,
                   output_schema: Optional[JsonObject] = None) -> str:
        params = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt}],
        }  # type: Dict[str, Any]
        if model is not None:
            params["model"] = model
        if effort is not None:
            params["effort"] = effort
        if sandbox_policy is not None:
            params["sandboxPolicy"] = sandbox_policy
        if output_schema is not None:
            params["outputSchema"] = output_schema
        result = self.call("turn/start", params)
        turn = result.get("turn")
        if not isinstance(turn, dict) or not isinstance(turn.get("id"), str):
            raise CodexCallError("protocol_error", "turn/start", {"message": "missing turn id"})
        return turn["id"]

    def steer(self, thread_id: str, turn_id: str, prompt: str) -> str:
        result = self.call("turn/steer", {
            "threadId": thread_id,
            "expectedTurnId": turn_id,
            "input": [{"type": "text", "text": prompt}],
        })
        returned_id = result.get("turnId")
        if not isinstance(returned_id, str):
            raise CodexCallError("protocol_error", "turn/steer", {"message": "missing turn id"})
        return returned_id

    def interrupt(self, thread_id: str, turn_id: str) -> None:
        self.call("turn/interrupt", {"threadId": thread_id, "turnId": turn_id})


def _default_connect(endpoint: str, max_frame_bytes: int,
                     max_queue: int) -> TextConnection:
    # Lazy import keeps the source package importable before the isolated tool is built.
    from websockets.sync.client import connect, unix_connect

    options = {
        "max_size": max_frame_bytes,
        "max_queue": max_queue,
        # Codex's Unix upgrader doesn't negotiate permessage-deflate.
        "compression": None,
    }
    if endpoint.startswith("unix://"):
        path = endpoint[len("unix://"):]
        return unix_connect(path, uri="ws://localhost/rpc", **options)
    return connect(endpoint, **options)


def _default_jitter(delay: float) -> float:
    # Bounded deterministic-in-range jitter without retaining caller data.
    return min(delay * 0.1, 0.05)


def default_connection_deps() -> CodexConnectionDeps:
    return CodexConnectionDeps(_default_connect, time.sleep, _default_jitter)


def codex_child_env() -> Dict[str, str]:
    """Copy ambient process state without product-managed callback credentials."""
    child_env = dict(os.environ)
    child_env.pop("CLAUDE_CODE_MESSAGING_SOCKET", None)
    child_env.pop("CLAUDE_CODE_MESSAGING_TOKEN", None)
    return child_env


class CodexConnection(CodexMethodAdapter):
    """One initialized JSON-RPC connection with request correlation and bounded retry."""

    def __init__(
            self,
            endpoint: str,
            on_notification: Callable[[JsonObject], None],
            approval_handler: Optional[Callable[[JsonObject], JsonObject]] = None,
            deps: Optional[CodexConnectionDeps] = None):
        if not isinstance(endpoint, str) or not endpoint:
            raise ValueError("endpoint must be non-empty")
        if not callable(on_notification):
            raise ValueError("on_notification must be callable")
        self.endpoint = endpoint
        self._on_notification = on_notification
        self._approval_handler = approval_handler
        self._deps = deps or default_connection_deps()
        self._ids = itertools.count(1)
        self._pending = {}  # type: Dict[int, queue.Queue]
        self._state_lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._closed = False
        self._close_error = None  # type: Optional[CodexTransportError]
        self._socket = None  # type: Optional[TextConnection]
        self._reader = None  # type: Optional[threading.Thread]
        self.stderr_diagnostics = []  # type: List[str]
        try:
            self._initialize_with_reconnect()
        except BaseException:
            self.close()
            raise

    def _initialize_with_reconnect(self) -> None:
        for attempt in range(MAX_INITIALIZE_RECONNECTS + 1):
            self._open_transport()
            try:
                self._call_once("initialize", {
                    "clientInfo": {
                        "name": "superdev_codex_worker",
                        "title": "Superdev Codex Worker",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "experimentalApi": True,
                        "optOutNotificationMethods": [
                            "item/agentMessage/delta",
                            "item/reasoning/textDelta",
                            "item/reasoning/summaryTextDelta",
                            "item/commandExecution/outputDelta",
                        ],
                    },
                }, 120.0)
            except CodexCallError as exc:
                if exc.kind != "upstream_busy" or attempt >= MAX_INITIALIZE_RECONNECTS:
                    raise
                self._retire_transport()
                self._backoff(attempt)
                continue
            self.notify("initialized", {})
            return

    def _open_transport(self) -> None:
        connection = self._deps.connect(self.endpoint, MAX_FRAME_BYTES, MAX_INCOMING_QUEUE)
        with self._state_lock:
            if self._closed:
                connection.close()
                raise CodexTransportError(details={"message": "connection is closed"})
            self._socket = connection
            reader = threading.Thread(
                target=self._read_loop,
                args=(connection,),
                name="codex-websocket-reader",
                daemon=True,
            )
            self._reader = reader
        reader.start()

    def _retire_transport(self) -> None:
        with self._state_lock:
            connection = self._socket
            reader = self._reader
            self._socket = None
            self._reader = None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=1.0)

    def _read_loop(self, connection: TextConnection) -> None:
        try:
            while True:
                frame = connection.recv()
                if not isinstance(frame, str):
                    raise ValueError("Codex WebSocket frame must be text")
                if len(frame.encode("utf-8")) > MAX_FRAME_BYTES:
                    raise ValueError("Codex WebSocket frame exceeded limit")
                try:
                    message = json.loads(frame)
                except (TypeError, ValueError) as exc:
                    raise ValueError("invalid JSON from Codex") from exc
                if not isinstance(message, dict):
                    raise ValueError("non-object JSON from Codex")
                self._dispatch(message)
        except Exception as exc:
            with self._state_lock:
                if self._socket is not connection or self._closed:
                    return
            self._fail_transport(CodexTransportError(details={
                "message": "Codex WebSocket receive failed",
                "error": type(exc).__name__,
            }))

    def _require_open(self) -> None:
        if self._closed:
            if self._close_error is not None:
                raise self._close_error
            raise CodexTransportError(details={"message": "connection is closed"})
        if self._socket is None:
            raise CodexTransportError(details={"message": "connection is unavailable"})

    def _send(self, message: JsonObject) -> None:
        encoded = json.dumps(message, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_FRAME_BYTES:
            raise CodexCallError("frame_too_large", str(message.get("method", "transport")))
        with self._write_lock:
            with self._state_lock:
                self._require_open()
                connection = self._socket
            try:
                connection.send(encoded)  # type: ignore[union-attr]
            except Exception as exc:
                error = CodexTransportError(details={
                    "message": "Codex WebSocket send failed",
                    "error": type(exc).__name__,
                })
                self._fail_transport(error)
                raise error

    def _call_once(self, method: str, params: Optional[Dict[str, Any]],
                   timeout: float) -> JsonObject:
        request_id = next(self._ids)
        pending = queue.Queue(maxsize=1)  # type: queue.Queue
        with self._state_lock:
            self._require_open()
            self._pending[request_id] = pending
        try:
            self._send({"method": method, "id": request_id, "params": params or {}})
        except BaseException:
            with self._state_lock:
                self._pending.pop(request_id, None)
            raise
        try:
            message = pending.get(timeout=timeout)
        except queue.Empty:
            with self._state_lock:
                self._pending.pop(request_id, None)
            raise CodexCallError("timeout", method)
        if isinstance(message, BaseException):
            raise message
        if "error" in message:
            raise CodexCallError.from_response(method, message["error"])
        result = message.get("result")
        if not isinstance(result, dict):
            raise CodexCallError("protocol_error", method, {"message": "result must be an object"})
        return result

    def call(self, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: float = 120.0) -> JsonObject:
        if not isinstance(method, str) or not method:
            raise ValueError("method must be non-empty")
        attempts = MAX_READ_RETRIES + 1 if method in IDEMPOTENT_READ_METHODS else 1
        for attempt in range(attempts):
            try:
                return self._call_once(method, params, timeout)
            except CodexCallError as exc:
                if exc.kind != "upstream_busy" or attempt + 1 >= attempts:
                    raise
                self._backoff(attempt)
        raise AssertionError("unreachable read retry")

    def _backoff(self, attempt: int) -> None:
        delay = min(0.05 * (2 ** attempt), 0.5)
        self._deps.sleep(delay + max(0.0, self._deps.jitter(delay)))

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        self._send({"method": method, "params": params or {}})

    def _dispatch(self, message: JsonObject) -> None:
        method = message.get("method")
        if "id" in message:
            request_id = message.get("id")
            if isinstance(request_id, bool) or not isinstance(request_id, (int, str)):
                raise ValueError("JSON-RPC id must be an integer or string")
        if "id" in message and method is None:
            with self._state_lock:
                pending = self._pending.pop(message.get("id"), None)
            if pending is not None:
                pending.put_nowait(message)
            return
        if "id" in message and isinstance(method, str):
            self._handle_server_request(message)
            return
        if isinstance(method, str):
            self._emit_notification(message)

    def _handle_server_request(self, message: JsonObject) -> None:
        method = message.get("method")
        if not isinstance(method, str):
            return
        if self._approval_handler is None:
            result = default_approval_response(method)
        else:
            try:
                candidate = self._approval_handler(message)
            except Exception:
                candidate = default_approval_response(method)
                with self._state_lock:
                    self.stderr_diagnostics.append("approval handler raised; request declined")
            result = candidate if isinstance(candidate, dict) else default_approval_response(method)
        self._send({"id": message["id"], "result": result})
        if method in APPROVAL_METHODS and is_decline(method, result):
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            self._emit_notification({"method": "approval/declined", "params": {
                "threadId": params.get("threadId"),
                "turnId": params.get("turnId"),
                "requestId": message.get("id"),
                "approvalMethod": method,
                "decision": "decline",
            }})

    def _emit_notification(self, message: JsonObject) -> None:
        try:
            self._on_notification(message)
        except BaseException:
            with self._state_lock:
                self.stderr_diagnostics.append("notification observer raised")

    def _fail_transport(self, error: CodexTransportError) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._close_error = error
            pending = list(self._pending.values())
            self._pending.clear()
            connection = self._socket
            self._socket = None
        for waiter in pending:
            try:
                waiter.put_nowait(error)
            except queue.Full:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        self._emit_notification({"method": "transport/error", "params": {
            "kind": "transport_error",
            "details": dict(error.details) if error.details is not None else None,
        }})

    def close(self) -> None:
        error = CodexTransportError(details={"message": "connection closed"})
        self._fail_transport(error)
        reader = self._reader
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=1.0)

    def shutdown(self) -> None:
        """Compatibility alias for broker code migrating from the stdio adapter."""
        self.close()
