# Testing Lanes — fast suite, slow suite, full suite

The canon for which tests run when. Every superdev skill that runs tests points here;
if another skill's wording ever disagrees with this file, this file wins and the
disagreement is a bug (route it through superdev:self-improvement).

## The bias: prefer the faster lane

At any moment, run the CHEAPEST test that answers the question in front of you:
the focused test while iterating, the fast suite at a commit, the full suite only
when facing the finishing gate. A heavier lane than the moment demands adds latency,
not safety — the gates exist precisely so you never need to buy reassurance by
over-running. Match the lane to the claim you're about to make: "this change works"
= focused; "this commit is safe" = fast; "this branch may merge" = full.

## The taxonomy — three names, one equation

**fast + slow = full.**

- **Fast suite** — every test NOT marked slow, run in parallel. The development lane:
  it gates every commit. It has a wall-clock **budget** (project-declared target, e.g.
  "< 3 minutes parallel"); creep past the budget is a defect to fix or file, not
  weather to accept.
- **Slow suite** — only the slow-marked tests: integration against real services,
  network, real databases, subprocess/end-to-end runs, big fixtures. Nameable (for CI
  splitting) but never a development gate by itself.
- **Full suite** — the union; everything. The ONLY thing allowed to mean "the tests
  pass, period."

**Membership is exclusion-by-default:** an unmarked test is fast. A test gets the slow
mark when it breaches the project's per-test budget (e.g. > 1s) or is categorically
slow (network, external service, real DB, process spawn, large fixture). Exclusion is
the load-bearing choice because it self-corrects: an unmarked slow test degrades the
fast lane immediately and visibly, so it gets marked — while an opt-in fast lane fails
by silent coverage loss nobody notices.

## The gate map

| Moment | What runs |
|---|---|
| While iterating (red-green-refactor) | the focused test(s) for what you're changing |
| **Before every commit** | **fast suite** — no exceptions |
| Task review | focused re-runs on specific doubt only — never a suite |
| Parallel-agent integration | fast suite |
| **Milestone gate** (parallel mode only, frozen tree) | **full suite** — each milestone boundary is a mini finishing gate |
| **Finishing gate** (finishing-a-development-branch, Step 1) | **full suite** |

At any commit gate, the task's OWN tests also run targeted — **regardless of which
lane they classify into** (measured trap: structural guards living in the slow tier
let three green fast gates miss a real defect).

The finishing gate hard-blocks merge/PR; nothing else in the flow ever waits on the
slow suite.

**The accepted trade (operator-ratified 2026-07-22):** one full-suite run per branch,
at the end. A regression in slow-covered code introduced early in a plan surfaces at
the finishing gate, with the whole branch diff as the search space. This was chosen
deliberately for development speed.

**Not doing (considered and rejected, 2026-07-22):** mid-plan full-suite checkpoints
at task-group boundaries, and an escalation trigger (full suite at commits touching
slow-covered code). Rejected to keep one rule with zero classification judgment calls:
fast everywhere, full once at finishing. Reconsider if finishing-gate failures that a
mid-plan run would have caught become a recurring, measured pain.
**Sanctioned exception (operator-ratified 2026-07-23):** MILESTONE GATES in parallel
execution mode (`Execution: subagent-driven-parallel`, multi-milestone plans) run the
full suite on a frozen tree — each milestone boundary is a mini finishing gate. This
is not the rejected checkpoint idea returning by stealth: it applies only to plans
explicitly authored as multi-milestone, where the gate follows the milestone, not an
arbitrary task count.

## How a project declares its lanes (and how an agent identifies them)

In order:

1. **Declared** — the project's CLAUDE.md carries a `Test lanes` block; this is the
   source of truth:

   ```markdown
   ## Test lanes
   - Fast suite: `pytest tests -m "not slow" -n auto`   (budget: < 3 min)
   - Full suite: `pytest tests -n auto`
   - Slow membership: > 1s/test, network, external services, subprocess/e2e
   ```

2. **Carried** — writing-plans copies the two lane commands verbatim into every plan's
   Global Constraints, so they cross the subagent boundary into every implementer
   without anyone remembering to mention them.

3. **Detected** — if undeclared, look for the project's own convention: pytest
   markers (`-m "not slow"`), npm scripts (`test:fast` / `test`), cargo test
   feature splits, go build tags. Use what exists; propose adding the CLAUDE.md
   block so the next agent doesn't re-detect.

4. **Absent** — no split exists: the whole suite IS the fast suite until it outgrows
   the budget. When it does, proposing the split (mark the slow tests, add the
   CLAUDE.md block) is your job — don't silently absorb a slow gate.

## Marking conventions by ecosystem

- **pytest:** `@pytest.mark.slow` + register the marker; fast = `-m "not slow"`.
- **npm/jest/vitest:** separate scripts (`test:fast` excludes slow projects/paths) or
  test-path patterns.
- **cargo:** `#[ignore]` for slow (fast = default run; full = `cargo test -- --include-ignored`).
- **go:** `testing.Short()` guards (fast = `go test -short ./...`; full = plain).

Whatever the mechanism, the CLAUDE.md block states the two commands — agents run the
declared commands, not reconstructed ones.
