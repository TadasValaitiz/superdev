# Process Discipline (stack-agnostic — applies ALWAYS)

Behavioral law for any implementer, reviewer, or session working under this plugin.
Unlike the per-stack design canons, **this file is NOT overridden by a project's declared
patterns doc** — a project may extend it, never silently drop it. Design shapes code;
this shapes conduct.

## 1. Test process — evidence, not vibes

- TDD where it applies (see test-driven-development, incl. `test-clearance.md` for domain
  shifts): failing test first; RED and GREEN evidence (commands + output) in any work report.
- Agent-harness note: long suite runs get explicit foreground timeouts — harnesses
  auto-background long commands and strand the run.

## 2. The live surface is the final bar

- **NEVER TRUST TESTS AS THE FINAL BAR — the real application surface is.** Green
  suites have shipped 100× render bugs and structurally-unreachable gates every unit
  test missed. Final sign-off = invoking the actual CLI/API end-to-end and checking
  outputs cohere — happy path AND refusal paths, with verbatim transcripts (command +
  output + exit code). **Sweep matrices beat spot checks:** enumerate every touched
  surface × human/JSON mode × error paths; a matrix row without its verbatim transcript
  counts as NOT RUN. Where feasible a second pair of hands re-runs a sample and diffs
  against the claimed output.


## 3. Reports, reviews, and session hygiene

- A work report is a CLAIM until re-verified: reviewers reproduce load-bearing
  numbers; "0 failed" without a transcript is refused. Plan text does not grade its
  own work — plan-mandated defects are still findings.
- Corrections are VISIBLE errata (a dated line naming what was wrong), never silent
  edits.
- Leave nothing behind, same session: every leftover (scratch files, stray writes,
  orphaned branches/worktrees, stale generated docs, armed watchers) is LANDED,
  CLEANED, or FILED as a self-contained ticket. An unfiled leftover is a future wrong
  conclusion waiting to happen.
- End-of-session sweep checklist: `git status` on EVERY checkout touched (main + all
  worktrees) · worktrees/branches/claims removed or explicitly handed off · generated
  docs current (their `--check` runs green) · scratch dirs holding evidence
  preserved-and-cited or deleted · ledgers/reports reflect final state, with visible
  errata for anything corrected.


