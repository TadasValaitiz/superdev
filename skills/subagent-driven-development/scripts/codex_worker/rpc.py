"""Local AF_UNIX JSON-RPC server and client for the Codex worker broker."""
import errno
import json
import os
import socket
import socketserver
import stat
import threading
from typing import Any, Callable, Dict, Optional, Union

from .models import IdentifierSelector, JsonObject, RpcFault, rpc_response

JsonId = Optional[Union[str, int]]

MAX_REQUEST_BYTES = 1024 * 1024


class SocketPathUnsafe(RuntimeError):
    """The requested socket path collides with something the daemon must not remove."""


class SocketInUse(RuntimeError):
    """The requested socket path is already served by a live process."""


def _fault(code: int, message: str, kind: str,
           recovery: Optional[str] = None, details: Optional[JsonObject] = None) -> RpcFault:
    return RpcFault(code, message, kind, recovery, details)


def _standard_fault(code: int, message: str, kind: str) -> RpcFault:
    return _fault(code, message, kind)


PARSE_ERROR = _standard_fault(-32700, "Parse error", "parse_error")
INVALID_REQUEST = _standard_fault(-32600, "Invalid Request", "invalid_request")
METHOD_NOT_FOUND = _standard_fault(-32601, "Method not found", "method_not_found")
INVALID_PARAMS = _standard_fault(-32602, "Invalid params", "invalid_params")
INTERNAL_ERROR = _standard_fault(-32603, "Internal error", "internal_error")


def daemon_unavailable_fault(socket_path: str) -> RpcFault:
    return _fault(
        -32000,
        "Codex worker daemon is not available",
        "daemon_unavailable",
        recovery="run codex-worker --socket %s daemon serve" % socket_path,
        details={"socket_path": socket_path},
    )


def encode_response(request_id: JsonId, result: Optional[JsonObject] = None,
                    fault: Optional[RpcFault] = None) -> bytes:
    envelope = rpc_response(request_id, result=result, fault=fault)
    return (json.dumps(envelope, separators=(",", ":")) + "\n").encode("utf-8")


class ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class RpcRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        request_id = None  # type: JsonId
        method = None  # type: Optional[str]
        try:
            raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
            if not raw or len(raw) > MAX_REQUEST_BYTES:
                self._write(encode_response(None, fault=INVALID_REQUEST))
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError, TypeError):
                self._write(encode_response(None, fault=PARSE_ERROR))
                return
            request_id = self._request_id(payload)
            try:
                method, params = self._validate_request(payload)
                result = self.server.dispatch(method, params)  # type: ignore[attr-defined]
                self._write(encode_response(request_id, result=result))
                if method == "daemon/shutdown":
                    self.server.request_shutdown()  # type: ignore[attr-defined]
            except RpcFault as fault:
                self._write(encode_response(request_id, fault=fault))
            except ValueError as exc:
                self._write(encode_response(request_id, fault=_fault(
                    -32602, "Invalid params", "invalid_params", details={"reason": str(exc)}
                )))
            except Exception as exc:
                self._write(encode_response(request_id, fault=_fault(
                    -32603, "Internal error", "internal_error", details={"reason": type(exc).__name__}
                )))
        except (BrokenPipeError, ConnectionError, OSError):
            return

    def _write(self, payload: bytes) -> None:
        self.wfile.write(payload)
        self.wfile.flush()

    @staticmethod
    def _request_id(payload: Any) -> JsonId:
        if not isinstance(payload, dict):
            return None
        request_id = payload.get("id")
        if type(request_id) in (str, int) or request_id is None:
            return request_id
        return None

    @staticmethod
    def _validate_request(payload: Any):
        if not isinstance(payload, dict):
            raise INVALID_REQUEST
        if payload.get("jsonrpc") != "2.0":
            raise INVALID_REQUEST
        if type(payload.get("id")) not in (str, int):
            raise INVALID_REQUEST
        method = payload.get("method")
        if not isinstance(method, str) or not method:
            raise INVALID_REQUEST
        params = payload.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise _fault(-32602, "Invalid params", "invalid_params")
        return method, params


class RpcServer(ThreadingUnixServer):
    """Threaded one-request-per-connection JSON-RPC server over an AF_UNIX path."""

    def __init__(self, socket_path: str, broker: Any):
        if not isinstance(socket_path, str) or not socket_path:
            raise SocketPathUnsafe("socket_path must be a non-empty string")
        self.socket_path = socket_path
        self.broker = broker
        self._shutdown_started = False
        self._bound_stat = None
        self._prepare_socket_path(socket_path)
        parent = os.path.dirname(socket_path)
        if parent:
            os.makedirs(parent, mode=0o700, exist_ok=True)
            try:
                os.chmod(parent, 0o700)
            except OSError:
                pass
        super().__init__(socket_path, RpcRequestHandler)
        os.chmod(socket_path, 0o600)
        try:
            self._bound_stat = os.stat(socket_path)
        except OSError:
            self._bound_stat = None

    def server_close(self) -> None:
        super().server_close()
        self._unlink_owned_socket()

    def request_shutdown(self) -> None:
        if self._shutdown_started:
            return
        self._shutdown_started = True
        threading.Thread(target=self.shutdown, name="codex-worker-rpc-shutdown", daemon=True).start()

    def dispatch(self, method: str, params: JsonObject) -> JsonObject:
        dispatcher = _DISPATCH.get(method)
        if dispatcher is None:
            raise _fault(-32601, "Method not found", "method_not_found", details={"method": method})
        return dispatcher(self.broker, params)

    def _prepare_socket_path(self, socket_path: str) -> None:
        try:
            metadata = os.lstat(socket_path)
        except FileNotFoundError:
            return
        if not stat.S_ISSOCK(metadata.st_mode):
            raise SocketPathUnsafe("socket path exists and is not a socket: %s" % socket_path)
        if _socket_accepts_connections(socket_path):
            raise SocketInUse("socket path is already served: %s" % socket_path)
        os.unlink(socket_path)

    def _unlink_owned_socket(self) -> None:
        try:
            metadata = os.lstat(self.socket_path)
        except FileNotFoundError:
            return
        if not stat.S_ISSOCK(metadata.st_mode):
            return
        if self._bound_stat is not None:
            if (metadata.st_dev, metadata.st_ino) != (self._bound_stat.st_dev, self._bound_stat.st_ino):
                return
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass


def _socket_accepts_connections(socket_path: str) -> bool:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(0.25)
        try:
            client.connect(socket_path)
        except OSError as exc:
            if exc.errno in (errno.ECONNREFUSED, errno.ENOENT, errno.ENOTSOCK):
                return False
            raise SocketInUse("socket path could not be probed safely: %s" % socket_path)
        request = {"jsonrpc": "2.0", "id": "probe", "method": "daemon/status", "params": {}}
        client.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
        # If a process accepted the connection, treat it as live even if it is
        # slow, incompatible, or returns an error.  Safety beats convenience:
        # never unlink a socket with an accepting peer behind it.
        try:
            client.recv(1)
        except (socket.timeout, OSError):
            pass
        return True
    finally:
        client.close()


def rpc_call(socket_path: str, method: str, params: Optional[JsonObject] = None,
             timeout: float = 30.0) -> JsonObject:
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    request = {"jsonrpc": "2.0", "id": "cli", "method": method, "params": params}
    received = b""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(timeout)
        try:
            client.connect(socket_path)
        except OSError as exc:
            raise daemon_unavailable_fault(socket_path) from exc
        encoded = (json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            client.sendall(encoded)
            while not received.endswith(b"\n"):
                chunk = client.recv(65536)
                if not chunk:
                    break
                received += chunk
                if len(received) > MAX_REQUEST_BYTES:
                    raise _fault(-32016, "Daemon response is too large", "daemon_protocol_error")
        except (socket.timeout, OSError) as exc:
            raise daemon_unavailable_fault(socket_path) from exc
    finally:
        client.close()
    if not received:
        raise daemon_unavailable_fault(socket_path)
    try:
        response = json.loads(received.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise _fault(-32016, "Daemon returned malformed JSON", "daemon_protocol_error") from exc
    if not isinstance(response, dict):
        raise _fault(-32016, "Daemon returned a non-object response", "daemon_protocol_error")
    return response


def _optional_string(params: JsonObject, key: str) -> Optional[str]:
    value = params.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("%s must be a non-empty string" % key)
    return value


def _required_string(params: JsonObject, key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError("%s must be a non-empty string" % key)
    return value


def _selector(params: JsonObject) -> IdentifierSelector:
    session_id = params.get("session_id")
    thread_id = params.get("thread_id")
    if session_id is not None and (not isinstance(session_id, str) or not session_id):
        raise ValueError("session_id must be a non-empty string")
    if thread_id is not None and (not isinstance(thread_id, str) or not thread_id):
        raise ValueError("thread_id must be a non-empty string")
    return IdentifierSelector(session_id=session_id, thread_id=thread_id)


def _number(params: JsonObject, key: str) -> float:
    value = params.get(key)
    if type(value) not in (int, float):
        raise ValueError("%s must be a number" % key)
    return float(value)


def _integer(params: JsonObject, key: str) -> int:
    value = params.get(key)
    if type(value) is not int:
        raise ValueError("%s must be an integer" % key)
    return value


def _no_params(broker: Any, params: JsonObject, method: Callable[[], JsonObject]) -> JsonObject:
    if params:
        raise ValueError("method does not accept params")
    return method()


def _daemon_status(broker: Any, params: JsonObject) -> JsonObject:
    return _no_params(broker, params, broker.daemon_status)


def _daemon_shutdown(broker: Any, params: JsonObject) -> JsonObject:
    return _no_params(broker, params, broker.shutdown)


def _model_list(broker: Any, params: JsonObject) -> JsonObject:
    return _no_params(broker, params, broker.model_list)


def _session_start(broker: Any, params: JsonObject) -> JsonObject:
    return broker.session_start(
        _required_string(params, "cwd"),
        name=_optional_string(params, "name"),
        model=_optional_string(params, "model"),
    )


def _session_resume(broker: Any, params: JsonObject) -> JsonObject:
    return broker.session_resume(_selector(params), name=_optional_string(params, "name"))


def _session_list(broker: Any, params: JsonObject) -> JsonObject:
    return _no_params(broker, params, broker.session_list)


def _session_show(broker: Any, params: JsonObject) -> JsonObject:
    return broker.session_show(_selector(params))


def _turn_start(broker: Any, params: JsonObject) -> JsonObject:
    return broker.turn_start(
        _selector(params),
        _required_string(params, "prompt"),
        model=_optional_string(params, "model"),
        effort=_optional_string(params, "effort"),
    )


def _turn_status(broker: Any, params: JsonObject) -> JsonObject:
    return broker.turn_status(_selector(params))


def _turn_wait(broker: Any, params: JsonObject) -> JsonObject:
    timeout = _number(params, "timeout")
    if timeout < 0:
        raise ValueError("timeout must be non-negative")
    return broker.turn_wait(_selector(params), timeout)


def _turn_events(broker: Any, params: JsonObject) -> JsonObject:
    after = _integer(params, "after")
    limit = _integer(params, "limit")
    if after < 0:
        raise ValueError("after must be non-negative")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    return broker.turn_events(_selector(params), after, limit)


def _turn_steer(broker: Any, params: JsonObject) -> JsonObject:
    return broker.turn_steer(_selector(params), _required_string(params, "prompt"))


def _turn_interrupt(broker: Any, params: JsonObject) -> JsonObject:
    return broker.turn_interrupt(_selector(params))


_DISPATCH = {
    "daemon/status": _daemon_status,
    "daemon/shutdown": _daemon_shutdown,
    "model/list": _model_list,
    "session/start": _session_start,
    "session/resume": _session_resume,
    "session/list": _session_list,
    "session/show": _session_show,
    "turn/start": _turn_start,
    "turn/status": _turn_status,
    "turn/wait": _turn_wait,
    "turn/events": _turn_events,
    "turn/steer": _turn_steer,
    "turn/interrupt": _turn_interrupt,
}  # type: Dict[str, Callable[[Any, JsonObject], JsonObject]]
