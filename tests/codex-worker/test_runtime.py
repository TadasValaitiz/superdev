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


if __name__ == "__main__":
    unittest.main()
