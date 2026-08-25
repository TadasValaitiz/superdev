# The system-design layer — superdev × orchestrator development organisation (anchor)

**Date:** 2026-08-25 · **Status:** draft
**Mode:** human-in-loop
**Decision log:** ./2026-08-24-system-design-layer-decisions.md (D1–D30; the arbitration surface is the addendum **plus each entry's own revisit-when**)
**Companions:** `../design/design.html` (v3 diagrams; sources `reporting.mmd`, `lifecycle.mmd`) · evidence base (pinned): `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/docs/superpowers/specs/2026-08-21-orchestrator-handoff-state.md`, `…/docs/reference/2026-08-21-orchestrator-process-feedback.md`, and the bench-architecture worktree `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.claude/worktrees/bench-architecture` @ `0c88eaa7` (12-angle series, 4 seat reports, angle-08 map)
**Origin:** brainstorm with Tadas

## 1. Problem & intent   [ANCHOR]

Superdev was written incrementally, before cross-session rooms existed. Its pipeline — brainstorm → spec → plan → subagent-driven build — assumes a *new feature* with a fresh spec each time, decision logs scoped per work stream, and no one to notify. It works, but the ai-trading-calibration milestone showed where it breaks on a codebase undergoing a **huge domain shift**:

- There is no **system-design level** above task brainstorms. Holistic design (the 12 bench angles, the current→target map, operator-ruled laws) had to be done by hand with Codex, outside the flow; without that manual work, design decisions get skipped, components duplicated, and migrations silently dropped (operator's words).
- Design was **fire-and-forget**: each brainstorm started cold; nothing preserved the architect's context between sessions; build-time insights landed as plan deviations and never steered the next design.
- Refactoring/legacy work is under-supported: grounding always happens on the legacy code, so once a migration is agreed, future design sessions have nothing sound to ground on; the D202 ceremony burned a session on a framing the operator dissolved in a sentence.
- The **test mass** (5000+ tests, re-pin waves, ~17 inert guards) makes drastic change expensive; there is no sanctioned path to harvest-and-delete.
- Coordination pain: everything-is-a-room cold starts, dead worktrees (~30), transport that loses messages, cursors that grow to 2415 lines.

The intent: a development **organisation** — rooms with contracts — in which two levels of knowledge work are explicit and separated: **L1 system design and big-picture understanding** (boundless, holistic, human-driven) and **L2 task-focused execution** (bounded, continuous, never waiting on design). Files are the law; messages are pointers. The code is pre-production: drastic moves are sanctioned; there is no production-grade migration ceremony.

Success looks like: the operator never has to manually police design conformance; development merges continuously while the architecture advances in ruled batches; a design session opens with a greppable agenda instead of a cold read; a milestone cannot close without its handoff to the next one; and the whole vocabulary — milestone, item, checkpoint, bridge, handoff, residue, marker, vision, angle — means the same thing in every skill.

## 2. Requirements   [ANCHOR]

| ID | Requirement | Source | Priority | Acceptance signal |
|----|-------------|--------|----------|-------------------|
| R1 | Design authority lives in a **corpus** of files (angles · current→target map · design D# log · visions), binding solo and orchestrated alike | D1 | must | briefs and brainstorms cite corpus paths; no design authority exists only in a session |
| R2 | A persistent **ARCHITECT room** owns the corpus and preserves context across milestones; system design is never fire-and-forget | D1 | must | the same room hosts successive design sessions; its context survives between them |
| R3 | System design is **human-driven**: no self-driven design; the architect idles between checkpoints unless messaged; works ahead only with the operator attached | D18 | must | architect brief forbids proactive work; sessions require the operator |
| R4 | When an architecture gap blocks the next charter and the operator is unavailable, the **orchestrator pauses chartering** — scoped to the charters that need the missing ruling; **already-chartered rooms always run to merge** (R8 is never violated by a pause); "full stop" means no further charters when the gap sits on a bridge every remaining charter crosses | D18, D21 | must | pause events name the missing ruling and the charters withheld; no live room is stopped by a design-dry pause. One named exception to "always run to merge": a room chartered with the operator away waits at its self-brainstorming **ratification gate** as a desk DECIDE (D30) |
| R5 | The **milestone is the implementation boundary** and the orchestrator's whole world; it may discuss boundary adjustments but is biased to contain | D11 | must | orchestrator brief; charters never exceed the milestone without an operator ruling |
| R6 | A milestone closes only with its **handoff**: architectural suggestions from what was built + upfront design (visions included) for the next milestone | D11, D15 | must | milestone close blocked on a handoff document |
| R7 | **Item rooms own their worktrees end to end** — create, work, FF-CAS merge, retire; a room may not close with an unmerged or surviving worktree (the **close gate**, orchestrator-verified) | D7 | must | close protocol checks `git worktree list`; no dead worktrees accumulate |
| R8 | Item rooms **always finish and merge**; architecture issues discovered mid-build are resolved locally and deferred via markers — nothing blocks publish for architectural reasons | D3 | must | no publish gate involves the architect; conformance reports are advisory and forward-acting |
| R9 | **Two greppable marker families**: `MIG-MARK[CLASS][D#]` in code (classes RESHAPE·REPLACE·SEAM·TEST, closed; removed with the fix, never resolved in place) and `DOC-MARK[STATUS][ref]` in the corpus (LOCKED·FLEXIBLE·DEFERRED·BLIND·MISMATCH) | D14 | must | census = grep; marker progress = count trend; session opens from BLIND/MISMATCH grep |
| R10 | **Residue** flows one way: any room appends rows (ID-blocked ledger) → orchestrator collects continuously → at a **checkpoint** hands the architect a clustered collection; the architect never works at individual-residual level | D8, D19 | must | residue ledger + checkpoint handover docs exist; no architect action between checkpoints |
| R11 | Checkpoints are declared from **rule + green lights + feel**: bridge-side merges/milestone close/operator ask · rooms signalling "nothing more to contribute" · orchestrator judgment | D19 | must | checkpoint doc records all three inputs |
| R12 | The **checkpoint handover** is a designed two-way protocol: *what we got · where we feel gaps · upcoming focus* + explicit agree/disagree, with the architect entitled to bounce tactical clusters back down | D20, D5 | must | handover + response documents follow the format; bounced clusters return to items |
| R13 | Strict **altitude split**: the architect never solves tactical problems (item rooms know the present best; the architect may only know the future better); item rooms never resolve L1 design forks locally — they file residue | D5 | must | briefs on both sides; drift protocol routes L1 forks to residue, not local spec edits |
| R14 | **Vision documents**: a REPLACE/RESHAPE cluster above threshold is not ruled until its post-migration vision exists; future sessions ground on the vision, not legacy code, wherever the map says the code will change | D12 | must | visions/ populated before big rulings; session protocol names grounding source per area |
| R15 | The **angle system**: numbered series in `design/angles/` with INDEX.md; per-angle contract (Purpose · Formal anchors · Series · DOC-MARKs); five kinds (policy/semantics, algebra, journey, boundary, map) plus Pydantic invariant sketches (FLEXIBLE) and functional-core/imperative-shell pseudo-code; anti-loosening: end-of-session angle sweep, mechanical staleness check (angle D#s vs log status), new-angle trigger for unplaceable residue | D23, D17 | must | INDEX current; no angle cites a superseded D# without an agenda entry |
| R16 | One **shared glossary** across all skills, including the residue/residual distinction: corpus/angle/vision/design-session · residue/marker/backlog · milestone/item/checkpoint/task; **bridge** (dependency seam), **handoff** (milestone close package); "phase" (as a work-unit name; the decision-log lifecycle field keeps it), "stage", "joint", "runway", "docket" retired; writing-plans' internal "Milestone Mn" renamed to **plan checkpoints**. Disambiguation rule: a **plan checkpoint** (`## Checkpoint Cn` inside an item's plan) is room-internal — it never notifies the architect; only an orchestrator-declared **design checkpoint** fires the handover protocol | D15, D13 | must | grep across skills finds one vocabulary; no plan checkpoint triggers a handover |
| R17 | **Front desk required**: view-only queue of events from every room, with a DESIGN column (handovers awaiting a session, ticking design-dry pauses) and merge/green-light events; conversations happen in the room that needs the operator, never at the desk | D4 | must | desk brief; operator reads one file |
| R18 | Orchestrator may charter **ad-hoc rooms** (probe, spike, sweep) with foreign skill mixes, keeping them out of the architect room; it never executes work itself — no micro-task tier; small work is absorbed into item rooms | D9, D22 | must | orchestrator brief |
| R19 | **The probe gate**: no item room chartered without a measured census; the probe result is filed | feedback §3, D11 | must | charter template requires the probe reference |
| R20 | **Test clearance** is an explicit disposition at every item brainstorm — one vocabulary: {keep · regenerate · archive-then-rewrite (harvest business requirements → archive → rewrite against the vision) · fix-in-place}; the plan refines mechanics only; `MIG-MARK[TEST]` carries deferred debt; map rows carry test verdicts | D16 | must | item brainstorm template has a mandatory test-disposition section |
| R21 | **Ledgers are truth; messages are pointers** — every protocol in this design names its ledger and single writer (or ID blocks); no payload travels only in a message | D2 | must | protocol table below; briefs restate it |
| R22 | Item-room internals follow D10's direction: corpus-awareness distinct from brainstorm/plan; SDD tasks wider; split **by role** (implementer · reviewer · follow-up), not by many small tasks — detailed by a follow-on deep-dive under this anchor | D10 | should | deep-dive spec exists before the item-room skill text changes |
| R25 | **Item-level brainstorming writes its own angles** (operator's angle template: central question · boundaries · concrete consequences · visible collisions · reconciled outcome; emergent angles welcome; overlap with system angles expected): session flow = corpus awareness (system passages quoted **with file:line**) → problem-space evaluation → initial questions → angle-by-angle with lettered forks → capture into design doc + item angle companions (beside the spec, never in `design/angles/`) + decision log; §5 areas carry DOC-MARK statuses (incl. SEED-ILLUSTRATIVE); implied variants/post-migration shape demand a vision; cross-boundary finds file residue | D26, D12 | must | a brainstormed spec ships with ≥1 item angle citing system lines; reviewer checks collisions + statuses |
| R28 | **Resume over reground (D32):** every subagent report carries a RESUME metadata block (worker kind · name/id · exact resume command or address · session ref · territory one-liner), tracked in a resume registry; fixes and territory re-entries go to the **resumed agent** carrying only the new findings; the report is the fallback if resume fails; no snapshot artifacts. Codex is first-class beside native Claude (not default, never opt-in-buried). Review cadence is **long**: reviews at plan checkpoints or per-deliverable, never per-mini-task | D31, D32 | must | a fix lands via resume with zero re-derivation; the registry names how to resume every live-territory agent; no per-mini-task reviews in a broad-arc plan |
| R27 | **The operator's item arc (D29):** brainstorm (HIL) → writing-plans → agree the execution shape → **step out**; execution auto-starts on that agreement with no further proceed-prompts; the operator returns only via the desk (DECIDE, checkride, or by choice) | D29 | must | after shape agreement, the next operator touchpoint is a desk item, not a permission prompt |
| R26 | **Plans are operational documents**: an **execution-shape proposal** (2–3 variants: task/deliverable counts, worker class, subagents/rooms, recommendation — always, even one-variant for small plans) precedes task writing; granularity dials to worker class (bite-size Sonnet ↔ broad role-carried Codex with plan checkpoints); an **Operational strategy** section that *refines* the brainstorm's test disposition into mechanics — the brainstorm decides {keep · regenerate · archive-then-rewrite · fix-in-place}; the plan may narrow, never reverse — with the archive lifecycle (sweep → `tests/_archived/<plan>/` + manifest + harvest file, recallable during development → post-development cleanup deletes archived tests, manifest kept); grounding adds map rows, visions and item angles with line refs; a **marker plan** states MIG-MARKs removed/planted and map rows discharged, with marker delta in gate receipts | D27, D28, D10 | must | plan header shows the chosen variant; archived tests carry manifest + harvest; gate receipts show marker delta |
| R24 | **Continuous process improvement, two speeds (D25):** the orchestrator captures process feedback (rooms append in ID blocks; measured facts — wall-clock, review cycles, wait time, tokens — are the orchestrator's, never self-graded) and adapts new briefs immediately; a `/superdev:improve` command batches the ledger into the `self-improvement` skill (inbox mode) for operator-gated, version-bumped skill edits | D25 | must | ledger exists; a flagged gap changes the next brief; improve run produces an approved edit |
| R23 | Everything ships as **updates to the existing plugins** — new `system-design` skill + edits in superdev; architect/front-desk/checkpoint support in room-graph-orchestration — no new plugin, no fork | D6 | must | changes land in both repos, version-bumped |

## 3. Use cases   [ANCHOR]

| UC | As the operator, I … and see … | Exercises | Realized by |
|----|-------------------------------|-----------|-------------|
| UC1 | run `/system-design` solo in any project and get a grounded, census-first session that writes angles, map rows, visions and D#s into the canonical corpus layout | R1, R14, R15 | 5.1, 5.2 |
| UC2 | attach to the ARCHITECT room whenever I have time and energy, find its context intact from last time, and architect ahead (visions, BLIND angles) with it | R2, R3 | 5.3 |
| UC3 | watch development continue while design lags: item rooms finish and merge, planting `MIG-MARK`s where the clean fix is deferred, and nothing waits on the architect | R8, R9 | 5.5 |
| UC4 | see the orchestrator pause exactly the items that need a missing ruling when I'm away, with the desk showing me what my absence is costing | R4, R17 | 5.4, 5.7 |
| UC5 | at a checkpoint, read one handover document (got / gaps / focus), see the architect's agree/disagree, attach for the session, and rule lettered forks over a grep-built agenda | R10, R11, R12 | 5.4, 5.3 |
| UC6 | track migration progress mechanically: `grep -rc MIG-MARK src/` trending down, map rows discharged per item, DOC-MARK[BLIND] count shrinking | R9, R15 | 5.2, 5.6 |
| UC7 | close a milestone and receive its handoff: what was built, what it suggests architecturally, and the next milestone's upfront design already drafted | R6 | 5.3, 5.4 |
| UC8 | charter an item and see its brief cite the map rows it discharges, its test disposition, and its grounding probe — and at close, its worktree merged and gone | R7, R19, R20 | 5.5, 5.4 |
| UC11 | I brainstorm an item, agree its execution shape, walk out — and the room is already building when I next look at the desk | R27, R26 | 5.5 |
| UC9 | when an item hits an arch-vs-code discrepancy, see it resolved in the room, a residue row filed, and the corpus improved at the next session — never a stalled room, never the architect doing tactics | R13 | 5.5, 5.3 |
| UC10 | find every one of these words meaning the same thing in every skill I open | R16 | 5.8 |

## 4. Approach narrative

The organising idea is one split, applied twice. The split is **future vs present** (D5): the ARCHITECT holds the future (boundless, holistic, ruled by the operator), item rooms hold the present (bounded, continuous, always merging). Applied to *work*, it yields the two levels of knowledge work (D1) and the rule that nothing in the present waits on the future — discrepancies resolve locally and travel upward as residue and markers (D3, D8), while the future reaches the present only through charters derived from a ruled corpus (D11, R19). Applied to *time*, it yields the checkpoint rhythm (D19): the present runs continuously; the future advances in batches, when the orchestrator judges — by rule, green lights and feel — that the present has produced enough to think about.

Everything else is machinery keeping that split honest. The **corpus** (5.1–5.2) makes the future a set of files anyone can ground on, with **visions** solving the poisoned-grounding problem — once the map says code will change, the vision is the truth to design against, not the legacy (D12). The **marker families** (5.6) make deferred architecture and unexamined design mechanically countable, so "how far along is the migration" is a grep, not a meeting. The **rooms** (5.3–5.5, 5.7) give each altitude an owner with the right lifetime: persistent where context accumulates (architect, orchestrator, desk), ephemeral where it must not (items). The **protocols** (5.4) — residue ledger, checkpoint handover, milestone handoff — are the only traffic between altitudes, each a ledger with a single writer and a pointer message (D2, R21). The **glossary** (5.8) makes the whole thing speakable in every skill, and the **skill-edit map** (5.9) lands it in the two existing plugins without a fork (D6).

## 5. Design

### 5.1 The corpus — canonical layout, per-project extensible

The file form of design authority (R1); everything else cites it.

- **Design:** canonical floor, projects may add kinds freely (D17):
  ```
  design/
  ├─ angles/        NN-<slug>.md numbered series + INDEX.md (number · purpose · anchors · last-updated · DOC-MARK counts)
  ├─ visions/       <area>.md — post-migration domain documents (D12; default rule: any REPLACE **or RESHAPE** cluster spanning >1 module needs one before its ruling)
  ├─ map.md         current→target map (row grammar in 5.2)
  ├─ decisions.md   design D# log — architect single-writer; supersede, never erase
  ├─ residue/residue.jsonl        append-only; any room, own ID block (5.10)
  ├─ residue-collections/         <date>-checkpoint-<n>.md + -response.md (protocol in 5.4)
  ├─ conformance/<item>.md        architect's advisory reports (5.10)
  ├─ handoffs/<milestone>.md      milestone handoff (5.10)
  └─ marker-census.md             generated; never hand-edited (5.10)
  ```
  The floor includes every ledger §5.10 names — the scaffold and the protocols cannot disagree. "Architect-only" writers mean the architect **role**: the solo `/system-design` skill and the ARCHITECT room are the same authority in one or many sessions.
- **Interface:** grep-stable names; briefs cite `design/…` paths; the solo skill and the architect room write the same shape.
- **Serves:** R1, R14 · **Governed by:** D1, D12, D17 · **Realizes:** UC1, UC2

### 5.2 The map and the angle system

The two artifact kinds that make design *checkable* rather than aspirational.

- **Map row grammar** (from bench angle-08, extended): `| id | code area | verdict KEEP/RESHAPE/REPLACE/DEFER | test verdict keep/regenerate/harvest-delete-rewrite | MIG-MARK refs | DOC-MARK status | discharging item | D# anchors |`. Charters cite rows; conformance reports and marker census reference them; a row nobody discharges is visible debt.
- **Angle contract** (D23): five kinds — policy/semantics · algebra · journey · boundary · map — each with Purpose (reader-oriented: "understandable without reading the engine") · Formal anchors (D#s + glossary; angles are prose over rulings, never decision owners) · Series position · DOC-MARKs. Content may include Pydantic invariant sketches (FLEXIBLE by default — responsibilities and invariants, never final field names) and functional-core/imperative-shell pseudo-code journeys. Angles overlap deliberately; overlap is where contradictions surface.
- **Anti-loosening:** end-of-session **angle sweep** (touched anchors ⇒ angle updated in-session); staleness check = grep an angle's cited D#s against the log's statuses; residue fitting no angle ⇒ new angle.
- **Interface / contract:** map rows and angle files are citable by stable ids (`M<n>`, `angles/NN-<slug>.md`); charters, conformance reports and agendas reference them and nothing else.
- **Serves:** R9 (doc half), R15 · **Governed by:** D14, D23 · **Realizes:** UC1, UC6

### 5.3 ARCHITECT room — the future

The persistent holder of the corpus and of nothing else.

- **Design:** runs the `system-design` skill continuously as a room. Between checkpoints: **idle** unless messaged (messages land in ledgers regardless; no proactive polling — D18). With the operator attached: sessions (census-first, lettered forks, grep-opened agenda: `DOC-MARK[BLIND|MISMATCH]`, marker census, residue clusters by angle) and ahead-of-need work (vision drafting, BLIND angles) — always human-driven. Per checkpoint: consumes the handover collection, answers agree/disagree, may bounce tactical clusters down (D5), prepares the agenda. Writes advisory conformance reports **at the checkpoint session**, over the diffs published since the last one (never blocking — D3; charters issued between checkpoints get none — R3/D8 leave no earlier moment). At milestone close: co-produces the **handoff** (suggestions + next milestone's upfront design). Never: tactical problem-solving, code, blocking anything, knowing the codebase better than the room in it.
- **Interface:** corpus (5.1) · checkpoint responses · conformance reports · handoff (with orchestrator).
- **Serves:** R2, R3, R6, R13, R14 · **Governed by:** D1, D3, D5, D12, D18 · **Realizes:** UC2, UC5, UC7, UC9

### 5.4 ORCHESTRATOR room — the milestone

The bounded world-keeper: charters, collects, checkpoints, pauses, closes.

- **Design:** its whole job is the current milestone (D11): grounding probe → charter (cites map rows, test disposition, bridges — the probe gate, R19); collects residue continuously and routes pointers; watches for checkpoint conditions (rule + green lights + feel — D19) and writes the **handover** (`what we got` facts: merges, map rows discharged, marker delta, deduped clusters · `where we feel gaps` labelled as feel, by angle · `upcoming focus` with blocking flags · green-light roster); receives the response; schedules the session via the desk. **Process feedback (D25):** it captures process observations continuously — its own, rooms' R5 lines, and measured facts (charter→merge wall-clock, review cycles, blocked-wait, token sums from session JSONLs) — into the process-feedback ledger, and **adapts every new charter's brief** from the accumulated feedback (fast loop, its own surface, an O-log line per change). It never self-edits skills. Owns the **design-dry pause** (D18/D21): it withholds *charters*, never stops live rooms — chartered items run to merge (D3); scoped to the charters needing the missing ruling, and "full stop" = no further charters when the gap sits on a bridge every remaining charter crosses. Verifies at room close that the worktree is merged and retired (the close gate). May charter ad-hoc rooms (D9); never executes work, no micro tier (D22); disposes measurement-closed items — the operator sees only genuine forks. Closes the milestone only with the handoff done (R6). Map-row **discharge** is two-step: the orchestrator *claims* it in the handover's "what we got"; the architect *writes* it into `map.md` at the session — the map keeps one writer.
- **The gate ladder** (named, not numbered — the only gates in this organisation): **the ruling gate** (operator approval: angle/map/vision changes bind only when ruled — R3); **the probe gate** (veto: no *item* charter without a grounding census — R19; ad-hoc probe rooms are exempt, being how censuses get made); **the publish recipe** (mechanical FF-CAS script; never blocks for architectural reasons — R8); **the close gate** (veto: a room may not close until its worktree is merged and retired **and its archived tests are deleted with the manifest retained** — R7/R26). Each is enforced outside the node it binds; each has been watched to fail before adoption.
- **Interface:** cursor · residue ledger (collector/router) · checkpoint handovers · charters · pause/green-light events to the desk.
- **Serves:** R4, R5, R10, R11, R12, R18, R19 · **Governed by:** D8, D9, D11, D19–D22 · **Realizes:** UC4, UC5, UC7, UC8

### 5.5 ITEM ROOM — the present

The only place code changes; bounded, finishing, honest about what it deferred.

- **Design:** the operator's arc inside the room is fixed (D29): brainstorm → plan → execution-shape **agreement — the trigger and the mode flip**: the room is HIL from brainstorm through agreement, autonomous after; execution auto-starts on the agreement whether or not the operator stays to watch (writing-plans hands off; subagent-driven-development auto-enters). Chartered with the operator away → `self-brainstorming` to its ratification gate, waiting there as a desk DECIDE (D30). Plan checkpoints are cleared by the room's reviewer role; only a failed one emits an event. Chartered per item; owns its worktree end to end (create → SDD → FF-CAS merge → retire — D7, the close gate). Reads the corpus at brainstorm (grounds on **visions** where the map says change — D12); resolves arch-vs-code discrepancies **locally** (it knows the present best — D5), planting `MIG-MARK`s where the clean fix belongs to a later pass (D3), filing residue rows for anything design-class (never resolving L1 forks locally — R13). Test disposition per D16 is a mandatory brainstorm output. Always finishes and merges (R8). Internals (role-split implementer/reviewer/follow-up, wider tasks, corpus-awareness vs planning) are D10/D16's follow-on deep-dive (R22) — this design fixes only the room's *contract*.
- **Interface / contract:** in — a charter (map rows, test disposition, probe ref, bridges); out — merged code, removed worktree, MIG-MARKs, residue rows, process-feedback rows, the item spec + item angles + item decision log, the archived-test manifest + harvest file, and an R5 debrief with a green-light line. Nothing else crosses its boundary.
- **Serves:** R7, R8, R13, R20, R22, R25, R26, R27 · **Governed by:** D3, D5, D7, D10, D16, D26–D30 · **Realizes:** UC3, UC8, UC9, UC11

### 5.6 The marker system

Deferred work and unexamined design, made countable.

- **Design:** code — `# MIG-MARK[RESHAPE|REPLACE|SEAM|TEST][D#]: note`; removed with the fix, never resolved in place; new class needs a D#. Docs — `DOC-MARK[LOCKED|FLEXIBLE|DEFERRED|BLIND|MISMATCH][D#|owner]`. Symmetry: every MIG-MARK's D# resolves to a corpus entry; every DOC-MARK[MISMATCH] eventually has a MIG-MARK twin or a residue row saying why not. Census scripts (a few lines of grep) produce: total, per class, per D#, trend; the architect's marker census and the session's opening grep are these scripts, not reading.
- **Interface / contract:** the census script's output format is fixed (totals · per class · per D# · trend); handovers embed it verbatim.
- **Serves:** R9 · **Governed by:** D14 · **Realizes:** UC3, UC6

### 5.7 FRONT DESK room

One queue so the operator's scarcest resource — architecture time — is visibly scheduled.

- **Design:** the proven view-only contract (hedge-graph/room-graph front desk: filter, rank, dedupe, two destinations, never decide) plus: a **DESIGN column** at the top of "waiting on you" — checkpoint handovers awaiting a session, design-dry pauses with their tick-time, D30 ratification DECIDEs — and room lifecycle events in the digest: **execution started** (the AH18 entry), merges, green lights, failed plan checkpoints. Conversations happen in the room that needs the operator; the desk only points.
- **Interface / contract:** renders `frontdesk/digest.md` (its only write, per 5.10) from the queue, cursor and events; never a source of truth.
- **Serves:** R17 · **Governed by:** D4 · **Realizes:** UC4

### 5.8 The glossary

One vocabulary, so every skill and brief says the same thing (full table: D15).

- Boundless: **corpus · angle · vision · design session**. Bridge-state: **residue · marker · backlog** (docket retired). **System angle ≠ item angle** and both stay: a *system angle* lives in `design/angles/` under the five-kind contract and the anti-loosening machinery (INDEX, sweep, staleness grep); an *item angle* lives beside its item's spec under the operator's template (central question · boundaries · consequences · collisions · reconciled outcome) with no INDEX/sweep obligations — overlap between the two is expected (D26). A **gate receipt** is the evidence line a plan checkpoint or the close gate records (tests run, marker delta, map rows claimed). **Residue ≠ residual** and both stay: a *residual* keeps its entrenched meaning — a loose end drained before a room/run closes (residual ledger, RES events); *residue* is a design-class finding flowing up to the architect. The glossary in every edited skill carries this pair side by side; neither is retired. Bounded: **milestone** (was phase) **· item · checkpoint** — two named altitudes, one word: a **plan checkpoint** (`## Checkpoint Cn`, room-internal gate group; never reaches the architect) and a **design checkpoint** (orchestrator-declared, fires the handover; D8's batching applies to these only) **· task** (wider, role-carried) — plus **bridge** (dependency seam between items/domains/CLIs; ordering falls out of contested bridges; was "joint") and **handoff** (milestone close package; was "runway"). Kept: charter, grounding probe/census, checkride, cursor, debrief, gate, room, D#/O#/R#.
- **Interface / contract:** the glossary is one section in the `system-design` skill; every edited skill links it rather than restating it.
- **Serves:** R16 · **Governed by:** D13, D15 · **Realizes:** UC10

### 5.9 Where it lands — the skill-edit map (R23)

The change set, in the two existing plugins.

- **superdev — new skill `system-design`:** the corpus (5.1), map + angle system (5.2, with worked examples per the operator's request), marker grammars (5.6), vision rule, session protocol (census-first + lettered forks + grep-opened agenda + angle sweep), the solo and room invocation modes, glossary.
- **The two-orchestrator resolution (D24, provisional — operator to ratify):** two orchestrator skills exist — superdev's (milestone-altitude rooms, FF-CAS room-mechanics, the one the calibration milestone actually runs on) and room-graph-orchestration's (generic graph running). §5.4's law lands in **superdev's `orchestrator`** — it already owns the milestone close and room mechanics this design extends. room-graph's orchestrator stays generic and unchanged in substance; its `graph-creator` gains the development-organisation shape as a named starting template (architect + desk briefs) pointing at superdev's stack.
- **superdev — edits, wave 1 (not governed by provisional D10/D16):** `orchestrator` (milestone boundary, design checkpoints + handover, design-dry pause, green lights, no micro tier, ad-hoc rooms, close gate, process-feedback capture + brief adaptation per D25); `self-improvement` (inbox mode: consume the process-feedback ledger, cluster, then its existing per-failure method; a `/superdev:improve` command entry); `brainstorming` (R25: corpus awareness with line-cited passages, problem-space evaluation, angle-by-angle flow + item angle companions, DOC-MARK statuses, vision demand; scope note "system-scale design → system-design skill"); `writing-plans` ("Milestone Mn" → "Checkpoint Cn" plan checkpoints; charter-style Read-first citing map rows); `using-git-worktrees` (retirement half: lifecycle belongs to the room that made it; close = merged + removed); `finishing-a-development-branch` (align its merge/cleanup options with the close gate — the room, not the finisher, retires the worktree); `using-superdev` (glossary pointer).
- **superdev — edits, wave 2 (after the R22 deep-dive ratifies D10/D16):** `subagent-driven-development` (role-split: implementer · reviewer · follow-up; wider tasks; design-class deviations file residue); `writing-plans` (R26: execution-shape proposal, granularity dial, Operational strategy + archive lifecycle, marker plan — D10/D16-governed; **hands off to execution on shape agreement**); `subagent-driven-development` additionally **auto-enters on that handoff** — the R27 auto-start and the HIL→autonomous flip live in these two skills' seam — and gains R28: the RESUME metadata contract + registry, resume-first fixes, long review cadence (checkpoint/deliverable), and the worker-class table with Codex first-class (not default — D32); `brainstorming` (mandatory test-disposition section); `test-driven-development` (test-clearance protocol, archive lifecycle mechanics).
- **room-graph-orchestration — edits:** `graph-creator` (the development-organisation shape as a named starting template; architect/desk brief variants); `room-communication` (green-light event; residue-row convention; residue/residual glossary pair). Its `orchestrator` skill: substance unchanged (D24).
- Sequencing: `system-design` skill first (everything cites it) → wave 1 (superdev orchestrator + non-item skills; room-graph `graph-creator` template **and `room-communication`** — its green-light event is a checkpoint input) → **item-room deep-dive (R22)** → wave 2 (the D10/D16-governed skills). Every edit under writing-skills discipline (baseline failure observed → edit → re-test). The implementation plan slices this by repo and wave; this section fixes only the change set and the ordering constraint.
- **Serves:** R23 · **Governed by:** D6, D24 · **Realizes:** all UCs (delivery)

### 5.10 The protocol table — every ledger, one writer

The mechanical form of "ledgers are truth; messages are pointers" (R21): every cross-room protocol in this design, its ledger, and who may write it.

| Protocol | Ledger path | Writer | Message |
|---|---|---|---|
| design authority | `design/angles/` · `design/visions/` · `design/map.md` · `design/decisions.md` | ARCHITECT only | pointer on change |
| residue | `design/residue/residue.jsonl` (append-only) | any room, own ID block; orchestrator owns disposition column | pointer per row |
| design-checkpoint handover | `design/residue-collections/<date>-checkpoint-<n>.md` | ORCHESTRATOR | pointer to architect |
| checkpoint response + agenda | `…-checkpoint-<n>-response.md` | ARCHITECT | pointer back |
| conformance report | `design/conformance/<item>.md` | ARCHITECT | pointer to orchestrator (advisory) |
| milestone handoff | `design/handoffs/<milestone>.md` | ORCHESTRATOR + ARCHITECT (two sections, one writer each) | pointer to operator via desk |
| cursor · charters · pause events | `orchestration/…` | ORCHESTRATOR | events to desk |
| room lifecycle (execution started · green light · failed plan checkpoint) | room's reports + cursor rows | room says; orchestrator records | events to desk |
| desk queue | `frontdesk/digest.md` | FRONT DESK | — (it IS the view) |
| marker census | generated `design/marker-census.md` | script (either room may run; output overwritten, never hand-edited) | attached to handovers |
| process feedback | `orchestration/process-feedback.jsonl` (append-only) | any room, own ID block; ORCHESTRATOR owns measured-facts rows and disposition | pointer per entry; consumed by `/superdev:improve` |

No payload travels only in a message; when a message and its ledger disagree, the ledger wins.

- **Serves:** R21 · **Governed by:** D2 · **Realizes:** UC5, UC6

## 6. Decisions (distilled; full trail in the log)

D1 corpus is law + persistent human-driven architect · D2 ledgers truth/messages pointers · D3 no publish gate; markers + forward conformance · D4 front desk required · D5 altitude split future/present · D6 update existing plugins · D7 item room owns worktree+merge · D8 orchestrator collects, architect works per-checkpoint · D9 ad-hoc rooms allowed · D10 item internals: wider tasks, role split (provisional → deep-dive) · D11 milestone = implementation boundary; closes with handoff · D12 vision docs · D13 backlog not docket · D14 MIG-MARK/DOC-MARK grammars · D15 glossary closed (handoff·bridge·checkpoint) · D16 test clearance (provisional → deep-dive) · D17 corpus layout canonical+extensible · D18 architect idles; design human-driven; orchestrator owns design-dry pause · D19 checkpoint = rule+green lights+feel · D20 handover protocol two-way with agree/disagree · D21 scoped pause · D22 no micro tier · D23 angle contract + anti-loosening · D24 (provisional) §5.4 lands in superdev's orchestrator · D25 process-improvement two-speed loop · D26 item angles, corpus cited at line level · D27 operational strategy HIL→protocol · D28 item-angle location, execution-shape proposals, archive lifecycle · D29 operator arc: agree shape → auto-start · D30 (provisional) operator-absent charter waits at ratification. Revisit-when hooks for the load-bearing rulings live in the log's 2026-08-25 addendum; entries recorded before it carry rulings without weighed alternatives — the addendum, not this section, is the arbitration surface.

## 7. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | The role-split item-room internals (one implementer carrying wider tasks + reviewer + follow-up) outperform bite-size task fan-out with current Codex/Sonnet workers | R22, 5.5 | unratified — the deep-dive tests it |
| A2 | The vision-size default (stated in 5.1: **any REPLACE or RESHAPE cluster spanning more than one module needs a vision before ruling**) may need per-project tuning | R14 | default promoted into the design; tuning unratified |
| A3 | Green-light signals are honest enough to weigh into checkpoints — noting that an ephemeral room's green light at close is near-vacuous; weight persistent/ad-hoc room signals higher | R11 | unratified — mitigated by rule+feel inputs; revisit if checkpoints fire early |
| A4 | The angle staleness check (grep D#s vs log status) is implementable as a small script in the skill | R15 | unratified — trivial if D# lines are grep-stable; verified at skill authoring |
| A5 | Existing milestone in ai-trading-calibration can adopt this incrementally (glossary + handover first) without re-chartering live rooms | 5.9 | unratified — operator's call at rollout |
| A6 | Harvest→delete→rewrite is the right default test clearance for REPLACE'd areas (D16 is provisional; R20 rests on it) | R20, 5.5 | unratified — the R22 deep-dive tests it |
| A7 | D24: superdev's orchestrator is the right home for §5.4 (room-graph's stays generic) | 5.9 | unratified — operator to ratify with this spec |
| A8 | D30: self-brainstorm-to-ratification is the right operator-absent behaviour | R4, 5.5 | unratified — operator to ratify with this spec |
| A9 | The Operational-strategy section's HIL phase ends in a protocol extraction (D27); tracked so the extraction happens rather than being remembered | R26 | open — extract after ~3 consistent choices |

## 8. Not doing

- A conformance **veto** on publish — rejected (D3): continuous merging beats blocked worktrees; markers carry the debt.
- Self-driven system design / architect autonomy — rejected (D18): human-driven, always.
- An orchestrator micro-task tier — rejected (D22): small work lives inside items.
- A residuals room, test room, or review room — ledgers wearing sessions; rejected at sizing.
- A new plugin / superdev fork — rejected (D6).
- Production-grade step-by-step migration ceremony — out of scope by the operator's ruling; pre-production allows drastic moves.
- Fixing the cross-session transport itself — mitigated by D2 (files primary) rather than solved here.
- Item-room internals and test-clearance mechanics — deliberately deferred to the R22 deep-dive under this anchor, not skipped.

## 9. Acceptance — hints & receipts   [ANCHOR: the hints]

| # | Acceptance hint (operator terms) | Proves | Lane | Receipt |
|---|----------------------------------|--------|------|---------|
| AH1 | A solo `/system-design` run in a fresh project produces the canonical corpus with at least one angle, a map, and a D# log — and a second session grounds on it without re-deriving | UC1, R1, R15 | slow | |
| AH2 | The architect room survives a milestone: attached twice weeks apart, it resumes with context and its corpus current | UC2, R2 | slow | |
| AH3 | An item room that hits a design discrepancy finishes anyway: marker planted, residue filed, merge completed, worktree gone at close — and the architect's next session folds that residue into the corpus without the architect ever entering the tactical question | UC3, UC8, UC9, R7, R8, R13 | slow | |
| AH4 | With the operator absent and a charter needing an unruled row, exactly the affected charters are withheld (live rooms keep running to merge) and the desk's DESIGN column shows why | UC4, R4, R17 | slow | |
| AH5 | A design checkpoint produces the three-part handover, an agree/disagree response with at least one cluster bounced down, and a session agenda organised by angle — while a plan checkpoint inside an item fires nothing at the architect | UC5, R10–R12 | slow | |
| AH6 | Migration progress is answerable by grep alone: marker totals per class trend, map rows discharged per item | UC6, R9 | fast | |
| AH7 | A milestone close is refused until its handoff (suggestions + next milestone's upfront design) exists | UC7, R6 | fast | |
| AH8 | An item brainstorm states its test disposition explicitly; a harvest-delete-rewrite item shows harvested requirements before deletion | R20 | slow | |
| AH9 | Grepping all edited skills finds the shared glossary, no retired term used in its old sense, and the residue/residual pair used only in their distinguished senses | UC10, R16 | fast | |
| AH10 | Every skill edit follows writing-skills discipline: a baseline failure observed before the edit, compliance after | 5.9, R23 | slow | |
| AH11 | The architect, messaged mid-lull with a juicy design question and no operator present, files it to the agenda and does nothing else — and never initiates design alone | R3 | slow | |
| AH12 | Every protocol in the table has its ledger created with the stated single writer, and a message-vs-ledger disagreement resolves to the ledger | R21 | fast | |
| AH13 | A charter that would exceed the milestone or lacks a probe reference is refused; an ad-hoc room is chartered for a probe without touching the architect room | R5, R18, R19 | slow | |
| AH14 | A big REPLACE or RESHAPE ruling is refused in-session until its vision exists; the next session's brainstorm grounds on that vision, not the legacy module | UC1, R14 | slow | |
| AH15 | A brief gap flagged in the feedback ledger appears fixed in the very next charter the orchestrator writes; later, `/superdev:improve` clusters the ledger and ships an operator-approved skill edit with a version bump | R24 | slow | |
| AH16 | An item brainstorm on corpus-governed territory opens with system passages quoted at file:line, runs angle-by-angle, and ships a spec with item angle companions and per-area statuses | R25 | slow | |
| AH17 | A plan for model-changing work presents execution-shape variants before any task exists; its swept tests sit in `tests/_archived/` with manifest + harvest, one is recalled mid-build, and post-development cleanup leaves only the manifest | R26 | slow | |
| AH18 | The moment the operator agrees the execution shape, the first task starts unprompted (whether they stay or leave); the desk shows "execution started"; the next operator touchpoint is a desk entry, not a question | UC11, R27 | slow | |
| AH19 | A reviewer finding is fixed by resuming the original implementer (SendMessage or `codex-worker run --name`) with only the findings; the registry shows resume metadata for every subagent of the arc; the broad arc was reviewed at checkpoints, not per-mini-task | R28 | slow | |

## 10. Drift protocol

Governs §4–§8; anchor bends only by soften-but-own (human-in-loop: divergences to the operator before finishing). One addition specific to this design: a build-time fork that is **design-class routes to the residue ledger for the next session** (R13), never to a silent local amendment of this spec — this document eats its own cooking.
