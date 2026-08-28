# Brainstorming Angle 3 — One session, walked end to end

**Purpose:** follow a single brainstorm from the operator's first message to the implementation handoff, showing what exists on disk at every station — without reading the skill.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D56, D65, D66 · [experience design](./2026-08-28-brainstorming-experience-design.md) BR1, BR11, BR12, BU1–BU5 · angles 1–2 of this series (bandwidth; lifecycle).
**Series:** 3 of 3 (brainstorming flow).

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH current skill text behaves differently today ·
> SEED-ILLUSTRATIVE worked example only, never a measurement.

## The central question

What does the operator actually experience, hour by hour, in a session run the way the reference corpus ran — and what artifact proves each hour happened?

## The mental model

A session is a pipeline that turns one vague intent ("improve how the orchestrator and architect collaborate") into four kinds of artifact: a **census** (what is), a **decision trail** (what was ruled and why), **companions** (what a stranger needs to understand it), and a **spec** (what gets built). The operator's experience is good exactly when, at every moment, they can answer *"what are we doing right now, and what will exist when this step ends?"* — the stations below are that answer, in order.

A session is not:

- implementation — a hard gate forbids writing product code before the design is approved;
- a meeting — most stations produce a committed artifact, not consensus;
- linear in content (angles collide and reopen) though it is linear in *stations*; or
- complete when the talking stops — two stations (sweep, reviews) happen after the last fork.

## Concrete journey

### LOCKED — station 1: the census, before anything else   (example: real READ/MEASURED lines from this stream, quoted as a census would carry them)

The session's first committed artifact is a written census of the ground:

```markdown
# Census — orchestrator/architect collaboration (2026-08-28)
**MEASURED** — 199 files in docs/superpowers/specs/ (ls | wc -l); marker counts:
  112 line-initial `**LOCKED:**` · 22 DOC-MARK[LOCKED] (grep, commands quoted — D53's evidence)
**READ** — the checkpoint protocol writes handovers to design/residue-collections/
  (checkpoint-protocol.md:10 — a path since RETIRED by D60; an honest census records what
  the text says today, staleness included)
**FLAGGED** — the residue inbox may be incompatible with worktrees (unverified —
  the work queue, not a conclusion)
```

Three tiers, and the third is the honest one: FLAGGED items are *the work queue, not conclusions* — suspicions the session must verify or drop, never silently promote. This means the operator can distinguish, from minute one, what the session KNOWS from what it merely suspects — and every later fork presentation inherits that honesty ("the evidence: MEASURED, 112 against 22").

### LOCKED — station 2: the agenda, amendable before work starts

Three to five candidate angles, each named with its central question and one line on why it matters, presented for amendment — drop, add, reorder — before the first clarifying question. The agreed agenda and every later amendment land in the decision log. The operator's cheapest, highest-leverage act in the whole session is here: redirecting a session costs one message now and a discarded document set later (this stream measured both prices).

### LOCKED — station 3: angle work — the loop the operator lives in

For each angle, the same rhythm: **open** with the situation in prose (what's being decided, what breaks — never an option list with no ground); **explore** one decision at a time, with enough architecture and code context that the operator can reason without having written the implementation; **collide** two or three materially different options per the Standard (angle 1 of this series) — sketches where shape exists; **rule** — the pick, with any rider, recorded as an event; **close** — state what was reconciled, and if the angle carried real collisions, *write its companion now* (angle 2 of this series) and commit it before the next angle opens.

The operator's view of a healthy session: a steady cadence of full fork presentations punctuated by "angle closed — companion committed" lines, with the log growing a D# at every ruling, in real time — never a promise of documentation later.

### LOCKED — station 4: the whole-design pass

After the last angle: how do the rulings compose into one shape? Presented as a fork like any other — two or three composition variants under the Standard — because composition IS a decision, and the session's biggest one. (This stream's own version: "two surfaces with opposite freshness laws, connected by pointer-relay messaging, governed by one mode law.")

### LOCKED — station 5: the sweep, then the documents face review

The in-session reconcile sweep (angle 2) makes the set self-consistent. Then two reviews, both fresh-eyes: the author's inline self-check, and the dispatched reviewer — which receives the spec, the log, AND the companions, and probes the experience bars: can a stranger answer questions from one companion alone; does any LOCKED lack its "this means"; does any deferral say bare "later"; does any resolved fork still read as a pending recommendation. Blockers are folded and confirmed once.

### LOCKED — station 6: the operator's gate, with the files in hand

The gate message hands over everything by link — spec, log, every companion — and asks for review before planning begins. The operator reads *documents*, not a chat summary; approval means the written record, not the conversation, is what got approved. Then, and only then, the writing-plans handoff.

## What a session cannot do

- Write product code — the hard gate holds regardless of how simple the project looks;
- rule reserved forks in the operator's absence — mode law aside, a brainstorm with the operator present IS the human mode;
- promote a FLAGGED census line to evidence without verifying it;
- skip stations for small projects — the stations scale down in length, never in kind (a small session's census is five lines; it still exists);
- end at the talking — an unswept, unreviewed, un-handed-over session is unfinished by definition.

## Current mismatch

**MISMATCH:** today's skill has no census artifact (step 1 explores without recording), no station-4 framing (approaches are proposed but not under the Standard — fixed in text, unexercised), no sweep, and a gate that hands over only the spec. The rebuilt checklist (implementation Tasks 1–3) is this journey, station by station; this angle is its target-state description and BH1–BH7 in the experience design are its receipts.

## Visible collisions

- **Ceremony versus scaling.** Six stations sound heavy for a small design. The resolution is that every station has a natural minimum (a five-line census, a two-angle agenda, one composition variant) — kind is preserved, length scales; the alternative, skipping stations below a size threshold, is how "simple" projects end up with unexamined assumptions, the oldest failure in the skill's own anti-patterns list.
- **Census cost versus grounding quality.** The census spends the session's first minutes on writing instead of talking. It buys every later fork its evidence line and every later reader the MEASURED/FLAGGED distinction — and the reference corpus put a census at the front of its best-run room. The collision is real for tiny sessions and the minimum-census answer above is deliberately cheap.
- **Real-time companions versus flow.** Stopping to write at each angle close interrupts conversational momentum. The measured alternative — batching — produced the index-documents this series' angle 2 dissects. Flow yields to the record, because the record is the product; the mitigation is that a well-run close is mostly assembly (the situation, the sketches, and the "this means" lines were all already produced live).

## Flexible and deferred

**FLEXIBLE:** census file naming; whether small sessions fold stations 1–2 into one message; companion commit granularity. **DEFERRED, with landing place:** the visual companion's role at station 3 (mockup-heavy sessions) — unchanged from the current skill, revisited if the rebuilt flow changes its economics.

## Reconciled outcome

**LOCKED:** the six-station journey (census → agenda → angle loop with close-time companions → whole-design pass → sweep + probing reviews → gate with files), each station leaving a named artifact; the cannot-do fences; kind-preserving scaling. The angle in one line: *the operator should never wonder what the session is doing or what it will leave behind — every hour has a station, and every station has an artifact.*
