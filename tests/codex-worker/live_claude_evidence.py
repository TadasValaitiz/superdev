#!/usr/bin/env python3
"""Validate that Claude drove only the PATH common codex-worker surface."""

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


def _completion(result: Json) -> Json:
    required = {"worker", "turn", "messages", "structured_output", "metrics", "recovery"}
    assert set(result) == required, result
    assert result["turn"]["status"] == "completed", result["turn"]
    assert isinstance(result["messages"], list) and result["messages"], result
    for metric in result["metrics"].values():
        assert set(metric) == {"value", "source", "availability"}, metric
        assert metric["source"] and metric["availability"] in {
            "measured", "reported", "derived", "unavailable",
        }
    return result["worker"]


def validate(transcript: Path, cwd: Path, cli: str) -> Json:
    tool_commands = {}  # type: Dict[str, str]
    tool_results = {}  # type: Dict[str, Json]
    all_commands = []  # type: List[str]
    callback_events = []  # type: List[Json]
    assistant_text = []  # type: List[str]
    assistant_text_records = []  # type: List[tuple]
    tool_result_positions = {}  # type: Dict[str, int]
    for record_index, line in enumerate(
            transcript.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        document = json.loads(line)
        for candidate in _walk(document):
            if candidate.get("type") == "text" and isinstance(candidate.get("text"), str):
                assistant_text.append(candidate["text"])
                assistant_text_records.append((record_index, candidate["text"]))
        for candidate in _walk(document):
            if (candidate.get("schema") == "codex-worker.claude-callback/v1"
                    and candidate.get("event") in ("turn_terminal", "turn_terminal_reference")):
                callback_events.append(candidate)
        for candidate in _walk(document):
            content = candidate.get("content")
            if isinstance(content, str):
                try:
                    parsed_content = json.loads(content)
                except ValueError:
                    continue
                if (isinstance(parsed_content, dict)
                        and parsed_content.get("schema") == "codex-worker.claude-callback/v1"
                        and parsed_content.get("event") in ("turn_terminal", "turn_terminal_reference")):
                    callback_events.append(parsed_content)
        for value in _walk(document):
            if value.get("type") == "tool_use":
                assert value.get("name") == "Bash", value
                command = value.get("input", {}).get("command")
                assert isinstance(command, str), value
                all_commands.append(command)
                tool_commands[str(value.get("id", ""))] = command
            elif value.get("type") == "tool_result":
                tool_id = str(value.get("tool_use_id", ""))
                if tool_id in tool_commands:
                    assert value.get("is_error") is not True, value
                    tool_results[tool_id] = _json_content(value.get("content"))
                    tool_result_positions[tool_id] = record_index

    assert all_commands, all_commands
    direct_codex = re.compile(r"(?:^|[;&|]\s*|\s)codex(?:\s|$)")
    assert not any(direct_codex.search(command) for command in all_commands), all_commands
    assert not any("mcp__" in command.lower() for command in all_commands), all_commands
    assert not any("--socket" in command for command in all_commands), all_commands
    assert not any(re.search(r"(?:^|\s)(?:python3\s+)?/\S*codex-worker(?:\s|$)", command)
                   for command in all_commands), all_commands
    assert all(re.search(r"(?:^|[;&|]\s*|\s)%s(?:\s|$)" % re.escape(cli), command)
               for command in all_commands), all_commands
    assert not any(re.search(r"\bcodex-worker\s+(?:--instance\s+\S+\s+)?(?:model|session|turn)\b", command)
                   for command in all_commands), all_commands
    required = (" start ", " message ", " run ", " goal show ", " history ", " status ", " daemon stop")
    assert all(any(fragment in command for command in all_commands) for fragment in required), all_commands

    broker_results = []  # type: List[Json]
    broker_commands = []  # type: List[str]
    for tool_id, command in tool_commands.items():
        envelope = tool_results.get(tool_id)
        assert envelope is not None, {"command": command, "reason": "missing Bash tool result"}
        assert "error" not in envelope and isinstance(envelope.get("result"), dict), envelope
        broker_results.append(envelope["result"])
        broker_commands.append(command)

    start_result = next(result for result, command in zip(broker_results, broker_commands)
                        if " start " in command)
    run_result = next(result for result, command in zip(broker_results, broker_commands)
                      if " run " in command)
    start_worker = _completion(start_result)
    run_worker = _completion(run_result)
    sid, tid = start_worker["session_id"], start_worker["thread_id"]
    turn_id = start_result["turn"]["turn_id"]
    assert start_worker["cwd"] == str(cwd.resolve()), start_worker
    assert start_worker == run_worker, (start_worker, run_worker)
    assert start_worker["tier"] == "medium" and start_worker["model"] == "gpt-5.6-terra"
    assert start_worker["effort"] == "medium" and start_worker["access"] == "full"
    assert re.search(r"-[A-Za-z0-9]{6,}$", start_worker["name"]), start_worker["name"]
    history = next(result for result, command in zip(broker_results, broker_commands)
                   if " history " in command)
    assert history["worker"] == start_worker and isinstance(history["turns"], list), history
    status = next(result for result, command in zip(broker_results, broker_commands)
                  if " status " in command)
    assert status["worker"] == start_worker and status["daemon_status"] == "ready", status
    assert status["callback"]["state"] == "enabled", status
    assert status["callback"]["last_terminal_attempt"]["state"] == "written", status
    stop = next(result for result, command in zip(broker_results, broker_commands)
                if " daemon stop" in command)
    assert stop["status_after"] == "stopped" and stop["durable_state"] == "preserved", stop
    unique_callbacks = {event["event_id"]: event for event in callback_events}
    full_text = "\n".join(assistant_text)
    reported_ids = list(dict.fromkeys(re.findall(r"terminal-[0-9a-f]{64}", full_text)))
    callback_ids = sorted(unique_callbacks)
    recovered = False
    if unique_callbacks:
        recovered_completions = [event.get("payload", {}).get("completion")
                                 for event in unique_callbacks.values()]
        recovered = start_result in recovered_completions and run_result in recovered_completions
    else:
        attestation_pattern = re.compile(
            r"Callback\s+#?([12])\s+received"
            r"(?:\s+\(`(terminal-[0-9a-f]{8,64})(?:\.\.\.)?`\))?")
        attestations = {}  # type: Dict[int, tuple]
        for position, value in assistant_text_records:
            match = attestation_pattern.search(value)
            if match:
                number = int(match.group(1))
                assert number not in attestations, {"duplicate_callback_attestation": number}
                marker = "CALLBACK_COMPLETION_%d=" % number
                assert marker in value, {"callback_attestation_missing_completion": number}
                raw_completion = value.split(marker, 1)[1].lstrip()
                completion, end = json.JSONDecoder().raw_decode(raw_completion)
                assert not raw_completion[end:].strip(), {
                    "callback_attestation_trailing_text": number}
                assert isinstance(completion, dict), completion
                attestations[number] = (position, match.group(2), completion)
        assert set(attestations) == {1, 2}, {"callback_attestations": attestations}
        matched_ids = []  # type: List[str]
        for number in (1, 2):
            prefix = attestations[number][1]
            if prefix:
                matches = [event_id for event_id in reported_ids if event_id.startswith(prefix)]
                assert len(matches) == 1, {"attestation": number, "prefix": prefix,
                                           "reported_ids": reported_ids}
                matched_ids.append(matches[0])
            else:
                assert len(reported_ids) == 2, {"attestation": number,
                                                "reported_ids": reported_ids}
                matched_ids.append(reported_ids[number - 1])
        assert matched_ids[0] != matched_ids[1], matched_ids
        start_tool_id = next(tool_id for tool_id, command in tool_commands.items()
                             if " start " in command)
        run_tool_id = next(tool_id for tool_id, command in tool_commands.items()
                           if " run " in command)
        start_position = tool_result_positions[start_tool_id]
        run_position = tool_result_positions[run_tool_id]
        assert start_position < attestations[1][0] < run_position, attestations
        assert run_position < attestations[2][0], attestations
        callback_ids = matched_ids
        recovered = (attestations[1][2] == start_result
                     and attestations[2][2] == run_result)
    assert callback_ids, {"callback_events": callback_events, "assistant_text": assistant_text}
    assert status["callback"]["last_terminal_attempt"]["event_id"] in callback_ids
    assert recovered, {"callbacks": unique_callbacks, "reported_ids": reported_ids}
    return {
        "session_id": sid, "thread_id": tid, "turn_id": turn_id,
        "worker_name": start_worker["name"],
        "model": start_worker["model"], "effort": start_worker["effort"],
        "terminal_status": start_result["turn"]["status"],
        "message_count": len(start_result["messages"]) + len(run_result["messages"]),
        "broker_commands": broker_commands,
        "durable_state": stop["durable_state"],
        "native_claude_available": True,
        "direct_codex_invocation": False,
        "mcp_invocation": False,
        "raw_codex_worker_invocation": False,
        "callback_event_ids": callback_ids,
        "full_result_recovered": recovered,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = validate(args.transcript, args.cwd, args.cli)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
