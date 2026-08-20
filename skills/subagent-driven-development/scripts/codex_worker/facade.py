"""Transport-independent named-worker orchestration service."""
from dataclasses import dataclass
import shlex
from typing import Callable, Optional, Protocol, runtime_checkable

from .broker import (AnnotationPolicy, ModelSelectionError, NativeCodexProxy,
                     SessionStartSpec, TurnStartSpec)
from .commands import (AccessMode, CallbackCapture, CallbackState, CallbackStatusView,
                       CompletionResponse, ControlResponse, FacadeFault,
                       FacadeFaultCode, GoalResponse, GoalSetRequest, GoalShowRequest,
                       GoalView, InterruptWorkerRequest, LimitsRequest, LimitsResponse,
                       Ok, Err, RecoveryView, Result, RunWorkerRequest, StartWorkerRequest,
                       SteerWorkerRequest, Tier, TurnView, WorkerHistoryRequest,
                       WorkerHistoryResponse, WorkerMessagesRequest, WorkerMessagesResponse,
                       WorkerStatusRequest, WorkerStatusResponse, WorkerView,
                       FACADE_FAULT_KINDS)
from .instance import InstanceIdentity
from .models import IdentifierSelector, RpcFault, SessionRecord
from .registry import RegistryError
from .runtime import SessionDetached, UnknownSession, WaitTimeout
from .callback_store import CallbackBinding
from .callback_dispatcher import TerminalProjectionContext


_TIER_MODELS = {Tier.MEDIUM: "gpt-5.6-terra", Tier.VERY_SMART: "gpt-5.6-sol"}

@runtime_checkable
class RegistryPort(Protocol):
    def resolve_name(self, name: str) -> SessionRecord: ...

@runtime_checkable
class BrokerPort(Protocol):
    codex: object
    def model_list(self) -> dict: ...
    def start_session(self, spec: SessionStartSpec) -> dict: ...
    def start_turn(self, spec: TurnStartSpec) -> dict: ...
    def session_resume(self, selector: IdentifierSelector) -> dict: ...
    def daemon_status(self) -> dict: ...
    def turn_steer(self, selector: IdentifierSelector, prompt: str,
                   expected_turn_id: Optional[str] = None) -> dict: ...
    def turn_interrupt(self, selector: IdentifierSelector,
                       expected_turn_id: Optional[str] = None) -> dict: ...

@runtime_checkable
class RuntimePort(Protocol):
    def status(self, session_id: str): ...
    def wait(self, session_id: str, timeout: Optional[float]): ...
    def agent_messages(self, session_id: str, tail: int): ...

@runtime_checkable
class ProjectorPort(Protocol):
    def project_completion(self, worker, turn, output_schema, duration_seconds, recovery): ...
    def project_history_turn(self, turn: dict): ...
    def chronological_history_pages(self, pages): ...
    def select_completion_messages(self, items, terminal: bool): ...

@runtime_checkable
class CallbackStorePort(Protocol):
    def bind(self, binding: CallbackBinding) -> CallbackBinding: ...
    def binding(self, session_id: str) -> Optional[CallbackBinding]: ...
    def status_view(self, session_id: str) -> CallbackStatusView: ...

@runtime_checkable
class CallbackDispatcherPort(Protocol):
    def now(self) -> str: ...
    def observe_turn(self, session_id: str, turn_id: str,
                     context: TerminalProjectionContext) -> None: ...

@runtime_checkable
class CallbackTransportPort(Protocol):
    def validate_capture(self, capture: CallbackCapture) -> CallbackCapture: ...


@dataclass(frozen=True)
class FacadeDeps:
    instance: InstanceIdentity
    registry: RegistryPort
    broker: BrokerPort
    runtime: RuntimePort
    projector: ProjectorPort
    clock: Callable[[], float]
    callback_store: Optional[CallbackStorePort] = None
    callback_dispatcher: Optional[CallbackDispatcherPort] = None
    callback_transport: Optional[CallbackTransportPort] = None


class WorkerFacade:
    def __init__(self, deps: FacadeDeps):
        self.deps = deps

    def start(self, request: StartWorkerRequest) -> Result[CompletionResponse, FacadeFault]:
        record = None
        try:
            try:
                existing = self.deps.registry.resolve_name(request.name)
            except RegistryError as exc:
                if str(exc) != "unknown worker name":
                    return Err(self._registry_fault(exc, request.name))
                existing = None
            if existing is not None:
                return Err(self._exists_fault(existing))
            model = self._select_model(request)
            capture = request.callback_capture
            if not request.no_callback and capture is not None and self.deps.callback_transport is not None:
                capture = self.deps.callback_transport.validate_capture(capture)
            self.deps.broker.start_session(SessionStartSpec(
                request.cwd, request.name, model, request.access,
                request.tier.value if request.tier else None, request.effort,
                AnnotationPolicy.PRESERVE_WORKER_POLICY))
            record = self.deps.registry.resolve_name(request.name)
            worker = self._worker(record)
            self._bind_callback(record, request.no_callback, capture)
            if request.goal is not None:
                try:
                    NativeCodexProxy(self.deps.broker.codex).goal_set(
                        record.thread_id, request.goal, "active", request.token_budget)
                except BaseException as exc:
                    return Err(self._effect_fault(exc, record, request.name))
            return self._start_and_wait(record, worker, request.prompt, request.output_schema,
                                        request.timeout)
        except BaseException as exc:
            return Err(self._effect_fault(exc, record, request.name))

    def run(self, request: RunWorkerRequest) -> Result[CompletionResponse, FacadeFault]:
        record = None
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault):
                return Err(record)
            try:
                attached = self.deps.runtime.status(record.session_id).attached
            except (UnknownSession, SessionDetached):
                attached = False
            if not attached:
                self.deps.broker.session_resume(IdentifierSelector(session_id=record.session_id))
            return self._start_and_wait(record, self._worker(record), request.prompt,
                                        request.output_schema, request.timeout)
        except BaseException as exc:
            return Err(self._effect_fault(exc, record, request.name))

    def status(self, request: WorkerStatusRequest) -> Result[WorkerStatusResponse, FacadeFault]:
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault): return Err(record)
            status = self.deps.runtime.status(record.session_id)
            if not status.attached:
                return Err(self._stopped_fault(request.name, record))
            callback = None
            if (self.deps.callback_store is not None
                    and self.deps.callback_store.binding(record.session_id) is not None):
                callback = self.deps.callback_store.status_view(record.session_id)
            response = WorkerStatusResponse(self._worker(record), "ready", status.attached,
                                            status.active_turn_id, self._turn_view(status.latest_turn))
            if callback is not None:
                response = WorkerStatusResponse(response.worker, response.daemon_status,
                                                response.attached, response.active_turn_id,
                                                response.latest_turn, callback)
            return Ok(response)
        except (UnknownSession, SessionDetached):
            return Err(self._stopped_fault(request.name, None))
        except BaseException as exc:
            return Err(self._effect_fault(exc, None, request.name))

    def messages(self, request: WorkerMessagesRequest) -> Result[WorkerMessagesResponse, FacadeFault]:
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault): return Err(record)
            if not self.deps.runtime.status(record.session_id).attached:
                return Err(self._stopped_fault(request.name, record))
            items, truncated, cursor = self.deps.runtime.agent_messages(record.session_id, request.tail)
            messages = self.deps.projector.select_completion_messages(items, False)
            return Ok(WorkerMessagesResponse(self._worker(record), messages, request.tail,
                                             len(messages), truncated, cursor))
        except (UnknownSession, SessionDetached):
            return Err(self._stopped_fault(request.name, None))
        except BaseException as exc:
            return Err(self._effect_fault(exc, None, request.name))

    def history(self, request: WorkerHistoryRequest) -> Result[WorkerHistoryResponse, FacadeFault]:
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault): return Err(record)
            stopped = self._attached_fault(record, request.name)
            if stopped: return Err(stopped)
            proxy = NativeCodexProxy(self.deps.broker.codex)
            pages, cursor = [], None
            while len([turn for page in pages for turn in page]) < request.tail:
                page = proxy.turns_list(record.thread_id, cursor, request.tail)
                if cursor is not None and page["nextCursor"] == cursor:
                    raise FacadeFault(FacadeFaultCode.CODEX_PROTOCOL_ERROR,
                                      "Codex history pagination did not progress",
                                      "codex_protocol_error")
                pages.append(page["turns"])
                cursor = page["nextCursor"]
                if cursor is None: break
            chronological = self.deps.projector.chronological_history_pages(pages)
            chronological = chronological[-request.tail:]
            turns = [self.deps.projector.project_history_turn(turn) for turn in chronological]
            return Ok(WorkerHistoryResponse(self._worker(record), turns, request.tail,
                                            len(turns), cursor is not None))
        except BaseException as exc:
            return Err(self._effect_fault(exc, None, request.name))

    def steer(self, request: SteerWorkerRequest) -> Result[ControlResponse, FacadeFault]:
        return self._control(request, "steer")

    def interrupt(self, request: InterruptWorkerRequest) -> Result[ControlResponse, FacadeFault]:
        return self._control(request, "interrupt")

    def goal_set(self, request: GoalSetRequest) -> Result[GoalResponse, FacadeFault]:
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault): return Err(record)
            stopped = self._attached_fault(record, request.name)
            if stopped: return Err(stopped)
            result = NativeCodexProxy(self.deps.broker.codex).goal_set(
                record.thread_id, request.objective, request.status, request.token_budget)
            return Ok(GoalResponse(self._worker(record), "present", self._goal(result["goal"])))
        except BaseException as exc:
            return Err(self._effect_fault(exc, None, request.name))

    def goal_show(self, request: GoalShowRequest) -> Result[GoalResponse, FacadeFault]:
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault): return Err(record)
            stopped = self._attached_fault(record, request.name)
            if stopped: return Err(stopped)
            goal = NativeCodexProxy(self.deps.broker.codex).goal_get(record.thread_id)["goal"]
            return Ok(GoalResponse(self._worker(record), "present" if goal else "absent",
                                   self._goal(goal) if goal else None))
        except BaseException as exc:
            return Err(self._effect_fault(exc, None, request.name))

    def limits(self, request: LimitsRequest) -> Result[LimitsResponse, FacadeFault]:
        try:
            if not self.deps.broker.daemon_status()["ready"]:
                return Err(self._stopped_fault(None, None))
            return Ok(LimitsResponse("available", NativeCodexProxy(self.deps.broker.codex).rate_limits_read()["rateLimits"]))
        except BaseException as exc:
            return Err(self._effect_fault(exc, None, None, limits=True))

    def _start_and_wait(self, record, worker, prompt, schema, timeout):
        started = self.deps.clock()
        result = self.deps.broker.start_turn(TurnStartSpec(record.session_id, prompt, record.model,
                                                           record.effort, AccessMode(record.access), schema))
        turn_id = result["turn_id"]
        if self.deps.callback_dispatcher is not None:
            context = TerminalProjectionContext(worker, schema, started, self._recovery(record))
            try:
                self.deps.callback_dispatcher.observe_turn(record.session_id, turn_id, context)
            except Exception:
                # Automatic callbacks are a durable side channel, never terminal truth.
                pass
        try:
            turn = self._wait(record.session_id, timeout)
        except WaitTimeout as exc:
            return Err(self._timeout_fault(record, exc.turn_id))
        return Ok(self.deps.projector.project_completion(worker, turn, schema,
                                                          self.deps.clock() - started,
                                                          self._recovery(record)))

    def _bind_callback(self, record, disabled, capture) -> None:
        if self.deps.callback_store is None:
            return
        if disabled:
            state = CallbackState.DISABLED
            route = (None, None, None, None, None, None)
        elif capture is None:
            state = CallbackState.UNAVAILABLE
            route = (None, None, None, None, None, None)
        elif capture.target_socket is None:
            state = CallbackState.UNAVAILABLE
            route = (None, None, None, None, None, capture.claude_config_dir)
        else:
            state = CallbackState.ENABLED
            route = (capture.target_socket, capture.child_token, capture.claude_session_id,
                     capture.claude_pid, capture.claude_proc_start, capture.claude_config_dir)
        now = (self.deps.callback_dispatcher.now()
               if self.deps.callback_dispatcher is not None else "1970-01-01T00:00:00Z")
        self.deps.callback_store.bind(CallbackBinding(record.session_id, state, *route, now))

    def _wait(self, session_id, timeout):
        return self.deps.runtime.wait(session_id, timeout)

    def _select_model(self, request):
        model = request.model if request.model is not None else _TIER_MODELS[request.tier]
        models = self.deps.broker.model_list()["models"]
        found = next((item for item in models if item["id"] == model), None)
        if found is None:
            raise FacadeFault(FacadeFaultCode.MODEL_UNAVAILABLE, "Requested model is unavailable",
                              "model_unavailable", details={"model": model, "models": models})
        if request.effort not in found["supported_efforts"]:
            supported = found["supported_efforts"]
            details = {"model": model, "supported_efforts": supported}
            if request.output_schema is not None:
                details["schema_retry"] = {
                    "required_option": "--output-schema",
                    "source": "caller's original file",
                    "guidance": "Retry with the original --output-schema file and one of supported_efforts",
                }
            raise FacadeFault(FacadeFaultCode.EFFORT_UNSUPPORTED, "Requested effort is unsupported",
                              "effort_unsupported",
                              details=details,
                              known_ids=self._known(name=request.name),
                              next_actions=self._corrected_start_actions(request, supported))
        return model

    def _corrected_start_actions(self, request, supported_efforts):
        if not supported_efforts or request.output_schema is not None:
            return []
        args = [
            "start", "--name", shlex.quote(request.name),
            "--prompt", shlex.quote(request.prompt),
            "--cwd", shlex.quote(request.cwd),
        ]
        if request.model is not None:
            args.extend(("--model", shlex.quote(request.model)))
        else:
            args.extend(("--tier", request.tier.value))
        args.extend(("--effort", shlex.quote(supported_efforts[0])))
        if request.access == AccessMode.READ_ONLY:
            args.append("--read-only")
        if request.goal is not None:
            args.extend(("--goal", shlex.quote(request.goal)))
        if request.token_budget is not None:
            args.extend(("--token-budget", str(request.token_budget)))
        if request.timeout is not None:
            args.extend(("--timeout", str(request.timeout)))
        return [{
            "command": self._command(" ".join(args)),
            "reason": "Retry with provider-supported effort %s; no fallback has run" % supported_efforts[0],
        }]

    def _resolve_policy(self, name):
        try: record = self.deps.registry.resolve_name(name)
        except RegistryError as exc:
            if str(exc) == "unknown worker name": return self._not_found_fault(name)
            return self._registry_fault(exc, name)
        if not record.common_policy_complete:
            return self._legacy_fault(record)
        return record

    def _control(self, request, action):
        record = None
        try:
            record = self._resolve_policy(request.name)
            if isinstance(record, FacadeFault): return Err(record)
            status = self.deps.runtime.status(record.session_id)
            if not status.attached: return Err(self._stopped_fault(request.name, record))
            turn_id = status.active_turn_id
            if turn_id is None:
                return Err(self._turn_not_active(record, None))
            method = self.deps.broker.turn_steer if action == "steer" else self.deps.broker.turn_interrupt
            result = (method(IdentifierSelector(session_id=record.session_id), request.prompt,
                             expected_turn_id=turn_id)
                      if action == "steer"
                      else method(IdentifierSelector(session_id=record.session_id),
                                  expected_turn_id=turn_id))
            return Ok(ControlResponse(self._worker(record), action, result["accepted"],
                                      result["turn_id"],
                                      "interrupted" if action == "interrupt" else "in_progress"))
        except BaseException as exc:
            return Err(self._effect_fault(exc, record, request.name))

    def _worker(self, record: SessionRecord) -> WorkerView:
        return WorkerView(self.deps.instance.value, record.name, record.session_id, record.thread_id,
                          record.cwd, Tier(record.tier) if record.tier else None, record.model,
                          record.effort, AccessMode(record.access))

    def _attached_fault(self, record, name):
        try:
            if not self.deps.runtime.status(record.session_id).attached:
                return self._stopped_fault(name, record)
        except (UnknownSession, SessionDetached):
            return self._stopped_fault(name, record)
        return None

    @staticmethod
    def _turn_view(turn):
        return None if turn is None else TurnView(turn.turn_id, turn.status, turn.error.to_dict() if turn.error else None)

    @staticmethod
    def _goal(goal):
        return GoalView(goal["threadId"], goal["objective"], goal["status"], goal["tokenBudget"],
                        goal["tokensUsed"], goal["timeUsedSeconds"], goal["createdAt"], goal["updatedAt"])

    def _recovery(self, record):
        name = record.name
        return RecoveryView(self._command("status --name %s" % name),
                            self._command("messages --name %s" % name),
                            self._command("interrupt --name %s" % name),
                            self._raw_resume_command(record.thread_id))

    def _command(self, suffix):
        return "codex-worker --instance %s %s" % (shlex.quote(self.deps.instance.value), suffix)

    def _raw_resume_command(self, thread_id):
        return self._command("session resume --thread %s" % shlex.quote(thread_id))

    def _raw_resume_action(self, thread_id):
        return {"command": self._raw_resume_command(thread_id),
                "reason": "Recover through the advanced raw session path"}

    def _not_found_fault(self, name):
        return FacadeFault(FacadeFaultCode.WORKER_NOT_FOUND, "Worker not found", "worker_not_found",
                           known_ids=self._known(name=name), next_actions=[{
                               "command": self._command("start --name %s" % name),
                               "reason": "Create this worker in the selected instance"}])

    def _known(self, record=None, name=None, turn_id=None):
        return {"instance": self.deps.instance.value, "name": name or (record.name if record else None),
                "session_id": record.session_id if record else None,
                "thread_id": record.thread_id if record else None, "turn_id": turn_id}

    def _exists_fault(self, record):
        if not record.common_policy_complete:
            actions = self._legacy_actions(record)
        else:
            actions = [
                {"command": self._command("run --name %s" % record.name), "reason": "Continue the existing worker"},
                {"command": self._command("start --name <different-name>"), "reason": "Create an independent worker"}]
        return FacadeFault(FacadeFaultCode.WORKER_NAME_EXISTS, "Worker name already exists", "worker_name_exists",
                           known_ids=self._known(record), next_actions=actions)

    def _legacy_actions(self, record):
        return [self._raw_resume_action(record.thread_id),
                {"command": self._command("turn start --session %s --prompt <text>" % record.session_id),
                 "reason": "Use the advanced raw turn path without inventing policy"},
                {"command": self._command("start --name <different-name>"),
                 "reason": "Create a common worker with explicit policy"}]

    def _legacy_fault(self, record):
        return FacadeFault(FacadeFaultCode.REGISTRY_ERROR, "Worker policy is incomplete in legacy state", "registry_error",
                           details={"policy_state": "incomplete_legacy"}, known_ids=self._known(record),
                           next_actions=self._legacy_actions(record))

    def _registry_fault(self, exc, name, record=None):
        return FacadeFault(FacadeFaultCode.REGISTRY_ERROR, "Could not read worker registry", "registry_error",
                           details={"reason": str(exc)}, known_ids=self._known(record, name=name))

    def _timeout_fault(self, record, turn_id):
        return FacadeFault(FacadeFaultCode.TIMEOUT_ACTIVE, "Timed out while worker turn remains active", "timeout_active",
                           retryable=True, known_ids=self._known(record, turn_id=turn_id), next_actions=[
                               {"command": self._command("status --name %s" % record.name), "reason": "Inspect active work"},
                               {"command": self._command("messages --name %s" % record.name), "reason": "Read retained narration"},
                               {"command": self._command("interrupt --name %s" % record.name), "reason": "Cancel only if deliberate"}])

    def _stopped_fault(self, name, record):
        if name is None:
            return FacadeFault(FacadeFaultCode.DAEMON_STOPPED, "Worker daemon is stopped", "daemon_stopped",
                               known_ids=self._known(), next_actions=[
                                   {"command": self._command("daemon status"),
                                    "reason": "Inspect the selected instance"},
                                   {"command": self._command("start --name <name> --prompt <text>"),
                                    "reason": "Start a named worker to launch the selected instance"}])
        return FacadeFault(FacadeFaultCode.DAEMON_STOPPED, "Worker daemon is stopped", "daemon_stopped",
                           known_ids=self._known(record, name), next_actions=[
                               {"command": self._command("run --name %s --prompt <text>" % name), "reason": "Resume deliberately"}])

    def _turn_not_active(self, record, turn_id):
        return FacadeFault(FacadeFaultCode.TURN_NOT_ACTIVE, "Turn is not active", "turn_not_active",
                           known_ids=self._known(record, turn_id=turn_id), next_actions=[
                               {"command": self._command("status --name %s" % record.name), "reason": "Inspect the latest turn"}])

    def _active_turn_actions(self, name):
        return [
            {"command": self._command("status --name %s" % name),
             "reason": "Inspect the active turn"},
            {"command": self._command("messages --name %s" % name),
             "reason": "Read retained narration"},
            {"command": self._command("steer --name %s --prompt <text>" % name),
             "reason": "Append an instruction to the active turn"},
            {"command": self._command("interrupt --name %s" % name),
             "reason": "Cancel only if deliberate"},
        ]

    def _effect_fault(self, exc, record, name, limits=False):
        if isinstance(exc, FacadeFault): return exc
        if isinstance(exc, WaitTimeout): return self._timeout_fault(record, exc.turn_id)
        if isinstance(exc, ModelSelectionError):
            details = exc.details or {}
            code = (FacadeFaultCode.EFFORT_UNSUPPORTED
                    if "effort" in details or "supported_efforts" in details
                    else FacadeFaultCode.MODEL_UNAVAILABLE)
            return FacadeFault(
                code,
                "Requested effort is unsupported" if code == FacadeFaultCode.EFFORT_UNSUPPORTED
                else "Requested model is unavailable",
                self._kind(code), details=details, known_ids=self._known(record, name),
                next_actions=[{
                    "command": self._command("model list"),
                    "reason": "Inspect the current live model catalog; no fallback has run",
                }],
            )
        if isinstance(exc, RpcFault):
            try: code = FacadeFaultCode(exc.code)
            except ValueError:
                code = FacadeFaultCode.DAEMON_STOPPED if exc.kind == "session_detached" else FacadeFaultCode.CODEX_FAILURE
            known = self._known(record, name)
            if isinstance(exc.details, dict):
                for key in ("session_id", "thread_id", "turn_id"):
                    if isinstance(exc.details.get(key), str):
                        known[key] = exc.details[key]
            if code == FacadeFaultCode.TURN_ACTIVE:
                if known["turn_id"] is None and record is not None:
                    try:
                        known["turn_id"] = self.deps.runtime.status(record.session_id).active_turn_id
                    except (UnknownSession, SessionDetached):
                        pass
                next_actions = self._active_turn_actions(known["name"])
                return FacadeFault(code, exc.message, self._kind(code), details=exc.details or {},
                                   known_ids=known, next_actions=next_actions)
            next_actions = []
            if isinstance(known["thread_id"], str):
                next_actions.append(self._raw_resume_action(known["thread_id"]))
            return FacadeFault(code, exc.message, self._kind(code), details=exc.details or {},
                               known_ids=known, next_actions=next_actions)
        if isinstance(exc, (RegistryError, OSError)): return self._registry_fault(exc, name, record)
        code = FacadeFaultCode.LIMITS_UNAVAILABLE if limits else FacadeFaultCode.CODEX_FAILURE
        details = {"reason": str(exc)}
        if limits:
            details.update({"capacity": "unknown", "inference": "do_not_infer"})
        return FacadeFault(code, "Codex operation failed" if not limits else "Codex limits are unavailable",
                           self._kind(code), details=details, known_ids=self._known(record, name))

    @staticmethod
    def _kind(code):
        return FACADE_FAULT_KINDS[code]
