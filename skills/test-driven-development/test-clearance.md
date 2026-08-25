# Test clearance — what happens to old tests under a domain shift

Governs REPLACE/RESHAPE territory (map verdicts — superdev:system-design `map-and-markers.md`).
The disposition is set at the item BRAINSTORM, per touched area; the plan refines mechanics
only, never reverses it.

## The four dispositions

| disposition | when | what happens |
|---|---|---|
| **keep** | the domain under the tests survives | tests stay; normal TDD discipline |
| **regenerate** | mechanical/golden-pin scaffolding over a stable behaviour | delete and regenerate from the generator after the change; never hand-maintain pins |
| **archive-then-rewrite** | the domain is being replaced; the tests encode requirements worth keeping | the lifecycle below |
| **fix-in-place** | small surface change; tests are cheap to update | update alongside the code |

## The archive lifecycle (archive-then-rewrite)

1. **The sweep is the arc's FIRST plan checkpoint.** Affected tests move to
   `tests/_archived/<plan>/` with a **manifest** (what moved, from where, why) and a
   **harvest file** — the business requirements extracted from the tests, written BEFORE
   anything is archived.
2. **The reviewer signs the harvest before anything is archived.** An unsigned harvest
   blocks the sweep — requirements captured by the same mind that wants the tests gone
   need a second reader.
3. **During development** the archive is a recall buffer: any archived test can be pulled
   back when a question needs it.
4. **Rewrite against the vision:** new tests are authored from the harvest file and the
   area's vision doc (`design/visions/`), never from the old implementation. The REVIEWER
   authors the requirement tests (it is the adversary — D38); the implementer makes them pass.
5. **Post-development cleanup is a close-gate item:** archived tests are DELETED; the
   manifest is kept for the record. The archive is a development-time buffer, not a museum.

## The inert-guard rule

A guard that has never been observed to fail is not a guard. The reviewer breaks the
guarded property and watches the red at each checkpoint — tooling this (a helper that
refuses a guard until a failure was observed) is welcome; the duty stands either way.

## Markers

Deferred test debt is `# MIG-MARK[TEST][D#]: …` — removed with the fix, never resolved in
place; the census counts it (superdev:system-design `map-and-markers.md#census`).
