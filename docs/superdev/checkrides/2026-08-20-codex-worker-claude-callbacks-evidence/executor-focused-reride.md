# Callback CLI focused re-ride — executor transcript

Date: 2026-08-20
Commit under ride: `9937c8e`
Substrate/tier: **MEASURED** local `codex-cli` through this worktree's `bin/codex-worker`, real local managed daemons, and the measured-shape local Claude registry/inbox fixture in `tests/codex-worker/live_broker_check.py`. The fixture is same-machine AF_UNIX receipt capture, not a Claude-delivery claim. Callback authentication tokens are replaced by `[REDACTED]` in the committed harness JSONL.

Each section is one literal top-level invocation, captured serially. The linked scenario JSONL is the complete sanitized harness record of every CLI subprocess it drove, including callback frames and their destination labels.

## 1. Callback-security refusal suite — refusal paths

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH python3 tests/codex-worker/live_broker_check.py --scenario callback-security`

```text
STDOUT:
{"result": {"ambiguous_kind": "callback_target_ambiguous", "credential_scrubbed": true, "disabled_kind": "callback_unavailable", "pid_reuse_kind": "callback_target_stale", "public_secret_scan": "absent", "stale_kind": "callback_target_stale", "unicode_oversize_kind": "callback_payload_too_large"}, "scenario": "callback-security", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260820T145955.794025Z-10823-callback-security/transcript.jsonl"}
STDERR:
EXIT: 0
```

Complete sanitized callback-frame and subprocess record: [callback-security/transcript.jsonl](focused-reride/callback-security/transcript.jsonl).

## 2. Callback-proactive inline/file/priorities/alternate — happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH python3 tests/codex-worker/live_broker_check.py --scenario callback-proactive`

```text
STDOUT:
{"result": {"alternate_event_id": "8fbeb0dc-9af6-4447-aea0-24482852669b", "file_event_id": "31c25642-d8d8-48c6-8064-82269b632415", "follow_terminal_event_id": "terminal-ff381c5e9eaa912897fea68acf606ef335843d9b6809379412f7d4aac638232d", "origin_preserved": true, "priorities": ["now", "later"], "proactive_event_id": "972c1c78-7498-41b5-932f-fee06ac9b7f3", "steer_accepted": true, "terminal_event_id": "terminal-c83622ca906ffe64c660d54bf6cfdea194d83d0e92bcd389d66342f0cbcc49c2"}, "scenario": "callback-proactive", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260820T150030.775192Z-12969-callback-proactive/transcript.jsonl"}
STDERR:
EXIT: 0
```

Complete sanitized callback-frame and subprocess record: [callback-proactive/transcript.jsonl](focused-reride/callback-proactive/transcript.jsonl).

## 3. Persisted origin retention — happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH python3 tests/codex-worker/live_broker_check.py --scenario callback-origin-retention`

```text
STDOUT:
{"result": {"origin_event_ids": ["terminal-f105925097d50b461a46a61dff712eccca623453e916e16947b84ac86fc3820b", "terminal-c08db0773e80f15e5eb1deb9e06163d103617367daa2c1ba3e5fffa85d1e2296", "terminal-25bf8ab7223be8670dace7ae87fbbd0b97b78f00fc3c25e4d9252bc263c535e8"], "persisted_origin_only": true, "replacement_frame_count": 0}, "scenario": "callback-origin-retention", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260820T150105.221297Z-14808-callback-origin-retention/transcript.jsonl"}
STDERR:
EXIT: 0
```

Complete sanitized callback-frame and subprocess record: [callback-origin-retention/transcript.jsonl](focused-reride/callback-origin-retention/transcript.jsonl).

## 4. Restart/recovery/artifact/raw-session-turn — happy and recovery paths

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH python3 tests/codex-worker/live_broker_check.py --scenario callback-recovery`

```text
STDOUT:
{"result": {"artifact_event_id": "terminal-f035e30682be008c9200614918ec88809c6f0b4ddfb3b6923ba9169e3d36e17a", "artifact_readback_verified": true, "artifact_sha256": "5c880367941b1f7e02f40e6f685c405c34c7e6794f57c84278549391f69c8471", "artifact_size_bytes": 801482, "failed_terminal_event_id": "terminal-e64d8ebc53b216d29c83ce8fd125806f66d21961b8fa03a13ac44eb8e7bc9b64", "failed_terminal_status": "failed", "interrupted_event_id": "terminal-03f4a680b206e12c4aeec3adbf2d0fc1d23f12cca9996bfd4c85ce6bbe81b410", "later_terminal_event_id": "terminal-8ce980300e2c2d6b8315f1389f8e38225a01bca3101c7eb6817d7ff95b52bf2f", "pending_attempt_count": 4, "pending_same_id_event_id": "terminal-3c083b00493a9188239c16e5d7957c51a55897a4ef1c6b8fb44244e54b412bd7", "pending_same_id_replayed": true, "raw_session_id": "6fe09def-3da3-4606-a02d-9b7b96cd1e36", "raw_turn_status": "completed", "restart_turn_id": "01a01fb1-1ff5-7ec3-ba90-c3e0be5c3487", "terminal_statuses": ["completed", "interrupted"], "wait_timeout_kind": "timeout_active", "written_event_id": "terminal-8ce980300e2c2d6b8315f1389f8e38225a01bca3101c7eb6817d7ff95b52bf2f", "written_replayed_after_restart": false}, "scenario": "callback-recovery", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260820T150129.592577Z-16184-callback-recovery/transcript.jsonl"}
STDERR:
EXIT: 0
```

Complete sanitized callback-frame and subprocess record: [callback-recovery/transcript.jsonl](focused-reride/callback-recovery/transcript.jsonl).

## 5. Start a clean managed daemon — setup happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH codex-worker --instance task8-focused-stopped daemon start`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"task8-focused-stopped","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/daemon.log"},"status":"ready","daemon_pid":20277,"codex_pid":20281,"worker_count":0,"readiness":{"ready":true,"daemon_pid":20277,"codex_pid":20281,"socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","state_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/registry.json","session_count":0},"last_error":null}}}
STDERR:
EXIT: 0
```

## 6. Stop daemon non-destructively — setup happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH codex-worker --instance task8-focused-stopped daemon stop`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"task8-focused-stopped","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/daemon.log"},"status_before":"ready","status_after":"stopped","daemon_pid":20277,"codex_pid":20281,"durable_state":"preserved","worker_count":0}}
STDERR:
EXIT: 0
```

## 7. Message while stopped — refusal path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH codex-worker --instance task8-focused-stopped message --name preserved-worker --message "message while stopped"`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","error":{"code":-32023,"message":"Worker daemon is stopped","data":{"kind":"daemon_stopped","retryable":false,"source":"codex-worker","details":{},"known_ids":{"instance":"task8-focused-stopped","name":null,"session_id":null,"thread_id":null,"turn_id":null},"next_actions":[{"command":"codex-worker --instance task8-focused-stopped daemon start","reason":"Start the selected managed daemon without starting a turn"}]}}}
STDERR:
EXIT: 1
```

## 8. Literal prescribed daemon start — recovery happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH codex-worker --instance task8-focused-stopped daemon start`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"task8-focused-stopped","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/daemon.log"},"status":"ready","daemon_pid":20681,"codex_pid":20686,"worker_count":0,"readiness":{"ready":true,"daemon_pid":20681,"codex_pid":20686,"socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","state_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/registry.json","session_count":0},"last_error":null}}}
STDERR:
EXIT: 0
```

## 9. Status after recovery, with no turn start — happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH codex-worker --instance task8-focused-stopped daemon status`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"task8-focused-stopped","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/daemon.log"},"status":"ready","daemon_pid":20681,"codex_pid":20686,"worker_count":0,"readiness":{"ready":true,"daemon_pid":20681,"codex_pid":20686,"socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","state_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/registry.json","session_count":0},"last_error":null}}}
STDERR:
EXIT: 0
```

## 10. Stop focused daemon after ride — cleanup happy path

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH codex-worker --instance task8-focused-stopped daemon stop`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"task8-focused-stopped","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-5a3791a534b9aa5ec1b8/s","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/5a3791a534b9aa5ec1b835939412beb23f9a17e886d93a0474272a9b0ce16304/daemon.log"},"status_before":"ready","status_after":"stopped","daemon_pid":20681,"codex_pid":20686,"durable_state":"preserved","worker_count":0}}
STDERR:
EXIT: 0
```

## 11. Controller cleanup-focused recovery reride — happy path

After evaluator inspection found that the foreground fake daemon could become an
unreaped child during managed cleanup, the harness was corrected to use raw graceful
shutdown and reap its own child. The controller reran the complete recovery scenario.

Invocation: `PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks/bin:$PATH python3 tests/codex-worker/live_broker_check.py --scenario callback-recovery`

```text
STDOUT:
{"result": {"artifact_event_id": "terminal-96d3860298403d6ab0481c6d2ce33386a9ab90da615ae5a63e7e84c66836051e", "artifact_readback_verified": true, "artifact_sha256": "c4a297de4aa9d826a6c8dd6f2e294bc6bbf16c969aaed1d74fad559593b46f3d", "artifact_size_bytes": 801482, "failed_terminal_event_id": "terminal-456fb4a225e4803ad32ea883c99a04199f78a9acfa4ed2657f0a08ddf80e270a", "failed_terminal_status": "failed", "interrupted_event_id": "terminal-9b44bdc92426f715ae3d32f3b3bd7893574f4b552826d2050a88073793eb446d", "later_terminal_event_id": "terminal-7e1654c849e2cdd5f86908e696c2e30f2fe7c9bddadec1e8c3c82459130e66ea", "pending_attempt_count": 4, "pending_same_id_event_id": "terminal-348f8172912ae28eb9f2c25ab67b2a84a6c4fa9261c603bb9f5c77051db75b2a", "pending_same_id_replayed": true, "raw_session_id": "3af6c73d-36e1-408f-b523-2713a067d2ee", "raw_turn_status": "completed", "restart_turn_id": "01a01fb8-e553-79a0-9bf4-211962aff305", "terminal_statuses": ["completed", "interrupted"], "wait_timeout_kind": "timeout_active", "written_event_id": "terminal-7e1654c849e2cdd5f86908e696c2e30f2fe7c9bddadec1e8c3c82459130e66ea", "written_replayed_after_restart": false}, "scenario": "callback-recovery", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260820T150957.753587Z-27343-callback-recovery/transcript.jsonl"}
STDERR:
EXIT: 0
```

Complete sanitized record: [callback-recovery-clean/transcript.jsonl](focused-reride/callback-recovery-clean/transcript.jsonl). Its raw fake-daemon shutdown, foreground process result, and both managed cleanup stops are exits 0 (sequences 36–39); there is no cleanup refusal.

## Executor report

**MEASURED final record:** 11 top-level invocations, 9 happy-path or
setup/recovery-success invocations, and 2 refusal-oriented invocations. The original
four executor scenario records contain 80 JSONL records, including 15 sanitized callback
frames with destination labels; the controller recovery replacement adds 39 records and
supersedes the cleanup portion of section 4. No invocation was NOT RUN. The final
superseding run has no unexpected error. All callback receipts are `written` local socket
handoffs, never a claim of Claude delivery.

The one-command-per-file captures for sections 5–10 are in [focused-reride/stopped-daemon/](focused-reride/stopped-daemon/); each invocation has its exact `stdout`, `stderr`, and `exit` file.
