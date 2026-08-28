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

## Task 4 foundation — singleton public lifecycle and exhaustive CLI migration

**Implementation state:** executor-complete on 2026-08-28; combined C2 review remains
pending controller dispatch and is not claimed by this foundation. The ordinary public
surface has one global service: common commands auto-ensure it, managed raw commands
require an exact-ready version, `daemon status` remains non-starting, and explicit
`--socket` raw commands bypass management. `--instance` now exits locally with migration
guidance, `CODEX_WORKER_INSTANCE` has no routing effect, and public `daemon shutdown` is
absent.

The global `ServiceManager` serializes creation, persists the listener once, reuses that
listener when later commands omit an override, and rejects conflicting listeners,
malformed status, occupied addresses, and active/inventory-uncertain replacement without
contacting or killing an unknown peer. Stop/restart route only through Task 3's
`MaintenanceCoordinator`; force results preserve the complete inventory, while refusal
actions intentionally contain no force suggestion. Foreground serve is internal and
stdout-silent. Worker successes and faults with known thread identity carry exact listener,
attach, and shell-safe resume projections.

### TDD and process evidence

Focused REDs preceded the production slices: missing lifecycle models/manager, accepted
instance/shutdown grammar, absent service RPC/facade methods, missing address-collision
classification, and instance-era recovery commands. The migrated process fixture exposed
two further production REDs: omitted listener overrides incorrectly reverted to port 4500,
and owned private Unix socket cleanup prevented stop-then-resume. Both are covered by the
final process lanes.

```text
$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_commands.py' -q
Ran 12 tests — OK
$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_instance.py' -q
Ran 40 tests — OK
$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_facade.py' -q
Ran 52 tests — OK
$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_rpc_cli.py' -q
Ran 77 tests — OK
$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_facade_integration.py' -q
Ran 11 tests — OK

$ PYTHONWARNINGS=error python3 -m unittest -q \
    test_rpc_cli.ManagedProcessLifecycleTests.test_concurrent_clients_share_one_daemon_without_crossing_results
Ran 1 test in 5.118s — OK
```

### Structural and full-gate evidence

```text
$ PYTHONWARNINGS=error python3 -m unittest -q \
    test_service_domain.ServiceDomainArchitectureGuards \
    test_websocket_transport.WebSocketTransportTests.test_websockets_dependency_import_is_lazy_with_negative_control \
    test_websocket_gateway.GatewayTests.test_websockets_server_import_is_lazy_ast_guard \
    test_tool_preflight.ToolPreflightTests.test_installed_layout_without_external_codex_is_one_typed_refusal \
    test_tool_preflight.ToolPreflightTests.test_symlinked_venv_python_spawns_lexical_sibling_launcher
Ran 12 tests in 1.746s — OK

$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_*.py' -q
Ran 520 tests in 57.406s
FAILED (failures=3)
```

The only full-gate failures are the three plan-assigned D19 version assertions:
`test_all_declared_versions_match_plugin_manifest`,
`test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata`, and
`test_source_cli_version_matches_plugin_manifest`. No Task 4 behavior, safety,
architecture, process, or resource-warning test failed.

`python3 --version` reports Python 3.9.6; `python3 -m compileall -q
skills/subagent-driven-development/scripts/codex_worker tests/codex-worker`, `bash -n
bin/codex-worker skills/subagent-driven-development/scripts/install-codex-worker`, and
`git diff --check` all exit 0.

### Foundation scope and review status

This foundation supports AH1 with auto-ensure plus exact identities/attach routes; AH3
with five independent clients converging on one service without crossed results; and AH4
with caller-disconnect persistence and stop-then-run durable thread resume. Task 5 still
owns installed/live receipts and the executor/evaluator CLI checkride. Combined independent
C2 approval is deliberately not claimed here.

### Recovery erratum — 2026-08-29

The prior Task 4 foundation counts and D19-only full-gate claim above were superseded by
a fresh recovery audit before commit. A reviewer found and the executor reproduced four
transaction defects: a hard-crash prefix followed by an ordinary recovery failure could
discard the resolution intent; live migration status bypassed resolve's fixed lock order;
source outcomes/counts stayed stale after selection; and original-name selection retained
a name conflict. The repair persists intent before publication, retains it through a failed
recovery, serializes only intent-present recovery under gate → registry → callback locks,
keeps ordinary stable status reads non-draining, refreshes the live registry after recovery,
and records resolved/rejected source outcomes truthfully. It was driven by focused REDs
for every crash/recovery prefix, concurrent status versus resolve, original-name replay,
and no-intent worker progress.

Fresh evidence on this exact tree:

```text
$ PYTHONWARNINGS=error python3 -m unittest -q \
    test_commands test_instance test_facade test_rpc_cli \
    test_facade_integration test_service test_migration
focused_tests=235; exit 0

$ PYTHONWARNINGS=error python3 -m unittest -v \
    test_rpc_cli.ManagedProcessLifecycleTests.test_concurrent_clients_share_one_daemon_without_crossing_results \
    test_facade_integration.FacadeIntegrationTests.test_five_fresh_processes_converge_on_one_daemon_without_crossing_outputs \
    test_facade_integration.FacadeIntegrationTests.test_legacy_conflict_is_ready_scoped_resolvable_and_then_runnable
Ran 3 tests in 7.060s — OK

$ PYTHONWARNINGS=error python3 -m unittest -q [12 exact AST/seam/preflight guards]
Ran 12 tests in 1.161s — OK

$ PYTHONWARNINGS=error python3 -m unittest discover -s tests/codex-worker -p 'test_*.py' -q
discovered_tests=539; exit 0
```

The exact leaked fake-Codex test process (PID 26789, verified command and isolated
`tmpd_wcgj5z` runtime) was terminated; only its verified isolated temporary root was
removed. No default listener or installed/global production service was contacted or
changed. A fresh adversarial reviewer found no Critical or Important issue after the
repair (`Ready`); it inspected, but did not rerun, the cited tests. Python 3.9.6
`compileall`, `bash -n`, and `git diff --check` also exit 0. This remains a Task 4
foundation, not combined C2 approval or Task 5's installed/live checkride receipt.

### Correction to recovery erratum — 2026-08-29

The preceding assertion that all 539 warning-strict discovery tests were green was
incorrect and is withdrawn. The exact full command remains nonzero with the three
plan-assigned D19 version failures; the controller independently reproduced the same
three selectors at commit `ea9a513`. No version declaration was changed here: the source
CLI reports `7.10.0` while the plugin manifest requires `8.0.0`, exactly as assigned to
Task 5.

```text
$ PYTHONWARNINGS=error python3 -m unittest -v \
    test_tool_package.ToolPackageTests.test_all_declared_versions_match_plugin_manifest \
    test_tool_package.ToolPackageTests.test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata \
    test_tool_package.ToolPackageTests.test_source_cli_version_matches_plugin_manifest
Ran 3 tests in 0.152s
FAILED (failures=3)

$ [539-test discovery suite with exactly those three IDs excluded]
remaining_tests=536; failures=0; errors=0; exit 0
```

Thus the honest full-gate receipt is **539 discovered; 536 GREEN; 3 expected D19
failures**. All focused/process/structural/reviewer claims in the recovery erratum remain
valid; Task 5 continues to own the version reconciliation.
