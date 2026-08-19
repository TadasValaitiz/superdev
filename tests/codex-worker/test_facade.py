import sys
import shlex
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import (AccessMode, Err, FacadeFaultCode, GoalSetRequest,
                                   GoalShowRequest, InterruptWorkerRequest, LimitsRequest,
                                   Ok, RunWorkerRequest, StartWorkerRequest, SteerWorkerRequest,
                                   WorkerHistoryRequest, WorkerMessagesRequest,
                                   WorkerStatusRequest)
from codex_worker.broker import TurnStartSpec
from codex_worker.facade import BrokerPort, ProjectorPort, RegistryPort, RuntimePort
from codex_worker.instance import InstanceIdentity
from codex_worker.commands import InstanceSource
from codex_worker.models import IdentifierSelector, RpcFault
from codex_worker.registry import SessionRegistry
from codex_worker.runtime import RuntimeStore


class _Broker:
    def __init__(self, registry, runtime):
        self.registry = registry
        self.runtime = runtime
        self.calls = []
        self.last_turn_spec = None
        self.control_fault = None
        self.response_text = "done"

    def model_list(self):
        return {"models": [{"id": "gpt-5.6-terra", "is_default": True,
                             "supported_efforts": ["medium"]}]}

    def daemon_status(self):
        return {"ready": True}

    def start_session(self, spec):
        self.calls.append("session_start")
        record = self.registry.create_worker("thread-1", spec.cwd, spec.name, spec.tier,
                                             spec.model, spec.effort, spec.access.value)
        self.runtime.attach(record)
        return {"session": record.to_dict(), "attached": True}

    def start_turn(self, spec):
        self.calls.append("turn_start")
        self.last_turn_spec = spec
        record = self.registry.resolve(IdentifierSelector(session_id=spec.session_id))
        self.runtime.reserve_start(spec.session_id)
        self.runtime.reconcile_start(spec.session_id, "turn-1")
        self.runtime.on_notification({"method": "item/completed", "params": {
            "threadId": record.thread_id, "turnId": "turn-1",
            "item": {"id": "message-1", "type": "agentMessage", "text": self.response_text, "phase": "final_answer"},
        }})
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": record.thread_id, "turn": {"id": "turn-1", "status": "completed"},
        }})
        return {"session_id": spec.session_id, "thread_id": record.thread_id, "turn_id": "turn-1", "status": "in_progress"}

    def session_resume(self, selector):
        record = self.registry.resolve(selector)
        self.runtime.attach(record)

    def turn_steer(self, selector, prompt):
        if self.control_fault is not None:
            raise self.control_fault
        self.calls.append("steer")
        return {"accepted": True}

    def turn_interrupt(self, selector):
        if self.control_fault is not None:
            raise self.control_fault
        self.calls.append("interrupt")
        return {"accepted": True}


class _Native:
    def __init__(self, calls):
        self.calls = calls
        self.goal = None
        self.native_calls = []
        self.pages = {None: ([{"id": "new", "status": "completed", "items": []}], "old"),
                      "old": ([{"id": "old", "status": "completed", "items": []}], None)}

    def goal_set(self, thread_id, objective=None, status=None, token_budget=None):
        self.calls.append("goal_set")
        self.goal = {"threadId": thread_id, "objective": objective or "existing",
                         "status": status or "active", "tokenBudget": token_budget,
                         "tokensUsed": 0, "timeUsedSeconds": 0,
                         "createdAt": 1, "updatedAt": 2}
        return {"goal": self.goal}

    def call(self, method, params):
        self.native_calls.append((method, dict(params)))
        if method == "thread/goal/set":
            return self.goal_set(params["threadId"], params.get("objective"),
                                 params.get("status"), params.get("tokenBudget"))
        if method == "thread/goal/get": return {"goal": self.goal}
        if method == "account/rateLimits/read": return {"rateLimits": {"primary": {"usedPercent": 1}}}
        if method == "thread/turns/list":
            turns, cursor = self.pages[params.get("cursor")]
            return {"data": turns, "nextCursor": cursor, "backwardsCursor": "newer"}
        raise AssertionError("unexpected native call: %s" % method)


class FacadeTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = str(Path(self.tempdir.name).resolve())
        self.registry = SessionRegistry(str(Path(self.cwd) / "registry.json"))
        self.runtime = RuntimeStore(event_limit=10)
        self.broker = _Broker(self.registry, self.runtime)
        self.native = _Native(self.broker.calls)
        self.broker.codex = self.native

    def tearDown(self):
        self.tempdir.cleanup()

    def test_start_installs_goal_before_first_turn_and_run_reuses_policy(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade

        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"),
            self.registry, self.broker, self.runtime, __import__("codex_worker.projection", fromlist=["x"]),
            lambda: 1.0,
        ))
        started = facade.start(StartWorkerRequest(
            name="build-a31", prompt="begin", cwd=self.cwd, goal="finish", token_budget=2000))
        self.assertIsInstance(started, Ok)
        self.assertEqual(self.broker.calls[:3], ["session_start", "goal_set", "turn_start"])
        persisted = self.registry.resolve_name("build-a31")
        self.assertEqual((persisted.tier, persisted.model, persisted.effort, persisted.access),
                         ("medium", "gpt-5.6-terra", "medium", "full"))
        followed = facade.run(RunWorkerRequest(name="build-a31", prompt="continue"))
        self.assertIsInstance(followed, Ok)
        self.assertEqual(followed.value.worker.thread_id, started.value.worker.thread_id)
        self.assertEqual(self.broker.last_turn_spec.access, AccessMode.FULL)
        self.assertEqual(self.broker.last_turn_spec.model, started.value.worker.model)

    def test_start_with_explicit_raw_model_persists_complete_null_tier_policy(self):
        self.broker.model_list = lambda: {"models": [{"id": "raw-model", "is_default": False,
                                                         "supported_efforts": ["high"]}]}
        result = self._facade().start(StartWorkerRequest(
            name="raw-a31", prompt="begin", cwd=self.cwd, tier=None, model="raw-model", effort="high"))
        self.assertIsInstance(result, Ok)
        record = self.registry.resolve_name("raw-a31")
        self.assertTrue(record.common_policy_complete)
        self.assertIsNone(record.tier)
        self.assertEqual((record.model, record.effort), ("raw-model", "high"))

    def _facade(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        return WorkerFacade(FacadeDeps(InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"),
                                       self.registry, self.broker, self.runtime,
                                       __import__("codex_worker.projection", fromlist=["x"]), lambda: 1.0))

    def _record(self, name="worker", tier="medium", access="full"):
        record = self.registry.create_worker("thread-" + name, self.cwd, name, tier,
                                             "gpt-5.6-terra", "medium", access)
        self.runtime.attach(record)
        return record

    def _worker_dict(self, record):
        return {
            "instance": "verified-instance", "name": record.name,
            "session_id": record.session_id, "thread_id": record.thread_id,
            "cwd": self.cwd, "tier": record.tier, "model": record.model,
            "effort": record.effort, "access": record.access,
        }

    def _completion_dict(self, record, structured_output=None):
        name = record.name
        return {
            "worker": self._worker_dict(record),
            "turn": {"turn_id": "turn-1", "status": "completed", "error": None},
            "messages": [{
                "type": "agent_message", "item_id": "message-1", "phase": "final_answer",
                "selection": "explicit_final", "text": self.broker.response_text,
            }],
            "structured_output": structured_output,
            "metrics": {
                "wall_duration_seconds": {"value": 0.0, "source": "codex-worker", "availability": "measured"},
                "item_counts": {"value": {"agentMessage": 1}, "source": "codex-worker", "availability": "derived"},
                "command_count": {"value": 0, "source": "codex-worker", "availability": "derived"},
                "command_duration_ms": {"value": None, "source": "codex", "availability": "unavailable"},
                "token_usage": {"value": None, "source": "codex", "availability": "unavailable"},
            },
            "recovery": {
                "status": "codex-worker --instance verified-instance status --name %s" % name,
                "messages": "codex-worker --instance verified-instance messages --name %s" % name,
                "interrupt": "codex-worker --instance verified-instance interrupt --name %s" % name,
                "raw_resume": "codex-worker --instance verified-instance session resume --thread %s" % record.thread_id,
            },
        }

    def test_dependencies_satisfy_declared_structural_protocols(self):
        import codex_worker.projection as projection
        self.assertIsInstance(self.registry, RegistryPort)
        self.assertIsInstance(self.broker, BrokerPort)
        self.assertIsInstance(self.runtime, RuntimePort)
        self.assertIsInstance(projection, ProjectorPort)

    def test_start_response_asserts_every_completion_field(self):
        result = self._facade().start(StartWorkerRequest("complete", "begin", self.cwd))
        self.assertIsInstance(result, Ok)
        record = self.registry.resolve_name("complete")
        self.assertEqual(result.value.to_dict(), self._completion_dict(record))

    def test_run_response_asserts_every_completion_field(self):
        record = self._record("continue")
        result = self._facade().run(RunWorkerRequest("continue", "next"))
        self.assertIsInstance(result, Ok)
        self.assertEqual(result.value.to_dict(), self._completion_dict(record))

    def test_goal_failure_prevents_turn_and_preserves_worker_ids_and_recovery(self):
        def fail_goal(*args, **kwargs):
            raise RpcFault(-32020, "goal rejected", "codex_failure", details={"provider": "codex"})
        self.native.goal_set = fail_goal

        result = self._facade().start(StartWorkerRequest(
            "goal-fails", "must-not-run", self.cwd, goal="finish"))

        self.assertIsInstance(result, Err)
        record = self.registry.resolve_name("goal-fails")
        self.assertNotIn("turn_start", self.broker.calls)
        self.assertEqual(result.error.known_ids, {
            "instance": "verified-instance", "name": "goal-fails",
            "session_id": record.session_id, "thread_id": record.thread_id, "turn_id": None,
        })
        self.assertEqual(shlex.split(result.error.next_actions[0]["command"])[-2:],
                         ["--thread", record.thread_id])

    def test_output_schema_reaches_turn_start_spec_exactly(self):
        schema = {"type": "object", "required": ["answer"]}
        self.broker.response_text = '{"answer":"yes"}'
        result = self._facade().start(StartWorkerRequest(
            "schema", "begin", self.cwd, output_schema=schema))
        self.assertIsInstance(result, Ok)
        record = self.registry.resolve_name("schema")
        self.assertEqual(self.broker.last_turn_spec, TurnStartSpec(
            record.session_id, "begin", "gpt-5.6-terra", "medium",
            AccessMode.FULL, schema))
        self.assertEqual(result.value.structured_output, {"answer": "yes"})

    def test_invalid_empty_model_selection_is_rejected_before_facade_effects(self):
        with self.assertRaisesRegex(ValueError, "exactly one of tier or model"):
            request = StartWorkerRequest(
                "invalid-selection", "begin", self.cwd, tier=None, model=None)
            self._facade().start(request)
        self.assertEqual(self.broker.calls, [])
        self.assertEqual(self.native.native_calls, [])
        self.assertEqual(self.registry.list(), [])

    def test_no_timeout_uses_one_indefinite_runtime_wait(self):
        waits = []
        original = self.runtime.wait
        def recording_wait(session_id, timeout):
            waits.append((session_id, timeout))
            return original(session_id, timeout)
        self.runtime.wait = recording_wait
        result = self._facade().start(StartWorkerRequest("indefinite", "begin", self.cwd))
        self.assertIsInstance(result, Ok)
        self.assertEqual(waits, [(result.value.worker.session_id, None)])

    def test_finite_timeout_preserves_active_ids_and_exact_recovery_actions(self):
        record = self._record("timed")
        waits = []
        def timeout(session_id, seconds):
            waits.append((session_id, seconds))
            raise __import__("codex_worker.runtime", fromlist=["WaitTimeout"]).WaitTimeout(session_id, "active-turn")
        self.runtime.wait = timeout
        result = self._facade().run(RunWorkerRequest("timed", "continue", timeout=2.5))
        self.assertIsInstance(result, Err)
        self.assertEqual(waits, [(record.session_id, 2.5)])
        self.assertEqual(result.error.code, FacadeFaultCode.TIMEOUT_ACTIVE)
        self.assertEqual(result.error.known_ids, {
            "instance": "verified-instance", "name": "timed", "session_id": record.session_id,
            "thread_id": record.thread_id, "turn_id": "active-turn",
        })
        self.assertEqual([shlex.split(action["command"])[3] for action in result.error.next_actions],
                         ["status", "messages", "interrupt"])

    def test_status_response_asserts_every_field(self):
        record = self._record("status-all")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "active", "status": "inProgress"}}})
        result = self._facade().status(WorkerStatusRequest("status-all"))
        self.assertEqual(result.value.to_dict(), {
            "worker": self._worker_dict(record), "daemon_status": "ready", "attached": True,
            "active_turn_id": "active", "latest_turn": None,
        })

    def test_messages_asserts_every_field_and_two_reads_do_not_consume(self):
        record = self._record("messages-all")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "active", "status": "inProgress"}}})
        for item_id, text in (("one", "first"), ("two", "second")):
            self.runtime.on_notification({"method": "item/completed", "params": {
                "threadId": record.thread_id, "turnId": "active",
                "item": {"id": item_id, "type": "agentMessage", "text": text, "phase": None}}})
        expected = {
            "worker": self._worker_dict(record),
            "messages": [{"type": "agent_message", "item_id": "two", "phase": None,
                          "selection": "live", "text": "second"}],
            "requested_tail": 1, "returned": 1, "truncated": True, "latest_cursor": 3,
        }
        first = self._facade().messages(WorkerMessagesRequest("messages-all", 1))
        second = self._facade().messages(WorkerMessagesRequest("messages-all", 1))
        self.assertEqual(first.value.to_dict(), expected)
        self.assertEqual(second.value.to_dict(), expected)

    def test_history_response_asserts_every_field(self):
        record = self._record("history-all")
        self.native.pages = {None: ([{
            "id": "new", "status": "inProgress", "startedAt": 2, "completedAt": None,
            "items": [{"id": "live", "type": "agentMessage", "text": "working", "phase": None}],
            "error": None,
        }, {
            "id": "old", "status": "failed", "startedAt": 1, "completedAt": 3,
            "items": [{"id": "final", "type": "agentMessage", "text": "failed answer", "phase": "final_answer"}],
            "error": {"message": "boom"},
        }], None)}
        result = self._facade().history(WorkerHistoryRequest("history-all", 2))
        self.assertIsInstance(result, Ok)
        self.assertEqual(result.value.to_dict(), {
            "worker": self._worker_dict(record),
            "turns": [
                {"turn_id": "old", "status": "failed", "started_at": 1, "completed_at": 3,
                 "messages": [{"type": "agent_message", "item_id": "final", "phase": "final_answer",
                               "selection": "explicit_final", "text": "failed answer"}],
                 "error": {"message": "boom"}},
                {"turn_id": "new", "status": "in_progress", "started_at": 2, "completed_at": None,
                 "messages": [{"type": "agent_message", "item_id": "live", "phase": None,
                               "selection": "live", "text": "working"}], "error": None},
            ],
            "requested_tail": 2, "returned": 2, "older_available": False,
        })

    def test_history_pages_twice_with_exact_cursors_and_chronological_tail(self):
        record = self._record("history-pages")
        self.native.pages = {
            None: ([{"id": "new", "status": "completed", "items": []}], "older"),
            "older": ([
                {"id": "middle", "status": "completed", "items": []},
                {"id": "old", "status": "completed", "items": []},
            ], None),
        }

        result = self._facade().history(WorkerHistoryRequest("history-pages", 3))

        self.assertIsInstance(result, Ok)
        history_calls = [params for method, params in self.native.native_calls
                         if method == "thread/turns/list"]
        self.assertEqual([params.get("cursor") for params in history_calls], [None, "older"])
        self.assertTrue(all(params["threadId"] == record.thread_id for params in history_calls))
        self.assertTrue(all(params["limit"] == 3 for params in history_calls))
        self.assertEqual([turn.turn_id for turn in result.value.turns], ["old", "middle", "new"])
        self.assertEqual(result.value.requested_tail, 3)
        self.assertEqual(result.value.returned, 3)
        self.assertFalse(result.value.older_available)

    def test_control_success_responses_assert_every_field(self):
        record = self._record("control-all")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "active", "status": "inProgress"}}})
        steer = self._facade().steer(SteerWorkerRequest("control-all", "focus"))
        interrupt = self._facade().interrupt(InterruptWorkerRequest("control-all"))
        worker = self._worker_dict(record)
        self.assertEqual(steer.value.to_dict(), {
            "worker": worker, "action": "steer", "accepted": True,
            "turn_id": "active", "status": "in_progress",
        })
        self.assertEqual(interrupt.value.to_dict(), {
            "worker": worker, "action": "interrupt", "accepted": True,
            "turn_id": "active", "status": "interrupted",
        })

    def test_goal_success_and_absence_responses_assert_every_field(self):
        record = self._record("goal-all")
        set_result = self._facade().goal_set(GoalSetRequest(
            "goal-all", objective="finish", status="paused", token_budget=9))
        expected_goal = {
            "thread_id": record.thread_id, "objective": "finish", "status": "paused",
            "token_budget": 9, "tokens_used": 0, "time_used_seconds": 0,
            "created_at": 1, "updated_at": 2,
        }
        self.assertEqual(set_result.value.to_dict(), {
            "worker": self._worker_dict(record), "availability": "present", "goal": expected_goal,
        })
        show_result = self._facade().goal_show(GoalShowRequest("goal-all"))
        self.assertEqual(show_result.value.to_dict(), set_result.value.to_dict())
        self.native.goal = None
        absent = self._facade().goal_show(GoalShowRequest("goal-all"))
        self.assertEqual(absent.value.to_dict(), {
            "worker": self._worker_dict(record), "availability": "absent", "goal": None,
        })

    def test_limits_response_asserts_every_field(self):
        result = self._facade().limits(LimitsRequest())
        self.assertEqual(result.value.to_dict(), {
            "availability": "available", "rate_limits": {"primary": {"usedPercent": 1}},
        })

    def test_unknown_name_and_incomplete_legacy_are_closed_actionable_faults(self):
        facade = self._facade()
        missing = facade.status(WorkerStatusRequest("absent"))
        self.assertIsInstance(missing, Err)
        self.assertEqual(missing.error.code, FacadeFaultCode.WORKER_NOT_FOUND)
        legacy = self.registry.create("legacy-thread", self.cwd, "legacy", "old-model", "medium")
        refused = facade.run(RunWorkerRequest("legacy", "continue"))
        self.assertIsInstance(refused, Err)
        self.assertEqual(refused.error.code, FacadeFaultCode.REGISTRY_ERROR)
        self.assertEqual(refused.error.details["policy_state"], "incomplete_legacy")
        self.assertEqual(refused.error.known_ids["thread_id"], legacy.thread_id)

    def test_history_goal_and_limits_guards_make_zero_native_calls(self):
        from codex_worker.models import ErrorDetail
        self._record("guarded")
        self.runtime.detach_all(ErrorDetail("stopped"))
        facade = self._facade()
        for result in (
                facade.history(WorkerHistoryRequest("guarded", 1)),
                facade.goal_set(GoalSetRequest("guarded", objective="x")),
                facade.goal_show(GoalShowRequest("guarded"))):
            self.assertIsInstance(result, Err)
            self.assertEqual(result.error.code, FacadeFaultCode.DAEMON_STOPPED)
        self.broker.daemon_status = lambda: {"ready": False}
        limits = facade.limits(LimitsRequest())
        self.assertIsInstance(limits, Err)
        self.assertEqual(limits.error.code, FacadeFaultCode.DAEMON_STOPPED)
        self.assertEqual(self.native.native_calls, [])

    def test_control_races_remain_typed_and_unrelated_codex_failure_is_not_reclassified(self):
        record = self._record("races")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "captured", "status": "inProgress"}}})
        cases = [
            (RpcFault(-32005, "turn is not active", "turn_not_active", details={
                "session_id": record.session_id, "thread_id": record.thread_id,
                "turn_id": "captured", "latest_turn": None}), FacadeFaultCode.TURN_NOT_ACTIVE),
            (RpcFault(-32003, "session detached", "session_detached"), FacadeFaultCode.DAEMON_STOPPED),
            (RpcFault(-32020, "provider failed", "codex_failure", details={"method": "turn/steer"}),
             FacadeFaultCode.CODEX_FAILURE),
        ]
        for fault, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                self.broker.control_fault = fault
                result = self._facade().steer(SteerWorkerRequest("races", "focus"))
                self.assertIsInstance(result, Err)
                self.assertEqual(result.error.code, expected_code)
                self.assertEqual(result.error.known_ids["session_id"], record.session_id)
                self.assertEqual(result.error.known_ids["thread_id"], record.thread_id)

    def test_incomplete_legacy_policy_refusal_preserves_ids_and_exact_actions(self):
        hostile_thread = "legacy thread; no"
        record = self.registry.create(hostile_thread, self.cwd, "legacy-actions", "old-model", "medium")
        result = self._facade().run(RunWorkerRequest("legacy-actions", "continue"))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.details, {"policy_state": "incomplete_legacy"})
        self.assertEqual(result.error.known_ids, {
            "instance": "verified-instance", "name": "legacy-actions",
            "session_id": record.session_id, "thread_id": hostile_thread, "turn_id": None,
        })
        self.assertEqual(shlex.split(result.error.next_actions[0]["command"]), [
            "codex-worker", "--instance", "verified-instance", "session", "resume",
            "--thread", hostile_thread,
        ])
        self.assertEqual(result.error.next_actions[1:], [
            {"command": "codex-worker --instance verified-instance turn start --session %s --prompt <text>" % record.session_id,
             "reason": "Use the advanced raw turn path without inventing policy"},
            {"command": "codex-worker --instance verified-instance start --name <different-name>",
             "reason": "Create a common worker with explicit policy"},
        ])

    def test_existing_incomplete_legacy_name_uses_legacy_aware_actions(self):
        record = self.registry.create("legacy-thread", self.cwd, "legacy-collision", "old-model", "medium")
        result = self._facade().start(StartWorkerRequest("legacy-collision", "again", self.cwd))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.WORKER_NAME_EXISTS)
        self.assertEqual(result.error.known_ids["session_id"], record.session_id)
        self.assertEqual([shlex.split(action["command"])[3:5]
                          for action in result.error.next_actions[:2]],
                         [["session", "resume"], ["turn", "start"]])
        self.assertEqual(result.error.next_actions[-1]["command"],
                         "codex-worker --instance verified-instance start --name <different-name>")

    def test_non_progressing_history_page_maps_protocol_error(self):
        self._record("history-stuck")
        self.native.pages = {
            None: ([{"id": "new", "status": "completed", "items": []}], "same"),
            "same": ([{"id": "new-again", "status": "completed", "items": []}], "same"),
        }
        result = self._facade().history(WorkerHistoryRequest("history-stuck", 3))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.CODEX_PROTOCOL_ERROR)
        self.assertEqual(result.error.kind, "codex_protocol_error")

    def test_existing_name_and_detached_observation_are_refused_without_mutation(self):
        facade = self._facade(); record = self._record("occupied")
        collision = facade.start(StartWorkerRequest("occupied", "again", self.cwd))
        self.assertIsInstance(collision, Err)
        self.assertEqual(collision.error.code, FacadeFaultCode.WORKER_NAME_EXISTS)
        self.runtime.detach_all(__import__("codex_worker.models", fromlist=["ErrorDetail"]).ErrorDetail("stopped"))
        stopped = facade.status(WorkerStatusRequest("occupied"))
        self.assertIsInstance(stopped, Err)
        self.assertEqual(stopped.error.code, FacadeFaultCode.DAEMON_STOPPED)

    def test_post_upstream_registry_fault_preserves_raw_recovery_ids(self):
        facade = self._facade()
        self.broker.start_session = lambda spec: (_ for _ in ()).throw(RpcFault(
            -32011, "not persisted", "registry_error", details={
                "session_id": "12345678-1234-5678-1234-567812345678",
                "thread_id": "upstream-thread", "operation": "session_start"}))
        refused = facade.start(StartWorkerRequest("broken", "start", self.cwd))
        self.assertIsInstance(refused, Err)
        self.assertEqual(refused.error.code, FacadeFaultCode.REGISTRY_ERROR)
        self.assertEqual(refused.error.known_ids["session_id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(refused.error.known_ids["thread_id"], "upstream-thread")

    def test_post_upstream_raw_recovery_shell_quotes_hostile_thread_as_one_argument(self):
        hostile_thread = "thread value; printf exploited"
        self.broker.start_session = lambda spec: (_ for _ in ()).throw(RpcFault(
            -32011, "not persisted", "registry_error", details={
                "session_id": "12345678-1234-5678-1234-567812345678",
                "thread_id": hostile_thread,
                "operation": "session_start"}))

        refused = self._facade().start(StartWorkerRequest("broken", "start", self.cwd))

        self.assertIsInstance(refused, Err)
        raw_resume = refused.error.next_actions[0]["command"]
        self.assertEqual(shlex.split(raw_resume), [
            "codex-worker", "--instance", "verified-instance", "session", "resume",
            "--thread", hostile_thread,
        ])

    def test_limits_stopped_recovery_is_instance_scoped_without_fabricated_worker_name(self):
        self.broker.daemon_status = lambda: {"ready": False}

        refused = self._facade().limits(LimitsRequest())

        self.assertIsInstance(refused, Err)
        self.assertEqual(refused.error.code, FacadeFaultCode.DAEMON_STOPPED)
        self.assertEqual(refused.error.known_ids, {
            "instance": "verified-instance", "name": None, "session_id": None,
            "thread_id": None, "turn_id": None,
        })
        self.assertEqual(refused.error.next_actions, [
            {
                "command": "codex-worker --instance verified-instance daemon status",
                "reason": "Inspect the selected instance",
            },
            {
                "command": "codex-worker --instance verified-instance start --name <name> --prompt <text>",
                "reason": "Start a named worker to launch the selected instance",
            },
        ])

    def test_recovery_commands_pin_the_verified_shell_quoted_instance(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        facade = WorkerFacade(FacadeDeps(InstanceIdentity(InstanceSource.DEFAULT, "scope; echo no"),
                                       self.registry, self.broker, self.runtime,
                                       __import__("codex_worker.projection", fromlist=["x"]), lambda: 1.0))
        missing = facade.status(WorkerStatusRequest("absent"))
        self.assertIsInstance(missing, Err)
        self.assertEqual(missing.error.next_actions, [{
            "command": "codex-worker --instance 'scope; echo no' start --name absent",
            "reason": "Create this worker in the selected instance"}])


if __name__ == "__main__":
    unittest.main()
