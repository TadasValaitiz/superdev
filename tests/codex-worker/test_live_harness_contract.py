import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("live_broker_check.py")
UV_SCRIPT = Path(__file__).with_name("live_uv_tool_check.py")
SPEC = importlib.util.spec_from_file_location("live_broker_check", SCRIPT)
assert SPEC and SPEC.loader
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)
UV_SPEC = importlib.util.spec_from_file_location("live_uv_tool_check_contract", UV_SCRIPT)
assert UV_SPEC and UV_SPEC.loader
UV = importlib.util.module_from_spec(UV_SPEC)
UV_SPEC.loader.exec_module(UV)

EXPECTED = (
    "preflight-package",
    "common-attach",
    "exactly-five",
    "lifecycle",
    "migration-callback-shared-control",
    "recovery",
)


class LiveHarnessContractTests(unittest.TestCase):
    def test_codex_version_probe_preserves_literal_cli_prefix(self):
        self.assertEqual(UV.require_codex_01501("codex-cli 0.150.1"),
                         "codex-cli 0.150.1")
        with self.assertRaises(AssertionError):
            UV.require_codex_01501("codex-cli 0.149.0")

    def test_isolated_runtime_root_is_short_and_owner_tokened(self):
        with tempfile.TemporaryDirectory() as td:
            recorder = LIVE.Recorder("preflight-package", live_root=Path(td))
            tool = UV.IsolatedTool(recorder, "runtime-contract")
            try:
                self.assertLess(len(str(tool.temp_dir)), 64)
                owner = json.loads((tool.temp_dir / "fixture-owner.json").read_text())
                self.assertEqual(owner["owner_token"], tool.owner_token)
                self.assertEqual(owner["expected_path"], str(tool.temp_dir))
            finally:
                shutil.rmtree(tool.temp_dir)

    def test_parser_exposes_exactly_six_separately_runnable_scenarios(self):
        self.assertEqual(LIVE.SCENARIOS, EXPECTED)
        self.assertEqual(set(LIVE.SCENARIO_FUNCTIONS), set(EXPECTED))
        for scenario in EXPECTED:
            self.assertEqual(LIVE.parse_args(["--scenario", scenario]).scenario, scenario)
            self.assertTrue(callable(getattr(LIVE, LIVE.SCENARIO_FUNCTIONS[scenario])))
        self.assertEqual(set(LIVE.LEGACY_SCENARIO_ALIASES), {
            "callback-common", "callback-proactive", "callback-origin-retention",
            "callback-recovery", "callback-security", "callback-five-workers"})
        for legacy, replacement in LIVE.LEGACY_SCENARIO_ALIASES.items():
            self.assertEqual(LIVE.parse_args(["--scenario", legacy]).scenario, legacy)
            self.assertIn(replacement, EXPECTED)

    def test_legacy_live_mechanisms_have_explicit_executable_supersession(self):
        mapping = LIVE.LEGACY_MECHANISM_SUPERSESSION
        self.assertIn("timeout then exact terminal", mapping["callback-recovery"])
        self.assertIn("artifact replay", mapping["callback-recovery"])
        self.assertIn("callback endpoint trust refusals", mapping["callback-security"])
        source = SCRIPT.read_text(encoding="utf-8")
        for fragment in (
            "SIMULATED production security fixture",
            "SIMULATED production artifact integrity fixture",
            "SIMULATED production artifact replay fixture",
            "timeout then exact terminal",
        ):
            self.assertIn(fragment, source)

    def test_recorder_contract_tracks_verbatim_commands_without_secret_values(self):
        with tempfile.TemporaryDirectory() as td:
            recorder = LIVE.Recorder("preflight-package", live_root=Path(td))
            completed = subprocess.CompletedProcess(
                ["codex-worker", "--version"], 0, "codex-worker 8.0.0\n", "")
            recorder.record_completed(
                completed, cwd=Path(td), env={"PATH": "/private/bin", "OPENAI_API_KEY": "secret"},
                elapsed_seconds=0.25, substrate="MEASURED real subprocess")
            row = json.loads(recorder.transcript_path.read_text().splitlines()[0])
            self.assertEqual(row["argv"], ["codex-worker", "--version"])
            self.assertEqual(row["cwd"], td)
            self.assertEqual(row["environment_allowlist"], ["PATH"])
            self.assertNotIn("/private/bin", json.dumps(row))
            self.assertNotIn("secret", json.dumps(row))
            self.assertEqual(row["substrate"], "MEASURED real subprocess")
            self.assertEqual(row["elapsed_seconds"], 0.25)

    def test_async_attempt_accounting_never_hides_an_unmatched_start(self):
        rows = [
            {"kind": "command", "stdout": '{"error":{"data":{"kind":"codex_failure"}}}'},
            {"kind": "command_start", "attempt_id": "a"},
        ]
        accounting = LIVE.command_accounting(rows)
        self.assertEqual(accounting, {
            "attempted": 2, "completed": 1, "unmatched_attempts": ["a"],
            "duplicate_attempt_ids": [], "terminal_without_start": [],
            "not_run": 1, "codex_failure_count": 1,
        })
        rows.append({"kind": "command", "attempt_id": "a", "stdout": "{}"})
        self.assertEqual(LIVE.command_accounting(rows)["unmatched_attempts"], [])
        rows.append({"kind": "command_start", "attempt_id": "a"})
        duplicate = LIVE.command_accounting(rows)
        self.assertEqual(duplicate["attempted"], 3)
        self.assertEqual(duplicate["duplicate_attempt_ids"], ["a"])
        self.assertEqual(duplicate["unmatched_attempts"], ["a"])
        rows.append({"kind": "command", "attempt_id": "a", "stdout": "{}"})
        rows.append({"kind": "command", "attempt_id": "a", "stdout": "{}"})
        self.assertEqual(LIVE.command_accounting(rows)["terminal_without_start"], ["a"])

    def test_finish_preserves_unmatched_attempt_as_measured_not_run(self):
        with tempfile.TemporaryDirectory() as td:
            old_root = LIVE.ROOT
            try:
                LIVE.ROOT = Path(td)
                recorder = LIVE.Recorder(
                    "preflight-package", live_root=Path(td) / ".superdev" / "live")
                recorder.record("command_start", {
                    "attempt_id": "preflight-package-1", "argv": ["codex-worker", "--version"]})

                summary = LIVE.finish_scenario(recorder, {}, {})
            finally:
                LIVE.ROOT = old_root

            self.assertEqual(summary["status"], "MEASURED incomplete")
            self.assertEqual(summary["command_accounting"]["unmatched_attempts"],
                             ["preflight-package-1"])
            self.assertEqual(summary["command_accounting"]["not_run"], 1)

    def test_every_run_has_owner_token_and_exact_cleanup_verification(self):
        source = SCRIPT.read_text(encoding="utf-8") + UV_SCRIPT.read_text(encoding="utf-8")
        for fragment in (
            "fixture-owner.json", "owner_token", "expected_pid", "expected_path",
            "token_verified", "pid_verified", "path_verified", "cleanup_outcome",
            "finally:", "cleanup_owned_fixture",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)
        self.assertNotIn("CODEX_WORKER_INSTANCE", source)
        self.assertNotIn('"--instance"', source)

    def test_tracked_evidence_contract_is_exact_and_secret_scanned(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for scenario in EXPECTED:
            tracked = (
                "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-"
                "evidence/scenarios/%s" % scenario
            )
            self.assertIn(tracked, source)
        for fragment in (
            "summary.json", "transcript.jsonl", "sanitize_record", "secret_scan",
            "record_count", "durable_hashes", "environment_allowlist",
        ):
            self.assertIn(fragment, source)

    def test_tracked_scenario_receipts_match_record_and_secret_guards(self):
        for scenario in EXPECTED:
            root = (Path(__file__).parents[2] / "docs" / "superdev" / "checkrides" /
                    "2026-08-28-codex-worker-shared-app-server-evidence" /
                    "scenarios" / scenario)
            summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
            transcript = (root / "transcript.jsonl").read_text(encoding="utf-8")
            self.assertEqual(summary["status"], "MEASURED complete")
            self.assertEqual(summary["record_count"], len(transcript.splitlines()))
            self.assertEqual(summary["secret_scan"], {"scanned": 2, "violations": []})

    def test_preflight_package_is_isolated_python39_and_measured(self):
        source = UV_SCRIPT.read_text(encoding="utf-8")
        for fragment in (
            '"UV_TOOL_DIR"', '"UV_TOOL_BIN_DIR"', '"UV_CACHE_DIR"', '"HOME"',
            '"CODEX_HOME"', '"--python", "3.9"', '"websockets"',
            '"codex 0.150.1"', '"fixture-owner.json"', '"--editable" not in',
            '"MEASURED real UV/tool subprocess"',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)
        ordinary, cleanup = source.split("def cleanup_owned_fixture", 1)
        self.assertNotIn('"daemon", "stop"', ordinary)
        self.assertIn('"daemon", "stop"', cleanup)
        self.assertNotIn('"--instance"', source)

    def test_common_attach_uses_real_second_websocket_client_and_exact_routes(self):
        source = SCRIPT.read_text(encoding="utf-8")
        section = source.split("def scenario_common_attach", 1)[1].split(
            "def scenario_exactly_five", 1)[0]
        section += source.split("def remote_control_script", 1)[1].split(
            "def scenario_preflight_package", 1)[0]
        for fragment in (
            "remote_control_script", "thread/resume",
            "turn/start", "turn/steer", "turn/interrupt", "session_id",
            "thread_id", "attach", "resume_command", "authoritative_events",
        ):
            self.assertIn(fragment, section)

    def test_exactly_five_has_independent_claude_metadata_and_no_crossing(self):
        source = SCRIPT.read_text(encoding="utf-8")
        section = source.split("def scenario_exactly_five", 1)[1].split(
            "def scenario_lifecycle", 1)[0]
        for fragment in (
            "five_worker_names", "CLAUDE_CODE_SESSION_ID", "five simultaneous",
            "crossed_files", "crossed_events", "crossed_callbacks", "tool.temp_dir",
        ):
            self.assertIn(fragment, section)

    def test_lifecycle_and_migration_scenarios_name_every_required_mechanism(self):
        source = SCRIPT.read_text(encoding="utf-8")
        lifecycle = source.split("def scenario_lifecycle", 1)[1].split(
            "def scenario_migration_callback_shared_control", 1)[0]
        for fragment in (
            "127.0.0.1:4500", "occupied", "alternate", "version replacement",
            "active worker", "unmapped TUI", "supervised force", "source deletion",
        ):
            self.assertIn(fragment, lifecycle)
        migration = source.split("def scenario_migration_callback_shared_control", 1)[1].split(
            "def scenario_recovery", 1)[0]
        for fragment in (
            "dedup", "quarantine", "migration", "resolve", "original callback",
            "shared control", "different ambient Claude metadata", "proactive",
        ):
            self.assertIn(fragment, migration)

    def test_recovery_proves_service_survives_caller_and_two_resume_paths(self):
        source = SCRIPT.read_text(encoding="utf-8")
        section = source.split("def scenario_recovery", 1)[1].split("def parse_args", 1)[0]
        for fragment in (
            "caller exit", "service persists", "session resume", "thread resume",
            "status", "history", "steer", "interrupt", "coherent",
        ):
            self.assertIn(fragment, section)


if __name__ == "__main__":
    unittest.main()
