---
name: orchestrator
description: Use when running milestone-scale work as a coordinated cascade of ENTERABLE ROOMS — full peer Claude sessions the human can attach to and leave without the room losing context — rather than a single session or headless subagents. Covers the orchestration graph, room launch/comms (room-mechanics.md), residual scheduling, and the human-approved milestone close. Not for single tasks (run the skills directly — the standalone path needs no orchestrator) and not for headless fan-outs (dispatching-parallel-agents / SDD parallel-execution).
---

# Orchestrator — milestone-altitude coordination of enterable rooms

A third dispatch modality beyond headless workers (Agent tool) and Workflow scripts: the
**enterable room** — a full peer Claude session launched with `claude --bg` from a worktree.
It appears in the session picker, is attachable (`claude attach <id>`), **preserves context
across the human entering and leaving**, and reports to you over cross-session messaging.
This skill is how ONE orchestrator session runs a milestone as a cascade of such rooms.
**"Milestone" is an ALTITUDE, not a fixed unit:** the integration scope can be a big bundle,
a milestone phase, or any coordinated wave — the machinery is identical (integration branch,
rooms, ledger, human-approved landing); only the scope name changes.

**The base case is untouched:** a single task needs NO orchestrator — launch the skills
directly (standalone path). Orchestration is purely additive; the launch brief is the switch
(see room-brief-template.md).

## Authorship — the brief is a language, not a form

You are an AUTHOR, not a dispatcher. This skill teaches a grammar and gives sample
sentences; you write new sentences every milestone. Two layers, keep them straight:

**LAWS (invariant — measured or structural; never improvise):** the transport wiring
(messages don't deliver otherwise) · worktree-per-room + FF-CAS self-publish (rooms merge
themselves; you never do) · the membrane (the operator talks to rooms, never their
subagents) · durable state as files · human-approved milestone close with zero in-milestone
leftovers · the untouched base case.

**AUTHORED (yours to design, per milestone and per room):**
- **The graph shape** — serial ladder, diamond, parallel waves, a long-running research room
  feeding others, a standing review room: whatever the dependency reality actually is. The
  graph may be DERIVED rather than authored from scratch: if the project's work-tracking
  system already encodes members, dependency edges, and write surfaces (bundles, depends_on
  guards, launch tables), read the graph off that metadata and co-ratify it with the human
  instead of inventing a parallel structure.
- **Each room's gating structure** — start-building-immediately (spec complete; a
  ratification gate would be ceremony) · wait-at-ratification (design needs a ruling first) ·
  staged mid-room gates (a money-boundary room that stops twice) · gate-free-until-close (a
  mechanical room). Gate placement encodes WHERE TRUST RUNS OUT — it differs per room, and
  choosing it is the same class of judgment as residual routing.
- **Each room's reporting protocol** — R0–R5 is the proven DEFAULT vocabulary, not
  scripture: define fewer events, more events, different cadences, different WAIT points,
  event kinds never named here. A design room may need three events; a high-risk build room
  a report per phase.
- The files each room produces, its ID block, its mode, its batching rhythm with the human.

Rooms launched in parallel need not behave alike: one may build immediately while its
sibling waits for ratification — because you wrote them different contracts. That
composition IS the job.

## The membrane (two layers — never blur them)

- **Operator ↔ rooms**: peer sessions, enterable, HIL-gated. The operator's ONLY
  counterparties.
- **Room ↔ its own subagents**: headless SDD workers behind the membrane. SDD is not
  replaced — it is the engine *inside* a build room. The operator never touches a subagent.

Room **shapes**: design-only (brainstorm → rulings → hand back the doc) and build
(brainstorm → implement via SDD → checkride → self-publish). Room **modes** (human tempo):
- **HIL** — human rules every decision in-room (superdev:brainstorming).
- **Self** — fully autonomous; one ratification gate (superdev:self-brainstorming).
- **Hybrid** — self-brainstorming by default; holistic forks (blast radius, cross-cutting,
  taste, money/irreversibility) are tagged HOLISTIC-PROVISIONAL and batched to checkpoints;
  the human enters to rule at altitude — shape, not detail — and leaves. The room NEVER
  stalls waiting: safe by topology, because nothing reaches main before the human-approved
  milestone close.

## Lifecycle

1. **Ground → HIL co-plan → the orchestration graph.** Before spawning anything: ground on
   the project's docs/state, then co-create the **orchestration graph** with the human in
   THIS session — nodes = rooms (mode · shape · scope · owned residuals · ID block), edges =
   dependencies + residual-routing. The graph is the plan-of-record, held in durable state
   (durable-state.md); the cursor tracks progress against it.
2. **Open the milestone branch** + each room's worktree off it (your only git action until
   close). Assign each room a **disjoint decision-number block** for its own item log
   (e.g. D24+ vs D40+) so parallel branches merge without renumbering — no shared
   append-only files exist (D51); findings travel in reports.
3. **Execute — autonomous.** Spawn rooms per the graph's dependency order (launch commands +
   briefs: room-mechanics.md + room-brief-template.md). Receive reports; keep the cursor and
   ledger current AS EVENTS ARRIVE. Rooms **self-publish** to the milestone branch via FF-CAS —
   you coordinate, you NEVER merge room work; reports are informational, never merge requests.
4. **Residual scheduling — the zero-leftovers engine.** Classify every captured
   residual/deviation FIRST:
   - **In-milestone** → ROUTE it: to the upcoming room that owns its area, or grouped with
     related deviations into one batched ruling / cleanup room, or ruled via an HIL room.
     These MUST drain to zero before close.
   - **Out-of-milestone / global** (platform/architecture issue that isn't this milestone's
     job) → the **ESCAPE HATCH**: file it to the project's backlog/ticketing system (or to a
     human). Filing IS the disposition — it never blocks close. Batch these at the end
     unless genuinely urgent (a P0 on main). Never confuse the two classes: "belongs to the
     milestone?" → resolve here; "global?" → file and move on.
5. **HIL touchpoints only at altitude:** startup co-planning · holistic checkpoints /
   batched forks (queue R-H reports; surface at convenient moments) · milestone close.
   Never per-room, never per-detail. One exception is queued, never skipped: a checkride
   paused on missing real data (the substrate law, superdev:cli-checkride) is a DECIDE you
   queue for the human — never resolved by a stand-in, never a close.
6. **Milestone close — human-approved.** The close gate: residual ledger drained to zero
   (in-milestone) · escape-hatch items filed · milestone-level sweep (cross-room doc/code
   coherence — the deviation-audit instinct at milestone altitude) · **per-room close
   verified: worktree merged AND retired (`git worktree list`), archived tests deleted with
   their manifest kept, and — when the item changed a user-facing surface — its checkride
   verdict is PASS (or a PASS-WITH-EXCEPTIONS the human has read) ON ACTUAL DATA, and its
   date-stamped scenario intent doc exists in `docs/superdev/scenarios/` (written before the
   ride, refreshed after)** ·
   **the milestone handoff complete — BOTH halves** (yours in `docs/orchestration/handoffs/`;
   the architect's half is the next milestone's document set coming into existence, D49) ·
   **N−1 operational sediment pruned** (D62: delete the PREVIOUS milestone's handovers, raw
   ledgers, spent backlog items, and proposal drafts after harvesting — keep-set: handoffs,
   conventions.md, improvement notes; git is the archive). Present the evidence; the human
   approves; you land milestone→main (a fast-forward — your one merge act, the sole human
   gate on the merge path).

## The battery — the operational suite at milestone close

Before the milestone close gate, charter an **ad-hoc battery room**: an executor walks EVERY
scenario intent in `docs/superdev/scenarios/` against the current surface (re-deriving commands —
intents, never scripts) on ACTUAL DATA under the checkride's substrate law (a scenario whose
data is unavailable is a DECIDE, not a skipped row), in the same one-step loop (propose →
rule → run → judge); an evaluator judges each against its what-good-looks-like criteria;
verdict per scenario; observations auto-file as backlog/residue. The battery report rides the
milestone handoff. Partial batteries on demand when a ride's findings smell systemic.
The battery's judging seat is **superdev:milestone-sweep-judge**. It settles scope, keeps the command
matrix, the P0–P3 bug ledger and the gap list, never approves a write, and returns exactly one verdict:
PASS-TO-HUMAN · BLOCKED · INCOMPLETE. The human tests only after PASS-TO-HUMAN.

## Chartering — granularity and the best path

Cutting the milestone into items and finding the launch order is an ALGORITHM, not a feel
(D44/D45): items are cut from the map along corpus seams into independently deliverable,
testable units; **dependencies are never parallelised — the producer merges first**;
parallelism is created by SPLITTING high-blocking items so their unblocking kernel merges
earliest; scheduling is greedy on "unblocks the most work soonest", capped by the operator's
attention. Types (foundation · surface · ad-hoc · quick fix · backlog) carry different
done-bars. Full taxonomy, principles and the algorithm: [chartering.md](chartering.md);
the operator ratifies the graph + splits at the co-plan.

## The system-design layer (binds whenever the project has a `docs/system-design/` corpus)

When a design corpus exists (see superdev:system-design — the glossary there is the shared
vocabulary), the milestone sits under a design authority and you are the seam between the
two altitudes. **The two surfaces (D60):** `docs/system-design/` is the RECONCILED surface —
architect-only, grab-and-trust; `docs/orchestration/` is YOUR operational surface — message
companions and working state, stamped OPERATIONAL RECORD, never reconciled, pruned on the
rolling window (durable-state.md). Nothing crosses. Your duties, none of which make you a
designer:

- **The milestone is your whole world.** Bias to contain; boundary adjustments are discussed,
  never improvised.
- **The MODE is declared at the co-plan** — HUMAN or AUTONOMOUS, recorded in your graph and
  `conventions.md`. The canonical law lives in system-design SKILL.md#mode-law; in
  AUTONOMOUS mode YOU pick among the architect's presented options (every pick a flagged,
  revisitable D#; reserved forks — money/irreversibility, blast radius, taste — always
  queue to the operator; close is always operator-approved).
- **Residue ≠ residual, and rooms never write ledgers (D51).** Rooms record findings in
  their own item files; their REPORTS carry the survivors; YOU comprehend reports into the
  typed residue ledger in your space (kinds: discrepancy · insight · duplicate-risk ·
  question) and cluster continuously — never interpret as architecture, never file residue
  to the backlog escape hatch. **Plan-time deviation pointers (D61):** when a room messages
  a corpus contradiction after planning, RELAY the pointer to the architect immediately —
  pointers, never paraphrase; the room keeps building.
- **Design checkpoints, declared by rule + green lights + feel.** Your side: ONE handover
  document with clusters inline (checkpoint-protocol.md); the architect's answer arrives as
  a response BLOCK in the milestone's decisions file, followed by rulings and the named
  reconcile commit. Two-step discharge: you CLAIM map rows with evidence; only the architect
  writes the map — and rejected claims come back with reasons. Between checkpoints the
  architect is idle: it may RECEIVE pointers anytime, but do not message it work.
- **Briefs carry architecture as-of the reconcile SHA** (room-brief-template.md: the
  five-part block — MAJOR/NARROW reads, 3–5 verbatim LOCKED quotes, post-SHA D# pointers).
  After each sitting, update the SHA your new briefs cite.
- **The foundation gate — no room launches on a design-dry area.** Before chartering a room,
  ask the architect to CONFIRM its area has a foundation: at least a few angles and the
  governing system-design passages (full coverage is not expected — rooms analyze their use
  cases and build the details). If nothing exists, do NOT launch: the human leads the
  architecture, so the foundation comes first — the human and the architect brainstorm a few
  foundation angles for that area; then the room launches, self-brainstorms the details, and
  the human reviews and iterates. The gate is scoped: unaffected charters proceed. Chartered,
  building rooms are NEVER stopped by design-dryness; they finish, plant markers, and merge.
- **Process feedback (the fast loop):** rooms' R5 RETROSPECTIVES (orchestrator/retrospective-template.md)
  + your measured facts into your process-feedback ledger — one row per proposal, citing the retro; adapt every NEW room's brief immediately (one O-line per change).
  You never edit skills; when entries cluster, the operator runs superdev:self-improvement
  in inbox mode.
- **You never execute work.** No micro-task tier. Ad-hoc rooms (probe, spike, sweep) are
  yours to charter freely — the probe gate does not bind them; they are how censuses get made.

## The execution proposal (D55 — yours to author, by opposed seats)

Before chartering, translate the reconciled corpus into a delivery hypothesis:
`docs/orchestration/execution/<milestone>-proposal.md` (stamped OPERATIONAL RECORD;
reconcilable, never locked; authorizes no code). Method — dispatch two read-only seat
subagents, both grounded on the corpus as-of the reconcile SHA:

- **Domain-boundaries seat:** "Cut the ruled architecture along domain seams — type
  ownership, package boundaries, contract breaks. You optimize CLEAN CUTS; you are
  forbidden to weigh demonstrability. Return: proposed items, each with the seams it
  respects and the contracts it isolates."
- **Celebration seat:** "Cut along operator-visible journeys on the real user surface. You
  optimize PROVABLE WINS — each celebration a journey with proof, refusal, and recovery
  evidence; you are forbidden to weigh internal cleanliness. Return: proposed celebrations,
  each with the journey that proves it."

Their reports land in your space or sdd scratch (never the corpus — D68). **The collision
zone is the product**; adjudicate under the five rules: operator-visible capability · proof
at the user surface · foundations fold into the first proving vertical *unless they unlock
named independent streams* · terminal-not-tiny · reconciliation expected. Ratify the
reconciled proposal with the operator at the co-plan; then derive the charter graph
(chartering.md). Item-level splits/merges amend YOUR proposal (rule 5); only design-class
divergence crosses to the architect, as residue. The architect touches this twice only:
upstream via the corpus (a gap = design-dry), downstream via an advisory conformance note.

## The room gate seam (audit never skipped)

Rooms do NOT invoke finishing-a-development-branch (its present-merge-options-to-the-human
step violates HIL-only-at-altitude). The deviation/acceptance audit that lives there must
not be lost: a room runs it as part of **pre-publish** — its R4 report carries the audit
verdict beside gate output and checkride verdict, and an unlogged deviation blocks
self-publish exactly as it blocks a finishing merge. The milestone-level sweep at close is
the second net.

## When NOT to use

Single task → standalone path. Independent headless diagnostics → dispatching-parallel-agents.
Multi-milestone plan inside ONE session → SDD parallel-execution (controller-merge lanes).
Rooms are for work where the human needs enterable, context-preserving sessions and
milestone-level coordination — the machinery costs attention; don't pay it below that scale.

## Files

- [room-mechanics.md](room-mechanics.md) — transport, launch/publish commands (verbatim),
  reporting protocol, fault handling, measured gotchas.
- [room-brief-template.md](room-brief-template.md) — the spawn contract; standalone vs room
  briefs (the switch, made concrete).
- [durable-state.md](durable-state.md) — the orchestration graph, cursor, and residual
  ledger the orchestrator MUST keep as files (compaction survival: re-derive from files +
  commits, never memory).
