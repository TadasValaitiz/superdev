"""Durable single-consumer dispatch of authoritative terminal turn callbacks."""
import copy
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .callback_domain import CallbackEvent
from .callback_store import CallbackOutboxEntry, CallbackStore
from .commands import (CallbackState, CompletionResponse, FacadeFault,
                       FacadeFaultCode, RecoveryView, WorkerView)
from .models import TurnSnapshot, copy_turn_snapshot


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
               else {"artifact": artifact, "turn_id": completion.turn.turn_id})
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


class TerminalCallbackDispatcher:
    """Own terminal projection, durable queueing, and the only automatic sender."""

    def __init__(self, store: CallbackStore, transport, runtime, projector,
                 monotonic: Callable[[], float], now: Callable[[], str],
                 retry_backoff: float = 0.25,
                 diagnostic: Optional[Callable[[dict], None]] = None):
        if retry_backoff < 0:
            raise ValueError("retry_backoff must be non-negative")
        self.store = store
        self.transport = transport
        self.runtime = runtime
        self.projector = projector
        self.monotonic = monotonic
        self.now = now
        self.retry_backoff = retry_backoff
        self.diagnostic = diagnostic
        self._condition = threading.Condition()
        self._contexts = {}  # type: Dict[Tuple[str, str], TerminalProjectionContext]
        self._snapshots = {}  # type: Dict[Tuple[str, str], TurnSnapshot]
        self._completions = {}  # type: Dict[Tuple[str, str], CompletionResponse]
        self._projection_errors = {}  # type: Dict[Tuple[str, str], BaseException]
        self._projection_owners = set()
        self._persistence_owners = set()
        self._processing = set()
        self._callback_done = set()
        self._callback_abandoned = set()
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
            context = self._contexts[key]
            isolated = self._snapshots[key]
        try:
            completion = self._project_once(key, context, isolated)
        except BaseException as exc:
            event_id = terminal_event_id(session_id, turn_id, "turn_terminal")
            self._durable_fault_once(key, session_id, event_id, type(exc).__name__)
            with self._condition:
                self._client_done.add(key)
                self._cleanup(key)
            raise
        with self._condition:
            worker_available = self._worker_available()
            shutdown_worker = (self._stopping and self._thread is not None
                               and self._thread.is_alive())
            self._client_done.add(key)
            self._cleanup(key)
        if worker_available or shutdown_worker:
            return CompletionResponse.from_dict(completion.to_dict())
        self._persist_fallback_once(key, context, completion)
        with self._condition:
            self._cleanup(key)
        return CompletionResponse.from_dict(completion.to_dict())

    def abandon_completion(self, session_id: str, turn_id: str) -> None:
        key = (session_id, turn_id)
        with self._condition:
            self._client_done.add(key)
            self._cleanup(key)

    def tracked_turn_count(self) -> int:
        with self._condition:
            return len(set(self._contexts) | set(self._snapshots) | set(self._completions)
                       | set(self._projection_errors) | set(self._projection_owners)
                       | set(self._persistence_owners)
                       | set(self._callback_abandoned)
                       | set(self._processing))

    def shutdown(self, timeout: float = 6.0) -> None:
        deadline = time.monotonic() + max(0.0, timeout)
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join(max(0.0, deadline - time.monotonic()))
        if thread is None or not thread.is_alive():
            self._drain_ready(deadline)
        with self._condition:
            if thread is None or not thread.is_alive():
                self._started = False

    def _on_terminal(self, session_id: str, snapshot: TurnSnapshot) -> None:
        key = (session_id, snapshot.turn_id)
        with self._condition:
            if key not in self._contexts:
                return
            abandoned = key in self._client_done
        self._handoff(session_id, snapshot)
        if abandoned:
            self.runtime.release_terminal_snapshot(session_id, snapshot.turn_id)

    def _handoff(self, session_id: str, snapshot: TurnSnapshot) -> None:
        if snapshot.status not in _TERMINAL_STATUSES:
            return
        key = (session_id, snapshot.turn_id)
        isolated = copy_turn_snapshot(snapshot)
        with self._condition:
            existing = self._snapshots.get(key)
            if existing is None:
                self._snapshots[key] = isolated
            self._condition.notify_all()

    def _ready_key(self) -> Optional[Tuple[str, str]]:
        return next((key for key in self._snapshots
                     if key in self._contexts and key not in self._processing
                     and key not in self._callback_done
                     and key not in self._callback_abandoned), None)

    def _run(self) -> None:
        while True:
            with self._condition:
                key = self._ready_key()
                if key is not None:
                    self._processing.add(key)
                    context = self._contexts[key]
                    snapshot = self._snapshots[key]
                else:
                    context = None
                    snapshot = None
                    if self._stopping:
                        return
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
        try:
            completion = self._project_once(key, context, snapshot)
        except BaseException as exc:
            self._durable_fault_once(key, key[0], event_id, type(exc).__name__)
            with self._condition:
                self._processing.discard(key)
                self._cleanup(key)
                self._condition.notify_all()
            return
        callback_done = self._persist_once(key, context, completion)
        if not callback_done:
            with self._condition:
                self._processing.discard(key)
                if not self._stopping:
                    self._condition.wait(self.retry_backoff)
            return
        with self._condition:
            self._processing.discard(key)
            self._cleanup(key)
            self._condition.notify_all()

    def _persist_once(self, key, context, completion) -> bool:
        with self._condition:
            while True:
                if key in self._callback_done:
                    return True
                if key in self._callback_abandoned:
                    return True
                if key not in self._persistence_owners:
                    self._persistence_owners.add(key)
                    break
                self._condition.wait()
        try:
            self._persist_completion(context, completion)
        except BaseException as exc:
            reason = exc.kind if isinstance(exc, FacadeFault) else type(exc).__name__
            event_id = terminal_event_id(key[0], key[1], "turn_terminal")
            recorded, fault_error = self._record_fault_once(key[0], event_id, reason, key[1])
            lost = False
            with self._condition:
                self._persistence_owners.discard(key)
                if recorded and self._stopping:
                    self._callback_done.add(key)
                    self._cleanup(key)
                elif self._stopping:
                    self._callback_abandoned.add(key)
                    lost = True
                    self._cleanup(key)
                self._condition.notify_all()
            if lost:
                self._emit_persistence_loss(
                    key[0], event_id, type(exc).__name__, fault_error)
            return self._stopping
        with self._condition:
            self._persistence_owners.discard(key)
            self._callback_done.add(key)
            self._cleanup(key)
            self._condition.notify_all()
            return True

    def _persist_fallback_once(self, key, context, completion) -> None:
        with self._condition:
            if key in self._callback_done or key in self._callback_abandoned:
                return
            if key in self._persistence_owners:
                return
            self._persistence_owners.add(key)
        event_id = terminal_event_id(key[0], key[1], "turn_terminal")
        try:
            self._persist_completion(context, completion)
        except BaseException as exc:
            reason = exc.kind if isinstance(exc, FacadeFault) else type(exc).__name__
            recorded, fault_error = self._record_fault_once(key[0], event_id, reason, key[1])
            with self._condition:
                self._persistence_owners.discard(key)
                if recorded:
                    self._callback_done.add(key)
                else:
                    self._callback_abandoned.add(key)
                self._cleanup(key)
                self._condition.notify_all()
            if not recorded:
                self._emit_persistence_loss(
                    key[0], event_id, type(exc).__name__, fault_error)
            return
        with self._condition:
            self._persistence_owners.discard(key)
            self._callback_done.add(key)
            self._cleanup(key)
            self._condition.notify_all()

    def _durable_fault_once(self, key, session_id, event_id, reason) -> bool:
        with self._condition:
            while True:
                if key in self._callback_done:
                    return True
                if key not in self._persistence_owners:
                    self._persistence_owners.add(key)
                    break
                self._condition.wait()
        recorded, fault_error = self._record_fault_once(session_id, event_id, reason, key[1])
        lost = False
        with self._condition:
            self._persistence_owners.discard(key)
            if recorded:
                self._callback_done.add(key)
                self._cleanup(key)
            elif self._stopping:
                self._callback_abandoned.add(key)
                lost = True
                self._cleanup(key)
            self._condition.notify_all()
        if lost:
            self._emit_persistence_loss(
                session_id, event_id, reason, fault_error)
        return recorded

    def _drain_ready(self, deadline: float) -> None:
        while time.monotonic() < deadline:
            with self._condition:
                key = self._ready_key()
                if key is None:
                    return
                self._processing.add(key)
                context = self._contexts[key]
                snapshot = self._snapshots[key]
            self._process_terminal(key, context, snapshot)

    def _project_once(self, key, context, snapshot) -> CompletionResponse:
        with self._condition:
            while True:
                completion = self._completions.get(key)
                if completion is not None:
                    return CompletionResponse.from_dict(completion.to_dict())
                error = self._projection_errors.get(key)
                if error is not None:
                    raise error
                if key not in self._projection_owners:
                    self._projection_owners.add(key)
                    break
                self._condition.wait()
        try:
            duration = max(0.0, self.monotonic() - context.started_at)
            projected = self.projector.project_completion(
                context.worker, snapshot, context.output_schema, duration, context.recovery)
            completion = CompletionResponse.from_dict(projected.to_dict())
        except BaseException as exc:
            with self._condition:
                self._projection_owners.discard(key)
                self._projection_errors[key] = exc
                self._condition.notify_all()
            raise
        with self._condition:
            self._projection_owners.discard(key)
            self._completions[key] = completion
            self._condition.notify_all()
            return CompletionResponse.from_dict(completion.to_dict())

    def _worker_available(self) -> bool:
        return (self._started and not self._stopping and self._thread is not None
                and self._thread.is_alive())

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

    def _record_fault_once(self, session_id: str, event_id: str,
                           reason: str, turn_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        try:
            self.store.record_terminal_fault(session_id, event_id, reason, self.now(), turn_id)
            return True, None
        except BaseException as exc:
            return False, type(exc).__name__

    def _emit_persistence_loss(self, session_id: str, event_id: str,
                               enqueue_error: str,
                               fault_error: Optional[str]) -> None:
        evidence = {
            "kind": "terminal_callback_persistence_lost",
            "session_id": session_id,
            "event_id": event_id,
            "enqueue_error": enqueue_error,
            "fault_error": fault_error,
        }
        try:
            if self.diagnostic is not None:
                self.diagnostic(evidence)
            else:
                logging.getLogger(__name__).error("%s", evidence)
        except BaseException:
            pass

    def _cleanup(self, key) -> None:
        if ((key not in self._callback_done and key not in self._callback_abandoned)
                or key not in self._client_done
                or key in self._processing):
            return
        self._contexts.pop(key, None)
        self._snapshots.pop(key, None)
        self._completions.pop(key, None)
        self._projection_errors.pop(key, None)
        self._projection_owners.discard(key)
        self._persistence_owners.discard(key)
        self._processing.discard(key)
        self._callback_done.discard(key)
        self._callback_abandoned.discard(key)
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
