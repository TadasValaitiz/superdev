# Codex worker CLI follow-up checkride — final evidence transcript

Date: 2026-08-19  
Implementation SHA: `55c630d399efad2b520a2d4b9b037987c6ba98b7`
Substrate: MEASURED real `codex-cli 0.147.0` (`gpt-5.6-sol`, `gpt-5.6-terra`) plus disposable git/worktree fixtures.  
Fixture honesty: the approval scenario is explicitly **deterministic live broker + fake upstream**, using the repository's fake Codex executable; it is not claimed as a real-provider approval request.  
No production code was edited by this executor. No verdict file was edited. Each scenario and manual lifecycle is chronological within its own captured record; the independent sections are not one shared wall-clock chronology.

The six scenario launcher invocations below each preserve client command streams, return codes, daemon lifecycle metadata, waiter processes, and fixture operations in the linked raw JSONL transcript. The raw JSONLs are verbatim client command-level evidence; daemon-start lifecycle metadata is supplemented by the tracked manual stream record [manual-f1-streams.md](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams.md), which preserves foreground serve stdout and stderr separately. Scenario summaries explicitly labeled synopsis are not claimed as verbatim launcher output.

## 1. Real concurrent worktrees: two completed coding tasks

Invocation:

```text
python3 tests/codex-worker/live_broker_check.py --scenario concurrent-worktrees
```

Launcher result synopsis (not a verbatim reproduction; the complete command-level stdout/stderr is preserved in the tracked raw record below):

```text
{"result": {"event_count_a": 18, "event_count_b": 22, "hello_execution": {"cursor": 15, "error": null, "event": "item_completed", "item": {"data": {"aggregatedOutput": "b'Hello from Codex\\n'\\n?? hello-output.txt\\n?? hello.py\\n", "command": "/bin/zsh -lc 'python3 hello.py && expected_file=$(mktemp /tmp/codex-hello-expected.XXXXXX) && printf 'Hello from Codex\\n' > $expected_file && cmp -s hello-output.txt $expected_file && [fixture hello.py verification omitted from synopsis] && git status --short -- hello.py hello-output.txt math_cli.py'", "cwd": "[fixture]/worktree-a", "exitCode": 0, "status": "completed"}, "item_id": "exec-af508aad-3fa0-442c-bc18-2259114b0663", "type": "commandExecution"}, "session_id": "c5227872-d4b6-4dbe-8f16-a2287191236f", "thread_id": "01a01702-3d73-7302-8b9a-359d60c87d7f", "turn_id": "01a01702-3e8f-7941-a2b6-2122cd432e2f"}, "hello_output": "Hello from Codex\\n", "math_execution": {"cursor": 16, "error": null, "event": "item_completed", "item": {"data": {"aggregatedOutput": "7\\n", "command": "/bin/zsh -lc 'python3 math_cli.py 2 5'", "cwd": "[fixture]/worktree-b", "exitCode": 0, "status": "completed"}, "item_id": "exec-47960075-5061-4be8-9996-1e97eb37248e", "type": "commandExecution"}, "session_id": "6bb5692b-4181-44bd-830a-d1688652cfef", "thread_id": "01a01702-3dea-70e0-9d51-8748d9908112", "turn_id": "01a01702-3ecc-7440-b11b-90045583f615"}, "math_output": "7\\n", "model_count": 7, "selected": [{"effort": "low", "model": "gpt-5.6-sol"}, {"effort": "medium", "model": "gpt-5.6-terra"}], "session_a": {"cwd": "[fixture]/worktree-a", "model": "gpt-5.6-sol", "name": "hello-worker", "session_id": "c5227872-d4b6-4dbe-8f16-a2287191236f", "thread_id": "01a01702-3d73-7302-8b9a-359d60c87d7f"}, "session_b": {"cwd": "[fixture]/worktree-b", "model": "gpt-5.6-terra", "name": "math-worker", "session_id": "6bb5692b-4181-44bd-830a-d1688652cfef", "thread_id": "01a01702-3dea-70e0-9d51-8748d9908112"}, "turn_a": {"status": "completed", "turn_id": "01a01702-3e8f-7941-a2b6-2122cd432e2f"}, "turn_b": {"status": "completed", "turn_id": "01a01702-3ecc-7440-b11b-90045583f615"}, "worker_b_token_absent": true}, "scenario": "concurrent-worktrees", "status": "PASS", "transcript": "2026-08-19-codex-worker-checkride-evidence/concurrent-worktrees.jsonl"}
```

Stderr: empty. Exit code: `0`.

Full chronological command/output record: [concurrent-worktrees.jsonl](2026-08-19-codex-worker-checkride-evidence/concurrent-worktrees.jsonl) (24 numbered records; tracked verbatim). It includes daemon setup/status, live model discovery, two session starts, two nonblocking turn starts, both waits, exact hello and math command/file evidence, event reads, and cleanup.

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

Full chronological command/output records: [control-first-race.jsonl](2026-08-19-codex-worker-checkride-evidence/control-first-race.jsonl) (18 numbered records, first attempt, ending in the captured upstream idle race) and [control-current.jsonl](2026-08-19-codex-worker-checkride-evidence/control-current.jsonl) (25 numbered records, fresh rerun, tracked verbatim). The fresh rerun passed with `gpt-5.6-sol/low` and `gpt-5.6-terra/medium`; it includes accepted steer and terminal `completed`, exact `steered.txt` byte verification and zero broad files, typed idle-steer `turn_not_active`, accepted interrupt and terminal `interrupted`, typed idle-interrupt `turn_not_active`, and cleanup.

Fresh rerun identity (the inline launcher result above is retained from the earlier passing rerun; the current run's complete command-level output is the tracked raw record): steer session `af6fba0b-b9e8-46b3-abe6-1197950dc092`, thread `01a0172a-baea-72c3-b23c-533d50388024`, turn `01a0172a-bbe2-7842-8044-ff42c140332c`; interrupt session `1665902f-07ae-4631-a07f-553c91964a2f`, thread `01a0172a-bb65-7c60-ac62-50a1b5a3578d`, turn `01a0172b-6f54-7763-8762-1f271a767fc1`. The fresh launcher exited `0` with scenario `control` `PASS`; its final interrupt and idle-control responses are `completed`/`interrupted` and typed `turn_not_active` respectively.

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

Full chronological command/output record: [observe-socket.jsonl](2026-08-19-codex-worker-checkride-evidence/observe-socket.jsonl) (35 numbered records, tracked verbatim). It explicitly starts waiter A and waiter B before either completes, runs `turn status` while both waits are pending, reads a live event cursor, records both waiter results with the same turn ID/status/result, reads bounded/truncated pages, runs unfiltered `lsof -Pan -p 75533 -iTCP -sTCP:LISTEN` with exit `1` and empty output, proves socket mode `0600`, tests live socket collision, performs shutdown, stale socket replacement, restart, and final cleanup.

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

Full chronological command/output record: [approvals.jsonl](2026-08-19-codex-worker-checkride-evidence/approvals.jsonl) (37 numbered records, tracked verbatim). It runs the real broker three times against the repository fake upstream, covering command approval, file approval, and user-input approval. Each turn reaches `completed`; each emits an `approval_declined` event with only the safe decline payload and no secret.

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

Full chronological command/output record: [recovery.jsonl](2026-08-19-codex-worker-checkride-evidence/recovery.jsonl) (39 numbered records, tracked verbatim). The raw record includes every daemon shutdown/start between seed, UUID resume, and fresh-registry raw-thread repair; no caller cwd is supplied for raw repair; both resumed turns recover the remembered token and write the requested proof files.

## 7. Fresh manual lifecycle: refusal, timeout, completion, shutdown

This independent fresh lifecycle is recorded in exact command order against socket /tmp/cw-f1.SnZYn7/worker.sock. Every command has separate byte-level stdout and stderr captures in [manual-f1-streams.md](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams.md). Session: 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39. Thread: 01a01736-3b08-7223-b22a-9ea4d78f12b8. Turn: 01a01736-6f07-7b70-9685-c67893e8bdb9.

### 7.1 Foreground daemon serve

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock daemon serve --state /tmp/cw-f1.SnZYn7/state.json --event-limit 40

Exit 0 after foreground shutdown. stdout: [serve.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/serve.stdout), 0 bytes, empty. stderr: [serve.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/serve.stderr), 63 bytes, codex-worker daemon listening on /tmp/cw-f1.SnZYn7/worker.sock followed by newline.

### 7.2 Unknown-session refusal

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock session show --session 00000000-0000-4000-8000-000000000000

Exit 1. stdout: [unknown.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/unknown.stdout), 321 bytes, structured unknown_session JSON. stderr: [unknown.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/unknown.stderr), 0 bytes, empty.

### 7.3 Unsupported turn selector refusal

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn status --turn 11111111-1111-4111-8111-111111111111

Exit 2. stdout: [unsupported.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/unsupported.stdout), 232 bytes, structured invalid-params JSON. stderr: [unsupported.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/unsupported.stderr), 243 bytes, argparse usage and diagnostic. These streams are separate and not merged.

### 7.4 Session start

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock session start --cwd /tmp/cw-f1.SnZYn7/repo --name f1-timeout --model gpt-5.6-sol

Exit 0. stdout: [start.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/start.stdout), 352 bytes, session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39. stderr: [start.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/start.stderr), 0 bytes.

### 7.5 Turn start

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn start --session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39 --prompt-file /tmp/cw-f1.SnZYn7/prompt.txt --model gpt-5.6-sol --effort low

Exit 0. stdout: [turn-start.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/turn-start.stdout), 215 bytes, turn 01a01736-6f07-7b70-9685-c67893e8bdb9 in progress. stderr: [turn-start.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/turn-start.stderr), 0 bytes.

### 7.6 Active wait timeout

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn wait --session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39 --timeout 0.01

Exit 1. stdout: [timeout.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/timeout.stdout), 688 bytes, actionable wait_timeout JSON identifying the active turn and next actions. stderr: [timeout.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/timeout.stderr), 0 bytes.

### 7.7 Completion wait

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn wait --session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39 --timeout 30

Exit 0. stdout: [completion.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/completion.stdout), 9280 bytes, complete terminal completed JSON. stderr: [completion.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/completion.stderr), 0 bytes.

### 7.8 Shutdown

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock daemon shutdown

Exit 0. stdout: [shutdown.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/shutdown.stdout), 56 bytes, accepted true JSON. stderr: [shutdown.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/shutdown.stderr), 0 bytes.

### 7.9 Post-shutdown status

Invocation: python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock daemon status

Exit 1. stdout: [post-status.stdout](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/post-status.stdout), 278 bytes, structured daemon_unavailable JSON. stderr: [post-status.stderr](2026-08-19-codex-worker-checkride-evidence/manual-f1-streams/post-status.stderr), 0 bytes. No daemon or Codex child remained.

## 8. Live `session list` with two sessions

This is a separate independent lifecycle, not a chronological continuation of §7. It records six client commands against its own already-running foreground daemon after creating two disposable linked worktrees. `list-alpha` used `gpt-5.6-sol` in `wt-a`; `list-beta` used `gpt-5.6-terra` in `wt-b`. The original ride did not preserve daemon startup streams; §7 separately provides representative foreground serve proof. The full six-command invocation, stdout, stderr, exit code, shutdown, and post-shutdown status are preserved in [manual-session-list.md](2026-08-19-codex-worker-checkride-evidence/manual-session-list.md). The `session list` result contains both UUID session IDs, thread IDs, names, models, worktree paths, and null active-turn state. This closes the client-method coverage for `session list` with live evidence.

## Receipt

- Scenario commands: `6` launcher scenarios (`5` passed, `1` first control race). Manual §7 lifecycle commands: `9`, with `5` exit-0 results and `4` expected nonzero refusal/timeout results. The independent §8 session-list record contains `6` client commands.
- Underlying recorded commands: concurrent worktrees `24`, control first attempt `18` (15 commands + prompt-file record + daemon start/exit; failed race) plus fresh rerun `25`, observe/socket `35`, approvals `37`, recovery `39`; all six raw records are chronological, verbatim, and tracked under `2026-08-19-codex-worker-checkride-evidence/`. The independent session-list record contains six separately captured client invocations; foreground serve proof is separate in §7.
- Real models/efforts: `gpt-5.6-sol/low` and `gpt-5.6-terra/medium` from live discovery; both completed distinct code tasks in distinct linked worktrees with no crossed files.
- Steer proof: exact `steered.txt` content `steer accepted\\n`, zero `broad-*.txt`, terminal status `completed`.
- Wait proof: one pending wait permitted concurrent status/events; two simultaneous waiters returned identical turn ID, terminal status, and result; bounded event cursor/truncation was exercised.
- Approval proof: fake upstream command/file/user-input approval requests declined, audited, secret-free, and terminal `completed`; fixture mechanism clearly labeled above.
- Socket proof: socket mode `0600`; unfiltered `lsof -Pan -p 75533 -iTCP -sTCP:LISTEN` returned exit `1` and empty output; live collision and stale replacement were exercised.
- Recovery proof: UUID resume and raw-thread repair included every daemon shutdown/start; corrected unknown-session response points to `session list` or `session resume --thread <thread-id> --name <name>`.
- Session-list proof: two live sessions were listed together from distinct linked worktrees, with full UUID/thread/model/cwd records and no active turns.
- Cleanup: all scenario daemons and the manual daemon were shut down; final daemon status was unavailable; no production files were modified or committed.
