# Codex worker shared app-server — CLI checkride

**Date:** 2026-08-29
**Behavioral candidate:** `8dbe8e0`
**Verdict:** **PENDING controller-dispatched executor/evaluator**
**Executor evidence:**
[`2026-08-28-codex-worker-shared-app-server-evidence/executor-transcript.md`](2026-08-28-codex-worker-shared-app-server-evidence/executor-transcript.md)
**Independent evaluation:**
[`2026-08-28-codex-worker-shared-app-server-evidence/evaluator-verdict.md`](2026-08-28-codex-worker-shared-app-server-evidence/evaluator-verdict.md)

## Frozen candidate boundary

Candidate `8dbe8e0` contains the shipping 8.0.0 skill behavior, singleton service fixes,
six isolated live lanes, and the real-Claude caller harness. Task 6 may change declared
release identity and installation state, but must not change Python or skill behavior
without reopening the affected executor/evaluator lanes and recording a new behavioral
candidate.

No implementation-role PASS judgment appears in this record. AH1–AH12 remain unchanged
until the independent evaluator accepts exact tracked record IDs.

## Ride scope handed to the executor

Drive each changed family one command at a time with literal argv, cwd, stdout, stderr,
exit code, elapsed time, and substrate label:

- successful prose and file starts with exact worker/session/thread and attach/resume routes;
- the composed callback/shared-TUI journey and lookup under different Claude metadata;
- common `start`, `run`, `message`, `status`, `messages`, `history`, `steer`, `interrupt`,
  `goal set/show`, `limits`, and `model list`;
- raw `session start/list/show/resume` and `turn start/wait/status/events/steer/interrupt`;
- migration status/conflict resolution;
- listener collision/config mismatch/active-work refusals;
- dangerous maintenance help, unknown-port peer preservation, forced impact, and restart
  durability.

The executor demonstrates only. A fresh very-smart evaluator judges literal output and
mechanism receipts from the operator perspective.

## Pre-existing measured evidence (not the independent verdict)

- [Real Claude PATH caller](2026-08-28-codex-worker-shared-app-server-evidence/real-claude-caller-summary.json)
- [Preflight/package](2026-08-28-codex-worker-shared-app-server-evidence/scenarios/preflight-package/summary.json)
- [Common/attach](2026-08-28-codex-worker-shared-app-server-evidence/scenarios/common-attach/summary.json)
- [Exactly five](2026-08-28-codex-worker-shared-app-server-evidence/scenarios/exactly-five/summary.json)
- [Lifecycle](2026-08-28-codex-worker-shared-app-server-evidence/scenarios/lifecycle/summary.json)
- [Migration/callback/shared-control](2026-08-28-codex-worker-shared-app-server-evidence/scenarios/migration-callback-shared-control/summary.json)
- [Recovery](2026-08-28-codex-worker-shared-app-server-evidence/scenarios/recovery/summary.json)

Every scenario summary currently says `MEASURED complete`, records zero secret-scan
violations, and leaves `checkride_verdict` pending. Those mechanism receipts are inputs
to the ride; they do not substitute for executor/evaluator judgment.
