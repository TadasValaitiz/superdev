# Chartering — granularity, the ticket taxonomy, and the best path

How the milestone becomes items, and items become a launch order. Ruled in D44/D45 (system-design decision log); the glossary is in superdev:system-design.

## The seven principles (cut items by these)

1. **Items are cut from the map, never from a to-do list** — an item is a coherent cluster of map rows it will discharge; charter cites them. No rows → design gap, not an item.
2. **Floor:** big enough for a broad arc — small work never gets a room (no micro tier); it's absorbed or waits.
3. **Ceiling:** one carrying implementer, merged inside the milestone. Needs two writers at once → it's two items with a bridge.
4. **Every item is independently deliverable and testable** — able to run its applicable passes and merge alone. A part that can't is a wrong cut, never a relaxed rule.
5. **Write-surface separability decides item vs items** — heavy file overlap = one item or serial; disjoint = parallel rooms welcome.
6. **Dependencies are never parallelised (D44):** producer merges first; the consumer's charter waits. No frozen contracts, no stubs — parallelism exists only between fully independent items.
7. **The fan-out cap is the operator's attention** — every item bills one brainstorm + one shape agreement; size the live-room count to their week, not to compute.

## The ticket taxonomy — types and done-bars

All types: merges · worktree retired · tests per disposition · residue filed.

| type | is | done-bar addition |
|---|---|---|
| **foundation item** | the base others build on — usually an unblocking kernel; often no user-facing surface | conformance-relevant rows claimed; **no checkride/scenario**, but the charter NAMES which downstream item will exercise it live — nothing ships forever unexercised |
| **surface item** | changes what the operator sees/touches | + checkride + date-stamped scenario capture |
| **ad-hoc room** | probe · spike · sweep — knowledge, not product code | findings filed (census/residue/report); probe-gate exempt; never silently becomes an item |
| **quick fix** | post-shape detail | never its own room — quick-fix lanes / follow-up seats inside an existing room |
| **backlog item** | parked question | not work until ruled into a milestone boundary at the co-plan |

## The best-path algorithm (yours to compute; the operator ratifies at co-plan)

1. **DAG:** nodes = candidate items (map-row clusters), edges = bridges.
2. **Blocking radius** per node = transitive dependents.
3. **Split high-radius nodes along corpus seams only:** extract the **unblocking kernel** — the minimal foundation item producing what dependents consume — so it merges earliest. A cut with no corpus seam is a design gap → residue for the architect; NEVER an improvised boundary. The architect is not in the loop on splits — it thinks holistically; seams are its product, scheduling is yours.
4. **Ratify:** present the graph + splits + types at the co-plan; the operator rules; record it as the milestone-graph section of the cursor (nodes carry type · radius · ready-state).
5. **Schedule greedily:** ready set = items with ALL dependencies MERGED. Launch from it up to the room budget (principle 7). On every merge: recompute, launch the newly ready. Priority = **unblocks-most-soonest**, never biggest or oldest.
6. **Degenerate kernel escape:** a kernel too small for a room becomes the giant item's FIRST plan checkpoint with an early partial FF-CAS publish — same unblocking effect, one room.

## Red flags
- Two rooms "coordinating" over a shared interface mid-flight — that dependency should have been serial or the cut different.
- A giant item everyone waits on, unsplit — compute its radius; the kernel wanted out weeks ago.
- A split part that can't run its passes alone — the cut followed convenience, not a seam.
