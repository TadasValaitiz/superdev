# CENSUS — evidence record; rules nothing

**Topic:** one global Codex Worker service exposing its Codex app-server to the remote TUI  
**Captured:** 2026-08-28  
**Authority:** evidence and work queue only; decisions live in the companion decision log.

## Current implementation

- **READ** `skills/subagent-driven-development/scripts/codex_worker/app_server.py:1-84`:
  the adapter owns one `codex app-server` child over stdin/stdout and starts reader/stderr
  threads. There is no network address another client can attach to.
- **READ** `skills/subagent-driven-development/scripts/codex_worker/cli.py:141-170` and
  `instance.py:60-80`: the public parser accepts `--instance`, and instance selection reads
  `CODEX_WORKER_INSTANCE` plus Claude ambient identity.
- **READ** `skills/subagent-driven-development/scripts/codex_worker/broker.py:144-166`:
  the daemon stamps `worker_version` at construction and returns it from status. This is a
  preservation-worthy exact-version precedent.
- **READ** `skills/subagent-driven-development/scripts/codex_worker/instance.py:330-520`:
  managed lifecycle already has lock/readiness/version/safe-socket machinery, but it is
  parameterized by instance and its recovery actions include per-instance stop.
- **READ** `tests/codex-worker/test_skill_integration.py:170-250` and
  `tests/codex-worker/live_claude_check.sh:20-60`: current skill/live expectations explicitly
  teach instance routing and routine daemon stop, which conflicts with the requested permanent
  global service.

## Installed Codex and official contract

- **MEASURED** `codex --version` on 2026-08-28 returned `codex-cli 0.150.1`.
- **MEASURED** `codex app-server --help` on 2026-08-28 reports supported listeners
  `stdio://` (default), `unix://`, `unix://PATH`, `ws://IP:PORT`, and `off`; it also reports
  `--ws-auth`, token-file/hash, signed-bearer secret, issuer, audience and clock-skew options.
- **MEASURED** `codex --help | rg -n -- '--remote|resume'` shows both the remote endpoint
  flag and the resume family in this installed CLI.
- **READ** [official OpenAI Codex App Server documentation](https://developers.openai.com/codex/app-server),
  fetched 2026-08-28: the documented local pairing is
  `codex app-server --listen ws://127.0.0.1:4500` then
  `codex --remote ws://127.0.0.1:4500`; WebSocket uses one JSON-RPC message per text frame;
  `/readyz` reports listener readiness; initialize is per connection; thread start/resume and
  turn APIs drive the same server-owned threads. It labels WebSocket experimental and says
  non-local connections require WebSocket authentication plus TLS.
- **MEASURED** in the preceding live brainstorm probe against the then-installed Codex 0.147.0:
  two
  independently initialized WebSocket clients used one app-server; the second resumed the
  first client's thread and started a turn; both received the authoritative completion. The
  probe threads were deleted and the server was stopped. This evidence must be reproduced into
  a tracked live receipt before acceptance; the exploratory terminal transcript is not itself
  a merge receipt. Codex was upgraded to 0.150.1 afterward; no claim is made that the old probe
  proves the current binary.
- **MEASURED** exact upstream checks used during reconciliation:
  `codex --version`; `codex app-server --help`; `codex --help | rg -n -- '--remote|resume'`;
  and `codex app-server generate-json-schema --out <private-temp-dir>`. The generated 0.150.1
  schema reports `thread/list` pages containing `Thread.status`, including `type: active`, and
  documents `sourceKinds: []` as all source kinds. This enables authoritative all-thread
  inventory but is not atomic with a direct public listener, which motivated D17's gateway gate.
- **MEASURED** isolated dependency probe:
  `uv venv --python 3.9 <private-temp>/venv`, `uv pip install --python <venv-python>
  'websockets>=14,<16'`, then importing `websockets.sync.client.connect` and
  `websockets.sync.server.serve` returned Python `3.9.6`, websockets `15.0.1`, and
  `sync-client-server-ok`. No user-global Python/UV tool state was changed.

## Durable state and migration pressure

- **MEASURED**
  `find "$HOME/Library/Application Support/superdev/codex-worker/instances" -maxdepth 2 -type f -name '*.json' | wc -l`
  returned `239` JSON files across legacy instance roots on 2026-08-28. This count is an
  inventory fact, not a promise about record count.
- **MEASURED** a read-only `find` + `jq` scan for `status-checker-abc` found two divergent
  durable mappings:

  | Legacy root prefix | wrapper session_id | Codex thread_id |
  |---|---|---|
  | `d2b4dd999806…` | `1970897c-16c5-4540-826f-7555e60d4295` | `01a0476b-1ade-7db1-95d8-cd5f185865ee` |
  | `37a8eec1ce19…` | `5abd3ed2-4b16-4502-9bda-087bff85d12f` | `01a046c7-3141-7833-940d-4255fb5267a7` |

  Therefore global migration cannot honestly use last-writer-wins, silent suffixes, or delete
  a source after copying.

## Repository state and scope

- **MEASURED** `git log -8 --oneline --decorate` showed main at `95df980` when this census
  was reconciled; the branch contains newer unrelated Superdev work than the earlier
  Codex-worker 7.10 release stream.
- **MEASURED** `git status --short` showed a pre-existing unrelated modification to
  `docs/superdev/specs/2026-08-28-architect-freshness-decisions.md`. This work must preserve
  it untouched and isolate implementation in a worktree.
- **FLAGGED** Codex 0.150.1 may have response/schema differences from the existing 0.147-era
  fake/live fixtures beyond transport and auth. The plan must regenerate the app-server schema
  and route every discovered drift through the shared decision log rather than assume parity.
- **FLAGGED** official WebSocket overload `-32001` needs bounded retry/jitter mapping in the
  worker adapter; its exact public fault mapping is an implementation-plan decision, not yet
  evidence.

## Salvage inventory

- **READ:** keep strict command/result models, one-object stdout, typed RPC faults, safe Unix
  socket ownership, exact-ready version handshake, durable fsync/atomic registry writes,
  callback capture/outbox, expected-turn control, bounded observation/event storage, model
  capability validation, Python 3.9 UV packaging, and the existing live/checkride harness.
- **READ:** replace instance-derived physical paths, private stdio transport, instance-scoped
  names, routine cleanup stops, and any output that fails to distinguish wrapper session ID
  from Codex thread ID.
