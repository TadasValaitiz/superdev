# Testing Lanes — fast suite, slow suite, full suite

The canon for which tests run when. Every superdev skill that runs tests points here;
if another skill's wording ever disagrees with this file, this file wins and the
disagreement is a bug (route it through superdev:self-improvement).

## The bias: prefer the faster lane

At any moment, run the CHEAPEST test that answers the question in front of you:
the focused test while iterating, the fast suite at a commit, and at the finishing gate
the fast suite PLUS the slow tests that actually cover what you touched — cherry-picked,
never the whole slow tier. A heavier lane than the moment demands adds latency, not
safety. Match the lane to the claim: "this change works" = focused; "this commit is
safe" = fast; "this branch may merge" = fast + the area's slow tests.

## Never launch the full suite as one command

**The full suite is a CONCEPT (fast + slow = everything), not a runnable gate command.**
Launching the whole slow tier in a single invocation is banned at every gate — it is the
scar this doctrine exists for: a monolithic run gets stuck on one hung test, you kill the
whole thing, and you rerun from zero, losing every result that already passed. It also
serializes badly when ≥2 agents gate at once.

Instead, slow coverage is **cherry-picked by area and run as SEPARATE commands:**

- After the fast suite is green, identify the slow tests that cover the code this change
  touched — by matching path/module/marker to the changed files (the slow test whose
  path mirrors a file you edited; the integration test for a subsystem you changed).
- Run each as its **own killable command** (one directory, one module, one marker per
  invocation). A stuck unit is killed and rerun ALONE; everything already green stays green.
- **Slow tests you authored for this change** are part of the area by definition — run
  them, separately, same way.
- When unsure whether a slow test is "in the area," include it — over-inclusion costs a
  few minutes; the backstop for what cherry-picking still misses is a **scheduled full
  sweep** (below), run as a separate chunked task on main, never at a consumer gate.

The honest trade: the finishing gate now proves *"fast green + the slow tests plausibly
affected by this change green,"* not *"every test passes."* The scheduled sweep is what
recovers the whole-suite guarantee — off the gate's critical path, where a stuck run
costs no one's publish.

## The taxonomy — three names, one equation

**fast + slow = full.**

- **Fast suite** — every test NOT marked slow, run in parallel. The development lane:
  it gates every commit. It has a wall-clock **budget** (project-declared target, e.g.
  "< 3 minutes parallel"); creep past the budget is a defect to fix or file, not
  weather to accept.
- **Slow suite** — only the slow-marked tests: integration against real services,
  network, real databases, subprocess/end-to-end runs, big fixtures. Nameable (for CI
  splitting) but never a development gate by itself.
- **Full suite** — the union; everything. A CONCEPT, not a gate command: "every test
  passes" is only ever established by the scheduled sweep, never by one invocation at a
  gate (see "Never launch the full suite as one command").
- **Scheduled sweep** — the slow tier run on latest main as a SEPARATE, chunked,
  killable task (per-directory / per-marker chunks; killing one chunk keeps the rest),
  on a cadence or after major milestones. This is where whole-suite truth is
  re-established, off every agent's publish path. A red it finds is a P0-class item (a
  regression that reached main) — file one per red.

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
| **Before every commit** | **fast suite** — one command, no exceptions |
| Task review | focused re-runs on specific doubt only — never a suite |
| Parallel-agent integration | fast suite |
| **Milestone gate** (parallel mode only, frozen tree) | fast suite + **area-selected slow tests, each its own command** |
| **Finishing gate** (finishing-a-development-branch, Step 1) | fast suite + **area-selected slow tests, each its own command** |
| **Scheduled sweep** (separate task on main, not a gate) | the slow tier in killable chunks — the whole-suite backstop |

At any commit gate, the task's OWN tests also run targeted — **regardless of which
lane they classify into** (measured trap: structural guards living in the slow tier
let three green fast gates miss a real defect).

The finishing gate hard-blocks merge/PR; no gate ever launches the whole slow tier as
one command.

**The accepted trade (operator-ratified 2026-08-12):** the gate runs fast (one command)
+ the slow tests covering the touched area (separate killable commands) — never the
monolithic full suite. This trades the "every test passed at merge" guarantee for
killability and concurrency (a stuck unit costs one rerun, not the whole gate; ≥2 agents
can gate without a monolithic pile-up). Whole-suite truth is recovered by the scheduled
sweep, off the publish path. MEASURED basis: 4 concurrent full-suite gates degraded 5.6×
(≈2020s vs ≈356s alone) with nondeterministic flaky reds under contention.

**Superseded (was operator-ratified 2026-07-22/23):** the earlier doctrine ran the FULL
suite as one command at the finishing gate, and again at milestone gates in parallel
mode. Replaced 2026-08-12 after the contention measurement above — the monolithic run's
stuck→kill→rerun-from-zero failure and its concurrency degradation outweighed the
single-command simplicity. The cherry-pick + scheduled-sweep split keeps the coverage
while removing the monolith.

## How a project declares its lanes (and how an agent identifies them)

In order:

1. **Declared** — the project's CLAUDE.md carries a `Test lanes` block; this is the
   source of truth:

   ```markdown
   ## Test lanes
   - Fast suite (the gate): `pytest tests -m "not slow" -n auto`   (budget: < 3 min)
   - Slow, by area (separate killable commands): `pytest <dir-or-path> -m slow -n auto`
     — pick the dirs/markers covering what you touched; NEVER `pytest tests -m slow` as
     one command.
   - Scheduled sweep (separate task, not a gate): `scripts/slow_sweep.sh` (chunked, killable)
   - Slow membership: > 1s/test, network, external services, subprocess/e2e
   ```

   If the project ships a gate entrypoint that REFUSES a whole-suite invocation
   (e.g. `scripts/gate.sh` rejecting `--suite all`), that mechanism is the declaration —
   prefer it over a raw pytest spelling; the refusal is what makes the rule unforgettable.

2. **Carried** — writing-plans copies the fast command + the slow-by-area recipe into
   every plan's Global Constraints, so they cross the subagent boundary into every
   implementer without anyone remembering to mention them.

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
- **cargo:** `#[ignore]` for slow (fast = default run; slow-by-area = `cargo test -p <crate> -- --ignored`).
- **go:** `testing.Short()` guards (fast = `go test -short ./...`; slow-by-area = `go test ./<pkg>/...`).

Whatever the mechanism, the CLAUDE.md block states the fast command and the slow-by-area
recipe — agents run the declared commands, not reconstructed ones, and never bundle the
whole slow tier into one invocation.
