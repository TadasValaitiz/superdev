# Installed Superdev 7.3.0 transcript

Date: 2026-08-20

These are the controller's literal installed-product commands and complete relevant
outputs. No credentials or durable callback/worker records were read or deleted.

## Original state

Command: `claude plugin marketplace list`

Relevant complete marketplace record:

```text
❯ superdev-dev
  Source: Directory (/Users/tadas/Projects/superdev)
```

Command: `claude plugin list --json`

Relevant complete plugin object:

```json
{
  "id": "superdev@superdev-dev",
  "version": "7.2.0",
  "scope": "user",
  "enabled": true,
  "installPath": "/Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0",
  "installedAt": "2026-08-19T22:47:29.261Z",
  "lastUpdated": "2026-08-19T22:47:29.261Z"
}
```

Both commands exited 0 with empty stderr.

## Reversible worktree installation

Command: `claude plugin marketplace remove superdev-dev --scope user`

```text
✔ Successfully removed marketplace: superdev-dev (from user settings)
```

Exit 0; stderr empty.

Command: `claude plugin marketplace add /Users/tadas/Projects/superdev/.worktrees/codex-worker-claude-callbacks --scope user`

```text
Adding marketplace…✔ Successfully added marketplace: superdev-dev (declared in user settings)
```

Exit 0; stderr empty. `claude plugin marketplace list` then reported the exact
worktree directory. Removing the marketplace had already disassociated the old
install, so the attempted conservative uninstall was a measured refusal:

Command: `claude plugin uninstall superdev@superdev-dev --scope user --keep-data`

```text
✘ Failed to uninstall plugin "superdev@superdev-dev": Plugin "superdev@superdev-dev" not found in installed plugins
```

Exit 1; durable data was untouched. `claude plugin list --json` confirmed no Superdev
object, then this literal recovery command was used:

Command: `claude plugin install superdev@superdev-dev --scope user`

```text
Installing plugin "superdev@superdev-dev"...✔ Successfully installed plugin: superdev@superdev-dev (scope: user)
```

Exit 0; stderr empty. The complete selected object from `claude plugin list --json` was:

```json
{
  "id": "superdev@superdev-dev",
  "version": "7.3.0",
  "scope": "user",
  "enabled": true,
  "installPath": "/Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.3.0",
  "installedAt": "2026-08-20T15:16:43.604Z",
  "lastUpdated": "2026-08-20T15:16:43.604Z"
}
```

## Installed bytes and external-cwd surface

The following one-line checks all exited 0 with empty stderr:

```text
test -x /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.3.0/bin/codex-worker
cmp -s bin/codex-worker /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.3.0/bin/codex-worker
cmp -s skills/subagent-driven-development/scripts/codex-worker /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.3.0/skills/subagent-driven-development/scripts/codex-worker
cmp -s skills/subagent-driven-development/scripts/codex_worker/cli.py /Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.3.0/skills/subagent-driven-development/scripts/codex_worker/cli.py
```

The installed manifest read-back was:

```json
{"manifest": "/Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.3.0/.claude-plugin/plugin.json", "name": "superdev", "version": "7.3.0"}
```

From a fresh `mktemp -d` external cwd, installed `codex-worker --help` exited 0 and
listed `start,run,message,status,messages,history,interrupt,steer,goal,limits,daemon,model,session,turn`.
Installed `codex-worker --instance task8-installed-730 daemon status` exited 0 with:

```json
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"task8-installed-730","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/809319b1ace1c3edf3a5b109e4d584168b040d6382c5e96990a843710b8df4a9","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-809319b1ace1c3edf3a5/s","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/809319b1ace1c3edf3a5b109e4d584168b040d6382c5e96990a843710b8df4a9/daemon.log"},"status":"stopped","daemon_pid":null,"codex_pid":null,"worker_count":0,"readiness":null,"last_error":null}}
```

## Installed callback smoke

The committed live harness was imported with both `CLI` and `RAW_CLI` pointed at the
installed 7.3.0 cache, then `scenario_callback_common()` was called. Exit 0, stderr
empty, stdout:

```json
{"result": {"complete_inline_result": true, "delivery_claimed": false, "disabled": "disabled", "standalone": "unavailable", "terminal_event_id": "terminal-3a23b2bd7a00b2e7f41b314aa0f29310a2610712e07949cd6bd3f916a7b34d4a", "terminal_written": true}, "scenario": "callback-common", "status": "PASS", "transcript": ".superdev/codex-worker-live/20260820T151711.528777Z-39185-callback-common/transcript.jsonl"}
```

This is a local written/correlated receipt, not a transport-delivery claim.

## Exact restoration

Commands and complete outputs:

```text
$ claude plugin marketplace remove superdev-dev --scope user
✔ Successfully removed marketplace: superdev-dev (from user settings)
[exit 0]
$ claude plugin marketplace add /Users/tadas/Projects/superdev --scope user
Adding marketplace…✔ Successfully added marketplace: superdev-dev (declared in user settings)
[exit 0]
$ claude plugin install superdev@superdev-dev --scope user
Installing plugin "superdev@superdev-dev"...✔ Successfully installed plugin: superdev@superdev-dev (scope: user)
[exit 0]
```

The final selected `claude plugin list --json` object is the restored original product:

```json
{
  "id": "superdev@superdev-dev",
  "version": "7.2.0",
  "scope": "user",
  "enabled": true,
  "installPath": "/Users/tadas/.claude/plugins/cache/superdev-dev/superdev/7.2.0",
  "installedAt": "2026-08-20T15:17:51.612Z",
  "lastUpdated": "2026-08-20T15:17:51.612Z"
}
```

The 7.3.0 installed cache and executable remain present for reconstruction; the active
marketplace pointer and enabled plugin were restored to their original main-checkout
source/version. No uninstall or cleanup deleted durable worker/callback state.
