# Codex worker global install — CLI Surface (status: draft)

**Design doc:** ./2026-08-28-codex-worker-global-install-design.md · **Decision log:** ./2026-08-28-codex-worker-global-install-decisions.md

## 1. `codex-worker` — installed tool identity

Global parser arguments are `--version` (terminal action), `--socket <absolute-path>`,
`--instance <validated-id>`, and `--pretty`. `--socket` and `--instance` are mutually
exclusive wherever both modes are available. Common commands reject `--socket`;
foreground/raw lifecycle commands retain their existing restrictions. The tables below
are the exhaustive current surface after this additive change; response and refusal
schemas remain governed by the ratified command-ergonomics and callback companions.

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker --version` | Print installed identity without daemon contact. | `--version` terminal global action; a family is not required and harmless formatting/selection globals may precede it. Exact stdout `codex-worker <distribution-version>\n`; empty stderr; exit 0. | Parser terminal action; no RPC/domain command model | READ | NEW |
| `codex-worker start` | Create a named worker and synchronously run its first turn. | `--name <worker>` required; exactly one of `--prompt <nonempty>` or `--prompt-file <readable-utf8>`; `--cwd <dir>` default process cwd; exactly one route after defaults: `--tier medium|very-smart` default medium or `--model <live-id>`; `--effort <supported>` default medium; `--read-only`; `--goal <nonempty <=4000>` optional; `--token-budget <positive-int>` requires goal; `--no-callback`; `--output-schema <readable-json-schema>`; `--timeout <finite >=0>` optional/no deadline; globals `--instance`, `--pretty`; `--socket` invalid. | `StartWorkerRequest -> CompletionResponse` | RECORD | EXISTS-KEEP |
| `codex-worker run` | Send a follow-up to a named worker and wait. | `--name <worker>` required; exactly one of `--prompt` or `--prompt-file`; `--output-schema <readable-json-schema>` optional; `--timeout <finite >=0>` optional/no deadline; globals `--instance`, `--pretty`; `--socket` invalid. | `RunWorkerRequest -> CompletionResponse` | RECORD | EXISTS-KEEP |
| `codex-worker message` | Send one proactive non-blocking Claude update. | `--name <worker>` required; exactly one of `--message <nonempty>` or `--message-file <readable-utf8>`; `--priority now|next|later` default next; `--cc-agent-name <registry-name>` optional override; globals `--instance`, `--pretty`; `--socket` invalid. | `MessageWorkerRequest -> CallbackSendResponse` | FILTER | EXISTS-KEEP |
| `codex-worker status` | Read named worker/runtime/callback state. | `--name <worker>` required; globals `--instance`, `--pretty`; `--socket` invalid. | `WorkerStatusRequest -> WorkerStatusResponse` | READ | EXISTS-KEEP |
| `codex-worker messages` | Read latest retained live agent narration. | `--name <worker>` required; `--tail <positive-int>` default 1; globals `--instance`, `--pretty`; `--socket` invalid. | `WorkerMessagesRequest -> WorkerMessagesResponse` | READ | EXISTS-KEEP |
| `codex-worker history` | Read latest durable turns/completions. | `--name <worker>` required; `--tail <positive-int>` default 1; globals `--instance`, `--pretty`; `--socket` invalid. | `WorkerHistoryRequest -> WorkerHistoryResponse` | READ | EXISTS-KEEP |
| `codex-worker steer` | Append an instruction to a named active turn. | `--name <worker>` required; exactly one of `--prompt` or `--prompt-file`; globals `--instance`, `--pretty`; `--socket` invalid. | `SteerWorkerRequest -> ControlResponse` | RECORD | EXISTS-KEEP |
| `codex-worker interrupt` | Interrupt a named active turn. | `--name <worker>` required; globals `--instance`, `--pretty`; `--socket` invalid. | `InterruptWorkerRequest -> ControlResponse` | RECORD | EXISTS-KEEP |
| `codex-worker goal set` | Set/update native goal state. | `--name <worker>` required; at least one of `--goal <nonempty <=4000>`, `--status active|paused|blocked|usageLimited|budgetLimited|complete`, `--token-budget <positive-int>`; globals `--instance`, `--pretty`; `--socket` invalid. | `GoalSetRequest -> GoalResponse` | RECORD | EXISTS-KEEP |
| `codex-worker goal show` | Read native goal and provider usage. | `--name <worker>` required; globals `--instance`, `--pretty`; `--socket` invalid. | `GoalShowRequest -> GoalResponse` | READ | EXISTS-KEEP |
| `codex-worker limits` | Read authoritative provider capacity when available. | No command args; globals `--instance`, `--pretty`; `--socket` invalid. | `LimitsRequest -> LimitsResponse` | READ | EXISTS-KEEP |
| `codex-worker daemon start` | Start the selected managed daemon without worker creation. | No command args; globals `--instance`, `--pretty`; `--socket` invalid. | `DaemonStatusRequest -> DaemonStatusResponse` | RECORD | EXISTS-KEEP |
| `codex-worker daemon status` | Read selected managed or explicit raw daemon health. | Managed: globals `--instance`, `--pretty`, no socket. Raw: global `--socket <absolute-path>`, `--pretty`, no instance. | `DaemonStatusRequest -> DaemonStatusResponse` or raw `daemon/status` | READ | EXISTS-KEEP |
| `codex-worker daemon stop` | Stop selected managed runtime without deleting durable state. | No command args; globals `--instance`, `--pretty`; `--socket` invalid. | `DaemonStopRequest -> DaemonStopResponse` | RECORD | EXISTS-KEEP |
| `codex-worker daemon shutdown` | Request raw graceful daemon shutdown. | No command args; `--socket <absolute-path>` optional (environment/platform raw default otherwise); `--pretty`; `--instance` invalid. | raw `daemon/shutdown` | RECORD | EXISTS-KEEP |
| `codex-worker daemon serve` | Run explicit broker in foreground. | `--state <absolute-path>` default raw environment/platform path; `--codex-bin <path-or-name>` default codex; `--event-limit <positive-int>` default 1000; global `--socket <absolute-path>`; `--instance`, `--pretty` invalid. | Foreground composition | RECORD | EXISTS-KEEP |
| `codex-worker model list` | Discover live models/efforts. | No command args; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `model/list` | READ | EXISTS-KEEP |
| `codex-worker session start` | Create a raw durable session. | `--cwd <absolute-dir>` required; `--name <text>` optional; `--model <live-id>` optional; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `session/start` | RECORD | EXISTS-KEEP |
| `codex-worker session resume` | Resume persisted session or recover raw thread. | Exactly one of `--session <uuid>` or `--thread <thread-id>`; `--name <text>` only with raw thread; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `session/resume` | RECORD | EXISTS-KEEP |
| `codex-worker session list` | List durable sessions. | No command args; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `session/list` | READ | EXISTS-KEEP |
| `codex-worker session show` | Inspect one durable session. | Exactly one of `--session <uuid>` or `--thread <thread-id>`; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `session/show` | READ | EXISTS-KEEP |
| `codex-worker turn start` | Start raw turn and return immediately. | Exactly one of `--session` or `--thread`; exactly one of `--prompt` or `--prompt-file`; `--model <live-id>` optional; `--effort <supported>` optional; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `turn/start` | RECORD | EXISTS-KEEP |
| `codex-worker turn status` | Read raw current/latest turn. | Exactly one of `--session` or `--thread`; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `turn/status` | READ | EXISTS-KEEP |
| `codex-worker turn wait` | Wait for raw terminal state. | Exactly one of `--session` or `--thread`; `--timeout <finite >=0>` default 900; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `turn/wait` | READ | EXISTS-KEEP |
| `codex-worker turn events` | Page retained raw events. | Exactly one of `--session` or `--thread`; `--after <nonnegative-int>` default 0; `--limit <1..1000>` default 100; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `turn/events` | READ | EXISTS-KEEP |
| `codex-worker turn steer` | Steer raw active turn. | Exactly one of `--session` or `--thread`; exactly one of `--prompt` or `--prompt-file`; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `turn/steer` | RECORD | EXISTS-KEEP |
| `codex-worker turn interrupt` | Interrupt raw active turn. | Exactly one of `--session` or `--thread`; at most one of globals `--instance` or `--socket`; `--pretty`. | raw `turn/interrupt` | RECORD | EXISTS-KEEP |

### 1b. Composition rationale

`--version` is one terminal parser action rather than a request/domain model because no
daemon interaction, operator decision, or state transition exists. It supports
version-aware preflight without exposing UV internals to RPC (D2, D3, D5). Existing
command families are exhaustively retained above and deliberately unchanged.

## 2. UV tool lifecycle — distribution operations

These are UV commands over the `codex-worker` Python distribution, not new
`codex-worker` subcommands.

| Command | Purpose | Args (all used by this design) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `uv tool install <source>` | Persistently install or replace the worker from a plugin, checkout, Git URL, or future registry release. | `<source>` — package spec/path/URL; `--reinstall` when compatibility repair requires replacement | UV-owned | RECORD | EXISTS-REUSE |
| `uv tool list` | Inspect installed tool identity and executables. | none required | UV-owned | READ | EXISTS-REUSE |
| `uv tool upgrade codex-worker` | Upgrade a registry/Git-installed worker within its source constraints. | `codex-worker` | UV-owned | RECORD | EXISTS-REUSE |
| `uv tool uninstall codex-worker` | Remove the isolated worker and its executable without touching worker session state. | `codex-worker` | UV-owned | RECORD | EXISTS-REUSE |

### 2b. Composition rationale

Package lifecycle remains UV's job rather than being duplicated as worker self-update
commands. The skill composes a short availability/version read with an installation only
when repair is required (D2). Durable daemon/session state lives outside UV's environment
and therefore survives tool replacement or uninstall.

## 3. Operator workflows

### Claude Code first use

1. Resolve the trusted plugin root from `CLAUDE_PLUGIN_ROOT`, or derive it from the exact
   loaded `SKILL.md` path; validate the skill, manifest, and package metadata beneath it.
2. Read the required version from the manifest; read UV's bin with
   `uv tool dir --bin`; inspect `command -v codex-worker` and
   `codex-worker --version`.
3. If the UV-owned executable is absent or mismatched, run
   `uv tool install --reinstall "$SUPERDEV_PLUGIN_ROOT/skills/subagent-driven-development/scripts"`.
4. Confirm its canonical path and exact version, then run normal short commands such as
   `codex-worker start --name <unique-name> --prompt-file <task-file>`.
5. Recovery: if UV is missing, install UV explicitly; if UV's bin is not first on PATH,
   run `uv tool update-shell` and start a new shell or prefix the current shell PATH. If
   another executable shadows it, report both paths and stop. Never invoke source directly.

### Local development

1. Run `uv tool install --reinstall <checkout>/skills/subagent-driven-development/scripts`
   for release-like checks, or add `--editable` for local iteration only.
2. Inspect it through UV and run `codex-worker --version` outside the checkout.
3. Replace an editable install with the non-editable source before installed-command
   acceptance; editable installs cannot prove runtime independence.
4. Recovery: run `uv tool uninstall codex-worker`; do not delete daemon/session state.

### Upgrade

1. The next skill preflight compares exact PATH/UV ownership and version with the loaded
   manifest.
2. If version differs in either direction, run the same non-editable `uv tool install
   --reinstall <bundled-source>` operation.
3. Run `codex-worker status --name <existing-name>` to confirm durable mapping/state
   survives replacement.

## 4. Docs to update

| Doc | What changes |
|---|---|
| `skills/subagent-driven-development/SKILL.md` | Require the one-per-session tool preflight before Codex dispatch. |
| `skills/subagent-driven-development/codex-worker.md` | Add install/preflight, version, lifecycle, and recovery guidance; keep all operating examples short. |
| `README.md` | Document standalone UV installation and the external Codex prerequisite. |
| CLI help | Add `--version`; no existing command/argument changes. |

## 5. Delta summary

The worker becomes a persistent UV-installed Python tool with one new global
`--version` flag. Existing common and raw worker commands are unchanged. Installation,
replacement, inspection, upgrade, and removal use UV's existing tool family; the
Superdev skill automatically performs the install/compatibility preflight and then uses
only the short `codex-worker` executable.
