# Codex worker → Claude callbacks — CLI Surface (status: draft)

**Design doc:** ./2026-08-20-codex-worker-claude-callbacks-design.md ·
**Decision log:** ./2026-08-20-codex-worker-claude-callbacks-decisions.md

## 1. `codex-worker start` — capture the originating Claude callback

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [--instance ID] [--pretty] start …` | Create a named worker, optionally bind its originating Claude room, and synchronously return the first terminal result. | `--name <worker>` required; exactly one of `--prompt <text>` or `--prompt-file <path>` required; `--cwd <absolute-or-relative>` default current directory and canonicalized; exactly one policy after defaults: `--tier medium|very-smart` default `medium`, or `--model <id>`; `--effort <level>` default `medium`; `--read-only` default false/full; `--goal <text>` optional; `--token-budget <positive-int>` optional and requires goal; `--output-schema <JSON-file>` optional; `--timeout <finite-nonnegative-seconds>` optional; `--no-callback` default false; global `--instance <id>` optional; global `--pretty` formatting only. `--socket` remains invalid for common commands. | `StartWorkerRequest` with internal secret `callback_capture` constructed locally from ambient Claude variables | FILTER + RECORD | EXISTS-REWORK |

Callback selection is deterministic:

1. `--no-callback` → durable `disabled` state; ambient values are ignored.
2. Valid socket/token/session/PID ambient values that match one live Claude registry
   identity → durable `enabled` binding containing the verified session ID, PID,
   process-start value, endpoint, and canonical Claude config root.
3. Otherwise → durable `unavailable` state; worker creation proceeds and retains the
   safety-checked start-time Claude config root when resolvable.

No public `--cc-agent-name` exists on `start`; D6 reserves that property for one
proactive override only. A later `run` does not inspect or replace ambient callback data.
Before the daemon launches Codex, it removes `CLAUDE_CODE_MESSAGING_SOCKET` and
`CLAUDE_CODE_MESSAGING_TOKEN` from the child environment. Disabled/unavailable bindings
carry nullable secret fields; they never synthesize empty paths or tokens.

The internal `CallbackCapture` JSON object has exactly these six fields and accepts no
extras:

| Field | Type / validation |
|---|---|
| `target_socket` | null, or an absolute non-symlink Unix-socket path equal to the selected live registry record |
| `child_token` | null, or exactly 32 lowercase hexadecimal characters |
| `claude_session_id` | null, or a non-empty string equal to the selected registry `sessionId` |
| `claude_pid` | null, or a positive integer equal to ambient `CLAUDE_PID`, the selected registry PID, and a `messagingSocketPath` basename exactly `<pid>.sock` |
| `claude_proc_start` | null, or a non-empty string equal to the selected registry `procStart` |
| `claude_config_dir` | canonical absolute, owner/safe-ancestor-validated Claude config root used for every later registry lookup |

The first five fields are either all non-null (a full enabled capture) or all null (a
root-only unavailable capture); partial identity is invalid. `no_callback=true` requires
`callback_capture=null`. With `no_callback=false`, a full capture means enabled, while a
root-only or null capture means unavailable. A malformed non-null object is
`invalid_params`, not a silent downgrade. The client preflights the object and the daemon
revalidates it before persistence.

### 1b. Composition rationale

Capture stays part of `start` because there is no operator decision between worker
creation and binding its return route. A separate callback-init command would reintroduce
the launch ceremony this feature removes and create a first-turn race. `--no-callback`
is the single explicit exception (D1, D6, D8).

## 2. `codex-worker message` — send a proactive non-blocking notification

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [--instance ID] [--pretty] message …` | Ask the daemon to relay one proactive event from a named worker to Claude and return after the bounded write attempt. | `--name <worker>` required; exactly one of `--message <text>` or `--message-file <path>` required; `--priority now|next|later` default `next`; `--cc-agent-name <Claude-registry-name>` optional one-send override; global `--instance <id>` optional; global `--pretty` formatting only. `--socket` is invalid. | `MessageWorkerRequest` | FILTER | NEW |

Success result:

```json
{
  "jsonrpc": "2.0",
  "id": "cli",
  "result": {
    "worker": {
      "instance": "default",
      "name": "implement-7f3",
      "session_id": "worker-session-uuid",
      "thread_id": "codex-thread-id",
      "cwd": "/absolute/worktree",
      "tier": "medium",
      "model": "gpt-5.6-terra",
      "effort": "medium",
      "access": "full"
    },
    "event_id": "stable-event-id",
    "attempt": {
      "event_id": "stable-event-id",
      "state": "written",
      "reason": null,
      "attempted_at": "RFC3339 timestamp",
      "attempt_count": 1,
      "turn_id": null
    }
  }
}
```

`written` means only that the complete frame was handed to the local socket. The command
does not print or imply `delivered`. It never waits for a Claude response, and it never
calls, steers, interrupts, or pauses Codex.

The command is injected into the named worker's initialization instructions in this
form:

```bash
codex-worker --instance default message --name implement-7f3 \
  --message "I found a schema ambiguity; I am continuing conservatively."
```

Urgent and low-priority variants are explicit:

```bash
codex-worker --instance default message --name implement-7f3 --priority now \
  --message "Blocking safety issue: do not merge yet."
codex-worker --instance default message --name implement-7f3 --priority later \
  --message "Progress update: deterministic checks are green."
```

One-send override:

```bash
codex-worker --instance default message --name implement-7f3 \
  --cc-agent-name orchestrator-original \
  --message "Please inspect the schema boundary."
```

The override does not change the stored default. Zero matching live names return
`callback_target_not_found`; multiple matching live names return
`callback_target_ambiguous`. Neither falls back to the origin or an arbitrary match.
The daemon resolves overrides only below the binding's persisted verified Claude config
root. An `unavailable` worker may use an override; a `disabled` worker refuses every send,
including an override.

### 2b. Composition rationale

This is one command rather than `prepare` + `send` because no human decision belongs
between building and relaying one notification. It is separate from `run` and `steer`
because it communicates outward without changing the Codex conversation. Worker name is
required because daemon fan-out has no reliable per-worker process identity, and the
injected command also pins `--instance` because names are only instance-local (D4, D5,
D9, D10, D18). Explicit `--message|--message-file` input follows the existing common
prompt pattern and keeps input validation local (D13); final envelope sizing remains a
daemon concern (D20).

## 3. `codex-worker status` — inspect redacted callback state

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [--instance ID] [--pretty] status --name WORKER` | Inspect runtime state plus callback availability and the last terminal attempt without exposing credentials. | `--name <worker>` required; global `--instance <id>` optional; global `--pretty` formatting only. `--socket` is invalid. | `WorkerStatusRequest` → additive `WorkerStatusResponse.callback` | READ | EXISTS-REWORK |

Additive callback projection:

```json
{
  "callback": {
    "state": "enabled",
    "pending_terminal_count": 0,
    "last_terminal_attempt": {
      "event_id": "stable-event-id",
      "state": "written",
      "reason": null,
      "attempted_at": "RFC3339 timestamp",
      "attempt_count": 1,
      "turn_id": "codex-turn-id"
    }
  }
}
```

Allowed binding states are `enabled`, `disabled`, and `unavailable`. The target socket,
child token, Claude session/PID/process-start metadata, config root, peer token, and
registry/key paths never appear.

### 3b. Composition rationale

Callback state belongs in the existing worker status because it is an annotation on the
same named worker lifecycle and introduces no operator decision that warrants another
status family. It is additive to the current runtime fields (D1, D7).

## 4. Callback RPC — daemon boundary

| Method | Purpose | Params | Request/response | Status |
|---|---|---|---|---|
| `worker/start` | Existing common start plus internal capture. | Exact `StartWorkerRequest` fields, including `no_callback` and nullable strict six-field secret `callback_capture` defined in §1. | `StartWorkerRequest` → existing `CompletionResponse` | EXISTS-REWORK |
| `worker/message` | Relay one proactive event. | Exact `MessageWorkerRequest`: `name`, `message`, `priority`, `cc_agent_name`. | `MessageWorkerRequest` → `CallbackSendResponse` | NEW |
| `worker/status` | Existing status plus redacted callback view. | Exact `WorkerStatusRequest`: `name`. | `WorkerStatusRequest` → reworked `WorkerStatusResponse` | EXISTS-REWORK |

The owner-only managed Unix socket is the only RPC path for callback capture. Secret
capture data must not be accepted on raw explicit-socket methods, included in request
logging, or echoed in faults.
This is a product-propagation boundary, not a new filesystem sandbox: the callback
feature does not prevent an existing same-UID full/read-capable worker from independently
inspecting user-readable Claude files.

### 4b. Claude callback event envelopes

All three wire events use the same closed outer shape:

```json
{
  "schema": "codex-worker.claude-callback/v1",
  "event": "turn_terminal",
  "event_id": "stable-event-id",
  "emitted_at": "RFC3339 timestamp",
  "priority": "next",
  "worker": {"instance": "default", "name": "implement-7f3", "session_id": "worker-session-uuid", "thread_id": "codex-thread-id", "cwd": "/absolute/worktree", "tier": "medium", "model": "gpt-5.6-terra", "effort": "medium", "access": "full"},
  "payload": {"completion": "the exact public CompletionResponse JSON object"}
}
```

`event` is exactly one of:

- `turn_terminal`: `payload.completion` is the complete public
  `CompletionResponse.to_dict()` projection, including ordered agent messages,
  structured output (where requested), honest metrics when available, and recovery
  metadata. The final agent message remains intact, so verdict/report/review content is
  not reduced to transport metadata.
- `turn_terminal_reference`: `payload.artifact` contains owner-readable absolute `path`,
  lowercase hex `sha256`, and positive `size_bytes` for an immutable JSON file whose
  content is that same complete completion projection. Claude verifies digest and size
  before using it.
- `worker_message`: `payload.message` is the caller's non-empty prose. It never carries
  callback credentials or invents a reply channel.

Terminal events always use `next`; `worker_message` uses the validated requested
priority. The daemon constructs and sizes the final serialized user line. It counts
JavaScript UTF-16 code units as `len(line.encode("utf-16-le")) / 2`, excluding the
newline. This is deliberately not a client-side estimate.

The surrounding Claude user envelope uses `msg_id = event_id` and UUIDv5 of `event_id`
under literal namespace `5b290fd0-2df0-5c73-980f-04f284476f55`; for example,
`event-fixture-1` maps to `740cb30c-652d-5f4f-bc30-36c14a48d007`. It always uses
`from_mode: "bypass"` and omits `session_id`. When an enabled binding has a captured
origin, `from` remains `uds:<captured-origin-socket>` even for a named override. A
root-only unavailable binding has no origin, so its permitted named override omits
`from`; it never substitutes the destination socket as sender identity.

## 5. Probe scripts — executable research evidence

These scripts live in
`/Users/tadas/Projects/ai-ethics/ai-trading-calibration/scripts/` and import the existing
stdlib-only `send_to_claude.py`. They are not installed as production Superdev commands.

| Command | Purpose | Args (all of them) | Gate | Status |
|---|---|---|---|---|
| `python3 scripts/probe_codex_completion_callback.py …` | Convert a real common-worker completion response into a v1 terminal event and send/dry-run it. | Exactly one input: `--completion-file <path>` or `--completion-stdin`; `--worker-name <name>` required only if absent from completion; `--cc-agent-name <name>` optional live override for probe targeting; `--dry-run` optional; `--event-id <id>` optional deterministic fixture override, otherwise generated; `--pretty` optional. Priority is fixed `next`. | READ + external send | NEW PROBE |
| `python3 scripts/probe_codex_agent_message.py …` | Build one v1 proactive event and send/dry-run it. | `--worker-name <name>` required; exactly one of `--message <text>` or `--message-file <path>` required; `--priority now|next|later` default `next`; `--cc-agent-name <name>` optional; `--dry-run` optional; `--event-id <id>` optional deterministic fixture override, otherwise generated; `--pretty` optional. | READ + external send | NEW PROBE |

When `cc-agent-name` is omitted, a probe uses the ambient
`CLAUDE_CODE_MESSAGING_SOCKET` and child token. Supplying it resolves the target through
the measured Claude registry logic. Both scripts emit exactly one JSON result and never
claim delivery.

## 6. Operator workflows — sequences, not just commands

### Normal no-poll completion

1. Claude runs `codex-worker start --name <unique> --prompt …` with no callback flags.
2. The command may run in Claude's normal background/concurrent shell machinery.
3. The daemon sends one `turn_terminal` event at terminal completion with priority
   `next`; Claude reads the full result from that incoming prompt. If the final envelope
   would exceed the line cap, it sends `turn_terminal_reference` instead with an
   owner-readable absolute artifact path, SHA-256 digest, and byte size; Claude verifies
   and reads that complete JSON artifact.
4. Claude optionally runs `codex-worker run --name <same> --prompt …`.

Recovery: if no callback arrives, Claude runs `codex-worker status --name <same>` and
reads the honest callback state/last attempt. `failed` or stale target does not erase the
Codex result; `messages` and `history` recover it.

### Codex proactive update

1. Initialization tells Codex its worker instance, name, and exact `message` command.
2. Codex invokes `codex-worker --instance <instance> message --name <same>
   --message …` and reads written/typed refusal.
3. Codex continues its task immediately.
4. Claude may respond with `steer` if the turn is active or `run` after it ends.

Recovery: `callback_unavailable` means continue work and include the issue in the final
report. A proactive `callback_send_failed` may be retried deliberately as a new event;
there is no synchronous wait. Automatic terminal outbox entries
retry non-written writes under their original event ID and may duplicate only in the
crash-before-commit window.

### One-message alternate reviewer

1. Codex sends `codex-worker --instance <instance> message --name <worker>
   --cc-agent-name <reviewer> --message …`.
2. The daemon requires exactly one live matching Claude name and sends once.
3. Later proactive/default terminal events continue to use the original binding.

Recovery: not-found or ambiguous is a typed stop for that message. Discover/rename the
Claude room outside Codex, then retry explicitly; never guess a target.

### Standalone or intentionally silent worker

1. Outside Claude, start normally; status reports callback unavailable.
2. Inside Claude, add `--no-callback`; status reports disabled.
3. All ordinary worker results, controls, recovery, and stop remain unchanged.

### Explicit managed-daemon recovery

`codex-worker --instance <instance> daemon start` starts or reuses the selected managed
daemon without starting a Codex turn. `message` remains non-autostarting; a stopped
message refusal points to this command so the operator can restore the relay and then
retry deliberately.

## 7. Errors and exits

| Code / kind | Exit | Meaning | Safe next action |
|---|---:|---|---|
| `-32602 invalid_params` | 2 | Local empty/duplicate message input, invalid priority/name, or malformed capture. | Correct arguments; no daemon lifecycle or send occurred. |
| `-32031 callback_unavailable` | 1 | Worker has no enabled default binding or was explicitly disabled. | Continue work; inspect status. Only `unavailable`, never `disabled`, may use a valid one-send override. |
| `-32032 callback_target_stale` | 1 | The captured Claude session/PID/process-start/endpoint identity no longer matches. | Do not send to the reused endpoint; inspect status and continue recovery through the worker result. |
| `-32033 callback_target_not_found` | 1 | Override name has zero live matches. | Verify the exact Claude agent name outside the Codex turn. |
| `-32034 callback_target_ambiguous` | 1 | Override name has multiple live matches. | Rename/select a unique Claude room; no message was sent. |
| `-32035 callback_target_unsafe` | 1 | Socket, key, registry entry, owner, mode, type, or ancestor failed validation. | Inspect the reported safe reason; do not unlink or chmod unknown paths. |
| `-32036 callback_send_failed` | 1 | Connection/write failed before a proven complete frame. | Inspect worker status and retry deliberately if still useful. |
| `-32037 callback_payload_too_large` | 1 | The daemon's final proactive user line exceeds 1,048,576 JavaScript UTF-16 code units, excluding newline. | Shorten the proactive message; oversized terminal results use an artifact reference automatically. |

Callback-store persistence failures reuse the existing `-32011 registry_error` contract
with known worker/thread/event identities and safe status/messages recovery.

Automatic terminal callback faults are stored in status rather than replacing the
successful/failed/interrupted `CompletionResponse` returned by `start` or `run`.

## 8. Docs to update (same branch, not later)

| Doc | What changes |
|---|---|
| `skills/subagent-driven-development/codex-worker.md` | Callback lifecycle, proactive command, event semantics, recovery, and no-poll guidance. |
| `skills/subagent-driven-development/SKILL.md` | Teach worker initialization to expose the proactive command and teach Claude to rely on callbacks without deleting diagnostic status/wait guidance. |
| `skills/subagent-driven-development/codex-model-selection.md` | No model-routing change; add only a cross-reference if invocation examples enumerate common worker flags. |
| `bin/codex-worker --help` / parser help | New `message`, `start --no-callback`, message flags, and callback status meaning. |
| `docs/reference/claude-code-messaging-protocol.md` in the source research repo | Link the two new probes and record their measured end-to-end results; do not recast them as production CLI. |
| `docs/README.md` in the source research repo | Extend the existing protocol row with both probe names. |

## 9. Delta summary

The common surface adds one top-level `message` command, one `start --no-callback`
escape hatch, and a redacted callback view on `status`. The daemon adds `worker/message`
and internal callback capture on `worker/start`; `run` remains argument-compatible and
uses the stored route. No command is renamed or removed, raw methods do not change, and
the trading repository gains two explicitly non-production probe scripts.
