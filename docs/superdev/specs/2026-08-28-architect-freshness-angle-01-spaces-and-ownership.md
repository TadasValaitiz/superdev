# Angle 1 — Spaces and ownership

**Purpose:** understand who may write where in a governed repository, why each boundary sits where it does, and how ownership is audited — without reading the spec or the decision log.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D47–D49, D51 (D50 superseded), D60, D68 · experience design §5.6. All quantities in this angle are real measurements from the evidence corpus, not illustrations.
**Series:** 1 of 4.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH current skill text behaves differently today.

## The central question

How can the operator KNOW — mechanically, from the repository itself, without trusting anyone's discipline — that nothing except the architect ever writes the system design?

## Boundaries

This angle starts at the repository's `docs/` root and stops at file ownership and transport: who writes, who reads, how content moves between owners. What the files *say* and how they stay fresh is angle 2's territory; how rooms consume them is angle 3's.

## Concrete journey

### LOCKED — four spaces, one writer each, everything under docs/

A governed repository has exactly four writing territories:

| Space | Sole writer | Everyone reads? | Contains | Audit command |
|---|---|---|---|---|
| `docs/system-design/` | ARCHITECT | yes | the architecture corpus (canon + milestones) | `git log -- docs/system-design/` |
| `docs/orchestration/` | ORCHESTRATOR | yes | operational records, ledgers, handovers, handoffs, execution proposals | `git log -- docs/orchestration/` |
| `docs/superdev/` | ITEM ROOMS (each its own item's files) | yes | item specs, plans, decision logs, scenario distills | per-item `git log` |
| `.superdev/sdd/` + worktrees | each room | owner only | scratch: briefs, reports, seat outputs | git-ignored — no history by design |

Read access is universal — the architect grounds on item specs and code freely; rooms quote the corpus into their sessions; the orchestrator reads everything. But a *write* never crosses a boundary. A session that believes another space's file is wrong does not fix it: it sends a message to the owner describing the problem, and the owner decides. This is the correction route, and it exists so that "who wrote this?" always has exactly one possible answer.

Why everything under `docs/`: in the evidence project, fourteen documentation streams already lived there — canon, decisions, reference, experiments, backlog. A corpus at the repo root would have been the lone orphan outside the tree every reader already walks. Documentation lives where documentation lives.

### LOCKED — the audit is one command

Ownership is not a policy statement; it is a checkable property:

```
git log --format='%an %s' -- docs/system-design/
```

must show architecture commits only — the architect's sittings, its reconcile commits, nothing else. Any foreign commit in that listing means the system is broken, and the check requires no interpretation, no review meeting, no trust. The same audit applies to each space with its own expected author. This is what "mechanically knowable" means: the guarantee is a `git log` invocation away at any moment, for any space.

### LOCKED — inside the architect's space: a small canon and a dated working set

The corpus divides into two layers with opposite maintenance disciplines:

**The canon layer** — `map.md` and `visions/<area>.md`. These files are *rewritten in place*. No banners, no supersession trail inside the file, no dates in the filename. The contract: if it's in canon, you may rely on it today, as written. When the architecture moves, canon moves in the same sitting. The layer stays deliberately tiny — a handful of files — because "always current" is expensive and only affordable at small size. (The evidence project had already invented this shape independently: a three-file `canon/` folder — vision, topology, operating procedures — surviving unstale while hundreds of dated docs churned around it.)

**The dated layer** — `milestones/<slug>/`, one folder per milestone, holding everything that milestone's design produced:

```
milestones/<slug>/
├─ INDEX.md            the angle index, the status vocabulary, this milestone's declared D# range
├─ decisions.md        the milestone's decision log
├─ angles/NN-<slug>.md the angle series
├─ anchors/<topic>.md  the formal design anchors
├─ census.md           the charter-time grounding sweep, every claim provenance-tagged:
│                        MEASURED = output of a command run in that sweep ·
│                        READ = taken from source or a committed doc, file:line given ·
│                        FLAGGED = noticed, unverified — "the work queue, not conclusions"
├─ inputs/             design-intake material the architect curates in — e.g. perspective
│                        ("seat") reports commissioned as inputs to a sitting; copying
│                        them in is authorship of the record (D68: EXECUTION seats'
│                        reports live in the orchestrator's space, never here)
└─ conformance-<item>.md  an advisory conformance read that outgrew its response-block line
```

Dated files are *never rewritten*: a superseded document gets a banner at the top redirecting to current authority, and the prose below stays as the historical record.

The milestone folder is the working set: a sitting touches one folder — the angles being flipped, the log being appended, the index that navigates them, all siblings. History is a *peek*: open the neighbouring milestone's folder directly.

### LOCKED — decision numbers: one stream, many files

Each milestone's `decisions.md` continues a single repo-wide D# stream — the bench milestone's log runs D350–D494 precisely because it continued a global count. Each INDEX declares its folder's range ("this milestone owns D350–D494"), so a bare "D372" cited from anywhere in the repository resolves to exactly one folder, forever. If two milestones ever run in parallel, they receive pre-assigned disjoint number blocks at charter time (milestone A rules D500–D599, milestone B D600–D699) — the same collision-avoidance trick used when parallel rooms once shared an append-only ledger. This is what makes cross-milestone citation safe without a global file.

### LOCKED — residue transport: rooms report, the orchestrator comprehends

The one flow that crosses all four spaces is the residue flow — design-class findings surfacing from item work. Its history explains its shape. The first design was a shared append-only file (`residue.jsonl`) that any room appended to, with disjoint ID blocks preventing numbering collisions. That design was born in the loop era, when agents shared one working directory and could not message each other — append-only-with-ID-blocks was how writers who couldn't talk avoided conflicts. Both premises died: rooms now message freely, and rooms now work in *isolated worktrees*, where a "shared" file is not actually shared — each branch sees its own copy until merge, and two rooms appending to the same file tail on different branches collide textually when the second rebases for its fast-forward publish. A per-room-files variant was considered and rejected in the same discussion. The operator's ruling: keep the working model —

1. Inside the room, most findings are **resolved internally** — the room grounds against the corpus, realizes the discrepancy is its own misreading or fixable within its charter, and the finding dies there. The room is the cheapest place to kill a false alarm.
2. What survives goes into the room's **report**, in the room's own words, beside its item files — the report is already the room's authored, durable record.
3. The **orchestrator comprehends the reports** and tracks surviving residue in his own ledger, in his own space, written in his own session on the milestone branch — so the worktree visibility problem never arises. His comprehension is a feature, not relay loss: he alone sees across rooms, so he is the one who notices rooms A and C hitting the same seam from opposite sides.
4. Every ledger entry is **typed** — residue rows tagged `discrepancy | insight | duplicate-risk | question`, process-feedback rows `friction | brief-gap | measurement | win` — so streams stay grep-separable, and an entry's fate is recorded by later artifacts *citing its ID* (a cluster, a ruling), never by editing the row.

### LOCKED — the handoff splits; no file has two writers

The old milestone handoff was one file with an orchestrator section and an architect section — two writers, one file, the exact thing the ownership law forbids. It splits naturally: the orchestrator writes his half (what was built, claims, retro facts) in `docs/orchestration/handoffs/` — note the near-homophone: `handoffs/` are per-MILESTONE close documents in the never-pruned keep-set, while `handovers/` (angle 2) are per-CHECKPOINT message companions pruned on the rolling window; the architect's half — "upfront design for the next milestone" — *is the creation of the next `milestones/<slug>/` folder itself*. The handoff is not a document the architect contributes a section to; it is the birth of the next working set.

## What the ownership law does not guarantee

The law is about writes, and only writes. It does not guarantee:

- **freshness of what you read** — reading a stale operational file from another space is permitted and expected; its OPERATIONAL RECORD stamp (angle 2), not the ownership law, tells you how much to trust it;
- **lossless comprehension** — the orchestrator's residue ledger is his comprehension of room reports, and comprehension can drop or distort; the bound is auditability, not perfection: at milestone close, item-room reports can be diffed against ledger rows, and D51's revisit clause reopens the transport if that audit finds losses;
- **content quality** — a space's sole writer can still write something wrong; correctness comes from reviews and reconciliation, not from ownership;
- **protection outside docs/** — code and tests follow the item-room worktree rules, not this law.

## Visible collisions

- **Doctrine versus the work.** The residue-transport fork's instructive part (the fork itself is settled in the journey above): the first redesign — doctrinally cleaner per-room files — was still wrong, because it optimized the law rather than the work. When a purity argument and a working practice collide, ask what problem the purity actually solves before paying for it.
- **Milestone-scoped logs vs global citation.** Self-contained folders pull toward per-milestone numbering; cross-references pull toward one global file. The reconciliation — local files, global stream, declared ranges — takes both sides' actual need and discards both sides' preferred mechanism.
- **The two-writer handoff vs the law.** Resolved not by choosing a writer but by discovering the file was two artifacts wearing one filename.

## Flexible and deferred

FLEXIBLE: exact filenames and sub-layout inside `docs/orchestration/` (the owner arranges his own space); the ledger file format (jsonl vs md tables). Nothing DEFERRED in this angle.

## Reconciled outcome

All load-bearing claims LOCKED: four spaces with one writer each and a one-command audit; canon/dated split inside the architect's space; milestone folders on a global D# stream; report-based residue transport with typed rows; the handoff split. The single-writer law admits no exception anywhere in the repository — the previous exceptions (shared residue file, two-section handoff) were both dissolved rather than granted.
