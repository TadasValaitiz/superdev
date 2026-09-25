# TAXONOMY — the room-graph vocabulary

One word per concept, one meaning per word, for everything about rooms, messages, process and scope. The
orchestrator skill and the architect's system-design skill use ONLY these words; every brief, report, residuals
file and retrospective uses them too. Design-corpus terms (corpus, angle, marker, map, vision…) live in
superdev:system-design `glossary.md`, which points here for the rest. When a skill and this file disagree,
this file wins; fix the skill.

**Terms are written in CAPITALS.** Skills adopt the capitals as they are edited — no mass replacement; the vocabulary converges as the skills improve.

**This file grows; it is never forced.** When a skill uses a concept this file does not name, ADD the term here
(with its meaning) instead of bending the skill into an existing word that does not fit. When a skill's word is
better than the one here, change this file. Every change to this file is a skill directive the human approves.

## 1. Roles and places

| Term | Means exactly | Replaces |
|---|---|---|
| **HUMAN** | The person who leads the architecture and approves in the room graph — the super user: rules reserved forks, says GO, approves destructive steps | "user"; "operator" meaning the authority |
| **OPERATOR** | Someone using a PRODUCT's own commands through Claude Code, in the operator's seat (e.g. a trading operator running the product CLI). A checkride's evaluator judges "from the operator's seat" | — |
| **ORCHESTRATOR** | The orchestration room: milestones, room graph, sequencing, merges, gates, grants | "controller" meaning the orchestrator |
| **ARCHITECT** | The architect room: owns the design corpus, scores and rules design | "architect" meaning any session running system-design (that is an "architect session") |
| **ROOM** | An enterable `claude --bg` session with a brief, its own worktree and a closing condition; an **ITEM ROOM** builds one ITEM | — |
| **ROOM SESSION** | The session running a skill — inside a room, or standalone on an ordinary branch | "the controller", "the room's session" |
| **SUBAGENT** | A headless helper inside a room; never enterable, never messaged by the human | — |
| **ROLE** | The named job a subagent fills, matching the skill or brief that defines it: implementer · reviewer (also the adversary that plants mutations) · ride executor · ride evaluator · sweep judge · sweep executor · questioner · responder | "seat" |
| **LANE** | A parallel line of work with its own worktree and file set, opened only after a file-conflict map | "lane" meaning a role |
| **THIRD-PARTY SERVICE** | A peer outside the graph (e.g. a data provider the project calls); contract-level requests only, never our file paths | — |

**Overlap rule:** **HUMAN** = authority in the room graph (approvals, rulings, GO). **OPERATOR** = using the product
(journeys, the operator's seat, operator-facing refusals and remedies). When the human uses the product themselves:
"the human, as operator".

## 2. The ladder and the scope

| Level | Means exactly | Owned / closed by |
|---|---|---|
| **ROADMAP** | the ordered list of milestones the human ratifies | the human |
| **MILESTONE** | a scoped set of journeys delivered together, with its MILESTONE SCOPE; the unit the orchestrator plans and the SWEEP and HUMAN TEST judge | the orchestrator; closed by the human at the MILESTONE CLOSE GATE |
| **ITEM** | one room's slice of the milestone: its area, write surface and journeys (ITEM SCOPE); designed at its DESIGN STOP, built, ridden, published | its item room; ITEM CLOSE (R5 CLOSE), checked by the orchestrator |
| **ARC** | a broad unit of BUILD inside an item: one deliverable, many files, carried by ONE implementer subagent from start to finish; ends at a plan checkpoint where the reviewer checks it. Arcs run one after another unless a file-conflict map allows parallel lanes | the room's session |
| **TASK** | the smallest unit inside an arc with its own test cycle — write the failing test, make it pass, commit; small enough that a reviewer could accept or reject it on its own | the implementer |

A room never says "my milestone": it has an ITEM; "the milestone" is always the orchestrator's. LANE is not a level:
it is a parallel line of work that can carry arcs side by side.

| Scope term | Means exactly |
|---|---|
| **MILESTONE SCOPE** | one document per milestone (`SCOPE.md`), written by the orchestrator and approved by the human at MILESTONE PLAN: the **journeys** the milestone must make work, in the human's words, and the commands each uses; every room, the sweep and the judge read it |
| **IN SCOPE** | the milestone's journeys: must work perfectly — every number labelled, no traceback, honest refusals with runnable remedies, help that matches behaviour. The SWEEP tests exactly these |
| **COMPLEMENTARY** | supporting commands the journeys need: must work and must not lie; lighter bar; swept only where a journey crosses them |
| **DEFERRED** | commands left as they are this milestone: no work, not swept, never a P0/P1 |
| **OUT OF SCOPE** | belongs to another named milestone: never built, swept or "just fixed" here |
| **ITEM SCOPE** | one room's slice: its area, its write surface (from MAPPING), its journeys; lives in the brief; always inside the MILESTONE SCOPE; never crosses another item's files without a grant |
| **SCOPE RULE (findings)** | inside IN SCOPE → triaged (§6 finding triage); in DEFERRED or OUT OF SCOPE → never a sweep finding, recorded in the RESIDUALS FILE tagged with its target milestone — except a crash an in-scope journey triggers |
| **SWEEP SCOPE** | the sweep judge's matrix has one row per IN SCOPE command; it tests on the milestone's main; PASS-TO-HUMAN speaks for the MILESTONE SCOPE only |
| **SCOPE CHANGE** | only the human changes the milestone scope; the orchestrator proposes, and the scope document records it with the human's words and the date |

## 3. Process steps and gates

**Milestone level (orchestrator):**
1. MAPPING — haiku subagents map ownership, shared seams, dependencies (chartering.md step 0).
2. FOUNDATION GATE — the architect confirms each item's area has foundation angles + system-design passages; if none, the human and the architect brainstorm them first.
3. MILESTONE PLAN — written by the orchestrator, advised by the architect, GO from the human.
4. ROOM LAUNCH — each room gets its brief, built from the map.
5. MERGES — the orchestrator merges each publish into main after the TEST GATE.
6. SWEEP — a regression over the milestone's IN SCOPE journeys, judged by the sweep judge.
7. HUMAN TEST — the human, as operator, tests the milestone.
8. RESIDUAL TRIAGE — the orchestrator triages every room's RESIDUALS FILE before the next milestone starts.
9. MILESTONE CLOSE — at the MILESTONE CLOSE GATE, approved by the human; retrospectives collected.

**Item level (room):**
1. GROUND — read in; write the census.
2. SELF-BRAINSTORM (or BRAINSTORM with the human) — agreed angle agenda → one angle at a time with a between-angle check → the TESTING & CLEARANCE angle last → whole-design shape → design review.
3. DESIGN STOP — DESIGN-REVIEW → ARCHITECT-VERDICT → R1 DESIGN-READY → the human approves in the room → RULED.
4. PLAN — names its finalization points.
5. BUILD — in arcs; parallel lanes only after a file-conflict map; PROBE while building.
6. CHECKRIDE — a regression at the plan's finalization points only.
7. AUDIT → PUBLISH.
8. ITEM CLOSE — in-area residuals closed · hand-off · RESIDUALS FILE · RETROSPECTIVE · R5 CLOSE → the orchestrator retires the room after its last merge.

| Gate | Who clears it |
|---|---|
| **FOUNDATION GATE** | the architect (+ the human when angles must be made first) |
| **DESIGN STOP** | the architect (ARCHITECT-VERDICT), then the human (RULED) |
| **TEST GATE** | FAST on every publish; the touched area's slow tests |
| **CHECKRIDE** | the ride evaluator |
| **CHECKPOINT GATE** | the reviewer, at a plan checkpoint inside an item (an arc's review) |
| **FINISHING GATE** | the branch's own final check before publish: tests, acceptance receipts, the deviation/acceptance audit |
| **DESTRUCTIVE-STEP GATE** | the human (or a standing ruling from the human): data drops or deletes, reseeds, schema changes on a shared store |
| **MILESTONE CLOSE GATE** | the human |

| Close | Requested by | Approved by | Means |
|---|---|---|---|
| **ITEM CLOSE** | the room (R5 CLOSE + RESIDUALS FILE + RETROSPECTIVE) | the orchestrator: all merged, in-area residuals closed, hand-off written → retires the room | one room is done |
| **MILESTONE CLOSE** | the orchestrator | the human, at the MILESTONE CLOSE GATE, after the SWEEP, the HUMAN TEST and the RESIDUAL TRIAGE | the milestone is done; the next may start |

**Words:** SWEEP = the milestone-level regression ("battery" retired). CHECKRIDE (or "ride") = the item-level
regression. SITTING = a design session between the human and the architect. PROBE = using a command while
building it; never called a test. DESIGN STOP is a stage, not a message.

## 4. Messages

One name per event. The room-communication plugin's older names are aliases only.

| Message | From → to | Means exactly |
|---|---|---|
| **R0 START** | room → orchestrator | alive, grounded, first move |
| **DESIGN-REVIEW** | room → architect | "review my design": the architecture summary + every design file as `file://` links; sent when (self-)brainstorming ends |
| **ARCHITECT-VERDICT** | architect → room (+ NOTICE to the orchestrator) | score · feedback · forks it ruled · **APPROVED** or **CHANGES-REQUESTED** (the room revises and re-sends DESIGN-REVIEW) |
| **R1 DESIGN-READY** | room → orchestrator | only after ARCHITECT-VERDICT APPROVED and the design review ran: the summary is updated and ready for the human to approve in the room |
| **R2 PLAN** | room → orchestrator | the plan is written |
| **R3 HEARTBEAT** | room → orchestrator | phase · last commit · next · blockers |
| **R4 PRE-PUBLISH** | room → orchestrator | gates + checkride verdict + audit, then publish |
| **R5 CLOSE** | room → orchestrator | the item is done: summary · RESIDUALS FILE path · RETROSPECTIVE path |
| **HIL-NEEDED** | anyone → orchestrator | THE single "human needed" message: what needs ruling · who is blocked · where it is written up; the human rules in the room named. A hybrid room may send a **BATCHED HIL-NEEDED**: several forks, each already decided provisionally, while it keeps working |
| **HOLD / PROCEED-PROVISIONAL / FYI** | orchestrator → room | the orchestrator's answer to a HIL-NEEDED: **HOLD** — that thread stops until RULED · **PROCEED-PROVISIONAL** — keep going, mark the work provisional, redo it if the ruling differs · **FYI** — nothing is blocked |
| **RULED** | room → orchestrator | what the human decided in that room; for a design, the GO to plan |
| **STOP** | room → orchestrator | the room stops ITSELF: an instruction about its own scope was broken, a gate is red out of scope, or it would touch outside its area |
| **HALT** | anyone → everyone | the shared premise is invalid; the whole graph stops; only the human restarts it |
| **PAUSE** | orchestrator → room | the orchestrator stops a room or a lane |
| **RES** | room → orchestrator | a residual outside the room's area, reported as found (it also goes in the RESIDUALS FILE at close) |
| **ASK-ARCHITECT** | room → architect | a design question or a corpus discrepancy |
| **CORRECTION** | anyone → a file's owner | "your file is wrong here", with a pointer; never an edit |
| **PEER** | room → orchestrator | a receipt of a direct exchange between rooms |
| **NOTICE** | anyone → orchestrator | a one-line FYI; no reply needed |

Design-stop order: brainstorming ends → DESIGN-REVIEW → ARCHITECT-VERDICT (APPROVED, or revise) → design review →
R1 DESIGN-READY → the human approves in the room → RULED → PLAN.

**Retired:** DECIDE, CLASS, R-H → HIL-NEEDED (+ HOLD / PROCEED-PROVISIONAL / FYI, then RULED) · STOP-SCOPED → PAUSE · A1 READY / HB → R1 / R3 ·
GREEN-LIGHT, PRE-SPAWN, ESCALATE → folded into R3 HEARTBEAT or HIL-NEEDED · "deviation pointer" / "pointer relay" →
ASK-ARCHITECT. "Stop" alone means only the STOP message.

## 5. Documents and where each is stored

| Document | Written by | Where | Lives |
|---|---|---|---|
| **DESIGN CORPUS** (angles, decision log, index) | architect only | `docs/system-design/` | reconciled; the design authority |
| **ITEM DESIGN FILES** (census, angle files, design doc, decision log, companions) | the room | the room's specs directory | kept |
| **ARCHITECTURE SUMMARY** | the room, at the DESIGN STOP | beside the design doc | kept; lists every design file as a `file://` link |
| **BRIEF** | orchestrator | `docs/orchestration/milestones/<milestone>/briefs/` | per milestone |
| **MILESTONE SCOPE · plan · map · room graph · cursor** | orchestrator | `docs/orchestration/milestones/<milestone>/` | per milestone |
| **RESIDUALS FILE** | each room, at ITEM CLOSE | `…/milestones/<milestone>/residuals/<room>.md` | input to RESIDUAL TRIAGE |
| **RESIDUAL TRIAGE** | orchestrator | `…/milestones/<milestone>/triage.md` | each residual: dropped · merged · carried into the next MILESTONE PLAN |
| **RETROSPECTIVE** | each room, at ITEM CLOSE (retrospective-template.md) | `…/milestones/<milestone>/retros/<room>.md` | feeds the process-feedback ledger |
| **HAND-OFF** | the room (item) and the orchestrator (milestone) | `…/milestones/<milestone>/handoffs/` | kept |
| **ROADMAP · conventions · process-feedback ledger** | orchestrator (the human ratifies the roadmap) | `docs/orchestration/` | project-wide |

**FILING RULE:** NO individual items are ever filed — not by rooms, not by a standalone ROOM SESSION. Every finding
that is not fixed goes into ONE combined **RESIDUALS FILE** per room (or per branch, when standalone); the orchestrator
(or, standalone, the human) runs RESIDUAL TRIAGE over whole files. Individual filing turns into a pile nobody triages.
A room closes residuals inside its ITEM SCOPE before ITEM CLOSE and leaves everything else in its RESIDUALS FILE.
A residual (a loose end) ≠ residue (a design-class finding that goes to the architect by ASK-ARCHITECT).

**RESIDUALS FILE format** — one row per residual: id (room prefix + number) · what (one line) · where found (file:line
or step) · why it is not closed here (outside the ITEM SCOPE, or named-and-deferred with who deferred it) · proposed
target (a milestone, a room, or drop) · evidence tier.

## 6. Status labels

| Axis | Labels | Used for |
|---|---|---|
| **evidence of a claim** | **MEASURED** (from a command run, quoted) · **READ** (from a file, file:line) · **REASONED** (argued from evidence) · **ASSUMPTION** (could not be grounded; always stated plainly) | every number and claim in any document or report. REPORTED = a claim relayed from another room or a third party, keeping its own tier |
| **a ruling** | **LOCKED** · **FLEXIBLE** · **DEFERRED** · **BLIND** · **MISMATCH** | design corpus statuses (system-design) |
| **a decision's strength** | **locked** · **provisional** (rests on an ASSUMPTION or awaits the human; also a timeboxed recommendation standing in for an unruled human cell) | decision logs; "candidate" is retired |
| **checkride verdict** (item level) | **PASS** · **PASS-WITH-EXCEPTIONS** · **FINDINGS** | one ride |
| **sweep verdict** (milestone level) | **PASS-TO-HUMAN** · **BLOCKED** · **INCOMPLETE** | the milestone; never mixed with ride verdicts |
| **finding triage** | **BLOCKS-PUBLISH** · **BLOCKS-MILESTONE** · **RESIDUAL** (goes into the RESIDUALS FILE) | ride, review and sweep findings; honesty and safety findings are never RESIDUAL |

Project data tiers (e.g. SIMULATED, SEED-DEFAULT) are the product's own vocabulary and stay in the project's rules;
FLAGGED (census) = a READ observation not yet verified.

## 7. How rules are written

- **One term per concept, from this file.** A word not in this file or the glossary is prose, never a new term.
- **A rule leads with a bold imperative, then its reason:** "**Never X** — because Y (the incident or measurement)."
  A rule with no reason is a guess; a reason with no rule is a story.
- **NEVER / ALWAYS / ONLY in capitals mark a law**; lower case is guidance.
- **Tables for fixed sets** (events, gates, verdicts, statuses); prose for behaviour.
- **Name who does it:** "the orchestrator…", "the room…", "the human…" — never "we" or "you" where the reader could
  be any of them.
- **Cite, don't restate:** a rule that lives in another skill is linked, not copied.
