# Angle 4 — Persistence wins over cleanup and silent migration

**Purpose:** Understand how upgrades, dangerous stops, and legacy per-instance state preserve active and durable work.
**Authority:** teaches ruled design — the decision log is the law.
**Formal anchors:** [decision log](./2026-08-28-codex-worker-shared-app-server-decisions.md) D8, D10, D14 · [design §5.6](./2026-08-28-codex-worker-shared-app-server-design.md)
**Series:** 4 of 4

> **Status guide:** LOCKED operator-ruled · MISMATCH current code behaves differently today · FLEXIBLE implementation detail may move inside the ruled boundary · DEFERRED explicitly owned by another design.

## The central question

How does a permanent shared service change cleanup, upgrades, and migration from old per-instance registries?

## The mental model

The global service is a library with checked-out books: routine callers may enter and leave,
but closing the building or rewriting the catalogue requires an inventory and an explicit
maintenance act.

It is not:

- a disposable test process stopped in every `finally` block;
- safe to restart merely because one Claude session ended;
- allowed to interrupt work to match a newly installed binary;
- a migration that picks one duplicate name arbitrarily;
- permission to delete old registries after import.

## Boundaries

This angle owns runtime maintenance and durable state transition. Angle 1 owns normal service
startup, Angle 2 owns live control, and Angle 3 owns the resulting global names. Production
rolling upgrades and mixed-version fleets are outside this internal tool.

## Concrete journey

### LOCKED — stop and restart are supervised maintenance

Normal skill completion leaves the service running. `daemon stop` and `daemon restart` first
inventory active turns and refuse with `service_busy`. `--force` is available only as a loud,
human-supervised override and enumerates affected worker identities before termination.

**This means:** callbacks, caller exits and test cleanup cannot accidentally terminate someone
else's work; the skill documents stop as dangerous; and the service remains immediately usable
between Claude sessions.

### LOCKED — version replacement is automatic only while idle

The daemon stamps its loaded version once. A new client compares that immutable value. If no
turn is active, it restarts the global runtime and preserves durable state; otherwise it refuses
replacement. **This means:** old code cannot masquerade as new after an in-place UV reinstall,
and active work is never sacrificed for convenience.

### LOCKED — legacy names migrate without guessing

First global startup scans every known per-instance registry. Unique names import. Identical
records deduplicate. A name pointing at different thread/session identities becomes a durable
conflict containing every source. `migration resolve` selects one thread explicitly while
preserving the other source records.

**This means:** existing conversations remain recoverable; automation cannot address an
ambiguous name; and an operator can audit the exact choice later.

### FLEXIBLE — ledgers may evolve while preservation stays fixed

The migration ledger schema and archival layout may change with versioned readers. **This
means:** storage can be hardened without weakening no-deletion, deterministic import or explicit
resolution.

## What lifecycle management cannot do

It cannot guarantee uninterrupted upgrade during an active turn, merge divergent legacy
conversations, reclaim an arbitrary occupied port, or make forced termination non-destructive.
It also cannot promise old multi-instance CLI behavior after migration.

## Current mismatch

Today the skill and harness often stop their selected runtime during cleanup, version checks
are instance-local, and legacy state remains partitioned. **SALVAGE:** retain immutable version
stamping, fail-closed readiness, atomic/fsynced registries, safe socket ownership checks and
durable stop semantics.

## Visible collisions

- Immediate upgrade versus active work: preservation wins; retry after turns finish.
- Global uniqueness versus legacy duplication: quarantine and explicit resolution preserve truth.

## Flexible and deferred

**FLEXIBLE:** migration ledger encoding, archival directory names, and maintenance diagnostics.
**DEFERRED, with landing places:** zero-downtime rolling upgrade belongs to a future production-service design only if this internal tool gains that requirement.

## Reconciled outcome

Three LOCKED preservation rules and one FLEXIBLE storage seam make permanence operational:
ordinary work never cleans up the service, upgrades wait for idleness, and migration never lies.
