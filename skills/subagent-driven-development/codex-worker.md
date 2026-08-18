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

Do not classify an interrupted or timed-out wait as cancellation automatically.
`turn wait` observes a turn; inspect `turn status`, use `turn steer` to add an
instruction, or use `turn interrupt` deliberately, then wait for the authoritative
terminal snapshot.

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
