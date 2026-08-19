"""Strict dependency-free domain models for the named worker façade."""
from dataclasses import dataclass, fields
from enum import Enum
import math
from pathlib import Path
import re
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

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
    WORKER_NAME_EXISTS = -32021
    WORKER_NOT_FOUND = -32022
    DAEMON_STOPPED = -32023
    DAEMON_START_FAILED = -32024
    TIMEOUT_ACTIVE = -32025
    MODEL_UNAVAILABLE = -32026
    EFFORT_UNSUPPORTED = -32027
    LIMITS_UNAVAILABLE = -32028
    INCOMPLETE_COMPLETION = -32029


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

    @classmethod
    def from_dict(cls, value: JsonObject):
        if not isinstance(value, dict) or set(value) != {item.name for item in fields(cls)}:
            raise ValueError("invalid %s fields" % cls.__name__)
        return cls(**value)


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
        validate_worker_name(self.name); validate_prompt(self.prompt); validate_canonical_cwd(self.cwd)
        if self.tier is not None: _enum(self.tier, Tier, "tier")
        if self.model is not None and (not isinstance(self.model, str) or not self.model): raise ValueError("model must be a non-empty string")
        if self.model is not None and self.tier is not None: raise ValueError("--tier and --model are mutually exclusive")
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
    def __post_init__(self) -> None: validate_worker_name(self.name); validate_prompt(self.prompt); _validate_turn_options(self.output_schema, self.timeout)


@dataclass(frozen=True)
class WorkerStatusRequest(StrictModel):
    name: str
    def __post_init__(self) -> None: validate_worker_name(self.name)


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
class HistoryTurnView(StrictModel): turn_id: str; status: str; started_at: Optional[str]; completed_at: Optional[str]; messages: List[AgentMessageView]; error: Optional[JsonObject]
@dataclass(frozen=True)
class WorkerHistoryResponse(StrictModel): worker: WorkerView; turns: List[HistoryTurnView]; requested_tail: int; returned: int; older_available: bool
@dataclass(frozen=True)
class ControlResponse(StrictModel): worker: WorkerView; action: str; accepted: bool; turn_id: str; status: str
@dataclass(frozen=True)
class GoalView(StrictModel): thread_id: str; objective: str; status: str; token_budget: Optional[int]; tokens_used: int; time_used_seconds: int; created_at: str; updated_at: str
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
        object.__setattr__(self, "details", {} if self.details is None else dict(self.details))
        object.__setattr__(self, "known_ids", {"instance": None, "name": None, "session_id": None, "thread_id": None, "turn_id": None} if self.known_ids is None else dict(self.known_ids))
        object.__setattr__(self, "next_actions", [] if self.next_actions is None else list(self.next_actions)); Exception.__init__(self, self.message)
    def to_dict(self) -> JsonObject:
        return {"code": self.code, "message": self.message, "data": {"kind": self.kind, "retryable": self.retryable, "source": self.source, "details": self.details, "known_ids": self.known_ids, "next_actions": self.next_actions}}
    @classmethod
    def worker_not_found(cls, name: str, instance: str):
        validate_worker_name(name)
        return cls(FacadeFaultCode.WORKER_NOT_FOUND, "Worker not found", "worker_not_found", known_ids={"instance": instance, "name": name, "session_id": None, "thread_id": None, "turn_id": None}, next_actions=[{"command": "codex-worker start --name %s" % name, "reason": "Create this worker in the selected instance"}])
