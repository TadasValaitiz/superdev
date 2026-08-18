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
    def test_correlates_broker_results_events_and_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); cwd = root / "repo"; cwd.mkdir()
            output = cwd / "from-claude.txt"; output.write_text("created through Claude Code\n")
            cli = "/repo/codex-worker"
            sid, tid, turn = "session-1", "thread-1", "turn-1"
            commands = [
                f"python3 {cli} model list", f"python3 {cli} session start --cwd {cwd}",
                f"python3 {cli} turn start --session {sid} --model m --effort high", f"python3 {cli} turn wait --session {sid}",
                f"python3 {cli} turn events --session {sid}",
            ]
            results = [
                {"models": [{"id": "m"}]},
                {"session": {"session_id": sid, "thread_id": tid, "cwd": str(cwd.resolve()), "model": "m"}},
                {"session_id": sid, "thread_id": tid, "turn_id": turn, "status": "in_progress"},
                {"session_id": sid, "thread_id": tid, "turn": {"turn_id": turn, "status": "completed"}},
                {"events": [
                    {"event": "item_completed", "session_id": sid, "thread_id": tid, "turn_id": turn,
                     "item": {"type": "fileChange", "data": {"status": "completed", "changes": [{"path": str(output.resolve())}]}}},
                    {"event": "turn_completed", "session_id": sid, "thread_id": tid, "turn_id": turn, "item": None},
                ]},
            ]
            transcript = root / "stream.jsonl"
            lines = []
            for i, (command, result) in enumerate(zip(commands, results)):
                lines.append({"message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": command}}]}})
                lines.append({"message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "is_error": False, "content": json.dumps({"result": result})}]}})
            transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
            state = root / "sessions.json"
            state.write_text(json.dumps({"schema_version": 1, "sessions": [{"session_id": sid, "thread_id": tid, "cwd": str(cwd.resolve())}]}))
            receipt = EVIDENCE.validate(transcript, state, cwd, cli)
            self.assertEqual((receipt["session_id"], receipt["thread_id"], receipt["turn_id"]), (sid, tid, turn))

            lines[0]["message"]["content"][0]["input"]["command"] = "codex app-server"
            transcript.write_text("\n".join(map(json.dumps, lines)) + "\n")
            with self.assertRaises(AssertionError):
                EVIDENCE.validate(transcript, state, cwd, cli)


if __name__ == "__main__":
    unittest.main()
