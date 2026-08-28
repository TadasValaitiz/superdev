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
