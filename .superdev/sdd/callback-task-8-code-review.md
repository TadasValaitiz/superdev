# Strengths

- The production fix wave is narrowly scoped and preserves the existing architecture: callback recovery remains typed, `message` still does not autostart, and the new `daemon start` action reuses the managed lifecycle without creating a turn (`skills/subagent-driven-development/scripts/codex_worker/cli.py:188`, `skills/subagent-driven-development/scripts/codex_worker/facade.py:430`).
- The focused checkride closes the initial evaluator's five blockers with command-by-command happy/refusal evidence, destination-labelled sanitized callback frames, pending same-ID replay, written non-replay, failed/interrupted callbacks, raw compatibility, and artifact digest/read-back (`docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/evaluator-verdict.md:112`).
- The live harness exercises exactly five overlapping named worker commands, stable origin after ambient replacement/removal, disabled/unavailable states, daemon-side Unicode refusal, credential scrubbing, and preserved daemon state (`tests/codex-worker/live_broker_check.py:1609`, `tests/codex-worker/live_broker_check.py:1935`).
- The release mirrors are consistently 7.3.0, the installed-product receipt checks executable/byte identity and external-cwd behavior, and restoration to the original marketplace source/version is recorded (`docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/installed-7.3.0/install-transcript.md:87`).
- Fresh reviewer verification passed: 128 focused tests and the full warning-strict 361-test lane; version check/audit, marketplace manifest, Codex package, plugin sync, shell syntax, and range `git diff --check` all exited 0. The reviewed worktree remained clean.

# Issues

## Critical

None.

## Important

1. `skills/subagent-driven-development/scripts/codex_worker/claude_transport.py:31` — process-start validation is locale-sensitive. `_process_start` inherits `LC_TIME`, while `_same_process_start` parses both the Claude registry string and `ps` output with English `%a %b` tokens (`claude_transport.py:44`). On this host, `LC_ALL=lt_LT.UTF-8 ps -o lstart=` emits Lithuanian day/month names, so parsing returns `False` and a valid captured origin/override is rejected as `callback_target_stale`. This makes automatic and proactive callbacks fail for users running a non-English locale and weakens UC1/AH1/AH8 release readiness. Fix by forcing a stable locale (for example `LC_ALL=C`) for the `ps` subprocess or by using a locale-independent process-birth representation; add a regression that runs the real `_process_start`/comparison boundary under a non-English `LC_TIME`.

2. `tests/codex-worker/live_claude_evidence.py:139` — the no-frame fallback is a false-positive acceptance gate. When no callback event is present, it accepts any terminal ID mentioned in assistant text and calls the full result recovered merely because the synchronous `start` result's message text appears in that same assistant text (`live_claude_evidence.py:149`). The test explicitly removes the callback frame, copies the last event ID from later `status`, repeats the already-visible start message, and expects PASS (`tests/codex-worker/test_live_claude_evidence.py:87`). Thus a run where Claude never received an automatic callback can satisfy AH1. The checked-in real transcript contains credible callback attestations, but the validator does not require them. Fix the fallback to require independent, ordered evidence for both terminal callbacks (or receiver `origin/msg_id` records), correlate each event ID and complete payload to its turn, and add a negative control with successful start/status output but no callback receipt that must fail.

3. `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-design.md:682` — the acceptance ledger/report is not reconstructable or fully truthful as written. AH1-AH4 and AH6 cite ignored `.superdev/codex-worker-live/...` paths or bare runtime basenames even though the tracked copies live under `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/`; a clean checkout has zero tracked `.superdev/codex-worker-live` files. The implementation report additionally lists nonexistent proactive/origin/recovery/security/five-worker run directories (`.superdev/sdd/callback-task-8-report.md:23`) while claiming every cell is rerunnable (`callback-task-8-report.md:52`). AH9 names `4ce3fd0a..3302175a` (`design.md:690`), which in Git excludes the probe implementation commit `4ce3fd0a` and selects only the follow-up `3302175a`; the report incorrectly calls that range wider than `581999f0..3302175a` (`callback-task-8-report.md:55`). Its raw pong file is also an untracked absolute checkout path. Fix every receipt to cite the tracked Superdev copy, correct the report's run IDs, record the probe as explicit SHAs `4ce3fd0a` and `3302175a` or range `581999f0..3302175a`, and commit/cite a sanitized pong artifact or the committed trading protocol section.

## Minor

1. `.superdev/sdd/callback-task-8-report.md:34` — the report says callback statements are “never delivery claims,” and the release notes say transport delivery remains unclaimed (`RELEASE-NOTES.md:23`), but the tracked real-Claude transcript explicitly calls the proactive event a “delivery receipt” and says it “was delivered here” (`docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/claude-caller/claude.stream.jsonl:40`). The product response correctly claims only `written`; scope the disclaimer to product/CLI write receipts and separately label the receiver-observed event as MEASURED arrival.

2. `RELEASE-NOTES.md:11` — “normal, urgent, or blocking priority” does not match the public enum `now|next|later` and “blocking” conflicts with the command's non-blocking semantics. Use the exact priority names or describe urgency without implying synchronous blocking.

# Recommendations

- Fix the locale boundary first and add a real non-English-locale regression before another installed callback smoke.
- Strengthen the real-Claude evidence validator with a no-callback negative control; rerun the real-Claude caller after the validator itself can distinguish synchronous command output from an injected callback.
- Repair §9 and the Task 8 report so every receipt resolves from a clean checkout and the trading commit/pong provenance is exact.
- Re-run the focused warning-strict lane, full 361-test lane, callback security/common scenarios, real-Claude caller, package/sync/version gates, and installed 7.3.0 smoke after the fixes.

# Use-Case Cross-Check

- UC1 — **partial** (`tests/codex-worker/live_claude_evidence.py:139`): the checked-in Claude transcript reports both callbacks, but the validator can pass without receipt and localized `ps` can reject a valid origin.
- UC2 — **realized** (`tests/codex-worker/live_broker_check.py:1650`): proactive inline/file messages occur during an active turn, followed by accepted steer and later run.
- UC3 — **realized** (`tests/codex-worker/live_broker_check.py:1681`): alternate one-send routing is observed and subsequent terminal/default events remain at origin.
- UC4 — **realized** (`tests/codex-worker/live_broker_check.py:1620`): disabled and unavailable workers complete normally with honest callback states.
- UC5 — **realized** (`tests/codex-worker/live_broker_check.py:1739`): timeout remains active until later completion, and completed/failed/interrupted terminal events are preserved.
- UC6 — **realized** (`tests/codex-worker/live_broker_check.py:1771`): written non-replay and pending same-ID replay after restart are exercised with durable state retained.
- UC7 — **partial** (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-design.md:690`): both probe commits and correlated pong contents exist, but the recorded Git range excludes the implementation commit and the raw pong path is untracked/non-portable.
- AH1 — **partial** (`tests/codex-worker/live_claude_evidence.py:139`): actual real-Claude evidence is credible, but the acceptance validator admits a no-callback false positive and the locale bug can prevent valid capture.
- AH2 — **realized** (`tests/codex-worker/live_broker_check.py:1707`): replacement and then removal of ambient Claude metadata still yield three origin-only terminal events.
- AH3 — **realized** (`tests/codex-worker/live_broker_check.py:1650`): proactive update, continued work, steer, run, and five-worker overlap are exercised.
- AH4 — **realized** (`tests/codex-worker/live_broker_check.py:1681`): one alternate frame and later origin frames are asserted and preserved in focused evidence.
- AH5 — **realized** (`tests/codex-worker/live_broker_check.py:1749`): completed, failed, interrupted, timeout-active, and later-terminal behavior is covered.
- AH6 — **realized** (`tests/codex-worker/live_broker_check.py:1618`): enabled, disabled, and standalone/unavailable completions and states are covered.
- AH7 — **realized** (`tests/codex-worker/live_broker_check.py:1791`): same-ID pending replay, increasing attempt count, written non-replay, immutable artifact digest, and read-back are covered.
- AH8 — **partial** (`skills/subagent-driven-development/scripts/codex_worker/claude_transport.py:31`): scrub/refusal mechanisms are covered, but valid process identity fails under localized `ps` output.
- AH9 — **partial** (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-design.md:690`): event/pong IDs are documented, but the commit range and portable raw receipt are wrong/incomplete.
- AH10 — **realized** (`tests/codex-worker/live_broker_check.py:1780`): raw session/turn methods, managed stop/start recovery, native Claude, and package compatibility are exercised.
- AH11 — **realized** (`tests/codex-worker/live_broker_check.py:260`): one-object parsing, typed refusals, and `written` client semantics are enforced; the minor evidence wording issue does not change the client contract.

# Assessment

Ready to merge: **No**.

The core callback/recovery implementation and release packaging have substantial positive evidence, and all fresh deterministic/package gates passed. Merge is blocked by one production correctness defect (locale-dependent origin validation) and two acceptance-gate/provenance defects (a validator that can pass without a callback, and non-reconstructable/inaccurate §9 receipts). Correct those, rerun the focused live/installed gates, and request a focused re-review.
