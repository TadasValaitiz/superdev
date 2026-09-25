---
name: self-brainstorming
description: Use when a design needs deep brainstorming but no human respondent is available or the human wants the exploration prepared before engaging — autonomous passes, delegated work, or pre-work for a big fork. Works ANGLE BY ANGLE like brainstorming: grounds, proposes an angle agenda the human agrees, then runs a bounded questioner↔responder loop per angle via the Workflow tool, writing each angle's companion as it closes; ends with an architecture summary at a STOP for human review. Not a replacement for brainstorming when the human is present and engaged — the human is always the better oracle.
---

# Self-Brainstorming — the question loop without the human

Brainstorming works because the right questions get asked about the right ANGLES, and
each angle is finished — reconciled and written — before the next opens. This skill
preserves that mechanism when no human is on the other side: one agent role asks the
questions (the design authority), another answers them from evidence (the grounded
oracle), and a scripted loop works the AGREED angle agenda one angle at a time — never
one open-ended loop over the whole design. The output is a design ready for human
review — never a design that pretends it was ratified. WHO ratifies is the
milestone MODE's call (canonical law: superdev:system-design SKILL.md#mode-law): HUMAN
mode — the operator, with the gate queuing as a desk DECIDE; AUTONOMOUS mode — the
ORCHESTRATOR ratifies (reading the assumptions section first), as a flagged, revisitable
pick; RESERVED forks (money/irreversibility, blast radius, taste) always wait for the
operator in both modes.

**Invoking this skill is the user's opt-in to multi-agent orchestration** — it is built
on the Workflow tool. If the Workflow tool is unavailable in the current harness, fall
back to running the same loop inline with native Claude Agent calls (one questioner
call, one responder call per round, you as the scribe). Pin grounding and responder to
`sonnet` (`medium`); pin questioner, synthesis, review, fix, and re-review to `opus`
(`very smart`). No Codex substitution: the roles, rules, and artifacts below are
identical either way.

<HARD-GATE>
Self-brainstorming produces a SPEC PROPOSAL, not an approved spec. Do NOT invoke
writing-plans or any implementation skill on the output until a human has ratified the
assumptions and approved the spec — or, in an explicitly autonomous context where the
operator has pre-delegated that authority, until you have re-verified every ASSUMPTION
against evidence and said so in the hand-off.
</HARD-GATE>

## Launched as a room? (GUARDED — default is standalone, unchanged)

If — and ONLY if — your launch brief names an orchestrator address, a reporting protocol
(R0–R5), and a milestone-branch publish recipe, you are an ORCHESTRATED ROOM: follow the
brief's reporting contract (R1 design-ready then WAIT at the gate for ratification per the milestone MODE (HUMAN: relayed human ruling; AUTONOMOUS: the orchestrator's flagged pick) — the
orchestrator carries your doc to the ruling authority per the milestone MODE — the human in HUMAN mode, its own flagged pick in AUTONOMOUS mode), produce its FILES-YOU-PRODUCE set, and
self-publish via the brief's FF-CAS recipe to the milestone branch — never to main. See
orchestrator/room-mechanics.md. Absent that contract, ignore this section entirely.

**HYBRID mode (brief says HYBRID):** run this skill as normal, plus fork classification —
the Questioner tags each fork **detail** (agent-owned; decide and lock as usual) or
**holistic** (human-owned: large blast radius, cross-cutting shape, taste, money/
irreversibility). Holistic forks are decided PROVISIONALLY (status HOLISTIC-PROVISIONAL,
never plain locked), batched, and surfaced via R-H reports — the picture + the fork in
prose, never a detail dump — while the loop KEEPS FLOWING; never stall waiting for the
human. The human enters at checkpoints, rules at altitude, leaves; re-flow whatever their
redirect touches. Safe by topology: nothing reaches main before the human-approved
milestone close.

## The two roles (and why the split matters)

**The Questioner is the design authority.** It owns the brainstorming skill's question
discipline: one question per round, the question that most reduces design uncertainty
next, 2–3 concrete options attached with trade-offs, ruthless YAGNI. It also owns the
ratchet: each round it reviews the previous answer and emits `locks` — decisions it now
considers settled, with rationale and a revisit-when hook. It works ONE angle at a time
and ends that angle by declaring it reconciled: no remaining unknown in this angle would
change what gets built. Unknowns that belong to another angle are parked for that angle,
never chased now; a genuinely new angle is proposed for the agenda, never worked silently.

**The Responder is a grounded oracle, not an imaginative one.** In human brainstorming
the human supplies ground truth; here the Responder must dig for it: read the codebase,
the docs, prior specs and decision logs, run read-only probes. Every answer carries an
evidence tier:

- `EVIDENCE` — grounded in something it actually read or ran (cited).
- `REASONED` — an inference from evidence, argued explicitly.
- `ASSUMPTION` — could not be grounded. Stated as an assumption, never dressed as fact.

**The iron rule:** a lock resting on an `ASSUMPTION`-tier answer is `provisional`, never
`locked`, and the assumption joins the ratification queue. The failure mode this
prevents: two agents confidently converging on invented requirements — a fluent spec
built on hallucinated ground truth is worse than no spec.

## The phases

You — the session running this skill (the CONTROLLER) — hold the spine. Workflows are
small: **ONE workflow run per angle**. The angle file is the hand-off between runs, so any
fresh session can pick up where the last angle file left off, and the architect (and the
human) can be brought in BETWEEN angles.

```
1 Ground    → YOU (or one sonnet agent) write the census (brainstorming step 1 contract:
              MEASURED / READ / FLAGGED, file:line; first line "CENSUS — evidence record;
              rules nothing"). If a docs/system-design/ corpus exists, READ the angles and
              decisions that govern this item and quote the load-bearing lines (file:line).
              Commit it.
2 Agenda    → YOU propose 3–5 ANGLES, inline, no workflow (superdev:system-design
              angle-guide.md#item-angles: one central question · why it matters ·
              boundaries) — a few, deep, for the UNCLEAR journeys and collisions; the
              well-understood shape goes to the domain-model / pipelines companions.
              ORDER THEM: the most important angle FIRST (the one the others depend on).
              STOP: the human agrees the agenda (drop · add · reorder). In an orchestrated
              room the human does it in the room. Record the agreed agenda in the decision log.
3 Angle N   → launch ONE self-brainstorm workflow for THIS angle (workflow-reference.md):
              inputs = the angle, the census, EVERY previous angle file, the governing
              system-design passages, and any architect answers. Questioner ↔ Responder,
              at most 6 rounds, scoped to this angle; the run closes the angle and WRITES
              + COMMITS its angle file per brainstorming's item-angle-template.md, then ends.
4 Between   → YOU read the new angle file before launching the next workflow:
              · check it against the system-design corpus (the architect keeps it correct);
              · a discrepancy with the corpus, or a question only the architect can answer
                → send the architect an ASK (a pointer: the cell, the corpus file:line, the
                angle's position); wait for the answer ONLY if the next angle depends on it,
                otherwise carry it as an open question into the next angle's inputs;
              · a question only the human can answer → ask the human now (in the room);
              · a genuinely NEW angle surfaced → add it to the agenda openly and tell the
                human; never work it silently;
              · the architect's answers and the human's rulings go into the next angle's
                inputs and the decision log.
              Then step 3 for the next angle. Repeat until every agreed angle is closed.
5 Shape     → after all angles: the whole-design shape, composed FROM the angle files and the
              domain-model (I#) / pipelines (P#) companions; design doc + decision log; the
              design doc indexes every angle, I# and P#.
6 Review    → the spec reviewer (skills/brainstorming/spec-document-reviewer-prompt.md) over
              the design doc + decision log + census + EVERY angle file; fix blocking issues once
7 Summary   → the architecture summary and the STOP (see The hand-off)
```

Why this shape:
- **Small workflows:** a run is one angle wide, so its context is one angle wide — the main
  token control. Depth comes from more agreed angles, never a longer loop.
- **The angle file is the checkpoint:** a paused or crashed brainstorm resumes from the last
  committed angle file; a different session (or a different room) can continue it.
- **The loop is open between angles:** the corpus check and the architect ASK happen where
  they are cheap — before the next angle builds on a wrong premise, not after the spec.
- **Measured in brainstorming:** angle files written hot, as each angle closes, carried
  ~1,500+ words of teaching detail; the same angles batched to the end became ~380-word
  cite-only indexes.

The per-angle workflow script, schemas, and role prompts: `skills/self-brainstorming/workflow-reference.md`.

## Artifacts (identical contract to brainstorming)

- **Angle companions** — one per agreed angle, `docs/superdev/specs/YYYY-MM-DD-<topic>-angle-NN-<slug>.md`,
  per `skills/brainstorming/item-angle-template.md`, WRITTEN AND COMMITTED WHEN THE ANGLE
  CLOSES (never batched to the end). The census is committed at Ground.
- **Design doc** — `docs/superdev/specs/YYYY-MM-DD-<topic>-design.md`, per
  `skills/brainstorming/design-doc-template.md`: numbered requirements (R#), narrative
  through-line with link-sentences, decisions (D#) with reasoning and revisit-when
  hooks, assumptions (A#), not-doing ledger, drift protocol. Header states
  `Origin: self-brainstorm run <id>`. The conditional companions apply here too:
  domain-touching work gets the Domain model section (`domain-design-template.md`);
  CLI-touching work gets the separate `…-cli-surface.md` (`cli-surface-template.md`) —
  the Shape stage writes them from the angle companions and ledgers.
- **Decision log** — same directory, `-decisions.md` suffix, per
  `skills/brainstorming/decision-log-template.md`. Every lock becomes a D# entry
  stamped with the round that produced it; rejected options and reversed locks stay in
  the log. The workflow's journal is the crash-recovery trail; the log is the durable one.

## The hand-off (how a run ends)

Every run ends at a STOP: no planning or execution follows until the design is reviewed.
Write an **ARCHITECTURE SUMMARY** beside the design doc (`…-architecture-summary.md`), for the
human in EVERY mode — autonomy delegates the running, never the look at the design:

1. **Assumptions requiring ratification** — the A# queue, each with what rests on it.
   This comes FIRST; it is the honesty bill for running without an oracle.
2. **Per angle:** its central question, the core forks (options weighed · what was decided ·
   why — one short paragraph each), and whether it closed reconciled or capped.
3. Rounds run per angle; the reviewer's verdict.
4. **The design files** — census, every angle file, design doc, decision log, and the
   domain-model / pipelines / CLI companions — each as a clickable `file://` absolute URL,
   so the human can open and review each one.
5. Recommended next step (usually: ratify A#s → approve spec → writing-plans).

Report it to the ratifying authority (per the mode law). Inside an orchestrated room, the
order is fixed: (1) the design files go to the architect for its score and feedback; (2) the
design review runs; (3) the summary is updated with both; (4) the human enters the room,
opens the files, and APPROVES there — the room waits for that approval before planning. The
orchestrator gets a one-line notice when the summary is ready for the human.

## Red flags

| Thought | Reality |
|---------|---------|
| "The responder's answer sounds right, lock it" | Sounds-right is not a tier. No evidence cited → ASSUMPTION → provisional. |
| "An angle hit its cap, close enough" | An unsaturated stop is a partial exploration. Say so in the hand-off. |
| "Skip the agenda stop, the angles are obvious" | The agenda is the human's steering point. Agreed angles are cheap; unagreed angles are where tokens burn. |
| "I'll write the angle companions at the end" | Batched companions become cite-only indexes. Write each angle as it closes. |
| "The spec is coherent, skip the reviewer" | Coherent-to-the-authors is exactly what the reviewer exists to test. |
| "Autonomous context, so skip ratification" | Autonomy delegates the RUNNING, not the truth bar. Re-verify assumptions or leave them flagged. |
| "Thread the whole transcript for richer context" | The ledger IS the context. Transcript-threading reintroduces anchoring and burns budget. |
