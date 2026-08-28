import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_INSTALLER = (
    ROOT / "skills" / "subagent-driven-development" / "scripts" / "install-codex-worker"
)
SOURCE_PACKAGE = ROOT / "skills" / "subagent-driven-development" / "scripts"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ToolPreflightTests(unittest.TestCase):
    expected_version = "7.9.0"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plugin = self.root / "plugin"
        self._write_plugin(self.plugin)
        self.installer = (
            self.plugin
            / "skills"
            / "subagent-driven-development"
            / "scripts"
            / "install-codex-worker"
        )
        if SOURCE_INSTALLER.exists():
            shutil.copy2(SOURCE_INSTALLER, self.installer)

        self.fake_bin = self.root / "fake-bin"
        self.fake_bin.mkdir()
        self.uv_bin = self.root / "uv-bin"
        self.uv_bin.mkdir()
        self.uv_log = self.root / "uv.log"
        self._write_fake_uv()

        self.home = self.root / "home"
        self.home.mkdir()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.state = self.root / "state"
        self.base_env = os.environ.copy()
        self.base_env.update({
            "HOME": str(self.home),
            "TMPDIR": str(self.runtime),
            "XDG_STATE_HOME": str(self.state),
            "UV_TOOL_DIR": str(self.root / "uv-tools"),
            "UV_TOOL_BIN_DIR": str(self.uv_bin),
            "UV_CACHE_DIR": str(self.root / "uv-cache"),
            "FAKE_UV_BIN": str(self.uv_bin),
            "FAKE_UV_LOG": str(self.uv_log),
            "FAKE_UV_INSTALL_VERSION": self.expected_version,
        })
        self.base_env.pop("CLAUDE_PLUGIN_ROOT", None)

    def _write_plugin(self, root, manifest_version=None, package_version=None):
        manifest_version = manifest_version or self.expected_version
        package_version = package_version or self.expected_version
        scripts = root / "skills" / "subagent-driven-development" / "scripts"
        scripts.mkdir(parents=True)
        (scripts.parent / "SKILL.md").write_text("# Loaded fixture skill\n", encoding="utf-8")
        (scripts / "pyproject.toml").write_text(
            "[project]\n"
            "name = \"codex-worker\"\n"
            "version = \"%s\"\n" % package_version,
            encoding="utf-8",
        )
        manifest = root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(
            json.dumps({"name": "superdev", "version": manifest_version}) + "\n",
            encoding="utf-8",
        )

    def _write_fake_uv(self):
        uv = self.fake_bin / "uv"
        uv.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$FAKE_UV_LOG\"\n"
            "if [ \"$1 $2 $3\" = \"tool dir --bin\" ]; then\n"
            "  printf '%s\\n' \"$FAKE_UV_BIN\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1 $2\" = \"tool install\" ]; then\n"
            "  if [ -n \"${FAKE_UV_FAIL_CODE:-}\" ]; then\n"
            "    echo 'fake install stdout'\n"
            "    echo 'fake install stderr' >&2\n"
            "    exit \"$FAKE_UV_FAIL_CODE\"\n"
            "  fi\n"
            "  temporary=\"$FAKE_UV_BIN/codex-worker.new\"\n"
            "  cat > \"$temporary\" <<EOF\n"
            "#!/bin/sh\n"
            "if [ \"\\$1\" = \"--version\" ]; then\n"
            "  printf 'codex-worker %s\\n' '$FAKE_UV_INSTALL_VERSION'\n"
            "  exit 0\n"
            "fi\n"
            "exit 64\n"
            "EOF\n"
            "  chmod +x \"$temporary\"\n"
            "  mv \"$temporary\" \"$FAKE_UV_BIN/codex-worker\"\n"
            "  exit 0\n"
            "fi\n"
            "echo \"unexpected fake uv invocation: $*\" >&2\n"
            "exit 97\n",
            encoding="utf-8",
        )
        uv.chmod(0o755)

    def _write_worker(self, directory, version, name="codex-worker"):
        worker = directory / name
        worker.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"--version\" ]; then\n"
            "  printf 'codex-worker %s\\n'\n"
            "  exit 0\n"
            "fi\n"
            "exit 64\n" % version,
            encoding="utf-8",
        )
        worker.chmod(0o755)
        return worker

    def env(self, path_parts=None, **updates):
        env = self.base_env.copy()
        env.update({key: str(value) for key, value in updates.items()})
        parts = path_parts or [self.fake_bin, self.uv_bin, Path("/usr/bin"), Path("/bin")]
        env["PATH"] = os.pathsep.join(str(part) for part in parts)
        return env

    def run_preflight(self, env=None):
        return subprocess.run(
            [str(self.installer)],
            cwd=self.root,
            env=env or self.env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def install_calls(self):
        if not self.uv_log.exists():
            return []
        return [
            line
            for line in self.uv_log.read_text(encoding="utf-8").splitlines()
            if line.startswith("tool install ")
        ]

    def assert_ready(self, completed):
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "codex-worker ready: %s (%s)\n" % (
                (self.uv_bin / "codex-worker").resolve(),
                self.expected_version,
            ),
        )
        self.assertEqual(completed.stderr, "")

    def test_installer_is_executable(self):
        self.assertTrue(self.installer.is_file())
        self.assertTrue(os.access(self.installer, os.X_OK))

    def test_absent_command_installs_once_non_editably_from_canonical_package(self):
        completed = self.run_preflight()
        self.assert_ready(completed)
        expected_package = (
            self.plugin / "skills" / "subagent-driven-development" / "scripts"
        ).resolve()
        self.assertEqual(
            self.install_calls(),
            ["tool install --reinstall %s" % expected_package],
        )
        self.assertNotIn("--editable", self.uv_log.read_text(encoding="utf-8"))
        version = subprocess.run(
            [str(self.uv_bin / "codex-worker"), "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(version.stdout, "codex-worker %s\n" % self.expected_version)

    def test_matching_uv_command_is_stable_and_idempotent(self):
        self._write_worker(self.uv_bin, self.expected_version)
        first = self.run_preflight()
        second = self.run_preflight()
        self.assert_ready(first)
        self.assert_ready(second)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(self.install_calls(), [])
        self.assertFalse(self.state.exists())
        self.assertEqual(list(self.root.rglob("*.sock")), [])
        self.assertEqual(list(self.root.rglob("sessions.json")), [])

    def test_older_and_newer_uv_commands_are_reinstalled_to_exact_version(self):
        for installed_version in ("7.8.9", "8.0.0"):
            with self.subTest(installed_version=installed_version):
                self.uv_log.unlink(missing_ok=True)
                self._write_worker(self.uv_bin, installed_version)
                completed = self.run_preflight()
                self.assert_ready(completed)
                self.assertEqual(len(self.install_calls()), 1)
                probe = subprocess.run(
                    [str(self.uv_bin / "codex-worker"), "--version"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(probe.stdout, "codex-worker %s\n" % self.expected_version)

    def test_foreign_shadow_refuses_without_install_or_mutation(self):
        shadow_bin = self.root / "shadow-bin"
        shadow_bin.mkdir()
        foreign = self._write_worker(shadow_bin, "7.3.0")
        before = foreign.read_bytes()
        completed = self.run_preflight(
            self.env([shadow_bin, self.fake_bin, self.uv_bin, "/usr/bin", "/bin"])
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.install_calls(), [])
        self.assertEqual(foreign.read_bytes(), before)
        self.assertIn(str(foreign.resolve()), completed.stderr)
        self.assertIn(str((self.uv_bin / "codex-worker").resolve()), completed.stderr)
        self.assertIn("PATH", completed.stderr)
        self.assertIn("uv tool update-shell", completed.stderr)

    def test_missing_uv_is_an_actionable_prerequisite_refusal(self):
        completed = self.run_preflight(self.env(["/usr/bin", "/bin"]))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("uv", completed.stderr.lower())
        self.assertIn("install", completed.stderr.lower())
        self.assertFalse((self.uv_bin / "codex-worker").exists())
        self.assertFalse(self.state.exists())

    def test_claude_plugin_root_must_equal_loaded_script_root_before_uv(self):
        other = self.root / "other-plugin"
        self._write_plugin(other)
        completed = self.run_preflight(
            self.env(CLAUDE_PLUGIN_ROOT=other)
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.install_calls(), [])
        self.assertIn(str(self.plugin.resolve()), completed.stderr)
        self.assertIn(str(other.resolve()), completed.stderr)

    def test_manifest_and_package_versions_must_match_before_uv(self):
        manifest = self.plugin / ".claude-plugin" / "plugin.json"
        manifest.write_text(
            json.dumps({"name": "superdev", "version": "7.8.0"}) + "\n",
            encoding="utf-8",
        )
        completed = self.run_preflight()
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.install_calls(), [])
        self.assertIn("7.8.0", completed.stderr)
        self.assertIn(self.expected_version, completed.stderr)

    def test_uv_bin_off_path_refuses_with_current_shell_recovery(self):
        completed = self.run_preflight(
            self.env([self.fake_bin, "/usr/bin", "/bin"])
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(len(self.install_calls()), 1)
        self.assertIn("uv tool update-shell", completed.stderr)
        self.assertIn("export PATH=", completed.stderr)
        self.assertIn(str(self.uv_bin.resolve()), completed.stderr)

    def test_matching_uv_command_off_path_refuses_without_reinstall(self):
        self._write_worker(self.uv_bin, self.expected_version)
        completed = self.run_preflight(
            self.env([self.fake_bin, "/usr/bin", "/bin"])
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.install_calls(), [])
        self.assertIn("uv tool update-shell", completed.stderr)

    def test_uv_executable_path_with_spaces_is_invoked_as_one_word(self):
        spaced_bin = self.root / "fake uv bin"
        spaced_bin.mkdir()
        shutil.copy2(self.fake_bin / "uv", spaced_bin / "uv")
        completed = self.run_preflight(
            self.env([spaced_bin, self.uv_bin, "/usr/bin", "/bin"])
        )
        self.assert_ready(completed)

    def test_install_failure_preserves_prior_tool_and_durable_sentinel(self):
        worker = self._write_worker(self.uv_bin, "7.8.0")
        sentinel = self.root / "uv-tools" / "codex-worker" / "durable-sentinel"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("preserve me\n", encoding="utf-8")
        worker_before = digest(worker)
        sentinel_before = digest(sentinel)
        completed = self.run_preflight(self.env(FAKE_UV_FAIL_CODE="42"))
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(digest(worker), worker_before)
        self.assertEqual(digest(sentinel), sentinel_before)
        self.assertIn("42", completed.stderr)
        self.assertIn("fake install stdout", completed.stderr)
        self.assertIn("fake install stderr", completed.stderr)

    def test_installed_layout_without_external_codex_is_one_typed_refusal(self):
        installed_root = self.root / "installed"
        site_packages = installed_root / "site-packages"
        shutil.copytree(SOURCE_PACKAGE / "codex_worker", site_packages / "codex_worker")
        dist_info = site_packages / "codex_worker-7.9.0.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: codex-worker\nVersion: 7.9.0\n",
            encoding="utf-8",
        )
        installed_bin = installed_root / "bin"
        installed_bin.mkdir(parents=True)
        interpreter = installed_bin / "python"
        interpreter.symlink_to(Path(sys.executable).resolve())
        launcher = installed_bin / "codex-worker"
        launcher.write_text(
            "#!%s\n"
            "import sys\n"
            "sys.path.insert(0, %r)\n"
            "from codex_worker.cli import main\n"
            "raise SystemExit(main())\n" % (interpreter, str(site_packages)),
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        env = self.env([installed_bin, "/usr/bin", "/bin"])
        env["CODEX_WORKER_INSTANCE"] = "missing-external-codex"
        completed = subprocess.run(
            [str(launcher), "--instance", "missing-external-codex", "daemon", "start"],
            cwd=self.root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(len(completed.stdout.splitlines()), 1, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["error"]["data"]["kind"], "daemon_start_failed")
        self.assertEqual(payload["error"]["data"]["details"]["reason"], "codex_not_found")
        self.assertIn("codex", json.dumps(payload).lower())
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
