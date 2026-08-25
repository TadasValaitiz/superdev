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

## D26 — Brainstorming writes its own item-level angles; system docs are cited with line numbers
**When:** 2026-08-25T05:53:59Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Altitude of detail, not just authority:** system-design angles are holistic and deliberately skip details, UX, and specifics; item-level brainstorming is where the details live. So the brainstorming skill **writes its own angles** (same template — the operator's 2026-08-25 angle definition doc — one central question, boundaries, concrete consequences, visible collisions, reconciled outcome), scoped to the item. **Repetition with system angles is acceptable and expected** — a little overlap beats a detail gap. The skill must be *aware* system-design documents may exist: it appends the relevant system-doc passages **with line numbers** into the session context and cites them precisely; new cross-boundary concerns discovered at item level are residue for the architect, but the item's own angles are the brainstorm's to write.
- **Revisit-when:** item angles start contradicting system angles silently → add a reconciliation check to the spec reviewer.

## D27 — Test/legacy strategy: own operational section with HIL now; unified protocol extracted later
**When:** 2026-08-25T05:53:59Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- writing-plans gains an **Operational strategy** section of its own (not folded into the execution-route line): what happens to the tests and legacy code this plan touches — fix-in-place · disable/temporarily archive then harvest use cases and rewrite · harvest-delete-rewrite — elicited from the operator initially, options proposed by the agent. **Explicit extraction path:** once the choices stabilise across plans, the pattern is extracted into a unified protocol (a reference doc the skill consults) and the human leaves the loop for those decisions. Auto-resolution is the end state; HIL is the calibration phase.
- **Revisit-when:** three plans in a row make the same choice for the same signature → extract the protocol then.

## D28 — Item angles beside the spec; execution-shape proposals; archive lifecycle
**When:** 2026-08-25T05:57:24Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Item angles** live in item space — `docs/superdev/specs/<date>-<topic>-angle-NN-<slug>.md` beside the design doc; `design/angles/` remains the architect's.
- **Execution shape:** writing-plans always proposes 2–3 variants (task count · deliverable count · worker class · subagent/room count, with a recommendation) before writing tasks; replaces the silent `Execution:` default even for small plans (one-variant proposal acceptable). Deeper execution improvements are owned by the R22 item-room deep-dive.
- **Archive lifecycle** (supersedes D27's open mechanics): initial sweep pushes affected tests to `tests/_archived/<plan>/` with a manifest + harvest file so anything can be **recalled during development**; after development completes, a cleanup step **deletes the archived tests and keeps only the manifest** for the record. Archive is a development-time buffer, not a museum.
- **Revisit-when:** a recalled test saves a build twice → maybe keep archives one milestone longer.

## D29 — The operator's item arc: brainstorm → agree execution shape → step out → execution auto-starts
**When:** 2026-08-25T06:03:33Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- Inside an item room the operator participates in brainstorming, bridges into writing-plans, agrees on the execution-shape proposal — and then **steps out**. Execution starts automatically at that moment; no further "shall I proceed" prompts, no waiting for the operator between plan approval and the first commit. The operator returns only via the desk's queue (a DECIDE, a checkride, or by choice).
- **Revisit-when:** an execution auto-start ever proceeds past a materially changed plan without the operator having seen the change.

## D30 — Operator-absent chartering: self-brainstorm to a ratification gate, wait as a desk DECIDE
**When:** 2026-08-25T06:07:37Z · **Phase:** spec · **Status:** provisional (operator to ratify) · **Decided by:** Claude, from the pipeline-walk review
- **Trigger:** R4 promises chartered rooms always run to merge, but D29 makes the operator a required brainstorm participant — a room chartered while the operator is away would stall before its first marker.
- **Decided:** such a room runs `self-brainstorming` (its stated purpose: pre-work when no human respondent is available) through spec and plan to the **ratification gate**, then waits there as a desk DECIDE. This waiting-at-ratification state is the **one named exception** to R8's "always finishes and merges". On ratification (+ execution-shape agreement) it auto-starts per D29. Alternatives: withhold item charters while the operator is away (stalls the milestone — rejected as a larger concession); let it proceed unratified (violates D29 and the operator's own verdict that self-brainstorming is not a substitute at real forks).
- **Revisit-when:** ratification queues exceed ~2 items — then the operator's availability, not the mechanism, is the bottleneck.

## Consistency rulings from the pipeline walk (2026-08-25, applied to the spec)
- **Auto-start trigger = the agreement**, not the detach (D29's "at that moment" stands; AH18 reworded). Staying attached after agreement is fine — the operator becomes an observer; no further prompts either way.
- **Item-room modes:** HIL from brainstorm through shape agreement; autonomous after; the agreement is the flip. Owner of the plan→execution handoff: writing-plans hands off, subagent-driven-development auto-enters (wave-2 line added).
- **Test disposition precedence:** the **brainstorm sets the disposition** {keep · regenerate · archive-then-rewrite · fix-in-place}; the plan may only refine it into mechanics (which tests, which archive path), never reverse it. One vocabulary, in the glossary.
- **Angle split:** **system angle** (design/angles/, five kinds, anti-loosening machinery binds) vs **item angle** (beside the spec, operator's template, no INDEX/sweep obligations). Glossary carries both, like residue/residual.
- **Plan checkpoints** are cleared by the room's reviewer role; only a failed one emits an event (orchestrator, desk-visible). They never notify the architect (unchanged).
- **Conformance reports** are produced at the checkpoint session, over the diffs published since the last one; charters issued between checkpoints get none.
- **Close gate checklist** gains: archived tests deleted, manifest retained (beside the worktree check). **Probe gate binds item charters only** (ad-hoc probe rooms are how censuses get made).
- **Gate receipts** defined: the evidence lines a plan checkpoint and the close gate record (tests run, marker delta, map rows claimed).

## D31 — Subagent snapshots are tracked and pasted into the next dispatch
**When:** 2026-08-25T06:16:20Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Decided:** SDD tracks its subagents and their **REGROUND snapshots** as first-class artifacts: every implementer writes `.superdev/sdd/task-N-snapshot.md` (territory map: files + why · invariants and traps · fast verify commands · unfinished edges) at task end and at each plan checkpoint; fix agents append deltas, never rewrite. A **snapshot registry** (`.superdev/sdd/snapshots.md`: task · territory · snapshot path · agent name while addressable) lets the controller, when dispatching the NEXT subagent into overlapping territory, paste/point the relevant snapshot(s) into the dispatch — reground becomes a read, not a re-derivation. Complementary fast path: while the original implementer is still addressable, fixes go by SendMessage continuation (its live context is the snapshot); the skill's "same subagent"/"fresh fix subagent" contradiction is resolved in favour of continuation-first.
- **Rests on:** D10 (wider role-carried tasks), R24 (snapshots citable by feedback/residue).
- **Revisit-when:** snapshots grow stale enough to mislead a dispatch twice → add a freshness stamp + verify-commands rerun before pasting.
- **Open from this round (not yet ruled):** flip Codex to preferred implementer for broad arcs? · review cadence per plan checkpoint with mid-arc continuation fixes?

## D32 — Resume beats snapshot: track resume metadata, not snapshot files (supersedes D31's artifact)
**When:** 2026-08-25T06:21:11Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Decided:** if a subagent can be resumed, its own session **is** the memory — no snapshot artifact. Both worker kinds store sessions (Codex: named worker sessions continued via `codex-worker run --name`; Claude subagents: addressable via SendMessage while the parent lives, session persisted on disk). So SDD keeps a **resume registry** instead: every subagent's report carries a mandatory **RESUME metadata block** — worker kind · name/agent-id · the exact resume command or SendMessage address · session/instance ref · territory one-liner — and the controller tracks it in the progress ledger. Fixes and re-entries into a territory go to the resumed agent, carrying only the new findings. The report file remains the fallback reground source if a resume ever fails; no separate snapshot files. D31's registry idea survives as this resume registry; its snapshot artifact is superseded.
- **Codex:** NOT the default implementer, but **recognized as first-class** — the worker-class table names it plainly beside native Claude; no "explicit opt-in only" framing.
- **Review cadence: longer.** Produce more code before reviewing — reviews move to plan checkpoints or per-deliverable, never per-mini-task; frequent small reviews cost more than they catch. Mid-arc findings go to the resumed implementer.
- **Revisit-when:** a resume fails twice on real work → reconsider a lightweight snapshot for cross-session territory handoffs.

## D33 — Ratification by delegation (operator: "I'm not going to read those docs, so I trust you")
**When:** 2026-08-25T06:26:41Z · **Phase:** spec · **Status:** locked · **Decided by:** Tadas (delegated), Claude (rulings)
- **D24 ratified:** §5.4's milestone law lands in superdev's `orchestrator`; room-graph's stays generic.
- **D30 ratified:** operator-absent charters self-brainstorm to the ratification gate and wait as a desk DECIDE — the one exception to "always merges".
- **Naming pairs ratified:** residue/residual and system-angle/item-angle both stay, distinguished in the glossary.
- Condition: a final cold-read subagent review over spec + log + angles passes; any blocking finding reopens the relevant D#.

## D34 — Plan-phase forks (wave 1)
**When:** 2026-08-25T06:30:13Z · **Phase:** plan · **Status:** locked · **Decided by:** Claude
- **No separate command file:** `/superdev:self-improvement` already invokes the skill by name; the "command" (R24) is the skill's new **inbox mode** (detects/accepts a process-feedback ledger argument). A thin alias skill was rejected — one more description in every prompt for zero capability.
- **writing-skills discipline per edit task:** each skill-edit task carries its own baseline→edit→verify cycle inside the task, not as a separate testing milestone.
- **Wave-1 AH subset:** organisation-level hints (AH2–AH8, AH11–AH15, AH17–AH19) need live rooms and land at rollout in the calibration project; this plan receipts AH1, AH9, AH16 (simulated session), AH10 (per-edit discipline).

## D35 — Execution shape agreed: variant A (inline, 5 broad tasks)
**When:** 2026-08-25T06:32:48Z · **Phase:** plan · **Status:** locked · **Decided by:** Tadas ("A")
- Per D29 this agreement is the flip: execution auto-starts once the plan reviewer's findings are folded. Inline in the authoring session; reviewer subagents at milestone gates; baseline/compliance subagents per edit.

## Wave-1 build closure — 2026-08-25T06:44:39Z
**Phase:** build. Shipped: superdev 7.4.0 (system-design skill + 7 skill edits) · room-graph-orchestration 2.3.0 (dev-organisation template, GREEN-LIGHT/CORRECTION events, residue conventions), both installed. All five tasks baseline→edit→GREEN per AH10. Receipts: AH1, AH9 (minus SDD, deferred), AH10, AH16 (simulated). **Rollout-owned (human-in-loop, named per Mode):** AH2–AH8, AH11–AH15, AH17–AH19 — live receipts come from adopting the organisation in ai-trading-calibration (A5). **Wave 2 gate:** the R22 item-room deep-dive (role-split SDD, test clearance, execution-shape elicitation, parallel-execution rename). Deviations: none against the plan beyond reviewer-folded items; one bonus (CORRECTION event added to protocol.md — a pre-existing gap the Task-5 baseline exposed).

## D36 — Long tasks are the norm; Codex excels at long runs and session resume
**When:** 2026-08-25T07:04:26Z · **Phase:** brainstorm (R22 deep-dive) · **Status:** locked · **Decided by:** Tadas
- Whether Codex or Claude subagent, **task length increases** — broad arcs are the default shape. For Codex specifically: emphasise that a worker can run very long and do a lot of work, and that **resuming the same session beats starting new ones** — long-run + resume is where Codex is strongest. This closes D31's open question: no blanket "Codex default", but wave-2 SDD text must present Codex as the long-arc powerhouse and resume-first as its idiom.

## D37 — Parallelism: one deep initial write; parallel only for reads and later quick-fix phases
**When:** 2026-08-25T07:04:26Z · **Phase:** brainstorm (R22) · **Status:** locked · **Decided by:** Tadas
- Everything lands in a single worktree, so parallel WRITES conflict. Ruling: the **initial implementation is one effortful, thinking, non-parallel arc** (one carrying implementer). Parallel is fine for **reads** (grounding, review, census) always — and for **later phases in the same worktree**: quick fixes, detail work, failing-test cleanup after the shape exists. Never parallel broad implementation. The parallel-execution doc's rename (wave 2) also inherits this: lanes are for the quick-fix phase, not for initial arcs.
- **Revisit-when:** two quick-fix lanes conflict in the same files twice → per-file lane locks, still no parallel initial arcs.

## D38 — Red-green splits by role: implementer keeps the inner loop; the reviewer is the test adversary
**When:** 2026-08-25T07:12:21Z · **Phase:** brainstorm (R22) · **Status:** locked · **Decided by:** Tadas ("c")
- Inside a broad arc the **implementer** keeps TDD's inner red-green loop (mechanical coverage, per slice, in-context; checkpoint receipts carry RED/GREEN evidence). The **reviewer** owns the oracle role: at each plan checkpoint it writes or commissions **adversarial tests** against the arc's claims; **every guard is observed to fail before the checkpoint clears** — watched-to-fail is the reviewer's duty, not the implementer's ritual. In harvest-delete-rewrite territory the reviewer authors the requirement tests **from the harvest file**, checking against the vision, never against the code. Reviewer test-writing is the sanctioned small parallel write of D37's quick-fix class.
- **Archive sweep ownership (closing the D16 gap):** the sweep is the implementer's FIRST plan checkpoint; the reviewer signs off the harvest file **before** anything is archived; post-development cleanup (delete archived tests, keep manifest) is a close-gate item.
- Alternatives: A same-mind red-green scaled (inert-guard bias scales with the arc — the 17-inert-guard evidence) · B full test-author split (re-introduces write fan-out; interface guessing). Revisit-when: reviewer-authored guards themselves go inert twice → rotate the adversary seat.
- **R22 deep-dive complete:** all seven questions ruled (D36, D37, D38 + prior D27/D28/D32). **D10 and D16 move provisional → ratified** with these mechanics.

## D39 — Wave-2 execution shape agreed: variant A (inline, 3 broad tasks)
**When:** 2026-08-25T07:24:02Z · **Phase:** plan · **Status:** locked · **Decided by:** Tadas ("A")
- Inline in the authoring session; tasks: (1) SDD rewrite (role-split, broad arcs, resume registry, Codex long-run emphasis, parallel-execution rename per D37) · (2) TDD (clearance mechanics, reviewer-adversary seam) · (3) writing-plans execution-shape elicitation + brainstorming test-disposition. Baseline→edit→GREEN per task; one release (superdev 7.5.0) with receipts. Auto-start on plan-reviewer fold, per D29/D35 precedent.

## D40 — Wave-2 plan forks (from the plan review)
**When:** 2026-08-25T07:30:27Z · **Phase:** plan · **Status:** locked · **Decided by:** Claude
- `Execution: subagent-driven-parallel` **retired** as a plan mode: parallelism is a *phase inside an arc* (D37), not a plan shape; enum becomes `subagent-driven | inline`; parallel-execution.md is rewritten from that premise (quick-fix lanes, same worktree, reads always).
- **No separate resume registry file**: RESUME metadata rows live in the SDD progress ledger (D32's "tracked in the progress ledger" upheld).
- The same-subagent/fix-subagent contradiction resolves **continuation-first** (D32): message the original implementer; fresh dispatch + report only when resume fails.

## Wave-2 build closure — 2026-08-25T07:34:37Z
**Phase:** build. Shipped superdev 7.5.0: SDD arc model (D32/D36–D38/D40), parallel-execution rewritten (D37; `subagent-driven-parallel` retired), test-clearance.md (D16/D38), execution-shape elicitation + auto-start (D27–D29), brainstorm disposition (6b/§7b), glossary additions. All three tasks baseline→edit→GREEN (a6bf6/abbd5); plan-review errata folded; AH9 completes (SDD sweep clean), AH8/AH17/AH19 skill-text halves receipted. Remaining live receipts (AH2–AH8-live, AH11–AH15, AH16-live, AH17–AH19-live) land at rollout in ai-trading-calibration. The system-design layer is now FULLY SHIPPED at skill level: waves 1+2 complete, D1–D40.

## D41 — Bootstrap lives in superdev, standalone and conversational
**When:** 2026-08-25T07:57:10Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- The dev-organisation bootstrap is a **superdev skill**, standalone — superdev must carry no loose links to room-graph-orchestration (cross-check ordered; fix any found). **Not deterministic**: a target project may already have conventions (doc layout, ledgers, test structure) that must be **bridged, adopted, or discarded** — a scaffold script can't judge that, so the bootstrap is conversational: survey what exists, propose a mapping per convention, operator rules, then create the floor accordingly. Rejected: (a) room-graph as home (superdev standalone-ness wins), (c) scaffold plugin (overkill).
- Milestone entry protocol confirmed as designed: seed corpus (session) → HIL co-plan with the orchestrator → charters; milestone→milestone via the handoff; backlog feeds only the boundary conversation.

## Bootstrap closure — 2026-08-25T07:59:25Z
**Phase:** build. D41 delivered: `bootstrapping-dev-organisation` shipped in superdev 7.6.0 (baseline a0ace → skill → GREEN a2e26, verbatim on all six probes). Cross-check clean: no superdev→room-graph links (glossary header made self-contained). The organisation is now fully deployable from zero: bootstrap → seed → launch → charter → handoff.

## D42 — Operational scenarios are INTENT documents; no replayable scripts
**When:** 2026-08-25T08:11:49Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **Trigger:** code+unit-test validation misses operator-experience discrepancies (naming, missing output detail); only live step-by-step CLI rides with reasoning about output catch them; captured scenarios must accumulate into an operational suite.
- **Decided:** a captured scenario is an **intent document** — operator goal · journey at intent level · what-good-looks-like criteria — never a replayable script. Deterministic scripts fail on every intentional improvement and miss experience regressions; non-deterministic execution (an executor re-deriving commands each run) finds more gaps and stays focused on user experience. A replayable script may later be *derived from* an intent doc if ever needed; the artifact of record is the intent. Rejected: A (recorded scripts), C (script-as-attachment — even as attachment it anchors the wrong thing; the PASS transcript remains committed as checkride *evidence*, but it is not part of the scenario).
- **Revisit-when:** a known-fragile path needs exact replay twice → derive a script from its intent doc, marked as derived.

## D43 — Scenario foundation only: date-stamped capture at item close; refinement deferred to a later room
**When:** 2026-08-25T08:15:15Z · **Phase:** brainstorm · **Status:** locked · **Decided by:** Tadas
- **No merging, refining, or composing now.** The foundation is exactly: after an item's worktree merges, a **date-stamped scenario intent artifact exists** for the surfaces it changed — `design/scenarios/<YYYY-MM-DD>-<item>-<slug>.md`, append-only, no INDEX curation, no architect sweep obligation. Distilled from the checkride's ride+findings as its final step; a close-gate line verifies it exists. At **milestone close** the accumulated scenarios are reusable (the battery — an ad-hoc room walking the intents; report rides the handoff). Refinement/merge/composition belongs to **some other room, later** — deliberately out of scope. Evaluator observations (non-blocking, experience-class) auto-file as backlog rows — the manual observation→backlog loop made mechanical.
- **Revisit-when:** the scenarios directory passes ~30 files or two batteries trip over duplicates → charter the refinement room.

## Scenario-foundation closure — 2026-08-25T08:16:35Z
**Phase:** build. D42/D43 shipped in superdev 7.7.0 (baseline a2dc7 → edits → GREEN a70f6, verbatim: intent-only, append-only, observations→backlog, battery at milestone close riding the handoff). Deferred by design: scenario refinement/merge room (revisit at ~30 files or two duplicate-tripped batteries).
