# Codex worker command ergonomics — CLI Surface (status: draft)

**Design doc:** ./2026-08-19-codex-worker-command-ergonomics-design.md ·
**Decision log:** ./2026-08-19-codex-worker-command-ergonomics-decisions.md

## 0. Global contract

The public executable is `codex-worker`. Every client invocation writes exactly one
JSON object to stdout; human diagnostics and usage remain on stderr. Exit `0` is a
successful command result, `1` is an operational refusal, and `2` is local usage or
validation failure. `--pretty` changes whitespace only.

| Argument | Meaning | Scope |
|---|---|---|
| `--instance <id>` | Explicit daemon-instance identity; highest-precedence selector. | Common and advanced client commands; optional. |
| `--pretty` | Indent the one JSON stdout object. | All client commands; invalid with foreground `daemon serve`. |
| `--socket <absolute-path>` | Explicit raw RPC endpoint. Mutually exclusive with `--instance`; not accepted by common façade commands. | Advanced compatibility commands only. |
| `-h`, `--help` | Render help and exit without a JSON client result. | Every parser level. |

Instance precedence is `--instance`, `CODEX_WORKER_INSTANCE`,
`CLAUDE_CODE_SESSION_ID`, user-local `default`. `CLAUDE_EFFORT` and all other Claude
variables do not configure model, effort, access, cwd, or lifecycle.

All new request/response command models are frozen strict stdlib models with rejected
extra fields. This preserves the plugin executable's no-site-package requirement while
providing the same typed seam promised by the command pattern.

## 1. `codex-worker start` and `codex-worker run` — synchronous worker messages

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker start` | Create one named worker, optionally install its goal, send the first message, wait, and return completion. | `--name <str>` required; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; `--cwd <existing-dir>` default actual process cwd; mutually exclusive `--tier medium\|very-smart` default `medium` or `--model <live-id>`; `--effort <supported-effort>` default `medium`; `--read-only` default false/full access; `--goal <non-empty-str<=4000>` optional; `--token-budget <positive-int>` optional and requires `--goal`; `--output-schema <readable-json-schema-path>` optional/per-turn; `--timeout <finite-seconds>=0` optional/default no deadline; global `--instance`, `--pretty`. | `StartWorkerRequest -> CompletionResponse` | RECORD | NEW |
| `codex-worker run` | Send a follow-up to an existing named worker, wait, and return the same completion shape. | `--name <str>` required; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; `--output-schema <readable-json-schema-path>` optional/per-turn; `--timeout <finite-seconds>=0` optional/default no deadline; global `--instance`, `--pretty`. No cwd/model/tier/effort/access/goal creation flags. | `RunWorkerRequest -> CompletionResponse` | RECORD | NEW |

### 1b. Composition rationale

`start` composes instance readiness, name creation, live policy validation, optional
goal installation, first turn, terminal wait, and projection because there is no useful
operator decision between them. If goal installation fails, the turn does not begin
and recovery IDs are returned. `run` is separate because creation configuration is a
one-time decision; a create-or-continue parser would permit accidental drift. Both are
synchronous because the harness already owns parallel process scheduling (D13, D23).

The prompt has two input spellings but one request field. Output schema and timeout are
per-turn/per-wait controls, so they remain legal on `run`; worker policy does not.

### 1c. Completion response

The success response retains JSON-RPC 2.0 framing:

```json
{
  "jsonrpc": "2.0",
  "id": "cli",
  "result": {
    "worker": {
      "instance": "claude-session-id-or-override",
      "name": "implement-7f3",
      "session_id": "daemon-uuid",
      "thread_id": "codex-thread-id",
      "cwd": "/absolute/context",
      "tier": "medium",
      "model": "live-model-id",
      "effort": "medium",
      "access": "full"
    },
    "turn": {
      "turn_id": "codex-turn-id",
      "status": "completed",
      "error": null
    },
    "messages": [
      {
        "type": "agent_message",
        "item_id": "item-id",
        "phase": "final_answer",
        "text": "The complete final report."
      }
    ],
    "structured_output": null,
    "metrics": {
      "wall_time_ms": {"value": 1234, "source": "codex-worker", "availability": "measured"},
      "observed_items": {"value": 8, "source": "codex-worker:codex-items", "availability": "derived"},
      "command_executions": {"value": 2, "source": "codex-worker:codex-items", "availability": "derived"},
      "command_duration_ms": {"value": 450, "source": "codex:durationMs", "availability": "derived"},
      "token_usage": {"value": null, "source": "codex", "availability": "unavailable"}
    },
    "recovery": {
      "status": "codex-worker status --name implement-7f3",
      "messages": "codex-worker messages --name implement-7f3",
      "interrupt": "codex-worker interrupt --name implement-7f3"
    }
  }
}
```

Values above illustrate shape, not acceptance measurements. The implementation never
hard-codes or fabricates those example IDs/counts/durations. If a caller needs named
`verdict`, `report`, and `review` fields, its schema requires them. In schema mode only,
the CLI JSON-decodes the last schema-governed final message into `structured_output`
and retains the original message; it never extracts fields from ordinary prose.

## 2. `codex-worker status/messages/history` — named observation

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker status` | Read persisted worker configuration and latest runtime turn state. | `--name <str>` required; global `--instance`, `--pretty`. | `WorkerStatusRequest -> WorkerStatusResponse` | READ | NEW |
| `codex-worker messages` | Read the latest retained live agent narration by name. | `--name <str>` required; `--tail <positive-int>` default `1` (SEED-DEFAULT); global `--instance`, `--pretty`. | `WorkerMessagesRequest -> WorkerMessagesResponse` | READ | NEW |
| `codex-worker history` | Read the latest durable Codex turns and their final messages by name. | `--name <str>` required; `--tail <positive-int>` default `1` (SEED-DEFAULT); global `--instance`, `--pretty`. | `WorkerHistoryRequest -> WorkerHistoryResponse` | READ | NEW |

### 2b. Composition rationale

`status` answers identity/state, `messages` answers current narration, and `history`
answers durable prior-turn content. Combining them would make every quick status call
load text/history and blur bounded runtime retention with native durable storage. Tail
is the only common pagination control; cursor/item views remain advanced (D25–D26,
D31).

All three refuse with typed `daemon_stopped` rather than starting a process. This keeps
reads observational. A later `run` is the intentional restart/resume action (D27).

## 3. `codex-worker steer/interrupt` — active-turn control

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker steer` | Append an instruction to the named worker's currently active turn. | `--name <str>` required; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; global `--instance`, `--pretty`. | `SteerWorkerRequest -> ControlResponse` | RECORD | NEW |
| `codex-worker interrupt` | Explicitly cancel the named worker's active turn. | `--name <str>` required; global `--instance`, `--pretty`. | `InterruptWorkerRequest -> ControlResponse` | RECORD | NEW |

### 3b. Composition rationale

Steering changes instructions only and carries no configuration flags because upstream
applies it at a step boundary to the captured active turn. Interrupt is separate and
explicit because caller disconnect, Ctrl-C, timeout, and daemon observation must not
silently mean cancellation (D25, D30). Exact upstream already-idle races are returned as
`turn_not_active`; unrelated provider failures are not collapsed into that result.

## 4. `codex-worker goal` — native objective and budget state

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker goal set` | Create, replace, or update Codex's native goal for a named worker. | `--name <str>` required; at least one of `--goal <non-empty-str<=4000>`, `--status active\|paused\|blocked\|usageLimited\|budgetLimited\|complete`, `--token-budget <positive-int>`; global `--instance`, `--pretty`. | `GoalSetRequest -> GoalResponse` | RECORD | NEW |
| `codex-worker goal show` | Return the named worker's current native goal and provider-reported usage. | `--name <str>` required; global `--instance`, `--pretty`. | `GoalShowRequest -> GoalResponse` | READ | NEW |

### 4b. Composition rationale

Goal state is not duplicated in the worker registry. `set` and `show` directly proxy
Codex's persistent thread goal, resolving only the worker name. A new objective can
reset native usage accounting; the response returns the upstream goal after mutation
so the caller sees that consequence. Status/budget-only updates preserve native usage
according to Codex semantics. There is no `goal clear`: this release has no destructive
common commands, and status `complete` expresses ordinary closure (D18, D29, D32).

`start --goal [--token-budget]` is the one-command initial form and always uses status
`active`. Later goal commands never autostart a stopped daemon.

## 5. `codex-worker limits` — native account capacity

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker limits` | Read Codex's authoritative current account rate-limit state. | Global `--instance`, `--pretty`; no command-specific args. | `LimitsRequest -> LimitsResponse` | READ | NEW |

### 5b. Composition rationale

The command returns the native payload rather than deriving a launch count or policy.
Unsupported authentication returns the stable `limits_unavailable` operational refusal;
it never substitutes guessed capacity. It does not autostart, so a fresh caller checks
it after the first normal worker start or while the runtime is already active (D27,
D31).

## 6. `codex-worker daemon` — selected-instance lifecycle

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker daemon status` | Read selected-instance health, PID/child identity, paths, and readiness without starting it. | Global `--instance`, `--pretty`. | `DaemonStatusRequest -> DaemonStatusResponse` | READ | EXISTS-REWORK |
| `codex-worker daemon stop` | Gracefully stop the selected daemon and Codex child without deleting durable state. | Global `--instance`, `--pretty`. | `DaemonStopRequest -> DaemonStopResponse` | RECORD | NEW |
| `codex-worker daemon shutdown` | Advanced compatibility alias for non-destructive stop on an explicit/current endpoint. | Global `--socket` or resolved instance; `--pretty`. | Existing `daemon/shutdown` request/response | RECORD | EXISTS-KEEP alias |
| `codex-worker daemon serve` | Run one explicitly configured broker in the foreground. | `--state <absolute-path>` default legacy environment/platform path; `--codex-bin <path-or-name>` default `codex`; `--event-limit <positive-int>` default `1000` (existing SEED-DEFAULT); global `--socket`; `--instance` and `--pretty` invalid. | Existing foreground composition args | RECORD | EXISTS-KEEP advanced |

### 6b. Composition rationale

There is no normal `ensure`: message commands already perform concurrency-safe implicit
startup. Status and stop remain explicit because they answer real diagnostic/control
questions. Stop never means clean, purge, reset, or delete (D6, D18, D27). Foreground
serve remains for debugging and external supervisors, not the Claude quickstart.

## 7. Advanced compatibility families

These commands retain the current raw broker altitude. Their response shapes and RPC
methods remain unchanged; they are documented so the new façade does not make recovery
opaque.

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker model list` | Discover live models and supported efforts. | Global `--socket`, `--pretty`; no command args. | Existing `model/list` | READ | EXISTS-KEEP |
| `codex-worker session start` | Create a raw durable session. | `--cwd <absolute-dir>` required; `--name <str>` optional annotation; `--model <live-id>` optional; global `--socket`, `--pretty`. | Existing `session/start` | RECORD | EXISTS-KEEP |
| `codex-worker session resume` | Resume a persisted session or recover a raw thread. | Exactly one of `--session <uuid>` or `--thread <id>`; `--name <str>` valid only with raw thread; global `--socket`, `--pretty`. | Existing `session/resume` | RECORD | EXISTS-KEEP |
| `codex-worker session list` | List persisted sessions. | Global `--socket`, `--pretty`; no command args. | Existing `session/list` | READ | EXISTS-KEEP |
| `codex-worker session show` | Inspect one session. | Exactly one of `--session <uuid>` or `--thread <id>`; global `--socket`, `--pretty`. | Existing `session/show` | READ | EXISTS-KEEP |
| `codex-worker turn start` | Start a raw turn and return immediately. | Exactly one of session/thread selector; exactly one prompt source; `--model <live-id>` optional; `--effort <supported>` optional; global `--socket`, `--pretty`. | Existing `turn/start` | RECORD | EXISTS-KEEP |
| `codex-worker turn status` | Read raw current/latest turn state. | Exactly one session/thread selector; global `--socket`, `--pretty`. | Existing `turn/status` | READ | EXISTS-KEEP |
| `codex-worker turn wait` | Wait for raw terminal turn state. | Exactly one session/thread selector; `--timeout <finite-seconds>=0` default `900` (existing SEED-DEFAULT); global `--socket`, `--pretty`. | Existing `turn/wait` | READ | EXISTS-KEEP |
| `codex-worker turn events` | Page retained raw notification events. | Exactly one session/thread selector; `--after <nonnegative-int>` default `0`; `--limit <int 1..1000>` default `100` (existing SEED-DEFAULT); global `--socket`, `--pretty`. | Existing `turn/events` | READ | EXISTS-KEEP |
| `codex-worker turn steer` | Steer a raw active turn. | Exactly one session/thread selector; exactly one prompt source; global `--socket`, `--pretty`. | Existing `turn/steer` | RECORD | EXISTS-KEEP |
| `codex-worker turn interrupt` | Interrupt a raw active turn. | Exactly one session/thread selector; global `--socket`, `--pretty`. | Existing `turn/interrupt` | RECORD | EXISTS-KEEP |

### 7b. Composition rationale

The common surface composes these operations because no harness decision belongs among
them. The advanced commands stay separate because raw-thread recovery, cursor paging,
foreground supervision, and live catalog diagnosis are explicit technical tasks. No
existing spelling is removed or silently redirected (D28, D38).

## 8. Operator workflows — sequences and recovery

### First worker in Claude Code

1. From the intended worktree, run `codex-worker start --name implement-7f3 --prompt
   "Implement the approved parser change."`.
2. Read `result.worker` to confirm cwd/model/effort/access and read all
   `result.messages`; if a schema was supplied, read `structured_output`.
3. Send the next instruction with `codex-worker run --name implement-7f3 --prompt
   "Now run the focused checks and report."`.

Recovery: `name_exists` means the conversation already exists—use `run` or choose a
collision-resistant name. `daemon_start_failed` names the daemon log. A timeout leaves
the turn running; inspect `status`/`messages` or explicitly `interrupt`.

### Five-worker fan-out

1. Mint five readable unique names such as `review-api-a31`, each with the correct cwd
   and creation policy.
2. Launch five `codex-worker start ...` shell commands concurrently using the harness's
   own mechanism.
3. Consume each complete JSON result as that process finishes; correlate by
   `result.worker.name`, never launch order.

Recovery: one name collision or worker failure does not cancel the other four. Do not
retry a timed-out start as `start`; inspect by name, then continue or interrupt.

### Goal-directed worker

1. Start with `--goal` and optional `--token-budget`; the goal is installed before the
   first prompt.
2. While the daemon is active, use `goal show --name ...` to read native status,
   `tokens_used`, and `time_used_seconds`.
3. Use `goal set --name ... --status paused` or update budget/objective deliberately.
4. Use `history --name ... --tail N` to recover durable final answers after live events
   roll off.

Recovery: a failed initial goal prevents the turn and returns worker/thread IDs. A new
objective may reset upstream usage; inspect the returned goal before continuing.

### Non-destructive runtime restart

1. Run `daemon status` for the selected instance.
2. Run `daemon stop`; confirm durable worker count/paths remain in the result.
3. A later `run --name ...` implicitly restarts the daemon, resumes the stored thread,
   and sends the follow-up.

Recovery: repeated stop is already-stopped success. Observation/control while stopped
returns `daemon_stopped` and never starts a process.

### Raw recovery

1. Take `thread_id` from a typed post-upstream persistence error.
2. Start or foreground-serve the advanced endpoint if required.
3. Use `session resume --thread <id> --name <annotation>` and then the advanced turn
   commands, or repair durable state before re-adopting the common name.

Recovery: never overwrite the malformed registry or assume the upstream thread was
rolled back. Preserve the reported IDs and log/state paths.

## 9. Error and refusal vocabulary

| Kind | Meaning | Required next action |
|---|---|---|
| `invalid_params` | Local argument, prompt, schema, path, number, or combination invalid. | Correct the named field; exit 2. |
| `worker_name_exists` | `start` name already exists in selected instance. | Use `run --name <name>` or choose a new unique name. |
| `worker_not_found` | Name absent for continuation/observation/control. | Use `start --name <name>` or select the right instance. |
| `daemon_stopped` | A non-autostart command selected an inactive runtime. | Use `start`/`run` to restart, or stop if observation was unintended. |
| `daemon_start_failed` | Implicit startup failed readiness. | Inspect the returned log/path/cause; no arbitrary sleep retry. |
| `timeout_active` | Local wait expired while turn remains active. | Use returned status/messages/interrupt commands. |
| `turn_not_active` | No matching active turn, including exact already-finished race. | Inspect status/history; start a later `run` if more work is needed. |
| `model_unavailable` / `effort_unsupported` | Requested tier/model/effort not live-supported. | Choose from returned discovery data; no fallback occurred. |
| `registry_error` | Durable state malformed/unwritable or post-upstream persistence failed. | Preserve file/IDs; use returned raw recovery path. |
| `limits_unavailable` | Current authentication/provider does not expose limits. | Treat capacity as unknown; do not infer it. |
| `incomplete_completion` | Terminal success lacked expected final/schema output. | Inspect returned messages/history and upstream error details. |
| `codex_failure` / `codex_protocol_error` | Upstream operation or contract failed. | Follow typed details; unrelated errors are never disguised as idle races. |

## 10. Docs to update on the implementation branch

| Doc | What changes |
|---|---|
| `skills/subagent-driven-development/codex-worker.md` | Lead with start/run, instance/environment behavior, outputs, lifecycle, proxies, and advanced recovery appendix. |
| `skills/subagent-driven-development/codex-model-selection.md` | Show tier-first start syntax, raw-model escape, persisted policy, and live no-fallback validation. |
| `skills/subagent-driven-development/SKILL.md` | Require collision-resistant named workers and use short `run` follow-ups; keep native Claude Code path intact. |
| `skills/using-superdev/references/codex-tools.md` | Replace low-level launch choreography with common façade examples while preserving Codex opt-in wording and Claude Code availability. |
| `bin/codex-worker` and CLI `--help` | Public launcher plus exhaustive common/advanced families and recovery-oriented help. |
| `RELEASE-NOTES.md` and plugin manifests | Describe surface change and bump/install through the plugin release procedure after acceptance. |

## 11. Delta summary

The release adds a PATH-installed, instance-aware common façade: synchronous `start`
and `run`; name-based status/messages/history/steer/interrupt; native goal and limits
proxies; and non-destructive daemon stop. Claude session identity and process cwd remove
normal setup flags, while dedicated flags/environment support other harnesses. Existing
daemon/model/session/turn commands remain as the advanced compatibility layer; daemon
`shutdown` remains an alias rather than a removal. No destructive cleanup, batch
scheduler, streaming mode, or hidden metric inference is added.
