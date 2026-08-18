# Manual live session-list record

Substrate: measured real Codex CLI 0.147.0, disposable fixture repository at `/tmp/cw-session-list.7qUy1a`; no credential values were detected or sanitized. This artifact honestly records six session-list client commands run against an already-running independent foreground daemon. The original ride did not preserve daemon startup streams; §7 separately proves the foreground serve stream contract. Client commands below were run separately with stdout and stderr captured independently. Blank stderr is recorded as `(empty)` where applicable.

## 1. daemon status

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock daemon status
```

stdout:

```json
{"jsonrpc":"2.0","id":"cli","result":{"ready":true,"daemon_pid":29022,"codex_pid":29024,"socket_path":"/tmp/cw-session-list.7qUy1a/worker.sock","state_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/sessions.json","session_count":0}}
```

stderr: `(empty)`

exit: `0`

## 2. session start (list-alpha)

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock session start --name list-alpha --cwd /tmp/cw-session-list.7qUy1a/wt-a --model gpt-5.6-sol
```

stdout:

```json
{"jsonrpc":"2.0","id":"cli","result":{"session":{"session_id":"3a90d369-ccf9-4192-b43e-27cd79d78f21","thread_id":"01a0172c-b5ec-73a1-83d7-6f60a5e00d9f","cwd":"/private/tmp/cw-session-list.7qUy1a/wt-a","created_at":"2026-08-18T23:20:01.339059Z","updated_at":"2026-08-18T23:20:01.339059Z","name":"list-alpha","model":"gpt-5.6-sol","effort":null},"attached":true}}
```

stderr: `(empty)`

exit: `0`

## 3. session start (list-beta)

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock session start --name list-beta --cwd /tmp/cw-session-list.7qUy1a/wt-b --model gpt-5.6-terra
```

stdout:

```json
{"jsonrpc":"2.0","id":"cli","result":{"session":{"session_id":"5681eec4-277a-4de5-a3c1-55db81a24e3b","thread_id":"01a0172c-b6c5-7482-8712-b39bef044931","cwd":"/private/tmp/cw-session-list.7qUy1a/wt-b","created_at":"2026-08-18T23:20:01.536076Z","updated_at":"2026-08-18T23:20:01.536076Z","name":"list-beta","model":"gpt-5.6-terra","effort":null},"attached":true}}
```

stderr: `(empty)`

exit: `0`

## 4. session list

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock session list
```

stdout:

```json
{"jsonrpc":"2.0","id":"cli","result":{"sessions":[{"session":{"session_id":"3a90d369-ccf9-4192-b43e-27cd79d78f21","thread_id":"01a0172c-b5ec-73a1-83d7-6f60a5e00d9f","cwd":"/private/tmp/cw-session-list.7qUy1a/wt-a","created_at":"2026-08-18T23:20:01.339059Z","updated_at":"2026-08-18T23:20:01.339059Z","name":"list-alpha","model":"gpt-5.6-sol","effort":null},"attached":true,"active_turn_id":null,"latest_turn_status":null},{"session":{"session_id":"5681eec4-277a-4de5-a3c1-55db81a24e3b","thread_id":"01a0172c-b6c5-7482-8712-b39bef044931","cwd":"/private/tmp/cw-session-list.7qUy1a/wt-b","created_at":"2026-08-18T23:20:01.536076Z","updated_at":"2026-08-18T23:20:01.536076Z","name":"list-beta","model":"gpt-5.6-terra","effort":null},"attached":true,"active_turn_id":null,"latest_turn_status":null}]}}
```

stderr: `(empty)`

exit: `0`

## 5. daemon shutdown

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock daemon shutdown
```

stdout:

```json
{"jsonrpc":"2.0","id":"cli","result":{"accepted":true}}
```

stderr: `(empty)`

exit: `0`

## 6. post-shutdown daemon status

Invocation:

```text
python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock daemon status
```

stdout:

```json
{"jsonrpc":"2.0","id":null,"error":{"code":-32000,"message":"Codex worker daemon is not available","data":{"kind":"daemon_unavailable","recovery":"run codex-worker --socket /tmp/cw-session-list.7qUy1a/worker.sock daemon serve","details":{"socket_path":"/tmp/cw-session-list.7qUy1a/worker.sock"}}}}
```

stderr: `(empty)`

exit: `1`
