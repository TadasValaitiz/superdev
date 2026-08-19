"""Thread-safe stdio adapter for one shared Codex app-server subprocess."""
import itertools
import json
import queue
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence

from .models import JsonObject


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
        return cls("upstream_error", method, details)


class CodexTransportError(CodexCallError):
    def __init__(self, kind: str = "transport_error", method: str = "transport",
                 details: Optional[JsonObject] = None):
        super().__init__(kind, method, details)


class CodexAppServer:
    """Newline-delimited JSON-RPC adapter with serialized writes and call routing."""

    _APPROVAL_METHODS = {
        "item/commandExecution/requestApproval",
        "item/fileChange/requestApproval",
        "item/tool/requestUserInput",
        "item/permissions/requestApproval",
    }

    def __init__(
        self,
        cwd: str,
        codex_argv: Sequence[str],
        on_notification: Callable[[JsonObject], None],
        approval_handler: Optional[Callable[[JsonObject], JsonObject]] = None,
    ):
        if not codex_argv:
            raise ValueError("codex_argv must not be empty")
        self._on_notification = on_notification
        self._approval_handler = approval_handler
        self._ids = itertools.count(1)
        self._pending = {}  # type: Dict[int, queue.Queue]
        self._state_lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._closed = False
        self._close_error = None  # type: Optional[CodexTransportError]
        self._cleanup_done = threading.Event()
        self.stderr_diagnostics = []  # type: List[str]
        self.proc = subprocess.Popen(
            list(codex_argv),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
        )
        self._reader = threading.Thread(target=self._read_loop, name="codex-app-server-reader", daemon=True)
        self._stderr_reader = threading.Thread(
            target=self._stderr_drain, name="codex-app-server-stderr", daemon=True
        )
        self._reader.start()
        self._stderr_reader.start()
        try:
            self._handshake()
        except BaseException:
            self.shutdown()
            raise

    def _require_open(self) -> None:
        if self._closed:
            if self._close_error is not None:
                raise self._close_error
            raise CodexTransportError(details={"message": "adapter is closed"})

    def _stderr_drain(self) -> None:
        stream = self.proc.stderr
        if stream is None:
            return
        for line in stream:
            # Record useful presence/size metadata, never untrusted stderr text.
            diagnostic = "codex stderr line received (%d chars)" % len(line.rstrip("\r\n"))
            with self._state_lock:
                self.stderr_diagnostics.append(diagnostic)
                if len(self.stderr_diagnostics) > 100:
                    del self.stderr_diagnostics[0]

    def _read_loop(self) -> None:
        stream = self.proc.stdout
        if stream is None:
            self._fail_transport(CodexTransportError(details={"message": "stdout unavailable"}))
            return
        try:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except (TypeError, ValueError) as exc:
                    self._fail_transport(CodexTransportError(
                        details={"message": "invalid JSONL from Codex", "error": type(exc).__name__}
                    ))
                    return
                if not isinstance(message, dict):
                    self._fail_transport(CodexTransportError(
                        details={"message": "non-object JSONL from Codex"}
                    ))
                    return
                self._dispatch(message)
        except (OSError, ValueError) as exc:
            self._fail_transport(CodexTransportError(
                details={"message": "Codex stdout read failed", "error": type(exc).__name__}
            ))
            return
        self._fail_transport(CodexTransportError(details={
            "message": "Codex app-server exited", "returncode": self.proc.poll()
        }))

    def _fail_transport(self, error: CodexTransportError) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._close_error = error
            pending = list(self._pending.values())
            self._pending.clear()
            cleanup = threading.Thread(
                target=self._cleanup_process,
                name="codex-app-server-cleanup",
                daemon=True,
            )
        for waiter in pending:
            try:
                waiter.put_nowait(error)
            except queue.Full:
                pass
        cleanup.start()
        self._emit_notification({
            "method": "transport/error",
            "params": {
                "kind": "transport_error",
                "details": dict(error.details) if error.details is not None else None,
            },
        })

    def _cleanup_process(self) -> None:
        try:
            stream = self.proc.stdin
            if stream is not None and not stream.closed:
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
            if self.proc.poll() is None:
                try:
                    self.proc.terminate()
                except OSError:
                    pass
                try:
                    self.proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    try:
                        self.proc.kill()
                    except OSError:
                        pass
                    self.proc.wait(timeout=1.0)
            current = threading.current_thread()
            for worker in (self._reader, self._stderr_reader):
                if worker is not current:
                    worker.join(timeout=1.0)
            for pipe in (self.proc.stdout, self.proc.stderr):
                if pipe is not None and not pipe.closed:
                    try:
                        pipe.close()
                    except (OSError, ValueError):
                        pass
        finally:
            self._cleanup_done.set()

    def _send(self, message: JsonObject) -> None:
        encoded = json.dumps(message, separators=(",", ":")) + "\n"
        with self._write_lock:
            with self._state_lock:
                self._require_open()
                stream = self.proc.stdin
            if stream is None:
                error = CodexTransportError(details={"message": "stdin unavailable"})
                self._fail_transport(error)
                raise error
            try:
                stream.write(encoded)
                stream.flush()
            except (BrokenPipeError, OSError, ValueError) as exc:
                error = CodexTransportError(details={
                    "message": "Codex stdin write failed", "error": type(exc).__name__
                })
                self._fail_transport(error)
                raise error

    def call(self, method: str, params: Optional[Dict[str, Any]] = None,
             timeout: float = 120.0) -> JsonObject:
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

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        self._send({"method": method, "params": params or {}})

    def _handshake(self) -> None:
        self.call("initialize", {
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
        })
        self.notify("initialized", {})

    def _dispatch(self, message: JsonObject) -> None:
        method = message.get("method")
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

    def _emit_notification(self, message: JsonObject) -> None:
        try:
            self._on_notification(message)
        except BaseException:
            # Notification observers cannot corrupt transport framing or strand calls.
            with self._state_lock:
                self.stderr_diagnostics.append("notification observer raised")

    @staticmethod
    def _default_approval_response(method: str) -> JsonObject:
        if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
            return {"decision": "decline"}
        if method == "item/tool/requestUserInput":
            return {"answers": {}}
        if method == "item/permissions/requestApproval":
            return {"permissions": {}}
        return {}

    @staticmethod
    def _is_decline(method: str, result: JsonObject) -> bool:
        if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
            return result.get("decision") in ("decline", "cancel")
        if method == "item/tool/requestUserInput":
            return not result.get("answers")
        if method == "item/permissions/requestApproval":
            return not result.get("permissions")
        return True

    def _handle_server_request(self, message: JsonObject) -> None:
        method = message.get("method")
        if not isinstance(method, str):
            return
        if self._approval_handler is None:
            result = self._default_approval_response(method)
        else:
            try:
                candidate = self._approval_handler(message)
            except Exception:
                candidate = self._default_approval_response(method)
                with self._state_lock:
                    self.stderr_diagnostics.append("approval handler raised; request declined")
            result = candidate if isinstance(candidate, dict) else self._default_approval_response(method)
        self._send({"id": message["id"], "result": result})
        if method in self._APPROVAL_METHODS and self._is_decline(method, result):
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            safe_params = {
                "threadId": params.get("threadId"),
                "turnId": params.get("turnId"),
                "requestId": message.get("id"),
                "approvalMethod": method,
                "decision": "decline",
            }
            self._emit_notification({"method": "approval/declined", "params": safe_params})

    def list_models(self) -> List[JsonObject]:
        data = self.call("model/list", {}).get("data", [])
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise CodexCallError("protocol_error", "model/list", {"message": "data must be a list"})
        return data

    def start_thread(self, cwd: str, model: Optional[str] = None,
                     sandbox: str = "workspace-write", allow_provider_model_fallback: Optional[bool] = None) -> JsonObject:
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
                   effort: Optional[str] = None, sandbox_policy: Optional[JsonObject] = None,
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

    def shutdown(self) -> None:
        error = CodexTransportError(details={"message": "adapter shutdown"})
        self._fail_transport(error)
        self._cleanup_done.wait(timeout=4.0)
