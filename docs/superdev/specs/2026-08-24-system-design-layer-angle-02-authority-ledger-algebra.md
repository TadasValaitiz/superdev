# Angle 2 — The Authority and Ledger Algebra

**Purpose:** make "who may write what, and what binds whom" understandable without reading any brief.
**Formal anchors:** R1, R13, R16, R21 · D2, D5, D8, D14, D24 · spec §5.10.
**Series:** 2 of 3.

> **Status guide:** LOCKED · FLEXIBLE · DEFERRED · MISMATCH.

## The central question
When two rooms disagree about a fact or a file, what single rule resolves it without a meeting?

## The algebra (three laws)

1. **Every mutable file has one writer** (or disjoint ID blocks in an append-only log). The §5.10 table is exhaustive; an unlisted write is a violation, not an innovation.        LOCKED
2. **Authority flows down only through charters; findings flow up only through ledgers.** The architect binds an item room *only* via a map row cited in its charter; an item room informs the architect *only* via residue. No side channels; messages are pointers.        LOCKED
3. **Altitude decides the resolver.** Present-tense disputes (what the code does, what a test proves) → the item room is right by default. Future-tense disputes (what the domain should be) → the corpus is right; if the corpus is silent, it is residue, not a local ruling.        LOCKED

## Concrete consequences (pseudo-model, FLEXIBLE)

```python
class LedgerEntry(FrozenModel):
    ledger: LedgerPath          # from the §5.10 table
    writer: RoomId | ScriptId   # exactly one owner or an ID-blocked appender
    binds: set[RoomId]          # who must obey it (charter rows bind; residue binds nobody)
    supersedes: EntryId | None  # never edited, always superseded
```
- A conformance report has `binds == {}` — advisory by construction (D3), not by politeness.
- A DOC-MARK[LOCKED] row has `binds == every room whose charter cites it`.

## Visible collisions
- **Two orchestrator skills** claim the milestone altitude (superdev's vs room-graph's) — reconciled by D24 (superdev's wins; DEFERRED until ratified).
- **residual vs residue, system angle vs item angle** — same words, different ledgers; reconciled by the glossary pairs. MISMATCH in skill texts until wave 1.
- **Discharge**: the room does the work, the orchestrator claims it, the architect writes it — three actors, one map row; reconciled as the two-step in §5.4.

## Reconciled outcome
Every dispute reduces to three lookups: whose ledger, whose altitude, whose charter row. If all three are silent, it is residue by definition.
