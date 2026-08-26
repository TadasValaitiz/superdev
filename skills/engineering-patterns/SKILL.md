---
name: engineering-patterns
description: Reference library of stack-specific engineering pattern canons (python-patterns.md now; react/others as they're authored) plus the selection cascade that decides WHICH patterns doc governs a given project. Consulted by writing-plans (Global Constraints line), the SDD implementer prompt (BINDING read), and both reviewers (conformance checks) — not invoked as a standalone task skill.
---

# Engineering Patterns — the library and the selection cascade

Implementer subagents write better code when a *specific, binding* patterns doc governs
them — "clean code" is vibes, "seams return Result[T], raising across a service seam is
a defect" is checkable law. This skill holds the plugin's generic per-stack canons and
the rule for choosing which doc governs a project.

## The selection cascade (orchestrator runs this at plan time)

0. **Process discipline applies ALWAYS** (`process-discipline.md` — stack-agnostic conduct law: live-surface final bar, sweep matrices, reports-as-claims, session hygiene). A declared project canon replaces the *design* doc only, never this file; projects may extend it.
1. **Declared — always wins (design docs only).** The project's CLAUDE.md carries:
   `Engineering patterns: <path> (BINDING)`. Use THAT doc; the plugin's generic file is
   out entirely. (A project doc may itself say "extends python-patterns.md §…" — then a
   human adjudicated the layering; you never merge docs yourself.)
2. **Detected.** No declaration → read the stack off the repo: `pyproject.toml` /
   `setup.py`/`setup.cfg` → `python-patterns.md`; `package.json` with a react dependency →
   `react-patterns.md` (when authored). Polyglot repo → one doc per language, each
   governing only its own tasks.
3. **Absent / unknown stack.** No matching canon exists → say so explicitly in the plan
   ("Engineering patterns: none declared/detected — generic review rubric only"). Never
   pretend a patterns doc governed when none did; never improvise one mid-plan (author
   it first, or file the gap).

**One governing doc per task. No auto-merging.** Two merged pattern docs with
un-adjudicated contradictions paralyze implementers or make them pick randomly.

## The injection contract (where the resolved doc enters the pipeline)

| Stage | Mechanism |
|---|---|
| writing-plans | Global Constraints carries the REQUIRED `Engineering patterns:` line (resolved path + BINDING/none). Task Read-first lines cite the *specific sections* a task lives in. |
| Implementer subagent | The prompt's BINDING line: read the doc before coding; code follows it; a knowing departure is a reportable deviation (→ decision log → deviation audit). |
| Task reviewer | Conformance check: diff the code against the declared doc's sections — the doc is the quality bar, not reviewer taste. |
| Final code reviewer | Same conformance check at whole-branch scope. |

## Adding a stack

Drop `<stack>-patterns.md` in this directory and add the detection rule above. A canon
earns its place by being *checkable*: every section states the rule, the reasoning, and
what a violation looks like in review. Distill from a project that already lived the
patterns (python-patterns.md is generalized from a trading platform's operator-ratified
law); never write one speculatively for a stack no project uses.

## Library

- `python-patterns.md` — services/CLI/persistence-shaped Python (Pydantic seams,
  hand-rolled DI, Result seams, Command-pattern CLI, output/exit contract). Generalized 2026-07-22, extended 2026-08-26.
- `process-discipline.md` — stack-agnostic behavioral law (test process, live-surface bar, reports, session hygiene). NEVER overridden; consumed by every implementer/reviewer prompt alongside the design doc.
- `guard-recipes.md` — copy-paste suite guards for the canon's teeth, each with its negative control.
- `react-patterns.md` — NOT YET AUTHORED; deferred until a React project needs it.
