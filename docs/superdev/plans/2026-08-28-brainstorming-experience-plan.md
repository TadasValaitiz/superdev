# Brainstorming Experience — Implementation Plan

> **For agentic workers:** Execution: inline (doc-only; D46 — verification by fresh-eyes
> reviews with the §5.5 experience probes, never TDD). Steps use `- [ ]`.

**Goal:** Rebuild the brainstorming skill and its templates so a session natively produces
the bench-corpus experience (BR1–BR14), then land the D47–D63 architecture transcription in
the remaining skills using the rebuilt templates as exemplars.

**Context pack:** the study (`specs/2026-08-28-bench-experience-study.md` — the WHY behind
every edit; quote it in reviews) · the experience design (`specs/2026-08-28-brainstorming-experience-design.md`)
· the decision log (D47–D69 — D68 boundary rulings and D69 FLAT corpus are load-bearing for Task 5) · the bench originals (angle-19, angle-06, D461, the angle-definition doc — NOW at
`/Users/tadas/Projects/ai-ethics/ai-trading-calibration/docs/system-design/` on main, flat,
per D69/a42b408e; the study header's worktree path is historical) as the depth reference ·
current skill files per task.

## Global Constraints
- D66 register law: every document these tasks produce or template is a TEACHING document;
  reviews probe "readable without the log", never word counts.
- D46: fresh-eyes review per task, blockers folded before the next task starts.
- The Fork Presentation Standard and angle-agenda flow (shipped, d0a0e36+) are the floor —
  nothing below re-opens them; these tasks build on top.
- Vocabulary verbatim from the log; supersede never erase.

## The Through-Line
Task 1 rebuilds the templates — the angle document form and the decision entry form — first,
because they are what every other edit points at: the skill text can only say "write to the
template" if the template already teaches the bench form. Task 2 rewires the skill's session
arc around them (census artifact, sketch-variants, close-time writing, the end-of-session
sweep). Task 3 turns the reviewers into experience probes. Task 4 exercises the whole
pipeline once on a real small design (the operator picks the subject) — the live receipt
that the experience actually changed, gating the release. Task 5 then transcribes D47–D63
into the remaining skills (the discarded plan's W3-2..W3-4 content, unchanged in scope),
now written in the rebuilt register with the rebuilt templates as exemplars. A conflict no
D# settles → log (phase: build), then proceed.

## Acceptance (anchored)
Discharges BH1–BH7 (experience design §9); Task 5 additionally discharges the freshness
spec's surviving AH set (AH1–AH7, AH9–AH14 — that spec's RULINGS stand though its document
was discarded; receipts land in the experience design's log entry for traceability).

### Task 1: the two templates — angle form and decision form
**Read first:** study P1 + P2 (every section maps to a template section); bench angle-06 and
angle-19 IN FULL (the reference experience); D461 in full; current `item-angle-template.md`,
`decision-log-template.md`, `design-doc-template.md`.
**Files:** rewrite `skills/brainstorming/item-angle-template.md` (the bench form: mental
model with analogy + "It is not:" · concrete journey with `### LOCKED — <claim>` subsections
each closing "this means…" · per-host walks · what-X-cannot-do · mismatch + salvage ·
collisions as "X versus Y: mechanism" · flexible-and-deferred with landing places ·
reconciled outcome · the depth bar and register law in the header). Rewrite
`decision-log-template.md` (adds: Decided-by line with selector/variant/rider · Rests on /
Affects · extension law slot · named anti-patterns · "Not X" clarifications — D461 as the
worked example, quoted). Touch `design-doc-template.md` §5 only where it references the old
angle form.
- [ ] Rewrite both templates with one fully-worked example each (drawn from this stream's
  own material, at full depth — the example IS the depth bar made concrete).
- [ ] REVIEW: a fresh reviewer, given ONLY the templates, writes a sample angle for a toy
  design and a sample entry; a second fresh reader answers comprehension questions from the
  sample angle without any other file. Fold blockers. Commit.

### Task 2: the session arc — census, sketch-variants, close-time writing, the sweep
**Read first:** experience design §5.1–§5.2; study P3; current SKILL.md (post-d0a0e36).
**Files:** `skills/brainstorming/SKILL.md`.
- [ ] Step 1 → census artifact: exploration produces `docs/superdev/specs/YYYY-MM-DD-<topic>-census.md`
  with MEASURED / READ / FLAGGED tiers ("FLAGGED are the work queue, not conclusions"),
  committed before the agenda is presented.
- [ ] Fork Presentation Standard gains the two additions: variants-with-shape arrive as
  typed sketches (the thing itself, small); the pick is an EVENT — selector, variant, rider
  recorded in the D# entry, rider enters the law.
- [ ] Step 5 close-time clause upgraded to the new template ("writes its companion to the
  bench form, then commits it — before the next angle opens"); new final step: the
  in-session reconcile sweep — every produced document's statuses checked against every
  ruling made this session; stale ones flipped; one commit.
- [ ] The presentation convention section (BR14) added verbatim-adapted from the bench
  angle-definition doc, including "a resolved fork records the selection, never a stale
  recommendation".
- [ ] REVIEW: reviewer walks the checklist as a simulated session and verifies each BR
  requirement has a step that produces it; probes ordering traps (census before agenda;
  companion before next angle). Fold. Commit.

### Task 3: reviewers as experience probes
**Read first:** experience design §5.5; current `spec-document-reviewer-prompt.md` (post-W3-1
edits if landed, else current).
**Files:** `spec-document-reviewer-prompt.md`.
- [ ] Add the probe set: stranger-comprehension (answers from the angle alone) ·
  LOCKED-without-consequence · bare-"later" deferrals · stale recommendation after a
  resolved fork · missing negative space on a likely-misread ruling · missing Decided-by/
  Rests-on/Affects in entries. Angle companions are required inputs (D65).
- [ ] REVIEW: run the upgraded prompt against this stream's own rewritten angle-01..03 —
  its findings are the calibration check (it should pass them and flag the two discarded
  thin ones if pointed at them). Fold. Commit.

### Task 4: the live receipt — one real session under the rebuilt skill
- [ ] With the operator: run one SMALL real brainstorm (operator picks the subject) end to
  end under the rebuilt skill. Its artifacts — census, sketch-forks, per-angle companions,
  the sweep commit, the upgraded entries — are the receipts for BH1–BH6; the reviewer run
  on its output receipts BH7.
- [ ] Seed one deliberately stale status into a session document mid-run and verify the
  sweep flips it (BH6's planted defect — tell the operator it was seeded, after).
- [ ] Fold whatever the live run teaches (there WILL be findings — D67's lesson is that the
  experience is only real in use); bump version; RELEASE-NOTES entry; release.

### Task 5: the D47–D69 transcription — explicit subtasks
**Read first:** the decision log D47–D63 + D68/D69 (the law); the four freshness angles
(the format exemplars); the AH appendix below (the receipts owed).
**5a — system-design skill** (`skills/system-design/`): SKILL.md corpus floor → the FLAT
structure (D69 filename convention, INDEX-as-hub, in-place-reconciled INDEX+glossary,
grandfather clause), single-writer law + audit line (D49), report-based residue with typed
rows (D51), session protocol with reconcile close (D52), response block (D60), THE
canonical mode-law section (D59). map-and-markers.md → positional grammar + census script
(globs per D69 filenames) with self-test fixtures. protocols.md → two-artifact checkpoint
worked example. angle-guide.md → align with the rebuilt item-angle-template.
**5b — orchestrator skill** (`skills/orchestrator/`): SKILL.md system-design-layer section
(spaces, typed ledgers, pointer relay incl. D61 plan-time forwarding, mode at co-plan,
handoff split with the D68 handoffs/handovers gloss, close gate + D62 pruning line,
execution-proposal section + two seat prompts per D55). checkpoint-protocol.md → full
rewrite to `docs/orchestration/handovers/` + response-block expectations.
room-brief-template.md → the five-part ARCHITECTURE CONTEXT block with FLAT paths (copy
the corrected block from freshness-angle-03). durable-state.md → ledger paths + the
OPERATIONAL RECORD stamp.
**5c — cross-wiring:** self-brainstorming SKILL.md (mode-resolved ratification gate);
writing-plans FULL-SET contract (D71: context pack lists every angle companion + census; task Read-first cites governing angle sections; self-review walks each angle's cannot-do + collisions against the task list; plan-document-reviewer-prompt.md receives the angles) + Mode text (cites the canonical law); brainstorming SKILL.md steps 1/8 path+
transport fixes (done early if blocker-driven); SDD SKILL.md room paragraph → D61 flow;
cli-checkride §5b → docs/superdev/scenarios/; test-driven-development/test-clearance.md
design/visions reference → flat vision filenames; glossary.md (two surfaces, reconcile
commit, claim marker, mode law, execution proposal, handover vs handoff, pruning window,
pointer relay, rider); bootstrapping SKILL.md (flat floor creation, bridge-rows).
**5d — release:** repo-wide sweep `grep -rn "design/" skills/ | grep -v system-design` →
zero unjustified survivors; per-skill fresh-eyes reviews; whole-wave review; fill the AH
appendix receipts; version bump (8.0.0 — breaking paths); RELEASE-NOTES; release.

## AH appendix — surviving acceptance hints (re-homed from the discarded freshness spec)
The discarded spec's hints remain the receipts Task 5 owes; their texts, verbatim, so no
discarded document is load-bearing: AH1 two-surface map drawable from skill text alone ·
AH2 census script runs on a corpus copy with zero prose false-positives · AH3 a composed
brief carries all five parts with real reads · AH4 the three mode-law citations resolve to
one canonical statement · AH5 worked checkpoint shows two artifacts + one commit, stamped,
placed · AH6 a simulated mid-item contradiction walks the D61 flow in the skill text ·
AH7 fresh-eyes reviews passed on every edited skill (spans ALL tasks) · AH9 skill text
walks a full checkpoint incl. the milestone set's D#-range line · AH10 a room finding
reaches the orchestrator's typed ledger from a report, no room-writable ledger anywhere ·
AH11 a complete proposal round: two seat dispatches, five-rule reconciliation, ratification,
derivation · AH12 the shipped close-gate checklist carries the N−1 pruning line + keep-set ·
AH13 every new term resolves in the glossary; bootstrapping maps existing conventions.
(AH8 already receipted — d0a0e36+; AH14 discharged by Tasks 2/3 — commit 862a7d9.)

**RECEIPTS (2026-08-28, Task 5d):** AH1/AH3/AH4/AH5/AH11/AH12/AH13 verified ✓ by the
independent Codex whole-wave review (worker review-experience-c41, gpt-5.6-sol, read-only)
with producing quotes per hint; AH6/AH9/AH10 initially ✗, fixed across three fold commits
and re-verified ✓; AH2 receipted by `scripts/marker-census.sh --selftest` (green) + the
live run on the bench corpus (57 LOCKED · 9 FLEXIBLE · 9 DEFERRED). Final verdict: GO.
AH7 receipted by the review chain itself (4 Claude passes + 4 Codex passes, all folded).
Still open by design: BH1–BH7 (Task 4's live trial — awaits a real design session).

## Self-review (updated post-review; Tasks 1–3 landed — their 'current file' lines are historical)
BR1–BR14 each have a producing step (BR1 T2 · BR2–BR8 T1 · BR9/BR10 T1+T2 · BR11 T2 ·
BR12 T1 headers · BR13 T1+T3 · BR14 T2); BH1–BH7 all receipt at T4; the surviving freshness
AH set receipts at T5. No placeholders; all current-file claims verified this session.
