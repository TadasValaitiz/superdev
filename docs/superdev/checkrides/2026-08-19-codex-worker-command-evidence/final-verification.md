# Task 8 final verification evidence

Date: 2026-08-20

All results below are fresh commands from the release stage. Stage 1 and checkride
measurements remain separately labeled in the summary and source transcripts.

## Finishing commands before release

- `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
  — PASS, 267 tests in 30.979 seconds.
- `python3 tests/codex-worker/live_broker_check.py` — PASS for preflight and all five
  real scenarios, ending with `{"status":"PASS","scenario":"all-live-broker-checks"}`.
  The run used Codex CLI 0.147.0, discovered Terra/medium and Sol/medium, demonstrated
  exactly five simultaneous workers, and kept token usage/capacity unavailable rather
  than inferring either.
- `bash tests/codex-worker/live_claude_check.sh` — PASS with Claude Code 2.1.236,
  six PATH common commands, Terra/medium, two returned messages, no MCP/direct/raw
  Codex invocation, and `durable_state: preserved`.

Fresh aggregate outputs were copied verbatim from these raw paths into the existing
tracked scenario directories:

- `.superdev/codex-worker-live/20260819T212756.399212Z-5094-preflight/`
- `.superdev/codex-worker-live/20260819T212757.912140Z-5094-common-journey/`
- `.superdev/codex-worker-live/20260819T212810.424398Z-5094-five-workers/`
- `.superdev/codex-worker-live/20260819T212820.739369Z-5094-control-recovery/`
- `.superdev/codex-worker-live/20260819T212831.731323Z-5094-native-proxies/`
- `.superdev/codex-worker-live/20260819T212841.389215Z-5094-access-schema/`
- `.superdev/codex-worker-live/20260819T212938Z-18021-claude-caller/`

## Version and package verification

- `./scripts/bump-version.sh 7.2.0` — all seven declared version fields changed from
  7.1.0 to 7.2.0.
- `./scripts/bump-version.sh --check` — PASS; all declared files in sync at 7.2.0.
- `./scripts/bump-version.sh --audit` — exit 0; reported only intentional 7.2.0
  references in the task brief/report, plan, decision/design, receipt, and checkride
  documentation.
- `bash tests/codex/test-marketplace-manifest.sh` — PASS.
- `bash tests/codex/test-package-codex-plugin.sh` — PASS after the D57 release-tooling
  correction; every archive assertion passed.
- `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh` — PASS.
- `bash -n scripts/package-codex-plugin.sh tests/codex/test-package-codex-plugin.sh`
  — PASS.

Release source commit: `c8c82ba` (`chore(release): bump superdev to 7.2.0`).

## Installed 7.2.0 verification

The configured marketplace originally advertised the main checkout's 7.1.0. The
first reversible attempt restored that source after `update` reported the plugin was
not installed. The second, controller-authorized flow temporarily points the marketplace
at the committed release worktree through final review and ran:

- `claude plugin install superdev@superdev-dev --scope user` — installed successfully.
- `claude plugin update superdev@superdev-dev` — latest version 7.2.0.
- `claude plugin list` — Superdev 7.2.0, user scope, enabled.
- `test -x /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0/bin/codex-worker`
  — PASS.
- Installed `.claude-plugin/plugin.json` version — `7.2.0`.
- From external `/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/tmp.vLKUmXWCOq`,
  installed `codex-worker --help` — exit 0; installed `codex-worker daemon status` —
  exit 0 with one JSON object, default instance stopped, zero workers.

Verbatim transcripts:

- [initial attempt and guaranteed restoration](installed-7.2.0/marketplace-attempt.txt)
- [successful reinstall and installed launcher checks](installed-7.2.0/install-transcript.txt)

No credentials, cache contents, or durable worker records are included or deleted.

## Post-fix installed-cache refresh

After the final product fix, the controller measured that installed `facade.py` was
stale while installed `commands.py` already matched the worktree. This was an
installed-cache issue, not a source change. The controller ran this refresh sequence:

- `claude plugin install superdev@superdev-dev --scope user` — reported already
  installed.
- `claude plugin uninstall superdev@superdev-dev --scope user --keep-data` — PASS.
- `claude plugin install superdev@superdev-dev --scope user` — PASS.
- `claude plugin update superdev@superdev-dev` — PASS; latest version 7.2.0.
- `claude plugin list` — Superdev 7.2.0, user scope, enabled.
- `cmp -s skills/subagent-driven-development/scripts/codex_worker/facade.py /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0/skills/subagent-driven-development/scripts/codex_worker/facade.py`
  — PASS, bytewise identical.
- `cmp -s skills/subagent-driven-development/scripts/codex_worker/commands.py /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0/skills/subagent-driven-development/scripts/codex_worker/commands.py`
  — PASS, bytewise identical.
- `test -x /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0/bin/codex-worker`
  — PASS.
- From a controller-created external `mktemp` cwd, the installed launcher `--help`
  and `daemon status` invocations both exited 0. Status was exactly one JSON object:
  default instance, stopped, zero workers.

The uninstall explicitly used `--keep-data`; no durable worker state or plugin data
was deleted. The `superdev-dev` marketplace remains pointed at
`/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade` pending branch
integration, after which the controller will restore the main-checkout source and
reverify installed 7.2.0.
