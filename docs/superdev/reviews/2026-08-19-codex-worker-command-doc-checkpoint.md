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

**Pending controller semantic review.** Append the verbatim verdict here: can a Claude
coordinator launch, follow up, fan out, inspect/control, stop/restart, and recover
without source inspection?

## Reviewer B — model/access/native-Claude boundaries

**Pending controller semantic review.** Append the verbatim verdict here: do the docs
agree with help on tier/effort/access and preserve native Claude as the default route?
