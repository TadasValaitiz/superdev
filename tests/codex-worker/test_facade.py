import sys
import shlex
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import (AccessMode, CallbackAttemptState, CallbackAttemptView,
                                   CallbackCapture, CallbackState, Err, FacadeFaultCode, GoalSetRequest,
                                   FACADE_FAULT_KINDS, FacadeFault,
                                   GoalShowRequest, InterruptWorkerRequest, LimitsRequest,
                                   MessagePriority, MessageWorkerRequest, Ok, RunWorkerRequest, StartWorkerRequest, SteerWorkerRequest,
                                   WorkerHistoryRequest, WorkerMessagesRequest,
                                   WorkerStatusRequest)
from codex_worker.broker import ModelSelectionError, TurnStartSpec
from codex_worker.facade import BrokerPort, ProjectorPort, RegistryPort, RuntimePort
from codex_worker.instance import InstanceIdentity
from codex_worker.commands import InstanceSource
from codex_worker.models import IdentifierSelector, RpcFault
from codex_worker.registry import SessionRegistry
from codex_worker.runtime import RuntimeStore
from codex_worker.callback_store import CallbackStore
from codex_worker.callback_dispatcher import TerminalCallbackDispatcher


class _CallbackDispatcher:
    def __init__(self, calls):
        self.calls = calls
        self.observed = []
        self.now = lambda: "2026-08-20T00:00:00Z"
        self.failure = None

    def observe_turn(self, session_id, turn_id, context):
        self.calls.append("callback_observe")
        self.observed.append((session_id, turn_id, context))
        if self.failure is not None:
            raise self.failure

    def completion_for(self, session_id, turn_id, snapshot):
        context = next(item[2] for item in self.observed
                       if item[0] == session_id and item[1] == turn_id)
        projection = __import__("codex_worker.projection", fromlist=["x"])
        return projection.project_completion(context.worker, snapshot, context.output_schema,
                                             0.0, context.recovery)

    def abandon_completion(self, session_id, turn_id): pass


class _CallbackTransport:
    def __init__(self, calls): self.calls = calls; self.sent = []
    def validate_capture(self, capture):
        self.calls.append("callback_validate")
        return capture

    def send(self, binding, event, cc_agent_name):
        self.calls.append("callback_send")
        self.sent.append((binding, event, cc_agent_name))
        return CallbackAttemptView(event.event_id, CallbackAttemptState.WRITTEN,
                                   None, "2026-08-20T00:00:00Z", 1)


class _Broker:
    def __init__(self, registry, runtime):
        self.registry = registry
        self.runtime = runtime
        self.calls = []
        self.last_turn_spec = None
        self.turn_specs = []
        self.control_fault = None
        self.response_text = "done"

    def model_list(self):
        return {"models": [{"id": "gpt-5.6-terra", "is_default": True,
                             "supported_efforts": ["medium"]}]}

    def daemon_status(self):
        return {"ready": True}

    def start_session(self, spec):
        self.calls.append("session_start")
        thread_id = "thread-%d" % (len(self.registry.list()) + 1)
        record = self.registry.create_worker(thread_id, spec.cwd, spec.name, spec.tier,
                                             spec.model, spec.effort, spec.access.value)
        self.runtime.attach(record)
        return {"session": record.to_dict(), "attached": True}

    def start_turn(self, spec):
        self.calls.append("turn_start")
        self.last_turn_spec = spec
        self.turn_specs.append(spec)
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

    def turn_steer(self, selector, prompt, expected_turn_id=None):
        if self.control_fault is not None:
            raise self.control_fault
        self.calls.append("steer")
        return {"accepted": True, "turn_id": expected_turn_id}

    def turn_interrupt(self, selector, expected_turn_id=None):
        if self.control_fault is not None:
            raise self.control_fault
        self.calls.append("interrupt")
        return {"accepted": True, "turn_id": expected_turn_id}


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
        self.callback_store = CallbackStore(Path(self.cwd) / "callbacks.json",
                                            Path(self.cwd) / "callback-artifacts")
        self.callback_dispatcher = _CallbackDispatcher(self.broker.calls)
        self.callback_transport = _CallbackTransport(self.broker.calls)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_message_builds_fresh_v1_event_and_never_starts_a_broker_turn(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        from codex_worker.projection import build_worker_message_event

        event_ids = iter(("event-a", "event-b"))
        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"), self.registry,
            self.broker, self.runtime, __import__("codex_worker.projection", fromlist=["x"]),
            lambda: 1.0, self.callback_store, self.callback_dispatcher,
            self.callback_transport, lambda: next(event_ids),
        ))
        started = facade.start(StartWorkerRequest("message-a", "caller prose", self.cwd,
            callback_capture=CallbackCapture("/tmp/claude.sock", "a" * 32, "claude-session",
                                             42, "measured", self.cwd)))
        self.assertIsInstance(started, Ok)
        first = facade.message(MessageWorkerRequest("message-a", "progress", MessagePriority.NOW))
        second = facade.message(MessageWorkerRequest("message-a", "progress", MessagePriority.NOW))
        self.assertIsInstance(first, Ok)
        self.assertIsInstance(second, Ok)
        self.assertEqual(first.value.event_id, "event-a")
        self.assertEqual(second.value.event_id, "event-b")
        self.assertEqual(first.value.attempt.event_id, "event-a")
        self.assertEqual(self.broker.calls.count("turn_start"), 1)
        event = build_worker_message_event(first.value.worker, "progress", MessagePriority.NOW,
                                           "event-a", "2026-08-20T00:00:00Z")
        self.assertEqual(event.schema, "codex-worker.claude-callback/v1")
        self.assertEqual(event.event, "worker_message")
        self.assertEqual(event.payload, {"message": "progress"})
        expected_block = (
            "You may broadcast a non-blocking update to Claude and continue working:\n"
            "codex-worker --instance verified-instance message --name message-a --message \"<prose>\"\n"
            "Use --message-file for long text. Optional one-send override: --cc-agent-name <name>.\n"
            "This command does not wait for a reply; Claude may later use steer or run.")
        self.assertEqual(self.broker.turn_specs[0].prompt, "caller prose\n\n" + expected_block)
        facade.run(RunWorkerRequest("message-a", "follow-up"))
        self.assertEqual(self.broker.turn_specs[1].prompt, "follow-up")

    def test_message_callback_fault_matrix_is_typed_redacted_and_instance_qualified(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"), self.registry,
            self.broker, self.runtime, __import__("codex_worker.projection", fromlist=["x"]),
            lambda: 1.0, self.callback_store, self.callback_dispatcher, self.callback_transport,
        ))
        capture = CallbackCapture("/tmp/claude.sock", "a" * 32, "claude-session", 42,
                                  "measured", self.cwd)
        self.assertIsInstance(facade.start(StartWorkerRequest("faults-a", "start", self.cwd,
                                                               callback_capture=capture)), Ok)
        codes = (FacadeFaultCode.CALLBACK_UNAVAILABLE, FacadeFaultCode.CALLBACK_TARGET_STALE,
                 FacadeFaultCode.CALLBACK_TARGET_NOT_FOUND, FacadeFaultCode.CALLBACK_TARGET_AMBIGUOUS,
                 FacadeFaultCode.CALLBACK_TARGET_UNSAFE, FacadeFaultCode.CALLBACK_SEND_FAILED,
                 FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE)
        for code in codes:
            with self.subTest(code=code):
                def fail(binding, event, cc_agent_name, code=code):
                    raise FacadeFault(code, "callback refusal", FACADE_FAULT_KINDS[code])
                self.callback_transport.send = fail
                result = facade.message(MessageWorkerRequest("faults-a", "secret prose"))
                self.assertIsInstance(result, Err)
                self.assertEqual((result.error.code, result.error.kind),
                                 (code, FACADE_FAULT_KINDS[code]))
                self.assertEqual(result.error.known_ids["name"], "faults-a")
                encoded = result.error.to_dict()
                self.assertNotIn("secret prose", str(encoded))
                self.assertNotIn("/tmp/claude.sock", str(encoded))
                commands = [shlex.split(action["command"])
                            for action in result.error.next_actions]
                if code == FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE:
                    self.assertEqual(commands[0][3:6],
                                     ["message", "--name", "faults-a"])
                    self.assertIn("shorter", result.error.next_actions[0]["reason"].lower())
                elif code == FacadeFaultCode.CALLBACK_SEND_FAILED:
                    self.assertEqual([command[3] for command in commands],
                                     ["status", "message"])
                else:
                    self.assertEqual(commands[0][3:], ["status", "--name", "faults-a"])
                    self.assertNotEqual(commands[0][3], "message")

    def test_projector_port_declares_the_proactive_event_builder(self):
        from codex_worker.facade import ProjectorPort
        self.assertIn("build_worker_message_event", ProjectorPort.__dict__)

    def test_message_override_is_one_send_only_and_named_workers_are_independent(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        event_ids = iter("event-%d" % index for index in range(5))
        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"), self.registry,
            self.broker, self.runtime, __import__("codex_worker.projection", fromlist=["x"]),
            lambda: 1.0, self.callback_store, self.callback_dispatcher, self.callback_transport,
            lambda: next(event_ids),
        ))
        capture = CallbackCapture("/tmp/claude.sock", "a" * 32, "claude-session", 42,
                                  "measured", self.cwd)
        for index in range(5):
            self.assertIsInstance(facade.start(StartWorkerRequest("fanout-%d" % index, "start", self.cwd,
                callback_capture=capture)), Ok)
        bindings = [self.callback_store.binding(self.registry.resolve_name("fanout-%d" % index).session_id)
                    for index in range(5)]
        replies = [facade.message(MessageWorkerRequest("fanout-%d" % index, "update-%d" % index,
                    MessagePriority.NEXT, "other-room" if index == 0 else None)) for index in range(5)]
        self.assertTrue(all(isinstance(reply, Ok) for reply in replies))
        self.assertEqual([sent[1].worker.name for sent in self.callback_transport.sent[-5:]],
                         ["fanout-%d" % index for index in range(5)])
        self.assertEqual(self.callback_transport.sent[-5][2], "other-room")
        self.assertEqual([self.callback_store.binding(binding.session_id) for binding in bindings], bindings)

    def test_message_unavailable_override_is_permitted_but_disabled_override_refuses(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"), self.registry,
            self.broker, self.runtime, __import__("codex_worker.projection", fromlist=["x"]),
            lambda: 1.0, self.callback_store, self.callback_dispatcher, self.callback_transport,
        ))
        self.assertIsInstance(facade.start(StartWorkerRequest("unavailable-a", "start", self.cwd)), Ok)
        self.assertIsInstance(facade.start(StartWorkerRequest("disabled-a", "start", self.cwd,
                                                               no_callback=True)), Ok)
        original_send = self.callback_transport.send
        def policy_send(binding, event, cc_agent_name):
            if binding.state == CallbackState.DISABLED:
                raise FacadeFault(FacadeFaultCode.CALLBACK_UNAVAILABLE,
                                  "Callbacks were disabled when this worker started", "callback_unavailable")
            self.assertEqual((binding.state, cc_agent_name), (CallbackState.UNAVAILABLE, "other-room"))
            return original_send(binding, event, cc_agent_name)
        self.callback_transport.send = policy_send
        accepted = facade.message(MessageWorkerRequest("unavailable-a", "update", MessagePriority.NEXT,
                                                        "other-room"))
        refused = facade.message(MessageWorkerRequest("disabled-a", "update", MessagePriority.NEXT,
                                                       "other-room"))
        self.assertIsInstance(accepted, Ok)
        self.assertIsInstance(refused, Err)
        self.assertEqual(refused.error.code, FacadeFaultCode.CALLBACK_UNAVAILABLE)

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

    def test_start_validates_and_persists_binding_before_exact_turn_observation(self):
        capture = CallbackCapture("/tmp/claude.sock", "a" * 32, "claude-session", 42,
                                  "process-start", "/tmp")

        result = self._facade().start(StartWorkerRequest(
            "callback-order", "begin", self.cwd, callback_capture=capture))

        self.assertIsInstance(result, Ok)
        self.assertEqual(self.broker.calls[:4], ["callback_validate", "session_start",
                                                 "turn_start", "callback_observe"])
        binding = self.callback_store.binding(result.value.worker.session_id)
        self.assertEqual(binding.state, CallbackState.ENABLED)
        self.assertEqual(self.callback_dispatcher.observed[0][1], "turn-1")

    def test_real_dispatcher_reuses_byte_exact_completion_after_pre_registration_finish(self):
        class Transport(_CallbackTransport):
            def __init__(self, calls):
                super().__init__(calls); self.sent = []
                self.deps = type("Deps", (), {"now": staticmethod(
                    lambda: "2026-08-20T00:00:01Z")})()
            def encode_user_line(self, binding, event): return "{}"
            def send(inner, binding, event, cc_agent_name):
                inner.sent.append(event)
                return CallbackAttemptView(event.event_id, CallbackAttemptState.WRITTEN,
                                           None, "2026-08-20T00:00:02Z", 1)
        transport = Transport(self.broker.calls)
        projection = __import__("codex_worker.projection", fromlist=["x"])
        dispatcher = TerminalCallbackDispatcher(
            self.callback_store, transport, self.runtime, projection,
            lambda: 7.0, transport.deps.now, 0.01)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        from codex_worker.facade import FacadeDeps, WorkerFacade
        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"), self.registry,
            self.broker, self.runtime, projection, lambda: 1.0,
            self.callback_store, dispatcher, transport))
        capture = CallbackCapture("/tmp/claude.sock", "a" * 32, "claude-session", 42,
                                  "process-start", "/tmp")

        result = facade.start(StartWorkerRequest(
            "shared-projection", "begin", self.cwd, callback_capture=capture))

        self.assertIsInstance(result, Ok)
        deadline = __import__("time").monotonic() + 2
        while not transport.sent and __import__("time").monotonic() < deadline:
            __import__("time").sleep(0.01)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.sent[0].payload["completion"], result.value.to_dict())
        self.assertEqual(result.value.metrics["wall_duration_seconds"].value, 6.0)

    def test_exact_wait_returns_first_turn_when_fast_successor_finishes_before_wait(self):
        original = self.broker.start_turn
        def start_with_successor(spec):
            result = original(spec)
            record = self.registry.resolve(IdentifierSelector(session_id=spec.session_id))
            self.runtime.reserve_start(spec.session_id)
            self.runtime.reconcile_start(spec.session_id, "turn-2")
            self.runtime.on_notification({"method": "turn/completed", "params": {
                "threadId": record.thread_id,
                "turn": {"id": "turn-2", "status": "completed"},
            }})
            return result
        self.broker.start_turn = start_with_successor

        result = self._facade().start(StartWorkerRequest(
            "fast-successor", "begin", self.cwd, no_callback=True))

        self.assertIsInstance(result, Ok)
        self.assertEqual(result.value.turn.turn_id, "turn-1")

    def test_real_wait_timeout_emits_nothing_then_later_same_turn_callback(self):
        class Transport(_CallbackTransport):
            def __init__(self, calls): super().__init__(calls); self.sent = []
            def encode_user_line(self, binding, event): return "{}"
            def send(inner, binding, event, cc_agent_name):
                inner.sent.append(event)
                return CallbackAttemptView(event.event_id, CallbackAttemptState.WRITTEN,
                                           None, "2026-08-20T00:00:02Z", 1)
        transport = Transport(self.broker.calls)
        projection = __import__("codex_worker.projection", fromlist=["x"])
        dispatcher = TerminalCallbackDispatcher(
            self.callback_store, transport, self.runtime, projection,
            lambda: 2.0, lambda: "2026-08-20T00:00:01Z", 0.01)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        def active_start(spec):
            record = self.registry.resolve(IdentifierSelector(session_id=spec.session_id))
            self.runtime.reserve_start(spec.session_id)
            self.runtime.reconcile_start(spec.session_id, "turn-timeout")
            return {"session_id": spec.session_id, "thread_id": record.thread_id,
                    "turn_id": "turn-timeout", "status": "in_progress"}
        self.broker.start_turn = active_start
        from codex_worker.facade import FacadeDeps, WorkerFacade
        facade = WorkerFacade(FacadeDeps(
            InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"), self.registry,
            self.broker, self.runtime, projection, lambda: 1.0,
            self.callback_store, dispatcher, transport))
        capture = CallbackCapture("/tmp/claude.sock", "a" * 32, "claude-session", 42,
                                  "process-start", "/tmp")

        result = facade.start(StartWorkerRequest(
            "later-terminal", "begin", self.cwd, timeout=0.0, callback_capture=capture))

        self.assertIsInstance(result, Err)
        self.assertEqual(transport.sent, [])
        record = self.registry.resolve_name("later-terminal")
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": record.thread_id,
            "turn": {"id": "turn-timeout", "status": "failed",
                     "error": {"message": "failed later"}},
        }})
        deadline = __import__("time").monotonic() + 2
        while not transport.sent and __import__("time").monotonic() < deadline:
            __import__("time").sleep(0.01)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.sent[0].payload["completion"]["turn"]["turn_id"],
                         "turn-timeout")
        deadline = __import__("time").monotonic() + 2
        while dispatcher.tracked_turn_count() and __import__("time").monotonic() < deadline:
            __import__("time").sleep(0.01)
        self.assertEqual(dispatcher.tracked_turn_count(), 0)

    def test_callback_observation_failure_does_not_change_completion_response(self):
        self.callback_dispatcher.failure = OSError("callback persistence unavailable")

        actual = self._facade().start(StartWorkerRequest(
            "callback-failure", "begin", self.cwd, no_callback=True))

        self.assertIsInstance(actual, Ok)
        record = self.registry.resolve_name("callback-failure")
        self.assertEqual(actual.value.to_dict(), self._completion_dict(record))

    def test_binding_storage_failure_refuses_before_first_turn_with_recovery_ids(self):
        class BrokenStore:
            def bind(self, binding): raise OSError("disk unavailable")
        facade = self._facade()
        object.__setattr__(facade.deps, "callback_store", BrokenStore())

        result = facade.start(StartWorkerRequest(
            "binding-failure", "begin", self.cwd, no_callback=True))

        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.REGISTRY_ERROR)
        self.assertNotIn("turn_start", self.broker.calls)
        self.assertIsNotNone(result.error.known_ids["session_id"])
        self.assertEqual(result.error.known_ids["thread_id"], "thread-1")

    def test_unsupported_effort_offers_shell_safe_corrected_raw_model_start(self):
        self.broker.model_list = lambda: {"models": [{
            "id": "raw model; no", "is_default": False,
            "supported_efforts": ["low", "high"],
        }]}
        request = StartWorkerRequest(
            name="retry-effort", prompt="continue; printf no", cwd=self.cwd,
            tier=None, model="raw model; no", effort="medium",
            access=AccessMode.READ_ONLY, goal="finish safely", token_budget=123,
            timeout=2.5,
        )

        result = self._facade().start(request)

        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.EFFORT_UNSUPPORTED)
        self.assertEqual(result.error.details, {
            "model": "raw model; no", "supported_efforts": ["low", "high"],
        })
        self.assertEqual(result.error.known_ids, {
            "instance": "verified-instance", "name": "retry-effort",
            "session_id": None, "thread_id": None, "turn_id": None,
        })
        self.assertEqual(len(result.error.next_actions), 1)
        self.assertEqual(shlex.split(result.error.next_actions[0]["command"]), [
            "codex-worker", "--instance", "verified-instance", "start",
            "--name", "retry-effort", "--prompt", "continue; printf no",
            "--cwd", self.cwd, "--model", "raw model; no", "--effort", "low",
            "--read-only", "--goal", "finish safely", "--token-budget", "123",
            "--timeout", "2.5",
        ])

    def test_unsupported_effort_corrected_start_preserves_tier_selection(self):
        self.broker.model_list = lambda: {"models": [{
            "id": "gpt-5.6-terra", "is_default": True,
            "supported_efforts": ["low"],
        }]}

        result = self._facade().start(StartWorkerRequest(
            name="retry-tier", prompt="continue", cwd=self.cwd, effort="high"))

        self.assertIsInstance(result, Err)
        command = shlex.split(result.error.next_actions[0]["command"])
        self.assertEqual(command[3:], [
            "start", "--name", "retry-tier", "--prompt", "continue",
            "--cwd", self.cwd, "--tier", "medium", "--effort", "low",
        ])
        self.assertNotIn("--model", command)

    def test_unsupported_effort_with_schema_requires_original_file_and_omits_action(self):
        self.broker.model_list = lambda: {"models": [{
            "id": "gpt-5.6-terra", "is_default": True,
            "supported_efforts": ["low"],
        }]}

        result = self._facade().start(StartWorkerRequest(
            name="retry-schema", prompt="continue", cwd=self.cwd, effort="high",
            output_schema={"type": "object", "required": ["verdict"]},
        ))

        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.next_actions, [])
        self.assertEqual(result.error.details, {
            "model": "gpt-5.6-terra",
            "supported_efforts": ["low"],
            "schema_retry": {
                "required_option": "--output-schema",
                "source": "caller's original file",
                "guidance": "Retry with the original --output-schema file and one of supported_efforts",
            },
        })

    def _facade(self):
        from codex_worker.facade import FacadeDeps, WorkerFacade
        return WorkerFacade(FacadeDeps(InstanceIdentity(InstanceSource.DEFAULT, "verified-instance"),
                                       self.registry, self.broker, self.runtime,
                                       __import__("codex_worker.projection", fromlist=["x"]), lambda: 1.0,
                                       self.callback_store, self.callback_dispatcher,
                                       self.callback_transport))

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
        def recording_wait(session_id, timeout, turn_id=None):
            waits.append((session_id, timeout, turn_id))
            return original(session_id, timeout, turn_id)
        self.runtime.wait = recording_wait
        result = self._facade().start(StartWorkerRequest("indefinite", "begin", self.cwd))
        self.assertIsInstance(result, Ok)
        self.assertEqual(waits, [(result.value.worker.session_id, None, "turn-1")])

    def test_finite_timeout_preserves_active_ids_and_exact_recovery_actions(self):
        record = self._record("timed")
        waits = []
        def timeout(session_id, seconds, turn_id=None):
            waits.append((session_id, seconds, turn_id))
            raise __import__("codex_worker.runtime", fromlist=["WaitTimeout"]).WaitTimeout(session_id, "active-turn")
        self.runtime.wait = timeout
        result = self._facade().run(RunWorkerRequest("timed", "continue", timeout=2.5))
        self.assertIsInstance(result, Err)
        self.assertEqual(waits, [(record.session_id, 2.5, "turn-1")])
        self.assertEqual(result.error.code, FacadeFaultCode.TIMEOUT_ACTIVE)
        self.assertEqual(result.error.known_ids, {
            "instance": "verified-instance", "name": "timed", "session_id": record.session_id,
            "thread_id": record.thread_id, "turn_id": "active-turn",
        })
        self.assertEqual([shlex.split(action["command"])[3] for action in result.error.next_actions],
                         ["status", "messages", "interrupt"])

    def test_run_active_turn_refusal_preserves_common_identity_and_controls(self):
        record = self._record("already-active")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id,
            "turn": {"id": "active-turn", "status": "inProgress"},
        }})
        self.broker.start_turn = lambda spec: (_ for _ in ()).throw(RpcFault(
            -32004, "session already has an active turn", "turn_active",
            details={"session_id": record.session_id},
        ))

        result = self._facade().run(RunWorkerRequest("already-active", "continue"))

        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code.value, -32004)
        self.assertEqual(result.error.kind, "turn_active")
        self.assertEqual(result.error.known_ids, {
            "instance": "verified-instance", "name": "already-active",
            "session_id": record.session_id, "thread_id": record.thread_id,
            "turn_id": "active-turn",
        })
        self.assertEqual(
            [shlex.split(action["command"])[3] for action in result.error.next_actions],
            ["status", "messages", "steer", "interrupt"],
        )

    def test_status_response_asserts_every_field(self):
        record = self._record("status-all")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "active", "status": "inProgress"}}})
        result = self._facade().status(WorkerStatusRequest("status-all"))
        self.assertEqual(result.value.to_dict(), {
            "worker": self._worker_dict(record), "daemon_status": "ready", "attached": True,
            "active_turn_id": "active", "latest_turn": None,
            "callback": {"state": "unavailable", "pending_terminal_count": 0,
                         "last_terminal_attempt": None},
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

    def test_limits_unavailable_marks_capacity_unknown_without_fake_action(self):
        self.native.call = lambda method, params: (_ for _ in ()).throw(
            RuntimeError("authentication does not expose limits"))

        result = self._facade().limits(LimitsRequest())

        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.LIMITS_UNAVAILABLE)
        self.assertEqual(result.error.details, {
            "reason": "authentication does not expose limits",
            "capacity": "unknown",
            "inference": "do_not_infer",
        })
        self.assertEqual(result.error.next_actions, [])

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

    def test_control_passes_captured_turn_and_returns_broker_confirmed_identity(self):
        record = self._record("captured-control")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id, "turn": {"id": "captured", "status": "inProgress"}}})
        seen = []

        def steer(selector, prompt, expected_turn_id=None):
            seen.append((prompt, expected_turn_id))
            return {"accepted": True, "turn_id": expected_turn_id}

        self.broker.turn_steer = steer
        result = self._facade().steer(SteerWorkerRequest("captured-control", "focus"))
        self.assertIsInstance(result, Ok)
        self.assertEqual(seen, [("focus", "captured")])
        self.assertEqual(result.value.turn_id, "captured")

    def test_steer_refuses_successor_started_after_facade_capture(self):
        record = self._record("steer-barrier")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id,
            "turn": {"id": "predecessor", "status": "inProgress"}}})
        upstream = []

        def steer(selector, prompt, expected_turn_id=None):
            self.runtime.on_notification({"method": "turn/completed", "params": {
                "threadId": record.thread_id,
                "turn": {"id": "predecessor", "status": "completed"}}})
            self.runtime.on_notification({"method": "turn/started", "params": {
                "threadId": record.thread_id,
                "turn": {"id": "successor", "status": "inProgress"}}})
            if self.runtime.status(record.session_id).active_turn_id != expected_turn_id:
                raise RpcFault(-32005, "turn is not active", "turn_not_active", details={
                    "session_id": record.session_id, "thread_id": record.thread_id,
                    "turn_id": expected_turn_id, "latest_turn": None,
                })
            upstream.append(expected_turn_id)
            return {"accepted": True, "turn_id": expected_turn_id}

        self.broker.turn_steer = steer
        result = self._facade().steer(SteerWorkerRequest("steer-barrier", "late"))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.TURN_NOT_ACTIVE)
        self.assertEqual(result.error.known_ids["turn_id"], "predecessor")
        self.assertEqual(upstream, [])
        self.assertEqual(self.runtime.status(record.session_id).active_turn_id, "successor")

    def test_interrupt_refuses_successor_started_after_facade_capture(self):
        record = self._record("interrupt-barrier")
        self.runtime.on_notification({"method": "turn/started", "params": {
            "threadId": record.thread_id,
            "turn": {"id": "predecessor", "status": "inProgress"}}})
        upstream = []

        def interrupt(selector, expected_turn_id=None):
            self.runtime.on_notification({"method": "turn/completed", "params": {
                "threadId": record.thread_id,
                "turn": {"id": "predecessor", "status": "completed"}}})
            self.runtime.on_notification({"method": "turn/started", "params": {
                "threadId": record.thread_id,
                "turn": {"id": "successor", "status": "inProgress"}}})
            if self.runtime.status(record.session_id).active_turn_id != expected_turn_id:
                raise RpcFault(-32005, "turn is not active", "turn_not_active", details={
                    "session_id": record.session_id, "thread_id": record.thread_id,
                    "turn_id": expected_turn_id, "latest_turn": None,
                })
            upstream.append(expected_turn_id)
            return {"accepted": True, "turn_id": expected_turn_id}

        self.broker.turn_interrupt = interrupt
        result = self._facade().interrupt(InterruptWorkerRequest("interrupt-barrier"))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.TURN_NOT_ACTIVE)
        self.assertEqual(result.error.known_ids["turn_id"], "predecessor")
        self.assertEqual(upstream, [])
        self.assertEqual(self.runtime.status(record.session_id).active_turn_id, "successor")

    def test_catalog_disappearance_maps_model_unavailable_without_creation(self):
        starts = []

        def refuse(spec):
            starts.append(spec)
            raise ModelSelectionError("model is not available from live discovery",
                                      {"model": spec.model})

        self.broker.start_session = refuse
        result = self._facade().start(StartWorkerRequest("catalog-model", "go", self.cwd))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.MODEL_UNAVAILABLE)
        self.assertEqual(result.error.details["model"], "gpt-5.6-terra")
        self.assertEqual(len(starts), 1)
        self.assertEqual(self.registry.list(), [])

    def test_catalog_effort_change_maps_effort_unsupported_without_creation(self):
        def refuse(spec):
            raise ModelSelectionError("effort is not supported by selected live model", {
                "model": spec.model, "effort": spec.effort, "supported_efforts": ["low"],
            })

        self.broker.start_session = refuse
        result = self._facade().start(StartWorkerRequest("catalog-effort", "go", self.cwd))
        self.assertIsInstance(result, Err)
        self.assertEqual(result.error.code, FacadeFaultCode.EFFORT_UNSUPPORTED)
        self.assertEqual(result.error.details["supported_efforts"], ["low"])
        self.assertEqual(self.registry.list(), [])

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
