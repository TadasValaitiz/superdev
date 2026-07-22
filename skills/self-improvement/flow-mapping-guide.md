# Flow-Mapping Guide — building the upstream/downstream dependency map

The map answers, for one implicated skill: **where could the missing information have
come from, and at which file did it die?** Generate it live from the current files.

## The information-flow model

Every superdev skill run is this pipeline; each `↓` is a boundary where information
can die:

```
CALLER  (user request · parent skill naming superdev:<x> · hook · workflow script)
  ↓  invocation context: what the orchestrator knows at dispatch time
ORCHESTRATOR  (the session executing SKILL.md)
  ↓  reads reference files SKILL.md names (templates, guides, checklists)
  ↓  fills a prompt template's slots and dispatches a SUBAGENT
SUBAGENT  — sees ONLY: its prompt + files the prompt tells it to read + what its
             own tools discover. No conversation history. No orchestrator memory.
  ↓  returns a report per the template's output contract
ORCHESTRATOR — sees ONLY the return; acts on it per SKILL.md's handling rules
  ↓  writes artifacts (specs, logs, plans, reports)
DOWNSTREAM  (next skill in the chain · later sessions · the operator)
```

The two subagent boundaries are where most context failures live: **enters** (template
+ slots + named docs) and **returns** (output contract). An orchestrator that "knows"
something has NOT communicated it unless it crossed one of these explicitly.

## Map format

One block per skill, kept in the diagnosis (commit it with the fix if useful):

```
SKILL: <name>                                    generated: <date> (live)
UPSTREAM (who invokes, what context enters)
  - <caller file:line> → names superdev:<x>; passes: <what the caller's text
    instructs the orchestrator to bring — item file, spec path, plan, nothing>
FILES READ BY ORCHESTRATOR
  - SKILL.md · <referenced templates/guides, with the SKILL.md line naming them>
SUBAGENT BOUNDARIES (one row per dispatch)
  - dispatch: <template file>
    enters:  slots [<SLOT names>] filled from <where the orchestrator gets them>;
             subagent told to read: <files>
    returns: <output contract — fields/format the template demands>
    handled: <SKILL.md section that consumes the return>
ARTIFACTS WRITTEN
  - <paths, from SKILL.md/templates>
DOWNSTREAM (who consumes the artifacts)
  - <skill/file that reads each artifact>
```

## Recipes (run from the plugin source root)

**Who invokes skill X** — plugin-internal callers, hooks, and the host project's own
skills (parent-skill emphasis fixes often land there):

```bash
grep -rn "superdev:X\|skills/X/" skills/ hooks/ --include="*.md" --include="*.json"
grep -rn "superdev:X" <host-project>/.claude/skills/ 2>/dev/null   # e.g. consumer-pass
```

**What the orchestrator reads** — files SKILL.md names:

```bash
grep -nE '[a-zA-Z0-9_-]+\.(md|sh|cjs|html)' skills/X/SKILL.md
```

**Subagent boundaries** — templates, their slots, their output contracts:

```bash
ls skills/X/*prompt*.md                     # dispatch templates
grep -nE '\[[A-Z_]+\]' skills/X/*prompt*.md # slots the orchestrator must fill
grep -n -A6 -iE 'output format|report back|returns' skills/X/*prompt*.md
```

For workflow-based skills (e.g. self-brainstorming), the boundary contracts are the
schemas and role prompts in the workflow reference file — same questions, same map.

**Downstream** — who consumes what X writes:

```bash
grep -rn "<artifact path or pattern>" skills/ <host-project>/.claude/skills/
```

**Cross-plugin note:** callers outside the plugin (project skills like consumer-pass,
CLAUDE.md directives, other plugins) are part of the map. A fix landing there needs no
plugin version bump — but record it in RELEASE-NOTES.md anyway if the diagnosis started
here, so the trail stays in one place.

## Reading the map for the bottleneck

Walk the missing information backward from where it was needed:

1. Did the receiver's INPUT contract carry it? (no → prompt/template or orchestrator issue —
   check whether the orchestrator even had it; if only the caller had it, parent-skill issue)
2. Did the sender's OUTPUT contract carry it? (subagent knew it, report dropped it →
   return-contract issue)
3. Was it supposed to come from a named doc? (doc thin/stale/missing → context-doc issue)
4. Does ANY row of the map own it? (no → missing subagent / missing stage)

The fix belongs at the boundary that failed — the most upstream location that is still
general enough to help every caller, and no further.
