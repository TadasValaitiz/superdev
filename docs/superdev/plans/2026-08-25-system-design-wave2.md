# System-Design Layer — Wave 2 Implementation Plan

> Execution: inline, shape A agreed (D39). Steps use `- [ ]`.

**Goal:** Land the D10/D16-governed engine-room edits: how work executes inside an item room now that workers are long-running and resumable.

**Architecture:** Three broad tasks over four skills in one repo; every ruling already exists (D27/D28/D32/D36–D38) — this wave is transcription into skill text under baseline→edit→GREEN discipline, then one release.

**Mode:** human-in-loop · **Context pack:** anchor spec (R22, R26, R28, §5.5, §5.9 wave-2 lines) · decision log D27, D28, D31–D39 · wave-1 plan (folded reviewer findings) · current `skills/subagent-driven-development/` (SKILL.md, implementer-prompt.md, task-reviewer-prompt.md, parallel-execution.md, codex-worker.md, codex-model-selection.md), `skills/test-driven-development/`, `skills/writing-plans/SKILL.md`, `skills/brainstorming/SKILL.md`.

## Global Constraints
Wave-1 constraints hold (glossary linkage, SDO descriptions, baseline-before-edit per AH10). New-vocabulary lines verbatim from the log: D36 (long arcs; Codex = long-run + **resume-first**), D37 (one deep initial write; parallel = reads + quick-fix phases in the same worktree; never broad implementation), D38 (implementer inner red-green; reviewer = test adversary, watched-to-fail per checkpoint; harvest-authored requirement tests; archive sweep = first checkpoint, reviewer signs harvest pre-deletion; cleanup at close gate), D32 (RESUME metadata block + registry in `.superdev/sdd/`; resume-first fixes; long review cadence), D27/D28 (execution-shape variants always; brainstorm sets disposition {keep · regenerate · archive-then-rewrite · fix-in-place}, plan refines mechanics only).

## The Through-Line
Task 1 rewrites SDD — the engine — and is load-bearing: its vocabulary (carrying implementer, plan-checkpoint review, RESUME block, quick-fix lanes) is what Tasks 2–3 reference. Task 2 gives TDD the two seams SDD now assumes: clearance mechanics and the adversary role. Task 3 adds the two elicitation surfaces upstream (plan shape variants; brainstorm disposition). Release last. A conflict with existing skill text that no D# settles → decision log, phase build.

## Acceptance
Discharges the wave-2 halves: AH9 (SDD rename completes the sweep), AH17 (execution-shape variants + archive lifecycle in skill text; live receipt at rollout), AH19 (resume/cadence skill text; live receipt at rollout). Unmet live halves stay named for rollout.

### Task W2-1: `subagent-driven-development` — the engine rewrite
**Role:** R28, D32, D36–D38; load-bearing vocabulary.
**Read first:** anchor §5.5, §5.9 wave-2; D32/D36/D37/D38 entries; all six current SDD files.
**Files:** Modify `SKILL.md`, `implementer-prompt.md`, `task-reviewer-prompt.md`, `parallel-execution.md`, `codex-worker.md` (framing lines only).
- [ ] Baseline (one subagent, current text): "how big is a task; who reviews and when; a reviewer found issues — same or new agent fixes, and how; can two implementers write in parallel; when do you pick Codex?"
- [ ] Edit — SKILL.md: broad **role-carried arcs** as the default task shape (bite-size only for Sonnet-class mechanical work); **one carrying implementer per arc, never parallel initial writes** (D37); reviews at **plan checkpoints** (diff-since-last + report), never per-mini-task (D32); **resume-first fixes** (SendMessage / `codex-worker run --name`; fresh dispatch + report only when resume fails); mandatory **RESUME metadata block** in every report + registry `.superdev/sdd/resume-registry.md`; Codex presented as the long-run powerhouse whose idiom is resuming one session (D36) — delete "opt-in only" framing, keep "not the default"; quick-fix parallel lanes in the same worktree for post-shape detail work only. implementer-prompt: RESUME block in the report contract; arc phases (implement → self-review → checkpoint receipt) replace 2–5-min steps for broad arcs. task-reviewer-prompt: the **adversary duty** (write/commission failing tests per checkpoint; observe each guard fail; in rewrite territory author from the harvest file). parallel-execution.md: rename milestone→checkpoint vocabulary; re-scope lanes to reads + quick-fix phase per D37; remove the wave-2 DOC-MARK from writing-plans.
- [ ] GREEN (same five questions) + grep: `grep -rn "milestone" skills/subagent-driven-development/` → 0 work-unit senses. Commit.

### Task W2-2: `test-driven-development` — clearance + adversary seams
**Role:** R20, D16, D38.
**Read first:** current `skills/test-driven-development/SKILL.md` (+ testing-lanes.md headers); D38.
**Files:** Modify `SKILL.md`; create `test-clearance.md`.
- [ ] Baseline: "domain models are being REPLACEd; 300 fixture-coupled tests fail; what does the skill tell you to do?" (expect: fix-forward/TDD-everything; no archive path).
- [ ] Edit — SKILL.md: a short "Domain shifts" section linking `test-clearance.md`: the iron law governs NEW code; in REPLACE/RESHAPE territory the disposition (set at brainstorm) governs the OLD tests. test-clearance.md: the four dispositions; archive mechanics (sweep = the arc's first plan checkpoint → `tests/_archived/<plan>/` + manifest + **harvest file** written before archiving, reviewer signs before deletion; recall path during development; close-gate cleanup deletes tests, keeps manifest); the reviewer-adversary seam (requirement tests authored from the harvest against the vision); inert-guard rule (a guard nobody watched fail is not a guard — the reviewer observes each fail at the checkpoint).
- [ ] GREEN (same scenario → archive-then-rewrite path with named artifacts). Commit.

### Task W2-3: upstream elicitation + release
**Role:** R26 halves, D27/D28.
**Read first:** writing-plans SKILL.md header block; brainstorming SKILL.md checklist; D27/D28.
**Files:** Modify `skills/writing-plans/SKILL.md`, `skills/brainstorming/SKILL.md`, `.claude-plugin/{plugin,marketplace}.json`, `RELEASE-NOTES.md`.
- [ ] Baseline: "does the plan ask the operator anything about execution shape or what happens to tests?" / "is test disposition part of the brainstorm checklist?"
- [ ] Edit — writing-plans: the **execution-shape proposal** replaces the silent `Execution:` decision — always propose 2–3 variants (task/deliverable counts, worker class, subagents/rooms, recommendation; one-variant form for small plans); an **Operational strategy** section that *refines* the brainstorm's disposition into mechanics (never reverses); note the D27 arc (HIL now → extract a protocol after ~3 consistent choices → auto-resolve). brainstorming: checklist gains the mandatory test-disposition question ({keep · regenerate · archive-then-rewrite · fix-in-place}, per touched area) with its output recorded in the spec.
- [ ] GREEN (same questions) · full-sweep greps (AH9 completes: no work-unit "milestone" outside orchestrator altitude, no retired terms) · bump 7.4.0 → 7.5.0 both manifests · RELEASE-NOTES `## v7.5.0` · commit · `claude plugin update superdev@superdev-dev` · receipts into anchor §9 (AH9 complete; AH17/AH19 skill-text halves) + build-closure log entry.

---
## Reviewer fold (binding errata — these override the task bullets above)

**W2-1:** `parallel-execution.md` is **rewritten from a new premise**, not renamed: dies — file-disjoint implementer lanes, isolated worktrees, shared-index/merge-audit laws, two-lane ceiling; survives — read-only parallelism, lanes-vs-rooms box, failure recovery; new — quick-fix lanes in the SAME worktree post-shape, reviewer test-writing named as D37's sanctioned small write. `codex-worker.md`: the two-implementer/two-worktree fan-out example (lines ~83–87) becomes one carrying implementer + one read-only reviewer, resume-first. `task-reviewer-prompt.md`: REWRITE the `## Tests` section and carve the read-only + don't-re-run clauses (reviewer MAY create test files and run them watched-to-fail; never mutates implementation); checkpoint-scoped placeholders (BASE = last checkpoint SHA; "task-scoped gate" → "checkpoint-scoped gate"). `implementer-prompt.md`: RESUME block + arc-phase report contract (the 2–5-min language lives in writing-plans → W2-3). SKILL.md sweep includes both dot graphs, Advantages/Cost/Red Flags (resolve the same-subagent-vs-fix-subagent contradiction as **continuation-first**), the **follow-up role**, **design-class deviations file residue** (in `## Decision Logging`), and **auto-enter on the writing-plans handoff** (D29 seam). GREEN greps add `per task|each task` and `isolated worktree|file-disjoint|merge audit`.
**W2-2:** harvest sign-off is **before anything is archived** (first plan checkpoint), everywhere; D38's implementer/reviewer split + inert-guard rule also lands in SKILL.md's `### Verify RED` (applies to every arc, not just REPLACE territory).
**W2-3:** owns the DOC-MARK removal; the bite-size doctrine (line 10 + `## Bite-Sized Task Granularity`) becomes the granularity dial; `## Execution Handoff`'s "do not ask which approach" is replaced by the proposal step + **auto-start on shape agreement** (D29); line ~221's checkpoint-lanes sentence re-scoped per D37; `Execution:` enum becomes `subagent-driven | inline` (mode `subagent-driven-parallel` retired — D40); `design-doc-template.md` gains the test-disposition section (R20's evidence); `glossary.md` gains disposition set · harvest file · arc · carrying implementer · quick-fix lane; brainstorming checklist insertion stated explicitly (fix the duplicate numbering while there).
**Acceptance adds:** AH8 (skill-text half) and AH10.
**Registry:** no separate file — RESUME metadata is tracked in the progress ledger (D32 upheld; D40).
**Order note:** W2-1's harvest-file reference is a stable forward reference defined by W2-2 (strict 1→2→3).
