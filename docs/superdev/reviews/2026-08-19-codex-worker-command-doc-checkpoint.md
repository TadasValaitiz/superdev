# Codex worker command documentation checkpoint

**Date:** 2026-08-19  
**Scope:** Task 7 named-worker documentation checkpoint

## Ownership map

| Document | Owns |
|---|---|
| `skills/subagent-driven-development/SKILL.md` | Concise SDD dispatch rule: Codex is opt-in, collision-resistant names, `start` then `run`, native Claude route preserved. |
| `skills/subagent-driven-development/codex-worker.md` | Product commands, operator workflow, named-worker controls, fan-out, non-destructive stop, and the technical appendix for advanced recovery. |
| `skills/subagent-driven-development/codex-model-selection.md` | Two-tier policy only: medium/Terra, very-smart/Sol, medium default effort, live no-fallback validation, and raw-model boundary. |
| `skills/using-superdev/references/codex-tools.md` | Separates native Codex-harness dispatch from the Claude Code local-worker route. |

## Structural evidence

- The installed launcher help confirms `start` creates a named worker and `run` sends a
  follow-up; both require `--name` and exactly one prompt source.
- `start --help` confirms optional `--tier`, `--model`, `--effort`, `--read-only`,
  `--goal`, `--token-budget`, `--output-schema`, and `--timeout`; `run --help` retains
  only prompt/schema/timeout controls.
- The operator reference leads with the required `implement-a31` `start`/`run` example,
  documents five-command harness-owned fan-out, and sends raw session/turn details to
  its technical appendix.
- Focused structural guards assert collision-resistant naming, `start`/`run`, no
  `daemon ensure`, native-Claude availability, appendix coverage, and separate native
  Codex-harness routing.

## Reviewer A — coordinator usability

### Original review (BLOCK)

VERDICT: BLOCK

FINDINGS:

- [Important] The five-command fan-out example launches every worker from the coordinator’s current directory, yet creation fixes each worker to its process cwd and `run` cannot change it. The following sentence requires distinct worktrees but does not show how to start each command in its assigned worktree. This can create five workers in one worktree, contrary to the SDD contract. Cite: `skills/subagent-driven-development/codex-worker.md:21`, `:33-35`, `:53-65`.
- [Important] Timeout/restart recovery is underspecified for an active turn. The docs say timeout is non-cancelling and suggest status/messages/interrupt, but omit the named waiting/resumption sequence and when it is safe to issue `run`; after a daemon restart, “a later run continues” could be read as sending a follow-up while the timed-out turn remains active. Cite: `skills/subagent-driven-development/codex-worker.md:69-72`, `:87-90`.

WORKFLOW YOU WOULD USE:

- From each assigned worktree, launch with isolated cwd explicitly, e.g. `(cd "$WT_A" && codex-worker start --name implement-a31 --prompt-file implement-a.md) &` through five distinct worktrees/names; correlate JSON by `result.worker.name`.
- Inspect with `codex-worker status --name implement-a31` and `codex-worker messages --name implement-a31 --tail 2`; steer active work with `steer`, or stop it with `interrupt`.
- Follow up only after the prior turn is terminal: `codex-worker run --name implement-a31 --prompt "Run the focused gate and report."`
- Stop non-destructively with `codex-worker daemon stop`; after restart/timeout, first inspect status/messages, then wait via the harness’s named-worker join mechanism or interrupt; only then use `run` for a new follow-up.

### Re-review 1 (BLOCK)

VERDICT: BLOCK

FINDINGS:

- [Important] Both operational blockers are closed: five backgrounded starts use distinct worktrees and correlation by name, and recovery explicitly requires observation plus a terminal prior turn before `run`. Cite: `skills/subagent-driven-development/codex-worker.md:54-67`, `:89-95`.
- [Important] The checkpoint labels a shortened restatement as the “Original verdict (BLOCK, verbatim),” but it is not the prior verbatim review response and omits its `WORKFLOW YOU WOULD USE` section. This misstates the audit record, though it does preserve the BLOCK outcome and has a clear pending re-review slot. Cite: `docs/superdev/reviews/2026-08-19-codex-worker-command-doc-checkpoint.md:31-38`.

WORKFLOW YOU WOULD USE:

- Launch concurrently from assigned worktrees: `(cd "$IMPLEMENT_A_WORKTREE" && codex-worker start --name implement-a31 --prompt-file implement-a.md) &` (repeat with distinct names/worktrees).
- Inspect by name: `codex-worker status --name implement-a31`; then `messages` or `history`.
- On timeout/restart, observe the same turn; interrupt only to cancel; issue `codex-worker run --name implement-a31 --prompt "…"` only after terminal status/history.
- Stop non-destructively with `codex-worker daemon stop`; later `run` restarts/continues the stored worker.

### Re-review 2

Pending controller verdict.

## Reviewer B — model/access/native-Claude boundaries

VERDICT: PASS

FINDINGS:

- No Critical/Important findings. Targeted help checks confirm documented `start`, `run`, named controls, raw recovery families, and flags.

BOUNDARY CHECK:

- Exactly two Codex tiers: medium→Terra; very-smart→Sol; medium effort default; no `CLAUDE_EFFORT` inheritance; live validation/no fallback.
- Full access is documented as creation default; `--read-only` is explicit.
- Codex is operator/plan opt-in; native Claude Code remains complete, equal/default-native SDD route.
- Instance precedence and advanced recovery are isolated in the technical appendix, avoiding harmful CLI-table duplication.
- Help checked: `bin/codex-worker --help`; `start --help`; `run --help`; `status/messages/history/steer/interrupt --help`; `daemon --help`; `goal --help`; `limits --help`; `model --help`; `session --help`; `turn --help`.
