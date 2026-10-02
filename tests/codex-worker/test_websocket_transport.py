import ast
import json
import queue
import sys
import threading
import time
import types
import unittest
from unittest import mock
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.websocket_transport import (
    MAX_FRAME_BYTES,
    CodexCallError,
    CodexConnection,
    CodexConnectionDeps,
    CodexMethodAdapter,
    CodexTransportError,
    _default_connect,
)


class FakeTextConnection:
    def __init__(self, responder):
        self.responder = responder
        self.sent = []
        self.incoming = queue.Queue()
        self.closed = False

    def send(self, frame):
        if self.closed:
            raise OSError("closed")
        self.sent.append(frame)
        value = json.loads(frame)
        responses = self.responder(value)
        if responses is None:
            return
        if not isinstance(responses, list):
            responses = [responses]
        for response in responses:
            self.incoming.put(response if isinstance(response, (str, bytes)) else json.dumps(response))

    def recv(self, timeout=None):
        value = self.incoming.get(timeout=timeout)
        if value is _CLOSED:
            raise OSError("closed")
        return value

    def close(self):
        if not self.closed:
            self.closed = True
            self.incoming.put(_CLOSED)

    def inject(self, value):
        self.incoming.put(value if isinstance(value, (str, bytes)) else json.dumps(value))


_CLOSED = object()


def no_sleep(_delay):
    return None


def no_jitter(_delay):
    return 0.0


class ConnectionFactory:
    def __init__(self, responders):
        self.responders = list(responders)
        self.connections = []
        self.calls = []

    def __call__(self, endpoint, max_frame_bytes, max_queue):
        self.calls.append((endpoint, max_frame_bytes, max_queue))
        connection = FakeTextConnection(self.responders.pop(0))
        self.connections.append(connection)
        return connection


def success_responder(message):
    if "id" not in message or "method" not in message:
        return None
    return {"id": message["id"], "result": {"method": message["method"]}}


class WebSocketTransportTests(unittest.TestCase):
    def make_client(self, responders=None, notifications=None, approval_handler=None):
        factory = ConnectionFactory(responders or [success_responder])
        observed = [] if notifications is None else notifications
        client = CodexConnection(
            "unix:///private/codex.sock",
            observed.append,
            approval_handler,
            CodexConnectionDeps(factory, no_sleep, no_jitter),
        )
        self.addCleanup(client.close)
        return client, factory

    def test_one_text_frame_per_message_and_one_handshake(self):
        client, factory = self.make_client()
        result = client.call("thread/read", {"threadId": "thread-1"}, timeout=1)
        self.assertEqual(result, {"method": "thread/read"})
        sent = [json.loads(frame) for frame in factory.connections[0].sent]
        self.assertEqual([message["method"] for message in sent], [
            "initialize", "initialized", "thread/read",
        ])
        self.assertTrue(all(not frame.endswith("\n") for frame in factory.connections[0].sent))
        self.assertEqual(factory.calls, [("unix:///private/codex.sock", MAX_FRAME_BYTES, 2)])

    def test_large_plugin_catalog_does_not_reconnect_or_break_followup(self):
        payload = "x" * (12 * 1024 * 1024)

        def responder(message):
            if message.get("method") == "plugin/list":
                return {"id": message["id"], "result": {"catalog": payload}}
            return success_responder(message)

        client, factory = self.make_client([responder])
        self.assertEqual(client.call("plugin/list", {}, timeout=3), {"catalog": payload})
        self.assertEqual(client.call("thread/list", {}, timeout=1), {"method": "thread/list"})
        self.assertEqual(len(factory.connections), 1)

    def test_non_finite_outbound_value_is_refused_without_serializing_a_frame(self):
        client, factory = self.make_client()
        before = list(factory.connections[0].sent)
        with self.assertRaises(CodexCallError) as caught:
            client.call("thread/read", {"value": float("nan")}, timeout=1)
        self.assertEqual(caught.exception.kind, "protocol_error")
        self.assertEqual(factory.connections[0].sent, before)

    def test_correlates_concurrent_requests_and_delivers_notifications(self):
        notifications = []

        def responder(message):
            if message.get("method") == "initialized":
                return None
            if message["method"] == "initialize":
                return {"id": message["id"], "result": {}}
            delay = 0.02 if message["params"]["value"] % 2 else 0.001

            def respond():
                time.sleep(delay)
                connection.inject({"id": message["id"], "result": {"value": message["params"]["value"]}})

            threading.Thread(target=respond, daemon=True).start()
            return None

        client, factory = self.make_client([responder], notifications)
        connection = factory.connections[0]
        connection.inject({"method": "turn/started", "params": {"turn": {"id": "turn-1"}}})
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(client.call, "thread/read", {"value": value}, 1) for value in range(12)]
            self.assertEqual([future.result()["value"] for future in futures], list(range(12)))
        self.assertEqual(notifications[0]["method"], "turn/started")

    def test_server_request_uses_approval_handler_and_safe_decline_event(self):
        notifications = []
        client, factory = self.make_client(
            notifications=notifications,
            approval_handler=lambda _message: {"decision": "decline"},
        )
        connection = factory.connections[0]
        connection.inject({
            "id": "approval-1",
            "method": "item/commandExecution/requestApproval",
            "params": {"threadId": "thread-1", "turnId": "turn-1", "secret": "DO-NOT-LEAK"},
        })
        deadline = time.monotonic() + 1
        while len(connection.sent) < 3:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(json.loads(connection.sent[-1]), {
            "id": "approval-1", "result": {"decision": "decline"},
        })
        self.assertNotIn("DO-NOT-LEAK", repr(notifications))
        self.assertEqual(notifications[-1]["method"], "approval/declined")

    def test_blocked_approval_handler_does_not_block_response_reader(self):
        approval_started = threading.Event()
        release_approval = threading.Event()
        handled = []

        def approval_handler(message):
            handled.append(message["id"])
            approval_started.set()
            if message["id"] == "approval-blocked":
                release_approval.wait(1)
            return {"decision": "decline"}

        client, factory = self.make_client(approval_handler=approval_handler)
        factory.connections[0].inject({
            "id": "approval-blocked",
            "method": "item/commandExecution/requestApproval",
            "params": {},
        })
        self.assertTrue(approval_started.wait(1))
        factory.connections[0].inject({
            "id": "approval-queued",
            "method": "item/fileChange/requestApproval",
            "params": {},
        })
        try:
            self.assertEqual(client.call("thread/read", {}, 0.2),
                             {"method": "thread/read"})
        finally:
            release_approval.set()
        deadline = time.monotonic() + 1
        while len([
                frame for frame in factory.connections[0].sent
                if json.loads(frame).get("id") in
                ("approval-blocked", "approval-queued")]) < 2:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        approval_responses = [
            json.loads(frame)["id"] for frame in factory.connections[0].sent
            if "result" in json.loads(frame) and
            json.loads(frame).get("id") in ("approval-blocked", "approval-queued")
        ]
        self.assertEqual(approval_responses, handled)

    def test_non_finite_approval_result_fails_transport_without_emitting_frame(self):
        notifications = []
        client, factory = self.make_client(
            notifications=notifications,
            approval_handler=lambda _message: {"decision": float("nan")},
        )
        before = list(factory.connections[0].sent)
        factory.connections[0].inject({
            "id": "approval-nan",
            "method": "item/commandExecution/requestApproval",
            "params": {},
        })
        deadline = time.monotonic() + 1
        while not factory.connections[0].closed:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(factory.connections[0].sent, before)
        self.assertEqual(notifications[-1]["method"], "transport/error")

    def test_close_and_oversized_frames_fail_all_waiters(self):
        def responder(message):
            if message.get("method") == "initialize":
                return {"id": message["id"], "result": {}}
            return None

        client, factory = self.make_client([responder])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.call, "thread/read", {"n": value}, 2) for value in range(2)]
            deadline = time.monotonic() + 1
            while len(factory.connections[0].sent) < 4:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.001)
            factory.connections[0].inject("x" * (MAX_FRAME_BYTES + 1))
            for future in futures:
                with self.assertRaises(CodexTransportError):
                    future.result()
        with self.assertRaises(CodexTransportError):
            client.call("thread/read", {}, 0.01)

    def test_malformed_boolean_response_id_fails_transport_not_correlation(self):
        def responder(message):
            if message.get("method") == "initialize":
                return {"id": message["id"], "result": {}}
            if message.get("method") == "initialized":
                return None
            return {"id": True, "result": {"wrong": True}}

        client, _factory = self.make_client([responder])
        with self.assertRaises(CodexTransportError):
            client.call("thread/read", {}, 0.2)

    def test_malformed_id_bearing_response_envelopes_fail_transport(self):
        def malformed_response(shape):
            def responder(message):
                if message.get("method") == "initialize":
                    return {"id": message["id"], "result": {}}
                if message.get("method") == "initialized":
                    return None
                return shape(message["id"])
            return responder

        shapes = (
            lambda request_id: {"id": request_id, "method": None, "result": {}},
            lambda request_id: {"jsonrpc": "1.0", "id": request_id, "result": {}},
            lambda request_id: {"id": request_id, "result": {}, "error": {}},
            lambda request_id: {"id": request_id, "error": "busy"},
        )
        for shape in shapes:
            with self.subTest(shape=shape(7)):
                client, _factory = self.make_client([malformed_response(shape)])
                with self.assertRaises(CodexTransportError):
                    client.call("thread/read", {}, 0.2)

    def test_non_finite_inbound_value_fails_transport(self):
        def responder(message):
            if message.get("method") == "initialize":
                return {"id": message["id"], "result": {}}
            if message.get("method") == "initialized":
                return None
            return '{"id":%d,"result":{"value":Infinity}}' % message["id"]

        client, _factory = self.make_client([responder])
        with self.assertRaises(CodexTransportError):
            client.call("thread/read", {}, 0.2)

    def test_initialize_overload_reconnects_with_one_handshake_per_connection(self):
        def overloaded_initialize(message):
            return {"id": message["id"], "error": {"code": -32001, "message": "overloaded"}}

        client, factory = self.make_client([overloaded_initialize, success_responder])
        self.assertEqual(len(factory.connections), 2)
        first = [json.loads(frame)["method"] for frame in factory.connections[0].sent]
        second = [json.loads(frame)["method"] for frame in factory.connections[1].sent]
        self.assertEqual(first, ["initialize"])
        self.assertEqual(second, ["initialize", "initialized"])
        self.assertTrue(factory.connections[0].closed)
        self.assertEqual(client.call("thread/read", {}, 1)["method"], "thread/read")

    def test_idempotent_read_retries_but_mutation_never_replays(self):
        counts = {}

        def responder(message):
            method = message.get("method")
            if method == "initialized":
                return None
            counts[method] = counts.get(method, 0) + 1
            if method == "initialize":
                return {"id": message["id"], "result": {}}
            if counts[method] == 1:
                return {"id": message["id"], "error": {"code": -32001, "message": "overloaded"}}
            return {"id": message["id"], "result": {"ok": True}}

        client, _factory = self.make_client([responder])
        self.assertEqual(client.call("model/list", {}, 1), {"ok": True})
        self.assertEqual(counts["model/list"], 2)
        with self.assertRaises(CodexCallError) as caught:
            client.call("turn/start", {}, 1)
        self.assertEqual(caught.exception.kind, "upstream_busy")
        self.assertEqual(counts["turn/start"], 1)

    def test_existing_history_read_is_bounded_idempotent_retry(self):
        attempts = []

        def responder(message):
            method = message.get("method")
            if method == "initialized":
                return None
            if method == "initialize":
                return {"id": message["id"], "result": {}}
            attempts.append(method)
            if len(attempts) == 1:
                return {"id": message["id"], "error": {
                    "code": -32001, "message": "overloaded",
                }}
            return {"id": message["id"], "result": {"data": []}}

        client, _factory = self.make_client([responder])
        self.assertEqual(client.call("thread/turns/list", {}, 1), {"data": []})
        self.assertEqual(attempts, ["thread/turns/list", "thread/turns/list"])

    def test_app_server_compatibility_module_reexports_connection_and_errors(self):
        from codex_worker import app_server

        self.assertIs(app_server.CodexConnection, CodexConnection)
        self.assertIs(app_server.CodexCallError, CodexCallError)
        self.assertIs(app_server.CodexTransportError, CodexTransportError)

    def test_websockets_dependency_import_is_lazy_with_negative_control(self):
        source_path = (ROOT / "skills" / "subagent-driven-development" / "scripts" /
                       "codex_worker" / "websocket_transport.py")

        def module_imports_websockets(source):
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, ast.Import) and any(
                        alias.name.startswith("websockets") for alias in node.names):
                    return True
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("websockets"):
                    return True
            return False

        self.assertTrue(module_imports_websockets("import websockets\n"))
        self.assertFalse(module_imports_websockets(source_path.read_text(encoding="utf-8")))

    def test_unix_connector_uses_codex_rpc_upgrade_without_extensions(self):
        calls = []
        sentinel = object()

        def unix_connect(path, uri, **options):
            calls.append((path, uri, options))
            return sentinel

        client_module = types.ModuleType("websockets.sync.client")
        client_module.connect = lambda *_args, **_kwargs: None
        client_module.unix_connect = unix_connect
        sync_module = types.ModuleType("websockets.sync")
        websockets_module = types.ModuleType("websockets")
        with mock.patch.dict(sys.modules, {
                "websockets": websockets_module,
                "websockets.sync": sync_module,
                "websockets.sync.client": client_module,
        }):
            result = _default_connect("unix:///private/codex.sock", 1024, 8)
        self.assertIs(result, sentinel)
        self.assertEqual(calls, [(
            "/private/codex.sock", "ws://localhost/rpc",
            {"max_size": 1024, "max_queue": 8, "compression": None},
        )])


class RecordingAdapter(CodexMethodAdapter):
    def __init__(self):
        self.calls = []

    def call(self, method, params=None, timeout=120.0):
        self.calls.append((method, params))
        return {"thread": {"id": "thr-1", "cwd": "/private/cwd"}}


class ThreadConfigWireTests(unittest.TestCase):
    def test_thread_start_sends_config_overrides_as_native_config(self):
        adapter = RecordingAdapter()
        adapter.start_thread("/private/cwd", model="m", sandbox="read-only",
                             config={"web_search": "live", "features.x": True})
        self.assertEqual(adapter.calls, [("thread/start", {
            "cwd": "/private/cwd", "approvalPolicy": "never", "sandbox": "read-only",
            "serviceName": "superdev_codex_worker", "model": "m",
            "config": {"web_search": "live", "features.x": True},
        })])

    def test_thread_resume_sends_config_overrides_as_native_config(self):
        adapter = RecordingAdapter()
        adapter.resume_thread("thr-1", sandbox="read-only", config={"web_search": "live"})
        self.assertEqual(adapter.calls, [("thread/resume", {
            "threadId": "thr-1", "approvalPolicy": "never", "sandbox": "read-only",
            "config": {"web_search": "live"},
        })])

    def test_absent_config_is_omitted_from_the_wire(self):
        adapter = RecordingAdapter()
        adapter.start_thread("/private/cwd")
        adapter.resume_thread("thr-1")
        self.assertNotIn("config", adapter.calls[0][1])
        self.assertNotIn("config", adapter.calls[1][1])


if __name__ == "__main__":
    unittest.main()
