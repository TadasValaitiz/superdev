# Angle 3 — Architecture into rooms, and back

**Purpose:** understand how the milestone architecture reaches a fresh item-room session without paraphrase drift, and what happens when the room's contact with real code proves the architecture wrong — without reading the brief template or the SDD skill.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D53, D57, D61 · experience design §5.6.
**Series:** 3 of 4.

> **Status guide (this angle owns the vocabulary — full glosses):** LOCKED operator-ruled,
> recorded at a D# · FLEXIBLE boundary agreed, exact shapes may move · DEFERRED a named
> later session owns it · BLIND not yet examined — said honestly, so nobody mistakes
> silence for approval · MISMATCH the repository behaves differently today; a
> reconciliation is owed · SEED-ILLUSTRATIVE an example explaining a mechanism, never a
> measurement or recommendation · SUPERSEDED→link this text is history; the link is the law.

## The central question

How does architecture travel into a session that has never seen it — and survive contact with code that contradicts it?

## Boundaries

The journey starts when the orchestrator composes an item room's brief and ends when the room's discoveries reach the checkpoint net. What the corpus contains and how it stays fresh are angles 1–2; how the item itself was cut and scheduled is angle 4.

## Concrete journey

### LOCKED — the marker grammar: rulings pre-distilled into quotable lines

Everything in this journey rides on one convention inside the corpus documents. Claims are marked positionally, in plain vocabulary:

```markdown
**LOCKED (D461):** `TargetBook` contains executable economic intent, not explanatory
strategy internals.
**FLEXIBLE:** the exact field names of the receipt model may move until first persistence.
**MISMATCH:** the repository still routes fees through the pre-§f frictionless ledger today.
**Status:** LOCKED (D437–D441) — this section survives the migration unchanged.
```

Two forms only: the line-initial **claim marker** (`**WORD:**` opening a line, marking one ruling) and the **section status** (`**Status:** WORD …` pricing a whole section). The payload after the marker is free — prose, a D#, a link, any mix. The vocabulary: LOCKED · FLEXIBLE · DEFERRED · BLIND · MISMATCH · SEED-ILLUSTRATIVE · SUPERSEDED→link. These are *epistemic* statuses — they answer "how much may I rely on this?", never "what workflow stage is this in".

Why plain words and not a bracket sigil like `DOC-MARK[LOCKED][D461]`: the evidence corpus measured its own author writing the plain form 112 times against the bracket's 22 — a grammar that loses to its author's hands under-counts forever. Distinguishability moved into tooling instead: a census script greps the positional forms (line-initial bold word + colon cannot collide with prose), reports counts per status per doc and the delta since the last reconcile. In code, `MIG-MARK[...]` keeps its bracket — source greps genuinely need a token no identifier can imitate.

The grammar's second job is the one this angle turns on: **LOCKED lines are pre-distilled quotables.** Because every ruling is already a self-contained marked sentence, briefs can quote the law without anyone paraphrasing it.

### LOCKED — inbound: the five-part brief block

An item room is a fresh session; everything it knows about your architecture, it learns from about a page. The brief's architecture section has five parts, each countering a failure that was actually observed:

```markdown
## ARCHITECTURE CONTEXT (as of reconcile commit abc1234, 2026-08-27)

READ FIRST — the law (read fully before writing anything):
- docs/system-design/milestones/bench/anchors/runtime-composition.md §3–4
- docs/system-design/milestones/bench/angles/06-adaptation-journey.md
- docs/orchestration/execution/bench-proposal.md — celebration 2, item 2a (your scope)
- Your area is marked REPLACE → ground on docs/system-design/visions/strategy-core.md,
  NOT on the current code in src/domain/strategy/.

READ ON NEED:
- angles/09-paper-wallet-runtime-bridge.md — only if you touch the wallet seam.

BINDING RULINGS (verbatim — these govern your item):
> **LOCKED (D461):** `TargetBook` contains executable economic intent, not explanatory
> strategy internals.
> **LOCKED (D455):** strategy evaluation runs every completed one-minute frame;
> `MemberBookPolicy` owns any slower cadence.
> **LOCKED (D437):** operational state, executable target, and analytics receipt are
> different objects.

RULED SINCE THE RECONCILE:
- D468 tightened the fee rule — read its entry in milestones/bench/decisions.md.
```

Part by part, against its failure:

1. **The as-of line** defeats silent staleness: the room knows exactly which corpus state briefed it, so anything newer is *knowably* uncovered rather than unknowingly missing.
2. **MAJOR reads** defeat wrong grounding — pointers at file-and-section precision, capped at three to five, with the one redirect that prevents the classic disaster: where the map says RESHAPE (the responsibility survives, its shape changes) or REPLACE (the design has killed this domain entirely), the room grounds on the *vision*, never the legacy code — building against a killed domain is building a fossil. (The verdicts live in `map.md`, the architect's current→target canon — angle 1; the architect assigns them.)
3. **NARROW reads** defeat both hunting and over-reading: the room neither searches the corpus blind nor pre-reads twenty files.
4. **The verbatim rulings** defeat paraphrase drift — the contested part, and the one place duplication is *sanctioned* in the whole system. The orchestrator selects the three-to-five LOCKED lines that bind this item and pastes them character-for-character. The evidence is a live ten-worker run whose orchestrator recorded the lesson explicitly: quoting the load-bearing sentences verbatim prevented drift better than any paraphrase — workers made to extract rulings from full documents drifted at exactly that step. The duplication's risks are bounded by construction: quotes freeze at brief time, live for the days of one item, and are stale-*detectable* because each cites a D# whose status supersession flips.
5. **Post-reconcile deltas as D# pointers** keep the one unsanctioned duplication — retelling rulings the docs don't carry yet — impossible: newer law arrives as a pointer into the decision log, never as retold content.

The whole block, as a map:

| Part | Defeats | Mechanism |
|---|---|---|
| as-of SHA line | silent staleness | freshness made knowable, not assumed |
| MAJOR reads | wrong grounding | 3–5 file:section pointers + the vision-not-legacy redirect |
| NARROW reads | hunting and over-reading | listed, read on need |
| verbatim rulings | paraphrase drift | frozen quotes of pre-distilled `**LOCKED:**` lines, D#-cited |
| post-SHA D# pointers | retold law | pointer into the log, never content |

### LOCKED — outbound: show must go on

Now the return path. Three days in, the room discovers its data layer physically cannot deliver what `**LOCKED (D455)**` demands for an entire asset class. The claim is load-bearing and wrong. What happens next was ruled with a phrase: *show must go on.*

**During grounding → brainstorm → planning**, the room collects every corpus contradiction in its *own* item files — its decision log, its spec's deviations section. Nothing stalls; nothing asks permission. Most discrepancies die right here, resolved by better reading — the room is the cheapest place to kill a false alarm, and the corpus never hears about those.

**After planning, before execution starts** — the seam this design adds — the survivors trigger a notification: the room finalizes its deviations section, messages the orchestrator a short summary plus a pointer to the file; the orchestrator **relays the pointer to the architect immediately**, not batched to the next checkpoint. The orchestrator is a relay of pointers by design — content lives in the room's file, in the room's own words; no paraphrase enters the chain. Why this timing: at plan time the deviation is fully characterized but nothing irreversible has been built, and the architect can begin re-ruling the affected area *in parallel with the room's execution* — the mode law (angle 2) decides whether that re-ruling happens autonomously or waits for the operator. The architect receiving a pointer between checkpoints breaks no idleness law: receiving is not ruling.

**During execution**, the room implements against reality, planting `MIG-MARK[MISMATCH][D455]` at the exact sites. The merged code contradicts the corpus — *honestly*: the marker is the corpus's own vocabulary saying "the repository behaves differently than the ruling; a reconciliation is owed." The room's flagged deviation entry preserves what it did and why.

**At the checkpoint**, anything not already re-ruled arrives through the normal net — the room's report, the orchestrator's clusters, the sitting's verdicts. The marker comes out when the fix or the re-ruling lands, and the census watches the count.

## Visible collisions

- **Evidence versus doctrine, as a policy.** Both of this angle's contested rulings (settled in the journey above) share one meta-rule worth naming: where measurement and principle disagreed — verbatim quotes beating pure pointers, plain markers beating the bracket — the measurement won, *and* the concession was bounded (one sanctioned duplication; rigor moved into tooling). The system's doctrine is falsifiable by its own practice, on purpose.
- **Honest motion versus frozen purity.** Show-must-go-on accepts merged code that temporarily contradicts the corpus — visibly, in markers, with the architect notified in hours. The alternative protected the corpus by stopping the work; the operator judged an honest, marked contradiction cheaper than a stalled milestone. The collision is permanent: every MISMATCH marker in the tree is this trade, re-made.
- **Freshness versus the quote.** The brief's frozen quotes are the one place the freshness guarantee (angle 2) is deliberately weakened: a reconcile can supersede a quoted D# while the room runs. The bound is detectability (the quote cites its D#) — and the unbuilt CORRECTION push below is this collision's open half.

## Current mismatch

**MISMATCH:** the skill text does not yet implement this angle. The room-brief template has no ARCHITECTURE CONTEXT block; the SDD skill still carries the retired residue-jsonl append verbatim; the marker sections still teach the DOC-MARK bracket; the census script does not exist. All land at implementation Task 5 — this angle describes the ruled target.

## Flexible and deferred

FLEXIBLE: the quote count (3–5 is guidance, not a cap), the notification message's wording, the deviations-section format. DEFERRED — the one named BLIND of the whole stream: the **mid-item CORRECTION push**. When a reconcile supersedes a D# quoted verbatim in a *live* room's brief, nothing yet pushes a correction to that room; today the checkpoint net catches it. The revisit triggers on D57/D61 own this: it becomes real the first time a room ships against a quoted ruling that was superseded mid-item.

## Reconciled outcome

LOCKED: the two-form plain marker grammar with census-as-tooling; the five-part brief block with its one sanctioned verbatim duplication; the show-must-go-on deviation flow with plan-time pointer relay and MISMATCH markers. FLEXIBLE and the one BLIND as above. The angle's whole content in one line: the law travels down as frozen quotations, reality travels up as pointed-at files, and every disagreement between them is either marked in code or ruled in the log — never silent.
