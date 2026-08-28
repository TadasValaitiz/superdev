# Shared App-Server Task 3 Report

## Status

Implemented authoritative cross-client reconciliation, complete fail-closed global activity
inventory, exact-gate maintenance coordination, and attach identity projection. Combined C2
review is intentionally pending controller dispatch after Task 4.

## Implementation

- Wrapped session start/resume, turn start/steer/interrupt, goal set, and legacy shutdown in
  Task 2's `ServiceMaintenanceGate`; blocking read/wait paths do not enter the mutation gate.
- Reconciled attached worker status from strict authoritative
  `thread/read(includeTurns=true)` results. TUI-started turns, delayed predecessor events,
  terminal-before-response, and fast successor races preserve exact authoritative turn
  identity. Reconciliation bounds retained turn items and does not fabricate agent messages.
- Added `WorkerBroker.turn_history` as Task 4's consume seam: attached history reads first
  reconcile the runtime from authoritative thread/turn state, then return the strict provider
  page with exact worker/thread identities and attach metadata.
- Kept terminal callback publication exactly once for repeated authoritative terminal state,
  including repeated status reconciliation. Callback binding remains registry metadata; no
  callback routing uses Claude identity as worker infrastructure identity.
- Added strict frozen `ActiveThreadItem`, `ActiveInventory`, and `MaintenanceResult` domain
  models. Inventory walks every strict `thread/list(sourceKinds=[])` page, deduplicates IDs,
  maps known worker records, retains unknown active rows as `unmapped_tui`, and fails closed on
  any malformed response, cursor loop, registry failure, or upstream error.
- Added `MaintenanceCoordinator.stop(force)` / `restart(listener, force)`. It drains the exact
  shared gate, inventories immediately under the live lease, refuses every active row without
  force, and passes the same live lease only to the private lifecycle capability. The
  coordinator exposes neither the gate nor termination as an ordinary public method.
- Added shell-safe `AttachView` projection from the configured public listener and exact Codex
  thread ID. Worker-bearing broker results and post-upstream partial registry faults carry it.

## Exact RED / GREEN

Initial focused RED:

```text
test_broker.py          ImportError: MaintenanceCoordinator was absent
test_runtime.py         10 tests: delayed predecessor erased successor;
                        delayed start resurrected terminal; reconcile_thread absent
test_projection.py      ImportError: build_attach_view was absent
partial-fault tests     KeyError: details["attach"]
```

`test_callback_dispatcher.py`'s new duplicate-terminal characterization was GREEN before a
dispatcher edit: the existing dispatcher/store already provided durable exactly-once
enqueue. Runtime reconciliation was then made idempotent at its observer seam as well.

During the broader focused lane, a legacy facade fake deliberately reused literal `turn-1`.
The first terminal-dedup implementation treated its second explicit active lifecycle as a
duplicate and left an indefinite wait active. Four accidentally detached test processes were
terminated; a single verbose selector and process stack isolated the exact test. The focused
regression was RED (`active_turn_id == "reused"`, expected `None`) before the fix. Dedup now
suppresses only a terminal not currently active and retains publishing state only for a newly
published terminal. The regression plus both previously blocking facade tests ran 3 tests in
0.006s — OK.

Final focused GREEN:

```text
$ python3 -W error::ResourceWarning -m unittest -q \
    test_broker test_runtime test_projection test_callback_dispatcher \
    test_app_server_runtime.RuntimeStoreTests
Ran 115 tests in 0.499s — OK

$ python3 -W error::ResourceWarning -m unittest -q \
    test_broker test_runtime test_projection test_callback_dispatcher \
    test_app_server_runtime test_facade test_facade_integration test_rpc_cli \
    test_service test_websocket_gateway test_websocket_transport \
    test_models_registry test_service_domain
Ran 356 tests in 33.038s — OK
```

## Verification

- AST/seam guards: service-domain import/public-inventory guards plus both lazy WebSocket import
  guards ran 10 tests in 0.014s — OK.
- Warning-strict full fast lane: 510 tests in 42.787s; exactly the three declared D19
  split-version failures remain. Exact names:
  `test_all_declared_versions_match_plugin_manifest`,
  `test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata`, and
  `test_source_cli_version_matches_plugin_manifest`.
- `python3 -m compileall -q skills/subagent-driven-development/scripts/codex_worker
  tests/codex-worker` and `git diff --check` exit 0.
- No installation, default-listener bind, live-service lifecycle, or global state mutation was
  performed.

## Files and receipts

Production: `broker.py`, `runtime.py`, `models.py`, and `projection.py`. The existing
`callback_dispatcher.py` required no production change after the RED characterization proved
its exactly-once seam already satisfied the task.

Tests: `test_broker.py`, `test_runtime.py`, `test_projection.py`, and
`test_callback_dispatcher.py`. Documentation: the accumulating
`docs/superdev/reviews/2026-08-28-codex-worker-shared-app-server-c2.md`, AH6/AH8/AH9
foundation cells, and this report.

The controller-owned `.superdev/sdd/progress.md` modification was preserved and excluded from
the task commit.

## Self-review, concerns, and departures

Fresh read-only review found and drove focused RED/GREEN fixes for an unseen delayed predecessor
poisoning a pending successor identity, shallowly mutable maintenance inventory, inconsistent
maintenance states, the missing broker history consume seam, and known identities lost on
post-upstream faults. Its final audit found no Critical or Important issue.

Self-review checked every broker mutation path, exact-gate identity, drain ordering, live-lease
termination, strict all-source pagination, malformed/error/cursor fail-closed behavior,
unmapped impact, expected-turn controls, delayed notification ordering, bounded terminal/item
retention, observer deduplication, attach quoting, partial-fault IDs, and detached-session
preservation. The actual gate lock is not held across upstream calls or waits; only a mutation
lease is held, as designed by Task 2.

Remaining concerns are scheduled integration work: Task 4 must compose this broker/coordinator
through the only ordinary public façade/RPC/CLI path and remove legacy public routing; Task 5
owns live two-client, replacement, callback, and supervised checkride receipts plus D19 version
reconciliation. Combined independent C2 review is not claimed.

Known engineering-pattern departures: none beyond the plan-approved D18 bounded raw-protocol /
legacy strict-frozen-dataclass exception. `WorkerBroker` temporarily retains a default private
gate for the pre-Task-4 legacy construction seam; Task 4 must inject the singleton service gate
on the public composition path.
