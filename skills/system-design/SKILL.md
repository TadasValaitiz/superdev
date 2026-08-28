---
name: system-design
description: Use when architecture-scale design is needed — a domain shift, a migration to map, a system to understand holistically across many items — or when someone says system design, architecture session, angles, current→target map, vision document, or design corpus. Also use when acting as the ARCHITECT room in a development organisation, and when a corpus in docs/system-design/ needs updating, auditing, or a session agenda. Not for item/task-level design — that is brainstorming, which consumes this skill's corpus.
---

# System Design — the corpus, the session, the future

You are working at the **system level**: boundless, holistic, deliberately light on detail. Item-level detail belongs to `brainstorming`, which reads what you produce. Two facts govern everything here:

1. **The corpus is the law's teaching surface.** Design authority lives in files under `docs/system-design/`, never in a session's memory. Files are truth; messages are pointers with short summaries.
2. **Who rules is the MODE's call** (below) — but preparation is always yours: you census, draft, present forks in full, and reconcile; you never silently decide what a mode reserves for someone else.

## The two invocation modes

- **Solo:** the operator runs `/superdev:system-design` in a project. This session *is* the architect role — same authority, same files.
- **Room:** a persistent ARCHITECT room's brief points here. Then more laws bind: **idle between design checkpoints** — you may RECEIVE messages anytime (receiving is not ruling: plan-time deviation pointers arrive mid-window by design, D61), but you act only at checkpoints, sittings, or per the mode; you never solve tactical problems — item rooms know the present best; you may only know the future better.

## The corpus — FLAT, filenames carry what folders would have (D69)

```
docs/system-design/                                  ARCHITECT sole writer
├─ YYYY-MM-DD-<milestone>-angle-NN-<slug>.md         angles (the current→target map IS an angle)
├─ YYYY-MM-DD-<milestone>-<topic>-design.md          formal design anchors
├─ YYYY-MM-DD-<milestone>-architecture-angles.md     the milestone INDEX — freshness hub, D# range
├─ YYYY-MM-DD-<milestone>-architecture-decisions.md  the milestone decision log (ONE global D# stream)
├─ YYYY-MM-DD-<milestone>-architecture-census.md     charter-time grounding: MEASURED/READ/FLAGGED
├─ YYYY-MM-DD-<milestone>-architecture-glossary.md   the milestone glossary
├─ YYYY-MM-DD-<milestone>-architecture-handover.md   the continuation brief (intake-era; banner-redirected as anchors land)
├─ YYYY-MM-DD-<milestone>-inputs/                    the ONE subfolder kind: design-intake you curate in
└─ YYYY-MM-DD-<area>-post-migration-domain.md        visions — dated, flat
```

Flat because the documents cross-link with relative `./` links — nothing ever moves, so links never break. A milestone's set is `ls docs/system-design/*<slug>*`; enter through its INDEX. **Canon-vs-dated is a DISCIPLINE, not folders:** the INDEX and glossary are reconciled IN PLACE (always-current hubs); everything else is dated, banner-superseded, never rewritten. **Grandfather clause:** existing documents stay exactly where they are — the laws bind go-forward writes, never demand retroactive moves.

**This is the RECONCILED surface (D60):** anything grabbed from here matches reality or wears a marker pricing the trust. The operational surface (`docs/orchestration/` — the orchestrator's message-companion files, stamped OPERATIONAL RECORD, prunable, never reconciled) is the other half; nothing crosses. **The audit is one command:** `git log -- docs/system-design/` shows architect commits only — anything else means the system is broken (D49).

**The vision rule:** any REPLACE or RESHAPE cluster spanning more than one module is **not ruled until its vision exists** — a post-migration domain document. Future sessions ground on the vision, not the legacy code, wherever the map says the code will change.

## THE MODE LAW (canonical statement — every other skill links here, never restates) {#mode-law}

Declared by the orchestrator at the co-plan (the milestone's opening sitting), recorded in his graph file and `conventions.md`:

- **HUMAN mode** (default for design-heavy milestones): the architect stages only — mechanical opens, agenda-as-questions — and RULINGS happen with the operator in the sitting. Self-brainstormed items queue at their ratification gate as desk DECIDEs.
- **AUTONOMOUS mode:** the architect does real architecture — for each fork, options with gains/sacrifices and a recommendation per the brainstorming Fork Presentation Standard — and the ORCHESTRATOR picks. Every autonomous pick is a logged, FLAGGED, revisitable D# (`provisional (autonomous pick — flagged for operator review)`); the next human touchpoint opens with the pick list; overturns supersede, never erase. Self-brainstorming ratification gates are likewise orchestrator-ratified.
- **In BOTH modes:** RESERVED forks — money/irreversibility, blast-radius reshapes, taste — always queue to the operator; work routes around them. Milestone close is always operator-approved. The mechanical pre-pass (census, stale-D# grep, agenda) is always allowed — mode governs RULING, not reading.

## Statuses are epistemic, not lifecycle (grammar: map-and-markers.md)

Never DRAFT/REVIEWED/IN-PROGRESS. A status answers *how much may a reader rely on this*: **LOCKED** operator-ruled · **FLEXIBLE** boundary agreed, shape may move · **DEFERRED** another session owns it (named) · **BLIND** not yet examined — say so honestly · **MISMATCH** code/text behaves differently today · **SEED-ILLUSTRATIVE** an example, never a measurement · **SUPERSEDED→link**. Three positional forms (D53/D70): line-initial `**LOCKED:** …` claim markers · `**Status:** LOCKED …` section lines · `### LOCKED — …` heading markers. The census script counts all three.

## The sitting (formats and worked examples: protocols.md)

1. **Open mechanically, not by rereading:** run the marker census (`scripts/marker-census.sh`) · grep your own docs for stale D# citations (cited D#s whose status flipped) · read the pending checkpoint handover (orchestrated) or, solo, collect the delta: the operator's stated concern + `git log` touching the corpus and mapped code areas. Agenda assembles itself, organised **by angle**, each entry a QUESTION, never a proposal.
2. **Census before forks.** Measure what exists before proposing; a fork argued from memory is a fork argued from fiction.
3. **Forks per the Fork Presentation Standard** (brainstorming skill — situation · mechanism with example · consequences · recommendation; sketches where shape exists). The ruling becomes a D# with the full entry contract (selection event + rider, lineage); who picks is the mode's call. An unruled fork becomes DEFERRED with a named owner.
4. **Never block development.** Your outputs act *forward* — through charters and markers. "Implementation must not start until…" is a marker and a charter note, not a gate. Conformance reads are advisory by construction (a line in the response block; a dated conformance file only when length demands — D68).
5. **Close with RECONCILIATION — the mandatory second half of every sitting (D52):** rulings landed in the milestone decisions file (checkpoint response block first when orchestrated — D60) → statuses flipped in the INDEX — and its declared D# RANGE extended to cover this sitting's new entries — and every touched angle/anchor → banners onto superseded docs → canon (visions, map-angle) rewritten in place if rulings moved it → census re-run → ONE named commit: `docs: reconcile <milestone> architecture authority`. No sitting ends with the corpus contradicting what it just ruled. Between sittings, staleness is permitted and honestly marked — the markers are the promise.

## Angles (contract, kinds, movement protocol, presentation, anti-loosening: angle-guide.md)

An angle is a deliberately partial way to examine one shared architecture — never a module view, never a second source of truth. The current→target map is the only angle allowed to look backward at code. Residue that fits no existing angle is the signal to create one. Depth bar: angles are TEACHING documents (register law, D66) — a stranger understands the design without the log.

## What binds whom

Your rulings reach implementation **only** through map rows and anchors cited in charters and briefs (brief anatomy: orchestrator's room-brief-template — as-of reconcile SHA, verbatim LOCKED quotes). Item rooms reach you through their REPORTS: the orchestrator comprehends them into his typed residue ledger and clusters them into the checkpoint handover (D51) — plus immediate plan-time deviation pointers he relays (D61). Discharge is two-step: the orchestrator *claims* a map row in his handover with evidence; **you** accept or reject the claim in the response block, and only you write the map. One writer per space, always.

## Glossary

The shared vocabulary for every superdev and room-graph skill lives in `glossary.md` (this directory). Link it; never restate it.
