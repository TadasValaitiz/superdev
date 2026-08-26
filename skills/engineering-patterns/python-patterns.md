# Python Engineering Patterns (generic canon)

The plugin's generic design law for Python projects with a service/CLI/persistence
shape. Generalized from an operator-ratified production canon (2026-07-23); a project's
own declared patterns doc ALWAYS supersedes this file (see SKILL.md cascade).

Every section is checkable: the rule, the reasoning, and what a violation looks like.
**Migration rule:** legacy code is lifted onto these patterns AS IT IS TOUCHED — never
big-bang, never left behind when edited.

## 1. Module architecture — five layers, arrows point inward

```
L0  value objects      identity, units, refs, records      deps: pydantic + stdlib ONLY
L1  pure kernels       math, classification, derivation    deps: L0; models in -> models out
L2  services           orchestration, effects              deps: L1 + repo Protocols + Deps
L3  persistence        repo Protocol + rows + records      public surface = Pydantic records
L4  shell              CLI leaves, wiring, runtimes        deps: everything; ZERO logic
```

- Package silhouette per domain: `domain.py` (L0/L1 models) · a kernels module (L1) ·
  `service.py` + `deps.py` (L2) · rows/records under `persistence/` (L3) · thin leaves
  in the CLI module (L4).
- **Arrow rules are enforced by tools that run in the suite** — import-linter contracts
  or grep-guard tests: kernels import no repo/CLI/IO; the CLI framework appears only in
  `cli*.py`. "Enforced" never means "by convention."
- One capability, one home. Moving a module leaves a one-line re-export shim so
  importers stay green.

## 2. Types law — no `dict[str, Any]` across any seam

- Every seam-crossing shape is a **frozen Pydantic model** (`ConfigDict(frozen=True,
  extra="forbid")`). `TypedDict` only for internal single-function transients. A bare
  dict reaching a service, a persisted column, or a CLI render is a defect.
- **Named intermediate types:** every pipeline stage boundary gets its own frozen
  model — no reused generic models, no tuples. A stage needing a new field grows a NEW
  type.
- **Unit-carrying value objects for consequential numbers.** A bare float crossing a
  boundary loses its units — classic scar class: a rate annualized twice because
  nothing said which basis it carried. The value carries its basis; derived quantities
  are DERIVED, never re-passed as parameters. If a wrong pairing is representable, it
  will eventually be paired wrong.
- **Teeth — the types law is machine-enforced, never aspirational:**
  - the strict type-checker (mypy/pyright strict) runs IN the suite; its errors are red,
    with a per-module strictness ratchet for legacy (modules only ever get stricter);
  - a shared frozen base model (`ConfigDict(frozen=True, extra="forbid")`) is the ONLY
    ancestor for seam models — grep-guard: no bare `BaseModel` on a seam;
  - AST/grep guards ban `dict[str, Any]`, `**kwargs`, and bare `float`/`int` money-or-units
    values in the signatures of L1/L2 public functions — guards run in the suite and each
    has a NEGATIVE CONTROL proving it fires;
  - a seam-inventory test enumerates every service entrypoint and asserts params/returns
    are models — a new untyped entrypoint is a red test, not a review comment.
- **Identity is an explicit value object, never a whole-object dump.** Where objects
  hash: `XxxIdentity` frozen model + a whitelist factory; hash = sha256 over canonical
  JSON (sorted keys, fixed separators) of the identity model only. Mandatory guards: a
  completeness set-equality test (every source field classified identity or
  non-identity — an unclassified new field is a red test); golden-hash pins on
  fixtures; defaults materialized before hashing; `exclude=`/`exclude_none=` never feed
  a hash; a `semantics_version` field bumps only on reinterpretation. Permission and
  authority flags live OUTSIDE identity.

## 3. DI wiring — hand-rolled composition roots, no framework

- ONE eager composition root per process entry: an `App` frozen dataclass built by
  `build_app()` — pure wiring, no I/O, no env reads — constructed once per CLI
  invocation; a future web server holds one from lifespan.
- Per-module frozen `XxxDeps` dataclass (`repo, clock, log_dir, …`) consumed by
  `XxxService(deps)`. **The Deps constructor IS the test-override seam** — tests
  construct with fakes and frozen clocks; no monkeypatched wiring, no DI framework.
- Cores never see containers: pure functions receive values, not dependencies.
  Services receive Deps, not the App.
- Repositories are consumed via a **Protocol**, never the concrete class.

## 4. Error handling + Result — refusals are values

- **Seams return `Result[T]`** (`Ok[T] | Err`, with a structured error carrying
  `{code, message, retryable, source, details}` and a CLOSED error-code enum — extend
  the enum, never pass strings). Raising across a service seam is a defect.
- One sanctioned broad-except: a `catching(fn, code=…)` converter at exception
  boundaries — it converts, never hides. Bare `except: pass` fails review.
- Pure kernels raise nothing at runtime — invalid states are refused at model
  construction (validators); missing data is an in-band value handled by a fail-closed
  branch, not an exception.
- CLI edge: match on the Result — `Ok` renders, `Err` prints `code: message` and exits
  nonzero. Refusal messages tell the caller WHAT TO DO NEXT (name the flag, the
  command, the format).
- Fail closed, loudly. Never silently substitute a default/provider/branch on missing
  inputs; an honest refusal with a reconstructable reason beats a plausible wrong
  answer.

## 5. Pipelines — functional composition inside the imperative shell

- Kit: `pipe(value, f1, f2, …)` for plain transforms; `flow(value, *steps)` for Result
  chains that SHORT-CIRCUIT on first `Err`; `compose(*steps)` to name a reusable
  pipeline; `.and_then(step)` inline for 2-3 steps; an async-aware variant mixes sync
  core steps with async shell steps.
- A step is `Callable[[FrozenA], Result[FrozenB]]` (or plain `A -> B` in pipe-land).
  Pure steps stay sync and dependency-free; effectful steps are bound service methods.
  A mis-ordered pipeline is a TYPE error, not a runtime surprise.
- Intermediate models may carry their predecessor's fields plus their own verdict and
  evidence ids — provenance is structural, not disciplinary.
- One public idiom per context; don't mix pipe/flow in one module without a reason.
- **Concrete over clever (composition law):** no higher-order generic drivers — lambdas,
  `partial()` bindings, wide `Callable` params, and `TypeVar` chains obscure the real call
  graph from humans, IDEs, static analysis, AND coding agents reconstructing the system
  from symbols. Pipelines are ordinary concrete Python: **named stage functions only**
  (no lambdas in `flow`/`compose` calls — grep-guarded), each stage an atomic transition
  consuming and producing immutable models. Removing a little loop duplication never
  justifies making the call graph unrecoverable.
- **Teeth:** mis-order is caught by the type-checker (that is the point of typed stages —
  verify it stays true: one deliberate mis-ordering per pipeline family exists as a
  type-check-must-fail fixture); a stage that raises instead of returning `Err` is caught
  by a suite guard driving each public pipeline with a poisoned input; stage models are
  append-only (predecessor's fields + own verdict) — a stage silently dropping upstream
  fields is a red completeness test.

## 6. Command pattern for CLI — the web-server-tomorrow guarantee

- Every command: exactly ONE frozen `XxxRequest` model and ONE `XxxResponse` model;
  the service entrypoint is exactly `(XxxRequest) -> Result[XxxResponse]`. Never loose
  positional/keyword params on the seam.
- The leaf's ENTIRE job: parse argv → Request → `app.<service>.<verb>(request)` →
  render. All validation lives in the Request's validators. Zero business decisions in
  the leaf.
- Consequences, by construction: a web route is JSON → the SAME Request → the SAME
  call → the SAME Response (`--json` prints exactly it); a command bus later is
  mechanical; agents author safely against uniform shapes.
- Renames keep the old spelling as a hidden alias for a transition window; CLI
  reference docs are regenerated IN THE SAME COMMIT as any surface/help change.
- **Output & exit contract (operator-experience law):**
  - exit map: **0** success · **1** internal error (a bug — never intentional) · **2**
    usage (framework-native) · **3** typed operational refusal, whose message names the
    RUNNABLE remedy (the flag, the command, the format — never just "invalid");
  - every command string emitted in hints, refusals, or `next:` blocks must EXIST on the
    live surface — guarded by a test that greps emitted spellings against the registry;
  - a command's capability limits are declared in its own `--help` (a `Limits:` block);
  - no derived/annualized figure is shown without its basis — payload and human mode both;
  - listings carry a provenance kernel: a row that shows an honesty tier also shows what
    derived it; full reconstruction lives on the detail surface.

## 7. Logging & observability — reconstructability is the bar

- Every state-changing command logs BY DEFAULT — structured JSONL: the parsed Request,
  step verdicts with evidence ids, the final Response, every persisted-record id. Pure
  reads stay opt-in.
- The acceptance test is literal: **a number the command reports must be rebuildable
  from the log alone.** If it isn't reconstructable, it isn't observable yet.
- Logs cross-reference the store (ids); they never duplicate truth.

## 8. Persistence — additive forever

- New columns additively; new tables create-if-absent; **no destructive migration, no
  in-place edits of historical artifacts** — recomputed values live in NEW versioned
  columns/rows beside the originals, with readers preferring current and rendering
  legacy AS legacy.
- Records-of-authority (verdicts, grants, lineage) are **append-only ledgers**:
  insert-only repo surface, current state derived from the latest row (ordered by
  autoincrement id, never wall-clock), corrections are new rows.
- Content-addressed rows are insert-or-verify: same key + different bytes raises,
  never silently overwrites. Check-then-insert races are backstopped by DB unique
  constraints.
- Persisted models tolerate legacy keys via explicit read-compat validators, so
  history stays readable forever.

## 9. Code reuse — one home, lift don't copy

- Before writing anything: grep for the existing capability. Duplicated logic in
  shells is the chronic disease of long-lived CLIs (real case: a 14k-line CLI file
  accreted 13 call sites of one leaked boundary, and two coexisting unit conversions —
  one rotten). The cure is lifting to L2 once and threading everywhere.
- Compat shims make moves cheap; deprecation windows make renames cheap. If a helper
  is copied once, it wanted to be a module.

## 10. Testing — evidence, not vibes

- TDD: failing test first; RED and GREEN evidence (commands + output) in any work
  report.
- Numbers asserted in tests carry a provenance comment (measured / simulated /
  seed / derived); fixture seeds state their unit contracts (fractions vs percent —
  the classic 100× render scar).
- Pin boundaries (exact threshold edges), golden hashes, sign/unit conventions; add
  NEGATIVE CONTROLS where a guard's value is coverage (prove the test fails when the
  property is broken).
- Guards run in the suite (arrow tests, completeness tests, golden pins) — a rule that
  doesn't run is a hope.
- Prefer real substrate in isolated per-test namespaces over hand-rolled fakes when
  the project supports it — no `Fake*Repo` drift to maintain.
- Agent-harness note: long suite runs get explicit foreground timeouts — harnesses
  auto-background long commands and strand the run.
- **NEVER TRUST TESTS AS THE FINAL BAR — the real application surface is.** Green
  suites have shipped 100× render bugs and structurally-unreachable gates every unit
  test missed. Final sign-off = invoking the actual CLI/API end-to-end and checking
  outputs cohere — happy path AND refusal paths, with verbatim transcripts (command +
  output + exit code). **Sweep matrices beat spot checks:** enumerate every touched
  surface × human/JSON mode × error paths; a matrix row without its verbatim transcript
  counts as NOT RUN. Where feasible a second pair of hands re-runs a sample and diffs
  against the claimed output.

## 11. Reports, reviews, and session hygiene

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

## 12. Policy seams — switchable logic is a named abstraction

Wherever behavior could plausibly be switched by different policies, rules, or
rankings — selection strategies, re-rankers, sampling, allocation, re-fit methods —
the switch point is an explicit named **Protocol** (a "policy seam") with registered
implementations, never inline branching. Selectable by name (flag/config), stamped
into run identity whenever it affects results, and implementable later without
touching consumers. One v1 implementation is fine — the seam itself is the
deliverable; the future policy is then a ticket, not a refactor.
