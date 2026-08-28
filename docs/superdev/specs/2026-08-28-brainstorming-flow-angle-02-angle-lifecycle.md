# Brainstorming Angle 2 — The angle lifecycle, end to end

**Purpose:** understand where angles are born, worked, written, REVIEWED, and reconciled in a brainstorm — and where today's skill still drops them.
**Formal anchors:** D56 (agenda-first), D65 (this gap's ruling); bench 08-25 angle-definition doc (the harvested source).
**Series:** 2 of 2.

> **Status guide:** LOCKED · FLEXIBLE · MISMATCH skill text behaves differently today.

## The central question
Does an angle live a complete life in the pipeline — or does it die after the agenda, leaving the design doc as the only survivor?

## Boundaries
Starts at session open; ends at the user review gate. System-scale angle law (sweep, INDEX) stays in angle-guide.md.

## Concrete consequences
The intended life: **identify → present agenda (operator amends) → work angle by angle → WRITE companions for collision-bearing angles → REVIEW them with the spec → RECONCILE doc ↔ angles → operator reads them as files.** Observed in this very session (the skill's first live run): the first three stages ran only after the operator forced them; companions were written only when the operator asked "what about angles?"; the spec reviewer was never pointed at them; no pass checked the companions against the design doc. Three MISMATCHES, one root cause: the checklist treats companions as a step-8 side effect (and step 11 hands over only the spec) ("each angle that carried real collisions becomes…") with no teeth, no reviewer input line, and no reconciliation step.
The ruled fixes (D65): (a) companion authoring moves INTO the angle close — a collision-bearing angle is written when it CLOSES, not batched at step 8; (b) the spec-reviewer dispatch lists the angle files as required inputs, with a cross-check row (angles contradict neither spec nor log; every companion's collisions appear in the spec's areas or Not-doing); (c) the user review gate hands the operator the angle files by link, beside the spec. **LOCKED.**

## Visible collisions
- **Angles as working method vs angles as deliverables:** the session used angles to think but nearly shipped none — the two roles need separate teeth (agenda for thinking; close-time writing for the record).
- **Review cost vs drift:** every artifact added to the reviewer's inputs grows the gate; but an unreviewed companion is a second truth — the same disease the two-surface law kills elsewhere.
- **Step-8 batching vs close-time writing:** batching loses the collision detail while it's hot; close-time writing matches the bench 7-step protocol ("write at the checkpoint").

## Reconciled outcome
LOCKED: the three D65 fixes. MISMATCH: current SKILL.md steps 5/8/10/11 — until the plan lands. FLEXIBLE: exact reviewer-prompt wording.
