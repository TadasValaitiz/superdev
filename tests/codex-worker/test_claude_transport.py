import hashlib
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
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.callback_store import CallbackBinding, CallbackEvent
from codex_worker.commands import (AccessMode, CallbackAttemptState, CallbackCapture,
                                   CallbackState, FacadeFault, Tier, WorkerView)
from codex_worker.claude_transport import (CALLBACK_UUID_NAMESPACE,
                                           MAX_USER_LINE_UTF16_UNITS,
                                           ClaudeTransport, ClaudeTransportDeps,
                                           _process_start, _same_process_start,
                                           capture_from_env)


class UnixInbox:
    def __init__(self, path):
        self.path = str(path)
        self.frames = []
        self.half_closed = threading.Event()
        self._stop = threading.Event()
        self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._listener.bind(self.path)
        self._listener.listen()
        # MEASURED Claude 2.1.237: inbox sockets are exactly owner-only 0600.
        os.chmod(self.path, 0o600)
        self._listener.settimeout(0.05)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                connection, _ = self._listener.accept()
            except socket.timeout:
                continue
            with connection:
                chunks = []
                while True:
                    data = connection.recv(65536)
                    if not data:
                        self.half_closed.set()
                        break
                    chunks.append(data)
                if chunks:
                    self.frames.append(b"".join(chunks))

    def close(self):
        self._stop.set()
        self._thread.join(1)
        self._listener.close()

    def wait_for_frames(self, count=1):
        deadline = time.monotonic() + 1
        while len(self.frames) < count and time.monotonic() < deadline:
            time.sleep(0.005)
        return len(self.frames) >= count


class ClaudeTransportTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        os.chmod(self.root, 0o700)
        self.config = self.root / "claude"
        self.sessions = self.config / "sessions"
        self.sockets = self.root / "cc-socks"
        # MEASURED Claude 2.1.237: session/socket registry directories are 0700.
        self.sessions.mkdir(parents=True, mode=0o700)
        self.sockets.mkdir(mode=0o700)
        os.chmod(self.config, 0o700)
        self.inboxes = []
        self.pid = os.getpid()
        self.sock = self.sockets / (str(self.pid) + ".sock")
        self.inbox = self._inbox(self.sock)
        self.session_id = "claude-session-1"
        self.proc_start = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(self.pid)], text=True).strip()
        self.child_token = "1" * 32
        self._registry("origin", self.session_id, self.pid, self.proc_start, self.sock)

    def tearDown(self):
        for inbox in self.inboxes:
            inbox.close()
        self.tempdir.cleanup()

    def _inbox(self, path):
        inbox = UnixInbox(path)
        self.inboxes.append(inbox)
        return inbox

    def _registry(self, name, session_id, pid, proc_start, sock, suffix=None):
        path = self.sessions / ((suffix or str(pid)) + ".json")
        # MEASURED Claude 2.1.237: these camel-case fields form the live registry identity.
        path.write_text(json.dumps({"pid": pid, "sessionId": session_id,
                                    "messagingSocketPath": str(sock), "name": name,
                                    "procStart": proc_start}), encoding="utf-8")
        os.chmod(path, 0o644)  # MEASURED Claude 2.1.237 registry-file mode.
        return path

    def _peer_key(self, sock, token="2" * 32, proc_start=None, prefix=None):
        # MEASURED Claude 2.1.237: Node path.resolve maps to abspath, not realpath.
        digest = hashlib.sha256(os.path.abspath(str(sock)).encode()).hexdigest()
        path = self.sessions / ("%s.%s.key" % (prefix or self.pid, digest))
        path.write_text(json.dumps({"peerToken": token,
                                    "procStart": proc_start or self.proc_start}), encoding="utf-8")
        os.chmod(path, 0o600)  # MEASURED Claude 2.1.237 peer-key mode.
        return path

    def _env(self):
        return {"CLAUDE_CONFIG_DIR": str(self.config),
                "CLAUDE_CODE_MESSAGING_SOCKET": str(self.sock),
                "CLAUDE_CODE_MESSAGING_TOKEN": self.child_token,
                "CLAUDE_CODE_SESSION_ID": self.session_id,
                "CLAUDE_PID": str(self.pid)}

    def _capture(self):
        return CallbackCapture(str(self.sock), self.child_token, self.session_id,
                               self.pid, self.proc_start, str(self.config))

    def _binding(self, state=CallbackState.ENABLED, target=None, config=None):
        if state == CallbackState.ENABLED:
            return CallbackBinding(str(uuid.uuid4()), state, str(target or self.sock),
                                   self.child_token, self.session_id, self.pid,
                                   self.proc_start, str(config or self.config),
                                   "2026-08-20T00:00:00Z")
        return CallbackBinding(str(uuid.uuid4()), state, None, None, None, None, None,
                               str(config) if config is not None else None,
                               "2026-08-20T00:00:00Z")

    def _event(self, message="hello", event_id="event-fixture-1"):
        worker = WorkerView("default", "builder", str(uuid.uuid4()), "thread-1",
                            str(self.root), Tier.MEDIUM, "gpt-5.6-terra", "medium",
                            AccessMode.FULL)
        return CallbackEvent("codex-worker.claude-callback/v1", "worker_message",
                             event_id, "2026-08-20T00:00:00Z", "next", worker,
                             {"message": message})

    @staticmethod
    def _fault_kind(call):
        with unittest.TestCase().assertRaises(FacadeFault) as caught:
            call()
        return caught.exception.kind

    def test_capture_full_root_only_and_null(self):
        capture = capture_from_env(self._env())
        self.assertEqual(capture, self._capture())
        self.assertEqual(capture_from_env({"CLAUDE_CONFIG_DIR": str(self.config)}),
                         CallbackCapture(None, None, None, None, None, str(self.config)))
        self.assertEqual(self._fault_kind(lambda: capture_from_env(
            {"CLAUDE_CONFIG_DIR": str(self.root / "missing")})),
            "callback_target_unsafe")

    def test_capture_without_config_override_returns_null_when_default_root_is_absent(self):
        absent_default = self.root / "absent-default-claude"
        with mock.patch("codex_worker.claude_transport.os.path.expanduser",
                        return_value=str(absent_default)):
            self.assertIsNone(capture_from_env({}))

    def test_capture_rejects_ambiguous_malformed_and_mismatched_registry(self):
        self._registry("duplicate", self.session_id, self.pid, self.proc_start,
                       self.sock, suffix="duplicate")
        self.assertEqual(self._fault_kind(lambda: capture_from_env(self._env())),
                         "callback_target_ambiguous")
        (self.sessions / "duplicate.json").unlink()
        malformed = self.sessions / "broken.json"
        malformed.write_text("{", encoding="utf-8")
        os.chmod(malformed, 0o644)
        self.assertEqual(self._fault_kind(lambda: capture_from_env(self._env())),
                         "callback_target_unsafe")
        malformed.unlink()
        wrong = self._env(); wrong["CLAUDE_CODE_SESSION_ID"] = "forged"
        self.assertEqual(capture_from_env(wrong),
                         CallbackCapture(None, None, None, None, None, str(self.config)))

    def test_capture_and_daemon_reject_pid_mismatched_socket_basename(self):
        """MEASURED convention: default registry sockets are <claude_pid>.sock."""
        wrong_socket = self.sockets / (str(self.pid + 1) + ".sock")
        self.inbox.close(); self.inboxes.remove(self.inbox); self.sock.unlink()
        self.inbox = self._inbox(wrong_socket)
        self.sock = wrong_socket
        self._registry("origin", self.session_id, self.pid, self.proc_start, wrong_socket)
        self.assertEqual(self._fault_kind(lambda: capture_from_env(self._env())),
                         "callback_target_unsafe")
        forged = CallbackCapture(str(wrong_socket), self.child_token, self.session_id,
                                 self.pid, self.proc_start, str(self.config))
        self.assertEqual(self._fault_kind(lambda: ClaudeTransport().validate_capture(forged)),
                         "callback_target_stale")

    def test_capture_ignores_claude_idle_records_without_a_messaging_socket(self):
        idle = self.sessions / "idle-without-socket.json"
        idle.write_text(json.dumps({
            "pid": self.pid, "sessionId": "idle-session", "procStart": self.proc_start,
            "name": "idle-room", "kind": "interactive", "status": "idle",
        }), encoding="utf-8")
        os.chmod(idle, 0o644)
        self.assertEqual(capture_from_env(self._env()), self._capture())

    def test_daemon_revalidates_forged_full_and_root_only_capture(self):
        transport = ClaudeTransport()
        self.assertEqual(transport.validate_capture(self._capture()), self._capture())
        forged = CallbackCapture(str(self.sock), self.child_token, "forged-session",
                                 self.pid, self.proc_start, str(self.config))
        self.assertEqual(self._fault_kind(lambda: transport.validate_capture(forged)),
                         "callback_target_stale")
        root_only = CallbackCapture(None, None, None, None, None, str(self.config))
        self.assertEqual(transport.validate_capture(root_only), root_only)
        alias = self.root / "alias"
        alias.symlink_to(self.config, target_is_directory=True)
        forged_root = CallbackCapture(None, None, None, None, None, str(alias))
        self.assertEqual(self._fault_kind(lambda: transport.validate_capture(forged_root)),
                         "callback_target_unsafe")

    def test_daemon_rejects_registry_that_matches_capture_but_not_live_process_start(self):
        deps = ClaudeTransportDeps(process_start=lambda _pid: "reused-process-start")
        self.assertEqual(self._fault_kind(
            lambda: ClaudeTransport(deps).validate_capture(self._capture())),
            "callback_target_stale")

    def test_capture_refuses_symlink_permissive_foreign_and_unsafe_ancestor(self):
        registry = self.sessions / (str(self.pid) + ".json")
        cases = []
        alias = self.root / "sessions-alias"
        self.sessions.rename(alias)
        self.sessions.symlink_to(alias, target_is_directory=True)
        cases.append(lambda: capture_from_env(self._env()))
        for call in cases:
            self.assertEqual(self._fault_kind(call), "callback_target_unsafe")
        self.sessions.unlink(); alias.rename(self.sessions)
        os.chmod(registry, 0o666)
        self.assertEqual(self._fault_kind(lambda: capture_from_env(self._env())),
                         "callback_target_unsafe")
        os.chmod(registry, 0o644)
        original_lstat = os.lstat
        def foreign(path):
            result = original_lstat(path)
            if Path(path) == registry:
                values = list(result); values[4] = os.getuid() + 1
                return os.stat_result(values)
            return result
        with mock.patch("codex_worker.claude_transport.os.lstat", side_effect=foreign):
            self.assertEqual(self._fault_kind(lambda: capture_from_env(self._env())),
                             "callback_target_unsafe")
        os.chmod(self.config, 0o777)
        self.assertEqual(self._fault_kind(lambda: capture_from_env(self._env())),
                         "callback_target_unsafe")

    def test_default_send_revalidates_identity_and_socket_reuse(self):
        transport = ClaudeTransport()
        binding = self._binding()
        registry = self.sessions / (str(self.pid) + ".json")
        data = json.loads(registry.read_text()); data["procStart"] = "reused-start"
        registry.write_text(json.dumps(data)); os.chmod(registry, 0o644)
        self.assertEqual(self._fault_kind(lambda: transport.send(binding, self._event(), None)),
                         "callback_target_stale")
        data["procStart"] = self.proc_start; registry.write_text(json.dumps(data)); os.chmod(registry, 0o644)
        self.inbox.close(); self.inboxes.remove(self.inbox); self.sock.unlink()
        replacement = self._inbox(self.sock)
        os.chmod(self.sock, 0o666)
        self.assertEqual(self._fault_kind(lambda: transport.send(binding, self._event(), None)),
                         "callback_target_unsafe")
        replacement.close(); self.inboxes.remove(replacement)

    def test_process_start_compares_claude_utc_registry_to_local_ps_time(self):
        registry_utc = "Tue Aug 11 13:42:33 2026"
        local_ps = "Tue Aug 11 16:42:33 2026"
        from codex_worker.claude_transport import _same_process_start
        shift = lambda value: value + __import__("datetime").timedelta(hours=3)
        self.assertTrue(_same_process_start(registry_utc, local_ps, shift))
        self.assertFalse(_same_process_start(
            registry_utc, "Tue Aug 11 17:42:33 2026", shift))

    def test_process_start_is_stable_under_non_english_ambient_locale(self):
        stable = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(self.pid)],
            text=True, env=dict(os.environ, LC_ALL="C")).strip()
        with mock.patch.dict(os.environ, {"LC_ALL": "lt_LT.UTF-8"}):
            observed = _process_start(self.pid)
        self.assertEqual(observed, stable)
        self.assertTrue(_same_process_start(stable, observed))

    def test_override_requires_one_live_name_and_safe_peer_key(self):
        transport = ClaudeTransport()
        target = self.sock
        target_inbox = self.inbox
        self._registry("target", "target-session", self.pid, self.proc_start, target,
                       suffix="target")
        self.assertEqual(self._fault_kind(lambda: transport.send(self._binding(), self._event(), "missing")),
                         "callback_target_not_found")
        self.assertEqual(self._fault_kind(lambda: transport.send(self._binding(), self._event(), "target")),
                         "callback_target_unsafe")
        key = self._peer_key(target, proc_start=self.proc_start, prefix=self.pid)
        attempt = transport.send(self._binding(), self._event(), "target")
        self.assertEqual(attempt.state, CallbackAttemptState.WRITTEN)
        self.assertTrue(target_inbox.half_closed.wait(1))
        self._registry("target", "other-session", self.pid, self.proc_start, target,
                       suffix="target-two")
        self.assertEqual(self._fault_kind(lambda: transport.send(self._binding(), self._event(), "target")),
                         "callback_target_ambiguous")
        (self.sessions / "target-two.json").unlink()
        os.chmod(key, 0o644)
        self.assertEqual(self._fault_kind(lambda: transport.send(self._binding(), self._event(), "target")),
                         "callback_target_unsafe")

    def test_disabled_and_unavailable_rules(self):
        transport = ClaudeTransport()
        self.assertEqual(self._fault_kind(lambda: transport.send(
            self._binding(CallbackState.DISABLED), self._event(), "origin")),
            "callback_unavailable")
        self.assertEqual(self._fault_kind(lambda: transport.send(
            self._binding(CallbackState.UNAVAILABLE, config=self.config), self._event(), None)),
            "callback_unavailable")
        self._peer_key(self.sock)
        attempt = transport.send(self._binding(CallbackState.UNAVAILABLE, config=self.config),
                                 self._event(), "origin")
        self.assertEqual(attempt.state, CallbackAttemptState.WRITTEN)

    def test_auth_then_deterministic_user_line_and_half_close(self):
        event = self._event()
        binding = self._binding()
        attempt = ClaudeTransport().send(binding, event, None)
        self.assertEqual(attempt.state, CallbackAttemptState.WRITTEN)
        self.assertTrue(self.inbox.wait_for_frames())
        auth_raw, user_raw, empty = self.inbox.frames[-1].split(b"\n")
        self.assertEqual(empty, b"")
        # MEASURED Claude 2.1.237: auth is the first NDJSON line, then one user line.
        self.assertEqual(json.loads(auth_raw), {"type": "auth", "token": self.child_token})
        user = json.loads(user_raw)
        self.assertEqual(user["msg_id"], event.event_id)
        # MEASURED Claude 2.1.237 envelope plus D27/D28 deterministic identity policy.
        self.assertEqual(str(CALLBACK_UUID_NAMESPACE), "5b290fd0-2df0-5c73-980f-04f284476f55")
        self.assertEqual(user["uuid"], str(uuid.uuid5(CALLBACK_UUID_NAMESPACE, event.event_id)))
        self.assertEqual(user["from"], "uds:" + binding.target_socket)
        self.assertEqual(user["from_mode"], "bypass")
        self.assertNotIn("session_id", user)
        self.assertEqual(user_raw.decode(), ClaudeTransport().encode_user_line(binding, event))
        self.assertEqual(str(uuid.uuid5(CALLBACK_UUID_NAMESPACE, "event-fixture-1")),
                         "740cb30c-652d-5f4f-bc30-36c14a48d007")

    def test_root_only_override_omits_from_and_never_uses_destination(self):
        self._peer_key(self.sock)
        binding = self._binding(CallbackState.UNAVAILABLE, config=self.config)
        ClaudeTransport().send(binding, self._event(), "origin")
        self.assertTrue(self.inbox.wait_for_frames())
        user = json.loads(self.inbox.frames[-1].splitlines()[1])
        self.assertNotIn("from", user)
        self.assertEqual(user["from_mode"], "bypass")

    def test_exact_utf16_limit_for_ascii_bmp_and_non_bmp(self):
        transport = ClaudeTransport()
        binding = self._binding()
        # MEASURED Claude 2.1.237 JavaScript receiver buffer cap, excluding newline.
        self.assertEqual(MAX_USER_LINE_UTF16_UNITS, 1_048_576)
        for character, units in (("a", 1), ("é", 1), ("😀", 2)):
            with self.subTest(character=character):
                empty = transport.encode_user_line(binding, self._event("", "boundary-" + str(units)))
                base = len(empty.encode("utf-16-le")) // 2
                fitting_count = (MAX_USER_LINE_UTF16_UNITS - base) // units
                fitting = self._event(character * fitting_count, "boundary-" + str(units))
                line = transport.encode_user_line(binding, fitting)
                self.assertLessEqual(len(line.encode("utf-16-le")) // 2,
                                     MAX_USER_LINE_UTF16_UNITS)
                overflowing = self._event(character * (fitting_count + 1),
                                          "boundary-" + str(units))
                self.assertEqual(self._fault_kind(lambda: transport.encode_user_line(binding, overflowing)),
                                 "callback_payload_too_large")


if __name__ == "__main__":
    unittest.main()
