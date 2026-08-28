# Angle 4 — Execution shaping and the authority boundary

**Purpose:** understand who turns ruled architecture into a delivery shape, by what method, and under which adjudication law — without reading the orchestrator skill.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D54→D55 (supersession), D68 · prior chartering stream D44/D45 · [experience design](./2026-08-28-brainstorming-experience-design.md) §5.6.
**Series:** 4 of 4.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it (named below) · MISMATCH current skill text behaves
> differently today · SEED-ILLUSTRATIVE worked example only, never a measurement.

## The central question

Where does design authority end and execution judgment begin, when grouping architecture into deliverable items?

## Why this deserves its own angle

This is the only angle in the stream carrying a *superseded ownership ruling*: the proposal method was designed under architect ownership (D54) and the operator overturned the owner — not the method — within the same session (D55): "execution is the orchestrator's altitude." The fork was live, argued, and reversed; the interesting result is that the method survived the move intact. Any future reader wondering "shouldn't the architect group the deliverables? they know the design best" is re-opening exactly this fork, and this angle exists so they meet the argument before they meet the temptation.

## Start and stop boundaries

**Starts at:** a reconciled corpus — the reconcile commit closing the pre-milestone sitting.
**Stops at:** the operator-ratified charter graph.
**Depends on:** the corpus as-of that reconcile SHA; the map's rows; the D44/D45 chartering mechanics.
**Does not own:** chartering mechanics themselves (D44/D45), brief composition (angle 3), the checkpoint conversation (angle 2), or any design ruling whatsoever.

## The mental model

The execution proposal translates *"what must be true"* (the corpus) into *"in what order it becomes demonstrable"* (a delivery hypothesis). It sits between system design and item design and is deliberately neither.

It is not:

- architecture — it rules nothing about the domain;
- a schedule — dates and room budgets live in the charter graph;
- a charter — no room is launched from it directly;
- an authorization to write code — it explicitly authorizes none;
- a locked document — its own status line says *reconcilable, not locked*; or
- a place where design forks get settled — a cut that needs a design ruling is a design gap, routed back, never improvised.

## Concrete journey

### LOCKED — the orchestrator is sole writer, and the method outlived the owner

The proposal lives at `docs/orchestration/execution/<milestone>-proposal.md`, orchestrator-written. The reasoning that moved it there: design *knowledge* is delivered by the corpus, which anyone can read — the architect's contribution is already on disk before the proposal work begins. Grouping deliverables, sizing them against operator attention, and ordering them by risk is execution *judgment*, which is the orchestrator's charter. Giving the architect a second, personal role in delivery grouping would entangle the design authority in operational choices — the exact entanglement the room separation exists to prevent. This means: the corpus is the interface between the two altitudes, and it must carry everything the proposal needs (see the design-dry refusal below for what happens when it doesn't).

### LOCKED — two seats, dispatched not consulted

The orchestrator does not write the proposal from one mind. He dispatches two subagents with opposed briefs:

- **The domain-boundaries seat** receives the corpus as-of the reconcile SHA plus the map rows, and optimizes for *clean cuts*: type ownership, package seams, contract breaks. It is forbidden to weigh demonstrability. It returns a proposed item set with, for each item, the seams it respects and the contracts it isolates.
- **The celebration seat** receives the same corpus plus the real user-facing surface, and optimizes for *provable wins*: operator-visible journeys with proof, refusal, and recovery evidence. It is forbidden to weigh internal cleanliness. It returns proposed celebrations with, for each, the journey that proves it.

Both reports land in the orchestrator's space or sdd scratch — never the corpus (D68; design-intake seats, the bench pattern of perspective reports feeding an architecture *sitting*, are a different animal, and those the architect curates into `milestones/<slug>/inputs/`). The reports are inputs, not rulings: nobody has adjudicated them, and their disagreement is the point.

### LOCKED — the collision zone is the product

Where the two seats disagree is precisely where the middle ground must be found — a proposal written from either seat alone ships that seat's blindness. The adjudication law is the five celebration rules (next section); the worked example below shows one collision resolved under them.

### LOCKED — the architect touches this twice, through existing channels only

**Upstream:** the corpus the seats read. If the celebration seat wants a vertical through an area with no vision document, that charter is *withheld* — the design-dry rule. Withholding is an absence, not a veto: nobody blocks anybody; the gap travels back as residue, lands at the next checkpoint, and the unaffected charters proceed.
**Downstream:** an advisory conformance note — normally one line in the checkpoint response block, a standalone `milestones/<slug>/conformance-<item>.md` only when it genuinely needs length (D68). Advice, never authorship; it cannot block.

### LOCKED — ratification, then derivation

The operator ratifies the reconciled proposal at the co-plan (the milestone's opening sitting, where mode and graph are also declared). The orchestrator then derives the charter graph via the D44/D45 mechanics — in one sentence: build the dependency DAG from map rows and bridges, compute each item's blocking radius, split high-radius items so their unblocking kernel merges earliest, and launch greedily on "unblocks the most work soonest" under the operator's attention budget. Dependencies are never parallelised; the producer merges first.

## The five celebration rules

The adjudication law, as a table a stranger can apply:

| Rule | What it requires | What it rejects | A cut it kills |
|---|---|---|---|
| 1. Operator-visible capability | every celebration completes a journey an operator can experience | internal components as deliverables | "migrate the schema" as an item |
| 2. Proof at the user surface | a real command journey with durable readback and refusal/recovery evidence | unit tests standing in for the celebration | "all tests green" as the done-bar |
| 3. Foundations inside the first vertical — *unless they unlock named independent streams* | non-visible prerequisites fold into the first celebration that proves them | standalone plumbing items with no contract gate | "build the event bus" as item 1 |
| 4. Terminal, not tiny | each item closes complete: brainstorm→design→plan→build→checkride→closure; never reopened to make its journey real | thin slices that defer their own proof | a vertical shaved to a stub to fit a week |
| 5. Reconciliation expected | item-level contact with code may split/merge/reorder items; the operator outcome stays stable | treating the first shape as settled | refusing a split when the code demands one |

## Worked example — the collision zone   (SEED-ILLUSTRATIVE)

Drawn from the bench corpus as an illustration, not a record. The domain seat proposes three items along package seams: `bench-core`, `bench-adaptation`, the shells — clean type ownership, and none of the three demonstrates anything an operator can run. The celebration seat proposes as item 1: *"one strategy backtest runs end to end on the new engine"* — a journey straddling all three seams.

Adjudication: rule 1 rejects the domain seat's items as deliverables in their own right. Rule 3 folds `bench-core` inside the first proving vertical — it is plumbing the backtest proves. Rule 3's *exception* carves `bench-adaptation` out as item 2 after all: it unlocks two named independent streams (replay adaptation and wallet adaptation) and can carry its own contract gate. Rule 4 stops the vertical being shaved to "backtest compiles and prints": the journey must reach durable readback and a refusal path. The reconciled cut: item 1 = the end-to-end backtest vertical (with core folded in), item 2 = the adaptation package behind its contract gate, item 3 = the shells' composition — each terminal, each provable, each respecting the seams the domain seat mapped.

## Structured sketch — the proposal file

```markdown
# <milestone> Execution Plan — Celebration-Led Proposal
> OPERATIONAL RECORD — point-in-time, never reconciled. Reconcilable, NOT locked.
> Authorizes no code. Design authority: docs/system-design/ as of reconcile <sha>.

## Celebrations (ordered)
1. <operator-visible capability> — journey: <commands>; proves: <map rows>
   items: 1a <vertical, foundations folded>, 1b <carved foundation + its named streams>
## Dependency intent        (what must merge before what, and why)
## Reconciliation ledger    (amendments as items met the code — rule 5)
```

It wears the operational stamp because it lives in the orchestrator's space: never reconciled, pruned on the rolling window when its milestone is one closed milestone old (angle 2). The charter graph derived from it may run *ahead* of it between sittings — the proposal is amended at the orchestrator's own rhythm (rule 5), and only design-class divergence crosses to the architect, as residue.

## What the execution proposal cannot do

- Authorize code, schema, CLI, or migration work — it says so in its own banner.
- Rule a design fork — a cut with no corpus seam under it is a design gap, never an improvised boundary.
- Be locked — reconciliation is expected by construction.
- Be architect-written or co-written — one writer, and it is not the design authority.
- Outrank ratification — the operator's co-plan approval is what makes it operative.
- Block on advice — the conformance note is advisory in both directions.

## Ownership

| Artifact | Writer | Space | Freshness contract |
|---|---|---|---|
| execution proposal | orchestrator | `docs/orchestration/execution/` | operational: stamped, prunable, reconcilable-not-locked |
| execution seat reports | the seats (via orchestrator dispatch) | orchestrator space / sdd scratch | operational, prunable |
| design-intake seat reports | architect (curated copies) | `milestones/<slug>/inputs/` | dated layer: never rewritten, banner-superseded |
| charter graph | orchestrator | `docs/orchestration/` | operational working state |
| conformance note | architect | response block, or `milestones/<slug>/conformance-<item>.md` | reconciled surface |

## Visible collisions

- **Architect altitude versus orchestrator altitude:** the method survived the ownership move — knowledge flows through the corpus, judgment stays with the executor, and neither needs a seat at the other's desk.
- **Domain purity versus provable wins:** institutionalized as the two seats; rule 3 and its exception resolve most collisions, and the worked example shows one dissolving.
- **Two opposed seats versus one author holding both rules:** a single author "balancing" both concerns produces the average of two blindnesses; dispatching the seats forces the collision to be *produced as evidence* before it is adjudicated.
- **Proposal versus charter graph:** the graph may run ahead of the proposal between sittings — a live, sanctioned drift bounded by rule 5's amendment duty and the design-class residue route.

## Current mismatch

**MISMATCH:** the orchestrator skill today has no execution-proposal section and no seat prompts (the design's R7 disposition: "orchestrator skill gains the section + seat prompts"; acceptance AH11 unchecked). This angle describes the ruled target; the skill text catches up at implementation Task 5.

## Flexible and deferred

**FLEXIBLE:** seat prompt wording; the proposal file's exact layout; how many celebrations a milestone carries.
**DEFERRED, with landing places:** milestones with no CLI surface — the celebration seat argues from whatever the operator-visible proof boundary is (API, artifact, report); lands the first time it happens, and this very project's skill-text milestones will be that first time (D54's revisit clause). Repeated design-dry bounces — the architect's anchors gain a required "seams" section rather than proposal authorship (D55's revisit clause).

## Reconciled outcome

**LOCKED:** orchestrator sole authorship at `docs/orchestration/execution/`; the two-seat method with opposed optimization targets and forbidden considerations; the five-rule adjudication law with rule 3's named-streams exception; the architect's two channels (corpus upstream, advisory conformance downstream), design-dry as absence-not-veto; co-plan ratification followed by D44/D45 derivation. The authority boundary the angle is named for, in one sentence: *the corpus decides what is true, the proposal hypothesizes what to prove next, the operator decides that the hypothesis is worth building — and no participant holds two of those pens.*
