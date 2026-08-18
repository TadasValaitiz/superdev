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
  feeding others, a standing review room: whatever the dependency reality actually is.
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
   close). Assign each room a **disjoint ID block** for any shared append-only ledger
   (e.g. decisions D24+ vs D40+) so parallel branches merge without renumbering.
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
   Never per-room, never per-detail.
6. **Milestone close — human-approved.** The close gate: residual ledger drained to zero
   (in-milestone) · escape-hatch items filed · milestone-level sweep (cross-room doc/code
   coherence — the deviation-audit instinct at milestone altitude). Present the evidence;
   the human approves; you land milestone→main (a fast-forward — your one merge act, the
   sole human gate on the merge path).

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
