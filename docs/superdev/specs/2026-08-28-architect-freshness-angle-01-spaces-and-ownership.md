# Angle 1 — Spaces and ownership

**Purpose:** understand who may write where in a governed repository, why each boundary sits where it does, and how ownership is audited — without reading the spec or the decision log.
**Formal anchors:** [decision log](./2026-08-28-architect-freshness-decisions.md) D47–D49 (D47/D48 amended by D69: flat corpus), D51 (D50 superseded), D60, D68, D69 · experience design §5.6. All quantities in this angle are real measurements from the evidence corpus, not illustrations.
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

### LOCKED — inside the architect's space: flat, with filenames doing the work of folders

The corpus is one flat directory. This is not a compromise — it is what the live corpus
chose for itself (40+ files by its fourth checkpoint) and the reason is load-bearing:
the documents cross-link densely with relative `./` links, and in a flat directory a
link can never break because nothing ever moves. The filename carries everything a
folder hierarchy would have — date, milestone, type, topic:

```
docs/system-design/
├─ 2026-08-20-bench-angle-06-adaptation-journey.md      an angle (the current→target
│                                                        map is itself an angle)
├─ 2026-08-20-bench-runtime-composition-design.md       a formal design anchor
├─ 2026-08-20-bench-architecture-angles.md              the milestone INDEX: angle list,
│                                                        status language, declared D# range
├─ 2026-08-20-bench-architecture-decisions.md           the milestone decision log
├─ 2026-08-20-bench-architecture-census.md              charter-time grounding sweep:
│                                                        MEASURED = command output that sweep ·
│                                                        READ = from source/doc, file:line ·
│                                                        FLAGGED = noticed, unverified —
│                                                        "the work queue, not conclusions"
├─ 2026-08-20-bench-architecture-glossary.md            the milestone glossary
├─ 2026-08-20-bench-architecture-inputs/                the ONE subfolder kind: design-intake
│                                                        the architect curates in (D68 —
│                                                        execution seats' reports go to the
│                                                        orchestrator's space, never here)
├─ 2026-08-24-strategy-core-post-migration-domain.md    a vision: dated, flat
└─ 2026-08-27-bench-optimization-operator-api-design.md a later checkpoint's anchor
```

A milestone's whole set is `ls docs/system-design/*bench*`; peeking at another milestone
is opening ITS index file. **Canon-versus-dated survives as a discipline, not as folders:**
the INDEX and glossary are reconciled *in place* — they are the freshness hubs, always
current, where statuses flip at every reconcile — while every other file is dated and
never rewritten: a superseded document gets a banner at the top redirecting to current
authority, and the prose below stays as the historical record. This means the reader's
protocol is one rule long: *enter through the index; trust banners over prose age.*

### LOCKED — decision numbers: one stream, many files

Each milestone's decisions file continues a single repo-wide D# stream — the bench milestone's log runs D350–D494 precisely because it continued a global count. Each INDEX declares its set's range ("this milestone owns D350–D494"), so a bare "D372" cited from anywhere in the repository resolves to exactly one folder, forever. If two milestones ever run in parallel, they receive pre-assigned disjoint number blocks at charter time (milestone A rules D500–D599, milestone B D600–D699) — the same collision-avoidance trick used when parallel rooms once shared an append-only ledger. One grandfather clause completes the picture (D69): documents already on the ground stay exactly where they are — the ownership and naming laws bind go-forward writes, and never demand retroactive moves that would break the link web. This is what makes cross-milestone citation safe without a global file.

### LOCKED — residue transport: rooms report, the orchestrator comprehends

The one flow that crosses all four spaces is the residue flow — design-class findings surfacing from item work. Its history explains its shape. The first design was a shared append-only file (`residue.jsonl`) that any room appended to, with disjoint ID blocks preventing numbering collisions. That design was born in the loop era, when agents shared one working directory and could not message each other — append-only-with-ID-blocks was how writers who couldn't talk avoided conflicts. Both premises died: rooms now message freely, and rooms now work in *isolated worktrees*, where a "shared" file is not actually shared — each branch sees its own copy until merge, and two rooms appending to the same file tail on different branches collide textually when the second rebases for its fast-forward publish. A per-room-files variant was considered and rejected in the same discussion. The operator's ruling: keep the working model —

1. Inside the room, most findings are **resolved internally** — the room grounds against the corpus, realizes the discrepancy is its own misreading or fixable within its charter, and the finding dies there. The room is the cheapest place to kill a false alarm.
2. What survives goes into the room's **report**, in the room's own words, beside its item files — the report is already the room's authored, durable record.
3. The **orchestrator comprehends the reports** and tracks surviving residue in his own ledger, in his own space, written in his own session on the milestone branch — so the worktree visibility problem never arises. His comprehension is a feature, not relay loss: he alone sees across rooms, so he is the one who notices rooms A and C hitting the same seam from opposite sides.
4. Every ledger entry is **typed** — residue rows tagged `discrepancy | insight | duplicate-risk | question`, process-feedback rows `friction | brief-gap | measurement | win` — so streams stay grep-separable, and an entry's fate is recorded by later artifacts *citing its ID* (a cluster, a ruling), never by editing the row.

### LOCKED — the handoff splits; no file has two writers

The old milestone handoff was one file with an orchestrator section and an architect section — two writers, one file, the exact thing the ownership law forbids. It splits naturally: the orchestrator writes his half (what was built, claims, retro facts) in `docs/orchestration/handoffs/` — note the near-homophone: `handoffs/` are per-MILESTONE close documents in the never-pruned keep-set, while `handovers/` (angle 2) are per-CHECKPOINT message companions pruned on the rolling window; the architect's half — "upfront design for the next milestone" — *is the creation of the next milestone's document set itself* (its INDEX, decisions file, census — the flat set under the new slug). The handoff is not a document the architect contributes a section to; it is the birth of the next working set.

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

All load-bearing claims LOCKED: four spaces with one writer each and a one-command audit; canon/dated split as discipline inside the flat corpus; milestone document sets on a global D# stream; report-based residue transport with typed rows; the handoff split. The single-writer law admits no exception anywhere in the repository — the previous exceptions (shared residue file, two-section handoff) were both dissolved rather than granted.
