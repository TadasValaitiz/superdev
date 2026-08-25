# Item angle template

An item angle is the operator's angle contract at item scale: a deliberately partial way to examine THIS item's design. It lives beside the item's spec (`YYYY-MM-DD-<topic>-angle-NN-<slug>.md`), never in `design/angles/`; no INDEX or sweep obligations. Repetition with system angles is expected. Full theory: superdev:system-design `angle-guide.md`.

```markdown
# Angle N — <one-phrase name>

**Purpose:** <one reader-oriented sentence: understand X without reading Y.>
**Formal anchors:** <R#/D# of the item spec; system-design D#s and map rows it touches, at file:line.>
**Series:** N of M.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH code behaves differently today ·
> SEED-ILLUSTRATIVE example only.

## The central question
<one sentence.>

## Boundaries
<where this journey starts, stops, and which neighbouring concern owns what's outside.>

## Concrete consequences
<named states, model sketches (FLEXIBLE by default), call sites, pseudo-code journeys.>

## Visible collisions
<where forces pull apart — including collisions with system angles, cited at file:line.
A collision with a LOCKED system ruling is residue, never resolved here.>

## Reconciled outcome
<what is LOCKED/FLEXIBLE/DEFERRED after this angle, in one short paragraph.>
```
