"""High-level durable session and turn contract for the Codex worker daemon."""
import os
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Tuple

from .app_server import CodexCallError
from .models import (
    IdentifierSelector,
    JsonObject,
    RpcFault,
    SessionRecord,
    session_result,
)
from .commands import AccessMode
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
        if (not all(isinstance(goal[key], str) and goal[key] for key in ("threadId", "objective", "createdAt", "updatedAt"))
                or goal["status"] not in ("active", "paused", "blocked", "usageLimited", "budgetLimited", "complete")
                or (goal["tokenBudget"] is not None and (type(goal["tokenBudget"]) is not int or goal["tokenBudget"] <= 0))
                or any(type(goal[key]) is not int or goal[key] < 0 for key in ("tokensUsed", "timeUsedSeconds"))):
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
        if set(result) != {"turns", "nextCursor"} or not isinstance(result["turns"], list) or result["nextCursor"] is not None and not isinstance(result["nextCursor"], str):
            self._protocol("thread/turns/list", "malformed turn page")
        from .projection import project_history_turn
        for turn in result["turns"]:
            try:
                project_history_turn(turn)
            except ValueError as exc:
                self._protocol("thread/turns/list", str(exc))
        return result
    def rate_limits_read(self) -> JsonObject:
        result = self._call("account/rateLimits/read", {})
        if set(result) != {"rateLimits"} or not isinstance(result["rateLimits"], dict):
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
                 socket_path: str, state_path: str, daemon_pid: Optional[int] = None):
        self.registry = registry
        self.codex = codex
        self.runtime = runtime
        self.socket_path = socket_path
        self.state_path = state_path
        self.daemon_pid = os.getpid() if daemon_pid is None else daemon_pid

    def daemon_status(self) -> JsonObject:
        proc = getattr(self.codex, "proc", None)
        poll = getattr(proc, "poll", None)
        ready = True
        if callable(poll):
            ready = poll() is None
        return {
            "ready": ready,
            "daemon_pid": self.daemon_pid,
            "codex_pid": getattr(proc, "pid", None),
            "socket_path": self.socket_path,
            "state_path": self.state_path,
            "session_count": len(self.registry.list()),
        }

    @staticmethod
    def _thread_sandbox(access: AccessMode) -> str:
        return "danger-full-access" if access == AccessMode.FULL else "read-only"

    @staticmethod
    def _turn_sandbox(access: AccessMode) -> JsonObject:
        return {"type": "dangerFullAccess"} if access == AccessMode.FULL else {"type": "readOnly", "networkAccess": False}

    def start_session(self, spec: SessionStartSpec) -> JsonObject:
        canonical_cwd = self._canonical_cwd(spec.cwd, "declared cwd")
        self._validate_model_effort(spec.model, None)
        session_id = str(uuid.uuid4())
        try:
            response = self.codex.start_thread(canonical_cwd, model=spec.model,
                                               sandbox=self._thread_sandbox(spec.access),
                                               allow_provider_model_fallback=False)
            thread_id, returned_cwd = self._resume_identity(response)
            if returned_cwd != canonical_cwd:
                raise _fault(-32014, "Codex returned a different working directory", "session_cwd_mismatch",
                             details={"expected_cwd": canonical_cwd, "returned_cwd": returned_cwd})
            record = self.registry.create(thread_id, canonical_cwd, spec.name, spec.model, None, session_id=session_id)
        except RpcFault:
            raise
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc
        except (RegistryError, OSError) as exc:
            raise self._post_upstream_registry_fault("session_start", session_id, thread_id, None, exc) from exc
        self.runtime.attach(record)
        return session_result(record, attached=True)

    def resume_session(self, spec: SessionResumeSpec) -> JsonObject:
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
        record = self._resolve(IdentifierSelector(session_id=spec.session_id), require_attached=True)
        if not isinstance(spec.prompt, str) or not spec.prompt:
            raise _fault(-32602, "prompt must be a non-empty string", "invalid_params")
        validation_model = spec.model if spec.model is not None or spec.effort is None else record.model
        effective_model = self._validate_model_effort(validation_model, spec.effort)
        upstream_model = effective_model if spec.effort is not None else spec.model
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
            raise self._from_lower(exc, record) from exc
        policy = AnnotationPolicy.PRESERVE_WORKER_POLICY if record.common_policy_complete else AnnotationPolicy.LEGACY_MUTABLE
        if policy == AnnotationPolicy.LEGACY_MUTABLE:
            annotation_model = effective_model if spec.effort is not None else spec.model or record.model
            annotation_effort = spec.effort or record.effort
            try:
                self.registry.update_annotations(record.session_id, model=annotation_model, effort=annotation_effort)
            except (RegistryError, OSError) as exc:
                raise self._post_upstream_registry_fault("turn_start_annotations", record.session_id, record.thread_id, turn_id, exc) from exc
        return {"session_id": record.session_id, "thread_id": record.thread_id, "turn_id": turn_id, "status": "in_progress"}

    def model_list(self) -> JsonObject:
        return {"models": self._models()}

    def session_start(self, cwd: str, name: Optional[str] = None,
                      model: Optional[str] = None) -> JsonObject:
        return self.start_session(SessionStartSpec(cwd, name, model))

    def session_resume(self, selector: IdentifierSelector,
                       name: Optional[str] = None) -> JsonObject:
        try:
            existing = self.registry.try_resolve(selector)
        except RegistryError as exc:
            raise _fault(-32011, "could not read session registry", "registry_error", details={"reason": str(exc)}) from exc
        if existing is not None:
            if name is not None:
                raise _fault(-32602, "--name is only valid for raw thread recovery", "invalid_params")
            try:
                response = self.resume_session(SessionResumeSpec(
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
                return session_result(existing, attached=True)
            except RpcFault:
                raise
            except (CodexCallError, CodexProtocolError) as exc:
                raise self._from_lower(exc) from exc

        if selector.thread_id is None:
            raise self._unknown_session(selector)
        session_id = str(uuid.uuid4())
        try:
            response = self.resume_session(SessionResumeSpec(selector.thread_id, AccessMode.FULL))
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
        except RpcFault:
            raise
        except (CodexCallError, CodexProtocolError) as exc:
            raise self._from_lower(exc) from exc
        except (RegistryError, OSError) as exc:
            raise self._post_upstream_registry_fault(
                "session_resume", session_id, selector.thread_id, None, exc,
            ) from exc
        self.runtime.attach(record)
        return session_result(record, attached=True)

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
        }

    def turn_start(self, selector: IdentifierSelector, prompt: str,
                   model: Optional[str] = None, effort: Optional[str] = None) -> JsonObject:
        record = self._resolve(selector, require_attached=True)
        return self.start_turn(TurnStartSpec(record.session_id, prompt, model, effort,
                                             AccessMode(record.access) if record.access else AccessMode.FULL))

    def turn_status(self, selector: IdentifierSelector) -> JsonObject:
        record = self._resolve(selector, require_attached=False)
        status = self._status_or_detached(record)
        return {
            "session_id": record.session_id, "thread_id": record.thread_id,
            "attached": status.attached, "active_turn_id": status.active_turn_id,
            "latest_turn": status.latest_turn.to_dict() if status.latest_turn else None,
        }

    def turn_wait(self, selector: IdentifierSelector, timeout: float) -> JsonObject:
        record = self._resolve(selector, require_attached=True)
        try:
            turn = self.runtime.wait(record.session_id, timeout)
            return {"session_id": record.session_id, "thread_id": record.thread_id, "turn": turn.to_dict()}
        except (WaitTimeout, NoTurn, SessionDetached, UnknownSession, ValueError) as exc:
            raise self._from_lower(exc, record) from exc

    def turn_events(self, selector: IdentifierSelector, after: int, limit: int) -> JsonObject:
        record = self._resolve(selector, require_attached=False)
        try:
            return self.runtime.events(record.session_id, after, limit).to_dict()
        except (UnknownSession, ValueError) as exc:
            raise self._from_lower(exc, record) from exc

    def turn_steer(self, selector: IdentifierSelector, prompt: str) -> JsonObject:
        if not isinstance(prompt, str) or not prompt:
            raise _fault(-32602, "prompt must be a non-empty string", "invalid_params")
        record = self._resolve(selector, require_attached=True)
        turn_id = self._active_turn_or_fault(record)
        try:
            returned_id = self.codex.steer(record.thread_id, turn_id, prompt)
        except CodexCallError as exc:
            self._raise_control_race_or_codex(record, turn_id, exc)
        if returned_id != turn_id:
            raise _fault(
                -32015, "Codex steer returned a different turn", "codex_protocol_error",
                details={"expected_turn_id": turn_id, "returned_turn_id": returned_id},
            )
        return {"session_id": record.session_id, "thread_id": record.thread_id,
                "turn_id": turn_id, "accepted": True}

    def turn_interrupt(self, selector: IdentifierSelector) -> JsonObject:
        record = self._resolve(selector, require_attached=True)
        turn_id = self._active_turn_or_fault(record)
        try:
            self.codex.interrupt(record.thread_id, turn_id)
        except CodexCallError as exc:
            self._raise_control_race_or_codex(record, turn_id, exc)
        return {"session_id": record.session_id, "thread_id": record.thread_id,
                "turn_id": turn_id, "accepted": True}

    def shutdown(self) -> JsonObject:
        try:
            self.codex.shutdown()
        except CodexCallError as exc:
            raise self._codex_fault(exc) from exc
        return {"accepted": True}

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
                    recovery="run session resume --session %s" % record.session_id,
                    details={"session_id": record.session_id, "thread_id": record.thread_id},
                )
        return record

    def _unknown_session(self, selector: IdentifierSelector) -> RpcFault:
        if selector.thread_id is not None:
            return _fault(
                -32001, "unknown raw thread; recover it with session resume --thread %s" % selector.thread_id,
                "unknown_session", recovery="run session resume --thread %s" % selector.thread_id,
                details={"thread_id": selector.thread_id},
            )
        return _fault(
            -32001, "unknown session", "unknown_session",
            recovery=(
                "run session list to choose a known session, or recover a raw Codex thread with "
                "session resume --thread <thread-id> --name <name>"
            ),
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

    def _active_turn_or_fault(self, record: SessionRecord) -> str:
        status = self._status_or_detached(record)
        if not status.attached:
            raise _fault(
                -32003, "session is detached", "session_detached",
                recovery="run session resume --session %s" % record.session_id,
            )
        if status.active_turn_id is None:
            latest_turn_id = status.latest_turn.turn_id if status.latest_turn else None
            raise self._turn_not_active(record, status.latest_turn, latest_turn_id)
        return status.active_turn_id

    def _raise_control_race_or_codex(self, record: SessionRecord, expected_turn_id: str,
                                     exc: CodexCallError) -> None:
        status = self._status_or_detached(record)
        if self._is_upstream_turn_not_active(exc):
            raise self._turn_not_active(record, status.latest_turn, expected_turn_id) from exc
        raise self._codex_fault(exc) from exc

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

    @staticmethod
    def _turn_not_active(record: SessionRecord, latest_turn: Any,
                         turn_id: Optional[str] = None) -> RpcFault:
        return _fault(
            -32005, "turn is not active", "turn_not_active",
            details={
                "session_id": record.session_id,
                "thread_id": record.thread_id,
                "turn_id": turn_id,
                "latest_turn": latest_turn.to_dict() if latest_turn else None,
            },
        )

    @staticmethod
    def _post_upstream_registry_fault(operation: str, session_id: str, thread_id: str,
                                      turn_id: Optional[str], exc: BaseException) -> RpcFault:
        details = {
            "operation": operation,
            "durable_state": "not_persisted",
            "session_id": session_id,
            "thread_id": thread_id,
            "reason": str(exc),
        }  # type: JsonObject
        if turn_id is None:
            recovery = "run session resume --thread %s" % thread_id
            message = "Codex thread exists but its session identity was not persisted"
        else:
            details["turn_id"] = turn_id
            recovery = (
                "inspect the upstream-started turn with turn status --session %s, "
                "then turn events --session %s" % (session_id, session_id)
            )
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

    def _from_lower(self, exc: BaseException, record: Optional[SessionRecord] = None) -> RpcFault:
        if isinstance(exc, CodexCallError):
            return self._codex_fault(exc)
        if isinstance(exc, CodexProtocolError):
            return _fault(-32015, "Codex protocol state is inconsistent", "codex_protocol_error",
                          details={"reason": str(exc)})
        if isinstance(exc, TurnActive):
            return _fault(-32004, "session already has an active turn", "turn_active",
                          details={"session_id": record.session_id if record else None})
        if isinstance(exc, SessionDetached):
            return _fault(-32003, "session is detached", "session_detached",
                          recovery="run session resume --session %s" % (record.session_id if record else "<id>"))
        if isinstance(exc, WaitTimeout):
            session_id = record.session_id if record else exc.session_id
            next_actions = [
                "turn status --session %s" % session_id,
                "turn wait --session %s --timeout <seconds>" % session_id,
                "turn steer --session %s --prompt <text>" % session_id,
                "turn interrupt --session %s" % session_id,
            ]
            return _fault(
                -32006, "timed out waiting for turn; work remains active", "wait_timeout",
                recovery="work remains active; run turn status/wait/steer/interrupt for session %s" % session_id,
                details={
                    "session_id": exc.session_id,
                    "turn_id": exc.turn_id,
                    "active": True,
                    "next_actions": next_actions,
                },
            )
        if isinstance(exc, NoTurn):
            return _fault(-32007, "session has no terminal turn", "no_turn",
                          details={"session_id": record.session_id if record else None})
        if isinstance(exc, (UnknownSession, ValueError)):
            return _fault(-32602, str(exc), "invalid_params")
        return _fault(-32020, "broker operation failed", "broker_error", details={"reason": str(exc)})
