# Architect ↔ Orchestrator Freshness — Decision Log

**Stream:** improving orchestrator↔architect collaboration; keeping milestone architecture
documentation up to date; briefs carrying milestone-architecture context.
**Evidence base:** ai-trading-calibration `bench-architecture` worktree — 46 new spec files,
24 angles, D350–D494, reconciliation commits, celebration-led execution proposal.
**Numbering:** continues superdev's system-design stream — this log owns D47+.

---

## D47 — Corpus root moves to `docs/system-design/`, milestone architecture in per-milestone folders   (phase: brainstorm, status: locked)

- **Trigger:** bench-architecture branch strain — a 199-file flat `docs/superpowers/specs/` dir carrying a de facto milestone corpus (24 angles, 5 anchors, census, D350–D494 log, execution proposal) with no structural separation from item specs.
- **Decision:** the design corpus root is `<repo>/docs/system-design/` (was top-level `design/`). Inside it, a **canon layer** (map.md, visions/ — always current, rewritten in place; bench's `canon/` proves the pattern) and a **dated layer** `milestones/<slug>/` (INDEX.md, angles/, anchors/, census.md, inputs/, execution-proposal.md [AMENDED by D55: proposal moved to docs/orchestration/execution/] — marker-bearing, reconciled via banners/status flips, never rewritten). `decisions.md` stays ONE global D# stream across milestones (D350–D494 continuity evidence). Item specs/plans remain `docs/superdev/specs|plans/`.
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

## D58 — Checkpoint handover: narrative trio + three factual attachments   (phase: brainstorm, status: locked)

- **Decision:** the handover keeps WHAT WE GOT / WHERE WE FEEL GAPS / UPCOMING FOCUS (each agree/disagree) as the spine — the cross-room narrative judgment only the orchestrator can write — and gains three attachments: (1) map-row claims with evidence at file:line (two-step discharge: claim here, architect writes map); (2) marker-census delta since the last reconcile (machine-generated, D53 script); (3) measured process facts (charter→merge wall-clock, review cycles, blocked-time — already collected for process feedback). The residue collection is referenced, never inlined. The checkpoint message is a pointer to the handover.
- **Alternatives:** minimal pointer-only handover — cheapest, but loses the narrative sections that made the bench continuation brief work; the ledgers don't carry what it felt like across rooms.
- **Revisit-when:** handover assembly regularly exceeds ~an hour (then: more of it becomes generated).

## D59 — One mode law: HUMAN vs AUTONOMOUS, declared at co-plan, honored by every ruling gate   (phase: brainstorm, status: locked; supersedes the B1/B2 pre-pass fork — absorbed)

- **Decision:** the orchestrator declares the milestone's mode at co-plan (recorded in graph + conventions). HUMAN mode: architect waits for the operator; rulings only in sittings; self-brainstormed items queue at their ratification gate as desk DECIDE. AUTONOMOUS mode: the architect does real architecture at checkpoints — options with gains/sacrifices + recommendation per the Fork Presentation Standard — and the ORCHESTRATOR picks; self-brainstorming ratification gates are likewise orchestrator-ratified. Unified with the plan Mode: field (already autonomous-capable).
- **Invariants in both modes:** every autonomous pick is a logged, FLAGGED, revisitable D# (options preserved, named as an autonomous-mode pick); the next human touchpoint opens with the pick list; overturns supersede, never erase. RESERVED forks — money/irreversibility, blast-radius reshapes, taste — always queue to the operator; work routes around them. Milestone close is operator-approved in both modes (safety stays topology). The mechanical pre-pass (census, stale-D# grep, agenda-as-questions) is allowed in both modes — mode governs RULING, not reading.
- **Why:** the milestone should never stall on an absent human it was told not to wait for; and the architect's "human-driven" law becomes a mode, not an absolute — with the reserved classes keeping the human's irreducible forks human.
- **Alternatives:** keep the absolute human-driven law (rejected: stalls milestones the operator declared autonomous); per-gate ad-hoc modes (rejected: three dialects of one question); B1/B2 pre-pass-only framing (absorbed — too narrow a cut).
- **Revisit-when:** an autonomous-mode overturn rate above ~1 in 4 picks at human review (then the reserved-fork classes are too narrow).

## D60 — The two-surface law; checkpoint = one operational handover + one reconciled response block   (phase: brainstorm, status: locked; supersedes the artifact clauses of D51/D58, resolves angle-⑥ fork c)

- **The law:** docs/system-design/ is the RECONCILED surface — anything grabbed from it matches reality or wears a marker/banner saying how much to trust it; reconciliation passes apply ONLY here. docs/orchestration/ is the OPERATIONAL surface — files exist as message companions (short message + pointer to detail file); every file opens with a standing stamp: "OPERATIONAL RECORD — point-in-time, never reconciled, may be outdated; design authority lives in docs/system-design/". Operational files are never reconciled — they are PRUNED: at milestone close, working state condenses into the handoff and sediment is deleted (git is the archive). Nothing crosses surfaces.
- **Checkpoint artifacts (2 total):** (1) orchestrator's handover doc `docs/orchestration/handovers/<milestone>-checkpoint-N.md` — narrative trio + map claims + residue clusters INLINE (residue-collections/ dies) + inlined census/process facts (recurring marker census is ephemeral script output, no committed file); write-once, stamped, prunable. (2) architect's response = a checkpoint block INSIDE milestones/<slug>/decisions.md (sections verdicts · claim verdicts · cluster dispositions incl. BOUNCED DOWN) followed by its D# entries — the response is part of the ruling record, on the reconciled surface. Per-item conformance/ files fold to a conformance-notes line in the block unless one genuinely needs length. The reconcile commit (D52) closes; messages both ways are pointers.
- **Alternatives (angle-⑥ forks a/b/c, recorded):** fork a — minimal pointer-only handover (rejected: loses the cross-room narrative only the orchestrator can write; D58). Fork b — architect solo pre-pass bounds (absorbed into D59's mode law: pre-pass allowed both modes, mode governs ruling). Fork c — separate response DOC in a responses/ dir (rejected: every doc type is a reconciliation surface; the response belongs inside the file reconciliation already owns) vs message-only response (rejected: claim verdicts and bounce-downs must not live in messages).
- **Bounce-down landing:** the orchestrator (backlog curator) converts bounced clusters into backlog items or routes them into an upcoming charter; his next handover's WHAT WE GOT confirms the filing — loop closed.
- **Why (operator):** "creating too many docs makes reconciliation very hard… orchestration is operational — those files are for messaging convenience, clearly not part of reconciliation, and should be pruned; orchestration never faces reconciliation passes at all."
- **Revisit-when:** an operational file is found being cited as design authority (then it gets deleted and its content ruled into the corpus, and the stamp language gets teeth).

## D61 — Mid-item contradictions: show must go on; plan-time deviation notification relayed by pointer   (phase: brainstorm, status: locked)

- **Decision (A2 + timing refinement):** an item room that finds the corpus contradicted by reality does NOT stall and does NOT wait for permission: it collects the discrepancies in its OWN item files (item decision log / spec deviations section) during grounding→brainstorm→planning; plants `MIG-MARK[MISMATCH][D#]` at the exact sites; implements against reality with a flagged deviation entry.
- **The notification seam:** AFTER planning, BEFORE execution starts — if design-class deviations were collected, the room finalizes the deviations section in its file, messages the ORCHESTRATOR a short summary + pointer; the orchestrator FORWARDS the pointer to the architect immediately (not batched to checkpoint). The orchestrator is a RELAY of pointers — never bloated messages; content lives in the room's file. The architect may act at once (re-rule in parallel while the room executes, per mode D59) or fold it to the next checkpoint; receiving pointers does not violate architect idleness — acting is the mode's call.
- **Checkpoint remains the net:** anything not handled immediately reconciles there; merged code carrying MISMATCH markers is honest by D60's marker promise.
- **Alternatives:** A1 route-by-severity with LOCKED inviolable below the architect (rejected: stalls a gutted item on an absent human; "show must go on").
- **Why (operator):** the architect learns at PLAN time and can start working immediately while the room executes — parallelism instead of a gate; pointer-relay keeps messages thin.
- **Revisit-when:** a room's local deviation from a LOCKED claim is overturned post-merge more than rarely (then the plan-time notification gains a short architect-ack window for LOCKED-class deviations in HUMAN mode).

## D62 — Close-pruning: rolling one-milestone window   (phase: brainstorm, status: locked)

- **Decision (P2):** at milestone N's close gate the orchestrator still harvests (process-feedback → handoff retro; improvement lessons → durable notes) and condenses (graph/cursor/residual outcomes → the handoff), but DELETES only milestone N−1's operational files. The just-closed milestone's handovers/ledgers/spent items survive one more milestone as a live reference window, then go at the next close. Deletion set at each close: N−1's handover docs, raw ledgers, spent backlog items (done/dropped/icebox), proposal working drafts. Always-kept in docs/orchestration/: handoffs, conventions.md, improvement-notes stream.
- **Alternatives:** P1 condense-then-delete at own close (recommended for minimal surface; rejected — operator prefers the safety window for early-next-milestone lookbacks).
- **Close-gate line added:** "N−1 operational sediment pruned" joins the checklist the operator approves.
- **Revisit-when:** the two-milestone surface measurably pollutes grounding (rooms citing stale operational files as authority — D60's revisit trigger).

## D63 — Calibration migration: selective — move the living architecture, bridge the history   (phase: brainstorm, status: locked)

- **Decision (M1):** one migration commit in ai-trading-calibration (git mv, history preserved): bench corpus (~40 files: angles, anchors, milestone decisions log D350–D494, census, glossary, inputs, INDEX from the existing angle index) → `docs/system-design/milestones/bench/`; `docs/canon/` → `docs/system-design/visions/` + `map.md` seeded from angle-08 (current→target). Then one mechanical link-fix pass (audit-file pattern) and CLAUDE.md operating-model paths updated.
- **Bridged, never moved:** `docs/decisions/` (208 per-file historical decisions) stays — conventions.md records the bridge ("pre-bench decisions per-file; milestone logs going forward"); `docs/superpowers/specs|plans` remains the ITEM lane per the standing CLAUDE.md ruling — item specs were never required to move.
- **Alternatives:** M2 grow-in-place (zero risk, but the ACTIVE corpus stays outside the reconciliation law and briefs point into the mixed pile — the freshness guarantee starts life broken).
- **Revisit-when:** the link-fix pass uncovers heavy inbound references from kept item specs into moved corpus files (then: leave a pointer stub at the old path for the hot ones).

## Agenda close (2026-08-28)

All angles reconciled: ⑤ D57 · ⑥ D58–D60 · ⑦ D61 · ⑧ D62 · ⑨ D63. ⑩ census tooling folded into the implementation plan. BLIND carried: mid-item CORRECTION push on superseded quoted D#s (D57/D61 revisit hooks).

## D64 — Two streams, never mixed: skill refinement vs project migration   (phase: brainstorm, status: locked)

- **Decision:** the superdev skill edits are their own stream (this spec + its plan, in the superdev repo, D46 review-verified). The calibration migration (D63) is NOT part of that plan — it belongs to the calibration project's own operational flow (its next milestone's bootstrap act, guided by the updated bootstrapping skill), like any milestone close/reconciliation/cleanup work.
- **Why (operator):** "skill refinement is a separate process — don't mix it with closing up a milestone or document reconciliation and cleanup."
- **Alternatives:** S1 skills-then-migrate (rejected as a bundle: ties the release to another project's milestone rhythm); S2 migrate-first (rejected: migration would run under old, un-governing skills); S3 interleave (rejected: two half-released plugin states). All three presumed one stream — the operator cut the premise instead.
- **Consequence:** the shape fork (S1/S2/S3) dissolves — skills ship on their own clock; migration runs whenever calibration's flow reaches it, under the shipped skills.
- **Revisit-when:** a skill edit turns out to REQUIRE a live migrated instance to be writable (then that edit alone waits for the migration, without merging the streams).

## D65 — The angle lifecycle gets teeth: close-time authoring, reviewed with the spec, reconciled, handed to the operator   (phase: brainstorm, status: locked)

- **Trigger:** operator, live (the skill's first run): angles were neither proposed nor written unprompted; the spec reviewer never saw them; no pass reconciled design doc ↔ angles ("you are not using, suggesting, or writing angles… no reconciliation pass between the design document and the angles").
- **Decision:** (a) a collision-bearing angle's companion is written when the angle CLOSES (movement step, not a step-8 batch); (b) the spec-reviewer dispatch lists angle companions as required inputs and gains a cross-check row — companions contradict neither spec nor log, and every companion collision appears in the spec's areas or §8; (c) the user review gate hands the operator the angle files by file:// link beside the spec. Spec gains R15 covering this; the plan implements it in brainstorming SKILL.md + spec-document-reviewer-prompt.md.
- **Why:** an unreviewed, unreconciled companion is a second source of truth — the exact disease the two-surface law kills in the corpus.
- **Revisit-when:** companion-writing at close measurably breaks session flow (then: draft-at-close, polish-at-step-8).

## D66 — The register law: conversation economy never applies to deliverables   (phase: brainstorm, status: locked)

- **Trigger:** operator, live: "You are not writing enough stuff… not verbose, not expressive, you don't think in other directions" — measured 7× depth gap between the bench angles (~2,750 words avg, teaching form) and this stream's companions (~380 words, cite-only), traced to chat-economy habits bleeding into document authoring, NOT to any skill prohibition.
- **Decision:** two registers, never mixed. OPERATIONAL register (messages, chat updates, commit lines): short, pointer-based — the existing law. DELIVERABLE register (specs, angles, visions, anchors, handovers' narrative sections): teaching documents — a reader understands the subject WITHOUT the log; each ruling earns prose re-derivation with a worked example; the writing pass is a second thinking pass expected to surface new directions, not transcription. "Messages are pointers to files" REQUIRES the files to carry full substance — a file that is itself a pointer breaks the doctrine it claims to follow.
- **Teeth:** the depth bar in item-angle-template.md + brainstorming step 5 (W3-1, already planned); reviewer prompts probe "can a stranger understand this without the log?".
- **Revisit-when:** deliverables bloat with padding that teaches nothing (the failure in the other direction — length must be earned by content, never by register compliance).

## D67 — Operator discards the wave-3 documentation set; brainstorming experience becomes the center   (phase: brainstorm, status: locked)

- **Trigger:** operator, live: "Overall, I'm very disappointed with the brainstorming skill… really check the angles that Codex's harness was producing and re-evaluate how to make brainstorming produce a similar experience… I discard everything, and you need to present me a new set of documentation."
- **Decision:** the wave-3 spec, plan, and companion set are DISCARDED as deliverables (banner-marked, never erased; the D47–D66 RULINGS themselves stand — they are operator decisions, not documentation). A new documentation set replaces them, grounded in a full-depth study of the bench corpus: (1) a bench-experience study with quoted evidence; (2) a new design for the brainstorming experience itself; (3) a new plan with brainstorming's rewrite at the center and the D47–D63 transcription re-planned around it.
- **Why:** the discarded set documented the rulings thinly (cite-only angles, compressed spec areas) — the register failure D66 names, applied to the whole set; and the brainstorming skill's own output experience was never designed, only patched.

## D68 — Three boundary clarifications from the angle calibration review   (phase: brainstorm, status: locked; self-decided trivial forks, logged for overturn)

- **Seat reports have two homes because there are two kinds of seats.** DESIGN-intake seats (the bench pattern: perspective reports commissioned as inputs to an architecture sitting) → the ARCHITECT curates copies into `milestones/<slug>/inputs/` — curation is authorship of the record. EXECUTION-proposal seats (D55's domain-boundaries and celebration seats) → the ORCHESTRATOR's space or sdd scratch, never the corpus. The angle-01 line placing "seat reports" generically in inputs/ was a D54-era fossil; corrected.
- **Conformance's home:** the advisory conformance read is normally a line in the checkpoint response block (inside milestones/<slug>/decisions.md); one that genuinely needs length becomes `milestones/<slug>/conformance-<item>.md` — architect space, dated layer. There is no separate conformance/ root. (Carried from the discarded spec's §5.1; now ruled on the record.)
- **handoffs/ vs handovers/ (near-homophones, different things):** `docs/orchestration/handovers/` = per-CHECKPOINT operational message companions, pruned on the rolling window. `docs/orchestration/handoffs/` = per-MILESTONE close documents (the orchestrator's half), in the never-pruned keep-set. Every document naming one must gloss the contrast on first use.
- **Rests on:** D49, D51, D55, D60, D62. **Affects:** angles 01/02/04 text; orchestrator skill text at implementation.
- **Revisit-when:** a third seat kind appears (then the two-homes rule generalizes to "the commissioning role owns the report").

## D69 — The corpus is FLAT; filenames carry what folders would have   (phase: brainstorm, status: locked; AMENDS D47/D48's milestones/<slug>/ nesting and D63's migration shape)

- **Trigger:** development started; the master system-design documents now exist ON THE GROUND at `docs/system-design/` (calibration main, commit a42b408e) — 40+ files, flat, date-prefixed, milestone slug in every filename, dense relative `./` cross-links. Operator: "they are already written in this structure and this form, and we don't want to reconcile them… flatter… improve it to match what is on the ground."
- **Decision:** `docs/system-design/` is FLAT. The naming convention carries milestone identity and type:
  `YYYY-MM-DD-<milestone>-angle-NN-<slug>.md` (angles; the current→target map IS an angle) ·
  `YYYY-MM-DD-<milestone>-<topic>-design.md` (anchors) ·
  `YYYY-MM-DD-<milestone>-architecture-{angles,decisions,census,glossary,handover}.md` (the milestone set: INDEX, log, census, glossary, continuation brief) ·
  `YYYY-MM-DD-<milestone>-inputs/` (the ONE subfolder kind: curated design-intake) ·
  `YYYY-MM-DD-<area>-post-migration-domain.md` (visions, dated and flat).
  Cross-links are relative `./` — flatness is what keeps them stable; nothing is ever moved.
- **Canon-vs-dated survives as DISCIPLINE, not folders:** the milestone INDEX file (`…-architecture-angles.md`) and glossary are reconciled IN PLACE (the freshness hubs — status language, per-angle statuses, D# range); everything else is dated, banner-superseded, never rewritten. "Peek between milestones" = the INDEX files; `ls docs/system-design/*<slug>*` lists a milestone's set.
- **D# stream unchanged:** global, each milestone's decisions file declares its range (bench: D350–D494).
- **Grandfather clause:** documents already on the ground stay exactly where and how they are — including `2026-08-27-bench-execution-celebrations-proposal.md`, written pre-D55 inside system-design; it stands as history. FUTURE execution proposals follow D55 (`docs/orchestration/execution/`); the single-writer law binds go-forward writes, never demands retroactive moves.
- **Alternatives:** nested `milestones/<slug>/{angles/,anchors/,…}` (D47's shape — cleaner ls, but migration would break every relative link in a live corpus for zero content gain); flat-with-symlinks (fragile, tooling-hostile).
- **Rests on:** D47/D48 (amended), D52, D55, D63 (amended: no restructuring migration remains — the corpus is already home). **Affects:** angle-01 text; system-design skill floor at implementation; census script globs; bootstrapping floor step.
- **Revisit-when:** a second concurrent milestone makes the flat directory genuinely ambiguous to navigate (then: revisit foldering for NEW milestones only; never move the old).

## D69 — Affects extension (set review, 2026-08-28)
The original Affects line named only angle-01 text; the set review measured the true blast radius: angles 01–04 all carried nested-path residue (brief-block reads, inputs/, conformance paths, milestone-folder phrasing) — all corrected at commit b6c7cc7. Lesson for future amendments: an Affects list is a claim to verify by grep, not to estimate.

## D70 — Marker grammar gains the HEADING form; census must count all three   (phase: build, status: locked; amends D53)

- **Trigger:** Codex independent review (review-experience-c41, gpt-5.6-sol, read-only): the angle template's `### LOCKED — <claim>` journey headings are a third status form D53 never named — census tooling built to D53's two forms would undercount load-bearing rulings. Ground truth: the bench corpus itself uses heading markers (angle-19's five `### LOCKED — …` subsections).
- **Decision:** three recognized positional forms: (1) claim marker `**LOCKED:** …` line-initial; (2) section status `**Status:** LOCKED …`; (3) **heading marker** `### LOCKED — …` (any heading level; status word leads, em-dash separates). The census regex matches all three; everything else in D53 (plain vocabulary, flexible payload, MIG-MARK bracket in code) unchanged.
- **Rests on:** D53; MEASURED — bench angle-19 headings. **Affects:** census script (Task 5a), map-and-markers.md, item-angle-template (already conformant).
- **Revisit-when:** a fourth form emerges in practice (then: the census script's self-test corpus is the gate for admitting it).

## D71 — Plans answer to the whole document set; angles govern where the spec is silent   (phase: plan, status: locked)
**Decided by:** operator (live, in-session; caught that writing-plans consumes a single anchor and ruled the full-set contract, with an angle companion to carry it)

- **Trigger:** the writing-plans skill's own text plans against "the spec"/"the anchor" alone — context pack, self-review, and plan reviewer all omit angle companions and census. Drift from this session's changes: angles became first-class carriers of collisions/cannot-do/mismatch AFTER writing-plans was last written, so planning still assumes the spec distills everything.
- **Decision:** a plan answers to the UNION: decision log (the law) · spec (the anchor) · every angle companion · census. Where the spec is SILENT and an angle speaks, the ANGLE GOVERNS — its content is ruled design that the spec's compression dropped, not optional commentary. Where spec and angle CONTRADICT, the plan may not pick: that is a failed reconcile sweep, routed back per the drift protocol before planning proceeds. Mechanics: context pack lists every companion; task Read-first lines cite governing angle sections; self-review walks each angle's cannot-do + collisions against the task list; the plan reviewer receives the angles.
- **Not a precedence inversion:** the log still outranks everything; an angle "governs" by TEACHING a ruling (citing its D#) — a plan citing an angle is citing the D# through it.
- **Affects:** writing-plans SKILL.md + plan-document-reviewer-prompt.md (Task 5c); brainstorming-flow angle 4 (new).
- **Revisit-when:** angle count per item grows enough that "read all companions" breaks planning budgets (then: the spec gains a per-area angle index so Read-first can slice).
