import sys
import tempfile
import threading
import time
import unittest
from dataclasses import FrozenInstanceError
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.app_server import CodexCallError
from codex_worker.broker import (FORCE_INVENTORY_TIMEOUT_SECONDS,
                                 MaintenanceCoordinator, ModelSelectionError, WorkerBroker)
from codex_worker.models import (ActiveInventory, ActiveThreadItem, IdentifierSelector,
                                 MaintenanceResult, RpcFault)
from codex_worker.registry import SessionRegistry
from codex_worker.runtime import RuntimeStore
from codex_worker.version import distribution_version
from codex_worker.websocket_gateway import ServiceBusyError, ServiceMaintenanceGate


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
        self.steer_return_id = None
        self.calls = []
        self.call_timeouts = []
        self.thread_pages = {}
        self.thread_reads = {}
        self.turn_pages = {}
        self.turns_by_thread = {}

    def list_models(self):
        return list(self.models)

    def call(self, method, params, timeout=120.0):
        self.call_timeouts.append((method, timeout))
        self.calls.append((method, dict(params)))
        if method == "thread/list":
            value = self.thread_pages.get(params.get("cursor"))
            if isinstance(value, BaseException):
                raise value
            if value is None:
                return {"data": [], "nextCursor": None, "backwardsCursor": None}
            return value
        if method == "thread/read":
            thread_id = params["threadId"]
            if thread_id in self.thread_reads:
                return self.thread_reads[thread_id]
            turns = list(self.turns_by_thread.get(thread_id, []))
            active = self._active is not None and self._active[0] == thread_id
            return {"thread": {
                "id": thread_id,
                "status": ({"type": "active", "activeFlags": []}
                           if active else {"type": "idle"}),
                "turns": turns,
            }}
        if method == "thread/turns/list":
            value = self.turn_pages.get(params.get("cursor"))
            if value is None:
                return {"data": [], "nextCursor": None, "backwardsCursor": None}
            return value
        raise AssertionError("unexpected raw call: %s" % method)

    def start_thread(self, cwd, model=None, sandbox="workspace-write", allow_provider_model_fallback=None,
                     config=None):
        self.start_calls.append({"cwd": cwd, "model": model, "sandbox": sandbox,
                                 "allowProviderModelFallback": allow_provider_model_fallback,
                                 "config": config})
        if self.start_exception is not None:
            raise self.start_exception
        return self.start_result or {"thread": {"id": "thr-start", "cwd": cwd}, "model": model}

    def resume_thread(self, thread_id, approval_policy="never", sandbox="workspace-write", config=None):
        self.resume_calls.append({"thread_id": thread_id, "approval_policy": approval_policy,
                                  "sandbox": sandbox, "cwd": None, "config": config})
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
        self.turns_by_thread.setdefault(thread_id, []).append({
            "id": turn_id, "status": "inProgress", "items": []})
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
        return self.steer_return_id or turn_id

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
        turns = self.turns_by_thread.setdefault(thread_id, [])
        existing = next((turn for turn in turns if turn["id"] == turn_id), None)
        if existing is None:
            turns.append({"id": turn_id, "status": status, "items": []})
        else:
            existing["status"] = status
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
        self.gate = ServiceMaintenanceGate()
        self.broker = WorkerBroker(
            self.registry, self.codex, self.runtime,
            socket_path=str(Path(self.cwd) / "worker.sock"), state_path=self.state_path,
            daemon_pid=1234, gate=self.gate, listener="ws://127.0.0.1:4500",
        )

    @staticmethod
    def active_thread(thread_id):
        return {"id": thread_id, "status": {
            "type": "active", "activeFlags": ["waitingOnApproval"]}}

    @staticmethod
    def idle_thread(thread_id):
        return {"id": thread_id, "status": {"type": "idle"}}

    def test_inventory_pages_all_sources_deduplicates_and_includes_unmapped_tui(self):
        worker = self.registry.create_worker(
            "worker-thread", self.cwd, "known-worker", "medium",
            "fake-model-a", "medium", "full")
        self.codex.thread_pages = {
            None: {"data": [self.active_thread("worker-thread"),
                            self.active_thread("tui-thread")],
                   "nextCursor": "page-2", "backwardsCursor": None},
            "page-2": {"data": [self.active_thread("tui-thread"),
                                 self.idle_thread("idle-thread")],
                       "nextCursor": None, "backwardsCursor": "back"},
        }
        self.codex.thread_reads = {
            "worker-thread": {"thread": {
                "id": "worker-thread", "status": {"type": "active"},
                "turns": [{"id": "worker-turn", "status": "inProgress"}]}},
            "tui-thread": {"thread": {
                "id": "tui-thread", "status": {"type": "active"},
                "turns": [{"id": "tui-turn", "status": "inProgress"}]}},
        }

        inventory = self.broker.list_active_threads()

        self.assertIsInstance(inventory, ActiveInventory)
        self.assertEqual([item.thread_id for item in inventory.items],
                         ["worker-thread", "tui-thread"])
        self.assertEqual(inventory.items[0].worker, "known-worker")
        self.assertEqual(inventory.items[0].session_id, worker.session_id)
        self.assertEqual(inventory.items[0].origin, "worker")
        self.assertEqual(inventory.items[1].origin, "unmapped_tui")
        self.assertIsNone(inventory.items[1].worker)
        self.assertEqual([item.turn_id for item in inventory.items],
                         ["worker-turn", "tui-turn"])
        self.assertEqual(self.codex.calls, [
            ("thread/list", {"sourceKinds": []}),
            ("thread/list", {"sourceKinds": [], "cursor": "page-2"}),
            ("thread/read", {"threadId": "worker-thread", "includeTurns": True}),
            ("thread/read", {"threadId": "tui-thread", "includeTurns": True}),
        ])

    def test_activity_and_maintenance_models_are_strict_frozen_round_trips(self):
        inventory = ActiveInventory([
            ActiveThreadItem("tui-thread", "unmapped_tui", None, None, "tui-turn",
                             ["waitingOnApproval"]),
        ])
        result = MaintenanceResult.completed("stop", inventory, True)
        self.assertEqual(MaintenanceResult.from_dict(result.to_dict()), result)
        with self.assertRaises(FrozenInstanceError):
            result.status = "refused"
        with self.assertRaises(AttributeError):
            result.inventory.items.clear()
        with self.assertRaises(AttributeError):
            result.inventory.items[0].active_flags.clear()
        malformed = result.to_dict()
        malformed["extra"] = True
        with self.assertRaises(ValueError):
            MaintenanceResult.from_dict(malformed)
        with self.assertRaises(ValueError):
            MaintenanceResult("restart", "completed", False, None, inventory)
        with self.assertRaises(ValueError):
            MaintenanceResult("stop", "completed", False,
                              "ws://localhost:4500", inventory)
        with self.assertRaises(ValueError):
            MaintenanceResult("stop", "refused", False, None, ActiveInventory())
        with self.assertRaises(ValueError):
            MaintenanceResult("stop", "completed", False, None, inventory)

    def test_unavailable_maintenance_impact_is_explicit_and_has_no_counts_or_ids(self):
        result = MaintenanceResult.unavailable(
            "stop", "completed", True, None, "upstream_inventory_unavailable")
        wire = result.to_dict()
        self.assertEqual(wire["inventory"], {
            "availability": "unavailable",
            "reason": "upstream_inventory_unavailable",
        })
        self.assertEqual(wire["workers"], {
            "availability": "unavailable",
            "reason": "upstream_inventory_unavailable",
        })
        self.assertNotIn("items", wire["inventory"])
        self.assertNotIn("active_count", wire["workers"])
        self.assertEqual(MaintenanceResult.from_dict(wire), result)
        malformed = dict(wire)
        malformed["durable_state"] = "discarded"
        with self.assertRaises(ValueError):
            MaintenanceResult.from_dict(malformed)
        malformed = dict(wire)
        malformed["forced"] = False
        with self.assertRaises(ValueError):
            MaintenanceResult.from_dict(malformed)
        with self.assertRaises(ValueError):
            MaintenanceResult.unavailable(
                "stop", "completed", False, None,
                "upstream_inventory_unavailable")

    def test_inventory_malformed_cursor_loop_and_upstream_error_all_fail_closed(self):
        for timeout in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.broker.list_active_threads(timeout=timeout)
        failures = [
            {None: {"data": "not-a-list", "nextCursor": None,
                    "backwardsCursor": None}},
            {None: {"data": [], "nextCursor": None}},
            {None: {"data": [self.active_thread("tui-thread")],
                    "nextCursor": "again", "backwardsCursor": None},
             "again": {"data": [], "nextCursor": "again",
                       "backwardsCursor": None}},
            {None: CodexCallError("transport_error", "thread/list",
                                  {"message": "disconnected"})},
        ]
        for pages in failures:
            with self.subTest(pages=pages):
                self.codex.calls = []
                self.codex.thread_pages = pages
                with self.assertRaises(RpcFault):
                    self.broker.list_active_threads()

    def test_every_worker_mutation_uses_shared_gate_and_drain_refuses_new_mutation(self):
        from codex_worker.broker import SessionResumeSpec, SessionStartSpec, TurnStartSpec
        from codex_worker.commands import AccessMode
        started = self.start_session()
        record = self.registry.resolve(started)
        mutations = {
            "start_session": lambda: self.broker.start_session(SessionStartSpec(
                self.cwd, "blocked-a", "fake-model-a")),
            "resume_session": lambda: self.broker.resume_session(SessionResumeSpec(
                record.thread_id, AccessMode.FULL)),
            "start_turn": lambda: self.broker.start_turn(TurnStartSpec(
                record.session_id, "blocked", "fake-model-a", "medium")),
            "session_start": lambda: self.broker.session_start(
                self.cwd, name="blocked-b", model="fake-model-a"),
            "session_resume": lambda: self.broker.session_resume(started),
            "turn_start": lambda: self.broker.turn_start(
                started, "blocked", model="fake-model-a", effort="medium"),
            "turn_steer": lambda: self.broker.turn_steer(started, "blocked"),
            "turn_interrupt": lambda: self.broker.turn_interrupt(started),
            "shutdown": self.broker.shutdown,
            "goal_set": lambda: self.broker.goal_set(record.thread_id, "blocked"),
        }
        with self.gate.drain():
            for name, mutation in mutations.items():
                with self.subTest(name=name), self.assertRaises(ServiceBusyError):
                    mutation()
        self.assertEqual(len(self.codex.start_calls), 1)
        self.assertFalse(self.codex.shutdown_called)

    def test_healthy_force_reports_complete_unmapped_inventory_before_termination(self):
        self.registry.create_worker(
            "idle-thread", self.cwd, "idle-worker", "medium",
            "fake-model-a", "medium", "full")
        self.codex.thread_pages = {None: {
            "data": [self.active_thread("tui-thread")],
            "nextCursor": None, "backwardsCursor": None,
        }}
        self.codex.thread_reads["tui-thread"] = {"thread": {
            "id": "tui-thread", "status": {"type": "active"},
            "turns": [{"id": "tui-turn", "status": "inProgress"}]}}

        class Lifecycle:
            def __init__(self, gate):
                self.gate = gate
                self.terminated = 0
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                self.terminated += 1
            def stopping(self): return False

        lifecycle = Lifecycle(self.gate)
        coordinator = MaintenanceCoordinator(self.broker, lifecycle)
        refused = coordinator.stop(force=False)
        self.assertEqual(refused.status, "refused")
        self.assertEqual(refused.inventory.items[0].origin, "unmapped_tui")
        self.assertEqual(refused.workers.to_dict(), {
            "active_names": [], "idle_names": ["idle-worker"],
            "active_count": 0, "idle_count": 1, "total_count": 1})
        self.assertEqual(lifecycle.terminated, 0)

        self.codex.calls = []
        self.codex.call_timeouts = []
        forced = coordinator.stop(force=True)
        self.assertEqual(forced.status, "completed")
        self.assertTrue(forced.forced)
        self.assertEqual(forced.inventory.items[0].thread_id, "tui-thread")
        self.assertIsNone(forced.impact_unavailable_reason)
        self.assertEqual(self.codex.calls[0],
                         ("thread/list", {"sourceKinds": []}))
        inventory_timeout = next(
            timeout for method, timeout in self.codex.call_timeouts
            if method == "thread/list")
        self.assertGreater(inventory_timeout, 0)
        self.assertLessEqual(inventory_timeout,
                             FORCE_INVENTORY_TIMEOUT_SECONDS)
        self.assertEqual(lifecycle.terminated, 1)
        self.codex.calls = []
        restarted = coordinator.restart("ws://127.0.0.1:4600", force=True)
        self.assertEqual(restarted.inventory.items[0].thread_id, "tui-thread")
        self.assertEqual(restarted.listener, "ws://127.0.0.1:4600")
        self.assertIsNone(restarted.impact_unavailable_reason)
        self.assertEqual(lifecycle.terminated, 2)
        self.assertFalse(hasattr(coordinator, "gate"))
        self.assertFalse(hasattr(coordinator, "terminate_owned"))

    def test_restart_refuses_active_inventory_and_reports_validated_listener(self):
        self.codex.thread_pages = {None: {
            "data": [self.active_thread("tui-thread")],
            "nextCursor": None, "backwardsCursor": None,
        }}
        self.codex.thread_reads["tui-thread"] = {"thread": {
            "id": "tui-thread", "status": {"type": "active"},
            "turns": [{"id": "tui-turn", "status": "inProgress"}]}}

        class Lifecycle:
            def __init__(self, gate): self.gate, self.terminated = gate, 0
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                self.terminated += 1
            def stopping(self): return False

        lifecycle = Lifecycle(self.gate)
        coordinator = MaintenanceCoordinator(self.broker, lifecycle)
        refused = coordinator.restart("ws://localhost:4600", force=False)
        self.assertEqual(refused.status, "refused")
        self.assertEqual(refused.listener, "ws://localhost:4600")
        self.assertEqual(lifecycle.terminated, 0)

    def test_nonforce_inventory_error_refuses_without_terminating_service(self):
        self.codex.thread_pages = {None: CodexCallError(
            "transport_error", "thread/list", {"message": "gone"})}

        class Lifecycle:
            def __init__(self, gate): self.gate, self.terminated = gate, 0
            def terminate_owned(self, lease): self.terminated += 1
            def stopping(self): return False

        lifecycle = Lifecycle(self.gate)
        result = MaintenanceCoordinator(self.broker, lifecycle).stop(force=False)
        self.assertEqual((result.status, result.forced), ("refused", False))
        self.assertEqual(result.impact_unavailable_reason,
                         "upstream_inventory_unavailable")
        self.assertEqual(lifecycle.terminated, 0)

    def test_force_skips_unavailable_inventory_and_terminates_owned_lifecycle(self):
        self.codex.thread_pages = {None: CodexCallError(
            "transport_error", "thread/list", {"message": "blocked"})}

        class Lifecycle:
            def __init__(self, gate): self.gate, self.terminated = gate, 0
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                self.terminated += 1
            def stopping(self): return False

        lifecycle = Lifecycle(self.gate)
        result = MaintenanceCoordinator(self.broker, lifecycle).stop(force=True)
        self.assertEqual((result.status, result.forced), ("completed", True))
        self.assertEqual(result.impact_unavailable_reason,
                         "upstream_inventory_unavailable")
        self.assertEqual(self.codex.calls,
                         [("thread/list", {"sourceKinds": []})])
        self.assertEqual(lifecycle.terminated, 1)

    def test_force_inventory_bounds_blocked_send_before_unavailable_fallback(self):
        entered = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        original_call = self.codex.call

        def blocked_call(method, params, timeout=120.0):
            if method == "thread/list":
                entered.set()
                release.wait(timeout=1.0)
                finished.set()
            return original_call(method, params, timeout)

        class Lifecycle:
            def __init__(self, gate): self.gate, self.terminated = gate, 0
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                self.terminated += 1
            def stopping(self): return False

        lifecycle = Lifecycle(self.gate)
        self.codex.call = blocked_call
        started = time.monotonic()
        try:
            with mock.patch("codex_worker.broker.FORCE_INVENTORY_TIMEOUT_SECONDS", 0.05):
                result = MaintenanceCoordinator(
                    self.broker, lifecycle).stop(force=True)
        finally:
            release.set()
        self.assertTrue(entered.is_set())
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(result.impact_unavailable_reason,
                         "upstream_inventory_unavailable")
        self.assertEqual(lifecycle.terminated, 1)
        self.assertTrue(finished.wait(timeout=1.0))

    def test_force_with_unsettled_mutation_never_claims_measured_impact(self):
        entered = threading.Event()
        release = threading.Event()

        def mutate():
            with self.gate.mutation("thread/start"):
                entered.set()
                release.wait(timeout=1.0)

        class Lifecycle:
            def __init__(self, gate): self.gate, self.terminated = gate, 0
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                self.terminated += 1
            def stopping(self): return False

        mutation = threading.Thread(target=mutate)
        mutation.start()
        self.assertTrue(entered.wait(timeout=1.0))
        lifecycle = Lifecycle(self.gate)
        try:
            result = MaintenanceCoordinator(
                self.broker, lifecycle).stop(force=True)
        finally:
            release.set()
            mutation.join(timeout=1.0)

        self.assertEqual(result.impact_unavailable_reason,
                         "upstream_inventory_unavailable")
        self.assertEqual(self.codex.calls, [])
        self.assertEqual(lifecycle.terminated, 1)

    def test_owned_teardown_error_is_a_typed_maintenance_failure(self):
        from codex_worker.broker import MaintenanceTerminationError
        from codex_worker.service import OwnedTeardownError

        class Lifecycle:
            def __init__(self, gate): self.gate = gate
            def stopping(self): return False
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                raise OwnedTeardownError("OSError")

        with self.assertRaises(MaintenanceTerminationError) as caught:
            MaintenanceCoordinator(self.broker, Lifecycle(self.gate)).stop(force=True)
        self.assertEqual(caught.exception.cause, "OSError")

    def test_stop_queued_behind_force_converges_without_closed_transport_inventory(self):
        self.registry.create_worker(
            "idle-thread", self.cwd, "known-idle", "medium",
            "fake-model-a", "medium", "full")
        entered = threading.Event()
        release = threading.Event()

        class Lifecycle:
            def __init__(self, gate):
                self.gate = gate
                self.is_stopping = False
            def stopping(self):
                return self.is_stopping
            def terminate_owned(self, lease):
                self.gate.authorize(lease)
                self.is_stopping = True
                entered.set()
                release.wait(timeout=1.0)

        lifecycle = Lifecycle(self.gate)
        coordinator = MaintenanceCoordinator(self.broker, lifecycle)
        with ThreadPoolExecutor(max_workers=2) as pool:
            forced = pool.submit(coordinator.stop, True)
            self.assertTrue(entered.wait(timeout=1.0))
            self.codex.thread_pages = {None: CodexCallError(
                "transport_error", "thread/list", {"message": "connection closed"})}
            queued = pool.submit(coordinator.stop, False)
            release.set()
            first = forced.result(timeout=1.0)
            second = queued.result(timeout=1.0)

        self.assertEqual((first.status, first.forced), ("completed", True))
        self.assertEqual((second.status, second.forced), ("completed", False))
        self.assertEqual(second.inventory.to_dict(), {"items": []})
        self.assertEqual(second.workers.to_dict(), {
            "active_names": [], "idle_names": ["known-idle"],
            "active_count": 0, "idle_count": 1, "total_count": 1,
        })

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

    def test_status_keeps_persisted_session_detached_until_explicit_resume(self):
        selector = self.start_session()
        detached = WorkerBroker(
            self.registry, self.codex, RuntimeStore(event_limit=5),
            socket_path=str(Path(self.cwd) / "replacement.sock"),
            state_path=self.state_path, daemon_pid=5678,
            gate=ServiceMaintenanceGate(), listener="ws://127.0.0.1:4500",
        )
        self.codex.calls = []
        result = detached.turn_status(selector)
        self.assertFalse(result["attached"])
        self.assertEqual(self.codex.calls, [])

    def test_status_reconciles_attached_thread_from_authoritative_tui_state(self):
        selector = self.start_session()
        self.codex.thread_reads["thr-start"] = {"thread": {
            "id": "thr-start",
            "status": {"type": "active", "activeFlags": []},
            "turns": [{"id": "tui-turn", "status": "inProgress", "items": []}],
        }}
        self.codex.calls = []
        active = self.broker.turn_status(selector)
        self.assertEqual(active["active_turn_id"], "tui-turn")
        self.assertEqual(self.codex.calls, [("thread/read", {
            "threadId": "thr-start", "includeTurns": True,
        })])

        self.codex.thread_reads["thr-start"] = {"thread": {
            "id": "thr-start",
            "status": {"type": "idle"},
            "turns": [{"id": "tui-turn", "status": "completed", "items": [{
                "id": "upstream-message", "type": "agentMessage", "text": "done",
            }]}],
        }}
        terminal = self.broker.turn_status(selector)
        self.assertEqual(terminal["latest_turn"]["turn_id"], "tui-turn")
        record = self.registry.resolve(selector)
        messages, _, _ = self.runtime.agent_messages(record.session_id, 10)
        self.assertEqual([item.item_id for item in messages], ["upstream-message"])
        self.assertEqual(self.runtime.events(record.session_id, 0, 10).events, [])

    def test_history_page_reconciles_attached_runtime_before_returning_provider_page(self):
        selector = self.start_session()
        self.codex.thread_reads["thr-start"] = {"thread": {
            "id": "thr-start", "status": {"type": "idle"},
            "turns": [{"id": "tui-terminal", "status": "completed", "items": []}],
        }}
        self.codex.turn_pages[None] = {
            "data": [{"id": "tui-terminal", "status": "completed", "items": []}],
            "nextCursor": "older", "backwardsCursor": None,
        }
        self.codex.calls = []
        page = self.broker.turn_history(selector, limit=10)
        self.assertEqual(page["turns"][0]["id"], "tui-terminal")
        self.assertEqual(page["attach"]["thread_id"], "thr-start")
        self.assertEqual(self.runtime.status(
            self.registry.resolve(selector).session_id).latest_turn.turn_id,
            "tui-terminal")
        self.assertEqual(self.codex.calls, [
            ("thread/read", {"threadId": "thr-start", "includeTurns": True}),
            ("thread/turns/list", {"threadId": "thr-start", "sortDirection": "desc",
                                   "itemsView": "full", "limit": 10}),
        ])

    def test_preserved_common_start_persists_policy_in_one_registry_record(self):
        from codex_worker.broker import AnnotationPolicy, SessionStartSpec
        from codex_worker.commands import AccessMode
        result = self.broker.start_session(SessionStartSpec(
            self.cwd, "common", "fake-model-a", AccessMode.FULL, "medium", "medium",
            AnnotationPolicy.PRESERVE_WORKER_POLICY))
        record = self.registry.resolve(IdentifierSelector(session_id=result["session"]["session_id"]))
        self.assertEqual((record.tier, record.model, record.effort, record.access),
                         ("medium", "fake-model-a", "medium", "full"))

    def test_worker_config_is_sent_on_thread_start_and_persisted(self):
        from codex_worker.broker import AnnotationPolicy, SessionStartSpec
        from codex_worker.commands import AccessMode
        result = self.broker.start_session(SessionStartSpec(
            self.cwd, "search", "fake-model-a", AccessMode.READ_ONLY, "medium", "medium",
            AnnotationPolicy.PRESERVE_WORKER_POLICY, config={"web_search": "live"}))
        self.assertEqual(self.codex.start_calls[-1]["config"], {"web_search": "live"})
        self.assertEqual(result["session"]["config"], {"web_search": "live"})
        record = self.registry.resolve(IdentifierSelector(session_id=result["session"]["session_id"]))
        self.assertEqual(record.config, {"web_search": "live"})

    def test_raw_session_start_refuses_config_it_could_not_persist(self):
        from codex_worker.broker import SessionStartSpec
        with self.assertRaises(RpcFault) as caught:
            self.broker.start_session(SessionStartSpec(self.cwd, None, None,
                                                       config={"web_search": "live"}))
        self.assertEqual(caught.exception.kind, "invalid_params")
        self.assertEqual(self.codex.start_calls, [])
        self.assertEqual(self.registry.list(), [])

    def test_session_without_config_sends_no_config(self):
        self.broker.session_start(self.cwd)
        self.assertIsNone(self.codex.start_calls[-1]["config"])

    def test_existing_worker_resume_reapplies_creation_config(self):
        record = self.registry.create_worker("thr-search", self.cwd, "search", "medium", "fake-model-a",
                                             "medium", "read_only", config={"web_search": "live"})
        self.codex.resume_result = {"thread": {"id": "thr-search", "cwd": self.cwd}}
        self.broker.session_resume(IdentifierSelector(session_id=record.session_id))
        self.assertEqual(self.codex.resume_calls[-1]["config"], {"web_search": "live"})
        self.assertEqual(self.codex.resume_calls[-1]["sandbox"], "read-only")

    def test_native_proxy_rejects_malformed_provider_result(self):
        from codex_worker.broker import NativeCodexProxy
        class Raw:
            def call(self, method, params):
                return {"unexpected": True}
        with self.assertRaises(CodexCallError) as caught:
            NativeCodexProxy(Raw()).rate_limits_read()
        self.assertEqual(caught.exception.kind, "protocol_error")

    def test_native_proxy_accepts_additive_rate_limit_envelope_fields(self):
        from codex_worker.broker import NativeCodexProxy
        class Raw:
            def call(self, method, params):
                return {
                    "rateLimits": {"primary": {"usedPercent": 21}},
                    "rateLimitsByLimitId": {"codex": {"primary": {"usedPercent": 21}}},
                    "rateLimitResetCredits": {"availableCount": 0, "credits": []},
                }

        value = NativeCodexProxy(Raw()).rate_limits_read()

        self.assertEqual(value["rateLimits"]["primary"]["usedPercent"], 21)

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
            "session_count": 0, "worker_names": [],
            "worker_version": distribution_version(),
        })
        models = self.broker.model_list()
        self.assertEqual(models["models"], [
            {"id": "fake-model-a", "is_default": True, "supported_efforts": ["medium"]},
            {"id": "fake-model-b", "is_default": False, "supported_efforts": ["high", "medium"]},
        ])

    def test_daemon_version_is_immutable_when_installed_metadata_changes(self):
        with mock.patch("codex_worker.broker.distribution_version", return_value="7.10.0"):
            broker = WorkerBroker(
                self.registry, self.codex, self.runtime, str(Path(self.cwd) / "worker.sock"),
                self.state_path, daemon_pid=1234,
            )
        with mock.patch("codex_worker.broker.distribution_version", return_value="7.10.1"):
            status = broker.daemon_status()
        self.assertEqual(status["worker_version"], "7.10.0")

    def test_session_start_validates_live_model_and_persists_immutable_cwd(self):
        with self.assertRaises(ModelSelectionError):
            self.broker.session_start(self.cwd, name="bad", model="not-live")
        result = self.broker.session_start(self.cwd, name="worker", model="fake-model-a")
        self.assertTrue(result["attached"])
        self.assertEqual(result["session"]["cwd"], self.cwd)
        self.assertEqual(result["session"]["model"], "fake-model-a")
        self.assertEqual(self.codex.start_calls[-1], {"cwd": self.cwd, "model": "fake-model-a",
                                                      "sandbox": "danger-full-access",
                                                      "allowProviderModelFallback": False,
                                                      "config": None})
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

    def test_post_upstream_start_cwd_mismatch_preserves_created_thread_identity(self):
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        self.codex.start_result = {"thread": {"id": "thr-cwd-drift", "cwd": other.name}}
        with self.assertRaises(RpcFault) as caught:
            self.broker.session_start(self.cwd)
        fault = caught.exception
        self.assertEqual(fault.kind, "session_cwd_mismatch")
        self.assertEqual(fault.details["thread_id"], "thr-cwd-drift")
        UUID(fault.details["session_id"])
        self.assertEqual(fault.details["attach"]["thread_id"], "thr-cwd-drift")

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
        self.assertEqual(caught.exception.details["session_id"], selector.session_id)
        self.assertEqual(caught.exception.details["thread_id"], "thr-start")
        self.assertEqual(caught.exception.details["attach"]["thread_id"], "thr-start")
        self.assertFalse(self.broker.session_show(selector)["attached"])

    def test_unknown_uuid_is_typed_and_unknown_thread_requires_explicit_resume(self):
        with self.assertRaises(RpcFault) as unknown_uuid:
            self.broker.session_show(IdentifierSelector(session_id="00000000-0000-0000-0000-000000000099"))
        self.assertEqual(unknown_uuid.exception.kind, "unknown_session")
        self.assertEqual(
            unknown_uuid.exception.recovery,
            "codex-worker session list",
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
        self.assertEqual(caught.exception.details["session_id"], session.session_id)
        self.assertEqual(caught.exception.details["thread_id"], "thr-start")
        self.assertEqual(caught.exception.details["turn_id"], "turn-response")
        self.assertEqual(caught.exception.details["attach"]["thread_id"], "thr-start")
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

    def test_post_upstream_steer_identity_mismatch_preserves_worker_identity(self):
        session = self.start_session()
        self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        self.codex.steer_return_id = "different-turn"
        with self.assertRaises(RpcFault) as caught:
            self.broker.turn_steer(session, "narrow")
        fault = caught.exception
        self.assertEqual(fault.kind, "codex_protocol_error")
        self.assertEqual(fault.details["session_id"], session.session_id)
        self.assertEqual(fault.details["thread_id"], "thr-start")
        self.assertEqual(fault.details["turn_id"], "turn-1")
        self.assertEqual(fault.details["returned_turn_id"], "different-turn")
        self.assertEqual(fault.details["attach"]["thread_id"], "thr-start")

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
        self.assertEqual(fault.details["attach"]["thread_id"], "thr-start")
        self.assertEqual(
            fault.details["attach"]["resume_command"],
            "codex --remote ws://127.0.0.1:4500 resume thr-start",
        )
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
            "attach": {
                "listener": "ws://127.0.0.1:4500",
                "thread_id": "thr-start",
                "attach_command": "codex --remote ws://127.0.0.1:4500",
                "resume_command": "codex --remote ws://127.0.0.1:4500 resume thr-start",
            },
        })
        self.assertEqual(fault.recovery,
                         "codex-worker turn status --session %s" % session.session_id)
        self.assertEqual(self.broker.turn_status(session)["active_turn_id"], "turn-1")

    def test_interrupt_completes_active_turn_and_idle_race_is_typed(self):
        session = self.start_session()
        self.broker.turn_start(session, "task", model="fake-model-a", effort="medium")
        interrupted = self.broker.turn_interrupt(session)
        self.assertTrue(interrupted["accepted"])
        waited = self.broker.turn_wait(session, 0)
        self.assertEqual(waited["turn"]["status"], "interrupted")
        self.assertEqual(waited["attach"]["thread_id"], waited["thread_id"])
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
            "codex-worker turn status --session %s" % session.session_id,
            "codex-worker turn wait --session %s --timeout 30" % session.session_id,
            "codex-worker turn interrupt --session %s" % session.session_id,
        ])
        page = self.broker.turn_events(session, after=0, limit=3)
        self.assertEqual(page["next_cursor"], 0)
        self.assertFalse(page["truncated"])
        self.assertEqual(page["attach"]["thread_id"], "thr-start")

    def test_shutdown_delegates_without_deleting_registry(self):
        self.start_session()
        self.assertEqual(self.broker.shutdown(), {"accepted": True})
        self.assertTrue(self.codex.shutdown_called)
        self.assertEqual(len(SessionRegistry(self.state_path).list()), 1)


if __name__ == "__main__":
    unittest.main()
