# Codex model selection

Read this reference only when the operator or plan explicitly selects a Codex worker.
Claude Code remains coordinator; native Claude model routing stays in `SKILL.md`.

## The two mappings

| SDD tier | Codex model | Operational meaning |
|---|---|---|
| `very smart` | `gpt-5.6-sol` | Frontier choice for architecture, difficult reasoning/coding, escalation, and dispatched design/final gates. |
| `medium` | `gpt-5.6-terra` | Balanced default for normal implementation, routine integration/debugging, and ordinary per-task review. |

`very smart` → `gpt-5.6-sol`; `medium` → `gpt-5.6-terra`.

Sol is the higher-judgment tier; Terra is the everyday engineering tier. These are the
only normal SDD recommendations for now. OpenAI describes Sol as its flagship for
complex professional work and describes Terra as balancing intelligence and cost
([model catalog](https://developers.openai.com/api/docs/models),
[Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), checked
2026-08-19). Runtime selection still follows the daemon's live response.

## Discover before dispatch

Run:

```sh
codex-worker --socket "$SOCKET" model list
```

Confirm the exact selected ID exists and read that model's returned
`supported_efforts`. Effort is independent of the SDD tier: choose only a
live-supported value. If the pinned model or desired effort is absent, block and
report it; never silently substitute another model or effort.

## Pin the model and effort

For a normal `medium` task:

```sh
codex-worker --socket "$SOCKET" session start \
  --cwd "$WORKTREE" --name "$ROLE" --model gpt-5.6-terra
codex-worker --socket "$SOCKET" turn start \
  --session "$SESSION_UUID" --prompt-file "$TASK_BRIEF" \
  --model gpt-5.6-terra --effort "$EFFORT"
```

For a dispatched `very smart` task or gate:

```sh
codex-worker --socket "$SOCKET" session start \
  --cwd "$WORKTREE" --name "$ROLE" --model gpt-5.6-sol
codex-worker --socket "$SOCKET" turn start \
  --session "$SESSION_UUID" --prompt-file "$TASK_BRIEF" \
  --model gpt-5.6-sol --effort "$EFFORT"
```

`$EFFORT` means one value returned for that exact model in `supported_efforts`, not a
remembered default. A session retains its latest model annotation; an explicit model
on a later turn may update it. Resume reattaches the same identity and immutable cwd:

```sh
codex-worker --socket "$SOCKET" session resume --session "$SESSION_UUID"
```

Resume is not a model-selection command. After attachment, pin the selected model and
live-supported effort on the next `turn start` when the role requires an explicit
choice.

Follow [Codex worker broker](codex-worker.md) for daemon lifecycle, session identity,
worktrees, task handoff, status/events/wait, steer/interrupt, and recovery. That file is
the mechanics authority; this appendix owns only model and effort choice.

## Not a model catalog

Do not recommend a third tier, enumerate older models, or publish static pricing and
capability matrices. Revisit the two mappings only when a pinned ID is unavailable or
measured SDD evaluations justify a change.
