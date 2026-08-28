# Angle 2 — The checkpoint seam

**Purpose:** understand the complete life of one design checkpoint — what crosses between orchestrator and architect, in which artifacts, under which freshness promises, and who rules — without reading either skill.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D52, D58–D60, D62, D68 · experience design §5.6.
**Series:** 2 of 4.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH current text behaves differently today ·
> BLIND not yet examined — said honestly · SEED-ILLUSTRATIVE worked example only — every
> SHA, duration, and count in this angle's sketches is invented for illustration, never a
> measurement.

## The central question

How do two altitudes converse through files without the files becoming a third, drifting version of the truth?

## The mental model

Two rooms with different jobs, at different heights — the **altitudes**. The ARCHITECT owns *what must be true*: the corpus, the rulings, the long view; it is idle between sittings. The ORCHESTRATOR owns *what happens next*: rooms, schedules, ledgers; it never stops. They share no file (angle 1), so everything they exchange crosses as a message pointing at a document one of them owns — and the checkpoint is the appointed moment when a milestone's accumulated learning crosses up and its accumulated questions get ruled.

The seam is not:

- a meeting protocol — nobody attends anything; documents and one message each way carry it;
- a review of the orchestrator's work — claims are audited, but the sitting rules on *design*, not performance;
- continuous — between checkpoints the architect hears only plan-time deviation pointers (angle 3), and receiving is not ruling; or
- a merge gate — publishing is FF-CAS by rooms; the seam governs understanding, not integration.

## Boundaries

The journey starts when the orchestrator declares a checkpoint and ends at the reconcile commit that closes the architect's sitting. How rooms produce the material that arrives here is angle 3; how a milestone's items were cut in the first place is angle 4. The mode law is explained here because the sitting is where it bites hardest, but it governs every ruling gate in the system, not only this one.

## Concrete journey

Follow one checkpoint end to end.

### LOCKED — the two-surface law is the ground everything stands on

The repository's documentation has two surfaces with *opposite* freshness contracts, and every artifact in this journey belongs unambiguously to one of them.

**The reconciled surface** (`docs/system-design/`): anything you grab from it matches reality — either the content is current, or it wears a marker or banner saying exactly how much to rely on it. This promise is expensive, which is why the surface is small and why a named process (reconciliation, below) exists solely to keep it.

**The operational surface** (`docs/orchestration/`): files exist here for one reason — messages must stay short, so the message carries a summary and a pointer, and the detail lives in a file. These files are point-in-time records *the moment they are written*: nobody ever reconciles them, they are allowed to rot, and they say so on their face. Every operational file opens with a standing stamp:

> OPERATIONAL RECORD — point-in-time, never reconciled. May be outdated the moment
> you read it. Design authority lives in docs/system-design/ (as of its last reconcile).

Because nothing here is reconciled, the surface is kept honest the only other way possible: **pruning**. At milestone N's close, milestone N−1's operational files are deleted — handovers, raw ledgers, spent backlog items, proposal drafts — after their durable lessons are harvested into the handoff. One milestone's files survive one milestone longer as a lookback window; git is the archive beyond that. (The keep-set that never gets pruned: the handoffs themselves, `conventions.md`, and the improvement-notes stream — the files that feed the next milestone and the skill-improvement loop.)

### LOCKED — declaration: rule + green lights + judgment

A checkpoint is declared by the orchestrator when a rule fires (a bridge side fully merged · milestone close · the operator asks), when rooms' green lights accumulate ("nothing more to contribute on this arc"), or when his judgment says the residue collection now justifies a sitting. Between checkpoints the architect is idle — the one exception being plan-time deviation pointers (angle 3), which it may *receive* at any time, because receiving is not ruling.

### LOCKED — the handover: one operational document carrying everything the seam needs

Declaring means writing ONE document — `docs/orchestration/handovers/<milestone>-checkpoint-N.md` — and messaging the architect a pointer to it. Its shape:

```markdown
# Handover — checkpoint 3
> OPERATIONAL RECORD — … (the stamp)

## WHAT WE GOT
Items 2a and 2c merged. The replay seam held; the fee model did not — three rooms
independently hit its edges. We believe the milestone's center of gravity moved…

## WHERE WE FEEL GAPS
The optimization area has no vision doc; charters are approaching it…

## UPCOMING FOCUS
Next window: items 2b, 3a. We propose taking 3a first because…

## MAP CLAIMS
R12 discharged — evidence: src/domain/target_book.py:112 + test transcript t3.
R17 discharged — evidence: replay CLI journey, transcript t4.

## CLUSTERS
1. fee-seam discrepancies (rooms A,C — rows A-12, A-14, C-3): both rooms found …
2. naming drift in the wallet bridge (room B — row B-7): …
4. module-internal refactor requests (room C — rows C-5, C-6): …

## FACTS
Census delta since reconcile abc1234: BLIND 3→0, MISMATCH +2 (both fee seam).
charter→merge: 2.1d avg · review cycles: 2 · blocked-wait: 4h total.
```

Three narrative sections first — they are the point. The ledgers hold every row and every measurement, but no file holds what it *felt like across rooms*; that judgment exists only in the orchestrator, and the handover is where it becomes durable.

**The claims section** practices two-step discharge: the orchestrator *claims* map rows with evidence; only the architect *writes* the map. This means a claim can be rejected — and the rejection, with its reason, survives (see the response block below), which `map.md` alone could never record.

**The clusters section** is his authored grouping of the typed ledger rows — interpretation *offered* to the sitting, never imposed on it; the sitting may regroup.

**The facts** are machine-generated numbers inlined, not attached: the recurring marker census is ephemeral script output that lives in handovers, never as a committed file. (The milestone folder's `census.md` — the charter-time grounding sweep — is a different, surviving artifact; the two share a name and nothing else.)

### LOCKED — the sitting: mechanical open, then ruling by mode

The architect's sitting opens mechanically, in both modes: read the handover, grep its own docs for markers gone stale (cited D#s whose status flipped), assemble an agenda organized by angle, each entry a *question*. Then the mode law decides who rules:

| | HUMAN mode | AUTONOMOUS mode |
|---|---|---|
| declared | at the co-plan — the milestone's opening sitting, where operator and orchestrator ratify the charter graph — default for design-heavy milestones | explicitly by the orchestrator, recorded in his graph file and `conventions.md` so every room and the architect can read it |
| architect does | stages only; waits for the operator; rulings happen in the sitting together | real architecture: for each fork, options with gains/sacrifices + a recommendation, presented to the Fork Presentation Standard (situation · mechanism-with-example · consequences · recommendation — owned in full by brainstorming-flow angle 1) |
| who picks | the operator | **the orchestrator** |
| the pick's record | ordinary D# | flagged D#: options preserved, named as an autonomous-mode pick, revisitable |
| reserved forks (money/irreversibility, blast-radius reshapes, taste) | operator | **operator — always**; tagged and queued; the architect designs around them so work continues |
| milestone close | operator approves | **operator approves — always** (safety stays topology: nothing reaches main un-approved) |

The invariant making autonomy safe: the next human touchpoint *opens with the pick list* — every autonomous pick reviewed first, overturnable by a superseding D# that preserves the original. Nothing is erased; the operator's authority is deferred, never diluted.

### LOCKED — the response lives inside the decision log, and the reconcile commit closes

The sitting's answer is NOT a new document — every new doc type is a new reconciliation surface, which is the disease. The response is a *block inside the milestone's decisions file* (`…-architecture-decisions.md`), immediately followed by the rulings it announces:

```markdown
## Checkpoint 3 — response (reconcile def5678)
Sections: GOT agree · GAPS agree, except the fee seam is worse than felt (D468) ·
FOCUS disagree — 2b before 3a; 3a's kernel depends on the fee ruling (D469)
Claims: R12 ACCEPTED · R17 REJECTED — receipt covers the read path only; re-claim
with a write-path receipt
Clusters: 1 → ruled, D466–D468 · 2 → deferred, needs the optimization vision ·
4 → BOUNCED DOWN — item-work, no design fork; suggest one quick-fix item
Conformance notes: celebration 3 straddles a REPLACE boundary — advisory only.

### D466 — the fee model owns its rounding …
### D467 — …
```

Claim verdicts and their *reasons* survive here — three weeks later, "R17 was rejected and why" is one grep away, which `map.md` alone could never tell you. **Bounced-down** clusters land mechanically: the orchestrator (backlog curator) converts each into backlog items or routes them into an upcoming charter, and his *next* handover's WHAT WE GOT confirms the filing — the loop audits itself.

Then the sitting's mandatory last act (both modes, every sitting — checkpoint-triggered or an operator brainstorm alike): the **reconciliation pass**. Statuses flip in the INDEX and the touched angles/anchors; superseded docs get banners; canon is rewritten if the rulings moved it; and ONE named commit closes: `docs: reconcile <milestone> architecture authority`. No sitting ends with the corpus contradicting what it just ruled. Between sittings, staleness is permitted — and honestly marked, which is what the markers are *for*.

## Visible collisions

- **Rich handover vs the pointer doctrine.** The narrative trio is genuine content in an operational file — allowed because the operational surface's contract ("point-in-time, may rot, will be pruned") makes durable-but-unreconciled content safe there. The same content on the reconciled surface would be a maintenance debt.
- **Symmetry versus surfaces.** The general lesson from the response's placement (the fork itself is settled in the journey above): when two artifacts always change together, they are one artifact — and every artifact type you add is a reconciliation surface you will pay for on every future sitting. Symmetric designs are seductive precisely because they multiply surfaces evenly.
- **Architect idleness vs staging cost.** Strict idleness wastes the operator's most expensive minutes on watching greps; unrestricted preparation drifts into pre-cooked conclusions. The mode law absorbed this: mechanical opens are always allowed because *reading is not ruling* — the line is drawn at judgment, not at activity.
- **Autonomy vs authority.** AUTONOMOUS mode looks like it transfers design authority to the orchestrator. It doesn't: it transfers *scheduling* of authority — picks are provisional-by-construction (flagged, reviewable, overturnable) and the irreducible forks never leave the operator. What the milestone gains is that it never stalls on an absent human it was told not to wait for.

## Flexible and deferred

FLEXIBLE: handover section wording and ordering; the stamp's exact phrasing; the response block's line format. DEFERRED: none — but note the mode law's revisit trigger: an autonomous-pick overturn rate above roughly one in four at human review means the reserved-fork classes are drawn too narrow.

## Reconciled outcome

LOCKED: the two-surface law with the stamp and rolling-window pruning; checkpoint = one handover doc + one response block + one reconcile commit; two-step discharge with durable claim verdicts; bounce-downs with a self-auditing loop; the mode law with reserved forks and flagged revisitable picks; reconciliation as every sitting's mandatory close. FLEXIBLE: wordings and formats above. The seam's whole design fits one sentence: judgment crosses in two named artifacts, authority stays where it always was, and the files can never disagree about which of them is the truth.
