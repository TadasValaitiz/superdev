# Angles — contract, kinds, and how they stay honest

Derived from the operator's bench angle definition (2026-08-25) and the 12-angle bench series; generalised.

## Definition

An **angle** is a deliberately partial way to examine one shared architecture. It follows one important question, journey, boundary, or source of tension far enough to expose domain models, state transitions, authority, use cases, and consequences — reasoning deeply from one direction without pretending that direction is the whole system. Angles overlap on purpose: the value comes from making concerns collide and reconciling them into one coherent design.

**An angle is not:** a separate architecture or alternative source of truth · an implementation task or plan · a generic topic with no concrete question · an exhaustive catalogue · permission to reopen LOCKED decisions silently · a module/component view (that mirrors code and kills holism).

## The contract — every angle carries {#angle-contract}

- **Purpose**, one reader-oriented sentence ("make X understandable without reading Y").
- **Formal anchors** — the D#s and glossary entries it renders. *Angles are prose over rulings; the decision log owns the forks.*
- **Series position** (`N of M`) and a row in `angles/INDEX.md` (number · purpose one-liner · anchors · last-updated · DOC-MARK counts).
- **DOC-MARK statuses** throughout — LOCKED/FLEXIBLE/DEFERRED/BLIND/MISMATCH/SEED-ILLUSTRATIVE.
- **The five useful-angle properties:** one central question · explicit boundaries (where the journey starts, stops, and who owns what's outside) · concrete domain consequences (named states, model sketches, call sites) · **visible collisions** (where forces pull apart) · a reconciled outcome. Length is earned by domain complexity, never by angle number.

## The five kinds {#five-kinds}

| kind | follows | example |
|---|---|---|
| policy/semantics | the system as one question and its answer | "what does the Bench do each time it may decide?" |
| algebra | one calculus made readable | capital/cash/regime allocation |
| journey | one entity end-to-end (exposes seams component views hide) | one deployment, one adaptation fit, one item's life |
| boundary | one seam examined from both sides | portable core vs runtime; operator's attention |
| map | current code → target (the only backward-looking angle) | KEEP/RESHAPE/REPLACE/DEFER by call site |

Angles may carry **Pydantic invariant sketches** (FLEXIBLE by default — responsibilities and invariants, never final field names) and **functional-core / imperative-shell pseudo-code** walkthroughs.

## When to create a new angle

A residue cluster that fits no existing angle · a distinct authority or package boundary appears · a journey nobody follows end to end · a collision two angles both touch but neither owns. Create it in the session; never fork an existing angle.

## Anti-loosening — how the set stays honest {#anti-loosening}

1. **The angle sweep** is the mandatory last act of every session: every angle whose anchors were touched is updated *in that session*, superseded in place, never copied.
2. **Staleness is mechanical:** grep an angle's cited D#s against the decision log's statuses; a superseded citation puts the angle on the next agenda.
3. **INDEX.md is the bloat display:** last-updated and DOC-MARK counts per angle. Sets beyond ~15 angles merge at a session.

## Item angles {#item-angles}

The same idea at item scale, written by `brainstorming`, living **beside the item's spec** (never in `design/angles/`), same five properties, no INDEX/sweep obligations. Repetition with system angles is expected and fine — system angles skip details deliberately; item angles are where details live. An item angle that contradicts a system angle is residue, not a local ruling.
