# Parallelism inside SDD — reads always, quick-fix lanes after the shape

Rewritten 2026-08-25 under D37/D40 (see the system-design decision log). The old mode —
file-disjoint implementer lanes in isolated worktrees, controller merge-audits, the
`Execution: subagent-driven-parallel` plan header — is RETIRED: everything lands in one
worktree, and the initial implementation of an arc is one effortful, non-parallel write by
its carrying implementer. Parallelism is a **phase property**, not a plan mode.

## What always runs in parallel (read-only)

- Grounding inventories, censuses, probes — no edits, no commits, no state-mutating runs.
- **Reviews concurrent with implementation**, pinned at the last checkpoint SHA — never
  against a tree still being mutated. Reviewer-authored adversarial tests are the one
  sanctioned reviewer write (task-reviewer-prompt.md): new test files only, uncommitted,
  handed over in the report.
- Next-arc grounding during the current arc's tail; delegated design exploration
  (self-brainstorming, write-only to spec files, assumptions queued).

## The quick-fix phase (parallel writes, same worktree — AFTER the shape exists)

Once an arc's shape has landed (post a cleared checkpoint), small parallel writes are
allowed in the SAME worktree: checkpoint findings, detail work, failing-test cleanup,
doc regeneration. Rules:

- **Follow-up seats, not second implementers:** each lane is a short-lived fix scope with
  a named file set; the carrying implementer (resumed) or a follow-up agent holds it.
- **Disjoint file sets per lane, declared in the dispatch;** overlapping fixes go to ONE
  lane. Two lanes conflicting in the same files twice → per-file locks (D37 revisit hook).
- **Commits are serial** — lanes edit in parallel, land one at a time; the controller (or
  the room) sequences the commits and runs the fast gate between landings.
- **Never a broad implementation in a lane.** If a "fix" grows past its file set, it is a
  new arc: stop the lane, charter it properly.

## Integration models — lanes vs rooms (unchanged)

Lanes here are HEADLESS fix scopes inside one room's worktree; the room self-publishes the
whole worktree via FF-CAS when its close gate passes. ENTERABLE ROOMS (the orchestrator
skill) are full peer sessions that self-publish — an orchestrator never merges room work.
Same repo, two models — pick by what the worker is, never blend.

## Failure recovery (kept — learned the hard way)

- On an agent death: **inspect the worktree FIRST** (`git status`/`git log` — what
  committed, what survives uncommitted), then **resume the same agent** (RESUME metadata
  in its report / the ledger's RESUME row) with the verified salvage state. Never blind
  re-dispatch — it double-writes.
- Under instability: wip-commit early and often — a drop costs minutes, not work.
- The progress ledger records every dispatch, landing, and adjudication AS IT HAPPENS;
  after any controller compaction, trust the ledger and `git log` over memory.
