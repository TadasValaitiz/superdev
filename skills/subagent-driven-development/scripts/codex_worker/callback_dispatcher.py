"""Durable single-consumer dispatch of authoritative terminal turn callbacks."""
import copy
import hashlib
import threading
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .callback_store import CallbackEvent, CallbackOutboxEntry, CallbackStore
from .commands import (CallbackState, CompletionResponse, FacadeFault,
                       FacadeFaultCode, RecoveryView, WorkerView)
from .models import ErrorDetail, ItemRecord, TurnSnapshot


SCHEMA = "codex-worker.claude-callback/v1"
_TERMINAL_STATUSES = frozenset(("completed", "failed", "interrupted"))


def terminal_event_id(session_id: str, turn_id: str, event_kind: str) -> str:
    identity = (session_id + "\0" + turn_id + "\0" + event_kind).encode("utf-8")
    return "terminal-" + hashlib.sha256(identity).hexdigest()


def build_terminal_event(completion: CompletionResponse, emitted_at: str,
                         event_kind: str = "turn_terminal",
                         artifact: Optional[dict] = None) -> CallbackEvent:
    if completion.turn.status not in _TERMINAL_STATUSES:
        raise ValueError("callback requires a terminal completion")
    if event_kind not in ("turn_terminal", "turn_terminal_reference"):
        raise ValueError("unsupported terminal callback kind")
    if event_kind == "turn_terminal_reference" and not isinstance(artifact, dict):
        raise ValueError("terminal reference requires an artifact descriptor")
    event_id = terminal_event_id(completion.worker.session_id,
                                 completion.turn.turn_id, event_kind)
    payload = ({"completion": completion.to_dict()} if event_kind == "turn_terminal"
               else {"artifact": artifact})
    return CallbackEvent(SCHEMA, event_kind, event_id, emitted_at, "next",
                         completion.worker, payload)


@dataclass(frozen=True)
class TerminalProjectionContext:
    worker: WorkerView
    output_schema: Optional[dict]
    started_at: float
    recovery: RecoveryView

    def isolated(self) -> "TerminalProjectionContext":
        return TerminalProjectionContext(
            WorkerView.from_dict(self.worker.to_dict()), copy.deepcopy(self.output_schema),
            self.started_at, RecoveryView.from_dict(self.recovery.to_dict()))


def _copy_snapshot(snapshot: TurnSnapshot) -> TurnSnapshot:
    error = (None if snapshot.error is None
             else ErrorDetail.from_dict(copy.deepcopy(snapshot.error.to_dict())))
    return TurnSnapshot(snapshot.turn_id, snapshot.status, error,
                        [ItemRecord.from_dict(copy.deepcopy(item.to_dict()))
                         for item in snapshot.items])


class TerminalCallbackDispatcher:
    """Own terminal projection, durable queueing, and the only automatic sender."""

    def __init__(self, store: CallbackStore, transport, runtime, projector,
                 monotonic: Callable[[], float], now: Callable[[], str],
                 retry_backoff: float = 0.25):
        if retry_backoff < 0:
            raise ValueError("retry_backoff must be non-negative")
        self.store = store
        self.transport = transport
        self.runtime = runtime
        self.projector = projector
        self.monotonic = monotonic
        self.now = now
        self.retry_backoff = retry_backoff
        self._condition = threading.Condition()
        self._contexts = {}  # type: Dict[Tuple[str, str], TerminalProjectionContext]
        self._snapshots = {}  # type: Dict[Tuple[str, str], TurnSnapshot]
        self._completions = {}  # type: Dict[Tuple[str, str], CompletionResponse]
        self._projection_errors = {}  # type: Dict[Tuple[str, str], BaseException]
        self._processing = set()
        self._callback_done = set()
        self._client_done = set()
        self._started = False
        self._stopping = False
        self._thread = None  # type: Optional[threading.Thread]

    def start(self) -> None:
        self.store.pending()
        with self._condition:
            if self._started:
                return
            self._started = True
            self._stopping = False
            self.runtime.add_terminal_observer(self._on_terminal)
            self._thread = threading.Thread(target=self._run,
                                            name="codex-worker-terminal-callback",
                                            daemon=True)
            self._thread.start()

    def observe_turn(self, session_id: str, turn_id: str,
                     context: TerminalProjectionContext) -> None:
        key = (session_id, turn_id)
        isolated = context.isolated()
        with self._condition:
            existing = self._contexts.get(key)
            if existing is not None and existing != isolated:
                raise ValueError("terminal projection context is immutable")
            self._contexts[key] = isolated
            self._condition.notify_all()
        snapshot = self.runtime.terminal_snapshot(session_id, turn_id)
        if snapshot is not None:
            self._handoff(session_id, snapshot)

    def queue(self, context: TerminalProjectionContext,
              snapshot: TurnSnapshot) -> Optional[CallbackOutboxEntry]:
        self.observe_turn(context.worker.session_id, snapshot.turn_id, context)
        self._handoff(context.worker.session_id, snapshot)
        return None

    def completion_for(self, session_id: str, turn_id: str,
                       snapshot: TurnSnapshot) -> CompletionResponse:
        key = (session_id, turn_id)
        self._handoff(session_id, snapshot)
        self.runtime.release_terminal_snapshot(session_id, turn_id)
        with self._condition:
            while key not in self._completions and key not in self._projection_errors:
                self._condition.wait()
            self._client_done.add(key)
            if key in self._projection_errors:
                error = self._projection_errors[key]
                self._cleanup(key)
                raise error
            completion = CompletionResponse.from_dict(self._completions[key].to_dict())
            self._cleanup(key)
            return completion

    def abandon_completion(self, session_id: str, turn_id: str) -> None:
        key = (session_id, turn_id)
        with self._condition:
            self._client_done.add(key)
            self._cleanup(key)

    def tracked_turn_count(self) -> int:
        with self._condition:
            return len(set(self._contexts) | set(self._snapshots) | set(self._completions)
                       | set(self._projection_errors) | set(self._processing))

    def shutdown(self, timeout: float = 6.0) -> None:
        with self._condition:
            if not self._started:
                return
            self._stopping = True
            self._condition.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join(max(0.0, timeout))
        with self._condition:
            if thread is None or not thread.is_alive():
                self._started = False

    def _on_terminal(self, session_id: str, snapshot: TurnSnapshot) -> None:
        self._handoff(session_id, snapshot)
        key = (session_id, snapshot.turn_id)
        with self._condition:
            abandoned = key in self._client_done
        if abandoned:
            self.runtime.release_terminal_snapshot(session_id, snapshot.turn_id)

    def _handoff(self, session_id: str, snapshot: TurnSnapshot) -> None:
        if snapshot.status not in _TERMINAL_STATUSES:
            return
        key = (session_id, snapshot.turn_id)
        isolated = _copy_snapshot(snapshot)
        with self._condition:
            existing = self._snapshots.get(key)
            if existing is None:
                self._snapshots[key] = isolated
            self._condition.notify_all()

    def _ready_key(self) -> Optional[Tuple[str, str]]:
        return next((key for key in self._snapshots
                     if key in self._contexts and key not in self._processing
                     and key not in self._callback_done), None)

    def _run(self) -> None:
        while True:
            with self._condition:
                if self._stopping:
                    return
                key = self._ready_key()
                if key is not None:
                    self._processing.add(key)
                    context = self._contexts[key]
                    snapshot = self._snapshots[key]
                else:
                    context = None
                    snapshot = None
            if key is not None:
                self._process_terminal(key, context, snapshot)
                continue
            try:
                entries = self.store.pending()
            except Exception:
                with self._condition:
                    if not self._stopping:
                        self._condition.wait(self.retry_backoff)
                continue
            if entries:
                for entry in entries:
                    with self._condition:
                        if self._stopping:
                            return
                    self._attempt(entry)
                with self._condition:
                    self._condition.wait(self.retry_backoff)
            else:
                with self._condition:
                    if not self._stopping:
                        self._condition.wait(self.retry_backoff)

    def _process_terminal(self, key, context, snapshot) -> None:
        event_id = terminal_event_id(key[0], key[1], "turn_terminal")
        with self._condition:
            completion = self._completions.get(key)
        if completion is None:
            try:
                duration = max(0.0, self.monotonic() - context.started_at)
                completion = self.projector.project_completion(
                    context.worker, snapshot, context.output_schema, duration, context.recovery)
            except Exception as exc:
                with self._condition:
                    self._projection_errors[key] = exc
                    self._condition.notify_all()
                self._record_fault_until_stopping(key[0], event_id, type(exc).__name__)
                self._mark_callback_done(key)
                return
            with self._condition:
                self._completions[key] = CompletionResponse.from_dict(completion.to_dict())
                self._condition.notify_all()
        try:
            self._persist_completion(context, completion)
        except Exception as exc:
            reason = exc.kind if isinstance(exc, FacadeFault) else type(exc).__name__
            self._record_fault_until_stopping(key[0], event_id, reason)
            # Retain the work and retry persistence after bounded backoff.
            with self._condition:
                self._processing.discard(key)
                self._condition.wait(self.retry_backoff)
            return
        self._mark_callback_done(key)

    def _persist_completion(self, context, completion) -> None:
        binding = self.store.binding(context.worker.session_id)
        if binding is None or binding.state != CallbackState.ENABLED:
            return
        emitted_at = self.now()
        event = build_terminal_event(completion, emitted_at)
        try:
            self.transport.encode_user_line(binding, event)
        except FacadeFault as exc:
            if exc.code != FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE:
                raise
            reference_id = terminal_event_id(context.worker.session_id,
                                             completion.turn.turn_id,
                                             "turn_terminal_reference")
            artifact = self.store.publish_artifact(reference_id, completion)
            event = build_terminal_event(
                completion, emitted_at, "turn_terminal_reference",
                {"path": artifact.path, "sha256": artifact.sha256,
                 "size_bytes": artifact.size_bytes})
            self.transport.encode_user_line(binding, event)
        entry = self.store.enqueue_terminal(context.worker.session_id, event)
        if entry is not None:
            with self._condition:
                self._condition.notify_all()

    def _record_fault_until_stopping(self, session_id: str, event_id: str,
                                     reason: str) -> None:
        while True:
            try:
                self.store.record_terminal_fault(session_id, event_id, reason, self.now())
                return
            except Exception:
                with self._condition:
                    if self._stopping:
                        return
                    self._condition.wait(self.retry_backoff)

    def _mark_callback_done(self, key) -> None:
        with self._condition:
            self._processing.discard(key)
            self._callback_done.add(key)
            self._cleanup(key)
            self._condition.notify_all()

    def _cleanup(self, key) -> None:
        if key not in self._callback_done or key not in self._client_done:
            return
        self._contexts.pop(key, None)
        self._snapshots.pop(key, None)
        self._completions.pop(key, None)
        self._projection_errors.pop(key, None)
        self._processing.discard(key)
        self._callback_done.discard(key)
        self._client_done.discard(key)

    def _attempt(self, entry: CallbackOutboxEntry) -> None:
        if entry.event is None:
            return
        binding = self.store.binding(entry.session_id)
        attempted_at = self.now()
        try:
            attempt = self.transport.send(binding, entry.event, None)
        except FacadeFault as exc:
            try:
                self.store.record_failed(entry.event_id, exc.kind, attempted_at)
            except Exception:
                return
        except Exception as exc:
            try:
                self.store.record_failed(entry.event_id, type(exc).__name__, attempted_at)
            except Exception:
                return
        else:
            try:
                self.store.record_written(entry.event_id,
                                          attempt.attempted_at or attempted_at)
            except Exception:
                return
