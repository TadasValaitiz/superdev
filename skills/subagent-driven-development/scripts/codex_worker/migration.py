"""Read-only legacy discovery and ordered, prefix-repairable global migration."""
import copy
import hashlib
import json
import os
import stat
import tempfile
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from .callback_domain import CallbackEvent
from .callback_store import (
    CallbackArtifact,
    CallbackBinding,
    CallbackOutboxEntry,
    CallbackStore,
    CallbackStoreSnapshot,
    UnsafeCallbackStoreError,
)
from .commands import AccessMode, CompletionResponse, Tier, WorkerView, validate_worker_name
from .instance import load_managed_identity
from .models import SessionRecord
from .registry import RegistryError, SessionRegistry
from .service_domain import (
    LegacyCandidate,
    LegacyConflict,
    MigrationOutcome,
    MigrationSourceView,
    MigrationState,
    MigrationStatusView,
    ServicePaths,
)


class MigrationCommitStage(str, Enum):
    ARTIFACTS = "artifacts"
    REGISTRY = "registry"
    CALLBACKS = "callbacks"
    LEDGER = "ledger"


class LegacyMigrationError(RuntimeError):
    def __init__(self, reason: str, path: Optional[Path] = None):
        self.reason = reason
        self.path = None if path is None else Path(path)
        message = reason if path is None else "%s: %s" % (reason, path)
        super().__init__(message)


def _after_commit_noop(stage: MigrationCommitStage) -> None:
    del stage


@dataclass(frozen=True)
class LegacyMigrationDeps:
    paths: ServicePaths
    legacy_instances_dir: Path
    after_commit: Callable[[MigrationCommitStage], None] = field(
        default=_after_commit_noop)
    fsync: Callable[[int], None] = field(default=os.fsync)
    replace: Callable[[str, Path], None] = field(default=os.replace)

    def __post_init__(self) -> None:
        if not isinstance(self.paths, ServicePaths):
            raise ValueError("paths must be ServicePaths")
        if (not isinstance(self.legacy_instances_dir, Path)
                or not self.legacy_instances_dir.is_absolute()):
            raise ValueError("legacy_instances_dir must be an absolute Path")


@dataclass(frozen=True)
class _LegacySource:
    registry_path: Path
    callback_path: Path
    artifact_dir: Path
    digest: str
    records: List[SessionRecord]
    callbacks: CallbackStoreSnapshot


@dataclass(frozen=True)
class _ProjectedEntry:
    entry: CallbackOutboxEntry
    artifact: Optional[Tuple[CallbackArtifact, CompletionResponse]]


@dataclass(frozen=True)
class _MigrationPlan:
    status: MigrationStatusView
    records: List[SessionRecord]
    callbacks: CallbackStoreSnapshot
    artifacts: List[Tuple[CallbackArtifact, CompletionResponse]]


class LegacyMigrator:
    """Plan the complete merge, then commit it in D20's fixed order."""
    LEDGER_VERSION = 1

    def __init__(self, deps: LegacyMigrationDeps):
        if not isinstance(deps, LegacyMigrationDeps):
            raise ValueError("deps must be LegacyMigrationDeps")
        self.deps = deps

    def scan_and_apply(self) -> MigrationStatusView:
        existing = self._read_ledger(optional=True)
        if existing is not None:
            return existing[0]
        try:
            plan = self._plan(self._load_sources())
        except LegacyMigrationError:
            raise
        except (OSError, RegistryError, UnsafeCallbackStoreError, ValueError,
                UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LegacyMigrationError("legacy_prevalidation_failed") from exc
        self._commit(plan, [])
        return plan.status

    def resolve(self, name: str, thread_id: str,
                as_name: Optional[str]) -> SessionRecord:
        validate_worker_name(name)
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("thread_id must be non-empty")
        if as_name is not None:
            validate_worker_name(as_name)
        ledger = self._read_ledger(optional=False)
        status, resolutions = ledger  # type: ignore[misc]
        conflict = next((item for item in status.conflicts if item.name == name), None)
        if conflict is None:
            target_name = as_name or name
            registry = SessionRegistry(self.deps.paths.registry_path,
                                       migration_path=self.deps.paths.migration_path)
            record = registry.resolve_name(target_name)
            if record.thread_id != thread_id:
                raise ValueError("legacy conflict or candidate was not found")
            return record
        candidates = [candidate for candidate in conflict.candidates
                      if candidate.thread_id == thread_id]
        if len(candidates) != 1:
            raise ValueError("legacy conflict thread must identify exactly one candidate")
        candidate = candidates[0]
        sources = self._load_sources()
        source = next((item for item in sources
                       if str(item.registry_path) == candidate.source_path
                       and item.digest == candidate.source_digest), None)
        if source is None:
            raise LegacyMigrationError("legacy_source_changed", Path(candidate.source_path))
        original = next((record for record in source.records
                         if record.session_id == candidate.session_id
                         and record.thread_id == candidate.thread_id), None)
        if original is None:
            raise LegacyMigrationError("legacy_candidate_missing", source.registry_path)
        target_name = as_name or name
        selected = replace(original, name=target_name)
        current_records = self._target_records()
        matches = [record for record in current_records
                   if record.name == target_name or record.session_id == selected.session_id
                   or record.thread_id == selected.thread_id]
        if matches and any(self._record_bytes(record) != self._record_bytes(selected)
                           for record in matches):
            raise ValueError("resolved candidate conflicts with the global registry")
        merged_records = list(current_records)
        if not matches:
            merged_records.append(selected)
        target_callbacks = self._target_callbacks()
        bindings, entries, artifacts = self._callbacks_for_resolution(
            source, original, selected, target_callbacks)
        merged_callbacks = self._merge_callback_snapshots(
            target_callbacks, CallbackStoreSnapshot(bindings, entries), set())
        if as_name is None:
            conflicts = [item for item in status.conflicts if item.name != name]
        else:
            conflicts = list(status.conflicts)
        next_status = MigrationStatusView(
            MigrationState.COMPLETE, True, status.imported_count,
            status.deduplicated_count, len(conflicts), list(status.sources), conflicts)
        resolution = {"name": name, "thread_id": thread_id, "as_name": as_name}
        next_resolutions = list(resolutions)
        if resolution not in next_resolutions:
            next_resolutions.append(resolution)
        plan = _MigrationPlan(next_status, self._sorted_records(merged_records),
                              merged_callbacks, artifacts)
        self._commit(plan, next_resolutions)
        return selected

    def _load_sources(self) -> List[_LegacySource]:
        root = self.deps.legacy_instances_dir
        if not root.exists():
            if root.is_symlink():
                raise LegacyMigrationError("unsafe_legacy_root", root)
            return []
        self._owner_directory(root, allow_non_owner_mode=True)
        children = []
        for child in root.iterdir():
            if child.is_symlink():
                raise LegacyMigrationError("unsafe_legacy_instance", child)
            metadata = os.lstat(child)
            if not stat.S_ISDIR(metadata.st_mode):
                raise LegacyMigrationError("unsafe_legacy_instance", child)
            children.append(Path(os.path.realpath(str(child))))
        sources = []
        for directory in sorted(children, key=str):
            registry_path = directory / "registry.json"
            callback_path = directory / "callbacks.json"
            artifact_dir = directory / "callback-artifacts"
            if load_managed_identity(registry_path) is None:
                raise LegacyMigrationError("unverified_legacy_instance", directory)
            self._owner_regular(registry_path)
            raw = registry_path.read_bytes()
            if not raw:
                raise LegacyMigrationError("empty_legacy_registry", registry_path)
            digest = hashlib.sha256(raw).hexdigest()
            records = SessionRegistry.read_existing(registry_path).list()
            if callback_path.exists() or callback_path.is_symlink():
                callbacks = CallbackStore.read_existing(callback_path, artifact_dir)
            else:
                callbacks = CallbackStoreSnapshot([], [])
            sources.append(_LegacySource(registry_path, callback_path, artifact_dir,
                                         digest, records, callbacks))
        return sources

    def _plan(self, sources: List[_LegacySource]) -> _MigrationPlan:
        candidate_pairs = []
        records_by_session = {}
        records_by_thread = {}
        for source in sources:
            for record in source.records:
                candidate = self._candidate(source, record)
                candidate_pairs.append((candidate, record, source))
                records_by_session.setdefault(record.session_id, []).append(
                    (candidate, record, source))
                records_by_thread.setdefault(record.thread_id, []).append(
                    (candidate, record, source))
        candidate_pairs.sort(key=lambda item: (
            item[0].source_path, item[0].name or "", item[0].session_id,
            item[0].thread_id))

        quarantine = set()
        divergent_names = set()
        by_name = {}
        for candidate, record, source in candidate_pairs:
            del source
            if record.name is not None:
                by_name.setdefault(record.name, []).append((candidate, record))
        for name, items in by_name.items():
            if len({self._record_bytes(record) for _, record in items}) > 1:
                divergent_names.add(name)
                quarantine.update(record.session_id for _, record in items)
        for groups in (records_by_session, records_by_thread):
            for items in groups.values():
                if len({self._record_bytes(record) for _, record, _ in items}) > 1:
                    quarantine.update(record.session_id for _, record, _ in items)

        projected = []
        binding_groups = {}
        event_groups = {}
        for source in sources:
            source_records = {record.session_id: record for record in source.records}
            for binding in source.callbacks.bindings:
                record = source_records.get(binding.session_id)
                if record is None:
                    raise LegacyMigrationError("callback_binding_without_registry_record",
                                               source.callback_path)
                binding_groups.setdefault(binding.session_id, []).append(binding)
            for entry in source.callbacks.outbox:
                record = source_records.get(entry.session_id)
                if record is None:
                    raise LegacyMigrationError("callback_event_without_registry_record",
                                               source.callback_path)
                item = self._project_entry(entry, record, source.artifact_dir)
                projected.append((source, item))
                event_groups.setdefault(entry.event_id, []).append(item.entry)

        for session_id, bindings in binding_groups.items():
            if len({self._canonical(self._binding_dict(binding))
                    for binding in bindings}) > 1:
                quarantine.add(session_id)
        for entries in event_groups.values():
            if len({self._canonical(self._entry_dict(entry)) for entry in entries}) > 1:
                quarantine.update(entry.session_id for entry in entries)

        target_records = self._target_records()
        for candidate, record, source in candidate_pairs:
            del candidate, source
            collisions = [item for item in target_records
                          if item.session_id == record.session_id
                          or item.thread_id == record.thread_id
                          or (record.name is not None and item.name == record.name)]
            if collisions and any(self._record_bytes(item) != self._record_bytes(record)
                                  for item in collisions):
                if record.name is None:
                    raise LegacyMigrationError("unnamed_registry_identifier_conflict")
                quarantine.add(record.session_id)

        target_callbacks = self._target_callbacks()
        target_binding_map = {value.session_id: value for value in target_callbacks.bindings}
        target_event_map = {value.event_id: value for value in target_callbacks.outbox}
        for session_id, bindings in binding_groups.items():
            existing = target_binding_map.get(session_id)
            if existing is not None and any(
                    self._canonical(self._binding_dict(existing)) !=
                    self._canonical(self._binding_dict(value)) for value in bindings):
                quarantine.add(session_id)
        for entries in event_groups.values():
            existing = target_event_map.get(entries[0].event_id)
            if existing is not None and any(
                    self._canonical(self._entry_dict(existing)) !=
                    self._canonical(self._entry_dict(value)) for value in entries):
                quarantine.update(value.session_id for value in entries)

        conflicts = []
        conflict_names = divergent_names | {
            record.name for _, record, _ in candidate_pairs
            if record.session_id in quarantine and record.name is not None}
        if any(record.session_id in quarantine and record.name is None
               for _, record, _ in candidate_pairs):
            raise LegacyMigrationError("unnamed_callback_conflict")
        for name in sorted(conflict_names):
            candidates = sorted(
                [candidate for candidate, record, _ in candidate_pairs
                 if record.name == name],
                key=lambda value: (value.source_path, value.session_id, value.thread_id))
            conflicts.append(LegacyConflict(
                name, candidates,
                sorted({candidate.source_digest for candidate in candidates})))

        selected_sessions = set()
        merged_records = list(target_records)
        source_views = []
        canonical_seen = set()
        for candidate, record, source in candidate_pairs:
            del source
            if record.name in conflict_names or record.session_id in quarantine:
                outcome = MigrationOutcome.CONFLICTED
            else:
                key = self._record_bytes(record)
                if key in canonical_seen:
                    outcome = MigrationOutcome.DEDUPLICATED
                else:
                    outcome = MigrationOutcome.IMPORTED
                    canonical_seen.add(key)
                selected_sessions.add(record.session_id)
                if not any(self._record_bytes(existing) == key
                           for existing in merged_records):
                    merged_records.append(record)
            source_views.append(MigrationSourceView(
                candidate.source_path, candidate.source_digest, candidate.name,
                candidate.session_id, candidate.thread_id, outcome))

        source_bindings = []
        for source in sources:
            source_bindings.extend(binding for binding in source.callbacks.bindings
                                   if binding.session_id in selected_sessions)
        source_entries = [item.entry for _, item in projected
                          if item.entry.session_id in selected_sessions]
        source_snapshot = CallbackStoreSnapshot(
            self._dedup_bindings(source_bindings), self._dedup_entries(source_entries))
        merged_callbacks = self._merge_callback_snapshots(
            target_callbacks, source_snapshot, selected_sessions)
        artifacts = self._dedup_artifacts(
            [item.artifact for _, item in projected
             if item.entry.session_id in selected_sessions and item.artifact is not None])
        self._prevalidate_artifact_targets(artifacts)
        status = MigrationStatusView(
            MigrationState.COMPLETE, True,
            sum(source.outcome == MigrationOutcome.IMPORTED for source in source_views),
            sum(source.outcome == MigrationOutcome.DEDUPLICATED for source in source_views),
            len(conflicts), source_views, conflicts)
        return _MigrationPlan(status, self._sorted_records(merged_records),
                              merged_callbacks, artifacts)

    def _callbacks_for_resolution(
            self, source: _LegacySource, source_record: SessionRecord,
            projected_record: SessionRecord,
            target: CallbackStoreSnapshot,
    ) -> Tuple[List[CallbackBinding], List[CallbackOutboxEntry],
               List[Tuple[CallbackArtifact, CompletionResponse]]]:
        bindings = [binding for binding in source.callbacks.bindings
                    if binding.session_id == source_record.session_id]
        projected = [self._project_entry(entry, source_record, source.artifact_dir,
                                         projected_record)
                     for entry in source.callbacks.outbox
                     if entry.session_id == source_record.session_id]
        snapshot = CallbackStoreSnapshot(bindings, [item.entry for item in projected])
        self._merge_callback_snapshots(target, snapshot, {source_record.session_id})
        artifacts = self._dedup_artifacts(
            [item.artifact for item in projected if item.artifact is not None])
        self._prevalidate_artifact_targets(artifacts)
        return bindings, [item.entry for item in projected], artifacts

    def _project_entry(self, entry: CallbackOutboxEntry, record: SessionRecord,
                       artifact_root: Path,
                       projected_record: Optional[SessionRecord] = None) -> _ProjectedEntry:
        if entry.event is None:
            return _ProjectedEntry(entry, None)
        event = entry.event
        self._validate_event_worker(event.worker, record)
        projection = projected_record or record
        worker = self._worker(projection)
        payload = copy.deepcopy(event.payload)
        artifact_pair = None
        if event.event == "turn_terminal":
            if not isinstance(payload.get("completion"), dict):
                raise LegacyMigrationError("invalid_terminal_completion")
            payload["completion"] = self._project_completion(
                payload["completion"], record, projection).to_dict()
        elif event.event == "turn_terminal_reference":
            reference = payload.get("artifact")
            completion = self._read_legacy_artifact(reference, artifact_root, record,
                                                    projection)
            artifact = self._target_artifact(event.event_id, completion)
            payload["artifact"] = {"path": artifact.path, "sha256": artifact.sha256,
                                   "size_bytes": artifact.size_bytes}
            artifact_pair = (artifact, completion)
        projected_event = CallbackEvent(
            event.schema, event.event, event.event_id, event.emitted_at,
            event.priority, worker, payload)
        projected_entry = CallbackOutboxEntry(
            entry.event_id, entry.session_id, projected_event, entry.state,
            entry.attempt_count, entry.last_error)
        return _ProjectedEntry(projected_entry, artifact_pair)

    def _read_legacy_artifact(self, value: object, artifact_root: Path,
                              record: SessionRecord,
                              projected_record: SessionRecord) -> CompletionResponse:
        if (not isinstance(value, dict)
                or set(value) != {"path", "sha256", "size_bytes"}
                or not isinstance(value["path"], str)
                or not isinstance(value["sha256"], str)
                or type(value["size_bytes"]) is not int):
            raise LegacyMigrationError("invalid_legacy_artifact_reference")
        path = Path(value["path"])
        if not path.is_absolute():
            raise LegacyMigrationError("legacy_artifact_path_not_absolute", path)
        self._owner_directory(artifact_root)
        self._owner_regular(path)
        try:
            canonical_root = artifact_root.resolve(strict=True)
            canonical_path = path.resolve(strict=True)
            canonical_path.relative_to(canonical_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise LegacyMigrationError("legacy_artifact_path_escape", path) from exc
        raw = path.read_bytes()
        if (len(raw) != value["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != value["sha256"]):
            raise LegacyMigrationError("legacy_artifact_digest_or_size_mismatch", path)
        try:
            completion = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LegacyMigrationError("invalid_legacy_artifact_json", path) from exc
        if not isinstance(completion, dict):
            raise LegacyMigrationError("invalid_legacy_artifact_completion", path)
        return self._project_completion(completion, record, projected_record)

    def _project_completion(self, value: dict, record: SessionRecord,
                            projected_record: SessionRecord) -> CompletionResponse:
        copied = copy.deepcopy(value)
        legacy_worker = copied.get("worker")
        if not isinstance(legacy_worker, dict):
            raise LegacyMigrationError("completion_worker_missing")
        try:
            parsed = WorkerView.from_dict(legacy_worker)
        except ValueError as exc:
            raise LegacyMigrationError("completion_worker_invalid") from exc
        self._validate_event_worker(parsed, record)
        copied["worker"] = self._worker(projected_record).to_dict()
        try:
            return CompletionResponse.from_dict(copied)
        except ValueError as exc:
            raise LegacyMigrationError("completion_projection_invalid") from exc

    @staticmethod
    def _validate_event_worker(worker: WorkerView, record: SessionRecord) -> None:
        if (worker.name != record.name or worker.session_id != record.session_id
                or worker.thread_id != record.thread_id or worker.cwd != record.cwd
                or worker.model != record.model or worker.effort != record.effort
                or (None if worker.tier is None else worker.tier.value) != record.tier
                or worker.access.value != record.access):
            raise LegacyMigrationError("callback_worker_does_not_match_registry")

    @staticmethod
    def _worker(record: SessionRecord) -> WorkerView:
        if (record.name is None or record.model is None or record.effort is None
                or record.access is None):
            raise LegacyMigrationError("callback_worker_policy_is_incomplete")
        return WorkerView("global", record.name, record.session_id, record.thread_id,
                          record.cwd, None if record.tier is None else Tier(record.tier),
                          record.model, record.effort, AccessMode(record.access))

    def _target_artifact(self, event_id: str,
                         completion: CompletionResponse) -> CallbackArtifact:
        if (not event_id or any(character not in
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                for character in event_id)):
            raise LegacyMigrationError("unsafe_callback_artifact_event_id")
        payload = self._completion_bytes(completion)
        return CallbackArtifact(
            event_id,
            str(self.deps.paths.callback_artifact_dir / (event_id + ".json")),
            hashlib.sha256(payload).hexdigest(), len(payload))

    def _prevalidate_artifact_targets(
            self, artifacts: Sequence[Tuple[CallbackArtifact, CompletionResponse]]) -> None:
        for artifact, completion in artifacts:
            target = Path(artifact.path)
            if target.exists() or target.is_symlink():
                self._owner_regular(target)
                raw = target.read_bytes()
                expected = self._completion_bytes(completion)
                if raw != expected:
                    raise LegacyMigrationError("global_artifact_collision", target)

    def _commit(self, plan: _MigrationPlan, resolutions: List[dict]) -> None:
        artifact_store = CallbackStore(self.deps.paths.callback_path,
                                       self.deps.paths.callback_artifact_dir)
        for expected, completion in plan.artifacts:
            actual = artifact_store.publish_artifact(expected.event_id, completion)
            if actual != expected:
                raise LegacyMigrationError("global_artifact_publication_mismatch",
                                           Path(expected.path))
        self._sync_existing(self.deps.paths.callback_artifact_dir)
        self.deps.after_commit(MigrationCommitStage.ARTIFACTS)

        SessionRegistry.publish_snapshot(
            self.deps.paths.registry_path, plan.records,
            migration_path=self.deps.paths.migration_path)
        self._sync_existing(self.deps.paths.registry_path)
        self._sync_existing(self.deps.paths.registry_path.parent)
        self.deps.after_commit(MigrationCommitStage.REGISTRY)

        CallbackStore(self.deps.paths.callback_path,
                      self.deps.paths.callback_artifact_dir).replace_snapshot(plan.callbacks)
        self._sync_existing(self.deps.paths.callback_path)
        self._sync_existing(self.deps.paths.callback_path.parent)
        self.deps.after_commit(MigrationCommitStage.CALLBACKS)

        self._write_ledger(plan.status, resolutions)
        self.deps.after_commit(MigrationCommitStage.LEDGER)

    def _read_ledger(self, optional: bool) -> Optional[Tuple[MigrationStatusView, List[dict]]]:
        path = self.deps.paths.migration_path
        if not path.exists():
            if path.is_symlink():
                raise LegacyMigrationError("unsafe_migration_ledger", path)
            if optional:
                return None
            raise LegacyMigrationError("migration_ledger_missing", path)
        self._owner_regular(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (not isinstance(payload, dict)
                    or set(payload) != {"version", "status", "resolutions"}
                    or payload["version"] != self.LEDGER_VERSION
                    or not isinstance(payload["resolutions"], list)):
                raise ValueError("invalid migration ledger")
            resolutions = payload["resolutions"]
            for value in resolutions:
                if (not isinstance(value, dict)
                        or set(value) != {"name", "thread_id", "as_name"}
                        or not isinstance(value["name"], str)
                        or not isinstance(value["thread_id"], str)
                        or value["as_name"] is not None
                        and not isinstance(value["as_name"], str)):
                    raise ValueError("invalid migration resolution")
            return MigrationStatusView.from_dict(payload["status"]), list(resolutions)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LegacyMigrationError("invalid_migration_ledger", path) from exc

    def _write_ledger(self, status: MigrationStatusView,
                      resolutions: List[dict]) -> None:
        path = self.deps.paths.migration_path
        self._mkdir_owner(path.parent)
        if path.exists() or path.is_symlink():
            self._owner_regular(path)
        payload = json.dumps(
            {"version": self.LEDGER_VERSION, "status": status.to_dict(),
             "resolutions": resolutions},
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8") + b"\n"
        descriptor, temporary = tempfile.mkstemp(prefix="migration.", dir=str(path.parent))
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                self.deps.fsync(handle.fileno())
            self.deps.replace(temporary, path)
            self._owner_regular(path)
            self._sync_existing(path.parent)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def _target_records(self) -> List[SessionRecord]:
        path = self.deps.paths.registry_path
        if not path.exists():
            if path.is_symlink():
                raise LegacyMigrationError("unsafe_global_registry", path)
            return []
        return SessionRegistry.read_existing(path).list()

    def _target_callbacks(self) -> CallbackStoreSnapshot:
        path = self.deps.paths.callback_path
        if not path.exists():
            if path.is_symlink():
                raise LegacyMigrationError("unsafe_global_callback_store", path)
            return CallbackStoreSnapshot([], [])
        return CallbackStore.read_existing(
            path, self.deps.paths.callback_artifact_dir)

    def _merge_callback_snapshots(
            self, target: CallbackStoreSnapshot, source: CallbackStoreSnapshot,
            selected_sessions: set) -> CallbackStoreSnapshot:
        bindings = {value.session_id: value for value in target.bindings}
        for value in source.bindings:
            existing = bindings.get(value.session_id)
            if existing is not None and existing != value:
                raise LegacyMigrationError("global_callback_binding_collision")
            bindings[value.session_id] = value
        outbox = {value.event_id: value for value in target.outbox}
        for value in source.outbox:
            if selected_sessions and value.session_id not in selected_sessions:
                continue
            existing = outbox.get(value.event_id)
            if existing is not None and existing != value:
                raise LegacyMigrationError("global_callback_event_collision")
            outbox[value.event_id] = value
        return CallbackStoreSnapshot(
            [bindings[key] for key in sorted(bindings)],
            [outbox[key] for key in sorted(outbox)])

    @classmethod
    def _dedup_bindings(cls, values: Sequence[CallbackBinding]) -> List[CallbackBinding]:
        result = {}
        for value in values:
            existing = result.get(value.session_id)
            if existing is not None and existing != value:
                raise LegacyMigrationError("callback_binding_conflict_after_planning")
            result[value.session_id] = value
        return [result[key] for key in sorted(result)]

    @classmethod
    def _dedup_entries(cls, values: Sequence[CallbackOutboxEntry]) -> List[CallbackOutboxEntry]:
        result = {}
        for value in values:
            existing = result.get(value.event_id)
            if existing is not None and existing != value:
                raise LegacyMigrationError("callback_event_conflict_after_planning")
            result[value.event_id] = value
        return [result[key] for key in sorted(result)]

    @classmethod
    def _dedup_artifacts(
            cls, values: Sequence[Tuple[CallbackArtifact, CompletionResponse]],
    ) -> List[Tuple[CallbackArtifact, CompletionResponse]]:
        result = {}
        for artifact, completion in values:
            existing = result.get(artifact.event_id)
            if existing is not None and existing != (artifact, completion):
                raise LegacyMigrationError("callback_artifact_conflict_after_planning")
            result[artifact.event_id] = (artifact, completion)
        return [result[key] for key in sorted(result)]

    @staticmethod
    def _candidate(source: _LegacySource, record: SessionRecord) -> LegacyCandidate:
        return LegacyCandidate(
            str(source.registry_path), source.digest, record.name,
            record.session_id, record.thread_id, record.cwd, record.created_at,
            record.updated_at, record.model, record.effort, record.tier,
            record.access)

    @staticmethod
    def _record_bytes(record: SessionRecord) -> bytes:
        return LegacyMigrator._canonical(record.to_dict())

    @staticmethod
    def _canonical(value: object) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")

    @staticmethod
    def _completion_bytes(completion: CompletionResponse) -> bytes:
        return LegacyMigrator._canonical(completion.to_dict()) + b"\n"

    @staticmethod
    def _binding_dict(value: CallbackBinding) -> dict:
        return CallbackStore._binding_dict(value)

    @staticmethod
    def _entry_dict(value: CallbackOutboxEntry) -> dict:
        return CallbackStore._entry_dict(value)

    @staticmethod
    def _sorted_records(records: Sequence[SessionRecord]) -> List[SessionRecord]:
        return sorted(records, key=lambda value: (
            value.name or "", value.session_id, value.thread_id))

    @staticmethod
    def _owner_regular(path: Path) -> None:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise LegacyMigrationError("unsafe_legacy_file", path) from exc
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600):
            raise LegacyMigrationError("unsafe_legacy_file", path)

    @staticmethod
    def _owner_directory(path: Path, allow_non_owner_mode: bool = False) -> None:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise LegacyMigrationError("unsafe_legacy_directory", path) from exc
        mode = stat.S_IMODE(metadata.st_mode)
        safe_mode = mode == 0o700 if not allow_non_owner_mode else not bool(mode & 0o022)
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid()
                or not safe_mode):
            raise LegacyMigrationError("unsafe_legacy_directory", path)

    @staticmethod
    def _mkdir_owner(path: Path) -> None:
        if path.exists() or path.is_symlink():
            LegacyMigrator._owner_directory(path)
            return
        if not path.parent.exists():
            LegacyMigrator._mkdir_owner(path.parent)
        os.mkdir(str(path), 0o700)
        LegacyMigrator._owner_directory(path)

    def _sync_existing(self, path: Path) -> None:
        if not path.exists():
            return
        flags = os.O_RDONLY
        if path.is_dir():
            flags |= getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(str(path), flags)
        try:
            self.deps.fsync(descriptor)
        finally:
            os.close(descriptor)
