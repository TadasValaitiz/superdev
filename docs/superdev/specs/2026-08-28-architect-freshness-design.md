# Architect ↔ Orchestrator Freshness — Design (anchor)

**Date:** 2026-08-28 · **Status:** draft
**Mode:** human-in-loop
**Decision log:** ./2026-08-28-architect-freshness-decisions.md (D47–D64; continues the system-design stream)
**Companions:** none (no CLI changes; no domain objects)
**Origin:** brainstorm with the operator (angle-first flow, its own first live run)
**Scope note (D64):** this spec governs SUPERDEV/ROOM-GRAPH SKILL TEXT ONLY. The calibration
migration (D63) is a separate stream in that project's own flow and is NOT discharged here.

## 1. Problem & intent   [ANCHOR]

The evidence base is the bench-architecture branch of ai-trading-calibration: ~40 files of
real milestone architecture (24 angles, 5 anchors, a D350–D494 log, census, execution
proposal) produced in one flat 199-file spec directory, kept honest only by hand-discipline:
reconciliation commits, continuation banners, an emergent plain-word marker grammar. It
worked — and it outgrew its container. Meanwhile superdev's corpus conventions (top-level
`design/`, shared residue jsonl, DOC-MARK bracket grammar, two-writer handoff file) described
a structure that live practice had already abandoned or invalidated (worktrees broke the
shared-file inbox; authors abandoned the bracket grammar 112:22).

Intent: rewrite the skill text so that (a) the architecture corpus has a home with an
enforceable freshness guarantee, (b) every write surface has exactly one writer, (c) the
orchestrator↔architect seam runs on two artifacts and pointer messages, (d) one mode law
governs every ruling gate, and (e) briefs carry architecture without paraphrase drift.
Success: a fresh orchestrator + architect + item room, running only on the shipped skill
text, reproduce the bench-quality corpus mechanics without any of the hand-invented parts.

## 2. Requirements   [ANCHOR]

| ID | Requirement | Source | Priority | Acceptance signal |
|----|-------------|--------|----------|-------------------|
| R1 | Corpus root is `docs/system-design/` with canon layer (map.md, visions/) and dated layer `milestones/<slug>/` (INDEX, decisions.md, angles/, anchors/, census.md, inputs/) | D47/D48 | must | system-design SKILL.md floor diagram matches; no `design/` root anywhere in plugin text |
| R2 | Milestone decision logs live in the milestone folder; D#s one global stream; INDEX declares the range | D48 | must | skill text states it; glossary entry |
| R3 | Single-writer spaces: system-design=architect, orchestration=orchestrator, superdev/=item rooms, scratch=.superdev/sdd; reads global; corrections are messages | D49 | must | every skill's write-surface text names only its own space |
| R4 | Shared residue inbox retired; rooms report, orchestrator comprehends+tracks typed rows (discrepancy/insight/duplicate-risk/question; friction/brief-gap/measurement/win) | D51 | must | no skill references residue.jsonl as room-writable |
| R5 | Reconciliation = mandatory closing half of every architect sitting, ending in one named reconcile commit; staleness between sittings allowed and marked | D52 | must | system-design session protocol text |
| R6 | Doc markers: plain positional grammar (line-initial `**LOCKED:**` claim markers; `**Status:**` section lines), flexible payload; DOC-MARK bracket retired for docs; MIG-MARK unchanged in code; census is a shipped script | D53 | must | map-and-markers.md rewritten; census script exists and runs |
| R7 | Execution proposal: orchestrator-authored via two opposed seats (domain vs celebration), five celebration rules, architect only via corpus + advisory conformance | D54/D55 | must | orchestrator skill gains the section + seat prompts |
| R8 | Brief anatomy: as-of reconcile SHA · MAJOR reads (vision-not-legacy) · NARROW reads · 3–5 verbatim LOCKED quotes with D#s · post-SHA D# pointers | D57 | must | room-brief-template.md carries the block |
| R9 | One mode law (HUMAN/AUTONOMOUS) at every ruling gate; reserved forks always human; autonomous picks flagged+revisitable; close always human | D59 | must | orchestrator, system-design, self-brainstorming all cite the same law |
| R10 | Checkpoint = one operational handover doc (trio + claims + clusters + inlined facts) + one response block inside milestone decisions.md; two-surface law with OPERATIONAL RECORD stamp | D58/D60 | must | protocols.md worked example rewritten |
| R11 | Mid-item contradictions: show must go on — collect in item files, plan-time pointer relayed room→orchestrator→architect, MISMATCH markers, checkpoint as net | D61 | must | brainstorming/SDD/room-brief text |
| R12 | Close gate gains rolling-window pruning (delete N−1 operational sediment) | D62 | must | orchestrator close-gate list |
| R13 | Angle-first brainstorming + Fork Presentation Standard (incl. re-ask-in-full); angle-guide movement protocol | D56 | must | ALREADY SHIPPED (d0a0e36 + follow-ups); receipt = commits |
| R14 | Glossary + bootstrapping ruling table updated to all of the above | D47–D63 | must | glossary diff; bootstrapping adopt/bridge/discard rows |

## 3. Use cases   [ANCHOR]

| UC | As the operator, I… | Exercises | Realized by |
|----|---------------------|-----------|-------------|
| UC1 | grab any doc from docs/system-design/ and rely on it — it matches reality or wears a marker saying how much to trust it | R1,R5,R6,R10 | 5.1,5.2 |
| UC2 | audit authorship in one command: git log per space shows only its owner | R3 | 5.1 |
| UC3 | sit at a checkpoint that opens with one handover + one collection of clusters, and close it knowing the corpus was reconciled before the commit | R5,R10 | 5.2,5.3 |
| UC4 | declare AUTONOMOUS mode and return to find every orchestrator pick flagged, logged, and overturnable — with money/taste forks still waiting for me | R9 | 5.3 |
| UC5 | read an item room's brief and see exactly which architecture governs it, how fresh, and its verbatim law | R8 | 5.4 |
| UC6 | learn at plan time (not merge time) that a room found the corpus contradicted, while the room keeps building | R11 | 5.4 |
| UC7 | approve a milestone close whose checklist includes pruned sediment — no more 1,000-file excavations | R12 | 5.3 |
| UC8 | brainstorm under an amendable angle agenda with every fork presented in full | R13 | (shipped) |

## 4. Approach narrative

Everything follows from one split (D60): the repo has a RECONCILED surface and an
OPERATIONAL surface. The reconciled surface (docs/system-design/) is small, architect-only,
and carries a guarantee — reconciliation passes (D52) exist to keep it, markers (D53) price
the trust, and the milestone folder (D47/D48) bounds what one reconcile must sweep. The
operational surface (docs/orchestration/) exists because messages must stay short — files
as message companions, stamped as never-reconciled, pruned on a rolling window (D62)
instead. Item rooms live in their own lane and worktrees; nothing they do writes either
surface (D49/D51) — their discoveries travel as pointer-relayed reports (D61), their
architecture context arrives as a five-part brief (D57), and the seam between altitudes is
exactly two artifacts per checkpoint (D58/D60). One mode law (D59) decides who rules at
each gate; the execution proposal (D55) translates ruled architecture into a delivery
hypothesis on the orchestrator's side of the line. The glossary and
bootstrapping table are the composition's vocabulary and on-ramp — without them the words
above don't resolve for a fresh reader. The skill-text work below transcribes this
composition; nothing in it invents beyond the log.

## 5. Design

### 5.1 system-design skill — the reconciled surface
Rewrites the floor (R1/R2/R3): corpus at docs/system-design/, canon-vs-dated layers,
milestone folders, single-writer law with the git-log audit line. map-and-markers.md
rewritten for the positional grammar + census script (R6; script in the skill's scripts/).
Advisory conformance: folded to a
conformance-notes line in the checkpoint response block; one that genuinely needs length
becomes `milestones/<slug>/conformance-<item>.md` (architect space, dated layer).
Session protocol: mechanical open (census, stale-D# grep, agenda-as-questions), sitting,
reconciliation close + named commit (R5), response block format (R10), mode law section
(R9). protocols.md worked examples rewritten to the two-artifact checkpoint.
**Status:** FLEXIBLE — exact section wording lands at implementation · Serves R1–R6,R9,R10 · UC1–UC3.

### 5.2 orchestrator skill — the operational surface
The orchestrator's files carry the operational surface's whole contract. SKILL.md
system-design-layer section rewritten: spaces, typed-row ledgers from reports (R4),
pointer-relay duty (R11), execution-proposal section + two seat prompt sketches (R7), mode
declaration at co-plan (R9), close gate + rolling-window pruning line (R12), and the D49
handoff split (its SKILL.md still describes the killed two-section design/handoffs/ file —
orchestrator half → docs/orchestration/handoffs/, architect half = next milestone folder's
birth). **checkpoint-protocol.md is the file D60 changes most** — it currently writes the
handover to design/residue-collections/ (the directory D60 kills): rewritten to the one
handover doc at docs/orchestration/handovers/<milestone>-checkpoint-N.md + the response
block format (R10). room-brief-template.md gains the five-part architecture block (R8).
durable-state.md: ledgers under docs/orchestration/, OPERATIONAL RECORD stamp.
**Status:** FLEXIBLE · Serves R3,R4,R7–R12 · UC2–UC7.

### 5.3 mode-law cross-wiring
One law stated once — this area makes every gate cite the same text instead of growing
three dialects. self-brainstorming: ratification gate resolves by mode (orchestrator ratifies in
AUTONOMOUS, desk DECIDE in HUMAN) with reserved-fork carve-out. writing-plans Mode field
text cites the unified law. All three skills cite ONE canonical statement (lives in
system-design SKILL.md; others link).
**Status:** FLEXIBLE · Serves R9 · UC4.

### 5.4 room-side text
The rooms are where the corpus meets code — this area rewires their skills to the new
transport and paths. brainstorming step 1 grounding paths → docs/system-design/…; residue
sentence → report-based (R4); deviation flow: collect → plan-time pointer → build on (R11).
**SDD is NOT a path fix:** SKILL.md's launched-as-room paragraph encodes the retired
mechanism verbatim ("appends a residue row (design/residue/residue.jsonl, own ID block)") —
rewritten to the D51/D61 flow (collect in item files → plan-time pointer → orchestrator
relay); this is where D61 lives for arcs. **cli-checkride writes `design/scenarios/` today**
(SKILL.md §5b) and orchestrator SKILL.md reads it — both move to docs/superdev/scenarios/.
using-git-worktrees/finishing: path fixes only.
**Status:** FLEXIBLE — exact wording lands at implementation · Serves R1,R4,R8,R11 · UC5,UC6.

### 5.5 glossary + bootstrapping
The composition only holds if its words resolve and new projects can land on it — this
area is the vocabulary and the on-ramp. Glossary: reconciled/operational surface · reconcile commit · claim marker/section status ·
mode law · execution proposal · handover/response block · pruning window · pointer relay.
Bootstrapping: preflight + ruling table rows for existing conventions (canon≙visions,
per-decision files bridge, item-lane path override); floor creation = docs/system-design +
docs/orchestration skeletons.
**Status:** FLEXIBLE · Serves R14 · all UCs indirectly.

## 6. Decisions
Distilled in the log (D47–D64) — this spec's §5 cites them inline; no divergence between files.

## 7. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | Rolling-window pruning (D62) won't starve process-feedback harvesting (harvest happens at close before deletion) | R12 | unratified — first live close proves |
| A2 | The census regex (D53) has no prose false-positives at scale | R6 | unratified — script ships with a self-test corpus |
| A3 | Plan-time deviation notification is early enough for LOCKED-class contradictions (no ack window needed) | R11 | unratified — D61 revisit hook |

## 8. Not doing
- Mid-item CORRECTION push to live rooms on superseded quoted D#s — named BLIND (D57/D61 hooks); revisit on first post-merge overturn.
- Calibration migration (D63) — separate stream (D64), receipt lives there.
- Per-milestone D# blocks for parallel milestones — D48 revisit hook, no live case yet.
- room-graph-orchestration plugin edits — vocabulary unchanged this round; revisit if the mode law needs cross-plugin mapping.

## 9. Acceptance — hints & receipts   [ANCHOR: the hints]

| # | Acceptance hint (operator terms) | Proves | Receipt (filled at gate) |
|---|----------------------------------|--------|--------------------------|
| AH1 | A reader of the shipped skill text can draw the two-surface map — every space, its writer, its freshness law — without this spec | R1,R3,D60 | |
| AH2 | The census script runs on the bench corpus copy and reports status counts with zero prose false-positives | R6 | |
| AH3 | A composed room brief (from the template) carries all five architecture parts, with real file:line MAJOR reads and verbatim quotes | R8 | |
| AH4 | The three mode-law citations (orchestrator, system-design, self-brainstorming) resolve to one canonical statement with identical reserved-fork classes | R9 | |
| AH5 | The worked checkpoint example shows exactly two artifacts + one commit, stamped and placed correctly | R10 | |
| AH6 | A simulated mid-item contradiction walks the D61 flow end-to-end in the skill text (collect → pointer → relay → build-on → checkpoint net) | R11 | |
| AH7 | Fresh-eyes reviews (D46) passed on every edited skill, blockers folded | all | |
| AH8 | Angle-first brainstorming + Fork Standard live and used (this session ran under them post-fix) | R13 | commits d0a0e36+ ; this session |
| AH9 | The skill text walks a full checkpoint: handover written, sitting held, response block + rulings landed, reconcile commit closes — with the milestone folder (incl. its decisions.md and INDEX D#-range line) named at every step | R2,R5,R10 | |
| AH10 | A room's design-class finding demonstrably reaches the orchestrator's typed ledger from a report — the skill text names the row shape (kind tags) and the report seam, with no room-writable ledger anywhere | R4 | |
| AH11 | The orchestrator text yields a complete execution proposal round: two opposed seat dispatches, collision reconciled under the five rules, operator ratification, charter graph derived | R7 | |
| AH12 | The close-gate checklist as shipped contains the N−1 pruning line, and the pruning's keep-set (handoffs, conventions, improvement notes) is named | R12 (UC7) | |
| AH13 | Every new term of this design resolves in the glossary, and the bootstrapping ruling table maps an existing-project convention onto each new space | R14 | |

## 10. Drift protocol
Standard (§10 of the template): governing D# → revisit-when → log fork (phase: build) →
supersede, never erase. Anchor changes only by soften-but-own.
