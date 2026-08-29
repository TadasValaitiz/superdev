"""High-level durable session and turn contract for the Codex worker daemon."""
import os
import shlex
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Protocol, Tuple

from .app_server import CodexCallError
from .models import (
    ActiveInventory,
    ActiveThreadItem,
    IdentifierSelector,
    JsonObject,
    MaintenanceResult,
    RpcFault,
    SessionRecord,
    session_result,
)
from .commands import AccessMode
from .version import distribution_version
from .registry import RegistryError, SessionRegistry
from .runtime import (
    CodexProtocolError,
    NoTurn,
    RuntimeStore,
    SessionDetached,
    TurnActive,
    UnknownSession,
    WaitTimeout,
)
from .service_domain import DEFAULT_PUBLIC_LISTENER, AttachView, validate_public_listener
from .websocket_gateway import DrainLease, ServiceMaintenanceGate


class ModelSelectionError(RpcFault):
    def __init__(self, message: str, details: Optional[JsonObject] = None):
        super().__init__(-32010, message, "invalid_model_selection", details=details)


class AnnotationPolicy(str, Enum):
    LEGACY_MUTABLE = "legacy_mutable"
    PRESERVE_WORKER_POLICY = "preserve_worker_policy"


@dataclass(frozen=True)
class SessionStartSpec:
    cwd: str
    name: Optional[str]
    model: Optional[str]
    access: AccessMode = AccessMode.FULL
    tier: Optional[str] = None
    effort: Optional[str] = None
    annotation_policy: AnnotationPolicy = AnnotationPolicy.LEGACY_MUTABLE


@dataclass(frozen=True)
class SessionResumeSpec:
    thread_id: str
    access: AccessMode = AccessMode.FULL


@dataclass(frozen=True)
class TurnStartSpec:
    session_id: str
    prompt: str
    model: Optional[str]
    effort: Optional[str]
    access: AccessMode = AccessMode.FULL
    output_schema: Optional[JsonObject] = None


class MaintenanceLifecycle(Protocol):
    @property
    def gate(self) -> ServiceMaintenanceGate:
        ...

    def terminate_owned(self, lease: DrainLease) -> None:
        ...


class NativeCodexProxy:
    """Thin, validated native calls; provider field names remain untouched."""
    def __init__(self, codex: Any): self.codex = codex
    def _call(self, method: str, params: JsonObject) -> JsonObject:
        result = self.codex.call(method, params)
        if not isinstance(result, dict):
            raise CodexCallError("protocol_error", method, {"message": "result must be an object"})
        return result
    @staticmethod
    def _protocol(method: str, message: str) -> None:
        raise CodexCallError("protocol_error", method, {"message": message})
    def _goal(self, method: str, result: JsonObject, allow_absent: bool) -> JsonObject:
        if set(result) != {"goal"}:
            self._protocol(method, "unexpected goal response fields")
        goal = result["goal"]
        if goal is None and allow_absent:
            return result
        required = {"threadId", "objective", "status", "tokenBudget", "tokensUsed", "timeUsedSeconds", "createdAt", "updatedAt"}
        if not isinstance(goal, dict) or set(goal) != required:
            self._protocol(method, "malformed goal")
        if (not all(isinstance(goal[key], str) and goal[key] for key in ("threadId", "objective"))
                or goal["status"] not in ("active", "paused", "blocked", "usageLimited", "budgetLimited", "complete")
                or (goal["tokenBudget"] is not None and (type(goal["tokenBudget"]) is not int or goal["tokenBudget"] <= 0))
                or any(type(goal[key]) is not int or goal[key] < 0 for key in (
                    "tokensUsed", "timeUsedSeconds", "createdAt", "updatedAt"
                ))):
            self._protocol(method, "malformed goal fields")
        return result
    def goal_set(self, thread_id: str, objective: Optional[str] = None, status: Optional[str] = None,
                 token_budget: Optional[int] = None) -> JsonObject:
        params = {"threadId": thread_id}
        if objective is not None: params["objective"] = objective
        if status is not None: params["status"] = status
        if token_budget is not None: params["tokenBudget"] = token_budget
        return self._goal("thread/goal/set", self._call("thread/goal/set", params), False)
    def goal_get(self, thread_id: str) -> JsonObject:
        return self._goal("thread/goal/get", self._call("thread/goal/get", {"threadId": thread_id}), True)
    def turns_list(self, thread_id: str, cursor: Optional[str] = None, limit: Optional[int] = None) -> JsonObject:
        params = {"threadId": thread_id, "sortDirection": "desc", "itemsView": "full"}
        if cursor is not None: params["cursor"] = cursor
        if limit is not None: params["limit"] = limit
        result = self._call("thread/turns/list", params)
        if (set(result) != {"data", "nextCursor", "backwardsCursor"}
                or not isinstance(result["data"], list)
                or any(result[key] is not None and not isinstance(result[key], str)
                       for key in ("nextCursor", "backwardsCursor"))):
            self._protocol("thread/turns/list", "malformed turn page")
        from .projection import project_history_turn
        for turn in result["data"]:
            try:
                project_history_turn(turn)
            except ValueError as exc:
                self._protocol("thread/turns/list", str(exc))
        return {"turns": result["data"], "nextCursor": result["nextCursor"]}
    def rate_limits_read(self) -> JsonObject:
        result = self._call("account/rateLimits/read", {})
        if "rateLimits" not in result or not isinstance(result["rateLimits"], dict):
            self._protocol("account/rateLimits/read", "malformed rate limits")
        return result


def _fault(code: int, message: str, kind: str,
           recovery: Optional[str] = None, details: Optional[JsonObject] = None) -> RpcFault:
    return RpcFault(code, message, kind, recovery, details)


class WorkerBroker:
    """Coordinate one Codex adapter, persistent sessions, and live turn state.

    This class intentionally owns no request-wide lock.  ``SessionRegistry`` and
    ``RuntimeStore`` protect their own short critical sections, while calls to
    Codex and condition-variable waits happen outside of broker-held locks.
    """

    def __init__(self, registry: SessionRegistry, codex: Any, runtime: RuntimeStore,
                 socket_path: str, state_path: str, daemon_pid: Optional[int] = None,
                 worker_version: Optional[str] = None,
                 gate: Optional[ServiceMaintenanceGate] = None,
                 listener: str = DEFAULT_PUBLIC_LISTENER):
        self.registry = registry
        self.codex = codex
        self.runtime = runtime
        self.socket_path = socket_path
        self.state_path = state_path
        self.daemon_pid = os.getpid() if daemon_pid is None else daemon_pid
        self.worker_version = distribution_version() if worker_version is None else worker_version
        if gate is not None and not isinstance(gate, ServiceMaintenanceGate):
            raise TypeError("gate must be ServiceMaintenanceGate")
        self._gate = gate or ServiceMaintenanceGate()
        self._listener = validate_public_listener(listener)

    def daemon_status(self) -> JsonObject:
        proc = getattr(self.codex, "proc", None)
        poll = getattr(proc, "poll", None)
        ready = True
        if callable(poll):
            ready = poll() is None
        records = self.registry.list()
        return {
            "ready": ready,
            "daemon_pid": self.daemon_pid,
            "codex_pid": getattr(proc, "pid", None),
            "socket_path": self.socket_path,
            "state_path": self.state_path,
            "session_count": len(records),
            "worker_names": sorted(record.name for record in records
                                   if record.name is not None),
            "worker_version": self.worker_version,
        }

    @staticmethod
    def _thread_sandbox(access: AccessMode) -> str:
        return "danger-full-access" if access == AccessMode.FULL else "read-only"

    @staticmethod
    def _turn_sandbox(access: AccessMode) -> JsonObject:
        return {"type": "dangerFullAccess"} if access == AccessMode.FULL else {"type": "readOnly", "networkAccess": False}

    def start_session(self, spec: SessionStartSpec) -> JsonObject:
        with self._gate.mutation("thread/start"):
            return self._start_session_authoritatively(spec)

    def _start_session_authoritatively(self, spec: SessionStartSpec) -> JsonObject:
        canonical_cwd = self._canonical_cwd(spec.cwd, "declared cwd")
        self._validate_model_effort(spec.model, None)
        if spec.annotation_policy == AnnotationPolicy.PRESERVE_WORKER_POLICY:
            if (spec.name is None or spec.model is None or spec.effort is None
                    or spec.access is None):
                raise _fault(-32602, "common worker start requires name, model, effort, and access",
                             "invalid_params")
            self._validate_model_effort(spec.model, spec.effort)
        session_id = str(uuid.uuid4())
        try:
            response = self.codex.start_thread(canonical_cwd, model=spec.model,
                                               sandbox=self._thread_sandbox(spec.access),
                                               allow_provider_model_fallback=False)
            thread_id, returned_cwd = self._resume_identity(response)
            if returned_cwd != canonical_cwd:
                raise _fault(-32014, "Codex returned a different working directory", "session_cwd_mismatch",
                             details=self._known_identity_details(
                                 session_id, thread_id, None,
                                 {"expected_cwd": canonical_cwd,
                                  "returned_cwd": returned_cwd}))
            if spec.annotation_policy == AnnotationPolicy.PRESERVE_WORKER_POLICY:
                record = self.registry.create_worker(
                    thread_id, canonical_cwd, spec.name, spec.tier, spec.model,
                    spec.effort, spec.access.value, session_id=session_id)
            else:
                record = self.registry.create(thread_id, canonical_cwd, spec.name, spec.model,
                                              None, session_id=session_id)
        except RpcFault:
            raise
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc
        except (RegistryError, OSError) as exc:
            raise self._post_upstream_registry_fault("session_start", session_id, thread_id, None, exc) from exc
        self.runtime.attach(record)
        result = session_result(record, attached=True)
        result["attach"] = self.attach_view(record.thread_id).to_dict()
        return result

    def resume_session(self, spec: SessionResumeSpec) -> JsonObject:
        with self._gate.mutation("thread/resume"):
            return self._resume_session_authoritatively(spec)

    def _resume_session_authoritatively(self, spec: SessionResumeSpec) -> JsonObject:
        try:
            response = self.codex.resume_thread(spec.thread_id, approval_policy="never",
                                                sandbox=self._thread_sandbox(spec.access))
            thread_id, cwd = self._resume_identity(response)
            if thread_id != spec.thread_id:
                raise _fault(-32015, "Codex resume returned a different thread", "codex_protocol_error")
            return response
        except RpcFault:
            raise
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc

    def start_turn(self, spec: TurnStartSpec) -> JsonObject:
        with self._gate.mutation("turn/start"):
            return self._start_turn_authoritatively(spec)

    def _start_turn_authoritatively(self, spec: TurnStartSpec) -> JsonObject:
        record = self._resolve(IdentifierSelector(session_id=spec.session_id), require_attached=True)
        if not isinstance(spec.prompt, str) or not spec.prompt:
            raise _fault(-32602, "prompt must be a non-empty string", "invalid_params")
        validation_model = spec.model if spec.model is not None or spec.effort is None else record.model
        effective_model = self._validate_model_effort(validation_model, spec.effort)
        upstream_model = effective_model if spec.effort is not None else spec.model
        turn_id = None  # type: Optional[str]
        try:
            self.runtime.reserve_start(record.session_id)
            try:
                turn_id = self.codex.start_turn(record.thread_id, spec.prompt, model=upstream_model,
                                                effort=spec.effort, sandbox_policy=self._turn_sandbox(spec.access),
                                                output_schema=spec.output_schema)
                self.runtime.reconcile_start(record.session_id, turn_id)
            except BaseException:
                self.runtime.cancel_start(record.session_id)
                raise
        except (CodexCallError, CodexProtocolError, TurnActive, SessionDetached, UnknownSession) as exc:
            raise self._from_lower(exc, record, turn_id) from exc
        policy = AnnotationPolicy.PRESERVE_WORKER_POLICY if record.common_policy_complete else AnnotationPolicy.LEGACY_MUTABLE
        if policy == AnnotationPolicy.LEGACY_MUTABLE:
            annotation_model = effective_model if spec.effort is not None else spec.model or record.model
            annotation_effort = spec.effort or record.effort
            try:
                self.registry.update_annotations(record.session_id, model=annotation_model, effort=annotation_effort)
            except (RegistryError, OSError) as exc:
                raise self._post_upstream_registry_fault("turn_start_annotations", record.session_id, record.thread_id, turn_id, exc) from exc
        return {"session_id": record.session_id, "thread_id": record.thread_id,
                "turn_id": turn_id, "status": "in_progress",
                "attach": self.attach_view(record.thread_id).to_dict()}

    def model_list(self) -> JsonObject:
        return {"models": self._models()}

    def session_start(self, cwd: str, name: Optional[str] = None,
                      model: Optional[str] = None) -> JsonObject:
        return self.start_session(SessionStartSpec(cwd, name, model))

    def session_resume(self, selector: IdentifierSelector,
                       name: Optional[str] = None) -> JsonObject:
        with self._gate.mutation("thread/resume"):
            return self._session_resume_authoritatively(selector, name)

    def _session_resume_authoritatively(self, selector: IdentifierSelector,
                                        name: Optional[str] = None) -> JsonObject:
        try:
            existing = self.registry.try_resolve(selector)
        except RegistryError as exc:
            raise _fault(-32011, "could not read session registry", "registry_error", details={"reason": str(exc)}) from exc
        if existing is not None:
            if name is not None:
                raise _fault(-32602, "--name is only valid for raw thread recovery", "invalid_params")
            try:
                response = self._resume_session_authoritatively(SessionResumeSpec(
                    existing.thread_id,
                    AccessMode(existing.access) if existing.access else AccessMode.FULL,
                ))
                thread_id, returned_cwd = self._resume_identity(response)
                if thread_id != existing.thread_id:
                    raise _fault(
                        -32015, "Codex resume returned a different thread", "codex_protocol_error",
                        details={"expected_thread_id": existing.thread_id, "returned_thread_id": thread_id},
                    )
                if returned_cwd != existing.cwd:
                    raise _fault(
                        -32014, "Codex resume working directory does not match the session", "session_cwd_mismatch",
                        details={"expected_cwd": existing.cwd, "returned_cwd": returned_cwd},
                    )
                self.runtime.attach(existing)
                result = session_result(existing, attached=True)
                result["attach"] = self.attach_view(existing.thread_id).to_dict()
                return result
            except RpcFault as exc:
                raise self._with_record_identity(exc, existing) from exc
            except (CodexCallError, CodexProtocolError) as exc:
                raise self._from_lower(exc, existing) from exc

        if selector.thread_id is None:
            raise self._unknown_session(selector)
        session_id = str(uuid.uuid4())
        try:
            response = self._resume_session_authoritatively(SessionResumeSpec(
                selector.thread_id, AccessMode.FULL))
            thread_id, recovered_cwd = self._resume_identity(response)
            if thread_id != selector.thread_id:
                raise _fault(
                    -32015, "Codex resume returned a different thread", "codex_protocol_error",
                    details={"expected_thread_id": selector.thread_id, "returned_thread_id": thread_id},
                )
            record = self.registry.create(
                thread_id, recovered_cwd, name,
                self._string_annotation(response, "model"),
                self._string_annotation(response, "reasoningEffort"),
                session_id=session_id,
            )
        except RpcFault as exc:
            raise _fault(
                exc.code, exc.message, exc.kind, exc.recovery,
                self._known_identity_details(
                    session_id, selector.thread_id, None, exc.details),
            ) from exc
        except (CodexCallError, CodexProtocolError) as exc:
            raise self._from_lower(exc) from exc
        except (RegistryError, OSError) as exc:
            raise self._post_upstream_registry_fault(
                "session_resume", session_id, selector.thread_id, None, exc,
            ) from exc
        self.runtime.attach(record)
        result = session_result(record, attached=True)
        result["attach"] = self.attach_view(record.thread_id).to_dict()
        return result

    def session_list(self) -> JsonObject:
        sessions = []  # type: List[JsonObject]
        try:
            records = self.registry.list()
        except RegistryError as exc:
            raise _fault(-32011, "could not read session registry", "registry_error", details={"reason": str(exc)}) from exc
        for record in records:
            status = self._status_or_detached(record)
            sessions.append({
                "session": record.to_dict(),
                "attached": status.attached,
                "active_turn_id": status.active_turn_id,
                "latest_turn_status": status.latest_turn.status if status.latest_turn else None,
                "attach": self.attach_view(record.thread_id).to_dict(),
            })
        return {"sessions": sessions}

    def session_show(self, selector: IdentifierSelector) -> JsonObject:
        record = self._resolve(selector, require_attached=False)
        status = self._status_or_detached(record)
        return {
            "session": record.to_dict(),
            "attached": status.attached,
            "active_turn_id": status.active_turn_id,
            "latest_turn": status.latest_turn.to_dict() if status.latest_turn else None,
            "attach": self.attach_view(record.thread_id).to_dict(),
        }

    def turn_start(self, selector: IdentifierSelector, prompt: str,
                   model: Optional[str] = None, effort: Optional[str] = None) -> JsonObject:
        record = self._resolve(selector, require_attached=True)
        return self.start_turn(TurnStartSpec(record.session_id, prompt, model, effort,
                                             AccessMode(record.access) if record.access else AccessMode.FULL))

    def turn_status(self, selector: IdentifierSelector) -> JsonObject:
        record = self._resolve(selector, require_attached=False)
        status = self._status_or_detached(record)
        if status.attached:
            self._reconcile_from_upstream(record)
            status = self._status_or_detached(record)
        return {
            "session_id": record.session_id, "thread_id": record.thread_id,
            "attached": status.attached, "active_turn_id": status.active_turn_id,
            "latest_turn": status.latest_turn.to_dict() if status.latest_turn else None,
            "attach": self.attach_view(record.thread_id).to_dict(),
        }

    def turn_history(self, selector: IdentifierSelector,
                     cursor: Optional[str] = None,
                     limit: Optional[int] = None) -> JsonObject:
        """Return an authoritative history page after reconciling attached runtime."""
        record = self._resolve(selector, require_attached=False)
        if self._status_or_detached(record).attached:
            self._reconcile_from_upstream(record)
        try:
            page = NativeCodexProxy(self.codex).turns_list(
                record.thread_id, cursor, limit)
        except CodexCallError as exc:
            raise self._from_lower(exc, record) from exc
        return {
            "session_id": record.session_id,
            "thread_id": record.thread_id,
            "turns": page["turns"],
            "nextCursor": page["nextCursor"],
            "attach": self.attach_view(record.thread_id).to_dict(),
        }

    def turn_wait(self, selector: IdentifierSelector, timeout: float) -> JsonObject:
        record = self._resolve(selector, require_attached=True)
        try:
            turn = self.runtime.wait(record.session_id, timeout)
            return {"session_id": record.session_id, "thread_id": record.thread_id,
                    "turn": turn.to_dict(),
                    "attach": self.attach_view(record.thread_id).to_dict()}
        except (WaitTimeout, NoTurn, SessionDetached, UnknownSession, ValueError) as exc:
            raise self._from_lower(exc, record) from exc

    def turn_events(self, selector: IdentifierSelector, after: int, limit: int) -> JsonObject:
        record = self._resolve(selector, require_attached=False)
        try:
            result = self.runtime.events(record.session_id, after, limit).to_dict()
            result["attach"] = self.attach_view(record.thread_id).to_dict()
            return result
        except (UnknownSession, ValueError) as exc:
            raise self._from_lower(exc, record) from exc

    def turn_steer(self, selector: IdentifierSelector, prompt: str,
                   expected_turn_id: Optional[str] = None) -> JsonObject:
        with self._gate.mutation("turn/steer"):
            return self._turn_steer_authoritatively(
                selector, prompt, expected_turn_id)

    def _turn_steer_authoritatively(self, selector: IdentifierSelector, prompt: str,
                                    expected_turn_id: Optional[str] = None) -> JsonObject:
        if not isinstance(prompt, str) or not prompt:
            raise _fault(-32602, "prompt must be a non-empty string", "invalid_params")
        record = self._resolve(selector, require_attached=True)
        turn_id = self._active_turn_or_fault(record, expected_turn_id)
        try:
            returned_id = self.codex.steer(record.thread_id, turn_id, prompt)
        except CodexCallError as exc:
            self._raise_control_race_or_codex(record, turn_id, exc)
        if returned_id != turn_id:
            raise _fault(
                -32015, "Codex steer returned a different turn", "codex_protocol_error",
                details=self._known_identity_details(
                    record.session_id, record.thread_id, turn_id,
                    {"expected_turn_id": turn_id,
                     "returned_turn_id": returned_id}),
            )
        return {"session_id": record.session_id, "thread_id": record.thread_id,
                "turn_id": turn_id, "accepted": True,
                "attach": self.attach_view(record.thread_id).to_dict()}

    def turn_interrupt(self, selector: IdentifierSelector,
                       expected_turn_id: Optional[str] = None) -> JsonObject:
        with self._gate.mutation("turn/interrupt"):
            return self._turn_interrupt_authoritatively(selector, expected_turn_id)

    def _turn_interrupt_authoritatively(self, selector: IdentifierSelector,
                                        expected_turn_id: Optional[str] = None) -> JsonObject:
        record = self._resolve(selector, require_attached=True)
        turn_id = self._active_turn_or_fault(record, expected_turn_id)
        try:
            self.codex.interrupt(record.thread_id, turn_id)
        except CodexCallError as exc:
            self._raise_control_race_or_codex(record, turn_id, exc)
        return {"session_id": record.session_id, "thread_id": record.thread_id,
                "turn_id": turn_id, "accepted": True,
                "attach": self.attach_view(record.thread_id).to_dict()}

    def shutdown(self) -> JsonObject:
        with self._gate.mutation("shutdown"):
            try:
                self.codex.shutdown()
            except CodexCallError as exc:
                raise self._codex_fault(exc) from exc
            return {"accepted": True}

    def goal_set(self, thread_id: str, objective: Optional[str] = None,
                 status: Optional[str] = None,
                 token_budget: Optional[int] = None) -> JsonObject:
        with self._gate.mutation("thread/goal/set"):
            return NativeCodexProxy(self.codex).goal_set(
                thread_id, objective, status, token_budget)

    def goal_get(self, thread_id: str) -> JsonObject:
        return NativeCodexProxy(self.codex).goal_get(thread_id)

    def attach_view(self, thread_id: str) -> AttachView:
        from .projection import build_attach_view
        return build_attach_view(self._listener, thread_id)

    def _reconcile_from_upstream(self, record: SessionRecord) -> None:
        try:
            result = self.codex.call("thread/read", {
                "threadId": record.thread_id,
                "includeTurns": True,
            })
            if (not isinstance(result, dict) or set(result) != {"thread"}
                    or not isinstance(result["thread"], dict)
                    or result["thread"].get("id") != record.thread_id):
                raise CodexCallError(
                    "protocol_error", "thread/read",
                    {"message": "malformed authoritative thread response"})
            self.runtime.reconcile_thread(result["thread"])
        except CodexCallError as exc:
            raise self._from_lower(exc, record) from exc
        except CodexProtocolError as exc:
            raise self._from_lower(exc, record) from exc

    def list_active_threads(self) -> ActiveInventory:
        """Page the all-source app-server inventory; any ambiguity fails closed."""
        try:
            records = self.registry.list()
        except RegistryError as exc:
            raise _fault(-32011, "could not read session registry", "registry_error",
                         details={"reason": str(exc)}) from exc
        by_thread = {record.thread_id: record for record in records}
        active = {}  # type: JsonObject
        cursor = None  # type: Optional[str]
        seen_cursors = set()
        try:
            while True:
                params = {"sourceKinds": []}  # type: JsonObject
                if cursor is not None:
                    params["cursor"] = cursor
                result = self.codex.call("thread/list", params)
                self._validate_inventory_page(result)
                for thread in result["data"]:
                    status = thread["status"]
                    thread_id = thread["id"]
                    if status["type"] == "active":
                        active.setdefault(thread_id, list(status["activeFlags"]))
                next_cursor = result.get("nextCursor")
                if next_cursor is None:
                    break
                if next_cursor in seen_cursors or next_cursor == cursor:
                    raise CodexCallError(
                        "protocol_error", "thread/list",
                        {"message": "thread inventory cursor did not progress"})
                seen_cursors.add(next_cursor)
                cursor = next_cursor
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc
        items = []
        for thread_id, active_flags in active.items():
            turn_id = self._inventory_turn_id(thread_id)
            record = by_thread.get(thread_id)
            if record is None:
                items.append(ActiveThreadItem(
                    thread_id, "unmapped_tui", None, None, turn_id, active_flags))
            else:
                items.append(ActiveThreadItem(
                    thread_id, "worker", record.name, record.session_id,
                    turn_id, active_flags))
        return ActiveInventory(items)

    def _inventory_turn_id(self, thread_id: str) -> str:
        try:
            result = self.codex.call("thread/read", {
                "threadId": thread_id, "includeTurns": True})
            thread = result.get("thread") if isinstance(result, dict) else None
            turns = thread.get("turns") if isinstance(thread, dict) else None
            active = ([turn for turn in turns
                       if isinstance(turn, dict) and turn.get("status") == "inProgress"]
                      if isinstance(turns, list) else [])
            if (thread is None or thread.get("id") != thread_id
                    or not isinstance(thread.get("status"), dict)
                    or thread["status"].get("type") != "active"
                    or len(active) != 1
                    or not isinstance(active[0].get("id"), str)
                    or not active[0]["id"]):
                raise CodexCallError(
                    "protocol_error", "thread/read",
                    {"message": "active inventory turn identity is ambiguous"})
            return active[0]["id"]
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc

    @staticmethod
    def _validate_inventory_page(result: object) -> None:
        expected = {"data", "nextCursor", "backwardsCursor"}
        if (not isinstance(result, dict) or set(result) != expected
                or not isinstance(result["data"], list)
                or result.get("nextCursor") is not None
                and (not isinstance(result.get("nextCursor"), str)
                     or not result.get("nextCursor"))
                or result.get("backwardsCursor") is not None
                and not isinstance(result.get("backwardsCursor"), str)):
            raise CodexCallError(
                "protocol_error", "thread/list",
                {"message": "malformed thread inventory page"})
        for thread in result["data"]:
            if (not isinstance(thread, dict)
                    or not isinstance(thread.get("id"), str)
                    or not thread["id"]
                    or not isinstance(thread.get("status"), dict)):
                raise CodexCallError(
                    "protocol_error", "thread/list",
                    {"message": "malformed thread inventory item"})
            status = thread["status"]
            status_type = status.get("type")
            if status_type == "active":
                if (set(status) != {"type", "activeFlags"}
                        or not isinstance(status.get("activeFlags"), list)
                        or any(not isinstance(flag, str) or not flag
                               for flag in status["activeFlags"])):
                    raise CodexCallError(
                        "protocol_error", "thread/list",
                        {"message": "malformed active thread status"})
            elif status_type in ("idle", "notLoaded", "systemError"):
                if set(status) != {"type"}:
                    raise CodexCallError(
                        "protocol_error", "thread/list",
                        {"message": "malformed inactive thread status"})
            else:
                raise CodexCallError(
                    "protocol_error", "thread/list",
                    {"message": "unknown thread status"})

    def _models(self) -> List[JsonObject]:
        try:
            raw_models = self.codex.list_models()
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc
        if not isinstance(raw_models, list):
            raise _fault(-32015, "Codex model list is malformed", "codex_protocol_error")
        normalized = []  # type: List[JsonObject]
        seen = set()
        for raw in raw_models:
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
                raise _fault(-32015, "Codex model list is malformed", "codex_protocol_error")
            model_id = raw["id"]
            if model_id in seen:
                raise _fault(-32015, "Codex model list contains duplicate IDs", "codex_protocol_error")
            seen.add(model_id)
            efforts = self._efforts(raw)
            is_default = raw.get("is_default", raw.get("isDefault", False))
            if type(is_default) is not bool:
                raise _fault(-32015, "Codex model default flag is malformed", "codex_protocol_error")
            normalized.append({"id": model_id, "is_default": is_default, "supported_efforts": efforts})
        return normalized

    @staticmethod
    def _efforts(raw: JsonObject) -> List[str]:
        value = raw.get("supported_efforts", raw.get("supportedReasoningEfforts", []))
        if not isinstance(value, list):
            raise _fault(-32015, "Codex model efforts are malformed", "codex_protocol_error")
        efforts = []
        for item in value:
            effort = item.get("reasoningEffort") if isinstance(item, dict) else item
            if not isinstance(effort, str) or not effort:
                raise _fault(-32015, "Codex model efforts are malformed", "codex_protocol_error")
            efforts.append(effort)
        if len(set(efforts)) != len(efforts):
            raise _fault(-32015, "Codex model efforts are duplicated", "codex_protocol_error")
        return efforts

    def _validate_model_effort(self, model: Optional[str], effort: Optional[str]) -> Optional[str]:
        if model is not None and (not isinstance(model, str) or not model):
            raise ModelSelectionError("model must be a non-empty string", {"model": model})
        if effort is not None and (not isinstance(effort, str) or not effort):
            raise ModelSelectionError("effort must be a non-empty string", {"effort": effort})
        models = self._models()
        selected = None
        if model is not None:
            selected = next((item for item in models if item["id"] == model), None)
            if selected is None:
                raise ModelSelectionError("model is not available from live discovery", {"model": model})
        elif effort is not None:
            defaults = [item for item in models if item["is_default"]]
            if len(defaults) == 1:
                selected = defaults[0]
            elif len(defaults) > 1:
                raise ModelSelectionError("live model list has multiple defaults")
            else:
                raise ModelSelectionError("effort requires an explicit model when no default is advertised",
                                          {"effort": effort})
        if effort is not None and selected is not None and effort not in selected["supported_efforts"]:
            raise ModelSelectionError("effort is not supported by selected live model",
                                      {"model": selected["id"], "effort": effort,
                                       "supported_efforts": selected["supported_efforts"]})
        return selected["id"] if selected is not None else None

    @staticmethod
    def _canonical_cwd(cwd: str, label: str) -> str:
        if not isinstance(cwd, str) or not cwd:
            raise _fault(-32602, "%s must be a non-empty path" % label, "invalid_params")
        path = Path(cwd)
        if not path.is_absolute():
            raise _fault(-32602, "%s must be absolute" % label, "invalid_params")
        try:
            canonical = str(path.resolve(strict=True))
        except (OSError, RuntimeError) as exc:
            raise _fault(-32602, "%s must be an existing directory" % label, "invalid_params") from exc
        if not os.path.isdir(canonical):
            raise _fault(-32602, "%s must be an existing directory" % label, "invalid_params")
        return canonical

    def _resume_identity(self, response: Any) -> Tuple[str, str]:
        if not isinstance(response, dict):
            raise _fault(-32015, "Codex thread response is malformed", "codex_protocol_error")
        thread = response.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
            raise _fault(-32015, "Codex thread response omitted its ID", "codex_protocol_error")
        # Codex 0.147.0 requires Thread.cwd.  Prefer it over the duplicate
        # response-level compatibility field and reject their disagreement.
        thread_cwd = self._upstream_cwd(thread.get("cwd"), "Codex thread.cwd")
        response_cwd = response.get("cwd")
        if response_cwd is not None:
            normalized_response_cwd = self._upstream_cwd(response_cwd, "Codex response cwd")
            if normalized_response_cwd != thread_cwd:
                raise _fault(-32015, "Codex response has conflicting working directories", "codex_protocol_error")
        return thread["id"], thread_cwd

    @staticmethod
    def _upstream_cwd(cwd: Any, label: str) -> str:
        """Validate a Codex-provided immutable cwd as upstream protocol data."""
        if not isinstance(cwd, str) or not cwd:
            raise _fault(-32015, "%s is missing or malformed" % label, "codex_protocol_error")
        path = Path(cwd)
        if not path.is_absolute():
            raise _fault(-32015, "%s must be absolute" % label, "codex_protocol_error")
        try:
            canonical = str(path.resolve(strict=True))
        except (OSError, RuntimeError) as exc:
            raise _fault(-32015, "%s must be an existing directory" % label, "codex_protocol_error") from exc
        if not os.path.isdir(canonical):
            raise _fault(-32015, "%s must be an existing directory" % label, "codex_protocol_error")
        return canonical

    @staticmethod
    def _string_annotation(response: Any, key: str) -> Optional[str]:
        value = response.get(key) if isinstance(response, dict) else None
        return value if isinstance(value, str) and value else None

    def _resolve(self, selector: IdentifierSelector, require_attached: bool) -> SessionRecord:
        try:
            record = self.registry.try_resolve(selector)
        except RegistryError as exc:
            raise _fault(-32011, "could not read session registry", "registry_error", details={"reason": str(exc)}) from exc
        if record is None:
            raise self._unknown_session(selector)
        if require_attached:
            status = self._status_or_detached(record)
            if not status.attached:
                raise _fault(
                    -32003, "session is detached", "session_detached",
                    recovery="codex-worker session resume --session %s" % shlex.quote(
                        record.session_id),
                    details=self._known_identity_details(
                        record.session_id, record.thread_id, None),
                )
        return record

    def _unknown_session(self, selector: IdentifierSelector) -> RpcFault:
        if selector.thread_id is not None:
            return _fault(
                -32001, "unknown raw thread; recover it with session resume --thread %s" % selector.thread_id,
                "unknown_session", recovery="codex-worker session resume --thread %s" % shlex.quote(
                    selector.thread_id),
                details={"thread_id": selector.thread_id},
            )
        return _fault(
            -32001, "unknown session", "unknown_session",
            recovery="codex-worker session list",
            details={"session_id": selector.session_id},
        )

    def _status_or_detached(self, record: SessionRecord):
        try:
            return self.runtime.status(record.session_id)
        except UnknownSession:
            # Persisted records are detached after a daemon restart until the
            # caller explicitly resumes them; read methods must not reattach.
            from .models import RuntimeStatus
            return RuntimeStatus(attached=False)

    def _active_turn_or_fault(self, record: SessionRecord,
                              expected_turn_id: Optional[str] = None) -> str:
        status = self._status_or_detached(record)
        if not status.attached:
            raise _fault(
                -32003, "session is detached", "session_detached",
                recovery="codex-worker session resume --session %s" % shlex.quote(
                    record.session_id),
                details=self._known_identity_details(
                    record.session_id, record.thread_id, expected_turn_id),
            )
        if (status.active_turn_id is None
                or expected_turn_id is not None and status.active_turn_id != expected_turn_id):
            latest_turn_id = status.latest_turn.turn_id if status.latest_turn else None
            raise self._turn_not_active(
                record, status.latest_turn,
                expected_turn_id if expected_turn_id is not None else latest_turn_id,
            )
        return status.active_turn_id

    def _raise_control_race_or_codex(self, record: SessionRecord, expected_turn_id: str,
                                     exc: CodexCallError) -> None:
        status = self._status_or_detached(record)
        if self._is_upstream_turn_not_active(exc):
            raise self._turn_not_active(record, status.latest_turn, expected_turn_id) from exc
        raise self._with_record_identity(self._codex_fault(exc), record,
                                         expected_turn_id) from exc

    @staticmethod
    def _is_upstream_turn_not_active(exc: CodexCallError) -> bool:
        expected_messages = {
            "turn/steer": "no active turn to steer",
            "turn/interrupt": "no active turn to interrupt",
        }
        if exc.kind != "upstream_error" or not isinstance(exc.details, dict):
            return False
        return (
            exc.details.get("code") == -32600
            and exc.details.get("message") == expected_messages.get(exc.method)
        )

    def _turn_not_active(self, record: SessionRecord, latest_turn: Any,
                         turn_id: Optional[str] = None) -> RpcFault:
        return _fault(
            -32005, "turn is not active", "turn_not_active",
            details={
                "session_id": record.session_id,
                "thread_id": record.thread_id,
                "turn_id": turn_id,
                "latest_turn": latest_turn.to_dict() if latest_turn else None,
                "attach": self.attach_view(record.thread_id).to_dict(),
            },
        )

    def _post_upstream_registry_fault(self, operation: str, session_id: str,
                                      thread_id: str, turn_id: Optional[str],
                                      exc: BaseException) -> RpcFault:
        details = {
            "operation": operation,
            "durable_state": "not_persisted",
            "session_id": session_id,
            "thread_id": thread_id,
            "reason": str(exc),
            "attach": self.attach_view(thread_id).to_dict(),
        }  # type: JsonObject
        if turn_id is None:
            recovery = "codex-worker session resume --thread %s" % shlex.quote(thread_id)
            message = "Codex thread exists but its session identity was not persisted"
        else:
            details["turn_id"] = turn_id
            recovery = "codex-worker turn status --session %s" % shlex.quote(session_id)
            message = "Codex turn started but its session annotations were not persisted"
        return _fault(-32011, message, "registry_error", recovery=recovery, details=details)

    @staticmethod
    def _codex_fault(exc: CodexCallError) -> RpcFault:
        if exc.kind == "protocol_error":
            return _fault(
                -32015, "Codex response violates the expected protocol", "codex_protocol_error",
                details={"method": exc.method, "details": exc.details},
            )
        return _fault(
            -32020, "Codex operation failed", "codex_failure",
            details={"method": exc.method, "kind": exc.kind, "details": exc.details},
        )

    def _known_identity_details(self, session_id: str, thread_id: str,
                                turn_id: Optional[str],
                                details: Optional[JsonObject] = None) -> JsonObject:
        result = dict(details or {})
        result.update({
            "session_id": session_id,
            "thread_id": thread_id,
            "attach": self.attach_view(thread_id).to_dict(),
        })
        if turn_id is not None:
            result["turn_id"] = turn_id
        return result

    def _with_record_identity(self, fault: RpcFault, record: SessionRecord,
                              turn_id: Optional[str] = None) -> RpcFault:
        return _fault(
            fault.code, fault.message, fault.kind, fault.recovery,
            self._known_identity_details(
                record.session_id, record.thread_id, turn_id, fault.details),
        )

    def _from_lower(self, exc: BaseException,
                    record: Optional[SessionRecord] = None,
                    turn_id: Optional[str] = None) -> RpcFault:
        if isinstance(exc, CodexCallError):
            fault = self._codex_fault(exc)
            return (fault if record is None
                    else self._with_record_identity(fault, record, turn_id))
        if isinstance(exc, CodexProtocolError):
            fault = _fault(-32015, "Codex protocol state is inconsistent",
                           "codex_protocol_error", details={"reason": str(exc)})
            return (fault if record is None
                    else self._with_record_identity(fault, record, turn_id))
        if isinstance(exc, TurnActive):
            fault = _fault(-32004, "session already has an active turn", "turn_active")
            return (fault if record is None
                    else self._with_record_identity(fault, record, turn_id))
        if isinstance(exc, SessionDetached):
            recovery = ("codex-worker session resume --session %s" % shlex.quote(record.session_id)
                        if record else None)
            fault = _fault(
                -32003, "session is detached", "session_detached", recovery=recovery)
            return (fault if record is None
                    else self._with_record_identity(fault, record, turn_id))
        if isinstance(exc, WaitTimeout):
            session_id = record.session_id if record else exc.session_id
            next_actions = [
                "codex-worker turn status --session %s" % shlex.quote(session_id),
                "codex-worker turn wait --session %s --timeout 30" % shlex.quote(session_id),
                "codex-worker turn interrupt --session %s" % shlex.quote(session_id),
            ]
            fault = _fault(
                -32006, "timed out waiting for turn; work remains active", "wait_timeout",
                recovery="codex-worker turn status --session %s" % shlex.quote(session_id),
                details={
                    "session_id": exc.session_id,
                    "turn_id": exc.turn_id,
                    "active": True,
                    "next_actions": next_actions,
                },
            )
            return (fault if record is None else self._with_record_identity(
                fault, record, exc.turn_id))
        if isinstance(exc, NoTurn):
            fault = _fault(-32007, "session has no terminal turn", "no_turn")
            return (fault if record is None
                    else self._with_record_identity(fault, record, turn_id))
        if isinstance(exc, (UnknownSession, ValueError)):
            fault = _fault(-32602, str(exc), "invalid_params")
            return (fault if record is None
                    else self._with_record_identity(fault, record, turn_id))
        fault = _fault(-32020, "broker operation failed", "broker_error",
                       details={"reason": str(exc)})
        return (fault if record is None
                else self._with_record_identity(fault, record, turn_id))


class MaintenanceCoordinator:
    """The only composition path from a drained gate to owned termination."""

    def __init__(self, broker: WorkerBroker, lifecycle: MaintenanceLifecycle):
        if not isinstance(broker, WorkerBroker):
            raise TypeError("broker must be WorkerBroker")
        gate = lifecycle.gate
        if not isinstance(gate, ServiceMaintenanceGate):
            raise TypeError("lifecycle gate must be ServiceMaintenanceGate")
        if broker._gate is not gate:
            raise ValueError("broker and lifecycle must share the exact maintenance gate")
        if not callable(getattr(lifecycle, "terminate_owned", None)):
            raise TypeError("lifecycle must terminate owned resources")
        self._broker = broker
        self._lifecycle = lifecycle
        self._gate = gate

    def stop(self, force: bool) -> MaintenanceResult:
        return self._maintain("stop", None, force)

    def restart(self, listener: str, force: bool) -> MaintenanceResult:
        validated = validate_public_listener(listener)
        return self._maintain("restart", validated, force)

    def _maintain(self, action: str, listener: Optional[str],
                  force: bool) -> MaintenanceResult:
        if type(force) is not bool:
            raise ValueError("force must be bool")
        with self._gate.drain() as lease:
            inventory = self._broker.list_active_threads()
            from .models import WorkerImpact
            records = self._broker.registry.list()
            all_names = {record.name for record in records if record.name is not None}
            active_names = {item.worker for item in inventory.items
                            if item.worker is not None}
            workers = WorkerImpact(sorted(active_names), sorted(all_names - active_names))
            if inventory.items and not force:
                return MaintenanceResult.refused(
                    inventory, action, listener, workers)
            self._lifecycle.terminate_owned(lease)
            return MaintenanceResult.completed(
                action, inventory, force, listener, workers)
