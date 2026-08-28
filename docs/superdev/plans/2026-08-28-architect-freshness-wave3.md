# Architect ↔ Orchestrator Freshness — Implementation Plan (wave 3)

> **For agentic workers:** Execution: inline (doc-only wave; D46 — verification by fresh-eyes
> REVIEWS, never TDD baseline/GREEN cycles). Steps use `- [ ]`.

**Goal:** Transcribe D47–D65 into superdev skill text: the two-surface corpus, single-writer
spaces, checkpoint seam, mode law, brief anatomy, deviation flow, marker grammar + census
script, and the brainstorming angle-lifecycle teeth.

**Architecture:** Four tasks over ~11 skill files in one repo; every ruling exists in the log —
this wave is transcription, not design. Task 1 is the brainstorming emphasis (operator
priority); Task 2 the reconciled surface; Task 3 the operational surface; Task 4 wiring +
release. A conflict no D# settles → decision log (phase: build), then proceed.

**Mode:** human-in-loop · **Execution:** inline

**Context pack:**
- Spec: docs/superdev/specs/2026-08-28-architect-freshness-design.md (R1–R15, AH1–AH14)
- Log: docs/superdev/specs/2026-08-28-architect-freshness-decisions.md (D47–D65)
- Angles: …-architect-freshness-angle-0{1..4}-*.md · …-brainstorming-flow-angle-0{1,2}-*.md
- Current skill files named per task below.

## Global Constraints
- D46: every edited file gets a fresh-eyes review; blockers folded before release. No TDD lanes.
- Vocabulary verbatim from the log: reconciled/operational surface (D60), reconcile commit
  (D52), claim marker / section status (D53), mode law + reserved forks (D59), five-part brief
  (D57), pointer relay (D61), rolling window (D62).
- Path law: corpus `docs/system-design/` (canon: map.md, visions/ · dated: milestones/<slug>/);
  operational `docs/orchestration/`; item lane `docs/superdev/{specs,plans,scenarios}/`;
  scratch `.superdev/sdd/`. NO `design/` root may survive anywhere in plugin text (R1 signal).
- One canonical mode-law statement lives in system-design SKILL.md; every other skill LINKS it.
- Marker vocabulary: LOCKED · FLEXIBLE · DEFERRED · BLIND · MISMATCH · SEED-ILLUSTRATIVE ·
  SUPERSEDED→link; forms: line-initial `**WORD:**` claim marker, `**Status:** WORD …` section line.

## The Through-Line
Task 1 lands the operator's priority — the brainstorming angle lifecycle (R15) and the doc-side
marker retirement (R6's template half) — first because its artifacts (companion timing, reviewer
inputs, marker status lines) are what Tasks 2–4 reference as exemplars. Task 2 rewrites the
reconciled surface's own skill (system-design) — load-bearing: its floor diagram, mode-law
statement, and census script are cited by every later file. Task 3 rewrites the operational
surface (orchestrator + its files) against Task 2's canonical text. Task 4 wires the remaining
skills to both, updates glossary + bootstrapping, and releases. Deviation → log (phase: build),
supersede never erase.

## Acceptance (anchored — do not restate)
Discharges AH1–AH7, AH9–AH14 (AH8 already receipted). Receipts filled into the spec's §9 at
the final gate. Unanswered hints are NAMED and pushed to the operator (Mode: human-in-loop).

### Task W3-1: brainstorming — angle lifecycle teeth + doc-side marker grammar
**Role:** R15/D65 (operator emphasis), R6 doc-half/D53. **Read first:** spec §5.4 R15 clause,
D65, D53; brainstorming-flow-angle-02 (the MISMATCH list is the edit map); current SKILL.md
steps 5/8/10/11, design-doc-template.md §5 status line, spec-document-reviewer-prompt.md,
item-angle-template.md.
**Files:** Modify `skills/brainstorming/SKILL.md`, `design-doc-template.md`,
`spec-document-reviewer-prompt.md`, `item-angle-template.md`.
- [ ] SKILL.md step 5: add the close-time clause — closing an angle that carried real
  collisions WRITES its companion then (movement step), step 8 keeps only the naming/template
  pointer (no batching); the DEPTH BAR travels with it (and into item-angle-template.md):
  a companion is a TEACHING document readable without the log — its body is a Concrete
  journey with one `### LOCKED — <claim>` subsection per ruling, each explained in prose
  with a worked example; a companion that only cites D#s is an index, not an angle
  (measured: bench angles avg ~2,750 words; cite-only companions ~380); step 10: reviewer dispatch lists angle companions as required inputs;
  step 11: the gate message hands the operator spec + companions as file:// links.
- [ ] spec-document-reviewer-prompt.md: add **Angles:** input line + a cross-check row
  (companions contradict neither spec nor log; every companion collision appears in spec areas
  or §8; template compliance); REPLACE its "carries a DOC-MARK status" clause with the
  positional `**Status:**` line grammar (D53).
- [ ] design-doc-template.md §5.x status line → `**Status:** LOCKED|FLEXIBLE|… (D#|owner) —
  …` positional form, DOC-MARK bracket text removed; item-angle-template.md status guide
  already plain — confirm, align anchor-precision note ("file:line, or §-level for
  same-directory companions").
- [ ] REVIEW (fresh subagent): follows the four files; verifies an agent obeying them writes
  companions at close, dispatches the reviewer with angles, hands files at the gate, and never
  writes a DOC-MARK bracket. Fold blockers. Commit.

### Task W3-2: system-design — the reconciled surface
**Role:** R1–R6, R9 canonical, R10 architect half. **Read first:** spec §5.1; D47–D53, D59,
D60; angles 01–02; current SKILL.md, map-and-markers.md, protocols.md, angle-guide.md (already
updated — touch only if a path/grammar line conflicts).
**Files:** Modify `skills/system-design/SKILL.md`, `map-and-markers.md`, `protocols.md`;
Create `skills/system-design/scripts/marker-census.sh` (+ small fixture corpus for its
self-test).
- [ ] SKILL.md: floor diagram → docs/system-design/ with canon/dated layers + milestones/
  folder (D47/D48, incl. the INDEX D#-range line and the census.md survives / recurring census
  ephemeral sentence); single-writer law + git-log audit line (D49); residue paragraph →
  report-based, typed rows named (D51); session protocol → mechanical open, sitting,
  reconciliation close with named commit (D52), response block (D60); THE canonical mode-law
  section (D59: HUMAN/AUTONOMOUS, reserved forks, flagged picks, close always human).
- [ ] map-and-markers.md: DOC-MARK bracket section replaced by claim-marker + section-status
  grammar with flexible payload examples and the census greps; MIG-MARK section unchanged.
- [ ] protocols.md: checkpoint worked example rewritten to the two-artifact shape (handover doc
  with trio+claims+clusters+facts; response block inside milestone decisions.md); row schemas
  → typed ledger rows (orchestrator-written); OPERATIONAL RECORD stamp text quoted once here.
- [ ] scripts/marker-census.sh: greps the positional grammar over a directory, prints counts
  per status per file + delta vs a given ref; self-test against the fixture corpus (incl. a
  prose line that must NOT match — A2's false-positive check). Run it; paste output into the
  task record (AH2 receipt candidate).
- [ ] REVIEW (fresh subagent): reads only the three files + script; must be able to draw the
  two-surface map unaided (AH1 probe) and walk a checkpoint end-to-end (AH9 probe). Fold. Commit.

### Task W3-3: orchestrator — the operational surface
**Role:** R3,R4,R7,R8,R10–R12. **Read first:** spec §5.2; D54–D62; angles 02–04; current
orchestrator SKILL.md, checkpoint-protocol.md, room-brief-template.md, durable-state.md,
chartering.md (link seam only).
**Files:** Modify all five.
- [ ] SKILL.md: system-design-layer section rewritten — spaces + typed ledgers from reports
  (D51), pointer-relay duty incl. the D61 plan-time deviation forward, mode declaration at
  co-plan linking the canonical law, design-checkpoint duties → handover doc + await response
  block, handoff split (orchestrator half docs/orchestration/handoffs/, architect half = next
  milestone folder birth — the two-section file text dies), close gate list + "N−1 operational
  sediment pruned" line with the keep-set (D62), NEW execution-proposal section (D55: two
  opposed seats, five rules, ratify at co-plan, derive charter via chartering.md).
- [ ] checkpoint-protocol.md: full rewrite — handover doc format at
  docs/orchestration/handovers/<milestone>-checkpoint-N.md (trio + map claims + clusters
  inline + inlined census/process facts), response-block expectations, reconcile-commit close;
  design/residue-collections/ path dies here.
- [ ] room-brief-template.md: the five-part ARCHITECTURE CONTEXT block (D57) with the worked
  example from the spec dialogue; plus the room-side deviation duty line (collect → plan-time
  pointer, D61).
- [ ] durable-state.md: ledgers under docs/orchestration/, OPERATIONAL RECORD stamp on every
  file's header spec; two seat-prompt sketches for the proposal (domain-boundaries seat,
  celebration seat) appended or as a short new section in SKILL.md — wherever reads cleaner.
- [ ] REVIEW (fresh subagent): AH3 probe (compose a brief from the template — all five parts
  present with real-looking reads), AH5 probe (two artifacts + commit, placed and stamped),
  AH11 probe (proposal round complete), AH12 probe (pruning line + keep-set). Fold. Commit.

### Task W3-4: cross-wiring, glossary, bootstrapping, release
**Role:** R9 links, R11 room side, R1 sweep, R13/R14. **Read first:** spec §5.3–§5.5; D59,
D61, D63-bridge rows; current self-brainstorming SKILL.md, writing-plans SKILL.md Mode text,
brainstorming step 1, SDD SKILL.md line ~23, cli-checkride SKILL.md §5b, using-git-worktrees,
finishing-a-development-branch, using-superdev, glossary.md, bootstrapping SKILL.md.
**Files:** Modify the ten named files + `.claude-plugin/{plugin,marketplace}.json`,
`RELEASE-NOTES.md`.
- [ ] Mode wiring: self-brainstorming ratification gate resolves by mode (orchestrator
  ratifies in AUTONOMOUS with flagged pick; desk DECIDE in HUMAN; reserved forks always
  operator) — links the canonical law; writing-plans Mode field text cites the same law.
- [ ] Room-side: brainstorming step 1 grounding paths → docs/system-design/… + deviation flow
  sentence (D61 replaces the residue-jsonl clause); SDD SKILL.md room paragraph → collect in
  item files, plan-time pointer, orchestrator relay (the quoted retired line dies);
  cli-checkride §5b distill path → docs/superdev/scenarios/ (and orchestrator SKILL.md's two
  reads — confirm done in W3-3).
- [ ] Sweep: `grep -rn "design/" skills/ | grep -v "system-design\|docs/system-design"` → every
  survivor is either fixed or justified in the task record (R1 signal); glossary gains the
  D-vocabulary (two surfaces, reconcile commit, claim marker/section status, mode law, execution
  proposal, handover/response block, pruning window, pointer relay) and retires stale entries;
  bootstrapping ruling table gains the bridge rows (canon≙visions, per-decision files, item-lane
  path override) and the floor step creates docs/system-design + docs/orchestration skeletons.
- [ ] Release: bump 7.9.0 → 8.0.0 (breaking: corpus paths + retired mechanisms) in both
  manifests; RELEASE-NOTES `## v8.0.0` summarizing D47–D65; final whole-wave REVIEW (fresh
  subagent, all edited files + spec): AH1/AH4/AH6/AH13/AH14 probes + the grep sweep re-run.
  Fold. Fill §9 receipts for AH1–AH7, AH9–AH14. Commit.

## Self-review (done at write time)
Spec coverage R1–R15 ✓ (R1 sweep W3-4 · R2/R5 W3-2 · R3/R4 W3-2+3 · R6 W3-1+2 · R7 W3-3 ·
R8 W3-3 · R9 W3-2+4 · R10 W3-2+3 · R11 W3-3+4 · R12 W3-3 · R13 shipped · R14 W3-4 · R15
W3-1). No placeholders; file names verified against the repo this session (reviewer receipts:
SDD line ~23, checkpoint-protocol.md:10, cli-checkride:49).
