import os
import inspect
import socket
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.service import (
    GatewayAuthentication,
    GlobalWorkerService,
    GlobalWorkerServiceDeps,
    GlobalWorkerServiceStatus,
    ListenerExposure,
    _ensure_owner_directory,
)
from codex_worker.path_security import unsafe_ancestor
from codex_worker.service_domain import ServiceConfig, derive_service_paths
from codex_worker.websocket_gateway import ServiceMaintenanceGate


class FakeProcess:
    next_pid = 9300

    def __init__(self, socket_path, mode=0o600):
        type(self).next_pid += 1
        self.pid = type(self).next_pid
        self.returncode = None
        self.socket_path = socket_path
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(str(socket_path))
        os.chmod(socket_path, mode)
        self.socket.listen(1)

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0
        self.socket.close()
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.terminate()


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FailingCloseConnection(FakeConnection):
    def close(self):
        self.closed = True
        raise OSError("connection close failed")


class FakeGateway:
    def __init__(self, listener, endpoint, gate, fail=False):
        self.listener = listener
        self.endpoint = endpoint
        self.gate = gate
        self.fail = fail
        self.ready = False
        self.closed = False

    def start(self):
        if self.fail:
            raise OSError("address in use")
        self.ready = True

    def close(self):
        self.ready = False
        self.closed = True


class FailingCloseGateway(FakeGateway):
    def close(self):
        self.ready = False
        self.closed = True
        raise OSError("gateway close failed")


class ServiceHarness:
    def __init__(self, socket_mode=0o600, gateway_fail=False):
        self.socket_mode = socket_mode
        self.gateway_fail = gateway_fail
        self.argv = []
        self.processes = []
        self.connections = []
        self.gateways = []

    def spawn(self, argv, cwd, env):
        self.argv.append((tuple(argv), cwd, env))
        socket_path = Path(argv[-1][len("unix://"):])
        process = FakeProcess(socket_path, self.socket_mode)
        self.processes.append(process)
        return process

    def connect(self, endpoint, on_notification, approval_handler):
        connection = FakeConnection()
        self.connections.append((endpoint, on_notification, approval_handler, connection))
        return connection

    def gateway(self, listener, endpoint, gate):
        gateway = FakeGateway(listener, endpoint, gate, self.gateway_fail)
        self.gateways.append(gateway)
        return gateway

    def deps(self):
        return GlobalWorkerServiceDeps(self.spawn, self.connect, self.gateway)


class FailingCloseHarness(ServiceHarness):
    def connect(self, endpoint, on_notification, approval_handler):
        connection = FailingCloseConnection()
        self.connections.append((endpoint, on_notification, approval_handler, connection))
        return connection

    def gateway(self, listener, endpoint, gate):
        gateway = FailingCloseGateway(listener, endpoint, gate)
        self.gateways.append(gateway)
        return gateway


class GlobalWorkerServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.paths = derive_service_paths("darwin", root / "state", root / "tmp", os.getuid())
        self.config = ServiceConfig("ws://127.0.0.1:4500", "8.1.0", "00000000-0000-0000-0000-000000000001")

    def make_service(self, harness):
        service = GlobalWorkerService(
            self.paths,
            self.config,
            lambda _message: None,
            None,
            harness.deps(),
            codex_argv=("/opt/bin/codex",),
        )
        def cleanup():
            if service.status().ready:
                lifecycle = service._lifecycle_for_composition()
                with lifecycle.gate.drain() as lease:
                    lifecycle.terminate_owned(lease)
        self.addCleanup(cleanup)
        return service

    def test_start_uses_private_codex_socket_and_reports_ready_only_after_gateway(self):
        harness = ServiceHarness()
        service = self.make_service(harness)
        status = service.start()
        self.assertTrue(status.ready)
        self.assertEqual(status.listener, "ws://127.0.0.1:4500")
        self.assertEqual(status.worker_version, "8.1.0")
        self.assertEqual(status.codex_pid, harness.processes[0].pid)
        self.assertEqual(status.exposure, ListenerExposure.LOOPBACK)
        self.assertEqual(status.authentication, GatewayAuthentication.NONE)
        expected_endpoint = "unix://%s" % self.paths.private_codex_socket
        self.assertEqual(harness.argv[0][0], (
            "/opt/bin/codex", "app-server", "--listen", expected_endpoint,
        ))
        self.assertEqual(harness.connections[0][0], expected_endpoint)
        self.assertEqual(harness.gateways[0].endpoint, expected_endpoint)
        self.assertEqual(stat.S_IMODE(self.paths.private_codex_socket.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.paths.private_codex_socket.parent.stat().st_mode), 0o700)

    def test_non_loopback_status_is_explicitly_unauthenticated_and_strict(self):
        config = ServiceConfig("ws://192.0.2.10:4500", "8.1.0",
                               "00000000-0000-0000-0000-000000000001")
        harness = ServiceHarness()
        service = GlobalWorkerService(
            self.paths, config, lambda _message: None, None, harness.deps(),
            codex_argv=("/opt/bin/codex",),
        )
        self.addCleanup(lambda: self._terminate_if_ready(service))
        status = service.start()
        self.assertEqual(status.exposure, ListenerExposure.NON_LOOPBACK)
        self.assertEqual(status.authentication, GatewayAuthentication.NONE)
        self.assertEqual(GlobalWorkerServiceStatus.from_dict(status.to_dict()), status)
        payload = status.to_dict()
        payload["secret"] = "must-refuse"
        with self.assertRaises(ValueError):
            GlobalWorkerServiceStatus.from_dict(payload)

    @staticmethod
    def _terminate_if_ready(service):
        if service.status().ready:
            lifecycle = service._lifecycle_for_composition()
            with lifecycle.gate.drain() as lease:
                lifecycle.terminate_owned(lease)

    def test_public_collision_refuses_before_spawning_and_preserves_peer(self):
        harness = ServiceHarness(gateway_fail=True)
        service = self.make_service(harness)
        with self.assertRaises(OSError):
            service.start()
        self.assertEqual(harness.processes, [])
        self.assertFalse(service.status().ready)

    def test_existing_private_socket_is_refused_without_unlink(self):
        self.paths.private_codex_socket.parent.mkdir(parents=True, mode=0o700)
        sentinel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sentinel.bind(str(self.paths.private_codex_socket))
        self.addCleanup(sentinel.close)
        before = os.lstat(self.paths.private_codex_socket)
        harness = ServiceHarness()
        with self.assertRaises(FileExistsError):
            self.make_service(harness).start()
        after = os.lstat(self.paths.private_codex_socket)
        self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
        self.assertEqual(harness.processes, [])

    def test_symlink_runtime_root_is_refused_without_chmod_of_target(self):
        target = Path(self.temporary.name) / "runtime-target"
        target.mkdir(mode=0o755)
        self.paths.private_codex_socket.parent.parent.mkdir(parents=True, exist_ok=True)
        self.paths.private_codex_socket.parent.symlink_to(target, target_is_directory=True)
        before = stat.S_IMODE(target.stat().st_mode)
        harness = ServiceHarness()
        with self.assertRaises(PermissionError):
            self.make_service(harness).start()
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), before)
        self.assertEqual(harness.processes, [])

    def test_intermediate_symlink_is_refused_before_creating_external_children(self):
        external = Path(self.temporary.name) / "external-target"
        external.mkdir(mode=0o755)
        linked_state = Path(self.temporary.name) / "linked-state"
        linked_state.symlink_to(external, target_is_directory=True)
        paths = derive_service_paths(
            "darwin", linked_state, Path(self.temporary.name) / "safe-runtime", os.getuid())
        harness = ServiceHarness()
        service = GlobalWorkerService(
            paths, self.config, lambda _message: None, None, harness.deps(),
            codex_argv=("/opt/bin/codex",),
        )
        self.addCleanup(lambda: self._terminate_if_ready(service))
        with self.assertRaises(PermissionError):
            service.start()
        self.assertFalse((external / "superdev").exists())
        self.assertEqual(harness.processes, [])

    def test_non_sticky_world_writable_ancestor_is_refused_before_creation(self):
        unsafe_state = Path(self.temporary.name) / "unsafe-state"
        unsafe_state.mkdir(mode=0o700)
        os.chmod(unsafe_state, 0o777)
        paths = derive_service_paths(
            "darwin", unsafe_state, Path(self.temporary.name) / "safe-runtime", os.getuid())
        harness = ServiceHarness()
        service = GlobalWorkerService(
            paths, self.config, lambda _message: None, None, harness.deps(),
            codex_argv=("/opt/bin/codex",),
        )
        self.addCleanup(lambda: self._terminate_if_ready(service))
        with self.assertRaises(PermissionError):
            service.start()
        self.assertFalse((unsafe_state / "superdev").exists())
        self.assertEqual(harness.processes, [])

    def test_owner_only_and_root_sticky_ancestor_controls_remain_supported(self):
        from codex_worker import instance

        self.assertIs(instance._unsafe_ancestor, unsafe_ancestor)
        owner_root = Path(self.temporary.name) / "owner-root"
        owner_root.mkdir(mode=0o700)
        owner_target = owner_root / "service"
        _ensure_owner_directory(owner_target)
        self.assertEqual(stat.S_IMODE(owner_target.stat().st_mode), 0o700)

        self.assertIsNone(unsafe_ancestor(Path("/tmp")))
        with tempfile.TemporaryDirectory(dir="/tmp", prefix="cw2-safe-") as sticky_child:
            sticky_target = Path(sticky_child) / "service"
            _ensure_owner_directory(sticky_target)
            self.assertEqual(stat.S_IMODE(sticky_target.stat().st_mode), 0o700)

    def test_private_socket_must_be_owner_only(self):
        harness = ServiceHarness(socket_mode=0o660)
        service = self.make_service(harness)
        with self.assertRaises(PermissionError):
            service.start()
        self.assertTrue(harness.gateways[0].closed)
        self.assertIsNotNone(harness.processes[0].poll())
        self.assertFalse(service.status().ready)

    def test_termination_requires_current_lease_from_exact_gate(self):
        harness = ServiceHarness()
        service = self.make_service(harness)
        service.start()
        lifecycle = service._lifecycle_for_composition()
        with self.assertRaises(PermissionError):
            lifecycle.terminate_owned(object())
        foreign = ServiceMaintenanceGate()
        with foreign.drain() as lease:
            with self.assertRaises(PermissionError):
                lifecycle.terminate_owned(lease)
        with lifecycle.gate.drain() as lease:
            lifecycle.terminate_owned(lease)
        self.assertFalse(service.status().ready)
        self.assertTrue(harness.gateways[0].closed)
        self.assertTrue(harness.connections[0][3].closed)
        self.assertIsNotNone(harness.processes[0].poll())
        with self.assertRaises(PermissionError):
            lifecycle.terminate_owned(lease)

    def test_service_has_no_public_stop_or_restart_surface(self):
        self.assertFalse(hasattr(GlobalWorkerService, "stop"))
        self.assertFalse(hasattr(GlobalWorkerService, "restart"))

    def test_ordinary_service_surface_cannot_issue_drain_or_termination_authority(self):
        service = self.make_service(ServiceHarness())
        self.assertFalse(hasattr(service, "maintenance_gate"))
        self.assertFalse(hasattr(service, "terminate_owned"))
        lifecycle = service._lifecycle_for_composition()
        self.assertIsInstance(lifecycle.gate, ServiceMaintenanceGate)
        with self.assertRaises(TypeError):
            type(lifecycle)(object(), service, lifecycle.gate)
        with self.assertRaises(AttributeError):
            lifecycle.gate = ServiceMaintenanceGate()

    def test_termination_attempts_every_owned_resource_when_close_raises(self):
        harness = FailingCloseHarness()
        service = self.make_service(harness)
        service.start()
        lifecycle = service._lifecycle_for_composition()
        with lifecycle.gate.drain() as lease:
            with self.assertRaises(OSError):
                lifecycle.terminate_owned(lease)
        self.assertFalse(service.status().ready)
        self.assertTrue(harness.gateways[0].closed)
        self.assertTrue(harness.connections[0][3].closed)
        self.assertIsNotNone(harness.processes[0].poll())

    def test_termination_refuses_to_unlink_substituted_private_socket_inode(self):
        harness = ServiceHarness()
        service = self.make_service(harness)
        service.start()
        process = harness.processes[0]
        process.returncode = 0
        process.socket.close()
        service.paths.private_codex_socket.unlink()
        replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        replacement.bind(str(service.paths.private_codex_socket))
        os.chmod(service.paths.private_codex_socket, 0o600)
        self.addCleanup(replacement.close)
        lifecycle = service._lifecycle_for_composition()
        with lifecycle.gate.drain() as lease:
            with self.assertRaisesRegex(PermissionError, "changed after readiness"):
                lifecycle.terminate_owned(lease)
        self.assertTrue(service.paths.private_codex_socket.exists())

    def test_load_bearing_service_seams_and_frozen_status_are_exact(self):
        self.assertEqual(list(inspect.signature(GlobalWorkerService.start).parameters), ["self"])
        self.assertEqual(list(inspect.signature(GlobalWorkerService.status).parameters), ["self"])
        self.assertEqual(list(inspect.signature(
            GlobalWorkerService._lifecycle_for_composition).parameters), ["self"])
        lifecycle = self.make_service(ServiceHarness())._lifecycle_for_composition()
        self.assertEqual(list(inspect.signature(
            lifecycle.terminate_owned).parameters), ["lease"])
        status = self.make_service(ServiceHarness()).status()
        with self.assertRaises(Exception):
            status.ready = True


if __name__ == "__main__":
    unittest.main()
