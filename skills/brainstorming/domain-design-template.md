# Domain Design Section Template

REQUIRED inside the design doc (as its own numbered section) whenever the work adds,
removes, or reshapes domain objects, their fields, or their relationships. Its job is
**discrepancy hunting**: laying the whole domain out in one place is what surfaces the
gaps a section-by-section read hides — the same concept under two names, two commands
persisting the same field differently, an invariant nobody enforces. CLI Command
models (Pydantic request models — the Command pattern) ARE domain objects and belong
in this section; that is how discrepancies between CLI commands become visible as
model diffs.

```markdown
## §N. Domain model

### N.1 The diagram

One mermaid classDiagram of every object this work touches — existing-and-kept,
changed, and new. Stereotype each class with its role, and mark identity explicitly:

    ```mermaid
    classDiagram
      class OrderSpec {
        <<value object — identity: hashes>>
        symbol: str
        qty: Decimal
        tif: TimeInForce
      }
      class PlaceOrderCommand {
        <<CLI command model — st order place>>
        spec: OrderSpec
        dry_run: bool  (non-identity)
      }
      PlaceOrderCommand --> OrderSpec
    ```

Relationships drawn, not implied. If the diagram is getting too big to read, the
design is too big for one spec — that is a finding, not a formatting problem.

### N.2 Naming & field conventions

The conventions this domain obeys (casing, unit suffixes, id/ref/hash naming,
tense of booleans) — and the DISCREPANCY TABLE: every place the same concept
appears under different names, or the same name means different things, across
domain objects AND across CLI command models:

| Concept | Appears as | Where | Resolution (D#) |
|---|---|---|---|
| <concept> | `qty` vs `quantity` vs `size` | OrderSpec / st order place / ledger row | D# — converge on `qty` |

An empty table means you looked and found none — say so explicitly. Never skip
the hunt; this table is the section's reason to exist.

### N.3 The delta ledger — what this work adds and removes

Explicit before → after, one row per change. "The domain after" without "the
domain before" hides exactly the drift this section exists to catch:

| Change | Object.field / invariant | Before | After | Why (D#) |
|---|---|---|---|---|
| ADD / REMOVE / RENAME / RETYPE | … | … | … | D# |
| INVARIANT-ADD / INVARIANT-REMOVE | … | (not enforced) | enforced by <validator/test/type> | D# |

### N.4 Invariants

Every invariant that must hold, each with its ENFORCER — the validator, frozen
type, or test that makes violation impossible or red. An invariant with no
enforcer is a wish; classify it as a gap and give it a task in the plan.
Include the identity rule where objects hash: which fields are identity, which
are annotations — and the test that fails when a new field lands unclassified.

### N.5 CLI ↔ domain mapping

Every CLI command touched by this work, its Pydantic Command model, and the
domain objects it consumes/produces — one row each. This row set must agree
with the CLI surface doc's family tables; a mismatch between the two documents
is a spec bug to fix before planning.
```

**How this section gets used downstream:** writing-plans lists it in the Context pack;
tasks that touch a domain object name this section in their Read-first line; the
implementer's model changes are checked against N.3/N.4 at task review. The delta
ledger is also the drift protocol's reference point — a build-time deviation that
touches the domain updates THIS section, not just the code.
