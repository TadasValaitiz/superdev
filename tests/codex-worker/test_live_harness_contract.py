import importlib.util
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("live_broker_check.py")
SPEC = importlib.util.spec_from_file_location("live_broker_check", SCRIPT)
assert SPEC and SPEC.loader
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)


class FakeRecorder:
    def __init__(self):
        self.records = []

    def record(self, kind, payload):
        self.records.append((kind, payload))


class FailingDaemon:
    def __init__(self):
        self.force_closed = False
        self.disposed = False

    def shutdown(self):
        raise RuntimeError("graceful shutdown failed")

    def close(self, force=False):
        self.force_closed = force

    def dispose(self):
        self.disposed = True


class GoalRunner:
    def __init__(self, token_budget):
        self.token_budget = token_budget
        self.calls = []

    def result(self, *argv, cwd=None):
        self.calls.append((argv, cwd))
        return {"availability": "present", "goal": {
            "status": "paused", "token_budget": self.token_budget,
        }}


class LiveHarnessContractTests(unittest.TestCase):
    def test_pause_goal_omits_budget_update_and_preserves_authoritative_budget(self):
        runner = GoalRunner(token_budget=31789)
        preceding = {"availability": "present", "goal": {
            "status": "active", "token_budget": 31789,
        }}

        updated = LIVE.pause_goal_preserving_budget(
            runner, "native-worker", Path("/tmp/native-workspace"), preceding,
        )

        self.assertEqual(runner.calls, [(('goal', 'set', '--name', 'native-worker',
                                         '--status', 'paused'),
                                        Path('/tmp/native-workspace'))])
        self.assertEqual(updated["goal"]["token_budget"], 31789)

    def test_managed_live_cli_preserves_codex_authentication_home(self):
        with tempfile.TemporaryDirectory() as root:
            recorder = type("RecorderStub", (), {"run_dir": Path(root)})()
            runner = LIVE.ManagedCLI(recorder, "test-instance")
            self.assertEqual(runner.env.get("HOME"), os.environ.get("HOME"))

    def test_raw_daemon_uses_python_entrypoint_not_public_shell_launcher(self):
        self.assertEqual(LIVE.RAW_CLI.name, "codex-worker")
        self.assertEqual(LIVE.RAW_CLI.parent.name, "scripts")
        self.assertTrue(LIVE.RAW_CLI.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))
        self.assertTrue(LIVE.CLI.read_text(encoding="utf-8").startswith("#!/bin/sh"))

    def test_selects_exact_two_tier_routes_at_medium_effort(self):
        models = [
            {"id": "gpt-5.6-sol", "supported_efforts": ["low", "medium", "high"]},
            {"id": "gpt-5.6-terra", "supported_efforts": ["low", "medium"]},
            {"id": "something-else", "supported_efforts": ["medium"]},
        ]
        self.assertEqual(LIVE.select_required_routes(models), {
            "medium": {"model": "gpt-5.6-terra", "effort": "medium"},
            "very-smart": {"model": "gpt-5.6-sol", "effort": "medium"},
        })
        with self.assertRaisesRegex(SystemExit, "BLOCKED"):
            LIVE.select_required_routes(models[:1])

    def test_common_command_requires_exactly_one_json_object(self):
        completed = subprocess.CompletedProcess(
            ["codex-worker", "status"], 0,
            stdout='{"jsonrpc":"2.0","id":"cli","result":{}}\n', stderr="",
        )
        self.assertEqual(LIVE.parse_cli_envelope(completed)["id"], "cli")
        for stdout in ("", "{}\n{}\n", "diagnostic\n{}\n", "[]\n"):
            bad = subprocess.CompletedProcess(["codex-worker"], 0, stdout=stdout, stderr="")
            with self.assertRaises(AssertionError):
                LIVE.parse_cli_envelope(bad)

    def test_completion_metrics_are_provenance_labelled(self):
        metrics = {
            "wall_time_ms": {"value": 12, "source": "codex-worker", "availability": "measured"},
            "token_usage": {"value": None, "source": "codex", "availability": "unavailable"},
        }
        LIVE.require_provenance_metrics(metrics)
        for bad in (
            {"wall_time_ms": {"value": 12, "source": "codex-worker"}},
            {"wall_time_ms": {"value": 12, "source": "", "availability": "measured"}},
            {"wall_time_ms": {"value": None, "source": "codex", "availability": "measured"}},
        ):
            with self.assertRaises(AssertionError):
                LIVE.require_provenance_metrics(bad)

    def test_five_worker_names_are_exactly_five_and_unique(self):
        names = LIVE.five_worker_names("live-abc")
        self.assertEqual(len(names), 5)
        self.assertEqual(len(set(names)), 5)
        self.assertTrue(all(name.startswith("live-abc-") for name in names))

    def test_parser_exposes_only_task_8_named_scenarios(self):
        expected = {
            "callback-common", "callback-proactive", "callback-origin-retention",
            "callback-recovery", "callback-security", "callback-five-workers",
        }
        for scenario in expected:
            self.assertEqual(LIVE.parse_args(["--scenario", scenario]).scenario, scenario)
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit):
                LIVE.parse_args(["--scenario", "concurrent-worktrees"])
        self.assertIn("invalid choice", stderr.getvalue())

    def test_callback_scenarios_have_separate_implementations(self):
        expected = {
            "callback-common": "scenario_callback_common",
            "callback-proactive": "scenario_callback_proactive",
            "callback-origin-retention": "scenario_callback_origin_retention",
            "callback-recovery": "scenario_callback_recovery",
            "callback-security": "scenario_callback_security",
            "callback-five-workers": "scenario_callback_five_workers",
        }
        self.assertEqual(LIVE.CALLBACK_SCENARIOS, expected)
        for function_name in expected.values():
            self.assertTrue(callable(getattr(LIVE, function_name)))

    def test_callback_contract_covers_required_acceptance_mechanisms(self):
        contract = LIVE.callback_acceptance_contract()
        self.assertEqual(set(contract), {
            "automatic_inline", "proactive_then_steer", "alternate_then_origin",
            "origin_retention", "terminal_statuses", "timeout_then_terminal",
            "restart_outbox", "artifact_digest", "security_refusals",
            "standalone_disabled", "five_simultaneous",
        })
        self.assertEqual(contract["terminal_statuses"], ["completed", "failed", "interrupted"])
        self.assertEqual(contract["security_refusals"], [
            "credential_scrub", "pid_reuse", "unicode_oversize", "stale", "ambiguous",
        ])
        self.assertEqual(contract["five_simultaneous"], 5)

    def test_checkride_preserves_sanitized_frames_and_drives_recovery_mechanisms(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"callback_frame"', source)
        self.assertIn('"[REDACTED]"', source)
        self.assertIn('"destination"', source)
        for fragment in (
                '"daemon", "start"', '"session", "resume"',
                '"session", "show"', '"turn", "status"',
                '"artifact_readback"', '"turn_terminal_reference"',
                '"failed_terminal_status"', '"pending_same_id_replayed"'):
            self.assertIn(fragment, source)
        self.assertNotIn("deterministic dispatcher receipt", source)
        self.assertIn('"--message-file"', source)
        self.assertIn('"later"', source)

    def test_timeout_contract_proves_no_terminal_before_later_completion(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('time.sleep(5)', source)
        self.assertIn('matching_timeout_events == []', source)
        self.assertIn('"timeout_no_terminal_snapshot"', source)
        self.assertIn('len(later_matching_events) == 1', source)
        self.assertIn('"timeout_preterminal_count": len(matching_timeout_events)', source)

    def test_cleanup_failure_is_not_suppressed(self):
        daemon = FailingDaemon()
        with self.assertRaisesRegex(RuntimeError, "graceful shutdown failed"):
            LIVE.cleanup_daemon(FakeRecorder(), daemon)
        self.assertTrue(daemon.force_closed)
        self.assertTrue(daemon.disposed)

    def test_successful_command_event_requires_cwd_command_and_success(self):
        cwd = Path("/tmp/worker-a")
        events = [
            {"event": "item_completed", "item": {"type": "commandExecution", "data": {
                "command": "python3 hello.py", "cwd": str(cwd.resolve()), "status": "failed", "exitCode": 1}}},
            {"event": "item_completed", "item": {"type": "commandExecution", "data": {
                "command": "python3 hello.py", "cwd": str(cwd.resolve()), "status": "completed", "exitCode": 0}}},
        ]
        found = LIVE.require_successful_command_event(events, cwd, "python3 hello.py")
        self.assertEqual(found["item"]["data"]["exitCode"], 0)
        with self.assertRaises(AssertionError):
            LIVE.require_successful_command_event(events, Path("/tmp/worker-b"), "python3 hello.py")

    def test_distinct_worker_evidence_requires_both_id_dimensions_and_token_isolation(self):
        session_a = {"session_id": "a", "thread_id": "ta"}
        session_b = {"session_id": "b", "thread_id": "tb"}
        LIVE.require_distinct_worker_evidence(session_a, session_b, "secret-a", {"turn": {}}, {"events": []})
        for bad in (
            ({"session_id": "a", "thread_id": "tb"}, {"turn": {}}),
            ({"session_id": "b", "thread_id": "ta"}, {"turn": {}}),
            ({"session_id": "b", "thread_id": "tb"}, {"turn": {"text": "secret-a"}}),
        ):
            with self.assertRaises(AssertionError):
                LIVE.require_distinct_worker_evidence(session_a, bad[0], "secret-a", bad[1], {"events": []})


if __name__ == "__main__":
    unittest.main()
