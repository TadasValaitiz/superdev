"""Notification-owned, condition-based observable state for Codex sessions."""
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

from .models import (
    ErrorDetail,
    EventPage,
    EventRecord,
    ItemRecord,
    JsonObject,
    RuntimeStatus,
    SessionRecord,
    TurnSnapshot,
)


class RuntimeStoreError(RuntimeError):
    pass


class UnknownSession(RuntimeStoreError):
    pass


class SessionDetached(RuntimeStoreError):
    pass


class TurnActive(RuntimeStoreError):
    pass


class NoTurn(RuntimeStoreError):
    pass


class WaitTimeout(RuntimeStoreError):
    def __init__(self, session_id: str, turn_id: Optional[str]):
        self.session_id = session_id
        self.turn_id = turn_id
        super().__init__("timed out waiting for session %s turn %s" % (session_id, turn_id or "pending"))


class CodexProtocolError(RuntimeStoreError):
    pass


@dataclass
class _SessionRuntime:
    record: SessionRecord
    condition: threading.Condition = field(default_factory=threading.Condition)
    attached: bool = True
    active_turn_id: Optional[str] = None
    start_pending: bool = False
    awaiting_start_response: bool = False
    observed_start_turn_id: Optional[str] = None
    latest_turn: Optional[TurnSnapshot] = None
    next_cursor: int = 1
    events: Deque[EventRecord] = field(default_factory=deque)
    items: Dict[str, List[ItemRecord]] = field(default_factory=dict)


class RuntimeStore:
    def __init__(self, event_limit: int):
        if type(event_limit) is not int or event_limit <= 0:
            raise ValueError("event_limit must be a positive integer")
        self._event_limit = event_limit
        self._lock = threading.RLock()
        self._sessions = {}  # type: Dict[str, _SessionRuntime]
        self._thread_sessions = {}  # type: Dict[str, str]

    def attach(self, record: SessionRecord) -> None:
        with self._lock:
            owner = self._thread_sessions.get(record.thread_id)
            if owner is not None and owner != record.session_id:
                raise CodexProtocolError("thread is already attached to another session")
            runtime = self._sessions.get(record.session_id)
            if runtime is None:
                runtime = _SessionRuntime(record=record)
                self._sessions[record.session_id] = runtime
                self._thread_sessions[record.thread_id] = record.session_id
            elif runtime.record.thread_id != record.thread_id:
                raise CodexProtocolError("session attachment changed thread identity")
        with runtime.condition:
            runtime.record = record
            runtime.attached = True
            runtime.condition.notify_all()

    def _get(self, session_id: str) -> _SessionRuntime:
        with self._lock:
            runtime = self._sessions.get(session_id)
        if runtime is None:
            raise UnknownSession("unknown runtime session: %s" % session_id)
        return runtime

    def _by_thread(self, thread_id: Optional[str]) -> Optional[_SessionRuntime]:
        if not isinstance(thread_id, str):
            return None
        with self._lock:
            session_id = self._thread_sessions.get(thread_id)
            return self._sessions.get(session_id) if session_id is not None else None

    def _append_event(self, runtime: _SessionRuntime, event: str,
                      turn_id: Optional[str] = None, item: Optional[ItemRecord] = None,
                      error: Optional[ErrorDetail] = None) -> EventRecord:
        record = EventRecord(
            runtime.next_cursor,
            event,
            runtime.record.session_id,
            runtime.record.thread_id,
            turn_id,
            item,
            error,
        )
        runtime.next_cursor += 1
        runtime.events.append(record)
        while len(runtime.events) > self._event_limit:
            runtime.events.popleft()
        return record

    def detach_all(self, reason: ErrorDetail) -> None:
        with self._lock:
            runtimes = list(self._sessions.values())
        for runtime in runtimes:
            with runtime.condition:
                runtime.attached = False
                lost_turn_id = runtime.active_turn_id
                runtime.active_turn_id = None
                runtime.start_pending = False
                runtime.awaiting_start_response = False
                runtime.observed_start_turn_id = None
                if lost_turn_id is not None:
                    items = list(runtime.items.pop(lost_turn_id, []))
                    runtime.latest_turn = TurnSnapshot(
                        lost_turn_id, "failed", reason, items
                    )
                runtime.items.clear()
                self._append_event(runtime, "transport_error", lost_turn_id, error=reason)
                runtime.condition.notify_all()

    @staticmethod
    def _thread_id(message: JsonObject) -> Optional[str]:
        params = message.get("params")
        if not isinstance(params, dict):
            return None
        thread_id = params.get("threadId")
        if isinstance(thread_id, str):
            return thread_id
        turn = params.get("turn")
        if isinstance(turn, dict) and isinstance(turn.get("threadId"), str):
            return turn["threadId"]
        return None

    @staticmethod
    def _turn_error(status: str, value: object) -> Optional[ErrorDetail]:
        if status != "failed" and value is None:
            return None
        details = dict(value) if isinstance(value, dict) else None
        return ErrorDetail("codex_turn_failed", details=details)

    def on_notification(self, message: JsonObject) -> None:
        if not isinstance(message, dict):
            return
        method = message.get("method")
        if method == "transport/error":
            params = message.get("params")
            params = params if isinstance(params, dict) else {}
            details = params.get("details")
            self.detach_all(ErrorDetail(
                "transport_error",
                details=dict(details) if isinstance(details, dict) else None,
            ))
            return
        if method not in ("turn/started", "turn/completed", "item/completed", "approval/declined"):
            return
        runtime = self._by_thread(self._thread_id(message))
        if runtime is None:
            return
        params = message.get("params")
        if not isinstance(params, dict):
            return
        with runtime.condition:
            if method == "turn/started":
                turn = params.get("turn")
                turn_id = turn.get("id") if isinstance(turn, dict) else None
                if not isinstance(turn_id, str):
                    return
                runtime.start_pending = False
                runtime.active_turn_id = turn_id
                retained = runtime.items.get(turn_id)
                runtime.items.clear()
                if retained:
                    runtime.items[turn_id] = retained
                if runtime.awaiting_start_response:
                    runtime.observed_start_turn_id = turn_id
                self._append_event(runtime, "turn_started", turn_id)
            elif method == "turn/completed":
                turn = params.get("turn")
                turn_id = turn.get("id") if isinstance(turn, dict) else None
                if not isinstance(turn_id, str):
                    return
                status = turn.get("status") if isinstance(turn.get("status"), str) else "unknown"
                error = self._turn_error(status, turn.get("error"))
                if runtime.awaiting_start_response:
                    # Terminal notification identity is the final authority.
                    runtime.observed_start_turn_id = turn_id
                runtime.start_pending = False
                runtime.active_turn_id = None
                items = list(runtime.items.pop(turn_id, []))
                runtime.items.clear()
                runtime.latest_turn = TurnSnapshot(
                    turn_id, status, error, items
                )
                self._append_event(runtime, "turn_completed", turn_id, error=error)
                runtime.condition.notify_all()
            elif method == "item/completed":
                item = params.get("item")
                turn_id = params.get("turnId")
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("type"), str):
                    return
                data = {key: value for key, value in item.items() if key not in ("id", "type")}
                item_record = ItemRecord(item["id"], item["type"], data)
                current_turn = (
                    isinstance(turn_id, str) and (
                        runtime.active_turn_id == turn_id or (
                            runtime.awaiting_start_response and
                            runtime.observed_start_turn_id == turn_id and
                            (runtime.latest_turn is None or runtime.latest_turn.turn_id != turn_id)
                        )
                    )
                )
                if current_turn:
                    runtime.items.setdefault(turn_id, []).append(item_record)
                self._append_event(
                    runtime, "item_completed", turn_id if isinstance(turn_id, str) else None, item_record
                )
            else:
                approval_method = params.get("approvalMethod")
                if not isinstance(approval_method, str):
                    approval_method = "unknown_approval"
                request_id = params.get("requestId")
                item_record = ItemRecord(
                    str(request_id) if request_id is not None else "unknown",
                    approval_method,
                    {"decision": "decline"},
                )
                turn_id = params.get("turnId") if isinstance(params.get("turnId"), str) else None
                self._append_event(runtime, "approval_declined", turn_id, item_record)

    def status(self, session_id: str) -> RuntimeStatus:
        runtime = self._get(session_id)
        with runtime.condition:
            return RuntimeStatus(runtime.attached, runtime.active_turn_id, runtime.latest_turn)

    def _require_attached(self, runtime: _SessionRuntime) -> None:
        if not runtime.attached:
            raise SessionDetached("session is detached: %s" % runtime.record.session_id)

    def reserve_start(self, session_id: str) -> None:
        runtime = self._get(session_id)
        with runtime.condition:
            self._require_attached(runtime)
            if runtime.start_pending or runtime.awaiting_start_response or runtime.active_turn_id is not None:
                raise TurnActive("session already has an active or pending turn")
            runtime.start_pending = True
            runtime.awaiting_start_response = True
            runtime.observed_start_turn_id = None

    def cancel_start(self, session_id: str) -> None:
        runtime = self._get(session_id)
        with runtime.condition:
            runtime.start_pending = False
            runtime.awaiting_start_response = False
            runtime.observed_start_turn_id = None
            runtime.condition.notify_all()

    def reconcile_start(self, session_id: str, returned_turn_id: str) -> None:
        runtime = self._get(session_id)
        if not isinstance(returned_turn_id, str) or not returned_turn_id:
            raise CodexProtocolError("turn/start response omitted its turn id")
        with runtime.condition:
            if not runtime.awaiting_start_response:
                raise CodexProtocolError("turn/start response has no reservation")
            observed = runtime.observed_start_turn_id
            runtime.awaiting_start_response = False
            runtime.start_pending = False
            runtime.observed_start_turn_id = None
            if observed is not None and observed != returned_turn_id:
                runtime.condition.notify_all()
                raise CodexProtocolError(
                    "turn/start response id %s mismatches notification id %s" %
                    (returned_turn_id, observed)
                )
            if observed is None:
                if runtime.active_turn_id is not None and runtime.active_turn_id != returned_turn_id:
                    runtime.condition.notify_all()
                    raise CodexProtocolError("turn/start response mismatches active turn")
                runtime.active_turn_id = returned_turn_id
            runtime.condition.notify_all()

    def require_idle(self, session_id: str) -> None:
        runtime = self._get(session_id)
        with runtime.condition:
            self._require_attached(runtime)
            if runtime.start_pending or runtime.awaiting_start_response or runtime.active_turn_id is not None:
                raise TurnActive("session has an active or pending turn")

    def wait(self, session_id: str, timeout: float) -> TurnSnapshot:
        runtime = self._get(session_id)
        if timeout < 0:
            raise ValueError("timeout must be non-negative")
        deadline = time.monotonic() + timeout
        with runtime.condition:
            while runtime.start_pending or runtime.active_turn_id is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WaitTimeout(session_id, runtime.active_turn_id)
                runtime.condition.wait(remaining)
            if runtime.latest_turn is None:
                raise NoTurn("session has no terminal turn: %s" % session_id)
            return runtime.latest_turn

    def events(self, session_id: str, after: int, limit: int) -> EventPage:
        if type(after) is not int or after < 0:
            raise ValueError("after must be a non-negative integer")
        if type(limit) is not int or limit <= 0:
            raise ValueError("limit must be a positive integer")
        runtime = self._get(session_id)
        with runtime.condition:
            retained = list(runtime.events)
            truncated = bool(retained and after < retained[0].cursor - 1)
            selected = [event for event in retained if event.cursor > after][:limit]
            next_cursor = selected[-1].cursor if selected else after
            return EventPage(selected, next_cursor, truncated)

    def agent_messages(self, session_id: str, tail: int):
        """Return a bounded, read-only live narration view without consuming events."""
        if type(tail) is not int or tail <= 0:
            raise ValueError("tail must be a positive integer")
        runtime = self._get(session_id)
        with runtime.condition:
            items = []
            if runtime.active_turn_id is not None:
                items = list(runtime.items.get(runtime.active_turn_id, []))
            elif runtime.latest_turn is not None:
                items = list(runtime.latest_turn.items)
            agents = [item for item in items if item.type == "agentMessage"]
            retained = list(runtime.events)
            latest_cursor = retained[-1].cursor if retained else None
            # Event eviction is the only available retention signal; callers see it
            # explicitly instead of treating this as durable history.
            truncated = len(agents) > tail
            return agents[-tail:], truncated, latest_cursor
