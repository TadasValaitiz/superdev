# Architect ↔ Orchestrator Freshness — Decision Log

**Stream:** improving orchestrator↔architect collaboration; keeping milestone architecture
documentation up to date; briefs carrying milestone-architecture context.
**Evidence base:** ai-trading-calibration `bench-architecture` worktree — 46 new spec files,
24 angles, D350–D494, reconciliation commits, celebration-led execution proposal.
**Numbering:** continues superdev's system-design stream — this log owns D47+.

---

## D47 — Corpus root moves to `docs/system-design/`, milestone architecture in per-milestone folders   (phase: brainstorm, status: locked)

- **Trigger:** bench-architecture branch strain — a 199-file flat `docs/superpowers/specs/` dir carrying a de facto milestone corpus (24 angles, 5 anchors, census, D350–D494 log, execution proposal) with no structural separation from item specs.
- **Decision:** the design corpus root is `<repo>/docs/system-design/` (was top-level `design/`). Inside it, a **canon layer** (map.md, visions/ — always current, rewritten in place; bench's `canon/` proves the pattern) and a **dated layer** `milestones/<slug>/` (INDEX.md, angles/, anchors/, census.md, inputs/, execution-proposal.md — marker-bearing, reconciled via banners/status flips, never rewritten). `decisions.md` stays ONE global D# stream across milestones (D350–D494 continuity evidence). Item specs/plans remain `docs/superdev/specs|plans/`.
- **Alternatives:** B per-milestone folders under `docs/superdev/specs/` (keeps one tree but leaves architect authority inside the item stream); C stay flat + index harder (what bench did — works to ~200 files, then navigation-only freshness); top-level `design/` root (prior superdev convention — orphan root when all other docs live under `docs/`).
- **Why:** docs/ is where every documentation stream already lives in real projects; canon-vs-dated split is the load-bearing distinction for freshness (canon is rewritten, dated is banner-redirected); global decision log preserved cross-milestone numbering continuity.
- **Bridge rule:** existing projects map conventions via bootstrapping's adopt/bridge/discard table (e.g. bench: `canon/` ≙ visions; 298 per-decision files bridged to the global log).
- **Revisit-when:** a project needs per-milestone decision logs (parallel milestone streams colliding over D#s), or the milestone folder itself exceeds ~50 files.

## D48 — Decision log moves INTO the milestone folder; D#s stay globally unique   (phase: brainstorm, status: locked; amends D47)

- **Decision:** `milestones/<slug>/decisions.md` — each milestone folder carries its own decision log; the milestone is the self-contained working set (log, angles, anchors, census, inputs, execution proposal all together). Cross-milestone "peeking" = open the neighbour folder's log directly.
- **Numbering:** D#s continue ONE repo-wide stream across milestone files (bench evidence: the bench log runs D350–D494, continuing a global stream). Each milestone's INDEX.md declares its D# range, so any bare D# resolves to exactly one folder.
- **Alternatives:** global `docs/system-design/decisions.md` (D47's first cut — one file, but daily work then spans two roots); per-milestone restart at D1 (ambiguous cross-references).
- **Why (operator):** "easier to work — we can peek between milestones."
- **Revisit-when:** two milestones run in parallel and collide over the next D# (then: pre-assign disjoint blocks at charter, same as room ID blocks).

## D49 — Single-writer spaces under docs/; the shared residue inbox is retired   (phase: brainstorm, status: locked)

- **Trigger:** operator wants certainty that "nothing else writes into system-design"; the old corpus floor had three foreign-writer members (residue: any room; handoffs: orchestrator section; scenarios: item rooms).
- **Decision:** four spaces, one writer each, everything under docs/ except scratch:
  `docs/system-design/` (ARCHITECT sole writer — map, visions, milestones/<slug>/ incl. decisions+census+inputs curation, conformance, checkpoint responses) ·
  `docs/orchestration/` (ORCHESTRATOR sole writer — graph, cursor, residual ledger, residue ledger, residue-collections, process-feedback, conventions, its handoff half) ·
  `docs/superdev/specs|plans|scenarios/` (item rooms, each its own item's files; checkride scenario distills land here) ·
  `.superdev/sdd/` + worktrees (per-room scratch, git-ignored).
  Read access is global; writes never cross spaces — corrections route as messages to the owner.
- **Residue transport:** the append-only shared `residue.jsonl` (loop-engineering-era inbox) is RETIRED. Rooms record findings in their own item files, send RES messages with pointers; the orchestrator is the residue ledger's only writer. The two-section handoff file splits: orchestrator half in docs/orchestration/handoffs/, architect half = the seed of the next milestones/<slug>/ folder.
- **Alternatives:** keep shared residue.jsonl with ID blocks (needless once messaging exists); third neutral inbox space (more roots, same problem); orchestration/ at repo top level (orphan root — docs/ is where documentation lives).
- **Why:** single-writer-per-space makes ownership auditable at a glance (`git log docs/system-design/` shows only architect commits); messaging replaced the reason the inbox existed.
- **Revisit-when:** a project without cross-session messaging adopts the corpus (then the append-only inbox returns as the bridge mechanism).

## D50 — Shared append-only ledgers root `docs/ledgers/`; rooms write their own entries; typed rows   (phase: brainstorm, status: locked; supersedes D49's residue-transport clause)

- **Decision:** two file kinds, two laws. Mutable files: single writer per space, never bends. Append-only ledgers: many writers with disjoint ID blocks, quarantined in their own root `docs/ledgers/` (outside architect AND orchestrator): `residue.jsonl` (any room appends design-class findings directly — the room is the author, not the orchestrator relay) and `process-feedback.jsonl` (rooms append their own process observations; orchestrator appends its measured facts; same file, own blocks). RES/R5 messages shrink to notifications ("appended R-A12"), never carriers.
- **Typed rows (marker technique):** every ledger row carries a `kind` tag so streams are grep-distinguishable — residue kinds: discrepancy | insight | duplicate-risk | question; process-feedback kinds: friction | brief-gap | measurement | win. Lifecycle is never edited into a row (append-only): a residue row's disposition lives in the orchestrator's collection and the architect's ruling, both citing the row ID; census by grep over kind + cited-vs-uncited IDs.
- **Stays orchestrator-owned (mutable work product):** residual ledger (routed+drained = mutation), residue-collections (authored clustering), graph, cursor, conventions, handoff half.
- **Why:** relays lose fidelity and durability; append-only makes multi-writer safe; a dedicated root keeps the single-writer guarantee of docs/system-design/ and docs/orchestration/ absolute.
- **Revisit-when:** a third ledger kind appears (add to docs/ledgers/, same laws), or ledger volume needs per-milestone sharding.

## D51 — Residue transport stays as-is: rooms report, orchestrator comprehends and tracks   (phase: brainstorm, status: locked; SUPERSEDES D50's ledger-root and per-room-file clauses)

- **Trigger:** worktree mechanics examined — any repo file written by multiple rooms on separate branches is either invisible-until-merge or a rebase conflict; per-room ledger files were proposed; operator ruled: keep the working model.
- **Decision:** (1) item rooms resolve much residue INTERNALLY — only surviving design-class findings reach their reports; (2) the orchestrator COMPREHENDS room reports and tracks residue in his own ledger under docs/orchestration/ — sole writer, written on the milestone branch, so the worktree problem never arises; comprehension is a feature (cross-room dedup + clustering); (3) no docs/ledgers/ root, no shared or per-room ledger files. Same for process feedback: rooms' R5 lines → orchestrator's file.
- **Survives from D50:** typed rows — the orchestrator tags kind on every entry (residue: discrepancy | insight | duplicate-risk | question · process-feedback: friction | brief-gap | measurement | win); dispositions cite entry IDs, census by grep.
- **Why:** "what is working is working fine" — the report is already the room's authored record (fidelity preserved in item files); the ledger is the orchestrator's tracking instrument, and moving it multiplied roots and mechanics for marginal gain.
- **Revisit-when:** evidence that orchestrator comprehension is losing or distorting findings between report and ledger (compare item reports vs ledger rows at a milestone close).

## D52 — Reconciliation is the mandatory closing half of every architect sitting   (phase: brainstorm, status: locked)

- **Decision:** every architect sitting — checkpoint-triggered or operator-brainstorm — ends with the reconciliation pass: rulings landed in decisions.md → statuses flipped in INDEX + touched angles/anchors → banners onto superseded docs (redirect to current authority; prose below stays as record) → census refreshed → ONE named commit: `docs: reconcile <milestone> architecture authority`. No sitting ends with the corpus contradicting what it just ruled. Between sittings staleness is permitted and honestly marked — the markers are the promise.
- **Sub-rule (brief freshness):** orchestrator briefs cite architecture docs as-of the last reconcile commit, naming its SHA; anything ruled since reaches rooms as D# pointers, never doc text. A room always knows exactly how fresh its context is.
- **Alternatives:** per-merged-item reconcile (kills the idle-between-checkpoints law); separate operator-triggered chore (ruling and bookkeeping decouple; bookkeeping loses — bench evidence shows reconcile-as-checkpoint-close working: commit 14f408f6 swept 14+ docs in one pass).
- **Revisit-when:** reconcile passes exceed ~an hour of sitting time (then: split census regen into a pre-sitting mechanical step).

## D53 — Marker grammar: ratify the emergent plain-vocabulary positional markers; DOC-MARK bracket retired for docs   (phase: brainstorm, status: locked)

- **Trigger:** bench census — same author wrote `**LOCKED:**` claim-prefixes 112× vs `DOC-MARK[LOCKED]` 22×; the bracket grammar loses to its own author's habits, and an under-writing grammar under-counts.
- **Decision:** two positional marker forms, plain vocabulary (LOCKED · FLEXIBLE · DEFERRED · BLIND · MISMATCH · SEED-ILLUSTRATIVE · SUPERSEDED):
  (1) **claim marker** — line-initial `**LOCKED:** …`; (2) **section status** — `**Status:** LOCKED …`.
  **Flexible payload:** what follows the marker may be plain text, a D# reference, a file link, or any mix — `**LOCKED (D461):**`, `**SUPERSEDED:** see [anchor](…)`, `**MISMATCH:** repo does X today` are all valid. The marker word + position is the grammar; the payload is free.
- **Census is tooling, not fingers:** the system-design skill ships the census script (regex over line-initial bold status words); "graph the markers" = one command → counts per status per doc + delta since last reconcile. Distinguishability lives in the script's regex, not in author ceremony.
- **Code unchanged:** `MIG-MARK[...]` in source keeps the bracket — source greps need a token that cannot collide with identifiers.
- **Alternatives:** enforce DOC-MARK everywhere (loses to habit, measured); allow both (double greps forever).
- **Revisit-when:** census shows a status word regularly appearing line-initial-bold in NON-marker meaning (then tighten the regex or reintroduce a sigil).

## D54 — Execution proposal: architect-authored via two opposed seat subagents   (phase: brainstorm, status: locked)

- **Decision:** `milestones/<slug>/execution-proposal.md` is architect-authored, but its METHOD is seat-based: dispatch two subagents arguing from opposed angles — (1) DOMAIN-BOUNDARIES seat (cut along domain seams: type ownership, package boundaries, contract breaks) and (2) CELEBRATION seat (cut along operator-visible CLI journeys with proof/refusal evidence). Their reports are inputs-not-rulings, curated into inputs/; the collision zone between them is where the middle ground is found, adjudicated by the five celebration rules (esp. rule 3: foundations fold inside the first proving vertical unless they unlock named independent streams). Architect reconciles with the operator at a sitting.
- **Five rules encoded as the proposal's law (bench harvest):** operator-visible capability, CLI proof boundary, foundations-inside-first-vertical, terminal-not-tiny items, reconciliation-expected (the doc is reconcilable-never-locked and authorizes no code).
- **Downstream:** orchestrator DERIVES his charter graph from the proposal via D44/D45 (mechanical cut, splits, greedy schedule); operator ratifies at co-plan; item-level divergences travel as residue → amended into the proposal at the next sitting; the operational graph may run ahead of the proposal between sittings.
- **Alternatives:** orchestrator authors (design judgment in orchestration space); co-authored file (recreates the two-writer file D49 killed); single-perspective authoring (no collision → the middle ground is never surfaced — bench's 4-seat intake proves opposed seats work).
- **Revisit-when:** a milestone's architecture has no CLI surface (then the celebration seat argues from whatever the operator-visible proof boundary is — API, artifact, report).

## D55 — Execution proposal is ORCHESTRATOR-authored; architect contributes only via corpus + advisory conformance   (phase: brainstorm, status: locked; SUPERSEDES D54's ownership — the seat METHOD survives)

- **Trigger:** operator correction — execution is the orchestrator's altitude ("architect should not be involved in this operational element", chartering brainstorm); briefs are orchestrator-authored, so the doc they derive from must be too.
- **Decision:** `docs/orchestration/execution/<milestone>-proposal.md`, orchestrator sole writer. Method unchanged from D54: two opposed seat subagents (domain-boundaries vs celebration/CLI-deliverable), both grounded on the corpus as-of the last reconcile SHA; collision reconciled under the five celebration rules; ratified with the operator at co-plan; charter graph derived via D44/D45. Seat reports live in his space or sdd scratch.
- **Architect's two touchpoints (existing channels only):** upstream — the corpus the seats read; a missing vision/unruled row surfaces as design-dry and withholds that charter. Downstream — advisory conformance read in conformance/ (non-blocking). Advice, never authorship.
- **Rule-5 reconciliation:** orchestrator amends his own proposal as items split/merge on contact with code; only design-class divergences travel to the architect as residue.
- **Why:** design KNOWLEDGE is delivered by the corpus (readable by all); grouping deliverables is execution JUDGMENT — the orchestrator's charter; keeps single-writer law and architect-idle law intact.
- **Revisit-when:** proposals repeatedly bounce off design-dry gaps (sign the corpus isn't carrying enough seam information — then the architect's anchors gain a required "seams" section, not proposal authorship).

## D56 — Brainstorming becomes angle-first with a Fork Presentation Standard; angle-guide absorbs the bench refinements   (phase: brainstorm, status: locked)

- **Trigger:** operator, live: fork options presented as bare A/B labels gave "no idea what I am picking on"; the skill mandated one-question-at-a-time but said nothing about option substance. Separately: the bench 08-25 angle-definition doc out-wrote our angle-guide.
- **Decision:** (1) brainstorming step 4: angles are identified AND PRESENTED to the operator as an amendable session agenda before clarifying questions; emergent angles added to the agenda explicitly. (2) Step 5: angle-by-angle work — each angle OPENS with its situation in prose, closes by stating what was reconciled. (3) New Fork Presentation Standard: every presented fork carries situation (failure modes) · mechanism with concrete example · consequences for THIS project · recommendation with reasoning; labels never substitute; trivial three-line forks are self-decided and logged, not presented. (4) angle-guide.md gains: create-vs-keep-as-subsection test + reserve-angles rule; the 7-step movement protocol (frame → explore → collide → log → follow consequences → close → write at checkpoint) with revisit discipline; the presentation convention (plain first, Pydantic sketches, no stale recommendations after a fork resolves).
- **Why:** the bench room independently discovered the same standard ("present enough architecture and code context for the operator to reason without having written the implementation") — practice validated it before we wrote it.
- **Verification:** D46 — fresh-eyes review dispatched over both files, not TDD.
- **Revisit-when:** operator reports sessions dragging from over-presented trivial forks (then tighten the triviality threshold).

## Session agenda (ratified 2026-08-28, per the new angle-first flow)

Closed: ① spaces/corpus (D47–D51) · ② reconciliation (D52) · ③ markers (D53) · ④ execution proposal (D54/D55) · meta: brainstorming skill fix (D56).
Open, in order: ⑤ briefs as architecture carriers · ⑥ the checkpoint conversation (orchestrator↔architect) · ⑦ item room skills · ⑧ milestone close & handoff (incl. sediment-removal duty) · ⑨ migration & bootstrap (calibration rollout) · ⑩ census tooling folded into the implementation plan unless raised.
Amendments to this agenda are logged here as they occur.

## D57 — Brief anatomy: five parts including 3–5 verbatim load-bearing rulings   (phase: brainstorm, status: locked)

- **Decision:** every item-room brief's architecture section carries: (1) as-of line naming the last reconcile commit SHA; (2) MAJOR reads — governing anchors/angles at file/section precision, the item's execution-proposal entry, and the VISION (never legacy code) wherever the map says RESHAPE/REPLACE; (3) NARROW reads listed for on-need; (4) **3–5 load-bearing rulings quoted VERBATIM** from the anchors' LOCKED lines, each citing its D# — the one sanctioned duplication in the system; (5) rulings newer than the reconcile SHA as D# pointers only, never retold.
- **Alternatives:** pointers-only (B) — doctrinally pure, but re-runs the measured failure: the calibration O-log (ten live workers) recorded that verbatim quoting prevented drift where extraction-by-the-worker did not.
- **Why:** paraphrase is the drift entry-point; quotes are frozen at brief time, scoped, short-lived (item rooms live days), and stale-detectable (each cites its D#, supersession flips the status).
- **Revisit-when:** a room ships against a quoted ruling superseded mid-item (then: reconcile events push a CORRECTION message to live rooms whose briefs cite the flipped D#).

## Standard amendment (from live failure, this session)

Fork Presentation Standard gains: **a re-ask is a full re-presentation** — a fork awaiting a ruling is presented complete at every asking; "as presented earlier" is never a substitute. Applied to the skill.
