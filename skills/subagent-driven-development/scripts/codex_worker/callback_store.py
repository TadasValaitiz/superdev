"""Owner-only durable callback bindings, terminal outbox, and result artifacts."""
import hashlib
import json
import os
import stat
import tempfile
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .commands import (CallbackAttemptState, CallbackAttemptView, CallbackState,
                       CallbackStatusView, CompletionResponse, WorkerView)


class CallbackOutboxState(str, Enum):
    PENDING = "pending"
    WRITTEN = "written"


class UnsafeCallbackStoreError(RuntimeError):
    pass


def _nonempty(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("%s must be a non-empty string" % name)


@dataclass(frozen=True)
class CallbackBinding:
    session_id: str
    state: CallbackState
    target_socket: Optional[str] = field(repr=False)
    child_token: Optional[str] = field(repr=False)
    claude_session_id: Optional[str] = field(repr=False)
    claude_pid: Optional[int] = field(repr=False)
    claude_proc_start: Optional[str] = field(repr=False)
    claude_config_dir: Optional[str] = field(repr=False)
    captured_at: str
    last_terminal_attempt: Optional[CallbackAttemptView] = None

    def __post_init__(self) -> None:
        _nonempty(self.session_id, "session_id")
        _nonempty(self.captured_at, "captured_at")
        if not isinstance(self.state, CallbackState):
            raise ValueError("state must be a CallbackState")
        route = (self.target_socket, self.child_token, self.claude_session_id,
                 self.claude_pid, self.claude_proc_start)
        if self.state == CallbackState.ENABLED:
            if any(item is None for item in route) or self.claude_config_dir is None:
                raise ValueError("enabled callback binding requires a complete capture")
        elif any(item is not None for item in route):
            raise ValueError("non-enabled callback binding cannot retain a route")
        elif self.state == CallbackState.DISABLED and self.claude_config_dir is not None:
            raise ValueError("disabled callback binding cannot retain a resolver root")
        if self.claude_config_dir is not None and (not isinstance(self.claude_config_dir, str)
                                                   or not Path(self.claude_config_dir).is_absolute()):
            raise ValueError("claude_config_dir must be absolute when present")
        if self.target_socket is not None and not Path(self.target_socket).is_absolute():
            raise ValueError("target_socket must be absolute")
        if self.child_token is not None and (len(self.child_token) != 32
                                             or any(char not in "0123456789abcdef" for char in self.child_token)):
            raise ValueError("child_token must be lowercase hexadecimal")
        if self.claude_pid is not None and (type(self.claude_pid) is not int or self.claude_pid <= 0):
            raise ValueError("claude_pid must be positive")


@dataclass(frozen=True)
class CallbackEvent:
    schema: str
    event: str
    event_id: str
    emitted_at: str
    priority: str
    worker: WorkerView
    payload: Dict[str, Any]

    def __post_init__(self) -> None:
        if self.schema != "codex-worker.claude-callback/v1":
            raise ValueError("unsupported callback schema")
        if self.event not in {"turn_terminal", "turn_terminal_reference", "worker_message"}:
            raise ValueError("unsupported callback event")
        _nonempty(self.event_id, "event_id"); _nonempty(self.emitted_at, "emitted_at")
        if self.priority not in {"now", "next", "later"}:
            raise ValueError("unsupported callback priority")
        if not isinstance(self.worker, WorkerView) or not isinstance(self.payload, dict):
            raise ValueError("invalid callback event")
        try:
            json.dumps(self.payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must be JSON-compatible") from exc


@dataclass(frozen=True)
class CallbackOutboxEntry:
    event_id: str
    session_id: str
    event: Optional[CallbackEvent]
    state: CallbackOutboxState
    attempt_count: int
    last_error: Optional[str]

    def __post_init__(self) -> None:
        _nonempty(self.event_id, "event_id"); _nonempty(self.session_id, "session_id")
        if not isinstance(self.state, CallbackOutboxState) or type(self.attempt_count) is not int or self.attempt_count < 0:
            raise ValueError("invalid callback outbox entry")
        if self.last_error is not None and not isinstance(self.last_error, str):
            raise ValueError("last_error must be a string")
        if self.state == CallbackOutboxState.PENDING and self.event is None:
            raise ValueError("pending callback entry requires its event")
        if self.event is not None and (self.event.event_id != self.event_id or self.event.worker.session_id != self.session_id):
            raise ValueError("callback event identity does not match outbox entry")


@dataclass(frozen=True)
class CallbackArtifact:
    event_id: str
    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        _nonempty(self.event_id, "event_id")
        if not Path(self.path).is_absolute() or len(self.sha256) != 64 or type(self.size_bytes) is not int or self.size_bytes < 0:
            raise ValueError("invalid callback artifact")


@dataclass(frozen=True)
class CallbackStoreDeps:
    lstat: Callable[[Path], os.stat_result] = os.lstat
    getuid: Callable[[], int] = os.getuid
    fsync: Callable[[int], None] = os.fsync
    replace: Callable[[str, Path], None] = os.replace


class CallbackStore:
    """A single-process serialized store; every mutation is atomically persisted."""
    def __init__(self, path: Path, artifact_dir: Path, deps: Optional[CallbackStoreDeps] = None):
        self.path = Path(path)
        self.artifact_dir = Path(artifact_dir)
        self.deps = deps or CallbackStoreDeps()
        self._lock = threading.RLock()

    def bind(self, binding: CallbackBinding) -> CallbackBinding:
        with self._lock:
            state = self._load()
            existing = self._binding_from_dict(state["bindings"].get(binding.session_id))
            if existing is not None and existing != binding:
                raise ValueError("callback binding is immutable")
            if existing is None:
                state["bindings"][binding.session_id] = self._binding_dict(binding)
                self._write(state)
            return binding

    def binding(self, session_id: str) -> Optional[CallbackBinding]:
        with self._lock:
            return self._binding_from_dict(self._load()["bindings"].get(session_id))

    def enqueue_terminal(self, session_id: str, event: CallbackEvent) -> Optional[CallbackOutboxEntry]:
        with self._lock:
            state = self._load()
            if session_id not in state["bindings"]:
                raise ValueError("callback binding not found")
            raw = state["outbox"].get(event.event_id)
            if raw is not None:
                entry = self._entry_from_dict(raw)
                if entry.session_id != session_id:
                    raise ValueError("callback event id belongs to another session")
                return entry if entry.state == CallbackOutboxState.PENDING else None
            entry = CallbackOutboxEntry(event.event_id, session_id, event, CallbackOutboxState.PENDING, 0, None)
            state["outbox"][event.event_id] = self._entry_dict(entry)
            self._write(state)
            return entry

    def pending(self, session_id: Optional[str] = None) -> List[CallbackOutboxEntry]:
        with self._lock:
            entries = [self._entry_from_dict(value) for value in self._load()["outbox"].values()]
            return [entry for entry in entries if entry.state == CallbackOutboxState.PENDING
                    and (session_id is None or entry.session_id == session_id)]

    def record_failed(self, event_id: str, error: str, attempted_at: str) -> CallbackOutboxEntry:
        _nonempty(error, "error"); _nonempty(attempted_at, "attempted_at")
        with self._lock:
            state = self._load(); entry = self._entry_from_dict(state["outbox"].get(event_id))
            if entry.state != CallbackOutboxState.PENDING:
                return entry
            entry = CallbackOutboxEntry(entry.event_id, entry.session_id, entry.event,
                                        entry.state, entry.attempt_count + 1, error)
            state["outbox"][event_id] = self._entry_dict(entry)
            self._set_attempt(state, entry.session_id, CallbackAttemptView(event_id, CallbackAttemptState.FAILED,
                              error, attempted_at, entry.attempt_count))
            self._write(state); return entry

    def record_written(self, event_id: str, attempted_at: str) -> CallbackOutboxEntry:
        _nonempty(attempted_at, "attempted_at")
        with self._lock:
            state = self._load(); entry = self._entry_from_dict(state["outbox"].get(event_id))
            if entry.state == CallbackOutboxState.WRITTEN:
                return entry
            entry = CallbackOutboxEntry(entry.event_id, entry.session_id, None,
                                        CallbackOutboxState.WRITTEN, entry.attempt_count + 1, None)
            state["outbox"][event_id] = self._entry_dict(entry)
            self._set_attempt(state, entry.session_id, CallbackAttemptView(event_id, CallbackAttemptState.WRITTEN,
                              None, attempted_at, entry.attempt_count))
            self._write(state); return entry

    def status_view(self, session_id: str) -> CallbackStatusView:
        with self._lock:
            state = self._load(); binding = self._binding_from_dict(state["bindings"].get(session_id))
            if binding is None:
                raise ValueError("callback binding not found")
            count = sum(1 for raw in state["outbox"].values()
                        if self._entry_from_dict(raw).session_id == session_id
                        and self._entry_from_dict(raw).state == CallbackOutboxState.PENDING)
            return CallbackStatusView(binding.state, count, binding.last_terminal_attempt)

    def publish_artifact(self, event_id: str, completion: CompletionResponse) -> CallbackArtifact:
        _safe_artifact_id(event_id)
        payload = json.dumps(completion.to_dict(), sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8") + b"\n"
        digest = hashlib.sha256(payload).hexdigest(); target = self.artifact_dir / (event_id + ".json")
        with self._lock:
            self._ensure_layout()
            if target.exists() or target.is_symlink():
                self._verify_artifact(target, digest, len(payload))
                return CallbackArtifact(event_id, str(target), digest, len(payload))
            fd, temporary = tempfile.mkstemp(prefix="artifact.", dir=str(self.artifact_dir))
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload); handle.flush(); self.deps.fsync(handle.fileno())
                try:
                    self.deps.replace(temporary, target)
                except FileExistsError:
                    pass
                self._verify_artifact(target, digest, len(payload))
                self._fsync_parent(self.artifact_dir)
            finally:
                try: os.unlink(temporary)
                except FileNotFoundError: pass
            return CallbackArtifact(event_id, str(target), digest, len(payload))

    def _load(self) -> Dict[str, Any]:
        self._ensure_layout()
        try: raw = self.path.read_bytes()
        except OSError as exc: raise UnsafeCallbackStoreError("callback store is unreadable") from exc
        if not raw:
            state = self._empty(); self._write(state); return state
        try: state = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise ValueError("malformed callback state") from exc
        if not isinstance(state, dict) or set(state) != {"version", "bindings", "outbox"} or state["version"] != 1 or not isinstance(state["bindings"], dict) or not isinstance(state["outbox"], dict):
            raise ValueError("malformed callback state")
        # Validate every record before it can affect a later write.
        for session_id, value in state["bindings"].items():
            binding = self._binding_from_dict(value)
            if binding is None or binding.session_id != session_id:
                raise ValueError("callback binding key does not match its record")
        for event_id, value in state["outbox"].items():
            entry = self._entry_from_dict(value)
            if entry.event_id != event_id:
                raise ValueError("callback outbox key does not match its record")
        return state

    @staticmethod
    def _empty() -> Dict[str, Any]: return {"version": 1, "bindings": {}, "outbox": {}}

    def _ensure_layout(self) -> None:
        self._mkdir(self.path.parent); self._mkdir(self.artifact_dir)
        if self.path.exists() or self.path.is_symlink(): self._owner_regular(self.path, 0o600)
        else:
            fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600); os.close(fd)
            self._owner_regular(self.path, 0o600)

    def _mkdir(self, path: Path) -> None:
        if path.exists() or path.is_symlink():
            self._owner_directory(path); return
        parent = path.parent
        if not parent.exists(): self._mkdir(parent)
        os.mkdir(str(path), 0o700)
        self._owner_directory(path)

    def _owner_regular(self, path: Path, mode: int) -> None:
        try: data = self.deps.lstat(path)
        except OSError as exc: raise UnsafeCallbackStoreError("unsafe callback file: %s" % path) from exc
        if not stat.S_ISREG(data.st_mode) or data.st_uid != self.deps.getuid() or stat.S_IMODE(data.st_mode) != mode:
            raise UnsafeCallbackStoreError("unsafe callback file: %s" % path)

    def _owner_directory(self, path: Path) -> None:
        try: data = self.deps.lstat(path)
        except OSError as exc: raise UnsafeCallbackStoreError("unsafe callback directory: %s" % path) from exc
        if not stat.S_ISDIR(data.st_mode) or data.st_uid != self.deps.getuid() or stat.S_IMODE(data.st_mode) != 0o700:
            raise UnsafeCallbackStoreError("unsafe callback directory: %s" % path)

    def _write(self, state: Dict[str, Any]) -> None:
        self._ensure_layout()
        fd, temporary = tempfile.mkstemp(prefix="callbacks.", dir=str(self.path.parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
                handle.flush(); self.deps.fsync(handle.fileno())
            self.deps.replace(temporary, self.path)
            self._owner_regular(self.path, 0o600); self._fsync_parent(self.path.parent)
        finally:
            try: os.unlink(temporary)
            except FileNotFoundError: pass

    def _fsync_parent(self, parent: Path) -> None:
        descriptor = os.open(str(parent), os.O_RDONLY)
        try: self.deps.fsync(descriptor)
        finally: os.close(descriptor)

    def _verify_artifact(self, path: Path, digest: str, size: int) -> None:
        self._owner_regular(path, 0o600)
        data = path.read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("callback artifact collision or tampering")

    def _set_attempt(self, state: Dict[str, Any], session_id: str, attempt: CallbackAttemptView) -> None:
        binding = self._binding_from_dict(state["bindings"][session_id])
        state["bindings"][session_id] = self._binding_dict(CallbackBinding(
            binding.session_id, binding.state, binding.target_socket, binding.child_token,
            binding.claude_session_id, binding.claude_pid, binding.claude_proc_start,
            binding.claude_config_dir, binding.captured_at, attempt))

    @staticmethod
    def _binding_dict(value: CallbackBinding) -> Dict[str, Any]:
        return {"session_id": value.session_id, "state": value.state.value, "target_socket": value.target_socket,
                "child_token": value.child_token, "claude_session_id": value.claude_session_id,
                "claude_pid": value.claude_pid, "claude_proc_start": value.claude_proc_start,
                "claude_config_dir": value.claude_config_dir, "captured_at": value.captured_at,
                "last_terminal_attempt": None if value.last_terminal_attempt is None else value.last_terminal_attempt.to_dict()}

    @staticmethod
    def _binding_from_dict(value: Optional[Dict[str, Any]]) -> Optional[CallbackBinding]:
        if value is None: return None
        required = {"session_id", "state", "target_socket", "child_token", "claude_session_id", "claude_pid", "claude_proc_start", "claude_config_dir", "captured_at", "last_terminal_attempt"}
        if not isinstance(value, dict) or set(value) != required: raise ValueError("malformed callback binding")
        attempt = None if value["last_terminal_attempt"] is None else CallbackAttemptView.from_dict(value["last_terminal_attempt"])
        return CallbackBinding(value["session_id"], CallbackState(value["state"]), value["target_socket"], value["child_token"], value["claude_session_id"], value["claude_pid"], value["claude_proc_start"], value["claude_config_dir"], value["captured_at"], attempt)

    @staticmethod
    def _event_dict(value: CallbackEvent) -> Dict[str, Any]:
        return {"schema": value.schema, "event": value.event, "event_id": value.event_id,
                "emitted_at": value.emitted_at, "priority": value.priority,
                "worker": value.worker.to_dict(), "payload": value.payload}

    @staticmethod
    def _event_from_dict(value: Dict[str, Any]) -> CallbackEvent:
        if not isinstance(value, dict) or set(value) != {"schema", "event", "event_id", "emitted_at", "priority", "worker", "payload"}: raise ValueError("malformed callback event")
        return CallbackEvent(value["schema"], value["event"], value["event_id"], value["emitted_at"], value["priority"], WorkerView.from_dict(value["worker"]), value["payload"])

    @classmethod
    def _entry_dict(cls, value: CallbackOutboxEntry) -> Dict[str, Any]:
        return {"event_id": value.event_id, "session_id": value.session_id,
                "event": None if value.event is None else cls._event_dict(value.event),
                "state": value.state.value, "attempt_count": value.attempt_count, "last_error": value.last_error}

    @classmethod
    def _entry_from_dict(cls, value: Optional[Dict[str, Any]]) -> CallbackOutboxEntry:
        if not isinstance(value, dict) or set(value) != {"event_id", "session_id", "event", "state", "attempt_count", "last_error"}: raise ValueError("malformed callback outbox entry")
        return CallbackOutboxEntry(value["event_id"], value["session_id"], None if value["event"] is None else cls._event_from_dict(value["event"]), CallbackOutboxState(value["state"]), value["attempt_count"], value["last_error"])


def _safe_artifact_id(value: str) -> None:
    _nonempty(value, "event_id")
    if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in value):
        raise ValueError("event_id is unsafe for an artifact path")
