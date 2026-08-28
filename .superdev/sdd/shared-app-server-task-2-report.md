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
