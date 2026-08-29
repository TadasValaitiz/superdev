import ast
import dataclasses
import inspect
import ipaddress
import os
import socket
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "subagent-driven-development" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from codex_worker.service_domain import (  # noqa: E402
    AttachView,
    LegacyCandidate,
    LegacyConflict,
    MigrationOutcome,
    MigrationSourceView,
    MigrationState,
    MigrationStatusView,
    ServiceConfig,
    ServicePaths,
    derive_service_paths,
    validate_public_listener,
)


SERVICE_DOMAIN_MODELS = {
    "AttachView", "LegacyCandidate", "LegacyConflict", "MigrationSourceView",
    "MigrationStatusView", "MigrationResolveView", "ServiceConfig", "ServicePaths",
}
SERVICE_DOMAIN_FUNCTIONS = {"derive_service_paths", "validate_public_listener"}


def _assert_import_arrows(path, forbidden):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.rsplit(".", 1)[-1])
            imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
    violations = forbidden & imported
    if violations:
        raise AssertionError("forbidden imports: %s" % sorted(violations))


def _assert_service_domain_inventory(module):
    actual_models = {
        name for name, value in vars(module).items()
        if inspect.isclass(value) and dataclasses.is_dataclass(value)
        and value.__module__ == module.__name__
    }
    if actual_models != SERVICE_DOMAIN_MODELS:
        raise AssertionError("service models differ: %s" % sorted(
            actual_models ^ SERVICE_DOMAIN_MODELS))
    actual_functions = {
        name for name, value in vars(module).items()
        if inspect.isfunction(value) and value.__module__ == module.__name__
        and not name.startswith("_")
    }
    if actual_functions != SERVICE_DOMAIN_FUNCTIONS:
        raise AssertionError("service functions differ: %s" % sorted(
            actual_functions ^ SERVICE_DOMAIN_FUNCTIONS))
    _assert_typed_methods(module, SERVICE_DOMAIN_FUNCTIONS)


def _assert_typed_methods(owner, names):
    for name in names:
        signature = inspect.signature(getattr(owner, name))
        if signature.return_annotation is inspect.Signature.empty:
            raise AssertionError("%s return is unannotated" % name)
        unannotated = [
            parameter.name for parameter in signature.parameters.values()
            if parameter.name != "self"
            and parameter.annotation is inspect.Signature.empty
        ]
        if unannotated:
            raise AssertionError("%s parameters are unannotated: %s" % (
                name, sorted(unannotated)))


def _numeric_addresses(host, port):
    try:
        rows = socket.getaddrinfo(
            host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM,
            flags=socket.AI_NUMERICHOST)
    except socket.gaierror:
        return set()
    return {ipaddress.ip_address(row[4][0].split("%", 1)[0]) for row in rows}


def _service_domain_negative_fixture():
    module = types.ModuleType("negative_service_domain_fixture")
    for name in SERVICE_DOMAIN_MODELS:
        model = dataclasses.make_dataclass(name, [])
        model.__module__ = module.__name__
        setattr(module, name, model)
    exec(  # pylint: disable=exec-used
        "def derive_service_paths(value: str) -> str:\n"
        "    return value\n"
        "def validate_public_listener(value: str) -> str:\n"
        "    return value\n"
        "def unexpected_public_seam(value: str) -> str:\n"
        "    return value\n",
        module.__dict__)
    return module


class ServiceDomainTests(unittest.TestCase):
    def test_paths_are_global_and_do_not_consume_session_identity(self):
        with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as runtime:
            paths = derive_service_paths("darwin", Path(state), Path(runtime), uid=501)

        self.assertEqual(paths.durable_dir, Path(state) / "superdev/codex-worker/service")
        self.assertEqual(paths.registry_path, paths.durable_dir / "registry.json")
        self.assertEqual(paths.config_path, paths.durable_dir / "service.json")
        self.assertEqual(paths.migration_path, paths.durable_dir / "migration.json")
        self.assertEqual(paths.callback_path, paths.durable_dir / "callbacks.json")
        self.assertEqual(paths.callback_artifact_dir,
                         paths.durable_dir / "callback-artifacts")
        self.assertEqual(paths.rpc_socket.parent, paths.private_codex_socket.parent)
        self.assertEqual(paths.start_lock.parent, paths.rpc_socket.parent)
        self.assertNotIn("CLAUDE_CODE_SESSION_ID", str(paths))
        self.assertNotIn("instances", str(paths.durable_dir))

    def test_path_derivation_is_behaviorally_independent_of_session_environment(self):
        with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as runtime:
            args = ("darwin", Path(state), Path(runtime), 501)
            with mock.patch.dict(os.environ, {
                    "CLAUDE_CODE_SESSION_ID": "session-a",
                    "CODEX_WORKER_INSTANCE": "instance-a",
            }):
                first = derive_service_paths(*args)
            with mock.patch.dict(os.environ, {
                    "CLAUDE_CODE_SESSION_ID": "session-b",
                    "CODEX_WORKER_INSTANCE": "instance-b",
            }):
                second = derive_service_paths(*args)

        self.assertEqual(first, second)

    def test_paths_reject_invalid_boundary_values(self):
        with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as runtime:
            for args in (("", Path(state), Path(runtime), 501),
                         ("darwin", Path("relative"), Path(runtime), 501),
                         ("darwin", Path(state), Path("relative"), 501),
                         ("darwin", Path(state), Path(runtime), -1),
                         ("darwin", Path(state), Path(runtime), True)):
                with self.subTest(args=args), self.assertRaises(ValueError):
                    derive_service_paths(*args)

    def test_listener_accepts_only_connectable_websocket_addresses_losslessly(self):
        accepted = (
            "ws://127.0.0.1:4500",
            "ws://127.1:4500",
            "ws://0x7f000001:4500",
            "ws://localhost:4500",
            "ws://example.test:65535",
            "ws://unspecified.example:4500",
            "ws://[::1]:1",
        )
        for value in accepted:
            with self.subTest(value=value):
                self.assertEqual(validate_public_listener(value), value)

    def test_listener_rejects_every_non_attachable_or_ambiguous_shape(self):
        rejected = (
            "", "off", "stdio://", "unix:///tmp/codex.sock",
            "wss://127.0.0.1:4500", "http://127.0.0.1:4500",
            "ws://127.0.0.1", "ws://127.0.0.1:0", "ws://127.0.0.1:65536",
            "ws://0.0.0.0:4500", "ws://[::]:4500", "ws://*:4500",
            "ws://user@127.0.0.1:4500", "ws://user:pass@127.0.0.1:4500",
            "ws://127.0.0.1:4500/", "ws://127.0.0.1:4500/path",
            "ws://127.0.0.1:4500?query=1", "ws://127.0.0.1:4500#fragment",
            "ws://127.0.0.1:not-a-port", "WS://127.0.0.1:4500",
            "ws://127.0.0.1:4500\n",
        )
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_public_listener(value)
        with self.assertRaises(ValueError):
            validate_public_listener(None)  # type: ignore[arg-type]

    def test_listener_rejects_every_numeric_alias_that_resolves_unspecified(self):
        aliases = (
            ("0", "0"), ("00", "00"), ("0000", "0000"), ("0x0", "0x0"),
            ("0.0", "0.0"), ("0.0.0", "0.0.0"),
            ("000.000.000.000", "000.000.000.000"),
            ("0:0:0:0:0:0:0:0", "[0:0:0:0:0:0:0:0]"),
        )
        unspecified_aliases = []
        for host, url_host in aliases:
            addresses = _numeric_addresses(host, 4500)
            if addresses and all(address.is_unspecified for address in addresses):
                unspecified_aliases.append((host, url_host))

        self.assertIn(("0", "0"), unspecified_aliases)
        for _, url_host in unspecified_aliases:
            value = "ws://%s:4500" % url_host
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_public_listener(value)

    def test_listener_numeric_classification_never_performs_hostname_dns(self):
        refusal = socket.gaierror(socket.EAI_NONAME, "not a numeric host")
        with mock.patch("codex_worker.service_domain.socket.getaddrinfo",
                        side_effect=refusal) as resolver:
            value = "ws://example.test:4500"
            self.assertEqual(validate_public_listener(value), value)

        _, kwargs = resolver.call_args
        self.assertEqual(kwargs["flags"], socket.AI_NUMERICHOST)

    def test_strict_models_round_trip_and_reject_extra_fields(self):
        candidate = LegacyCandidate(
            source_path="/state/instances/a/registry.json",
            source_digest="a" * 64,
            name="status-checker-abc",
            session_id="00000000-0000-0000-0000-000000000001",
            thread_id="thread-a",
            cwd="/tmp",
            created_at="2026-08-28T00:00:00Z",
            updated_at="2026-08-28T00:00:00Z",
            model="gpt-5.6-terra",
            effort="medium",
            tier="medium",
            access="full",
        )
        conflict = LegacyConflict("status-checker-abc", [candidate], ["a" * 64])
        source = MigrationSourceView(candidate.source_path, candidate.source_digest,
                                     candidate.name, candidate.session_id,
                                     candidate.thread_id, MigrationOutcome.CONFLICTED)
        values = (
            ServiceConfig("ws://127.0.0.1:4500", "8.1.0",
                          "00000000-0000-0000-0000-000000000099"),
            AttachView("ws://127.0.0.1:4500", "thread-a",
                       "codex --remote ws://127.0.0.1:4500",
                       "codex --remote ws://127.0.0.1:4500 resume thread-a"),
            candidate,
            conflict,
            source,
            MigrationStatusView(MigrationState.COMPLETE, True, 0, 0, 1,
                                [source], [conflict]),
        )
        for value in values:
            with self.subTest(model=type(value).__name__):
                rebuilt = type(value).from_dict(value.to_dict())
                self.assertEqual(rebuilt, value)
                extra = dict(value.to_dict(), unexpected=True)
                with self.assertRaises(ValueError):
                    type(value).from_dict(extra)
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    setattr(value, "unexpected", True)

    def test_model_contracts_reject_inconsistent_conflict_and_counts(self):
        candidate = LegacyCandidate(
            "/state/instances/a/registry.json", "a" * 64, "worker-a",
            "00000000-0000-0000-0000-000000000001", "thread-a", "/tmp",
            "2026-08-28T00:00:00Z", "2026-08-28T00:00:00Z",
            "model", "medium", "medium", "full")
        with self.assertRaises(ValueError):
            LegacyConflict("other-name", [candidate], ["a" * 64])
        with self.assertRaises(ValueError):
            LegacyConflict("worker-a", [candidate], ["b" * 64])
        with self.assertRaises(ValueError):
            MigrationStatusView(MigrationState.COMPLETE, False, 0, 0, 0, [], [])


class ServiceDomainArchitectureGuards(unittest.TestCase):
    def test_service_domain_import_arrows_point_inward(self):
        path = SCRIPTS / "codex_worker" / "service_domain.py"
        forbidden = {"app_server", "broker", "callback_dispatcher", "cli", "facade",
                     "instance", "migration", "registry", "rpc", "runtime", "service",
                     "websocket_gateway", "websocket_transport"}
        _assert_import_arrows(path, forbidden)

    def test_service_domain_import_guard_rejects_forbidden_fixture(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = Path(root) / "forbidden_service_domain.py"
            fixture.write_text("from codex_worker.cli import main\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "cli"):
                _assert_import_arrows(fixture, {"cli"})

    def test_service_domain_seam_inventory_is_closed_and_typed(self):
        import codex_worker.service_domain as domain

        _assert_service_domain_inventory(domain)

    def test_service_domain_inventory_guard_rejects_unexpected_public_fixture(self):
        with self.assertRaisesRegex(AssertionError, "unexpected_public_seam"):
            _assert_service_domain_inventory(_service_domain_negative_fixture())

    def test_migration_import_arrows_exclude_shell_and_transport(self):
        path = SCRIPTS / "codex_worker" / "migration.py"
        forbidden = {"app_server", "broker", "callback_dispatcher", "cli", "facade",
                     "rpc", "runtime", "service", "websocket_gateway",
                     "websocket_transport"}
        _assert_import_arrows(path, forbidden)

    def test_migration_import_guard_rejects_forbidden_fixture(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = Path(root) / "forbidden_migration.py"
            fixture.write_text("from codex_worker.rpc import RpcServer\n", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "rpc"):
                _assert_import_arrows(fixture, {"rpc"})

    def test_migration_public_service_seams_are_typed(self):
        from codex_worker.migration import LegacyMigrator

        _assert_typed_methods(LegacyMigrator, ("scan_and_apply", "resolve"))

    def test_migration_seam_guard_rejects_unannotated_fixture(self):
        namespace = {}
        exec(  # pylint: disable=exec-used
            "class LegacyMigrator:\n"
            "    def scan_and_apply(self):\n"
            "        return None\n"
            "    def resolve(self, name, thread_id, as_name):\n"
            "        return None\n",
            namespace)
        with self.assertRaisesRegex(AssertionError, "unannotated"):
            _assert_typed_methods(namespace["LegacyMigrator"],
                                  ("scan_and_apply", "resolve"))


if __name__ == "__main__":
    unittest.main()
