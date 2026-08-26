# Superdev — a development organisation for coding agents

A heavily evolved fork of [Superpowers by Jesse Vincent](https://github.com/obra/superpowers) (MIT — original LICENSE retained). The upstream methodology — brainstorm → spec → plan → subagent-driven build, with TDD, YAGNI and review gates — is still the engine. This fork grows it into a **development organisation**: persistent, enterable Claude sessions ("rooms") coordinated over a design corpus, built for long-running work on codebases undergoing real domain shifts.

## The two layers

**L1 — System design (boundless, human-driven).** A persistent ARCHITECT room owns the *corpus*: angle documents (deliberately partial views of the whole system), a current→target map (`KEEP / RESHAPE / REPLACE / DEFER`, with test verdicts), post-migration *vision* documents (so future design grounds on where you're going, not the legacy you're leaving), and a decision log. Nothing here ever blocks development — deferred architecture lives as greppable `MIG-MARK`/`DOC-MARK` markers until a later pass removes them.

**L2 — Execution (bounded, continuous).** An ORCHESTRATOR runs one milestone at a time: it cuts items from the map along corpus seams (never parallelising a dependency — parallelism is created by *splitting* blockers so their unblocking kernel merges first), charters item rooms that own their worktrees cradle-to-grave, collects design findings as *residue*, and hands the architect a clustered collection at *design checkpoints*. Item rooms always finish and merge. A FRONT DESK renders one queue for the operator, whose attention is the system's scarcest resource and is spent on exactly three things: design rulings, execution-shape agreements, and checkrides.

Files are the law; messages are pointers to them. Every gate is enforced outside the node it binds.

## Install

```bash
claude plugin marketplace add <this-repo-or-local-path>
claude plugin install superdev@superdev
# in a session: /reload-plugins
```

For live development, register the checkout as a directory marketplace instead — edits apply on `/reload-plugins`.

## Where to start

- **New or existing project →** `/superdev:bootstrapping-dev-organisation` — verifies cross-session messaging, maps your existing conventions (adopt / bridge / discard, your ruling per convention), creates the corpus floor, seeds it in a design session, launches the rooms, reaches the first charter.
- **Single task, no organisation →** just start working; the classic pipeline (brainstorming → writing-plans → subagent-driven-development) runs standalone, unchanged.
- **Architecture-scale thinking →** `/superdev:system-design` — solo or as the architect room.

## Skill catalog

| Layer | Skills |
|---|---|
| Organisation | `bootstrapping-dev-organisation` · `orchestrator` (milestone machinery, chartering, checkpoints, rooms) · `system-design` (corpus, angles, markers, glossary — the shared vocabulary every skill links) |
| Item pipeline | `brainstorming` (corpus-aware, angle-by-angle, test disposition) · `writing-plans` (execution-shape proposal → agreement auto-starts the build; plan checkpoints) · `subagent-driven-development` (broad role-carried arcs, one carrying implementer, resume-first fixes, Codex as the long-run worker) |
| Quality gates | `cli-checkride` (executor drives the live surface; evaluator judges from the operator's seat; distills reusable scenario intents) · `test-driven-development` + `test-clearance` (what happens to tests under a domain shift: keep · regenerate · archive-then-rewrite · fix-in-place) · `verification-before-completion` · `requesting`/`receiving-code-review` · `finishing-a-development-branch` |
| Law | `engineering-patterns` — two files with different override rules: `python-patterns.md` (per-stack **design law**, project-overridable) and `process-discipline.md` (stack-agnostic **conduct law**, never overridden), plus `guard-recipes.md` (the enforcement, copy-paste ready) |
| Toolchain | `self-improvement` (single failures or an accumulated process-feedback ledger → operator-gated skill fixes) · `writing-skills` · `using-git-worktrees` · `systematic-debugging` · `dispatching-parallel-agents` · `executing-plans` · `self-brainstorming` |

## Design record

The organisation's full design — 46+ logged decisions, the anchor spec, angle companions — lives in `docs/superdev/specs/2026-08-24-system-design-layer-design.md` and its decision log. Release history: `RELEASE-NOTES.md`.

## Credits & license

MIT. Built on Superpowers © 2025 Jesse Vincent (see `LICENSE`); the development-organisation layer, system-design corpus, chartering algorithm, checkride scenarios, and pattern canons are this fork's additions, operator-driven by Tadas.
