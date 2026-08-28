# Angle 1 — Spaces and ownership

**Purpose:** understand who may write where in a governed repository, why each boundary sits where it does, and how ownership is audited — without reading the spec or the decision log.
**Formal anchors:** D47–D49, D51 (D50 superseded), D60 · spec §5.1/§5.2 (R1–R4).
**Series:** 1 of 4.

> **Status guide:** LOCKED operator-ruled · FLEXIBLE boundary agreed, shape may move ·
> DEFERRED another session owns it · MISMATCH current skill text behaves differently today.

## The central question

How can the operator KNOW — mechanically, from the repository itself, without trusting anyone's discipline — that nothing except the architect ever writes the system design?

## Boundaries

This angle starts at the repository's `docs/` root and stops at file ownership and transport: who writes, who reads, how content moves between owners. What the files *say* and how they stay fresh is angle 2's territory; how rooms consume them is angle 3's. The journey below follows one repository through a working day.

## Concrete journey

### LOCKED — four spaces, one writer each, everything under docs/

A governed repository has exactly four writing territories:

```
docs/system-design/     ARCHITECT only      the architecture corpus
docs/orchestration/     ORCHESTRATOR only   operational records and ledgers
docs/superdev/          ITEM ROOMS          specs, plans, scenarios — each room its own item's files
.superdev/sdd/ + worktrees                  per-room scratch, git-ignored, outside docs/
```

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

**The dated layer** — `milestones/<slug>/`, one folder per milestone, holding everything that milestone's design produced: `INDEX.md` (the angle index, the status vocabulary, and the milestone's declared D# range), `decisions.md` (the milestone's decision log), `angles/`, `anchors/`, `census.md` (the charter-time grounding sweep, provenance-tagged MEASURED/READ/FLAGGED), and `inputs/` (curated copies of intake — seat reports, charters; copying them in is authorship of the record). Dated files are *never rewritten*: a superseded document gets a banner at the top redirecting to current authority, and the prose below stays as the historical record.

The milestone folder is the working set: a sitting touches one folder — the angles being flipped, the log being appended, the index that navigates them, all siblings. History is a *peek*: open the neighbouring milestone's folder directly.

### LOCKED — decision numbers: one stream, many files

Each milestone's `decisions.md` continues a single repo-wide D# stream — the bench milestone's log runs D350–D494 precisely because it continued a global count. Each INDEX declares its folder's range ("this milestone owns D350–D494"), so a bare "D372" cited from anywhere in the repository resolves to exactly one folder, forever. If two milestones ever run in parallel, they receive pre-assigned disjoint blocks at charter time — the same trick as room ID blocks. This is what makes cross-milestone citation safe without a global file.

### LOCKED — residue transport: rooms report, the orchestrator comprehends

The one flow that crosses all four spaces is the residue flow — design-class findings surfacing from item work. Its history explains its shape. The first design was a shared append-only file (`residue.jsonl`) that any room appended to, with disjoint ID blocks preventing numbering collisions. That design was born in the loop era, when agents shared one working directory and could not message each other — append-only-with-ID-blocks was how writers who couldn't talk avoided conflicts. Both premises died: rooms now message freely, and rooms now work in *isolated worktrees*, where a "shared" file is not actually shared — each branch sees its own copy until merge, and two rooms appending to the same file tail on different branches collide textually when the second rebases for its fast-forward publish. A per-room-files variant was considered and rejected in the same discussion. The operator's ruling: keep the working model —

1. Inside the room, most findings are **resolved internally** — the room grounds against the corpus, realizes the discrepancy is its own misreading or fixable within its charter, and the finding dies there. The room is the cheapest place to kill a false alarm.
2. What survives goes into the room's **report**, in the room's own words, beside its item files — the report is already the room's authored, durable record.
3. The **orchestrator comprehends the reports** and tracks surviving residue in his own ledger, in his own space, written in his own session on the milestone branch — so the worktree visibility problem never arises. His comprehension is a feature, not relay loss: he alone sees across rooms, so he is the one who notices rooms A and C hitting the same seam from opposite sides.
4. Every ledger entry is **typed** — residue rows tagged `discrepancy | insight | duplicate-risk | question`, process-feedback rows `friction | brief-gap | measurement | win` — so streams stay grep-separable, and an entry's fate is recorded by later artifacts *citing its ID* (a cluster, a ruling), never by editing the row.

### LOCKED — the handoff splits; no file has two writers

The old milestone handoff was one file with an orchestrator section and an architect section — two writers, one file, the exact thing the ownership law forbids. It splits naturally: the orchestrator writes his half (what was built, claims, retro facts) in `docs/orchestration/handoffs/`; the architect's half — "upfront design for the next milestone" — *is the creation of the next `milestones/<slug>/` folder itself*. The handoff is not a document the architect contributes a section to; it is the birth of the next working set.

## Visible collisions

- **Single-writer purity vs multi-writer ledgers.** Three transports were designed, argued, and two discarded in one sitting: the shared inbox (invalidated by worktrees and by messaging's existence), per-room ledger files (rejected — the operator kept the working report-based model rather than multiply roots and mechanics), and report→orchestrator comprehension (won). The instructive part: the *first* redesign looked doctrinally cleaner and was still wrong, because it optimized the law rather than the work.
- **Milestone-scoped logs vs global citation.** Self-contained folders pull toward per-milestone numbering; cross-references pull toward one global file. The reconciliation — local files, global stream, declared ranges — takes both sides' actual need and discards both sides' preferred mechanism.
- **The two-writer handoff vs the law.** Resolved not by choosing a writer but by discovering the file was two artifacts wearing one filename.

## Flexible and deferred

FLEXIBLE: exact filenames and sub-layout inside `docs/orchestration/` (the owner arranges his own space); the ledger file format (jsonl vs md tables). Nothing DEFERRED in this angle.

## Reconciled outcome

All load-bearing claims LOCKED: four spaces with one writer each and a one-command audit; canon/dated split inside the architect's space; milestone folders on a global D# stream; report-based residue transport with typed rows; the handoff split. The single-writer law admits no exception anywhere in the repository — the previous exceptions (shared residue file, two-section handoff) were both dissolved rather than granted.
