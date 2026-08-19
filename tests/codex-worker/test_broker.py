import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.app_server import CodexCallError
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
        self.start_exception = None
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
        self.control_failure = None
        self.control_hook = None

    def list_models(self):
        return list(self.models)

    def start_thread(self, cwd, model=None, sandbox="workspace-write", allow_provider_model_fallback=None):
        self.start_calls.append({"cwd": cwd, "model": model, "sandbox": sandbox,
                                 "allowProviderModelFallback": allow_provider_model_fallback})
        if self.start_exception is not None:
            raise self.start_exception
        return self.start_result or {"thread": {"id": "thr-start", "cwd": cwd}, "model": model}

    def resume_thread(self, thread_id, approval_policy="never", sandbox="workspace-write"):
        self.resume_calls.append({"thread_id": thread_id, "approval_policy": approval_policy,
                                  "sandbox": sandbox, "cwd": None})
        result = self.resume_result
        if result is None:
            raise AssertionError("test must provide resume_result")
        return result

    def start_turn(self, thread_id, prompt, model=None, effort=None, sandbox_policy=None, output_schema=None):
        self.turn_start_calls.append({"thread_id": thread_id, "prompt": prompt,
                                      "model": model, "effort": effort,
                                      "sandboxPolicy": sandbox_policy, "outputSchema": output_schema})
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
        if self.control_hook is not None:
            self.control_hook()
        if self.control_failure is not None:
            raise self.control_failure
        return turn_id

    def interrupt(self, thread_id, turn_id):
        self.interrupt_calls.append({"thread_id": thread_id, "turn_id": turn_id})
        if self.control_hook is not None:
            self.control_hook()
        if self.control_failure is not None:
            raise self.control_failure
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

    def test_typed_specs_use_provider_accurate_access_seams(self):
        from codex_worker.broker import SessionStartSpec, TurnStartSpec
        from codex_worker.commands import AccessMode
        full = self.broker.start_session(SessionStartSpec(self.cwd, "full", "fake-model-a", AccessMode.FULL))
        self.assertEqual(self.codex.start_calls[-1]["sandbox"], "danger-full-access")
        self.assertFalse(self.codex.start_calls[-1]["allowProviderModelFallback"])
        self.broker.start_turn(TurnStartSpec(full["session"]["session_id"], "go", "fake-model-a", "medium", AccessMode.FULL))
        self.assertEqual(self.codex.turn_start_calls[-1]["sandboxPolicy"], {"type": "dangerFullAccess"})
        self.codex.start_result = {"thread": {"id": "thr-read", "cwd": self.cwd}}
        read = self.broker.start_session(SessionStartSpec(self.cwd, "read", "fake-model-a", AccessMode.READ_ONLY))
        self.assertEqual(self.codex.start_calls[-1]["sandbox"], "read-only")
        self.broker.start_turn(TurnStartSpec(read["session"]["session_id"], "go", "fake-model-a", "medium", AccessMode.READ_ONLY, {"type": "object"}))
        self.assertEqual(self.codex.turn_start_calls[-1]["sandboxPolicy"], {"type": "readOnly", "networkAccess": False})
        self.assertEqual(self.codex.turn_start_calls[-1]["outputSchema"], {"type": "object"})

    def test_preserved_common_start_persists_policy_in_one_registry_record(self):
        from codex_worker.broker import AnnotationPolicy, SessionStartSpec
        from codex_worker.commands import AccessMode
        result = self.broker.start_session(SessionStartSpec(
            self.cwd, "common", "fake-model-a", AccessMode.FULL, "medium", "medium",
            AnnotationPolicy.PRESERVE_WORKER_POLICY))
        record = self.registry.resolve(IdentifierSelector(session_id=result["session"]["session_id"]))
        self.assertEqual((record.tier, record.model, record.effort, record.access),
                         ("medium", "fake-model-a", "medium", "full"))

    def test_native_proxy_rejects_malformed_provider_result(self):
        from codex_worker.broker import NativeCodexProxy
        class Raw:
            def call(self, method, params):
                return {"unexpected": True}
        with self.assertRaises(CodexCallError) as caught:
            NativeCodexProxy(Raw()).rate_limits_read()
        self.assertEqual(caught.exception.kind, "protocol_error")

    def test_read_only_resume_has_no_creation_only_fallback_field(self):
        from codex_worker.broker import SessionResumeSpec
        from codex_worker.commands import AccessMode
        self.codex.resume_result = {"thread": {"id": "thr-read", "cwd": self.cwd}}
        self.broker.resume_session(SessionResumeSpec("thr-read", AccessMode.READ_ONLY))
        self.assertEqual(self.codex.resume_calls[-1]["sandbox"], "read-only")
        self.assertNotIn("allowProviderModelFallback", self.codex.resume_calls[-1])

    def test_complete_common_policy_survives_raw_override_while_legacy_mutates(self):
        from codex_worker.broker import TurnStartSpec
        from codex_worker.commands import AccessMode
        complete = self.registry.create_worker("thr-common", self.cwd, "common", "medium", "fake-model-a", "medium", "full")
        self.runtime.attach(complete)
        self.broker.turn_start(IdentifierSelector(session_id=complete.session_id), "raw", "fake-model-b", "high")
        preserved = self.registry.resolve(IdentifierSelector(session_id=complete.session_id))
        self.assertEqual((preserved.tier, preserved.model, preserved.effort, preserved.access), ("medium", "fake-model-a", "medium", "full"))
        self.codex.complete_active_turn()
        self.broker.start_turn(TurnStartSpec(complete.session_id, "common", "fake-model-a", "medium", AccessMode.FULL))
        self.assertEqual(self.codex.turn_start_calls[-1]["model"], "fake-model-a")
        self.codex.complete_active_turn()
        legacy = self.registry.create("thr-legacy", self.cwd, None, "fake-model-a", "medium")
        self.runtime.attach(legacy)
        self.broker.turn_start(IdentifierSelector(session_id=legacy.session_id), "raw", "fake-model-b", "high")
        updated = self.registry.resolve(IdentifierSelector(session_id=legacy.session_id))
        self.assertEqual((updated.model, updated.effort), ("fake-model-b", "high"))

    def test_native_proxy_success_shapes_and_pagination_fields(self):
        from codex_worker.broker import NativeCodexProxy
        class Raw:
            def __init__(self): self.calls = []
            def call(self, method, params):
                self.calls.append((method, params))
                if method == "thread/goal/get": return {"goal": None}
                if method == "thread/goal/set": return {"goal": {"threadId": "t", "objective": "o", "status": "active", "tokenBudget": None, "tokensUsed": 0, "timeUsedSeconds": 0, "createdAt": 1, "updatedAt": 2}}
                if method == "thread/turns/list": return {"data": [{"id": "t", "status": "completed", "items": []}], "nextCursor": "next", "backwardsCursor": "back"}
                return {"rateLimits": {"primary": {"usedPercent": 1}}}
        raw = Raw(); proxy = NativeCodexProxy(raw)
        self.assertIsNone(proxy.goal_get("t")["goal"])
        goal = proxy.goal_set("t", "o", "active")["goal"]
        self.assertEqual(goal["objective"], "o")
        self.assertEqual(goal["createdAt"], 1)
        self.assertEqual(proxy.turns_list("t", "cursor", 2)["nextCursor"], "next")
        self.assertEqual(proxy.rate_limits_read()["rateLimits"]["primary"]["usedPercent"], 1)
        self.assertEqual(raw.calls[2], ("thread/turns/list", {"threadId": "t", "sortDirection": "desc", "itemsView": "full", "cursor": "cursor", "limit": 2}))

    def test_native_proxy_pages_newest_first_with_exact_cursors(self):
        from codex_worker.broker import NativeCodexProxy
        class Raw:
            def __init__(self): self.calls = []
            def call(self, method, params):
                self.calls.append((method, params))
                if params.get("cursor") is None:
                    return {"data": [{"id": "new", "status": "completed", "items": []}], "nextCursor": "old", "backwardsCursor": "newer"}
                return {"data": [{"id": "old", "status": "completed", "items": []}], "nextCursor": None, "backwardsCursor": "newer"}
        raw = Raw(); proxy = NativeCodexProxy(raw)
        first = proxy.turns_list("thread", None, 1); second = proxy.turns_list("thread", first["nextCursor"], 1)
        self.assertEqual([turn["id"] for turn in first["turns"] + second["turns"]], ["new", "old"])
        self.assertEqual(raw.calls, [("thread/turns/list", {"threadId": "thread", "sortDirection": "desc", "itemsView": "full", "limit": 1}), ("thread/turns/list", {"threadId": "thread", "sortDirection": "desc", "itemsView": "full", "cursor": "old", "limit": 1})])

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
        self.assertEqual(self.codex.start_calls[-1], {"cwd": self.cwd, "model": "fake-model-a",
                                                      "sandbox": "danger-full-access",
                                                      "allowProviderModelFallback": False})
        self.assertEqual(SessionRegistry(self.state_path).list()[0].cwd, self.cwd)

    def test_raw_thread_recovery_uses_returned_cwd_and_persists_mapping(self):
        self.codex.resume_result = {"thread": {"id": "thr-9", "cwd": self.cwd}, "cwd": self.cwd,
                                    "model": "fake-model-b", "reasoningEffort": "high"}
        result = self.broker.session_resume(IdentifierSelector(thread_id="thr-9"), name="recovered")
        self.assertEqual(result["session"]["thread_id"], "thr-9")
        self.assertEqual(result["session"]["cwd"], self.cwd)
        self.assertEqual(result["session"]["name"], "recovered")
        self.assertEqual(self.codex.resume_calls[0]["cwd"], None)
        self.assertEqual(self.codex.resume_calls[0]["sandbox"], "danger-full-access")
        self.assertEqual(SessionRegistry(self.state_path).resolve(IdentifierSelector(thread_id="thr-9")).cwd, self.cwd)

    def test_recovery_rejects_invalid_upstream_cwds_as_protocol_faults_without_persisting(self):
        invalid_responses = [
            {"thread": {"id": "thr-missing"}},
            {"thread": {"id": "thr-relative", "cwd": "relative"}},
            {"thread": {"id": "thr-gone", "cwd": str(Path(self.cwd) / "gone")}},
            {"thread": {"id": "thr-conflict", "cwd": self.cwd}, "cwd": tempfile.gettempdir()},
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                self.codex.resume_result = response
                thread_id = response["thread"]["id"]
                with self.assertRaises(RpcFault) as caught:
                    self.broker.session_resume(IdentifierSelector(thread_id=thread_id))
                self.assertEqual(caught.exception.kind, "codex_protocol_error")
                self.assertIsNone(self.registry.try_resolve(IdentifierSelector(thread_id=thread_id)))

    def test_adapter_protocol_error_is_a_broker_protocol_fault(self):
        self.codex.start_exception = CodexCallError("protocol_error", "thread/start", {
            "message": "thread/start response omitted thread id",
        })
        with self.assertRaises(RpcFault) as caught:
            self.broker.session_start(self.cwd)
        self.assertEqual(caught.exception.code, -32015)
        self.assertEqual(caught.exception.kind, "codex_protocol_error")

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
        self.assertEqual(
            unknown_uuid.exception.recovery,
            "run session list to choose a known session, or recover a raw Codex thread with "
            "session resume --thread <thread-id> --name <name>",
        )
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

    def test_effort_only_turn_uses_persisted_nondefault_model_for_validation_and_upstream(self):
        session = self.start_session(model="fake-model-b")
        result = self.broker.turn_start(session, "task", effort="high")
        self.assertEqual(result["turn_id"], "turn-1")
        self.assertEqual(self.codex.turn_start_calls[-1]["model"], "fake-model-b")
        self.assertEqual(self.codex.turn_start_calls[-1]["effort"], "high")
        record = self.registry.resolve(session)
        self.assertEqual((record.model, record.effort), ("fake-model-b", "high"))

    def test_effort_only_turn_uses_discovered_default_when_session_has_no_model(self):
        session = self.start_session()
        self.broker.turn_start(session, "task", effort="medium")
        self.assertEqual(self.codex.turn_start_calls[-1]["model"], "fake-model-a")
        record = self.registry.resolve(session)
        self.assertEqual((record.model, record.effort), ("fake-model-a", "medium"))

    def test_effort_only_turn_does_not_search_nondefault_models_for_a_supported_effort(self):
        session = self.start_session()
        with self.assertRaises(ModelSelectionError) as caught:
            self.broker.turn_start(session, "task", effort="high")
        self.assertEqual(caught.exception.details["model"], "fake-model-a")
        self.assertEqual(self.codex.turn_start_calls, [])

    def test_model_only_turn_preserves_omitted_persisted_effort(self):
        session = self.start_session(model="fake-model-b")
        self.broker.turn_start(session, "first", effort="high")
        self.codex.complete_active_turn()
        self.broker.turn_start(session, "second", model="fake-model-a")
        self.assertEqual(self.codex.turn_start_calls[-1]["model"], "fake-model-a")
        self.assertEqual(self.codex.turn_start_calls[-1]["effort"], None)
        record = self.registry.resolve(session)
        self.assertEqual((record.model, record.effort), ("fake-model-a", "high"))

    def test_turn_with_omitted_options_preserves_persisted_annotations(self):
        session = self.start_session(model="fake-model-b")
        self.broker.turn_start(session, "first", effort="high")
        self.codex.complete_active_turn()
        self.broker.turn_start(session, "second")
        self.assertEqual(self.codex.turn_start_calls[-1]["model"], None)
        self.assertEqual(self.codex.turn_start_calls[-1]["effort"], None)
        record = self.registry.resolve(session)
        self.assertEqual((record.model, record.effort), ("fake-model-b", "high"))

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
        self.assertEqual(result["status"], "in_progress")
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

    def test_delayed_steer_error_after_replacement_turn_is_not_active_race(self):
        session = self.start_session()
        self.broker.turn_start(session, "first", model="fake-model-a", effort="medium")

        def replace_turn():
            self.codex.complete_active_turn()
            self.broker.turn_start(session, "replacement", model="fake-model-a", effort="medium")

        self.codex.control_hook = replace_turn
        self.codex.control_failure = CodexCallError(
            "upstream_error", "turn/steer",
            {"code": -32600, "message": "no active turn to steer"},
        )
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_steer(session, "narrow the task")
        self.assertEqual(caught.exception.kind, "turn_not_active")
        self.assertEqual(caught.exception.details["latest_turn"]["turn_id"], "turn-1")
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-2")

    def test_delayed_interrupt_error_after_replacement_turn_is_not_active_race(self):
        session = self.start_session()
        self.broker.turn_start(session, "first", model="fake-model-a", effort="medium")

        def replace_turn():
            self.codex.complete_active_turn()
            self.broker.turn_start(session, "replacement", model="fake-model-a", effort="medium")

        self.codex.control_hook = replace_turn
        self.codex.control_failure = CodexCallError(
            "upstream_error", "turn/interrupt",
            {"code": -32600, "message": "no active turn to interrupt"},
        )
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_interrupt(session)
        self.assertEqual(caught.exception.kind, "turn_not_active")
        self.assertEqual(caught.exception.details["latest_turn"]["turn_id"], "turn-1")
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-2")

    def test_expected_steer_turn_refuses_successor_before_upstream_dispatch(self):
        session = self.start_session()
        self.broker.turn_start(session, "first", model="fake-model-a", effort="medium")
        self.codex.complete_active_turn()
        self.broker.turn_start(session, "successor", model="fake-model-a", effort="medium")

        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_steer(session, "late steer", expected_turn_id="turn-1")

        self.assertEqual(caught.exception.kind, "turn_not_active")
        self.assertEqual(caught.exception.details["turn_id"], "turn-1")
        self.assertEqual(self.codex.steer_calls, [])
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-2")

    def test_expected_interrupt_turn_refuses_successor_before_upstream_dispatch(self):
        session = self.start_session()
        self.broker.turn_start(session, "first", model="fake-model-a", effort="medium")
        self.codex.complete_active_turn()
        self.broker.turn_start(session, "successor", model="fake-model-a", effort="medium")

        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_interrupt(session, expected_turn_id="turn-1")

        self.assertEqual(caught.exception.kind, "turn_not_active")
        self.assertEqual(caught.exception.details["turn_id"], "turn-1")
        self.assertEqual(self.codex.interrupt_calls, [])
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-2")

    def test_upstream_idle_steer_response_before_delayed_completion_is_typed_with_both_identities(self):
        session = self.start_session()
        self.broker.turn_start(session, "first", model="fake-model-a", effort="medium")
        self.codex.complete_active_turn()
        self.broker.turn_start(session, "second", model="fake-model-a", effort="medium")
        response_ready = threading.Event()

        def response_before_notification():
            response_ready.set()

        self.codex.control_hook = response_before_notification
        self.codex.control_failure = CodexCallError(
            "upstream_error", "turn/steer",
            {"code": -32600, "message": "no active turn to steer"},
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.broker.turn_steer, session, "too late")
            self.assertTrue(response_ready.wait(1.0))
            caught = future.exception(timeout=1.0)
            self.codex.complete_active_turn()
        self.assertIsInstance(caught, RpcFault)
        self.assertEqual(caught.kind, "turn_not_active")
        self.assertEqual(caught.details["turn_id"], "turn-2")
        self.assertEqual(caught.details["latest_turn"]["turn_id"], "turn-1")
        self.assertEqual(self.broker.turn_status(session)["latest_turn"]["turn_id"], "turn-2")

    def test_upstream_idle_interrupt_response_before_delayed_completion_is_typed_with_both_identities(self):
        session = self.start_session()
        self.broker.turn_start(session, "first", model="fake-model-a", effort="medium")
        self.codex.complete_active_turn()
        self.broker.turn_start(session, "second", model="fake-model-a", effort="medium")
        response_ready = threading.Event()

        def response_before_notification():
            response_ready.set()

        self.codex.control_hook = response_before_notification
        self.codex.control_failure = CodexCallError(
            "upstream_error", "turn/interrupt",
            {"code": -32600, "message": "no active turn to interrupt"},
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.broker.turn_interrupt, session)
            self.assertTrue(response_ready.wait(1.0))
            caught = future.exception(timeout=1.0)
            self.codex.complete_active_turn()
        self.assertIsInstance(caught, RpcFault)
        self.assertEqual(caught.kind, "turn_not_active")
        self.assertEqual(caught.details["turn_id"], "turn-2")
        self.assertEqual(caught.details["latest_turn"]["turn_id"], "turn-1")
        self.assertEqual(self.broker.turn_status(session)["latest_turn"]["turn_id"], "turn-2")

    def test_unrelated_control_error_is_not_misclassified_as_idle_race(self):
        session = self.start_session()
        self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")

        def complete_before_unrelated_error():
            self.codex.complete_active_turn()

        self.codex.control_hook = complete_before_unrelated_error
        self.codex.control_failure = CodexCallError(
            "upstream_error", "turn/steer", {"code": -32600, "message": "permission denied"},
        )
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_steer(session, "narrow")
        self.assertEqual(caught.exception.kind, "codex_failure")

    def test_session_start_persistence_failure_exposes_unpersisted_upstream_identity(self):
        with mock.patch("codex_worker.registry.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(RpcFault) as caught:
                self.broker.session_start(self.cwd, name="worker", model="fake-model-b")
        fault = caught.exception
        self.assertEqual((fault.code, fault.kind), (-32011, "registry_error"))
        self.assertEqual(fault.details["operation"], "session_start")
        self.assertEqual(fault.details["durable_state"], "not_persisted")
        UUID(fault.details["session_id"])
        self.assertEqual(fault.details["thread_id"], "thr-start")
        self.assertNotIn("turn_id", fault.details)
        self.assertIn("session resume --thread thr-start", fault.recovery)

    def test_raw_resume_persistence_failure_exposes_unpersisted_upstream_identity(self):
        self.codex.resume_result = {"thread": {"id": "thr-recovered", "cwd": self.cwd}}
        with mock.patch("codex_worker.registry.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(RpcFault) as caught:
                self.broker.session_resume(
                    IdentifierSelector(thread_id="thr-recovered"), name="recovered"
                )
        fault = caught.exception
        self.assertEqual((fault.code, fault.kind), (-32011, "registry_error"))
        self.assertEqual(fault.details["operation"], "session_resume")
        self.assertEqual(fault.details["durable_state"], "not_persisted")
        UUID(fault.details["session_id"])
        self.assertEqual(fault.details["thread_id"], "thr-recovered")
        self.assertIn("session resume --thread thr-recovered", fault.recovery)

    def test_turn_annotation_persistence_failure_exposes_started_turn_identity_and_recovery(self):
        session = self.start_session(model="fake-model-a")
        with mock.patch("codex_worker.registry.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(RpcFault) as caught:
                self.broker.turn_start(session, "task", effort="medium")
        fault = caught.exception
        self.assertEqual((fault.code, fault.kind), (-32011, "registry_error"))
        self.assertEqual(fault.details, {
            "operation": "turn_start_annotations",
            "durable_state": "not_persisted",
            "session_id": session.session_id,
            "thread_id": "thr-start",
            "turn_id": "turn-1",
            "reason": "disk full",
        })
        self.assertIn("turn status --session %s" % session.session_id, fault.recovery)
        self.assertIn("turn events --session %s" % session.session_id, fault.recovery)
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-1")

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
        self.assertIn("work remains active", caught.exception.message)
        self.assertTrue(caught.exception.details["active"])
        self.assertEqual(caught.exception.details["next_actions"], [
            "turn status --session %s" % session.session_id,
            "turn wait --session %s --timeout <seconds>" % session.session_id,
            "turn steer --session %s --prompt <text>" % session.session_id,
            "turn interrupt --session %s" % session.session_id,
        ])
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
