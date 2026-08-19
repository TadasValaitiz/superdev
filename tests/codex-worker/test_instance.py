import os
import json
import socket
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
from codex_worker.rpc import rpc_call as production_rpc_call


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

    def _leave_stale_socket(self):
        self.paths.socket_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        endpoint = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        endpoint.bind(str(self.paths.socket_path))
        endpoint.close()
        os.chmod(self.paths.socket_path, 0o600)

    def _assert_start_fault(self, fault, reason, cause=None, offending_path=None):
        path = self.paths.socket_path if offending_path is None else offending_path
        self.assertEqual(fault.code, instance_module.FacadeFaultCode.DAEMON_START_FAILED)
        self.assertEqual(fault.kind, "daemon_start_failed")
        self.assertEqual(fault.details, {
            "reason": reason,
            "cause": cause,
            "socket_path": str(self.paths.socket_path),
            "offending_path": str(path),
            "log_path": str(self.paths.log_path),
            "durable_state": "preserved",
        })
        self.assertEqual(fault.known_ids, {
            "instance": self.identity.value, "name": None, "session_id": None,
            "thread_id": None, "turn_id": None,
        })
        self.assertEqual(len(fault.next_actions), 3)
        self.assertIn("daemon status", fault.next_actions[0]["command"])
        self.assertIn(str(path), fault.next_actions[1]["command"])
        self.assertIn(str(self.paths.log_path), fault.next_actions[2]["command"])

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

    def test_stop_is_stopped_when_managed_directories_do_not_exist_yet(self):
        stopped = self.manager.stop()
        self.assertEqual(stopped.status_before, "stopped")
        self.assertEqual(stopped.status_after, "stopped")

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
        def rpc(socket_path_string, method, params, timeout):
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
        self._assert_start_fault(caught.exception, "readiness_timeout")

    def test_spawn_failure_has_complete_managed_start_contract(self):
        def spawn(argv, log_path):
            raise OSError("spawn denied")

        manager = InstanceManager(InstanceDeps(
            self.paths, "/launcher", "codex", spawn,
            lambda *args: (_ for _ in ()).throw(OSError("absent")), lambda: 0.0,
        ), self.identity)
        with self.assertRaises(instance_module.FacadeFault) as caught:
            manager.ensure_running()
        self._assert_start_fault(caught.exception, "spawn_failed", {
            "type": "OSError", "message": "spawn denied",
        })

    def test_child_early_exit_has_complete_managed_start_contract(self):
        manager = InstanceManager(InstanceDeps(
            self.paths, "/launcher", "codex", lambda *args: Process(running=False),
            lambda *args: (_ for _ in ()).throw(OSError("absent")), lambda: 0.0,
        ), self.identity)
        with self.assertRaises(instance_module.FacadeFault) as caught:
            manager.ensure_running()
        self._assert_start_fault(caught.exception, "child_exited")

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
        with self.assertRaises(instance_module.FacadeFault) as caught:
            self.manager.ensure_running()
        self.assertEqual(caught.exception.code, instance_module.FacadeFaultCode.DAEMON_START_FAILED)
        self.assertEqual(caught.exception.details["offending_path"], str(self.paths.lock_path))
        self.assertEqual(caught.exception.details["log_path"], str(self.paths.log_path))
        self.assertEqual(caught.exception.known_ids["instance"], self.identity.value)
        self.assertTrue(caught.exception.next_actions)
        self.assertTrue(self.paths.lock_path.is_symlink())

    def test_status_surfaces_protocol_failure_as_failed(self):
        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", lambda a, b: Process(),
            lambda *args: (_ for _ in ()).throw(ValueError("malformed")), lambda: 0.0), self.identity)
        self.assertEqual(manager.status().status, "failed")

    def test_stop_refuses_swapped_current_user_socket_with_typed_failure(self):
        self._leave_stale_socket()
        original = os.lstat(self.paths.socket_path)

        def rpc(socket_path, method, params, timeout):
            if method == "daemon/status":
                return {"result": {"ready": True, "daemon_pid": 11, "codex_pid": 12,
                                   "session_count": 0}}
            if method == "daemon/shutdown":
                os.unlink(self.paths.socket_path)
                replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                replacement.bind(str(self.paths.socket_path))
                replacement.close()
                os.chmod(self.paths.socket_path, 0o600)
                self.assertNotEqual(os.lstat(self.paths.socket_path).st_ino, original.st_ino)
                return {"result": {"accepted": True}}
            raise AssertionError(method)

        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", lambda a, b: Process(),
                                                rpc, lambda: 0.0), self.identity)
        with mock.patch.object(instance_module, "_pid_alive", return_value=False):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                manager.stop()
        self.assertEqual(caught.exception.code, instance_module.FacadeFaultCode.DAEMON_STOP_FAILED)
        self.assertEqual(caught.exception.details["reason"], "socket_changed")
        self.assertTrue(self.paths.socket_path.exists())

    def test_stale_pid_metadata_does_not_block_safe_socket_repair(self):
        self._leave_stale_socket()
        ready = [False]
        spawns = []

        def rpc(socket_path_string, method, params, timeout):
            if ready[0]:
                return {"result": {"ready": True, "daemon_pid": 21, "codex_pid": 22,
                                   "session_count": 0}}
            return {"result": {"ready": False, "daemon_pid": 999991, "codex_pid": 999992,
                               "session_count": 0}}

        def spawn(argv, stderr_path):
            self.assertFalse(self.paths.socket_path.exists())
            spawns.append(list(argv))
            ready[0] = True
            return Process()

        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", spawn, rpc,
                                                lambda: 0.0), self.identity)
        with mock.patch.object(instance_module, "_pid_alive") as pid_alive:
            self.assertEqual(manager.ensure_running().status, "ready")
        pid_alive.assert_not_called()
        self.assertEqual(len(spawns), 1)
        self.assertTrue(self.paths.metadata_path.exists())

    def test_production_unavailable_fault_allows_verified_stale_socket_repair(self):
        self._leave_stale_socket()
        ready = [False]
        spawns = []

        def rpc(socket_path, method, params, timeout):
            if ready[0]:
                return {"result": {"ready": True, "daemon_pid": 31, "codex_pid": 32,
                                   "session_count": 0}}
            return production_rpc_call(socket_path, method, params, timeout)

        def spawn(argv, stderr_path):
            self.assertFalse(self.paths.socket_path.exists())
            spawns.append(list(argv))
            ready[0] = True
            return Process()

        manager = InstanceManager(InstanceDeps(self.paths, "/launcher", "codex", spawn, rpc,
                                                lambda: 0.0), self.identity)
        self.assertEqual(manager.ensure_running().status, "ready")
        self.assertEqual(len(spawns), 1)

    def test_accepting_socket_is_not_repaired_when_rpc_probe_fails(self):
        self.paths.socket_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        endpoint = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(endpoint.close)
        endpoint.bind(str(self.paths.socket_path))
        os.chmod(self.paths.socket_path, 0o600)
        endpoint.listen(1)
        with self.assertRaises(instance_module.FacadeFault) as caught:
            self.manager.ensure_running()
        self._assert_start_fault(caught.exception, "socket_peer_active")
        self.assertTrue(self.paths.socket_path.exists())
        self.assertEqual(self.spawns, [])

    def test_socket_that_starts_accepting_at_unlink_boundary_is_preserved(self):
        self.paths.socket_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        endpoint = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(endpoint.close)
        endpoint.bind(str(self.paths.socket_path))
        os.chmod(self.paths.socket_path, 0o600)
        probes = [0]

        def peer_probe(socket_path):
            probes[0] += 1
            if probes[0] == 1:
                return False
            endpoint.listen(1)
            return True

        with mock.patch.object(instance_module, "_socket_accepts_connections",
                               side_effect=peer_probe):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                self.manager.ensure_running()
        self.assertEqual(caught.exception.details["reason"], "socket_peer_active")
        self.assertEqual(probes[0], 2)
        self.assertTrue(self.paths.socket_path.exists())
        self.assertEqual(self.spawns, [])

    def test_socket_swapped_during_final_peer_probe_is_preserved(self):
        self._leave_stale_socket()
        original = os.lstat(self.paths.socket_path)
        probes = [0]

        def peer_probe(socket_path):
            probes[0] += 1
            if probes[0] == 2:
                os.unlink(self.paths.socket_path)
                replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                replacement.bind(str(self.paths.socket_path))
                replacement.close()
                os.chmod(self.paths.socket_path, 0o600)
                self.assertNotEqual(os.lstat(self.paths.socket_path).st_ino, original.st_ino)
            return False

        with mock.patch.object(instance_module, "_socket_accepts_connections",
                               side_effect=peer_probe):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                self.manager.ensure_running()
        self.assertEqual(caught.exception.details["reason"], "socket_changed")
        self.assertEqual(probes[0], 2)
        self.assertTrue(self.paths.socket_path.exists())
        self.assertEqual(self.spawns, [])

    def test_group_or_world_permissive_socket_is_refused_without_unlink_or_spawn(self):
        for mode in (0o660, 0o606):
            with self.subTest(mode=oct(mode)):
                self._leave_stale_socket()
                os.chmod(self.paths.socket_path, mode)
                with self.assertRaises(instance_module.FacadeFault) as caught:
                    self.manager.ensure_running()
                self.assertEqual(caught.exception.code, instance_module.FacadeFaultCode.DAEMON_START_FAILED)
                self.assertEqual(caught.exception.details["reason"], "unsafe_socket")
                self.assertTrue(self.paths.socket_path.exists())
                self.assertEqual(self.spawns, [])
                os.unlink(self.paths.socket_path)

    def test_foreign_owned_socket_metadata_is_refused_without_root(self):
        self._leave_stale_socket()
        real_lstat = os.lstat

        def injected_lstat(path):
            metadata = real_lstat(path)
            if os.fspath(path) != os.fspath(self.paths.socket_path):
                return metadata
            return type("InjectedStat", (), {
                "st_mode": metadata.st_mode, "st_uid": os.getuid() + 1,
                "st_dev": metadata.st_dev, "st_ino": metadata.st_ino,
            })()

        with mock.patch.object(instance_module.os, "lstat", side_effect=injected_lstat):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                self.manager.ensure_running()
        self.assertEqual(caught.exception.details["reason"], "unsafe_socket")
        self.assertTrue(self.paths.socket_path.exists())
        self.assertEqual(self.spawns, [])

    def test_foreign_owned_controlled_ancestor_is_refused_without_root(self):
        self.paths.socket_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        controlled_ancestor = self.paths.socket_path.parent.parent
        real_lstat = os.lstat

        def injected_lstat(path):
            metadata = real_lstat(path)
            if os.fspath(path) != os.fspath(controlled_ancestor):
                return metadata
            return type("InjectedStat", (), {
                "st_mode": metadata.st_mode, "st_uid": os.getuid() + 1,
                "st_dev": metadata.st_dev, "st_ino": metadata.st_ino,
            })()

        with mock.patch.object(instance_module.os, "lstat", side_effect=injected_lstat):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                self.manager.ensure_running()
        self.assertEqual(caught.exception.code, instance_module.FacadeFaultCode.DAEMON_START_FAILED)
        self.assertEqual(caught.exception.details["offending_path"], str(controlled_ancestor))
        self.assertEqual(self.spawns, [])

    def test_short_hash_collision_has_distinct_runtime_endpoints(self):
        first = resolve_instance("collision-8515", {})
        second = resolve_instance("collision-11163", {})
        self.assertEqual(first.key_hash[:6], second.key_hash[:6])
        first_paths = derive_instance_paths(first, "darwin", Path("/state"), Path("/tmp"), 501)
        second_paths = derive_instance_paths(second, "darwin", Path("/state"), Path("/tmp"), 501)
        self.assertNotEqual(first_paths.socket_path, second_paths.socket_path)
        self.assertNotEqual(first_paths.lock_path, second_paths.lock_path)
        self.assertTrue(first_paths.socket_path.parent.name.endswith(first.key_hash[:20]))
        self.assertTrue(second_paths.socket_path.parent.name.endswith(second.key_hash[:20]))

    def test_short_hash_collision_cannot_accept_the_other_daemon(self):
        first = resolve_instance("collision-8515", {})
        second = resolve_instance("collision-11163", {})
        root = Path(self.tempdir.name)
        first_paths = derive_instance_paths(first, "darwin", root / "state", root / "tmp",
                                            os.getuid())
        second_paths = derive_instance_paths(second, "darwin", root / "state", root / "tmp",
                                             os.getuid())
        probes = []
        spawns = []

        def rpc(socket_path, method, params, timeout):
            probes.append(socket_path)
            if socket_path == str(first_paths.socket_path):
                return {"result": {"ready": True, "daemon_pid": 1, "codex_pid": 2,
                                   "session_count": 0}}
            raise OSError("absent")

        def spawn(argv, log_path):
            spawns.append(list(argv))
            return Process(running=False)

        first_manager = InstanceManager(InstanceDeps(
            first_paths, "/launcher", "codex", spawn, rpc, lambda: 0.0), first)
        second_manager = InstanceManager(InstanceDeps(
            second_paths, "/launcher", "codex", spawn, rpc, lambda: 0.0), second)
        self.assertEqual(first_manager.ensure_running().status, "ready")
        with self.assertRaises(instance_module.FacadeFault) as caught:
            second_manager.ensure_running()
        self.assertEqual(caught.exception.details["reason"], "child_exited")
        self.assertEqual(len(spawns), 1)
        self.assertIn(str(second_paths.socket_path), spawns[0])
        self.assertIn(str(first_paths.socket_path), probes)
        self.assertIn(str(second_paths.socket_path), probes)

    def test_stop_refuses_foreign_controlled_ancestor_and_preserves_socket(self):
        self._leave_stale_socket()
        self.ready = True
        controlled_ancestor = self.paths.socket_path.parent.parent
        real_lstat = os.lstat
        shutdowns = []
        original_rpc = self.manager.deps.rpc_call

        def rpc(socket_path, method, params, timeout):
            if method == "daemon/shutdown":
                shutdowns.append(method)
            return original_rpc(socket_path, method, params, timeout)

        def injected_lstat(path):
            metadata = real_lstat(path)
            if os.fspath(path) != os.fspath(controlled_ancestor):
                return metadata
            return type("InjectedStat", (), {
                "st_mode": metadata.st_mode, "st_uid": os.getuid() + 1,
                "st_dev": metadata.st_dev, "st_ino": metadata.st_ino,
            })()

        self.manager.deps = InstanceDeps(self.paths, "/launcher", "codex",
                                         self.manager.deps.spawn, rpc, lambda: 0.0)
        with mock.patch.object(instance_module.os, "lstat", side_effect=injected_lstat):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                self.manager.stop()
        self.assertEqual(caught.exception.code, instance_module.FacadeFaultCode.DAEMON_STOP_FAILED)
        self.assertEqual(caught.exception.details["reason"], "unsafe_parent")
        self.assertEqual(shutdowns, [])
        self.assertTrue(self.paths.socket_path.exists())

class ControlledParentTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.identity = resolve_instance("parent-tests", {})

    def _manager(self, state_home, temp_root):
        paths = derive_instance_paths(self.identity, "darwin", state_home, temp_root, os.getuid())
        deps = InstanceDeps(paths, "/launcher", "codex", lambda a, b: Process(running=False),
                            lambda *args: (_ for _ in ()).throw(OSError("absent")), lambda: 3.0)
        return InstanceManager(deps, self.identity)

    def test_symlink_controlled_parent_is_refused(self):
        real_temp = self.root / "real-temp"
        real_temp.mkdir(mode=0o700)
        linked_temp = self.root / "linked-temp"
        linked_temp.symlink_to(real_temp, target_is_directory=True)
        manager = self._manager(self.root / "state", linked_temp)
        with self.assertRaises(instance_module.FacadeFault):
            manager.ensure_running()

    def test_intermediate_symlink_in_controlled_parent_is_refused(self):
        real_temp = self.root / "real-intermediate"
        nested_temp = real_temp / "nested"
        nested_temp.mkdir(parents=True, mode=0o700)
        linked_component = self.root / "linked-component"
        linked_component.symlink_to(real_temp, target_is_directory=True)
        manager = self._manager(self.root / "state", linked_component / "nested")
        with self.assertRaises(instance_module.FacadeFault):
            manager.ensure_running()

    def test_group_or_world_writable_non_sticky_parent_is_refused(self):
        for name, mode in (("group-temp", 0o770), ("world-temp", 0o707)):
            with self.subTest(mode=oct(mode)):
                unsafe_temp = self.root / name
                unsafe_temp.mkdir(mode=mode)
                os.chmod(unsafe_temp, mode)
                manager = self._manager(self.root / (name + "-state"), unsafe_temp)
                with self.assertRaises(instance_module.FacadeFault):
                    manager.ensure_running()

    def test_owner_only_and_sticky_temp_parents_are_supported(self):
        for name, mode in (("owner-temp", 0o700), ("sticky-temp", 0o1777)):
            with self.subTest(mode=oct(mode)):
                temp_root = self.root / name
                temp_root.mkdir(mode=mode)
                os.chmod(temp_root, mode)
                manager = self._manager(self.root / (name + "-state"), temp_root)
                with self.assertRaises(instance_module.FacadeFault) as caught:
                    manager.ensure_running()
                self.assertEqual(caught.exception.details["reason"], "child_exited")

    def test_foreign_owned_shared_sticky_temp_parent_is_supported(self):
        sticky_temp = self.root / "foreign-sticky-temp"
        sticky_temp.mkdir(mode=0o1777)
        os.chmod(sticky_temp, 0o1777)
        manager = self._manager(self.root / "sticky-state", sticky_temp)
        real_lstat = os.lstat

        def injected_lstat(path):
            metadata = real_lstat(path)
            if os.fspath(path) != os.fspath(sticky_temp):
                return metadata
            return type("InjectedStat", (), {
                "st_mode": metadata.st_mode, "st_uid": os.getuid() + 1,
                "st_dev": metadata.st_dev, "st_ino": metadata.st_ino,
            })()

        with mock.patch.object(instance_module.os, "lstat", side_effect=injected_lstat):
            with self.assertRaises(instance_module.FacadeFault) as caught:
                manager.ensure_running()
        self.assertEqual(caught.exception.details["reason"], "child_exited")

    def test_foreign_owned_non_shared_sticky_parent_is_refused(self):
        sticky_private = self.root / "foreign-sticky-private"
        sticky_private.mkdir(mode=0o1700)
        os.chmod(sticky_private, 0o1700)
        manager = self._manager(self.root / "sticky-private-state", sticky_private)
        real_lstat = os.lstat

        def injected_lstat(path):
            metadata = real_lstat(path)
            if os.fspath(path) != os.fspath(sticky_private):
                return metadata
            return type("InjectedStat", (), {
                "st_mode": metadata.st_mode, "st_uid": os.getuid() + 1,
                "st_dev": metadata.st_dev, "st_ino": metadata.st_ino,
            })()

        with mock.patch.object(instance_module.os, "lstat", side_effect=injected_lstat):
            with self.assertRaises(instance_module.FacadeFault):
                manager.ensure_running()


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

    def test_load_managed_identity_refuses_writable_ancestor_without_touching_metadata(self):
        identity = resolve_instance("unsafe-load-parent", {})
        paths = derive_instance_paths(identity, "darwin", self.state_home, self.temp_root,
                                      os.getuid())
        paths.durable_dir.mkdir(parents=True, mode=0o700)
        payload = {"source": identity.source.value, "value": identity.value,
                   "key_hash": identity.key_hash}
        paths.metadata_path.write_text(json.dumps(payload) + "\n")
        os.chmod(paths.metadata_path, 0o600)
        controlled_ancestor = paths.durable_dir.parent
        real_lstat = os.lstat

        def injected_lstat(path):
            metadata = real_lstat(path)
            if os.fspath(path) != os.fspath(controlled_ancestor):
                return metadata
            return type("InjectedStat", (), {
                "st_mode": (metadata.st_mode & ~0o777) | 0o770, "st_uid": os.getuid(),
                "st_dev": metadata.st_dev, "st_ino": metadata.st_ino,
            })()

        before = paths.metadata_path.read_bytes()
        with mock.patch.object(instance_module.os, "lstat", side_effect=injected_lstat):
            self.assertIsNone(load_managed_identity(paths.registry_path))
        self.assertEqual(paths.metadata_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
