# Shared App-Server Checkpoint C2 Review

Checkpoint C2 remains open until Task 4 makes the singleton broker and supervised
maintenance coordinator the only ordinary public RPC/CLI path. This file accumulates
rerunnable foundations and does not present Task 3 implementer evidence as the combined
independent C2 review.

## Task 3 foundation — authoritative reconciliation and complete activity inventory

**Implementation state:** executor-complete on 2026-08-28; combined C2 review remains
pending controller dispatch after Task 4. Every broker mutation enters Task 2's shared
maintenance gate. Status reads reconcile an attached worker thread from authoritative
`thread/read(includeTurns=true)` data; subscribed TUI turn notifications preserve exact
successor identity under delayed predecessor events and never synthesize agent messages.
RuntimeStore applies bounded in-memory duplicate suppression; the durable deterministic-ID
callback dispatcher/store remains the end-to-end exactly-once guarantee.

`WorkerBroker.turn_history` is the Task 3 consume seam for Task 4: it reconciles attached
runtime through authoritative `thread/read(includeTurns=true)` before returning the strict
provider history page, exact worker/thread identities, and `AttachView`.

The maintenance inventory pages strict `thread/list` responses with `sourceKinds: []`,
deduplicates thread IDs, maps registry-backed workers, retains unknown active threads as
`origin: unmapped_tui`, and turns malformed pages, cursor loops, registry errors, and
upstream errors into fail-closed faults. `MaintenanceCoordinator` acquires a live drain
lease, inventories immediately, refuses any active row without force, and passes that same
live lease to the private lifecycle termination capability. It exposes neither the gate nor
termination capability as an ordinary public method.

Every worker-bearing broker success now carries an exact public-listener `AttachView`.
Post-upstream registry faults retain session/thread/turn identities and the same shell-safe
attach/resume routes.

### TDD evidence

Initial focused REDs were observed before production changes:

```text
test_broker.py              ImportError: MaintenanceCoordinator was absent
test_runtime.py             delayed predecessor completion erased the successor;
                            delayed start resurrected a terminal turn;
                            RuntimeStore.reconcile_thread was absent
test_projection.py          build_attach_view was absent
partial-fault assertions    attach metadata was absent
```

The callback duplicate-terminal characterization was already GREEN through the existing
durable callback dispatcher/store seam; RuntimeStore now also suppresses duplicate terminal
observer publication. A broader regression exposed a legacy fake that deliberately reuses
`turn-1`: the first dedup implementation left its explicit second active lifecycle waiting.
A focused RED captured that state, and the fix distinguishes a duplicate terminal from an
explicitly active lifecycle while still publishing the terminal callback only once per ID.

### GREEN evidence

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

Coverage includes response-before-notification, TUI follow-up, delayed/out-of-order
predecessor and successor turns, expected-turn steer/interrupt races, reconnect status
reconciliation, bounded authoritative items, no synthetic agent messages, duplicate
terminal callbacks, strict cursor pagination, inventory error/cursor/malformed refusal,
all broker mutations during drain, unmapped TUI impact, no-force stop/restart refusal,
force termination under the exact live lease, partial-fault identities, detached-session
preservation, and shell-safe attach projection.

### Structural and full-gate evidence

```text
$ python3 -W error::ResourceWarning -m unittest -q \
    test_service_domain.ServiceDomainArchitectureGuards \
    test_websocket_transport.WebSocketTransportTests.test_websockets_dependency_import_is_lazy_with_negative_control \
    test_websocket_gateway.GatewayTests.test_websockets_server_import_is_lazy_ast_guard
Ran 10 tests in 0.014s — OK

$ python3 -W error::ResourceWarning -m unittest discover -q \
    -s tests/codex-worker -p 'test_*.py'
Ran 510 tests in 42.787s
FAILED (failures=3)
```

The only failures are the three plan-assigned D19 split-version assertions:
`test_all_declared_versions_match_plugin_manifest`,
`test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata`, and
`test_source_cli_version_matches_plugin_manifest`. No Task 3 behavioral, safety,
architecture, or resource-warning test failed.

`python3 -m compileall -q skills/subagent-driven-development/scripts/codex_worker
tests/codex-worker` and `git diff --check` both exit 0.

### Foundation scope and review status

This foundation supports AH6 with exact-gate active refusal and durable-state-preserved
maintenance results; AH8 with complete force/no-force impact including `unmapped_tui`; and
AH9 with callback metadata independence and exactly-once terminal dispatch under TUI
reconciliation. Task 4 still owns public CLI/RPC lifecycle composition and the remaining C2
AH1/AH3/AH4 foundations. Task 5 owns real two-client, live replacement, composed callback,
and supervised checkride receipts. Combined independent C2 review is not claimed here.
