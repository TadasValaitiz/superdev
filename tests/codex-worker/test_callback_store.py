import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.callback_store import (CallbackBinding, CallbackEvent, CallbackOutboxState,
                                         CallbackStore, CallbackStoreDeps, UnsafeCallbackStoreError)
from codex_worker.commands import (AccessMode, CallbackState, CompletionResponse,
                                   CompletionSelection, MetricAvailability, MetricEvidence,
                                   RecoveryView, Tier, TurnView, WorkerView)


class CallbackStoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.path = root / "callbacks.json"
        self.artifacts = root / "callback-artifacts"
        self.store = CallbackStore(self.path, self.artifacts)
        self.worker = WorkerView("scope", "worker", "12345678-1234-5678-1234-567812345678",
                                 "thread", str(root), Tier.MEDIUM, "model", "medium", AccessMode.FULL)

    def binding(self, state=CallbackState.ENABLED):
        full = state == CallbackState.ENABLED
        return CallbackBinding(self.worker.session_id, state,
            "/tmp/socket" if full else None, "a" * 32 if full else None,
            "claude-session" if full else None, 123 if full else None,
            "start" if full else None, str(self.tempdir.name), "2026-08-20T00:00:00Z")

    def event(self, event_id="event-1"):
        return CallbackEvent("codex-worker.claude-callback/v1", "turn_terminal", event_id,
                             "2026-08-20T00:00:00Z", "next", self.worker,
                             {"completion": {"turn": {"turn_id": "turn"}}})

    def completion(self):
        return CompletionResponse(self.worker, TurnView("turn", "completed", None), [], None,
            {"wall_time_ms": MetricEvidence(1, "test", MetricAvailability.MEASURED)},
            RecoveryView("status", "messages", "interrupt"))

    def test_initializes_missing_and_zero_byte_state_with_owner_only_modes(self):
        self.assertIsNone(self.store.binding(self.worker.session_id))
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.artifacts).st_mode), 0o700)
        self.path.write_bytes(b"")
        os.chmod(self.path, 0o600)
        self.assertIsNone(CallbackStore(self.path, self.artifacts).binding(self.worker.session_id))

    def test_binding_and_multiple_pending_events_survive_restart(self):
        self.store.bind(self.binding())
        self.store.enqueue_terminal(self.worker.session_id, self.event("event-1"))
        self.store.enqueue_terminal(self.worker.session_id, self.event("event-2"))
        reloaded = CallbackStore(self.path, self.artifacts)
        self.assertEqual(reloaded.binding(self.worker.session_id).state, CallbackState.ENABLED)
        self.assertEqual([entry.event_id for entry in reloaded.pending(self.worker.session_id)], ["event-1", "event-2"])

    def test_disabled_binding_rejects_even_a_resolver_root(self):
        with self.assertRaises(ValueError):
            self.binding(CallbackState.DISABLED)

    def test_full_root_only_and_disabled_bindings_round_trip(self):
        root = str(self.tempdir.name)
        unavailable = CallbackBinding("session-unavailable", CallbackState.UNAVAILABLE,
            None, None, None, None, None, root, "2026-08-20T00:00:00Z")
        disabled = CallbackBinding("session-disabled", CallbackState.DISABLED,
            None, None, None, None, None, None, "2026-08-20T00:00:00Z")
        enabled = self.binding()
        for binding in (enabled, unavailable, disabled):
            self.store.bind(binding)
        reloaded = CallbackStore(self.path, self.artifacts)
        self.assertEqual(reloaded.binding(enabled.session_id), enabled)
        self.assertEqual(reloaded.binding(unavailable.session_id), unavailable)
        self.assertEqual(reloaded.binding(disabled.session_id), disabled)

    def test_failed_attempt_keeps_complete_pending_event_and_written_never_replays(self):
        self.store.bind(self.binding())
        self.store.enqueue_terminal(self.worker.session_id, self.event())
        failed = self.store.record_failed("event-1", "socket refused", "2026-08-20T00:01:00Z")
        self.assertEqual((failed.state, failed.attempt_count, failed.event.event_id),
                         (CallbackOutboxState.PENDING, 1, "event-1"))
        self.assertEqual(self.store.status_view(self.worker.session_id).last_terminal_attempt.turn_id,
                         "turn")
        self.store.record_written("event-1", "2026-08-20T00:02:00Z")
        self.assertEqual(self.store.status_view(self.worker.session_id).last_terminal_attempt.turn_id,
                         "turn")
        self.assertEqual(self.store.pending(self.worker.session_id), [])
        self.assertEqual(self.store.enqueue_terminal(self.worker.session_id, self.event()), None)

    def test_malformed_nonempty_state_and_unsafe_modes_are_refused_without_reset(self):
        self.path.parent.mkdir(mode=0o700, exist_ok=True)
        self.path.write_text("not json")
        os.chmod(self.path, 0o600)
        with self.assertRaises(ValueError):
            CallbackStore(self.path, self.artifacts).binding(self.worker.session_id)
        self.assertEqual(self.path.read_text(), "not json")
        self.path.write_text('{"version":1,"bindings":{},"outbox":{}}\n')
        os.chmod(self.path, 0o644)
        with self.assertRaises(UnsafeCallbackStoreError):
            CallbackStore(self.path, self.artifacts).binding(self.worker.session_id)

    def test_injected_stat_refuses_foreign_callback_file_without_replacing_it(self):
        self.store.binding(self.worker.session_id)
        original = self.path.read_bytes()
        foreign = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=os.getuid() + 1)
        deps = CallbackStoreDeps(lstat=lambda path: foreign if Path(path) == self.path else os.lstat(path))
        with self.assertRaises(UnsafeCallbackStoreError):
            CallbackStore(self.path, self.artifacts, deps).bind(self.binding())
        self.assertEqual(self.path.read_bytes(), original)

    def test_atomic_state_write_fsyncs_before_replace_and_parent_after(self):
        self.store.bind(self.binding())
        order = []
        def fsync(fd):
            order.append("fsync")
            os.fsync(fd)
        def replace(source, target):
            order.append("replace")
            os.replace(source, target)
        store = CallbackStore(self.path, self.artifacts, CallbackStoreDeps(fsync=fsync, replace=replace))
        store.enqueue_terminal(self.worker.session_id, self.event())
        self.assertEqual(order, ["fsync", "replace", "fsync"])

    def test_artifact_is_canonical_immutable_and_insert_or_verify(self):
        artifact = self.store.publish_artifact("event-1", self.completion())
        expected = json.dumps(self.completion().to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        self.assertEqual(Path(artifact.path).read_bytes(), expected)
        self.assertEqual((artifact.sha256, artifact.size_bytes), (hashlib.sha256(expected).hexdigest(), len(expected)))
        self.assertEqual(stat.S_IMODE(os.stat(artifact.path).st_mode), 0o600)
        self.assertEqual(self.store.publish_artifact("event-1", self.completion()), artifact)
        with self.assertRaises(ValueError):
            self.store.publish_artifact("event-1", CompletionResponse(self.worker, TurnView("turn", "failed", None), [], None, {}, RecoveryView("status", "messages", "interrupt")))

    def test_artifact_race_preserves_different_target_created_at_publication(self):
        target = self.artifacts / "event-1.json"
        foreign = b'{"foreign":true}\n'
        def racing_link(source, destination):
            Path(destination).write_bytes(foreign)
            os.chmod(destination, 0o600)
            return os.link(source, destination)
        store = CallbackStore(self.path, self.artifacts, CallbackStoreDeps(link=racing_link))
        with self.assertRaises(ValueError):
            store.publish_artifact("event-1", self.completion())
        self.assertEqual(target.read_bytes(), foreign)
        self.assertEqual(list(self.artifacts.glob("artifact.*")), [])
