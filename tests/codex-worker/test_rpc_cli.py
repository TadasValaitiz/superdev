import contextlib
import io
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.models import IdentifierSelector, RpcFault
from codex_worker.rpc import (
    RpcServer,
    SocketInUse,
    SocketPathUnsafe,
    encode_response,
    rpc_call,
)
from codex_worker import cli


class FakeBroker:
    def __init__(self):
        self.calls = []
        self.shutdown_called = False

    def daemon_status(self):
        self.calls.append(("daemon/status", {}))
        return {
            "ready": True,
            "daemon_pid": 111,
            "codex_pid": 222,
            "socket_path": "fake.sock",
            "state_path": "fake-state.json",
            "session_count": 0,
        }

    def shutdown(self):
        self.calls.append(("daemon/shutdown", {}))
        self.shutdown_called = True
        return {"accepted": True}

    def model_list(self):
        self.calls.append(("model/list", {}))
        return {"models": [{"id": "fake-model", "is_default": True, "supported_efforts": ["medium"]}]}

    def session_start(self, cwd, name=None, model=None):
        self.calls.append(("session/start", {"cwd": cwd, "name": name, "model": model}))
        return {"session": _session("session-1", "thread-1", cwd, name, model, None), "attached": True}

    def session_resume(self, selector, name=None):
        self.calls.append(("session/resume", {"selector": selector, "name": name}))
        return {"session": _session(selector.session_id or "session-recovered",
                                    selector.thread_id or "thread-1",
                                    tempfile.gettempdir(), name, None, None),
                "attached": True}

    def session_list(self):
        self.calls.append(("session/list", {}))
        return {"sessions": []}

    def session_show(self, selector):
        self.calls.append(("session/show", {"selector": selector}))
        return {"session": _session(selector.session_id or "session-1",
                                    selector.thread_id or "thread-1",
                                    tempfile.gettempdir(), None, None, None),
                "attached": True, "active_turn_id": None, "latest_turn": None}

    def turn_start(self, selector, prompt, model=None, effort=None):
        self.calls.append(("turn/start", {
            "selector": selector, "prompt": prompt, "model": model, "effort": effort,
        }))
        return {"session_id": selector.session_id or "session-1",
                "thread_id": selector.thread_id or "thread-1",
                "turn_id": "turn-1", "status": "in_progress"}

    def turn_status(self, selector):
        self.calls.append(("turn/status", {"selector": selector}))
        return {"session_id": selector.session_id or "session-1",
                "thread_id": selector.thread_id or "thread-1",
                "attached": True, "active_turn_id": "turn-1", "latest_turn": None}

    def turn_wait(self, selector, timeout):
        self.calls.append(("turn/wait", {"selector": selector, "timeout": timeout}))
        return {"session_id": selector.session_id or "session-1",
                "thread_id": selector.thread_id or "thread-1",
                "turn": {"turn_id": "turn-1", "status": "completed", "error": None, "items": []}}

    def turn_events(self, selector, after, limit):
        self.calls.append(("turn/events", {"selector": selector, "after": after, "limit": limit}))
        return {"events": [], "next_cursor": after, "truncated": False}

    def turn_steer(self, selector, prompt):
        self.calls.append(("turn/steer", {"selector": selector, "prompt": prompt}))
        return {"session_id": selector.session_id or "session-1",
                "thread_id": selector.thread_id or "thread-1",
                "turn_id": "turn-1", "accepted": True}

    def turn_interrupt(self, selector):
        self.calls.append(("turn/interrupt", {"selector": selector}))
        return {"session_id": selector.session_id or "session-1",
                "thread_id": selector.thread_id or "thread-1",
                "turn_id": "turn-1", "accepted": True}


def _session(session_id, thread_id, cwd, name, model, effort):
    return {
        "session_id": session_id,
        "thread_id": thread_id,
        "cwd": cwd,
        "created_at": "2026-08-18T00:00:00Z",
        "updated_at": "2026-08-18T00:00:00Z",
        "name": name,
        "model": model,
        "effort": effort,
    }


class RpcServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.socket_path = str(Path(self.tempdir.name) / "worker.sock")
        self.servers = []

    def tearDown(self):
        for server in reversed(self.servers):
            with contextlib.suppress(Exception):
                server.shutdown()
            with contextlib.suppress(Exception):
                server.server_close()

    def start_server(self, broker=None):
        server = RpcServer(self.socket_path, broker or FakeBroker())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        server._test_thread = thread
        self.servers.append(server)
        return server

    def ping(self, server):
        response = rpc_call(server.socket_path, "daemon/status", {}, timeout=1.0)
        return response["result"]["ready"]

    def send_raw(self, payload):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            client.connect(self.socket_path)
            client.sendall(payload)
            received = b""
            while not received.endswith(b"\n"):
                chunk = client.recv(4096)
                if not chunk:
                    break
                received += chunk
        return json.loads(received.decode("utf-8"))

    def test_parse_error_uses_null_id_and_standard_code(self):
        self.start_server()
        response = self.send_raw(b"not-json\n")
        self.assertEqual(response, {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": "Parse error",
                "data": {"kind": "parse_error"},
            },
        })

    def test_invalid_request_and_unknown_method_use_standard_codes(self):
        self.start_server()
        invalid = self.send_raw(b'{"jsonrpc":"2.0","id":"bad","params":{}}\n')
        self.assertEqual(invalid["id"], "bad")
        self.assertEqual(invalid["error"]["code"], -32600)
        unknown = self.send_raw(
            b'{"jsonrpc":"2.0","id":"unknown","method":"missing/method","params":{}}\n'
        )
        self.assertEqual(unknown["id"], "unknown")
        self.assertEqual(unknown["error"]["code"], -32601)

    def test_live_socket_is_never_unlinked(self):
        first = self.start_server()
        with self.assertRaises(SocketInUse):
            RpcServer(self.socket_path, FakeBroker())
        self.assertTrue(self.ping(first))

    def test_stale_socket_is_replaced_with_owner_only_mode(self):
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(self.socket_path)
        stale.close()
        server = self.start_server()
        self.assertEqual(stat.S_IMODE(os.stat(self.socket_path).st_mode), 0o600)
        self.assertTrue(self.ping(server))

    def test_non_socket_collision_is_never_removed(self):
        Path(self.socket_path).write_text("owned by another process", encoding="utf-8")
        with self.assertRaises(SocketPathUnsafe):
            self.start_server()
        self.assertEqual(Path(self.socket_path).read_text(encoding="utf-8"), "owned by another process")

    def test_dispatch_converts_params_and_domain_faults_to_json_rpc(self):
        broker = FakeBroker()
        server = self.start_server(broker)
        response = rpc_call(server.socket_path, "turn/wait", {
            "session_id": "session-1",
            "timeout": 0,
        }, timeout=1.0)
        self.assertEqual(response["result"]["turn"]["status"], "completed")
        self.assertEqual(broker.calls[-1][1]["selector"], IdentifierSelector(session_id="session-1"))
        response = rpc_call(server.socket_path, "turn/wait", {
            "session_id": "session-1",
            "thread_id": "thread-1",
            "timeout": 0,
        }, timeout=1.0)
        self.assertEqual(response["error"]["code"], -32602)
        self.assertEqual(response["error"]["data"]["kind"], "invalid_params")

    def test_encode_response_preserves_the_shared_rpc_sum_type_serializer(self):
        encoded = encode_response("x", fault=RpcFault(-32001, "unknown", "unknown_session"))
        self.assertEqual(json.loads(encoded.decode("utf-8")), {
            "jsonrpc": "2.0",
            "id": "x",
            "error": {"code": -32001, "message": "unknown",
                      "data": {"kind": "unknown_session"}},
        })


@dataclass(frozen=True)
class CliCase:
    method: str
    argv: List[str]
    expected_params: dict
    expected_exit: int = 0
    expected_envelope: tuple = (True, False)


def documented_client_argv_cases(cwd, session_id, thread_id, prompt_file):
    return [
        CliCase("daemon/status", ["daemon", "status"], {}),
        CliCase("daemon/shutdown", ["daemon", "shutdown"], {}),
        CliCase("model/list", ["model", "list"], {}),
        CliCase("session/start", ["session", "start", "--cwd", cwd, "--name", "builder",
                                  "--model", "fake-model"],
                {"cwd": str(Path(cwd).resolve()), "name": "builder", "model": "fake-model"}),
        CliCase("session/resume", ["session", "resume", "--session", session_id],
                {"session_id": session_id, "thread_id": None, "name": None}),
        CliCase("session/list", ["session", "list"], {}),
        CliCase("session/show", ["session", "show", "--thread", thread_id],
                {"session_id": None, "thread_id": thread_id}),
        CliCase("turn/start", ["turn", "start", "--session", session_id, "--prompt", "build it",
                               "--model", "fake-model", "--effort", "medium"],
                {"session_id": session_id, "thread_id": None, "prompt": "build it",
                 "model": "fake-model", "effort": "medium"}),
        CliCase("turn/status", ["turn", "status", "--session", session_id],
                {"session_id": session_id, "thread_id": None}),
        CliCase("turn/wait", ["turn", "wait", "--thread", thread_id, "--timeout", "0.25"],
                {"session_id": None, "thread_id": thread_id, "timeout": 0.25}),
        CliCase("turn/events", ["turn", "events", "--session", session_id, "--after", "2",
                                "--limit", "10"],
                {"session_id": session_id, "thread_id": None, "after": 2, "limit": 10}),
        CliCase("turn/steer", ["turn", "steer", "--session", session_id,
                               "--prompt-file", str(prompt_file)],
                {"session_id": session_id, "thread_id": None, "prompt": "from file\n"}),
        CliCase("turn/interrupt", ["turn", "interrupt", "--session", session_id],
                {"session_id": session_id, "thread_id": None}),
    ]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.socket_path = str(Path(self.tempdir.name) / "worker.sock")
        self.cwd = str(Path(self.tempdir.name).resolve())
        self.session_id = "00000000-0000-0000-0000-000000000001"
        self.thread_id = "thread-live"
        self.prompt_file = Path(self.tempdir.name) / "prompt.txt"
        self.prompt_file.write_text("from file\n", encoding="utf-8")
        self.rpc_calls = []

    def run_cli(self, argv, fake_rpc=None):
        out = io.StringIO()
        err = io.StringIO()
        original_rpc_call = cli.rpc_call
        if fake_rpc is not None:
            cli.rpc_call = fake_rpc
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(["--socket", self.socket_path] + list(argv))
        finally:
            cli.rpc_call = original_rpc_call
        return type("Completed", (), {
            "returncode": code,
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
        })()

    def fake_rpc_success(self, socket_path, method, params, timeout):
        self.assertEqual(socket_path, self.socket_path)
        self.rpc_calls.append((method, params, timeout))
        return {"jsonrpc": "2.0", "id": "cli",
                "result": {"method": method, "params": params}}

    def test_every_client_command_emits_one_json_object(self):
        cases = documented_client_argv_cases(
            self.cwd, self.session_id, self.thread_id, self.prompt_file
        )
        self.assertEqual(len(cases), 13)
        self.assertEqual({case.method for case in cases}, cli.DOCUMENTED_CLIENT_METHODS)
        for case in cases:
            with self.subTest(argv=case.argv):
                self.rpc_calls = []
                completed = self.run_cli(case.argv, fake_rpc=self.fake_rpc_success)
                self.assertEqual(completed.returncode, case.expected_exit, case.argv)
                lines = completed.stdout.splitlines()
                self.assertEqual(len(lines), 1, case.argv)
                payload = json.loads(lines[0])
                self.assertEqual(("result" in payload, "error" in payload), case.expected_envelope)
                self.assertEqual(payload["result"]["method"], case.method)
                self.assertEqual(payload["result"]["params"], case.expected_params)

    def test_rpc_error_is_structured_and_exit_one(self):
        def fake_rpc_error(socket_path, method, params, timeout):
            return {"jsonrpc": "2.0", "id": "cli",
                    "error": {"code": -32005, "message": "turn is not active",
                              "data": {"kind": "turn_not_active"}}}

        completed = self.run_cli(["turn", "steer", "--session", self.session_id,
                                  "--prompt", "try anyway"], fake_rpc=fake_rpc_error)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["error"]["data"]["kind"], "turn_not_active")

    def test_daemon_absent_is_structured_and_exit_one(self):
        completed = self.run_cli(["daemon", "status"], fake_rpc=None)
        self.assertEqual(completed.returncode, 1)
        lines = completed.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["error"]["data"]["kind"], "daemon_unavailable")

    def test_pretty_is_rejected_for_foreground_serve(self):
        completed = self.run_cli(["--pretty", "daemon", "serve"])
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")

    def test_mutually_exclusive_identifiers_and_prompts_are_usage_exit_two(self):
        identifier = self.run_cli(["session", "show", "--session", self.session_id,
                                   "--thread", self.thread_id])
        self.assertEqual(identifier.returncode, 2)
        prompt = self.run_cli(["turn", "start", "--session", self.session_id,
                               "--prompt", "inline", "--prompt-file", str(self.prompt_file)])
        self.assertEqual(prompt.returncode, 2)

    def test_pretty_prints_one_json_object_for_client_commands(self):
        completed = self.run_cli(["--pretty", "daemon", "status"], fake_rpc=self.fake_rpc_success)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(len(json.loads(completed.stdout)), 3)
        self.assertIn("\n  ", completed.stdout)

    def test_foreground_serve_has_no_stdout_and_shutdown_preserves_registry(self):
        script = ROOT / "skills" / "subagent-driven-development" / "scripts" / "codex-worker"
        fake_codex = ROOT / "tests" / "codex-worker" / "fake_codex.py"
        fake_bin = Path(self.tempdir.name) / "fake-codex"
        fake_bin.write_text(
            "#!/usr/bin/env python3\n"
            "import runpy, sys\n"
            "if len(sys.argv) > 1 and sys.argv[1] == 'app-server':\n"
            "    del sys.argv[1]\n"
            "sys.argv[0] = %r\n"
            "runpy.run_path(%r, run_name='__main__')\n" % (str(fake_codex), str(fake_codex)),
            encoding="utf-8",
        )
        fake_bin.chmod(0o700)
        state_path = str(Path(self.tempdir.name) / "sessions.json")
        proc = subprocess.Popen(
            [sys.executable, str(script), "--socket", self.socket_path,
             "daemon", "serve", "--state", state_path, "--codex-bin", str(fake_bin),
             "--event-limit", "5"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.time() + 5.0
            status = None
            while time.time() < deadline:
                try:
                    status = rpc_call(self.socket_path, "daemon/status", {}, timeout=0.25)
                    break
                except RpcFault:
                    time.sleep(0.05)
            self.assertIsNotNone(status)
            self.assertTrue(status["result"]["ready"])
            started = rpc_call(self.socket_path, "session/start", {
                "cwd": self.cwd,
                "name": "integration",
                "model": None,
            }, timeout=1.0)
            self.assertTrue(started["result"]["attached"])
            stopped = rpc_call(self.socket_path, "daemon/shutdown", {}, timeout=1.0)
            self.assertEqual(stopped["result"], {"accepted": True})
            stdout, stderr = proc.communicate(timeout=5.0)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5.0)
        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(stdout, "")
        self.assertTrue(Path(state_path).exists())
        self.assertIn("codex-worker daemon listening", stderr)


if __name__ == "__main__":
    unittest.main()
