# Item angle template — the teaching form

An item angle is a deliberately partial way to examine THIS item's design: it follows one
question, journey, boundary, or tension far enough to expose consequences. It lives beside
the item's spec (`YYYY-MM-DD-<topic>-angle-NN-<slug>.md`); no INDEX or sweep obligations at
item scale. Repetition with system angles is expected. Full theory: superdev:system-design
`angle-guide.md`.

**The depth bar (register law, D66):** an angle companion is a TEACHING document — a
stranger reads it and understands the design *without opening the decision log*. Its length
is earned by domain complexity, never by the angle number: lean questions close in ~600
words, heavy journeys may need ~2,000+. The density law underneath is sections-per-thousand-
words, not totals — no section carries more than ~160 words of unbroken prose. **A companion
that only cites D#s is an index wearing angle clothes; delete it and write the angle.**

**When it is written:** at the angle's CLOSE, while the collision detail is hot — never
batched to the session's end. An angle that carried no real collisions closes into a
paragraph of the session record instead; that is success, not omission.

**Anchor precision:** decision IDs with relative links to the governing log/design; §-level
anchors are acceptable for same-directory companions, file:line for anything farther.

```markdown
# Angle N — <one-phrase name>

**Purpose:** <one reader-oriented sentence: understand X without reading Y.>
**Formal anchors:** [decision log](./<file>.md) D#… · <governing design §…> ·
**Series:** N of M.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it (named below) · MISMATCH current code/text behaves
> differently today · SEED-ILLUSTRATIVE worked example only, never a measurement.
> <Gloss every status the body actually uses — a guide listing four while the body uses
> six is the sharpest self-inconsistency a reviewer will find.>

## The central question
<one sentence, self-contained — no term a stranger hasn't met yet.>

## The mental model
<Orient before detailing. An analogy from outside the domain where one exists ("adaptation
is a LoRA-style overlay: the base is frozen, only a bounded layer learns"). Then the
negative space — "It is not:" followed by the 3–6 most likely WRONG intuitions, each
demolished in a line. Every misreading met at the door.>

## Boundaries
<Where this journey starts, where it stops, which neighbouring concern owns what's outside
— and which OTHER ANGLE owns each excluded piece, by number.>

## Concrete journey
<The heart. Walk one entity/scenario end to end. One `###` subsection per load-bearing
ruling:>

### LOCKED — <the claim, as a sentence>
<The ruling explained in prose, with its shape shown where shape exists — a small frozen
model, a formula, a file tree, a message flow, labeled with its epistemic weight
("FLEXIBLE sketch around locked laws"). Then ALWAYS the consequence: "This means…" —
2–3 concrete things the reader can now rely on. A LOCKED without its consequence is
the cheapest fix a reviewer will demand.>

<Where the design serves more than one host/context, walk the SAME law once per host as
`->` flows — difference-under-repetition is how a boundary teaches itself. Use tables for
ownership, comparisons, and repeated mappings. Label invented figures SEED-ILLUSTRATIVE;
cite measured ones with their source.>

## What <the subject> cannot do
<Capability fences as first-class content — the reader asking "can I…?" finds the no
before building the yes. Include what the design does NOT guarantee.>

## Current mismatch
<How today's code/text differs from the ruled target — honest MISMATCH claims, with
SALVAGE: which existing precedents are worth keeping and why. Omit only if genuinely none.>

## Visible collisions
<Tensions the journey did NOT already settle — "X versus Y: <the mechanism that resolves
or bounds it>", one line each. Never re-argue a fork the journey settled; collisions that
merely repeat the journey are the most common padding a reviewer will cut.>

## Flexible and deferred
**FLEXIBLE:** <what may still move, and within what bounds.>
**DEFERRED, with landing places:** <each deferral names the session/design that owns it —
bare "later" is a finding. "DEFERRED: none" requires checking the governing D#s'
revisit-when clauses first; they are usually live.>

## Reconciled outcome
<What is LOCKED / FLEXIBLE / DEFERRED after this angle, in one short paragraph, closing
with the angle's whole content in one sentence.>
```

---

## Worked excerpt (from a real angle — the bar, made concrete)

> ## The mental model
>
> The execution proposal translates *"what must be true"* (the corpus) into *"in what
> order it becomes demonstrable"* (a delivery hypothesis). It sits between system design
> and item design and is deliberately neither.
>
> It is not:
> - architecture — it rules nothing about the domain;
> - a schedule — dates and room budgets live in the charter graph;
> - an authorization to write code — it explicitly authorizes none;
> - a locked document — its own status line says *reconcilable, not locked*.
>
> ### LOCKED — the orchestrator is sole writer, and the method outlived the owner
>
> The proposal lives at `docs/orchestration/execution/<milestone>-proposal.md`,
> orchestrator-written. The reasoning that moved it there: design *knowledge* is delivered
> by the corpus, which anyone can read — the architect's contribution is already on disk
> before the proposal work begins. Grouping deliverables is execution *judgment*, which is
> the orchestrator's charter. **This means:** the corpus is the interface between the two
> altitudes, and it must carry everything the proposal needs — when it doesn't, the gap
> surfaces as a withheld charter, not as the architect stepping in.

The excerpt shows the moves in miniature: analogy-free but contrast-rich mental model;
the ruling as prose with its reasoning; the bolded consequence. Write every section to
this bar or leave the angle unwritten until you can.
