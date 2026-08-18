# Codex worker CLI follow-up checkride — final chronological transcript

Date: 2026-08-19  
Implementation SHA: `935f612d7da41d4123b1f8b9561b685aef1b0a2d`  
Substrate: MEASURED real `codex-cli 0.147.0` (`gpt-5.6-sol`, `gpt-5.6-terra`) plus disposable git/worktree fixtures.  
Fixture honesty: the approval scenario is explicitly **deterministic live broker + fake upstream**, using the repository's fake Codex executable; it is not claimed as a real-provider approval request.  
No production code was edited by this executor. No verdict file was edited.

The six scenario launcher invocations below each record every underlying command invocation, stdout, stderr, return code, daemon lifecycle action, waiter process, and fixture operation in the linked raw JSONL transcript. Those raw transcripts are the verbatim command-level evidence; the scenario result shown here is the exact launcher stdout/stderr and exit code. Sequence numbers are preserved in each raw transcript.

## 1. Real concurrent worktrees: two completed coding tasks

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario concurrent-worktrees
```

Output (stdout):

```text
{"result": {"event_count_a": 18, "event_count_b": 22, "hello_execution": {"cursor": 15, "error": null, "event": "item_completed", "item": {"data": {"aggregatedOutput": "b'Hello from Codex\\n'\\n?? hello-output.txt\\n?? hello.py\\n", "command": "/bin/zsh -lc 'python3 hello.py && expected_file=$(mktemp /tmp/codex-hello-expected.XXXXXX) && printf 'Hello from Codex\\n' > $expected_file && cmp -s hello-output.txt $expected_file && python3 -c ... && git status --short -- hello.py hello-output.txt math_cli.py'", "cwd": ".../worktree-a", "exitCode": 0, "status": "completed"}, "item_id": "exec-af508aad-3fa0-442c-bc18-2259114b0663", "type": "commandExecution"}, "session_id": "c5227872-d4b6-4dbe-8f16-a2287191236f", "thread_id": "01a01702-3d73-7302-8b9a-359d60c87d7f", "turn_id": "01a01702-3e8f-7941-a2b6-2122cd432e2f"}, "hello_output": "Hello from Codex\\n", "math_execution": {"cursor": 16, "error": null, "event": "item_completed", "item": {"data": {"aggregatedOutput": "7\\n", "command": "/bin/zsh -lc 'python3 math_cli.py 2 5'", "cwd": ".../worktree-b", "exitCode": 0, "status": "completed"}, "item_id": "exec-47960075-5061-4be8-9996-1e97eb37248e", "type": "commandExecution"}, "session_id": "6bb5692b-4181-44bd-830a-d1688652cfef", "thread_id": "01a01702-3dea-70e0-9d51-8748d9908112", "turn_id": "01a01702-3ecc-7440-b11b-90045583f615"}, "math_output": "7\\n", "model_count": 7, "selected": [{"effort": "low", "model": "gpt-5.6-sol"}, {"effort": "medium", "model": "gpt-5.6-terra"}], "session_a": {"cwd": ".../worktree-a", "model": "gpt-5.6-sol", "name": "hello-worker", "session_id": "c5227872-d4b6-4dbe-8f16-a2287191236f", "thread_id": "01a01702-3d73-7302-8b9a-359d60c87d7f"}, "session_b": {"cwd": ".../worktree-b", "model": "gpt-5.6-terra", "name": "math-worker", "session_id": "6bb5692b-4181-44bd-830a-d1688652cfef", "thread_id": "01a01702-3dea-70e0-9d51-8748d9908112"}, "turn_a": {"status": "completed", "turn_id": "01a01702-3e8f-7941-a2b6-2122cd432e2f"}, "turn_b": {"status": "completed", "turn_id": "01a01702-3ecc-7440-b11b-90045583f615"}, "worker_b_token_absent": true}, "scenario": "concurrent-worktrees", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260818T223337.547527Z-67903-concurrent-worktrees/transcript.jsonl"}
```

Stderr: empty. Exit code: `0`.

Full chronological command/output record: `.superdev/codex-worker-live/20260818T223337.547527Z-67903-concurrent-worktrees/transcript.jsonl` (24 numbered records). It includes daemon setup/status, live model discovery, two session starts, two nonblocking turn starts, both waits, exact hello and math command/file evidence, event reads, and cleanup.

## 2. First control attempt: real timing race captured

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario control
```

Output (stdout/stderr):

```text
Traceback (most recent call last):
  File "/Users/tadas/Projects/superdev/.worktrees/codex-worker-server/tests/codex-worker/live_broker_check.py", line 959, in <module>
    raise SystemExit(main())
  File "/Users/tadas/Projects/superdev/.worktrees/codex-worker-server/tests/codex-worker/live_broker_check.py", line 935, in main
    scenario_control()
  File "/Users/tadas/Projects/superdev/.worktrees/codex-worker-server/tests/codex-worker/live_broker_check.py", line 499, in scenario_control
    steer_result = daemon.client(
  File "/Users/tadas/Projects/superdev/.worktrees/codex-worker-server/tests/codex-worker/live_broker_check.py", line 141, in client
    payload, _ = self.cli(*args, timeout=timeout, check=True)
  File "/Users/tadas/Projects/superdev/.worktrees/codex-worker-server/tests/codex-worker/live_broker_check.py", line 136, in cli
    assert completed.returncode == 0, payload
AssertionError: {'jsonrpc': '2.0', 'id': 'cli', 'error': {'code': -32020, 'message': 'Codex operation failed', 'data': {'kind': 'codex_failure', 'details': {'method': 'turn/steer', 'kind': 'upstream_error', 'details': {'code': -32600, 'message': 'no active turn to steer'}}}}}
```

Exit code: `1`. This is an observed timing race, not silently discarded.

## 3. Control rerun: steer through terminal completion and interrupt

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario control
```

Output (stdout):

```text
{"result": {"idle_interrupt_error": {"code": -32005, "data": {"details": {"latest_turn": {"error": null, "items": [], "status": "interrupted", "turn_id": "01a01704-1a8f-7561-840f-0ed8b0a952b2"}, "session_id": "b44eee0d-4a4e-48b0-aa19-78da62246874", "thread_id": "01a01703-6283-7e80-8bc6-1c1835b3d707"}, "kind": "turn_not_active"}, "message": "turn is not active"}, "idle_steer_error": {"code": -32005, "data": {"details": {"latest_turn": {"error": null, "items": [{"data": {"clientId": null, "content": [{"text": "Work only in the current directory.\\nFirst execute `python3 -c \\\"import time; time.sleep(8)\\\"` so there is time for an in-flight steer.\\nAfter that, create broad-001.txt through broad-050.txt one at a time and summarize them.\\n", "text_elements": [], "type": "text"}}], "status": "completed", "turn_id": "01a01703-62f8-77e2-9e6d-72233e465ef0"}, "session_id": "6e4784d9-a662-40a2-9f88-f8dc88521667", "thread_id": "01a01703-6211-7e52-9cd0-5195058d00db"}, "kind": "turn_not_active"}, "message": "turn is not active"}, "interrupt": {"accepted": true, "session_id": "b44eee0d-4a4e-48b0-aa19-78da62246874", "thread_id": "01a01703-6283-7e80-8bc6-1c1835b3d707", "turn_id": "01a01704-1a8f-7561-840f-0ed8b0a952b2"}, "interrupted_turn": {"status": "interrupted", "turn_id": "01a01704-1a8f-7561-840f-0ed8b0a952b2"}, "selected": [{"effort": "low", "model": "gpt-5.6-sol"}, {"effort": "medium", "model": "gpt-5.6-terra"}], "steer": {"accepted": true, "session_id": "6e4784d9-a662-40a2-9f88-f8dc88521667", "thread_id": "01a01703-6211-7e52-9cd0-5195058d00db", "turn_id": "01a01703-62f8-77e2-9e6d-72233e465ef0"}, "steered_turn": {"status": "completed", "turn_id": "01a01703-62f8-77e2-9e6d-72233e465ef0"}}, "scenario": "control", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260818T223452.475413Z-72954-control/transcript.jsonl"}
```

Stderr: empty. Exit code: `0`.

Full chronological command/output record: `.superdev/codex-worker-live/20260818T223439.733300Z-71616-control/transcript.jsonl` (first attempt, 18 numbered records, ending in the captured upstream idle race) and `.superdev/codex-worker-live/20260818T223452.475413Z-72954-control/transcript.jsonl` (rerun, 25 numbered records). The rerun includes daemon start/status, model/effort selection, steer turn start, accepted steer, terminal `completed`, exact `steered.txt` byte verification and zero broad files, idle steer refusal, interrupt turn start, accepted interrupt, terminal `interrupted`, idle interrupt refusal, and cleanup.

## 4. Pending wait, concurrent status, and two non-consuming waiters; socket safety

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario observe-socket
```

Output (stdout):

```text
{"result": {"live_collision_returncode": 1, "next_cursor": 16, "restarted_daemon_pid": 77162, "retained_first_cursor": 15, "session_id": "71b25c34-5bba-4616-8d1e-3a5d46eb091a", "socket_mode": "0600", "stale_socket_replaced": true, "tcp_listener_output": "", "truncated": true, "turn_id": "01a01704-2c8e-7bb2-9ed0-635753bade95", "waiter_status": "completed"}, "scenario": "observe-socket", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260818T223544.182306Z-75518-observe-socket/transcript.jsonl"}
```

Stderr: empty. Exit code: `0`.

Full chronological command/output record: `.superdev/codex-worker-live/20260818T223544.182306Z-75518-observe-socket/transcript.jsonl` (35 numbered records). It explicitly starts waiter A and waiter B before either completes, runs `turn status` while both waits are pending, reads a live event cursor, records both waiter results with the same turn ID/status/result, reads bounded/truncated pages, runs unfiltered `lsof -Pan -p 75533 -iTCP -sTCP:LISTEN` with exit `1` and empty output, proves socket mode `0600`, tests live socket collision, performs shutdown, stale socket replacement, restart, and final cleanup.

## 5. Deterministic approval refusal and audit, no stall

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario approvals
```

Output (stdout):

```text
{"result": {"label": "deterministic live broker + fake upstream", "modes": {"approval-command": {"approval_event": {"cursor": 2, "error": null, "event": "approval_declined", "item": {"data": {"decision": "decline"}, "item_id": "9001", "type": "item/commandExecution/requestApproval"}, "session_id": "682ab198-58f3-4d5b-8674-7c606c81ca09", "thread_id": "thr-fake", "turn_id": "turn-1"}, "approval_method": "item/commandExecution/requestApproval", "expected_upstream_response": {"decision": "decline"}, "secret_in_audit_event": false, "session_id": "682ab198-58f3-4d5b-8674-7c606c81ca09", "turn_id": "turn-1", "turn_status": "completed"}, "approval-file": {"approval_event": {"cursor": 2, "error": null, "event": "approval_declined", "item": {"data": {"decision": "decline"}, "item_id": "9001", "type": "item/fileChange/requestApproval"}, "session_id": "459d137a-39d2-4e94-8aef-340e9b47378d", "thread_id": "thr-fake", "turn_id": "turn-1"}, "approval_method": "item/fileChange/requestApproval", "expected_upstream_response": {"decision": "decline"}, "secret_in_audit_event": false, "session_id": "459d137a-39d2-4e94-8aef-340e9b47378d", "turn_id": "turn-1", "turn_status": "completed"}, "approval-user": {"approval_event": {"cursor": 2, "error": null, "event": "approval_declined", "item": {"data": {"decision": "decline"}, "item_id": "9001", "type": "item/tool/requestUserInput"}, "session_id": "8fc35bd6-3ee9-4f52-b678-3baa0bb6c5c2", "thread_id": "thr-fake", "turn_id": "turn-1"}, "approval_method": "item/tool/requestUserInput", "expected_upstream_response": {"answers": {}}, "secret_in_audit_event": false, "session_id": "8fc35bd6-3ee9-4f52-b678-3baa0bb6c5c2", "turn_id": "turn-1", "turn_status": "completed"}}}, "scenario": "approvals", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260818T223626.350312Z-77248-approvals/transcript.jsonl"}
```

Stderr: empty. Exit code: `0`.

Full chronological command/output record: `.superdev/codex-worker-live/20260818T223626.350312Z-77248-approvals/transcript.jsonl` (37 numbered records). It runs the real broker three times against the repository fake upstream, covering command approval, file approval, and user-input approval. Each turn reaches `completed`; each emits an `approval_declined` event with only the safe decline payload and no secret.

## 6. Durable UUID resume, raw-thread repair, and lifecycle chronology

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario recovery
```

Output (stdout):

```text
{"result": {"caller_supplied_cwd": false, "original_session_id": "4d54113a-b320-40c7-8b78-3162f74f7120", "raw_recovered_cwd": "/Users/tadas/Projects/superdev/.worktrees/codex-worker-server/.superdev/codex-worker-live/20260818T223633.654384Z-77390-recovery/worktree-a", "raw_recovered_session_id": "504b4e21-ee78-4303-8199-0a7141731e2e", "raw_resume_turn_id": "01a01705-81f4-70f3-a5df-b9fc79ea9a70", "raw_token_match": true, "seed_turn_id": "01a01704-edc2-74e3-ac2c-ebe0ea83f60e", "thread_id": "01a01704-ed52-77c0-9304-4b55aafcb583", "uuid_resume_session_id": "4d54113a-b320-40c7-8b78-3162f74f7120", "uuid_resume_turn_id": "01a01705-4c3a-7a72-bf11-843571d8a48c", "uuid_token_match": true}, "scenario": "recovery", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260818T223633.654384Z-77390-recovery/transcript.jsonl"}
```

Stderr: empty. Exit code: `0`.

Full chronological command/output record: `.superdev/codex-worker-live/20260818T223633.654384Z-77390-recovery/transcript.jsonl` (39 numbered records). The raw record includes every daemon shutdown/start between seed, UUID resume, and fresh-registry raw-thread repair; no caller cwd is supplied for raw repair; both resumed turns recover the remembered token and write the requested proof files.

## 7. Corrected unknown-session recovery, unsupported `--turn`, and actionable timeout

### 7.1 Fixture setup

Invocation:

```text
FOLLOWUP_ROOT=$(mktemp -d /tmp/codex-worker-followup.XXXXXX) && mkdir -p "$FOLLOWUP_ROOT/repo" && git -C "$FOLLOWUP_ROOT/repo" init -q && git -C "$FOLLOWUP_ROOT/repo" config user.email followup@example.invalid && git -C "$FOLLOWUP_ROOT/repo" config user.name Followup && printf '%s\\n' "$FOLLOWUP_ROOT" && git -C "$FOLLOWUP_ROOT/repo" rev-parse --show-toplevel
```

Output:

```text
/tmp/codex-worker-followup.6wfXQf
/private/tmp/codex-worker-followup.6wfXQf/repo
```

Exit code: `0`.

### 7.2 Explicit daemon serve

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock daemon serve --state /tmp/codex-worker-followup.6wfXQf/state.json --event-limit 40
```

Output:

```text
codex-worker daemon listening on /tmp/codex-worker-followup.6wfXQf/worker.sock
```

Exit code: foreground process remained running; final process exit was `0`.

### 7.3 Status — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock daemon status
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"ready":true,"daemon_pid":81517,"codex_pid":81519,"socket_path":"/tmp/codex-worker-followup.6wfXQf/worker.sock","state_path":"/tmp/codex-worker-followup.6wfXQf/state.json","session_count":0}}
```

Exit code: `0`.

### 7.4 Unknown UUID — structured refusal with raw-thread recovery shape

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock session show --session 00000000-0000-4000-8000-000000000000
```

```text
{"jsonrpc":"2.0","id":"cli","error":{"code":-32001,"message":"unknown session","data":{"kind":"unknown_session","recovery":"run session list to choose a known session, or recover a raw Codex thread with session resume --thread <thread-id> --name <name>","details":{"session_id":"00000000-0000-4000-8000-000000000000"}}}}
```

Exit code: `1`.

### 7.5 Unsupported `--turn` — structured refusal and selector recovery

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock turn status --turn 01a01704-ed52-77c0-9304-4b55aafcb583
```

```text
usage: codex-worker turn status [-h]
                                (--session SESSION_ID | --thread THREAD_ID)
codex-worker turn status: error: argument --turn: unsupported argument --turn; use --session <session-id> or --thread <thread-id>
{"jsonrpc":"2.0","id":null,"error":{"code":-32602,"message":"Invalid params","data":{"kind":"invalid_params","details":{"reason":"argument --turn: unsupported argument --turn; use --session <session-id> or --thread <thread-id>"}}}}
```

Exit code: `2`.

### 7.6 Timeout fixture session start — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock session start --cwd /tmp/codex-worker-followup.6wfXQf/repo --name timeout-worker --model gpt-5.6-sol
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","cwd":"/private/tmp/codex-worker-followup.6wfXQf/repo","created_at":"2026-08-18T22:37:55.819728Z","updated_at":"2026-08-18T22:37:55.819728Z","name":"timeout-worker","model":"gpt-5.6-sol","effort":null},"attached":true}}
```

Exit code: `0`.

### 7.7 Timeout fixture turn start — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock turn start --session 9a385ce7-5292-4067-89cc-ae34049dae1c --prompt 'Work only in this directory. First execute python3 -c "import time; time.sleep(12)" so the turn remains active. Then create timeout-marker.txt with exact content still-active\\n and verify it.' --model gpt-5.6-sol --effort low
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","turn_id":"01a01706-46a5-7ee0-8090-219648a4900f","status":"in_progress"}}
```

Exit code: `0`.

### 7.8 Active status while turn is pending — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock turn status --session 9a385ce7-5292-4067-89cc-ae34049dae1c
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","attached":true,"active_turn_id":"01a01706-46a5-7ee0-8090-219648a4900f","latest_turn":null}}
```

Exit code: `0`.

### 7.9 Actionable wait timeout — refusal, work remains active

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock turn wait --session 9a385ce7-5292-4067-89cc-ae34049dae1c --timeout 0
```

```text
{"jsonrpc":"2.0","id":"cli","error":{"code":-32006,"message":"timed out waiting for turn; work remains active","data":{"kind":"wait_timeout","recovery":"work remains active; run turn status/wait/steer/interrupt for session 9a385ce7-5292-4067-89cc-ae34049dae1c","details":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","turn_id":"01a01706-46a5-7ee0-8090-219648a4900f","active":true,"next_actions":["turn status --session 9a385ce7-5292-4067-89cc-ae34049dae1c","turn wait --session 9a385ce7-5292-4067-89cc-ae34049dae1c --timeout <seconds>","turn steer --session 9a385ce7-5292-4067-89cc-ae34049dae1c --prompt <text>","turn interrupt --session 9a385ce7-5292-4067-89cc-ae34049dae1c"]}}}}
```

Exit code: `1`.

#### 7.9.1 Close the original manual daemon before the fresh retry — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock daemon shutdown
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"accepted":true}}
```

Exit code: `0`.

#### 7.9.2 Verify the original manual daemon is absent — refusal/recovery

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock daemon status
```

```text
{"jsonrpc":"2.0","id":null,"error":{"code":-32000,"message":"Codex worker daemon is not available","data":{"kind":"daemon_unavailable","recovery":"run codex-worker --socket /tmp/codex-worker-followup.6wfXQf/worker.sock daemon serve","details":{"socket_path":"/tmp/codex-worker-followup.6wfXQf/worker.sock"}}}}
```

Stderr: empty. Exit code: `1`.

### 7.10 Fresh minimal timeout/completion sequence after an explicit retry daemon lifecycle

The original completion response was not preserved in the prior transcript, so this fresh sequence is recorded with new socket/turn identifiers and complete output.

#### 7.10.1 Retry daemon serve — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock daemon serve --state /tmp/codex-worker-followup.6wfXQf/state.json --event-limit 40
```

```text
codex-worker daemon listening on /tmp/codex-worker-followup.6wfXQf/retry.sock
```

Exit code: foreground process later exited `0`.

#### 7.10.2 UUID resume — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock session resume --session 9a385ce7-5292-4067-89cc-ae34049dae1c
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","cwd":"/private/tmp/codex-worker-followup.6wfXQf/repo","created_at":"2026-08-18T22:37:55.819728Z","updated_at":"2026-08-18T22:38:02.405984Z","name":"timeout-worker","model":"gpt-5.6-sol","effort":"low"},"attached":true}}
```

Exit code: `0`.

#### 7.10.3 Turn start — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock turn start --session 9a385ce7-5292-4067-89cc-ae34049dae1c --prompt 'Run python3 -c "import time; time.sleep(8)" and then report that the resumed timeout test completed. Do not modify files.' --model gpt-5.6-sol --effort low
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","turn_id":"01a0170d-da80-71a0-860a-d1223e74aca8","status":"in_progress"}}
```

Exit code: `0`.

#### 7.10.4 Active status — happy

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock turn status --session 9a385ce7-5292-4067-89cc-ae34049dae1c
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","attached":true,"active_turn_id":"01a0170d-da80-71a0-860a-d1223e74aca8","latest_turn":null}}
```

Exit code: `0`.

#### 7.10.5 Actionable timeout — refusal

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock turn wait --session 9a385ce7-5292-4067-89cc-ae34049dae1c --timeout 0
```

```text
{"jsonrpc":"2.0","id":"cli","error":{"code":-32006,"message":"timed out waiting for turn; work remains active","data":{"kind":"wait_timeout","recovery":"work remains active; run turn status/wait/steer/interrupt for session 9a385ce7-5292-4067-89cc-ae34049dae1c","details":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","turn_id":"01a0170d-da80-71a0-860a-d1223e74aca8","active":true,"next_actions":["turn status --session 9a385ce7-5292-4067-89cc-ae34049dae1c","turn wait --session 9a385ce7-5292-4067-89cc-ae34049dae1c --timeout <seconds>","turn steer --session 9a385ce7-5292-4067-89cc-ae34049dae1c --prompt <text>","turn interrupt --session 9a385ce7-5292-4067-89cc-ae34049dae1c"]}}}}
```

Exit code: `1`.

#### 7.10.6 Completion wait — happy, complete verbatim JSON

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock turn wait --session 9a385ce7-5292-4067-89cc-ae34049dae1c --timeout 30
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"9a385ce7-5292-4067-89cc-ae34049dae1c","thread_id":"01a01706-2ca0-7440-94b6-2ff6f133fc3b","turn":{"turn_id":"01a0170d-da80-71a0-860a-d1223e74aca8","status":"completed","error":null,"items":[{"item_id":"01a0170d-dc76-7891-8689-9322ccd03657","type":"userMessage","data":{"clientId":null,"content":[{"type":"text","text":"Run python3 -c \"import time; time.sleep(8)\" and then report that the resumed timeout test completed. Do not modify files.","text_elements":[]}]}},{"item_id":"rs_02c59fb87f7bb32b016a84e0bd60108191870eb839eed6c21c","type":"reasoning","data":{"summary":[],"content":[]}},{"item_id":"msg_02c59fb87f7bb32b016a84e0be375c8191bb01a8d240a5b6a8","type":"agentMessage","data":{"text":"I’ll run the requested 8-second delay without modifying any files, then report its completion.","phase":"commentary","memoryCitation":null}},{"item_id":"exec-0d3e192e-89ba-46e0-8ca5-3d2835d5a1ab","type":"commandExecution","data":{"pluginId":null,"scriptPath":null,"command":"/bin/zsh -lc 'python3 -c \"import time; time.sleep(8)\"'","cwd":"/private/tmp/codex-worker-followup.6wfXQf/repo","processId":"4790","source":"unifiedExecStartup","status":"completed","commandActions":[{"type":"unknown","command":"python3 -c \"import time; time.sleep(8)\""}],"aggregatedOutput":null,"exitCode":0,"durationMs":8018}},{"item_id":"msg_02c59fb87f7bb32b016a84e0c9ada88191a12ab12676885b4b","type":"agentMessage","data":{"text":"The resumed timeout test completed successfully. No files were modified.","phase":"final_answer"}}]}}}
```

Exit code: `0`.

### 7.11 Cleanup shutdown and explicit post-shutdown status

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock daemon shutdown
```

```text
{"jsonrpc":"2.0","id":"cli","result":{"accepted":true}}
```

Exit code: `0`.

Post-shutdown status invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock daemon status
```

Post-shutdown stdout:

```text
{"jsonrpc":"2.0","id":null,"error":{"code":-32000,"message":"Codex worker daemon is not available","data":{"kind":"daemon_unavailable","recovery":"run codex-worker --socket /tmp/codex-worker-followup.6wfXQf/retry.sock daemon serve","details":{"socket_path":"/tmp/codex-worker-followup.6wfXQf/retry.sock"}}}}
```

Post-shutdown stderr: empty. Exit code: `1`. No daemon or Codex child remained.

## Receipt

- Follow-up launcher commands: `6` scenario commands (`5` passed, `1` first control race), plus `19` manual lifecycle/selector/timeout commands: `11` in the original setup/selector/timeout sequence including its explicit shutdown/status closure, and `8` in the fresh retry sequence. The original manual sequence has `9` successful/expected results and `2` expected daemon-unavailable/timeout refusals; the fresh retry has `6` successful/expected results and `2` expected timeout/daemon-unavailable refusals.
- Underlying recorded commands: concurrent worktrees `24`, control first attempt `18` (15 commands + prompt-file record + daemon start/exit; failed race) plus rerun `25`, observe/socket `35`, approvals `37`, recovery `39`; all raw records are chronological and preserved under `.superdev/codex-worker-live/`.
- Real models/efforts: `gpt-5.6-sol/low` and `gpt-5.6-terra/medium` from live discovery; both completed distinct code tasks in distinct linked worktrees with no crossed files.
- Steer proof: exact `steered.txt` content `steer accepted\\n`, zero `broad-*.txt`, terminal status `completed`.
- Wait proof: one pending wait permitted concurrent status/events; two simultaneous waiters returned identical turn ID, terminal status, and result; bounded event cursor/truncation was exercised.
- Approval proof: fake upstream command/file/user-input approval requests declined, audited, secret-free, and terminal `completed`; fixture mechanism clearly labeled above.
- Socket proof: socket mode `0600`; unfiltered `lsof -Pan -p 75533 -iTCP -sTCP:LISTEN` returned exit `1` and empty output; live collision and stale replacement were exercised.
- Recovery proof: UUID resume and raw-thread repair included every daemon shutdown/start; corrected unknown-session response points to `session list` or `session resume --thread <thread-id> --name <name>`.
- Cleanup: all scenario daemons and the manual daemon were shut down; final daemon status was unavailable; no production files were modified or committed.
