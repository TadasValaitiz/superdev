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
