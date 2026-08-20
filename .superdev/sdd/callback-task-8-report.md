# Callback Task 8 implementation report

Date: 2026-08-20
Base: `cf073be`
Status: PASS pending final code-review receipt

## TDD and deterministic gate

The first change was a RED contract expansion for the six separately runnable callback
scenarios and the real-Claude evidence validator. Focused RED failed on the absent
scenario/receipt contracts. GREEN added the live scenarios and fixed the product seams
they exposed. The final warning-strict gate is `361 tests` PASS in 32.150 seconds;
`py_compile`, `bash -n`, and `git diff --check` also pass. Expected argparse stderr from
the concurrent-worktrees fixture is captured, so the final fast gate is pristine. The
Task 1 representative enum minor is closed by the exhaustive exact code/kind guard.

## MEASURED live acceptance

Initial separate raw run directories:

- preflight: `.superdev/codex-worker-live/20260820T141136.693287Z-13475-preflight/`
- common: `.superdev/codex-worker-live/20260820T141214.365903Z-13986-callback-common/`
- proactive/alternate/origin terminal: `.superdev/codex-worker-live/20260820T141247.118195Z-16520-callback-proactive/`
- origin metadata replacement/unset retention: `.superdev/codex-worker-live/20260820T141313.541987Z-18109-callback-origin-retention/`
- timeout/terminal/restart/artifact: `.superdev/codex-worker-live/20260820T141417.462968Z-23274-callback-recovery/`
- credential/PID/Unicode/stale/ambiguous: `.superdev/codex-worker-live/20260820T141629.212746Z-31212-callback-security/`
- exactly five simultaneous named workers: `.superdev/codex-worker-live/20260820T141706.195738Z-34392-callback-five-workers/`
- real Claude caller: `.superdev/codex-worker-live/20260820T142608Z-45432-claude-caller/`

Focused recovery supersedes the first recovery record at
`.superdev/codex-worker-live/20260820T150957.753587Z-27343-callback-recovery/`.
It proves wait timeout then later terminal, completed/failed/interrupted, written
non-replay, pending same-ID replay (attempt count 4), raw session/turn compatibility,
and an 801482-byte artifact with exact SHA/readback. All callback statements are local
written/correlated receipts, never delivery claims. Sanitized raw copies are tracked
under `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/`.

## CLI checkride

Fresh executor `/root/callback_task8_implementer/callback_checkride_executor` ran at
`gpt-5.6-terra`, medium. Fresh evaluator
`/root/callback_task8_implementer/callback_checkride_evaluator` ran at
`gpt-5.6-sol`, high. Its first NEEDS_WORK identified five operator/mechanism blocks.
Fix wave `9937c8e` and cleanup `07ff933` added typed recovery, explicit daemon start,
daemon-owned Unicode sizing, exact sanitized callback frames, missing mechanism rides,
and selected-instance stop recovery. Fresh focused executor
`/root/callback_task8_implementer/callback_focused_reride_executor` rerode the affected
surface. Final evaluator verdict: PASS at `07ff933`, no blockers.

## UC/AH and independent probe receipts

Design §9 contains a rerunnable receipt in every AH1–AH11 cell. Trading probe evidence
is the untouched worktree
`/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.claude/worktrees/codex-worker-callback-probes`,
requested commit range `581999f0..3302175a` (design records the wider provenance range
`4ce3fd0a..3302175a`). Live pong evidence is the trading main checkout's
`.superdev/brainstorm/codex-worker-claude-callback-ping-pong.jsonl`, sequence 3/4.
The dirty trading main checkout was not modified.

## Release and installed product

Release tooling bumped all declared mirrors to 7.3.0. Version check/audit,
marketplace manifest, Codex package, and plugin sync gates pass independently. The
committed worktree was temporarily selected as `superdev-dev`, installed enabled as
7.3.0, and verified for manifest, executable/byte-identical launcher, external-cwd
help/status, and installed callback smoke PASS. The original main-checkout marketplace
source and enabled 7.2.0 installation were then restored; the 7.3.0 cache remains for
reconstruction. No durable worker/callback state or artifacts were deleted. Exact
receipt: `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/installed-7.3.0/install-transcript.md`.

## Commits

- `ed3b023` — live acceptance harness and first product corrections
- `9937c8e` — actionable callback recovery and reride mechanisms
- `07ff933` — selected-instance daemon-stop recovery
- `1918fba` — checkride acceptance evidence
- `4911b68` — 7.3.0 release metadata

## Deviations and concerns

The initial checkride required one product fix wave and one cleanup correction, both
closed by the evaluator. During marketplace switching, the old install became
disassociated before `uninstall --keep-data`, producing an expected safe `not found`
refusal; installation proceeded and the original state was restored exactly. No open
acceptance, evaluator, release, install, or ledger blocker remains.
