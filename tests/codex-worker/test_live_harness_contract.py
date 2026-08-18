import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("live_broker_check.py")
SPEC = importlib.util.spec_from_file_location("live_broker_check", SCRIPT)
assert SPEC and SPEC.loader
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)


class FakeRecorder:
    def __init__(self):
        self.records = []

    def record(self, kind, payload):
        self.records.append((kind, payload))


class FailingDaemon:
    def __init__(self):
        self.force_closed = False
        self.disposed = False

    def shutdown(self):
        raise RuntimeError("graceful shutdown failed")

    def close(self, force=False):
        self.force_closed = force

    def dispose(self):
        self.disposed = True


class LiveHarnessContractTests(unittest.TestCase):
    def test_cleanup_failure_is_not_suppressed(self):
        daemon = FailingDaemon()
        with self.assertRaisesRegex(RuntimeError, "graceful shutdown failed"):
            LIVE.cleanup_daemon(FakeRecorder(), daemon)
        self.assertTrue(daemon.force_closed)
        self.assertTrue(daemon.disposed)

    def test_successful_command_event_requires_cwd_command_and_success(self):
        cwd = Path("/tmp/worker-a")
        events = [
            {"event": "item_completed", "item": {"type": "commandExecution", "data": {
                "command": "python3 hello.py", "cwd": str(cwd.resolve()), "status": "failed", "exitCode": 1}}},
            {"event": "item_completed", "item": {"type": "commandExecution", "data": {
                "command": "python3 hello.py", "cwd": str(cwd.resolve()), "status": "completed", "exitCode": 0}}},
        ]
        found = LIVE.require_successful_command_event(events, cwd, "python3 hello.py")
        self.assertEqual(found["item"]["data"]["exitCode"], 0)
        with self.assertRaises(AssertionError):
            LIVE.require_successful_command_event(events, Path("/tmp/worker-b"), "python3 hello.py")

    def test_distinct_worker_evidence_requires_both_id_dimensions_and_token_isolation(self):
        session_a = {"session_id": "a", "thread_id": "ta"}
        session_b = {"session_id": "b", "thread_id": "tb"}
        LIVE.require_distinct_worker_evidence(session_a, session_b, "secret-a", {"turn": {}}, {"events": []})
        for bad in (
            ({"session_id": "a", "thread_id": "tb"}, {"turn": {}}),
            ({"session_id": "b", "thread_id": "ta"}, {"turn": {}}),
            ({"session_id": "b", "thread_id": "tb"}, {"turn": {"text": "secret-a"}}),
        ):
            with self.assertRaises(AssertionError):
                LIVE.require_distinct_worker_evidence(session_a, bad[0], "secret-a", bad[1], {"events": []})


if __name__ == "__main__":
    unittest.main()
