# The shared vocabulary

One table, one meaning per word, across every skill that touches the development organisation. Skills link here; none restates it.

## Boundless (design side)
| Term | Means |
|---|---|
| **corpus** | the design law as files: `design/` — angles, visions, map, decisions, residue, conformance, handoffs |
| **system angle** | one deliberately partial view through the whole system, in `design/angles/` under the five-kind contract and the anti-loosening machinery (INDEX, sweep, staleness grep) |
| **item angle** | the same idea at item scale: lives beside its item's spec, operator's template, no INDEX/sweep obligations. Overlap with system angles is expected |
| **vision** | a post-migration domain document in `design/visions/`; the grounding source wherever the map says code will change |
| **design session** | one operator-ruled sitting: census-first, lettered forks, angle sweep at close |

## Bridge state
| Term | Means |
|---|---|
| **residue** | a design-class finding (discrepancy, insight, duplicate risk) flowing UP: room → residue ledger → orchestrator collection → architect at a design checkpoint |
| **residual** | (unchanged, entrenched) a loose end drained before a room/run closes — residual ledger, RES events. *Residue ≠ residual; both stay* |
| **marker** | greppable deferred-work note: `MIG-MARK` in code, `DOC-MARK` in docs; removed with the fix, never resolved in place |
| **backlog** | parked open questions awaiting disposition (`docs/backlog/`). The word "docket" is retired |

## Bounded (implementation side), largest → smallest
| Term | Means |
|---|---|
| **milestone** | THE implementation boundary; the orchestrator's whole world; closes only with its handoff. (The word "phase" is retired as a work-unit name; decision-log lifecycle fields keep it) |
| **item** | one chartered concern → one item room; charter cites the map rows it discharges |
| **design checkpoint** | orchestrator-declared verify-and-hand-off moment (rule + green lights + feel); fires the handover protocol to the architect |
| **plan checkpoint** | `## Checkpoint Cn` inside an item's plan: a room-internal gate group; cleared by the room's reviewer role; **never** notifies the architect. ("stage" and plan-internal "Milestone Mn" are retired) |
| **task** | one role-carried unit inside a plan — broad for Codex/opus-class workers, bite-size for Sonnet-class |
| **bridge** | the seam between bounded things (items, domains, CLIs) where a dependency crosses; ordering falls out of contested bridges. ("joint" retired) |
| **handoff** | the milestone-close package: architectural suggestions + the next milestone's upfront design, visions included. ("runway" retired) |
| **arc** | one broad, role-carried unit of work: one carrying implementer, many files, plan checkpoints inside |
| **carrying implementer** | the single agent that writes an arc's initial implementation — never parallelised |
| **quick-fix lane** | a small parallel write scope in the SAME worktree, post-shape: disjoint files, serial commits, follow-up seats |
| **test disposition** | {keep · regenerate · archive-then-rewrite · fix-in-place} — set at brainstorm, refined (never reversed) by the plan |
| **harvest file** | the business requirements extracted from tests BEFORE archiving; reviewer-signed; the source for rewrite-territory requirement tests |
| **scenario** | a date-stamped operator-journey INTENT document (goal · journey · what-good-looks-like) in `design/scenarios/` — distilled from a checkride, re-driven by the battery; never a replayable script |
| **battery** | the milestone-close ad-hoc room that walks every scenario intent against the current surface |
| **gate receipt** | the evidence line a plan checkpoint or the close gate records: tests run, marker delta, map rows claimed |

## Kept unchanged
charter · grounding probe / census · checkride · cursor · debrief · gate · room · green light · D# (design) · O# (orchestration method) · R5/RES (room events)

## The gate ladder (named, never numbered)
**ruling gate** (operator approval: corpus changes bind only when ruled) · **probe gate** (veto: no *item* charter without a census; ad-hoc probe rooms exempt) · **publish recipe** (mechanical FF-CAS; never blocks for architectural reasons) · **close gate** (veto: room close requires worktree merged+retired and archived tests deleted with manifest kept).
