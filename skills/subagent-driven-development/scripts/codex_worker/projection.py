"""Pure projections from Codex items to the public worker result models."""
import json
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

from .commands import (
    AgentMessageView, CompletionResponse, CompletionSelection, HistoryTurnView,
    MetricAvailability, MetricEvidence, RecoveryView, TurnView, WorkerView,
)
from .models import ItemRecord, TurnSnapshot


def agent_view(item: ItemRecord) -> AgentMessageView:
    data = item.data
    text = data.get("text")
    phase = data.get("phase")
    if not isinstance(text, str) or phase not in (None, "commentary", "final_answer"):
        raise ValueError("malformed Codex agent message")
    return AgentMessageView("agent_message", item.item_id, phase, CompletionSelection.LIVE, text)


def select_completion_messages(items: Sequence[ItemRecord], terminal: bool) -> List[AgentMessageView]:
    agents = [agent_view(item) for item in items if item.type == "agentMessage"]
    if not terminal:
        return [replace(item, selection=CompletionSelection.LIVE) for item in agents]
    finals = [item for item in agents if item.phase == "final_answer"]
    if finals:
        return [replace(item, selection=CompletionSelection.EXPLICIT_FINAL) for item in finals]
    return [replace(agents[-1], selection=CompletionSelection.TERMINAL_FALLBACK)] if agents else []


def derive_metrics(items: Sequence[ItemRecord], duration_seconds: float) -> Dict[str, MetricEvidence]:
    counts = {}  # type: Dict[str, int]
    commands = 0
    duration_ms = 0
    have_duration = False
    token_usage = None
    for item in items:
        counts[item.type] = counts.get(item.type, 0) + 1
        if item.type == "commandExecution":
            commands += 1
            value = item.data.get("durationMs")
            if type(value) is int and value >= 0:
                duration_ms += value
                have_duration = True
        if token_usage is None and isinstance(item.data.get("tokenUsage"), dict):
            token_usage = dict(item.data["tokenUsage"])
    metrics = {
        "wall_duration_seconds": MetricEvidence(duration_seconds, "codex-worker", MetricAvailability.MEASURED),
        "item_counts": MetricEvidence(counts, "codex-worker", MetricAvailability.DERIVED),
        "command_count": MetricEvidence(commands, "codex-worker", MetricAvailability.DERIVED),
        "command_duration_ms": MetricEvidence(duration_ms if have_duration else None, "codex", MetricAvailability.DERIVED if have_duration else MetricAvailability.UNAVAILABLE),
        "token_usage": MetricEvidence(token_usage, "codex", MetricAvailability.REPORTED if token_usage is not None else MetricAvailability.UNAVAILABLE),
    }
    return metrics


def project_completion(worker: WorkerView, turn: TurnSnapshot, output_schema: Optional[dict],
                       duration_seconds: float, recovery: Optional[RecoveryView] = None) -> CompletionResponse:
    terminal = turn.status != "in_progress"
    messages = select_completion_messages(turn.items, terminal)
    structured_output = None
    if output_schema is not None:
        if not messages:
            raise ValueError("incomplete completion: no agent message for schema output")
        try:
            structured_output = json.loads(messages[-1].text)
        except (TypeError, ValueError) as exc:
            raise ValueError("incomplete completion: schema output is not JSON") from exc
    error = turn.error.to_dict() if turn.error else None
    if recovery is None:
        recovery = RecoveryView("status", "messages", "interrupt")
    return CompletionResponse(worker, TurnView(turn.turn_id, turn.status, error), messages,
                              structured_output, derive_metrics(turn.items, duration_seconds), recovery)


def project_history_turn(turn: dict) -> HistoryTurnView:
    if not isinstance(turn, dict) or not isinstance(turn.get("id"), str) or not isinstance(turn.get("status"), str):
        raise ValueError("malformed Codex history turn")
    items = turn.get("items", [])
    if not isinstance(items, list):
        raise ValueError("malformed Codex history items")
    records = [ItemRecord(item["id"], item["type"], {k: v for k, v in item.items() if k not in ("id", "type")})
               for item in items if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("type"), str)]
    terminal = turn["status"] != "inProgress"
    status = "in_progress" if turn["status"] == "inProgress" else turn["status"]
    error = turn.get("error") if isinstance(turn.get("error"), dict) else None
    return HistoryTurnView(turn["id"], status, turn.get("startedAt"), turn.get("completedAt"),
                           select_completion_messages(records, terminal), error)
