import json
import os
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

    def test_snapshot_is_schema_versioned_and_owner_only(self):
        record = SessionRegistry(self.state_path).create("thr-1", self.cwd, None, "m", "e")
        payload = json.loads(self.state_path.read_text())
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["sessions"][0]["session_id"], record.session_id)
        self.assertEqual(os.stat(self.state_path).st_mode & 0o777, 0o600)

    def test_load_rejects_corrupt_or_wrong_schema(self):
        self.state_path.parent.mkdir()
        self.state_path.write_text("not json")
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path)
        self.state_path.write_text(json.dumps({"schema_version": 2, "sessions": []}))
        with self.assertRaises(ValueError):
            SessionRegistry(self.state_path)


if __name__ == "__main__":
    unittest.main()
