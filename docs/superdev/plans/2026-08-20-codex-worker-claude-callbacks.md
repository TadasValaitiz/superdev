# Codex worker → Claude callbacks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable local callback relay so named Codex workers automatically notify their originating Claude Code room at terminal completion and can proactively send non-blocking messages through a short instance-qualified CLI command.

**Architecture:** The existing managed daemon remains the sole product-supported relay. A strict secret capture is bound once to the durable worker session; an owner-only callback store retains bindings, an event-ID-keyed terminal outbox, and immutable oversized-result artifacts. A hardened stdlib Claude transport revalidates the captured process identity before every write, while the façade composes automatic terminal events and proactive `message` requests without changing raw Codex methods or turn truth.

**Tech Stack:** Python 3.9-compatible stdlib, frozen dependency-free strict dataclass models, AF_UNIX JSON-RPC/NDJSON, `unittest`, shell checkride scripts, Markdown skill/reference docs.

**Execution:** subagent-driven

**Mode:** autonomous

**Context pack** — the artifacts downstream workers read:
- Spec: `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-design.md` · Decision log: `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-decisions.md`
- Domain model: design §5.1; capture/store/transport/dispatcher areas: §5.2–5.7
- CLI surface: `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-cli-surface.md`
- Prior art: `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-design.md`, `docs/superdev/plans/2026-08-19-codex-worker-command-ergonomics.md`, `docs/superdev/checkrides/2026-08-19-codex-worker-command-checkride.md`
- Measured transport reference: `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/docs/reference/claude-code-messaging-protocol.md`
- Measured sender prototype: `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/scripts/send_to_claude.py`

## Global Constraints

- Zero new runtime dependencies; production and probe code are stdlib-only and remain Python 3.9-compatible (no `X | Y` annotations in Superdev production code).
- Event schema is exactly `codex-worker.claude-callback/v1`; event names are exactly `turn_terminal`, `turn_terminal_reference`, and `worker_message`.
- Callback faults are the closed block `-32031` through `-32037` from D22; callback-store persistence reuses `-32011 registry_error`.
- The final Claude user line is capped at 1,048,576 JavaScript UTF-16 code units, counted as `len(line.encode("utf-16-le")) / 2` excluding newline.
- Automatic terminal callbacks use a durable at-least-once **write** policy: all non-written entries retry with the same event ID; recorded `written` entries never intentionally replay; delivery is never claimed.
- Proactive `message` is one bounded attempt, never autostarts a stopped daemon, never waits for a reply, and an explicit retry is a new event.
- Injected proactive commands always carry exact global `--instance <WorkerView.instance>` plus `--name <WorkerView.name>`, with every dynamic shell argument quoted; `cc-agent-name` changes one proactive destination only. Root-only unavailable capture receives this override guidance; null and disabled capture do not.
- `disabled` forbids default and override sends; `unavailable` may resolve a one-message override only through its safely persisted start-time Claude config root.
- The product scrubs `CLAUDE_CODE_MESSAGING_SOCKET` and `CLAUDE_CODE_MESSAGING_TOKEN` from Codex app-server children and never exposes captured credentials through public JSON, prompts, logs, or recovery actions. This is not a same-UID filesystem sandbox (D23).
- Raw session/turn RPC, native Claude dispatch, two-tier model selection, full/read-only worker access, goal/limits proxies, and non-destructive daemon stop retain their existing meaning. No MCP or cloud transport is added.
- Product code/spec live in `/Users/tadas/Projects/superdev`; technical probes/reference/evidence live in `/Users/tadas/Projects/ai-ethics/ai-trading-calibration` and are committed independently (D14, D26).
- Skill/reference guidance follows D24: focused structural checks plus fresh semantic reviewer agents; do not run a large pressure-scenario campaign. Python production changes still use strict RED→GREEN TDD.
- Release version is 7.3.0 and must be produced by existing release tooling, then package/sync/reinstall/audit checked (D25).

**Test lanes:** fast (the gate): `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` · slow-by-area (separate killable commands): callback scenarios added to `python3 tests/codex-worker/live_broker_check.py --scenario <name>`, the real Claude caller `bash tests/codex-worker/live_claude_check.sh`, and the CLI checkride executor/evaluator · scheduled sweep: none declared by this repository. Every commit runs the fast gate plus focused owned tests; each slow callback scenario runs separately at its owning gate.

**Engineering patterns:** `skills/engineering-patterns/python-patterns.md` (BINDING), with the existing command-façade D40 substitution of dependency-free frozen strict dataclasses for Pydantic. Implementers read §§1–4, 6, 8–11 before coding; knowing departures are reportable deviations.

## The Through-Line

The build starts by freezing the public and secret value vocabulary because every later layer consumes those exact models and fault codes. Task 1 is therefore LOAD-BEARING: it defines capture nullability, event/attempt/status projections, and proactive request/response contracts. Task 2 is the second LOAD-BEARING seam: durable bindings, event-ID-keyed outbox entries, and write-once artifacts must be trustworthy before any socket is opened. Task 3 then implements the only effectful Claude boundary—capture discovery, process-identity revalidation, deterministic envelope encoding, and credential-scrubbed Codex spawning.

With those seams stable, Task 4 composes automatic completion events through a single dispatcher, preserving terminal truth while making retries durable. Runtime commits and publishes copy-isolated terminal notifications; request and dispatcher share one projection claim, while the healthy dispatcher owns normal persistence/retry and bounded shutdown fallback owns one enqueue/fault attempt. Task 5 exposes the proactive common RPC/CLI and start-time capture with the exact instance-qualified instruction Codex sees. Task 6 independently proves the raw event shapes in the source-research repository; it is evidence, not production authority. Task 7 teaches SDD users the new capability without replacing native Claude or adding polling ceremony. Task 8 drives the installed product through real Codex and Claude, records every acceptance receipt, bumps 7.3.0, and performs the CLI checkride.

The first five tasks are intentionally sequential because each consumes the prior task's public seam. Probe and documentation details may vary internally, but their event/command contracts may not. When reality diverges, follow the affected D# revisit hook, append a build-phase decision to the shared decision log, and update every downstream Consumes/Produces block before continuing. A change that weakens no-poll completion, stable origin routing, the credential-propagation boundary, raw compatibility, or exact CLI semantics breaks this through-line and returns to the operator.

## Acceptance (anchored — do not restate here)

This plan discharges design UC1–UC7 and AH1–AH11. Task 8 fills each §9 receipt with a re-runnable deterministic test, real callback scenario, tracked probe transcript, installed CLI transcript, or file:line evidence. An unanswered hint is named and filed as an owned backlog item under autonomous mode; it is never silently dropped.

---

### Task 1: Callback command and wire contracts

**Role in the build:** Define the LOAD-BEARING strict models and closed faults consumed by persistence, transport, façade, RPC, CLI, and status (R1–R10; D15–D22).

**Read first:** design §5.1 and §6 D15–D22; CLI surface §§1–4 and §7; `skills/engineering-patterns/python-patterns.md` §§2, 4, 6, 10.

**Files:**
- Modify: `skills/subagent-driven-development/scripts/codex_worker/commands.py`
- Modify: `tests/codex-worker/test_commands.py`

**Interfaces:**
- Consumes: existing `StrictModel`, `StartWorkerRequest`, `WorkerStatusResponse`, `WorkerView`, `FacadeFaultCode`, and exact dataclass serialization.
- Produces: `CallbackState`, `CallbackAttemptState`, `MessagePriority`, `CallbackCapture`, `MessageWorkerRequest`, `CallbackAttemptView`, `CallbackStatusView`, `CallbackSendResponse`; reworked `StartWorkerRequest(no_callback, callback_capture)` and `WorkerStatusResponse(callback)`; exact callback fault enum/kind mappings.

- [ ] **Step 1: Write focused RED contract tests**

Add table-driven tests that construct and round-trip every new strict model, reject extra keys, enforce the full/root-only/null capture matrix, reject partial capture and uppercase/wrong-length tokens, enforce non-empty message and enum priority, pin fault codes `-32031..-32037`, and prove public callback views contain no socket/token/config-root fields. Use this exact capture fixture shape:

```python
capture = CallbackCapture(
    target_socket="/tmp/cc-socks/123.sock",
    child_token="a" * 32,
    claude_session_id="session-1",
    claude_pid=123,
    claude_proc_start="measured-start",
    claude_config_dir="/tmp/claude-config",
)
root_only = CallbackCapture(None, None, None, None, None, "/tmp/claude-config")
```

- [ ] **Step 2: Run RED and retain the expected failure**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_commands.py -v`

Expected: failures/import errors name the missing callback types and absent `StartWorkerRequest` / `WorkerStatusResponse` fields.

- [ ] **Step 3: Implement the minimal closed models**

Add enums and frozen strict dataclasses, then extend `_check_contract`/custom loaders only where nested capture parsing requires it. The cross-field rule is explicit:

```python
route = (self.target_socket, self.child_token, self.claude_session_id,
         self.claude_pid, self.claude_proc_start)
if any(item is None for item in route) and not all(item is None for item in route):
    raise ValueError("callback capture identity must be fully populated or fully absent")
```

Add all seven exact callback `FacadeFaultCode` members and `FACADE_FAULT_KINDS` entries. Preserve old field order/serialization except for the spec's additive fields.

- [ ] **Step 4: Run GREEN and compatibility contracts**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_commands.py tests/codex-worker/test_rpc_cli.py -v`

Expected: all tests pass with pristine warning-strict output.

- [ ] **Step 5: Run fast gate and commit**

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Commit:

```bash
git add skills/subagent-driven-development/scripts/codex_worker/commands.py \
  tests/codex-worker/test_commands.py
git commit -m "feat(codex-worker): define callback contracts"
```

### Task 2: Durable callback store and immutable artifacts

**Role in the build:** Persist stable origin bindings, every non-written terminal event, attempt evidence, and complete oversized results without weakening existing registry durability (R2, R3, R7, R8; D16, D17, D21).

**Read first:** design §5.1 invariants, §5.2, §5.4, §5.7; decision log D16, D17, D21; `registry.py:72-148`; engineering patterns §§3, 4, 8, 10.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/callback_store.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/instance.py`
- Create: `tests/codex-worker/test_callback_store.py`
- Modify: `tests/codex-worker/test_instance.py`

**Interfaces:**
- Consumes: Task 1 callback enums/views/capture, `WorkerView`, `CompletionResponse`, instance durable directory and atomic registry conventions.
- Produces: frozen internal `CallbackBinding`, `CallbackEvent`, `CallbackOutboxState`, `CallbackOutboxEntry`, `CallbackArtifact`; `CallbackStore.bind`, `binding`, `enqueue_terminal`, `pending`, `record_failed`, `record_written`, `status_view`, and `publish_artifact`; additive `InstancePaths.callback_path` / `callback_artifact_dir`.

- [ ] **Step 1: Write RED persistence and artifact tests**

Cover missing/zero-byte v1 initialization, exact `0600` callback file and `0700` artifact directory, malformed non-empty preservation, foreign owner/mode refusal via injected stat seams, file and parent fsync ordering, full/root-only/disabled binding round trips, multiple pending events for one worker, stable same-ID retry counts, written non-replay, and daemon-stop-neutral persistence. Add artifact tests that assert canonical JSON bytes, SHA-256/size read-back, owner-only mode, same-content insert-or-verify, and different-content collision refusal.

- [ ] **Step 2: Run RED**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_callback_store.py tests/codex-worker/test_instance.py -v`

Expected: import failure for `callback_store` and absent callback instance paths.

- [ ] **Step 3: Implement strict records and atomic store**

Use frozen dataclasses/closed validators and one JSON schema version. The store API must serialize state changes under one lock and use temp-write → file fsync → `os.replace` → parent fsync. The event record contains the complete bounded callback event before send:

```python
@dataclass(frozen=True)
class CallbackOutboxEntry:
    event_id: str
    session_id: str
    event: Optional[CallbackEvent]
    state: CallbackOutboxState
    attempt_count: int
    last_error: Optional[str]
```

`CallbackOutboxState` is closed to `pending|written`; a failed transport attempt leaves
the entry pending and records the public `CallbackAttemptState.failed` evidence separately.
`event` is required while pending and may become null only after the written marker is
durably committed. Never overwrite one event with a later turn.

- [ ] **Step 4: Implement write-once artifact publication**

Canonicalize the public completion JSON with sorted keys/fixed separators and newline, compute SHA-256 and byte size, write owner-only through a temporary file, fsync, publish without replacing different bytes, verify final inode/mode/digest/size, and fsync the parent. Return only `CallbackArtifact(event_id, path, sha256, size_bytes)`. A written reference event may release its inline outbox payload, but the referenced artifact itself remains readable and immutable; daemon stop and normal outbox compaction never delete it.

- [ ] **Step 5: Run GREEN, fast gate, and commit**

Run focused: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_callback_store.py tests/codex-worker/test_instance.py -v`

Run fast: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Commit:

```bash
git add skills/subagent-driven-development/scripts/codex_worker/callback_store.py \
  skills/subagent-driven-development/scripts/codex_worker/instance.py \
  tests/codex-worker/test_callback_store.py tests/codex-worker/test_instance.py
git commit -m "feat(codex-worker): persist callback outbox"
```

### Task 3: Hardened Claude transport and child-environment scrubbing

**Role in the build:** Convert one validated callback event into the measured Claude 2.1.237 wire write while binding the default to the exact captured process and preventing product-managed credential propagation to Codex (R5, R6, R9, R10; D15, D20, D21, D23, D27, D28).

**Read first:** design §5.2–5.3 and §5.7; CLI §4b; decision log D15, D20, D21, D23, D27, D28; measured protocol reference §§2–4, 6, 9; engineering patterns §§3, 4, 9, 10.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/claude_transport.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/app_server.py`
- Create: `tests/codex-worker/test_claude_transport.py`
- Modify: `tests/codex-worker/test_app_server_runtime.py`

**Interfaces:**
- Consumes: `CallbackCapture`, Task 2 bindings/events, persisted start-time config root, existing safe-path/owner conventions.
- Produces: `capture_from_env(env) -> Optional[CallbackCapture]`, `ClaudeTransportDeps`, `ClaudeTransport.validate_capture(capture) -> CallbackCapture`, `ClaudeTransport.encode_user_line`, `ClaudeTransport.send(binding, event, cc_agent_name) -> CallbackAttemptView`, closed transport-to-façade fault conversion, and `_codex_child_env`.

- [ ] **Step 1: Write RED capture, adversarial socket, and envelope tests**

Use temp owner-only Claude config/session roots and real local AF_UNIX listeners. Cover full capture, root-only capture, null capture, ambiguous/malformed registry entries, exact session/PID/procStart/socket matching, PID/socket reuse, symlinks, foreign/permissive files, unsafe ancestors, zero/multiple override names, missing peer key, disabled/unavailable state rules, auth/user line order, half-close, and no `session_id`. Call `validate_capture` directly with structurally valid but forged RPC capture values and prove it refuses them before persistence; full captures must independently match the live registry/process/endpoint, while root-only captures must independently revalidate their safe canonical config root.

Pin D27 with assertions:

```python
self.assertEqual(user["msg_id"], event.event_id)
self.assertEqual(str(CALLBACK_UUID_NAMESPACE), "5b290fd0-2df0-5c73-980f-04f284476f55")
self.assertEqual(user["uuid"], str(uuid.uuid5(CALLBACK_UUID_NAMESPACE, event.event_id)))
self.assertEqual(user["from"], "uds:" + binding.target_socket)
self.assertEqual(user["from_mode"], "bypass")
```

Pin the cross-repository fixture `event-fixture-1 -> 740cb30c-652d-5f4f-bc30-36c14a48d007`.
For a root-only unavailable binding plus named override, assert `from` is absent while
`from_mode` remains `bypass`; never substitute the destination socket. Add ASCII, BMP,
and non-BMP boundary tests against the exact final serialized user line and
`callback_payload_too_large`.

- [ ] **Step 2: Write RED child-environment test and run focused RED**

Have the injected `Popen` capture `env`; assert socket/token are absent while harmless metadata and PATH remain. Run:

`python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_claude_transport.py tests/codex-worker/test_app_server_runtime.py -v`

Expected: missing transport module and inherited credential assertions fail.

- [ ] **Step 3: Implement capture and strict resolver**

Resolve only the start-time canonical config root. Full capture requires one registry record matching all ambient identity fields, the documented `<pid>.sock` basename invariant, and a safe live endpoint; a safe root without a full identity returns root-only capture; no safe root returns null. `validate_capture` is the daemon-side trust boundary: it performs the same independent safe-root and, for full captures, exact live registry/process/endpoint/basename checks on the RPC value before any bind. Revalidate the exact captured registry identity again before each default write. For override, select exactly one live `name` with the same basename invariant, derive the peer-key digest with `os.path.abspath` (not `realpath`), and validate owner/type/mode/ancestors before reading its 32-hex peer token.

- [ ] **Step 4: Implement deterministic encoder/write and scrub spawn env**

Build compact `allow_nan=False` JSON, count UTF-16 units before connect, write auth then user lines with `sendall`, half-close, and report only `written` after all bytes are accepted. Convert early errors to the closed callback faults; never claim delivery. In `CodexAppServer`, pass an explicit copy of `os.environ` with the two messaging credential keys removed.

- [ ] **Step 5: Run GREEN, fast gate, and commit**

Run focused: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_claude_transport.py tests/codex-worker/test_app_server_runtime.py -v`

Run fast: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Commit:

```bash
git add skills/subagent-driven-development/scripts/codex_worker/claude_transport.py \
  skills/subagent-driven-development/scripts/codex_worker/app_server.py \
  tests/codex-worker/test_claude_transport.py tests/codex-worker/test_app_server_runtime.py
git commit -m "feat(codex-worker): add Claude callback transport"
```

### Task 4: Terminal callback dispatcher and façade lifecycle

**Role in the build:** Turn authoritative `CompletionResponse` values into durable inline/reference notifications without polling, loss-by-overwrite, duplicate concurrent consumers, or mutation of Codex terminal truth (R1–R3, R7, R8; D1, D7, D16, D17, D19).

**Read first:** design §5.4 and §5.7; CLI §4b and normal no-poll workflow; Task 2/3 public interfaces; engineering patterns §§3–5, 8, 10.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/callback_dispatcher.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/facade.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/runtime.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/cli.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/rpc.py`
- Create: `tests/codex-worker/test_callback_dispatcher.py`
- Modify: `tests/codex-worker/test_facade.py`
- Modify: `tests/codex-worker/test_runtime.py`
- Modify: `tests/codex-worker/test_rpc_cli.py`

**Interfaces:**
- Consumes: Task 2 store/artifacts, Task 3 transport, `CompletionResponse`, broker-created `SessionRecord` and managed daemon lifecycle.
- Produces: `RuntimeStore.add_terminal_observer` plus exact-turn terminal snapshot lookup, `TerminalCallbackDispatcher.start/observe_turn/queue/shutdown`, stable event builder, façade callback binding before first turn, terminal observation independent of the client wait, and redacted status projection with `pending_terminal_count`.

- [ ] **Step 1: Write RED dispatcher and façade-order tests**

Cover inline completed/failed/interrupted events, no event at the instant of wait timeout followed by an event when that exact turn later becomes terminal, completion-before-observer-registration, observer-registration/concurrent-completion dedupe, artifact reference on oversized final envelope, enqueue-before-connect ordering, exactly one in-process consumer per event, multiple pending turns, same-ID restart recovery, increasing attempt count, written non-replay, bounded shutdown, and callback failures leaving the returned completion byte-for-byte unchanged. Add storage-failure tests proving first turn does not start and `-32011` includes known worker/thread recovery IDs.

- [ ] **Step 2: Run RED**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_callback_dispatcher.py tests/codex-worker/test_facade.py tests/codex-worker/test_runtime.py tests/codex-worker/test_rpc_cli.py -v`

Expected: missing dispatcher/store dependencies and absent callback status fields.

- [ ] **Step 3: Implement event builder and single dispatcher**

Build the exact v1 envelope from the public `CompletionResponse.to_dict()`. Derive terminal event ID deterministically from session ID, turn ID, and event kind. Persist before wake-up. Add a non-blocking RuntimeStore terminal-observer seam that publishes the immutable exact `TurnSnapshot` only after runtime state is committed and invokes observers outside runtime locks. The dispatcher owns all automatic sends, serializes attempts per event ID, retries only non-written entries with bounded interruptible backoff, and records safe failure reasons/attempt counts.

- [ ] **Step 4: Integrate binding, terminal hook, status, and daemon lifecycle**

Extend `FacadeDeps` with callback store/dispatcher. In `start`, pass the incoming capture through Task 3's daemon-side `validate_capture`, then persist enabled/disabled/unavailable binding after broker session creation/policy promotion and before the first turn. After `broker.start_turn` returns its exact turn ID, register immutable projection context (`worker`, schema, start time, recovery) with `observe_turn`; registration happens before the client wait and immediately queries RuntimeStore's exact-turn terminal snapshot to close the completion-before-registration race. Runtime terminal observers enqueue from that saved context even after `_start_and_wait` has returned `wait_timeout`; stable event/store insertion makes the query-versus-callback overlap idempotent. The synchronous path projects and returns the same completion; the dispatcher owns callback queueing, including the bounded persist-once fallback that `completion_for()` invokes only when its worker is unavailable. Add callback status to `status`. Wire store/transport/dispatcher in `_serve`; start recovery after server construction, and shut the dispatcher down before closing transport/store/Codex.

- [ ] **Step 5: Run GREEN, fast gate, and commit**

Run focused: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_callback_dispatcher.py tests/codex-worker/test_facade.py tests/codex-worker/test_runtime.py tests/codex-worker/test_rpc_cli.py -v`

Run fast: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Commit:

```bash
git add skills/subagent-driven-development/scripts/codex_worker/callback_dispatcher.py \
  skills/subagent-driven-development/scripts/codex_worker/facade.py \
  skills/subagent-driven-development/scripts/codex_worker/runtime.py \
  skills/subagent-driven-development/scripts/codex_worker/cli.py \
  skills/subagent-driven-development/scripts/codex_worker/rpc.py \
  tests/codex-worker/test_callback_dispatcher.py tests/codex-worker/test_facade.py \
  tests/codex-worker/test_runtime.py \
  tests/codex-worker/test_rpc_cli.py
git commit -m "feat(codex-worker): dispatch terminal callbacks"
```

### Task 5: Proactive `message` CLI and exact worker initialization

**Role in the build:** Expose the short fire-and-continue command Codex can invoke during an active turn, with one-message override and exact daemon/worker routing (R4, R5, R10, R11; D4, D5, D9, D10, D13, D18, D20–D22).

**Read first:** design §5.5–5.6; entire CLI companion §2–4 and §6–7; decision log D18–D22; engineering patterns §§4, 6, 7, 10.

**Files:**
- Modify: `skills/subagent-driven-development/scripts/codex_worker/facade.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/rpc.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/cli.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/projection.py`
- Modify: `tests/codex-worker/test_facade.py`
- Modify: `tests/codex-worker/test_rpc_cli.py`
- Modify: `tests/codex-worker/test_facade_integration.py`

**Interfaces:**
- Consumes: `MessageWorkerRequest`, `CallbackSendResponse`, callback store and Task 3 transport, exact managed instance selection, existing one-object CLI handling.
- Produces: `build_worker_message_event`, `WorkerFacade.message`, common RPC `worker/message`, top-level `message` parser/params, `start --no-callback` capture flow, and instance-qualified initialization prose.

- [ ] **Step 1: Write RED façade/RPC/CLI tests**

Cover `--message|--message-file` exclusivity and empty/unreadable files, priority enum/default, optional `--cc-agent-name`, no `--socket`, no daemon autostart, exact one JSON object on every outcome, local exit 2 versus daemon exit 1, all seven callback faults, unavailable override success, disabled override refusal, default binding immutability, and five simultaneous named workers sending independently. Assert the transport request never calls broker turn methods. Pin the production event builder to the exact `codex-worker.claude-callback/v1` `worker_message` envelope, worker identity, message, priority, and a freshly minted UUID event ID for every call; two deliberate identical CLI retries must produce different event IDs.

- [ ] **Step 2: Pin exact initialization instruction under RED**

The first turn prompt must retain the caller's prose and add one bounded instruction block containing the measured worker values:

```text
You may broadcast a non-blocking update to Claude and continue working:
codex-worker --instance <instance> message --name <name> --message "<prose>"
Use --message-file for long text. Optional one-send override: --cc-agent-name <name>.
This command does not wait for a reply; Claude may later use steer or run.
```

Assert the block appears once on initial `start`, never repeats on `run`, contains no callback credential/path, and preserves native Claude guidance.

- [ ] **Step 3: Run RED**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade.py tests/codex-worker/test_rpc_cli.py tests/codex-worker/test_facade_integration.py -v`

Expected: missing parser/RPC/façade method and absent initialization block.

- [ ] **Step 4: Implement the common surface**

Add the parser family and strict `_params_for` route. Capture Claude ambient data only for `worker/start`; `run` never recaptures. `build_worker_message_event` constructs the exact public envelope and calls the injected UUID provider once per request—there is no idempotent reuse for proactive sends. `WorkerFacade.message` resolves name, reads binding, builds one new event, performs one transport attempt, and returns `CallbackSendResponse`. Add recovery actions with exact `--instance` and shell-quoted name/message-file guidance; do not echo prose or secrets into faults.

- [ ] **Step 5: Run GREEN, process concurrency, fast gate, and commit**

Run focused: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade.py tests/codex-worker/test_rpc_cli.py tests/codex-worker/test_facade_integration.py -v`

Run fast: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Commit:

```bash
git add skills/subagent-driven-development/scripts/codex_worker/{facade,rpc,cli,projection}.py \
  tests/codex-worker/test_facade.py tests/codex-worker/test_rpc_cli.py \
  tests/codex-worker/test_facade_integration.py
git commit -m "feat(codex-worker): add proactive Claude messages"
```

### Task 6: Source-repository callback probes

**Role in the build:** Demonstrate the exact terminal/proactive event shapes and measured Claude write/pong independently of production code while preserving one source of transport research truth (R12, UC7; D12, D14, D19, D26–D28).

**Read first:** design §5.8 and §9 AH9; CLI companion §5; trading repo `AGENTS.md`, root `CLAUDE.md`, protocol reference, and `scripts/send_to_claude.py`.

**Files (trading repo isolated worktree):**
- Create: `scripts/probe_codex_completion_callback.py`
- Create: `scripts/probe_codex_agent_message.py`
- Modify: `scripts/send_to_claude.py`
- Create: `tests/test_codex_callback_probes.py`
- Modify: `docs/reference/claude-code-messaging-protocol.md`
- Modify: `docs/README.md`

**Interfaces:**
- Consumes: exact callback schema/event names from Task 1 and existing `send_to_claude.py` functions.
- Produces: an additive explicit-envelope-UUID seam in the existing sender, two stdlib executable probes with dry-run/live one-object results, deterministic `--event-id`, and correlated `orchestrator-original` evidence committed in the trading-repo branch.

- [ ] **Step 1: Create an isolated trading-repo worktree and record its base**

Use `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.worktrees/codex-worker-callback-probes` on branch `codex-worker-callback-probes`. Verify the project-local directory is ignored and leave the active checkout's unrelated modified/untracked files untouched.

- [ ] **Step 2: Write RED probe tests**

Import the sender and both scripts by path. Assert exact v1 envelope keys, terminal `CompletionResponse` passthrough, proactive message/priority, deterministic event ID, and full D27/D28 outer parity: `msg_id == event_id`, literal namespace `5b290fd0-2df0-5c73-980f-04f284476f55`, known mapping `event-fixture-1 -> 740cb30c-652d-5f4f-bc30-36c14a48d007`, origin-addressed `from` when supplied, `from_mode == "bypass"`, and absent `session_id`. Also cover input exclusivity, dry-run no-connect, token redaction, one JSON stdout object, and failure exit behavior. Fixtures and outputs are labelled SIMULATED; only the later live send is MEASURED.

- [ ] **Step 3: Run RED and implement minimal probes**

Run: `uv run pytest tests/test_codex_callback_probes.py -q`

Expected RED: modules/files absent and the sender cannot accept an explicit envelope UUID. Add an optional `message_uuid` argument to `send_to_claude.build_payload` and `send` (plus CLI `--uuid`) while preserving UUIDv4 defaults for existing callers. Implement argparse entrypoints that import this sender rather than copy its registry/socket logic and pass the D27 UUIDv5 value explicitly. `probe_codex_completion_callback.py` accepts exactly one of `--completion-file|--completion-stdin`; `probe_codex_agent_message.py` accepts exactly one of `--message|--message-file`. Both support `--cc-agent-name`, `--event-id`, `--dry-run`, and `--pretty`, and print exactly one result JSON object.

- [ ] **Step 4: Run GREEN and the trading fast gate**

Run focused: `uv run pytest tests/test_codex_callback_probes.py -q`

Run gate: `uv run pytest tests --suite fast -n auto`

Expected: focused and project fast suites pass; record exact measured counts/times from output rather than copying historical numbers.

- [ ] **Step 5: Drive both live probes separately**

Send one proactive and one terminal probe to `orchestrator-original`, each with a unique event ID and priority `next`. Preserve the raw one-object command outputs and append-only pong lines. Confirm the probe evidence only demonstrates transport/event shape; it does not claim daemon scrubbing, outbox restart, or delivery acknowledgement.

- [ ] **Step 6: Update source docs and commit the trading branch**

Add probe names/results to the protocol reference and docs index with MEASURED version/time labels. Commit only owned files:

```bash
git add scripts/send_to_claude.py scripts/probe_codex_completion_callback.py \
  scripts/probe_codex_agent_message.py \
  tests/test_codex_callback_probes.py docs/reference/claude-code-messaging-protocol.md \
  docs/README.md
git commit -m "test(claude-code): add Codex callback probes"
```

Return the trading commit SHA and evidence paths to the Superdev controller; do not merge or clean the user's active checkout.

### Task 7: SDD callback guidance and semantic review checkpoint

**Role in the build:** Teach Claude and Codex the low-friction callback workflow while preserving native Claude dispatch, short follow-ups, exact instance routing, and honest recovery (R1, R4, R5, R11; D4–D6, D18, D23, D24).

**Read first:** design §4 and §5.5–5.8; CLI companion §6–8; `skills/subagent-driven-development/SKILL.md` callback/Codex-worker sections; `skills/subagent-driven-development/codex-worker.md`; decision log D24; writing-skills guidance on reference-skill retrieval tests (user override replaces the pressure campaign).

**Files:**
- Modify: `skills/subagent-driven-development/codex-worker.md`
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `tests/codex-worker/test_skill_integration.py`
- Modify: `README.md` or the existing Codex-worker reference index only if it already enumerates common commands.

**Interfaces:**
- Consumes: installed CLI behavior from Tasks 4–5 and exact examples from the CLI companion.
- Produces: concise initialization/callback/recovery guidance, structural guards for instance/name/continue-working/no-delivery/native-Claude language, and semantic reviewer reports.

- [ ] **Step 1: Add focused structural RED guards**

Extend `test_skill_integration.py` to require: exact `codex-worker --instance <instance> message --name <name>` guidance; `--message-file`; non-blocking continue-working semantics; automatic terminal callback/no-poll normal path; `status/messages/history` diagnostic recovery; `cc-agent-name` one-send scope; no credential instructions; and explicit preservation of native Claude Code. Do not add a multi-agent pressure campaign (D24).

- [ ] **Step 2: Run RED, write minimal guidance, and run GREEN**

Run RED/GREEN: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_skill_integration.py -v`

The guidance must be reference-sized, link to CLI `--help`, and avoid repeating the whole wire protocol. Native Claude remains the default SDD route unless the operator/plan explicitly selects Codex.

- [ ] **Step 3: Dispatch one fresh semantic retrieval reviewer**

Give the reviewer only the updated skill/reference plus three scenarios: originating-room automatic completion, proactive question while continuing, and alternate one-message reviewer. Require it to return the exact commands/expected semantics and flag any ambiguity. Fix substantive findings before task review.

- [ ] **Step 4: Run fast gate and commit**

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Commit:

```bash
git add skills/subagent-driven-development/SKILL.md \
  skills/subagent-driven-development/codex-worker.md \
  tests/codex-worker/test_skill_integration.py README.md
git commit -m "docs(sdd): teach Codex callback messages"
```

Stage only docs that actually changed; do not force-add an unchanged index.

### Task 8: Live acceptance, CLI checkride, release, and receipts

**Role in the build:** Prove the complete installed experience on real Codex and Claude, iterate the user-facing surface until the independent evaluator passes, and publish reconstructable 7.3.0 evidence for every UC/AH (R1–R12; D11, D12, D14, D22–D27).

**Read first:** design §3 and §9; entire CLI companion; `superdev:cli-checkride`; existing live harness/checkride files; release/package scripts and 7.2.0 final-verification record.

**Files:**
- Modify: `tests/codex-worker/live_broker_check.py`
- Modify: `tests/codex-worker/live_claude_check.sh`
- Modify: `tests/codex-worker/live_claude_evidence.py`
- Modify: `tests/codex-worker/test_live_harness_contract.py`
- Modify: `tests/codex-worker/test_live_claude_evidence.py`
- Create: `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-checkride.md`
- Create: `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/executor-transcript.md`
- Create: `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/evaluator-verdict.md`
- Create: `docs/superdev/checkrides/2026-08-20-codex-worker-claude-callbacks-evidence/final-verification.md`
- Modify via existing release tooling: `RELEASE-NOTES.md`, `package.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and generated version mirrors selected by the tooling.
- Modify: design §9 receipt cells and decision log only for measured build forks.

**Interfaces:**
- Consumes: all Tasks 1–7 production surfaces and the Task 6 trading commit/evidence SHA.
- Produces: deterministic live-harness contracts, separate real callback scenarios, real Claude caller evidence, a PASS executor/evaluator checkride, AH1–AH11 receipts, 7.3.0 package/install evidence, and a clean feature branch.

- [ ] **Step 1: Write RED live-harness contract tests**

Add deterministic tests requiring separately runnable scenarios for: automatic inline completion; proactive mid-turn message + later steer/run; one-message override with origin-preserved terminal event; an explicit origin-retention journey that starts under origin Claude metadata, replaces/unsets ambient Claude metadata for a later `run`, and proves the terminal event still targets only the persisted origin; completed/failed/interrupted and wait-timeout-then-later-terminal notifications; daemon restart same-ID pending replay/written non-replay; artifact reference/digest read-back; credential scrub/PID-reuse/Unicode refusals; standalone/disabled behavior; and exactly five concurrent named workers. Extend real-Claude evidence validation to require PATH-only common commands, no MCP/direct raw Codex, callback event IDs, full result recovery, and durable-state preservation.

- [ ] **Step 2: Run RED, implement harness scenarios, and run warning-strict fast GREEN**

Run focused: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_live_harness_contract.py tests/codex-worker/test_live_claude_evidence.py -v`

Run fast: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`

Expected: all deterministic tests pass with no ResourceWarnings.

- [ ] **Step 3: Run live preflight and callback scenarios separately**

Run each as its own killable command, preserving raw outputs before moving on:

```bash
python3 tests/codex-worker/live_broker_check.py --preflight
python3 tests/codex-worker/live_broker_check.py --scenario callback-common
python3 tests/codex-worker/live_broker_check.py --scenario callback-proactive
python3 tests/codex-worker/live_broker_check.py --scenario callback-origin-retention
python3 tests/codex-worker/live_broker_check.py --scenario callback-recovery
python3 tests/codex-worker/live_broker_check.py --scenario callback-security
python3 tests/codex-worker/live_broker_check.py --scenario callback-five-workers
bash tests/codex-worker/live_claude_check.sh
```

Label provider/model/token/timing values MEASURED from transcripts. Do not infer delivery, capacity, or unavailable metrics.

- [ ] **Step 4: Execute the required CLI checkride loop**

Dispatch a medium-tier executor agent to run every touched command one at a time against real local daemons, showing invocation, full stdout, full stderr, and exit code. Include happy and refusal paths for `start --no-callback`, automatic callback, `message` inline/file/priorities/override, callback status, stopped-daemon message, stale/ambiguous/oversize targets, restart recovery, artifact read-back, and raw compatibility. Commit a sanitized-but-verbatim transcript.

Dispatch a very-smart evaluator agent with the operator context and transcript. It judges friction, truthfulness, recovery, provenance, and mechanism; findings iterate through one fix wave, focused reride, and re-evaluation until PASS. Design-changing findings append a D# before code changes.

- [ ] **Step 5: Fill receipts and run final code/evidence gates**

Fill design §9 AH1–AH11 with exact deterministic/live/checkride/probe receipts, including the independent trading commit SHA. Run:

```bash
python3 -m py_compile skills/subagent-driven-development/scripts/codex_worker/*.py
bash -n tests/codex-worker/live_claude_check.sh
python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
git diff --check
```

- [ ] **Step 6: Bump and verify 7.3.0**

Use the existing version-bump script with `7.3.0`, then run the repository's version audit, marketplace tests, Codex plugin package test, and sync test as separate commands. Commit source and evidence before installation. Reversibly point the local development marketplace at this worktree only if required, install/update `superdev@superdev-dev`, confirm the installed manifest and `bin/codex-worker` bytes/executable bit, and run external-cwd `--help`, stopped `status`, and one callback smoke. Restore any external marketplace source after integration or record the exact controller-owned restoration step.

- [ ] **Step 7: Final commit**

Stage only callback/release/evidence files and commit with truthful subjects, splitting production fixes, release metadata, and evidence when their review boundaries differ. The final tree must be clean, and daemon stop must preserve worker/callback state and artifacts.
