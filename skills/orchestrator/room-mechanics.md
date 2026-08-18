# Room Mechanics — transport, launch, publish, reporting, faults

Generalized from a production project's proven reference (multi-session room orchestration,
technically verified 2026-08-18: live S-room sessions + measured ping-pong delivery tests).
Every command here is the verbatim working form.

## The pieces

- **Orchestrator (control room)** — a normal Claude Code session. Holds the durable state,
  launches rooms, receives reports. Never merges room work.
- **Room** — a full peer session launched with `claude --bg`. NOT a subagent: subagents are
  turn-based and can never be entered or messaged by the human; a `--bg` session appears in
  the session picker / `claude agents`, is enterable via `claude attach <id>`, and survives
  independently.
- **Worktree per room** — each room is launched FROM its own git worktree, born isolated;
  its branch is cut from the integration (milestone) branch.

## Transport (set-and-forget)

Global base, set ONCE in `~/.claude/settings.json`: `crossSessionInbound: "accept"` (+ the
agent-teams env if teammate tools are wanted; + the project's default permission mode).
With `accept`, messages auto-deliver in both directions across permission classes. Without
it, mode-parity applies: only same-class pairs auto-deliver; mismatches are held.
Everything room-specific rides the LAUNCH COMMAND as flags — no per-launch settings files.

- **SendMessage**, addressed by session name (`to: "<room-name>"`); arrives wrapped as
  `<cross-session-message from-name=… from-mode=…>`.
- **`claude logs <id>`** reads any session's transcript, always, regardless of class.

## Launching a room (verbatim)

```bash
# 1. Orchestrator pre-creates the worktree (NEVER launch from the main checkout):
git worktree add .claude/worktrees/<area> -b item/<area> <integration-branch>

# 2. From INSIDE that worktree, one of two canonical commands:
# HIL room — inbound messages HELD for the human sitting in the room (they stay the sole
# ruling authority there; the flag scopes to this session only, nothing on disk):
claude --bg --settings '{"crossSessionInbound":"hold"}' -n "<room-name>" "<brief>"
# Self room AND hybrid room — direct command channel (hybrid's safety comes from the
# milestone gate + the human entering voluntarily, not from a hold gate):
claude --bg --permission-mode bypassPermissions -n "<room-name>" "<brief>"
```

The **brief is the launch prompt** — ~1 page of pointers (files to read) + protocol, never
the content itself (room-brief-template.md). `-n` names the session; the name is the message
address. Seed the brief AT LAUNCH: it needs no delivery approval; a follow-up SendMessage to
an HIL room would sit in the hold queue.

## Publishing (the FF-CAS, verbatim)

Rooms never touch `main`. From the room's worktree, only after its full definition of done:

```bash
git rebase <integration-branch>            # onto the current tip
<run the merge gate>                       # must be green POST-rebase
git push . HEAD:refs/heads/<integration-branch>
```

The LOCAL FF-only push IS the compare-and-swap: if a peer landed first, the push refuses
(non-FF) → rebase, re-gate, retry. The integration branch reaches `main` once, at milestone
close, human-approved.

## Reporting protocol (room → orchestrator, via SendMessage)

- **R0 START** — after grounding: what was read · worktree state · first move.
- **R1 DESIGN-READY** — design/surface doc path + rulings needed. Self rooms WAIT here for
  relayed ratification; HIL rooms send it as a record (the human ruled in-room).
- **R2 PLAN** — plan summary before implementation (tasks · cutover scope · removals).
- **PRE-SPAWN** — before the room dispatches its own subagents (how the orchestrator sees
  multi-agent activity behind the membrane).
- **R3 HEARTBEAT** — every commit-batch or ~45 min: phase · last commit · next · blockers.
  **Silence >90 min of active work = fault.**
- **R-H HOLISTIC CHECKPOINT** (hybrid rooms) — the accumulated HOLISTIC-PROVISIONAL batch +
  current shape, whenever it grows. The orchestrator queues it for the human at an altitude
  touchpoint; rooms never ping the human directly. The room keeps flowing — never waits on R-H.
- **R4 PRE-PUBLISH** — gate output (exit code, counts) · diff stat · checkride verdict ·
  **deviation/acceptance audit verdict** (an unlogged deviation blocks publish) → then
  self-publish and confirm.
- **R5 CLOSE** — summary · residual dispositions · proposed cursor text for the
  orchestrator's durable state.
- **STOP (immediately, any time):** contradiction with a human ruling/lock · gate red the
  room can't triage inside its scope · anything touching outside its worktree.

## Fault handling (never blind-relaunch)

Heartbeat silence → **inspect first**: `claude logs <id>` (what happened, what committed) →
nudge via SendMessage → `claude attach <id>` if judgment is needed → only then relaunch a
fresh room from the worktree's committed state. The worktree + logs ARE the salvage state;
a blind relaunch double-writes.

## Gotchas (all measured in practice)

- A **subagent/fork can never be an enterable room** — it completes when its turn ends. Use
  `claude --bg` sessions for anything a human enters or messages.
- **Teammate spawning (agent teams) needs an interactive lead** — a `--bg` control room
  downgrades teammate spawns to plain subagents.
- **EnterWorktree is unavailable to forked subagents** — pre-create worktrees with plain git
  and launch from inside them.
- **cwd drifts** across the orchestrator's shell calls — absolute paths, or re-`cd` before
  every git operation, or you read/commit in the wrong checkout.
- **Settings hot-reload is not guaranteed** for a running session — launch flags are
  deterministic; global settings changes bind only sessions launched after them.
- **Disjoint ID blocks** for any shared append-only ledger (decision numbers D24+ vs D40+):
  assigned in the orchestration graph at spawn, or parallel branches collide on renumbering.
