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
