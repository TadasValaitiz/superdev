"""Dependency-free callback value objects shared by projection and persistence."""
import json
from dataclasses import dataclass
from typing import Any, Dict

from .commands import WorkerView


def _nonempty(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("%s must be a non-empty string" % name)


@dataclass(frozen=True)
class CallbackEvent:
    schema: str
    event: str
    event_id: str
    emitted_at: str
    priority: str
    worker: WorkerView
    payload: Dict[str, Any]

    def __post_init__(self) -> None:
        if self.schema != "codex-worker.claude-callback/v1":
            raise ValueError("unsupported callback schema")
        if self.event not in {"turn_terminal", "turn_terminal_reference", "worker_message"}:
            raise ValueError("unsupported callback event")
        _nonempty(self.event_id, "event_id"); _nonempty(self.emitted_at, "emitted_at")
        if self.priority not in {"now", "next", "later"}:
            raise ValueError("unsupported callback priority")
        if not isinstance(self.worker, WorkerView) or not isinstance(self.payload, dict):
            raise ValueError("invalid callback event")
        try:
            json.dumps(self.payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must be JSON-compatible") from exc
