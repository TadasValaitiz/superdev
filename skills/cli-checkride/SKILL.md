---
name: cli-checkride
description: Use as the validation gate for any branch/area that changed a user-facing surface (CLI or API) — an executor agent drives the real surface live ONE STEP AT A TIME on ACTUAL DATA while an evaluator agent sits in the operator's seat, ruling on each step before it runs and judging it after; missing real data STOPS the ride and asks the operator; the work ITERATES until the evaluator passes the ride. Tests are the floor; the checkride is the gate. Not for trivial/no-surface changes (the finishing gate's receipt cross-check suffices there).
---

# CLI Checkride — actual data, one step at a time, judged from the operator's seat

A green suite has shipped 100× render bugs and structurally-unreachable gates. The checkride
is the *active* form of "the real surface is the final bar" (engineering-patterns
`process-discipline.md` §2): not "is there a receipt?" but "drive it as the operator will,
watch it, judge it as the operator would."

**The scar this skill carries (2026-09-01/02).** An item's final ride PASSed with zero
findings on a stub data server, committed fixture inputs, and a two-day window — every
number honestly labelled SEED-TEST. The next day the operator's real journey (blank page,
real data service, six-month window) died four different ways before producing a single
result: a discovery step that needed source code, a silent forty-minute exit 137, a raw
traceback where a typed refusal belonged, a refusal naming the wrong remedy. Nothing in that
ride could have seen any of it. Two failures, both named by the operator: **no pre-planned
expectations** to judge against, and **riding whatever was at hand** (fixtures, stubs, tests
that mean nothing in the real world). Every rule below exists so neither can recur.

## When

- **Any branch/area that changed a user-facing surface** (new/renamed commands, changed
  args/output, API routes) — in a room's DoD, or at an ordinary branch's finishing gate.
- **Not** for trivial/no-surface branches: the deviation auditor's receipt cross-check
  covers those. Scoping is about *which surfaces changed*, never about *how much of the
  operator's journey to ride*: the ride starts where the operator starts and crosses every
  neighbouring surface the journey needs, changed or not — seams are where operators die.

## The substrate law — actual data, or stop and ask

<HARD-GATE>
A checkride step runs on ACTUAL DATA only: the project's real data path — real services,
real datasets, real inputs — at the scale the design's use cases name (the operator's
window, universe, volume). A disposable, freshly created STORE is fine; the DATA in it must
be real. Fixtures, mocks, stubs, seeded synthetic providers, recorded responses,
"fixture"/"dense"/test-only modes and flags: NEVER on a checkride step, however honestly
labelled.

If a step needs data or a service that is not available (service down, no coverage for the
window, an input that exists only as a fixture), the step is NOT RUN, the ride PAUSES, and
the OPERATOR is asked what to do — provision the real data · authorize a disclosed exception
for named steps · defer the step as a named gap. The operator's answer is recorded verbatim
in the ride ledger before anything else runs. Only the operator can authorize an exception;
an exception step's evidence is labelled EXCEPTION and can never be the only evidence for a
use case.

AUTONOMOUS mode: the room raises DECIDE to the orchestrator (the question in the operator's
words, what is missing, what it blocks) and the ride stays paused; the item cannot close on
that gate. Neither the room nor the orchestrator resolves it by picking a stand-in.
</HARD-GATE>

**Data preflight.** Before either seat is dispatched, the controller verifies that the real
data the checkride plan names actually exists (service reachable, coverage present for the
window and universe). A preflight failure is the same STOP — earlier and cheaper.

## Two artifacts exist before any command runs

1. **The checkride plan** — written at PLAN time by writing-plans
   ([checkride-plan.md](checkride-plan.md)): the operator's starting point, the journeys to
   ride at intent level, the command families each crosses (including neighbouring surfaces
   the plan does not change), the actual data each needs and how its availability is
   verified, the expectations the evaluator judges against, and what the plan deliberately
   does not ride. The plan reviewer judges it with the plan. A ride with no checkride plan
   has nothing to be judged against: write one (from the design's use cases) before the
   ride — never ride "what changed".
2. **The scenario intent doc** — written BEFORE the ride, from the checkride plan, the
   design's UC/AH rows, and the operator's own words:
   `docs/superdev/scenarios/<YYYY-MM-DD>-<item>-<slug>.md` — operator goal · the journey at
   intent level (never exact commands) · what-good-looks-like criteria · the actual data the
   journey needs · the operator's starting point. **No expected result number appears in it**
   (a prewritten number turns the ride into a confirmation exercise). Refreshed AFTER the
   ride with criteria born from findings; date-stamped, append-only. This is what the
   milestone-close battery re-drives.

## The two seats (separate agents, never one)

- **EXECUTOR** ([executor-prompt.md](executor-prompt.md)) — proposes each step in the
  operator's words, runs it exactly as approved against the actual-data substrate, and
  records invocation · full verbatim output · exit code. It demonstrates; it never judges,
  never fixes, never substitutes an input the operator would not have.
- **EVALUATOR** ([evaluator-prompt.md](evaluator-prompt.md)) — sits in the OPERATOR'S SEAT,
  armed with the operator-context pack (the project's operator laws / persona doc when one
  exists, the checkride plan, the scenario, the design's UC/AH rows): rules on every
  proposal before it runs, judges every output after, files findings as they occur. It
  judges; it never fixes.

Model policy: the evaluator is the `very smart` tier and the executor is the `medium` tier.
Native Claude Code resolves those to `opus` and `sonnet`; an explicitly selected Codex
worker resolves them through `../subagent-driven-development/codex-model-selection.md`.

## The loop — one step, one ruling, one judgment

The ride mimics an operator session: a command is proposed and explained before it runs,
the operator approves or redirects, it runs, the operator reads the output and decides what
to do next. **It is a dialogue, never a script.** Per step:

1. **PROPOSE** (executor): the next command in words the operator would use — what it does,
   why now, what it should show, what it writes, the honesty tier of any number it will
   print, which scenario row it serves.
2. **RULE** (evaluator, as the operator): **GO** · **AMEND** (the operator would not do it
   that way — a different command, flag, order, or a step the executor skipped) · **ASK**
   (the operator would not understand the proposal from the surface alone — that is itself a
   finding about the surface, filed now) · **STOP** (the substrate law fired, or a blocking
   finding makes further steps meaningless).
3. **RUN** (executor): the exact invocation, the FULL verbatim output, the exit code. Happy
   and refusal paths alike. If the executor would need anything the operator could not have
   — source code, a Python one-liner, a hidden flag, a test helper, a value only the tests
   know — it does NOT run; it records **OPERATOR-SURFACE GAP** as the step's result and the
   evaluator files it.
4. **JUDGE** (evaluator): the step verdict and its findings (what · why it matters to the
   operator · severity), answered through the operator's questions — readable? explainable
   (every number traceable to a run id / log / explain path)? honest (refusals name a
   RUNNABLE remedy; nothing overclaims)? is the obvious next command there? does each gate
   guard something real? — and **what the operator would do next**. That "next" is the
   input to the executor's next PROPOSE.

Mechanics that make the loop real:

- **Both seats stay alive for the whole ride.** Spawn each once; continue the SAME agent
  per step (native Claude Code: `Agent` once, then `SendMessage` to it; Codex:
  `spawn_agent`, then `send_input`). Never respawn per step — the accumulated context IS
  the operator's memory of the session. If the harness offers a Workflow tool, the loop may
  run as a workflow (the self-brainstorming precedent) with the same roles and ledger.
- **The controller relays and keeps the ledger.** Each step's four parts are appended, as
  they happen, to `docs/superdev/checkrides/<YYYY-MM-DD>-<item>-checkride.md` (header:
  substrate line · data preflight result · date · SHA · scenario path). The ledger IS the
  transcript; a step without all four parts is NOT RUN.
- **A blocking finding pauses the ride at that step.** The fix lane runs (fix subagents or
  the room's implementer); the ride RESUMES from that step on the new tree and re-drives the
  steps the fix touched — it does not restart from step 1, and it does not skip ahead. The
  final verdict covers the whole journey on the final tree.
- **Design-changing findings go back through the design doc** (a D# amendment), never
  patched silently around.
- **When the human is present, the human IS the operator seat**: the evaluator prepares each
  step's questions and files the findings; the human rules.

## Verdict, then the three closing duties

- **PASS** — the evaluator would hand this surface to the operator as-is, and every step ran
  on actual data. **PASS-WITH-EXCEPTIONS** — same, but one or more steps ran under an
  operator-authorized exception; each is listed with the operator's words, and the gate
  that reads the verdict decides with the operator. **FINDINGS** — blocking findings,
  ordered; the ride resumes from the earliest blocked step after the fix lane. **No PASS
  exists for a ride with no actual-data step**, and a ride paused on the substrate law has
  no verdict at all — it has a DECIDE.
- **Commit the ledger + verdict** with the work — the ride is evidence and must be
  reconstructable later.
- **Refresh the scenario intent doc** with criteria born from this ride's findings (a new
  dated file when the surface's intent changed; append-only).
- **File the observations:** every non-blocking, experience-class observation becomes a
  backlog item (or a residue row when design-class) directly from the evaluator's findings —
  never left living only inside the ledger.

## Red flags

| Thought | Reality |
|---------|---------|
| "A stub server is right there in the tests" | The stub proves a mechanism; the operator runs the real path. Use the real path, or STOP and ask. |
| "The fixture is labelled SEED-TEST, so it's honest" | Honest labelling of the wrong substrate is still the wrong substrate. |
| "A short window finishes fast" | The operator's window is the design's window. Ride at the operator's scale, or STOP and ask. |
| "I'll run every command first and judge at the end" | A script cannot ask "what would the operator do now?". One step, one ruling, one judgment. |
| "The plan's literal command block is the ride" | The checkride plan names journeys and expectations, never a script. Derive each step live. |
| "No checkride plan — I'll ride what changed" | Without expectations there is nothing to judge against. Write the plan and the scenario first. |
| "I'll compute that value with a one-liner" | If the operator could not get it from the surface, it is an OPERATOR-SURFACE GAP, not a step. |
| "The data isn't there; I'll seed something similar" | The substrate law: STOP and ask the operator. Only they can authorize an exception. |

## Relationship to the finishing gate

At finishing-a-development-branch, the deviation auditor's acceptance cross-check (Part B)
delegates to a checkride **when the branch changed a user-facing surface**; otherwise its
lighter receipt check stands — under the same substrate law (a receipt from a stand-in is
not a receipt). In orchestrated rooms, the checkride is part of the room's DoD, its verdict
class and substrate line ride the R4 pre-publish report, and a ride paused on missing data
is the room's DECIDE.
