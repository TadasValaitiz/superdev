import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "subagent-driven-development" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from codex_worker.callback_domain import CallbackEvent  # noqa: E402
from codex_worker.callback_store import (  # noqa: E402
    CallbackBinding,
    CallbackOutboxState,
    CallbackStore,
)
from codex_worker.commands import (  # noqa: E402
    AccessMode,
    CallbackState,
    CompletionResponse,
    RecoveryView,
    Tier,
    TurnView,
    WorkerView,
)
from codex_worker.instance import InstanceIdentity, derive_instance_paths  # noqa: E402
from codex_worker.commands import InstanceSource  # noqa: E402
from codex_worker.migration import (  # noqa: E402
    LegacyMigrationDeps,
    LegacyMigrationError,
    LegacyMigrator,
    MigrationCommitStage,
)
from codex_worker.models import IdentifierSelector, SessionRecord  # noqa: E402
from codex_worker.registry import LegacyNameConflict, SessionRegistry  # noqa: E402
from codex_worker.service_domain import (  # noqa: E402
    MigrationOutcome,
    MigrationState,
    derive_service_paths,
)


FIXTURES = Path(__file__).with_name("fixtures")


class MigrationFixture:
    def __init__(self, testcase):
        self.testcase = testcase
        self.temporary = tempfile.TemporaryDirectory()
        testcase.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state_home = self.root / "state"
        self.temp_root = self.root / "tmp"
        self.cwd = self.root / "cwd"
        self.cwd.mkdir(mode=0o700)
        self.temp_root.mkdir(mode=0o700)
        self.paths = derive_service_paths("darwin", self.state_home, self.temp_root,
                                          uid=os.getuid())
        self.instances = self.state_home / "superdev/codex-worker/instances"

    def record(self, suffix, name, thread_id=None, **changes):
        values = {
            "session_id": "00000000-0000-0000-0000-%012x" % suffix,
            "thread_id": thread_id or "thread-%s" % suffix,
            "cwd": str(self.cwd.resolve()),
            "created_at": "2026-08-28T00:00:00Z",
            "updated_at": "2026-08-28T00:00:00Z",
            "name": name,
            "model": "gpt-5.6-terra",
            "effort": "medium",
            "tier": "medium",
            "access": "full",
        }
        values.update(changes)
        return SessionRecord(**values)

    def add_instance(self, label, records):
        identity = InstanceIdentity(InstanceSource.FLAG, label)
        paths = derive_instance_paths(identity, "darwin", self.state_home,
                                      self.temp_root, os.getuid())
        paths.durable_dir.mkdir(mode=0o700, parents=True)
        metadata = {"source": identity.source.value, "value": identity.value,
                    "key_hash": identity.key_hash}
        paths.metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8")
        os.chmod(paths.metadata_path, 0o600)
        SessionRegistry(paths.registry_path).replace_all(records)
        return paths

    def worker(self, record, instance="legacy-instance"):
        return WorkerView(instance, record.name, record.session_id, record.thread_id,
                          record.cwd, Tier(record.tier), record.model, record.effort,
                          AccessMode(record.access))

    def binding(self, record, state=CallbackState.ENABLED, token="a" * 32):
        full = state == CallbackState.ENABLED
        resolver = str(self.root) if state != CallbackState.DISABLED else None
        return CallbackBinding(
            record.session_id, state,
            "/tmp/claude.sock" if full else None,
            token if full else None,
            "claude-session" if full else None,
            123 if full else None,
            "process-start" if full else None,
            resolver,
            "2026-08-28T00:00:00Z",
        )

    def event(self, record, event_id, event="turn_terminal"):
        payload = ({"completion": self.completion(record).to_dict()}
                   if event == "turn_terminal" else {"message": "progress"})
        return CallbackEvent("codex-worker.claude-callback/v1", event, event_id,
                             "2026-08-28T00:00:00Z", "next",
                             self.worker(record), payload)

    def completion(self, record):
        return CompletionResponse(
            self.worker(record), TurnView("turn-1", "completed", None), [], None, {},
            RecoveryView("status", "messages", "interrupt"))

    def source_hashes(self):
        result = {}
        if not self.instances.exists():
            return result
        for path in sorted(self.instances.rglob("*")):
            if path.is_file() and not path.is_symlink():
                metadata = os.stat(path)
                result[str(path.relative_to(self.instances))] = (
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    stat.S_IMODE(metadata.st_mode), metadata.st_mtime_ns,
                )
        return result

    def migrator(self, **changes):
        values = {"paths": self.paths, "legacy_instances_dir": self.instances}
        values.update(changes)
        return LegacyMigrator(LegacyMigrationDeps(**values))


class LegacyMigrationTests(unittest.TestCase):
    def test_imports_unique_deduplicates_byte_equal_and_quarantines_sanitized_conflict(self):
        fixture = MigrationFixture(self)
        unique = fixture.record(1, "unique-worker")
        duplicate = fixture.record(2, "duplicate-worker")
        measured = json.loads((FIXTURES / "status-checker-abc-legacy-records.json")
                              .read_text(encoding="utf-8"))["records"]
        conflict_a = SessionRecord(cwd=str(fixture.cwd.resolve()), **measured[0])
        conflict_b = SessionRecord(cwd=str(fixture.cwd.resolve()), **measured[1])
        fixture.add_instance("unique", [unique])
        fixture.add_instance("duplicate-a", [duplicate])
        fixture.add_instance("duplicate-b", [duplicate])
        fixture.add_instance("conflict-a", [conflict_a])
        fixture.add_instance("conflict-b", [conflict_b])
        before = fixture.source_hashes()

        status = fixture.migrator().scan_and_apply()

        self.assertEqual(status.status, MigrationState.COMPLETE)
        self.assertTrue(status.ready)
        self.assertEqual((status.imported_count, status.deduplicated_count,
                          status.conflict_count), (2, 1, 1))
        self.assertEqual({candidate.thread_id for candidate in status.conflicts[0].candidates},
                         {"thread-a", "thread-b"})
        self.assertEqual(fixture.source_hashes(), before)
        records = SessionRegistry(fixture.paths.registry_path).list()
        self.assertEqual({record.name for record in records},
                         {"unique-worker", "duplicate-worker"})
        self.assertEqual(stat.S_IMODE(os.stat(fixture.paths.migration_path).st_mode), 0o600)

        ledger_before = fixture.paths.migration_path.read_bytes()
        registry_before = fixture.paths.registry_path.read_bytes()
        repeated = fixture.migrator().scan_and_apply()
        self.assertEqual(repeated, status)
        self.assertEqual(fixture.paths.migration_path.read_bytes(), ledger_before)
        self.assertEqual(fixture.paths.registry_path.read_bytes(), registry_before)
        self.assertEqual(fixture.source_hashes(), before)

    def test_conflicted_name_refuses_with_all_candidates_and_no_force_action(self):
        fixture = MigrationFixture(self)
        a = fixture.record(1, "collision", "thread-a")
        b = fixture.record(2, "collision", "thread-b")
        fixture.add_instance("a", [a])
        fixture.add_instance("b", [b])
        fixture.migrator().scan_and_apply()
        registry = SessionRegistry(fixture.paths.registry_path,
                                   migration_path=fixture.paths.migration_path)

        with self.assertRaises(LegacyNameConflict) as caught:
            registry.resolve_name("collision")

        self.assertEqual(caught.exception.kind, "legacy_name_conflict")
        self.assertEqual({item["thread_id"] for item in caught.exception.candidates},
                         {"thread-a", "thread-b"})
        self.assertNotIn("--force", json.dumps(caught.exception.next_actions))

    def test_resolve_selects_original_name_or_imports_explicit_alternate(self):
        fixture = MigrationFixture(self)
        a = fixture.record(1, "collision", "thread-a")
        b = fixture.record(2, "collision", "thread-b")
        fixture.add_instance("a", [a])
        b_paths = fixture.add_instance("b", [b])
        b_store = CallbackStore(b_paths.callback_path, b_paths.callback_artifact_dir)
        b_store.bind(fixture.binding(b))
        b_store.enqueue_terminal(b.session_id, fixture.event(b, "event-b"))
        migrator = fixture.migrator()
        migrator.scan_and_apply()

        alternate = migrator.resolve("collision", "thread-b", "collision-b")
        self.assertEqual((alternate.name, alternate.thread_id), ("collision-b", "thread-b"))
        migrated_event = CallbackStore(
            fixture.paths.callback_path, fixture.paths.callback_artifact_dir,
        ).pending(alternate.session_id)[0].event
        self.assertEqual((migrated_event.worker.instance, migrated_event.worker.name),
                         ("global", "collision-b"))
        with self.assertRaises(LegacyNameConflict):
            SessionRegistry(fixture.paths.registry_path,
                            migration_path=fixture.paths.migration_path).resolve_name("collision")

        selected = migrator.resolve("collision", "thread-a", None)
        self.assertEqual((selected.name, selected.thread_id), ("collision", "thread-a"))
        registry = SessionRegistry(fixture.paths.registry_path,
                                   migration_path=fixture.paths.migration_path)
        self.assertEqual(registry.resolve_name("collision"), selected)
        self.assertEqual(registry.resolve_name("collision-b"), alternate)

    def test_migrates_all_binding_states_pending_written_and_equal_events(self):
        fixture = MigrationFixture(self)
        enabled = fixture.record(1, "enabled")
        unavailable = fixture.record(2, "unavailable")
        disabled = fixture.record(3, "disabled")
        duplicate = fixture.record(4, "duplicate")
        sources = [
            fixture.add_instance("enabled", [enabled]),
            fixture.add_instance("unavailable", [unavailable]),
            fixture.add_instance("disabled", [disabled]),
            fixture.add_instance("duplicate-a", [duplicate]),
            fixture.add_instance("duplicate-b", [duplicate]),
        ]
        for paths, record, state in zip(
                sources[:3], (enabled, unavailable, disabled),
                (CallbackState.ENABLED, CallbackState.UNAVAILABLE, CallbackState.DISABLED)):
            store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
            store.bind(fixture.binding(record, state))
            store.enqueue_terminal(record.session_id, fixture.event(record, "event-%s" % record.name))
        # Preserve a written entry and its attempt history.
        CallbackStore(sources[2].callback_path, sources[2].callback_artifact_dir).record_written(
            "event-disabled", "2026-08-28T00:01:00Z")
        for paths in sources[3:]:
            store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
            store.bind(fixture.binding(duplicate))
            store.enqueue_terminal(duplicate.session_id,
                                   fixture.event(duplicate, "event-duplicate"))
        before = fixture.source_hashes()

        status = fixture.migrator().scan_and_apply()

        self.assertEqual(status.conflict_count, 0)
        target = CallbackStore(fixture.paths.callback_path,
                               fixture.paths.callback_artifact_dir)
        self.assertEqual(target.binding(enabled.session_id).state, CallbackState.ENABLED)
        self.assertEqual(target.binding(unavailable.session_id).state,
                         CallbackState.UNAVAILABLE)
        self.assertEqual(target.binding(disabled.session_id).state, CallbackState.DISABLED)
        self.assertEqual(target.pending(enabled.session_id)[0].event.worker.instance, "global")
        self.assertEqual(len(target.pending(duplicate.session_id)), 1)
        self.assertEqual(target.pending(disabled.session_id), [])
        self.assertEqual(target.status_view(disabled.session_id)
                         .last_terminal_attempt.state.value, "written")
        self.assertEqual(fixture.source_hashes(), before)

    def test_callback_binding_or_event_id_mismatch_quarantines_associated_workers(self):
        fixture = MigrationFixture(self)
        binding_record = fixture.record(1, "binding-conflict")
        event_a = fixture.record(2, "event-a")
        event_b = fixture.record(3, "event-b")
        binding_paths = [fixture.add_instance("binding-a", [binding_record]),
                         fixture.add_instance("binding-b", [binding_record])]
        for paths, token in zip(binding_paths, ("a" * 32, "b" * 32)):
            CallbackStore(paths.callback_path, paths.callback_artifact_dir).bind(
                fixture.binding(binding_record, token=token))
        event_paths = [fixture.add_instance("event-a", [event_a]),
                       fixture.add_instance("event-b", [event_b])]
        for paths, record in zip(event_paths, (event_a, event_b)):
            store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
            store.bind(fixture.binding(record))
            store.enqueue_terminal(record.session_id,
                                   fixture.event(record, "shared-event-id"))

        status = fixture.migrator().scan_and_apply()

        self.assertEqual({conflict.name for conflict in status.conflicts},
                         {"binding-conflict", "event-a", "event-b"})
        self.assertEqual(SessionRegistry(fixture.paths.registry_path).list(), [])
        self.assertEqual(CallbackStore(fixture.paths.callback_path,
                                       fixture.paths.callback_artifact_dir).pending(), [])

    def test_cross_name_session_or_thread_collision_is_quarantined_before_commit(self):
        for collision in ("session", "thread"):
            with self.subTest(collision=collision):
                fixture = MigrationFixture(self)
                a = fixture.record(1, "worker-a", "thread-a")
                if collision == "session":
                    b = fixture.record(1, "worker-b", "thread-b")
                else:
                    b = fixture.record(2, "worker-b", "thread-a")
                fixture.add_instance("a", [a])
                fixture.add_instance("b", [b])

                status = fixture.migrator().scan_and_apply()

                self.assertEqual({item.name for item in status.conflicts},
                                 {"worker-a", "worker-b"})
                self.assertEqual(SessionRegistry(fixture.paths.registry_path).list(), [])

    def test_terminal_reference_is_verified_republished_and_projected_global(self):
        fixture = MigrationFixture(self)
        record = fixture.record(1, "referenced")
        paths = fixture.add_instance("referenced", [record])
        store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
        store.bind(fixture.binding(record))
        artifact = store.publish_artifact("terminal-ref", fixture.completion(record))
        event = CallbackEvent(
            "codex-worker.claude-callback/v1", "turn_terminal_reference", "terminal-ref",
            "2026-08-28T00:00:00Z", "next", fixture.worker(record),
            {"artifact": {"path": artifact.path, "sha256": artifact.sha256,
                          "size_bytes": artifact.size_bytes}})
        store.enqueue_terminal(record.session_id, event)
        before = fixture.source_hashes()

        fixture.migrator().scan_and_apply()

        target = CallbackStore(fixture.paths.callback_path,
                               fixture.paths.callback_artifact_dir)
        migrated = target.pending(record.session_id)[0].event
        migrated_artifact = migrated.payload["artifact"]
        self.assertEqual(migrated.worker.instance, "global")
        self.assertTrue(Path(migrated_artifact["path"])
                        .is_relative_to(fixture.paths.callback_artifact_dir))
        content = json.loads(Path(migrated_artifact["path"]).read_text(encoding="utf-8"))
        self.assertEqual(content["worker"]["instance"], "global")
        self.assertEqual(hashlib.sha256(Path(migrated_artifact["path"]).read_bytes()).hexdigest(),
                         migrated_artifact["sha256"])
        self.assertEqual(fixture.source_hashes(), before)

    def test_unsafe_sources_and_artifact_escape_or_digest_mismatch_refuse_before_commit(self):
        cases = ("registry-symlink", "artifact-escape", "artifact-digest", "artifact-size")
        for case in cases:
            with self.subTest(case=case):
                fixture = MigrationFixture(self)
                record = fixture.record(1, "unsafe")
                paths = fixture.add_instance("unsafe", [record])
                if case == "registry-symlink":
                    target = paths.durable_dir / "registry-target.json"
                    paths.registry_path.replace(target)
                    paths.registry_path.symlink_to(target)
                else:
                    store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
                    store.bind(fixture.binding(record))
                    artifact = store.publish_artifact("unsafe-ref", fixture.completion(record))
                    reference = {"path": artifact.path, "sha256": artifact.sha256,
                                 "size_bytes": artifact.size_bytes}
                    if case == "artifact-escape":
                        outside = fixture.root / "outside.json"
                        outside.write_bytes(Path(artifact.path).read_bytes())
                        os.chmod(outside, 0o600)
                        reference["path"] = str(outside)
                    elif case == "artifact-digest":
                        reference["sha256"] = "0" * 64
                    else:
                        reference["size_bytes"] += 1
                    event = CallbackEvent(
                        "codex-worker.claude-callback/v1", "turn_terminal_reference",
                        "unsafe-ref", "2026-08-28T00:00:00Z", "next",
                        fixture.worker(record), {"artifact": reference})
                    store.enqueue_terminal(record.session_id, event)
                before = fixture.source_hashes()

                with self.assertRaises(LegacyMigrationError):
                    fixture.migrator().scan_and_apply()

                self.assertFalse(fixture.paths.migration_path.exists())
                self.assertFalse(fixture.paths.registry_path.exists())
                self.assertEqual(fixture.source_hashes(), before)

    def test_restart_repairs_every_commit_prefix_and_ledger_is_fsynced_last(self):
        for crash_stage in MigrationCommitStage:
            with self.subTest(stage=crash_stage.value):
                fixture = MigrationFixture(self)
                record = fixture.record(1, "crash-safe")
                paths = fixture.add_instance("crash-safe", [record])
                store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
                store.bind(fixture.binding(record))
                artifact = store.publish_artifact("crash-ref", fixture.completion(record))
                store.enqueue_terminal(record.session_id, CallbackEvent(
                    "codex-worker.claude-callback/v1", "turn_terminal_reference",
                    "crash-ref", "2026-08-28T00:00:00Z", "next",
                    fixture.worker(record), {"artifact": {
                        "path": artifact.path, "sha256": artifact.sha256,
                        "size_bytes": artifact.size_bytes}}))
                before = fixture.source_hashes()
                observed = []

                def crash(stage):
                    observed.append(stage)
                    if stage == crash_stage:
                        raise RuntimeError("simulated crash after %s" % stage.value)

                with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                    fixture.migrator(after_commit=crash).scan_and_apply()
                self.assertEqual(fixture.source_hashes(), before)
                if crash_stage != MigrationCommitStage.LEDGER:
                    self.assertFalse(fixture.paths.migration_path.exists())

                repaired = fixture.migrator().scan_and_apply()
                self.assertTrue(repaired.ready)
                self.assertEqual(SessionRegistry(fixture.paths.registry_path)
                                 .resolve(IdentifierSelector(session_id=record.session_id)), record)
                self.assertEqual(len(CallbackStore(fixture.paths.callback_path,
                                                   fixture.paths.callback_artifact_dir)
                                     .pending(record.session_id)), 1)
                self.assertEqual(fixture.source_hashes(), before)

    def test_completion_ledger_file_and_directory_are_fsynced(self):
        fixture = MigrationFixture(self)
        fixture.add_instance("one", [fixture.record(1, "one")])
        calls = []

        def recording_fsync(descriptor):
            calls.append(descriptor)
            os.fsync(descriptor)

        status = fixture.migrator(fsync=recording_fsync).scan_and_apply()
        self.assertTrue(status.ready)
        # Registry, callback store, and ledger each fsync file + containing directory.
        self.assertGreaterEqual(len(calls), 6)


if __name__ == "__main__":
    unittest.main()
