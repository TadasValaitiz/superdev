# Task 8 final verification

Date: 2026-08-20

## Source gates

- `python3 -m py_compile skills/subagent-driven-development/scripts/codex_worker/*.py`
  — PASS, exit 0.
- `bash -n tests/codex-worker/live_claude_check.sh` — PASS, exit 0.
- `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
  — PASS, 361 tests in 32.150 seconds, no warning output.
- `git diff --check` — PASS, exit 0.

## Live and checkride gates

Six callback scenarios were run separately and passed, followed by a real Claude
caller validator PASS. Exact live paths and UC/AH mappings are in the design §9
receipts and the tracked raw JSONL copies beside this file. `callback-five-workers`
used exactly five simultaneous uniquely named workers. Values from the live runs are
labeled MEASURED; no token, capacity, or delivery value is inferred.

The fresh Terra/medium executor and fresh Sol/high evaluator completed one fix/reride
loop. The independent final verdict is PASS at product candidate `07ff933`; all five
initial findings and the cleanup recovery finding are closed. See
`executor-transcript.md`, `executor-focused-reride.md`, and `evaluator-verdict.md`.

## Version, package, and sync gates

- `./scripts/bump-version.sh 7.3.0` — updated the seven declared version mirrors.
- `./scripts/bump-version.sh --check` — PASS; every declared mirror is 7.3.0.
- `./scripts/bump-version.sh --audit` — exit 0; undeclared matches are intentional
  release requirements in the task brief, plan, and D25 decision record.
- `bash tests/codex/test-marketplace-manifest.sh` — PASS.
- `bash tests/codex/test-package-codex-plugin.sh` — PASS, all archive assertions.
- `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh` — PASS.

Release source commit: `4911b68` (`chore(release): bump superdev to 7.3.0`).

## Installed-product gate

The committed worktree was temporarily selected as the development marketplace and
installed as enabled Superdev 7.3.0. The installed manifest, executable bit, launcher,
raw launcher, and CLI module were verified; external-cwd help and stopped-instance
status exited 0. The installed callback-common smoke passed with a written/correlated
terminal receipt plus disabled and unavailable cases.

The exact original marketplace source `/Users/tadas/Projects/superdev` and enabled
7.2.0 plugin were restored after integration. The 7.3.0 cache remains reconstructable.
See [the sanitized verbatim transcript](installed-7.3.0/install-transcript.md).

No durable worker/callback state or artifacts were deleted.
