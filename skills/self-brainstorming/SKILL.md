---
name: self-brainstorming
description: Use when a design needs deep brainstorming but no human respondent is available or the human wants the exploration prepared before engaging — autonomous passes, delegated work, or pre-work for a big fork. Runs a questioner↔responder agent dialogue via the Workflow tool that progressively locks decisions and produces the same two artifacts as brainstorming (rich design doc + decision log), ending at a human ratification gate. Not a replacement for brainstorming when the human is present and engaged — the human is always the better oracle.
---

# Self-Brainstorming — the question loop without the human

Brainstorming works because the right questions get asked and each answer narrows the
design. This skill preserves that mechanism when no human is on the other side: one
agent role asks the questions (the design authority), another answers them from
evidence (the grounded oracle), and a scripted loop locks decisions round by round
until the questioner declares saturation. The output is a design ready for human
ratification — never a design that pretends it was ratified.

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
brief's reporting contract (R1 design-ready then WAIT for relayed ratification — the
orchestrator carries your doc to the human), produce its FILES-YOU-PRODUCE set, and
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
considers settled, with rationale and a revisit-when hook. It ends the loop by declaring
saturation: no remaining unknown would change what gets built.

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

## The loop

State lives in the script, not in the agents: a **decision ledger** (the ratchet) and an
**assumption queue**. Each round threads the distilled ledger — not the full transcript —
into both prompts: agents get fresh eyes every round (less anchoring), and the ledger
stays the single source of truth. Depth scales with the budget/rounds knob: small
problems saturate in a few rounds; deep ones run until saturation, the round cap, or the
budget floor — whichever comes first (an unsaturated stop is REPORTED as such, never
passed off as convergence).

```
Explore    → one grounding agent maps current state, constraints, prior art,
             load-bearing unknowns (this seeds the Questioner)
Dialogue   → loop: Questioner (locks + next question) ↔ Responder (evidence-tiered
             answer + alternatives + recommendation)
Synthesize → one agent writes BOTH artifacts from the ledger, per the brainstorming
             skill's templates — the design doc in TWO PASSES (shape, then enrichment)
             and the decision log carrying every lock AND every rejected path
Review     → dispatch the spec reviewer (skills/brainstorming/
             spec-document-reviewer-prompt.md) over spec + log; fix blocking issues once
```

The full script skeleton, schemas, and role prompts: `skills/self-brainstorming/workflow-reference.md`.

## Artifacts (identical contract to brainstorming)

- **Design doc** — `docs/superdev/specs/YYYY-MM-DD-<topic>-design.md`, per
  `skills/brainstorming/design-doc-template.md`: numbered requirements (R#), narrative
  through-line with link-sentences, decisions (D#) with reasoning and revisit-when
  hooks, assumptions (A#), not-doing ledger, drift protocol. Header states
  `Origin: self-brainstorm run <id>`. The conditional companions apply here too:
  domain-touching work gets the Domain model section (`domain-design-template.md`);
  CLI-touching work gets the separate `…-cli-surface.md` (`cli-surface-template.md`) —
  the synthesis stage writes them from the ledger like everything else.
- **Decision log** — same directory, `-decisions.md` suffix, per
  `skills/brainstorming/decision-log-template.md`. Every lock becomes a D# entry
  stamped with the round that produced it; rejected options and reversed locks stay in
  the log. The workflow's journal is the crash-recovery trail; the log is the durable one.

## The hand-off (how a run ends)

Report to the human, leading with what needs them:

1. **Assumptions requiring ratification** — the A# queue, each with what rests on it.
   This comes FIRST; it is the honesty bill for running without an oracle.
2. Locked decisions (count + the load-bearing ones), rounds run, saturated or capped.
3. Paths to both artifacts + the reviewer's verdict.
4. Recommended next step (usually: ratify A#s → approve spec → writing-plans).

## Red flags

| Thought | Reality |
|---------|---------|
| "The responder's answer sounds right, lock it" | Sounds-right is not a tier. No evidence cited → ASSUMPTION → provisional. |
| "We hit the round cap, close enough" | An unsaturated stop is a partial exploration. Say so in the hand-off. |
| "The spec is coherent, skip the reviewer" | Coherent-to-the-authors is exactly what the reviewer exists to test. |
| "Autonomous context, so skip ratification" | Autonomy delegates the RUNNING, not the truth bar. Re-verify assumptions or leave them flagged. |
| "Thread the whole transcript for richer context" | The ledger IS the context. Transcript-threading reintroduces anchoring and burns budget. |
