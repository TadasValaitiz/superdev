# Protocols — the ledgers between altitudes, with worked examples

Every protocol: a ledger with one writer (or ID blocks), plus a pointer message. When a message and its ledger disagree, the ledger wins.

## The design-checkpoint handover (orchestrator → architect) {#checkpoint-handover}

`design/residue-collections/<date>-checkpoint-<n>.md`, orchestrator single-writer. Declared from **rule + green lights + feel**. Three parts and a question:

```markdown
# Checkpoint 3 — handover (orchestrator → architect)
Green lights: item-3.1 ✓ · item-3.3 ✓ · warehouse-fix ✓   Rule trigger: regime-bridge side merged
Feel: contributions exhausted on this arc — nothing live is producing.

## 1. WHAT WE GOT                                [facts]
- merged: 3.1 regime-migration (claims map rows M12, M14) · warehouse-only-bars
- marker delta: MIG-MARK 41 → 33 (−9 removed with fixes; +1 planted: SEAM D381 in bench_engine)
- residue clusters (deduped, rows cited, no interpretation):
  C1 regime-grant edge cases — R-3.1-4, R-3.1-7, R-WHB-2 → map row M14
  C2 detector timeline leaks into deployable spec — R-3.1-9 → map row M17 (KEEP — contested?)

## 2. WHERE WE FEEL GAPS                         [feel, labelled as feel, by angle]
- paper-wallet boundary is BLIND in the corpus; two clusters brushed it (angle-09 territory)

## 3. UPCOMING FOCUS                             [what the next charters need]
- want to charter: 3.3 bench core. Blocked on: M17 ruling, paper-wallet vision
- not blocked: 3.4 deploy prep — can charter today

## Question to architect: agree or disagree with 1–3?
```

## The response (architect → orchestrator) {#checkpoint-response}

`…-checkpoint-<n>-response.md`, architect single-writer. Agree/disagree per section; the architect may **bounce a cluster back down** ("tactical, not structural — item level, no corpus change"); ends with the session agenda organised by angle and the DOC-MARKs planted:

```markdown
# Checkpoint 3 — architect response
§1 AGREE (M12, M14 will be written as discharged at the session).
§2 PARTIAL: paper-wallet gap real → vision drafting on the agenda; the 3.2↔3.3 wobble is tactical — bounced to item level.
§3 DISAGREE on one: M17 cannot be ruled without the operator — session required first.
Agenda: [M17 fork (lettered) · paper-wallet vision scope · C1 → angle-02 update]
DOC-MARKs planted: map M17 → [MISMATCH][C2] · visions/paper-wallet.md → [BLIND→DEFERRED][session-4]
```

## The milestone handoff {#milestone-handoff}

`design/handoffs/<milestone>.md` — two sections, one writer each; a milestone may not close without it:

```markdown
# Handoff — milestone 3 → milestone 4
## What was built, and what it suggests            [orchestrator]
merged items + map rows discharged + marker census + retro facts (wall-clock, review cycles, token sums)
architectural suggestions harvested from residue that stayed unresolved
## Upfront design for milestone 4                  [architect]
visions ready: paper-wallet.md (LOCKED core, FLEXIBLE fields) · rulings milestone 4 rests on: D…, D…
angles updated this milestone: 02, 08, 09 · BLIND areas milestone 4 will hit: …
```

## The session protocol {#session-protocol}

Open mechanically (BLIND/MISMATCH grep · marker census · the pending handover) → agenda by angle → census before forks → lettered forks, operator rules, D# per ruling → visions before big rulings (any REPLACE/RESHAPE cluster >1 module) → **angle sweep** → INDEX update → response document. A session that skipped the sweep is unfinished.
