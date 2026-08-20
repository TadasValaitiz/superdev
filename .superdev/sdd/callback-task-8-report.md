# Callback Task 8 implementation report

Date: 2026-08-20
Base: `cf073be`
Status: PASS; evaluator PASS and final reviewer Ready to merge Yes

## TDD and deterministic gate

The first change was a RED contract expansion for the six separately runnable callback
scenarios and the real-Claude evidence validator. Focused RED failed on the absent
scenario/receipt contracts. GREEN added the live scenarios and fixed the product seams
they exposed. The final warning-strict gate is `361 tests` PASS in 32.150 seconds;
`py_compile`, `bash -n`, and `git diff --check` also pass. Expected argparse stderr from
the concurrent-worktrees fixture is captured, so the final fast gate is pristine. The
Task 1 representative enum minor is closed by the exhaustive exact code/kind guard.

## MEASURED live acceptance

Tracked receipts for the initial separate runs (each summary retains its original raw
run path):

- preflight: `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/preflight/`
- common: tracked `callback-common/` beneath that same evidence directory
- proactive/alternate/origin terminal: tracked `callback-proactive/`
- origin metadata replacement/unset retention: tracked `callback-origin-retention/`
- timeout/terminal/restart/artifact: tracked `callback-recovery/`
- credential/PID/Unicode/stale/ambiguous: tracked `callback-security/`
- exactly five simultaneous named workers: tracked `callback-five-workers/`
- real Claude caller: tracked `claude-caller/`

Focused recovery supersedes the first recovery record at tracked
`docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/focused-reride/callback-recovery-clean/`.
It proves wait timeout then later terminal, completed/failed/interrupted, written
non-replay, pending same-ID replay (attempt count 4), raw session/turn compatibility,
and an 801482-byte artifact with exact SHA/readback. Product/CLI attempt statements are
local `written` receipts, never delivery claims; the real Claude transcript separately
contains MEASURED receiver-observed callback attestations. Sanitized raw copies are tracked
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

A fresh final branch reviewer at `gpt-5.6-sol`, high found no Critical issues and three
Important release-readiness issues: locale-sensitive process identity, a permissive
no-frame validator fallback, and non-portable receipt provenance. The TDD review wave
forces a stable process locale, requires two ordered receiver attestations plus both
full results, adds a no-callback negative control, and repairs the ledger/probe receipts.
Fresh tracked common/security/real-Claude evidence is under
`docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/reviewer-fix-wave/`.
The final exact-completion rerun is the `claude-caller-exact/` child: both ordered
receiver attestations contain parseable full completion objects equal to their
corresponding complete command results, closing the reviewer's remaining I2 concern.
The final focused re-review at candidate `8e724e6` is Ready to merge Yes with no
remaining Critical, Important, or Minor findings.

## UC/AH and independent probe receipts

Design §9 contains a rerunnable receipt in every AH1–AH11 cell. Trading probe evidence
is the untouched worktree
`/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.claude/worktrees/codex-worker-callback-probes`,
commit range `581999f0..3302175a`, containing probe implementation `4ce3fd0a` and
side-effect correction `3302175a`. Live pong evidence from the trading main checkout's
`.superdev/brainstorm/codex-worker-claude-callback-ping-pong.jsonl`, sequence 3/4, is
copied verbatim to tracked checkride evidence as `trading-probe-pongs.jsonl`.
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
- `ec42d98` — release and initial installed-product receipts
- `79d6ec2` — final review locale/validator/provenance fixes
- `76ee44b` — post-review localized installed-product proof
- `8e724e6` — exact received-completion contract and live receipt

## Deviations and concerns

The initial checkride required one product fix wave and one cleanup correction, both
closed by the evaluator. During marketplace switching, the old install became
disassociated before `uninstall --keep-data`, producing an expected safe `not found`
refusal; installation proceeded and the original state was restored exactly. No open
acceptance, evaluator, release, install, or ledger blocker remains. The post-review
installed callback smoke also passes under Lithuanian `LC_ALL`; the original external
marketplace/plugin state is restored.
