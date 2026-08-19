---
name: cli-checkride
description: Use as the validation gate for any branch/area that changed a user-facing surface (CLI or API) — an executor agent drives the real surface live, command by command, and an evaluator agent judges every input/output/mechanism from the operator's perspective; the work ITERATES until the evaluator passes the ride. Tests are the floor; the checkride is the gate. Not for trivial/no-surface changes (the finishing gate's receipt cross-check suffices there).
---

# CLI Checkride — driven live, judged from the operator's seat

A green suite has shipped 100× render bugs and structurally-unreachable gates. The checkride
is the *active* form of "the real surface is the final bar" (engineering-patterns §10): not
"is there a receipt?" but "drive it, watch it, judge it as the operator would."

## When

- **Any branch/area that changed a user-facing surface** (new/renamed commands, changed
  args/output, API routes) — in a room's DoD, or at an ordinary branch's finishing gate.
- **Not** for trivial/no-surface branches: the deviation auditor's receipt cross-check
  covers those. Scoping matters — an executor+evaluator ride on a one-line bugfix is the
  monolithic-full-suite mistake in a new costume.

## The two roles (separate agents, never one)

- **EXECUTOR** ([executor-prompt.md](executor-prompt.md)) — drives each touched command/route
  ONE AT A TIME against a real store/substrate: real invocations, args shown, FULL output
  shown, exit codes shown. Happy paths AND refusal paths. It demonstrates; it does not judge.
- **EVALUATOR** ([evaluator-prompt.md](evaluator-prompt.md)) — judges every input, output,
  and mechanism FROM THE OPERATOR'S PERSPECTIVE, armed with the operator-context pack (the
  project's notes/intuition/scenarios for this area). It files findings: output unreadable?
  provenance missing? a number unexplainable? friction in the frequent path? a gate guarding
  nothing? It judges; it does not fix.

Model policy: the evaluator is the `very smart` tier and the executor is the `medium`
tier. Native Claude Code resolves those tiers to `opus` and `sonnet`; an explicitly
selected Codex worker resolves them through
`../subagent-driven-development/codex-model-selection.md`. The executor needs
diligence, not brilliance.

## The loop

1. Executor runs the ride → transcript (every command · args · verbatim output · exit code).
2. Evaluator judges the transcript (+ re-drives specific commands on doubt) → verdict:
   **PASS** or findings (each: what · why it matters to the operator · severity).
3. Findings → the implementation ITERATES (fix subagents or the room's implementer) →
   re-ride the affected commands → re-judge. Repeat until PASS.
4. Findings that would change the *design* go back through the design doc (a D# amendment),
   never patched silently around it.
5. **Commit the final transcript + verdict** with the work (`…-checkride.md`) — the ride is
   evidence, and it must be reconstructable later.
6. When the human is present, they are the evaluator's final reader: the evaluator prepares
   the ride, the human stamps it.

The demonstration runs on the most realistic substrate available and STATES the honesty
tier of every number shown (a fixture demo proves mechanism, not edge — say so).

## Relationship to the finishing gate

At finishing-a-development-branch, the deviation auditor's acceptance cross-check (Part B)
delegates to a checkride **when the branch changed a user-facing surface**; otherwise its
lighter receipt check stands. In orchestrated rooms, the checkride is part of the room's DoD
and its verdict rides the R4 pre-publish report.
