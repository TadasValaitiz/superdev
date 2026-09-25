# Orchestrator Durable State — the operational surface (`docs/orchestration/`)

The orchestrator is the long-lived session, so it WILL compact. Its authority must live in
FILES, not memory: post-compaction it re-derives everything from these files + landed
commits, never from recollection. Update AS EVENTS HAPPEN, not in batches. Vocabulary:
[taxonomy.md](taxonomy.md).

**The surface law (D60):** `docs/orchestration/` is the OPERATIONAL surface — files exist
as message companions and working state; they are point-in-time, never reconciled, and
every file opens with the standing stamp:

> OPERATIONAL RECORD — point-in-time, never reconciled. May be outdated the moment you
> read it. Design authority lives in docs/system-design/ (as of its last reconcile).

## The layout — one folder per milestone

```
docs/orchestration/
  ROADMAP.md                      the ordered milestones — the human ratifies
  conventions.md                  project-wide conventions (kept)
  process-feedback.md             project-wide: retrospectives feed it; input to superdev:self-improvement (kept)
  milestones/<milestone>/
    SCOPE.md                      MILESTONE SCOPE (the human approves; the sweep judges against it)
    plan.md                       MILESTONE PLAN + the architect's advice + the human's GO
    map.md                        MAPPING output: ownership, shared seams, dependencies
    graph.md                      the room graph + grants
    cursor.md                     the recovery point
    triage.md                     RESIDUAL TRIAGE of every room's RESIDUALS FILE
    briefs/                       the rooms' briefs + the shared room rules
    residuals/<room>.md           each room's RESIDUALS FILE, left at ITEM CLOSE
    retros/<room>.md              each room's RETROSPECTIVE, left at ITEM CLOSE
    handoffs/                     item hand-offs + the milestone hand-off
```

A new milestone starts in a new folder. A closed milestone's folder stays as the record; git is the archive.

## 1. The room graph (`graph.md` — plan-of-record; co-created with the human at MILESTONE PLAN)

One node per room; MILESTONE PLAN also declares the milestone's MODE (HUMAN | AUTONOMOUS —
canonical law: superdev:system-design SKILL.md#mode-law), recorded here and in
`conventions.md` so every room and the architect can read it.

| Room | Mode (HIL/self/hybrid) | Shape (design/build) | ITEM SCOPE (from map.md) | Write surface | D# block | Depends on |
|---|---|---|---|---|---|---|

Edges = dependencies (launch order) and shared seams (from `map.md`). Grants beyond a room's
write surface are recorded here as numbered amendments. The graph changes only by
human-ratified amendment.

## 2. The CURSOR (`cursor.md` — updated as state changes; the recovery point)

Current phase / what is LIVE · what landed (per room: published SHA, close pointer) ·
what's next · prior entries as a dated stack, newest first — never rewrite, prepend.

## 3. Residuals — files from the rooms, triage by the orchestrator

- **Rooms never file backlog items.** A room closes residuals inside its ITEM SCOPE before ITEM CLOSE, reports the
  rest as RES when found, and leaves them all in its **RESIDUALS FILE** at ITEM CLOSE (format: taxonomy.md §5).
- **RESIDUAL TRIAGE (`triage.md`), before the next milestone starts:** the orchestrator reads every residuals file and
  gives each residual ONE disposition — **dropped** (with why) · **merged** (into another residual) · **carried**
  (into the next MILESTONE PLAN, with its target item). Nothing reaches a shared backlog without this triage.
- **Residue ≠ residual:** a design-class finding goes to the architect directly by ASK-ARCHITECT; the orchestrator
  does not keep a residue ledger.

## 4. The process-feedback ledger (`process-feedback.md`, project-wide)

One row per proposal from each room's RETROSPECTIVE (retrospective-template.md), plus the orchestrator's own measured
facts; kinds `friction | brief-gap | measurement | win`. Feeds brief adaptation now (every NEW brief) and
superdev:self-improvement in batch (the human runs it).

## 5. What awaits the human

There is no separate queue file: every "human needed" moment is a **HIL-NEEDED** message naming the room where the
human rules; the orchestrator lists the open ones in `cursor.md` (what · who is blocked · where written up) until
RULED arrives.
