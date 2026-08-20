import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import AccessMode, FacadeFault, FacadeFaultCode, Tier, WorkerView
from codex_worker.models import ItemRecord, TurnSnapshot
from codex_worker.projection import chronological_history_pages, derive_metrics, project_completion, project_history_turn, select_completion_messages


class ProjectionTests(unittest.TestCase):
    def test_projection_does_not_import_callback_persistence(self):
        source = (ROOT / "skills" / "subagent-driven-development" / "scripts" /
                  "codex_worker" / "projection.py").read_text(encoding="utf-8")
        self.assertNotIn("callback_store import", source)
        from codex_worker.callback_domain import CallbackEvent
        self.assertEqual(CallbackEvent.__module__, "codex_worker.callback_domain")

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

    def test_multiple_explicit_finals_are_retained_in_order(self):
        messages = select_completion_messages([
            ItemRecord("one", "agentMessage", {"text": "a", "phase": "final_answer"}),
            ItemRecord("two", "agentMessage", {"text": "b", "phase": "final_answer"}),
        ], True)
        self.assertEqual([message.item_id for message in messages], ["one", "two"])
        self.assertTrue(all(message.selection.value == "explicit_final" for message in messages))

    def test_missing_duration_and_token_usage_are_explicitly_unavailable(self):
        metrics = derive_metrics([ItemRecord("c", "commandExecution", {})], 1.0)
        self.assertEqual(metrics["command_count"].value, 1)
        self.assertIsNone(metrics["command_duration_ms"].value)
        self.assertEqual(metrics["command_duration_ms"].availability.value, "unavailable")
        self.assertIsNone(metrics["token_usage"].value)
        self.assertEqual(metrics["token_usage"].availability.value, "unavailable")

    def test_history_terminal_fallback_and_in_progress_live(self):
        terminal = project_history_turn({"id": "old", "status": "completed", "items": [{"id": "a", "type": "agentMessage", "text": "answer"}]})
        live = project_history_turn({"id": "new", "status": "inProgress", "items": [{"id": "b", "type": "agentMessage", "text": "work"}]})
        self.assertEqual(terminal.messages[0].selection.value, "terminal_fallback")
        self.assertEqual(live.messages[0].selection.value, "live")

    def test_newest_first_provider_pages_become_chronological(self):
        self.assertEqual([turn["id"] for turn in chronological_history_pages([
            [{"id": "new"}], [{"id": "old"}],
        ])], ["old", "new"])
