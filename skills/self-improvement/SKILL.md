---
name: self-improvement
description: Use when a superdev skill or its subagents misfired — a subagent missing context it needed, an orchestrator acting on a thin report, a workflow gap — or when the operator asks to improve/evolve the plugin. Diagnoses WHERE in the information flow the failure entered (prompt, orchestrator, return contract, context doc, or missing subagent), plans the smallest fix at that boundary, and applies it ONLY after operator approval, then version-bumps and reinstalls so Claude Code picks it up. Not for fixing the project the skill was working on — this improves the toolchain itself.
---

# Self-Improvement — fix the toolchain where the information died

Skills fail the way pipelines fail: information that existed somewhere never reached
the place that needed it. A subagent asks for context the orchestrator had. A report
omits the one fact the next step turned on. A template never requests what every run
needs. This skill finds the boundary where the information died, fixes THAT file, and
ships the fix through the plugin's version machinery — with the operator approving the
plan before any file changes.

<HARD-GATE>
No plugin file is edited before the operator approves the plan. The plan must name
exact filesystem paths and what changes in each. Approval of the plan is approval of
those paths — discovering mid-apply that another file needs touching reopens the gate.
</HARD-GATE>

## Checklist

1. **Capture the failure from evidence** — actual dispatched prompt + actual return, never memory
2. **Map the information flow** — upstream/downstream file map for the implicated skill (see `flow-mapping-guide.md`)
3. **Localize the bottleneck** — classify which boundary dropped the information
4. **Plan the smallest fix** — exact files, what changes, why this layer beats the alternatives
5. **OPERATOR GATE** — present plan, wait for explicit approval
6. **Apply** — edit source repo, version-bump, changelog, commit
7. **Ship** — `claude plugin update`, verify new version installed, operator reloads
8. **Verify** — confirm the change is live; where feasible, encode the failure as an eval case

## Step 1 — Capture the failure from evidence

Reconstruct the actual exchange, not the remembered one:

- What did the orchestrator ACTUALLY send? (the dispatched prompt from the transcript,
  the filled template, the files the subagent was told to read)
- What did the subagent ACTUALLY return? (its report/final message — `.superdev/sdd/`
  reports, workflow journals, transcript)
- What did the orchestrator DO with the return — and what did it need that wasn't there?

A diagnosis built on "the prompt probably included X" is invented evidence. If the
exchange can't be reconstructed, say so and reproduce the failure first.

## Step 2 — Map the information flow

Build the file-level dependency map for the implicated skill: what invokes it and with
what context (upstream), which reference files/templates feed each subagent dispatch
(the boundary contracts), and what consumes its outputs (downstream). Recipes and the
map format: `skills/self-improvement/flow-mapping-guide.md`. Generate the map LIVE from
the current files — a cached map is a hypothesis, not evidence; regenerate before
trusting it.

The map must make the two boundary contracts explicit for every subagent:
**what enters** (prompt template + slots the orchestrator fills + docs the subagent is
told to read) and **what returns** (the output contract the orchestrator acts on).

## Step 3 — Localize the bottleneck

At each boundary ask four questions: what did the sender know? what did the contract
carry? what did the receiver get? what did the receiver need? The bottleneck is where
*needed* wasn't in *carried*. Classify it:

| Class | Signature | Fix lands in |
|-------|-----------|--------------|
| **Prompt/template issue** | The dispatch template never requests or carries X, so no orchestrator could pass it | the `*-prompt.md` template |
| **Orchestrator issue** | The orchestrator HAD X but the SKILL.md never tells it to include X in the dispatch (or fills the slot thinly) | the skill's SKILL.md dispatch instructions |
| **Parent-skill issue** | The context lives one level up — the CALLING skill (possibly outside this plugin, e.g. a project skill like consumer-pass) doesn't emphasize passing X down | the parent skill's file; no plugin bump if external |
| **Return-contract issue** | The subagent knew/produced X but the output format drops it — the orchestrator never sees it | the template's output contract + the SKILL.md section that handles the return |
| **Context-doc issue** | The reference doc the subagent reads is missing, stale, or thin on X | the context/reference document |
| **Missing subagent** | No role in the workflow owns the concern at all — nothing failed, the stage doesn't exist | SKILL.md flow + a new prompt template |

Most failures are context failures, and the cheapest fix is usually the most upstream
one that is still general: fixing the template helps every future caller; emphasizing
in one parent skill helps only that caller. But don't over-upstream — if only one
parent has the context, the parent is the right home. Say which trade you made and why.

## Step 4 — Plan, Step 5 — Operator gate

Present a compact plan:

```
Failure:      <one sentence, with evidence pointer>
Bottleneck:   <class from the table> at <boundary>
Fix:
  <abs path to file 1> — <what changes and why here>
  <abs path to file 2> — …
Rejected:     <the alternative layers and why not>
Version bump: <patch|minor> → <n.n.n>   (prompt/doc tweak = patch; new
              subagent, new skill, or flow change = minor)
```

Then STOP and wait for explicit approval. Pushback or edits amend the plan; silence is
not approval.

## Steps 6–8 — Apply, ship, verify

All edits go to the plugin SOURCE repo (find it via the marketplace's
`installLocation`/source in `~/.claude/plugins/known_marketplaces.json` — NEVER edit
the installed snapshot under `~/.claude/plugins/cache/`, it is overwritten on update).

1. Make the approved edits. Nothing beyond the approved paths.
2. **Version-bump:** `scripts/bump-version.sh <new-version>` (updates all declared
   manifests), then `scripts/bump-version.sh --audit` to catch stragglers.
3. **Changelog:** append a RELEASE-NOTES.md entry — version, date, the failure
   diagnosed, the bottleneck class, files touched. This is the plugin's own decision
   log; future diagnoses will grep it.
4. Commit (conventional message; the diff should contain only approved files + version
   manifests + notes).
5. **Reinstall the snapshot:** `claude plugin update <plugin>@<marketplace>` (the bare
   plugin name may not resolve — MEASURED 2026-07-22: `update superdev` failed,
   `update superdev@superdev-dev` succeeded) — Claude Code installs
   plugins as versioned snapshots in its cache; source edits are INVISIBLE until this
   runs and the version changed (verified 2026-07-22: an unbumped edit never reaches
   the cache). Confirm with `claude plugin list` / the install record that the new
   version is the installed one.
6. Ask the operator to run `/reload-plugins` (or restart the session) — the running
   session holds the old skill set until then.
7. **Verify live:** grep the new cache path for the changed lines. Where feasible,
   encode the original failure as an eval case (`evals/**/case.yaml`,
   `claude plugin eval`) so the regression is checkable, and/or re-run the scenario
   that failed.

## Red flags

| Thought | Reality |
|---------|---------|
| "The subagent was just being lazy" | Subagents see ONLY what crosses the boundary. Missing output traces to missing input more often than to disobedience. |
| "I'll fix the prompt AND the doc AND the parent to be safe" | Shotgun edits hide which fix worked and bloat every future dispatch. One boundary, one fix; widen only on evidence. |
| "Small tweak, skip the gate" | The gate is the skill. Toolchain edits compound across every future run — the operator sees them first. |
| "Edited, done" | Un-bumped and un-updated = not shipped; the cache still serves the old version. Steps 6–8 are the delivery. |
| "I remember what the dispatch said" | Reconstruct it. Diagnosing from remembered prompts is inventing evidence. |
