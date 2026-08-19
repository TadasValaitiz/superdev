# Codex worker command ergonomics — CLI Surface (status: approved for planning — autonomous handoff)

**Design doc:** ./2026-08-19-codex-worker-command-ergonomics-design.md ·
**Decision log:** ./2026-08-19-codex-worker-command-ergonomics-decisions.md

## 0. Global contract

The public executable is `codex-worker`. Every client invocation writes exactly one
JSON object to stdout; human diagnostics and usage remain on stderr. Exit `0` is a
successful command result, `1` is an operational refusal, and `2` is local usage or
validation failure. `--pretty` changes whitespace only.

| Argument | Meaning | Scope |
|---|---|---|
| `--instance <id>` | Explicit daemon-instance identity; highest-precedence selector where supported. | Common commands, advanced model/session/turn, and instance-mode daemon status; invalid for raw daemon serve/shutdown. |
| `--pretty` | Indent the one JSON stdout object. | All client commands; invalid with foreground `daemon serve`. |
| `--socket <absolute-path>` | Explicit raw RPC endpoint. Mutually exclusive with `--instance`; not accepted by common façade commands. | Advanced compatibility commands only. |
| `-h`, `--help` | Render help and exit without a JSON client result. | Every parser level. |

Common-command instance precedence is `--instance`, `CODEX_WORKER_INSTANCE`,
`CLAUDE_CODE_SESSION_ID`, user-local `default`. Advanced model/session/turn clients use
an explicit `--socket` or `--instance`; with neither, they retain
`SUPERDEV_CODEX_WORKER_SOCKET` or the legacy user-temp socket default. Raw daemon serve
and shutdown are socket-only. Daemon status uses instance mode unless `--socket` is
explicitly present, which selects the legacy wire mode. `CLAUDE_EFFORT` and all other
Claude variables do not configure model, effort, access, cwd, or lifecycle.

`<worker-name>` means the exact 1–128 character token
`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. It is compared case-sensitively and never used as a
path component.

All new request/response command models are frozen strict stdlib models with rejected
extra fields. This preserves the plugin executable's no-site-package requirement while
providing the same typed seam promised by the command pattern.

## 1. `codex-worker start` and `codex-worker run` — synchronous worker messages

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker start` | Create one named worker, optionally install its goal, send the first message, wait, and return completion. | `--name <worker-name>` required; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; `--cwd <existing-dir>` default actual process cwd; mutually exclusive `--tier medium\|very-smart` default `medium` or `--model <live-id>`; `--effort <supported-effort>` default `medium`; `--read-only` default false/full access; `--goal <non-empty-str<=4000>` optional; `--token-budget <positive-int>` optional and requires `--goal`; `--output-schema <readable-json-schema-path>` optional/per-turn; `--timeout <finite-seconds>=0` optional/default no deadline; global `--instance`, `--pretty`; `--socket` invalid. | `StartWorkerRequest -> CompletionResponse` | RECORD | NEW |
| `codex-worker run` | Send a follow-up to an existing named worker, wait, and return the same completion shape. | `--name <worker-name>` required; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; `--output-schema <readable-json-schema-path>` optional/per-turn; `--timeout <finite-seconds>=0` optional/default no deadline; global `--instance`, `--pretty`; `--socket` invalid. No cwd/model/tier/effort/access/goal creation flags. | `RunWorkerRequest -> CompletionResponse` | RECORD | NEW |

### 1b. Composition rationale

`start` composes instance readiness, name creation, live policy validation, optional
goal installation, first turn, terminal wait, and projection because there is no useful
operator decision between them. If goal installation fails, the turn does not begin
and recovery IDs are returned. `run` is separate because creation configuration is a
one-time decision; a create-or-continue parser would permit accidental drift. Both are
synchronous because the harness already owns parallel process scheduling (D13, D23).

The prompt has two input spellings but one request field. Output schema and timeout are
per-turn/per-wait controls, so they remain legal on `run`; worker policy does not.
At the adapter edge, full/read-only become thread `sandbox` values
`danger-full-access`/`read-only` on create or resume, and turn `sandboxPolicy` objects
`{type: dangerFullAccess}`/`{type: readOnly, networkAccess: false}` on every message.
Only thread creation sends `allowProviderModelFallback: false`.

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
        "selection": "explicit_final",
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
the CLI JSON-decodes the last selected completion message into `structured_output`
and retains the original message; it never extracts fields from ordinary prose.
When no completed agent message has an explicit final phase, the array contains the last
agent message with its actual null/unknown `phase` and
`selection: "terminal_fallback"`. Only a terminal turn with no agent message at all is
an incomplete completion.

## 2. `codex-worker status/messages/history` — named observation

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker status` | Read persisted worker configuration and latest runtime turn state. | `--name <worker-name>` required; global `--instance`, `--pretty`; `--socket` invalid. | `WorkerStatusRequest -> WorkerStatusResponse` | READ | NEW |
| `codex-worker messages` | Read the latest retained live agent narration by name. | `--name <worker-name>` required; `--tail <positive-int>` default `1` (SEED-DEFAULT); global `--instance`, `--pretty`; `--socket` invalid. | `WorkerMessagesRequest -> WorkerMessagesResponse` | READ | NEW |
| `codex-worker history` | Read the latest durable Codex turns and their completion messages by name. | `--name <worker-name>` required; `--tail <positive-int>` default `1` (SEED-DEFAULT); global `--instance`, `--pretty`; `--socket` invalid. | `WorkerHistoryRequest -> WorkerHistoryResponse` | READ | NEW |

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
| `codex-worker steer` | Append an instruction to the named worker's currently active turn. | `--name <worker-name>` required; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; global `--instance`, `--pretty`; `--socket` invalid. | `SteerWorkerRequest -> ControlResponse` | RECORD | NEW |
| `codex-worker interrupt` | Explicitly cancel the named worker's active turn. | `--name <worker-name>` required; global `--instance`, `--pretty`; `--socket` invalid. | `InterruptWorkerRequest -> ControlResponse` | RECORD | NEW |

### 3b. Composition rationale

Steering changes instructions only and carries no configuration flags because upstream
applies it at a step boundary to the captured active turn. Interrupt is separate and
explicit because caller disconnect, Ctrl-C, timeout, and daemon observation must not
silently mean cancellation (D25, D30). Exact upstream already-idle races are returned as
`turn_not_active`; unrelated provider failures are not collapsed into that result.

## 4. `codex-worker goal` — native objective and budget state

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker goal set` | Create, replace, or update Codex's native goal for a named worker. | `--name <worker-name>` required; at least one of `--goal <non-empty-str<=4000>`, `--status active\|paused\|blocked\|usageLimited\|budgetLimited\|complete`, `--token-budget <positive-int>`; global `--instance`, `--pretty`; `--socket` invalid. | `GoalSetRequest -> GoalResponse` | RECORD | NEW |
| `codex-worker goal show` | Return the named worker's current native goal and provider-reported usage. | `--name <worker-name>` required; global `--instance`, `--pretty`; `--socket` invalid. | `GoalShowRequest -> GoalResponse` | READ | NEW |

### 4b. Composition rationale

Goal state is not duplicated in the worker registry. `set` and `show` directly proxy
Codex's persistent thread goal, resolving only the worker name. A new objective can
reset native usage accounting; the response returns the upstream goal after mutation
so the caller sees that consequence. Status/budget-only updates preserve native usage
according to Codex semantics and return the authoritative provider state. Provider
budget invariants can determine that returned state—for example, a budget below
already-reported `tokens_used` can produce `budgetLimited` despite a requested status—so
callers must inspect the returned goal. There is no `goal clear`: this release has no destructive
common commands, and status `complete` expresses ordinary closure (D18, D29, D32).

`start --goal [--token-budget]` is the one-command initial form and always uses status
`active`. Later goal commands never autostart a stopped daemon.

## 5. `codex-worker limits` — native account capacity

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker limits` | Read Codex's authoritative current account rate-limit state. | Global `--instance`, `--pretty`; no command-specific args; `--socket` invalid. | `LimitsRequest -> LimitsResponse` | READ | NEW |

### 5b. Composition rationale

The command returns the native payload rather than deriving a launch count or policy.
Unsupported authentication returns the stable `limits_unavailable` operational refusal;
its details mark `capacity` as `unknown` and `inference` as `do_not_infer`, with no
fabricated executable recovery action. It never substitutes guessed capacity. It does not autostart, so a fresh caller checks
it after the first normal worker start or while the runtime is already active (D27,
D31).

## 6. `codex-worker daemon` — selected-instance lifecycle

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker daemon status` | Read selected-instance health, PID/child identity, paths, and readiness without starting it. | Global `--instance`, `--pretty`; no command-specific args; `--socket` selects the legacy row below instead. | `DaemonStatusRequest -> DaemonStatusResponse` | READ | EXISTS-REWORK |
| `codex-worker daemon stop` | Gracefully stop the selected daemon and Codex child without deleting durable state. | Global `--instance`, `--pretty`; no command-specific args; `--socket` invalid. | `DaemonStopRequest -> DaemonStopResponse` | RECORD | NEW |
| `codex-worker --socket <absolute-path> daemon status` | Call the existing raw daemon health method and retain its wire response. | `--socket <absolute-path>` required for this mode; `--pretty`; `--instance` mutually exclusive; no command-specific args. | Existing `daemon/status` request/response | READ | EXISTS-KEEP advanced |
| `codex-worker daemon shutdown` | Existing raw graceful shutdown spelling. | `--socket <absolute-path>` optional, otherwise `SUPERDEV_CODEX_WORKER_SOCKET`/legacy default; `--pretty`; `--instance` invalid; no command-specific args. | Existing `daemon/shutdown` request/response | RECORD | EXISTS-KEEP advanced |
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
| `codex-worker model list` | Discover live models and supported efforts. | At most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`; no command args. | Existing `model/list` | READ | EXISTS-KEEP |
| `codex-worker session start` | Create a raw durable session. | `--cwd <absolute-dir>` required; `--name <str>` optional annotation; `--model <live-id>` optional; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `session/start` | RECORD | EXISTS-KEEP |
| `codex-worker session resume` | Resume a persisted session or recover a raw thread. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; `--name <str>` valid only with `--thread`; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `session/resume` | RECORD | EXISTS-KEEP |
| `codex-worker session list` | List persisted sessions. | At most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`; no command args. | Existing `session/list` | READ | EXISTS-KEEP |
| `codex-worker session show` | Inspect one session. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `session/show` | READ | EXISTS-KEEP |
| `codex-worker turn start` | Start a raw turn and return immediately. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; `--model <live-id>` optional; `--effort <supported>` optional; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `turn/start` | RECORD | EXISTS-KEEP |
| `codex-worker turn status` | Read raw current/latest turn state. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `turn/status` | READ | EXISTS-KEEP |
| `codex-worker turn wait` | Wait for raw terminal turn state. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; `--timeout <finite-seconds>=0` default `900` (existing SEED-DEFAULT); at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `turn/wait` | READ | EXISTS-KEEP |
| `codex-worker turn events` | Page retained raw notification events. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; `--after <nonnegative-int>` default `0`; `--limit <int 1..1000>` default `100` (existing SEED-DEFAULT); at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `turn/events` | READ | EXISTS-KEEP |
| `codex-worker turn steer` | Steer a raw active turn. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; exactly one of `--prompt <non-empty-str>` or `--prompt-file <readable-utf8-path>`; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `turn/steer` | RECORD | EXISTS-KEEP |
| `codex-worker turn interrupt` | Interrupt a raw active turn. | Exactly one of `--session <daemon-uuid>` or `--thread <codex-thread-id>`; at most one of global `--instance <id>` or `--socket <absolute-path>`; `--pretty`. | Existing `turn/interrupt` | RECORD | EXISTS-KEEP |

### 7b. Composition rationale

The common surface composes these operations because no harness decision belongs among
them. The advanced commands stay separate because raw-thread recovery, cursor paging,
foreground supervision, and live catalog diagnosis are explicit technical tasks. No
existing spelling is removed or silently redirected (D28, D38).

## 8. Public response models

Every success appears under the outer JSON-RPC `result`. Every object rejects unknown
fields at its service seam; additive response evolution requires an explicit model and
documentation change.

| Model | Exact fields |
|---|---|
| `WorkerView` | `instance: str`; `name: worker-name`; `session_id: uuid`; `thread_id: str`; `cwd: absolute-path`; `tier: medium\|very-smart\|null` (null for raw model); `model: str`; `effort: str`; `access: full\|read_only`. |
| `TurnView` | `turn_id: str`; `status: in_progress\|completed\|failed\|interrupted`; `error: object\|null` copied from authoritative turn state. |
| `AgentMessageView` | `type: "agent_message"`; `item_id: str`; `phase: commentary\|final_answer\|null`; `selection: explicit_final\|terminal_fallback\|live`; `text: str`. Terminal completion and terminal history use explicit-final-or-fallback selection; `messages` and in-progress history use `live`. |
| `MetricEvidence` | `value: JSON\|null`; `source: str`; `availability: measured\|reported\|derived\|unavailable`. |
| `CompletionResponse` | `worker: WorkerView`; `turn: TurnView`; `messages: AgentMessageView[]`; `structured_output: JSON\|null`; `metrics: object[str, MetricEvidence]`; `recovery: RecoveryView`. |
| `RecoveryView` | `status: command-str`; `messages: command-str`; `interrupt: command-str`; optional `raw_resume: command-str\|null`. Commands include shell quoting appropriate to the validated worker/ID token. |
| `WorkerStatusResponse` | `worker: WorkerView`; `daemon_status: ready`; `attached: bool`; `active_turn_id: str\|null`; `latest_turn: TurnView\|null`. A stopped daemon is an error, not a fabricated worker status. |
| `WorkerMessagesResponse` | `worker: WorkerView`; `messages: AgentMessageView[]`; `requested_tail: positive-int`; `returned: nonnegative-int`; `truncated: bool`; `latest_cursor: nonnegative-int\|null`. |
| `HistoryTurnView` | `turn_id: str`; `status: in_progress\|completed\|failed\|interrupted`; `started_at: upstream-int64\|null`; `completed_at: upstream-int64\|null`; `messages: AgentMessageView[]`; `error: object\|null`. Integer timestamps preserve upstream values without assigning an undocumented unit. Terminal turns apply explicit-final-or-fallback selection; in-progress turns return available narration as `live` and never infer a terminal message. |
| `WorkerHistoryResponse` | `worker: WorkerView`; `turns: HistoryTurnView[]` chronological; `requested_tail: positive-int`; `returned: nonnegative-int`; `older_available: bool`. |
| `ControlResponse` | `worker: WorkerView`; `action: steer\|interrupt`; `accepted: true`; `turn_id: str`; `status: in_progress\|interrupted`. Idle/race refusal uses `RpcErrorData`. |
| `GoalView` | `thread_id: str`; `objective: str`; `status: active\|paused\|blocked\|usageLimited\|budgetLimited\|complete`; `token_budget: int\|null`; `tokens_used: nonnegative-int`; `time_used_seconds: nonnegative-int`; `created_at: upstream-int64`; `updated_at: upstream-int64`. Integer timestamps preserve upstream values without assigning an undocumented unit. |
| `GoalResponse` | `worker: WorkerView`; `availability: present\|absent`; `goal: GoalView\|null`. `goal set` always returns `present`; `goal show` may return `absent`. |
| `LimitsResponse` | `availability: available`; `rate_limits: object` copied from `account/rateLimits/read` without renamed/dropped provider fields. Unsupported auth uses `limits_unavailable`, not this success model. |
| `InstanceView` | `instance: str`; `source: flag\|environment\|claude_session\|default`; `durable_dir: absolute-path`; `socket_path: absolute-path`; `log_path: absolute-path`. |
| `DaemonStatusResponse` | `instance: InstanceView`; `status: stopped\|starting\|ready\|stopping\|failed`; `daemon_pid: int\|null`; `codex_pid: int\|null`; `worker_count: nonnegative-int`; `readiness: object\|null`; `last_error: object\|null`. |
| `DaemonStopResponse` | `instance: InstanceView`; `status_before: stopped\|starting\|ready\|stopping\|failed`; `status_after: stopped`; `daemon_pid: int\|null`; `codex_pid: int\|null`; `durable_state: "preserved"`; `worker_count: nonnegative-int`. |

Every refusal uses this exact outer/data shape:

```json
{
  "jsonrpc": "2.0",
  "id": "cli",
  "error": {
    "code": -32021,
    "message": "Worker name already exists",
    "data": {
      "kind": "worker_name_exists",
      "retryable": false,
      "source": "codex-worker",
      "details": {},
      "known_ids": {
        "instance": null,
        "name": null,
        "session_id": null,
        "thread_id": null,
        "turn_id": null
      },
      "next_actions": [
        {"command": "codex-worker ...", "reason": "Why this is safe"}
      ]
    }
  }
}
```

The null identities and sample next action illustrate shape. The code/kind pair is
normative. `details` may add kind-specific structured fields but cannot replace
`known_ids` or `next_actions`.

## 9. Operator workflows — sequences and recovery

### First worker in Claude Code

1. From the intended worktree, run `codex-worker start --name implement-7f3 --prompt
   "Implement the approved parser change."`.
2. Read `result.worker` to confirm cwd/model/effort/access and read all
   `result.messages`; if a schema was supplied, read `structured_output`.
3. Send the next instruction with `codex-worker run --name implement-7f3 --prompt
   "Now run the focused checks and report."`.

Recovery: `worker_name_exists` means the conversation already exists—use `run` or choose a
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

## 10. Error and refusal vocabulary

| Code | Kind | Meaning | Required next action |
|---|---|---|---|
| `-32602` | `invalid_params` | Local argument, prompt, schema, path, number, or combination invalid. | Correct the named field; exit 2. |
| `-32021` | `worker_name_exists` | `start` name already exists in selected instance. | Use `run --name <name>` or choose a new unique name. |
| `-32022` | `worker_not_found` | Name absent for continuation/observation/control. | Use `start --name <name>` or select the right instance. |
| `-32023` | `daemon_stopped` | A non-autostart command selected an inactive runtime. | Use `start`/`run` to restart, or stop if observation was unintended. |
| `-32024` | `daemon_start_failed` | Implicit startup failed readiness. | Inspect the returned log/path/cause; no arbitrary sleep retry. |
| `-32030` | `daemon_stop_failed` | Graceful stop did not terminate every reported process before its bounded deadline. | Inspect returned PIDs/status, then retry stop; durable state and verified runtime markers were preserved. |
| `-32025` | `timeout_active` | Local wait expired while turn remains active. | Use returned status/messages/interrupt commands. |
| `-32004` | `turn_active` | A new `start`/`run` turn was refused because the named worker already has active work. | Use returned status/messages/steer/interrupt commands; do not assume the existing turn stopped. |
| `-32005` | `turn_not_active` | No matching active turn, including exact already-finished race. | Inspect status/history; start a later `run` if more work is needed. |
| `-32026` | `model_unavailable` | Requested tier/raw model is absent from live discovery. | Choose from returned discovery data; no fallback occurred. |
| `-32027` | `effort_unsupported` | Selected model does not advertise the effort. | Without `--output-schema`, use the shell-safe corrected `start` action for the first returned supported effort, or choose another returned effort; tier/raw model and name are preserved and no fallback occurred. With `--output-schema`, no executable action is advertised because only the parsed schema reaches the façade: retry with the caller's original schema file and one of `supported_efforts`, as stated in structured `schema_retry` details. |
| `-32011` | `registry_error` | Durable state malformed/unwritable or post-upstream persistence failed. | Preserve file/IDs; use returned raw recovery path. |
| `-32028` | `limits_unavailable` | Current authentication/provider does not expose limits. | Treat capacity as unknown; do not infer it. |
| `-32029` | `incomplete_completion` | Terminal success had no agent message or schema-mode JSON was undecodable. | Inspect returned turn/history and upstream details. |
| `-32020` / `-32015` | `codex_failure` / `codex_protocol_error` | Upstream operation or contract failed. | Follow typed details; unrelated errors are never disguised as idle races. |

## 11. Docs to update on the implementation branch

| Doc | What changes |
|---|---|
| `skills/subagent-driven-development/codex-worker.md` | Lead with start/run, instance/environment behavior, outputs, lifecycle, proxies, and advanced recovery appendix. |
| `skills/subagent-driven-development/codex-model-selection.md` | Show tier-first start syntax, raw-model escape, persisted policy, and live no-fallback validation. |
| `skills/subagent-driven-development/SKILL.md` | Require collision-resistant named workers and use short `run` follow-ups; keep native Claude Code path intact. |
| `skills/using-superdev/references/codex-tools.md` | Replace low-level launch choreography with common façade examples while preserving Codex opt-in wording and Claude Code availability. |
| `bin/codex-worker` and CLI `--help` | Public launcher plus exhaustive common/advanced families and recovery-oriented help. |
| `RELEASE-NOTES.md` and plugin manifests | Describe surface change and bump/install through the plugin release procedure after acceptance. |

## 12. Delta summary

The release adds a PATH-installed, instance-aware common façade: synchronous `start`
and `run`; name-based status/messages/history/steer/interrupt; native goal and limits
proxies; and non-destructive daemon stop. Claude session identity and process cwd remove
normal setup flags, while dedicated flags/environment support other harnesses. Existing
daemon/model/session/turn commands remain as the advanced compatibility layer; daemon
`shutdown` remains an alias rather than a removal. No destructive cleanup, batch
scheduler, streaming mode, or hidden metric inference is added.
