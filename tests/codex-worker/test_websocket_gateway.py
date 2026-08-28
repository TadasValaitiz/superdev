import ast
import json
import queue
import socket
import sys
import threading
import time
import types
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))
FIXTURE = Path(__file__).with_name("fixtures") / "codex-0.150.1-client-request-methods.json"

from codex_worker.websocket_gateway import (
    CURRENT_CLIENT_REQUEST_METHODS,
    DRAIN_ALLOWED_REQUESTS,
    DrainLease,
    FrameClass,
    GatewayDeps,
    ServiceBusyError,
    ServiceMaintenanceGate,
    WebSocketGateway,
    _default_backend_connect,
    classify_frontend_frame,
)


_CLOSED = object()


class FakeSocket:
    def __init__(self):
        self.incoming = queue.Queue()
        self.sent = []
        self.closed = False

    def recv(self):
        value = self.incoming.get(timeout=2)
        if value is _CLOSED:
            raise OSError("closed")
        return value

    def send(self, frame):
        if self.closed:
            raise OSError("closed")
        self.sent.append(frame)

    def inject(self, frame):
        self.incoming.put(frame)

    def close(self):
        if not self.closed:
            self.closed = True
            self.incoming.put(_CLOSED)


class FakeServer:
    def __init__(self, handler):
        self.handler = handler
        self.running = threading.Event()
        self.closed = threading.Event()

    def serve_forever(self):
        self.running.set()
        self.closed.wait()

    def shutdown(self):
        self.closed.set()


class FakeGatewayFactory:
    def __init__(self):
        self.backends = []
        self.servers = []
        self.binds = []

    def connect_backend(self, endpoint, max_frame_bytes, max_queue):
        backend = FakeSocket()
        self.backends.append(backend)
        return backend

    def bind_server(self, handler, host, port, max_frame_bytes, max_queue):
        self.binds.append((host, port, max_frame_bytes, max_queue))
        server = FakeServer(handler)
        self.servers.append(server)
        return server


class RealBindingServer:
    def __init__(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind((host, port))
        except BaseException:
            self.socket.close()
            raise
        self.socket.listen(1)
        self.closed = threading.Event()

    def serve_forever(self):
        self.closed.wait()

    def shutdown(self):
        self.socket.close()
        self.closed.set()


class RealBindFactory(FakeGatewayFactory):
    def bind_server(self, handler, host, port, max_frame_bytes, max_queue):
        server = RealBindingServer(host, port)
        self.servers.append(server)
        return server


def unused_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


class MaintenanceGateTests(unittest.TestCase):
    def test_drain_blocks_new_mutations_and_waits_forwarded_mutations(self):
        gate = ServiceMaintenanceGate()
        forwarded = threading.Event()
        release = threading.Event()
        drained = threading.Event()
        active_during_drain = []

        def mutate():
            with gate.mutation("turn/start"):
                forwarded.set()
                release.wait(1)

        def drain():
            with gate.drain():
                active_during_drain.append(gate.active_mutations)
                drained.set()

        mutation_thread = threading.Thread(target=mutate)
        mutation_thread.start()
        self.assertTrue(forwarded.wait(1))
        drain_thread = threading.Thread(target=drain)
        drain_thread.start()
        deadline = time.monotonic() + 1
        while not gate.draining:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        with self.assertRaises(ServiceBusyError):
            with gate.mutation("turn/steer"):
                pass
        self.assertFalse(drained.is_set())
        release.set()
        mutation_thread.join(1)
        drain_thread.join(1)
        self.assertTrue(drained.is_set())
        self.assertEqual(active_during_drain, [0])

    def test_drain_lease_is_gate_owned_live_authorization(self):
        gate = ServiceMaintenanceGate()
        foreign = ServiceMaintenanceGate()
        with self.assertRaises(TypeError):
            DrainLease(object(), object())
        with gate.drain() as lease:
            gate.authorize(lease)
            with self.assertRaises(PermissionError):
                foreign.authorize(lease)
        with self.assertRaises(PermissionError):
            gate.authorize(lease)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.gate = ServiceMaintenanceGate()
        self.factory = FakeGatewayFactory()
        self.gateway = WebSocketGateway(
            "ws://127.0.0.1:4500",
            "unix:///private/codex.sock",
            self.gate,
            GatewayDeps(self.factory.connect_backend, self.factory.bind_server),
        )
        self.gateway.start()
        self.addCleanup(self.gateway.close)

    def bridge(self):
        frontend = FakeSocket()
        thread = threading.Thread(target=self.factory.servers[0].handler, args=(frontend,))
        thread.start()
        deadline = time.monotonic() + 1
        while not self.factory.backends:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        return frontend, self.factory.backends[-1], thread

    def test_binds_exact_listener_and_maps_one_frontend_to_one_backend(self):
        self.assertTrue(self.gateway.ready)
        self.assertEqual(self.factory.binds[0][:2], ("127.0.0.1", 4500))
        first, first_backend, first_thread = self.bridge()
        second, second_backend, second_thread = self.bridge()
        self.assertIsNot(first_backend, second_backend)
        first.close()
        second.close()
        first_thread.join(1)
        second_thread.join(1)

    def test_ready_clears_when_server_loop_exits_unexpectedly(self):
        self.assertTrue(self.gateway.ready)
        self.factory.servers[0].shutdown()
        deadline = time.monotonic() + 1
        while self.gateway.ready:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertFalse(self.gateway.ready)

    def test_successful_frames_are_byte_equivalent_and_mutation_settles_on_response(self):
        frontend, backend, thread = self.bridge()
        request = '{ "id" : "r-1", "method" : "turn/start", "params" : {"x":1} }'
        response = '{ "id" : "r-1", "result" : {"turn":{"id":"t"}} }'
        frontend.inject(request)
        deadline = time.monotonic() + 1
        while not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(backend.sent, [request])
        self.assertEqual(self.gate.active_mutations, 1)
        backend.inject(response)
        while not frontend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(frontend.sent, [response])
        self.assertEqual(self.gate.active_mutations, 0)
        frontend.close()
        thread.join(1)

    def test_incomplete_or_ambiguous_backend_envelope_does_not_settle_mutation(self):
        frontend, backend, thread = self.bridge()
        frontend.inject('{"id":7,"method":"turn/start","params":{}}')
        deadline = time.monotonic() + 1
        while not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(self.gate.active_mutations, 1)

        incomplete = '{"id":7}'
        ambiguous = '{"id":7,"result":{},"error":{}}'
        null_method = '{"id":7,"method":null,"result":{}}'
        malformed_error = '{"id":7,"error":"busy"}'
        backend.inject(incomplete)
        backend.inject(ambiguous)
        backend.inject(null_method)
        backend.inject(malformed_error)
        while len(frontend.sent) < 4:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(frontend.sent[:4], [
            incomplete, ambiguous, null_method, malformed_error,
        ])
        self.assertEqual(self.gate.active_mutations, 1)

        backend.inject('{"id":7,"result":{}}')
        while self.gate.active_mutations:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        frontend.close()
        thread.join(1)

    def test_drain_allows_only_explicit_requests_and_client_responses(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["codex_version"], "codex-cli 0.150.1")
        self.assertEqual(set(fixture["client_request_methods"]), CURRENT_CLIENT_REQUEST_METHODS)
        self.assertEqual(DRAIN_ALLOWED_REQUESTS, frozenset({
            "thread/list", "thread/read", "turn/interrupt",
        }))
        frontend, backend, thread = self.bridge()
        with self.gate.drain():
            for index, method in enumerate(fixture["client_request_methods"]):
                frontend.inject(json.dumps({"id": index, "method": method, "params": {}}))
            frontend.inject(json.dumps({"id": "future", "method": "future/mutation", "params": {}}))
            client_response = '{"id":"server-approval","result":{"decision":"decline"}}'
            frontend.inject(client_response)
            deadline = time.monotonic() + 2
            expected_busy = len(fixture["client_request_methods"]) - len(DRAIN_ALLOWED_REQUESTS) + 1
            while len(frontend.sent) < expected_busy or len(backend.sent) < len(DRAIN_ALLOWED_REQUESTS) + 1:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.001)
        forwarded = [json.loads(frame) if frame != client_response else frame for frame in backend.sent]
        self.assertEqual({frame["method"] for frame in forwarded if isinstance(frame, dict)},
                         DRAIN_ALLOWED_REQUESTS)
        self.assertIn(client_response, backend.sent)
        busy = [json.loads(frame) for frame in frontend.sent]
        self.assertEqual(len(busy), expected_busy)
        self.assertTrue(all(item["error"]["code"] == -32040 for item in busy))
        self.assertTrue(all(item["error"]["data"]["kind"] == "service_busy" for item in busy))
        frontend.close()
        thread.join(1)

    def test_malformed_and_binary_frontend_frames_fail_closed(self):
        frontend, backend, thread = self.bridge()
        frontend.inject("not-json")
        frontend.inject(b"binary")
        deadline = time.monotonic() + 1
        while len(frontend.sent) < 2:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(backend.sent, [])
        faults = [json.loads(frame)["error"]["data"]["kind"] for frame in frontend.sent]
        self.assertEqual(faults, ["invalid_request", "invalid_request"])
        frontend.close()
        thread.join(1)

    def test_non_finite_frontend_json_is_refused_before_forwarding(self):
        frontend, backend, thread = self.bridge()
        frontend.inject('{"id":1,"method":"turn/start","params":{"value":NaN}}')
        deadline = time.monotonic() + 1
        while not frontend.sent and not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(backend.sent, [])
        self.assertEqual(json.loads(frontend.sent[0])["error"]["data"]["kind"],
                         "invalid_request")
        frontend.close()
        thread.join(1)

    def test_invalid_request_id_is_refused_instead_of_bypassing_settlement(self):
        frontend, backend, thread = self.bridge()
        frontend.inject('{"id":null,"method":"turn/start","params":{}}')
        deadline = time.monotonic() + 1
        while not frontend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(backend.sent, [])
        self.assertEqual(json.loads(frontend.sent[0])["error"]["data"]["kind"],
                         "invalid_request")
        self.assertEqual(self.gate.active_mutations, 0)
        frontend.close()
        thread.join(1)

    def test_frontend_disconnect_releases_inflight_mutation(self):
        frontend, backend, thread = self.bridge()
        frontend.inject('{"id":1,"method":"turn/start","params":{}}')
        deadline = time.monotonic() + 1
        while not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(self.gate.active_mutations, 1)
        frontend.close()
        thread.join(1)
        self.assertEqual(self.gate.active_mutations, 0)

    def test_duplicate_inflight_request_id_is_refused_before_second_forward(self):
        frontend, backend, thread = self.bridge()
        request = '{"id":1,"method":"turn/start","params":{}}'
        frontend.inject(request)
        deadline = time.monotonic() + 1
        while not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        frontend.inject(request)
        while not frontend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(backend.sent, [request])
        self.assertEqual(json.loads(frontend.sent[0])["error"]["data"]["kind"],
                         "invalid_request")
        self.assertEqual(self.gate.active_mutations, 1)
        backend.inject('{"id":1,"result":{}}')
        while self.gate.active_mutations:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        frontend.close()
        thread.join(1)

    def test_duplicate_inflight_allowlisted_read_id_is_refused_before_forward(self):
        frontend, backend, thread = self.bridge()
        request = '{"id":"read-1","method":"thread/read","params":{"threadId":"t"}}'
        frontend.inject(request)
        frontend.inject(request)
        deadline = time.monotonic() + 1
        while len(backend.sent) < 2 and not frontend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertEqual(backend.sent, [request])
        self.assertEqual(json.loads(frontend.sent[0])["error"]["data"]["kind"],
                         "invalid_request")
        backend.inject('{"id":"read-1","result":{}}')
        frontend.close()
        thread.join(1)

    def test_backend_disconnect_closes_frontend_and_releases_inflight_mutation(self):
        frontend, backend, thread = self.bridge()
        frontend.inject('{"id":1,"method":"turn/start","params":{}}')
        deadline = time.monotonic() + 1
        while not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        backend.close()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertTrue(frontend.closed)
        self.assertEqual(self.gate.active_mutations, 0)

    def test_non_finite_backend_json_closes_bridge_without_forwarding(self):
        frontend, backend, thread = self.bridge()
        frontend.inject('{"id":1,"method":"turn/start","params":{}}')
        deadline = time.monotonic() + 1
        while not backend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        backend.inject('{"id":1,"result":{"value":Infinity}}')
        while not frontend.closed and not frontend.sent:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.001)
        self.assertTrue(frontend.closed)
        self.assertEqual(frontend.sent, [])
        thread.join(1)
        self.assertEqual(self.gate.active_mutations, 0)

    def test_server_approval_request_and_client_response_continue_during_drain(self):
        frontend, backend, thread = self.bridge()
        server_request = '{"id":"approval","method":"item/fileChange/requestApproval","params":{}}'
        client_response = '{"id":"approval","result":{"decision":"decline"}}'
        with self.gate.drain():
            backend.inject(server_request)
            deadline = time.monotonic() + 1
            while not frontend.sent:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.001)
            frontend.inject(client_response)
            while not backend.sent:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.001)
        self.assertEqual(frontend.sent, [server_request])
        self.assertEqual(backend.sent, [client_response])
        frontend.close()
        thread.join(1)

    def test_schema_classifier_set_equality_and_unknown_fail_closed(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(set(fixture["client_request_methods"]), CURRENT_CLIENT_REQUEST_METHODS)
        for method in CURRENT_CLIENT_REQUEST_METHODS:
            expected = FrameClass.ALLOWED if method in DRAIN_ALLOWED_REQUESTS else FrameClass.BLOCKED
            self.assertEqual(classify_frontend_frame({"id": 1, "method": method}), expected)
        self.assertEqual(classify_frontend_frame({"id": 1, "method": "future/method"}),
                         FrameClass.BLOCKED)
        self.assertEqual(classify_frontend_frame({"id": 1, "result": {}}), FrameClass.RESPONSE)
        with self.assertRaises(AssertionError):
            self.assertEqual(set(fixture["client_request_methods"]) | {"upstream/new"},
                             CURRENT_CLIENT_REQUEST_METHODS)

    def test_websockets_server_import_is_lazy_ast_guard(self):
        source = (ROOT / "skills" / "subagent-driven-development" / "scripts" /
                  "codex_worker" / "websocket_gateway.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        module_imports = [node for node in tree.body
                          if isinstance(node, (ast.Import, ast.ImportFrom))]
        rendered = "\n".join(ast.unparse(node) for node in module_imports)
        self.assertNotIn("websockets", rendered)
        violating = ast.parse("from websockets.sync.server import serve\n")
        self.assertIn("websockets", ast.unparse(violating.body[0]))

    def test_private_backend_uses_codex_rpc_upgrade_without_extensions(self):
        calls = []
        sentinel = object()

        def unix_connect(path, uri, **options):
            calls.append((path, uri, options))
            return sentinel

        client_module = types.ModuleType("websockets.sync.client")
        client_module.unix_connect = unix_connect
        with mock.patch.dict(sys.modules, {
                "websockets": types.ModuleType("websockets"),
                "websockets.sync": types.ModuleType("websockets.sync"),
                "websockets.sync.client": client_module,
        }):
            result = _default_backend_connect("unix:///private/codex.sock", 2048, 4)
        self.assertIs(result, sentinel)
        self.assertEqual(calls, [(
            "/private/codex.sock", "ws://localhost/rpc",
            {"max_size": 2048, "max_queue": 4, "compression": None},
        )])


class RealCollisionTests(unittest.TestCase):
    def test_fixed_bind_collision_preserves_first_peer_without_fallback(self):
        port = unused_port()
        factory = RealBindFactory()
        gate = ServiceMaintenanceGate()
        first = WebSocketGateway(
            "ws://127.0.0.1:%d" % port,
            "unix:///private/one.sock",
            gate,
            GatewayDeps(factory.connect_backend, factory.bind_server),
        )
        second = WebSocketGateway(
            "ws://127.0.0.1:%d" % port,
            "unix:///private/two.sock",
            gate,
            GatewayDeps(factory.connect_backend, factory.bind_server),
        )
        first.start()
        self.addCleanup(first.close)
        with self.assertRaises(OSError):
            second.start()
        probe = socket.create_connection(("127.0.0.1", port), timeout=1)
        probe.close()
        self.assertTrue(first.ready)
        self.assertFalse(second.ready)


if __name__ == "__main__":
    unittest.main()
