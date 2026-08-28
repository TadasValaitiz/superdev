import json
import subprocess
import sys
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
        self.assertIn('dependencies = []', text)
        self.assertIn('codex-worker = "codex_worker.cli:main"', text)
        self.assertIn('requires = ["hatchling>=1.27,<2"]', text)
        self.assertIn('build-backend = "hatchling.build"', text)
        self.assertIn('packages = ["codex_worker"]', text)

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
