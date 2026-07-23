---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `superdev:using-git-worktrees` skill at execution time.

**Save plans to:** `docs/superdev/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

A task is the smallest unit that carries its own test cycle and is worth a
fresh reviewer's gate. When drawing task boundaries: fold setup,
configuration, scaffolding, and documentation steps into the task whose
deliverable needs them; split only where a reviewer could meaningfully
reject one task while approving its neighbor. Each task ends with an
independently testable deliverable.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Execution:** subagent-driven | subagent-driven-parallel | inline — decided at plan
time per the Execution Handoff rule (inline ONLY when the plan is 1-2 tasks with no
interface handoffs AND no substantive design doc behind it; PARALLEL only for
multi-milestone long plans — see subagent-driven-development/parallel-execution.md)

**Mode:** autonomous | human-in-loop — carried from the anchor (design doc). Governs
how the finishing gate routes an unmet acceptance hint / anchor deviation: autonomous
files an owned backlog item and closes; human-in-loop pushes the divergence to the
operator before finishing.

**Context pack** — the artifacts downstream workers read; list every path that exists:
- Spec: [design doc] · Decision log: [companion -decisions.md]
- Domain model: [design doc §N, if the spec has one]
- CLI surface: [companion -cli-surface.md, if commands change]
- Prior art: [related specs/plans a worker might need]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section.]

**Test lanes** (REQUIRED line — copied from the project CLAUDE.md `Test lanes`
block, or detected per test-driven-development/testing-lanes.md):
fast: `<command>` · full: `<command>`. Every commit gate runs FAST; the full
suite runs ONLY at the finishing gate.

**Engineering patterns** (REQUIRED line — resolved via the engineering-patterns
skill's cascade: project CLAUDE.md declaration > stack detection > none):
`<path to governing doc>` (BINDING) — or "none declared/detected". Implementers
read it before coding; knowing departures are reportable deviations. Task
Read-first lines cite the specific sections a task lives in.

## The Through-Line

[The build story, in prose — not bullets, not a restated task list: how the
tasks compose into the goal, why the order is what it is, which tasks are
LOAD-BEARING (their Produces interfaces anchor everything downstream) and
which are flexible in implementation detail. A reader should understand the
whole build from this section before opening any task. If you cannot write
this section, the decomposition is wrong — fix the tasks, not the prose.]

**When reality diverges from a task** (an interface won't hold, a dependency
misbehaves, a step is impossible as written): don't patch locally and press on.
Re-read this section to see what the deviation threatens, check the governing
D#'s revisit-when hook in the spec, append the fork to the decision log
(phase: build), and update the DOWNSTREAM tasks' Consumes/Produces blocks
before continuing. A deviation whose through-line still holds is a re-plan;
one that breaks it goes back to the human.

## Acceptance (anchored — do not restate here)

[This plan's acceptance bar is the anchor's Use Cases (design doc §3) and Acceptance
hints (§9) — the operator-language "what must be demonstrable." Do NOT copy a Goals
table into the plan; that split acceptance across two files and let them drift. Instead:

- Name which UC#/AH# THIS plan discharges (a subset, if the anchor spans multiple plans).
- Each gate (milestone gate in parallel mode; the finishing gate always) answers its
  owned hints with RECEIPTS — one re-runnable piece of evidence per hint (test+output,
  CLI transcript, file:line), filled into the anchor's §9 receipt column when the real
  surface exists.
- An unanswered hint is NAMED, never dropped, and routed by the plan's `Mode`:
  autonomous → file an owned backlog item (naming the UC#/AH# it discharges) and close;
  human-in-loop → push to the operator before finishing.

This plan discharges: UC#…, AH#… ]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Role in the build:** [One sentence: what this task contributes to the
Through-Line and which spec R#/D# it implements. This line travels into the
implementer subagent's brief with the task text — it is the only big picture
that subagent gets, so make it carry weight. If a task has no honest Role
line, it doesn't belong in the plan.]

**Read first:** [The Context-pack sections THIS task's implementer must read
before coding — specific anchors, not whole documents: "spec §5.2", "domain
model N.3 delta ledger rows for OrderSpec", "CLI surface family 1 table".
Subagents have Read — point them at the truth instead of paraphrasing it.]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter
  and return types. A task's implementer sees only their own task; this
  block is how they learn the names and types neighboring tasks use.]

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Milestones (optional — long plans only)

When a plan is long enough to need them (roughly 8+ tasks or multiple distinct
deliverable phases), group tasks under milestone headers:

```markdown
## Milestone M1: <name — the deliverable this phase completes>

[One-line milestone narrative: what is TRUE about the system when this gate passes.]
**Milestone gate:** frozen tree · review findings folded · FULL suite green ·
**anchor acceptance hints owned by this milestone answered with receipts** (unanswered → named + routed by Mode).

### Task 1: ...
### Task 2: ...
```

Milestones are the unit of parallel execution (`Execution: subagent-driven-parallel`):
within a milestone, file-disjoint tasks may run as concurrent lanes; the milestone
gate is serial on a frozen tree. Single-milestone plans don't need the headers — the
finishing gate is their only gate. A milestone whose narrative line you cannot write
is two milestones (or none).

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

**4. Narrative & trace:** Does the Through-Line explain the task ordering and name the load-bearing tasks — or is it a bare task list wearing prose? Does every task's Role line trace to a spec R#/D#? Would an implementer hitting a wall mid-task know where to look (Through-Line → spec D# revisit-when → decision log)?

**5. Acceptance & context flow:** Does the plan name which anchor UC#/AH# it discharges, and does every must-R#/UC# in that subset have tasks that will produce a receipt? Does every task carry a Read-first line pointing at real Context-pack anchors — and does the Context pack list every artifact that exists (design/anchor, decision log, domain section, CLI surface)?

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Plan Review (REQUIRED — fresh eyes)

Your self-review above is inline. After it, dispatch the **plan reviewer subagent** per
`skills/writing-plans/plan-document-reviewer-prompt.md` — it reads the plan against the
anchor and checks narrative/trace, acceptance coverage (every discharged UC#/AH# has
tasks that produce a receipt), and buildability. You are the author; you are the worst
judge of your own plan's gaps. Fix blocking issues and re-dispatch once. (This is the
plan-level equivalent of brainstorming's required spec reviewer.)

## Decision Logging (planning forks)

Planning surfaces forks the spec didn't settle — a library choice, a sequencing
trade-off, an interface detail the design left open. Do not resolve these silently
inside a task description: append each one to the work stream's decision log (the
spec's companion `-decisions.md` file, next D#, `phase: plan`, per
`skills/brainstorming/decision-log-template.md`) with options, reasoning, and a
revisit-when hook. If a fork contradicts a spec D#, that is the spec's §10 drift
protocol — check the D#'s revisit-when trigger and amend the spec's decision status,
don't quietly plan around it. A plan whose choices are all traceable to the spec or
the log is re-plannable months later; one with silent choices is not.

## Execution Handoff

**Subagent-driven development is the DEFAULT — do not ask which approach.** After
saving the plan, announce and proceed:

**"Plan complete and saved to `docs/superdev/plans/<filename>.md`. Proceeding with subagent-driven development."**

- **REQUIRED SUB-SKILL:** Use superdev:subagent-driven-development
- Fresh subagent per task + two-stage review

**The inline exception** — use executing-plans instead ONLY when BOTH hold, judged at
plan time and recorded in the plan header's `Execution:` field:

1. The plan is super small: 1-2 tasks with no interface handoffs between them
2. There is no substance in the design document behind it (no design doc at all, or a
   few-sentence one with no numbered decisions)

Then: **REQUIRED SUB-SKILL:** Use superdev:executing-plans (inline, batch execution).

The operator overrides either direction with a word — an explicit request beats the
rule. A separate/parallel-session execution (the operator takes the plan to another
session) also uses executing-plans; that is session topology, not plan size, and it is
always the operator's call, never offered proactively.
