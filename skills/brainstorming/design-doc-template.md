# Design Document Template

The design doc is the **anchor** for the whole build — the single file that carries the
initial idea, the context, the reasoning, the use cases, and the acceptance bar, plus the
design that delivers them. Acceptance lives HERE, not in the plan: the plan executes
against this doc and proves it at the gates.

**The anchor region — frozen, but not rigid.** §1 intent, §2 requirements, §3 use cases,
and the §9 acceptance *hints* are the anchor: reality is measured against them, and they
are **never silently edited to match what got built**. They bend only by an *owned*
change:

- **Autonomous build (most work):** when a requirement/use-case must soften, or a slice
  must defer, **file a backlog item that names the UC#/R# it discharges**, then proceed
  and close. Development never blocks on the anchor.
- **Human-in-loop build:** when deviation is *large* (many hints unmet, or a use case
  materially changed), **push the divergence to the human before finishing** — not after.

The design region (§4–§8) evolves freely as you build, via the §10 drift protocol. The
line between the two is the whole point: the *what / why / done-bar* stays stable; the
*how* is discovered.

**Two passes.** Pass 1 lays the shape and the anchor (§1, §2, §3, §4, §9). Pass 2
enriches with what governs the design: decisions with revisit-hooks (§6), assumptions
(§7), declined scope (§8), and the narrative link-sentences that open every design area.
A design doc that skips pass 2 is a sketch, not a spec.

**The traceability rule (what makes the doc coherent instead of scattered):**
requirements `R1..Rn`, use cases `UC1..UCn`, decisions `D1..Dn`, acceptance hints
`AH1..AHn`. Every design area cites the R#/D# it serves; every use case maps to the R# it
exercises and the §4 areas that realize it; every acceptance hint names the UC#/R# it
proves. An area serving no R#/UC# is scope creep; an R# or UC# no area serves is unbuilt
scope; a must-R#/UC# with no acceptance hint has no done-bar. All review-blocking.

**The narrative rule:** §4 tells the story of the design as one connected argument —
problem → chosen shape → why this shape → how the areas compose. Every §5 area OPENS with
one sentence naming its role in that story.

---

```markdown
# <Topic> — Design (anchor)

**Date:** YYYY-MM-DD · **Status:** draft | approved | superseded-by <path>
**Mode:** autonomous | human-in-loop   ← governs how anchor deviations route (see top)
**Decision log:** ./YYYY-MM-DD-<topic>-decisions.md   ← full deliberation trail
**Companions:** <-cli-surface.md if commands change; related specs, or "none">
**Origin:** brainstorm with <human> | self-brainstorm run <workflow run id>

## 1. Problem & intent   [ANCHOR]

Why this work exists, in prose. What hurts today (with evidence — file paths, measured
numbers, observed failures), what changes when this lands, and the success criteria. A
stranger should read only this section and correctly guess most of the design.

## 2. Requirements   [ANCHOR]

Requirements are design-independent: they survive any redesign. If deleting a
requirement would not change what must be built, it isn't one — cut it.

| ID | Requirement | Source | Priority | Acceptance signal |
|----|-------------|--------|----------|-------------------|
| R1 | <what must be true> | stated / discovered / assumption (A#) | must / should | <how we'll know> |

Include non-functional requirements (performance floors, compatibility, operational
constraints) — the ones most often lost between brainstorm and build.

## 3. Use cases   [ANCHOR]

The concrete workflows in the operator's/user's OWN terms — what they DO and what they
SEE, end-to-end. A use case is a journey; a requirement (§2) is a property that journey
must have. These are the work's reason; §9 proves each one runs on the real surface.

| UC | As a <role>, I <do this> and see <this> | Exercises R# | Realized by §5 area(s) |
|----|------------------------------------------|--------------|------------------------|
| UC1 | place an order and get a fill or an honest refusal | R1, R3 | 5.2, 5.4 |

Write them at the altitude the operator described — "place an order and see a fill,"
not "call place_order()." A UC no §5 area realizes is unbuilt scope; a §5 area no UC
needs is scope creep.

## 4. Approach narrative

The through-line, in prose. From the problem to the chosen shape; why this shape won
(cite D#); how the §5 areas compose into one system — what talks to what, in what order,
why the boundaries fall where they do. The connective tissue reviewers check the rest
of the doc against.

## 5. Design

One subsection per area. Each MUST open with its narrative link-sentence.

> **Conditional sections:** work touches domain objects → one area is the **Domain
> model** section per `domain-design-template.md` (diagram, naming discrepancy table,
> add/remove delta ledger, invariants with enforcers, CLI↔domain mapping). Commands
> added/changed → the separate `…-cli-surface.md` companion (per `cli-surface-template.md`)
> is required and linked in the header.

### 5.x <Area>

<Link-sentence: the role this area plays in the §4 story.>
**Status:** `DOC-MARK[LOCKED|FLEXIBLE|DEFERRED|BLIND|MISMATCH|SEED-ILLUSTRATIVE][D#|owner]` — epistemic, per superdev:system-design `map-and-markers.md#doc-mark`; when a corpus exists, cite the governing map row / system-angle passage at file:line.

- **Design:** the actual shape — structures, flow, behavior.
- **Interface / contract:** what consumers see; what this area promises.
- **Depends on:** other areas, external systems.
- **Serves:** R#… · **Governed by:** D#… · **Realizes:** UC#…

## 6. Decisions

The distilled record — one entry per fork that shaped this design. Full trail (including
rejected lines) lives in the decision log; D-numbers are shared between the files.

### D<n> — <short title>   (status: locked | provisional | superseded-by D<m>)

- **Decision:** what was chosen.
- **Alternatives:** each with what it gains and sacrifices.
- **Why:** the reasoning that picked the winner — evidence over taste where possible.
- **Revisit-when:** <concrete trigger that reopens this — "if the parser needs streaming",
  "if profile shows >100ms here">. The hook the build phase checks under drift. "Never"
  must be argued, not defaulted.

## 7. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | <assuming without evidence> | R#/UC#/D#/§5.x | unratified / ratified by <who,when> / refuted → D# |

Assumptions are honest debts. A self-brainstormed spec leads its hand-off with this
section — nothing implementation-critical may rest on an unratified A#.

## 8. Not doing

Declined scope, with why — the YAGNI ledger. Prevents the next reader from
"discovering" an idea already weighed and rejected.

- <feature/direction> — rejected because <reason>; reconsider if <condition>.

## 9. Acceptance — hints & receipts   [ANCHOR: the hints]

The done bar, in two columns filled at two different times:

- **Hint (now, at brainstorm):** the capability that must be demonstrable, in the
  operator's language — NOT a pinned command. "A declarative act-ratified regime drives a
  bench switching read end-to-end." A hint names *what must be true* and leaves *how it's
  proven* open. Concrete criteria written before code either over-specify (and get
  renegotiated quietly mid-build) or pass vacuously — a hint can't be satisfied by drift
  because you cannot quietly abandon a named capability.
- **Receipt (later, at the gate):** ONE piece of re-runnable evidence per hint — a test
  name + output, a CLI transcript, or a file:line — assembled when the real surface
  exists. A claim without a receipt is not an answer. An unanswered hint is NAMED, never
  papered over, and routed per the anchor's soften-but-own rule (owned backlog item in
  autonomous mode, human pushback in HIL mode).

| # | Acceptance hint (operator terms) | Proves | Lane | Receipt (filled at gate) |
|---|----------------------------------|--------|------|--------------------------|
| AH1 | <capability that must be demonstrable end-to-end> | UC1 / R3 | fast/slow | <test/transcript/file:line> |

Every must-R# and every UC# is covered by ≥1 hint. New tests are fast by default, slow
only when categorically necessary (test-driven-development/testing-lanes.md) — the
fast-suite budget is a design constraint on test design, not an afterthought.

## 10. Drift protocol

Governs the DESIGN region (§4–§8). Anchor-region changes (§1/§2/§3/§9-hints) follow the
soften-but-own rule at the top of this file, never silent edits.

When build reality contradicts a §5 area (an interface won't hold, a dependency
misbehaves, a task uncovers a missing requirement):

1. Find the governing D# and check its revisit-when trigger.
2. Append the fork to the decision log (same D-numbering, phase: build) — decide there,
   or escalate if the trigger says a human owns it.
3. Amend the affected §5 area and flip the D# status (superseded-by, never silently
   edited). If the drift reaches into the anchor (an R#/UC#/hint can't hold), STOP the
   silent edit — run the soften-but-own rule (file the item, or push to the human).
4. Never erase — the superseded path stays visible; that's what makes the doc
   trustworthy months later.
```
