#!/usr/bin/env python3
"""Validate that Claude drove codex-worker successfully and only through the broker."""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


Json = Dict[str, Any]


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)


def _json_content(content: Any) -> Json:
    if isinstance(content, str):
        parsed = json.loads(content)
    elif isinstance(content, list):
        text = "".join(
            str(block.get("text", "")) for block in content if isinstance(block, dict)
        )
        parsed = json.loads(text)
    else:
        raise AssertionError("Bash tool result was not JSON text")
    assert isinstance(parsed, dict), parsed
    return parsed


def validate(transcript: Path, state_path: Path, cwd: Path, cli: str) -> Json:
    tool_commands = {}  # type: Dict[str, str]
    tool_results = {}  # type: Dict[str, Json]
    all_commands = []  # type: List[str]
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        document = json.loads(line)
        for value in _walk(document):
            if value.get("type") == "tool_use" and value.get("name") == "Bash":
                command = value.get("input", {}).get("command")
                if isinstance(command, str):
                    all_commands.append(command)
                    tool_commands[str(value.get("id", ""))] = command
            elif value.get("type") == "tool_result":
                tool_id = str(value.get("tool_use_id", ""))
                if tool_id in tool_commands:
                    assert value.get("is_error") is not True, value
                    tool_results[tool_id] = _json_content(value.get("content"))

    joined = "\n".join(all_commands)
    assert cli in joined, all_commands
    direct_codex = re.compile(r"(?:^|[;&|]\s*|\s)codex(?:\s|$)")
    assert not any(direct_codex.search(command) for command in all_commands), all_commands
    required = ("model list", "session start", "turn start", "turn wait", "turn events")
    assert all(any(fragment in command for command in all_commands) for fragment in required), all_commands

    broker_results = []  # type: List[Json]
    broker_commands = []  # type: List[str]
    for tool_id, command in tool_commands.items():
        if cli not in command:
            continue
        envelope = tool_results.get(tool_id)
        assert envelope is not None, {"command": command, "reason": "missing Bash tool result"}
        assert "error" not in envelope and isinstance(envelope.get("result"), dict), envelope
        broker_results.append(envelope["result"])
        broker_commands.append(command)

    session_result = next(result for result in broker_results if isinstance(result.get("session"), dict))
    session = session_result["session"]
    sid, tid = session["session_id"], session["thread_id"]
    assert session["cwd"] == str(cwd.resolve()), session
    start_result = next(
        result for result in broker_results
        if result.get("status") == "in_progress" and result.get("turn_id")
    )
    turn_id = start_result["turn_id"]
    assert start_result["session_id"] == sid and start_result["thread_id"] == tid, start_result
    wait_result = next(result for result in broker_results if isinstance(result.get("turn"), dict))
    turn = wait_result["turn"]
    assert turn["status"] == "completed", turn
    assert (wait_result["session_id"], wait_result["thread_id"], turn["turn_id"]) == (sid, tid, turn_id), wait_result
    turn_start_command = next(command for command in broker_commands if "turn start" in command)
    model_match = re.search(r"--model(?:=|\s+)([^\s]+)", turn_start_command)
    effort_match = re.search(r"--effort(?:=|\s+)([^\s]+)", turn_start_command)
    assert model_match and effort_match, turn_start_command
    selected_model = model_match.group(1).strip("'\"")
    selected_effort = effort_match.group(1).strip("'\"")
    assert session.get("model") in (None, selected_model), session
    event_result = next(result for result in broker_results if isinstance(result.get("events"), list))
    events = event_result["events"]
    correlated = [
        event for event in events
        if (event.get("session_id"), event.get("thread_id"), event.get("turn_id")) == (sid, tid, turn_id)
    ]
    assert len(correlated) == len(events) and events, events
    assert any(event.get("event") == "turn_completed" for event in events), events
    expected_file = str((cwd / "from-claude.txt").resolve())
    file_events = []
    for event in events:
        item = event.get("item") or {}
        data = item.get("data") or {}
        if item.get("type") == "fileChange" and data.get("status") == "completed":
            if any(change.get("path") == expected_file for change in data.get("changes", [])):
                file_events.append(event)
    assert file_events, {"expected_file": expected_file, "events": events}
    assert (cwd / "from-claude.txt").read_bytes() == b"created through Claude Code\n"

    registry = json.loads(state_path.read_text(encoding="utf-8"))
    matches = [
        record for record in registry.get("sessions", [])
        if record.get("session_id") == sid and record.get("thread_id") == tid
        and record.get("cwd") == str(cwd.resolve())
    ]
    assert len(matches) == 1, {"expected": [sid, tid, str(cwd.resolve())], "registry": registry}
    return {
        "session_id": sid, "thread_id": tid, "turn_id": turn_id,
        "model": selected_model, "effort": selected_effort,
        "terminal_status": turn["status"], "event_count": len(events),
        "file_change_cursor": file_events[0].get("cursor"),
        "broker_commands": broker_commands,
        "registry_session_persisted": True,
        "direct_codex_invocation": False,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = validate(args.transcript, args.state, args.cwd, args.cli)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
