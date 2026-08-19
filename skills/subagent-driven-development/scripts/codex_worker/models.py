"""Python 3.9-compatible wire and domain models."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import re

JsonObject = Dict[str, Any]
_WORKER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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

    @property
    def common_policy_complete(self) -> bool:
        return all(value is not None for value in (self.name, self.tier, self.model, self.effort, self.access))

    def to_dict(self) -> JsonObject:
        return {"session_id": self.session_id, "thread_id": self.thread_id, "cwd": self.cwd,
                "created_at": self.created_at, "updated_at": self.updated_at,
                "name": self.name, "model": self.model, "effort": self.effort,
                "tier": self.tier, "access": self.access}

    @classmethod
    def from_dict(cls, value: JsonObject):
        v1_fields = {"session_id", "thread_id", "cwd", "created_at", "updated_at", "name", "model", "effort"}
        required = v1_fields | {"tier", "access"}
        if not isinstance(value, dict) or set(value) not in (v1_fields, required):
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
        copied = dict(value)
        copied.setdefault("tier", None)
        copied.setdefault("access", None)
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
