import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills" / "subagent-driven-development" / "scripts"
PYPROJECT = SCRIPTS / "pyproject.toml"
SOURCE_LAUNCHER = SCRIPTS / "codex-worker"
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
VERSION_CONFIG = ROOT / ".version-bump.json"


def read_declared_version(entry):
    path = ROOT / entry["path"]
    if entry.get("format", "json") == "toml":
        in_project = False
        matches = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_project = stripped == "[project]"
            elif in_project and stripped.startswith("version"):
                key, separator, value = stripped.partition("=")
                if key.strip() == "version" and separator:
                    matches.append(value.strip().strip('"'))
        if len(matches) != 1:
            raise AssertionError("expected one [project] version in %s" % path)
        return matches[0]

    value = json.loads(path.read_text(encoding="utf-8"))
    for part in entry["field"].split("."):
        value = value[int(part)] if part.isdigit() else value[part]
    return value


class ToolPackageTests(unittest.TestCase):
    def test_pyproject_declares_isolated_console_tool(self):
        text = PYPROJECT.read_text(encoding="utf-8")
        self.assertIn('name = "codex-worker"', text)
        self.assertIn('requires-python = ">=3.9"', text)
        self.assertIn('dependencies = ["websockets>=15,<16"]', text)
        self.assertIn('codex-worker = "codex_worker.cli:main"', text)
        self.assertIn('requires = ["hatchling>=1.27,<2"]', text)
        self.assertIn('build-backend = "hatchling.build"', text)
        self.assertIn('packages = ["codex_worker"]', text)

    def test_websocket_modules_import_without_eager_dependency_resolution(self):
        completed = subprocess.run(
            [sys.executable, "-c", (
                "import codex_worker.websocket_transport; "
                "import codex_worker.websocket_gateway; "
                "import codex_worker.service"
            )],
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(SCRIPTS)},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")

    def test_source_cli_version_matches_plugin_manifest(self):
        expected = json.loads(CLAUDE_MANIFEST.read_text(encoding="utf-8"))["version"]
        completed = subprocess.run(
            [sys.executable, str(SOURCE_LAUNCHER), "--version"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "codex-worker %s\n" % expected)
        self.assertEqual(completed.stderr, "")

    def test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata(self):
        expected = json.loads(CLAUDE_MANIFEST.read_text(encoding="utf-8"))["version"]
        with tempfile.TemporaryDirectory() as temporary:
            dist_info = Path(temporary) / "codex_worker-99.0.0.dist-info"
            dist_info.mkdir()
            (dist_info / "METADATA").write_text(
                "Metadata-Version: 2.1\nName: codex-worker\nVersion: 99.0.0\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = temporary + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [sys.executable, str(SOURCE_LAUNCHER), "--version"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "codex-worker %s\n" % expected)
        self.assertEqual(completed.stderr, "")

    def test_all_declared_versions_match_plugin_manifest(self):
        config = json.loads(VERSION_CONFIG.read_text(encoding="utf-8"))
        expected = json.loads(CLAUDE_MANIFEST.read_text(encoding="utf-8"))["version"]
        declared = {entry["path"]: read_declared_version(entry) for entry in config["files"]}
        self.assertEqual(declared, {path: expected for path in declared})
        self.assertIn(
            "skills/subagent-driven-development/scripts/pyproject.toml",
            declared,
        )


if __name__ == "__main__":
    unittest.main()
