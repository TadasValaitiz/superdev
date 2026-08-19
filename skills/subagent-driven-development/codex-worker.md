# Codex worker broker

Use this reference when the implementation plan explicitly selects a local Codex
worker. The broker is local JSON-RPC over an owner-only Unix socket, not MCP and
not a cloud service. Claude Code remains the coordinator: it owns the daemon,
worktrees, task handoffs, and review gates.

## Start and discover

The coordinator starts the daemon explicitly in a managed foreground process and
keeps its stderr log. Clients do not auto-start it and never fall back to a
one-shot `codex exec` workflow:

```sh
codex-worker --socket "$SOCKET" daemon serve --state "$STATE"
codex-worker --socket "$SOCKET" daemon status
codex-worker --socket "$SOCKET" model list
```

Read the live `model list` result before choosing a model or effort. Do not use
remembered aliases or assume that a model supports an effort it did not return.
If the daemon is absent, report that fact and start the exact `daemon serve`
command; do not invent a different lifecycle command.

Resolve SDD's two tiers through [Codex model selection](codex-model-selection.md);
that appendix owns model meaning and effort selection, while this reference owns
worker lifecycle and recovery mechanics.

## One session per role and worktree

The coordinator creates worktrees using the normal SDD/worktree procedure. Give
each implementer and reviewer a distinct session and worktree, even when the
same model is selected. Session UUIDs are the stable logical identities; names
are annotations only.

```sh
codex-worker --socket "$SOCKET" session start \
  --cwd "$IMPLEMENTER_WORKTREE" --name implementer --model "$MODEL"
codex-worker --socket "$SOCKET" turn start --session "$SESSION_UUID" \
  --prompt-file "$TASK_BRIEF" --model "$MODEL" --effort "$EFFORT"
codex-worker --socket "$SOCKET" turn wait --session "$SESSION_UUID"
codex-worker --socket "$SOCKET" turn events --session "$SESSION_UUID"
```

Every client command prints one JSON envelope. For every `session start` and
`session resume` response, read the field paths
`.result.session.session_id` and `.result.session.thread_id` and retain those
values before running later commands. Do not assign the whole JSON response to
`SESSION_UUID` or `THREAD_ID`; the placeholders above mean the extracted field
values, not the response envelope.

The normal SDD file handoffs still apply: provide the task brief, collect the
worker's report, and generate/pass the review-package file. A Codex implementer
cannot be the required independent reviewer of its own diff; a worker never
reviews its own diff. The coordinator must use a distinct reviewer session (and
preserve the existing spec-compliance and code-quality review gates).

Codex terminal state is evidence for the SDD report, not a replacement for it:

| Worker outcome | SDD handling |
|---|---|
| completed, with report/tests/evidence complete | `DONE` |
| completed, but the report records unresolved concerns | `DONE_WITH_CONCERNS` |
| stopped because required context or a handoff is missing | `NEEDS_CONTEXT`; supply it and re-dispatch |
| failed because the daemon/Codex/workspace cannot safely continue | `BLOCKED`; preserve evidence and resolve the blocker |

Only a `wait_timeout` error means that observation timed out; it does not cancel
the turn. A `turn wait` timeout exits 1 and returns an error envelope whose
`.error.data.kind == "wait_timeout"`, not a result envelope. That timeout
means work remains active: the error sets `.error.data.details.active == true`
and `.error.data.details.next_actions` to concrete `turn status`, `turn wait`,
`turn steer`, and `turn interrupt` commands for the same session. A successful
terminal `turn wait` returns `.result.turn.status`; `turn status` reports a
latest terminal state at `.result.latest_turn.status`. Turn commands select a
conversation with `--session` or `--thread`; `--turn` is unsupported and a
returned `turn_id` is evidence, not a later selector. An authoritative
`.result.turn.status == "interrupted"` from `turn wait`, or
`.result.latest_turn.status == "interrupted"` from `turn status`, is
terminal/incomplete: reconcile the disk and report evidence and normally map it
to `NEEDS_CONTEXT` or `DONE_WITH_CONCERNS`. Never treat an interrupted turn as
merely a wait failure. Use `turn status`, `turn steer`, or deliberate
`turn interrupt` as appropriate, then wait for the authoritative terminal
snapshot.

## Recovery and cwd safety

If the daemon or caller disappears, restart the same explicit `daemon serve`,
then attach the retained conversation:

```sh
codex-worker --socket "$SOCKET" session resume --session "$SESSION_UUID"
codex-worker --socket "$SOCKET" turn status --session "$SESSION_UUID"
```

If the registry mapping is missing but the raw thread ID from Codex is recorded, use
the explicit repair path and retain the newly returned UUID:

```sh
codex-worker --socket "$SOCKET" session resume \
  --thread "$THREAD_ID" --name recovered-implementer
```

Raw recovery validates the cwd returned by Codex before persisting the repaired
mapping. A session's cwd is immutable: resume does not accept a replacement cwd,
turns cannot retarget it, and the session cannot be retargeted; a different
worktree requires a new session. If a turn completes between status and
steer/interrupt, accept the typed benign race and do not implicitly control a
new turn.

## Scope boundary

Brainstorming and design reasoning remain in the main session (the main Claude
Code session). Use a Codex worker for an explicitly delegated implementation or
other planned task, not as a substitute for the main-session brainstorming
conversation.
