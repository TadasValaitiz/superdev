# Orchestrator Durable State — the operational surface (`docs/orchestration/`)

The orchestrator is the long-lived session, so it WILL compact. Its authority must live in
FILES, not memory: post-compaction it re-derives everything from these files + landed
commits, never from recollection. Update AS EVENTS HAPPEN, not in batches.

**The surface law (D60):** `docs/orchestration/` is the OPERATIONAL surface — files exist
as message companions and working state; they are point-in-time, never reconciled, and
every file opens with the standing stamp:

> OPERATIONAL RECORD — point-in-time, never reconciled. May be outdated the moment you
> read it. Design authority lives in docs/system-design/ (as of its last reconcile).

Because nothing here is reconciled, it is PRUNED instead (D62): at milestone N's close,
milestone N−1's operational files are deleted after harvesting (handovers, raw ledgers,
spent backlog items, proposal drafts). The never-pruned keep-set: `handoffs/`,
`conventions.md`, the improvement-notes stream. Git is the archive beyond the window.

## 1. The orchestration graph (plan-of-record; co-created with the human at the co-plan)

One node per room; the co-plan also declares the milestone's MODE (HUMAN | AUTONOMOUS —
canonical law: superdev:system-design SKILL.md#mode-law), recorded here and in
`conventions.md` so every room and the architect can read it.

| Room | Mode (HIL/self/hybrid) | Shape (design/build) | Scope | Owned residuals | D# block | Depends on |
|---|---|---|---|---|---|---|

Edges = dependencies (launch order) + residual-routing. The graph changes only by
human-ratified amendment.

## 2. The CURSOR (updated as state changes — the recovery point)

Current phase / what is LIVE · what landed (per room: published SHA, close pointer) ·
what's next · prior entries as a dated stack, newest first — never rewrite, prepend.

## 3. The typed ledgers (yours alone — built from room REPORTS, D51)

Rooms never write these; you comprehend their reports (and relay plan-time deviation
pointers to the architect immediately, D61 — relay pointers, never paraphrase):
- **Residue ledger** — design-class findings; kinds `discrepancy | insight | duplicate-risk | question`; each row cites its source report. Disposition lives in handover clusters + response verdicts citing row ids — rows are never edited.
- **Process-feedback ledger** — rooms' R5 lines + your `measurement` rows; kinds `friction | brief-gap | measurement | win`. Feeds brief adaptation now, self-improvement in batch.

## 4. The residual/deviation ledger (cross-room — the zero-leftovers engine)

| # | What (one line) | Source (room/report) | Class (in-milestone / GLOBAL) | Routing (→room / →batch / →HIL / →escape-hatch ticket) | Status (open / routed / ruled / filed / done) |
|---|---|---|---|---|---|

Close gate reads off this table: every in-milestone row done/ruled, every GLOBAL row filed.
Residue ≠ residual: design-class findings go to ledger 3, never to the escape hatch.

## 5. The decision queue (`docs/orchestration/decision_queue.md`) (human-facing)

Everything awaiting the human in one place: pending self-room design docs · R-H batches ·
deferred + RESERVED forks (mode law: money/irreversibility, blast radius, taste — always
human, both modes) · in AUTONOMOUS mode, the FLAGGED pick list (every autonomous pick,
newest first — the next human touchpoint opens here) · the close package.
