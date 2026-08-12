## Subagent dispatch requires multi-agent support

Add to your Codex config (`~/.codex/config.toml`):

```toml
[features]
multi_agent = true
```

This enables `spawn_agent`, `wait_agent`, and `close_agent` for skills like `dispatching-parallel-agents` and `subagent-driven-development`. When using subagent-driven-development, you should always close implementer and reviewer subagents when they have finished all their work.

## Subagent model routing

For Superdev dispatches, always set `model` and `reasoning_effort` explicitly. An
omitted override inherits the coordinator's model and can silently spend the most
capable tier on mechanical work.

Use `fork_turns: "none"` for SDD implementers and reviewers. Their context crosses
the boundary through brief, report, grounding, and diff files; inheriting the full
conversation defeats that isolation. In Codex, full-history forks also cannot accept
model or effort overrides.

When the following models are available, use this routing table:

| Work | Model | Effort |
|---|---|---|
| Complete-spec transcription or isolated mechanical edit | `gpt-5.6-luna` | `medium` |
| Small mechanical review | `gpt-5.6-terra` | `medium` |
| Multi-file integration, ordinary debugging, task review | `gpt-5.6-terra` | `high` |
| Difficult cross-component debugging | `gpt-5.6-sol` | `high` |
| Architecture, design, final whole-branch review | `gpt-5.6-sol` | `xhigh` |

If those model IDs are unavailable, inspect the dispatch tool's current model list
and choose the nearest cheap, balanced, or frontier equivalent explicitly. Never
remove the override merely to make the call valid.

Do not dispatch an agent just to run deterministic commands such as `rg`, AST/import
inventory scripts, Ruff, pytest, `jq`, or generated-reference checks. Run those tools
directly and dispatch only when their outputs require independent judgment or can be
analyzed concurrently with other useful work.

## Environment Detection

Skills that create worktrees or finish branches should detect their
environment with read-only git commands before proceeding:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

- `GIT_DIR != GIT_COMMON` → already in a linked worktree (skip creation)
- `BRANCH` empty → detached HEAD (cannot branch/push/PR from sandbox)

See `using-git-worktrees` Step 0 and `finishing-a-development-branch`
Step 1 for how each skill uses these signals.

## Codex App Finishing

When the sandbox blocks branch/push operations (detached HEAD in an
externally managed worktree), the agent commits all work and informs
the user to use the App's native controls:

- **"Create branch"** — names the branch, then commit/push/PR via App UI
- **"Hand off to local"** — transfers work to the user's local checkout

The agent can still run tests, stage files, and output suggested branch
names, commit messages, and PR descriptions for the user to copy.
