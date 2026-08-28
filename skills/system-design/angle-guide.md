# Angles — contract, kinds, and how they stay honest

Derived from the operator's bench angle definition (2026-08-25) and the 12-angle bench series; generalised.

## Definition

An **angle** is a deliberately partial way to examine one shared architecture. It follows one important question, journey, boundary, or source of tension far enough to expose domain models, state transitions, authority, use cases, and consequences — reasoning deeply from one direction without pretending that direction is the whole system. Angles overlap on purpose: the value comes from making concerns collide and reconciling them into one coherent design.

**An angle is not:** a separate architecture or alternative source of truth · an implementation task or plan · a generic topic with no concrete question · an exhaustive catalogue · permission to reopen LOCKED decisions silently · a module/component view (that mirrors code and kills holism).

## The contract — every angle carries {#angle-contract}

- **Purpose**, one reader-oriented sentence ("make X understandable without reading Y").
- **Formal anchors** — the D#s and glossary entries it renders. *Angles are prose over rulings; the decision log owns the forks.*
- **Series position** (`N of M`) and a row in the milestone INDEX file (`…-architecture-angles.md`, flat corpus — D69) (number · purpose one-liner · anchors · last-updated · DOC-MARK counts).
- **Marker statuses** throughout — LOCKED/FLEXIBLE/DEFERRED/BLIND/MISMATCH/SEED-ILLUSTRATIVE, in the positional grammar (D53/D70: line-initial claim markers, Status lines, heading markers; the DOC-MARK bracket is retired — full rewrite lands at implementation Task 5).
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

## When to create a new angle — and when NOT to

**Create** when the discussion introduces: a residue cluster that fits no existing angle · a distinct authority or package boundary · a distinct state lifecycle · a complete journey nobody follows end to end · a parity question spanning multiple shells · a collision two angles both touch but neither owns · a tension that can change several downstream models or interfaces. Create it in the session; never fork an existing angle.

**Keep it as a subsection of the current angle** when it is only: one field or naming choice · one refusal or edge case inside the same lifecycle · an implementation detail that doesn't change the domain contract · another example of an already-explained rule · a question resolvable without affecting another angle.

**Reserve angles stay unnamed and unwritten** until a concern passes the create test — no empty documents or scope expansion merely because a number was available.

## How an angle moves through a session {#angle-movement}

1. **Frame it** — central question, current context, boundaries, in prose, before any option appears.
2. **Explore one decision at a time** — present enough architecture and code context for the operator to reason without having written the implementation (this is the brainstorming skill's Fork Presentation Standard, at architecture scale).
3. **Collide alternatives** — two or three materially different approaches with gains, sacrifices, and a recommendation.
4. **Log every resolved fork immediately** — decision, rejected alternatives, reasoning, revisit-when; never batch-reconstruct.
5. **Follow consequences** — check the ruling against the domain models, runtimes, journeys, and current code it touches.
6. **Close the angle** — summarize what is LOCKED, FLEXIBLE, DEFERRED, MISMATCH — and name what remains BLIND (not yet examined — say so honestly); do NOT turn unresolved implementation work into guessed architecture.
7. **Write at the checkpoint** — produce/update the readable companion and reconcile its rulings into the formal anchors before the reconcile commit (the architect's sitting-close, D52).

**Revisit discipline:** a later angle may expose a real conflict in an earlier one — reopening requires a NEW decision entry and an explicit amendment. Overlap is never permission for silent drift.

## Presentation convention {#angle-presentation}

Plain explanation first; models or short flows only where they improve understanding. Small Pydantic examples for domain shapes; explicit use cases for behavior; tables for ownership, comparisons, and repeated mappings. Visuals are optional and must be accompanied by an understandable text explanation — never forced. Label claims with the positional marker statuses (`map-and-markers.md#doc-markers` — claim/Status/heading forms, D53/D70); label illustrative quantities SEED-ILLUSTRATIVE (never present an example as measured). Once a fork is resolved, the written angle records the SELECTED architecture and why — it never preserves a recommendation as though the choice were still pending.

## Anti-loosening — how the set stays honest {#anti-loosening}

1. **The angle sweep** is the mandatory last act of every session: every angle whose anchors were touched is updated *in that session*, superseded in place, never copied.
2. **Staleness is mechanical:** grep an angle's cited D#s against the decision log's statuses; a superseded citation puts the angle on the next agenda.
3. **INDEX.md is the bloat display:** last-updated and DOC-MARK counts per angle. Sets beyond ~15 angles merge at a session.

## Item angles {#item-angles}

The same idea at item scale, written by `brainstorming`, living **beside the item's spec** (never in `design/angles/`), same five properties, no INDEX obligations (the brainstorm SESSION's reconcile sweep does apply to them; the corpus-level angle sweep does not). Repetition with system angles is expected and fine — system angles skip details deliberately; item angles are where details live. An item angle that contradicts a system angle is residue, not a local ruling.
