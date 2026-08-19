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

**Original verdict (BLOCK, verbatim):**

> (1) codex-worker.md fan-out commands must demonstrate each `start` executed from its assigned distinct worktree/cwd, not five commands from coordinator cwd; make harness-owned concurrency and JSON correlation clear. (2) timeout/restart recovery must explicitly show the named observation/wait sequence and say `run` is allowed only after prior turn is terminal; avoid implying restart means old active work can be overlapped. Use exact supported CLI—inspect help if needed.

**Re-review:** Pending controller verdict after the correction. The reference now uses
five backgrounded `(cd "$WORKTREE" && codex-worker start …) &` commands, correlates by
`result.worker.name`, and requires `status` then `messages`/`history` before `run` once
the preceding turn is terminal.

## Reviewer B — model/access/native-Claude boundaries

**Verdict (verbatim):** Reviewer B PASSed all model/access/native-Claude/help boundaries.
