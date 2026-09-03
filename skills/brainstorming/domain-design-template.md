# Domain model companion template — what exists, and what makes it authoritative

REQUIRED as a SEPARATE companion file — `YYYY-MM-DD-<topic>-domain-model.md`, next to the
design doc — whenever the work adds, removes, or reshapes domain objects, their fields,
relationships, identities, or invariants. (It was a design-doc section until 2026-09-03;
measured on a real item, the section form grew past 600 lines because this is where the
invariants live. A companion keeps the anchor readable and stays live through the build.)
Its job is two things at once: **discrepancy hunting** — laying the whole domain out in one
place surfaces the same concept under two names, two commands persisting one field
differently, an invariant nobody enforces — and **invariant ownership**: every invariant
gets an `I#`, an enforcer, and, at plan time, an owning task. CLI Command models (Pydantic
request models — the Command pattern) ARE domain objects and belong here; that is how
discrepancies between commands become visible as model diffs.

Written in Pass 2 (SKILL.md step 8b) and **updated after every ruling that touches a
shape** — "the companion now exists; I'll keep updating it after each ruling" is the tempo.
Sketches are FLEXIBLE by default (responsibilities and invariants, never final field
names) unless a ruling LOCKs a shape; label each with its status and D#.

```markdown
# <Topic> — Domain model (status: draft | ratified <who, when>)

**Design doc:** ./YYYY-MM-DD-<topic>-design.md · **Decision log:** ./…-decisions.md ·
**Pipelines:** ./…-pipelines.md (if any) · **CLI surface:** ./…-cli-surface.md (if any)
**Governed by:** D#…

## 1. Domain boundary

What this domain OWNS; what it CONSUMES from neighbours (each neighbour named, with the
exact seam); what it must NEVER own or recreate (the duplicate-authority fences).

## 2. Aggregate model

One mermaid classDiagram of every object this work touches — existing-and-kept, changed,
and new — stereotyped by role, identity marked:

    ```mermaid
    classDiagram
      class OrderSpec {
        <<value object — identity: hashes>>
        symbol: str
        qty: Decimal
      }
      class PlaceOrderCommand {
        <<CLI command model — st order place>>
        spec: OrderSpec
        dry_run: bool  (non-identity)
      }
      PlaceOrderCommand --> OrderSpec
    ```

Then the ownership table:

| Object | Role | Identity | Status (D#) |
|---|---|---|---|
| `OrderSpec` | value object | content hash of (symbol, qty, tif) | LOCKED (D#) |

If the diagram is too big to read, the design is too big for one spec — a finding.

## 3. Objects

One subsection per object, in dependency order:

### `<Object>` — LOCKED | DERIVED | FLEXIBLE (D#)

    ```python
    class <Object>(FrozenModel):
        field: Type          # unit · identity? · what it means
    ```

**This means:** one or two lines a reader can rely on (what may never change once
created, what is derived, what it is NOT).

## 4. Naming & field conventions — and the DISCREPANCY TABLE

The conventions this domain obeys (casing, unit suffixes, id/ref/hash naming, tense of
booleans) — and every place the same concept appears under different names, or the same
name means different things, across domain objects AND CLI command models:

| Concept | Appears as | Where | Resolution (D#) |
|---|---|---|---|
| <concept> | `qty` vs `quantity` vs `size` | OrderSpec / st order place / ledger row | D# — converge on `qty` |

An empty table means you looked and found none — say so. Never skip the hunt.

## 5. The delta ledger — what this work adds and removes

| Change | Object.field / invariant | Before | After | Why (D#) |
|---|---|---|---|---|
| ADD / REMOVE / RENAME / RETYPE | … | … | … | D# |
| INVARIANT-ADD / INVARIANT-REMOVE | I# | (not enforced) | enforced by <enforcer> | D# |

## 6. Identity and comparison invariants

Which fields are identity and which are annotations, per object; what two objects may
never be compared as equal silently (different scopes, bases, windows, versions); what a
reference spelling is and what resolution is forbidden (bare / latest). Each is an `I#`
row in §7.

## 7. Invariants and enforcers

| I# | Invariant (one sentence) | Enforcer | Owning task (plan fills) | Status |
|---|---|---|---|---|
| I1 | <what must hold> | frozen type / validator / transaction / import guard / test | Task N | LOCKED (D#) |

**An invariant with no enforcer is a wish** — mark it `GAP` here and the plan gives it a
task; the plan reviewer BLOCKS on an I# with no owning task. Include the identity test
that fails when a new field lands unclassified.

## 8. Transitions summary

Which pipelines create, append to, and terminate each object — one row per object,
pointing at the pipelines companion's P#.n steps. (The pipelines companion carries the
mechanics; this table is the cross-reference that catches an object no pipeline creates,
or a mutation no pipeline owns.)

## 9. CLI ↔ domain mapping

Every CLI command touched, its Pydantic Command model, the domain objects it consumes and
produces — one row each. Must agree with the CLI surface doc's family tables; a mismatch
is a spec bug to fix before planning.

## 10. Deferred and flexible field ledger

What is intentionally undecided — each with the ruling that will decide it and the
session/item that owns it. Bare "later" is a finding.
```

**Downstream use:** the plan's Context pack lists this file; every task that touches a
domain object carries `Invariants preserved: I# → enforcer → test in this task`
(writing-plans task structure); the implementer's Read-first quotes those rows and the
delta-ledger rows; the task reviewer checks each claimed I#'s enforcer is present and
tested; the §10 drift protocol updates THIS file first when a build-time deviation touches
the domain — never only the code.
