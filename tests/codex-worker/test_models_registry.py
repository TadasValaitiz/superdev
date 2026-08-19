import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.models import (
    IdentifierSelector,
    RpcFault,
    rpc_response,
)
from codex_worker.registry import (
    RegistryConflict,
    SessionRegistry,
)


class ModelTests(unittest.TestCase):
    def test_identifier_selector_requires_exactly_one_namespace(self):
        with self.assertRaises(ValueError):
            IdentifierSelector()
        with self.assertRaises(ValueError):
            IdentifierSelector(session_id="a", thread_id="b")
        self.assertEqual(IdentifierSelector(session_id="a").kind, "session")

    def test_rpc_error_response_supports_null_id(self):
        response = rpc_response(None, fault=RpcFault(-32700, "Parse error", "parse_error"))
        self.assertIsNone(response["id"])
        self.assertIn("error", response)
        self.assertNotIn("result", response)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = self.tempdir.name
        self.state_path = Path(self.cwd) / "state" / "sessions.json"

    def tearDown(self):
        self.tempdir.cleanup()

    def write_v1_record(self, name):
        self.state_path.parent.mkdir(exist_ok=True)
        self.state_path.write_text(json.dumps({"schema_version": 1, "sessions": [{
            "session_id": "12345678-1234-5678-1234-567812345678", "thread_id": "thr-1",
            "cwd": self.cwd, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
            "name": name, "model": "legacy-model", "effort": "medium",
        }]}))

    def test_missing_and_zero_byte_registry_initialize_v2_owner_only(self):
        for seed in (None, b""):
            path = Path(self.cwd) / ("state-%s.json" % ("missing" if seed is None else "empty"))
            if seed is not None:
                path.write_bytes(seed)
            registry = SessionRegistry(path)
            self.assertEqual(registry.list(), [])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 2)

    def test_v1_records_load_without_loss_and_upgrade_on_next_write(self):
        self.write_v1_record(name="legacy")
        registry = SessionRegistry(self.state_path)
        legacy = registry.resolve_name("legacy")
        self.assertIsNone(legacy.tier)
        self.assertIsNone(legacy.access)
        self.assertFalse(legacy.common_policy_complete)
        registry.create_worker("thr-2", self.cwd, "new-a31", "medium", "gpt-5.6-terra", "medium", "full")
        payload = json.loads(self.state_path.read_text())
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["sessions"][0]["model"], "legacy-model")

    def test_registry_rejects_duplicate_thread_ids(self):
        registry = SessionRegistry(self.state_path)
        first = registry.create("thr-1", self.cwd, "one", None, None)
        with self.assertRaises(RegistryConflict):
            registry.create("thr-1", self.cwd, "two", None, None)
        self.assertEqual(registry.resolve(IdentifierSelector(session_id=first.session_id)), first)

    def test_failed_replace_preserves_previous_snapshot(self):
        registry = SessionRegistry(self.state_path)
        record = registry.create("thr-1", self.cwd, None, None, None)
        with mock.patch("os.replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                registry.update_annotations(record.session_id, model="changed")
        restored = SessionRegistry(self.state_path)
        self.assertIsNone(restored.resolve(IdentifierSelector(session_id=record.session_id)).model)

    def test_snapshot_syncs_file_then_replacement_directory(self):
        events = []
        SessionRegistry(self.state_path)

        class RecordingFile:
            def __init__(self, fd):
                self.fd = fd
                self.wrote = False

            def write(self, value):
                if not self.wrote:
                    events.append("temp-write")
                    self.wrote = True
                return len(value)

            def flush(self):
                events.append("temp-flush")

            def fileno(self):
                return self.fd

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                events.append("temp-close")

        temp_fd = 101
        directory_fd = 102
        temp_name = str(self.state_path.parent / "sessions.json.tmp")

        def fsync(fd):
            events.append("file-fsync" if fd == temp_fd else "directory-fsync")

        def replace(source, target):
            self.assertEqual(source, temp_name)
            self.assertEqual(target, str(self.state_path))
            events.append("replace")

        def open_directory(path, flags):
            self.assertEqual(path, str(self.state_path.parent))
            self.assertEqual(flags, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            events.append("directory-open")
            return directory_fd

        def close(fd):
            self.assertEqual(fd, directory_fd)
            events.append("directory-close")

        with mock.patch("codex_worker.registry.tempfile.mkstemp", return_value=(temp_fd, temp_name)), \
             mock.patch("codex_worker.registry.os.fchmod"), \
             mock.patch("codex_worker.registry.os.fdopen", return_value=RecordingFile(temp_fd)), \
             mock.patch("codex_worker.registry.os.fsync", side_effect=fsync), \
             mock.patch("codex_worker.registry.os.replace", side_effect=replace), \
             mock.patch("codex_worker.registry.os.open", side_effect=open_directory), \
             mock.patch("codex_worker.registry.os.close", side_effect=close):
            SessionRegistry(self.state_path).create("thr-1", self.cwd, None, None, None)

        self.assertEqual(events, [
            "temp-write", "temp-flush", "file-fsync", "temp-close",
            "replace", "directory-open", "directory-fsync", "directory-close",
        ])

    def test_directory_sync_failure_closes_descriptor(self):
        events = []

        class RecordingFile:
            def write(self, value):
                events.append("temp-write")
                return len(value)

            def flush(self):
                events.append("temp-flush")

            def fileno(self):
                return 101

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                events.append("temp-close")

        temp_name = str(self.state_path.parent / "sessions.json.tmp")

        def fsync(fd):
            events.append("file-fsync" if fd == 101 else "directory-fsync")
            if fd == 102:
                raise OSError("directory sync failed")

        with mock.patch("codex_worker.registry.tempfile.mkstemp", return_value=(101, temp_name)), \
             mock.patch("codex_worker.registry.os.fchmod"), \
             mock.patch("codex_worker.registry.os.fdopen", return_value=RecordingFile()), \
             mock.patch("codex_worker.registry.os.fsync", side_effect=fsync), \
             mock.patch("codex_worker.registry.os.replace", side_effect=lambda *_: events.append("replace")), \
             mock.patch("codex_worker.registry.os.open", side_effect=lambda *_: events.append("directory-open") or 102), \
             mock.patch("codex_worker.registry.os.close", side_effect=lambda fd: events.append("directory-close")):
            with self.assertRaisesRegex(OSError, "directory sync failed"):
                SessionRegistry(self.state_path).create("thr-1", self.cwd, None, None, None)

        self.assertEqual(events[-2:], ["directory-fsync", "directory-close"])

    def test_snapshot_is_schema_versioned_and_owner_only(self):
        record = SessionRegistry(self.state_path).create("thr-1", self.cwd, None, "m", "e")
        payload = json.loads(self.state_path.read_text())
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["sessions"][0]["session_id"], record.session_id)
        self.assertEqual(os.stat(self.state_path).st_mode & 0o777, 0o600)

    def test_load_rejects_corrupt_or_wrong_schema(self):
        self.state_path.parent.mkdir()
        self.state_path.write_text("not json")
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path)

    def test_create_canonicalizes_cwd_and_rejects_bad_inputs(self):
        real = Path(self.cwd) / "real"
        real.mkdir()
        link = Path(self.cwd) / "link"
        link.symlink_to(real, target_is_directory=True)
        record = SessionRegistry(self.state_path).create("thr-1", str(link), None, None, None)
        self.assertEqual(record.cwd, str(real.resolve()))
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path).create("thr-2", self.cwd, None, 1, None)
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path).create("thr-3", self.cwd, None, None, None, session_id="")

    def test_snapshot_rejects_bool_version_and_unknown_fields(self):
        self.state_path.parent.mkdir()
        for payload in ({"schema_version": True, "sessions": []},
                        {"schema_version": 1, "sessions": [], "extra": 1}):
            self.state_path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                SessionRegistry(self.state_path)

    def test_existing_world_readable_state_is_hardened(self):
        registry = SessionRegistry(self.state_path)
        registry.create("thr-1", self.cwd, None, None, None)
        os.chmod(self.state_path, 0o644)
        SessionRegistry(self.state_path)
        self.assertEqual(os.stat(self.state_path).st_mode & 0o777, 0o600)

    def test_state_path_symlink_is_rejected(self):
        self.state_path.parent.mkdir()
        target = self.state_path.parent / "real.json"
        target.write_text(json.dumps({"schema_version": 2, "sessions": []}))
        self.state_path.symlink_to(target)
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path)

    def test_foreign_owner_state_is_rejected_when_testable(self):
        if os.getuid() == 0:
            self.skipTest("root cannot exercise foreign-owner behavior")
        self.state_path.parent.mkdir()
        self.state_path.write_text(json.dumps({"schema_version": 1, "sessions": []}))
        try:
            os.chown(self.state_path, os.getuid() + 1, os.getgid())
        except PermissionError:
            self.skipTest("cannot alter owner on this host")
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path)
        self.state_path.write_text(json.dumps({"schema_version": 2, "sessions": []}))
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path)


if __name__ == "__main__":
    unittest.main()
