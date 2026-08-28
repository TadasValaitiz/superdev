# Brainstorming Angle 2 — The angle lifecycle, end to end

**Purpose:** understand where angles are born, worked, written, reviewed, and reconciled inside a brainstorm — and how today's skill drops them — without reading the skill or the decision log.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D56, D65, D66, D67 · [the study](./2026-08-28-bench-experience-study.md) Parts 1 & 3 · [experience design](./2026-08-28-brainstorming-experience-design.md) BR2–BR8, BR11, BR13.
**Series:** 2 of 4 (brainstorming flow).

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH current skill text behaves differently today ·
> SEED-ILLUSTRATIVE worked example only, never a measurement.

## The central question

Does an angle live a complete life in the pipeline — or does it die after the agenda, leaving the design doc as the only survivor?

## The mental model

An angle is a deliberately partial way to examine one shared design: it follows one question, journey, boundary, or tension far enough to expose consequences, without pretending that direction is the whole system. Several angles overlap on purpose — the value comes from making concerns *collide* and reconciling the collision. And the angle's document is not a record of that examination; it IS the examination's second pass: writing it forces every ruling to be re-derived in prose, which is where gaps and new directions actually surface. A session that thinks in angles but writes none has done half the thinking.

An angle is not:

- a separate architecture or alternative source of truth — the log rules; angles teach;
- a task, a backlog item, or a plan;
- a generic topic with no concrete question ("performance", "security");
- an exhaustive catalogue of related concerns;
- permission to reopen a locked decision silently; or
- mandatory paperwork — an angle with no collisions closes into a paragraph, not a file.

## Concrete journey — the intended life, then the observed one

### LOCKED — the full life has seven stations

```
identify (3–5 candidates from the problem's shape)
  -> present the agenda (operator amends: drop, add, reorder — logged)
  -> work angle by angle (open with the situation; forks per the Standard)
  -> WRITE the companion when the angle closes (collision-bearing angles only)
  -> review (the spec reviewer receives the companions, cross-checks them)
  -> reconcile (the session-end sweep: every doc's statuses vs every ruling)
  -> hand over (the operator receives the files, by link, at the gate)
```

Three stations deserve their "this means":

**The agenda is the session's spine, and it is the operator's.** Presenting it before the first clarifying question means the operator shapes *what gets examined*, not just what gets picked — the cheapest moment to redirect a session is before it starts. Emergent angles get added out loud ("this collision opens a new angle — adding it"), never worked silently; the agenda and its amendments are logged, because months later "why was X never examined?" is a real question the record must answer.

**Close-time writing is a timing law, not a formality.** The companion is written when its angle closes — not batched at session end — because the collision detail is hot exactly then: which alternatives were argued, what the operator's rider was, which consequence sealed it. The reference corpus wrote the same rule for itself ("write at the checkpoint… reconcile its rulings into the formal design anchors before committing") and this stream's own history is the counter-example: companions batched to the end came out as ~380-word citation lists, and companions demanded retroactively required a full evidence study to reconstruct what the hot version would have contained for free.

**The sweep makes the set self-consistent before anyone else reads it.** Rulings made late in a session routinely invalidate statuses written early in it. The last act re-checks every produced document against every D# of the session, flips what moved, and banners what died — the item-scale version of the architect's reconcile commit. A document set shipped without the sweep contains its own contradictions, and the reader cannot tell which side is current.

### LOCKED — the create-versus-subsection test guards the set's size

New angle only when the discussion introduces: a distinct authority or package boundary · a distinct state lifecycle · a complete journey nobody follows end to end · a parity question spanning contexts · a tension that can move several downstream models. It stays a *subsection of the current angle* when it is one field, one edge case, an implementation detail, another example of an explained rule, or resolvable without touching another angle. Reserve angles stay unnamed until a concern passes the test — no empty documents because a number was free.

### LOCKED — the depth bar and the register law

A companion is a TEACHING document: a stranger reads it and understands the design without opening the log. Its body is a concrete journey whose `### LOCKED — <claim>` subsections each close with "this means…"; its length is earned by domain complexity, never by the angle number — the reference corpus runs lean (~600 words) where the question is narrow and heavy (~3,000) where a journey demands it, and the density law underneath is *sections per thousand words*, not totals: no section exceeds ~160 words of unbroken prose. A companion that only cites D#s is an index wearing angle clothes. The register law (D66) fences this from the opposite failure: conversation economy never applies to deliverables, and deliverable depth never applies to messages.

## The observed life — how this very stream dropped its angles   (the evidence)

The skill's first live run under angle-first flow — this stream — hit four failures, each now a ruled fix:

1. **Angles were worked but not written.** Nine angles were examined; zero companions existed until the operator asked "what about angles?" — the checklist treated companions as a step-8 side effect with no teeth. *Fix: close-time writing (D65a).*
2. **The companions that then appeared were indexes.** ~380 words, cite-only, failing their own Purpose lines; a calibration review against the reference corpus measured the gap at 7×. *Fix: the depth bar in the template, with the corpus as the standing exemplar (D66/D67).*
3. **Nobody reviewed them.** The spec reviewer's inputs were spec + log only; the companions were a second, unchecked source of truth. *Fix: companions are required reviewer inputs with a cross-check row — contradictions with spec or log are blocking (D65b).*
4. **The operator never received them.** The review gate handed over the spec alone. *Fix: the gate message hands the operator every companion, by file link, beside the spec (D65c).*

## What the lifecycle cannot do

- Make a collision exist — an angle whose work surfaced no real tension closes without a companion, and that is success, not omission;
- replace the decision log — the log rules, with lineage and riders; companions teach the rulings;
- survive skipped sweeps — one unswept session leaves stale statuses that every later reader inherits;
- police itself — the reviewer's cross-check row is the enforcement; the checklist alone was proven insufficient by this stream's own history.

## Current mismatch

**MISMATCH:** the skill text carries the agenda-first flow and the Fork Presentation Standard, but steps 5/8/10/11 still encode the old lifecycle — no close-time clause, batch-style step-8 wording, reviewer inputs without companions, a gate that hands over only the spec. All four land at implementation Tasks 1–3; this stream's later angles (written close-to-hot, reviewed, calibrated) are the receipts that the target life produces the intended documents.

## Visible collisions

- **Angles as working method versus angles as deliverables.** A session can think brilliantly in angles and ship nothing — the two roles need separate teeth: the agenda serves the thinking; close-time writing serves the record. Conflating them is how the first run lost its documents.
- **Review cost versus a second truth.** Every artifact added to the reviewer's inputs grows the gate; but an unreviewed companion is an unaudited authority — the same disease the corpus's two-surface law exists to kill. The cost is paid because the alternative is silent drift between teaching and law.
- **Depth versus padding.** The depth bar could be gamed by length; the register law's own revisit clause guards the other flank — length must be earned by content, and a reviewer probe ("answer these questions from the angle alone") measures teaching, not words.

## Flexible and deferred

**FLEXIBLE:** the companion filename convention; how the sweep is recorded (its own commit vs the session's last). **DEFERRED, with landing place:** whether the sweep should be mechanically assisted (a stale-status grep over the session's documents) — folds into the census-script work at implementation Task 5.

## Reconciled outcome

**LOCKED:** the seven-station life (agenda logged · close-time writing · reviewer cross-check · session-end sweep · hand-over by link); the create-versus-subsection test with reserve angles; the depth bar and register law. The angle in one line: *an angle that was worked but never written, reviewed, and reconciled did half its job — the document is the second pass of the thinking, and the lifecycle exists to make that pass mandatory while the thinking is hot.*
