"""Durable single-consumer dispatch of authoritative terminal turn callbacks."""
import hashlib
import threading
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .callback_store import (CallbackEvent, CallbackOutboxEntry, CallbackStore)
from .commands import (CallbackState, CompletionResponse, FacadeFault,
                       FacadeFaultCode, RecoveryView, WorkerView)
from .models import TurnSnapshot


SCHEMA = "codex-worker.claude-callback/v1"
_TERMINAL_STATUSES = frozenset(("completed", "failed", "interrupted"))


def _terminal_event_id(session_id: str, turn_id: str, event_kind: str) -> str:
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
    event_id = _terminal_event_id(completion.worker.session_id,
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


class TerminalCallbackDispatcher:
    """Own the only automatic callback consumer in a daemon process."""

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
        self._started = False
        self._stopping = False
        self._thread = None  # type: Optional[threading.Thread]

    def start(self) -> None:
        # Validate/load recovery state synchronously so malformed durable state
        # refuses daemon startup instead of killing a background thread silently.
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
            self._condition.notify_all()

    def observe_turn(self, session_id: str, turn_id: str,
                     context: TerminalProjectionContext) -> None:
        key = (session_id, turn_id)
        with self._condition:
            existing = self._contexts.get(key)
            if existing is not None and existing != context:
                raise ValueError("terminal projection context is immutable")
            self._contexts[key] = context
        snapshot = self.runtime.terminal_snapshot(session_id, turn_id)
        if snapshot is not None:
            self.queue(context, snapshot)

    def queue(self, context: TerminalProjectionContext,
              snapshot: TurnSnapshot) -> Optional[CallbackOutboxEntry]:
        if snapshot.status not in _TERMINAL_STATUSES:
            return None
        binding = self.store.binding(context.worker.session_id)
        if binding is None or binding.state != CallbackState.ENABLED:
            return None
        duration = max(0.0, self.monotonic() - context.started_at)
        completion = self.projector.project_completion(
            context.worker, snapshot, context.output_schema, duration, context.recovery)
        emitted_at = self.now()
        event = build_terminal_event(completion, emitted_at)
        try:
            self.transport.encode_user_line(binding, event)
        except FacadeFault as exc:
            if exc.code != FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE:
                raise
            reference_id = _terminal_event_id(context.worker.session_id,
                                              snapshot.turn_id,
                                              "turn_terminal_reference")
            artifact = self.store.publish_artifact(reference_id, completion)
            event = build_terminal_event(
                completion, emitted_at, "turn_terminal_reference",
                {"path": artifact.path, "sha256": artifact.sha256,
                 "size_bytes": artifact.size_bytes})
            # The bounded reference must itself fit before it enters the outbox.
            self.transport.encode_user_line(binding, event)
        entry = self.store.enqueue_terminal(context.worker.session_id, event)
        if entry is not None:
            with self._condition:
                self._condition.notify_all()
        return entry

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
        with self._condition:
            context = self._contexts.get((session_id, snapshot.turn_id))
        if context is None:
            return
        try:
            self.queue(context, snapshot)
        except Exception:
            # Runtime terminal truth is authoritative even if callback persistence fails.
            return

    def _run(self) -> None:
        while True:
            with self._condition:
                if self._stopping:
                    return
            entries = self.store.pending()
            if not entries:
                with self._condition:
                    if self._stopping:
                        return
                    self._condition.wait()
                continue
            for entry in entries:
                with self._condition:
                    if self._stopping:
                        return
                self._attempt(entry)
            with self._condition:
                if self._stopping:
                    return
                self._condition.wait(self.retry_backoff)

    def _attempt(self, entry: CallbackOutboxEntry) -> None:
        if entry.event is None:
            return
        binding = self.store.binding(entry.session_id)
        attempted_at = self.now()
        try:
            attempt = self.transport.send(binding, entry.event, None)
        except FacadeFault as exc:
            self.store.record_failed(entry.event_id, exc.kind, attempted_at)
        except Exception as exc:
            self.store.record_failed(entry.event_id, type(exc).__name__, attempted_at)
        else:
            self.store.record_written(entry.event_id,
                                      attempt.attempted_at or attempted_at)
