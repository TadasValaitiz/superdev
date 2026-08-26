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
⟨SELF: self-brainstorm; the design doc goes to the orchestrator for the human's BATCHED
ratification BEFORE you implement. HYBRID: self-brainstorm; tag holistic forks
HOLISTIC-PROVISIONAL and surface them via R-H; the human enters to rule at altitude — keep
flowing, never wait. HIL: the human converses and rules here, in-session.⟩
The orchestrator coordinates; it NEVER merges your work.

HOME: this worktree (⟨abs path⟩, branch item/⟨area⟩ cut from ⟨milestone branch⟩) is your
entire world — never run git or write files outside it. Your ID BLOCK for shared
append-only ledgers: ⟨e.g. D40+⟩.
PUBLISH RECIPE (only after ratification + full DoD):
  git rebase ⟨milestone branch⟩ && ⟨gate command⟩ green post-rebase &&
  git push . HEAD:refs/heads/⟨milestone branch⟩
(the LOCAL FF-only push IS the CAS; a non-FF refusal = a peer landed first → rebase,
re-gate, retry). NEVER push to main.

MISSION (end-to-end, no handoffs): ⟨e.g. design the area → ratification → implement →
cutover → checkride → cleanup → close⟩. DoD = ⟨the area's definition of done⟩.

READ FIRST (MAJOR — the law): ⟨binding docs⟩ · ⟨notes/refs to quote-check against your design⟩.
NARROW (on need): ⟨reference material · the surface being replaced · landed code⟩.

SCOPE: ⟨what this room owns⟩. RESIDUALS OWNED: ⟨R# — file:line + what to do⟩.
⟨Optional: CROSSWALK / backlog rows to disposition.⟩

PROCESS (superdev spine — invoke the skills, don't imitate them):
superdev:⟨self-⟩brainstorming → design doc ⟨path⟩ → RATIFICATION GATE → superdev:writing-plans →
superdev:subagent-driven-development (TDD; gate = ⟨command⟩) → ⟨cutover/cleanup steps⟩ →
CLI CHECKRIDE (superdev:cli-checkride — executor drives the new surface live; evaluator
judges from the operator's perspective; iterate until pass; commit the transcript) →
deviation/acceptance audit → self-publish per the recipe.

FILES YOU PRODUCE: design doc ⟨path⟩ · decision-log entries ⟨your ID block⟩ (candidate until
ratified) · plan (in worktree) · checkride transcript ⟨path⟩ · ⟨project-specific artifacts:
manifest updates, crosswalk dispositions, …⟩ · proposed cursor text (in R5).

RULES: never invent a number; divergence from a human lock = STOP AND REPORT (the
orchestrator owns cross-room decisions); follow the governing engineering-patterns doc;
sub-agents inherit the HOME paragraph verbatim; heartbeat every commit-batch / ~45 min.

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
R4 PRE-PUBLISH — gate output + diff stat + checkride verdict + deviation/acceptance AUDIT
   verdict (an unlogged deviation blocks publish) → then self-publish + confirm.
GREEN-LIGHT — you have nothing more to contribute to the CURRENT arc (not a close; you
stay open for fixes/reviews): which arc · why exhausted. A checkpoint input.
DECIDE — you need a human decision: question in the operator's words · what blocks · your
next move if guessing · wrong-vs-redone · touched-world yes/no. The ORCHESTRATOR classifies
(BLOCK / PROCEED-MARKED / FYI); you are blocked on that thread until CLASS arrives. The
ANSWER reaches you by the operator attaching to YOUR room (the desk points them here; it
never relays) or by the orchestrator relaying a RULED — record RULED upward (when the operator ruled in your room).
R5 CLOSE — summary · residual dispositions · proposed cursor text.
(Vocabulary mapping, if your project also reads the generic room-communication skill:
R1 ≙ A1 READY · R3 ≙ HB; STOP-SCOPED / CORRECTION / PEER / HALT are available as defined
there and mean the same here.)
STOP (immediately): contradiction with a human lock · gate red you can't triage in scope ·
anything touching outside your worktree.
```
