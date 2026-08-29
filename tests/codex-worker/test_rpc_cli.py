import contextlib
import fcntl
import io
import json
import os
import signal
import socket
import shlex
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from dataclasses import dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.models import IdentifierSelector, RpcFault
from codex_worker.cli import build_parser, _params_for
from codex_worker.instance import (InstanceDeps, InstanceManager, derive_instance_paths,
                                   resolve_instance)
from codex_worker.service_domain import derive_service_paths
from codex_worker.commands import (
    AccessMode,
    AgentMessageView,
    CompletionResponse,
    CompletionSelection,
    ControlResponse,
    Err,
    FACADE_FAULT_KINDS,
    FacadeFault,
    FacadeFaultCode,
    GoalResponse,
    GoalView,
    HistoryTurnView,
    LimitsResponse,
    MetricAvailability,
    MetricEvidence,
    Ok,
    RecoveryView,
    Tier,
    TurnView,
    WorkerHistoryResponse,
    WorkerMessagesResponse,
    WorkerStatusResponse,
    WorkerView,
)
import codex_worker.rpc as rpc_module
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


def _pid_exists(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _websockets_pythonpath():
    """Use uv's already-downloaded test dependency without mutating an install."""
    cache = Path.home() / ".cache" / "uv" / "archive-v0"
    for metadata in sorted(cache.glob("*/websockets-15.*.dist-info")):
        return str(metadata.parent)
    raise AssertionError("websockets 15 must already exist in the uv cache")


def _unused_loopback_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return "ws://127.0.0.1:%d" % probe.getsockname()[1]


class RecoveryActionTests(unittest.TestCase):
    def test_raw_fault_rejects_prose_and_placeholder_recovery_actions(self):
        for recovery in ("run session list", "codex-worker turn wait --timeout <seconds>"):
            with self.subTest(recovery=recovery), self.assertRaisesRegex(ValueError, "literal"):
                RpcFault(-32000, "refused", "daemon_unavailable", recovery=recovery)

    def test_managed_daemon_unavailable_recovery_is_public_start(self):
        fault = rpc_module.daemon_unavailable_fault("/tmp/private.sock")
        self.assertEqual(fault.recovery, "codex-worker daemon start")

    def test_literal_codex_worker_actions_parse_on_the_public_surface(self):
        actions = [
            "codex-worker daemon start",
            "codex-worker daemon status",
            "codex-worker status --name worker-a",
            "codex-worker session show --session 12345678-1234-5678-1234-567812345678",
        ]
        parser = cli.build_parser()
        for command in actions:
            with self.subTest(command=command):
                tokens = shlex.split(command)
                parsed = parser.parse_args(tokens[1:])
                self.assertIsNotNone(parsed.family)

    def test_emitted_next_actions_are_exhaustively_parser_checked(self):
        valid = {"error": {"data": {"next_actions": [
            {"command": "codex-worker daemon start", "reason": "start"},
            {"command": "codex --remote ws://127.0.0.1:4500 resume thread-a",
             "reason": "attach"},
        ]}}}
        cli._validate_wire_recovery_actions(valid)
        for command in ("codex-worker daemon serve", "codex-worker daemon serve --bad",
                        "codex-worker daemon serve --help",
                        "codex-worker --pretty daemon serve --help",
                        "codex-worker daemon serve -h --bad",
                        "missing-tool status", "/etc/hosts",
                        "/bin/ls /tmp; /usr/bin/false",
                        "/bin/ls /tmp # ignored",
                        "/bin/ls /tmp/*",
                        "/bin/ls /tmp\n/usr/bin/false",
                        "/bin/ls /tmp # comment\n/usr/bin/false"):
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, "recovery"):
                cli._validate_wire_recovery_actions({
                    "error": {"data": {"next_actions": [
                        {"command": command, "reason": "bad"}]}}})
        cli._validate_wire_recovery_actions({"error": {"data": {"next_actions": [{
            "command": "codex-worker run --name x --prompt ';'", "reason": "safe"}]}}})
        cli._validate_wire_recovery_actions({"error": {"data": {"next_actions": [{
            "command": "codex-worker run --name x --prompt '<'", "reason": "safe"}, {
            "command": "codex-worker run --name x --prompt '>'", "reason": "safe"}]}}})

    def test_completion_recovery_commands_are_inside_the_exhaustive_guard(self):
        for command in ("missing-tool status", "codex-worker daemon serve --bad",
                        "codex-worker status --name <worker>", "codex --remote wrong"):
            with self.subTest(command=command), self.assertRaises(ValueError):
                cli._validate_wire_recovery_actions({
                    "result": {"recovery": {
                        "status": command, "messages": "codex-worker messages --name worker-a",
                        "interrupt": "codex-worker interrupt --name worker-a",
                        "raw_resume": None,
                    }}})

    def test_attach_resume_and_resolution_commands_are_inside_the_exhaustive_guard(self):
        payloads = [
            {"result": {"attach": {
                "attach_command": "codex-worker daemon serve",
                "resume_command": "missing-tool go"}}},
            {"result": {"resolution_actions": [{
                "command": "codex-worker daemon serve", "reason": "bad"}]}},
        ]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                cli._validate_wire_recovery_actions(payload)

    def test_user_output_and_command_events_are_not_misclassified_as_recovery(self):
        cli._validate_wire_recovery_actions({
            "result": {"structured_output": {"command": "echo harmless"}}})
        cli._validate_wire_recovery_actions({
            "result": {"items": [{"data": {"command": "echo harmless"}}]}})


class PublicHelpLimitsTests(unittest.TestCase):
    def test_every_public_leaf_help_states_limits(self):
        leaves = [
            ["start"], ["run"], ["message"], ["status"], ["messages"],
            ["history"], ["steer"], ["interrupt"], ["goal", "set"],
            ["goal", "show"], ["limits"], ["daemon", "start"],
            ["daemon", "status"], ["daemon", "stop"], ["daemon", "restart"],
            ["migration", "status"], ["migration", "resolve"], ["model", "list"],
            ["session", "start"], ["session", "resume"], ["session", "list"],
            ["session", "show"], ["turn", "start"], ["turn", "status"],
            ["turn", "wait"], ["turn", "events"], ["turn", "steer"],
            ["turn", "interrupt"],
        ]
        parser = cli.build_parser()
        for path in leaves:
            with self.subTest(path=path), self.assertRaises(SystemExit) as caught:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    parser.parse_args(path + ["--help"])
            self.assertEqual(caught.exception.code, 0)
            self.assertIn("Limits:", output.getvalue())

    def test_global_maintenance_help_names_force_impact(self):
        parser = cli.build_parser()
        for action in ("stop", "restart"):
            with self.subTest(action=action), self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    parser.parse_args(["daemon", action, "--help"])
            help_text = output.getvalue()
            for fragment in ("Machine-wide", "Active work", "--force", "every reported"):
                self.assertIn(fragment, help_text)

    def test_managed_raw_help_states_no_autostart_boundary(self):
        parser = cli.build_parser()
        for path in (["model", "list"], ["session", "resume"], ["turn", "status"]):
            with self.subTest(path=path), self.assertRaises(SystemExit):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    parser.parse_args(path + ["--help"])
            for fragment in ("strictly ready", "never auto-starts", "--socket bypass"):
                self.assertIn(fragment, output.getvalue())


class RpcServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.socket_path = str(Path(self.tempdir.name) / "worker.sock")
        self.servers = []

    def tearDown(self):
        for server in reversed(self.servers):
            if getattr(server, "_test_thread", None) is not None:
                with contextlib.suppress(Exception):
                    server.shutdown()
            with contextlib.suppress(Exception):
                server.server_close()

    def start_server(self, broker=None, facade=None, service_facade=None):
        server = RpcServer(self.socket_path, broker or FakeBroker(), facade, service_facade)
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

    def test_server_refuses_unsafe_socket_parent_before_binding(self):
        parent = Path(self.tempdir.name) / "unsafe-parent"
        parent.mkdir()
        parent.chmod(0o777)
        self.socket_path = str(parent / "worker.sock")
        with self.assertRaises(SocketPathUnsafe):
            self.start_server()
        self.assertFalse(Path(self.socket_path).exists())

    def test_existing_socket_parent_permissions_are_not_changed(self):
        parent = Path(self.tempdir.name) / "shared"
        parent.mkdir()
        parent.chmod(0o755)
        self.socket_path = str(parent / "worker.sock")
        self.start_server()
        self.assertEqual(stat.S_IMODE(parent.stat().st_mode), 0o755)

    def test_concurrent_daemons_cannot_both_replace_the_same_stale_socket(self):
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(self.socket_path)
        stale.close()
        successes = []
        failures = []
        lock = threading.Lock()

        def build_server():
            try:
                server = RpcServer(self.socket_path, FakeBroker())
            except Exception as exc:
                with lock:
                    failures.append(exc)
                return
            with lock:
                successes.append(server)

        workers = [threading.Thread(target=build_server) for _ in range(6)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.servers.extend(successes)
        self.assertEqual(len(successes), 1)
        self.assertTrue(all(isinstance(exc, SocketInUse) for exc in failures))
        self.assertEqual(len(failures), 5)

    def test_start_lock_path_must_be_a_regular_file(self):
        Path(self.socket_path + ".lock").mkdir()
        with self.assertRaises(SocketPathUnsafe):
            self.start_server()
        self.assertTrue(Path(self.socket_path + ".lock").is_dir())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_start_lock_path_symlink_is_rejected_without_touching_target(self):
        target = Path(self.tempdir.name) / "lock-target"
        target.write_text("keep me", encoding="utf-8")
        os.symlink(str(target), self.socket_path + ".lock")
        with self.assertRaises(SocketPathUnsafe):
            self.start_server()
        self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_start_lock_is_bounded_when_held_by_another_process(self):
        lock_path = self.socket_path + ".lock"
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        old_timeout = rpc_module.START_LOCK_TIMEOUT_SECONDS
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            rpc_module.START_LOCK_TIMEOUT_SECONDS = 0.1
            with self.assertRaises(SocketInUse):
                self.start_server()
        finally:
            rpc_module.START_LOCK_TIMEOUT_SECONDS = old_timeout
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def test_foreign_owned_stale_socket_is_refused_without_unlinking(self):
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(self.socket_path)
        stale.close()
        original_lstat = rpc_module.os.lstat
        original = original_lstat(self.socket_path)

        class FakeStat:
            st_mode = original.st_mode
            st_uid = os.getuid() + 1
            st_dev = original.st_dev
            st_ino = original.st_ino

        def fake_lstat(path):
            if path == self.socket_path:
                return FakeStat()
            return original_lstat(path)

        rpc_module.os.lstat = fake_lstat
        try:
            with self.assertRaises(SocketPathUnsafe):
                self.start_server()
        finally:
            rpc_module.os.lstat = original_lstat
        self.assertTrue(Path(self.socket_path).exists())

    def test_constructor_failure_after_bind_unlinks_only_owned_bound_socket(self):
        original_chmod = rpc_module.os.chmod

        def failing_chmod(path, mode):
            if path == self.socket_path:
                raise OSError("forced chmod failure")
            return original_chmod(path, mode)

        rpc_module.os.chmod = failing_chmod
        try:
            with self.assertRaises(OSError):
                RpcServer(self.socket_path, FakeBroker())
        finally:
            rpc_module.os.chmod = original_chmod
        self.assertFalse(Path(self.socket_path).exists())

    def test_bound_stat_none_never_unlinks_replacement_socket(self):
        server = self.start_server()
        server._bound_stat = None
        server.server_close()
        self.assertTrue(Path(self.socket_path).exists())
        os.unlink(self.socket_path)
        replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(replacement.close)
        replacement.bind(self.socket_path)
        replacement.listen(1)
        server.server_close()
        self.assertTrue(Path(self.socket_path).exists())

    def test_socket_is_owner_only_before_listen(self):
        original_activate = rpc_module.ThreadingUnixServer.server_activate
        observed_modes = []

        def checking_activate(server):
            observed_modes.append(stat.S_IMODE(os.stat(server.socket_path).st_mode))
            return original_activate(server)

        rpc_module.ThreadingUnixServer.server_activate = checking_activate
        try:
            self.start_server()
        finally:
            rpc_module.ThreadingUnixServer.server_activate = original_activate
        self.assertEqual(observed_modes, [0o600])

    def test_socket_is_owner_only_immediately_when_bound(self):
        original_bind = rpc_module.ThreadingUnixServer.server_bind
        observed_modes = []

        def checking_bind(server):
            original_bind(server)
            observed_modes.append(stat.S_IMODE(os.stat(server.socket_path).st_mode))

        rpc_module.ThreadingUnixServer.server_bind = checking_bind
        try:
            self.start_server()
        finally:
            rpc_module.ThreadingUnixServer.server_bind = original_bind
        self.assertEqual(observed_modes, [0o600])

    def test_params_null_is_rejected_as_invalid_params(self):
        self.start_server()
        response = self.send_raw(
            b'{"jsonrpc":"2.0","id":"null-params","method":"daemon/status","params":null}\n'
        )
        self.assertEqual(response["id"], "null-params")
        self.assertEqual(response["error"]["code"], -32602)

    def test_unguarded_shutdown_method_is_absent_and_wrapper_remains(self):
        broker = FakeBroker()
        server = self.start_server(broker)
        response = self.send_raw(
            b'{"jsonrpc":"2.0","id":"bye","method":"daemon/shutdown","params":{}}\n')
        self.assertEqual(response["error"]["code"], -32601)
        self.assertFalse(broker.shutdown_called)
        self.assertTrue(server._test_thread.is_alive())
        self.assertTrue(self.ping(server))

    def test_rpc_rejects_unknown_params_and_non_finite_raw_json(self):
        self.start_server()
        unknown = rpc_call(self.socket_path, "session/start", {
            "cwd": str(Path(self.tempdir.name).resolve()),
            "name": None,
            "model": None,
            "unexpected": True,
        }, timeout=1.0)
        self.assertEqual(unknown["error"]["code"], -32602)
        self.assertEqual(unknown["error"]["data"]["kind"], "invalid_params")
        non_finite = self.send_raw(
            b'{"jsonrpc":"2.0","id":"nan","method":"turn/wait",'
            b'"params":{"session_id":"s","timeout":Infinity}}\n'
        )
        self.assertEqual(non_finite["id"], None)
        self.assertEqual(non_finite["error"]["code"], -32700)
        huge_integer = b"1" + (b"0" * 400)
        overflowing = self.send_raw(
            b'{"jsonrpc":"2.0","id":"huge","method":"turn/wait",'
            b'"params":{"session_id":"s","timeout":' + huge_integer + b'}}\n'
        )
        self.assertEqual(overflowing["id"], "huge")
        self.assertEqual(overflowing["error"]["code"], -32602)

    def test_rpc_call_rejects_overflow_timeout_and_clamps_platform_timeout(self):
        server = self.start_server()
        with self.assertRaises(ValueError):
            rpc_call(server.socket_path, "daemon/status", {}, timeout=10 ** 400)
        response = rpc_call(server.socket_path, "daemon/status", {}, timeout=1e10)
        self.assertTrue(response["result"]["ready"])

    def test_rpc_call_refuses_untrusted_endpoint_before_connecting(self):
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(self.socket_path)
        listener.listen(1)
        os.chmod(self.socket_path, 0o666)
        with self.assertRaises(RpcFault) as caught:
            rpc_call(self.socket_path, "daemon/status", {}, timeout=0.1)
        self.assertEqual(caught.exception.kind, "socket_endpoint_unsafe")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_rpc_call_refuses_symlinked_socket_before_sending_prompt(self):
        target_socket = str(Path(self.tempdir.name) / "attacker.sock")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(target_socket)
        listener.listen(1)
        os.chmod(target_socket, 0o600)
        os.symlink(target_socket, self.socket_path)
        with self.assertRaises(RpcFault) as caught:
            rpc_call(self.socket_path, "turn/start", {
                "session_id": "session-1",
                "thread_id": None,
                "prompt": "SECRET prompt",
            }, timeout=0.1)
        self.assertEqual(caught.exception.kind, "socket_endpoint_unsafe")
        listener.settimeout(0.1)
        with self.assertRaises(socket.timeout):
            listener.accept()

    def test_rpc_call_refuses_unsafe_socket_parent(self):
        parent = Path(self.tempdir.name) / "unsafe-parent"
        parent.mkdir()
        parent.chmod(0o777)
        self.socket_path = str(parent / "worker.sock")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(self.socket_path)
        listener.listen(1)
        os.chmod(self.socket_path, 0o600)
        with self.assertRaises(RpcFault) as caught:
            rpc_call(self.socket_path, "daemon/status", {}, timeout=0.1)
        self.assertEqual(caught.exception.kind, "socket_endpoint_unsafe")

    def test_rpc_call_revalidates_socket_inode_after_connect_before_sending_prompt(self):
        legitimate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        attacker = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(legitimate.close)
        self.addCleanup(attacker.close)
        legitimate.bind(self.socket_path)
        legitimate.listen(1)
        os.chmod(self.socket_path, 0o600)

        original_validate = rpc_module._validate_socket_endpoint
        captured = []
        accept_threads = []
        swapped = False

        def accept_attacker():
            conn, _ = attacker.accept()
            with conn:
                conn.settimeout(1.0)
                try:
                    captured.append(conn.recv(4096))
                except socket.timeout:
                    captured.append(b"timeout")
                with contextlib.suppress(OSError):
                    conn.sendall(b'{"jsonrpc":"2.0","id":"cli","result":{}}\n')

        def swapping_validate(path, expected=None):
            nonlocal swapped
            if expected is None:
                result = original_validate(path)
            else:
                result = original_validate(path, expected)
            if path == self.socket_path and expected is None and not swapped:
                swapped = True
                legitimate.close()
                os.unlink(self.socket_path)
                attacker.bind(self.socket_path)
                attacker.listen(1)
                os.chmod(self.socket_path, 0o600)
                thread = threading.Thread(target=accept_attacker, daemon=True)
                thread.start()
                accept_threads.append(thread)
            return result

        rpc_module._validate_socket_endpoint = swapping_validate
        try:
            with self.assertRaises(RpcFault) as caught:
                rpc_call(self.socket_path, "turn/start", {
                    "session_id": "session-1",
                    "thread_id": None,
                    "prompt": "SECRET prompt",
                }, timeout=1.0)
        finally:
            rpc_module._validate_socket_endpoint = original_validate
            for thread in accept_threads:
                thread.join(timeout=1.0)
        self.assertEqual(caught.exception.kind, "socket_endpoint_unsafe")
        self.assertTrue(captured)
        self.assertFalse(any(b"SECRET" in item for item in captured))

    def test_rpc_call_rejects_forged_response_envelope(self):
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(self.socket_path)
        listener.listen(1)
        os.chmod(self.socket_path, 0o600)

        def forged_server():
            conn, _ = listener.accept()
            with conn:
                conn.recv(4096)
                conn.sendall(b'{"jsonrpc":"2.0","id":"attacker","result":{}}\n')

        thread = threading.Thread(target=forged_server, daemon=True)
        thread.start()
        with self.assertRaises(RpcFault) as caught:
            rpc_call(self.socket_path, "daemon/status", {}, timeout=1.0)
        thread.join(timeout=1.0)
        self.assertEqual(caught.exception.kind, "daemon_protocol_error")

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

    def test_service_and_migration_rpc_use_strict_requests_and_public_faults(self):
        calls = []
        class ServiceFacade:
            def readiness(self, request):
                calls.append(("readiness", request.to_dict()))
                return Ok(type("View", (), {"to_dict": lambda self: {
                    "status": "ready", "service_version": "8.1.0"}})())
            def status(self, request):
                calls.append(("status", request.to_dict()))
                return Ok(type("View", (), {"to_dict": lambda self: {"status": "ready"}})())
            def stop(self, request):
                calls.append(("stop", request.to_dict()))
                return Err(FacadeFault(FacadeFaultCode.SERVICE_BUSY,
                    "Global service has active work", "service_busy",
                    details={"active": [{"origin": "unmapped_tui"}]},
                    next_actions=[{"command": "codex-worker daemon status",
                                   "reason": "Inspect active work"}]))
            def migration_status(self, request):
                calls.append(("migration_status", request.to_dict()))
                return Ok(type("View", (), {"to_dict": lambda self: {"status": "complete"}})())
            def migration_resolve(self, request):
                calls.append(("migration_resolve", request.to_dict()))
                return Ok(type("View", (), {"to_dict": lambda self: {"thread_id": request.thread_id}})())
        server = self.start_server(service_facade=ServiceFacade())
        self.assertEqual(rpc_call(server.socket_path, "service/readiness", {}, 1)["result"],
                         {"status": "ready", "service_version": "8.1.0"})
        self.assertEqual(rpc_call(server.socket_path, "service/status", {}, 1)["result"],
                         {"status": "ready"})
        refused = rpc_call(server.socket_path, "service/stop", {"force": False}, 1)
        self.assertEqual(refused["error"]["code"], -32040)
        self.assertEqual(refused["error"]["data"]["details"]["active"][0]["origin"],
                         "unmapped_tui")
        self.assertNotIn("--force", json.dumps(refused["error"]["data"]["next_actions"]))
        self.assertEqual(rpc_call(server.socket_path, "migration/status", {}, 1)["result"],
                         {"status": "complete"})
        resolved = rpc_call(server.socket_path, "migration/resolve", {
            "name": "legacy-a", "thread_id": "thread-a", "as_name": None}, 1)
        self.assertEqual(resolved["result"]["thread_id"], "thread-a")

    def test_force_stop_during_stopping_returns_completed_and_shuts_rpc_server(self):
        from codex_worker.facade import ServiceFacade, ServiceFacadeDeps
        from codex_worker.models import ActiveInventory, MaintenanceResult, WorkerImpact
        from codex_worker.service import (GatewayAuthentication, GlobalWorkerServiceStatus,
                                          ListenerExposure)
        from codex_worker.service_domain import ServiceConfig

        class Service:
            def status(self):
                return GlobalWorkerServiceStatus(
                    False, "ws://127.0.0.1:4500", "8.0.0", None,
                    "/tmp/private.sock", ListenerExposure.LOOPBACK,
                    GatewayAuthentication.NONE)

        class Broker(FakeBroker):
            def daemon_status(self):
                return {"worker_names": ["known-idle"]}

        class StoppingMaintenance:
            def stop(self, force):
                return MaintenanceResult.completed(
                    "stop", ActiveInventory(), force,
                    workers=WorkerImpact([], ["known-idle"]))

        broker = Broker()
        facade = ServiceFacade(ServiceFacadeDeps(
            Service(), broker, StoppingMaintenance(), object(),
            ServiceConfig("ws://127.0.0.1:4500", "8.0.0",
                          "00000000-0000-0000-0000-000000000004")))
        server = self.start_server(broker=broker, service_facade=facade)

        response = rpc_call(
            server.socket_path, "service/stop", {"force": True}, timeout=1.0)

        self.assertEqual(response["result"], {
            "action": "stop", "status": "completed", "forced": True,
            "listener": None, "inventory": {"items": []},
            "workers": {"active_names": [], "idle_names": ["known-idle"],
                        "active_count": 0, "idle_count": 1, "total_count": 1},
            "durable_state": "preserved",
        })
        server._test_thread.join(timeout=1.0)
        self.assertFalse(server._test_thread.is_alive())

    def test_encode_response_preserves_the_shared_rpc_sum_type_serializer(self):
        encoded = encode_response("x", fault=RpcFault(-32001, "unknown", "unknown_session"))
        self.assertEqual(json.loads(encoded.decode("utf-8")), {
            "jsonrpc": "2.0",
            "id": "x",
            "error": {"code": -32001, "message": "unknown",
                      "data": {"kind": "unknown_session"}},
        })

    def test_common_rpc_success_families_have_exact_public_shapes(self):
        worker = WorkerView(
            "worker-a", "00000000-0000-0000-0000-000000000001",
            "thread-a", str(Path(self.tempdir.name).resolve()), Tier.MEDIUM,
            "fake-model-a", "medium", AccessMode.FULL,
        )
        turn = TurnView("turn-a", "completed", None)
        message = AgentMessageView(
            "agent_message", "item-a", "final_answer",
            CompletionSelection.EXPLICIT_FINAL, "done",
        )
        completion = CompletionResponse(
            worker, turn, [message], None,
            {"wall_time_ms": MetricEvidence(1, "codex-worker", MetricAvailability.MEASURED)},
            RecoveryView("status", "messages", "interrupt"),
        )
        goal = GoalView(
            "thread-a", "finish", "active", 10, 1, 2,
            1787160000, 1787160001,
        )
        responses = {
            "start": completion,
            "run": completion,
            "status": WorkerStatusResponse(worker, "ready", True, None, turn),
            "messages": WorkerMessagesResponse(worker, [message], 1, 1, False, 4),
            "history": WorkerHistoryResponse(
                worker, [HistoryTurnView("turn-a", "completed", None, None, [message], None)],
                1, 1, False,
            ),
            "steer": ControlResponse(worker, "steer", True, "turn-a", "in_progress"),
            "interrupt": ControlResponse(worker, "interrupt", True, "turn-a", "interrupted"),
            "goal_set": GoalResponse(worker, "present", goal),
            "goal_show": GoalResponse(worker, "absent", None),
            "limits": LimitsResponse("available", {"primary": {"usedPercent": 1}}),
        }

        class GoldenFacade:
            def __getattr__(self, name):
                return lambda request: Ok(responses[name])

        server = self.start_server(facade=GoldenFacade())
        cases = {
            "worker/start": {"name": "worker-a", "prompt": "go", "cwd": worker.cwd,
                             "tier": "medium", "model": None, "effort": "medium",
                             "access": "full", "goal": None, "token_budget": None,
                             "output_schema": None, "timeout": None},
            "worker/run": {"name": "worker-a", "prompt": "go",
                           "output_schema": None, "timeout": None},
            "worker/status": {"name": "worker-a"},
            "worker/messages": {"name": "worker-a", "tail": 1},
            "worker/history": {"name": "worker-a", "tail": 1},
            "worker/steer": {"name": "worker-a", "prompt": "go"},
            "worker/interrupt": {"name": "worker-a"},
            "worker/goal/set": {"name": "worker-a", "objective": "finish",
                                "status": None, "token_budget": None},
            "worker/goal/show": {"name": "worker-a"},
            "account/limits": {},
        }
        expected = {
            "worker/start": completion.to_dict(), "worker/run": completion.to_dict(),
            "worker/status": responses["status"].to_dict(),
            "worker/messages": responses["messages"].to_dict(),
            "worker/history": responses["history"].to_dict(),
            "worker/steer": responses["steer"].to_dict(),
            "worker/interrupt": responses["interrupt"].to_dict(),
            "worker/goal/set": responses["goal_set"].to_dict(),
            "worker/goal/show": responses["goal_show"].to_dict(),
            "account/limits": responses["limits"].to_dict(),
        }
        for method, params in cases.items():
            with self.subTest(method=method):
                response = rpc_call(server.socket_path, method, params, timeout=1.0)
                self.assertEqual(response, {
                    "jsonrpc": "2.0", "id": "cli", "result": expected[method],
                })

    def test_cli_section_10_code_kind_pairs_are_exhaustive_and_exact(self):
        expected = {
            -32602: "invalid_params", -32004: "turn_active", -32005: "turn_not_active",
            -32011: "registry_error", -32015: "codex_protocol_error",
            -32020: "codex_failure", -32021: "worker_name_exists",
            -32022: "worker_not_found", -32023: "daemon_stopped",
            -32024: "daemon_start_failed", -32025: "timeout_active",
            -32026: "model_unavailable", -32027: "effort_unsupported",
            -32028: "limits_unavailable", -32029: "incomplete_completion",
            -32030: "daemon_stop_failed",
            -32031: "callback_unavailable", -32032: "callback_target_stale",
            -32033: "callback_target_not_found", -32034: "callback_target_ambiguous",
            -32035: "callback_target_unsafe", -32036: "callback_send_failed",
            -32037: "callback_payload_too_large",
            -32038: "tool_version_mismatch",
            -32039: "address_in_use", -32040: "service_busy",
            -32041: "legacy_name_conflict", -32042: "service_config_conflict",
        }
        self.assertEqual({code.value: kind for code, kind in FACADE_FAULT_KINDS.items()},
                         expected)
        for code in FacadeFaultCode:
            fault = FacadeFault(code, "message", expected[code.value])
            payload = rpc_module.FacadeRpcFault(fault).to_dict()
            self.assertEqual(payload["code"], code.value)
            self.assertEqual(payload["data"]["kind"], expected[code.value])
            self.assertEqual(set(payload["data"]), {
                "kind", "retryable", "source", "details", "known_ids", "next_actions",
            })

    def test_registry_storage_fault_rpc_adapter_preserves_all_known_recovery_ids(self):
        known = {"name": "worker-a",
                 "session_id": "session-a", "thread_id": "thread-a", "turn_id": None}
        fault = FacadeFault(FacadeFaultCode.REGISTRY_ERROR,
                            "Could not persist callback binding", "registry_error",
                            known_ids=known)
        payload = rpc_module.FacadeRpcFault(fault).to_dict()
        self.assertEqual(payload["code"], -32011)
        self.assertEqual(payload["data"]["known_ids"], known)


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

    def test_version_is_terminal_plain_text_and_never_touches_runtime(self):
        forbidden = []
        original_rpc_call = cli.rpc_call
        original_instance_manager = cli._instance_manager
        original_serve = cli._serve
        cli.rpc_call = lambda *args, **kwargs: forbidden.append("rpc")
        cli._instance_manager = lambda *args, **kwargs: forbidden.append("instance")
        cli._serve = lambda *args, **kwargs: forbidden.append("serve")
        try:
            completed = self.run_cli(
                ["--pretty", "--version"],
                include_socket=False,
            )
        finally:
            cli.rpc_call = original_rpc_call
            cli._instance_manager = original_instance_manager
            cli._serve = original_serve
        self.assertEqual(completed.returncode, 0)
        self.assertRegex(completed.stdout, r"^codex-worker \d+\.\d+\.\d+\n$")
        self.assertEqual(completed.stderr, "")
        self.assertEqual(forbidden, [])
        with self.assertRaises(json.JSONDecodeError):
            json.loads(completed.stdout)

    def test_global_parser_removes_instance_shutdown_and_adds_guarded_service_migration(self):
        parser = build_parser()
        restart = parser.parse_args(["daemon", "restart", "--force",
                                     "--app-server-listen", "ws://localhost:4600"])
        self.assertEqual((restart.method, restart.force, restart.app_server_listen),
                         ("service/restart", True, "ws://localhost:4600"))
        resolve = parser.parse_args(["migration", "resolve", "--name", "legacy-a",
                                     "--thread", "thread-a", "--as-name", "legacy-b"])
        self.assertEqual(resolve.method, "migration/resolve")
        for argv in (["--instance", "old", "status", "--name", "a"],
                     ["daemon", "shutdown"]):
            completed = self.run_cli(list(argv), fake_rpc=self.fake_rpc_success,
                                     include_socket=False)
            payload = self.assert_json_error(completed, 2, "invalid_params")
            if "--instance" in argv:
                self.assertIn("migration status",
                              payload["error"]["data"]["details"]["reason"])
        self.assertEqual(self.rpc_calls, [])

    def test_global_common_autoensure_and_explicit_socket_raw_bypass(self):
        managed = []
        class Manager:
            deps = type("Deps", (), {"paths": type("Paths", (), {
                "rpc_socket": Path(self.socket_path)})()})()
            def ensure_running(inner, listener=None):
                managed.append(("ensure", listener)); return type("S", (), {"status": "ready"})()
            def status(inner):
                managed.append(("status", None)); return type("S", (), {
                    "status": "ready", "service_version": cli.distribution_version(),
                    "to_dict": lambda self: {"status": "ready"}})()
        with mock.patch.object(cli, "_service_manager", return_value=Manager()), \
                mock.patch.object(cli, "rpc_call", side_effect=self.fake_rpc_success):
            common = self.run_cli(["status", "--name", "worker-a"],
                                  include_socket=False)
            self.assertEqual(common.returncode, 0, common.stderr)
            raw = self.run_cli(["--socket", self.socket_path, "model", "list"],
                               include_socket=False)
            self.assertEqual(raw.returncode, 0, raw.stderr)
        self.assertEqual(managed, [("ensure", None)])

    def test_loaded_plugin_version_skew_is_typed_before_any_runtime_contact(self):
        plugin = Path(self.tempdir.name) / "cached-plugin"
        manifest = plugin / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps({"name": "superdev", "version": "0.0.1"}) + "\n",
            encoding="utf-8",
        )
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(plugin)}):
            completed = self.run_cli(
                ["model", "list"], fake_rpc=self.fake_rpc_success, include_socket=True,
            )
            self.assert_json_error(completed, 3, "tool_version_mismatch")
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["error"]["data"]["details"]["loaded_version"], "0.0.1")
        self.assertEqual(payload["error"]["data"]["details"]["installed_version"],
                         cli.distribution_version())
        self.assertTrue(payload["error"]["data"]["next_actions"])
        self.assertEqual(self.rpc_calls, [])

    def test_local_invalid_params_precede_loaded_plugin_version_skew(self):
        plugin = Path(self.tempdir.name) / "cached-plugin"
        manifest = plugin / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"version": "0.0.1"}) + "\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(plugin)}):
            completed = self.run_cli(
                ["start", "--name", "bad/name", "--prompt", "one"],
                fake_rpc=self.fake_rpc_success,
            )
        self.assert_json_error(completed, 2, "invalid_params")
        self.assertEqual(self.rpc_calls, [])

    def test_loaded_plugin_version_skew_guards_foreground_daemon_serve(self):
        plugin = Path(self.tempdir.name) / "cached-plugin"
        manifest = plugin / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"version": "0.0.1"}) + "\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(plugin)}), \
                mock.patch.object(cli, "_serve") as serve:
            completed = self.run_cli(["daemon", "serve"])
            self.assert_json_error(completed, 3, "tool_version_mismatch")
        serve.assert_not_called()

    def test_managed_raw_families_refuse_old_daemon_before_requested_rpc(self):
        for command, requested_method in (
                (["model", "list"], "model/list"),
                (["session", "list"], "session/list")):
            with self.subTest(command=command):
                self.rpc_calls = []
                manager = type("Manager", (), {
                    "deps": type("Deps", (), {"paths": type("Paths", (), {
                        "rpc_socket": Path(self.socket_path)})()})(),
                    "readiness": lambda self: type("Status", (), {
                        "status": "ready", "service_version": "0.0.1"})(),
                })()
                with mock.patch.object(cli, "_service_manager", return_value=manager):
                    completed = self.run_cli(command, fake_rpc=self.fake_rpc_success,
                                             include_socket=False)
                payload = self.assert_json_error(completed, 3, "tool_version_mismatch")
                details = payload["error"]["data"]["details"]
                self.assertEqual(details["actual_version"], "0.0.1")
                self.assertEqual(details["expected_version"], cli.distribution_version())
                self.assertEqual(self.rpc_calls, [])
                self.assertIn(
                    "codex-worker daemon status",
                    payload["error"]["data"]["next_actions"][0]["command"],
                )

    def test_managed_raw_stopped_daemon_preserves_no_autostart_refusal(self):
        manager = type("Manager", (), {
            "deps": type("Deps", (), {"paths": type("Paths", (), {
                "rpc_socket": Path(self.socket_path)})()})(),
            "readiness": lambda self: None,
        })()
        with mock.patch.object(cli, "_spawn_daemon") as spawn, \
                mock.patch.object(cli, "_service_manager", return_value=manager):
            completed = self.run_cli(
                ["model", "list"],
                fake_rpc=self.fake_rpc_success,
                include_socket=False,
            )
        self.assert_json_error(completed, 3, "daemon_unavailable")
        self.assertEqual(self.rpc_calls, [])
        spawn.assert_not_called()

    def test_managed_raw_failed_status_refuses_before_target_rpc(self):
        manager = type("Manager", (), {
            "deps": type("Deps", (), {"paths": type("Paths", (), {
                "rpc_socket": Path(self.socket_path)})()})(),
            "readiness": lambda self: None,
        })()
        with mock.patch.object(cli, "_service_manager", return_value=manager):
            completed = self.run_cli(["session", "list"],
                                     fake_rpc=self.fake_rpc_success,
                                     include_socket=False)
        self.assert_json_error(completed, 3, "daemon_unavailable")
        self.assertEqual(self.rpc_calls, [])

    def test_message_parser_maps_strict_prose_file_surface(self):
        parser = build_parser()
        args = parser.parse_args(["message", "--name", "build-1", "--message", "progress"])
        self.assertEqual(args.method, "worker/message")
        self.assertEqual(_params_for(args), {
            "name": "build-1", "message": "progress", "priority": "next",
            "cc_agent_name": None,
        })

    def test_message_local_input_refusals_are_one_json_and_never_connect(self):
        empty = Path(self.tempdir.name) / "empty-message.txt"
        empty.write_text("", encoding="utf-8")
        cases = [
            ["message", "--name", "build-1", "--message", ""],
            ["message", "--name", "build-1", "--message-file", str(empty)],
            ["message", "--name", "build-1", "--message-file", str(empty.parent / "missing.txt")],
            ["message", "--name", "bad name", "--message", "progress"],
            ["message", "--name", "build-1", "--message", "progress", "--priority", "invalid"],
            ["message", "--name", "build-1", "--message", "a", "--message-file", str(empty)],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                self.rpc_calls = []
                completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success, include_socket=False)
                self.assert_json_error(completed, 2)
                self.assertEqual(self.rpc_calls, [])

    def test_oversized_unicode_message_reaches_daemon_for_final_envelope_sizing(self):
        huge = Path(self.tempdir.name) / "huge-unicode.txt"
        huge.write_text("😀" * 600000, encoding="utf-8")
        completed = self.run_cli(
            ["message", "--name", "build-1", "--message-file", str(huge)],
            fake_rpc=self.fake_rpc_success, include_socket=False)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(len(self.rpc_calls), 1)
        self.assertEqual(self.rpc_calls[0][0], "worker/message")
        self.assertEqual(self.rpc_calls[0][1]["message"], "😀" * 600000)

    def test_managed_daemon_start_is_an_explicit_json_lifecycle_action(self):
        class Manager:
            def require_external_codex(self):
                raise AssertionError("a ready managed peer must not require client PATH codex")
            def ensure_running(self, listener=None):
                return type("Readiness", (), {"status": "ready"})()
            def status(self):
                return type("Status", (), {"to_dict": lambda self: {
                    "status": "ready", "instance": {"instance": "chosen"},
                }})()
        original = cli._service_manager
        cli._service_manager = lambda: Manager()
        try:
            completed = self.run_cli(
                ["daemon", "start"], include_socket=False)
        finally:
            cli._service_manager = original
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["result"]["status"], "ready")
        self.assertEqual(completed.stderr, "")

    def test_daemon_launcher_prefers_source_adjacent_entrypoint_over_argv0(self):
        original = sys.argv[0]
        sys.argv[0] = "codex-worker"
        try:
            launcher = cli._daemon_launcher()
        finally:
            sys.argv[0] = original
        self.assertEqual(
            launcher,
            str(ROOT / "skills" / "subagent-driven-development" / "scripts" / "codex-worker"),
        )

    def test_message_rejects_socket_and_stopped_daemon_does_not_autostart(self):
        self.rpc_calls = []
        socket_refusal = self.run_cli(["message", "--name", "build-1", "--message", "progress"],
                                      fake_rpc=self.fake_rpc_success, include_socket=True)
        self.assert_json_error(socket_refusal, 2)
        self.assertEqual(self.rpc_calls, [])
        original_endpoint = cli._common_endpoint
        calls = []
        cli._common_endpoint = lambda instance, autostart: calls.append(autostart) or (_ for _ in ()).throw(
            FacadeFault(FacadeFaultCode.DAEMON_STOPPED, "Worker daemon is stopped", "daemon_stopped"))
        try:
            stopped = self.run_cli(["message", "--name", "build-1", "--message", "progress"],
                                   include_socket=False)
        finally:
            cli._common_endpoint = original_endpoint
        self.assert_json_error(stopped, 3, "daemon_stopped")
        self.assertEqual(calls, [True])

    def fake_codex_bin(self):
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
        return fake_bin

    def run_cli(self, argv, fake_rpc=None, include_socket=True):
        out = io.StringIO()
        err = io.StringIO()
        original_rpc_call = cli.rpc_call
        original_common_endpoint = cli._common_endpoint
        if fake_rpc is not None:
            cli.rpc_call = fake_rpc
            cli._common_endpoint = lambda instance, autostart: self.socket_path
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                prefix = ["--socket", self.socket_path] if include_socket else []
                code = cli.main(prefix + list(argv))
        finally:
            cli.rpc_call = original_rpc_call
            cli._common_endpoint = original_common_endpoint
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

    def assert_json_error(self, completed, expected_exit, expected_kind="invalid_params"):
        self.assertEqual(completed.returncode, expected_exit)
        lines = completed.stdout.splitlines()
        self.assertEqual(len(lines), 1, completed.stderr)
        payload = json.loads(lines[0])
        self.assertEqual(payload.get("jsonrpc"), "2.0")
        self.assertEqual(payload.get("id"), "cli")
        self.assertEqual(set(payload), {"jsonrpc", "id", "error"})
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["data"]["kind"], expected_kind)
        return payload

    def test_every_client_command_emits_one_json_object(self):
        cases = documented_client_argv_cases(
            self.cwd, self.session_id, self.thread_id, self.prompt_file
        )
        self.assertEqual(len(cases), 12)
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
                self.assertEqual(payload, {
                    "jsonrpc": "2.0", "id": "cli",
                    "result": {"method": case.method, "params": case.expected_params},
                })

    def test_every_managed_raw_client_preserves_raw_response(self):
        cases = [case for case in documented_client_argv_cases(
            self.cwd, self.session_id, self.thread_id, self.prompt_file
        ) if case.method != "daemon/status"]
        original_manager = cli._service_manager
        manager = type("Manager", (), {
            "deps": type("Deps", (), {
                "paths": type("Paths", (), {"rpc_socket": Path(self.socket_path)})(),
            })(),
            "readiness": lambda self: type("Readiness", (), {
                "status": "ready", "service_version": cli.distribution_version(),
            })(),
            "status": lambda self: (_ for _ in ()).throw(
                AssertionError("managed raw dispatch must not enumerate inventory")),
        })()
        cli._service_manager = lambda: manager
        try:
            for case in cases:
                with self.subTest(method=case.method):
                    self.rpc_calls = []
                    completed = self.run_cli(
                        case.argv,
                        fake_rpc=self.fake_rpc_success, include_socket=False,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(json.loads(completed.stdout), {
                        "jsonrpc": "2.0", "id": "cli",
                        "result": {"method": case.method, "params": case.expected_params},
                    })
        finally:
            cli._service_manager = original_manager

    def test_common_wait_timeout_maps_to_socket_timeout_without_cancelling(self):
        cases = [
            (["start", "--name", "a", "--prompt", "go", "--cwd", self.cwd], None),
            (["run", "--name", "a", "--prompt", "go"], None),
            (["start", "--name", "a", "--prompt", "go", "--cwd", self.cwd,
              "--timeout", "0"], 5.0),
            (["run", "--name", "a", "--prompt", "go", "--timeout", "2.5"], 7.5),
        ]
        for argv, expected_timeout in cases:
            with self.subTest(argv=argv):
                self.rpc_calls = []
                completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success,
                                         include_socket=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(self.rpc_calls[0][2], expected_timeout)

    def test_managed_daemon_success_models_have_exact_cli_shapes(self):
        instance = {
            "instance": "chosen", "source": "flag",
            "durable_dir": str(Path(self.tempdir.name) / "durable"),
            "socket_path": self.socket_path,
            "log_path": str(Path(self.tempdir.name) / "daemon.log"),
        }
        status = {
            "instance": instance, "status": "ready", "daemon_pid": 101,
            "codex_pid": 102, "worker_count": 3,
            "readiness": {"ready": True}, "last_error": None,
        }
        stopped = {
            "instance": instance, "status_before": "ready", "status_after": "stopped",
            "daemon_pid": 101, "codex_pid": 102, "durable_state": "preserved",
            "worker_count": 3,
        }

        class Result:
            def __init__(self, value): self.value = value
            def to_dict(self): return self.value

        manager = type("Manager", (), {
            "status": lambda self: Result(status),
            "stop": lambda self, force=False: stopped,
        })()
        original = cli._service_manager
        cli._service_manager = lambda: manager
        try:
            for argv, result in ((["daemon", "status"], status),
                                 (["daemon", "stop"], stopped)):
                with self.subTest(argv=argv):
                    completed = self.run_cli(argv, include_socket=False)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(json.loads(completed.stdout), {
                        "jsonrpc": "2.0", "id": "cli", "result": result,
                    })
        finally:
            cli._service_manager = original

    def test_typed_rpc_error_is_structured_and_exits_three(self):
        def fake_rpc_error(socket_path, method, params, timeout):
            return {"jsonrpc": "2.0", "id": "cli",
                    "error": {"code": -32005, "message": "turn is not active",
                              "data": {"kind": "turn_not_active"}}}

        completed = self.run_cli(["turn", "steer", "--session", self.session_id,
                                  "--prompt", "try anyway"], fake_rpc=fake_rpc_error)
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(json.loads(completed.stdout)["error"]["data"]["kind"], "turn_not_active")

    def test_rpc_internal_error_is_the_only_typed_exit_one(self):
        for kind in ("internal_error", "broker_error"):
            def fake_internal(socket_path, method, params, timeout, kind=kind):
                return {"jsonrpc": "2.0", "id": "cli",
                        "error": {"code": -32603, "message": "Internal error",
                                  "data": {"kind": kind}}}

            with self.subTest(kind=kind):
                completed = self.run_cli(
                    ["--socket", self.socket_path, "model", "list"],
                    fake_rpc=fake_internal, include_socket=False)
                self.assert_json_error(completed, 1, kind)

    def test_daemon_absent_is_structured_and_exits_three(self):
        completed = self.run_cli(["daemon", "status"], fake_rpc=None)
        self.assertEqual(completed.returncode, 3)
        lines = completed.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["error"]["data"]["kind"], "daemon_unavailable")

    def test_common_stopped_refusal_is_one_exact_operational_json_object(self):
        original = cli._common_endpoint
        cli._common_endpoint = lambda instance, autostart: (_ for _ in ()).throw(
            FacadeFault(FacadeFaultCode.DAEMON_STOPPED, "Worker daemon is stopped",
                        "daemon_stopped")
        )
        try:
            completed = self.run_cli(["status", "--name", "worker-a"],
                                     include_socket=False)
        finally:
            cli._common_endpoint = original
        payload = self.assert_json_error(completed, 3, "daemon_stopped")
        self.assertEqual(payload["error"]["code"], -32023)
        self.assertEqual(set(payload["error"]["data"]), {
            "kind", "retryable", "source", "details", "known_ids", "next_actions",
        })

    def test_known_stopped_worker_rpc_refusal_keeps_ids_and_runnable_actions(self):
        known = {
            "name": "stopped-worker", "session_id": "session-known",
            "thread_id": "thread-known", "turn_id": None,
        }
        actions = [
            {"command": "codex-worker daemon start", "reason": "Start the service"},
            {"command": "codex-worker status --name stopped-worker",
             "reason": "Check the known worker"},
            {"command": "codex --remote ws://127.0.0.1:4500 resume thread-known",
             "reason": "Resume the known thread"},
        ]

        def fake_stopped(socket_path, method, params, timeout):
            fault = FacadeFault(
                FacadeFaultCode.DAEMON_STOPPED, "Worker daemon is stopped",
                "daemon_stopped", known_ids=known, next_actions=actions)
            return {"jsonrpc": "2.0", "id": "cli",
                    "error": rpc_module.FacadeRpcFault(fault).to_dict()}

        completed = self.run_cli(
            ["status", "--name", known["name"]], fake_rpc=fake_stopped,
            include_socket=False)

        payload = self.assert_json_error(completed, 3, "daemon_stopped")
        self.assertEqual(payload["error"]["data"]["known_ids"], known)
        self.assertEqual(payload["error"]["data"]["next_actions"], actions)
        cli._validate_wire_recovery_actions(payload)

    def test_legacy_instance_environment_has_no_routing_effect(self):
        with mock.patch.dict(os.environ, {"CODEX_WORKER_INSTANCE": "hostile; no"}), \
                mock.patch.object(cli, "rpc_call", side_effect=self.fake_rpc_success), \
                mock.patch.object(cli, "_common_endpoint", return_value=self.socket_path):
            completed = self.run_cli(["status", "--name", "worker-a"],
                                     include_socket=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("hostile", completed.stdout)

    def test_pretty_is_rejected_for_foreground_serve(self):
        completed = self.run_cli(["--pretty", "daemon", "serve"])
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")

    def test_help_remains_normal_argparse_output(self):
        completed = self.run_cli(["--help"])
        self.assertEqual(completed.returncode, 0)
        self.assertTrue(completed.stdout.startswith("usage: codex-worker"))
        self.assertNotIn('"jsonrpc"', completed.stdout)

        daemon = self.run_cli(["daemon", "--help"])
        self.assertEqual(daemon.returncode, 0)
        self.assertNotIn("serve", daemon.stdout)
        self.assertNotIn("shutdown", daemon.stdout)
        self.assertNotIn("instance", daemon.stdout)

    def test_usage_errors_emit_one_json_object_and_exit_two(self):
        identifier = self.run_cli(["session", "show", "--session", self.session_id,
                                   "--thread", self.thread_id])
        self.assert_json_error(identifier, 2)
        self.assertIn("error:", identifier.stderr)
        prompt = self.run_cli(["turn", "start", "--session", self.session_id,
                               "--prompt", "inline", "--prompt-file", str(self.prompt_file)])
        self.assert_json_error(prompt, 2)
        non_finite = self.run_cli(["turn", "wait", "--session", self.session_id,
                                   "--timeout", "inf"])
        self.assert_json_error(non_finite, 2)
        self.assertNotIn("Traceback", non_finite.stderr)
        unsupported_turn = self.run_cli(["turn", "wait", "--turn", "turn-1", "--timeout", "0"])
        payload = self.assert_json_error(unsupported_turn, 2)
        reason = payload["error"]["data"]["details"]["reason"]
        self.assertIn("unsupported argument --turn", reason)
        self.assertIn("--session", reason)
        self.assertIn("--thread", reason)
        self.assertIn("error:", unsupported_turn.stderr)

    def test_pretty_usage_errors_honor_pretty_flag(self):
        completed = self.run_cli(["--pretty", "session", "show", "--session", self.session_id,
                                  "--thread", self.thread_id])
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["error"]["data"]["kind"], "invalid_params")
        self.assertIn("\n  ", completed.stdout)
        self.assertIn("error:", completed.stderr)

    def test_session_resume_name_is_only_valid_for_raw_thread_recovery(self):
        completed = self.run_cli(["session", "resume", "--session", self.session_id,
                                  "--name", "forbidden"], fake_rpc=self.fake_rpc_success)
        payload = self.assert_json_error(completed, 2)
        self.assertIn("--name", payload["error"]["data"]["details"]["reason"])
        self.assertEqual(self.rpc_calls, [])

    def test_prompt_validation_is_local_and_structured(self):
        cases = [
            ["turn", "start", "--session", self.session_id, "--prompt", ""],
            ["turn", "steer", "--session", self.session_id, "--prompt-file", ""],
            ["turn", "steer", "--session", self.session_id,
             "--prompt-file", str(Path(self.tempdir.name) / "missing.txt")],
        ]
        empty_prompt_file = Path(self.tempdir.name) / "empty.txt"
        empty_prompt_file.write_text("", encoding="utf-8")
        cases.append(["turn", "start", "--session", self.session_id,
                      "--prompt-file", str(empty_prompt_file)])
        for argv in cases:
            with self.subTest(argv=argv):
                self.rpc_calls = []
                completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success)
                self.assert_json_error(completed, 2)
                self.assertEqual(self.rpc_calls, [])

    def test_pretty_prints_one_json_object_for_client_commands(self):
        completed = self.run_cli(["--pretty", "daemon", "status"], fake_rpc=self.fake_rpc_success)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(len(json.loads(completed.stdout)), 3)
        self.assertIn("\n  ", completed.stdout)

    def test_common_command_matrix_builds_exact_rpc_requests(self):
        cases = [
            (['start', '--name', 'build-1', '--prompt', 'go', '--cwd', self.cwd, '--no-callback'], 'worker/start',
             {'name': 'build-1', 'prompt': 'go', 'cwd': self.cwd, 'tier': 'medium',
              'model': None, 'effort': 'medium', 'access': 'full', 'goal': None,
              'token_budget': None, 'output_schema': None, 'timeout': None,
              'no_callback': True, 'callback_capture': None}),
            (['run', '--name', 'build-1', '--prompt', 'again'], 'worker/run',
             {'name': 'build-1', 'prompt': 'again', 'output_schema': None, 'timeout': None}),
            (['status', '--name', 'build-1'], 'worker/status', {'name': 'build-1'}),
            (['messages', '--name', 'build-1', '--tail', '2'], 'worker/messages', {'name': 'build-1', 'tail': 2}),
            (['history', '--name', 'build-1'], 'worker/history', {'name': 'build-1', 'tail': 1}),
            (['steer', '--name', 'build-1', '--prompt', 'focus'], 'worker/steer', {'name': 'build-1', 'prompt': 'focus'}),
            (['interrupt', '--name', 'build-1'], 'worker/interrupt', {'name': 'build-1'}),
            (['goal', 'set', '--name', 'build-1', '--goal', 'finish'], 'worker/goal/set',
             {'name': 'build-1', 'objective': 'finish', 'status': None, 'token_budget': None}),
            (['goal', 'show', '--name', 'build-1'], 'worker/goal/show', {'name': 'build-1'}),
            (['limits'], 'account/limits', {}),
        ]
        for argv, method, params in cases:
            with self.subTest(argv=argv):
                self.rpc_calls = []
                result = self.run_cli(argv, fake_rpc=self.fake_rpc_success, include_socket=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.rpc_calls[0][0:2], (method, params))

    def test_common_commands_reject_socket_and_creation_flags_on_run(self):
        rejected = [
            ['--socket', self.socket_path, 'start', '--name', 'build-1', '--prompt', 'go'],
            ['run', '--name', 'build-1', '--prompt', 'go', '--cwd', self.cwd],
            ['goal', 'set', '--name', 'build-1'],
            ['start', '--name', 'build-1', '--prompt', 'go', '--token-budget', '1'],
        ]
        for argv in rejected:
            with self.subTest(argv=argv):
                result = self.run_cli(argv, fake_rpc=self.fake_rpc_success,
                                      include_socket=False)
                self.assert_json_error(result, 2)
        self.assertEqual(self.rpc_calls, [])

    def test_every_common_command_rejects_explicit_socket_before_rpc(self):
        commands = [
            ["start", "--name", "a", "--prompt", "go"],
            ["run", "--name", "a", "--prompt", "go"],
            ["status", "--name", "a"],
            ["messages", "--name", "a"],
            ["history", "--name", "a"],
            ["steer", "--name", "a", "--prompt", "go"],
            ["interrupt", "--name", "a"],
            ["goal", "set", "--name", "a", "--status", "paused"],
            ["goal", "show", "--name", "a"],
            ["limits"],
        ]
        for command in commands:
            with self.subTest(command=command):
                self.rpc_calls = []
                completed = self.run_cli(
                    ["--socket", self.socket_path] + command,
                    fake_rpc=self.fake_rpc_success, include_socket=False,
                )
                self.assert_json_error(completed, 2)
                self.assertEqual(self.rpc_calls, [])

    def test_invalid_explicit_instance_is_local_and_does_not_reach_rpc(self):
        completed = self.run_cli(
            ["--instance", "", "status", "--name", "a"], include_socket=False,
        )
        self.assert_json_error(completed, 2)
        self.assertEqual(self.rpc_calls, [])

    def test_common_parser_exhaustively_validates_names_prompts_and_turn_options(self):
        schema = Path(self.tempdir.name) / "schema.json"
        schema.write_text('{"type":"object"}', encoding="utf-8")
        non_object_schema = Path(self.tempdir.name) / "schema-array.json"
        non_object_schema.write_text('[]', encoding="utf-8")
        malformed_schema = Path(self.tempdir.name) / "schema-bad.json"
        malformed_schema.write_text('{', encoding="utf-8")
        valid = [
            ["start", "--name", "a", "--prompt", "go", "--cwd", self.cwd],
            ["start", "--name", "a" * 128, "--prompt-file", str(self.prompt_file),
             "--cwd", self.cwd, "--goal", "finish", "--token-budget", "1",
             "--output-schema", str(schema), "--timeout", "0", "--read-only"],
            ["start", "--name", "raw", "--prompt", "go", "--cwd", self.cwd,
             "--model", "fake-model", "--effort", "high"],
            ["run", "--name", "a", "--prompt", "go", "--output-schema", str(schema),
             "--timeout", "1e10"],
            ["goal", "set", "--name", "a", "--status", "paused"],
            ["goal", "set", "--name", "a", "--token-budget", "2"],
            ["messages", "--name", "a", "--tail", "1"],
            ["history", "--name", "a", "--tail", "999"],
        ]
        for argv in valid:
            with self.subTest(valid=argv):
                self.rpc_calls = []
                completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success,
                                         include_socket=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(len(completed.stdout.splitlines()), 1)
                self.assertEqual(len(self.rpc_calls), 1)

        invalid = [
            ["start", "--name", "_bad", "--prompt", "go"],
            ["start", "--name", "bad/name", "--prompt", "go"],
            ["start", "--name", "a" * 129, "--prompt", "go"],
            ["start", "--name", "a", "--prompt", ""],
            ["start", "--name", "a", "--prompt", "go", "--prompt-file", str(self.prompt_file)],
            ["start", "--name", "a"],
            ["start", "--name", "a", "--prompt", "go", "--cwd", str(Path(self.cwd) / "missing")],
            ["start", "--name", "a", "--prompt", "go", "--tier", "medium", "--model", "fake-model"],
            ["start", "--name", "a", "--prompt", "go", "--tier", "unknown"],
            ["start", "--name", "a", "--prompt", "go", "--model", ""],
            ["start", "--name", "a", "--prompt", "go", "--effort", ""],
            ["start", "--name", "a", "--prompt", "go", "--goal", ""],
            ["start", "--name", "a", "--prompt", "go", "--goal", "x" * 4001],
            ["start", "--name", "a", "--prompt", "go", "--token-budget", "0"],
            ["run", "--name", "a", "--prompt", "go", "--tier", "medium"],
            ["run", "--name", "a", "--prompt", "go", "--model", "fake-model"],
            ["run", "--name", "a", "--prompt", "go", "--read-only"],
            ["run", "--name", "a", "--prompt", "go", "--goal", "finish"],
            ["run", "--name", "a", "--prompt", "go", "--token-budget", "2"],
            ["run", "--name", "a", "--prompt", "go", "--effort", "high"],
            ["run", "--name", "a", "--prompt", "go", "--output-schema", str(non_object_schema)],
            ["run", "--name", "a", "--prompt", "go", "--output-schema", str(malformed_schema)],
            ["run", "--name", "a", "--prompt", "go", "--output-schema", str(schema) + ".missing"],
            ["run", "--name", "a", "--prompt", "go", "--timeout", "-1"],
            ["run", "--name", "a", "--prompt", "go", "--timeout", "nan"],
            ["run", "--name", "a", "--prompt", "go", "--timeout", "inf"],
            ["run", "--name", "a", "--prompt", "go", "--timeout", "1e309"],
            ["messages", "--name", "a", "--tail", "0"],
            ["history", "--name", "a", "--tail", "-1"],
            ["goal", "set", "--name", "a"],
            ["goal", "set", "--name", "a", "--goal", "x" * 4001],
            ["goal", "set", "--name", "a", "--token-budget", "0"],
            ["goal", "set", "--name", "a", "--status", "unknown"],
        ]
        for argv in invalid:
            with self.subTest(invalid=argv):
                self.rpc_calls = []
                completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success,
                                         include_socket=False)
                self.assert_json_error(completed, 2)
                self.assertEqual(self.rpc_calls, [])

    def test_endpoint_selector_matrix_and_absolute_socket_validation(self):
        valid = [
            (["start", "--name", "a", "--prompt", "go", "--cwd", self.cwd], False),
            (["model", "list"], False),
            (["--socket", self.socket_path, "model", "list"], False),
            (["daemon", "status"], False),
            (["--socket", self.socket_path, "daemon", "status"], False),
            (["daemon", "stop"], False),
            (["migration", "status"], False),
        ]
        original_manager = cli._service_manager

        class Manager:
            deps = type("Deps", (), {"paths": type("Paths", (), {
                "rpc_socket": Path(self.socket_path)})()})()
            def status(inner):
                return type("Response", (), {
                    "status": "ready", "last_error": None,
                    "service_version": cli.distribution_version(),
                    "to_dict": lambda self: {"status": "ready"},
                })()
            def ensure_running(inner, listener=None):
                return inner.status()
            def readiness(inner):
                return type("Response", (), {
                    "status": "ready", "service_version": cli.distribution_version(),
                })()
            def stop(inner, force=False):
                return {"status_after": "stopped", "force": force}

        cli._service_manager = lambda: Manager()
        try:
            for argv, include_socket in valid:
                with self.subTest(valid=argv):
                    self.rpc_calls = []
                    completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success,
                                             include_socket=include_socket)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(len(completed.stdout.splitlines()), 1)
        finally:
            cli._service_manager = original_manager

        invalid = [
            ["--socket", self.socket_path, "--instance", "chosen", "model", "list"],
            ["--socket", self.socket_path, "start", "--name", "a", "--prompt", "go",
             "--cwd", self.cwd],
            ["--socket", self.socket_path, "daemon", "stop"],
            ["--instance", "chosen", "daemon", "shutdown"],
            ["--instance", "chosen", "daemon", "serve"],
            ["--pretty", "daemon", "serve"],
            ["--socket", "relative.sock", "model", "list"],
            ["--socket", "relative.sock", "daemon", "serve"],
            ["--socket", self.socket_path, "daemon", "serve", "--state", "relative.json"],
            ["--socket", self.socket_path, "session", "start", "--cwd", "."],
        ]
        original_serve = cli._serve
        serve_calls = []
        cli._serve = lambda args: serve_calls.append(args) or 99
        try:
            for argv in invalid:
                with self.subTest(invalid=argv):
                    self.rpc_calls = []
                    completed = self.run_cli(argv, fake_rpc=self.fake_rpc_success,
                                             include_socket=False)
                    is_serve = "daemon" in argv and "serve" in argv
                    if is_serve and "--instance" not in argv:
                        self.assertEqual(completed.returncode, 2)
                        self.assertEqual(completed.stdout, "")
                    else:
                        self.assert_json_error(completed, 2)
                    self.assertEqual(self.rpc_calls, [])
        finally:
            cli._serve = original_serve
        self.assertEqual(serve_calls, [])

    def test_invalid_common_request_never_selects_or_starts_an_endpoint(self):
        called = []
        original = cli._common_endpoint
        cli._common_endpoint = lambda instance, autostart: called.append((instance, autostart))
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(['start', '--name', 'bad/name', '--prompt', 'go'])
        finally:
            cli._common_endpoint = original
        result = type("Completed", (), {"returncode": code, "stdout": out.getvalue(), "stderr": err.getvalue()})()
        self.assert_json_error(result, 2)
        self.assertEqual(called, [])
        self.assertEqual(self.rpc_calls, [])

    def test_invalid_raw_selector_never_selects_or_contacts_managed_service(self):
        with mock.patch.object(cli, "_service_manager") as manager, \
                mock.patch.object(cli, "rpc_call") as contact:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(["turn", "status", "--session", ""])
        result = type("Completed", (), {
            "returncode": code, "stdout": out.getvalue(), "stderr": err.getvalue()})()
        payload = self.assert_json_error(result, 2, "invalid_params")
        self.assertIn("non-empty", payload["error"]["data"]["details"]["reason"])
        manager.assert_not_called()
        contact.assert_not_called()

    def test_foreground_serve_has_no_stdout_and_sigterm_preserves_registry(self):
        script = ROOT / "skills" / "subagent-driven-development" / "scripts" / "codex-worker"
        fake_bin = self.fake_codex_bin()
        listener = _unused_loopback_listener()
        state_path = str(Path(self.tempdir.name) / "sessions.json")
        proc = subprocess.Popen(
            [sys.executable, str(script), "--socket", self.socket_path,
             "daemon", "serve", "--state", state_path, "--codex-bin", str(fake_bin),
             "--event-limit", "5", "--app-server-listen", listener],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(os.environ, PYTHONPATH=_websockets_pythonpath(),
                     FAKE_CODEX_ERROR=str(Path(self.tempdir.name) / "fake-error.txt"),
                     TMPDIR=self.tempdir.name),
        )
        try:
            deadline = time.time() + 5.0
            status = None
            while time.time() < deadline:
                if proc.poll() is not None:
                    stdout, stderr = proc.communicate(timeout=1.0)
                    child_error = Path(self.tempdir.name, "fake-error.txt")
                    self.fail("daemon exited before ready: stdout=%r stderr=%r child=%r" %
                              (stdout, stderr, child_error.read_text() if child_error.exists() else None))
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
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=5.0)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5.0)
        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(stdout, "")
        self.assertTrue(Path(state_path).exists())

    def test_foreground_serve_handles_sigterm_without_stdout(self):
        script = ROOT / "skills" / "subagent-driven-development" / "scripts" / "codex-worker"
        fake_bin = self.fake_codex_bin()
        listener = _unused_loopback_listener()
        state_path = str(Path(self.tempdir.name) / "sigterm-sessions.json")
        proc = subprocess.Popen(
            [sys.executable, str(script), "--socket", self.socket_path,
             "daemon", "serve", "--state", state_path, "--codex-bin", str(fake_bin),
             "--event-limit", "5", "--app-server-listen", listener],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(os.environ, PYTHONPATH=_websockets_pythonpath(),
                     FAKE_CODEX_ERROR=str(Path(self.tempdir.name) / "fake-error.txt"),
                     TMPDIR=self.tempdir.name),
        )
        try:
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if proc.poll() is not None:
                    stdout, stderr = proc.communicate(timeout=1.0)
                    child_error = Path(self.tempdir.name, "fake-error.txt")
                    self.fail("daemon exited before ready: stdout=%r stderr=%r child=%r" %
                              (stdout, stderr, child_error.read_text() if child_error.exists() else None))
                try:
                    status = rpc_call(self.socket_path, "daemon/status", {}, timeout=0.25)
                    if status["result"]["ready"]:
                        break
                except RpcFault:
                    time.sleep(0.05)
            else:
                self.fail("daemon did not become ready")
            codex_pid = status["result"]["codex_pid"]
            started = rpc_call(self.socket_path, "session/start", {
                "cwd": self.cwd,
                "name": "sigterm",
                "model": None,
            }, timeout=1.0)
            session_id = started["result"]["session"]["session_id"]
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=5.0)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5.0)
        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(stdout, "")
        payload = json.loads(Path(state_path).read_text(encoding="utf-8"))
        self.assertEqual([record["session_id"] for record in payload["sessions"]], [session_id])
        self.assertFalse(_pid_exists(codex_pid))

class PublicLauncherTests(unittest.TestCase):
    def test_launcher_runs_from_an_unrelated_working_directory(self):
        launcher = ROOT / "bin" / "codex-worker"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(launcher), "--help"], cwd=directory, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Local Unix-socket broker", result.stdout)

    def test_launcher_resolves_a_symlink_before_finding_the_plugin_root(self):
        launcher = ROOT / "bin" / "codex-worker"
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "codex-worker"
            link.symlink_to(launcher)
            result = subprocess.run([str(link), "--help"], cwd=directory, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Local Unix-socket broker", result.stdout)

    def test_subprocess_unsafe_runtime_ancestor_is_one_typed_json(self):
        launcher = ROOT / "bin" / "codex-worker"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir(mode=0o700)
            unsafe_tmp = root / "unsafe-tmp"
            unsafe_tmp.mkdir(mode=0o777)
            os.chmod(unsafe_tmp, 0o777)
            env = dict(os.environ, HOME=str(home), XDG_STATE_HOME=str(root / "state"),
                       TMPDIR=str(unsafe_tmp))
            result = subprocess.run(
                [str(launcher), "start", "--name", "worker-a", "--prompt", "go",
                 "--cwd", directory, "--app-server-listen", _unused_loopback_listener()],
                cwd=directory, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["error"]["data"]["kind"], "daemon_start_failed")
        self.assertNotIn("instance", payload["error"]["data"]["known_ids"])
        self.assertNotIn("Traceback", result.stderr)

    def test_subprocess_unsafe_start_lock_is_one_typed_json(self):
        launcher = ROOT / "bin" / "codex-worker"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir(mode=0o700)
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            env = dict(os.environ, HOME=str(home), XDG_STATE_HOME=str(root / "state"),
                       TMPDIR=str(runtime))
            state_home = (home / "Library" / "Application Support"
                          if sys.platform == "darwin" else root / "state")
            paths = derive_service_paths(sys.platform, state_home, runtime, os.getuid())
            paths.start_lock.parent.mkdir(mode=0o700)
            paths.start_lock.symlink_to(paths.start_lock.parent / "target")
            result = subprocess.run(
                [str(launcher), "run", "--name", "worker-a", "--prompt", "go"],
                cwd=directory, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False,
            )
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["error"]["data"]["kind"], "daemon_start_failed")
        self.assertEqual(payload["error"]["data"]["details"]["reason"],
                         "unsafe_start_lock")
        self.assertNotIn("Traceback", result.stderr)


class ManagedProcessLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.launcher = ROOT / "bin" / "codex-worker"
        self.listener = _unused_loopback_listener()
        fake_codex = ROOT / "tests" / "codex-worker" / "fake_codex.py"
        fake_bin_dir = self.root / "bin"
        fake_bin_dir.mkdir()
        fake_bin = fake_bin_dir / "codex"
        fake_bin.write_text(
            "#!/usr/bin/env python3\n"
            "import os, runpy, sys\n"
            "if len(sys.argv) > 1 and sys.argv[1] == 'app-server':\n"
            "    del sys.argv[1]\n"
            "sys.argv.extend(['--delay', os.environ.get('FAKE_CODEX_DELAY', '0.03')])\n"
            "sys.argv[0] = %r\n"
            "runpy.run_path(%r, run_name='__main__')\n" % (str(fake_codex), str(fake_codex)),
            encoding="utf-8",
        )
        fake_bin.chmod(0o700)
        runtime_dir = self.root / "runtime"
        runtime_dir.mkdir()
        self.env = dict(os.environ)
        self.env.update({
            "HOME": str(self.root / "home"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "CODEX_WORKER_INSTANCE": "task5-process-%s" % os.getpid(),
            "FAKE_CODEX_DELAY": "3.0",
            "PATH": str(fake_bin_dir) + os.pathsep + self.env.get("PATH", ""),
            "PYTHONPATH": _websockets_pythonpath(),
            "TMPDIR": str(runtime_dir),
        })
        (self.root / "home").mkdir()
        self.workdirs = []
        for index in range(7):
            workdir = self.root / ("work-%d" % index)
            workdir.mkdir()
            self.workdirs.append(workdir)
        self.app_server_pid = None
        self.private_codex_socket = derive_service_paths(
            "darwin", Path(self.env["XDG_STATE_HOME"]), runtime_dir,
            os.getuid()).private_codex_socket
        self.addCleanup(self._stop_daemon)
        self._json(self._run("daemon", "start", "--app-server-listen", self.listener))
        status = self._json(self._run("daemon", "status"))["result"]
        self.app_server_pid = status["app_server_pid"]
        self.assertTrue(_pid_exists(self.app_server_pid))
        self.assertTrue(self.private_codex_socket.exists())

    def _run(self, *argv, cwd=None, timeout=10):
        return subprocess.run(
            [str(self.launcher)] + list(argv), cwd=str(cwd or self.root), env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
            check=False,
        )

    def _json(self, completed, expected_exit=0):
        self.assertEqual(completed.returncode, expected_exit,
                         "stdout=%s\nstderr=%s" % (completed.stdout, completed.stderr))
        self.assertEqual(len(completed.stdout.splitlines()), 1, completed.stderr)
        return json.loads(completed.stdout)

    def _status_until(self, name, expected, timeout=5.0):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = self._run("status", "--name", name, timeout=3)
            if last.returncode == 0:
                payload = json.loads(last.stdout)
                latest = payload["result"]["latest_turn"]
                if expected == "in_progress" and payload["result"]["active_turn_id"] is not None:
                    return payload
                if latest is not None and latest["status"] == expected:
                    return payload
            elif last.stdout:
                payload = json.loads(last.stdout)
                if payload.get("error", {}).get("data", {}).get("kind") not in {
                        "daemon_stopped", "worker_not_found"}:
                    self.fail(last.stdout)
        self.fail("worker %s did not reach %s; last=%r" % (name, expected, last))

    def _stop_daemon(self):
        before = self._json(self._run("daemon", "status"))["result"]
        current_app_server_pid = before["app_server_pid"]
        if current_app_server_pid is not None:
            self.app_server_pid = current_app_server_pid
        stopped = self._run("daemon", "stop", "--force", timeout=5)
        self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
        if current_app_server_pid is not None:
            self.assertFalse(
                _pid_exists(current_app_server_pid),
                "owned app-server pid %d survived daemon stop" % current_app_server_pid,
            )
        self.assertFalse(
            self.private_codex_socket.exists(),
            "private app-server listener survived daemon stop",
        )

    def test_force_stop_reaps_exact_app_server_and_private_listener(self):
        app_server_pid = self.app_server_pid
        private_socket = self.private_codex_socket
        self._stop_daemon()
        self.assertFalse(_pid_exists(app_server_pid))
        self.assertFalse(private_socket.exists())

    def test_force_stop_skips_blocked_owned_child_inventory_and_converges(self):
        app_server_pid = self.app_server_pid
        os.kill(app_server_pid, signal.SIGSTOP)
        try:
            completed = self._run("daemon", "stop", "--force", timeout=15)
        finally:
            if _pid_exists(app_server_pid):
                os.kill(app_server_pid, signal.SIGCONT)

        payload = self._json(completed)["result"]
        self.assertEqual((payload["status"], payload["forced"]),
                         ("completed", True))
        self.assertEqual(payload["inventory"], {
            "availability": "unavailable",
            "reason": "upstream_inventory_unavailable",
        })
        self.assertEqual(payload["workers"], {
            "availability": "unavailable",
            "reason": "upstream_inventory_unavailable",
        })
        self.assertFalse(_pid_exists(app_server_pid))
        self.assertFalse(self.private_codex_socket.exists())

    def test_concurrent_clients_share_one_daemon_without_crossing_results(self):
        self.env["FAKE_CODEX_DELAY"] = "1.0"
        processes = []
        for index in range(5):
            name = "worker-%d" % index
            prompt = "prompt-%d" % index
            processes.append((index, subprocess.Popen(
                [str(self.launcher), "start", "--name", name, "--prompt", prompt,
                 "--cwd", str(self.workdirs[index]), "--model", "fake-model-a",
                 "--effort", "medium", "--app-server-listen", self.listener],
                cwd=str(self.workdirs[index]), env=self.env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )))
        results = []
        try:
            for index, process in processes:
                stdout, stderr = process.communicate(timeout=10)
                completed = type("Completed", (), {
                    "returncode": process.returncode, "stdout": stdout, "stderr": stderr,
                })()
                results.append((index, completed))
        finally:
            for _, process in processes:
                if process.poll() is None:
                    process.terminate()
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        process.wait(timeout=2)
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=2)

        results = [(index, self._json(completed)) for index, completed in results]

        statuses = [self._json(self._run("daemon", "status"))["result"] for _ in range(5)]
        status = statuses[0]
        self.assertEqual(status["status"], "ready")
        self.assertIsInstance(status["pid"], int)
        self.assertTrue(_pid_exists(status["pid"]))
        self.assertEqual({item["pid"] for item in statuses}, {status["pid"]})
        self.assertEqual(status["worker_count"]["value"], 5)
        names, threads, sessions, finals = set(), set(), set(), set()
        for index, payload in results:
            result = payload["result"]
            worker = result["worker"]
            names.add(worker["name"])
            threads.add(worker["thread_id"])
            sessions.add(worker["session_id"])
            self.assertEqual(worker["name"], "worker-%d" % index)
            self.assertEqual(worker["cwd"], str(self.workdirs[index].resolve()))
            self.assertEqual(result["turn"]["status"], "completed")
            self.assertEqual([message["text"] for message in result["messages"]],
                             ["done:prompt-%d" % index])
            finals.add(result["messages"][0]["text"])
        self.assertEqual(len(names), 5)
        self.assertEqual(len(threads), 5)
        self.assertEqual(len(sessions), 5)
        self.assertEqual(len(finals), 5)

    def test_disconnect_and_timeout_leave_turn_and_daemon_active(self):
        self.env["FAKE_CODEX_DELAY"] = "10.0"
        waiting = subprocess.Popen(
            [str(self.launcher), "start", "--name", "detached", "--prompt", "wait",
             "--cwd", str(self.workdirs[5]), "--model", "fake-model-a",
             "--app-server-listen", self.listener],
            cwd=str(self.workdirs[5]), env=self.env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            active = self._status_until("detached", "in_progress")
            daemon_pid = self._json(self._run("daemon", "status"))["result"]["pid"]
            waiting.terminate()
            waiting.communicate(timeout=3)
            self._status_until("detached", "in_progress")
            daemon = self._json(self._run("daemon", "status"))["result"]
            self.assertEqual(daemon["status"], "ready")
            self.assertEqual(daemon["pid"], daemon_pid)
            self.assertTrue(_pid_exists(daemon["pid"]))
        finally:
            if waiting.poll() is None:
                waiting.kill()
            waiting.communicate(timeout=3)

        timed = self._run(
            "start", "--name", "timed", "--prompt", "slow", "--model", "fake-model-a",
            "--cwd", str(self.workdirs[6]), "--timeout", "0", cwd=self.workdirs[6], timeout=5,
        )
        timeout_payload = self._json(timed, expected_exit=3)
        self.assertEqual(timeout_payload["error"]["code"], -32025)
        self.assertEqual(timeout_payload["error"]["data"]["kind"], "timeout_active")
        timed_status = self._status_until("timed", "in_progress")
        self.assertIsNotNone(timed_status["result"]["active_turn_id"])

    def test_repeated_stop_then_run_restarts_the_same_thread(self):
        self.env["FAKE_CODEX_DELAY"] = "0.03"
        started = self._json(self._run(
            "start", "--name", "restartable", "--prompt", "first",
            "--cwd", str(self.workdirs[0]), "--model", "fake-model-a",
            "--app-server-listen", self.listener, cwd=self.workdirs[0],
        ))["result"]
        thread_id = started["worker"]["thread_id"]
        first_stop = self._json(self._run("daemon", "stop"))["result"]
        second_stop = self._json(self._run("daemon", "stop"))["result"]
        self.assertEqual(first_stop["status"], "completed")
        self.assertEqual(second_stop["status"], "completed")
        self.env["FAKE_CODEX_RESUME_CWD"] = str(self.workdirs[0].resolve())
        continued = self._json(self._run(
            "run", "--name", "restartable", "--prompt", "second",
            cwd=self.workdirs[0],
        ))["result"]
        self.assertEqual(continued["worker"]["thread_id"], thread_id)
        self.assertEqual(continued["messages"][0]["text"], "done:second")

if __name__ == "__main__":
    unittest.main()
