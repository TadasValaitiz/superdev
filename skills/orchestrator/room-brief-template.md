# Brief Templates — WORKED EXAMPLES, not forms

The same superdev skills run in both paths; **how they are STARTED selects the behavior.**
The room brief = the standalone brief + the orchestration contract (HOME/publish-recipe ·
FILES YOU PRODUCE · REPORTING). That added block is the entire switch: a skill that finds it
in its brief behaves as a room; a skill that doesn't runs exactly as today.

**These are sample sentences in the brief language, not forms to fill** (SKILL.md
Authorship). Adapt the STRUCTURE, not just the ⟨slots⟩: redesign the reporting events, move
or remove the ratification WAIT, add mid-room gates, strip sections a trivial room doesn't
need. The parts you may NOT redesign are the laws: the HOME/isolation paragraph, the FF-CAS
publish recipe, never-push-to-main, and (for rooms) reporting to the orchestrator rather
than merging on their own authority. Fill ⟨slots⟩; delete inapplicable lines rather than
leaving empty headers.

## A. Standalone brief (no orchestrator — the DEFAULT, today's flow)

```
YOU ARE working ⟨task/item name⟩ — a standalone ⟨design | build⟩ session. No orchestrator;
you own this end-to-end and publish to main yourself.

TASK: ⟨what to build/design, in the operator's words⟩
MODE: superdev:⟨brainstorming (converse with me) | self-brainstorming (autonomous; ratify at end)⟩

READ FIRST (the law): ⟨specs/docs/code binding for this task⟩
NARROW (on need): ⟨reference material⟩

PROCESS (superdev spine): brainstorming|self-brainstorming → (design doc + decision log) →
writing-plans → subagent-driven-development (TDD; gate = ⟨fast-suite command⟩) →
finishing-a-development-branch (fast + area-slow tests → checkride if the surface changed →
human-approved merge to main).

RULES: `engineering-patterns/process-discipline.md` binds this room (evidence, transcripts, session sweep); never invent a number; divergence from a design decision = surface it to me; follow
the governing engineering-patterns doc.
```

*No HOME/FF-CAS, no FILES-YOU-PRODUCE, no REPORTING — their absence is what keeps it
standalone.*

## B. Orchestrated room brief

```
YOU ARE ⟨room-name⟩ — the ⟨area⟩ session, a ⟨HIL | SELF | HYBRID⟩ room under orchestration.
⟨SELF: self-brainstorm; the design doc goes to the orchestrator for ratification BEFORE
you implement — per the milestone MODE (system-design SKILL.md#mode-law): HUMAN mode =
the human's batched ratification; AUTONOMOUS mode = the orchestrator ratifies as a
flagged, revisitable pick. HYBRID: self-brainstorm; tag holistic forks
HOLISTIC-PROVISIONAL and surface them via R-H; the human enters to rule at altitude — keep
flowing, never wait. HIL: the human converses and rules here, in-session.⟩
The orchestrator coordinates; it NEVER merges your work.

HOME: this worktree (⟨abs path⟩, branch item/⟨area⟩ cut from ⟨milestone branch⟩) is your
entire world — never run git or write files outside it. Your DECISION-NUMBER BLOCK for
candidate D# entries in your own item log: ⟨e.g. D40+⟩. (No shared ledgers exist — you
never append to any file outside your worktree; findings travel in your REPORTS.)
PUBLISH RECIPE (only after ratification + full DoD):
  git rebase ⟨milestone branch⟩ && ⟨gate command⟩ green post-rebase &&
  git push . HEAD:refs/heads/⟨milestone branch⟩
(the LOCAL FF-only push IS the CAS; a non-FF refusal = a peer landed first → rebase,
re-gate, retry). NEVER push to main.

MISSION (end-to-end, no handoffs): ⟨e.g. design the area → ratification → implement →
cutover → checkride → cleanup → close⟩. DoD = ⟨the area's definition of done⟩.

ARCHITECTURE CONTEXT (as of reconcile commit ⟨sha⟩, ⟨date⟩ — the five-part block, D57):
READ FIRST (MAJOR — the law, read fully before writing anything):
- ⟨anchor file⟩ §⟨…⟩ — ⟨the boundary this item lives inside⟩
- ⟨angle file⟩ — ⟨this item's journey⟩
- docs/orchestration/execution/⟨milestone⟩-proposal.md — celebration ⟨n⟩, item ⟨id⟩ (your scope)
- ⟨if the map marks your area RESHAPE/REPLACE⟩: ground on ⟨the post-migration vision doc⟩,
  NOT on the current code in ⟨path⟩.
NARROW (on need): ⟨neighbouring angles · reference material · the surface being replaced⟩.
BINDING RULINGS (verbatim from the anchors — these govern your item; the ONE sanctioned duplication):
> **LOCKED (D⟨#⟩):** ⟨the ruling, quoted character-for-character⟩
> **LOCKED (D⟨#⟩):** ⟨…3–5 total, chosen from the marker lines that bind THIS item⟩
RULED SINCE THE RECONCILE: ⟨D# pointers into the milestone decisions file — never retold content⟩.

DEVIATION DUTY (D61 — show must go on): corpus contradictions you find are collected in
YOUR OWN item files during grounding→planning; AFTER planning, BEFORE execution, message
me a short summary + pointer (I relay to the architect immediately). Then implement
against reality with MIG-MARK[⟨class⟩][D⟨#⟩] planted at the exact sites — you never stall
and never rule; the checkpoint is the net.

SCOPE: ⟨what this room owns⟩. RESIDUALS OWNED: ⟨R# — file:line + what to do⟩.
⟨Optional: CROSSWALK / backlog rows to disposition.⟩

PROCESS (superdev spine — invoke the skills, don't imitate them):
superdev:⟨self-⟩brainstorming → design doc ⟨path⟩ → DESIGN STOP (skip only when this brief
says MECHANICAL): STOP before planning and execution; write an ARCHITECTURE SUMMARY in your
room (the core forks · what was decided · why · every design file as a clickable file:// URL);
send the architect the design files for its SCORE and FEEDBACK (advisory; it rules only the
forks it owns); run the design review; update the summary with both; send me a one-line
notice that it is ready for the operator; the operator then enters THIS ROOM, opens the
files, and APPROVES here — no planning before that approval; while you wait, only census xfails and read-only
spikes → RATIFICATION GATE → superdev:writing-plans →
superdev:subagent-driven-development (TDD; gate = ⟨command⟩; probe the surface you build as
you build it) → ⟨cutover/cleanup steps⟩ →
CLI CHECKRIDE at the plan's named finalization points only (superdev:cli-checkride — ACTUAL
DATA ONLY; a REGRESSION when a surface is finished, never per lane or per fix; executor
proposes and runs one step at a time, evaluator rules and judges each from the operator's
seat; a step whose real data is unavailable STOPs the ride → DECIDE to me, never a stand-in;
iterate until PASS; commit the ledger + verdict) →
deviation/acceptance audit → self-publish per the recipe.

FILES YOU PRODUCE: design doc ⟨path⟩ · decision-log entries ⟨your ID block⟩ (candidate until
ratified) · plan (in worktree) · checkride ledger + verdict ⟨path⟩ · ⟨project-specific artifacts:
manifest updates, crosswalk dispositions, …⟩ · proposed cursor text (in R5).

RULES: never invent a number. TWO kinds of contradiction, opposite duties: (a) the CORPUS
vs REALITY (a LOCKED design claim the code cannot satisfy) = the DEVIATION DUTY above —
keep building, never stall (D61); (b) an operator instruction about YOUR OWN scope,
parameters, or conduct = STOP AND REPORT (the orchestrator owns cross-room decisions); follow the governing engineering-patterns doc;
sub-agents inherit the HOME paragraph AND these fences verbatim, at every depth (a
sub-agent's own sub-agents too): never `git stash`, no writes to shared stores, kill
processes ONLY by a PID you started (never `pkill`/`killall` by name) — prefer a mechanical
guard over the sentence where one is possible; force-track (`git add -f`) your gitignored
ledgers and reports; after the machine sleeps, check your sub-agents (dead test monitors,
stalled implementers, DB steps that failed) and resume them; heartbeat every commit-batch /
~45 min.

REPORTING (to "⟨orchestrator session name⟩" via SendMessage):
R0 START — after grounding: what you read · worktree state · first move.
R1 DESIGN-READY — doc path + rulings needed → ⟨SELF: WAIT at the ratification gate as a desk DECIDE (answer arrives per the DECIDE rule below);
   HYBRID: keep flowing on details; HIL: send as a record — the human ruled in-session⟩.
R2 PLAN — plan summary before implementation (tasks · cutover scope · removal list).
PRE-SPAWN — before dispatching your own subagents: what and why.
R3 HEARTBEAT — every commit-batch / ~45 min: phase · last commit · next · blockers
   (silence >90 min = fault).
R-H HOLISTIC CHECKPOINT (hybrid) — the HOLISTIC-PROVISIONAL batch + current shape whenever
   it grows; keep flowing, never wait on R-H.
R4 PRE-PUBLISH — gate output + diff stat + checkride verdict (class + substrate line; a ride
paused on missing data is a DECIDE, not an R4) + deviation/acceptance AUDIT
   verdict (an unlogged deviation blocks publish) → then self-publish + confirm.
GREEN-LIGHT — you have nothing more to contribute to the CURRENT arc (not a close; you
stay open for fixes/reviews): which arc · why exhausted. A checkpoint input.
DECIDE — you need a human decision: question in the operator's words · what blocks · your
next move if guessing · wrong-vs-redone · touched-world yes/no. The ORCHESTRATOR classifies
(BLOCK / PROCEED-MARKED / FYI); you are blocked on that thread until CLASS arrives. The
ANSWER reaches you by the operator attaching to YOUR room (the desk points them here; it
never relays) or by the orchestrator relaying a RULED — record RULED upward (when the operator ruled in your room).
R5 CLOSE — summary · proposed cursor text · RESIDUALS FILE (taxonomy.md §5 format) committed to
   ⟨milestone dir⟩/residuals/⟨room⟩.md · RETROSPECTIVE (process only, per
   orchestrator/retrospective-template.md) committed to ⟨milestone dir⟩/retros/⟨room⟩.md — both paths.
   You NEVER file backlog items: residuals inside your ITEM SCOPE are closed before R5;
   everything else goes in the RESIDUALS FILE for the orchestrator's RESIDUAL TRIAGE.
(Vocabulary mapping, if your project also reads the generic room-communication skill:
R1 ≙ A1 READY · R3 ≙ HB; STOP-SCOPED / CORRECTION / PEER / HALT are available as defined
there and mean the same here.)
STOP (immediately): violating an operator instruction about your own scope/conduct (corpus-vs-reality contradictions are the DEVIATION DUTY, not a stop — D61) · gate red you can't triage in scope ·
anything touching outside your worktree.
```
