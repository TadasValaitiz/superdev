# Codex Worker Shared App-Server — CLI Surface

**Status:** FLEXIBLE exact surface under operator-locked global topology; D15/D17 provisional pending review
**Authority:** Public command and JSON contract for the design in
[`2026-08-28-codex-worker-shared-app-server-design.md`](./2026-08-28-codex-worker-shared-app-server-design.md).
The decision log remains authoritative for reasoning and drift arbitration.

## 1. Global command grammar

```text
codex-worker [--pretty] [--socket ABSOLUTE_PATH] COMMAND ...
```

- `--instance` is removed with a local usage error and migration guidance.
  `CODEX_WORKER_INSTANCE` has no routing effect and produces no ambient warning.
- `--socket` remains an expert/testing bypass for raw model/session/turn operations and raw
  daemon status. It is invalid for common worker commands and managed lifecycle/migration.
  It never selects or creates another public service and never implies an attach address.
- Without `--socket`, every operational command addresses one machine-local global service.
- Every client invocation emits exactly one JSON object on stdout. Success exits 0; an
  uncaught internal bug exits 1; local usage errors exit 2; and every typed operational
  refusal exits 3 with a literal runnable remedy. `daemon serve` remains stdout-silent.
- Local argument validation precedes service startup or network contact.

The global service owns exactly one public Codex-TUI gateway listener. Its default is:

```text
ws://127.0.0.1:4500
```

An explicit public `ws://HOST:PORT` listener is preserved unchanged by the service gateway.
`HOST` must be connectable as written: wildcard/unspecified hosts (`0.0.0.0`, `::`, `[::]`)
and port `0` are rejected. Port is `1..65535`; userinfo, path, query and fragment are absent.
The Codex child itself listens on an owner-only Unix-WebSocket path. `wss://` belongs at an
operator-owned TLS reverse proxy; `stdio://`, `off`, and public Unix paths are rejected for
this human-attach surface. A live generation's public listener is immutable: a different
request produces `service_config_conflict`, never a second service or silent restart.

## 2. Common worker commands

| Command | Purpose | Args (all) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `start` | create worker + first turn | `--name NAME` required (1–128 chars; no control/NUL/path separator); exactly one of `--prompt NONEMPTY_TEXT` / `--prompt-file READABLE_UTF8_PATH`; `--cwd EXISTING_ABS_DIR` required; mutually exclusive `--tier medium\|very-smart` (default `medium`) / `--model NONEMPTY_ID`; `--effort NONEMPTY_SUPPORTED_EFFORT` default `medium`; `--read-only` default false/full; `--goal NONEMPTY_TEXT<=4000` optional; `--token-budget POSITIVE_INT` optional and requires `--goal`; `--no-callback`; `--output-schema READABLE_JSON_OBJECT_PATH`; `--timeout FINITE_NONNEGATIVE_SECONDS` optional/no deadline; `--app-server-listen ws://HOST:PORT` optional/fixed default; top-level `--pretty`; `--socket` invalid | `StartWorkerCommand` | RECORD | EXISTS-REWORK |
| `run` | continue worker | `--name NAME` required; exactly one prompt input with the same validation; `--output-schema READABLE_JSON_OBJECT_PATH`; `--timeout FINITE_NONNEGATIVE_SECONDS` optional/no deadline; top-level `--pretty`; `--socket` invalid | `RunWorkerCommand` | RECORD | EXISTS-KEEP |
| `message` | proactive callback | `--name NAME` required; exactly one of `--message NONEMPTY_TEXT` / `--message-file READABLE_NONEMPTY_UTF8_PATH`; `--priority now\|next\|later` default `next`; `--cc-agent-name NONEMPTY_NAME` optional | `MessageWorkerCommand` | RECORD | EXISTS-KEEP |
| `status` | inspect worker | `--name NAME` required | `StatusWorkerCommand` | READ | EXISTS-REWORK |
| `messages` | recent messages | `--name NAME` required; `--tail POSITIVE_INT` default `1` | `MessagesWorkerCommand` | READ | EXISTS-KEEP |
| `history` | recent turns | `--name NAME` required; `--tail POSITIVE_INT` default `1` | `HistoryWorkerCommand` | READ | EXISTS-KEEP |
| `steer` | append active turn | `--name NAME` required; exactly one prompt input | `SteerWorkerCommand` | RECORD | EXISTS-REWORK |
| `interrupt` | interrupt active turn | `--name NAME` required | `InterruptWorkerCommand` | RECORD | EXISTS-REWORK |
| `goal set` | update native goal | `--name NAME` required; at least one of `--goal NONEMPTY_TEXT<=4000`, `--status active\|paused\|blocked\|usageLimited\|budgetLimited\|complete`, `--token-budget POSITIVE_INT` | `SetGoalCommand` | RECORD | EXISTS-KEEP |
| `goal show` | inspect native goal | `--name NAME` required | `ShowGoalCommand` | READ | EXISTS-KEEP |
| `limits` | inspect provider limits | no command args | `LimitsCommand` | READ | EXISTS-KEEP |

Unless a row states otherwise, common rows accept top-level `--pretty`, reject top-level
`--socket`, apply the same 1–128-character worker-name validator, and reject unknown args.
Prompt/message files must be readable UTF-8 and non-empty; local validation happens before the
global service is contacted or started.

### `start`

```text
codex-worker start --name NAME
  (--prompt TEXT | --prompt-file PATH)
  --cwd ABSOLUTE_PATH
  [--tier very-smart|medium | --model MODEL]
  [--effort EFFORT]
  [--read-only]
  [--goal TEXT]
  [--token-budget INTEGER]
  [--timeout SECONDS]
  [--output-schema PATH]
  [--no-callback]
  [--app-server-listen ADDRESS]
```

`NAME` is globally unique, not scoped to a Claude session. The command ensures the global
service, creates a worker mapping only when the name is absent, starts the first turn, waits
for the configured observation outcome, and returns its complete projection. Reusing an
existing name continues that worker only through `run`; `start` refuses the collision.

`--cwd` remains explicit for the initial message. The Claude ambient working directory may
be shown as a suggestion but is not silently substituted when the flag is absent. Claude
environment values are callback metadata only; `CLAUDE_EFFORT` is never inherited.
When neither policy selector is present, `--tier medium` is the SEED-DEFAULT. A token budget
without an initial goal is a local exit-2 error. These laws preserve the existing validation
contract except for the operator-requested explicit initial cwd.

### `run`

```text
codex-worker run --name NAME
  (--prompt TEXT | --prompt-file PATH)
  [--timeout SECONDS]
  [--output-schema PATH]
```

`run` continues the globally named worker and inherits its immutable cwd/model/effort/access,
goal and callback binding. It may reattach a durable detached thread before starting a turn.

### Observation and control

```text
codex-worker status --name NAME
codex-worker messages --name NAME [--tail INTEGER]
codex-worker history --name NAME [--tail INTEGER]
codex-worker steer --name NAME (--prompt TEXT | --prompt-file PATH)
codex-worker interrupt --name NAME
codex-worker message --name NAME (--message TEXT | --message-file PATH)
  [--priority now|next|later] [--cc-agent-name NAME]
```

These commands are globally routed by `NAME`. `steer` and `interrupt` bind the currently
observed turn ID before the app-server call; a successor turn cannot be controlled by a stale
request. Remote-TUI and worker operations have equal authority. Codex app-server responses
are authoritative, and losing races receive typed active/not-active refusals.

Goal and capacity commands retain their current arguments and semantics:

```text
codex-worker goal set --name NAME [--goal TEXT]
  [--status active|paused|blocked|usageLimited|budgetLimited|complete]
  [--token-budget INTEGER]
codex-worker goal show --name NAME
codex-worker limits
```

At least one update field is required for `goal set`.

### 2b. Composition rationale

The split between `start` and `run` remains because immutable policy, cwd, goal and callback
capture belong only to creation; follow-ups deliberately stay short. Observation remains
separate from control because reading state does not authorize mutation. D15 changes only the
selector/topology fields required by D6–D11 and adds attach projection; it does not churn the
mature worker, goal, limit or callback vocabulary.

## 3. Service lifecycle commands

| Command | Purpose | Args (all) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `daemon start` | ensure global service | `--app-server-listen CONNECTABLE_ws://HOST:PORT` optional/fixed default; top-level `--pretty`; `--socket` invalid | `StartServiceCommand` | RECORD | EXISTS-REWORK |
| `daemon status` | inspect managed service without starting | no command args; top-level `--pretty`; no `--socket` in this form | `StatusServiceCommand` | READ | EXISTS-REWORK |
| `--socket ABS_PATH daemon status` | inspect explicit expert RPC endpoint | top-level absolute `--socket` required; `--pretty`; no command args | existing raw `daemon/status` | READ | EXISTS-KEEP raw |
| `daemon serve` | hidden internal foreground server | `--state ABS_PATH` optional platform default; `--codex-bin PATH_OR_NAME` default `codex`; `--event-limit POSITIVE_INT` default `1000`; `--app-server-listen CONNECTABLE_ws://HOST:PORT` optional/fixed default; top-level `--socket ABS_PATH` optional internal RPC endpoint; `--pretty` invalid | `ServeServiceCommand` | RECORD | INTERNAL (suppressed from public family help) |
| `daemon restart` | supervised restart | `--app-server-listen CONNECTABLE_ws://HOST:PORT` optional; `--force`; top-level `--pretty`; `--socket` invalid | `RestartServiceCommand` | FILTER + RECORD | NEW |
| `daemon stop` | supervised stop | `--force`; top-level `--pretty`; `--socket` invalid | `StopServiceCommand` | FILTER + RECORD | EXISTS-REWORK |
| `daemon shutdown` | old unguarded shutdown | none | — | — | REMOVED |

### Start and inspect

```text
codex-worker daemon start [--app-server-listen ADDRESS]
codex-worker daemon status
codex-worker daemon serve [--app-server-listen ADDRESS]
```

`daemon start` is idempotent only when the live service is compatible and its listener equals
the requested/default address. `daemon serve` is an internal foreground entry point used by
the manager and packaging tests. `daemon status` never starts the service.

The status result includes:

```json
{
  "status": "ready",
  "service_version": "8.1.0",
  "pid": 12345,
  "app_server_pid": 12346,
  "listener": "ws://127.0.0.1:4500",
  "exposure": "loopback",
  "auth": "none",
  "attach_command": "codex --remote ws://127.0.0.1:4500",
  "worker_count": {
    "value": 2,
    "source": "codex-worker registry",
    "availability": "derived",
    "basis": {
      "active_names": [], "idle_names": ["build-a", "review-a"],
      "active_count": 0, "idle_count": 2, "total_count": 2
    }
  },
  "active_turn_count": {
    "value": 0,
    "source": "codex app-server inventory",
    "availability": "derived",
    "basis": {"items": []}
  },
  "migration": {"status": "complete", "conflict_count": 0},
  "durable_state": "preserved"
}
```

Numbers in this illustrative schema are **SEED-ILLUSTRATIVE**, not measurements.
The count envelopes are reconstructable: `worker_count.value` equals the unique names in
its basis, and `active_turn_count.value` equals the active inventory items. Each active item
retains worker/session/thread/turn identity, origin, and active flags. Stopped status derives
its worker basis from durable registry names and reports active inventory as available and
empty; it never invents live activity.

Every public leaf command's own `--help` ends with a `Limits:` block. The stop/restart blocks
state that maintenance is machine-wide, active work refuses without `--force`, and force may
interrupt every listed identity. Raw session/turn help states that the managed service must
already be strictly ready and is never auto-started by those commands. The hidden foreground
`daemon serve` entry point is not a public recovery action.

### Restart and stop — supervised maintenance only

```text
codex-worker daemon restart [--app-server-listen ADDRESS] [--force]
codex-worker daemon stop [--force]
```

These commands are dangerous maintenance controls. Without `--force`, either refuses when
any turn is active. With `--force`, the result enumerates every affected name/session/thread/
turn before terminating the selected global runtime. The skill and normal automation MUST
NOT invoke stop or restart as cleanup. A caller disconnect never stops the service.

`daemon shutdown` is removed from the public grammar. The internal RPC shutdown method uses
the same active-work guard and is not a shortcut around it.

### Version replacement

An installed-client/service-version mismatch follows one rule:

1. zero active turns: the manager replaces the selected global runtime, preserves durable
   mappings, and verifies the new immutable service version;
2. one or more active turns: `service_busy` refuses replacement and identifies active work;
3. no operation ever kills another process merely because it owns port 4500.

## 4. Legacy migration commands

| Command | Purpose | Args (all) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `migration status` | inspect import/conflicts | no command args; top-level `--pretty`; `--socket` invalid | `MigrationStatusCommand` | READ | NEW |
| `migration resolve` | select/import a candidate | `--name NAME` required; `--thread NONEMPTY_THREAD_ID` required; `--as-name NEW_VALID_GLOBAL_NAME` optional; top-level `--pretty`; `--socket` invalid | `ResolveLegacyConflictCommand` | RECORD | NEW |

```text
codex-worker migration status
codex-worker migration resolve --name NAME --thread THREAD_ID [--as-name NEW_NAME]
```

The first global-service start scans the known legacy instance registries. Unique names are
imported. Byte-equivalent duplicate mappings are deduplicated. Divergent duplicate names are
quarantined in a durable conflict ledger and cannot be addressed until explicitly resolved.

Without `--as-name`, resolution selects one recorded thread for the conflicted global name.
With `--as-name`, it imports that candidate under a new globally unique name while leaving the
original conflict unresolved. Neither form deletes an unselected legacy record; the ledger
records the choice and source identities. `migration status` is read-only and reports imported,
deduplicated and conflicted counts plus resolution actions.

## 5. Raw compatibility commands

Existing raw families remain available for diagnostics and recovery:

```text
codex-worker model list
codex-worker session start|list|resume ...
codex-worker turn start|wait|status|events|steer|interrupt ...
```

Without `--socket`, they address the global service and must complete the same exact-ready
version handshake before stateful RPC. With explicit `--socket`, they preserve the current
expert bypass and do not auto-start or manage a daemon. Their detailed arguments and JSON
models remain governed by the preceding Codex-worker CLI surface specification except where
this document changes global selection and lifecycle.

The inherited exhaustive raw contract is
[`2026-08-18-codex-worker-server-cli-surface.md`](./2026-08-18-codex-worker-server-cli-surface.md).
This work changes only endpoint selection: remove `--instance`, preserve top-level
`--socket ABSOLUTE_PATH`, and require exact-ready global service status before managed RPC.

### 5b. Composition rationale

Raw families remain because they are the lossless recovery/debug boundary beneath ergonomic
workers. They do not gain listener flags: service configuration is lifecycle state, not a
property of a model/session/turn request. Explicit `--socket` remains the intentional escape
hatch for tests and expert-owned endpoints (D15).

## 6. Identity and attach projection

Every successful common `start`, `run`, and `status` result includes this stable block:

```json
{
  "name": "review-7f3a",
  "session_id": "8e7f2c63-...",
  "thread_id": "01a048d2-...",
  "turn_id": "01a048d3-...",
  "attach": {
    "listener": "ws://127.0.0.1:4500",
    "attach_command": "codex --remote ws://127.0.0.1:4500",
    "resume_command": "codex --remote ws://127.0.0.1:4500 resume 01a048d2-..."
  }
}
```

Values are **SEED-ILLUSTRATIVE**. `session_id` is the Codex-worker durable mapping ID;
`thread_id` is the Codex conversation ID accepted by `codex resume` and remote attach. The
two are never presented as interchangeable. `turn_id` is nullable when no turn exists.

## 7. Typed failures added by this surface

| JSON-RPC code | kind | Meaning and required recovery detail |
|---:|---|---|
| `-32039` | `address_in_use` | Default/requested listener is occupied by an unverified peer; include listener and read-only inspection actions, never kill/fallback. |
| `-32040` | `service_busy` | Stop/restart/version replacement would interrupt active work; include every active name/thread/turn and retry/status actions. |
| `-32041` | `legacy_name_conflict` | Global name has divergent legacy mappings; include every source identity/thread and an exact `migration resolve` action. |
| `-32042` | `service_config_conflict` | Live service listener differs from requested listener; include both addresses and status/maintenance guidance. |

Existing typed faults retain their codes and one-object envelope. No traceback, credential,
callback token, or raw auth value may cross stdout JSON.

## 8. Operator journeys

### Start, attach, and share control

```text
codex-worker start --name review-7f3a --cwd /repo --prompt "Review the branch"
# Copy result.attach.resume_command into a terminal.
codex --remote ws://127.0.0.1:4500 resume <thread_id>
```

The remote TUI and worker see the same app-server thread. Either can start a follow-up,
steer, or interrupt; simultaneous conflicts are resolved by authoritative app-server replies.

### Parallel Claude callers

Independent callers use distinct globally unique names such as `audit-a91c`, `tests-41de`,
and `docs-27b0`. They do not need shared Claude session IDs. Their shell processes may run
concurrently and receive results in completion order.

### Occupied port

If another process owns `127.0.0.1:4500`, ordinary start returns `address_in_use`. The process
is preserved and no alternate port is selected. An operator may deliberately choose another
WebSocket address with `--app-server-listen` before the service generation starts.

### Upgrade and maintenance

An idle incompatible service is replaced automatically. Active work blocks replacement. An
operator who explicitly accepts interruption may use `daemon restart --force`; the skill must
never infer that permission from task completion, caller exit, or stale callback state.

## 9. Compatibility boundary

- Source-level Python APIs remain internal and may be refactored behind the public contract.
- Old instance arguments are an intentional breaking removal; a local usage error points to
  global names and migration status rather than silently honoring the old scope.
- Legacy durable data is migrated or quarantined, never silently discarded.
- `stdio://` and private Unix WebSocket remain internal app-server transports; the public
  shared-control product path is the service-owned WebSocket gateway.
- Non-loopback or otherwise exposed listener security is the operator's responsibility for
  this internal tool; status must label the exposure honestly.

## 10. Docs to update in the same branch

| Doc/surface | Required change |
|---|---|
| `skills/subagent-driven-development/SKILL.md` | global preflight/naming/attach handoff; forbid routine stop and instance use |
| `skills/subagent-driven-development/references/codex-worker.md` | shared-control workflow, maintenance warning, migration |
| `skills/subagent-driven-development/references/codex-tools.md` | installed command examples without instance routing |
| `codex-worker --help` and family help | new/removed flags, migration/restart families, danger text |
| live/checkride docs | permanent-service cleanup rules and shared-client scenarios |

## 11. Delta summary

The surface removes public multi-instance routing, makes one global WebSocket-backed service
implicit, adds a listener option only at service creation/maintenance, returns exact remote
attach/resume routes with every known Codex thread, adds explicit migration inspection and
resolution, and replaces routine shutdown with guarded supervised stop/restart. Existing
worker, goal, callback and raw diagnostic operations remain, now addressing the singleton
service or an explicit expert `--socket`.
