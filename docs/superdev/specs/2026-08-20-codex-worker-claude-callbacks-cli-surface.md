# Codex worker → Claude callbacks — CLI Surface (status: draft)

**Design doc:** ./2026-08-20-codex-worker-claude-callbacks-design.md ·
**Decision log:** ./2026-08-20-codex-worker-claude-callbacks-decisions.md

## 1. `codex-worker start` — capture the originating Claude callback

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [--instance ID] [--pretty] start …` | Create a named worker, optionally bind its originating Claude room, and synchronously return the first terminal result. | `--name <worker>` required; exactly one of `--prompt <text>` or `--prompt-file <path>` required; `--cwd <absolute-or-relative>` default current directory and canonicalized; exactly one policy after defaults: `--tier medium|very-smart` default `medium`, or `--model <id>`; `--effort <level>` default `medium`; `--read-only` default false/full; `--goal <text>` optional; `--token-budget <positive-int>` optional and requires goal; `--output-schema <JSON-file>` optional; `--timeout <finite-nonnegative-seconds>` optional; `--no-callback` default false; global `--instance <id>` optional; global `--pretty` formatting only. `--socket` remains invalid for common commands. | `StartWorkerRequest` with internal secret `callback_capture` constructed locally from ambient Claude variables | FILTER + RECORD | EXISTS-REWORK |

Callback selection is deterministic:

1. `--no-callback` → durable `disabled` state; ambient values are ignored.
2. Both valid `CLAUDE_CODE_MESSAGING_SOCKET` and
   `CLAUDE_CODE_MESSAGING_TOKEN` → durable `enabled` binding.
3. Otherwise → durable `unavailable` state; worker creation proceeds.

No public `--cc-agent-name` exists on `start`; D6 reserves that property for one
proactive override only. A later `run` does not inspect or replace ambient callback data.

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
      "state": "written",
      "reason": null,
      "attempted_at": "RFC3339 timestamp"
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
codex-worker message --name implement-7f3 \
  --message "I found a schema ambiguity; I am continuing conservatively."
```

Urgent and low-priority variants are explicit:

```bash
codex-worker message --name implement-7f3 --priority now \
  --message "Blocking safety issue: do not merge yet."
codex-worker message --name implement-7f3 --priority later \
  --message "Progress update: deterministic checks are green."
```

One-send override:

```bash
codex-worker message --name implement-7f3 \
  --cc-agent-name orchestrator-original \
  --message "Please inspect the schema boundary."
```

The override does not change the stored default. Zero matching live names return
`callback_target_not_found`; multiple matching live names return
`callback_target_ambiguous`. Neither falls back to the origin or an arbitrary match.

### 2b. Composition rationale

This is one command rather than `prepare` + `send` because no human decision belongs
between building and relaying one notification. It is separate from `run` and `steer`
because it communicates outward without changing the Codex conversation. Worker name is
required because daemon fan-out has no reliable per-worker process identity (D4, D5,
D9, D10). Explicit `--message|--message-file` input follows the existing common prompt
pattern and keeps validation local (D13).

## 3. `codex-worker status` — inspect redacted callback state

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `codex-worker [--instance ID] [--pretty] status --name WORKER` | Inspect runtime state plus callback availability and the last terminal attempt without exposing credentials. | `--name <worker>` required; global `--instance <id>` optional; global `--pretty` formatting only. `--socket` is invalid. | `WorkerStatusRequest` → additive `WorkerStatusResponse.callback` | READ | EXISTS-REWORK |

Additive callback projection:

```json
{
  "callback": {
    "state": "enabled",
    "last_terminal_attempt": {
      "event_id": "stable-event-id",
      "state": "written",
      "reason": null,
      "attempted_at": "RFC3339 timestamp"
    }
  }
}
```

Allowed binding states are `enabled`, `disabled`, and `unavailable`. The target socket,
child token, Claude session metadata, peer token, and registry/key paths never appear.

### 3b. Composition rationale

Callback state belongs in the existing worker status because it is an annotation on the
same named worker lifecycle and introduces no operator decision that warrants another
status family. It is additive to the current runtime fields (D1, D7).

## 4. Callback RPC — daemon boundary

| Method | Purpose | Params | Request/response | Status |
|---|---|---|---|---|
| `worker/start` | Existing common start plus internal capture. | Exact `StartWorkerRequest` fields, including `no_callback` and nullable secret `callback_capture`. | `StartWorkerRequest` → existing `CompletionResponse` | EXISTS-REWORK |
| `worker/message` | Relay one proactive event. | Exact `MessageWorkerRequest`: `name`, `message`, `priority`, `cc_agent_name`. | `MessageWorkerRequest` → `CallbackSendResponse` | NEW |
| `worker/status` | Existing status plus redacted callback view. | Exact `WorkerStatusRequest`: `name`. | `WorkerStatusRequest` → reworked `WorkerStatusResponse` | EXISTS-REWORK |

The owner-only managed Unix socket is the only RPC path for callback capture. Secret
capture data must not be accepted on raw explicit-socket methods, included in request
logging, or echoed in faults.

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
   `next`; Claude reads the full result from that incoming prompt.
4. Claude optionally runs `codex-worker run --name <same> --prompt …`.

Recovery: if no callback arrives, Claude runs `codex-worker status --name <same>` and
reads the honest callback state/last attempt. `failed` or stale target does not erase the
Codex result; `messages` and `history` recover it.

### Codex proactive update

1. Initialization tells Codex its worker name and the `message` command.
2. Codex invokes `message --name <same> --message …` and reads written/typed refusal.
3. Codex continues its task immediately.
4. Claude may respond with `steer` if the turn is active or `run` after it ends.

Recovery: `callback_unavailable` means continue work and include the issue in the final
report. `callback_send_failed` may be retried deliberately; there is no automatic blind
retry and no synchronous wait.

### One-message alternate reviewer

1. Codex sends `message --name <worker> --cc-agent-name <reviewer> --message …`.
2. The daemon requires exactly one live matching Claude name and sends once.
3. Later proactive/default terminal events continue to use the original binding.

Recovery: not-found or ambiguous is a typed stop for that message. Discover/rename the
Claude room outside Codex, then retry explicitly; never guess a target.

### Standalone or intentionally silent worker

1. Outside Claude, start normally; status reports callback unavailable.
2. Inside Claude, add `--no-callback`; status reports disabled.
3. All ordinary worker results, controls, recovery, and stop remain unchanged.

## 7. Errors and exits

| Kind | Exit | Meaning | Safe next action |
|---|---:|---|---|
| `invalid_params` | 2 | Local empty/duplicate message input, invalid priority/name, malformed capture, or oversized encoded line. | Correct arguments; no daemon lifecycle or send occurred. |
| `callback_unavailable` | 1 | Worker has no enabled binding or was explicitly disabled. | Continue work; inspect status or use a valid one-send override. |
| `callback_target_not_found` | 1 | Override name has zero live matches. | Verify the exact Claude agent name outside the Codex turn. |
| `callback_target_ambiguous` | 1 | Override name has multiple live matches. | Rename/select a unique Claude room; no message was sent. |
| `callback_target_unsafe` | 1 | Socket, key, registry entry, owner, mode, type, or ancestor failed validation. | Inspect the reported safe reason; do not unlink or chmod unknown paths. |
| `callback_send_failed` | 1 | Connection/write failed before a proven complete frame. | Inspect worker status and retry deliberately if still useful. |
| `callback_send_uncertain` | 1 | A complete write cannot be proved or disproved. | Do not blindly retry; use event ID when reconciling. |

Automatic terminal callback faults are stored in status rather than replacing the
successful/failed/interrupted `CompletionResponse` returned by `start` or `run`.

## 8. Docs to update (same branch, not later)

| Doc | What changes |
|---|---|
| `skills/subagent-driven-development/codex-worker.md` | Callback lifecycle, proactive command, event semantics, recovery, and no-poll guidance. |
| `skills/subagent-driven-development/SKILL.md` | Teach worker initialization to expose the proactive command and teach Claude to rely on callbacks without deleting diagnostic status/wait guidance. |
| `skills/subagent-driven-development/references/codex-model-selection.md` | No model-routing change; add only a cross-reference if invocation examples enumerate common worker flags. |
| `bin/codex-worker --help` / parser help | New `message`, `start --no-callback`, message flags, and callback status meaning. |
| `docs/reference/claude-code-messaging-protocol.md` in the source research repo | Link the two new probes and record their measured end-to-end results; do not recast them as production CLI. |
| `docs/README.md` in the source research repo | Extend the existing protocol row with both probe names. |

## 9. Delta summary

The common surface adds one top-level `message` command, one `start --no-callback`
escape hatch, and a redacted callback view on `status`. The daemon adds `worker/message`
and internal callback capture on `worker/start`; `run` remains argument-compatible and
uses the stored route. No command is renamed or removed, raw methods do not change, and
the trading repository gains two explicitly non-production probe scripts.
