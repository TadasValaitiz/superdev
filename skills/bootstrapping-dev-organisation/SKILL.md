---
name: bootstrapping-dev-organisation
description: Use when standing up the development organisation in a project — new or existing — before its first milestone: establishing the rooms (orchestrator, architect, front desk, item rooms), verifying cross-session messaging, creating or mapping the design corpus and ledgers onto the project's existing conventions, and reaching the first charter. Triggers on "bootstrap the organisation", "set up the rooms", "start using the system-design layer here", "first milestone in a new project".
---

# Bootstrapping the development organisation

You are setting up the organisation whose law lives in `superdev:system-design` (corpus, glossary, protocols) and `superdev:orchestrator` (milestone machinery, room mechanics). This skill is the **cold-start conversation** — deliberately NOT a script: an existing project has conventions, and each one is **bridged, adopted, or discarded by the operator's ruling**, never by a scaffold's assumption.

## Phase 0 — Technical preflight (refuse with the fix; never promise messaging you haven't verified)

1. **Git repo.** Rooms share truth through commits. No repo → `git init` + first commit before anything else.
2. **Transport.** Rooms are `claude --bg` peer sessions messaging via SendMessage. The setting that bites: `~/.claude/settings.json` must have `"crossSessionInbound": "accept"` — without it rooms launch, look healthy, and messages are **silently held**. Verify it; verify `claude agents --json` lists sessions. On a fresh machine this is the #1 nuance.
3. **Worktree tooling.** Item rooms own worktrees cradle-to-grave; confirm `git worktree` works here (or the native tool) and where trees go (`.worktrees/` ignored, or project convention).
4. **Nothing in flight.** Uncommitted work or live sessions in this repo → surface before launching anything into it.

## Phase 1 — Survey, then the ruling conversation (the heart of this skill)

**Survey first** (read, don't create): existing spec/design locations (`docs/rfcs/`, `docs/specs/`, …), decision records (ADRs, decision logs), backlog (TODO.md, tickets), test layout and fixture weight, CLAUDE.md conventions, any prior orchestration state.

Then put a **mapping table to the operator, one row per convention, three options each — they rule, you never default:**

| found | canonical role it could play | adopt / bridge / discard |
|---|---|---|
| `docs/adr/` | the design D# log (`design/decisions.md`) | **adopt** = the existing path IS the canonical file (record the mapping); **bridge** = keep both with a pointer note and one writer; **discard** = leave it frozen as history, start the canonical file |
| `docs/rfcs/` | angle/vision material | same three options |
| `TODO.md` | the backlog | same — and read it before ruling: it often encodes milestone intent worth harvesting |

Record every ruling in `orchestration/conventions.md` — the map future rooms read so they never guess which file is law here. **Two things are never negotiable away:** single-writer ownership per file, and the corpus floor's *roles* existing somewhere (the paths may be the project's own; the roles may not be dropped).

## Phase 2 — Create the floor (per the rulings, by hand)

The canonical floor, with adopted paths substituted where ruled: `design/` (angles+INDEX, visions, map.md, decisions.md, residue/residue.jsonl, residue-collections/, conformance/, handoffs/, marker-census.md — see `superdev:system-design`) · `orchestration/` (cursor.md, residual_ledger.md, decision_queue.md, process-feedback.jsonl, conventions.md) · `frontdesk/digest.md` · `.superdev/sdd/progress.md` · `docs/backlog/` (or adopted equivalent). Assign **ID blocks** per future room in `orchestration/conventions.md`. Commit the floor.

## Phase 3 — Seed the corpus (mandatory BEFORE any charter)

The probe gate and every charter cite map rows — **an empty corpus can charter nothing**. So the first working session is a `superdev:system-design` session with the operator (this bootstrap session may become it): ground on the codebase, write the first angles and the current→target map, a vision for any migration already known, D#s for what the operator rules. Harvest the surveyed RFCs/ADRs/TODO into it where the rulings said adopt.

## Phase 4 — Launch (order matters; briefs per superdev:orchestrator's room-brief-template)

1. **ORCHESTRATOR** (runs `superdev:orchestrator`; owns `orchestration/`) — send it the **activation message**: roster, ID blocks, gate ladder, conventions map, what to escalate.
2. **FRONT DESK** (view-only; renders `decision_queue` + events; DESIGN column; conversations happen in the room that needs the operator, never at the desk).
3. **ARCHITECT** (runs `superdev:system-design` in room mode; **launches idle** — its law: nothing between design checkpoints unless messaged; human-driven always).
4. **Item rooms: none yet.** They exist only when chartered.

## Phase 5 — The first milestone (who talks to whom about what)

- **Content** comes from the corpus you just seeded, not from conversation: the operator + **ORCHESTRATOR** run its HIL co-plan — cut the milestone boundary from the map (rows, bridges, item order), ratify the graph, then charter (probe gate: each item charter needs a census — ad-hoc probe rooms make them).
- **Later milestones** open from the **handoff** (milestone N may not close without next-milestone upfront design in it); the **backlog** feeds only this boundary conversation — the orchestrator brings items that now fit; the operator rules them in or leaves them parked. Nothing enters a milestone around this conversation.
- The desk never scopes milestones; it only shows you that the conversation is waiting.

## Red flags
- Creating a parallel spec/ADR/backlog location without a ruling — that's drift by scaffold.
- Promising room messaging before `crossSessionInbound` is verified.
- Chartering an item before the corpus has a row for it.
- Launching all rooms at once "to be ready" — an item room with no charter is coordination cost with no work.
