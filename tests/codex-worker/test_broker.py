import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.broker import ModelSelectionError, WorkerBroker
from codex_worker.models import IdentifierSelector, RpcFault
from codex_worker.registry import SessionRegistry
from codex_worker.runtime import RuntimeStore


class FakeCodex:
    def __init__(self):
        self.models = [
            {"id": "fake-model-a", "isDefault": True,
             "supportedReasoningEfforts": [{"reasoningEffort": "medium"}]},
            {"id": "fake-model-b", "isDefault": False,
             "supportedReasoningEfforts": [{"reasoningEffort": "high"}, {"reasoningEffort": "medium"}]},
        ]
        self.start_result = None
        self.resume_result = None
        self.start_calls = []
        self.resume_calls = []
        self.turn_start_calls = []
        self.steer_calls = []
        self.interrupt_calls = []
        self.shutdown_called = False
        self.proc = type("Process", (), {"pid": 4321})()
        self._on_notification = None
        self._active = None
        self._next_turn = 1
        self.emit_before_response = False
        self.response_turn_id = None
        self.notification_turn_id = None

    def list_models(self):
        return list(self.models)

    def start_thread(self, cwd, model=None):
        self.start_calls.append({"cwd": cwd, "model": model})
        return self.start_result or {"thread": {"id": "thr-start", "cwd": cwd}, "model": model}

    def resume_thread(self, thread_id, approval_policy="never", sandbox="workspace-write"):
        self.resume_calls.append({"thread_id": thread_id, "approval_policy": approval_policy,
                                  "sandbox": sandbox, "cwd": None})
        result = self.resume_result
        if result is None:
            raise AssertionError("test must provide resume_result")
        return result

    def start_turn(self, thread_id, prompt, model=None, effort=None):
        self.turn_start_calls.append({"thread_id": thread_id, "prompt": prompt,
                                      "model": model, "effort": effort})
        turn_id = self.response_turn_id or "turn-%d" % self._next_turn
        self._next_turn += 1
        self._active = (thread_id, turn_id)
        if self.emit_before_response:
            notified_id = self.notification_turn_id or turn_id
            self._emit_started(thread_id, notified_id)
            self._emit_completed(thread_id, notified_id, "completed")
            self._active = None
        return turn_id

    def steer(self, thread_id, turn_id, prompt):
        self.steer_calls.append({"thread_id": thread_id, "turn_id": turn_id, "prompt": prompt})
        return turn_id

    def interrupt(self, thread_id, turn_id):
        self.interrupt_calls.append({"thread_id": thread_id, "turn_id": turn_id})
        if self._active == (thread_id, turn_id):
            self._emit_completed(thread_id, turn_id, "interrupted")
            self._active = None

    def complete_active_turn(self):
        if self._active is None:
            raise AssertionError("no active fake turn")
        thread_id, turn_id = self._active
        self._emit_completed(thread_id, turn_id, "completed")
        self._active = None

    def shutdown(self):
        self.shutdown_called = True

    def _emit_started(self, thread_id, turn_id):
        self._on_notification({"method": "turn/started", "params": {
            "threadId": thread_id, "turn": {"id": turn_id, "status": "inProgress"},
        }})

    def _emit_completed(self, thread_id, turn_id, status):
        self._on_notification({"method": "turn/completed", "params": {
            "threadId": thread_id, "turn": {"id": turn_id, "status": status},
        }})


class WorkerBrokerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = str(Path(self.tempdir.name).resolve())
        self.state_path = str(Path(self.cwd) / "sessions.json")
        self.registry = SessionRegistry(self.state_path)
        self.runtime = RuntimeStore(event_limit=5)
        self.codex = FakeCodex()
        self.codex._on_notification = self.runtime.on_notification
        self.broker = WorkerBroker(
            self.registry, self.codex, self.runtime,
            socket_path=str(Path(self.cwd) / "worker.sock"), state_path=self.state_path,
            daemon_pid=1234,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def start_session(self, name=None, model=None):
        result = self.broker.session_start(self.cwd, name=name, model=model)
        return IdentifierSelector(session_id=result["session"]["session_id"])

    def test_daemon_status_and_model_list_use_stable_outer_shapes(self):
        status = self.broker.daemon_status()
        self.assertEqual(status, {
            "ready": True, "daemon_pid": 1234, "codex_pid": 4321,
            "socket_path": str(Path(self.cwd) / "worker.sock"), "state_path": self.state_path,
            "session_count": 0,
        })
        models = self.broker.model_list()
        self.assertEqual(models["models"], [
            {"id": "fake-model-a", "is_default": True, "supported_efforts": ["medium"]},
            {"id": "fake-model-b", "is_default": False, "supported_efforts": ["high", "medium"]},
        ])

    def test_session_start_validates_live_model_and_persists_immutable_cwd(self):
        with self.assertRaises(ModelSelectionError):
            self.broker.session_start(self.cwd, name="bad", model="not-live")
        result = self.broker.session_start(self.cwd, name="worker", model="fake-model-a")
        self.assertTrue(result["attached"])
        self.assertEqual(result["session"]["cwd"], self.cwd)
        self.assertEqual(result["session"]["model"], "fake-model-a")
        self.assertEqual(self.codex.start_calls[-1], {"cwd": self.cwd, "model": "fake-model-a"})
        self.assertEqual(SessionRegistry(self.state_path).list()[0].cwd, self.cwd)

    def test_raw_thread_recovery_uses_returned_cwd_and_persists_mapping(self):
        self.codex.resume_result = {"thread": {"id": "thr-9", "cwd": self.cwd}, "cwd": self.cwd,
                                    "model": "fake-model-b", "reasoningEffort": "high"}
        result = self.broker.session_resume(IdentifierSelector(thread_id="thr-9"), name="recovered")
        self.assertEqual(result["session"]["thread_id"], "thr-9")
        self.assertEqual(result["session"]["cwd"], self.cwd)
        self.assertEqual(result["session"]["name"], "recovered")
        self.assertEqual(self.codex.resume_calls[0]["cwd"], None)
        self.assertEqual(self.codex.resume_calls[0]["sandbox"], "workspace-write")
        self.assertEqual(SessionRegistry(self.state_path).resolve(IdentifierSelector(thread_id="thr-9")).cwd, self.cwd)

    def test_existing_session_resume_rejects_upstream_cwd_drift_without_attaching(self):
        selector = self.start_session()
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        self.runtime = RuntimeStore(event_limit=5)
        self.codex._on_notification = self.runtime.on_notification
        self.broker = WorkerBroker(
            self.registry, self.codex, self.runtime,
            socket_path=str(Path(self.cwd) / "worker.sock"), state_path=self.state_path,
            daemon_pid=1234,
        )
        self.codex.resume_result = {"thread": {"id": "thr-start", "cwd": other.name}, "cwd": other.name}
        with self.assertRaises(RpcFault) as caught:
            self.broker.session_resume(selector)
        self.assertEqual(caught.exception.kind, "session_cwd_mismatch")
        self.assertFalse(self.broker.session_show(selector)["attached"])

    def test_unknown_uuid_is_typed_and_unknown_thread_requires_explicit_resume(self):
        with self.assertRaises(RpcFault) as unknown_uuid:
            self.broker.session_show(IdentifierSelector(session_id="00000000-0000-0000-0000-000000000099"))
        self.assertEqual(unknown_uuid.exception.kind, "unknown_session")
        with self.assertRaisesRegex(RpcFault, "session resume --thread"):
            self.broker.turn_status(IdentifierSelector(thread_id="unknown"))

    def test_session_list_and_show_project_runtime_without_implicit_resume(self):
        selector = self.start_session(name="same")
        listed = self.broker.session_list()
        self.assertEqual(listed["sessions"][0]["session"]["name"], "same")
        self.assertTrue(listed["sessions"][0]["attached"])
        shown = self.broker.session_show(selector)
        self.assertEqual(shown["active_turn_id"], None)
        self.assertIsNone(shown["latest_turn"])
        self.assertEqual(self.codex.resume_calls, [])

    def test_turn_start_validates_effort_against_live_model_list(self):
        session = self.start_session()
        with self.assertRaises(ModelSelectionError):
            self.broker.turn_start(session, "task", model="fake-model-a", effort="unsupported")
        with self.assertRaises(ModelSelectionError):
            self.broker.turn_start(session, "task", model="not-live", effort="medium")

    def test_turn_start_is_nonblocking_and_updates_annotations_after_live_validation(self):
        session = self.start_session()
        result = self.broker.turn_start(session, "task", model="fake-model-b", effort="high")
        self.assertEqual(result["status"], "in_progress")
        self.assertEqual(result["turn_id"], "turn-1")
        record = self.registry.resolve(session)
        self.assertEqual((record.model, record.effort), ("fake-model-b", "high"))
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-1")

    def test_turn_start_completing_before_response_returns_terminal_runtime_and_allows_next_turn(self):
        session = self.start_session()
        self.codex.emit_before_response = True
        result = self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        self.assertEqual(result["turn_id"], "turn-1")
        status = self.broker.turn_status(session)
        self.assertIsNone(status["active_turn_id"])
        self.assertEqual(status["latest_turn"]["status"], "completed")
        self.codex.emit_before_response = False
        self.assertEqual(self.broker.turn_start(session, "again", model="fake-model-a", effort="medium")["turn_id"], "turn-2")

    def test_mismatched_turn_start_response_is_typed_protocol_fault_and_releases_reservation(self):
        session = self.start_session()
        self.codex.emit_before_response = True
        self.codex.response_turn_id = "turn-response"
        self.codex.notification_turn_id = "turn-notified"
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        self.assertEqual(caught.exception.kind, "codex_protocol_error")
        self.codex.emit_before_response = False
        self.codex.response_turn_id = None
        self.codex.notification_turn_id = None
        self.assertEqual(self.broker.turn_start(session, "again", model="fake-model-a", effort="medium")["turn_id"], "turn-2")

    def test_wait_does_not_block_steer(self):
        session = self.start_session()
        self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        with ThreadPoolExecutor(max_workers=2) as pool:
            waiter = pool.submit(self.broker.turn_wait, session, 2.0)
            steered = self.broker.turn_steer(session, "narrow the task")
            self.codex.complete_active_turn()
        self.assertTrue(steered["accepted"])
        self.assertEqual(waiter.result()["turn"]["status"], "completed")
        self.assertEqual(self.codex.steer_calls[-1]["turn_id"], "turn-1")

    def test_interrupt_completes_active_turn_and_idle_race_is_typed(self):
        session = self.start_session()
        self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        interrupted = self.broker.turn_interrupt(session)
        self.assertTrue(interrupted["accepted"])
        self.assertEqual(self.broker.turn_wait(session, 0)["turn"]["status"], "interrupted")
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_interrupt(session)
        self.assertEqual(caught.exception.kind, "turn_not_active")
        self.assertEqual(caught.exception.details["latest_turn"]["status"], "interrupted")

    def test_events_and_wait_translate_runtime_errors_to_typed_faults(self):
        session = self.start_session()
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_wait(session, 0)
        self.assertEqual(caught.exception.kind, "no_turn")
        self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_wait(session, 0)
        self.assertEqual(caught.exception.kind, "wait_timeout")
        page = self.broker.turn_events(session, after=0, limit=3)
        self.assertEqual(page["next_cursor"], 0)
        self.assertFalse(page["truncated"])

    def test_shutdown_delegates_without_deleting_registry(self):
        self.start_session()
        self.assertEqual(self.broker.shutdown(), {"accepted": True})
        self.assertTrue(self.codex.shutdown_called)
        self.assertEqual(len(SessionRegistry(self.state_path).list()), 1)


if __name__ == "__main__":
    unittest.main()
