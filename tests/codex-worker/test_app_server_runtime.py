import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.app_server import CodexAppServer, CodexCallError, CodexTransportError
from codex_worker.models import ErrorDetail, SessionRecord
from codex_worker.runtime import (
    CodexProtocolError,
    NoTurn,
    RuntimeStore,
    TurnActive,
    WaitTimeout,
)


class AppServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = self.tempdir.name
        self.clients = []
        self.notifications = []

    def tearDown(self):
        for client in self.clients:
            client.shutdown()
        self.tempdir.cleanup()

    def make_client(self, mode="normal", delay=0.03, callback=None):
        fake = Path(__file__).with_name("fake_codex.py")
        client = CodexAppServer(
            self.cwd,
            [sys.executable, str(fake), "--mode", mode, "--delay", str(delay)],
            callback or self.notifications.append,
        )
        self.clients.append(client)
        return client

    def test_handshake_and_wrappers_use_measured_wire_shapes(self):
        client = self.make_client()
        self.assertEqual(client.list_models()[0]["id"], "fake-model-a")
        started = client.start_thread(self.cwd, model="fake-model-b")
        self.assertEqual(started["thread"]["id"], "thr-fake")
        resumed = client.resume_thread("thr-resumed")
        self.assertEqual(resumed["thread"]["id"], "thr-resumed")
        turn_id = client.start_turn("thr-resumed", "do work", model="fake-model-a", effort="medium")
        self.assertEqual(client.steer("thr-resumed", turn_id, "narrow"), turn_id)
        client.interrupt("thr-resumed", turn_id)

    def test_concurrent_calls_do_not_interleave_json_lines(self):
        client = self.make_client()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: client.list_models(), range(40)))
        self.assertTrue(all(result[0]["id"] == "fake-model-a" for result in results))

    def test_measured_approval_methods_fail_closed_with_schema_valid_shapes_and_safe_audit(self):
        cases = {
            "approval-command": {"decision": "decline"},
            "approval-file": {"decision": "decline"},
            "approval-user": {"answers": {}},
            "approval-permissions": {"permissions": {}},
        }
        for mode, expected_response in cases.items():
            observed = []
            client = self.make_client(mode=mode, callback=observed.append)
            client.start_thread(self.cwd)
            client.start_turn("thr-fake", "contains SECRET")
            deadline = time.monotonic() + 2
            while not (any(x.get("method") == "approval/declined" for x in observed)
                       and any(x.get("method") == "item/completed" for x in observed)):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.005)
            safe = [x for x in observed if x.get("method") == "approval/declined"]
            self.assertEqual(len(safe), 1)
            self.assertNotIn("SECRET", repr(safe))
            self.assertIn("approvalMethod", safe[0]["params"])
            completed = next(x for x in observed if x.get("method") == "item/completed")
            self.assertEqual(completed["params"]["item"]["decision"], expected_response)

    def test_custom_approval_handler_response_is_used(self):
        fake = Path(__file__).with_name("fake_codex.py")
        observed = []
        client = CodexAppServer(
            self.cwd,
            [sys.executable, str(fake), "--mode", "approval-command"],
            observed.append,
            approval_handler=lambda _: {"decision": "accept"},
        )
        self.clients.append(client)
        client.start_thread(self.cwd)
        client.start_turn("thr-fake", "work")
        deadline = time.monotonic() + 2
        while not any(x.get("method") == "item/completed" for x in observed):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.005)
        item = next(x for x in observed if x.get("method") == "item/completed")
        self.assertEqual(item["params"]["item"]["decision"], {"decision": "accept"})
        self.assertFalse(any(x.get("method") == "approval/declined" for x in observed))

    def test_failing_custom_approval_handler_still_fails_closed(self):
        fake = Path(__file__).with_name("fake_codex.py")
        observed = []

        def broken_handler(_):
            raise RuntimeError("handler failed")

        client = CodexAppServer(
            self.cwd,
            [sys.executable, str(fake), "--mode", "approval-command"],
            observed.append,
            approval_handler=broken_handler,
        )
        self.clients.append(client)
        client.start_thread(self.cwd)
        client.start_turn("thr-fake", "work")
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline and not any(
                x.get("method") == "approval/declined" for x in observed):
            time.sleep(0.005)
        self.assertTrue(any(x.get("method") == "approval/declined" for x in observed))

    def test_malformed_output_fails_all_pending_calls(self):
        client = self.make_client(mode="malformed")
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(client.list_models) for _ in range(4)]
        for future in futures:
            with self.assertRaises(CodexTransportError):
                future.result()
        with self.assertRaises(CodexTransportError):
            client.list_models()

    def test_malformed_output_terminates_reaps_child_and_closes_all_pipes(self):
        client = self.make_client(mode="malformed")
        with self.assertRaises(CodexTransportError):
            client.list_models()
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and (
                client.proc.poll() is None
                or not all(pipe.closed for pipe in (client.proc.stdin, client.proc.stdout, client.proc.stderr))):
            time.sleep(0.005)
        self.assertIsNotNone(client.proc.poll())
        self.assertTrue(all(pipe.closed for pipe in (client.proc.stdin, client.proc.stdout, client.proc.stderr)))

    def test_child_exit_fails_call_instead_of_hanging(self):
        client = self.make_client(mode="exit")
        with self.assertRaises(CodexTransportError):
            client.list_models()

    def test_upstream_error_is_typed(self):
        client = self.make_client()
        with self.assertRaises(CodexCallError) as caught:
            client.call("unknown/test")
        self.assertEqual(caught.exception.kind, "upstream_error")
        self.assertEqual(caught.exception.method, "unknown/test")

    def test_shutdown_is_idempotent_and_rejects_future_calls(self):
        client = self.make_client()
        client.shutdown()
        client.shutdown()
        self.assertTrue(client.proc.stdin.closed)
        self.assertTrue(client.proc.stdout.closed)
        self.assertTrue(client.proc.stderr.closed)
        with self.assertRaises(CodexTransportError):
            client.list_models()


class RuntimeStoreTests(unittest.TestCase):
    def setUp(self):
        self.session = SessionRecord(
            "00000000-0000-0000-0000-000000000001",
            "thr-1",
            "/tmp",
            "2026-08-18T00:00:00Z",
            "2026-08-18T00:00:00Z",
        )
        self.store = RuntimeStore(event_limit=3)
        self.store.attach(self.session)

    def started(self, turn_id="turn-1"):
        return {"method": "turn/started", "params": {
            "threadId": self.session.thread_id,
            "turn": {"id": turn_id, "status": "inProgress", "items": []},
        }}

    def completed(self, turn_id="turn-1", status="completed", error=None):
        return {"method": "turn/completed", "params": {
            "threadId": self.session.thread_id,
            "turn": {"id": turn_id, "status": status, "items": [], "error": error},
        }}

    def item(self, index, turn_id="turn-1"):
        return {"method": "item/completed", "params": {
            "threadId": self.session.thread_id,
            "turnId": turn_id,
            "item": {"id": "item-%s" % index, "type": "agentMessage", "text": str(index)},
        }}

    def test_all_waiters_observe_same_completion_without_consuming_it(self):
        self.store.reserve_start(self.session.session_id)
        self.store.on_notification(self.started())
        self.store.reconcile_start(self.session.session_id, "turn-1")
        with ThreadPoolExecutor(max_workers=2) as pool:
            waits = [pool.submit(self.store.wait, self.session.session_id, 2.0) for _ in range(2)]
            self.store.on_notification(self.item(1))
            self.store.on_notification(self.completed())
        snapshots = [future.result() for future in waits]
        self.assertEqual([x.turn_id for x in snapshots], ["turn-1", "turn-1"])
        self.assertIs(snapshots[0], snapshots[1])
        self.assertIs(self.store.wait(self.session.session_id, 0), snapshots[0])
        self.assertEqual(snapshots[0].items[0].data["text"], "1")

    def test_wait_blocks_while_start_is_reserved_before_started_notification(self):
        self.store.reserve_start(self.session.session_id)
        result = []
        waiter = threading.Thread(target=lambda: result.append(self.store.wait(self.session.session_id, 1)))
        waiter.start()
        time.sleep(0.02)
        self.assertTrue(waiter.is_alive())
        self.store.on_notification(self.started())
        self.store.on_notification(self.completed())
        waiter.join(1)
        self.assertEqual(result[0].turn_id, "turn-1")

    def test_event_page_marks_evicted_cursor_and_is_exclusive(self):
        for index in range(3):
            self.store.on_notification(self.item(index))
        self.store.on_notification(self.started())
        page = self.store.events(self.session.session_id, after=0, limit=10)
        self.assertTrue(page.truncated)
        self.assertEqual([event.cursor for event in page.events], [2, 3, 4])
        self.assertEqual(self.store.events(self.session.session_id, after=3, limit=10).events[0].cursor, 4)
        self.assertEqual(page.next_cursor, 4)

    def test_events_normalize_only_authoritative_methods(self):
        self.store.on_notification({"method": "item/started", "params": {"threadId": "thr-1"}})
        self.store.on_notification({"method": "item/agentMessage/delta", "params": {"threadId": "thr-1"}})
        self.store.on_notification(self.item(1))
        self.assertEqual([event.event for event in self.store.events(self.session.session_id, 0, 10).events], ["item_completed"])

    def test_reserve_is_atomic_and_cancel_releases_it(self):
        self.store.reserve_start(self.session.session_id)
        with self.assertRaises(TurnActive):
            self.store.reserve_start(self.session.session_id)
        self.store.cancel_start(self.session.session_id)
        self.store.reserve_start(self.session.session_id)

    def test_reconcile_synthesizes_active_only_without_notification(self):
        self.store.reserve_start(self.session.session_id)
        self.store.reconcile_start(self.session.session_id, "turn-response")
        self.assertEqual(self.store.status(self.session.session_id).active_turn_id, "turn-response")

    def test_reconcile_accepts_started_and_completed_before_response(self):
        self.store.reserve_start(self.session.session_id)
        self.store.on_notification(self.started("turn-race"))
        self.store.on_notification(self.completed("turn-race"))
        self.store.reconcile_start(self.session.session_id, "turn-race")
        status = self.store.status(self.session.session_id)
        self.assertIsNone(status.active_turn_id)
        self.assertEqual(status.latest_turn.turn_id, "turn-race")
        self.store.reserve_start(self.session.session_id)

    def test_reconcile_rejects_response_notification_id_mismatch(self):
        self.store.reserve_start(self.session.session_id)
        self.store.on_notification(self.started("turn-notified"))
        self.store.on_notification(self.completed("turn-notified"))
        with self.assertRaises(CodexProtocolError):
            self.store.reconcile_start(self.session.session_id, "turn-response")

    def test_terminal_notification_identity_supersedes_started_identity(self):
        self.store.reserve_start(self.session.session_id)
        self.store.on_notification(self.started("turn-started"))
        self.store.on_notification(self.completed("turn-terminal"))
        with self.assertRaises(CodexProtocolError):
            self.store.reconcile_start(self.session.session_id, "turn-started")

    def test_completion_notification_owns_terminal_identity_and_error(self):
        self.store.on_notification(self.started("turn-failed"))
        upstream_error = {"message": "bad", "codexErrorInfo": "SandboxError"}
        self.store.on_notification(self.completed("turn-failed", "failed", upstream_error))
        snapshot = self.store.status(self.session.session_id).latest_turn
        self.assertEqual(snapshot.status, "failed")
        self.assertEqual(snapshot.error.kind, "codex_turn_failed")
        self.assertEqual(snapshot.error.details["codexErrorInfo"], "SandboxError")

    def test_wait_timeout_and_no_turn_are_distinct(self):
        with self.assertRaises(NoTurn):
            self.store.wait(self.session.session_id, 0)
        self.store.reserve_start(self.session.session_id)
        with self.assertRaises(WaitTimeout):
            self.store.wait(self.session.session_id, 0.01)

    def test_detach_marks_status_emits_transport_error_and_wakes_waiter(self):
        self.store.on_notification(self.started("turn-lost"))
        with ThreadPoolExecutor(max_workers=1) as pool:
            waiter = pool.submit(self.store.wait, self.session.session_id, 1)
            self.store.detach_all(ErrorDetail("transport_error", details={"message": "child exited"}))
            snapshot = waiter.result()
        status = self.store.status(self.session.session_id)
        self.assertFalse(status.attached)
        self.assertEqual(snapshot.status, "failed")
        self.assertEqual(snapshot.error.kind, "transport_error")
        self.assertEqual(self.store.events(self.session.session_id, 0, 10).events[-1].event, "transport_error")

    def test_approval_decline_notification_is_safely_normalized(self):
        self.store.on_notification({"method": "approval/declined", "params": {
            "threadId": "thr-1", "turnId": "turn-1", "requestId": 7,
            "approvalMethod": "item/commandExecution/requestApproval", "decision": "decline",
        }})
        event = self.store.events(self.session.session_id, 0, 10).events[0]
        self.assertEqual(event.event, "approval_declined")
        self.assertEqual(event.item.type, "item/commandExecution/requestApproval")
        self.assertNotIn("prompt", event.item.data)

    def test_unknown_thread_notifications_are_ignored(self):
        message = self.started()
        message["params"]["threadId"] = "thr-other"
        self.store.on_notification(message)
        self.assertEqual(self.store.events(self.session.session_id, 0, 10).events, [])


class AdapterRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = self.tempdir.name
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.shutdown()
        self.tempdir.cleanup()

    def make_pair(self, mode):
        store = RuntimeStore(event_limit=20)
        record = SessionRecord(
            "00000000-0000-0000-0000-000000000009",
            "thr-fake",
            self.cwd,
            "2026-08-18T00:00:00Z",
            "2026-08-18T00:00:00Z",
        )
        store.attach(record)
        fake = Path(__file__).with_name("fake_codex.py")
        client = CodexAppServer(
            self.cwd, [sys.executable, str(fake), "--mode", mode], store.on_notification
        )
        self.clients.append(client)
        client.start_thread(self.cwd)
        return client, store, record

    def test_actual_jsonl_completion_before_response_reconciles_terminal_state(self):
        client, store, record = self.make_pair("complete-before-response")
        store.reserve_start(record.session_id)
        turn_id = client.start_turn(record.thread_id, "work")
        store.reconcile_start(record.session_id, turn_id)
        self.assertEqual(store.wait(record.session_id, 0).turn_id, turn_id)
        self.assertIsNone(store.status(record.session_id).active_turn_id)
        store.reserve_start(record.session_id)

    def test_actual_jsonl_mismatched_response_id_is_protocol_error(self):
        client, store, record = self.make_pair("mismatch-before-response")
        store.reserve_start(record.session_id)
        turn_id = client.start_turn(record.thread_id, "work")
        with self.assertRaises(CodexProtocolError):
            store.reconcile_start(record.session_id, turn_id)

    def test_actual_child_exit_detaches_runtime_and_records_transport_event(self):
        client, store, record = self.make_pair("exit")
        with self.assertRaises(CodexTransportError):
            client.list_models()
        deadline = time.monotonic() + 1
        while store.status(record.session_id).attached and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertFalse(store.status(record.session_id).attached)
        self.assertEqual(store.events(record.session_id, 0, 10).events[-1].event, "transport_error")


if __name__ == "__main__":
    unittest.main()
