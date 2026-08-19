"""Real-process deterministic receipts for the named worker command façade."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / "bin" / "codex-worker"
FAKE = Path(__file__).with_name("fake_codex.py")


class FacadeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.state = root / "state"
        self.capture = root / "capture.jsonl"
        self.scenario = root / "scenario.json"
        self.scenario.write_text(json.dumps({"delay": 0.02, "turn_delays": {
            "prompt-0": 0.50, "prompt-1": 0.40, "prompt-2": 0.30,
            "prompt-3": 0.20, "prompt-4": 0.10,
        }, "turn_outputs": {"prompt-0": "token-0", "prompt-1": "token-1",
                               "prompt-2": "token-2", "prompt-3": "token-3", "prompt-4": "token-4"}}), encoding="utf-8")
        fake_bin = root / "bin"
        fake_bin.mkdir()
        codex = fake_bin / "codex"
        codex.write_text("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, FAKE), encoding="utf-8")
        codex.chmod(0o700)
        self.env = dict(os.environ, HOME=str(root / "home"), XDG_STATE_HOME=str(self.state),
                        FAKE_CODEX_SCENARIO=str(self.scenario), FAKE_CODEX_CAPTURE=str(self.capture),
                        PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))
        self.instance = "integration-%s" % os.path.basename(self.tempdir.name)

    def command(self, argv, cwd=None):
        return subprocess.run([str(COMMAND), "--instance", self.instance] + argv,
                              cwd=str(cwd or ROOT), env=self.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)

    def test_five_fresh_processes_converge_on_one_daemon_without_crossing_outputs(self):
        workspaces = []
        processes = []
        for index in range(5):
            cwd = Path(self.tempdir.name) / ("cwd-%d" % index)
            cwd.mkdir(); workspaces.append(cwd)
            processes.append(subprocess.Popen(
                 [str(COMMAND), "--instance", self.instance, "start", "--name", "worker-%d" % index,
                 "--cwd", str(cwd), "--prompt", "prompt-%d" % index,
                 "--model", "fake-model-a", "--effort", "medium",
                 ],
                env=self.env, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        finished = []
        deadline = time.monotonic() + 12
        remaining = set(range(len(processes)))
        while remaining and time.monotonic() < deadline:
            for index in list(remaining):
                if processes[index].poll() is not None:
                    finished.append(index); remaining.remove(index)
            time.sleep(0.005)
        self.assertFalse(remaining, "worker clients did not finish before the bounded deadline")
        responses = []; failures = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=1)
            failures.append((process.returncode, stderr, stdout))
        for returncode, stderr, stdout in failures:
            self.assertEqual(returncode, 0, stderr + stdout + self._daemon_log())
            responses.append(json.loads(stdout))
        results = [response["result"] for response in responses]
        self.assertEqual(finished, [4, 3, 2, 1, 0])
        self.assertEqual({result["worker"]["name"] for result in results},
                         {"worker-%d" % index for index in range(5)})
        self.assertEqual({result["worker"]["thread_id"] for result in results},
                         {"thr-fake"} | {"thr-fake-%d" % index for index in range(2, 6)})
        self.assertEqual(len({result["worker"]["session_id"] for result in results}), 5)
        for index, result in enumerate(results):
            self.assertEqual(result["worker"]["cwd"], str(workspaces[index].resolve()))
            self.assertEqual(result["messages"][-1]["text"], "token-%d" % index)
            self.assertEqual(result["messages"][-1]["selection"], "terminal_fallback")
        status = self.command(["daemon", "status"])
        self.assertEqual(status.returncode, 0, status.stderr)
        managed = json.loads(status.stdout)["result"]
        self.assertEqual(managed["worker_count"], 5)
        self.assertTrue(_pid_exists(managed["daemon_pid"]))
        self.assertTrue(_pid_exists(managed["codex_pid"]))
        captures = [json.loads(line) for line in self.capture.read_text(encoding="utf-8").splitlines()]
        starts = [row for row in captures if row.get("method") == "thread/start"]
        self.assertEqual(len(starts), 5)
        self.assertEqual({row["params"]["cwd"] for row in starts}, {str(path.resolve()) for path in workspaces})
        self.assertEqual({row["params"]["model"] for row in starts}, {"fake-model-a"})
        turns = [row for row in captures if row.get("method") == "turn/start"]
        self.assertEqual({row["params"]["model"] for row in turns}, {"fake-model-a"})
        self.assertEqual({row["params"]["effort"] for row in turns}, {"medium"})
        self.assertEqual({row["params"]["sandboxPolicy"]["type"] for row in turns}, {"dangerFullAccess"})
        self.assertEqual(stat.S_IMODE(self.capture.stat().st_mode), 0o600)

    def test_stop_then_run_preserves_the_named_thread_and_registry(self):
        created = self.command(["start", "--name", "restart-1", "--prompt", "first",
                                "--cwd", str(ROOT), "--model", "fake-model-a"])
        self.assertEqual(created.returncode, 0, created.stderr)
        thread_id = json.loads(created.stdout)["result"]["worker"]["thread_id"]
        stopped = self.command(["daemon", "stop"])
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        continued = self.command(["run", "--name", "restart-1", "--prompt", "second"])
        self.assertEqual(continued.returncode, 0, continued.stderr)
        self.assertEqual(json.loads(continued.stdout)["result"]["worker"]["thread_id"], thread_id)
        captures = [json.loads(line) for line in self.capture.read_text(encoding="utf-8").splitlines()]
        self.assertIn(thread_id, [row["params"].get("threadId") for row in captures
                                  if row.get("method") == "thread/resume"])

    def test_duplicate_and_unknown_names_are_refused_without_mutating_registry(self):
        created = self.command(["start", "--name", "stable", "--prompt", "first",
                                "--cwd", str(ROOT), "--model", "fake-model-a"])
        self.assertEqual(created.returncode, 0, created.stderr)
        duplicate = self.command(["start", "--name", "stable", "--prompt", "again",
                                  "--cwd", str(ROOT), "--model", "fake-model-a"])
        unknown = self.command(["run", "--name", "missing", "--prompt", "again"])
        for result, kind in ((duplicate, "worker_name_exists"), (unknown, "worker_not_found")):
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)["error"]["data"]["kind"], kind)

    def test_goal_failure_refuses_before_starting_a_turn(self):
        self.set_scenario({"goal_set_failure": True})
        result = self.command(["start", "--name", "goal-fails", "--prompt", "never-send",
                               "--cwd", str(ROOT), "--model", "fake-model-a", "--goal", "finish"])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["error"]["data"]["kind"], "codex_failure")
        captures = self.captures()
        self.assertEqual(len([row for row in captures if row.get("method") == "thread/goal/set"]), 1)
        self.assertEqual([row for row in captures if row.get("method") == "turn/start"], [])

    def test_native_absence_and_unavailable_limits_are_typed_without_autostart_surprises(self):
        self.set_scenario({"goal_absent": True, "limits_unavailable": True})
        created = self.command(["start", "--name", "proxies", "--prompt", "done",
                                "--cwd", str(ROOT), "--model", "fake-model-a"])
        self.assertEqual(created.returncode, 0, created.stderr)
        goal = self.command(["goal", "show", "--name", "proxies"])
        limits = self.command(["limits"])
        self.assertEqual(json.loads(goal.stdout)["result"]["availability"], "absent")
        self.assertEqual(limits.returncode, 1)
        self.assertEqual(json.loads(limits.stdout)["error"]["data"]["kind"], "limits_unavailable")

    def test_no_agent_and_schema_decode_refusals_preserve_completed_message_evidence(self):
        self.set_scenario({"turn_outputs": {"schema": "not-json"}})
        schema = Path(self.tempdir.name) / "schema.json"
        schema.write_text('{"type":"object"}', encoding="utf-8")
        result = self.command(["start", "--name", "schema", "--prompt", "schema", "--cwd", str(ROOT),
                               "--model", "fake-model-a", "--output-schema", str(schema)])
        self.assertEqual(result.returncode, 1, result.stderr)
        error = json.loads(result.stdout)["error"]
        self.assertEqual(error["data"]["kind"], "incomplete_completion")
        self.assertEqual(error["data"]["details"]["messages"][-1]["text"], "not-json")

    def test_history_keeps_live_narration_live_and_paginates_terminal_finals(self):
        self.set_scenario({"history_pages": {"null": {"turns": [{"id": "live", "status": "inProgress",
            "items": [{"id": "live-message", "type": "agentMessage", "text": "working", "phase": None}]}],
            "nextCursor": "older"}, "older": {"turns": [{"id": "final", "status": "completed",
            "items": [{"id": "final-message", "type": "agentMessage", "text": "answer", "phase": "final_answer"}]}], "nextCursor": None}}})
        created = self.command(["start", "--name", "history", "--prompt", "first", "--cwd", str(ROOT),
                                "--model", "fake-model-a"])
        self.assertEqual(created.returncode, 0, created.stderr)
        history = self.command(["history", "--name", "history", "--tail", "2"])
        self.assertEqual(history.returncode, 0, history.stderr)
        turns = json.loads(history.stdout)["result"]["turns"]
        self.assertEqual([turn["turn_id"] for turn in turns], ["final", "live"])
        self.assertEqual(turns[-1]["messages"][0]["selection"], "live")
        self.assertEqual(turns[0]["messages"][0]["selection"], "explicit_final")

    def test_no_agent_completion_is_a_typed_incomplete_refusal(self):
        self.set_scenario({"no_agent_messages": True})
        result = self.command(["start", "--name", "empty", "--prompt", "empty", "--cwd", str(ROOT),
                               "--model", "fake-model-a"])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["error"]["data"]["kind"], "incomplete_completion")

    def set_scenario(self, value):
        self.scenario.write_text(json.dumps(value), encoding="utf-8")

    def captures(self):
        return [json.loads(line) for line in self.capture.read_text(encoding="utf-8").splitlines()]

    def tearDown(self):
        try:
            self.command(["daemon", "stop"])
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _daemon_log(self):
        logs = list(Path(self.env["HOME"]).rglob("daemon.log"))
        return logs[0].read_text(encoding="utf-8") if logs else ""


def _pid_exists(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


if __name__ == "__main__":
    unittest.main()
