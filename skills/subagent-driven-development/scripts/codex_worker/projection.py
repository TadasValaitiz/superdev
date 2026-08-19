"""Pure projections from Codex items to the public worker result models."""
import json
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

from .commands import (
    AgentMessageView, CompletionResponse, CompletionSelection, HistoryTurnView,
    FacadeFault, FacadeFaultCode, MetricAvailability, MetricEvidence, RecoveryView,
    TurnView, WorkerView,
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


def _incomplete(turn_id: str, messages: Sequence[AgentMessageView], reason: str) -> FacadeFault:
    return FacadeFault(FacadeFaultCode.INCOMPLETE_COMPLETION, "Codex completion is incomplete",
                       "incomplete_completion", details={
                           "turn_id": turn_id,
                           "messages": [message.to_dict() for message in messages],
                           "parse_reason": reason,
                       })


def project_completion(worker: WorkerView, turn: TurnSnapshot, output_schema: Optional[dict],
                       duration_seconds: float, recovery: Optional[RecoveryView] = None) -> CompletionResponse:
    terminal = turn.status != "in_progress"
    messages = select_completion_messages(turn.items, terminal)
    structured_output = None
    if turn.status == "completed" and not messages:
        raise _incomplete(turn.turn_id, messages, "no_agent_message")
    if output_schema is not None:
        if not messages:
            raise _incomplete(turn.turn_id, messages, "no_agent_message")
        try:
            structured_output = json.loads(messages[-1].text)
        except (TypeError, ValueError) as exc:
            raise _incomplete(turn.turn_id, messages, "invalid_json") from exc
    error = turn.error.to_dict() if turn.error else None
    if recovery is None:
        recovery = RecoveryView("status", "messages", "interrupt")
    return CompletionResponse(worker, TurnView(turn.turn_id, turn.status, error), messages,
                              structured_output, derive_metrics(turn.items, duration_seconds), recovery)


def project_history_turn(turn: dict) -> HistoryTurnView:
    if (not isinstance(turn, dict) or not isinstance(turn.get("id"), str)
            or turn.get("status") not in ("inProgress", "completed", "failed", "interrupted")):
        raise ValueError("malformed Codex history turn")
    items = turn.get("items", [])
    if not isinstance(items, list):
        raise ValueError("malformed Codex history items")
    records = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or not isinstance(item.get("type"), str) or not item["type"]:
            raise ValueError("malformed Codex history item")
        records.append(ItemRecord(item["id"], item["type"], {key: value for key, value in item.items() if key not in ("id", "type")}))
    for field in ("startedAt", "completedAt"):
        if (field in turn and turn[field] is not None
                and (type(turn[field]) is not int or turn[field] < 0)):
            raise ValueError("malformed Codex history timestamp")
    if turn.get("error") is not None and not isinstance(turn.get("error"), dict):
        raise ValueError("malformed Codex history error")
    terminal = turn["status"] != "inProgress"
    status = "in_progress" if turn["status"] == "inProgress" else turn["status"]
    error = turn.get("error") if isinstance(turn.get("error"), dict) else None
    return HistoryTurnView(turn["id"], status, turn.get("startedAt"), turn.get("completedAt"),
                           select_completion_messages(records, terminal), error)


def chronological_history_pages(pages: Sequence[Sequence[dict]]) -> List[dict]:
    """Reverse provider newest-first pages without interpreting their contents."""
    flattened = []
    for page in pages:
        flattened.extend(page)
    return list(reversed(flattened))
