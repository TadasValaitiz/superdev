# Orchestrator Durable State — graph, cursor, ledger

The orchestrator is the long-lived session, so it WILL compact. Its authority must therefore
live in FILES, not memory: post-compaction it re-derives everything from these files + the
landed commits, never from recollection. This is SDD's progress-ledger discipline at
milestone altitude — and like that ledger, updating these files AS EVENTS HAPPEN (not in
batches "later") is what makes recovery lossless.

Home: one orchestration doc in the project's spec/docs area (or three sibling files for a
big milestone). Required sections, project-agnostic:

## 1. The orchestration graph (plan-of-record; co-created with the human at startup)

One node per room:

| Room | Mode (HIL/self/hybrid) | Shape (design/build) | Scope | Owned residuals | ID block | Depends on |
|---|---|---|---|---|---|---|

Edges = dependencies (launch order) + residual-routing (which room absorbs which known
residual). The graph changes only by human-ratified amendment — it is the milestone's
anchor, and the soften-but-own rule applies to it.

## 2. The CURSOR (updated as state changes — the recovery point)

- Current phase / what is LIVE right now (room names + ids + state).
- What landed (per room: published SHA, close summary pointer).
- What's next (the next launch per the graph).
- Prior entries kept as a dated stack (newest first) — the cursor's history IS the
  milestone's narrative; never rewrite, prepend.

## 3. The residual/deviation ledger (cross-room — the zero-leftovers engine)

One row per captured residual/deviation, updated on every report that carries one:

| # | What (one line) | Source (room/report) | Class (in-milestone / GLOBAL) | Routing (→room / →batch / →HIL / →escape-hatch ticket) | Status (open / routed / ruled / filed / done) |
|---|---|---|---|---|---|

Close gate reads directly off this table: every in-milestone row `done/ruled`, every GLOBAL
row `filed` (with its ticket reference). A row without routing is un-triaged work — the
table must never hold one at close.

## 4. The ratification queue (human-facing)

Everything awaiting the human, in one place, so an altitude touchpoint is a ruling session
over an organized queue, not archaeology: pending self-room design docs · R-H holistic
checkpoint batches · deferred forks grouped for a batched ruling · the close package.
Each entry: what · from which room · decision needed · pointer to the full artifact.
