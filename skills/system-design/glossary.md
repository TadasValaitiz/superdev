# The shared vocabulary

One table, one meaning per word, across every skill that touches the development organisation. Skills link here; none restates it.

## Boundless (design side)
| Term | Means |
|---|---|
| **corpus** | the design law's teaching surface as files: `docs/system-design/` — FLAT (D69), filenames carry milestone+type; the RECONCILED surface |
| **system angle** | one deliberately partial view through the whole system — a `…-angle-NN-<slug>.md` file in the flat corpus, under the five-kind contract and the anti-loosening machinery (INDEX file, sweep, staleness grep) |
| **item angle** | the same idea at item scale: lives beside its item's spec, operator's template; no INDEX obligations, and the brainstorm SESSION's reconcile sweep DOES apply to it (the corpus-level angle sweep does not). Overlap with system angles is expected |
| **vision** | a post-migration domain document (`…-post-migration-domain.md`, flat); the grounding source wherever the map says code will change |
| **design session / sitting** | one ruling sitting (who rules = the mode law): census-first, forks per the Fork Presentation Standard, RECONCILIATION as the mandatory close (statuses, banners, canon, the named reconcile commit) |

## Bridge state
| Term | Means |
|---|---|
| **residue** | a design-class finding flowing UP by REPORT (D51): room's own files → room report → orchestrator's typed ledger (kinds: discrepancy · insight · duplicate-risk · question) → handover clusters → architect at a checkpoint. Rooms never write ledgers |
| **residual** | (unchanged, entrenched) a loose end drained before a room/run closes — residual ledger, RES events. *Residue ≠ residual; both stay* |
| **marker** | greppable status/deferred-work note: `MIG-MARK[..]` bracket in CODE; three positional plain-word forms in DOCS (claim `**LOCKED:**` · section `**Status:**` · heading `### LOCKED —`, D53/D70); removed/flipped with the fix, never resolved in place |
| **backlog** | parked open questions awaiting disposition (`docs/backlog/`). The word "docket" is retired |

## Bounded (implementation side), largest → smallest
| Term | Means |
|---|---|
| **milestone** | THE implementation boundary; the orchestrator's whole world; closes only with its handoff. (The word "phase" is retired as a work-unit name; decision-log lifecycle fields keep it) |
| **item** | one chartered concern → one item room; charter cites the map rows it discharges |
| **design checkpoint** | orchestrator-declared moment (rule + green lights + feel): ONE handover doc (operational) up; a response BLOCK in the milestone decisions file + rulings + the reconcile commit back |
| **plan checkpoint** | `## Checkpoint Cn` inside an item's plan: a room-internal gate group; cleared by the room's reviewer role; **never** notifies the architect. ("stage" and plan-internal "Milestone Mn" are retired) |
| **task** | one role-carried unit inside a plan — broad for Codex/opus-class workers, bite-size for Sonnet-class |
| **bridge** | the seam between bounded things (items, domains, CLIs) where a dependency crosses; ordering falls out of contested bridges. ("joint" retired) |
| **handoff** | the milestone-close package, SPLIT (D49/D68): orchestrator's half in `docs/orchestration/handoffs/` (never pruned); the architect's half IS the next milestone's document set coming into existence. Contrast **handover** (per-checkpoint, pruned). ("runway" retired) |
| **arc** | one broad, role-carried unit of work: one carrying implementer, many files, plan checkpoints inside |
| **carrying implementer** | the single agent that writes an arc's initial implementation — never parallelised |
| **quick-fix lane** | a small parallel write scope in the SAME worktree, post-shape: disjoint files, serial commits, follow-up seats |
| **test disposition** | {keep · regenerate · archive-then-rewrite · fix-in-place} — set at brainstorm, refined (never reversed) by the plan |
| **harvest file** | the business requirements extracted from tests BEFORE archiving; reviewer-signed; the source for rewrite-territory requirement tests |
| **scenario** | a date-stamped operator-journey INTENT document (goal · journey · what-good-looks-like) in `docs/superdev/scenarios/` — distilled from a checkride, re-driven by the battery; never a replayable script |
| **battery** | the milestone-close ad-hoc room that walks every scenario intent against the current surface |
| **foundation item** | an item building the base others consume (often an unblocking kernel); testable and mergeable but usually surface-less — no checkride, but its charter names the downstream item that will exercise it live |
| **surface item** | an item changing what the operator sees/touches — checkride + scenario capture in its done-bar |
| **blocking radius** | an item's transitive dependents in the milestone DAG — the number it holds hostage |
| **unblocking kernel** | the minimal foundation part of a high-radius item that, merged first, releases its dependents |
| **gate receipt** | the evidence line a plan checkpoint or the close gate records: tests run, marker delta, map rows claimed |

## The freshness layer (D47–D71)
| Term | Means |
|---|---|
| **reconciled surface** | `docs/system-design/` — grab anything, it matches reality or wears a marker pricing your trust; kept true by reconciliation, architect sole writer |
| **operational surface** | `docs/orchestration/` — message-companion files + working state; stamped OPERATIONAL RECORD, never reconciled, PRUNED instead; orchestrator sole writer |
| **reconcile commit** | the named commit (`docs: reconcile <milestone> architecture authority`) that closes every architect sitting; briefs cite architecture as-of its SHA |
| **mode law** | HUMAN vs AUTONOMOUS, declared at the co-plan, honored by every ruling gate; reserved forks (money/irreversibility, blast radius, taste) always human; canonical text: system-design SKILL.md#mode-law |
| **handover** | the per-checkpoint operational document (trio + claims + clusters + facts); pruned on the rolling window. ≠ handoff |
| **execution proposal** | the orchestrator's celebration-led delivery hypothesis (`docs/orchestration/execution/`), authored via two opposed seats, adjudicated by the five rules; reconcilable, never locked, authorizes no code (D55) |
| **celebration** | an operator-visible capability proven by a real journey with refusal/recovery evidence — the proposal's unit |
| **pointer relay** | the orchestrator forwarding a room's plan-time deviation pointer to the architect immediately — pointers, never paraphrase (D61) |
| **pruning window** | at milestone N's close, milestone N−1's operational files are deleted after harvesting; git is the archive (D62) |
| **rider** | a requirement the operator attaches while picking a fork variant; enters the law with the variant (recorded in the D# Decided-by line) |
| **register law** | conversation economy never applies to deliverables; a deliverable is a teaching document readable without the log (D66) |
| **full-set contract** | a plan answers to spec + log + ALL angles + census; angle content governs spec silence; contradictions stop planning (D71) |

## Kept unchanged
charter · grounding probe / census · checkride · cursor · debrief · gate · room · green light · D# (design) · O# (orchestration method) · R5/RES (room events)

## The gate ladder (named, never numbered)
**ruling gate** (operator approval: corpus changes bind only when ruled) · **probe gate** (veto: no *item* charter without a census; ad-hoc probe rooms exempt) · **publish recipe** (mechanical FF-CAS; never blocks for architectural reasons) · **close gate** (veto: room close requires worktree merged+retired and archived tests deleted with manifest kept).
