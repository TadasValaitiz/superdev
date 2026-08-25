# System-Design Layer — Wave 1 Implementation Plan

> **For agentic workers:** Execution field below is `inline` by design (see the Execution-shape proposal — the operator agrees a variant before anything starts, per the anchor's own D29). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Land the `system-design` skill and the wave-1 skill edits in superdev and room-graph-orchestration, so the corpus/checkpoint/marker machinery exists before the R22 deep-dive unlocks wave 2.

**Architecture:** One new skill carries everything the others cite (corpus, glossary, markers, protocols, angle guide); seven existing skills gain thin, pointed edits that reference it rather than restate it; every edit follows writing-skills discipline (baseline failure observed → edit → compliance verified). Two repos, both directory-live.

**Tech Stack:** Markdown skills · bash/grep census snippets · subagent baseline/compliance runs. No production code, no test lanes.

**Execution:** inline (operator agrees shape first — see proposal below)
**Mode:** human-in-loop

**Execution shape: variant A agreed (D35, 2026-08-25).** The proposal below is the historical record; do not re-ask.
- **A (recommended): 5 broad role-carried tasks, inline in the authoring session.** The constraint is context: 34 decisions, 3 review rounds and the operator's angle template live in the author's head; a fresh implementer per skill would re-derive them from files at every hop. Reviewer subagents (opus) at the two milestone gates; baseline/compliance subagents per edit. ~2 deliverables (skill + edit set), 6–8 verification subagents total.
- **B: subagent-driven, 9 bite-size tasks.** Fresh implementer per skill file + per-task review. Costs: every implementer re-grounds on a 30-decision spec; per-mini-task reviews are exactly what D32 retired.
- **C: separate session/room** with this plan as charter. Right if the operator wants this out of the current session; loses the live context for no isolation benefit (both repos are the operator's own plugins).

**Context pack:**
- Spec: `docs/superdev/specs/2026-08-24-system-design-layer-design.md` (R1–R28, §5.1–5.10) · Decision log: `…-decisions.md` (D1–D34 + addendum)
- Angle companions: `…-angle-01-item-journey.md`, `…-angle-02-authority-ledger-algebra.md`, `…-angle-03-operator-attention.md`
- Operator's angle theory (import source): `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.claude/worktrees/bench-architecture/docs/superpowers/specs/2026-08-25-bench-angle-definition-and-template.md` and `…/2026-08-20-bench-architecture-angles.md` (status language, INDEX shape)
- Map precedent: `…/2026-08-20-bench-angle-08-current-to-target-map.md` (KEEP/RESHAPE/REPLACE/DEFER prose)
- Prior packaging precedent: `~/Projects/hedge-graph` (marker census scripts style), `~/Projects/room-graph-orchestration/skills/graph-creator/packaging.md`

## Global Constraints

- Glossary terms exactly as spec §5.8: milestone · item · plan checkpoint / design checkpoint · bridge · handoff · residue ≠ residual · system angle ≠ item angle · marker · vision · corpus · backlog. Retired as work-unit names: phase, stage, joint, runway, docket.
- Marker grammars verbatim: `MIG-MARK[RESHAPE|REPLACE|SEAM|TEST][D#]: note` · `DOC-MARK[LOCKED|FLEXIBLE|DEFERRED|BLIND|MISMATCH|SEED-ILLUSTRATIVE][ref]`.
- Corpus floor exactly as spec §5.1 (incl. `residue/`, `residue-collections/`, `conformance/`, `handoffs/`, `marker-census.md`).
- Every edited skill LINKS the glossary in `system-design`; none restates it (spec 5.8 Interface).
- Skill descriptions: "Use when …" triggering conditions only, never workflow summaries (writing-skills SDO).
- Every edit task: baseline observed BEFORE the edit, compliance after (AH10); one writing-skills cycle per task, inside the task.
- Version bumps: superdev `plugin.json` minor bump once at the end; room-graph `plugin.json` + `marketplace.json` agree; both repos committed, room-graph pushed.

**Test lanes:** none (text-first; per-task verification = subagent baseline/compliance runs; the grep sweeps below are the fast checks).
**Engineering patterns:** none declared/detected.

## The Through-Line

Everything cites the new skill, so it goes first and is the only load-bearing task: **Task 1** writes `skills/system-design/` — the corpus layout, the glossary, both marker grammars with their census greps, the angle guide (the operator's own template, generalised), the session protocol with worked examples (D18 demanded examples), and the checkpoint-handover/response/handoff formats from spec §5.4/5.10. Its Produces block — file names and section anchors — is the interface every later task's edit points at. **Task 2** rewrites superdev's `orchestrator` around the milestone law; it consumes Task 1's anchors for everything conceptual and adds only what the orchestrator *does* (checkpoint declaration, handover, pause, green lights, process feedback, ad-hoc rooms, close gate). **Task 3** carries the two learning-loop edits: `self-improvement` inbox mode and `brainstorming`'s R25 flow. **Task 4** is the small-edit sweep (writing-plans checkpoint rename + Read-first, using-git-worktrees retirement, finishing-a-development-branch alignment, using-superdev pointer). **Task 5** crosses repos: graph-creator's development-organisation template with architect/desk brief variants, room-communication's green-light + residue conventions — then both repos bump, commit, and the receipts land in spec §9. Order is strict 1→2→(3,4 in either order)→5. If an edit fights a skill's existing text in a way the spec didn't foresee, that's a §10 drift: log it (phase: build), don't improvise.

**When reality diverges from a task:** re-read this section, check the governing D#'s revisit-when (the log's addendum), append the fork to the decision log, update downstream Consumes/Produces before continuing.

## Acceptance (anchored)

This plan discharges: **AH1, AH9, AH16 (simulated), AH10** (per D34). All organisation-level hints (AH2–AH8, AH11–AH15, AH17–AH19) are rollout receipts in the calibration project — named, not dropped; Mode is human-in-loop so any wave-1 shortfall goes to the operator before finishing.

---

## Checkpoint C1: the skill exists and self-checks

When this passes: a fresh project can run `/superdev:system-design` solo and get the canonical corpus; every later edit has stable anchors to cite.

### Task 1: The `system-design` skill

**Role in the build:** The load-bearing artifact — R1, R9, R14–R16, D12, D14, D17, D23; everything in Tasks 2–5 cites its anchors.
**Read first:** spec §5.1, §5.2, §5.8, §5.10; the operator's angle template doc (full); angle-08's opening; log D12, D14, D17, D23, D26.
**Files:** Create `skills/system-design/SKILL.md`, `angle-guide.md`, `map-and-markers.md`, `protocols.md`, `glossary.md`.
**Interfaces — Produces (cited by all later tasks):** section anchors `glossary.md` (one table, all §5.8 terms + both ≠-pairs) · `map-and-markers.md#map-row-grammar`, `#mig-mark`, `#doc-mark`, `#census` (grep one-liners) · `angle-guide.md#five-kinds`, `#angle-contract`, `#anti-loosening`, `#item-angles` · `protocols.md#checkpoint-handover`, `#checkpoint-response`, `#milestone-handoff`, `#session-protocol` (with one full worked example each, drawn from the checkpoint-3 example already in this work stream's dialogue) · `SKILL.md` frontmatter description triggering on: system design, architecture session, migration map, angles, vision docs, corpus.

- [ ] **Step 1 — Baseline (writing-skills RED):** dispatch one subagent: "A project has `design/` with angles and a map. Run a system-design session for a new domain shift." WITHOUT the skill — record what structure it invents (expected: ad-hoc doc, no statuses, no map grammar).
- [ ] **Step 2 — Write the five files.** SKILL.md: invocation modes (solo = this session is the architect role; room = brief points here and adds D18's idle/human-driven law), corpus floor tree (§5.1 verbatim incl. the vision default rule), the two altitudes note (system vs item angles), session protocol pointer, DOC-MARK-driven agenda opening (`grep -rn "DOC-MARK\[BLIND\]\|DOC-MARK\[MISMATCH\]" design/`), angle sweep as the mandatory last act. Keep SKILL.md ≤ ~150 lines; weight lives in the reference files.
- [ ] **Step 3 — Compliance (GREEN):** same scenario WITH the skill (point the subagent at the dev repo path): it must produce the canonical tree, statuses, and a session agenda from the greps. Fix gaps; note rationalizations.
- [ ] **Step 4 — AH1 receipt:** scaffold-free solo run in `$(mktemp -d)`: corpus created, one angle, map, D# log; second run grounds on it (subagent transcript saved to `docs/superdev/reviews/`).
- [ ] **Step 5 — Commit** `feat(system-design): the corpus skill — glossary, markers, angles, protocols`.

## Checkpoint C2: superdev speaks the law

When this passes: superdev's orchestrator, learning loop and small skills all cite the new anchors; grep sweeps pass.

### Task 2: `orchestrator` — the milestone law

**Role:** R4–R6, R10–R12, R17–R19, R24, D8, D9, D11, D18–D22, D24, D25 — the biggest single edit; §5.4 made operational.
**Read first:** spec §5.4 (all), §5.7, §5.10 table; log D19–D22, D25, D30; current `skills/orchestrator/SKILL.md` + `room-mechanics.md` in full (respect its FF-CAS/close machinery — extend, don't rewrite).
**Files:** Modify `skills/orchestrator/SKILL.md`; create `skills/orchestrator/checkpoint-protocol.md` (the handover/response duty from the orchestrator's side, citing `system-design/protocols.md` for formats).
- [ ] Baseline: subagent plays orchestrator given a finished item + residue rows — observe: no checkpoint concept, no green lights, no design-dry behaviour.
- [ ] Edit: milestone boundary + bias-to-contain · checkpoint declaration (rule+green lights+feel) · handover/response duty · **two-step map-row discharge** (orchestrator *claims* rows in the handover; only the architect *writes* `map.md` — the §5.10 single-writer guarantee) · design-dry pause (charters only; D30 ratification-wait exception; scoped vs full per D21) · residue collection + process-feedback capture + brief adaptation (D25, never self-editing skills) · ad-hoc rooms · probe gate (item charters only) · close gate (worktree check + archived-tests check — noting the archive artifact itself is wave-2; the gate text names it now so wave 2 slots in) · desk feeding incl. execution-started events · green-light weighting note (A3).
- [ ] Compliance: same scenario — the subagent declares/refuses a checkpoint correctly and names the handover doc. Commit.

### Task 3: The learning loop — `self-improvement` inbox mode + `brainstorming` R25

**Role:** R24 (slow loop), R25, D25–D26, D28.
**Read first:** spec R24/R25 rows; §5.9 wave-1 lines; log D25, D26, D28; current `skills/self-improvement/SKILL.md` (its per-failure method stays untouched); current `skills/brainstorming/SKILL.md` process section.
**Files:** Modify `skills/self-improvement/SKILL.md` (new "Inbox mode" section: accept `orchestration/process-feedback.jsonl`, cluster by skill/boundary, then run the existing per-failure loop per cluster; operator gate unchanged). Brainstorming — four files, six changes as a checklist the compliance run scores one by one:
  1. `skills/brainstorming/SKILL.md`: corpus-awareness step (quote governing passages **with file:line**) between grounding and questions;
  2. same file: problem-space evaluation + 3–5 candidate angles, then angle-by-angle dialogue with lettered forks and emergent-angle triggers;
  3. same file: capture step adds item angle companions beside the spec + vision demand; scope line "system-scale design → use system-design"; glossary link;
  4. `skills/brainstorming/design-doc-template.md`: §5 area block gains a DOC-MARK status line;
  5. `skills/brainstorming/spec-document-reviewer-prompt.md`: reviewer checks collisions reconciled + statuses present + item angles cite system lines;
  6. Create `skills/brainstorming/item-angle-template.md` (the operator's angle contract, item-scoped: central question · boundaries · concrete consequences · collisions · reconciled outcome · status guide).
- [ ] Baselines (two subagents, one per skill, current text) → edits → compliance runs (brainstorm scenario must produce ≥1 item angle citing a system line = **AH16 simulated receipt**). Commit per skill.

### Task 4: Small-edit sweep

**Role:** R7, R16, D7, D15 — the rename and the lifecycle halves.
**Read first:** spec §5.8; log D7, D15; each target's current text around the quoted lines.
**Files:** Modify `skills/writing-plans/SKILL.md` — the **whole** Milestones passage (`## Milestones (optional…)` heading, `## Milestone M1` template, `**Milestone gate:**`, and the closing "Milestones are the unit of parallel execution…" paragraph) becomes plan-checkpoint vocabulary (`## Checkpoint C1`, checkpoint gate, "a checkpoint whose narrative line you cannot write is two checkpoints"), with a `DOC-MARK[DEFERRED][wave-2]` comment noting `subagent-driven-development/parallel-execution.md` still speaks the old sense until wave 2; plus Read-first gains "map rows / visions when a corpus exists" and the never-notifies-the-architect note. `skills/using-git-worktrees/SKILL.md` (retirement half: the creator merges and removes; close = worktree gone). `skills/finishing-a-development-branch/SKILL.md` (close-gate alignment ONLY — the room, not the finisher, retires the worktree; the archive note is wave-2, dropped). `skills/using-superdev/SKILL.md` (glossary pointer, inserted after `## Skill Priority`).
- [ ] **Baseline (one subagent, four scenarios — one per edited skill, pre-edit):** "what is a milestone inside a plan?" · "who removes a worktree at the end?" · "who cleans up when finishing a branch in a room?" · "where do I find the shared vocabulary?" — record all four answers.
- [ ] Edits (list above).
- [ ] **Compliance (same four scenarios, post-edit):** answers must give plan-checkpoint vocabulary, room-retires-worktree, close-gate alignment, glossary location.
- [ ] Greps that were RED before the edit (verified: today `writing-plans` has 14 milestone-as-plan-unit hits): `grep -rn "## Milestone M\|Milestone gate" skills/writing-plans/` → empty; parallel-execution's 10 hits remain and are DOC-MARKed deferred = **AH9 receipt (superdev minus SDD; SDD is wave 2)**.
- [ ] Run the existing guard: `bash tests/claude-code/test-worktree-path-policy.sh` → PASS (it asserts on the literal text of both worktree skills).
- [ ] Commit.

## Checkpoint C3: cross-repo + release

### Task 5: room-graph-orchestration edits + release both

**Role:** R23, D6, D24 — the template and the conventions; the release that makes it real.
**Read first:** spec §5.9 room-graph lines; log D24, D33; `room-graph-orchestration/skills/graph-creator/SKILL.md` (Step 5b + packaging.md pattern), `room-communication/protocol.md` events table.
**Files:** Modify `graph-creator/SKILL.md` (+ create `graph-creator/dev-organisation.md`: the named starting template — architect + desk brief variants pointing at superdev's `system-design`/`orchestrator` stack, the persistent/ephemeral roster, gate ladder by name); modify `room-communication/protocol.md` (green-light event row; residue-row convention + residue≠residual pair) and `SKILL.md` description if triggers change.
- [ ] **Baseline (one subagent, two scenarios, pre-edit):** graph-creator asked for a dev organisation (observe it invents one) · a room asked how to report a design-class finding vs a loose end (observe RES conflation — `room-communication/edge-obligations.md:79` defines RES as "a residual outside the sender's scope"; that is the exact line the residue≠residual pair lands beside; the OTHER `edge-obligations.md` under graph-creator/ is untouched).
- [ ] Edits — `dev-organisation.md` must carry the desk brief's **DESIGN column and execution-started event** (this file is the front desk's only wave-1 home).
- [ ] **Compliance (same two scenarios):** graph-creator reaches for the template; the room distinguishes residue from residual.
- [ ] Grep sweep both repos for retired-sense terms = **AH9 receipt (complete except SDD, deferred)**.
- [ ] Release: superdev `plugin.json` **and `.claude-plugin/marketplace.json`** 7.3.0 → 7.4.0; room-graph 2.2.0 → 2.3.0 (both files agree); **`README.md` per-skill list + `RELEASE-NOTES.md` `## v7.4.0` section gain `system-design`** (it must not ship invisible to the repo's own catalogues); commit both repos; push room-graph; `claude plugin update` both; `/reload-plugins` note for the operator.
- [ ] Receipts: fill AH1/AH9/AH10/AH16 rows in spec §9 with commands/transcript paths; name the rollout-owned hints in the finishing note. Commit `docs: wave-1 receipts`.
