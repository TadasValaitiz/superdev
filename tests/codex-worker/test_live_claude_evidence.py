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
            run_completion = dict(
                completion, turn={"turn_id": "turn-2", "status": "completed", "error": None},
                messages=[dict(completion["messages"][0], text="follow-up result")])
            callback_event_2 = {
                "schema": "codex-worker.claude-callback/v1",
                "event": "turn_terminal",
                "event_id": "callback-event-2",
                "payload": {"completion": dict(run_completion)},
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
                run_completion,
                {"worker": worker, "availability": "absent", "goal": None},
                {"worker": worker, "turns": [], "requested_tail": 2, "returned": 0,
                 "older_available": False},
                {"worker": worker, "daemon_status": "ready", "attached": True,
                 "active_turn_id": None, "latest_turn": completion["turn"],
                 "callback": {"state": "enabled", "pending_terminal_count": 0,
                              "last_terminal_attempt": {"event_id": "callback-event-2",
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
                if i == 2:
                    lines.append({"type": "user", "message": {"role": "user", "content": json.dumps(callback_event_2)}})
            transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
            receipt = EVIDENCE.validate(transcript, cwd, cli)
            self.assertEqual((receipt["session_id"], receipt["thread_id"], receipt["turn_id"]), (sid, tid, turn))
            self.assertTrue(receipt["native_claude_available"])
            self.assertEqual(receipt["durable_state"], "preserved")
            self.assertEqual(receipt["callback_event_ids"], ["callback-event-1", "callback-event-2"])
            self.assertTrue(receipt["full_result_recovered"])

            # Claude stream-json can omit injected callback frames while Claude's
            # final answer still reports their durable IDs and recovered result.
            terminal_id_1 = "terminal-" + "a" * 64
            terminal_id_2 = "terminal-" + "b" * 64
            status_result = results[5]
            status_result["callback"]["last_terminal_attempt"]["event_id"] = terminal_id_2
            without_injected_frame = [line for line in lines if line.get("type") != "user"]
            attested = []
            for line in without_injected_frame:
                attested.append(line)
                block = line.get("message", {}).get("content", [{}])[0]
                if block.get("type") == "tool_result" and block.get("tool_use_id") == "t5":
                    block["content"] = json.dumps({"result": status_result})
                if block.get("type") == "tool_result" and block.get("tool_use_id") == "t0":
                    attested.append({"message": {"content": [{"type": "text", "text":
                        "Callback 1 received (`%s...`). CALLBACK_COMPLETION_1=%s" % (
                            terminal_id_1[:17], json.dumps(completion, separators=(",", ":")))}]}})
                if block.get("type") == "tool_result" and block.get("tool_use_id") == "t2":
                    attested.append({"message": {"content": [{"type": "text", "text":
                        "Callback 2 received (`%s...`). CALLBACK_COMPLETION_2=%s" % (
                            terminal_id_2[:17], json.dumps(run_completion,
                                                          separators=(",", ":")))}]}})
            attested.append({
                "message": {"content": [{
                    "type": "text",
                    "text": ("Callbacks %s and %s; recovered: complete result / "
                             "follow-up result") % (terminal_id_1, terminal_id_2),
                }]},
            })
            transcript.write_text("\n".join(map(json.dumps, attested)) + "\n")
            hidden_receipt = EVIDENCE.validate(transcript, cwd, cli)
            self.assertEqual(hidden_receipt["callback_event_ids"], [terminal_id_1, terminal_id_2])
            self.assertTrue(hidden_receipt["full_result_recovered"])

            attested_without_payload = json.loads(json.dumps(attested))
            for line in attested_without_payload:
                block = line.get("message", {}).get("content", [{}])[0]
                if block.get("type") == "text" and "CALLBACK_COMPLETION_" in block["text"]:
                    block["text"] = block["text"].split(" CALLBACK_COMPLETION_", 1)[0]
            transcript.write_text(
                "\n".join(map(json.dumps, attested_without_payload)) + "\n")
            with self.assertRaises(AssertionError):
                EVIDENCE.validate(transcript, cwd, cli)

            # Successful synchronous start/run output plus a later status event ID is
            # not proof that Claude observed either automatic callback.
            unobserved = list(without_injected_frame)
            unobserved.append({"message": {"content": [{"type": "text", "text":
                ("Command summary copied IDs %s and %s and outputs complete result / "
                 "follow-up result") % (terminal_id_1, terminal_id_2)}]}})
            transcript.write_text("\n".join(map(json.dumps, unobserved)) + "\n")
            with self.assertRaises(AssertionError):
                EVIDENCE.validate(transcript, cwd, cli)

            for forbidden in ("codex app-server", "python3 /repo/codex-worker model list", "mcp__codex__call"):
                lines[0]["message"]["content"][0]["input"]["command"] = forbidden
                transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
                with self.assertRaises(AssertionError):
                    EVIDENCE.validate(transcript, cwd, cli)


if __name__ == "__main__":
    unittest.main()
