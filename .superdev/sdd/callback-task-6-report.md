# Task 6 — source-repository callback probes report

## Status

Implemented and committed in the isolated trading-repository worktree.

- Trading worktree: `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.claude/worktrees/codex-worker-callback-probes`
- Branch/base: `codex-worker-callback-probes` from `581999f0`
- Trading commit: `4ce3fd0a43f0175c914633414b7f2711a87f6e4d` (`test(claude-code): add Codex callback probes`)
- Files committed: `scripts/send_to_claude.py`, both probe scripts,
  `tests/test_codex_callback_probes.py`, the protocol reference, and docs index.

## TDD receipt

1. RED: `uv run pytest tests/test_codex_callback_probes.py -q` before implementation
   produced 3 failures and 4 errors: the two probe modules were absent and
   `send_to_claude.build_payload()` lacked `message_uuid`.
2. GREEN: the focused contract suite passed 9 tests in 0.15s.
3. A live invocation with the system `python3` found a reproducible Python 3.9 import
   error for `datetime.UTC`. Root cause: the initial probes used a Python 3.11-only
   spelling despite `python3` being the documented execution surface. A RED test was
   added for imports under system `python3`; the minimal fix uses `timezone.utc`.
4. Final focused receipt: `uv run pytest tests/test_codex_callback_probes.py -q` →
   **10 passed in 0.20s** (SIMULATED contracts). It covers the literal D27/D28 UUIDv5
   namespace and fixture mapping, UUID default preservation, terminal completion
   passthrough, proactive priority, input exclusivity, one-object dry-run/failure output,
   no token in dry-run output, and system-Python importability.

## Gate receipt

`uv run pytest tests --suite fast -n auto` completed with exit status 0 after the final
change. The runner reported 18 workers and 5,129 items; tool-recorded wall time was 28.5s.
The process emitted pre-existing-looking SQLAlchemy/psycopg `AdminShutdown` connection
cleanup tracebacks near completion, so the gate output was not pristine. The captured
output was truncated before pytest's final textual summary, but the command itself
completed successfully. This warning is a concern to retain for controller review; this
task does not touch database code.

## MEASURED live probe evidence

Target preflight resolved `orchestrator-original` from the live registry to
`/tmp/cc-socks/56571.sock` (`live: true`). Each non-dry-run probe printed one JSON object,
used priority `next`, `msg_id == event_id`, deterministic D28 UUIDv5, `from_mode:"bypass"`,
and omitted `session_id`.

| event ID | event | write receipt | correlated append-only pong |
|---|---|---|---|
| `probe-live-proactive-20260820T133944Z` | `worker_message` | MEASURED `attempt.state: written`; 920 bytes; authenticated | JSONL seq 3, `received_at: 2026-08-20T13:41:40+03:00` |
| `probe-live-terminal-20260820T134123Z` | `turn_terminal` | MEASURED `attempt.state: written`; 1154 bytes; authenticated | JSONL seq 4, `received_at: 2026-08-20T13:42:10+03:00` |

Pong evidence path (main repository, append-only):
`/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.superdev/brainstorm/codex-worker-claude-callback-ping-pong.jsonl`.

The terminal event contains a clearly labelled **SIMULATED** completion fixture. The
socket writes and matching pongs are **MEASURED** only as wire-write/pong correlation;
they do not prove daemon delivery, credential scrubbing, outbox restart behavior, or
security policy.

## Worktree deviation

The plan named `.worktrees/codex-worker-callback-probes`, but that path is not ignored.
To preserve the active dirty checkout, the controller created and this task used the
repo-convention ignored `.claude/worktrees/codex-worker-callback-probes` path instead.
No files in the main checkout were modified by this implementation commit.

## Controller baseline control

After the review fix, the controller ran the exact gate on the untouched base checkout
at `581999f0` (the only main-checkout dirt was unrelated documentation). It reproduced
the same SQLAlchemy/psycopg `AdminShutdown` cleanup traceback at 95% and then completed:

```text
5119 passed in 39.08s
exit 0
```

This establishes the non-pristine database cleanup output as a pre-existing repository
gate defect rather than a probe-code regression. The feature branch's changed surface is
covered by its clean focused `13 passed in 0.55s`; the exact full gate still passes but
must retain the honestly labelled pre-existing-noise qualification.

## Follow-up findings and fix receipt (2026-08-20)

Controller review found two probe-boundary defects in `4ce3fd0a`:

1. Dry-run resolution called `socket_live()` and therefore opened a liveness connection.
2. `--message-file` / `--completion-file` reads occurred before the JSON failure boundary,
   producing a traceback for a missing file.

Fresh RED receipt: `uv run pytest tests/test_codex_callback_probes.py -q` produced three
failures: the real listening AF_UNIX target accepted two dry-run connections (one per
probe), and each missing-file case emitted no JSON stdout and a traceback. The test's
first attempt used an overlong macOS temporary AF_UNIX path; it was corrected to a short,
per-process `/tmp` path before recording the behavioral RED.

Fix commit: `3302175a3c848cae00f407f7f8673ff7c2862c5a`
(`fix(claude-code): keep callback probes side-effect free`). It adds an additive
`probe_live=True` resolution seam whose default preserves normal live behavior. Both
probes pass `probe_live=False` for dry-run, so target name/path resolution does not call
`socket_live()`; normal sends remain liveness-checked and unchanged. File reads and empty
message validation now occur inside each script's existing one-object JSON failure path.

GREEN receipt: `uv run pytest tests/test_codex_callback_probes.py -q` → **13 passed in
0.55s**. The added deterministic AF_UNIX listener test records zero accepted connections
across both dry-run probes; parameterized missing-file tests assert exit 1, exactly one
JSON stdout object, and no traceback.

Fast-gate receipts were captured fully outside the repository worktree:

| run | result | clean? | evidence |
|---|---|---|---|
| `/tmp/task6-fast-gate-1.log` | reached 5,132 items / exit 0 | no | 13 `psycopg.errors.AdminShutdown` cleanup tracebacks near 96%; output lacked final summary/time in the first capture |
| `/tmp/task6-fast-gate-2.log` | **5,132 passed in 33.45s**; `/usr/bin/time` real **34.25s**; exit 0 | no | 6 repeated `psycopg.errors.AdminShutdown: terminating connection due to administrator command` cleanup tracebacks near 96% |

Diagnosis: the warnings come from SQLAlchemy pool rollback during Postgres connection
finalization, while the repository's test harness deliberately uses `DROP DATABASE ...
WITH (FORCE)` and documents a sibling-worktree force-drop hazard in
`tests/integration/test_pg_bootstrap_concurrency.py`; this task changes neither the test
database lifecycle nor database code. The prescribed one bounded rerun repeated the
warnings. **Historical disposition:** the Task 6 implementation report was BLOCKED on
the requested clean fast-gate receipt; no warnings were hidden. **2026-08-20 erratum
(D36):** controller reproduction on the untouched base later produced `5119 passed` /
exit 0 with the same cleanup noise, and the changed probe surface later had a clean
focused `13 passed` receipt. This does not turn either historical 5132-test run into a
pristine full gate; final Task 6 disposition is accepted scoped probe evidence, with the
full-gate noise explicitly outside its code scope.

The original D27/D28 and live-event/pong evidence is preserved unchanged.
