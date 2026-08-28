# The map and the marker families

## Map row grammar {#map-row-grammar}

The current→target map is an ANGLE — `YYYY-MM-DD-<milestone>-angle-NN-current-to-target-map.md` in the flat corpus — and the only document allowed to look backward at code. One row per current-code responsibility:

| id | code area | verdict | test verdict | markers | status | discharging item | anchors |
|---|---|---|---|---|---|---|---|
| M14 | `src/…/bench_engine.py` allocation state | RESHAPE | archive-then-rewrite | MIG-MARK[SEAM][D381] | LOCKED (D372) | item-3.3 | D372, angle-02 |

- **verdict** ∈ KEEP (semantics align; may hide behind a new interface) · RESHAPE (responsibility right, model/algebra conflicts with rulings) · REPLACE (must not remain authoritative; no dual-read, no crosswalk) · DEFER (a later design owns the destination).
- **test verdict** ∈ keep · regenerate · archive-then-rewrite · fix-in-place — set by the item brainstorm; the plan may only refine mechanics, never reverse.
- **discharging item**: written ONLY by the architect, at a sitting, after the orchestrator claims it in a handover and the claim is ACCEPTED in the response block. A row nobody discharges is visible debt.

## MIG-MARK — code markers (bracket form, unchanged) {#mig-mark}

```python
# MIG-MARK[RESHAPE][D372]: cash sleeve still authored here; moves to regime grant in the bench pass
# MIG-MARK[REPLACE][D350]: legacy public bench read — delete at gen-2 cutover
# MIG-MARK[SEAM][D381]: temporary adapter; collapses when TargetBook lands
# MIG-MARK[TEST][D376]: golden pins regenerate after reshape; do not hand-maintain
```
Source greps need a token no identifier can imitate, so code keeps the bracket. Classes are **closed** (RESHAPE · REPLACE · SEAM · TEST); a new class needs a D#. Every D# must resolve to a corpus entry. **A marker is removed with the fix, never resolved in place** — progress IS the count trend. Planting a marker is how an item finishes *now* and defers the clean fix without stalling; under show-must-go-on (D61), `MIG-MARK[MISMATCH-class]` sites are how merged code honestly contradicts a ruling until the re-ruling lands.

## Doc markers — three positional forms, plain vocabulary (D53/D70) {#doc-markers}

The DOC-MARK bracket is retired for documents — the live corpus's own author abandoned it 112:22 (MEASURED), and a grammar that loses to its author's hands under-counts forever. Distinguishability lives in the census script, not author ceremony. The three counted forms:

1. **Claim marker** — line-initial: `**LOCKED (D461):** the claim, as a sentence.`
2. **Section status** — `**Status:** FLEXIBLE — exact fields may move (D372).`
3. **Heading marker** — `### LOCKED — one study asks one typed question` (any heading level; status word leads, em-dash separates).

Vocabulary (glosses in SKILL.md): LOCKED · FLEXIBLE · DEFERRED · BLIND · MISMATCH · SEED-ILLUSTRATIVE · SUPERSEDED→link. The payload after the marker is free — prose, a D#, a link, any mix. Symmetry rule: every doc MISMATCH eventually has a MIG-MARK twin in code or a residue row explaining why not.

## The census — tooling, not fingers {#census}

```bash
scripts/marker-census.sh docs/system-design/            # doc markers: counts per status per file, all three forms
scripts/marker-census.sh docs/system-design/ --since <ref>   # delta vs the last reconcile commit
grep -rn "MIG-MARK" src/ | wc -l                        # code debt, total
grep -rn "MIG-MARK\[REPLACE\]" src/                     # per class
grep -rn "MIG-MARK\[.*\]\[D372\]" src/                  # per decision
```

The recurring census is **ephemeral script output** — quoted into checkpoint handovers, never committed as a file (D60). BLIND/MISMATCH counts are the sitting's mechanical agenda feed. (The milestone's `…-architecture-census.md` is the different, surviving artifact: the charter-time grounding sweep with MEASURED/READ/FLAGGED provenance.)
