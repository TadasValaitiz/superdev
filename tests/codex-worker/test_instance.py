import os
import json
import stat
import sys
import tempfile
import threading
import unittest
from unittest import mock
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.instance import (InstanceDeps, InstanceManager, derive_instance_paths,
                                   load_managed_identity, resolve_instance)
import codex_worker.instance as instance_module


@dataclass
class Process:
    pid: int = 1234
    running: bool = True

    def poll(self):
        return None if self.running else 0


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.identity = resolve_instance("session-alpha", {})
        self.paths = derive_instance_paths(self.identity, "darwin", root / "state", root / "tmp", os.getuid())
        self.spawns = []
        self.ready = False

        def spawn(argv, stderr_path):
            self.spawns.append((list(argv), stderr_path))
            self.ready = True
            return Process()

        def rpc_call(socket_path, method, params, timeout):
            if method == "daemon/status":
                if not self.ready:
                    raise OSError("not ready")
                return {"result": {"ready": True, "daemon_pid": 1234, "codex_pid": 5678,
                                   "session_count": 2}}
            if method == "daemon/shutdown":
                self.ready = False
                return {"result": {"accepted": True}}
            raise AssertionError(method)

        self.manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", spawn,
                                                       rpc_call, lambda: 0.0), self.identity)

    def test_concurrent_start_spawns_once_and_writes_verified_metadata(self):
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.manager.ensure_running())) for _ in range(5)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len(self.spawns), 1)
        self.assertEqual({result.status for result in results}, {"ready"})
        self.assertEqual(self.spawns[0][0], ["/launcher", "--socket", str(self.paths.socket_path),
                                               "daemon", "serve", "--state", str(self.paths.registry_path),
                                               "--codex-bin", "codex"])
        self.assertEqual(load_managed_identity(self.paths.registry_path), self.identity)
        self.assertEqual(stat.S_IMODE(os.stat(self.paths.metadata_path).st_mode), 0o600)

    def test_stop_is_idempotent_and_preserves_durable_state(self):
        self.manager.ensure_running()
        stopped = self.manager.stop()
        self.assertEqual(stopped.status_after, "stopped")
        self.assertTrue(self.paths.metadata_path.exists())
        repeated = self.manager.stop()
        self.assertEqual(repeated.status_before, "stopped")

    def test_metadata_rejects_permissive_file_and_parent_hash_mismatch(self):
        self.manager.ensure_running()
        os.chmod(self.paths.metadata_path, 0o644)
        self.assertIsNone(load_managed_identity(self.paths.registry_path))
        os.chmod(self.paths.metadata_path, 0o600)
        payload = json.loads(self.paths.metadata_path.read_text())
        payload["key_hash"] = "0" * 64
        self.paths.metadata_path.write_text(json.dumps(payload))
        os.chmod(self.paths.metadata_path, 0o600)
        self.assertIsNone(load_managed_identity(self.paths.registry_path))

    def test_delayed_readiness_polls_until_daemon_reports_ready(self):
        clock = [0.0]
        calls = [0]
        def rpc(socket_path, method, params, timeout):
            calls[0] += 1
            if method == "daemon/status" and calls[0] >= 3:
                return {"result": {"ready": True, "daemon_pid": 11, "codex_pid": 12, "session_count": 0}}
            raise OSError("not ready")
        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", lambda a, b: Process(), rpc,
                                                lambda: clock[0], lambda _: clock.__setitem__(0, clock[0] + 1)), self.identity)
        self.assertEqual(manager.ensure_running().status, "ready")
        self.assertGreaterEqual(calls[0], 3)

    def test_readiness_timeout_reports_typed_log_path(self):
        clock = [0.0]
        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", lambda a, b: Process(),
                                                lambda *args: (_ for _ in ()).throw(OSError("absent")),
                                                lambda: clock[0], lambda _: clock.__setitem__(0, clock[0] + 3)), self.identity)
        with self.assertRaises(Exception) as caught:
            manager.ensure_running()
        self.assertEqual(caught.exception.kind, "daemon_start_failed")
        self.assertEqual(caught.exception.details["reason"], "readiness_timeout")
        self.assertEqual(caught.exception.details["log_path"], str(self.paths.log_path))

    def test_stop_retains_metadata_when_reported_pid_is_alive(self):
        self.manager.ensure_running()
        clock = [0.0]
        self.manager.deps = InstanceDeps(self.paths, "/launcher", "codex", self.manager.deps.spawn,
            self.manager.deps.rpc_call, lambda: clock[0], lambda _: clock.__setitem__(0, clock[0] + 3))
        with mock.patch.object(instance_module, "_pid_alive", return_value=True):
            with self.assertRaises(Exception) as caught:
                self.manager.stop()
        self.assertEqual(caught.exception.code.value, -32030)
        self.assertEqual(caught.exception.details["durable_state"], "preserved")
        self.assertTrue(self.paths.metadata_path.exists())

    def test_unsafe_existing_lock_is_refused_without_replacement(self):
        self.paths.lock_path.parent.mkdir(parents=True, mode=0o700)
        self.paths.lock_path.symlink_to(self.paths.lock_path.parent / "target")
        with self.assertRaises(RuntimeError): self.manager.ensure_running()
        self.assertTrue(self.paths.lock_path.is_symlink())

    def test_status_surfaces_protocol_failure_as_failed(self):
        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", lambda a, b: Process(),
            lambda *args: (_ for _ in ()).throw(ValueError("malformed")), lambda: 0.0), self.identity)
        self.assertEqual(manager.status().status, "failed")


class InstanceResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_home = Path(self.tempdir.name) / "state"
        self.temp_root = Path(self.tempdir.name) / "tmp"

    def test_instance_precedence_and_short_socket(self):
        env = {"CODEX_WORKER_INSTANCE": "env-id", "CLAUDE_CODE_SESSION_ID": "claude-id"}
        self.assertEqual(resolve_instance("flag-id", env).value, "flag-id")
        self.assertEqual(resolve_instance(None, env).value, "env-id")
        self.assertEqual(resolve_instance(None, {"CLAUDE_CODE_SESSION_ID": "claude-id"}).value,
                         "claude-id")
        paths = derive_instance_paths(resolve_instance(None, {}), "darwin",
                                      self.state_home, self.temp_root, 501)
        self.assertLess(len(os.fsencode(paths.socket_path)), 100)
        self.assertNotIn("default", paths.socket_path.name)


if __name__ == "__main__":
    unittest.main()
