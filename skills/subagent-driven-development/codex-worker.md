# Codex worker commands

Use this reference only when the operator or plan explicitly selects a local Codex
worker. Claude Code remains an equal native SDD mechanism and the coordinator keeps
the normal worktree, task-brief, report, and independent-review contracts.

## Start, then continue

From the intended worktree, create one collision-resistant worker name: a readable
role plus a random or numbered suffix prevents concurrent workers in one instance from
colliding. `start` creates a name and sends its first message; `run` continues that
same configuration. Every client command writes exactly one JSON object to stdout;
inspect `result.worker`, `result.messages`, and any `structured_output` rather than
reconstructing terminal answers from events.

```sh
codex-worker start --name implement-a31 --prompt-file task.md
codex-worker run --name implement-a31 --prompt "Run the focused gate and report."
```

Creation defaults to the resolved process cwd, full access, the `medium` tier, and
`medium` effort. Choose `--read-only` explicitly for a reviewer. Creation can also set
an objective, budget, per-turn output schema, or selected tier:

```sh
codex-worker start --name review-b32 --prompt-file review.md \
  --tier very-smart --read-only --goal "Review the change" --token-budget 12000 \
  --output-schema review-schema.json
```

The normal tier policy is in [Codex model selection](codex-model-selection.md). It has
only `medium` → Terra and `very-smart` → Sol; raw `--model` is the mutually exclusive
live-discovered escape hatch. `run` accepts only the name, one prompt source, and
per-turn `--output-schema`/`--timeout`: it cannot change cwd, access, tier, model,
effort, or goal. Terminal worker evidence maps to the normal SDD report statuses:
`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.

## Coordinate active work

Use names, not session/thread/socket paths, for the ordinary surface:

```sh
codex-worker status --name implement-a31
codex-worker messages --name implement-a31 --tail 2
codex-worker steer --name implement-a31 --prompt "Prioritize the failing test."
codex-worker interrupt --name implement-a31
```

`status` reports configuration and latest state; `messages` is the bounded live view;
`history --name ... --tail N` is durable turn read-back. `steer` affects only an active
turn. `interrupt` is the sole common cancellation command and can return an honest
already-idle race.

The harness owns fan-out. It launches independent shell commands and correlates each
one by `result.worker.name`, never launch order:

```sh
(cd "$IMPLEMENT_A_WORKTREE" && codex-worker start --name implement-a31 --prompt-file implement-a.md) &
(cd "$IMPLEMENT_B_WORKTREE" && codex-worker start --name implement-b32 --prompt-file implement-b.md) &
(cd "$REVIEW_C_WORKTREE" && codex-worker start --name review-c33 --prompt-file review-c.md) &
(cd "$REVIEW_D_WORKTREE" && codex-worker start --name review-d34 --prompt-file review-d.md) &
(cd "$VERIFY_E_WORKTREE" && codex-worker start --name verify-e35 --prompt-file verify-e.md) &
```

Use the harness's normal join/wait mechanism. Each worker needs its own appropriate
worktree and distinct named conversation, with the usual task brief, report,
review-package, and independent-review handoffs; no implementer is its own reviewer.

## Lifecycle and native proxies

`start` and `run` bring up the selected managed runtime as needed. Reads and controls
do not. `codex-worker daemon stop` is non-destructive: it stops only the runtime and
preserves workers, logs, configuration, and recovery identities; a later `run`
continues the same worker. `daemon status` diagnoses the selected instance.

`goal set`/`goal show` proxy Codex's native objective and budget state; `limits` returns
the authoritative native account limits or an explicit unavailable result. A status-
or budget-only goal update also returns authoritative provider state: inspect it rather
than assuming the requested status won over provider budget invariants. An unavailable
limits result means capacity is unknown and must not be inferred. These
commands, as well as `status`, `messages`, `history`, `steer`, and `interrupt`, do not
start a stopped runtime.

## Technical appendix: recovery and advanced compatibility

The common commands select an instance in this precedence order: `--instance`,
`CODEX_WORKER_INSTANCE`, `CLAUDE_CODE_SESSION_ID`, then the user-local `default`.
Use `--instance` or the environment override for a non-Claude harness; do not select
transport paths on the ordinary surface. Model policy is selected only at creation; no setting inherits effort from
`CLAUDE_EFFORT`.

A `start`/`run` timeout is a local wait limit, not cancellation. Use `status --name …`
then `messages --name …` (or durable `history --name …`) to observe the same named
turn; explicitly `interrupt --name …` only if cancellation is intended. Do not issue
`run` until `status` or history shows the prior turn is terminal: a restart resumes the
stored conversation and must not overlap an active old turn. If durable persistence
reports known session/thread IDs, preserve them and the reported log/state paths. Do
not overwrite malformed state or assume an upstream thread was rolled back.

If `start` reports `effort_unsupported`, use its shell-safe corrected `start` action or
choose another advertised effort. The action preserves the original name and tier/raw
model choice; the provider was not silently substituted. If `run` reports
`turn_active`, use its returned named status/messages/steer/interrupt actions instead
of overlapping the existing turn.

For raw recovery, foreground supervision, live model diagnosis, or cursor-level event
inspection, use the advanced compatibility families: `daemon serve`/`shutdown`,
`model list`, `session start`/`resume`/`list`/`show`, and `turn start`/`status`/`wait`/
`events`/`steer`/`interrupt`. Raw `session resume --thread <id> --name <annotation>`
repairs a recorded upstream thread; raw commands require their documented session or
thread selectors. For a retained raw UUID, use `session resume --session <uuid>` before
raw `turn status`; raw `turn steer` and raw `turn interrupt` retain the same explicit
control semantics. A raw turn selector is never a later control selector. Keep this
escape hatch separate from ordinary named-worker work.
