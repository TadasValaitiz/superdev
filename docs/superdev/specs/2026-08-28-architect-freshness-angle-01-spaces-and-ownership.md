# Angle 1 — Spaces and ownership

**Purpose:** understand who may write where, and why, without reading the whole spec.
**Formal anchors:** D47–D49, D51 (D50 superseded), D60 (decisions log); spec §5.1/§5.2 (R1–R4).
**Series:** 1 of 4.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH code behaves differently today.

## The central question
How can the operator KNOW — mechanically, not by trust — that nothing but the architect ever writes the system design?

## Boundaries
Starts at the repo's docs/ root; stops at file ownership and transport. What the files SAY is angle 2's territory; how rooms consume them is angle 3's.

## Concrete consequences
Four spaces, one writer each: `docs/system-design/` (ARCHITECT: map.md, visions/, milestones/<slug>/ with INDEX·decisions.md·angles/·anchors/·census.md·inputs/), `docs/orchestration/` (ORCHESTRATOR: graph, cursor, ledgers, handovers/, handoffs/, execution/), `docs/superdev/` (ITEM ROOMS: specs, plans, scenarios), `.superdev/sdd/` + worktrees (scratch). The audit is one command: `git log docs/system-design/` shows only architect commits — anything else is a broken system. **LOCKED.**
Canon vs dated inside the architect's space: map.md/visions rewritten in place, always reliable; milestones/ never rewritten — banners + status flips only. **LOCKED.**

## Visible collisions
- **Multi-writer ledgers vs single-writer law:** three designs were tried live — shared append-only residue.jsonl (dies: worktrees make "shared" false — invisible until merge, tail-conflicts at rebase), per-room ledger files (rejected: operator kept the working report-based model; the extra docs/ledgers/ root would have multiplied roots), and the winner: rooms REPORT, orchestrator comprehends and tracks in his own ledger (D51). Messaging replaced the inbox era's reason to exist.
- **The two-writer handoff file** vs the law: split — orchestrator half in his space; architect half IS the next milestone folder's birth (D49).
- **Decision-log placement:** global file vs milestone folder — milestone folder won (self-contained working set, D48), with D#s staying one global stream so any bare D# resolves to one folder.

## Reconciled outcome
All LOCKED: four spaces, one writer each, report-based residue transport, canon/dated split, milestone-scoped logs on a global D# stream. FLEXIBLE: exact filenames inside docs/orchestration/. Nothing DEFERRED.
