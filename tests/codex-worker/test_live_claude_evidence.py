import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("live_claude_evidence.py")
LIVE_SCRIPT = Path(__file__).with_name("live_claude_check.sh")
WRAPPER = Path(__file__).with_name("codex_worker_isolation_wrapper.sh")
SPEC = importlib.util.spec_from_file_location("live_claude_evidence", SCRIPT)
assert SPEC and SPEC.loader
EVIDENCE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(EVIDENCE)


class ClaudeEvidenceTests(unittest.TestCase):
    def test_real_claude_auth_and_worker_state_have_an_explicit_isolation_boundary(self):
        source = LIVE_SCRIPT.read_text(encoding="utf-8")
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertIn('env -u CLAUDE_CONFIG_DIR HOME="$REAL_HOME" claude -p', source)
        self.assertIn('codex_worker_isolation_wrapper.sh', source)
        self.assertIn('codex-worker.uv-real', source)
        self.assertNotIn('cp "$REAL_HOME/.claude.json"', source)
        self.assertNotIn('CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$REAL_HOME/.claude}"', source)
        for variable in ("HOME", "XDG_STATE_HOME", "TMPDIR", "CLAUDE_CONFIG_DIR"):
            self.assertIn('export %s=' % variable, wrapper)
        self.assertIn('exec "$CODEX_WORKER_UV_EXECUTABLE" "$@"', wrapper)
        self.assertIn('RUNTIME_REAL=$(cd "$RUNTIME" && pwd -P)', source)
        self.assertIn('"$RUNTIME_REAL" == /private/tmp/cw5-claude.*', source)

    def test_tracked_real_claude_receipt_covers_every_family_and_cleanup(self):
        path = (Path(__file__).parents[2] / "docs" / "superdev" / "checkrides" /
                "2026-08-28-codex-worker-shared-app-server-evidence" /
                "real-claude-caller-summary.json")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "MEASURED complete")
        self.assertEqual(receipt["checkride_verdict"],
                         "PENDING controller executor/evaluator")
        self.assertEqual(set(receipt["command_coverage"]), {
            "start", "run", "message", "status", "messages", "history",
            "steer", "interrupt", "goal_set", "goal_show", "limits", "model_list",
            "session_start", "session_list", "session_show", "session_resume",
            "turn_start", "turn_wait", "turn_status", "turn_events", "turn_steer",
            "turn_interrupt",
        })
        self.assertTrue(all(receipt["command_coverage"].values()))
        self.assertEqual(receipt["cleanup"], {
            "claude_config_copied": False, "processes_remaining": 0,
            "runtime_deleted": True, "service_status": "stopped",
            "socket_listeners_remaining": 0,
        })

    def test_validates_path_only_complete_family_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cwd = root / "unrelated"; cwd.mkdir()
            worker = {
                "name": "claude-live-a31f09", "session_id": "session-1",
                "thread_id": "thread-1", "cwd": str(cwd.resolve()),
                "tier": "medium", "model": "gpt-5.6-terra", "effort": "medium",
                "access": "full", "attach": {"listener": "ws://127.0.0.1:4777",
                    "thread_id": "thread-1", "attach_command": "codex --remote ws://127.0.0.1:4777",
                    "resume_command": "codex --remote ws://127.0.0.1:4777 resume thread-1"},
            }
            completion = {"worker": worker,
                "turn": {"turn_id": "turn-1", "status": "completed", "error": None},
                "messages": [{"type": "agent_message", "item_id": "i", "phase": "final_answer",
                              "selection": "explicit_final", "text": "ok"}],
                "structured_output": None,
                "metrics": {"token_usage": {"value": None, "source": "codex",
                                             "availability": "unavailable"}},
                "recovery": {"status": "codex-worker status --name claude-live-a31f09"}}
            commands = [
                "codex-worker start --name claude-live-a31f09 --cwd %s --prompt hi" % cwd,
                "codex-worker run --name claude-live-a31f09 --prompt again",
                "codex-worker message --name claude-live-a31f09 --message update",
                "codex-worker status --name claude-live-a31f09",
                "codex-worker messages --name claude-live-a31f09",
                "codex-worker history --name claude-live-a31f09",
                "codex-worker steer --name claude-live-a31f09 --prompt steer",
                "codex-worker interrupt --name claude-live-a31f09",
                "codex-worker goal set --name claude-live-a31f09 --goal finish",
                "codex-worker goal show --name claude-live-a31f09", "codex-worker limits",
                "codex-worker model list", "codex-worker session start --cwd %s" % cwd,
                "codex-worker session list", "codex-worker session show --session session-2",
                "codex-worker session resume --session session-2",
                "codex-worker turn start --session session-2 --prompt long",
                "codex-worker turn wait --session session-2", "codex-worker turn status --session session-2",
                "codex-worker turn events --session session-2",
                "codex-worker turn steer --session session-2 --prompt steer",
                "codex-worker turn interrupt --session session-2",
            ]
            status = {"worker": worker, "daemon_status": "ready", "attached": True,
                      "active_turn_id": None, "latest_turn": completion["turn"],
                      "callback": {"state": "enabled", "pending_terminal_count": 0,
                                   "last_terminal_attempt": {"state": "written"}}}
            history = {"worker": worker, "turns": [], "requested_tail": 1,
                       "returned": 0, "older_available": False}
            results = []
            for command in commands:
                if " start " in command and "session start" not in command: value = completion
                elif " run " in command: value = completion
                elif " status " in command and "turn status" not in command: value = status
                elif " history " in command: value = history
                else: value = {"ok": True}
                results.append(value)
            transcript = root / "stream.jsonl"; rows = []
            for index, (command, result) in enumerate(zip(commands, results)):
                tool_id = "t%d" % index
                rows.append({"message": {"content": [{"type": "tool_use", "id": tool_id,
                    "name": "Bash", "input": {"command": command}}]}})
                rows.append({"message": {"content": [{"type": "tool_result",
                    "tool_use_id": tool_id, "is_error": False,
                    "content": json.dumps({"result": result})}]}})
            transcript.write_text("\n".join(map(json.dumps, rows)) + "\n")
            receipt = EVIDENCE.validate(transcript, cwd, "codex-worker")
            self.assertEqual(set(receipt["coverage"]), set(EVIDENCE.REQUIRED_COMMAND_PATTERNS))
            self.assertEqual(receipt["attach"]["thread_id"], "thread-1")

            for forbidden in ("codex app-server", "codex-worker --instance x status --name a",
                              "codex-worker --socket /tmp/s turn status --session x",
                              "codex-worker daemon stop", "mcp__codex__call"):
                changed = json.loads(json.dumps(rows)); changed[0]["message"]["content"][0]["input"]["command"] = forbidden
                transcript.write_text("\n".join(map(json.dumps, changed)) + "\n")
                with self.assertRaises(AssertionError):
                    EVIDENCE.validate(transcript, cwd, "codex-worker")


if __name__ == "__main__": unittest.main()
