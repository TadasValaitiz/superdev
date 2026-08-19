import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("live_claude_evidence.py")
SPEC = importlib.util.spec_from_file_location("live_claude_evidence", SCRIPT)
assert SPEC and SPEC.loader
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)


class ClaudeEvidenceTests(unittest.TestCase):
    def test_validates_path_common_command_journey(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cwd = root / "repo"; cwd.mkdir()
            cli = "codex-worker"
            sid, tid, turn = "session-1", "thread-1", "turn-1"
            worker = {
                "instance": "claude-live", "name": "claude-caller-a31f09",
                "session_id": sid, "thread_id": tid, "cwd": str(cwd.resolve()),
                "tier": "medium", "model": "gpt-5.6-terra", "effort": "medium",
                "access": "full",
            }
            completion = {
                "worker": worker,
                "turn": {"turn_id": turn, "status": "completed", "error": None},
                "messages": [{"type": "agent_message", "item_id": "item-1",
                              "phase": "final_answer", "selection": "explicit_final",
                              "text": "complete result"}],
                "structured_output": None,
                "metrics": {"token_usage": {"value": None, "source": "codex",
                                              "availability": "unavailable"}},
                "recovery": {"status": "codex-worker status --name claude-caller-a31f09"},
            }
            commands = [
                f"cd {cwd} && {cli} start --name claude-caller-a31f09 --prompt 'answer briefly'",
                f"{cli} run --name claude-caller-a31f09 --prompt 'short follow-up'",
                f"{cli} goal show --name claude-caller-a31f09",
                f"{cli} history --name claude-caller-a31f09 --tail 2",
                f"{cli} status --name claude-caller-a31f09",
                f"{cli} daemon stop",
            ]
            results = [
                completion,
                dict(completion, turn={"turn_id": "turn-2", "status": "completed", "error": None}),
                {"worker": worker, "availability": "absent", "goal": None},
                {"worker": worker, "turns": [], "requested_tail": 2, "returned": 0,
                 "older_available": False},
                {"worker": worker, "daemon_status": "ready", "attached": True,
                 "active_turn_id": None, "latest_turn": completion["turn"]},
                {"instance": {"instance": "claude-live"}, "status_before": "ready",
                 "status_after": "stopped", "daemon_pid": 1, "codex_pid": 2,
                 "durable_state": "preserved", "worker_count": 1},
            ]
            transcript = root / "stream.jsonl"
            lines = []
            for i, (command, result) in enumerate(zip(commands, results)):
                lines.append({"message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": command}}]}})
                lines.append({"message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "is_error": False, "content": json.dumps({"result": result})}]}})
            transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
            receipt = EVIDENCE.validate(transcript, cwd, cli)
            self.assertEqual((receipt["session_id"], receipt["thread_id"], receipt["turn_id"]), (sid, tid, turn))
            self.assertTrue(receipt["native_claude_available"])
            self.assertEqual(receipt["durable_state"], "preserved")

            for forbidden in ("codex app-server", "python3 /repo/codex-worker model list", "mcp__codex__call"):
                lines[0]["message"]["content"][0]["input"]["command"] = forbidden
                transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
                with self.assertRaises(AssertionError):
                    EVIDENCE.validate(transcript, cwd, cli)


if __name__ == "__main__":
    unittest.main()
