# Codex worker server — CLI Surface (status: ratified by human, 2026-08-18)

**Design doc:** ./2026-08-18-codex-worker-server-design.md · **Decision log:** ./2026-08-18-codex-worker-server-decisions.md

All client commands print exactly one JSON object to stdout. Human diagnostics and foreground daemon logs go to stderr. RPC/domain failure exits 1; local usage/validation failure exits 2; success exits 0. Global `--socket PATH` may precede every command and defaults to `$SUPERDEV_CODEX_WORKER_SOCKET` or a UID-scoped path under the platform temporary directory. Global `--pretty` pretty-prints client responses; validation rejects it with foreground `daemon serve`, which has no JSON stdout response. The serve-only flags appear after `daemon serve`; `--state PATH` defaults to `$SUPERDEV_CODEX_WORKER_STATE` or the user state directory.

## 1. `codex-worker daemon` — broker lifecycle

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [--socket PATH] daemon serve [--state PATH] [--codex-bin PATH] [--event-limit INT]` | Run the broker in the foreground. | Global `--socket PATH`; serve-only `--state PATH`; serve-only `--codex-bin PATH` [default `codex`]; serve-only `--event-limit INT` [default 1000, must be >0]. Global `--pretty` is rejected. | `DaemonServeCommand` | RECORD | NEW |
| `codex-worker [--socket PATH] [--pretty] daemon status` | Read daemon health and child/server identity. | Global flags only. | `DaemonStatusCommand` | READ | NEW |
| `codex-worker [--socket PATH] [--pretty] daemon shutdown` | Request graceful wrapper shutdown without deleting sessions. | Global flags only. | `DaemonShutdownCommand` | RECORD | NEW |

### 1b. Composition rationale

Explicit serve/status/shutdown commands preserve lifecycle ownership (D3). `serve` stays foreground: no hidden daemonization or service installation occurs. Status is separate because it is a read used for readiness and recovery; shutdown is a deliberate state transition. Socket/state configuration is global because every family addresses the same broker, while child launch/event retention exist only at serve time.

## 2. `codex-worker model` — live capability discovery

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [GLOBAL] model list` | Return models and supported efforts from the running Codex app-server. | Global flags only. | `ModelListCommand` | READ | NEW |

### 2b. Composition rationale

Discovery is one command because there is no operator decision between model and effort enumeration: effort values are nested in each returned model. IDs are never pinned in the CLI contract (D9).

## 3. `codex-worker session` — durable conversation identity

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [GLOBAL] session start` | Create a Codex thread and persisted logical session. | `--cwd PATH` required; `--name TEXT` optional; `--model ID` optional. | `SessionStartCommand` | RECORD | NEW |
| `codex-worker [GLOBAL] session resume` | Attach a persisted or raw Codex thread to this daemon. | Exactly one of `--session UUID` or `--thread THREAD_ID`; `--name TEXT` optional only when repairing a raw mapping. | `SessionResumeCommand` | RECORD | NEW |
| `codex-worker [GLOBAL] session list` | List persisted sessions and attachment/runtime summaries. | No family args. | `SessionListCommand` | READ | NEW |
| `codex-worker [GLOBAL] session show` | Inspect one persisted session and its runtime state. | Exactly one of `--session UUID` or `--thread THREAD_ID`. | `SessionShowCommand` | READ | NEW |

### 3b. Composition rationale

Start and resume are separate because the operator decides whether a new conversation or an existing durable thread is intended (D5–D6). Resume accepts both identifiers but keeps them mutually exclusive so recovery is never ambiguous. List and show are read-only views and never implicitly resume detached sessions; explicit resume keeps upstream load/subscription effects observable.

## 4. `codex-worker turn` — task execution and intervention

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [GLOBAL] turn start` | Start a turn and return immediately. | Exactly one of `--session UUID` or `--thread THREAD_ID`; exactly one of `--prompt TEXT` or `--prompt-file PATH`; `--model ID` optional; `--effort VALUE` optional. | `TurnStartCommand` | RECORD | REWORKED from one-shot positional prompt |
| `codex-worker [GLOBAL] turn status` | Read active/latest turn state immediately. | Exactly one of `--session UUID` or `--thread THREAD_ID`. | `TurnStatusCommand` | READ | NEW |
| `codex-worker [GLOBAL] turn wait` | Wait for the active/latest turn to reach terminal state. | Exactly one of `--session UUID` or `--thread THREAD_ID`; `--timeout SECONDS` [default 900, must be >=0]. | `TurnWaitCommand` | READ | NEW |
| `codex-worker [GLOBAL] turn events` | Read a bounded page of authoritative notifications/items. | Exactly one of `--session UUID` or `--thread THREAD_ID`; `--after CURSOR` [default 0, >=0]; `--limit INT` [default 100, 1..1000]. | `TurnEventsCommand` | READ | NEW |
| `codex-worker [GLOBAL] turn steer` | Append instructions to the active turn. | Exactly one of `--session UUID` or `--thread THREAD_ID`; exactly one of `--prompt TEXT` or `--prompt-file PATH`. | `TurnSteerCommand` | RECORD | NEW |
| `codex-worker [GLOBAL] turn interrupt` | Interrupt the active turn. | Exactly one of `--session UUID` or `--thread THREAD_ID`. | `TurnInterruptCommand` | RECORD | NEW |

### 4b. Composition rationale

Start and wait are deliberately separate because steer/interrupt must have a real in-flight window (D7). `turn wait` may hold one threaded RPC connection while other commands proceed. Status is immediate; events carry the audit items that status intentionally omits. Steer and interrupt are distinct because one changes instructions and the other terminates work. Prompt files avoid shell quoting and size problems without reading stdin, whose blocking/ownership behavior would be ambiguous for autonomous callers.

## 5. Operator workflows — sequences, not just commands

### Start a local worker and complete a task

1. Start `codex-worker daemon serve` in an explicitly managed foreground/background shell and retain its stderr log.
2. Run `codex-worker daemon status`; read `ready`, Codex child state, and paths.
3. Run `codex-worker model list`; choose an ID and one of that model's returned efforts.
4. Run `codex-worker session start --cwd <worktree> --name <role> --model <id>`; retain `session_id` and `thread_id`.
5. Run `codex-worker turn start --session <uuid> --prompt-file <brief> --model <id> --effort <effort>`; retain `turn_id`.
6. Run `codex-worker turn wait --session <uuid>`; inspect status, errors, and completed items.
7. Run `codex-worker turn events --session <uuid>` when command/file evidence is needed.

Recovery: if the daemon is absent, explicitly restart `daemon serve`, then `session resume --session <uuid>` and resume at step 5 or inspect status. A wait timeout does not cancel the turn; use status, steer, or interrupt.

### Steer or interrupt in-flight work

1. Start a turn and retain its returned `turn_id`.
2. Run `turn status`; confirm the same turn is active.
3. To redirect, run `turn steer --session <uuid> --prompt <instruction>`, then `turn wait`.
4. To stop, run `turn interrupt --session <uuid>`, then `turn wait` and expect terminal `interrupted`.

Recovery: if active work completed between status and control, the command returns a typed benign race/idle error with latest terminal state. Do not retry steer against a new turn implicitly.

### Recover after wrapper registry loss

1. Obtain the raw `thread_id` previously returned or recorded in Codex history.
2. Run `session resume --thread <thread_id> --name <recovered-role>`.
3. Retain the returned `session_id`; subsequent commands use it.
4. Run a follow-up turn that depends on prior conversational context to validate recovery.

Recovery: if Codex cannot resume the raw thread, stop and inspect the returned upstream error. The broker does not fabricate an empty replacement conversation under the requested identity.

### Run isolated workers in multiple worktrees

1. Create/identify each worktree outside the broker.
2. Start one session per worktree with a distinct name and immutable cwd.
3. Select model/effort pairs from `model list`, then start turns independently.
4. Wait or inspect each session by UUID; verify outputs only within its declared worktree.

Recovery: a cwd cannot be retargeted. Start a new session for a different worktree; do not reuse a conversation whose filesystem identity no longer matches.

## 6. Docs to update (same branch, not later)

| Doc | What changes |
|---|---|
| `skills/subagent-driven-development/SKILL.md` or a directly linked reference | Explain when and how Claude Code uses the local Codex worker broker, including explicit lifecycle, model discovery, and recovery. |
| `skills/subagent-driven-development/scripts/codex-worker --help` | Exhaustive family/flag help matching this contract. |
| `README.md` or relevant contributor/operator reference | Minimal installation/runtime prerequisites and local-only scope if the server is user-facing beyond the skill. |

## 7. Delta summary

The existing one-shot `codex-worker CWD PROMPT` prototype becomes a foreground local daemon plus a short-lived JSON CLI client. New daemon, model, session, and turn families expose explicit lifecycle, live capability discovery, multiple durable sessions, non-blocking turns, status/events/wait, steer, interrupt, and UUID/raw-thread recovery. The positional one-shot invocation is not retained as an alias because it would silently create a new app-server/session and undermine the explicit durable lifecycle selected in D3–D6.
