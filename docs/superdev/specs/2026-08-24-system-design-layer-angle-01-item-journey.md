# Angle 1 — One Item's Journey, Charter to Corpus

**Purpose:** follow a single item end to end so every seam between rooms is visible without reading the briefs.
**Formal anchors:** R4, R7–R8, R25–R28 · D3, D7, D26–D32 in the [decision log](./2026-08-24-system-design-layer-decisions.md).
**Series:** 1 of 3.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move · DEFERRED another session owns it · MISMATCH today's skills behave differently.

## The central question
What happens to one chartered item, minute by minute, and at which moments does authority change hands?

## The journey

```text
charter (probe gate: census attached, map rows cited, test disposition set)      LOCKED
  → room launches, worktree created (room-owned, cradle to grave)                LOCKED
  → operator present?
      yes → HIL brainstorm: corpus passages quoted at file:line,
            angle-by-angle, item angles written beside the spec                  LOCKED
      no  → self-brainstorming to the ratification gate; waits as a desk DECIDE  LOCKED (D30/D33; mechanics land across waves 1–2)
  → writing-plans: execution-shape variants proposed (tasks · deliverables ·
    workers · rooms) → operator agrees                                           LOCKED
  → THE FLIP: agreement = auto-start; room goes autonomous; desk shows
    "execution started"; operator may stay as observer                           LOCKED
  → broad role-carried arcs (Codex first-class, not default); reviews at
    plan checkpoints, never per-mini-task; fixes by resuming the implementer     LOCKED (mechanics FLEXIBLE, wave 2)
  → discrepancy with architecture? resolve LOCALLY, plant MIG-MARK,
    file residue — never stall, never do L1 design                               LOCKED
  → FF-CAS merge (mechanical; nothing architectural can block it)                LOCKED
  → close gate: worktree retired + archived tests deleted, manifest kept        LOCKED
  → R5 debrief + green light + RESUME registry entries                           LOCKED
  → (later, design checkpoint) its residue reaches the architect as part of
    a collection; its discharge is written into map.md at the session            LOCKED
```

## Concrete consequences
- The item's outputs are enumerable: merged code · retired worktree · MIG-MARKs · residue rows · process-feedback rows · item spec + angles + decision log · archive manifest + harvest · R5 with green light · resume metadata. Anything else is a contract violation.
- A room has exactly two waiting states: the D30 ratification wait (pre-flip) and a DECIDE classified BLOCK (any time). Everything else is motion.

## Visible collisions
- **"Always merges" vs "operator required to brainstorm"** — collided in review; reconciled by D30's single named exception (the ratification wait). MISMATCH until its mechanics land (chartering side wave 1, auto-enter side wave 2).
- **Long arcs vs per-task review ceremony** — today's skill text (bite-size tasks, review-per-task) is a MISMATCH with D32's long cadence.

## Reconciled outcome
An item is a bounded, always-finishing machine whose only human moments are the brainstorm and one agreement; everything it cannot decide leaves as a marker or a residue row, not as a stall.
