# Codex worker command checkride

**Date:** 2026-08-19

**Stage:** executor handoff prepared; independent command-by-command checkride pending

**Overall verdict:** NOT YET EVALUATED

This file is the provisional handoff for Task 8 Steps 1–4. It does not claim the
independent executor/evaluator PASS required by Step 5. The evidence below is the
sanitized-but-verbatim output of separate real commands; no credential environment was
captured. The transcript scan found only Claude's literal `apiKeySource: "none"`, not a
credential or bearer value.

## Stage 1 live evidence

| Command | Stage 1 result | Verbatim evidence |
|---|---|---|
| `python3 tests/codex-worker/live_broker_check.py --preflight` | PASS — Codex CLI 0.147.0; Terra/medium and Sol/medium present | `2026-08-19-codex-worker-command-evidence/preflight/` |
| `python3 tests/codex-worker/live_broker_check.py --scenario common-journey` | PASS | `2026-08-19-codex-worker-command-evidence/common-journey/` |
| `python3 tests/codex-worker/live_broker_check.py --scenario five-workers` | PASS — exactly five simultaneous names | `2026-08-19-codex-worker-command-evidence/five-workers/` |
| `python3 tests/codex-worker/live_broker_check.py --scenario control-recovery` | PASS | `2026-08-19-codex-worker-command-evidence/control-recovery/` |
| `python3 tests/codex-worker/live_broker_check.py --scenario native-proxies` | PASS — limits typed unavailable | `2026-08-19-codex-worker-command-evidence/native-proxies/` |
| `python3 tests/codex-worker/live_broker_check.py --scenario access-schema` | PASS | `2026-08-19-codex-worker-command-evidence/access-schema/` |
| `bash tests/codex-worker/live_claude_check.sh` | PASS — Claude Code 2.1.236, PATH common commands only | `2026-08-19-codex-worker-command-evidence/claude-caller/` |

All counts, IDs, durations, paths, model/effort values, goal usage, and timestamps in
the evidence are copied from the command transcripts. Token usage is recorded as
unavailable. The five-worker result claims five simultaneous workers only; it makes no
100-worker capacity claim.

## Independent executor scope — pending

The executor must still drive each touched command and refusal one at a time, showing
the exact command, complete stdout/stderr, and exit code. The ride must include the
common `start`, `run`, `status`, `messages`, `history`, `steer`, `interrupt`, `goal set`,
`goal show`, `limits`, `daemon status`, and `daemon stop` paths plus explicit-socket
daemon status/shutdown compatibility and the designed refusal matrix.

The evaluator must independently judge exact JSON shapes, syntax, exit codes, paths,
recovery actions, lifecycle effects, nullable-phase fallback, and provider metadata.
This skeleton must not be changed to PASS until that evaluator returns PASS.

## Release state

Version bump, release notes, packaging, plugin update/reinstall, installed-launcher
evidence, anchor receipt edits, and the final evidence commit remain intentionally
pending.
