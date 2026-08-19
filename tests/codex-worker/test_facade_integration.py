"""Real-process deterministic receipts for the named worker command façade."""
import json
import os
import shutil
import socket
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

    @unittest.skipUnless(os.name == "posix" and hasattr(socket, "AF_UNIX")
                         and shutil.which("ps") is not None,
                         "requires POSIX AF_UNIX and ps process inspection")
    def test_five_fresh_processes_converge_on_one_daemon_without_crossing_outputs(self):
        self.set_scenario({"turn_barrier": 5, "turn_delays": {
            "prompt-0": 0.50, "prompt-1": 0.40, "prompt-2": 0.30,
            "prompt-3": 0.20, "prompt-4": 0.10,
        }, "turn_outputs": {"prompt-0": "token-0", "prompt-1": "token-1",
                            "prompt-2": "token-2", "prompt-3": "token-3",
                            "prompt-4": "token-4"}})
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
            self.addCleanup(self.cleanup_process, processes[-1])
        self.wait_for_capture_count("turn/start", 5)
        first_active_status = self.daemon_status()
        daemon_pid = first_active_status["daemon_pid"]
        codex_pid = first_active_status["codex_pid"]
        daemon_command = self.process_command(daemon_pid)
        self.assertIn(first_active_status["instance"]["socket_path"], daemon_command)
        self.assertIn(str(Path(first_active_status["instance"]["durable_dir"]) / "registry.json"),
                      daemon_command)
        self.assertEqual(self.process_parent(codex_pid), daemon_pid)
        self.assertEqual(self.codex_children(daemon_pid), [codex_pid])
        self.assertTrue(any(process.poll() is None for process in processes))
        active_statuses = [first_active_status] + [self.daemon_status() for _ in processes[1:]]
        self.assertEqual({status["daemon_pid"] for status in active_statuses}, {daemon_pid})
        self.assertEqual({status["codex_pid"] for status in active_statuses}, {codex_pid})

        observed_client_completion_order = []
        deadline = time.monotonic() + 12
        remaining = set(range(len(processes)))
        while remaining and time.monotonic() < deadline:
            for index in list(remaining):
                if processes[index].poll() is not None:
                    observed_client_completion_order.append(index); remaining.remove(index)
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
        self.assertEqual(set(observed_client_completion_order), set(range(5)))
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
        self.assertEqual(managed["daemon_pid"], daemon_pid)
        self.assertEqual(managed["codex_pid"], codex_pid)
        captures = [json.loads(line) for line in self.capture.read_text(encoding="utf-8").splitlines()]
        starts = [row for row in captures if row.get("method") == "thread/start"]
        self.assertEqual(len(starts), 5)
        initialize = [row for row in captures if row.get("method") == "initialize"]
        self.assertEqual([row["params"] for row in initialize], [{
            "clientInfo": {"name": "superdev_codex_worker", "title": "Superdev Codex Worker",
                           "version": "0.1.0"},
            "capabilities": {"experimentalApi": True, "optOutNotificationMethods": [
                "item/agentMessage/delta", "item/reasoning/textDelta",
                "item/reasoning/summaryTextDelta", "item/commandExecution/outputDelta",
            ]},
        }])
        expected_thread_params = [{
            "cwd": str(path.resolve()), "approvalPolicy": "never",
            "sandbox": "danger-full-access", "serviceName": "superdev_codex_worker",
            "model": "fake-model-a", "allowProviderModelFallback": False,
        } for path in workspaces]
        self.assertCountEqual([row["params"] for row in starts], expected_thread_params)
        turns = [row for row in captures if row.get("method") == "turn/start"]
        expected_turn_params = [{
            "threadId": results[index]["worker"]["thread_id"],
            "input": [{"type": "text", "text": "prompt-%d" % index}],
            "model": "fake-model-a", "effort": "medium",
            "sandboxPolicy": {"type": "dangerFullAccess"},
        } for index in range(5)]
        self.assertCountEqual([row["params"] for row in turns], expected_turn_params)
        completions = [row for row in captures if row.get("kind") == "completion"]
        self.assertEqual([row["prompt"] for row in sorted(completions, key=lambda row: row["seq"])],
                         ["prompt-4", "prompt-3", "prompt-2", "prompt-1", "prompt-0"])
        self.assertEqual([row["output"] for row in sorted(completions, key=lambda row: row["seq"])],
                         ["token-4", "token-3", "token-2", "token-1", "token-0"])
        self.assertEqual([row["at"] for row in sorted(completions, key=lambda row: row["seq"])],
                         sorted(row["at"] for row in completions))
        self.assertEqual({row["pid"] for row in captures}, {codex_pid})
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

    def test_section_10_name_and_model_refusals_preserve_registry_state(self):
        created = self.command(["start", "--name", "stable", "--prompt", "first",
                                "--cwd", str(ROOT), "--model", "fake-model-a"])
        self.assertEqual(created.returncode, 0, created.stderr)
        status = self.daemon_status()
        registry = Path(status["instance"]["durable_dir"]) / "registry.json"
        preserved = registry.read_bytes()
        cases = [
            (["start", "--name", "stable", "--prompt", "again", "--cwd", str(ROOT),
              "--model", "fake-model-a"], -32021, "worker_name_exists"),
            (["run", "--name", "missing", "--prompt", "again"],
             -32022, "worker_not_found"),
            (["start", "--name", "bad-model", "--prompt", "again", "--cwd", str(ROOT),
              "--model", "missing-model"], -32026, "model_unavailable"),
            (["start", "--name", "bad-effort", "--prompt", "again", "--cwd", str(ROOT),
              "--model", "fake-model-a", "--effort", "high"],
             -32027, "effort_unsupported"),
        ]
        for argv, code, kind in cases:
            with self.subTest(kind=kind):
                result = self.command(argv)
                self.assertEqual(result.returncode, 1, result.stderr)
                error = json.loads(result.stdout)["error"]
                self.assertEqual((error["code"], error["data"]["kind"]), (code, kind))
                self.assertEqual(registry.read_bytes(), preserved)

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
        captures = self.captures()
        thread_id = json.loads(created.stdout)["result"]["worker"]["thread_id"]
        self.assertEqual([row["params"] for row in captures
                          if row.get("method") == "thread/goal/get"], [{"threadId": thread_id}])
        self.assertEqual([row["params"] for row in captures
                          if row.get("method") == "account/rateLimits/read"], [{}])

    def test_schema_is_forwarded_exactly_on_the_composed_turn(self):
        self.set_scenario({"turn_outputs": {"structured": '{"verdict":"pass"}'}})
        schema = Path(self.tempdir.name) / "schema.json"
        schema_value = {"type": "object", "properties": {"verdict": {"type": "string"}},
                        "required": ["verdict"], "additionalProperties": False}
        schema.write_text(json.dumps(schema_value), encoding="utf-8")
        result = self.command(["start", "--name", "structured", "--prompt", "structured",
                               "--cwd", str(ROOT), "--model", "fake-model-a",
                               "--effort", "medium", "--output-schema", str(schema)])
        self.assertEqual(result.returncode, 0, result.stderr)
        thread_id = json.loads(result.stdout)["result"]["worker"]["thread_id"]
        turn = next(row for row in self.captures() if row.get("method") == "turn/start")
        self.assertEqual(turn["params"], {
            "threadId": thread_id, "input": [{"type": "text", "text": "structured"}],
            "model": "fake-model-a", "effort": "medium",
            "sandboxPolicy": {"type": "dangerFullAccess"}, "outputSchema": schema_value,
        })

    def test_multiple_explicit_finals_and_command_metrics_are_composed_exactly(self):
        self.set_scenario({
            "turn_outputs": {"metrics": ["first final", "second final"]},
            "turn_phases": {"metrics": "final_answer"},
            "usage": False,
            "command_duration_ms": 37,
        })
        completed = self.command([
            "start", "--name", "metrics", "--prompt", "metrics",
            "--cwd", str(ROOT), "--model", "fake-model-a",
        ])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)["result"]
        self.assertEqual([message["text"] for message in result["messages"]],
                         ["first final", "second final"])
        self.assertEqual([message["selection"] for message in result["messages"]],
                         ["explicit_final", "explicit_final"])
        self.assertEqual(result["metrics"]["command_count"], {
            "value": 1, "source": "codex-worker", "availability": "derived",
        })
        self.assertEqual(result["metrics"]["command_duration_ms"], {
            "value": 37, "source": "codex", "availability": "derived",
        })
        self.assertEqual(result["metrics"]["token_usage"], {
            "value": None, "source": "codex", "availability": "unavailable",
        })

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
        live_turn = {
            "id": "live", "status": "inProgress",
            "items": [{"id": "live-message", "type": "agentMessage",
                       "text": "working", "phase": None}],
        }
        completed_turn = {
            "id": "final", "status": "completed",
            "items": [{"id": "final-message", "type": "agentMessage",
                       "text": "answer", "phase": "final_answer"}],
        }
        self.set_scenario({"history_pages": {
            "null": {"turns": [live_turn], "nextCursor": "older"},
            "older": {"turns": [completed_turn], "nextCursor": None},
        }})
        created = self.command(["start", "--name", "history", "--prompt", "first", "--cwd", str(ROOT),
                                "--model", "fake-model-a"])
        self.assertEqual(created.returncode, 0, created.stderr)
        history = self.command(["history", "--name", "history", "--tail", "2"])
        self.assertEqual(history.returncode, 0, history.stderr)
        turns = json.loads(history.stdout)["result"]["turns"]
        self.assertEqual([turn["turn_id"] for turn in turns], ["final", "live"])
        self.assertEqual(turns[-1]["messages"][0]["selection"], "live")
        self.assertEqual(turns[0]["messages"][0]["selection"], "explicit_final")
        thread_id = json.loads(created.stdout)["result"]["worker"]["thread_id"]
        requests = [row["params"] for row in self.captures()
                    if row.get("method") == "thread/turns/list"]
        self.assertEqual(requests, [
            {"threadId": thread_id, "sortDirection": "desc", "itemsView": "full", "limit": 2},
            {"threadId": thread_id, "sortDirection": "desc", "itemsView": "full",
             "cursor": "older", "limit": 2},
        ])

    def test_goal_set_and_show_forward_exact_native_parameters(self):
        created = self.command(["start", "--name", "goal", "--prompt", "first",
                                "--cwd", str(ROOT), "--model", "fake-model-a",
                                "--goal", "finish", "--token-budget", "123"])
        self.assertEqual(created.returncode, 0, created.stderr)
        shown = self.command(["goal", "show", "--name", "goal"])
        self.assertEqual(shown.returncode, 0, shown.stderr)
        thread_id = json.loads(created.stdout)["result"]["worker"]["thread_id"]
        captures = self.captures()
        self.assertEqual([row["params"] for row in captures
                          if row.get("method") == "thread/goal/set"], [{
                              "threadId": thread_id, "objective": "finish",
                              "status": "active", "tokenBudget": 123,
                          }])
        self.assertEqual([row["params"] for row in captures
                          if row.get("method") == "thread/goal/get"], [{"threadId": thread_id}])

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

    def wait_for_capture_count(self, method, count, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rows = self.captures() if self.capture.exists() else []
            if len([row for row in rows if row.get("method") == method]) >= count:
                return
            time.sleep(0.005)
        self.fail("capture did not receive %d %s requests before deadline" % (count, method))

    def daemon_status(self):
        completed = self.command(["daemon", "status"])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)["result"]

    def process_parent(self, pid):
        completed = subprocess.run(["ps", "-p", str(pid), "-o", "ppid="], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return int(completed.stdout.strip())

    def process_command(self, pid):
        completed = subprocess.run(["ps", "-p", str(pid), "-o", "command="], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def codex_children(self, daemon_pid):
        completed = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        children = []
        for line in completed.stdout.splitlines():
            fields = line.strip().split(None, 2)
            if len(fields) == 3 and int(fields[1]) == daemon_pid:
                self.assertIn(str(FAKE), fields[2])
                self.assertIn("app-server", fields[2])
                children.append(int(fields[0]))
        return children

    def cleanup_process(self, process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        for stream in (process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()

    def tearDown(self):
        try:
            self.command(["daemon", "stop"])
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _daemon_log(self):
        logs = list(Path(self.env["HOME"]).rglob("daemon.log"))
        return logs[0].read_text(encoding="utf-8") if logs else ""

if __name__ == "__main__":
    unittest.main()
