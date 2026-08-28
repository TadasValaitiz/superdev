# Shared App-Server Task 2 Report

## Status

Implemented the private Codex WebSocket connection, fixed public WebSocket gateway, shared
maintenance gate/capability, and composed global service. Independent combined C1 review is
intentionally pending controller dispatch.

## Implementation

- Added `CodexConnection`: lazy websockets sync imports, `/rpc` Unix upgrade without compression,
  one initialize/initialized handshake, bounded frames/queue, concurrent response correlation,
  safe approval handling, fail-all disconnect behavior, bounded explicit-read overload retries,
  and zero mutation replay.
- Lifted the existing Codex convenience methods and child-environment scrubber into one shared
  protocol-independent home while preserving `CodexAppServer` compatibility exports.
- Added `ServiceMaintenanceGate` and live exact-gate `DrainLease` authorization. Drain waits for
  forwarded mutations, blocks new mutations, and allows only `thread/list`, `thread/read`,
  `turn/interrupt`, and client responses.
- Added a byte-preserving one-frontend/one-backend `WebSocketGateway`, typed busy responses,
  duplicate/invalid-ID refusal, exact listener binding, and disconnect cleanup.
- Added `GlobalWorkerService`: public bind before child spawn, private owner-only Unix socket
  verification, explicit exposure/authentication status, rollback, best-effort owned-resource
  cleanup, and lease-guarded private termination. Public stop/restart is absent by design and is
  deferred to Task 3.
- Added the generated Codex 0.150.1 fixture with all 95 client request methods and pinned
  `websockets>=15,<16` in the isolated worker package.

## Exact RED / GREEN

Initial warning-strict focused runs for `test_websocket_transport.py`,
`test_websocket_gateway.py`, and `test_service.py` each failed with `ModuleNotFoundError` for
their not-yet-created production module. The package test additionally failed its new dependency
assertion before `websockets>=15,<16` was declared (alongside the three already-known D19 version
failures).

Focused regression REDs then reproduced: a stranded backend-first bridge; chmod through a
runtime-root symlink; missing non-loopback/auth status; real Codex upgrade rejection until the
measured `/rpc` URI and disabled compression were used; a fast-response/duplicate-ID race;
invalid null and boolean response IDs; incomplete resource cleanup after a close failure; and an
omitted `thread/turns/list` idempotent read. Production changed only after each RED.

Final focused GREEN:

```text
test_websocket_transport.py  11 tests in 0.039s  OK
test_websocket_gateway.py    15 tests in 0.025s  OK
test_service.py              10 tests in 0.011s  OK
test_app_server_runtime.py   32 tests in 0.469s  OK
test_runtime.py               7 tests in 0.006s  OK
```

## Verification

- Generated schema guard: `codex-cli 0.150.1`; 95 generated request methods; generated fixture,
  tracked fixture, and production set exactly equal. The focused gateway lane also passes the
  classifier and lazy-import AST guards.
- Isolated Python 3.9: Python 3.9.6, websockets 15.0.1, sync client/server imports and all three
  source modules pass.
- Real gateway: private Unix backend plus public WebSocket; fixed collision refused, first peer
  preserved, successful backend response byte-equivalent.
- Real Codex/service: owner-only private socket, public-to-private initialize/model-list, and
  exact-gate drain-authorized termination pass on an ephemeral listener.
- Wheel: exact source-module allowlist passes with 26 entries; dependency metadata present.
- Warning-strict full fast lane: 469 tests in 44.161s; only the three declared D19 split-version
  failures remain. Their exact names are `test_all_declared_versions_match_plugin_manifest`,
  `test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata`, and
  `test_source_cli_version_matches_plugin_manifest`.
- Shell package archive gate: `bash tests/codex/test-package-codex-plugin.sh` passed every archive,
  metadata, module-allowlist, mode, reproducibility, source-format, and dirty-tree check against
  the Task 2 commit.
- `python3 -m compileall -q skills/subagent-driven-development/scripts/codex_worker
  tests/codex-worker` and `git diff --check` passed.

## Files

Production: `app_server.py`, `runtime.py`, `service.py`, `websocket_gateway.py`,
`websocket_transport.py`, and worker `pyproject.toml`. Tests: `test_app_server_runtime.py`,
`test_runtime.py`, `test_service.py`, `test_tool_package.py`, `test_websocket_gateway.py`,
`test_websocket_transport.py`, and the generated 0.150.1 fixture. Documentation: this report,
the accumulating C1 receipt, and AH5/AH11 foundation receipts in the design.

The pre-existing `.superdev/sdd/progress.md` modification was preserved and excluded from this
task commit.

## Self-review, concerns, and deviations

Self-review verified exact listener collision behavior, no fallback/kill/unlink/trust path,
one-to-one backends, response-byte preservation, all-known-plus-unknown drain classification,
settled mutation accounting, capability ownership/liveness, no replay of mutations, private
socket ownership/mode, exposure projection, best-effort cleanup, and lazy package seams.

Concerns are limited to scheduled follow-on work: independent combined C1 review is pending;
public lifecycle/inventory belongs to Task 3; installed/default-port proof and the three D19
version reconciliations belong to Task 5. No global service or default listener was mutated.

Knowing engineering-pattern departures: none beyond the plan-approved D18 frozen strict-dataclass
exception for this legacy package.

## C1 correction pass

### Findings addressed

- Backend mutation accounting now releases only for a structurally valid response: method absent,
  valid integer/string ID, exactly one of result/error, object-shaped error when present, and
  `jsonrpc == "2.0"` when a version is present. Incomplete, ambiguous, null-method, and malformed
  error envelopes remain byte-preserving but do not settle; bridge teardown remains the fallback.
- The ordinary `GlobalWorkerService` surface no longer exposes its maintenance gate or termination.
  A sealed, frozen `_ServiceLifecycle` capability is available only through the private Task 3
  composition seam; it carries the exact gate and accepts only that gate's still-live lease.
- Directory creation walks every component, refuses user-controlled symlink ancestors before
  creating or chmodding external children, validates created ownership, and tolerates only leading
  root-owned platform aliases such as macOS `/var -> /private/var`.
- The singleton Codex child now removes `CLAUDE_CODE_SESSION_ID` and `CODEX_WORKER_INSTANCE` in
  addition to the two Claude messaging credentials, while retaining provider authentication and
  configuration such as `OPENAI_API_KEY` and `CODEX_HOME`.
- Gateway readiness clears in the server-loop `finally` path.
- Approval work moved from the sole response reader to one bounded FIFO worker. Responses remain
  correlated while a handler blocks; queued approvals preserve order; close joins are bounded.
- Allowlisted reads now occupy the same in-flight ID table as mutations, so duplicate IDs refuse
  before the second forward and clear only on a valid response or teardown.
- WebSocket parsing rejects `NaN`/`Infinity` in both directions. Worker emissions use
  `allow_nan=False`; non-finite request/approval data is never serialized, and invalid backend
  JSON closes the bridge without forwarding.

### Watched RED and focused GREEN

Each correction was driven by a focused failing test before production changed:

```text
incomplete_or_ambiguous_backend_envelope...  RED: active_mutations was 0, expected 1
ordinary_service_surface...                  RED: public maintenance_gate still present
intermediate_symlink...                      RED: PermissionError not raised
scrubs_parent_identity...                    RED: CLAUDE_CODE_SESSION_ID still inherited
ready_clears...                              RED: ready remained true past deadline
blocked_approval_handler...                  RED: thread/read timed out
duplicate_inflight_allowlisted...            RED: duplicate request forwarded twice
non_finite_outbound/inbound/frontend/backend/approval
                                               RED: values serialized, accepted, or forwarded
```

The first no-follow directory implementation exposed macOS's root-owned `/var` alias in the full
service test; the final traversal distinguishes leading platform aliases from symlinks beneath a
user-owned boundary. Final warning-strict focused evidence:

```text
test_websocket_transport.py  15 tests in 0.042s  OK
test_websocket_gateway.py    20 tests in 0.038s  OK
test_service.py              12 tests in 0.014s  OK
test_app_server_runtime.py   32 tests in 0.516s  OK
test_runtime.py               7 tests in 0.007s  OK
```

### Correction verification

```text
isolated Python: 3.9.6 / websockets 15.0.1 / sync-client-server-ok / lazy-modules-ok
real gateway: collision-refused / incomplete-envelope-held-mutation-ok /
              valid-response-settled-mutation-ok / byte-equivalent-frames-ok /
              first-peer-preserved-ok
real Codex service: private-owner-only-socket-ok /
                    ordinary-termination-surface-absent-ok /
                    public-to-private-handshake-ok / private-lifecycle-termination-ok
schema: codex-cli 0.150.1 / generated-request-methods=95 /
        schema-fixture-production-set-equality-ok
wheel: wheel-allowlist-ok files=26 / wheel-websockets-metadata-ok
shell package archive gate: all checks passed against the correction commit
compileall + diff-check: exit 0
full warning-strict fast lane: 487 tests in 47.504s; exactly the three assigned D19 failures
```

### Generic-canon review response

The review's `Dict[str, Any]` and raised-error comments were evaluated but not applied as an
interface redesign. Design §5.2 explicitly fixes `CodexConnection.call(method, params, timeout)`
as the raw heterogeneous Codex JSON-RPC adapter, and the Task 2 brief repeats that exact consumed
interface. Its dictionaries are protocol frames generated from 95 upstream request variants, not
worker domain/service records; wrapping the same open payload in a generic model would add no
closed-field guarantee and would leave the required compatibility call intact.

Likewise, this task's fixed-bind contract requires the low-level bind exception to propagate with
no fallback/peer action, and the existing adapter contract uses `CodexCallError` /
`CodexTransportError`. Replacing those internal protocol exceptions with a new `Result` family
would break the approved compatibility seam before Task 4 performs public RPC/CLI fault mapping.
D18 explicitly chooses incremental strict frozen dataclasses for domain models and exact
compatibility re-exports while this topology changes.

For re-review, the bounded decision proposal is to clarify D18 (without changing behavior) that
raw Codex protocol/gateway boundaries retain their measured open JSON and exception contracts,
while Task 4 must convert service failures into the existing closed public RPC/CLI fault model.
No new decision was silently added by this executor.

### Remaining review status

The correction pass is executor-complete. Independent C1 re-review remains required; this report
does not claim approval. The only expected fast-lane failures remain the three D19 version tests
owned by Task 5.
