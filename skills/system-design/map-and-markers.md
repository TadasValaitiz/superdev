# The map and the two marker families

## Map row grammar {#map-row-grammar}

`design/map.md` — the only design document allowed to look backward at code. One row per current-code responsibility:

| id | code area | verdict | test verdict | markers | status | discharging item | anchors |
|---|---|---|---|---|---|---|---|
| M14 | `src/…/bench_engine.py` allocation state | RESHAPE | archive-then-rewrite | MIG-MARK[SEAM][D381] | DOC-MARK[LOCKED][D372] | item-3.3 | D372, angle-02 |

- **verdict** ∈ KEEP (semantics align; may hide behind a new interface) · RESHAPE (responsibility right, model/algebra conflicts with rulings) · REPLACE (must not remain authoritative; no dual-read, no crosswalk) · DEFER (a later design owns the destination).
- **test verdict** ∈ keep · regenerate · archive-then-rewrite · fix-in-place — set by the item brainstorm; the plan may only refine mechanics, never reverse.
- **discharging item**: written ONLY by the architect, at a session, after the orchestrator claims it in a handover. A row nobody discharges is visible debt.

## MIG-MARK — code markers {#mig-mark}

```python
# MIG-MARK[RESHAPE][D372]: cash sleeve still authored here; moves to regime grant in the bench pass
# MIG-MARK[REPLACE][D350]: legacy public bench read — delete at gen-2 cutover
# MIG-MARK[SEAM][D381]: temporary adapter; collapses when TargetBook lands
# MIG-MARK[TEST][D376]: golden pins regenerate after reshape; do not hand-maintain
```
Classes are **closed** (RESHAPE · REPLACE · SEAM · TEST); a new class needs a D#. Every D# must resolve to a corpus entry. **A marker is removed with the fix, never resolved in place** — progress IS the count trend. Planting a marker is how an item finishes *now* and defers the clean fix to a later pass without stalling (the design never blocks development).

## DOC-MARK — corpus markers {#doc-mark}

`DOC-MARK[LOCKED|FLEXIBLE|DEFERRED|BLIND|MISMATCH|SEED-ILLUSTRATIVE][D#|owner]`
Epistemic, not lifecycle: they answer "how much may a reader rely on this here", not "how far along is it". BLIND is the honest "not yet examined" — sessions open by grepping for it. Symmetry rule: every DOC-MARK[MISMATCH] eventually has a MIG-MARK twin in code or a residue row explaining why not.

## The census {#census}

```bash
grep -rn "MIG-MARK" src/ | wc -l                                   # total debt
grep -rn "MIG-MARK\[REPLACE\]" src/                                # per class
grep -rn "MIG-MARK\[.*\]\[D372\]" src/                             # per decision
grep -rn "DOC-MARK\[BLIND\]\|DOC-MARK\[MISMATCH\]" design/         # the session agenda, mechanically
```
Output goes to `design/marker-census.md` (generated, overwritten, never hand-edited; attach to every checkpoint handover).
