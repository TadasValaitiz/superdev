import ast
import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path


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
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {"app_server", "broker", "callback_dispatcher", "cli", "facade",
                     "instance", "migration", "registry", "rpc", "runtime", "service",
                     "websocket_gateway", "websocket_transport"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.rsplit(".", 1)[-1])
            elif isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
        self.assertFalse(forbidden & imported, forbidden & imported)

    def test_service_domain_seam_inventory_is_closed_and_typed(self):
        import inspect
        import codex_worker.service_domain as domain

        expected_models = {
            "AttachView", "LegacyCandidate", "LegacyConflict", "MigrationSourceView",
            "MigrationStatusView", "ServiceConfig", "ServicePaths",
        }
        actual_models = {
            name for name, value in vars(domain).items()
            if inspect.isclass(value) and dataclasses.is_dataclass(value)
            and value.__module__ == domain.__name__
        }
        self.assertEqual(actual_models, expected_models)
        expected_functions = {"derive_service_paths", "validate_public_listener"}
        actual_functions = {
            name for name, value in vars(domain).items()
            if inspect.isfunction(value) and value.__module__ == domain.__name__
            and not name.startswith("_")
        }
        self.assertEqual(actual_functions, expected_functions)
        for name in expected_functions:
            signature = inspect.signature(getattr(domain, name))
            self.assertIsNot(signature.return_annotation, inspect.Signature.empty)
            self.assertTrue(all(parameter.annotation is not inspect.Signature.empty
                                for parameter in signature.parameters.values()))

    def test_migration_import_arrows_exclude_shell_and_transport(self):
        path = SCRIPTS / "codex_worker" / "migration.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {"app_server", "broker", "callback_dispatcher", "cli", "facade",
                     "rpc", "runtime", "service", "websocket_gateway",
                     "websocket_transport"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.rsplit(".", 1)[-1])
            elif isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
        self.assertFalse(forbidden & imported, forbidden & imported)

    def test_migration_public_service_seams_are_typed(self):
        import inspect
        from codex_worker.migration import LegacyMigrator

        for name in ("scan_and_apply", "resolve"):
            signature = inspect.signature(getattr(LegacyMigrator, name))
            self.assertIsNot(signature.return_annotation, inspect.Signature.empty)
            self.assertTrue(all(parameter.annotation is not inspect.Signature.empty
                                for parameter in signature.parameters.values()
                                if parameter.name != "self"))


if __name__ == "__main__":
    unittest.main()
