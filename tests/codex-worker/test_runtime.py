import sys
import tempfile
import threading
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
        self.assertIs(observed[0][1], observed[0][2])
        self.assertEqual(observed[0][1].status, "failed")
        self.assertIsNone(self.runtime.terminal_snapshot(self.record.session_id, "turn-2"))


if __name__ == "__main__":
    unittest.main()
