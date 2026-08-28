# The orchestrator's checkpoint duties — quick card

Formats and worked examples live in superdev:system-design `protocols.md`; this card is your side only.

## Declaring (rule + green lights + feel)
- Track green lights as cursor rows (room · arc · when · your weighting note).
- A checkpoint is a DECISION you log: which rule input fired, which lights you counted, one line of feel.
- Milestone close is always a checkpoint; never let it be the only one on a long milestone.

## Writing the handover — ONE document (`docs/orchestration/handovers/<milestone>-checkpoint-<n>.md`, you are the single writer)
It opens with the OPERATIONAL RECORD stamp (durable-state.md) — write-once, pruned on the rolling window; the old separate residue-collection doc is dead, clusters live inline:
1. **WHAT WE GOT** — the cross-room narrative only you can write, plus facts: merges, what held and what didn't.
2. **WHERE WE FEEL GAPS** — labelled as feel, organised by angle (cite angle numbers, never write architecture).
3. **UPCOMING FOCUS** — the charters you want next and exactly what each needs ruled; blocking flags.
4. **MAP CLAIMS** — rows you CLAIM discharged, each with evidence at file:line/transcript (the architect accepts or rejects; only they write the map).
5. **CLUSTERS** — your authored grouping of the typed residue ledger's rows: cite row ids, zero rulings.
6. **FACTS** — inlined numbers: the census-script delta since the last reconcile commit (ephemeral output, never a committed file) + measured process facts (charter→merge, review cycles, blocked-wait).
Ask "agree or disagree with 1–3?" and send ONE pointer message.

## Receiving the response — a BLOCK in the milestone's decisions file, not a document
Find it in `docs/system-design/…-architecture-decisions.md` under `## Checkpoint <n> — response (reconcile <sha>)`, followed by the new D# entries. Your duties:
- AGREE sections → proceed. **BOUNCED-DOWN clusters** → file each as backlog items or route into an upcoming charter — and CONFIRM the filing in your NEXT handover's WHAT WE GOT (the loop audits itself).
- **REJECTED claims** → the row stays undischarged; re-claim only with the receipt the rejection named.
- DISAGREE on a charter's readiness → that charter waits; apply the scoped design-dry rule.
- The response's agenda items needing the operator → queue via the desk (DESIGN column) and stop; never schedule the operator.
- Note the reconcile commit SHA — it is the as-of line for every brief you write until the next one (room-brief-template.md).

## After the sitting
- Re-read the map angle (discharges written, statuses moved) and re-charter accordingly; kill charters the rulings invalidated.
- Fold new learnings into the next briefs (fast loop) and log an O-line per adaptation.
