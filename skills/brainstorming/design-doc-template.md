# Design Document Template

The design doc is written in **two passes** (see SKILL.md). Pass 1 lays down the shape
(§1, §3, §4, §8). Pass 2 enriches it with everything that is NOT the design itself but
governs it: requirements (§2), decisions with reasoning and revisit-hooks (§5),
assumptions (§6), declined scope (§7), and the narrative link-sentences that open every
design area. A design doc that skips pass 2 is a sketch, not a spec.

**The traceability rule (what makes the doc coherent instead of scattered):**
requirements are numbered `R1..Rn`, decisions are numbered `D1..Dn`, and every design
area cites the R#/D# it serves. A reader must be able to trace any component back to a
requirement and a decision — and any requirement forward to the area that satisfies it.
An area with no R#/D# is unjustified scope; an R# no area serves is an unmet requirement.
Both are review-blocking.

**The narrative rule:** §3 tells the story of the design as one connected argument —
problem → chosen shape → why this shape → how the areas compose into the whole. Every
§4 area then OPENS with one sentence naming its role in that story. If you cannot write
that sentence, the area doesn't belong in this spec (or the narrative is missing a beat —
fix whichever is true).

---

```markdown
# <Topic> — Design

**Date:** YYYY-MM-DD · **Status:** draft | approved | superseded-by <path>
**Decision log:** ./YYYY-MM-DD-<topic>-decisions.md   ← full deliberation trail lives there
**Predecessors / companions:** <related specs, or "none">
**Origin:** brainstorm with <human> | self-brainstorm run <workflow run id>

## 1. Problem & intent

Why this work exists, in prose. What hurts today (with evidence — file paths, measured
numbers, observed failures), what changes when this lands, and the success criteria —
measurable where possible. A stranger should be able to read only this section and
correctly guess most of the design.

## 2. Requirements

Requirements are design-independent: they survive any redesign. If deleting a
requirement would not change what must be built, it isn't one — cut it.

| ID | Requirement | Source | Priority | Acceptance signal |
|----|-------------|--------|----------|-------------------|
| R1 | <what must be true> | stated / discovered / assumption (A#) | must / should | <how we'll know> |

Include non-functional requirements (performance floors, compatibility, operational
constraints) — these are the ones most often lost between brainstorm and build.

## 3. Approach narrative

The through-line, in prose (not bullets). From the problem to the chosen shape; why this
shape won over the alternatives (cite D#); and how the areas in §4 compose into one
system — what talks to what, in what order, and why the boundaries fall where they do.
This section is the connective tissue reviewers check the rest of the doc against.

## 4. Design

One subsection per area. Each area MUST open with its narrative link-sentence.

### 4.x <Area>

<Link-sentence: the role this area plays in the §3 story.>

- **Design:** the actual shape — structures, flow, behavior.
- **Interface / contract:** what consumers see; what this area promises.
- **Depends on:** other areas, external systems.
- **Serves:** R#… · **Governed by:** D#…

## 5. Decisions

The distilled record — one entry per fork that shaped this design. The full deliberation
trail (including rejected lines of questioning) lives in the decision log; IDs are shared
between the two files.

### D<n> — <short title>   (status: locked | provisional | superseded-by D<m>)

- **Decision:** what was chosen.
- **Alternatives:** each with what it gains and what it sacrifices.
- **Why:** the reasoning that picked the winner — evidence over taste where possible.
- **Revisit-when:** <the concrete trigger that reopens this decision — e.g. "if the
  parser needs streaming input", "if profile shows >100ms here", "if upstream ships X">.
  This is the hook the build phase checks when reality drifts from the spec. Every
  decision has one; "never" must be argued, not defaulted.

## 6. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | <what we're assuming without evidence> | R#/D#/§4.x | unratified / ratified by <who, when> / refuted → see D# |

Assumptions are honest debts. A self-brainstormed spec leads with this section in its
hand-off — nothing implementation-critical may rest on an unratified A#.

## 7. Not doing

Declined scope, with why — the YAGNI ledger. This section prevents the next reader
from "discovering" an idea that was already weighed and rejected.

- <feature/direction> — rejected because <reason>; reconsider if <condition>.

## 8. Testing & validation

How we'll know it works: test approach per area, and an acceptance mapping — every
must-R# names the test/probe/measurement that will demonstrate it.

## 9. Drift protocol

When build reality contradicts this spec (an interface won't hold, a dependency
misbehaves, a task uncovers a missing requirement):

1. Find the governing D# and check its revisit-when trigger.
2. Append the new fork to the decision log (same D-numbering, phase: build) — decide
   there, or escalate if the trigger says a human owns it.
3. Amend this spec: flip the D# status (superseded-by, never silently edited), update
   the affected §4 area and R# rows.
4. Never erase — the superseded path stays visible; that's what makes the doc
   trustworthy months later.
```
