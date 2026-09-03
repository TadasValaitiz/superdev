# The checkride plan — expectations before the ride

Written at PLAN time (writing-plans), as a REQUIRED section of any plan that changes a
user-facing surface. Reviewed with the plan by the plan reviewer. It is ideas and
expectations — journeys and command families — never exact commands: the ride derives each
step live, one at a time, under the evaluator's rulings.

## The section (copy into the plan)

```markdown
## Checkride plan

**Surfaces this plan changes:** ⟨command families / routes added or changed⟩
**Neighbouring surfaces the journey crosses:** ⟨families this plan does NOT change but the
operator must pass through — discovery, setup, data readiness, inspection⟩

**The operator's starting point:** ⟨what the operator has when the journey begins: an empty
store? a file they wrote? a prior result? — the ride starts THERE, never from a committed
fixture or a pre-seeded catalogue⟩

**Journeys to ride** (intent level, one row each):

| # | Operator goal | Command families crossed | What good looks like | Refusal paths that matter | Discharges |
|---|---|---|---|---|---|
| J1 | ⟨…⟩ | ⟨…⟩ | ⟨mechanisms the operator must see — never numbers⟩ | ⟨…⟩ | UC#/AH# |

**Actual data each journey needs** (the substrate law — engineering-patterns/process-discipline.md §2):

| Journey | Service / dataset | Coverage · window · universe · scale | Availability check before the ride | If unavailable |
|---|---|---|---|---|
| J1 | ⟨…⟩ | ⟨the operator's scale, from the design's use cases⟩ | ⟨the preflight command / check⟩ | STOP and ask the operator — never a stand-in |

**Expectations the evaluator judges against:** ⟨per journey: the mechanisms, provenance,
exit classes, remedies, and honesty tiers the operator must see; the operator laws in force
(e.g. "never needs source code")⟩

**Deliberately not ridden here:** ⟨journeys deferred, and which item/room rides them⟩
```

## What the plan reviewer checks

- Present whenever any task changes a user-facing surface; absent = BLOCKING.
- Starts at the operator's real starting point, not mid-journey.
- Names actual data per journey with a verifiable availability check; "the test fixture",
  "the stub", "the mock" anywhere in the data table = BLOCKING; unknown availability is
  named as a risk, never assumed.
- Crosses the neighbouring surfaces the journey needs (seams are where operators die).
- Expectations are judgeable (mechanisms, provenance, exits, remedies) and contain no
  prewritten result numbers.
- Every discharged UC#/AH# appears in a journey row.
- No literal command scripts (a script is a confirmation exercise, not a ride).
