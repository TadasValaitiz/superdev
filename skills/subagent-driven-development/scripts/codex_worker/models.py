"""Python 3.9-compatible wire and domain models."""
import copy
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

JsonObject = Dict[str, Any]
_WORKER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_ACTIVE_ORIGINS = frozenset(("worker", "unmapped_tui"))


def _validate_config_value(value: Any) -> None:
    if type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            _validate_config_value(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) and key for key in value):
        for item in value.values():
            _validate_config_value(item)
        return
    raise ValueError("config values must be finite JSON values without null")


def validate_thread_config(config: Optional[JsonObject]) -> None:
    """Validate creation-time Codex config overrides (dotted keys, like ``codex -c``)."""
    if config is None:
        return
    if not isinstance(config, dict) or not config:
        raise ValueError("config must be null or a non-empty object")
    for key, value in config.items():
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError("config keys must be non-empty strings without surrounding whitespace")
        _validate_config_value(value)


def _validate_recovery_command(command: str) -> None:
    if (not isinstance(command, str) or not command.strip()
            or "<" in command or ">" in command
            or not command.startswith(("codex-worker ", "codex "))):
        raise ValueError("recovery action must be a literal public command")


@dataclass(frozen=True)
class IdentifierSelector:
    session_id: Optional[str] = None
    thread_id: Optional[str] = None

    def __post_init__(self) -> None:
        if (self.session_id is None) == (self.thread_id is None):
            raise ValueError("exactly one of session_id or thread_id is required")

    @property
    def kind(self) -> str:
        return "session" if self.session_id is not None else "thread"


@dataclass(frozen=True)
class ErrorDetail:
    kind: str
    recovery: Optional[str] = None
    details: Optional[JsonObject] = None

    def __post_init__(self) -> None:
        if self.recovery is not None:
            _validate_recovery_command(self.recovery)
        if self.details is not None and "next_actions" in self.details:
            actions = self.details["next_actions"]
            if (not isinstance(actions, list)
                    or any(not isinstance(action, str) for action in actions)):
                raise ValueError("next_actions must contain literal public commands")
            for action in actions:
                _validate_recovery_command(action)

    def to_dict(self) -> JsonObject:
        result = {"kind": self.kind}
        if self.recovery is not None:
            result["recovery"] = self.recovery
        if self.details is not None:
            result["details"] = dict(self.details)
        return result

    @classmethod
    def from_dict(cls, value: JsonObject):
        if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
            raise ValueError("invalid error detail")
        if value.get("recovery") is not None and not isinstance(value.get("recovery"), str):
            raise ValueError("invalid error recovery")
        if value.get("details") is not None and not isinstance(value.get("details"), dict):
            raise ValueError("invalid error details")
        return cls(value["kind"], value.get("recovery"), value.get("details"))


@dataclass(frozen=True)
class ItemRecord:
    item_id: str
    type: str
    data: JsonObject

    def to_dict(self) -> JsonObject:
        return {"item_id": self.item_id, "type": self.type, "data": dict(self.data)}

    @classmethod
    def from_dict(cls, value: JsonObject):
        if (not isinstance(value, dict) or not isinstance(value.get("item_id"), str)
                or not isinstance(value.get("type"), str) or not isinstance(value.get("data"), dict)):
            raise ValueError("invalid item record")
        return cls(value["item_id"], value["type"], value["data"])


@dataclass(frozen=True)
class TurnSnapshot:
    turn_id: str
    status: str
    error: Optional[ErrorDetail] = None
    items: List[ItemRecord] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return {"turn_id": self.turn_id, "status": self.status,
                "error": self.error.to_dict() if self.error else None,
                "items": [item.to_dict() for item in self.items]}


def copy_turn_snapshot(snapshot: TurnSnapshot) -> TurnSnapshot:
    """Return a recursively isolated snapshot at an in-process boundary."""
    if not isinstance(snapshot, TurnSnapshot):
        raise ValueError("invalid turn snapshot")
    error = (None if snapshot.error is None
             else ErrorDetail.from_dict(copy.deepcopy(snapshot.error.to_dict())))
    items = [ItemRecord.from_dict(copy.deepcopy(item.to_dict()))
             for item in snapshot.items]
    return TurnSnapshot(snapshot.turn_id, snapshot.status, error, items)


@dataclass(frozen=True)
class EventRecord:
    cursor: int
    event: str
    session_id: str
    thread_id: str
    turn_id: Optional[str] = None
    item: Optional[ItemRecord] = None
    error: Optional[ErrorDetail] = None

    def to_dict(self) -> JsonObject:
        return {"cursor": self.cursor, "event": self.event, "session_id": self.session_id,
                "thread_id": self.thread_id, "turn_id": self.turn_id,
                "item": self.item.to_dict() if self.item else None,
                "error": self.error.to_dict() if self.error else None}


@dataclass(frozen=True)
class EventPage:
    events: List[EventRecord]
    next_cursor: int
    truncated: bool = False

    def to_dict(self) -> JsonObject:
        return {"events": [event.to_dict() for event in self.events],
                "next_cursor": self.next_cursor, "truncated": self.truncated}


@dataclass(frozen=True)
class RuntimeStatus:
    attached: bool = False
    active_turn_id: Optional[str] = None
    latest_turn: Optional[TurnSnapshot] = None

    def to_dict(self) -> JsonObject:
        return {"attached": self.attached, "active_turn_id": self.active_turn_id,
                "latest_turn": self.latest_turn.to_dict() if self.latest_turn else None}


@dataclass(frozen=True)
class ActiveThreadItem:
    """One authoritative active app-server thread and its optional worker mapping."""

    thread_id: str
    origin: str
    worker: Optional[str]
    session_id: Optional[str]
    turn_id: str
    active_flags: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.thread_id, str) or not self.thread_id:
            raise ValueError("active thread_id must be non-empty")
        if self.origin not in _ACTIVE_ORIGINS:
            raise ValueError("active origin is invalid")
        if (self.worker is not None
                and (not isinstance(self.worker, str)
                     or not _WORKER_NAME_RE.fullmatch(self.worker))):
            raise ValueError("active worker must be non-empty when present")
        if self.session_id is not None and (not isinstance(self.session_id, str)
                                             or not self.session_id):
            raise ValueError("active session_id must be non-empty when present")
        if not isinstance(self.turn_id, str) or not self.turn_id:
            raise ValueError("active turn_id must be non-empty")
        if (not isinstance(self.active_flags, (list, tuple))
                or any(not isinstance(value, str) or not value
                       for value in self.active_flags)):
            raise ValueError("active flags must be non-empty strings")
        if self.origin == "unmapped_tui" and (
                self.worker is not None or self.session_id is not None):
            raise ValueError("unmapped TUI activity cannot carry worker identity")
        if self.origin == "worker" and self.session_id is None:
            raise ValueError("worker activity requires session identity")
        object.__setattr__(self, "active_flags", tuple(self.active_flags))

    def to_dict(self) -> JsonObject:
        return {
            "thread_id": self.thread_id,
            "origin": self.origin,
            "worker": self.worker,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "active_flags": list(self.active_flags),
        }

    @classmethod
    def from_dict(cls, value: JsonObject):
        required = {"thread_id", "origin", "worker", "session_id", "turn_id",
                    "active_flags"}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("invalid ActiveThreadItem fields")
        return cls(value["thread_id"], value["origin"], value["worker"],
                   value["session_id"], value["turn_id"], value["active_flags"])


@dataclass(frozen=True)
class ActiveInventory:
    """Complete fail-closed active-thread inventory from all app-server sources."""

    items: Tuple[ActiveThreadItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if (not isinstance(self.items, (list, tuple))
                or any(not isinstance(item, ActiveThreadItem) for item in self.items)):
            raise ValueError("inventory items must be ActiveThreadItem values")
        identities = [item.thread_id for item in self.items]
        if len(set(identities)) != len(identities):
            raise ValueError("inventory thread IDs must be unique")
        object.__setattr__(self, "items", tuple(self.items))

    @property
    def active_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> JsonObject:
        return {"items": [item.to_dict() for item in self.items]}

    @classmethod
    def from_dict(cls, value: JsonObject):
        if not isinstance(value, dict) or set(value) != {"items"} or not isinstance(
                value["items"], list):
            raise ValueError("invalid ActiveInventory fields")
        return cls([ActiveThreadItem.from_dict(item) for item in value["items"]])


@dataclass(frozen=True)
class WorkerImpact:
    """Exact named-worker split captured before global maintenance."""

    active_names: Tuple[str, ...] = field(default_factory=tuple)
    idle_names: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for values in (self.active_names, self.idle_names):
            if (not isinstance(values, (list, tuple))
                    or any(not isinstance(value, str) or not value for value in values)):
                raise ValueError("worker impact names must be non-empty strings")
            if list(values) != sorted(set(values)):
                raise ValueError("worker impact names must be unique and sorted")
        if set(self.active_names) & set(self.idle_names):
            raise ValueError("active and idle worker names must be disjoint")
        object.__setattr__(self, "active_names", tuple(self.active_names))
        object.__setattr__(self, "idle_names", tuple(self.idle_names))

    def to_dict(self) -> JsonObject:
        return {"active_names": list(self.active_names),
                "idle_names": list(self.idle_names),
                "active_count": len(self.active_names),
                "idle_count": len(self.idle_names),
                "total_count": len(self.active_names) + len(self.idle_names)}

    @classmethod
    def from_dict(cls, value: JsonObject):
        required = {"active_names", "idle_names", "active_count", "idle_count",
                    "total_count"}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("invalid WorkerImpact fields")
        result = cls(value["active_names"], value["idle_names"])
        if result.to_dict() != value:
            raise ValueError("worker impact counts do not match names")
        return result


@dataclass(frozen=True)
class MaintenanceResult:
    """Internal lifecycle result retaining the exact pre-termination impact."""

    action: str
    status: str
    forced: bool
    listener: Optional[str]
    inventory: Optional[ActiveInventory]
    workers: Optional[WorkerImpact] = field(default_factory=WorkerImpact)
    durable_state: str = "preserved"
    impact_unavailable_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.action not in ("stop", "restart"):
            raise ValueError("maintenance action is invalid")
        if self.status not in ("refused", "completed"):
            raise ValueError("maintenance status is invalid")
        if type(self.forced) is not bool:
            raise ValueError("maintenance forced must be bool")
        if self.listener is not None and (not isinstance(self.listener, str)
                                          or not self.listener):
            raise ValueError("maintenance listener must be non-empty when present")
        if (self.action == "stop") != (self.listener is None):
            raise ValueError("only restart maintenance carries a listener")
        if self.listener is not None:
            from .service_domain import validate_public_listener
            validate_public_listener(self.listener)
        impact_available = self.impact_unavailable_reason is None
        if impact_available:
            if not isinstance(self.inventory, ActiveInventory):
                raise ValueError("maintenance inventory must be ActiveInventory")
            if not isinstance(self.workers, WorkerImpact):
                raise ValueError("maintenance workers must be WorkerImpact")
        else:
            if self.impact_unavailable_reason != "upstream_inventory_unavailable":
                raise ValueError("maintenance impact unavailable reason is invalid")
            if self.inventory is not None or self.workers is not None:
                raise ValueError("unavailable maintenance impact cannot carry inventory")
            if self.status == "completed" and not self.forced:
                raise ValueError("unavailable maintenance completion must be forced")
        if self.status == "refused":
            if self.forced:
                raise ValueError("maintenance refusal cannot be forced")
            if impact_available and not self.inventory.items:
                raise ValueError("maintenance refusal requires active or unavailable impact")
        if (self.status == "completed" and impact_available
                and self.inventory.items and not self.forced):
            raise ValueError("active maintenance completion must be forced")
        if self.durable_state != "preserved":
            raise ValueError("maintenance must preserve durable state")

    @classmethod
    def refused(cls, inventory: ActiveInventory, action: str = "stop",
                listener: Optional[str] = None, workers: Optional[WorkerImpact] = None):
        return cls(action, "refused", False, listener, inventory,
                   workers or WorkerImpact())

    @classmethod
    def completed(cls, action: str, inventory: ActiveInventory, forced: bool,
                  listener: Optional[str] = None,
                  workers: Optional[WorkerImpact] = None):
        return cls(action, "completed", forced, listener, inventory,
                   workers or WorkerImpact())

    @classmethod
    def unavailable(cls, action: str, status: str, forced: bool,
                    listener: Optional[str], reason: str):
        return cls(action, status, forced, listener, None, None,
                   "preserved", reason)

    def to_dict(self) -> JsonObject:
        return {
            "action": self.action,
            "status": self.status,
            "forced": self.forced,
            "listener": self.listener,
            "inventory": (self.inventory.to_dict() if self.inventory is not None else {
                "availability": "unavailable",
                "reason": self.impact_unavailable_reason,
            }),
            "workers": (self.workers.to_dict() if self.workers is not None else {
                "availability": "unavailable",
                "reason": self.impact_unavailable_reason,
            }),
            "durable_state": self.durable_state,
        }

    @classmethod
    def from_dict(cls, value: JsonObject):
        required = {"action", "status", "forced", "listener", "inventory", "workers",
                    "durable_state"}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("invalid MaintenanceResult fields")
        if value["durable_state"] != "preserved":
            raise ValueError("maintenance must preserve durable state")
        unavailable = {
            "availability": "unavailable",
            "reason": "upstream_inventory_unavailable",
        }
        if value["inventory"] == unavailable or value["workers"] == unavailable:
            if value["inventory"] != unavailable or value["workers"] != unavailable:
                raise ValueError("maintenance unavailable impact must be consistent")
            return cls.unavailable(
                value["action"], value["status"], value["forced"], value["listener"],
                "upstream_inventory_unavailable")
        return cls(value["action"], value["status"], value["forced"],
                   value["listener"], ActiveInventory.from_dict(value["inventory"]),
                   WorkerImpact.from_dict(value["workers"]), value["durable_state"])


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    thread_id: str
    cwd: str
    created_at: str
    updated_at: str
    name: Optional[str] = None
    model: Optional[str] = None
    effort: Optional[str] = None
    tier: Optional[str] = None
    access: Optional[str] = None
    config: Optional[JsonObject] = None

    @property
    def common_policy_complete(self) -> bool:
        return all(value is not None for value in (self.name, self.model, self.effort, self.access))

    def to_dict(self) -> JsonObject:
        return {"session_id": self.session_id, "thread_id": self.thread_id, "cwd": self.cwd,
                "created_at": self.created_at, "updated_at": self.updated_at,
                "name": self.name, "model": self.model, "effort": self.effort,
                "tier": self.tier, "access": self.access, "config": copy.deepcopy(self.config)}

    @classmethod
    def from_dict(cls, value: JsonObject):
        v1_fields = {"session_id", "thread_id", "cwd", "created_at", "updated_at", "name", "model", "effort"}
        v2_fields = v1_fields | {"tier", "access"}
        if not isinstance(value, dict) or set(value) not in (v1_fields, v2_fields, v2_fields | {"config"}):
            raise ValueError("invalid session record")
        strings = ("session_id", "thread_id", "cwd", "created_at", "updated_at")
        if any(not isinstance(value.get(key), str) for key in strings):
            raise ValueError("invalid session record field")
        if any(value.get(key) is not None and not isinstance(value.get(key), str) for key in ("name", "model", "effort", "tier", "access")):
            raise ValueError("invalid session annotation")
        if value.get("name") is not None and not _WORKER_NAME_RE.fullmatch(value["name"]):
            raise ValueError("invalid worker name")
        if value.get("tier") not in (None, "medium", "very-smart") or value.get("access") not in (None, "full", "read_only"):
            raise ValueError("invalid common policy")
        validate_thread_config(value.get("config"))
        copied = dict(value)
        copied.setdefault("tier", None)
        copied.setdefault("access", None)
        copied["config"] = copy.deepcopy(value.get("config"))
        return cls(**copied)


@dataclass(frozen=True)
class RpcFault(Exception):
    code: int
    message: str
    kind: str
    recovery: Optional[str] = None
    details: Optional[JsonObject] = None

    def __post_init__(self) -> None:
        # Broker/domain callers raise this value directly; keeping the wire
        # representation and the exception contract in one type prevents a
        # second, drifting hierarchy of RPC errors.
        Exception.__init__(self, self.message)
        ErrorDetail(self.kind, self.recovery, self.details)

    def to_dict(self) -> JsonObject:
        data = ErrorDetail(self.kind, self.recovery, self.details).to_dict()
        return {"code": self.code, "message": self.message, "data": data}


def rpc_response(request_id: Optional[Union[str, int]], result: Optional[JsonObject] = None,
                 fault: Optional[RpcFault] = None) -> JsonObject:
    if (result is None) == (fault is None):
        raise ValueError("exactly one of result or fault is required")
    response = {"jsonrpc": "2.0", "id": request_id}
    if fault is not None:
        response["error"] = fault.to_dict()
    else:
        response["result"] = dict(result)  # type: ignore[arg-type]
    return response


def session_result(record: SessionRecord, attached: bool) -> JsonObject:
    return {"session": record.to_dict(), "attached": attached}
