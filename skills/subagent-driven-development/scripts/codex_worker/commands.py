"""Strict dependency-free domain models for the named worker façade."""
from dataclasses import dataclass, fields
from enum import Enum
import math
from pathlib import Path
import re
import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, get_args, get_origin, get_type_hints

JsonObject = Dict[str, Any]
JsonValue = Any
WORKER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class Tier(str, Enum):
    MEDIUM = "medium"
    VERY_SMART = "very-smart"


class AccessMode(str, Enum):
    FULL = "full"
    READ_ONLY = "read_only"


class InstanceSource(str, Enum):
    FLAG = "flag"
    ENVIRONMENT = "environment"
    CLAUDE_SESSION = "claude_session"
    DEFAULT = "default"


class CompletionSelection(str, Enum):
    EXPLICIT_FINAL = "explicit_final"
    TERMINAL_FALLBACK = "terminal_fallback"
    LIVE = "live"


class MetricAvailability(str, Enum):
    MEASURED = "measured"
    REPORTED = "reported"
    DERIVED = "derived"
    UNAVAILABLE = "unavailable"


class FacadeFaultCode(int, Enum):
    INVALID_PARAMS = -32602
    TURN_NOT_ACTIVE = -32005
    REGISTRY_ERROR = -32011
    CODEX_PROTOCOL_ERROR = -32015
    CODEX_FAILURE = -32020
    WORKER_NAME_EXISTS = -32021
    WORKER_NOT_FOUND = -32022
    DAEMON_STOPPED = -32023
    DAEMON_START_FAILED = -32024
    TIMEOUT_ACTIVE = -32025
    MODEL_UNAVAILABLE = -32026
    EFFORT_UNSUPPORTED = -32027
    LIMITS_UNAVAILABLE = -32028
    INCOMPLETE_COMPLETION = -32029
    DAEMON_STOP_FAILED = -32030


FACADE_FAULT_KINDS = {
    FacadeFaultCode.INVALID_PARAMS: "invalid_params",
    FacadeFaultCode.TURN_NOT_ACTIVE: "turn_not_active",
    FacadeFaultCode.REGISTRY_ERROR: "registry_error",
    FacadeFaultCode.CODEX_PROTOCOL_ERROR: "codex_protocol_error",
    FacadeFaultCode.CODEX_FAILURE: "codex_failure",
    FacadeFaultCode.WORKER_NAME_EXISTS: "worker_name_exists",
    FacadeFaultCode.WORKER_NOT_FOUND: "worker_not_found",
    FacadeFaultCode.DAEMON_STOPPED: "daemon_stopped",
    FacadeFaultCode.DAEMON_START_FAILED: "daemon_start_failed",
    FacadeFaultCode.TIMEOUT_ACTIVE: "timeout_active",
    FacadeFaultCode.MODEL_UNAVAILABLE: "model_unavailable",
    FacadeFaultCode.EFFORT_UNSUPPORTED: "effort_unsupported",
    FacadeFaultCode.LIMITS_UNAVAILABLE: "limits_unavailable",
    FacadeFaultCode.INCOMPLETE_COMPLETION: "incomplete_completion",
    FacadeFaultCode.DAEMON_STOP_FAILED: "daemon_stop_failed",
}


def validate_worker_name(value: str) -> None:
    if not isinstance(value, str) or not WORKER_NAME_RE.fullmatch(value):
        raise ValueError("name must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def validate_prompt(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("prompt must be a non-empty string")


def validate_canonical_cwd(value: str) -> None:
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise ValueError("cwd must be an absolute existing directory")
    try:
        resolved = Path(value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("cwd must be an absolute existing directory") from exc
    if not resolved.is_dir():
        raise ValueError("cwd must be a canonical existing directory")


def _enum(value: Any, enum: Type[Enum], field_name: str) -> None:
    if not isinstance(value, enum):
        raise ValueError("%s must be a %s" % (field_name, enum.__name__))


class StrictModel:
    """Frozen dataclass serialization with an explicit no-extra-fields seam."""
    def to_dict(self) -> JsonObject:
        return {item.name: _dump(getattr(self, item.name)) for item in fields(self)}

    def __post_init__(self) -> None:
        hints = get_type_hints(type(self))
        for item in fields(self):
            _check_value(getattr(self, item.name), hints[item.name], item.name)
        _check_literals(self)
        _check_contract(self)

    @classmethod
    def from_dict(cls, value: JsonObject):
        if not isinstance(value, dict) or set(value) != {item.name for item in fields(cls)}:
            raise ValueError("invalid %s fields" % cls.__name__)
        hints = get_type_hints(cls)
        return cls(**{item.name: _load(value[item.name], hints[item.name], item.name) for item in fields(cls)})


def _json(value: Any, field_name: str) -> None:
    if value is None or type(value) in (str, int, float, bool):
        return
    if isinstance(value, list):
        for item in value: _json(item, field_name)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values(): _json(item, field_name)
        return
    raise ValueError("%s must be JSON-compatible" % field_name)


def _check_value(value: Any, annotation: Any, field_name: str) -> None:
    origin = get_origin(annotation)
    if annotation is Any:
        _json(value, field_name); return
    if origin is Union:
        if value is None and type(None) in get_args(annotation): return
        for candidate in get_args(annotation):
            if candidate is type(None): continue
            try: _check_value(value, candidate, field_name); return
            except ValueError: pass
        raise ValueError("invalid %s" % field_name)
    if origin in (list, List):
        if not isinstance(value, list): raise ValueError("%s must be a list" % field_name)
        for item in value: _check_value(item, get_args(annotation)[0], field_name)
        return
    if origin in (dict, Dict):
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value): raise ValueError("%s must be an object" % field_name)
        for item in value.values(): _check_value(item, get_args(annotation)[1], field_name)
        return
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        if not isinstance(value, annotation): raise ValueError("invalid %s" % field_name)
        return
    if isinstance(annotation, type) and issubclass(annotation, StrictModel):
        if not isinstance(value, annotation): raise ValueError("invalid %s" % field_name)
        return
    if annotation in (str, int, bool, float) and (type(value) is not annotation): raise ValueError("invalid %s" % field_name)


def _load(value: Any, annotation: Any, field_name: str) -> Any:
    origin = get_origin(annotation)
    if annotation is Any:
        _json(value, field_name); return value
    if origin is Union:
        if value is None and type(None) in get_args(annotation): return None
        for candidate in get_args(annotation):
            if candidate is type(None): continue
            try: return _load(value, candidate, field_name)
            except (ValueError, TypeError): pass
        raise ValueError("invalid %s" % field_name)
    if origin in (list, List):
        if not isinstance(value, list): raise ValueError("%s must be a list" % field_name)
        return [_load(item, get_args(annotation)[0], field_name) for item in value]
    if origin in (dict, Dict):
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value): raise ValueError("%s must be an object" % field_name)
        return {key: _load(item, get_args(annotation)[1], field_name) for key, item in value.items()}
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        try: return annotation(value)
        except (TypeError, ValueError) as exc: raise ValueError("invalid %s" % field_name) from exc
    if isinstance(annotation, type) and issubclass(annotation, StrictModel):
        return annotation.from_dict(value)
    _check_value(value, annotation, field_name); return value


_LITERALS = {
    "TurnView": {"status": {"in_progress", "completed", "failed", "interrupted"}},
    "AgentMessageView": {"type": {"agent_message"}, "phase": {"commentary", "final_answer", None}},
    "WorkerStatusResponse": {"daemon_status": {"ready"}},
    "ControlResponse": {"action": {"steer", "interrupt"}, "status": {"in_progress", "interrupted"}},
    "GoalView": {"status": {"active", "paused", "blocked", "usageLimited", "budgetLimited", "complete"}},
    "GoalResponse": {"availability": {"present", "absent"}},
    "LimitsResponse": {"availability": {"available"}},
    "DaemonStatusResponse": {"status": {"stopped", "starting", "ready", "stopping", "failed"}},
    "DaemonStopResponse": {"status_before": {"stopped", "starting", "ready", "stopping", "failed"}, "status_after": {"stopped"}, "durable_state": {"preserved"}},
}


def _check_literals(value: Any) -> None:
    for field_name, choices in _LITERALS.get(type(value).__name__, {}).items():
        if getattr(value, field_name) not in choices: raise ValueError("invalid %s" % field_name)


def _check_contract(value: Any) -> None:
    name = type(value).__name__
    if name == "MetricEvidence" and not value.source: raise ValueError("metric source must be non-empty")
    if name == "RecoveryView" and not all((value.status, value.messages, value.interrupt)): raise ValueError("recovery commands must be non-empty")
    if name in {"WorkerMessagesResponse", "WorkerHistoryResponse"}:
        _positive(value.requested_tail, "requested_tail")
        if type(value.returned) is not int or value.returned < 0: raise ValueError("returned must be non-negative")
    if name == "WorkerMessagesResponse" and value.latest_cursor is not None and (type(value.latest_cursor) is not int or value.latest_cursor < 0): raise ValueError("latest_cursor must be non-negative")
    if name == "ControlResponse" and value.accepted is not True: raise ValueError("accepted must be true")
    if name == "GoalView":
        if not value.thread_id or not value.objective: raise ValueError("goal identity fields must be non-empty")
        if value.token_budget is not None: _positive(value.token_budget, "token_budget")
        if any(type(item) is not int or item < 0 for item in (
            value.tokens_used, value.time_used_seconds, value.created_at, value.updated_at
        )): raise ValueError("goal usage and timestamps must be non-negative")
    if name == "GoalResponse" and ((value.availability == "present") != (value.goal is not None)): raise ValueError("goal availability does not match goal")
    if name == "InstanceView":
        if not value.instance: raise ValueError("instance must be non-empty")
        for field_name in ("durable_dir", "socket_path", "log_path"):
            path = getattr(value, field_name)
            if not Path(path).is_absolute(): raise ValueError("%s must be absolute" % field_name)
    if name in {"DaemonStatusResponse", "DaemonStopResponse"}:
        if type(value.worker_count) is not int or value.worker_count < 0: raise ValueError("worker_count must be non-negative")
        for pid in (value.daemon_pid, value.codex_pid):
            if pid is not None and (type(pid) is not int or pid <= 0): raise ValueError("pid must be positive")


def _dump(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, StrictModel):
        return value.to_dict()
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class StartWorkerRequest(StrictModel):
    name: str
    prompt: str
    cwd: str
    tier: Optional[Tier] = Tier.MEDIUM
    model: Optional[str] = None
    effort: str = "medium"
    access: AccessMode = AccessMode.FULL
    goal: Optional[str] = None
    token_budget: Optional[int] = None
    output_schema: Optional[JsonObject] = None
    timeout: Optional[float] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_worker_name(self.name); validate_prompt(self.prompt); validate_canonical_cwd(self.cwd)
        if self.tier is not None: _enum(self.tier, Tier, "tier")
        if self.model is not None and (not isinstance(self.model, str) or not self.model): raise ValueError("model must be a non-empty string")
        if (self.tier is None) == (self.model is None): raise ValueError("exactly one of tier or model is required")
        if not isinstance(self.effort, str) or not self.effort: raise ValueError("effort must be a non-empty string")
        _enum(self.access, AccessMode, "access")
        if self.goal is not None and (not isinstance(self.goal, str) or not self.goal or len(self.goal) > 4000): raise ValueError("goal must be a non-empty string of at most 4000 characters")
        if self.token_budget is not None and (type(self.token_budget) is not int or self.token_budget <= 0): raise ValueError("token_budget must be a positive integer")
        if self.token_budget is not None and self.goal is None: raise ValueError("--token-budget requires --goal")
        _validate_turn_options(self.output_schema, self.timeout)

    @classmethod
    def from_dict(cls, value: JsonObject):
        if not isinstance(value, dict) or set(value) != {item.name for item in fields(cls)}:
            raise ValueError("invalid StartWorkerRequest fields")
        copied = dict(value)
        if copied["tier"] is not None:
            copied["tier"] = Tier(copied["tier"])
        copied["access"] = AccessMode(copied["access"])
        return cls(**copied)


@dataclass(frozen=True)
class RunWorkerRequest(StrictModel):
    name: str; prompt: str; output_schema: Optional[JsonObject] = None; timeout: Optional[float] = None
    def __post_init__(self) -> None: super().__post_init__(); validate_worker_name(self.name); validate_prompt(self.prompt); _validate_turn_options(self.output_schema, self.timeout)


@dataclass(frozen=True)
class WorkerStatusRequest(StrictModel):
    name: str
    def __post_init__(self) -> None: super().__post_init__(); validate_worker_name(self.name)


@dataclass(frozen=True)
class WorkerMessagesRequest(WorkerStatusRequest):
    tail: int = 1
    def __post_init__(self) -> None: super().__post_init__(); _positive(self.tail, "tail")


@dataclass(frozen=True)
class WorkerHistoryRequest(WorkerMessagesRequest):
    pass


@dataclass(frozen=True)
class SteerWorkerRequest(WorkerStatusRequest):
    prompt: str = ""
    def __post_init__(self) -> None: super().__post_init__(); validate_prompt(self.prompt)


@dataclass(frozen=True)
class InterruptWorkerRequest(WorkerStatusRequest):
    pass


@dataclass(frozen=True)
class GoalSetRequest(WorkerStatusRequest):
    objective: Optional[str] = None; status: Optional[str] = None; token_budget: Optional[int] = None
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.objective is None and self.status is None and self.token_budget is None: raise ValueError("goal set requires at least one change")
        if self.objective is not None and (not isinstance(self.objective, str) or not self.objective or len(self.objective) > 4000): raise ValueError("objective must be a non-empty string of at most 4000 characters")
        if self.status is not None and self.status not in {"active", "paused", "blocked", "usageLimited", "budgetLimited", "complete"}: raise ValueError("invalid goal status")
        if self.token_budget is not None: _positive(self.token_budget, "token_budget")


@dataclass(frozen=True)
class GoalShowRequest(WorkerStatusRequest): pass
@dataclass(frozen=True)
class LimitsRequest(StrictModel): pass
@dataclass(frozen=True)
class DaemonStatusRequest(StrictModel): pass
@dataclass(frozen=True)
class DaemonStopRequest(StrictModel): pass


def _positive(value: Any, name: str) -> None:
    if type(value) is not int or value <= 0: raise ValueError("%s must be a positive integer" % name)


def _validate_turn_options(schema: Optional[JsonObject], timeout: Optional[float]) -> None:
    if schema is not None and not isinstance(schema, dict): raise ValueError("output_schema must be an object")
    if timeout is not None and (not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout < 0): raise ValueError("timeout must be finite and non-negative")


@dataclass(frozen=True)
class WorkerView(StrictModel):
    instance: str; name: str; session_id: str; thread_id: str; cwd: str; tier: Optional[Tier]; model: str; effort: str; access: AccessMode
    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.instance or not self.session_id or not self.thread_id or not self.model or not self.effort:
            raise ValueError("worker identity and configuration strings must be non-empty")
        try:
            uuid.UUID(self.session_id)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("session_id must be a UUID") from exc
        validate_worker_name(self.name)
        validate_canonical_cwd(self.cwd)
@dataclass(frozen=True)
class TurnView(StrictModel): turn_id: str; status: str; error: Optional[JsonObject]
@dataclass(frozen=True)
class AgentMessageView(StrictModel): type: str; item_id: str; phase: Optional[str]; selection: CompletionSelection; text: str
@dataclass(frozen=True)
class MetricEvidence(StrictModel): value: JsonValue; source: str; availability: MetricAvailability
@dataclass(frozen=True)
class RecoveryView(StrictModel): status: str; messages: str; interrupt: str; raw_resume: Optional[str] = None
@dataclass(frozen=True)
class CompletionResponse(StrictModel): worker: WorkerView; turn: TurnView; messages: List[AgentMessageView]; structured_output: JsonValue; metrics: Dict[str, MetricEvidence]; recovery: RecoveryView
@dataclass(frozen=True)
class WorkerStatusResponse(StrictModel): worker: WorkerView; daemon_status: str; attached: bool; active_turn_id: Optional[str]; latest_turn: Optional[TurnView]
@dataclass(frozen=True)
class WorkerMessagesResponse(StrictModel): worker: WorkerView; messages: List[AgentMessageView]; requested_tail: int; returned: int; truncated: bool; latest_cursor: Optional[int]
@dataclass(frozen=True)
class HistoryTurnView(StrictModel): turn_id: str; status: str; started_at: Optional[int]; completed_at: Optional[int]; messages: List[AgentMessageView]; error: Optional[JsonObject]
@dataclass(frozen=True)
class WorkerHistoryResponse(StrictModel): worker: WorkerView; turns: List[HistoryTurnView]; requested_tail: int; returned: int; older_available: bool
@dataclass(frozen=True)
class ControlResponse(StrictModel): worker: WorkerView; action: str; accepted: bool; turn_id: str; status: str
@dataclass(frozen=True)
class GoalView(StrictModel): thread_id: str; objective: str; status: str; token_budget: Optional[int]; tokens_used: int; time_used_seconds: int; created_at: int; updated_at: int
@dataclass(frozen=True)
class GoalResponse(StrictModel): worker: WorkerView; availability: str; goal: Optional[GoalView]
@dataclass(frozen=True)
class LimitsResponse(StrictModel): availability: str; rate_limits: JsonObject
@dataclass(frozen=True)
class InstanceView(StrictModel): instance: str; source: InstanceSource; durable_dir: str; socket_path: str; log_path: str
@dataclass(frozen=True)
class DaemonStatusResponse(StrictModel): instance: InstanceView; status: str; daemon_pid: Optional[int]; codex_pid: Optional[int]; worker_count: int; readiness: Optional[JsonObject]; last_error: Optional[JsonObject]
@dataclass(frozen=True)
class DaemonStopResponse(StrictModel): instance: InstanceView; status_before: str; status_after: str; daemon_pid: Optional[int]; codex_pid: Optional[int]; durable_state: str; worker_count: int


# Internal service Result carriers; RPC uses the explicit façade and raw wire envelopes above.
T = TypeVar("T"); E = TypeVar("E")
@dataclass(frozen=True)
class Ok(Generic[T]): value: T
@dataclass(frozen=True)
class Err(Generic[E]): error: E
Result = Union[Ok[T], Err[E]]


@dataclass(frozen=True)
class FacadeFault(Exception):
    code: int; message: str; kind: str; retryable: bool = False; source: str = "codex-worker"; details: JsonObject = None; known_ids: JsonObject = None; next_actions: List[JsonObject] = None
    def __post_init__(self) -> None:
        details = {} if self.details is None else self.details
        known_ids = {"instance": None, "name": None, "session_id": None, "thread_id": None, "turn_id": None} if self.known_ids is None else self.known_ids
        next_actions = [] if self.next_actions is None else self.next_actions
        try:
            code = FacadeFaultCode(self.code)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid façade fault code") from exc
        if not isinstance(self.message, str) or not self.message or not isinstance(self.kind, str) or not self.kind:
            raise ValueError("fault message and kind must be non-empty strings")
        if self.kind != FACADE_FAULT_KINDS[code]:
            raise ValueError("fault code and kind do not match")
        if type(self.retryable) is not bool or not isinstance(self.source, str) or not self.source:
            raise ValueError("invalid façade fault metadata")
        if not isinstance(details, dict): raise ValueError("details must be an object")
        _json(details, "details")
        if not isinstance(known_ids, dict): raise ValueError("known_ids must be an object")
        required_ids = {"instance", "name", "session_id", "thread_id", "turn_id"}
        if set(known_ids) != required_ids or any(value is not None and not isinstance(value, str) for value in known_ids.values()):
            raise ValueError("invalid known_ids")
        if not isinstance(next_actions, list): raise ValueError("next_actions must be a list")
        for action in next_actions:
            if not isinstance(action, dict) or set(action) != {"command", "reason"} or not all(isinstance(value, str) and value for value in action.values()):
                raise ValueError("invalid next action")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "details", dict(details))
        object.__setattr__(self, "known_ids", dict(known_ids))
        object.__setattr__(self, "next_actions", list(next_actions)); Exception.__init__(self, self.message)
    def to_dict(self) -> JsonObject:
        return {"code": self.code.value, "message": self.message, "data": {"kind": self.kind, "retryable": self.retryable, "source": self.source, "details": self.details, "known_ids": self.known_ids, "next_actions": self.next_actions}}
    @classmethod
    def from_dict(cls, value: JsonObject):
        if not isinstance(value, dict) or set(value) != {"code", "message", "data"} or not isinstance(value.get("data"), dict):
            raise ValueError("invalid façade fault envelope")
        data = value["data"]
        required = {"kind", "retryable", "source", "details", "known_ids", "next_actions"}
        if set(data) != required: raise ValueError("invalid façade fault data")
        return cls(value["code"], value["message"], data["kind"], data["retryable"], data["source"], data["details"], data["known_ids"], data["next_actions"])
    @classmethod
    def worker_not_found(cls, name: str, instance: str):
        validate_worker_name(name)
        return cls(FacadeFaultCode.WORKER_NOT_FOUND, "Worker not found", "worker_not_found", known_ids={"instance": instance, "name": name, "session_id": None, "thread_id": None, "turn_id": None}, next_actions=[{"command": "codex-worker start --name %s" % name, "reason": "Create this worker in the selected instance"}])
