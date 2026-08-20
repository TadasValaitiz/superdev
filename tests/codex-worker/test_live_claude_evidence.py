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
            callback_event = {
                "schema": "codex-worker.claude-callback/v1",
                "event": "turn_terminal",
                "event_id": "callback-event-1",
                "payload": {"completion": dict(completion)},
            }
            commands = [
                f"cd {cwd} && {cli} start --name claude-caller-a31f09 --prompt 'answer briefly'",
                f"{cli} message --name claude-caller-a31f09 --message 'progress'",
                f"{cli} run --name claude-caller-a31f09 --prompt 'short follow-up'",
                f"{cli} goal show --name claude-caller-a31f09",
                f"{cli} history --name claude-caller-a31f09 --tail 2",
                f"{cli} status --name claude-caller-a31f09",
                f"{cli} daemon stop",
            ]
            results = [
                completion,
                {"worker": worker, "event_id": "proactive-event-1", "attempt": {
                    "state": "written", "reason": None,
                    "attempted_at": "2026-08-20T00:00:00Z", "attempt_count": 1}},
                dict(completion, turn={"turn_id": "turn-2", "status": "completed", "error": None}),
                {"worker": worker, "availability": "absent", "goal": None},
                {"worker": worker, "turns": [], "requested_tail": 2, "returned": 0,
                 "older_available": False},
                {"worker": worker, "daemon_status": "ready", "attached": True,
                 "active_turn_id": None, "latest_turn": completion["turn"],
                 "callback": {"state": "enabled", "pending_terminal_count": 0,
                              "last_terminal_attempt": {"event_id": "callback-event-1",
                                "state": "written", "reason": None,
                                "attempted_at": "2026-08-20T00:00:00Z", "attempt_count": 1}}},
                {"instance": {"instance": "claude-live"}, "status_before": "ready",
                 "status_after": "stopped", "daemon_pid": 1, "codex_pid": 2,
                 "durable_state": "preserved", "worker_count": 1},
            ]
            transcript = root / "stream.jsonl"
            lines = []
            for i, (command, result) in enumerate(zip(commands, results)):
                lines.append({"message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": command}}]}})
                lines.append({"message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "is_error": False, "content": json.dumps({"result": result})}]}})
                if i == 0:
                    lines.append({"type": "user", "message": {"role": "user", "content": json.dumps(callback_event)}})
            transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
            receipt = EVIDENCE.validate(transcript, cwd, cli)
            self.assertEqual((receipt["session_id"], receipt["thread_id"], receipt["turn_id"]), (sid, tid, turn))
            self.assertTrue(receipt["native_claude_available"])
            self.assertEqual(receipt["durable_state"], "preserved")
            self.assertEqual(receipt["callback_event_ids"], ["callback-event-1"])
            self.assertTrue(receipt["full_result_recovered"])

            # Claude stream-json can omit injected callback frames while Claude's
            # final answer still reports their durable IDs and recovered result.
            terminal_id = "terminal-" + "a" * 64
            status_result = results[5]
            status_result["callback"]["last_terminal_attempt"]["event_id"] = terminal_id
            without_injected_frame = [line for line in lines if line.get("type") != "user"]
            for line in without_injected_frame:
                block = line.get("message", {}).get("content", [{}])[0]
                if block.get("type") == "tool_result" and block.get("tool_use_id") == "t5":
                    block["content"] = json.dumps({"result": status_result})
            without_injected_frame.append({
                "message": {"content": [{
                    "type": "text",
                    "text": f"Callback {terminal_id}; recovered: complete result",
                }]},
            })
            transcript.write_text("\n".join(map(json.dumps, without_injected_frame)) + "\n")
            hidden_receipt = EVIDENCE.validate(transcript, cwd, cli)
            self.assertEqual(hidden_receipt["callback_event_ids"], [terminal_id])
            self.assertTrue(hidden_receipt["full_result_recovered"])

            for forbidden in ("codex app-server", "python3 /repo/codex-worker model list", "mcp__codex__call"):
                lines[0]["message"]["content"][0]["input"]["command"] = forbidden
                transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
                with self.assertRaises(AssertionError):
                    EVIDENCE.validate(transcript, cwd, cli)


if __name__ == "__main__":
    unittest.main()
