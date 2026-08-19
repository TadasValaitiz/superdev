# Codex worker command façade — final review fix report

**Date:** 2026-08-20
**Base reviewed:** `2d7c81a`
**Outcome:** DONE; all four Important findings and the whitespace Minor are fixed.

## Root causes and fixes

1. **Managed lifecycle safety:** `acquire_start_lock()` enters before the old
   `ensure_running()` body could translate its `RuntimeError`, and unsafe ancestor
   detection discarded the actual offending component. Managed startup now converts
   `UnsafePathError`/setup `OSError` to `-32024 daemon_start_failed` with the selected
   instance, offending path, log path, preserved-state claim, reason, and read-only
   inspection actions. Low-level helpers still raise `UnsafePathError` (a
   `RuntimeError`) when called directly. `start` and `run` subprocess regressions prove
   one JSON object, exit 1, and no traceback for unsafe ancestor/lock state.

2. **Runtime identity collision:** the six-hex (24-bit) component was independent of
   the full-digest durable path and allowed two identities to share socket/lock state.
   Runtime paths now use a compact `scw-<uid>-<20 hex>` owner-only directory with `s`
   and `l` leaf names. This supplies 80 bits of identity while measuring below the
   macOS AF_UNIX budget. The deterministic identities `collision-8515` and
   `collision-11163` share the old `a72c92` prefix but now derive different endpoints;
   a ready first endpoint cannot satisfy the second manager's probe.

   Migration behavior is deliberately non-destructive: legacy six-hex runtime
   endpoints are neither connected to nor deleted. Durable state remains at the same
   full-digest path, and the next managed invocation starts/reuses that durable
   instance at the new endpoint. A still-running legacy daemon may coexist until it is
   stopped through its old/raw endpoint.

3. **Captured-turn control:** the façade captured a turn ID but called broker methods
   that independently selected the current active turn. The optional internal broker
   seam now accepts `expected_turn_id`, rechecks runtime immediately before dispatch,
   sends exactly that ID upstream, and returns its confirmed ID. Both steer and
   interrupt barrier regressions complete the predecessor and start a successor
   between façade capture and broker dispatch; the successor receives no upstream
   control and the response is typed `turn_not_active` for the predecessor.

4. **Catalog drift:** the façade and broker perform separate live validations; a
   catalog change in between raised `ModelSelectionError(-32010)`, which the façade's
   closed enum converter collapsed to `-32020`. The minimal chosen branch is the
   reviewer's permitted structured translation: missing-model drift maps to
   `-32026 model_unavailable`, effort drift maps to `-32027 effort_unsupported`, and
   both provide a selected-instance `model list` inspection action stating that no
   fallback ran. Deterministic regressions prove no durable worker/upstream creation
   occurs on either refusal.

5. **Whitespace:** removed only the trailing spaces on line 3 of the documentation
   checkpoint.

## TDD evidence

Initial focused RED:

```text
python3 -W error::ResourceWarning -m unittest \
  tests/codex-worker/test_instance.py \
  tests/codex-worker/test_broker.py \
  tests/codex-worker/test_facade.py -v

Ran 102 tests
FAILED (failures=4, errors=4)
```

The expected failures were the six-hex collision, escaped lifecycle errors, absent
`expected_turn_id` broker seam / façade forwarding, and catalog errors incorrectly
reported as `CODEX_FAILURE`.

Focused GREEN:

```text
python3 -W error::ResourceWarning -m unittest \
  tests/codex-worker/test_facade.py \
  tests/codex-worker/test_broker.py \
  tests/codex-worker/test_instance.py -v

Ran 105 tests in 0.417s
OK
```

Main/subprocess lifecycle GREEN:

```text
python3 -W error::ResourceWarning -m unittest \
  tests.codex-worker.test_rpc_cli.CliTests.test_main_unsafe_managed_lock_is_one_json_without_traceback \
  tests.codex-worker.test_rpc_cli.PublicLauncherTests.test_subprocess_unsafe_runtime_ancestor_is_one_typed_json \
  tests.codex-worker.test_rpc_cli.PublicLauncherTests.test_subprocess_unsafe_start_lock_is_one_typed_json -v

Ran 3 tests in 0.354s
OK
```

Warning-strict fast gate:

```text
python3 -W error::ResourceWarning -m unittest discover \
  -s tests/codex-worker -p 'test_*.py'

281 discovered tests; exit 0
```

The printed argparse invalid-choice line is expected output from its refusal test; the
gate exited successfully.

Final static verification:

```text
python3 -m py_compile <three changed production modules and four changed test modules>
git diff --check

exit 0
```

No live broker, Claude checkride, or plugin reinstall was run, per controller scope.

## Interface / compatibility / decisions for D59+

- Public error enum and CLI method vocabulary are unchanged. `-32024` details are
  enriched for managed safety refusals; `-32026/-32027` are existing documented codes.
- Raw broker control calls remain source-compatible because `expected_turn_id` is an
  optional final parameter. Common façade control always supplies it.
- Runtime endpoint layout changes. Ratification requested: accept the compact 80-bit
  component instead of 32 hex because 32 exceeded the measured macOS AF_UNIX path
  limit. The non-destructive legacy behavior is documented above.
- Catalog handling uses precise translation rather than a validated snapshot threaded
  through session and turn creation. This is the reviewer's explicit fallback option
  and avoids broadening the creation interfaces in the final-fix pass. Ratification
  requested for that minimal choice.
