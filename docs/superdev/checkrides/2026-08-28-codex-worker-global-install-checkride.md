# Codex worker global installation — CLI checkride

**Date:** 2026-08-28
**Candidate:** `de425d7a072805bca26cf4d5f8b761d0a701d578` (`codex-worker 7.9.0`)
**Final verdict:** **PASS**
**Executor evidence:**
[`2026-08-28-codex-worker-global-install-evidence/executor-transcript.md`](2026-08-28-codex-worker-global-install-evidence/executor-transcript.md)
**Independent evaluation:**
[`2026-08-28-codex-worker-global-install-evidence/evaluator-verdict.md`](2026-08-28-codex-worker-global-install-evidence/evaluator-verdict.md)

## What was ridden

The executor drove the real installed command one invocation at a time with literal
argv, cwd, stdout, stderr, exit code, elapsed time, and honesty tier. UV tool/bin/cache,
HOME, worker state, runtime, and PATH were isolated under fresh temporary roots. The
successful provider lane explicitly retained the existing `CODEX_HOME` authentication
location without reading or printing credential contents.

| Operator journey | Final evidence |
|---|---|
| Absent command installs from trusted bundled source | literal absent `command -v`, preflight, one UV reinstall, then PATH command/version |
| Lower and higher version mismatch repair | simulated starting versions `0.0.1` and `9999.0.0`, each over measured real isolated UV behavior; exactly one reinstall and measured required version afterward |
| Exact version is idempotent | subsequent preflight logs only `uv tool dir --bin`, with no install |
| Shadow, missing UV, install failure, missing external Codex | actionable typed refusals; foreign executable, prior tool, and durable sentinel bytes preserved where applicable |
| Non-editable source independence | real UV/Python 3.9 install, literal source move, PATH command and import from isolated UV site-packages afterward |
| Durable reinstall | identical session/thread IDs through create, runtime stop, reinstall, D11 `run --name` reattachment, status, and runtime-only stop |
| Unrelated-repository plain PATH operation | literal `codex-worker start` and `status` from `/Users/tadas/Projects/ai-ethics/ai-trading-calibration`, exactly one read-only/no-callback `status-checker-abc`, Git state unchanged |
| Ownership audit | `command -v`, `uv tool list --show-paths`, executable and import provenance all point inside the selected isolated UV tool environment |

The final transcript contains 117 command records and 124 total records/events. The
evaluator independently reconstructed the focused appendices and accepted the surface
only after the plain PATH journey succeeded with the correct provider-home boundary.

## Evaluation iterations

The first verdict was NEEDS FIXES because operations used absolute UV-bin launchers,
several install-state transitions were summarized instead of reconstructed, source
removal was not literal, and simulated starting versions were not labelled precisely.
Focused rerides closed those evidence defects. Two failed external attempts remain in
the transcript as honest incident records: one `incomplete_completion`, followed by a
fresh attempt whose isolated HOME accidentally hid provider authentication and produced
an upstream 401. Neither is used as success evidence. The final appendix explicitly set
`CODEX_HOME` while retaining all UV and worker isolation, then passed.

An exploratory durable reride also remained incomplete and is not substituted for the
complete D11 scenario. Its runtime was stopped non-destructively and its command,
environment, and stop output are preserved verbatim in the tracked executor transcript.

**Evidence-handoff erratum (2026-08-28):** the evaluator handed off
`/tmp/cw-reride-durable-2pdl66d5` for preservation, but that directory was already absent
when the Task 4 implementer resumed (initial listing empty; later `find` and `stat`
confirmed absence). The implementer did not delete or move it. This is reported rather
than silently claiming the raw root was retained; no PASS finding relies on that
incomplete exploratory run.

## Nonblocking observations routed

The evaluator's two advisory observations are tracked as backlog items in
[`docs/superdev/backlog/2026-08-28-codex-worker-global-install-observations.md`](../backlog/2026-08-28-codex-worker-global-install-observations.md):

1. Preflight success should distinguish installed, repaired-from/to, and already-ready.
2. `incomplete_completion` should return known worker identities and runnable
   status/history recovery when a mapping exists.

They do not block this release: the intended final journey passed, and the incomplete
incidents are preserved without weakening or relabelling their outputs.

## Release relationship

The original independently evaluated checkride covered the complete implementation at
7.9.0. The coupled 7.10.0 release then changed declared identity and release notes and
ran package/version plus current-user installed-command verification. Final review later
added D12 runtime/cached-room compatibility behavior, so “changes only declared identity”
is no longer accurate. The focused
[`d12-reride/executor-transcript.md`](2026-08-28-codex-worker-global-install-evidence/d12-reride/executor-transcript.md)
retains its exploratory setup failures, then reconstructs the corrected old-peer,
managed-raw, loaded-root, foreground-serve, and release-audit journeys in 78 literal
events. Its independent
[`d12-reride/evaluator-verdict.md`](2026-08-28-codex-worker-global-install-evidence/d12-reride/evaluator-verdict.md)
is **PASS**, closing AH6 for current HEAD without relabelling the failed attempts.

Final review subsequently tightened managed raw selection so only an exact-ready status
probe may expose the target endpoint. The focused
[`post-fix-ah6-executor-transcript.md`](2026-08-28-codex-worker-global-install-evidence/d12-reride/post-fix-ah6-executor-transcript.md)
records 11 events (9 exit 0, 2 exit 1): non-object and generic failed status probes each
return typed `daemon_unavailable` after only `daemon/status`, while exact-ready proceeds
to `model/list`. The aggregate evaluator verdict is **PASS** for behavioral candidate
`2db9ccd` and evidence-only descendant `a856b7c`.
