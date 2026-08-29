import hashlib
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace


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
    LiveMigrationCoordinator,
    MigrationCommitStage,
)
from codex_worker.models import IdentifierSelector, SessionRecord  # noqa: E402
from codex_worker.registry import LegacyNameConflict, SessionRegistry  # noqa: E402
from codex_worker.service_domain import (  # noqa: E402
    MigrationOutcome,
    MigrationState,
    derive_service_paths,
)
from codex_worker.websocket_gateway import ServiceMaintenanceGate  # noqa: E402


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
        return WorkerView(record.name, record.session_id, record.thread_id,
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
        self.assertEqual(migrated_event.worker.name, "collision-b")
        self.assertNotIn("instance", migrated_event.worker.to_dict())
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
        self.assertNotIn(
            "instance", target.pending(enabled.session_id)[0].event.worker.to_dict())
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
        self.assertNotIn("instance", migrated.worker.to_dict())
        self.assertTrue(Path(migrated_artifact["path"])
                        .is_relative_to(fixture.paths.callback_artifact_dir))
        content = json.loads(Path(migrated_artifact["path"]).read_text(encoding="utf-8"))
        self.assertNotIn("instance", content["worker"])
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

    def test_live_resolution_restart_repairs_every_commit_prefix(self):
        class SimulatedHardCrash(BaseException):
            pass

        for crash_stage in MigrationCommitStage:
            with self.subTest(stage=crash_stage.value):
                fixture = MigrationFixture(self)
                selected = fixture.record(1, "collision", "thread-a")
                rejected = fixture.record(2, "collision", "thread-b")
                unrelated = fixture.record(3, "unrelated", "thread-unrelated")
                fixture.add_instance("a", [selected, unrelated])
                rejected_paths = fixture.add_instance("b", [rejected])
                rejected_store = CallbackStore(
                    rejected_paths.callback_path,
                    rejected_paths.callback_artifact_dir)
                rejected_store.bind(fixture.binding(rejected))
                rejected_store.enqueue_terminal(
                    rejected.session_id, fixture.event(rejected, "event-rejected"))
                armed = [False]

                def crash(stage):
                    if armed[0] and stage == crash_stage:
                        raise SimulatedHardCrash(stage.value)

                migrator = fixture.migrator(after_commit=crash)
                migrator.scan_and_apply()
                registry = SessionRegistry(
                    fixture.paths.registry_path,
                    migration_path=fixture.paths.migration_path)
                callbacks = CallbackStore(
                    fixture.paths.callback_path,
                    fixture.paths.callback_artifact_dir)
                broker = SimpleNamespace(
                    registry=registry, _gate=ServiceMaintenanceGate())
                coordinator = LiveMigrationCoordinator(migrator, broker, callbacks)
                armed[0] = True

                with self.assertRaises(SimulatedHardCrash):
                    coordinator.resolve("collision", "thread-b", "collision-b")

                armed[0] = False
                self.assertTrue(
                    fixture.paths.migration_path.with_name(
                        "migration-resolution.json").exists())
                repaired = fixture.migrator().scan_and_apply()
                self.assertTrue(repaired.ready)
                self.assertEqual(
                    (repaired.imported_count, repaired.deduplicated_count,
                     repaired.conflict_count), (2, 0, 1))
                self.assertEqual(
                    {item.thread_id: item.outcome for item in repaired.sources},
                    {"thread-a": MigrationOutcome.CONFLICTED,
                     "thread-b": MigrationOutcome.IMPORTED,
                     "thread-unrelated": MigrationOutcome.IMPORTED})
                self.assertFalse(
                    fixture.paths.migration_path.with_name(
                        "migration-resolution.json").exists())
                repaired_registry = SessionRegistry(
                    fixture.paths.registry_path,
                    migration_path=fixture.paths.migration_path)
                self.assertEqual(
                    repaired_registry.resolve_name("collision-b").thread_id,
                    "thread-b")
                self.assertEqual(
                    repaired_registry.resolve_name("unrelated").thread_id,
                    "thread-unrelated")
                self.assertEqual(
                    CallbackStore(
                        fixture.paths.callback_path,
                        fixture.paths.callback_artifact_dir,
                    ).pending(rejected.session_id)[0].event.worker.name,
                    "collision-b")

    def test_live_resolution_exception_rolls_back_every_commit_prefix(self):
        for failure_stage in MigrationCommitStage:
            with self.subTest(stage=failure_stage.value):
                fixture = MigrationFixture(self)
                selected = fixture.record(1, "collision", "thread-a")
                rejected = fixture.record(2, "collision", "thread-b")
                unrelated = fixture.record(3, "unrelated", "thread-unrelated")
                fixture.add_instance("a", [selected, unrelated])
                rejected_paths = fixture.add_instance("b", [rejected])
                rejected_store = CallbackStore(
                    rejected_paths.callback_path,
                    rejected_paths.callback_artifact_dir)
                rejected_store.bind(fixture.binding(rejected))
                rejected_store.enqueue_terminal(
                    rejected.session_id, fixture.event(rejected, "event-rejected"))
                armed = [False]

                def fail(stage):
                    if armed[0] and stage == failure_stage:
                        raise RuntimeError(stage.value)

                migrator = fixture.migrator(after_commit=fail)
                migrator.scan_and_apply()
                registry = SessionRegistry(
                    fixture.paths.registry_path,
                    migration_path=fixture.paths.migration_path)
                callbacks = CallbackStore(
                    fixture.paths.callback_path,
                    fixture.paths.callback_artifact_dir)
                coordinator = LiveMigrationCoordinator(
                    migrator,
                    SimpleNamespace(
                        registry=registry, _gate=ServiceMaintenanceGate()),
                    callbacks)
                before = (
                    fixture.paths.registry_path.read_bytes(),
                    fixture.paths.callback_path.read_bytes(),
                    fixture.paths.migration_path.read_bytes(),
                )
                armed[0] = True

                with self.assertRaises(RuntimeError):
                    coordinator.resolve("collision", "thread-b", "collision-b")

                self.assertEqual(
                    (fixture.paths.registry_path.read_bytes(),
                     fixture.paths.callback_path.read_bytes(),
                     fixture.paths.migration_path.read_bytes()),
                    before)
                self.assertFalse(
                    fixture.paths.migration_path.with_name(
                        "migration-resolution.json").exists())
                self.assertEqual(
                    registry.resolve_name("unrelated").thread_id,
                    "thread-unrelated")
                with self.assertRaises(LegacyNameConflict):
                    registry.resolve_name("collision")
                self.assertEqual(callbacks.pending(rejected.session_id), [])

    def test_recovery_failure_preserves_intent_after_each_hard_crash_prefix(self):
        class SimulatedHardCrash(BaseException):
            pass

        later_stages = {
            MigrationCommitStage.ARTIFACTS: (
                MigrationCommitStage.REGISTRY,
                MigrationCommitStage.CALLBACKS,
                MigrationCommitStage.LEDGER,
            ),
            MigrationCommitStage.REGISTRY: (
                MigrationCommitStage.CALLBACKS,
                MigrationCommitStage.LEDGER,
            ),
            MigrationCommitStage.CALLBACKS: (MigrationCommitStage.LEDGER,),
        }
        for crash_stage, failure_stages in later_stages.items():
            for failure_stage in failure_stages:
                with self.subTest(crash=crash_stage.value,
                                  failure=failure_stage.value):
                    fixture = MigrationFixture(self)
                    selected = fixture.record(1, "collision", "thread-a")
                    rejected = fixture.record(2, "collision", "thread-b")
                    fixture.add_instance("a", [selected])
                    rejected_paths = fixture.add_instance("b", [rejected])
                    rejected_store = CallbackStore(
                        rejected_paths.callback_path,
                        rejected_paths.callback_artifact_dir)
                    rejected_store.bind(fixture.binding(rejected))
                    rejected_store.enqueue_terminal(
                        rejected.session_id,
                        fixture.event(rejected, "event-rejected"))
                    armed = [False]

                    def crash(stage):
                        if armed[0] and stage == crash_stage:
                            raise SimulatedHardCrash(stage.value)

                    migrator = fixture.migrator(after_commit=crash)
                    migrator.scan_and_apply()
                    armed[0] = True
                    with self.assertRaises(SimulatedHardCrash):
                        migrator.resolve("collision", "thread-b", "collision-b")

                    def fail(stage):
                        if stage == failure_stage:
                            raise RuntimeError(stage.value)

                    with self.assertRaises(RuntimeError):
                        fixture.migrator(after_commit=fail).scan_and_apply()
                    intent_path = fixture.paths.migration_path.with_name(
                        "migration-resolution.json")
                    self.assertTrue(intent_path.exists())

                    repaired = fixture.migrator().scan_and_apply()
                    self.assertTrue(repaired.ready)
                    self.assertEqual(
                        (repaired.imported_count, repaired.deduplicated_count,
                         repaired.conflict_count), (1, 0, 1))
                    self.assertEqual(
                        {item.thread_id: item.outcome for item in repaired.sources},
                        {"thread-a": MigrationOutcome.CONFLICTED,
                         "thread-b": MigrationOutcome.IMPORTED})
                    self.assertFalse(intent_path.exists())
                    registry = SessionRegistry(
                        fixture.paths.registry_path,
                        migration_path=fixture.paths.migration_path)
                    self.assertEqual(
                        registry.resolve_name("collision-b").thread_id,
                        "thread-b")
                    self.assertEqual(
                        CallbackStore(
                            fixture.paths.callback_path,
                            fixture.paths.callback_artifact_dir,
                        ).pending(rejected.session_id)[0].event.worker.name,
                        "collision-b")

    def test_live_status_waits_for_resolve_commit_and_refreshes_registry(self):
        fixture = MigrationFixture(self)
        selected = fixture.record(1, "collision", "thread-a")
        rejected = fixture.record(2, "collision", "thread-b")
        fixture.add_instance("a", [selected])
        fixture.add_instance("b", [rejected])
        commit_started = threading.Event()
        allow_commit = threading.Event()
        status_reached_commit = threading.Event()
        armed = [False]

        def block_after_registry(stage):
            if armed[0] and stage == MigrationCommitStage.REGISTRY:
                if threading.current_thread().name == "live-resolve":
                    commit_started.set()
                    self.assertTrue(allow_commit.wait(5))
                else:
                    status_reached_commit.set()

        migrator = fixture.migrator(after_commit=block_after_registry)
        migrator.scan_and_apply()
        armed[0] = True
        registry = SessionRegistry(
            fixture.paths.registry_path,
            migration_path=fixture.paths.migration_path)
        callbacks = CallbackStore(
            fixture.paths.callback_path,
            fixture.paths.callback_artifact_dir)
        coordinator = LiveMigrationCoordinator(
            migrator,
            SimpleNamespace(
                registry=registry, _gate=ServiceMaintenanceGate()),
            callbacks)
        outcome = []

        resolve_thread = threading.Thread(
            target=lambda: outcome.append(
                coordinator.resolve("collision", "thread-b", "collision-b")),
            name="live-resolve")
        resolve_thread.start()
        self.assertTrue(commit_started.wait(5))
        status_thread = threading.Thread(
            target=lambda: outcome.append(coordinator.scan_and_apply()),
            name="live-status")
        status_thread.start()
        status_committed_while_resolve_drained = status_reached_commit.wait(0.25)
        allow_commit.set()
        resolve_thread.join(5)
        status_thread.join(5)
        self.assertFalse(resolve_thread.is_alive())
        self.assertFalse(status_thread.is_alive())
        self.assertFalse(status_committed_while_resolve_drained)
        self.assertEqual(len(outcome), 2)
        self.assertEqual(registry.resolve_name("collision-b").thread_id, "thread-b")

    def test_live_status_without_recovery_does_not_drain_worker_mutations(self):
        fixture = MigrationFixture(self)
        record = fixture.record(1, "ready")
        fixture.add_instance("ready", [record])
        migrator = fixture.migrator()
        migrator.scan_and_apply()
        registry = SessionRegistry(
            fixture.paths.registry_path,
            migration_path=fixture.paths.migration_path)
        callbacks = CallbackStore(
            fixture.paths.callback_path,
            fixture.paths.callback_artifact_dir)
        gate = ServiceMaintenanceGate()
        coordinator = LiveMigrationCoordinator(
            migrator, SimpleNamespace(registry=registry, _gate=gate), callbacks)
        mutation_started = threading.Event()
        release_mutation = threading.Event()
        status_finished = threading.Event()
        status_outcome = []

        def active_mutation():
            with gate.mutation("thread/start"):
                mutation_started.set()
                self.assertTrue(release_mutation.wait(5))

        def read_status():
            try:
                status_outcome.append(coordinator.scan_and_apply())
            finally:
                status_finished.set()

        mutation = threading.Thread(target=active_mutation)
        mutation.start()
        self.assertTrue(mutation_started.wait(5))
        status = threading.Thread(target=read_status)
        status.start()
        completed_without_drain = status_finished.wait(0.25)
        release_mutation.set()
        mutation.join(5)
        status.join(5)
        self.assertFalse(mutation.is_alive())
        self.assertFalse(status.is_alive())
        self.assertTrue(completed_without_drain)
        self.assertEqual(len(status_outcome), 1)
        self.assertTrue(status_outcome[0].ready)

    def test_resolution_updates_source_outcomes_and_counts(self):
        fixture = MigrationFixture(self)
        first = fixture.record(1, "collision", "thread-a")
        second = fixture.record(2, "collision", "thread-b")
        fixture.add_instance("a", [first])
        fixture.add_instance("b", [second])
        migrator = fixture.migrator()
        migrator.scan_and_apply()

        alternate = migrator.resolve("collision", "thread-b", "collision-b")
        first_status = migrator.scan_and_apply()
        self.assertEqual((first_status.imported_count,
                          first_status.deduplicated_count,
                          first_status.conflict_count), (1, 0, 1))
        self.assertEqual(
            {item.thread_id: item.outcome for item in first_status.sources},
            {"thread-a": MigrationOutcome.CONFLICTED,
             "thread-b": MigrationOutcome.IMPORTED})
        self.assertEqual(
            [candidate.thread_id for candidate in first_status.conflicts[0].candidates],
            [first.thread_id])

        migrator.resolve("collision", first.thread_id, None)
        final_status = migrator.scan_and_apply()
        self.assertEqual((final_status.imported_count,
                          final_status.deduplicated_count,
                          final_status.conflict_count), (2, 0, 0))
        self.assertEqual(
            {item.thread_id: item.outcome for item in final_status.sources},
            {"thread-a": MigrationOutcome.IMPORTED,
             "thread-b": MigrationOutcome.IMPORTED})
        self.assertEqual(alternate.name, "collision-b")

    def test_original_name_resolution_is_immediate_idempotent_and_recovers_ledger_crash(self):
        class SimulatedHardCrash(BaseException):
            pass

        for hard_crash in (False, True):
            with self.subTest(hard_crash=hard_crash):
                fixture = MigrationFixture(self)
                selected = fixture.record(1, "collision", "thread-a")
                rejected = fixture.record(2, "collision", "thread-b")
                fixture.add_instance("a", [selected])
                fixture.add_instance("b", [rejected])
                armed = [False]

                def crash_after_ledger(stage):
                    if armed[0] and stage == MigrationCommitStage.LEDGER:
                        raise SimulatedHardCrash(stage.value)

                migrator = fixture.migrator(after_commit=crash_after_ledger)
                migrator.scan_and_apply()
                armed[0] = hard_crash
                if hard_crash:
                    with self.assertRaises(SimulatedHardCrash):
                        migrator.resolve("collision", selected.thread_id, None)
                    self.assertTrue(fixture.paths.migration_path.with_name(
                        "migration-resolution.json").exists())
                    migrator = fixture.migrator()
                    status = migrator.scan_and_apply()
                else:
                    migrator.resolve("collision", selected.thread_id, None)
                    status = migrator.scan_and_apply()

                self.assertFalse(fixture.paths.migration_path.with_name(
                    "migration-resolution.json").exists())
                self.assertEqual((status.imported_count, status.deduplicated_count,
                                  status.conflict_count), (1, 0, 0))
                self.assertEqual(
                    {item.thread_id: item.outcome for item in status.sources},
                    {"thread-a": MigrationOutcome.IMPORTED,
                     "thread-b": MigrationOutcome.CONFLICTED})
                registry = SessionRegistry(
                    fixture.paths.registry_path,
                    migration_path=fixture.paths.migration_path)
                self.assertEqual(
                    registry.resolve_name("collision").thread_id,
                    selected.thread_id)
                self.assertEqual(
                    migrator.resolve("collision", selected.thread_id, None).thread_id,
                    selected.thread_id)

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
