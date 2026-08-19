# Task 6 report — deterministic adversarial gate

## Scope delivered

- Added a scenario/capture seam to `tests/codex-worker/fake_codex.py`.  It accepts a
  UTF-8 JSON scenario with default and prompt-specific delays and emits owner-only
  received-method/params JSONL receipts.
- Added real installed-command subprocess coverage for five fresh callers converging
  on one daemon, per-worker cwd/thread/session/output isolation, non-destructive
  stop/restart thread recovery, and duplicate/unknown-name refusals.

## RED → GREEN evidence

The first five-process test failed first because the scenario fake did not accept the
real `codex app-server` argv.  After making that contract explicit, it exposed the
fixture's default model mismatch; the test now deliberately selects the fake's
advertised raw model.  No production behavior was changed.

## Verification

- `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade_integration.py tests/codex-worker/test_rpc_cli.py tests/codex-worker/test_live_harness_contract.py -v` — 63 passed.
- `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` — 241 passed, 1 skipped.
- `python3 -m py_compile tests/codex-worker/fake_codex.py tests/codex-worker/test_facade_integration.py` and `git diff --check` — passed.

## Fork / remaining coverage note

The existing `test_rpc_cli.py` already covers the stated raw endpoint, lock, socket,
timeout, non-finite JSON, response-ID, disconnect, signal, and §10 matrices; its
existing cases passed unchanged.  `test_live_harness_contract.py` already covers
identity/token evidence.  Accordingly this task only added the missing composed
real-process driver rather than duplicating those tests.

## Review follow-up — RED/GREEN evidence

- RED: the initial expanded five-process assertion observed `[4, 2, 3, 1, 0]`, showing
  that 20ms delay spacing was not a deterministic completion-order contract under
  concurrent startup.  GREEN: scenario-specific 100ms-separated delays and bounded
  `poll()` receipt collection now prove `[4, 3, 2, 1, 0]` independently of launch or
  `communicate()` order.
- RED: completion receipts made existing direct `row["method"]` reads fail because
  they correctly have no request method.  GREEN: request filtering is explicit via
  `row.get("method")`, preserving request assertions and adding completion timestamps.
- Added scenario controls for prompt output(s), phases, command duration, usage,
  goal failure/absence, paginated history, limits availability, malformed method
  responses, and owner-only JSONL capture of all request params.
- Added composed receipts for goal-before-turn refusal, absent goal/unavailable limits,
  schema decode/no-agent incomplete completions, and live-vs-terminal paged history.
- Focused warning-strict gate: 68 passed. Full deterministic gate: 246 passed,
  1 skipped. `py_compile` and `git diff --check` passed.

## Completion follow-up — 2026-08-19

Erratum: the earlier completion-order receipt did not first prove that all five
`turn/start` requests had reached the fake. Its delay spacing therefore still depended
on request-arrival timing, and the client `poll()` order was asserted as if it were the
completion oracle. This follow-up replaces that evidence rather than silently treating
it as sufficient.

### RED → GREEN

- RED command:
  `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade_integration.py -v`
  failed in
  `FacadeIntegrationTests.test_five_fresh_processes_converge_on_one_daemon_without_crossing_outputs`
  with `KeyError: 'seq'`. This proved the test required a capture-authoritative receipt
  sequence that the scenario fake did not yet emit.
- GREEN: `fake_codex.py` now serializes every capture row under one lock with `seq`,
  monotonic `at`, and fake process `pid`, and its five-way scenario waits on a bounded
  request-count barrier before applying prompt-specific delays. The test waits until
  capture contains five `turn/start` requests, then derives the required
  `prompt-4 ... prompt-0` / `token-4 ... token-0` order only from `kind == completion`
  rows ordered by `seq`; client exit order is merely checked for completeness.
- Root-cause correction: putting the barrier in the shared fixture made ordinary
  one-turn scenarios time out. Moving it into only the five-worker scenario restored
  isolation; the focused integration file then passed all 10 tests.

### Deterministic coverage map

- Five workers / one process family / exact upstream policy:
  `tests/codex-worker/test_facade_integration.py:46` waits for all five turn requests,
  samples five active daemon statuses, asserts one daemon PID and one Codex PID, checks
  the exact daemon socket/state command, verifies the Codex PPID and sole live child,
  and ties every capture PID to that child. Lines 114–147 assert the complete
  `initialize`, five `thread/start`, and five `turn/start` parameter objects plus the
  capture-authoritative completion order. `tests/codex-worker/fake_codex.py:49` is the
  instance-scoped sequence/PID receipt and `:72` is the bounded five-request barrier.
- Exact composed native calls:
  `tests/codex-worker/test_facade_integration.py:200` asserts `thread/goal/get` and the
  empty `account/rateLimits/read` params; `:217` is the dedicated exact output-schema
  forwarding case; `:246` asserts both history pages' thread/cursor/limit and fixed
  provider fields; `:279` asserts exact `thread/goal/set` and `thread/goal/get` params.
- Registry durability:
  `tests/codex-worker/test_models_registry.py:56` covers missing and zero-byte owner-only
  bootstrap; `:89` preserves malformed-record bytes; `:106` injects replace failure and
  proves the previous snapshot survives; `:230` preserves malformed and truncated
  non-empty bytes exactly; `:278` deterministically injects foreign ownership and
  proves bytes survive. Post-upstream replace failures retain code/kind, operation,
  durable state, and all raw IDs in `tests/codex-worker/test_broker.py:531`, `:544`, and
  `:559`; the exact raw-resume next action (including hostile-ID shell quoting) is
  asserted in `tests/codex-worker/test_facade.py:511` and `:523`.
- Endpoint refusal and safe cleanup:
  `tests/codex-worker/test_rpc_cli.py:245`, `:251`, `:302`, and `:325` preserve foreign,
  non-socket, unsafe-parent, and symlink targets; `:351` and `:367` prove cleanup removes
  only the owned endpoint and never a replacement; `:462`, `:472`, `:492`, and `:506`
  prove permissive/symlink/unsafe/swapped client endpoints receive no prompt bytes.
- §10 exactness and state preservation:
  the exhaustive code/kind vocabulary remains table-driven at
  `tests/codex-worker/test_rpc_cli.py:687`. The new composed table at
  `tests/codex-worker/test_facade_integration.py:164` asserts exact
  `worker_name_exists`, `worker_not_found`, `model_unavailable`, and
  `effort_unsupported` codes/kinds and byte-identical registry state after every row.

### Fresh verification

- Focused warning-strict task gate (integration, RPC CLI, live harness contract,
  registry, broker): `Ran 124 tests in 27.894s` — `OK`.
- Warning-strict fast lane:
  `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
  — `Ran 249 tests in 29.156s` — `OK`.
- `python3 -m py_compile tests/codex-worker/fake_codex.py
  tests/codex-worker/test_facade_integration.py
  tests/codex-worker/test_models_registry.py` and `git diff --check` — passed.
