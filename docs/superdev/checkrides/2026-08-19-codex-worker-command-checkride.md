# Codex worker command checkride

**Dates:** 2026-08-19 historical ride; 2026-08-20 focused re-ride and evaluation

**Roles:** the CHECKRIDE EXECUTOR drove the real CLI and recorded commands, complete
stdout/stderr, and exit codes. The independent CHECKRIDE EVALUATOR judged the surface
from the operator's perspective and made no product edits.

**Overall verdict:** **PASS**

The substrate was a **MEASURED** real local Codex provider (`codex-cli 0.147.0`) with
isolated named instances and temporary working directories. Stage 1 broker and Claude
caller runs are separate **MEASURED** live evidence. AH10/AH11 fixture tests are labeled
**deterministic**, not provider measurements. Token usage remained unavailable, and
the provider did not expose account capacity; neither value is inferred.

## Independent ride and repair history

- The historical executor ride recorded 39 commands: 28 happy paths and 11 refusals.
  Its affected active-control capture was later superseded rather than rewritten.
- The first evaluation blocked on an over-budget goal input interpretation, a real
  `turn_active` façade mapping defect, and incomplete affected-path capture. It also
  advised explicit unknown-capacity details and executable unsupported-effort recovery.
- Product fix `7d356e2` and contract/design follow-up `ffa24e7` added the typed
  `-32004 turn_active` mapping, preserved identities and named controls, clarified
  authoritative goal state, marked limits capacity unknown, and added the corrected
  effort retry.
- The executor then recorded 16 fully reconstructable focused commands: 12 happy paths
  and 4 refusals. The goal pause used a budget above measured usage; active timeout,
  overlap refusal, status, messages, steer, interrupt, limits, effort recovery, raw
  recovery/events, and non-destructive stop were each captured separately.
- The independent evaluator returned **PASS**: B1–B3 and E1/E2 are closed; all
  UC1–UC10 and AH1–AH12 are realized with live and deterministic lanes distinguished.

Direct records:

- [Complete sanitized-verbatim executor transcript](2026-08-19-codex-worker-command-evidence/executor-transcript.md)
- [Independent evaluator PASS verdict](2026-08-19-codex-worker-command-evidence/evaluator-verdict.md)

## Stage 1 live evidence

| Command | Result | Direct evidence |
|---|---|---|
| `python3 tests/codex-worker/live_broker_check.py --preflight` | PASS — live Terra/medium and Sol/medium discovered | [preflight transcript](2026-08-19-codex-worker-command-evidence/preflight/transcript.jsonl), [summary](2026-08-19-codex-worker-command-evidence/preflight/summary.json) |
| `python3 tests/codex-worker/live_broker_check.py --scenario common-journey` | PASS — start, follow-up, preserved stop/restart | [common journey transcript](2026-08-19-codex-worker-command-evidence/common-journey/transcript.jsonl), [summary](2026-08-19-codex-worker-command-evidence/common-journey/summary.json) |
| `python3 tests/codex-worker/live_broker_check.py --scenario five-workers` | PASS — exactly five simultaneous names, not a capacity claim | [five-worker transcript](2026-08-19-codex-worker-command-evidence/five-workers/transcript.jsonl), [summary](2026-08-19-codex-worker-command-evidence/five-workers/summary.json) |
| `python3 tests/codex-worker/live_broker_check.py --scenario control-recovery` | PASS — observation/control and raw socket compatibility | [control transcript](2026-08-19-codex-worker-command-evidence/control-recovery/transcript.jsonl), [summary](2026-08-19-codex-worker-command-evidence/control-recovery/summary.json) |
| `python3 tests/codex-worker/live_broker_check.py --scenario native-proxies` | PASS — native goal/history and typed-unavailable limits | [native transcript](2026-08-19-codex-worker-command-evidence/native-proxies/transcript.jsonl), [summary](2026-08-19-codex-worker-command-evidence/native-proxies/summary.json) |
| `python3 tests/codex-worker/live_broker_check.py --scenario access-schema` | PASS — full/read-only enforcement and schema output | [access/schema transcript](2026-08-19-codex-worker-command-evidence/access-schema/transcript.jsonl), [summary](2026-08-19-codex-worker-command-evidence/access-schema/summary.json) |
| `bash tests/codex-worker/live_claude_check.sh` | PASS — real Claude caller used PATH common commands only | [Claude stream](2026-08-19-codex-worker-command-evidence/claude-caller/claude.stream.jsonl), [validated evidence](2026-08-19-codex-worker-command-evidence/claude-caller/validated-common-evidence.json), [summary](2026-08-19-codex-worker-command-evidence/claude-caller/summary.json) |

All IDs, paths, durations, model/effort fields, goal usage, and timestamps in these
files are copied from the recorded commands. Five simultaneous workers demonstrate
five only. Limits capacity and completion token usage remain explicitly unavailable.

## Release and installed evidence

Release source commit `c8c82ba` bumps every declared manifest to 7.2.0. Fresh finishing
and package results are recorded in the [final verification record](2026-08-19-codex-worker-command-evidence/final-verification.md).

Claude's configured `superdev-dev` marketplace originally pointed at the main checkout,
which still advertised 7.1.0. The first reversible source switch is preserved verbatim:
removing/re-adding the marketplace disassociated the installed plugin, the update refused
honestly, and the EXIT cleanup restored the original source. With controller authorization,
the marketplace was then switched to this committed release worktree and the plugin was
explicitly reinstalled. It intentionally remains worktree-backed through final review;
the controller will restore the main-checkout source after integration.

- [Failed update and successful restoration transcript](2026-08-19-codex-worker-command-evidence/installed-7.2.0/marketplace-attempt.txt)
- [Successful reinstall, update/list, and outside-repository launcher transcript](2026-08-19-codex-worker-command-evidence/installed-7.2.0/install-transcript.txt)

The installed manifest reports 7.2.0 and `claude plugin list` reports the user-scope
plugin enabled. The executable launcher at
`/Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0/bin/codex-worker` ran
`--help` and observational `daemon status` from a fresh external `mktemp` directory.
No cache or durable worker record was deleted.
