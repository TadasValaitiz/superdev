# Codex worker commands

Use this reference only when the operator or plan explicitly selects a local Codex
worker. Claude Code remains an equal native SDD mechanism. Keep the normal worktree,
task brief, report, review-package, and independent-review contracts.

## Trusted preflight

Before the first Codex dispatch in a session, require one successful bundled preflight.
Set `SUPERDEV_PLUGIN_ROOT` from `CLAUDE_PLUGIN_ROOT` when present; otherwise derive the
canonical plugin root containing the exact loaded `SKILL.md` path.

```sh
"$SUPERDEV_PLUGIN_ROOT/skills/subagent-driven-development/scripts/install-codex-worker" \
  && codex-worker --version
```

The preflight accepts only a UV-owned executable whose version exactly matches the
loaded plugin manifest. It installs an absent or mismatched tool non-editably with
`uv tool install --reinstall` from that trusted package. A foreign executable earlier
on PATH is a refusal: follow the reported `uv tool update-shell` or current-shell PATH
repair, then retry. A failed attempt does not satisfy the preflight; after success, do
not rerun it in that session unless a later typed version-skew refusal explicitly
requires coordinated repair. Never invoke the source launcher or fall back to an
absolute source path. Native Claude-only work needs neither this preflight nor UV.

UV owns one mutable global command, so a mismatch repair affects every open room.
Coordinate rooms using other cached plugin versions before repair. `codex-worker
--version` and `uv tool list` are safe diagnostics. Package lifecycle commands are
maintenance opportunities, not routine dispatch ceremony. A local checkout, a pinned
Git URL, and a future registry release remain valid explicit sources:

```sh
uv tool install --reinstall /path/to/local/superdev/skills/subagent-driven-development/scripts
uv tool install --reinstall 'git+https://github.com/TadasValaitiz/superdev.git#subdirectory=skills/subagent-driven-development/scripts'
uv tool install --reinstall codex-worker
uv tool list
uv tool upgrade codex-worker
uv tool uninstall codex-worker
```

Reinstalling or uninstalling the tool does not remove durable workers, callbacks, or
registries. It also does not grant authority to stop the global service.

## Start, then continue

Worker names are globally unique across every Claude room and terminal on the machine.
Mint a readable role plus a random suffix of at least four hexadecimal characters, for
example `review-a91c`; a random suffix avoids global clashes. `start` atomically creates
the name and sends the first message. `run` continues that exact durable worker.

Creation always names an explicit absolute cwd; ambient shell or Claude cwd is context,
not an implicit creation choice:

```sh
codex-worker start --name implement-a31f --cwd /absolute/project --prompt-file task.md
codex-worker run --name implement-a31f --prompt "Run the focused gate and report."
```

Every client invocation emits exactly one JSON object. Read the returned object rather
than reconstructing an answer from events; inspect `result.worker`, `result.messages`,
and any `structured_output`. In every implementer/reviewer handoff,
report `result.worker.session_id`, `result.worker.thread_id`, and
`result.worker.attach.resume_command`, as well as the worker name, exact controller resume command,
creation cwd, terminal SDD status, report path, commits, tests, and concerns. The Codex
thread ID in the attach route is distinct from the wrapper session UUID.

Keep the two resume routes visibly distinct in the handoff:

```text
Human attach (verbatim returned value): result.worker.attach.resume_command
Controller continuation: codex-worker run --name implement-a31f --prompt <follow-up>
```

Creation defaults to full access, the `medium` tier, and `medium` effort. Select
`--read-only` for a reviewer. Creation can also set a goal, token budget, output-schema,
or elevated tier:

```sh
codex-worker start --name review-b32e --cwd /absolute/project --prompt-file review.md \
  --tier very-smart --read-only --goal "Review the change" --token-budget 12000 \
  --output-schema review-schema.json
```

Creation can also fix Codex config overrides for the worker's life. `--search` enables
live web search (`web_search="live"`, what `codex --search` sets), so one research worker
answers many questions without reloading skills per call. `--config KEY=VALUE` is a
repeatable `codex -c` override: dotted KEY, VALUE parsed as JSON when it parses,
otherwise a string. The overrides are sent on `thread/start`, re-sent when a detached
worker is resumed, and returned as `result.worker.config`:

```sh
codex-worker start --name research-c41d --cwd /absolute/scratch --prompt-file question.md \
  --read-only --search
codex-worker run --name research-c41d --prompt "Next question: ..."
```

The model policy is in [Codex model selection](codex-model-selection.md). `run` accepts
only the globally unique name, one prompt source, and per-turn output-schema/timeout;
it cannot change cwd, access, tier, model, effort, config, goal, callback binding, or
listener.
Terminal evidence maps to `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.

## Callback guidance

Callback-routing Claude metadata, including `CLAUDE_CODE_SESSION_ID`, is callback-only.
It does not select the global service, partition global lookup, namespace a name, or
change what a human TUI can resume. `CLAUDE_PLUGIN_ROOT` identifies only the loaded
package for trusted preflight; it never selects runtime infrastructure. The origin route is captured once at creation;
later commands under different ambient Claude metadata still resolve the same global
name.

The automatic terminal callback is the normal no-poll completion path. Continue with
other work; do not pause or wait for a reply. If a callback is absent or unsuccessful,
recover the authoritative result with `status/messages/history` by name.

Initialization gives a worker this global proactive form and its collision-resistant
readable worker name; a random suffix avoids global clashes:

```sh
codex-worker message --name <name> --message-file update.md
```

`--message` is the short-text alternative. The command does not pause, steer, or
interrupt. It does not wait for Codex. `written` proves a local write, never `delivered`.
`--cc-agent-name` redirects one-send proactive delivery only and never changes the
stored origin. Never pass or expose callback credentials in prompts or reports.

## Coordinate active work

Ordinary work uses the global name only. Direct WebSocket/listener flags belong only to
service creation or supervised maintenance; after creation they never appear on common
commands.

```sh
codex-worker status --name implement-a31f
codex-worker messages --name implement-a31f --tail 2
codex-worker history --name implement-a31f --tail 2
codex-worker steer --name implement-a31f --prompt "Prioritize the failing test."
codex-worker interrupt --name implement-a31f
```

`status` reports identity, authoritative state, and attach metadata. `messages` is the
bounded live view; `history` is durable read-back. `steer` and `interrupt` bind the
observed active turn and may return an honest already-finished race. A caller exit and
a local timeout never cancel a turn or stop infrastructure.

The harness owns fan-out and correlates each one-object result by
`result.worker.name`, never launch order. Every creation carries its own explicit cwd:

```sh
codex-worker start --name review-c33a --cwd "$REVIEW_C_WORKTREE" --prompt-file review-c.md &
codex-worker start --name review-d34b --cwd "$REVIEW_D_WORKTREE" --prompt-file review-d.md &
codex-worker start --name verify-e35c --cwd "$VERIFY_E_WORKTREE" --prompt-file verify-e.md &
```

Use the harness's normal join/wait mechanism. Each worker needs an appropriate
worktree and distinct named conversation. No implementer is its own reviewer.

## Goals, limits, and recovery

`goal set`/`goal show` proxy Codex's native objective and budget state. `limits`
returns authoritative provider capacity or an explicit unavailable result; never infer
a number. Inspect returned goal state rather than assuming an update won over provider
budget invariants.

A `start`/`run` timeout is a local wait limit, not cancellation. Use `status --name`,
then `messages --name` or `history --name`. Do not issue `run` until the prior turn is
terminal; it must not overlap an active old turn. Explicitly `interrupt --name` only
when cancellation is intended.

For raw recovery, foreground supervision, live model diagnosis, or cursor-level event
inspection, use the advanced compatibility families: `model list`, `session
start`/`resume`/`list`/`show`, and `turn start`/`wait`/`status`/`events`/`steer`/
`interrupt`. Raw `session resume --thread <id> --name <annotation>` repairs a retained
upstream thread. For a retained wrapper UUID, use `session resume --session <uuid>`.
Raw endpoint selection is an expert diagnostic path, not a normal worker recipe.
The exact raw controls are `turn steer` and `turn interrupt`. `daemon serve` remains a
hidden foreground supervision/debugging entry point; do not use it for ordinary work.

Model policy is selected only at creation; no setting inherits effort from
`CLAUDE_EFFORT`. Full access and read-only remain explicit creation policies. If
`effort_unsupported` refuses a start, use the returned supported efforts without
silently substituting a model. Preserve every known session/thread/attach identity and
durable path on partial failure.

## Supervised machine-wide maintenance

`codex-worker daemon stop` and `codex-worker daemon restart` are dangerous,
machine-wide maintenance commands. They can disconnect every Claude room and TUI, not
just the caller's worker. Agents use either command only with explicit human supervision
and agreement after reviewing the complete global activity/impact report.

They are never cleanup, never normal task completion, never callback recovery, and never
an automatic version-repair action. `--force` is never automated or copied from a
recovery hint. Ordinary completion leaves the global service running. An active-work
refusal is a safe stop: report it and wait for human direction rather than escalating.

The service may replace an incompatible generation automatically only when its
authoritative global inventory proves zero active turns. Otherwise it returns a typed
busy refusal without interruption. An occupied listener is preserved; never kill an
unknown port peer or choose an unreported fallback.

## Technical appendix

The one global service uses `ws://127.0.0.1:4500` by default. Ordinary `start` never
supplies a listener argument. Only a supervised diagnostic or isolated fixture may use
`start` or `daemon start` to deliberately establish another connectable public listener
for a new generation. Later common commands reuse the stored listener and attach route without
transport arguments. `daemon status` is read-only and does not start the service.

Advanced raw model/session/turn commands remain the lossless diagnostic boundary and
may use their documented explicit socket bypass. That bypass neither creates another
managed service nor belongs in ordinary task, callback, RESUME, or cleanup guidance.
