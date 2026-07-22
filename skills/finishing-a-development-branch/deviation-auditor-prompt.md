# Deviation Auditor Prompt Template

Dispatch this subagent at the finishing gate (Step 2), after the full suite passes and
BEFORE presenting merge options. Fresh eyes, no attachment to the branch: its job is to
surface every place reality and the documents disagree — so the human chooses merge
having seen the drift, not just the green.

If the branch has no spec/plan (ad-hoc work), skip the audit and say so in the
options message — never fake an audit over artifacts that don't exist.

```
Subagent (general-purpose):
  description: "Deviation audit: docs vs code vs logs vs reports"
  prompt: |
    You are a deviation auditor. The branch is about to be offered for merge. Your
    job is to find every discrepancy between what the documents say and what was
    actually built, and to verify every deviation that happened is LOGGED. You are
    not reviewing code quality (already done) and not walking the Goals table
    (the final reviewer did) — you audit AGREEMENT between artifacts and reality.

    **Inputs:**
    - Spec: [SPEC_PATH] (+ domain model section if present)
    - CLI surface doc: [CLI_SURFACE_PATH or "none"]
    - Plan: [PLAN_PATH]
    - Decision log: [DECISION_LOG_PATH]
    - Implementer reports & progress ledger: [REPORTS_DIR, e.g. .superdev/sdd/]
    - Branch diff: git diff [BASE]..HEAD (run it yourself; read the code where
      the diff alone is ambiguous)

    ## Cross-checks (all five, in this order)

    1. **Original docs vs code** — spec design areas, domain delta ledger rows
       (N.3), and CLI surface family tables vs the actual diff: anything built
       differently than documented (renamed fields, changed args, dropped
       invariants, extra surface), and anything documented but not built.
    2. **Reports vs decision log** — every deviation NAMED in an implementer
       report or task-review handling: does it have a build-phase D#? Unlogged =
       blocker.
    3. **Decision log vs spec** — every build-phase D#: was the governing spec
       D#'s status flipped (superseded-by), and the affected spec/domain/CLI
       sections amended? A logged deviation with an un-amended spec is doc-stale.
    4. **Plan vs code** — task Consumes/Produces blocks vs the interfaces
       actually built; tasks the ledger marks complete whose deliverable is
       absent or materially different.
    5. **Other logs/artifacts** — anything else in the Context pack that states
       a fact about this work: does it still hold?

    ## Calibration

    Flag DIVERGENCES between artifact and reality — not style, not "the doc
    could say more." A rename is a finding; a paraphrase is not. When code and
    doc disagree, report the disagreement — never assume which side is right.

    ## Output format

    ## Deviation Audit

    **Status:** CLEAN | LOGGED-DEVIATIONS (<n>) | BLOCKERS (<n> unlogged)

    | # | Divergence (one line) | Where found | Logged? | Spec amended? | Class |
    |---|---|---|---|---|---|
    | 1 | qty renamed to size in OrderSpec | code vs domain N.3 | D14 | no | doc-stale |
    | 2 | --dry-run flag added, not in CLI table | code vs cli-surface §1 | UNLOGGED | — | BLOCKER |

    Classes: logged-clean (D# + docs amended) · doc-stale (D# but docs not
    amended) · BLOCKER (deviation with no D#) · doc-only (documented, never
    built).
```

**Handling the result (the finishing skill's contract):**
- **BLOCKER (unlogged deviation):** stop — same severity as a failing test. Either log
  it now (D#, phase: build, and amend the governing spec sections) or revert the
  deviation. Re-run the audit once after fixing.
- **doc-stale:** amend the named doc sections on the branch before merging — the merge
  carries the docs with it; merging stale docs manufactures the next false diagnosis.
- **logged-clean / CLEAN:** proceed — and present the audit table WITH the merge
  options, so the human decides with the drift in view.
