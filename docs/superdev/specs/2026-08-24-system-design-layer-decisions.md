# superdev system-design layer — Decision log

**Design doc:** ./2026-08-24-system-design-layer-design.md
Append-only; newest at the bottom.

Context at start (2026-08-24): evidence from ai-trading-calibration Phase 3 —
`docs/superpowers/specs/2026-08-21-orchestrator-handoff-state.md`, `docs/reference/2026-08-21-orchestrator-process-feedback.md`,
and the bench-architecture worktree (9 angle docs, 4 Codex seat reports, angle-08's KEEP/RESHAPE/REPLACE/DEFER
current→target map, per-angle LOCKED/FLEXIBLE/DEFERRED/CURRENT-MISMATCH status vocabulary).
Operator's diagnosis: superdev's brainstorm→plan→SDD pipeline was built for new features; it lacks a
**system-design level** (holistic, longer-lived, angle-based, with migrate/delete markers) above task-level
brainstorms; refactoring/migration work is under-supported; test strategy during big domain shifts is unclear
(5000+ tests, re-pin waves, ~17 inert guards); build-time insights that should steer the next design session
are captured only as plan deviations; without manual enforcement, design decisions get skipped, components
duplicated, migrations missed. Code is pre-production — drastic moves allowed; no production-grade
step-by-step migration ceremony wanted. Operator currently does the system-design work with Codex by hand
and wants it in the orchestrator flow.
---

## D1 — Corpus is the law; a persistent ARCHITECT room keeps it alive
**When:** 2026-08-24T06:59:41Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Trigger:** where does design authority live (corpus / orchestrator / both)?
- **Decided:** The design corpus (angles + current→target map + design decision log) is the binding law, so it works solo and orchestrated. System design is **not fire-and-forget**: a persistent ARCHITECT room owns the corpus, keeps its context across milestones, continuously absorbs residue/discrepancies from builds, and hosts operator design sessions in-room. Two knowledge levels are explicit: L1 system design / big picture (ARCHITECT) vs L2 task execution quality (item rooms + SDD).
- **Rests on:** process-feedback §§3,5,7; angle-08 evidence; operator statement 2026-08-24.

## D2 — Ledgers are truth; messages are pointers (re-affirmed for the new layer)
**When:** 2026-08-24T06:59:41Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Every instruction/finding lands in a committed ledger; messages only say "new entry at X". Superdev's per-workstream decision files predate cross-session messaging and must be re-cut along room ownership lines rather than session lines.

## D3 — No architect gate on publish; conformance is advisory and forward-acting
**When:** 2026-08-24T07:18:11Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Trigger:** should the ARCHITECT's conformance receipt be a veto on publish?
- **Decided:** No. Development is continuous. A worktree that stops is a worktree that never merges, and unmerged code corrupts every later plan — so an item room always finishes and publishes. Conformance findings act FORWARD: the skill plants **markers in the codebase** (deliberate, addressable architecture debt) so work can complete with issues delayed to the next migration pass; the orchestrator may charter follow-up work to absorb a marker. The receipt informs the next charter, never blocks this publish.
- **Revisit-when:** a marker class turns out to be silently ignored across two sessions → then discuss a harder mechanism.

## D4 — FRONT DESK is required
**When:** 2026-08-24T07:18:11Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Operator's desk room: every room may notify it of events; it renders one queue. Whoever needs the operator's input holds the conversation in their own room (item room, architect); the desk only points there.

## D5 — Strict altitude split: ARCHITECT = future; ITEM ROOM = present
**When:** 2026-08-24T07:18:11Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- ARCHITECT never solves tactical problems. A discrepancy between architecture and the code is resolved IN the item room (it knows the current implementation best), then reported back as residue; the architect folds it into the corpus at the next session. "The architect will not know more about the codebase; it may only know the future better."

## D6 — Packaging: update the superdev plugin (improvement, not a fork)
**When:** 2026-08-24T07:18:11Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- New `system-design` skill + edits to the affected superdev skills; room-graph-orchestration gains the architect/front-desk charter support. No new plugin.

## D7 — Worktree and merge belong to the ITEM ROOM
**When:** 2026-08-24T07:28:45Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- The item room owns its worktree end to end: creation, work, FF-CAS merge, and retirement at close. The orchestrator only verifies at room close that the worktree is merged and gone (the 30-dead-worktrees debt never recurs). Supersedes the "worktree lifecycle" line in the orchestrator's responsibilities.

## D8 — Orchestrator collects residue; architect works per-checkpoint on the collection
**When:** 2026-08-24T07:28:45Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Continuous per-residual triage is the ORCHESTRATOR's (it already routes everything). The ARCHITECT never works at the individual-residual level: at a **checkpoint** — e.g. a set of worktrees merged, a milestone event — the orchestrator hands it the residue collection and initiates a design push; the architect then advances the corpus against the whole collection. Supersedes D1's "continuously absorbs" phrasing: the architect thinks in batches anchored to system state, not in dribs.

## D9 — Orchestrator may create rooms outside the standard roster
**When:** 2026-08-24T07:28:45Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- The four persistent rooms + item rooms are the *standard* shape, not a closed list. The orchestrator may charter an ad-hoc room with a different skill combination when a concern fits neither an item room nor the architect (e.g. a probe, a spike, a cross-cutting sweep) — explicitly so the architect room is not polluted with foreign skill mixes.

## D10 — Item-room direction (details deferred): wider tasks, split by role not by task
**When:** 2026-08-24T07:28:45Z · **Phase:** brainstorm · **Status:** provisional (deep-dive owns it) · **Decided by:** Tadas
- Inside the item room: (a) awareness of the corpus and of the ARCHITECT is one concern; brainstorm/plan is another. (b) SDD tasks should be **wider and bigger** than today's bite-size tasks — Codex-grade implementers can carry them. (c) The split is **by role, not by task**: one implementation agent carries the work, one reviewer, then follow-up — not many small task subagents each rebuilding context.

## D11 — The milestone is the implementation boundary and the orchestrator's whole world
**When:** 2026-08-24T07:35:11Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Design is boundless (must be holistic, touch every angle). Implementation is bounded, and the boundary is the **milestone**. The orchestrator's only job is the milestone: keep work inside it, manage boundary adjustments (upstream/downstream dependencies may force them — allowed to discuss, biased to contain). A milestone must END with (a) architectural suggestions from what was built and (b) upfront system design prepared for the NEXT milestone (live example: paper-wallet design prepared during the current one). One shared granularity vocabulary across all skills is required before room design.

## D12 — Vision documents: post-migration grounding material
**When:** 2026-08-24T07:44:55Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Trigger:** grounding poisons future design — every session grounds on the codebase, and the codebase is legacy until a migration lands, so "migration needs to be done" written in an angle leaves nothing to ground the NEXT session on.
- **Decided:** when the map declares a large change, the corpus gains a **VISION document** — a post-migration domain document describing how that area WILL look — and future design sessions ground on the vision, not the legacy code, for everything the map says will change. Precedent: Tadas's post-migration strategy-core domain doc, pointed at as truth for later sessions. Rule: a REPLACE/RESHAPE cluster above a size threshold is not ruled until its vision doc exists.

## D13 — Docket dropped; the word is BACKLOG (already in practice)
**When:** 2026-08-24T07:44:55Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Parked open questions = backlog items (`docs/backlog/items/…` already exists in the calibration repo). "Docket" retired.

## D14 — Two marker families, both greppable: MIG-MARK in code, DOC-MARK in the corpus
**When:** 2026-08-24T07:49:07Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Code:** `MIG-MARK[<CLASS>][<D#>]: note` — classes RESHAPE · REPLACE · SEAM · TEST (closed; new class needs a D#). Removed with the fix, never resolved in place; census = grep, progress = count trend.
- **Docs:** `DOC-MARK[<STATUS>][<D#|owner>]` — statuses **LOCKED** (operator-ruled) · **FLEXIBLE** (boundary agreed, shape may move) · **DEFERRED** (another session owns it) · **BLIND** (not yet examined — the architect's honest "I haven't looked here") · **MISMATCH** (code does something different today). Extends the bench-angle status guide, made greppable so a session can open with "grep the BLINDs and MISMATCHes".
- One symmetry rule: every MIG-MARK's D# resolves to a corpus entry; every DOC-MARK[MISMATCH] should eventually have a MIG-MARK twin in code or a residue row explaining why not.

## D15 — Glossary closed: handoff · bridge · checkpoint (absorbs stage)
**When:** 2026-08-24T07:49:07Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Handoff** = the milestone-close package: architectural suggestions + next milestone's upfront design (visions included). **Bridge** = the seam between bounded things (items, domains, CLIs) where a dependency crosses; ordering falls out of contested bridges. **Checkpoint** = any declared verify-then-hand-off moment, at plan level (`## Checkpoint C1`) and milestone level alike; "stage" and "joint" and "runway" retired. Full ladder: corpus/angle/vision/design-session (boundless) · residue/marker/backlog (bridge state) · milestone/item/checkpoint/task/micro-task (bounded), with charter, census, checkride, cursor, debrief kept.

## D16 — Test clearance for domain redesigns (item-level brainstorm owns the details)
**When:** 2026-08-24T07:49:07Z · **Phase:** brainstorm · **Status:** provisional (item-room deep-dive) · **Decided by:** Tadas
- Legacy tests are the biggest time sink under drastic architecture change. Direction: **clearance for deletion** — capture business requirements FROM the tests (harvest), then delete them with the code they guard, then write new tests against the vision. Each item-level brainstorm must decide the test disposition explicitly (harvest→delete→rewrite vs keep vs regenerate); MIG-MARK[TEST] carries the debt when deferred. Extends the D76 harvest/delete/rewrite directive that was right and under-used.

## D17 — Corpus layout: canonical shape, per-project extensible
**When:** 2026-08-24T12:16:59Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- One canonical directory shape so graphs, briefs and greps are uniform across projects: `design/angles/` · `design/visions/` · `design/map.md` (row grammar: verdict KEEP/RESHAPE/REPLACE/DEFER · test verdict · MIG-MARK refs · DOC-MARK status · discharging item) · `design/decisions.md` · `design/residue-collections/`. Projects may add document kinds freely — the canon is a floor, not a ceiling.

## D18 — The architect idles between checkpoints; system design is human-driven; the orchestrator pauses when design runs dry
**When:** 2026-08-24T12:16:59Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Between checkpoints the ARCHITECT does **nothing** unless a message arrives (messages land in logs regardless; no proactive polling — reaching out would trigger work). **There is no self-driven system design**: the room is human-driven, period. When the human has time/energy they attach and keep architecting (upfront visions, BLIND areas) — the architect works WITH them, holding context. When the human is absent and an architecture gap appears, the **ORCHESTRATOR** must recognise it and pause or stop execution — "design can no longer be continued" is a halt condition it owns, not something rooms discover individually.
- Session-protocol examples to be produced when the skill is written (operator wants to see them).

## D19 — Checkpoint declaration: rule + feel + worker green lights
**When:** 2026-08-24T12:21:53Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- A checkpoint is declared from three inputs: **rule** (bridge-side merges complete, milestone close, operator ask) · **green lights** — rooms explicitly signal "I have nothing more to contribute to this arc" · **feel** — the orchestrator judges that everyone has contributed enough. Not purely mechanical (supersedes the "never senses ripeness" proposal).

## D20 — The checkpoint handover is a designed protocol, not a dump
**When:** 2026-08-24T12:21:53Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Orchestrator→architect handover is a structured ledger document + pointer message: *what we got · where we feel gaps exist · what we want to focus on next* — and it explicitly asks the architect **agree or disagree**. The architect's response (agree/disagree per section + session agenda) is the same protocol in reverse. Clustering yes; "blocking-next-charter" flag kept but subordinated to the three-part narrative. Full format in the design doc.

## D21 — Design-dry pause is scoped
**When:** 2026-08-24T12:21:53Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Pause only items whose charters need the missing ruling; full milestone stop only when the gap sits on a bridge every remaining item crosses.

## D22 — No orchestrator-level micro tier; small work lives inside items
**When:** 2026-08-24T12:21:53Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- The orchestrator focuses on items and never executes work itself. Micro tasks are absorbed INTO item rooms (a room may be chartered lean, or an adjacent live room picks small work up). Supersedes the process-feedback §3 "micro-task tier at the orchestrator" and D10's mention of it.

## D23 — Angle contract: model sketches + shell pseudo-code; organised against loosening
**When:** 2026-08-25T04:57:42Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Content forms** an angle may carry, beyond prose: (a) **Pydantic model sketches** — invariant/variant modeling of domain types (FrozenModel-style), marked FLEXIBLE by default: they express agreed responsibilities and invariants, never final field names; (b) **functional-core / imperative-shell pseudo-code** — short walkthroughs showing how the pure core and the imperative shell interact for a journey. Both are DOC-MARKed like everything else.
- **Anti-loosening organisation** (angles complement system design and must not decay): angles live only in `design/angles/` as a numbered series with an `INDEX.md` (number · purpose one-liner · formal anchors · last-updated · DOC-MARK counts); every design session ends with an **angle sweep** — any angle whose anchors were touched is updated in the same session, superseded in place, never forked; an angle citing a superseded D# is mechanically detectable (grep D#s against the log's status) and goes on the next agenda; a residue cluster fitting no angle triggers a NEW angle, keeping the set honest.

## D24 — §5.4 lands in superdev's orchestrator; room-graph's stays generic
**When:** 2026-08-25T05:09:50Z · **Phase:** spec · **Status:** provisional (operator to ratify with the spec) · **Decided by:** Claude, from the reviewer's two-orchestrator finding
- Two orchestrator skills exist. superdev's already owns milestone close + FF-CAS room mechanics and is what the calibration milestone runs on → it receives the milestone/checkpoint/pause law. room-graph-orchestration's stays a generic graph runner; its graph-creator gains the development-organisation template. Alternatives: deprecate superdev's (breaks the live milestone's canon) · duplicate in both (drift). Revisit-when: the two skills' audiences merge.

## Addendum (2026-08-25) — revisit-when hooks for load-bearing rulings
Appended, not rewritten (the log is append-only). These are the arbitration triggers §10 reads:
- **D1** revisit: never for corpus-as-law; architect-room shape if two projects need different room mixes.
- **D5** revisit: if item rooms repeatedly mis-resolve design-class questions locally → tighten what counts as L1, not the split.
- **D7** revisit: if a merge conflict class appears that rooms cannot resolve alone → a merge-helper protocol, ownership unchanged.
- **D8** revisit: if checkpoint batches arrive too large to hold in one session → smaller checkpoints, never per-residual work. (Also: D1's "continuously absorbs" phrasing is superseded by this entry — D1 status stands for its core.)
- **D11** revisit: if two consecutive milestones blow their boundary at the same bridge → the milestone was cut wrong; re-cut at design, don't loosen the rule.
- **D12** revisit: if visions drift from what lands twice → visions gain a post-merge reconciliation step.
- **D14** revisit: a needed marker class (new D#) or a grep collision with real code.
- **D15** note: the bounded ladder's "micro-task" entry is superseded by D22 (micro tasks exist only inside items); "phase" is retired only as a work-unit name — the decision-log lifecycle field keeps it.
- **D18** revisit: if pauses become chronic → the operator's architecture time is the bottleneck; fix scheduling, not autonomy.
- **D19** revisit: if checkpoints fire early on hollow green lights (A3) → weight rule inputs higher.
- **D21** revisit: if a withheld charter turns out to have been safe twice → narrow what "needs the ruling" means.
- **D22** revisit: if item rooms refuse small work and it pools unowned → a "sweeper" item per milestone, still not an orchestrator tier. (D22's claim to supersede a D10 micro-task mention is withdrawn — D10 contains none.)
- **D23** revisit: if the angle set exceeds ~15 → merge angles at a session; the INDEX makes bloat visible.
- **D17** note (2026-08-25): the corpus floor is extended by the §5.10 protocol ledgers (`residue/`, `conformance/`, `handoffs/`, `marker-census.md`) — spec-mandated, not per-project extensions.
- **D18** note (2026-08-25): its "pause or stop execution" phrasing is superseded by D21+R4/R8 — a design-dry pause withholds charters only; live rooms always run to merge.

## D25 — Process improvement: orchestrator captures feedback → briefs adapt now → a command batches skill fixes through self-improvement
**When:** 2026-08-25T05:25:12Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Trigger:** how do we continuously improve the process and the skills (bad briefs, velocity, token burn, process issues)?
- **Decided:** No retro room, no retro ceremony. (1) The ORCHESTRATOR **captures process feedback** as it runs (its own observations + rooms' R5 lines + measured facts: wall-clock, review cycles, wait times, tokens summed from session JSONLs) into a **process-feedback ledger** — shared memory each room can also append to in its ID block. (2) **Fast loop:** the orchestrator acts on it immediately where it owns the surface — every newly spawned room's brief is altered per the accumulated feedback; an O-log line records what changed and why. (3) **Slow loop:** a **command** (`/superdev:improve` or equivalent) kicks the existing `self-improvement` skill over the accumulated ledger — it clusters entries, diagnoses boundaries per its flow-mapping method, and ships operator-approved skill edits with version bumps. Cross-checked 2026-08-25: `self-improvement` is current and fits as the engine; it gains an inbox mode (consume a feedback ledger, not just a single failure) and the command entry point. Rooms never self-grade velocity — measured facts come from the orchestrator's timestamps and logs.
- **Rests on:** D2 (ledger + pointers), the O-log precedent (O1–O58), process-feedback doc §6.
- **Revisit-when:** brief-adaptation drifts from the skill text so far that new projects start worse than adapted ones → that is the signal the slow loop is overdue, not a reason for more live patching.
