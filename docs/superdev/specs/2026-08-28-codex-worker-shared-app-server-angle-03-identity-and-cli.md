# Angle 3 — Global worker names lead to explicit attach routes

**Purpose:** Understand which IDs mean what and why Claude session metadata no longer selects worker state.
**Authority:** teaches ruled design — the decision log is the law.
**Formal anchors:** [decision log](./2026-08-28-codex-worker-shared-app-server-decisions.md) D2, D7, D11 · [design §5.3 and §5.5](./2026-08-28-codex-worker-shared-app-server-design.md)
**Series:** 3 of 4

> **Status guide:** LOCKED operator-ruled · MISMATCH current code behaves differently today · FLEXIBLE implementation detail may move inside the ruled boundary · DEFERRED explicitly owned by another design.

## The central question

How can many Claude callers create resumable workers while a human receives the exact Codex thread ID needed by a remote TUI?

## The mental model

A worker name is a global contact name; the wrapper session ID is its durable record key; the
Codex thread ID is the conversation passport. Claude room metadata is merely a return address
for callbacks.

It is not:

- one overloaded “session ID” used for every layer;
- a namespace derived from `CLAUDE_CODE_SESSION_ID`;
- a requirement that callbacks be enabled;
- a hidden thread only the worker can resume;
- permission to collide because two callers live in different rooms.

## Boundaries

This angle owns public naming, identifiers, attach projection and short follow-up commands.
Angle 1 owns service selection. Angle 2 owns what attached clients may do. Angle 4 owns import
of old per-instance names. Callback transport details remain governed by the existing callback
design.

## Concrete journey

### LOCKED — the name is globally unique and intentionally caller-minted

A Claude caller fans out `review-7f3a`, `tests-41de`, and `docs-27b0`. Every `start` atomically
claims one global name. The random or numbered suffix is a skill-level convention that avoids
accidental collision. `run --name review-7f3a` is then enough for every follow-up.

**This means:** concurrent shell commands can address independent workers without passing
Claude metadata repeatedly; a collision is legible instead of an implicit continuation; and
workers survive the originating Claude process.

### LOCKED — results distinguish wrapper and Codex identities

Every start/status projection carries `name`, wrapper `session_id`, Codex `thread_id`, nullable
`turn_id`, listener, and copyable attach/resume commands. The remote command uses `thread_id`,
never the wrapper UUID.

**This means:** Claude can pass a precise resume route to the user; registry recovery can still
use its own stable session key; and support reports can correlate the two without conflation.

### LOCKED — Claude environment is callback metadata, not infrastructure identity

`CLAUDE_CODE_SESSION_ID`, messaging socket, token, PID and optional `cc-agent-name` are captured
only when callback delivery is enabled. A later worker command may run under a different Claude
environment without changing global lookup. **This means:** disabling callbacks does not
disable workers, and remote TUI use has no dependency on a Claude room.

## What the identity model cannot do

It cannot infer a globally unique name from a generic label, expose callback credentials in
status, or reconstruct a missing legacy choice when two old records used the same name for
different threads. It also does not promise per-subagent OS identity because Claude exports no
such value.

## Current mismatch

Today `--instance` and `CODEX_WORKER_INSTANCE` partition registries, often using Claude session
IDs. **SALVAGE:** retain durable wrapper UUIDs, exact thread IDs, callback capture validation,
short named follow-ups, and structured one-object output.

## Visible collisions

- Short commands versus fan-out: required globally unique name is the one repeated selector.
- Human-friendly names versus deterministic migration: divergent duplicates are quarantined, not guessed.

## Flexible and deferred

**FLEXIBLE:** display ordering, optional diagnostic metadata, and attach block formatting while fields remain stable.
**DEFERRED, with landing places:** aliases or hierarchical names belong to a future naming design if collision rates justify them.

## Reconciled outcome

Three LOCKED identity laws replace implicit Claude scoping with one clear global name and an
explicit bridge from wrapper session to remotely resumable Codex thread.
