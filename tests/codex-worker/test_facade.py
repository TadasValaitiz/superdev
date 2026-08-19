import sys
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
from codex_worker.instance import InstanceIdentity
from codex_worker.commands import InstanceSource
from codex_worker.models import ItemRecord, TurnSnapshot
from codex_worker.models import RpcFault
from codex_worker.registry import SessionRegistry
from codex_worker.runtime import RuntimeStore


class _Broker:
    def __init__(self, registry, runtime):
        self.registry = registry
        self.runtime = runtime
        self.calls = []
        self.last_turn_spec = None

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
        self.runtime.reserve_start(spec.session_id)
        self.runtime.reconcile_start(spec.session_id, "turn-1")
        self.runtime.on_notification({"method": "item/completed", "params": {
            "threadId": "thread-1", "turnId": "turn-1",
            "item": {"id": "message-1", "type": "agentMessage", "text": "done", "phase": "final_answer"},
        }})
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"},
        }})
        return {"session_id": spec.session_id, "thread_id": "thread-1", "turn_id": "turn-1", "status": "in_progress"}

    def session_resume(self, selector):
        record = self.registry.resolve(selector)
        self.runtime.attach(record)

    def turn_steer(self, selector, prompt):
        self.calls.append("steer")
        return {"accepted": True}

    def turn_interrupt(self, selector):
        self.calls.append("interrupt")
        return {"accepted": True}


class _Native:
    def __init__(self, calls):
        self.calls = calls
        self.goal = None

    def goal_set(self, thread_id, objective=None, status=None, token_budget=None):
        self.calls.append("goal_set")
        self.goal = {"threadId": thread_id, "objective": objective or "existing",
                         "status": status or "active", "tokenBudget": token_budget,
                         "tokensUsed": 0, "timeUsedSeconds": 0,
                         "createdAt": "created", "updatedAt": "updated"}
        return {"goal": self.goal}

    def call(self, method, params):
        if method == "thread/goal/set":
            return self.goal_set(params["threadId"], params.get("objective"),
                                 params.get("status"), params.get("tokenBudget"))
        if method == "thread/goal/get": return {"goal": self.goal}
        if method == "account/rateLimits/read": return {"rateLimits": {"primary": {"usedPercent": 1}}}
        if method == "thread/turns/list":
            pages = {None: ([{"id": "new", "status": "completed", "items": []}], "old"),
                     "old": ([{"id": "old", "status": "completed", "items": []}], None)}
            turns, cursor = pages[params.get("cursor")]
            return {"turns": turns, "nextCursor": cursor}
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

    def test_observation_history_goal_limits_and_control_return_exact_response_models(self):
        facade = self._facade(); record = self._record()
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "active", "status": "inProgress"}}})
        self.runtime.on_notification({"method": "item/completed", "params": {
            "threadId": record.thread_id, "turnId": "active",
            "item": {"id": "live", "type": "agentMessage", "text": "working", "phase": None}}})
        status = facade.status(WorkerStatusRequest("worker"))
        self.assertEqual(status.value.worker.instance, "verified-instance")
        self.assertEqual(status.value.active_turn_id, "active")
        messages = facade.messages(WorkerMessagesRequest("worker", 1))
        self.assertEqual(messages.value.messages[0].selection.value, "live")
        self.assertEqual([turn.turn_id for turn in facade.history(WorkerHistoryRequest("worker", 2)).value.turns], ["old", "new"])
        self.assertEqual(facade.goal_set(GoalSetRequest("worker", objective="finish")).value.availability, "present")
        self.assertEqual(facade.goal_show(GoalShowRequest("worker")).value.goal.objective, "finish")
        self.assertEqual(facade.limits(LimitsRequest()).value.rate_limits, {"primary": {"usedPercent": 1}})
        self.assertEqual(facade.steer(SteerWorkerRequest("worker", "focus")).value.turn_id, "active")
        self.assertEqual(facade.interrupt(InterruptWorkerRequest("worker")).value.status, "interrupted")

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
