"""Local AF_UNIX JSON-RPC server and client for the Codex worker broker."""
import errno
import fcntl
import json
import math
import os
import socket
import socketserver
import stat
import threading
import time
from typing import Any, Callable, Dict, Optional, Union

from .models import IdentifierSelector, JsonObject, RpcFault, rpc_response
from .commands import (FacadeFault, GoalSetRequest, GoalShowRequest, InterruptWorkerRequest,
                       LimitsRequest, Ok, RunWorkerRequest, StartWorkerRequest,
                       MessageWorkerRequest, SteerWorkerRequest, WorkerHistoryRequest, WorkerMessagesRequest,
                       WorkerStatusRequest)

JsonId = Optional[Union[str, int]]

# A proactive message may legitimately approach one million UTF-16 code units;
# Python's ASCII-safe JSON encoding can expand each unit to a six-byte escape.
# Leave bounded headroom for the daemon-owned final-envelope refusal while keeping
# the client response cap smaller and independent.
MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
START_LOCK_TIMEOUT_SECONDS = 2.0


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


def socket_endpoint_unsafe_fault(socket_path: str, reason: str) -> RpcFault:
    return _fault(
        -32017,
        "Codex worker socket endpoint is unsafe",
        "socket_endpoint_unsafe",
        recovery="remove the unsafe endpoint and restart codex-worker daemon serve",
        details={"socket_path": socket_path, "reason": reason},
    )


def _json_dumps(payload: JsonObject) -> str:
    return json.dumps(payload, separators=(",", ":"), allow_nan=False)


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-finite JSON constant is not allowed: %s" % value)


def _json_loads(data: Union[str, bytes]) -> Any:
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data, parse_constant=_reject_json_constant)


def _finite_nonnegative_float(value: Any, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError("%s must be a finite non-negative number" % label)
    try:
        parsed = float(value)
    except OverflowError as exc:
        raise ValueError("%s must be finite" % label) from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError("%s must be a finite non-negative number" % label)
    return parsed


def _bounded_platform_timeout(timeout: float) -> float:
    maximum = getattr(threading, "TIMEOUT_MAX", None)
    if type(maximum) in (int, float) and math.isfinite(float(maximum)):
        return min(timeout, float(maximum))
    return timeout


def encode_response(request_id: JsonId, result: Optional[JsonObject] = None,
                    fault: Optional[RpcFault] = None) -> bytes:
    envelope = rpc_response(request_id, result=result, fault=fault)
    return (_json_dumps(envelope) + "\n").encode("utf-8")


class ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class RpcRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        request_id = None  # type: JsonId
        method = None  # type: Optional[str]
        shutdown_accepted = False
        try:
            raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
            if not raw or len(raw) > MAX_REQUEST_BYTES:
                self._write(encode_response(None, fault=INVALID_REQUEST))
                return
            try:
                payload = _json_loads(raw)
            except (UnicodeDecodeError, ValueError, TypeError):
                self._write(encode_response(None, fault=PARSE_ERROR))
                return
            request_id = self._request_id(payload)
            try:
                method, params = self._validate_request(payload)
                result = self.server.dispatch(method, params)  # type: ignore[attr-defined]
                shutdown_accepted = method == "daemon/shutdown"
                self._write(encode_response(request_id, result=result))
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
        finally:
            if shutdown_accepted:
                self.server.request_shutdown()  # type: ignore[attr-defined]

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
        if "params" not in payload or not isinstance(payload.get("params"), dict):
            raise _fault(-32602, "Invalid params", "invalid_params")
        return method, payload["params"]


COMMON_METHODS = {
    "worker/start": ("start", StartWorkerRequest),
    "worker/run": ("run", RunWorkerRequest),
    "worker/message": ("message", MessageWorkerRequest),
    "worker/status": ("status", WorkerStatusRequest),
    "worker/messages": ("messages", WorkerMessagesRequest),
    "worker/history": ("history", WorkerHistoryRequest),
    "worker/steer": ("steer", SteerWorkerRequest),
    "worker/interrupt": ("interrupt", InterruptWorkerRequest),
    "worker/goal/set": ("goal_set", GoalSetRequest),
    "worker/goal/show": ("goal_show", GoalShowRequest),
    "account/limits": ("limits", LimitsRequest),
}


class FacadeRpcFault(RpcFault):
    """RPC adapter preserving the façade's richer refusal data unchanged."""
    def __init__(self, fault: FacadeFault):
        super().__init__(fault.code.value, fault.message, fault.kind)
        self._facade_fault = fault

    def to_dict(self) -> JsonObject:
        return self._facade_fault.to_dict()


class RpcServer(ThreadingUnixServer):
    """Threaded one-request-per-connection JSON-RPC server over an AF_UNIX path."""

    def __init__(self, socket_path: str, broker: Any, facade: Any = None):
        if not isinstance(socket_path, str) or not socket_path:
            raise SocketPathUnsafe("socket_path must be a non-empty string")
        self.socket_path = socket_path
        self.broker = broker
        self.facade = facade
        self._shutdown_started = False
        self._bound_stat = None
        self._lock_fd = None  # type: Optional[int]
        parent = os.path.dirname(socket_path)
        if parent:
            os.makedirs(parent, mode=0o700, exist_ok=True)
        parent_reason = _unsafe_socket_parent_reason(socket_path)
        if parent_reason is not None:
            raise SocketPathUnsafe(parent_reason)
        try:
            self._acquire_start_lock()
            self._prepare_socket_path(socket_path)
            try:
                super().__init__(socket_path, RpcRequestHandler, bind_and_activate=False)
                previous_umask = os.umask(0o177)
                try:
                    self.server_bind()
                finally:
                    os.umask(previous_umask)
                self._bound_stat = os.lstat(socket_path)
                if not stat.S_ISSOCK(self._bound_stat.st_mode) or self._bound_stat.st_uid != os.getuid():
                    raise SocketPathUnsafe("bound socket inode is unsafe")
                os.chmod(socket_path, 0o600)
                hardened = os.lstat(socket_path)
                if ((hardened.st_dev, hardened.st_ino) != (self._bound_stat.st_dev, self._bound_stat.st_ino)
                        or not stat.S_ISSOCK(hardened.st_mode)
                        or hardened.st_uid != os.getuid()
                        or stat.S_IMODE(hardened.st_mode) != 0o600):
                    raise SocketPathUnsafe("bound socket permissions could not be hardened")
                self._bound_stat = hardened
                self.server_activate()
            except OSError:
                if hasattr(self, "socket"):
                    self.server_close()
                raise
            except BaseException:
                if hasattr(self, "socket"):
                    self.server_close()
                raise
        finally:
            self._release_start_lock()

    def server_close(self) -> None:
        super().server_close()
        self._unlink_owned_socket()

    def request_shutdown(self) -> None:
        if self._shutdown_started:
            return
        self._shutdown_started = True
        threading.Thread(target=self.shutdown, name="codex-worker-rpc-shutdown", daemon=True).start()

    def dispatch(self, method: str, params: JsonObject) -> JsonObject:
        common = COMMON_METHODS.get(method)
        if common is not None:
            if self.facade is None:
                raise _fault(-32601, "Method not found", "method_not_found", details={"method": method})
            operation, request_type = common
            try:
                request = request_type.from_dict(params)
            except ValueError as exc:
                raise _fault(-32602, "Invalid params", "invalid_params", details={"reason": str(exc)}) from exc
            result = getattr(self.facade, operation)(request)
            if isinstance(result, Ok):
                return result.value.to_dict()
            fault = result.error
            if isinstance(fault, FacadeFault):
                raise FacadeRpcFault(fault)
            raise _fault(-32603, "Internal error", "internal_error")
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
        if metadata.st_uid != os.getuid():
            raise SocketPathUnsafe("socket path is not owned by this user: %s" % socket_path)
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
        if self._bound_stat is None:
            return
        if (metadata.st_dev, metadata.st_ino) != (self._bound_stat.st_dev, self._bound_stat.st_ino):
            return
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass

    def _acquire_start_lock(self) -> None:
        lock_path = self.socket_path + ".lock"
        try:
            existing = os.lstat(lock_path)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.getuid():
                raise SocketPathUnsafe("socket lock path must be an owner-owned regular file")
            if stat.S_IMODE(existing.st_mode) & 0o077:
                raise SocketPathUnsafe("socket lock path must be owner-only")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise SocketPathUnsafe("socket lock path is unsafe: %s" % lock_path) from exc
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise SocketPathUnsafe("socket lock path must be an owner-owned regular file")
            os.fchmod(fd, 0o600)
            metadata = os.fstat(fd)
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise SocketPathUnsafe("socket lock path permissions could not be hardened")
            deadline = time.monotonic() + START_LOCK_TIMEOUT_SECONDS
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise SocketInUse("socket startup lock is held: %s" % lock_path)
                    time.sleep(0.02)
        except BaseException:
            os.close(fd)
            raise
        self._lock_fd = fd

    def _release_start_lock(self) -> None:
        if self._lock_fd is None:
            return
        fd = self._lock_fd
        self._lock_fd = None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


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
        client.sendall((_json_dumps(request) + "\n").encode("utf-8"))
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
             timeout: Optional[float] = 30.0) -> JsonObject:
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    if timeout is not None:
        timeout = _bounded_platform_timeout(_finite_nonnegative_float(timeout, "timeout"))
    expected_endpoint = _validate_socket_endpoint(socket_path)
    request = {"jsonrpc": "2.0", "id": "cli", "method": method, "params": params}
    received = b""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.settimeout(timeout)
        try:
            client.connect(socket_path)
        except OSError as exc:
            raise daemon_unavailable_fault(socket_path) from exc
        encoded = (_json_dumps(request) + "\n").encode("utf-8")
        try:
            _validate_socket_endpoint(socket_path, expected_endpoint)
            client.sendall(encoded)
            while not received.endswith(b"\n"):
                chunk = client.recv(65536)
                if not chunk:
                    break
                received += chunk
                if len(received) > MAX_RESPONSE_BYTES:
                    raise _fault(-32016, "Daemon response is too large", "daemon_protocol_error")
        except (socket.timeout, OSError) as exc:
            if isinstance(exc, RpcFault):
                raise
            raise daemon_unavailable_fault(socket_path) from exc
    finally:
        client.close()
    if not received:
        raise daemon_unavailable_fault(socket_path)
    try:
        response = _json_loads(received)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise _fault(-32016, "Daemon returned malformed JSON", "daemon_protocol_error") from exc
    _validate_response_envelope(response, expected_id="cli")
    return response


def _validate_response_envelope(response: Any, expected_id: str) -> None:
    if not isinstance(response, dict):
        raise _fault(-32016, "Daemon returned a non-object response", "daemon_protocol_error")
    if response.get("jsonrpc") != "2.0":
        raise _fault(-32016, "Daemon response has invalid jsonrpc version", "daemon_protocol_error")
    if response.get("id") != expected_id:
        raise _fault(-32016, "Daemon response id does not match request", "daemon_protocol_error")
    has_result = "result" in response
    has_error = "error" in response
    if has_result == has_error:
        raise _fault(-32016, "Daemon response must contain exactly one of result or error",
                     "daemon_protocol_error")
    if has_result and not isinstance(response.get("result"), dict):
        raise _fault(-32016, "Daemon response result must be an object", "daemon_protocol_error")
    if has_error:
        error = response.get("error")
        if (not isinstance(error, dict)
                or type(error.get("code")) is not int
                or not isinstance(error.get("message"), str)
                or not isinstance(error.get("data"), dict)
                or not isinstance(error["data"].get("kind"), str)):
            raise _fault(-32016, "Daemon response error is malformed", "daemon_protocol_error")


def _validate_socket_endpoint(socket_path: str, expected: Any = None):
    try:
        metadata = os.lstat(socket_path)
    except FileNotFoundError as exc:
        raise daemon_unavailable_fault(socket_path) from exc
    except OSError as exc:
        raise socket_endpoint_unsafe_fault(socket_path, "could not inspect socket path") from exc
    if expected is not None and (metadata.st_dev, metadata.st_ino) != (expected.st_dev, expected.st_ino):
        raise socket_endpoint_unsafe_fault(socket_path, "socket endpoint changed during connect")
    if not stat.S_ISSOCK(metadata.st_mode):
        raise socket_endpoint_unsafe_fault(socket_path, "path is not an AF_UNIX socket")
    if metadata.st_uid != os.getuid():
        raise socket_endpoint_unsafe_fault(socket_path, "socket is not owned by this user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise socket_endpoint_unsafe_fault(socket_path, "socket is accessible by group or other users")
    parent_reason = _unsafe_socket_parent_reason(socket_path)
    if parent_reason is not None:
        raise socket_endpoint_unsafe_fault(socket_path, parent_reason)
    return metadata


def _unsafe_socket_parent_reason(socket_path: str) -> Optional[str]:
    parent = os.path.dirname(socket_path) or "."
    try:
        parent_metadata = os.lstat(parent)
    except OSError as exc:
        return "could not inspect socket parent: %s" % type(exc).__name__
    if not stat.S_ISDIR(parent_metadata.st_mode):
        return "socket parent is not a directory"
    parent_mode = stat.S_IMODE(parent_metadata.st_mode)
    parent_writable_by_others = bool(parent_mode & 0o022)
    parent_sticky = bool(parent_metadata.st_mode & stat.S_ISVTX)
    if parent_writable_by_others and not parent_sticky:
        return "socket parent is writable by group/other users without sticky-bit protection"
    return None


def _expect_params(params: JsonObject, allowed, required=()) -> None:
    allowed_set = set(allowed)
    unexpected = sorted(set(params) - allowed_set)
    if unexpected:
        raise ValueError("unexpected params: %s" % ", ".join(unexpected))
    missing = [key for key in required if key not in params]
    if missing:
        raise ValueError("missing params: %s" % ", ".join(missing))


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
    try:
        parsed = float(value)
    except OverflowError as exc:
        raise ValueError("%s must be finite" % key) from exc
    if not math.isfinite(parsed):
        raise ValueError("%s must be finite" % key)
    return parsed


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
    _expect_params(params, ("cwd", "name", "model"), required=("cwd",))
    return broker.session_start(
        _required_string(params, "cwd"),
        name=_optional_string(params, "name"),
        model=_optional_string(params, "model"),
    )


def _session_resume(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id", "name"))
    return broker.session_resume(_selector(params), name=_optional_string(params, "name"))


def _session_list(broker: Any, params: JsonObject) -> JsonObject:
    return _no_params(broker, params, broker.session_list)


def _session_show(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id"))
    return broker.session_show(_selector(params))


def _turn_start(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id", "prompt", "model", "effort"), required=("prompt",))
    return broker.turn_start(
        _selector(params),
        _required_string(params, "prompt"),
        model=_optional_string(params, "model"),
        effort=_optional_string(params, "effort"),
    )


def _turn_status(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id"))
    return broker.turn_status(_selector(params))


def _turn_wait(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id", "timeout"), required=("timeout",))
    timeout = _number(params, "timeout")
    if timeout < 0:
        raise ValueError("timeout must be non-negative")
    return broker.turn_wait(_selector(params), _bounded_platform_timeout(timeout))


def _turn_events(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id", "after", "limit"), required=("after", "limit"))
    after = _integer(params, "after")
    limit = _integer(params, "limit")
    if after < 0:
        raise ValueError("after must be non-negative")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    return broker.turn_events(_selector(params), after, limit)


def _turn_steer(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id", "prompt"), required=("prompt",))
    return broker.turn_steer(_selector(params), _required_string(params, "prompt"))


def _turn_interrupt(broker: Any, params: JsonObject) -> JsonObject:
    _expect_params(params, ("session_id", "thread_id"))
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
