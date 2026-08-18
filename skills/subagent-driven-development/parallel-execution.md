# Parallel Execution Mode — multi-milestone plans only

Activated ONLY when the plan header says `Execution: subagent-driven-parallel`
(chosen at plan time: multiple milestones AND long enough that sequential wall-clock
hurts). Sequential SDD remains the default for everything else — parallelism is paid
for in controller attention, and on small plans the overhead exceeds the win.

Origin: generalized from a production program's battle-tested protocol (~30 subagent
dispatches, 3 API-death recoveries with zero work lost, ~12 confirmed review findings
all caught pre-publish — measured in that program). Every law below was learned from a
real failure, kept here with its scar.

## 1. The controller model

ONE controller session orchestrates; it never implements beyond trivial inline fixes.
Model pins per SKILL.md Model Selection — an explicit `model` on EVERY dispatch (an
unpinned launch inheriting the controller's model is itself a violation).

Context flows as FILES, never pasted history: every task gets a **brief file**
(mission narrative + ordered reading list with §-anchors, never bare line numbers +
build spec + gates + CRITICAL QUESTIONS + report contract) and returns a **report
file**; the chat return is status + commits + one line + concerns. The controller
cross-checks every report's critical-question answers against the tree before
accepting — trust nothing, re-run the cheap gates personally.

## 2. The parallel lanes (what runs concurrently)

- **File-disjoint implementer lanes → isolated worktrees.** Disjointness is PROVEN
  from the tasks' `Files:` blocks (empty intersection), never assumed. Each brief
  carries a strict file-ownership list. The agent's step 0 is ALWAYS branching from
  the PROGRAM branch tip (an isolation worktree may base on main, which lacks the
  program's docs — verify the base). The controller merges each lane back:
  **merge audit + combined-tree fast gate**, never a blind accept.
- **Same-file tasks stay sequential** — or better, BATCH them into one dispatch (one
  coherent deliverable, commits per sub-scope) instead of paying two context-loads.
- **Reviews run concurrent with implementation**, in worktrees PINNED at the reviewed
  SHA — never against a tree still being mutated. Findings fold before the milestone
  gate. Findings files are copied out of reviewer worktrees IMMEDIATELY (they
  auto-clean; a lost findings file is lost evidence).
- **Cross-milestone pipelining:** milestone N+1's read-only grounding inventory runs
  DURING milestone N's execution; the controller writes N+1's plan from the banked
  inventory during N's tail. Read-only agents (no edits, no commits, no test runs
  that mutate state) are always safe to parallel.
- **Delegated design exploration** (self-brainstorming runs, write-only to spec
  files, never committing, assumptions queued for the human) parallels execution the
  same way.

## Integration models — lanes vs rooms (do not mix them up)

This file's lanes are HEADLESS workers: the CONTROLLER merges each lane back
(merge audit + combined gate) because a headless lane cannot be trusted to self-publish.
ENTERABLE ROOMS (the orchestrator skill) are the opposite: full peer sessions that ran the
whole discipline including the checkride, so they SELF-PUBLISH via FF-CAS to the milestone
branch and the orchestrator never merges. Same repo, two models — pick by what the worker
is, never blend (a controller merging room work recreates the bottleneck; a lane
self-publishing skips the merge audit).

## 3. The serial set (never parallelize)

Merges/publishes (one at a time). Milestone gates (a FROZEN tree — nothing mutates
during the gate). Genuine dependencies (a task consuming another's Produces).
Human checkpoints. The review-fix cycle for confirmed findings — fixes land before
the next dependent wiring.

## 4. Controller disciplines (each learned the hard way)

- **Shared-index law:** while ANY implementer holds a worktree, the controller makes
  NO commits there — a controller commit can capture the implementer's staged files.
  File edits are fine; commits happen at landing boundaries. Uncommitted briefs
  reach isolated agents by ABSOLUTE path.
- **Merge-audit law:** never trust a clean auto-merge. Two agents adding to one file
  can produce silently-wrong results a green suite won't catch (measured case: a
  duplicate JSON key — parse last-wins, guard still green, dead text in the tree).
  Eyeball every file both lanes touched; re-gate the combined tree.
- **Gate economics:** per task = the FAST suite + the task's OWN tests targeted —
  **regardless of which lane they classify into** (measured trap: a project's AST
  guards lived in the slow tier, so three green fast gates missed a real defect) —
  plus any targeted structural guards. Milestone and finishing gates run the fast
  suite + area-selected slow tests as separate killable commands (never the whole
  slow tier as one invocation — testing-lanes.md); the scheduled sweep is the
  whole-suite backstop.
- **Wave rhythm:** verify (controller's own re-run) → merge → combined gate → commit
  orchestration state → dispatch the ENTIRE next wave in one message (implementers +
  reviewers together).
- **The ledger is the recovery map:** every dispatch, acceptance, adjudication, and
  protocol amendment goes into the progress ledger AS IT HAPPENS, committed at
  boundaries (the existing `.superdev/sdd/progress.md` discipline, at wave
  granularity). Session memory then only needs a pointer.
- **Docs regenerate in the same commit** as any surface they describe — line-anchor
  drift otherwise breaks the next agent's grounding.

## 5. Failure recovery (agent deaths, stalls)

- On an agent death: **inspect the worktree FIRST** (`git status`/`git log` — what
  committed, what survives uncommitted), then **resume the same agent** with a
  message stating the verified salvage state. Never blind re-dispatch — it
  double-writes.
- Under instability, every dispatch carries: **wip-commit early and often** (a drop
  costs minutes, not work).
- Process checks match exact names (`pgrep -x`), never loose patterns that catch
  bystanders.
- Fallback when resumes keep dying: the controller finishes the remnant inline.

## 6. When NOT to parallelize

Tiny tasks (dispatch overhead exceeds the win). Anything sharing mutable state you
cannot PROVE disjoint from the Files: blocks. A fix cycle whose output the next task
consumes. Reviews of a mutating tree (pin a SHA instead). And never past
comprehension: **the controller must be able to audit every merge — two concurrent
lanes is the comfortable ceiling, three only when one is read-only.** More lanes than
you can audit is not speed; it is deferred debugging.

## 7. Gates in this mode

Per-task commit gates: fast suite + own tests (§4 gate economics). **Milestone
gates: on a frozen tree, findings folded first — fast suite + the slow tests
covering that milestone's area, each its own killable command** (never the whole
slow tier as one invocation — testing-lanes.md). The terminal finishing gate (same
fast + area-slow shape + deviation/acceptance audit + human merge decision) runs at
the end. Whole-suite truth comes from the scheduled sweep on main, off the gate path.
