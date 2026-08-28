import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.registry import SessionRegistry
from codex_worker.runtime import RuntimeStore
from codex_worker.models import copy_turn_snapshot


class RuntimeTerminalObserverTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        registry = SessionRegistry(str(Path(self.tempdir.name) / "registry.json"))
        self.record = registry.create_worker("thread-1", self.tempdir.name, "observer", "medium",
                                             "gpt-5.6-terra", "medium", "full")
        self.runtime = RuntimeStore(10)
        self.runtime.attach(self.record)

    def test_terminal_snapshot_is_exact_and_observer_sees_committed_state_outside_lock(self):
        observed = []

        def observer(session_id, snapshot):
            observed.append((session_id, snapshot, self.runtime.terminal_snapshot(session_id,
                                                                                  snapshot.turn_id)))

        self.runtime.add_terminal_observer(observer)
        self.runtime.reserve_start(self.record.session_id)
        self.runtime.reconcile_start(self.record.session_id, "turn-1")
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "turn-1", "status": "failed", "error": {"message": "no"}},
        }})

        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][1].to_dict(), observed[0][2].to_dict())
        self.assertIsNot(observed[0][1], observed[0][2])
        self.assertEqual(observed[0][1].status, "failed")
        self.assertIsNone(self.runtime.terminal_snapshot(self.record.session_id, "turn-2"))

    def _complete(self, turn_id, status="completed"):
        self.runtime.reserve_start(self.record.session_id)
        self.runtime.reconcile_start(self.record.session_id, turn_id)
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": turn_id, "status": status},
        }})

    def test_real_wait_timeout_then_later_exact_terminal_is_retained_until_release(self):
        self.runtime.reserve_start(self.record.session_id)
        self.runtime.reconcile_start(self.record.session_id, "turn-later")
        with self.assertRaises(__import__("codex_worker.runtime", fromlist=["WaitTimeout"]).WaitTimeout):
            self.runtime.wait(self.record.session_id, 0)
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "turn-later", "status": "interrupted"},
        }})
        self.assertEqual(self.runtime.terminal_snapshot(
            self.record.session_id, "turn-later").status, "interrupted")
        self.runtime.release_terminal_snapshot(self.record.session_id, "turn-later")
        self.assertIsNone(self.runtime.terminal_snapshot(self.record.session_id, "turn-later"))

    def test_fast_successor_does_not_erase_exact_predecessor(self):
        self._complete("turn-a")
        self._complete("turn-b")
        self.assertEqual(self.runtime.terminal_snapshot(
            self.record.session_id, "turn-a").turn_id, "turn-a")
        self.assertEqual(self.runtime.terminal_snapshot(
            self.record.session_id, "turn-b").turn_id, "turn-b")

    def test_unclaimed_raw_terminal_retention_is_bounded(self):
        runtime = RuntimeStore(2)
        runtime.attach(self.record)
        for turn_id in ("raw-a", "raw-b", "raw-c"):
            runtime.reserve_start(self.record.session_id)
            runtime.reconcile_start(self.record.session_id, turn_id)
            runtime.on_notification({"method": "turn/completed", "params": {
                "threadId": self.record.thread_id,
                "turn": {"id": turn_id, "status": "completed"},
            }})
        self.assertIsNone(runtime.terminal_snapshot(self.record.session_id, "raw-a"))
        self.assertIsNotNone(runtime.terminal_snapshot(self.record.session_id, "raw-b"))
        self.assertIsNotNone(runtime.terminal_snapshot(self.record.session_id, "raw-c"))

    def test_each_observer_and_lookup_receive_copy_isolated_snapshots(self):
        seen = []
        def mutating(session_id, snapshot):
            snapshot.items[0].data["text"] = "mutated"
            snapshot.items[0].data["nested"]["value"] = "mutated"
            snapshot.items.clear()
        def reading(session_id, snapshot):
            seen.append((snapshot.items[0].data["text"],
                         snapshot.items[0].data["nested"]["value"]))
        self.runtime.add_terminal_observer(mutating)
        self.runtime.add_terminal_observer(reading)
        self.runtime.reserve_start(self.record.session_id)
        self.runtime.reconcile_start(self.record.session_id, "turn-copy")
        self.runtime.on_notification({"method": "item/completed", "params": {
            "threadId": self.record.thread_id, "turnId": "turn-copy",
            "item": {"id": "m", "type": "agentMessage", "text": "original",
                     "nested": {"value": "original"}},
        }})
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "turn-copy", "status": "completed"},
        }})
        self.assertEqual(seen, [("original", "original")])
        self.assertEqual(self.runtime.terminal_snapshot(
            self.record.session_id, "turn-copy").items[0].data["text"], "original")
        self.assertEqual(self.runtime.status(
            self.record.session_id).latest_turn.items[0].data["nested"]["value"], "original")

    def test_shared_snapshot_copy_kernel_deeply_isolates_nested_values(self):
        from codex_worker.models import ItemRecord, TurnSnapshot
        original = TurnSnapshot("copy-kernel", "completed", None, [
            ItemRecord("item", "agentMessage", {"nested": {"value": "original"}})])
        copied = copy_turn_snapshot(original)
        copied.items[0].data["nested"]["value"] = "changed"
        self.assertEqual(original.items[0].data["nested"]["value"], "original")

    def test_websocket_close_notification_detaches_without_endpoint_or_request_data(self):
        self.runtime.on_notification({
            "method": "transport/error",
            "params": {"kind": "transport_error", "details": {
                "message": "Codex WebSocket receive failed", "error": "ConnectionClosed",
            }},
        })
        status = self.runtime.status(self.record.session_id)
        self.assertFalse(status.attached)
        page = self.runtime.events(self.record.session_id, 0, 10)
        self.assertEqual(page.events[-1].event, "transport_error")
        self.assertNotIn("endpoint", repr(page.to_dict()))

    def test_tui_followup_and_delayed_predecessor_completion_preserve_successor(self):
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "tui-predecessor", "status": "inProgress"},
        }})
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "tui-successor", "status": "inProgress"},
        }})
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "tui-predecessor", "status": "interrupted"},
        }})
        status = self.runtime.status(self.record.session_id)
        self.assertEqual(status.active_turn_id, "tui-successor")
        self.assertEqual(status.latest_turn.turn_id, "tui-predecessor")

    def test_delayed_started_does_not_resurrect_terminal_turn(self):
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "terminal-first", "status": "completed"},
        }})
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "terminal-first", "status": "inProgress"},
        }})
        status = self.runtime.status(self.record.session_id)
        self.assertIsNone(status.active_turn_id)
        self.assertEqual(status.latest_turn.turn_id, "terminal-first")

    def test_explicit_new_active_lifecycle_can_complete_even_if_fake_reuses_turn_id(self):
        notification = {"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "reused", "status": "completed"},
        }}
        for _ in range(2):
            self.runtime.reserve_start(self.record.session_id)
            self.runtime.reconcile_start(self.record.session_id, "reused")
            self.runtime.on_notification(notification)
        status = self.runtime.status(self.record.session_id)
        self.assertIsNone(status.active_turn_id)
        self.assertEqual(status.latest_turn.turn_id, "reused")

    def test_authoritative_read_reconciles_without_synthesizing_agent_messages(self):
        observed = []
        self.runtime.add_terminal_observer(
            lambda session_id, snapshot: observed.append((session_id, snapshot.turn_id)))
        active = {
            "id": self.record.thread_id,
            "status": {"type": "active", "activeFlags": []},
            "turns": [{"id": "tui-active", "status": "inProgress", "items": []}],
        }
        status = self.runtime.reconcile_thread(active)
        self.assertEqual(status.active_turn_id, "tui-active")
        self.assertEqual(self.runtime.agent_messages(self.record.session_id, 10)[0], [])

        terminal = {
            "id": self.record.thread_id,
            "status": {"type": "idle"},
            "turns": [{"id": "tui-active", "status": "completed", "items": []}],
        }
        self.runtime.reconcile_thread(terminal)
        self.runtime.reconcile_thread(terminal)
        self.assertEqual(observed, [(self.record.session_id, "tui-active")])
        self.assertEqual(self.runtime.agent_messages(self.record.session_id, 10)[0], [])

    def test_pending_start_read_of_old_history_does_not_poison_response_identity(self):
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "old", "status": "completed"},
        }})
        self.runtime.reserve_start(self.record.session_id)
        self.runtime.reconcile_thread({
            "id": self.record.thread_id,
            "status": {"type": "idle"},
            "turns": [{"id": "old", "status": "completed", "items": []}],
        })
        self.runtime.reconcile_start(self.record.session_id, "new")
        self.assertEqual(
            self.runtime.status(self.record.session_id).active_turn_id, "new")

    def test_unseen_delayed_predecessor_terminal_cannot_rebind_observed_successor(self):
        self.runtime.reserve_start(self.record.session_id)
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "successor", "status": "inProgress"},
        }})
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.record.thread_id,
            "turn": {"id": "delayed-predecessor", "status": "completed"},
        }})
        self.runtime.reconcile_start(self.record.session_id, "successor")
        status = self.runtime.status(self.record.session_id)
        self.assertEqual(status.active_turn_id, "successor")
        self.assertEqual(status.latest_turn.turn_id, "delayed-predecessor")


if __name__ == "__main__":
    unittest.main()
