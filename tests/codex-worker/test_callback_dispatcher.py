import tempfile
import threading
import time
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.callback_dispatcher import (TerminalCallbackDispatcher,
                                              TerminalProjectionContext, build_terminal_event)
from codex_worker.callback_store import CallbackBinding, CallbackStore
from codex_worker.commands import (AccessMode, CallbackAttemptState,
                                   CallbackState, CompletionResponse,
                                   MetricAvailability, MetricEvidence, RecoveryView, Tier,
                                   TurnView, WorkerView)
from codex_worker.models import SessionRecord, TurnSnapshot
from codex_worker.runtime import RuntimeStore


class _Projector:
    def __init__(self):
        self.calls = 0
        self.failure = None
    def project_completion(self, worker, turn, schema, duration, recovery):
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return CompletionResponse(worker, TurnView(turn.turn_id, turn.status, None), [], None,
                                  {"wall_duration_seconds": MetricEvidence(
                                      duration, "codex-worker", MetricAvailability.MEASURED)}, recovery)


class _Transport:
    def __init__(self, fail=False, oversized=False, on_send=None):
        self.fail = fail
        self.oversized = oversized
        self.sent = []
        self.concurrent = 0
        self.maximum = 0
        self.on_send = on_send

    def encode_user_line(self, binding, event):
        if self.oversized and event.event == "turn_terminal":
            from codex_worker.commands import FacadeFault, FacadeFaultCode
            raise FacadeFault(FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE, "large",
                              "callback_payload_too_large")
        return "{}"

    def send(self, binding, event, cc_agent_name):
        from codex_worker.commands import CallbackAttemptView, FacadeFault, FacadeFaultCode
        self.concurrent += 1
        self.maximum = max(self.maximum, self.concurrent)
        try:
            if self.on_send is not None:
                self.on_send(event)
            self.sent.append(event)
            if self.fail:
                raise FacadeFault(FacadeFaultCode.CALLBACK_SEND_FAILED, "safe failure",
                                  "callback_send_failed", retryable=True)
            return CallbackAttemptView(event.event_id, CallbackAttemptState.WRITTEN, None,
                                       "2026-08-20T00:00:01Z", 1)
        finally:
            self.concurrent -= 1


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.store = CallbackStore(root / "callbacks.json", root / "artifacts")
        self.runtime = RuntimeStore(10)
        self.worker = WorkerView("default", "worker-a", "12345678-1234-5678-1234-567812345678",
                                 "thread-a", str(root.resolve()), Tier.MEDIUM,
                                 "gpt-5.6-terra", "medium", AccessMode.FULL)
        self.binding = CallbackBinding(self.worker.session_id, CallbackState.ENABLED,
                                       "/tmp/claude.sock", "a" * 32, "claude-session", 42,
                                       "start", "/tmp", "2026-08-20T00:00:00Z")
        self.store.bind(self.binding)
        self.runtime.attach(SessionRecord(
            self.worker.session_id, self.worker.thread_id, self.worker.cwd,
            "2026-08-20T00:00:00Z", "2026-08-20T00:00:00Z", self.worker.name,
            self.worker.model, self.worker.effort, self.worker.tier.value,
            self.worker.access.value))
        self.context = TerminalProjectionContext(
            self.worker, None, 10.0,
            RecoveryView("status", "messages", "interrupt", "resume"))

    def _dispatcher(self, transport=None, backoff=0.01):
        projector = _Projector()
        dispatcher = TerminalCallbackDispatcher(self.store, transport or _Transport(), self.runtime,
                                          projector, lambda: 12.0,
                                          lambda: "2026-08-20T00:00:01Z", backoff)
        dispatcher.test_projector = projector
        return dispatcher

    def _wait(self, predicate):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if predicate(): return
            time.sleep(0.01)
        self.fail("condition was not reached")

    def test_builder_preserves_exact_public_completion_for_all_terminal_statuses(self):
        for status in ("completed", "failed", "interrupted"):
            completion = _Projector().project_completion(
                self.worker, TurnSnapshot("turn-" + status, status, None, []), None, 2.0,
                self.context.recovery)
            event = build_terminal_event(completion, "2026-08-20T00:00:01Z")
            self.assertEqual(event.payload, {"completion": completion.to_dict()})
            self.assertEqual(event.priority, "next")
            self.assertEqual(event.event, "turn_terminal")

    def test_observe_closes_completion_before_registration(self):
        transport = _Transport()
        dispatcher = self._dispatcher(transport)
        dispatcher.start()
        self.addCleanup(dispatcher.shutdown)
        self.runtime.reserve_start(self.worker.session_id)
        self.runtime.reconcile_start(self.worker.session_id, "turn-1")
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.worker.thread_id,
            "turn": {"id": "turn-1", "status": "completed"},
        }})
        self.assertEqual(transport.sent, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-1", self.context)
        self._wait(lambda: len(transport.sent) == 1)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(self.store.pending(), [])

    def test_observer_delivers_after_nonterminal_wait_and_overlap_is_idempotent(self):
        transport = _Transport()
        dispatcher = self._dispatcher(transport)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        self.runtime.reserve_start(self.worker.session_id)
        self.runtime.reconcile_start(self.worker.session_id, "turn-later")
        dispatcher.observe_turn(self.worker.session_id, "turn-later", self.context)
        self.assertEqual(transport.sent, [])
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.worker.thread_id,
            "turn": {"id": "turn-later", "status": "interrupted"},
        }})
        dispatcher.queue(self.context, TurnSnapshot("turn-later", "interrupted", None, []))
        self._wait(lambda: len(transport.sent) == 1)
        self.assertEqual(len(transport.sent), 1)

    def test_controlled_listener_and_exact_lookup_overlap_projects_and_enqueues_once(self):
        transport = _Transport()
        dispatcher = self._dispatcher(transport)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        entered = threading.Event(); release = threading.Event()
        snapshot = TurnSnapshot("turn-overlap", "completed", None, [])
        original_lookup = self.runtime.terminal_snapshot
        def blocked_lookup(session_id, turn_id):
            entered.set(); release.wait(1)
            return TurnSnapshot(snapshot.turn_id, snapshot.status, snapshot.error,
                                list(snapshot.items))
        self.runtime.terminal_snapshot = blocked_lookup
        observer = threading.Thread(target=dispatcher.observe_turn,
                                    args=(self.worker.session_id, "turn-overlap", self.context))
        observer.start()
        self.assertTrue(entered.wait(1))
        dispatcher._on_terminal(self.worker.session_id, snapshot)
        release.set(); observer.join(1)
        self.runtime.terminal_snapshot = original_lookup
        self._wait(lambda: len(transport.sent) == 1)
        self.assertEqual(dispatcher.test_projector.calls, 1)
        self.assertEqual(len(transport.sent), 1)

    def test_one_projection_is_reused_by_client_and_callback_then_context_is_released(self):
        transport = _Transport()
        dispatcher = self._dispatcher(transport)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        snapshot = TurnSnapshot("turn-shared", "completed", None, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-shared", self.context)
        dispatcher.queue(self.context, snapshot)
        completion = dispatcher.completion_for(self.worker.session_id, "turn-shared", snapshot)
        self._wait(lambda: len(transport.sent) == 1)
        self.assertEqual(transport.sent[0].payload["completion"], completion.to_dict())
        self.assertEqual(dispatcher.test_projector.calls, 1)
        self._wait(lambda: dispatcher.tracked_turn_count() == 0)

    def test_stopped_dispatcher_cannot_strand_synchronous_projection(self):
        dispatcher = self._dispatcher()
        snapshot = TurnSnapshot("turn-stopped", "completed", None, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-stopped", self.context)
        completion = dispatcher.completion_for(
            self.worker.session_id, "turn-stopped", snapshot)
        self.assertEqual(completion.turn.turn_id, "turn-stopped")
        self.assertEqual(dispatcher.test_projector.calls, 1)

    def test_failed_dispatcher_thread_cannot_strand_synchronous_projection(self):
        dispatcher = self._dispatcher()
        dispatcher._run = lambda: None
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        snapshot = TurnSnapshot("turn-thread-failed", "completed", None, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-thread-failed", self.context)
        completion = dispatcher.completion_for(
            self.worker.session_id, "turn-thread-failed", snapshot)
        self.assertEqual(completion.turn.turn_id, "turn-thread-failed")
        self.assertEqual(dispatcher.test_projector.calls, 1)

    def test_shutdown_race_wakes_and_allows_synchronous_projection(self):
        dispatcher = self._dispatcher()
        worker_entered = threading.Event(); release_worker = threading.Event()
        def stalled_worker():
            worker_entered.set(); release_worker.wait(1)
        dispatcher._run = stalled_worker
        dispatcher.start(); self.assertTrue(worker_entered.wait(1))
        snapshot = TurnSnapshot("turn-shutdown", "completed", None, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-shutdown", self.context)
        completed = []
        caller = threading.Thread(target=lambda: completed.append(dispatcher.completion_for(
            self.worker.session_id, "turn-shutdown", snapshot)))
        caller.start(); caller.join(0.2)
        self.assertFalse(caller.is_alive())
        shutdown = threading.Thread(target=dispatcher.shutdown)
        shutdown.start(); release_worker.set(); shutdown.join(1)
        self.assertFalse(shutdown.is_alive())
        completion = completed[0]
        self.assertEqual(completion.turn.turn_id, "turn-shutdown")
        self.assertEqual(dispatcher.test_projector.calls, 1)

    def test_contextless_raw_terminal_does_not_enter_dispatcher_cache(self):
        dispatcher = self._dispatcher()
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        self.runtime.reserve_start(self.worker.session_id)
        self.runtime.reconcile_start(self.worker.session_id, "raw-turn")
        self.runtime.on_notification({"method": "turn/completed", "params": {
            "threadId": self.worker.thread_id,
            "turn": {"id": "raw-turn", "status": "completed"},
        }})
        self.assertEqual(dispatcher.tracked_turn_count(), 0)
        self.assertIsNotNone(self.runtime.terminal_snapshot(
            self.worker.session_id, "raw-turn"))

    def test_slow_store_does_not_block_runtime_notification_thread(self):
        entered = threading.Event(); release = threading.Event()
        original = self.store.enqueue_terminal
        def slow_enqueue(session_id, event):
            entered.set(); release.wait(1); return original(session_id, event)
        self.store.enqueue_terminal = slow_enqueue
        dispatcher = self._dispatcher(); dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        self.runtime.reserve_start(self.worker.session_id)
        self.runtime.reconcile_start(self.worker.session_id, "turn-slow")
        dispatcher.observe_turn(self.worker.session_id, "turn-slow", self.context)
        finished = threading.Event()
        def notify():
            self.runtime.on_notification({"method": "turn/completed", "params": {
                "threadId": self.worker.thread_id,
                "turn": {"id": "turn-slow", "status": "completed"},
            }})
            finished.set()
        notification = threading.Thread(target=notify)
        notification.start()
        self.assertTrue(finished.wait(0.2))
        self.assertTrue(entered.wait(1))
        release.set()
        notification.join(1)

    def test_projection_failure_is_durably_redacted_and_context_is_released(self):
        dispatcher = self._dispatcher()
        dispatcher.test_projector.failure = RuntimeError("secret /tmp/socket token")
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        snapshot = TurnSnapshot("turn-project-fail", "failed", None, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-project-fail", self.context)
        with self.assertRaises(RuntimeError):
            dispatcher.completion_for(self.worker.session_id, "turn-project-fail", snapshot)
        self._wait(lambda: self.store.status_view(
            self.worker.session_id).last_terminal_attempt is not None)
        attempt = self.store.status_view(self.worker.session_id).last_terminal_attempt
        self.assertEqual(attempt.state, CallbackAttemptState.FAILED)
        self.assertEqual(attempt.reason, "RuntimeError")
        self.assertNotIn("secret", repr(attempt.to_dict()))
        self._wait(lambda: dispatcher.tracked_turn_count() == 0)

    def test_enqueue_failure_is_exposed_without_changing_cached_completion_then_retries(self):
        failing = {"enabled": True}
        original = self.store.enqueue_terminal
        def conditional_enqueue(session_id, event):
            if failing["enabled"]:
                raise RuntimeError("secret callback path")
            return original(session_id, event)
        self.store.enqueue_terminal = conditional_enqueue
        transport = _Transport()
        dispatcher = self._dispatcher(transport)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        snapshot = TurnSnapshot("turn-enqueue-fail", "completed", None, [])
        dispatcher.observe_turn(self.worker.session_id, "turn-enqueue-fail", self.context)
        completion = dispatcher.completion_for(
            self.worker.session_id, "turn-enqueue-fail", snapshot)
        self._wait(lambda: self.store.status_view(
            self.worker.session_id).last_terminal_attempt is not None)
        attempt = self.store.status_view(self.worker.session_id).last_terminal_attempt
        self.assertEqual(attempt.reason, "RuntimeError")
        self.assertNotIn("secret", repr(attempt.to_dict()))
        self.assertEqual(completion.turn.turn_id, "turn-enqueue-fail")
        failing["enabled"] = False
        self._wait(lambda: len(transport.sent) == 1)
        self._wait(lambda: dispatcher.tracked_turn_count() == 0)

    def test_saved_context_is_copy_isolated_from_external_mutation(self):
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        context = TerminalProjectionContext(self.worker, schema, 10.0, self.context.recovery)
        dispatcher = self._dispatcher(); dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        dispatcher.observe_turn(self.worker.session_id, "turn-context", context)
        schema["properties"]["answer"]["type"] = "integer"
        with dispatcher._condition:
            saved = dispatcher._contexts[(self.worker.session_id, "turn-context")].isolated()
        self.assertEqual(saved.output_schema["properties"]["answer"]["type"], "string")

    def test_event_is_durable_before_transport_connect(self):
        observed = []
        def on_send(event):
            observed.append([entry.event_id for entry in self.store.pending()])
        transport = _Transport(on_send=on_send)
        dispatcher = self._dispatcher(transport)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        dispatcher.queue(self.context, TurnSnapshot("turn-durable", "completed", None, []))
        self._wait(lambda: len(transport.sent) == 1)
        self.assertEqual(observed, [[transport.sent[0].event_id]])

    def test_oversized_inline_publishes_verified_reference(self):
        transport = _Transport(oversized=True)
        dispatcher = self._dispatcher(transport)
        dispatcher.start(); self.addCleanup(dispatcher.shutdown)
        dispatcher.queue(self.context, TurnSnapshot("turn-big", "completed", None, []))
        self._wait(lambda: len(transport.sent) == 1)
        event = transport.sent[0]
        self.assertEqual(event.event, "turn_terminal_reference")
        artifact = event.payload["artifact"]
        self.assertTrue(Path(artifact["path"]).is_file())
        self.assertEqual(artifact["size_bytes"], Path(artifact["path"]).stat().st_size)

    def test_recovery_retries_same_id_increases_attempt_and_written_is_not_replayed(self):
        failing = _Transport(fail=True)
        first = self._dispatcher(failing, backoff=0.05)
        first.start()
        first.queue(self.context, TurnSnapshot("turn-retry", "completed", None, []))
        self._wait(lambda: bool(self.store.pending())
                   and self.store.pending()[0].attempt_count >= 1)
        event_id = self.store.pending()[0].event_id
        first.shutdown(0.2)
        succeeding = _Transport()
        second = self._dispatcher(succeeding)
        second.start(); self.addCleanup(second.shutdown)
        self._wait(lambda: not self.store.pending())
        self.assertEqual(succeeding.sent[0].event_id, event_id)
        self.assertGreaterEqual(self.store.binding(self.worker.session_id).last_terminal_attempt.attempt_count, 2)
        second.shutdown()
        third_transport = _Transport()
        third = self._dispatcher(third_transport); third.start(); third.shutdown()
        self.assertEqual(third_transport.sent, [])

    def test_single_consumer_handles_multiple_pending_and_shutdown_is_bounded(self):
        transport = _Transport()
        dispatcher = self._dispatcher(transport)
        dispatcher.start()
        for number in range(3):
            dispatcher.queue(self.context, TurnSnapshot("turn-%s" % number, "completed", None, []))
        self._wait(lambda: len(transport.sent) == 3)
        started = time.monotonic(); dispatcher.shutdown(0.2)
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(transport.maximum, 1)


if __name__ == "__main__":
    unittest.main()
