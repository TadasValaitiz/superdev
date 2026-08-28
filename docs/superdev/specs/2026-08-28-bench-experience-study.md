# The Bench Experience — a study of what the Codex harness actually produced

**Date:** 2026-08-28 · **Status:** evidence document (read-only record; feeds the brainstorming
experience design)
**Evidence base:** ai-trading-calibration, branch `item/bench-architecture` —
`docs/superpowers/specs/`: 21+ angles, 5 design anchors, decision log D350–D494, census,
angle-definition doc, celebration-led execution proposal, continuation handover. Read in
full for this study: angle-19 (study journey), angle-06 (adaptation journey), D461 (a
representative decision entry), the angle-definition-and-template doc, and the heads of the
census, handover, INDEX, and execution proposal.

## Why this study exists

The operator ran months of architecture work through Codex- and Claude-driven design rooms
and judged the resulting experience — the documents, the option-picking, the way rulings
accumulate — markedly better than what superdev's brainstorming skill produces. This study
names WHAT is better, with quoted evidence, so the skill can be rebuilt to produce it
rather than to gesture at it. The one-line verdict up front: **the bench documents teach;
brainstorming's documents record. Teaching is the product.**

---

## Part 1 — What a bench angle document does (and mine did not)

### 1.1 It opens with a mental model, taught by analogy and by contrast

Angle-06's first section after the header is not content — it is orientation:

> "Adaptation is a small learned overlay on an immutable deployed base. It resembles a
> LoRA-style adjustment in spirit: the main model/program remains fixed and only a
> declared, bounded coefficient layer changes.
>
> It is not:
> - a new Bench deployment for every fit;
> - arbitrary replacement of base parameters;
> - a database row that every consumer reads as global latest; or
> - an exchange/Nautilus software adapter."

Two techniques in eight lines: an analogy from outside the domain (LoRA) that installs the
right intuition instantly, and a **negative-space list** that demolishes the four most
likely wrong intuitions before they form. Every misreading the document's future reader
would bring is met at the door. Nothing in my discarded companions did either.

### 1.2 Claims are typed sketches, not prose about types

Where a ruling has shape, the shape appears — as a small, frozen, readable model:

```python
AdaptationProgram = StrategyWeightProgram | MemberGrantProgram

-base_grant <= fitted_delta <= 0
effective_grant = base_grant + fitted_delta
```

and the document is explicit about the epistemic weight: "This is a **FLEXIBLE model sketch**
around locked identity and authority rules." The sketch carries the semantics; the label
prevents the sketch's incidental details (field names) from hardening into law. The
angle-definition doc makes this a convention: "Prefer small Pydantic examples for domain
shapes and explicit use cases for behavior."

### 1.3 Every LOCKED claim is followed by its consequence, spelled out

Angle-19, after the manifest-freezing rule:

> "This means the operator knows what was declared, not only what happened to finish.
> Parallel workers cannot change candidate membership. A sampler upgrade cannot alter an
> already-open study."

The pattern is *claim → "this means" → three concrete things the reader can now rely on*.
The ruling is not merely stated; its protective work is demonstrated. This is the single
cheapest technique in the corpus and the one whose absence makes a document feel like an
index.

### 1.4 Journeys are walked per host, showing law vs orchestration

Angle-06 walks the SAME adaptation law twice — "The paper-wallet journey" (queued,
asynchronous, wallet keeps its current adjustment on failure) and "The historical replay
journey" (synchronous, waits at the boundary) — as `->` text flows. The reader learns
which parts are law (identical in both walks) and which are host orchestration (everything
that differs). Difference-under-repetition is how the boundary teaches itself.

### 1.5 Negative space is first-class: "What adaptation cannot do"

Seven bulleted prohibitions, then the reason the last one matters. Capability fences get
their own section, not a parenthetical. A reader asking "can I…?" finds the no *before*
building the yes.

### 1.6 Honest mismatch, with salvage

"Current code mismatch and useful seams" names exactly how today's code differs from the
ruled design AND which existing precedents are worth keeping ("`domain/knobs/apply.py`
demonstrates infrastructure-free application logic"). Mismatch sections that only condemn
teach half as much as ones that also salvage.

### 1.7 Deferrals name their landing place

"**DEFERRED:** these become decisions in the adaptive replay, optimization, and paper-wallet
sessions." — not "later", but *which future session owns it*. And flexibility has an edge:
"Replay bootstrap is no longer flexible: adaptation begins cold at the evaluation boundary
(D427)" — the document updates its own flexibility claims as rulings land, which is what
reconciliation looks like from inside a document.

### 1.8 Collisions are one-line tensions with their resolution attached

Angle-19: "**Parallelism versus reproducibility:** workers may finish out of order, but the
frozen manifest and fresh replay state make completion order economically irrelevant." —
name the two forces, state the mechanism that dissolves them, one line. Four of these end
the angle. They read as the residue of real arguments, because they are.

---

## Part 2 — What a bench decision entry does (D461 dissected)

The entry header:

> **When:** 2026-08-27T10:03:00+03:00 · **Phase:** optimization brainstorm · **Status:** locked for MVP architecture
> **Decided by:** operator (live, in-session; selected C with an explicit sampler-extensibility requirement)

Notice `selected C with an explicit … requirement`. The selection EVENT is recorded — not
just the outcome, but that the operator picked a lettered variant AND attached a rider.
The picking experience supports amendment: an option is not take-it-or-leave-it; the
operator's pick can carry a requirement that becomes part of the law.

The body's discipline, section by section:

- **Trigger** names the ambiguity that forced the fork: "`seeded allocation sampler` was
  ambiguous with outcome-fitted calibration" — future readers know *why* this fork existed.
- The decided law includes **"Not X" clarifications** ("Not isotonic calibration: … It is
  neither a sampler variant nor an allocation candidate generator") — negative space again,
  at ruling granularity.
- An **extension law**: what every future addition of this kind must contribute — the ruling
  governs its own descendants.
- **Named anti-patterns**: "No opaque plugin bag: sampler-specific fields do not live in
  `dict[str, Any]`" — the ruling forbids the specific cheap escape its implementers would
  reach for.
- **Rests on:** D382–D385, D397, D403, D425, D449, D451, D459–D460 — backward lineage.
  **Affects:** the forward surface list. Between them, the entry is a graph node, not a note.
- **Revisit-when** is a falsifiable condition, not a date.

Superdev's decision-log template has Trigger/Options/Why/Revisit-when. It lacks: the
selection event, Rests-on/Affects lineage, extension laws, named anti-patterns, and "Not X"
clarifications. Those five are where the bench log's arbitration power lives.

---

## Part 3 — The process qualities around the documents

1. **Census before design.** The room's first artifact was a measured census with a
   provenance vocabulary — MEASURED / READ / FLAGGED — and the doc says plainly:
   "FLAGGED … are the work queue, not conclusions." Brainstorming's "explore project
   context" step produces no artifact and has no honesty tiers.
2. **Inputs are not rulings.** Four Codex seat reports arrived labeled "INPUTS, NOT
   RULINGS… Nobody has adjudicated them"; reconciling them WITH the operator was the work.
   The experience of picking options at its best: materially different, fully-argued
   variants colliding in front of the operator.
3. **Documents are written DURING the process, reconciled at checkpoints** — the angle
   set grew angle by angle across four checkpoints (12 → 18 → 21 angles), each checkpoint
   ending in a reconcile commit that re-stamped statuses ("Replay bootstrap is no longer
   flexible…"). Writing was not a phase after thinking; it WAS the thinking's second pass.
4. **Self-describing honesty.** The execution proposal opens "Status: INITIAL PROPOSAL —
   RECONCILABLE, NOT LOCKED… authorizes no code." Documents state their own authority level
   in their first lines.
5. **Presentation convention, stated and followed:** "plain explanation first"; models
   where they improve understanding; tables for ownership; visuals optional and never bare;
   "Once a fork is resolved, the written angle records the selected architecture and why.
   It does not preserve a recommendation as though the choice were still pending."

---

## Part 4 — The gap, stated plainly

| dimension | bench corpus | brainstorming skill today |
|---|---|---|
| angle depth | ~2,750 words avg; teaches without the log | companions optional, batched, no depth bar (mine: ~380 words, cite-only) |
| mental models | analogy + negative space open every angle | not asked for anywhere |
| typed sketches | convention ("prefer small Pydantic examples") | not asked for |
| claim → consequence | "this means…" after every LOCKED | not asked for |
| journeys | per-host walks, `->` flows | not asked for |
| decision entries | selection event, lineage (rests-on/affects), extension laws, anti-patterns | trigger/options/why/revisit only |
| fork experience | fully-specified variants; pick + rider requirements recorded | improved this session (Fork Standard) but variants are prose, not sketches; riders not captured |
| census | measured artifact with provenance tiers | a step with no artifact |
| writing timing | during, reconciled at checkpoints | after (steps 7–8), batched |
| document honesty | self-describing status in first lines | status field exists; self-description not taught |

The design that follows (`2026-08-28-brainstorming-experience-design.md`) turns each right-hand
cell into the left-hand one.
