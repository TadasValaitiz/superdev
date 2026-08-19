import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import AccessMode, FacadeFault, FacadeFaultCode, Tier, WorkerView
from codex_worker.models import ItemRecord, TurnSnapshot
from codex_worker.projection import derive_metrics, project_completion, project_history_turn, select_completion_messages


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.worker = WorkerView("default", "worker", "00000000-0000-0000-0000-000000000001",
                                 "thread", str(ROOT), Tier.MEDIUM, "model", "medium", AccessMode.FULL)
    def test_terminal_fallback_and_live_messages_preserve_nullable_phase(self):
        items = [
            ItemRecord("a", "agentMessage", {"text": "work"}),
            ItemRecord("b", "agentMessage", {"text": "answer"}),
        ]
        selected = select_completion_messages(items, terminal=True)
        self.assertEqual([(x.item_id, x.selection.value) for x in selected],
                         [("b", "terminal_fallback")])
        self.assertEqual([x.selection.value for x in select_completion_messages(items, terminal=False)],
                         ["live", "live"])

    def test_terminal_completion_without_agent_message_is_typed_incomplete(self):
        with self.assertRaises(FacadeFault) as caught:
            project_completion(self.worker, TurnSnapshot("turn", "completed"), None, 1.0)
        self.assertEqual(caught.exception.code, FacadeFaultCode.INCOMPLETE_COMPLETION)
        self.assertEqual(caught.exception.kind, "incomplete_completion")

    def test_schema_decode_failure_retains_selected_message_for_diagnosis(self):
        turn = TurnSnapshot("turn", "completed", items=[ItemRecord("answer", "agentMessage", {"text": "nope", "phase": "final_answer"})])
        with self.assertRaises(FacadeFault) as caught:
            project_completion(self.worker, turn, {"type": "object"}, 1.0)
        self.assertEqual(caught.exception.details["turn_id"], "turn")
        self.assertEqual(caught.exception.details["messages"][0]["item_id"], "answer")
        self.assertEqual(caught.exception.details["parse_reason"], "invalid_json")

    def test_history_rejects_malformed_item_instead_of_dropping_it(self):
        with self.assertRaises(ValueError):
            project_history_turn({"id": "turn", "status": "completed", "items": [{"id": "bad"}]})

    def test_metrics_count_items_and_preserve_authoritative_duration_and_tokens(self):
        metrics = derive_metrics([
            ItemRecord("c", "commandExecution", {"durationMs": 25}),
            ItemRecord("a", "agentMessage", {"text": "ok", "tokenUsage": {"total": 3}}),
        ], 1.25)
        self.assertEqual(metrics["item_counts"].value, {"commandExecution": 1, "agentMessage": 1})
        self.assertEqual(metrics["command_duration_ms"].value, 25)
        self.assertEqual(metrics["token_usage"].availability.value, "reported")
