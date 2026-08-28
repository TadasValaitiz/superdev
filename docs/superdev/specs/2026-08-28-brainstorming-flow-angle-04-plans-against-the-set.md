# Brainstorming Angle 4 — Plans answer to the whole set

**Purpose:** understand what an implementation plan is accountable to when the design documents are a SET — spec, angles, census, log — and what governs when they disagree or the spec is silent, without reading the skill.
**Authority:** teaches ruled design (D71) — the log is the law.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D71 · D66 (register law) · [experience design](./2026-08-28-brainstorming-experience-design.md) BR2–BR8 (what angles uniquely carry).
**Series:** 4 of 4 (brainstorming flow).

> **Status guide:** LOCKED operator-ruled · MISMATCH current skill text behaves differently today ·
> SEED-ILLUSTRATIVE worked example only, never a measurement.

## The central question

When a plan is written, what is it checked against — and who wins when the documents that describe one design say different things?

## The mental model

The session's output is not a document; it is a SET with a division of labor. The **log** rules (every fork, with lineage). The **spec** anchors (requirements, acceptance, the composed shape — deliberately compressed). The **angles** teach (journeys, collisions, capability fences, mismatches — deliberately expansive). The **census** grounds (what was true, tiered). Compression is the spec's job, which means the spec *provably drops content the angles keep* — that is by design, not a defect. A plan that answers only to the spec therefore answers to a lossy projection of the design.

The set is not:

- redundant copies of one truth — each document keeps what the others drop;
- a precedence ladder where the spec outranks the angles — both TEACH rulings; only the log RULES;
- optional context — a plan's context pack that omits an existing companion is incomplete by definition; or
- self-reconciling — agreement across the set is manufactured by the reconcile sweep, never assumed.

## Concrete journey — one plan, written wrong and then right   (SEED-ILLUSTRATIVE)

A plan is written for the config-loader design from the spec alone. The spec's §5 says "the merged result is frozen at startup." The plan schedules a task: "add a test helper that mutates config in place for fixture setup" — reasonable-looking, spec-compatible. But the *angle's* "What the config loader cannot do" section (content the spec compressed away) forbids exactly this, and its decision entry's anti-patterns line names it: *"no test helper that mutates the frozen object in place."* No reviewer catches it, because no reviewer received the angle. The violation ships.

Same plan, under the full-set contract:

### LOCKED — the context pack lists every companion, and Read-first slices them

The plan's context pack enumerates the whole set — spec, log, every angle file, census. Each task's Read-first line cites the governing *angle sections*, not just spec §s: the implementer touching the publish step reads the angle's freeze journey and its cannot-do fence before coding. **This means:** the content the spec compressed away still reaches the person whose work it governs — through the document written to teach it.

### LOCKED — where the spec is silent, the angle governs

The mutation-helper task dies at self-review: the checklist walks each angle's "cannot do" and "Visible collisions" against the task list, and the helper crosses a fence. The angle's authority here is not its own — it teaches a ruling and cites its D#; the plan is obeying the log *through* the angle. **This means:** "the spec doesn't mention it" is never license; silence in the compressed document defers to speech in the expansive one.

### LOCKED — where spec and angle contradict, the plan stops

If the spec said "config may be reloaded" while the angle said "frozen forever", the planner does NOT pick the more convenient reading. A contradiction inside the set is a failed reconcile sweep — the set goes back to be reconciled (drift protocol, new D# if the fork is real) before planning proceeds. **This means:** plans never launder document drift into build decisions; the one authority that can resolve a contradiction is the log, via a ruling.

### LOCKED — the plan reviewer receives the set

The fresh-eyes plan reviewer gets what the author got — and probes the same fence-walk from outside. A discharged-hint table that no angle contradicts is now a checkable claim.

## What the full-set contract cannot do

- Resolve spec-vs-angle contradictions — only a ruling can; the contract just refuses to plan over them;
- substitute for the reconcile sweep — it catches leaks at planning time; the sweep prevents them at writing time;
- make a bad angle good — a cite-only companion teaches nothing to check against (the depth bar is upstream of this);
- rank angles above the log — lineage always terminates in a D#.

## Current mismatch

**MISMATCH:** writing-plans SKILL.md today plans against "the spec"/"the anchor" alone — its context pack template, self-review, and plan-reviewer prompt all omit angle companions and census. The four mechanics above land at implementation Task 5c; this angle is their target-state description.

## Visible collisions

- **Compression versus completeness:** the spec must stay readable in one sitting, so it drops what angles keep — the collision is resolved by routing, not by fattening the spec: each reader gets the document written for their need, and the plan's Read-first is the router.
- **Reading budget versus safety:** "read all companions" grows with angle count; bounded today by item scale (2–6 angles) and by Read-first slicing — D71's revisit clause owns the day a set outgrows this.

## Flexible and deferred

**FLEXIBLE:** exact wording of the self-review fence-walk; whether census joins Read-first lines or stays pack-level. **DEFERRED, with landing place:** a per-area angle index inside the spec (activates via D71's revisit clause if angle counts break planning budgets).

## Reconciled outcome

**LOCKED:** plans answer to the union — log rules, spec anchors, angles teach, census grounds; angle content governs spec silence; contradictions stop planning; context pack, Read-first, self-review, and plan reviewer all carry the set. In one sentence: *a plan that answers only to the spec answers to a lossy projection — the set is the design, and the plan is accountable to all of it.*
