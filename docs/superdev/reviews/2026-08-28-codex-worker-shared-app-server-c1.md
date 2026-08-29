# Shared App-Server Checkpoint C1 Review

Checkpoint C1 remains open until Task 2 adds the private WebSocket connection, public
gateway, listener collision evidence, and the independently reviewed combined gate. This
file accumulates the rerunnable foundations without presenting an implementer's report as
independent review.

## Task 1 foundation — global domain and lossless migration

**Implementation state:** complete on 2026-08-28. The singleton path derivation contains no
Claude/session selector; strict frozen models cover service config, attach projection,
legacy candidates/conflicts, source outcomes, and migration status. Listener validation
preserves accepted `ws://HOST:PORT` bytes and rejects non-connectable/publicly unsupported
forms.

The D20 migrator verifies owner-only legacy instance metadata, registries, callback stores,
and referenced artifacts without hardening or rewriting them. It plans the complete merge,
quarantines divergent names and callback key mismatches, projects legacy callback workers to
the global compatibility identity, and commits artifacts → registry → callback store → ledger.
First-publication writers do not create an empty authority before atomic replacement. Missing
ledger prefixes are rebuilt from untouched sources.

The sanitized `status-checker-abc` fixture contains two distinct wrapper session IDs and
Codex thread IDs. It contains no measured user paths, prompts, tokens, or callback secrets.

### TDD evidence

Initial service-domain RED:

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_service_domain.py'
ImportError: ModuleNotFoundError: No module named 'codex_worker.service_domain'
FAILED (errors=1)
```

Initial migration RED:

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_migration.py'
ImportError: ModuleNotFoundError: No module named 'codex_worker.migration'
FAILED (errors=1)
```

Self-review negative-control REDs also reproduced a valid hostname containing
`unspecified` being rejected and first-publication failures leaving an empty registry or
callback authority. The focused regression commands failed before the corresponding fixes
and pass afterward.

### GREEN evidence

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_service_domain.py'
Ran 10 tests ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_migration.py'
Ran 9 tests ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_commands.py'
Ran 10 tests ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_models_registry.py'
Ran 22 tests ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_instance.py'
Ran 36 tests ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_callback_store.py'
Ran 13 tests ... OK
```

The service-domain file contains the exact AST import-arrow and public seam-inventory guards;
they run in `test_service_domain.py`. Migration tests use real temporary files and cover unique
import, canonical duplicate deduplication, sanitized divergent-name quarantine, explicit
resolution, repeat idempotence, callback binding states, pending/written outbox records,
equal/conflicting callback keys, terminal-reference publication, unsafe paths/digests/sizes,
source byte/mode/mtime preservation, fsync, and all four ordered commit boundaries.

### Full fast gate observation

```text
$ python3 -W error::ResourceWarning -m unittest discover -q -s tests/codex-worker -p 'test_*.py'
Ran 427 tests in 44.330s
FAILED (failures=3)
```

All three failures are the measured pre-existing D19 split-version baseline in
`test_tool_package`: `.claude-plugin/plugin.json` is `8.0.0`, while six declared authorities
remain `7.10.0`. The plan assigns behavior-neutral reconciliation to Task 5 before the 8.1.0
release; Task 1 does not modify version authorities. No Task 1 behavior test failed.

**Erratum (2026-08-28):** the transcript above was the preliminary full-gate run before two
self-review negative controls were added. The final pre-commit run executed 429 tests in
45.228s and retained exactly the same three D19 baseline failures; no additional failure was
introduced.

**Erratum 2 (2026-08-28):** one further prevalidation negative control was added after that
run. The final frozen-tree run executed 430 tests in 45.074s and again retained exactly those
three D19 baseline failures.

### Review status

Implementer self-review is complete. The plan's independent adversarial C1 review and its
negative controls remain pending until Task 2 completes the other load-bearing half of C1.

## Task 2 foundation — private WebSocket transport and maintenance gateway

**Implementation state:** executor-complete on 2026-08-28; independent combined C1 review
remains pending. `CodexConnection` owns one initialized private WebSocket connection with
bounded frames/queues, correlated concurrent calls, fail-all disconnect behavior, safe approval
handling, bounded overload retry for an explicit read set, and no mutation replay. The legacy
stdio adapter and WebSocket adapter share one protocol-method implementation home.

`WebSocketGateway` binds the exact configured authority and maps each public frontend one-to-one
to a private Unix backend. Successful frames are forwarded byte-for-byte. Its shared
`ServiceMaintenanceGate` accounts already-forwarded mutations until their exact response or
bridge teardown, permits only `thread/list`, `thread/read`, `turn/interrupt`, and client
responses during drain, and rejects every other known or unknown request with typed busy.
`DrainLease` is a live, exact-gate authorization capability rather than a marker value.

`GlobalWorkerService` binds the public listener before spawning
`codex app-server --listen unix://...`, refuses pre-existing private paths without unlinking,
verifies owner-only real directories and socket ownership/mode, reports loopback/non-loopback
and unauthenticated exposure explicitly, and requires its exact live drain lease for private
termination. Public stop/restart remains deliberately deferred to Task 3.

### TDD evidence

The three initial focused tests each observed RED before their production module existed:

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_websocket_transport.py'
ImportError: ModuleNotFoundError: No module named 'codex_worker.websocket_transport'
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_websocket_gateway.py'
ImportError: ModuleNotFoundError: No module named 'codex_worker.websocket_gateway'
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_service.py'
ImportError: ModuleNotFoundError: No module named 'codex_worker.service'
```

Subsequent focused REDs reproduced backend-first disconnect stranding, symlink-target chmod,
non-loopback status omission, the real Codex `/rpc`/extension upgrade requirement, duplicate and
invalid request-ID accounting, partial cleanup after a close error, and an omitted existing-history
read. Each regression was added before its corresponding production fix. The measured Codex
diagnostic was `Missing, duplicated or incorrect header sec-websocket-extensions`; both private
connectors now use `ws://localhost/rpc` with compression disabled.

### GREEN evidence

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_websocket_transport.py'
Ran 11 tests in 0.039s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_websocket_gateway.py'
Ran 15 tests in 0.025s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_service.py'
Ran 10 tests in 0.011s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_app_server_runtime.py'
Ran 32 tests in 0.469s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_runtime.py'
Ran 7 tests in 0.006s ... OK
```

The gateway focused lane includes the generated-method equality and lazy-import AST guards. A
fresh private generation from `codex-cli 0.150.1` produced 95 methods and matched the tracked
fixture and production classifier exactly. Exhaustive drain tests attack all 95 methods plus an
unknown method, and the real collision test proves that a failed second bind leaves the first
peer connectable.

### Real-substrate and package evidence

```text
$ PYTHONPATH=skills/subagent-driven-development/scripts uv run --isolated --python 3.9 --with 'websockets>=15,<16' python <sync import fixture>
3.9.6
15.0.1
sync-client-server-ok
lazy-modules-ok

$ PYTHONPATH=... uv run --isolated --python 3.9 --with 'websockets>=15,<16' python <real Unix backend/public gateway fixture>
collision-refused
byte-equivalent-backend-response-ok
first-peer-preserved-ok

$ PYTHONPATH=... uv run --isolated --python 3.9 --with 'websockets>=15,<16' python <real GlobalWorkerService/Codex fixture>
private-owner-only-socket-ok
public-to-private-handshake-ok
model-list-nonempty-ok
drain-authorized-termination-ok

$ python3 <temporary wheel allowlist fixture invoking uv build --wheel>
wheel-allowlist-ok files=26
wheel-websockets-metadata-ok

$ bash tests/codex/test-package-codex-plugin.sh
All Codex package archive tests passed

$ python3 -m compileall -q skills/subagent-driven-development/scripts/codex_worker tests/codex-worker
$ git diff --check
# both exited 0 with no output
```

All live fixtures used ephemeral public ports and private temporary directories. No installed
service or default public listener was mutated. The live default-port and installed-package
receipts remain Task 5.

### Full fast gate observation

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
Ran 469 tests in 44.161s
FAILED (failures=3)
```

The failures are exactly the three D19 split-version tests assigned to Task 5:
`test_all_declared_versions_match_plugin_manifest`,
`test_source_cli_prefers_adjacent_pyproject_over_ambient_metadata`, and
`test_source_cli_version_matches_plugin_manifest`. No other fast-lane test failed.

### Review status

Executor self-review found no unresolved Task 2 correctness issue. The approved D18 frozen
strict-dataclass exception remains the only knowing pattern exception. This receipt records the
foundation and does not claim the plan's independent C1 approval; the controller dispatches that
fresh combined reviewer after the Task 2 commit.

## Task 2 C1 correction — settlement, authority, and boundary hardening

The first independent C1 review found one critical settlement bug and seven important boundary
issues. The executor reproduced each before changing production code and corrected them without
adding Task 3's public lifecycle/inventory behavior.

Backend bridge accounting now recognizes only valid response envelopes; an ID alone, both
result/error, explicit null method, malformed error, or invalid JSON cannot release a forwarded
mutation. Allowlisted reads also occupy the in-flight ID table, so duplicate IDs refuse before a
second forward. Strict JSON rejects non-finite values in both directions and on worker/approval
emission. Successful valid frames remain byte-equivalent.

Approval callbacks run on one bounded FIFO worker rather than the response reader, preserving
correlation and approval order with bounded close joining. Gateway readiness clears when the
serve loop exits. Directory creation rejects symlinks after entering a user-controlled path and
does not create/chmod external children, while permitting leading root-owned platform aliases.
The child environment additionally removes parent session/instance routing selectors while
preserving intended provider auth/config.

Ordinary service callers can no longer obtain the service's gate or termination method. Task 3
receives a sealed frozen private lifecycle composition capability carrying the exact gate; only a
still-live lease from that gate authorizes owned-resource termination. Public stop/restart and
authoritative inventory remain Task 3.

### Correction RED / GREEN

Focused REDs observed the exact defects: active mutation count dropped on `{\"id\":7}`, the
public maintenance gate existed, an intermediate symlink created external children, parent
session/instance variables survived, `ready` stayed true after serve exit, a blocked approval
caused `thread/read` timeout, duplicate `thread/read` IDs forwarded twice, and `NaN`/`Infinity`
were accepted or emitted.

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_websocket_transport.py'
Ran 15 tests in 0.042s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_websocket_gateway.py'
Ran 20 tests in 0.038s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_service.py'
Ran 12 tests in 0.014s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_app_server_runtime.py'
Ran 32 tests in 0.516s ... OK
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_runtime.py'
Ran 7 tests in 0.007s ... OK
```

### Real and full-gate correction evidence

```text
isolated Python 3.9.6 / websockets 15.0.1: sync-client-server-ok; lazy-modules-ok
real Unix/public gateway: collision-refused; incomplete-envelope-held-mutation-ok;
  valid-response-settled-mutation-ok; byte-equivalent-frames-ok; first-peer-preserved-ok
real Codex service: private-owner-only-socket-ok; ordinary-termination-surface-absent-ok;
  public-to-private-handshake-ok; private-lifecycle-termination-ok
generated schema: codex-cli 0.150.1; 95 methods; schema-fixture-production-set-equality-ok
wheel: wheel-allowlist-ok files=26; wheel-websockets-metadata-ok
compileall and diff-check: exit 0

$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
Ran 487 tests in 47.504s
FAILED (failures=3)
```

The only failures remain the three D19 version tests assigned to Task 5; no correction or Task 1
behavior failed. No default listener or installed/global service was mutated.

### Canon reconciliation and re-review status

The suggested raw-payload/exception redesign conflicts with the exact Task 2 interface and design
§5.2: `CodexConnection.call(method, params, timeout)` is the open, generated Codex JSON-RPC wire
adapter, while D18 governs strict frozen worker domain models and incremental compatibility. The
fixed-bind contract also deliberately propagates collision, and Task 4 owns public closed-fault
conversion. A wrapper around the same 95 heterogeneous payloads would not make them closed and
would not remove the required compatibility call.

Proposed bounded clarification for re-review: record under D18 that raw Codex protocol/gateway
boundaries retain measured JSON and internal exception contracts, and require Task 4 to convert
service failures at the public RPC/CLI edge. This executor did not silently change the decision
log. Independent C1 re-review remains pending; this correction receipt does not claim approval.

## C1 correction — Task 1 listener and enforcement guards

The public-listener validator now classifies every OS-supported numeric spelling with
`getaddrinfo(..., AI_NUMERICHOST)`, so classification cannot query DNS. It rejects any result
whose address is unspecified, including the measured `0`, `00`, `0000`, `0x0`, abbreviated and
zero-padded IPv4, and expanded IPv6 forms, while preserving exact accepted hostname, loopback,
IPv4, IPv6, and connectable numeric-alias text. The independently probed alias table requires
host `0` to classify as unspecified. A separate patched-hostname control proves the production
resolver call always carries `AI_NUMERICHOST`.

The four architecture/seam guards now share their assertion implementations with four executable
negative controls. Two temporary fixture files inject forbidden `cli`/`rpc` imports; a generated
module adds an unexpected public service seam; a generated migrator exposes unannotated methods.
All four counterexamples make the real assertion raise. They do not inspect the test module's own
source. A behavioral path regression derives equal `ServicePaths` under contradictory
`CLAUDE_CODE_SESSION_ID` and `CODEX_WORKER_INSTANCE` values.

### Correction RED / GREEN

Before the production listener change, the 17-test service-domain lane failed for all seven
OS-recognized IPv4 unspecified aliases and errored because no numeric-only resolver seam existed:

```text
Ran 17 tests in 0.014s
FAILED (failures=7, errors=1)
```

After correction:

```text
$ python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_service_domain.py'
Ran 17 tests in 0.014s ... OK
$ python3 -W error::ResourceWarning -m unittest -q \
  test_service_domain test_migration test_commands test_models_registry \
  test_instance test_callback_store
Ran 108 tests in 0.538s ... OK
$ python3 -W error::ResourceWarning -m unittest -q <four original architecture guards>
Ran 4 tests in 0.007s ... OK
$ python3 -W error::ResourceWarning -m unittest -q <four negative controls>
Ran 4 tests in 0.002s ... OK
```

### Migration Result-law re-review request

No incompatible return-shape change was made. Generic Python §4 requires Result-valued seams
(`skills/engineering-patterns/python-patterns.md:74-89`), and D18 does not explicitly waive that
law. But the Task 1 brief's published interface is exactly
`scan_and_apply() -> MigrationStatusView` and `resolve(...) -> SessionRecord`, with a direct
`.conflict_count` usage (`.superdev/sdd/task-1-brief.md:20-36`); the approved plan repeats both
contracts (`docs/superdev/plans/2026-08-28-codex-worker-shared-app-server.md:95-111`). Both brief
and plan also explicitly require `resolve_name` to *raise* `legacy_name_conflict`
(`.superdev/sdd/task-1-brief.md:41-43`; plan lines 116-118), which the existing typed registry
seam does at `skills/subagent-driven-development/scripts/codex_worker/registry.py:300-305`.
D14 selected explicit conflict refusal/resolution, and D18 selected
incremental evolution of existing dependency-light seams rather than an unrelated big-bang.

Returning `Ok | Err` from the existing names would break the approved direct types and their
consumers; a parallel wrapper family would expand this task and leave the published interface
ambiguous. This is therefore disclosed as a genuine generic-canon/task-interface conflict for
architectural re-review. Re-review should either accept the specific direct/typed-exception
legacy migration seam or amend the brief/plan and downstream contracts explicitly. This
correction preserves the single-source task interface rather than silently selecting a fork.

## C1 second correction — Task 2 response dispatch and ancestor policy

Re-review accepted the prior Task 2 technical explanations and withdrew the generic-canon
findings. D18 and the plan now record the bounded clarification: the generated Codex JSON-RPC
connection/gateway remain raw protocol adapters with typed internal errors, while strict frozen
models govern worker domain/public command seams and Task 4 owns public fault conversion.

The two remaining Important findings were reproduced before production changed. A table-driven
transport case showed that ID-bearing envelopes with `method: null`, JSON-RPC 1.0, both
`result` and `error`, or a non-object `error` could incorrectly resolve a waiter. A service case
showed that a non-sticky `0777` ancestor was accepted and a child directory was created. The RED
outputs were respectively two missing `CodexTransportError` failures plus two incorrectly raised
`CodexCallError` values, and one missing `PermissionError`.

`websocket_transport.py` now owns one strict JSON-RPC response-envelope predicate used by both
connection dispatch and gateway classification. Only a non-boolean integer/string ID, absent
method, absent-or-2.0 version, exactly one result/error, and object-shaped error can correlate or
settle. Any other ID-bearing response shape fails the transport and all call waiters; the gateway
still forwards accepted response bytes unchanged. `path_security.py` now owns the existing
owner/sticky ancestor policy, with a compatibility alias retained in `instance.py` and direct use
by Claude capture and global-service directory creation. Non-sticky group/world-writable
components are refused before creation; owner-only `0700`, root-owned sticky `/tmp`, and leading
root-owned platform aliases remain supported.

Fresh correction evidence:

```text
focused transport/gateway/service/instance/Claude lane: 102 tests in 1.278s, OK
real Python 3.9.6 / websockets 15.0.1 Unix WebSocket:
  malformed-id-envelope-failed-transport-ok; sync-client-server-ok; lazy-modules-ok
real filesystem: nonsticky-0777-ancestor-refused-ok; owner-0700-root-sticky-controls-ok
generated Codex 0.150.1 schema: 95 methods; fixture/production set equality, OK
wheel: exact 23-source-module allowlist; 27 total files; websockets metadata, OK
compileall and diff-check: exit 0
full warning-strict fast lane: 490 tests in 46.721s; exactly three D19 failures
```

The only fast-lane failures are the same version-baseline tests assigned to Task 5. The shell
archive gate passed every committed-`HEAD` archive, metadata, source-module (including
`path_security.py`), mode, reproducibility, and dirty-tree check. Independent C1 re-review of
these last two corrections remains pending; this executor receipt does not claim approval.
