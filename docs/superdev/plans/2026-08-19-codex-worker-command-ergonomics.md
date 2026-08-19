# Codex Worker Command Ergonomics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing local Codex RPC broker into a PATH-installed, Claude-session-aware named-worker CLI with implicit message-command lifecycle, short follow-ups, complete terminal results, native goal/history/limits proxies, and non-destructive recovery.

**Architecture:** A dependency-free command/domain layer and version-compatible registry sit beneath a session-scoped `InstanceManager`. A pure projector and `WorkerFacade` compose the existing broker/app-server/runtime primitives into name-selected synchronous operations; the CLI remains a thin parser/router and preserves the raw socket/session/turn surface as an advanced compatibility mode.

**Tech Stack:** Python 3.9 standard library (`argparse`, frozen `dataclasses`, `enum`, `json`, `pathlib`, `fcntl`, `socket`, `subprocess`, `threading`, `unittest`), POSIX AF_UNIX, Codex 0.147.0 app-server JSON-RPC, Bash launcher/live harnesses, Claude Code.

**Execution:** subagent-driven

**Mode:** autonomous

**Context pack** — the artifacts downstream workers read:
- Spec: `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-design.md` · Decision log: `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-decisions.md`
- Domain model: design §5.9
- CLI surface: `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-cli-surface.md`
- Prior art: `docs/superdev/specs/2026-08-18-codex-worker-server-design.md`; `docs/superdev/plans/2026-08-18-codex-worker-server.md`; `skills/subagent-driven-development/codex-worker.md`; `/Users/tadas/Downloads/codex-app-server-reference.md`; fresh Codex schemas generated into a task-owned temporary directory with `codex app-server generate-json-schema --experimental --out "$SCHEMA_DIR"`

## Global Constraints

- Python 3.9 and the standard library are the only Python runtime dependencies; D40's frozen strict models are the binding exception to the generic Pydantic seam rule.
- The control plane remains current-user-only AF_UNIX. No TCP/WebSocket/MCP/cloud service is introduced.
- Common instance precedence is `--instance`, `CODEX_WORKER_INSTANCE`, `CLAUDE_CODE_SESSION_ID`, then user-local `default`; `CLAUDE_EFFORT` never selects Codex effort.
- Durable state is Superdev-owned and instance-keyed; the socket alone uses a short hashed owner-only runtime path.
- Worker names match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. `(instance, name)` is unique; name is never a path fragment.
- `start` creates only and owns creation configuration. `run` continues only and cannot change cwd/model/tier/effort/access. Both wait indefinitely unless `--timeout` is supplied.
- Medium tier resolves live to Terra and very-smart to Sol; raw `--model` is mutually exclusive. Default effort is medium. Unsupported model/effort blocks without fallback.
- Thread create/resume use `sandbox: danger-full-access|read-only`; turn start uses `sandboxPolicy: {type: dangerFullAccess}|{type: readOnly, networkAccess: false}`. Only thread create sends `allowProviderModelFallback: false`.
- Caller timeout/disconnect ends only the local wait. `interrupt` is the only common command that cancels a turn.
- `daemon stop` preserves registry, worker records, logs, and recovery IDs. No clean, purge, delete, archive, or goal-clear command is added.
- Every client command prints exactly one JSON object; usage errors exit 2, operational refusals exit 1, success exits 0. Advanced socket-selected wire responses remain unchanged.
- Completion selects all explicit `final_answer` messages, otherwise the last terminal agent message as a marked fallback. In-progress history narration is `live`, never terminal fallback.
- Metrics are MEASURED, REPORTED, DERIVED, or unavailable with explicit source. Hidden steps and absent token usage are never inferred.
- Use `superdev:writing-skills` before modifying `SKILL.md` or behavior-shaping references. Documentation semantics use fresh reviewer agents rather than a token-heavy behavior campaign.

**Test lanes:** fast (the gate): `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` · slow-by-area (separate killable commands): `python3 tests/codex-worker/live_broker_check.py` and `bash tests/codex-worker/live_claude_check.sh` · scheduled sweep: none declared by this repository. Every commit runs the fast gate plus focused owned tests; slow commands run separately only at their owning task and finishing gate.

**Engineering patterns:** `skills/engineering-patterns/python-patterns.md` (BINDING), with only D40's explicit dependency-free strict-stdlib-model substitution. Implementers read §§1–4, 6–11 before coding; all other knowing departures are reportable deviations.

## The Through-Line

Task 1 is LOAD-BEARING: it fixes the request, response, refusal, worker identity, and registry migration contracts every later task imports. Task 2 is also LOAD-BEARING: it turns an instance identity into safe durable/runtime paths and one concurrency-safe daemon without involving worker semantics. Task 3 adds the pure protocol projection and exact Codex adapter seams—phase fallback, metrics, access encodings, output schema, goal/history/limits—so Task 4 can compose named workflows without parsing events or provider payloads in orchestration code. Task 5 exposes that façade through high-level RPC and the exact dual-mode CLI while retaining raw compatibility. Task 6 hardens the integrated mechanism with deterministic concurrency, crash, security, and refusal evidence. Task 7 updates behavior-shaping documentation only after the command exists, using small semantic reviewers. Task 8 drives the real installed surface through five concurrent named workers and a Claude caller, fills anchor receipts, then releases/reinstalls the verified plugin.

The order is intentionally sequential: Tasks 2–5 consume names/types created immediately upstream and touch shared composition seams. Parallelizing them would turn interface negotiation into merge conflict rather than reduce latency. When reality diverges, trace the threatened interface through this paragraph, check the governing D# revisit hook, append a phase `build` fork to the decision log, and update every downstream Consumes/Produces block before continuing. Any drift that breaks durable name identity, non-destructive stop, exact access/model policy, one-object JSON, or the anchored five-worker surface follows autonomous soften-but-own routing rather than silent adaptation.

## Acceptance (anchored — do not restate here)

This plan discharges UC1–UC10 and AH1–AH12 from the design anchor. Tasks 1–6 produce deterministic receipts for AH7/AH9–AH12 and the error/security portions of the other hints. Task 7 produces documentation/installed-launcher evidence. Task 8 owns real-surface receipts for AH1–AH8/AH10/AH12 and fills every design §9 receipt cell with one re-runnable command/transcript/file reference. Any unanswered hint is named and gets an owned backlog item naming its UC#/AH# before autonomous close; no skip or unmeasured claim is converted into a pass.

---

### Task 1: Strict façade models and additive worker registry

**Role in the build:** Define the stable common request/response/refusal shapes and migrate durable records without losing existing raw sessions (R2–R3, R8, R11, R13; D11–D12, D35–D36, D40–D42).

**Read first:** Design §5.2, §5.5–§5.6, §5.9.1–§5.9.5; CLI surface §§0, 8, 10; decision log D35–D36/D40–D42/D46; Python patterns §§2, 4, 6, 8.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/commands.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/models.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/registry.py`
- Modify: `tests/codex-worker/test_models_registry.py`
- Create: `tests/codex-worker/test_commands.py`

**Interfaces:**
- Consumes: existing `SessionRecord`, `RpcFault`, and schema-v1 registry files.
- Produces: shared frozen `Ok[T]`, `Err[E]`, and `Result[T, E]` types; closed `Tier`, `AccessMode`, `InstanceSource`, `CompletionSelection`, and `MetricAvailability` enums; frozen strict request models `StartWorkerRequest`, `RunWorkerRequest`, `WorkerStatusRequest`, `WorkerMessagesRequest`, `WorkerHistoryRequest`, `SteerWorkerRequest`, `InterruptWorkerRequest`, `GoalSetRequest`, `GoalShowRequest`, `LimitsRequest`, `DaemonStatusRequest`, `DaemonStopRequest`; frozen response/value models named exactly as CLI §8; `FacadeFault(code, message, kind, retryable, source, details, known_ids, next_actions)`; registry schema v2 with `SessionRecord.tier/access`, `SessionRecord.common_policy_complete`, `resolve_name(name)`, and `create_worker(thread_id: str, cwd: str, name: str, tier: Optional[str], model: str, effort: str, access: str, session_id: Optional[str] = None) -> SessionRecord`.

- [ ] **Step 1: Write RED tests for strict command and response construction**

```python
def test_worker_name_and_start_configuration_are_strict(self):
    with self.assertRaises(ValueError):
        StartWorkerRequest(name="bad name", prompt="x", cwd=self.cwd)
    with self.assertRaises(ValueError):
        StartWorkerRequest(name="a" * 129, prompt="x", cwd=self.cwd)
    request = StartWorkerRequest(name="review-a31", prompt="inspect", cwd=self.cwd)
    self.assertEqual(request.tier, Tier.MEDIUM)
    self.assertEqual(request.effort, "medium")
    self.assertEqual(request.access, AccessMode.FULL)

def test_facade_fault_has_exact_machine_recovery_shape(self):
    fault = FacadeFault.worker_not_found("review-a31", "scope")
    self.assertEqual(fault.to_dict()["data"], {
        "kind": "worker_not_found", "retryable": False,
        "source": "codex-worker", "details": {},
        "known_ids": {"instance": "scope", "name": "review-a31",
                      "session_id": None, "thread_id": None, "turn_id": None},
        "next_actions": [{"command": "codex-worker start --name review-a31",
                          "reason": "Create this worker in the selected instance"}],
    })
```

- [ ] **Step 2: Run focused RED**

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_commands.py' -v`
Expected: FAIL because `codex_worker.commands` does not exist.

- [ ] **Step 3: Implement frozen strict models and closed common fault codes**

```python
WORKER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

@dataclass(frozen=True)
class StartWorkerRequest:
    name: str
    prompt: str
    cwd: str
    tier: Optional[Tier] = Tier.MEDIUM
    model: Optional[str] = None
    effort: str = "medium"
    access: AccessMode = AccessMode.FULL
    goal: Optional[str] = None
    token_budget: Optional[int] = None
    output_schema: Optional[JsonObject] = None
    timeout: Optional[float] = None

    def __post_init__(self) -> None:
        validate_worker_name(self.name)
        validate_prompt(self.prompt)
        validate_canonical_cwd(self.cwd)
        if self.model is not None and self.tier is not None:
            raise ValueError("--tier and --model are mutually exclusive")
        if self.token_budget is not None and self.goal is None:
            raise ValueError("--token-budget requires --goal")
```

Implement explicit `to_dict`/`from_dict` for every seam model, reject unknown keys,
preserve nullability/enums from CLI §8, and pin new codes `-32021..-32030` including
typed `daemon_stop_failed`. Keep existing `RpcFault/ErrorDetail` serialization unchanged
for advanced methods.

- [ ] **Step 4: Write RED registry migration/bootstrap tests**

```python
def test_missing_and_zero_byte_registry_initialize_v2_owner_only(self):
    for seed in (None, b""):
        path = self.root / ("state-%s.json" % ("missing" if seed is None else "empty"))
        if seed is not None:
            path.write_bytes(seed)
        registry = SessionRegistry(path)
        self.assertEqual(registry.list(), [])
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(json.loads(path.read_text())["schema_version"], 2)

def test_v1_records_load_without_loss_and_upgrade_on_next_write(self):
    self.write_v1_record(name="legacy")
    registry = SessionRegistry(self.state_path)
    legacy = registry.resolve_name("legacy")
    self.assertIsNone(legacy.tier)
    self.assertIsNone(legacy.access)
    self.assertFalse(legacy.common_policy_complete)
    registry.create_worker("thr-2", self.cwd, "new-a31", "medium",
                           "gpt-5.6-terra", "medium", "full")
    self.assertEqual(json.loads(self.state_path.read_text())["schema_version"], 2)
```

- [ ] **Step 5: Implement additive registry v2**

Accept exact v1 and v2 schemas; map v1 `tier/access` to null in memory and write all
records as v2 only after a successful mutation. Missing/zero-byte input writes the
empty v2 snapshot atomically. Preserve non-empty malformed bytes and include
path/expected versions in `RegistryError`. Enforce unique non-null names in addition to
session/thread IDs, parent fsync after replace, and exact owner-only regular-file checks.
Loading never invents access, tier, model, or effort. A record is common-policy complete
when `name/model/effort/access` are present; `tier` may deliberately be null for an
explicit raw-model worker. Legacy/raw records remain incomplete because access is null.

- [ ] **Step 6: Run focused and fast gates**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_commands.py tests/codex-worker/test_models_registry.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/subagent-driven-development/scripts/codex_worker/commands.py \
  skills/subagent-driven-development/scripts/codex_worker/models.py \
  skills/subagent-driven-development/scripts/codex_worker/registry.py \
  tests/codex-worker/test_commands.py tests/codex-worker/test_models_registry.py
git commit -m "feat(codex-worker): add named worker command domain"
```

### Task 2: Session-scoped instance manager and public launcher

**Role in the build:** Resolve harness identity into safe paths and one concurrency-safe daemon while keeping lifecycle independent from worker orchestration (R1, R4, R6, R10–R11; D4–D6, D8–D9, D18, D27, D33–D34, D37).

**Read first:** Design §5.1, §5.6–§5.8; CLI surface §§0, 6; decision log D33–D34/D37/D43/D47; Python patterns §§3–4, 6–8.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/instance.py`
- Create: `bin/codex-worker`
- Create: `tests/codex-worker/test_instance.py`
- Modify: `tests/codex-worker/test_rpc_cli.py`

**Interfaces:**
- Consumes: Task 1 `InstanceSource`, `InstanceView`, `DaemonStatusResponse`, `DaemonStopResponse`, `FacadeFault`.
- Produces: `InstanceIdentity`, `validate_instance_id`; `resolve_instance(explicit, env) -> InstanceIdentity`; `derive_instance_paths(identity, platform, state_home, temp_root, uid) -> InstancePaths`; injectable `InstanceDeps`; `InstanceManager.status()`, `ensure_running()`, `stop()`; owner-only `instance.json`; `load_managed_identity(state_path) -> Optional[InstanceIdentity]`; executable cwd-independent `bin/codex-worker`.

- [ ] **Step 1: Write RED precedence/path tests**

```python
def test_instance_precedence_and_short_socket(self):
    env = {"CODEX_WORKER_INSTANCE": "env-id", "CLAUDE_CODE_SESSION_ID": "claude-id"}
    self.assertEqual(resolve_instance("flag-id", env).value, "flag-id")
    self.assertEqual(resolve_instance(None, env).value, "env-id")
    self.assertEqual(resolve_instance(None, {"CLAUDE_CODE_SESSION_ID": "claude-id"}).value,
                     "claude-id")
    paths = derive_instance_paths(resolve_instance(None, {}), "darwin",
                                  self.state_home, self.temp_root, 501)
    self.assertLess(len(os.fsencode(paths.socket_path)), 100)
    self.assertNotIn("default", paths.socket_path.name)
```

- [ ] **Step 2: Run focused RED**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_instance.py -v`
Expected: FAIL because `codex_worker.instance` does not exist.

- [ ] **Step 3: Implement pure resolution and path derivation**

```python
def resolve_instance(explicit: Optional[str], env: Mapping[str, str]) -> InstanceIdentity:
    candidates = ((InstanceSource.FLAG, explicit),
                  (InstanceSource.ENVIRONMENT, env.get("CODEX_WORKER_INSTANCE")),
                  (InstanceSource.CLAUDE_SESSION, env.get("CLAUDE_CODE_SESSION_ID")),
                  (InstanceSource.DEFAULT, "default"))
    source, value = next((source, value) for source, value in candidates if value)
    return InstanceIdentity(source, validate_instance_id(value))
```

Derive durable platform state on macOS under
`~/Library/Application Support/superdev/codex-worker/instances/<sha256>` and on other
Unix systems under
`${XDG_STATE_HOME:-~/.local/state}/superdev/codex-worker/instances/<sha256>`. Derive
the socket under the platform temporary directory as
`superdev-cw-<effective-uid>/<sha256-prefix>/worker.sock`. Persist original identity
only in owner-only metadata, not path text.

Create `instance.json` beside `registry.json` before spawn with mode `0600`. Loading
verifies owner, type, mode, exact fields, and agreement between the identity hash and
the parent directory name. An arbitrary raw state path without verified managed
metadata remains valid for advanced methods but cannot construct a common façade.

- [ ] **Step 4: Write RED concurrent-start, stale-state, stop, and adversarial path tests**

Use an injected `spawn(argv, stderr_path) -> ProcessHandle`, `rpc_status(socket)`, clock,
and bounded lock timeout. Race five threads through `ensure_running()` and assert one
spawn. Cover symlink/foreign/permissive lock/socket/parent refusal, failed readiness
with log path, stale PID repair, already-stopped success, graceful child exit, and no
durable deletion.

- [ ] **Step 5: Implement `InstanceManager`**

```python
@dataclass(frozen=True)
class InstanceDeps:
    paths: InstancePaths
    launcher: str
    codex_bin: str
    spawn: Callable[[Sequence[str], str], ProcessHandle]
    rpc_call: Callable[[str, str, JsonObject, Optional[float]], JsonObject]
    monotonic: Callable[[], float]

class InstanceManager:
    def ensure_running(self) -> DaemonStatusResponse:
        with acquire_start_lock(self.deps.paths.lock_path, timeout=2.0):
            ready = self._probe()
            if ready is not None:
                return ready
            process = self.deps.spawn(self._serve_argv(), str(self.deps.paths.log_path))
            return self._wait_ready(process)
```

Use `O_NOFOLLOW` where available, `lstat/fstat` owner/type checks, bounded nonblocking
flock, exact modes, inode rechecks, and atomic metadata writes. `_serve_argv()` returns
`[launcher, "--socket", str(paths.socket_path), "daemon", "serve", "--state",
str(paths.registry_path), "--codex-bin", codex_bin]`; the spawned child stays in raw
foreground serve mode. `stop()` sends raw shutdown, waits for both reported PIDs to
disappear, and removes only verified runtime markers.

- [ ] **Step 6: Add and verify the launcher**

`bin/codex-worker` resolves `../skills/subagent-driven-development/scripts/codex-worker`
relative to its own real path and `exec`s it with all arguments. Set executable mode and
test invocation from a temporary cwd with no repository-relative assumptions.

- [ ] **Step 7: Run focused/fast gates and commit**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_instance.py tests/codex-worker/test_rpc_cli.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add bin/codex-worker skills/subagent-driven-development/scripts/codex_worker/instance.py \
  tests/codex-worker/test_instance.py tests/codex-worker/test_rpc_cli.py
git commit -m "feat(codex-worker): manage session-scoped daemon instances"
```

### Task 3: Exact Codex protocol seams and pure result projection

**Role in the build:** Add provider-accurate access/output/proxy calls and a pure completion/history projector before orchestration depends on them (R3, R7–R9; D15–D17, D20–D22, D29–D32, D39, D41, D44).

**Read first:** Design §5.3–§5.5; CLI surface §§1c, 4–5, 8; decision log D39/D41/D44/D48; generate fresh schemas with the Context-pack command and read `ThreadStartParams`, `ThreadResumeParams`, `TurnStartParams`, `ThreadGoal*`, `ThreadTurnsListParams`, and `AccountRateLimitsReadResponse`.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/projection.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/broker.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/runtime.py`
- Modify: `tests/codex-worker/fake_codex.py`
- Create: `tests/codex-worker/test_projection.py`
- Modify: `tests/codex-worker/test_broker.py`
- Modify: `tests/codex-worker/test_app_server_runtime.py`

**Interfaces:**
- Consumes: Task 1 response/value models; existing `WorkerBroker`, `RuntimeStore`, `CodexAppServer.call`.
- Produces: `SessionStartSpec(cwd, name, model, access, tier, effort, annotation_policy)`, `SessionResumeSpec`, `TurnStartSpec`; public broker methods `start_session(spec)`, `resume_session(spec)`, `start_turn(spec)` used by both raw dispatch and façade; `AnnotationPolicy.LEGACY_MUTABLE|PRESERVE_WORKER_POLICY`; one-write common creation through `registry.create_worker`; `NativeCodexProxy.goal_set/get`, `turns_list`, `rate_limits_read`; pure `select_completion_messages`, `project_completion`, `project_history_turn`, `derive_metrics`.

- [ ] **Step 1: Write RED adapter request-shape tests**

```python
def test_full_and_read_only_use_both_protocol_encodings(self):
    full = self.broker.start_session(SessionStartSpec(self.cwd, "n", self.model,
                                                      AccessMode.FULL))
    self.assertEqual(self.codex.calls[-1][1]["sandbox"], "danger-full-access")
    self.assertFalse(self.codex.calls[-1][1]["allowProviderModelFallback"])
    self.broker.start_turn(TurnStartSpec(full.session_id, "go", self.model, "medium",
                                        AccessMode.FULL, None))
    self.assertEqual(self.codex.calls[-1][1]["sandboxPolicy"],
                     {"type": "dangerFullAccess"})
```

Add the paired read-only case, resume assertion proving it sends `sandbox` but not
`allowProviderModelFallback`, and output-schema forwarding only on turn start.

- [ ] **Step 2: Run focused RED and implement typed broker seams**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_broker.py -v`
Expected: FAIL because typed specs/public methods do not exist.

Refactor existing raw dispatchers to construct specs and call the same methods. Preserve
all existing raw params/results. Add `NativeCodexProxy` with exact method/field spelling;
validate every response before constructing Task 1 models.

Registry mutation is record-aware: a schema-v2 worker with complete common policy keeps
its creation-time `tier/model/effort/access` immutable even when addressed through a raw
turn command, while a legacy/raw record with incomplete common policy retains existing
mutable model/effort annotation behavior. A raw override on a common worker affects that
turn only. Add paired tests for both branches and prove a later common `run` resends the
original persisted policy.

- [ ] **Step 3: Write RED projection tests for nullable phase, schema mode, and metrics**

```python
def test_terminal_phase_fallback_is_visible_but_live_history_is_not_terminal(self):
    items = [agent("a", "work", None), agent("b", "answer", None)]
    selected = select_completion_messages(items, terminal=True)
    self.assertEqual([(x.item_id, x.selection.value) for x in selected],
                     [("b", "terminal_fallback")])
    live = select_completion_messages(items, terminal=False)
    self.assertEqual([x.selection.value for x in live], ["live", "live"])

def test_explicit_finals_and_schema_json_are_preserved(self):
    items = [agent("a", "note", "commentary"),
             agent("b", '{"verdict":"pass"}', "final_answer")]
    response = project_completion(self.worker, terminal_turn(items), self.schema, 1.25)
    self.assertEqual(response.structured_output, {"verdict": "pass"})
    self.assertEqual(response.messages[0].text, '{"verdict":"pass"}')
```

Cover multiple explicit finals, zero agent messages, invalid schema-mode JSON, item
counts by type, command count, sum of authoritative `durationMs`, missing duration, and
reported/unavailable token usage.

- [ ] **Step 4: Implement pure projector and bounded runtime access**

```python
def select_completion_messages(items: Sequence[ItemRecord], terminal: bool) -> List[AgentMessageView]:
    agents = [agent_view(item) for item in items if item.type == "agentMessage"]
    if not terminal:
        return [replace(item, selection=CompletionSelection.LIVE) for item in agents]
    finals = [item for item in agents if item.phase == "final_answer"]
    if finals:
        return [replace(item, selection=CompletionSelection.EXPLICIT_FINAL) for item in finals]
    return ([replace(agents[-1], selection=CompletionSelection.TERMINAL_FALLBACK)]
            if agents else [])
```

Keep `RuntimeStore.latest_turn` as the bounded terminal source; never retain unbounded
per-turn buckets. Add a read-only retained-agent-message projection with cursor/truncate
metadata for the common `messages` command without consuming events.

- [ ] **Step 5: Extend fake Codex and verify native proxies**

Teach `fake_codex.py` deterministic goal set/get, paginated turns list, rate limits,
nullable message phase, output schema, token usage, and request capture. Tests assert
goal fields/status enums, history pagination/order, unsupported limits mapping, and no
renamed/dropped rate-limit keys.

- [ ] **Step 6: Run focused/fast gates and commit**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_projection.py tests/codex-worker/test_broker.py tests/codex-worker/test_app_server_runtime.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add skills/subagent-driven-development/scripts/codex_worker/projection.py \
  skills/subagent-driven-development/scripts/codex_worker/broker.py \
  skills/subagent-driven-development/scripts/codex_worker/runtime.py \
  tests/codex-worker/fake_codex.py tests/codex-worker/test_projection.py \
  tests/codex-worker/test_broker.py tests/codex-worker/test_app_server_runtime.py
git commit -m "feat(codex-worker): project native Codex worker results"
```

### Task 4: Named-worker façade service

**Role in the build:** Compose durable name lookup, policy, native proxies, waits, recovery, and result projection into one transport-independent service (R2–R9, R13; D13–D17, D23–D32, D35, D39–D44).

**Read first:** Design §4 and §5.2–§5.7; CLI surface §§1–5, 8, 10; decision log D46–D48; domain §5.9.5; Python patterns §§3–6.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/facade.py`
- Create: `tests/codex-worker/test_facade.py`

**Interfaces:**
- Consumes: Tasks 1–3 models, registry, verified `InstanceIdentity`, `WorkerBroker`, `NativeCodexProxy`, `RuntimeStore`, projector.
- Produces: frozen `FacadeDeps(instance, registry, broker, runtime, projector, clock)`; `WorkerFacade.start/run/status/messages/history/steer/interrupt/goal_set/goal_show/limits`, each exactly `(Request) -> Result[Response, FacadeFault]` using Task 1's `Ok`/`Err`; no CLI/env/socket logic. Every `WorkerView.instance` and recovery command uses `deps.instance.value`, never client-supplied RPC metadata.

- [ ] **Step 1: Write RED happy-path composition tests**

```python
def test_start_installs_goal_before_first_turn_and_run_reuses_policy(self):
    started = self.facade.start(StartWorkerRequest(
        name="build-a31", prompt="begin", cwd=self.cwd, goal="finish", token_budget=2000))
    self.assertIsInstance(started, Ok)
    self.assertEqual(self.calls[:3], ["session_start", "goal_set", "turn_start"])
    followed = self.facade.run(RunWorkerRequest(name="build-a31", prompt="continue"))
    self.assertEqual(followed.value.worker.thread_id, started.value.worker.thread_id)
    self.assertEqual(self.last_turn_spec.access, AccessMode.FULL)
    self.assertEqual(self.last_turn_spec.model, started.value.worker.model)
```

Also prove goal failure prevents first turn while returning persisted IDs; explicit
schema, indefinite wait, timeout-active recovery, and client-independent service
completion.

- [ ] **Step 2: Run focused RED and implement start/run**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade.py -v`
Expected: FAIL because `WorkerFacade` does not exist.

Implement model discovery before upstream creation, exact tier mapping, effort
validation, registry persistence/recovery, goal-before-turn ordering, terminal wait,
and projector calls. Catch every effect exception at the seam and return closed
`FacadeFault`; include raw recovery after post-upstream persistence failure.

- [ ] **Step 3: Write RED observation/control/proxy tests**

Cover full field equality for every CLI §8 response. Assert unknown name, existing name,
idle control race, unrelated Codex failure, stopped/not-attached state, live message
tail/truncation, multi-page history, goal absence/update, and limits unavailable.

Add migrated/raw named-record cases: operations requiring common policy return typed
`registry_error` with `details.policy_state: "incomplete_legacy"`, preserve all IDs,
and offer exact advanced session/turn recovery plus a different-name common `start`.
Existing-name `start` remains `worker_name_exists` with the same legacy-aware actions.
The façade never guesses policy and never rewrites a record merely by observing it.

- [ ] **Step 4: Implement remaining façade methods**

Resolve name exactly once per call. `steer`/`interrupt` capture the active turn ID
before dispatch and preserve the broker's exact idle-race mapping. `history` pages until
the requested tail is satisfied and returns chronological order. No read/control/proxy
method starts or stops a daemon.

- [ ] **Step 5: Run focused/fast gates and commit**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add skills/subagent-driven-development/scripts/codex_worker/facade.py \
  tests/codex-worker/test_facade.py
git commit -m "feat(codex-worker): compose named worker workflows"
```

### Task 5: High-level RPC, implicit lifecycle, and exact CLI surface

**Role in the build:** Make the façade reachable through the public one-command harness journey while preserving every advanced raw method and response (R1–R6, R10, R12–R13; D6, D18, D23–D28, D30, D34–D38, D43).

**Read first:** Design §5.1, §5.6, §5.8; CLI surface §§0–10; decision log D23–D28/D34/D38/D43/D47; Python patterns §§3, 6–7.

**Files:**
- Modify: `skills/subagent-driven-development/scripts/codex_worker/rpc.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/cli.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/__init__.py`
- Modify: `tests/codex-worker/test_rpc_cli.py`

**Interfaces:**
- Consumes: Task 2 `InstanceManager` and verified managed identity loader; Task 4 `WorkerFacade`; existing raw `WorkerBroker`.
- Produces: composite RPC dispatcher with `worker/*`, `worker/goal/*`, `account/limits`; parser and renderer for every CLI table row; common/advanced endpoint mode resolver; daemon status/stop models; preserved raw JSON-RPC methods.

- [ ] **Step 1: Write RED parser/model matrix tests**

Build a table covering every common command and exhaustive args from CLI §§1–6. Assert
`run` rejects creation flags, common commands reject `--socket`, daemon shutdown rejects
`--instance`, dual daemon status mode, exact prompt-source rules, output-schema loading,
name bounds, goal-set at-least-one, finite timeout, and one JSON error on stdout.

- [ ] **Step 2: Run focused RED and add thin parser leaves**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_rpc_cli.py -v`
Expected: FAIL because top-level common commands are absent.

Parser leaves may only convert argv/files into Task 1 requests, select endpoint mode,
call the instance/service client, and render. Move all validation/business decisions to
constructors/services.

- [ ] **Step 3: Add RED process-level start/run/autostart tests**

Use `fake_codex.py` and five concurrent client subprocesses. Begin with no socket,
registry, or daemon. Assert all clients converge on one daemon PID; each output is one
JSON object with its own name/thread/cwd/final; no process is killed when one waiting
client is terminated; an explicit timeout leaves status active.

- [ ] **Step 4: Implement composite RPC and lifecycle routing**

```python
COMMON_METHODS = {
    "worker/start": facade.start,
    "worker/run": facade.run,
    "worker/status": facade.status,
    "worker/messages": facade.messages,
    "worker/history": facade.history,
    "worker/steer": facade.steer,
    "worker/interrupt": facade.interrupt,
    "worker/goal/set": facade.goal_set,
    "worker/goal/show": facade.goal_show,
    "account/limits": facade.limits,
}
```

Only start/run call `InstanceManager.ensure_running`. Other common commands require
ready and return `daemon_stopped`. Advanced model/session/turn endpoint order is
explicit socket, explicit instance, legacy socket env/default. Daemon status is managed
unless `--socket` is explicit; raw shutdown/serve remain socket-only. Socket client
timeout is infinite when the request wait is infinite and leaves server work running on
disconnect.

At daemon bootstrap, load verified `instance.json` adjacent to managed state and inject
its `InstanceIdentity` into `FacadeDeps`. If metadata is absent or inconsistent,
register only the advanced dispatcher. Common requests do not carry or select their
response instance identity.

- [ ] **Step 5: Verify every response/error field and compatibility mode**

Add golden-shape assertions for all CLI §8 models and §10 code/kind pairs. Invoke every
existing advanced client both against explicit socket and (where allowed) explicit
instance; pin existing raw response equality. Assert foreground serve has no stdout,
managed status/stop are non-destructive, repeated stop succeeds, and restart/run resumes
the prior thread.

- [ ] **Step 6: Run focused/fast gates and commit**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_rpc_cli.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add skills/subagent-driven-development/scripts/codex_worker/rpc.py \
  skills/subagent-driven-development/scripts/codex_worker/cli.py \
  skills/subagent-driven-development/scripts/codex_worker/__init__.py \
  tests/codex-worker/test_rpc_cli.py
git commit -m "feat(codex-worker): expose harness-friendly worker CLI"
```

### Task 6: Deterministic integration, concurrency, and adversarial hardening

**Role in the build:** Prove the composed mechanism under five-way races, crashes, unsafe paths, protocol variation, and every refusal before spending real-model tokens (R3–R6, R9–R13; D14, D24, D30, D33–D36, D41–D44).

**Read first:** Design §5.1, §5.5–§5.7 and §9 AH3/AH9–AH12; CLI surface §§8–10; Python patterns §§7–11.

**Files:**
- Modify: `tests/codex-worker/fake_codex.py`
- Create: `tests/codex-worker/test_facade_integration.py`
- Modify: `tests/codex-worker/test_rpc_cli.py`
- Modify: `tests/codex-worker/test_live_harness_contract.py`

**Interfaces:**
- Consumes: complete Tasks 1–5 installed-from-source CLI and injectable fake Codex.
- Produces: deterministic subprocess receipts for common journeys, five-worker concurrency, non-destructive restart, phase/schema/metrics, native proxies, dual endpoint compatibility, and adversarial security.

- [ ] **Step 1: Add a deterministic scenario driver to fake Codex**

The fake accepts a JSON scenario file describing delayed turns, nullable phases,
multiple finals, command durations, usage/no-usage, goal state, paginated history,
limits unavailable, malformed responses, and captured thread/turn request params. It
writes all received methods/params to an owner-only JSONL capture for assertions.

- [ ] **Step 2: Write and run RED five-worker subprocess integration**

Start five `codex-worker start` processes simultaneously against one fresh explicit
instance, each with a different temporary cwd/name/output token. Assert exactly one
daemon child, five unique session/thread IDs, correct output tokens, and completion
order independent from launch order.

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade_integration.py -v`
Expected: FAIL until the integration driver and any surfaced race fixes are complete.

- [ ] **Step 3: Add refusal and durability matrix**

Cover duplicate name, unknown name, invalid model/effort, goal failure before turn,
timeout-active, disconnect persistence, idle control, malformed registry preservation,
post-upstream replace failure with raw IDs, missing/zero-byte bootstrap, stop/restart
same thread, absent goal, limits unavailable, no-agent completion, schema decode failure,
and live history not mislabeled terminal.

- [ ] **Step 4: Add adversarial endpoint/lock/process cases**

Reproduce symlinked/foreign/permissive lock and socket attacks, unsafe parent, stale
replacement owner mismatch, chmod-before-listen, client response-ID mismatch,
shutdown-response disconnect, signal child cleanup, oversized/non-finite JSON, huge
timeouts, and socket-path length. Every refusal must preserve unrelated files and exit
without ResourceWarnings.

- [ ] **Step 5: Run warning-strict focused/fast gates and commit**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_facade_integration.py tests/codex-worker/test_rpc_cli.py tests/codex-worker/test_live_harness_contract.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add tests/codex-worker/fake_codex.py tests/codex-worker/test_facade_integration.py \
  tests/codex-worker/test_rpc_cli.py tests/codex-worker/test_live_harness_contract.py
git commit -m "test(codex-worker): harden named worker command surface"
```

### Task 7: Skill, operator reference, and technical appendix

**Role in the build:** Teach Claude Code and other harnesses the finished low-friction surface while preserving native Claude Code as an equal SDD mechanism (R1–R3, R8, R12; D1, D11–D12, D21–D23, D37–D38).

**Read first:** Invoke `superdev:writing-skills`; design §1, §3 UC1–UC3, and §5.8; CLI surface §§1–9 and §11; `skills/subagent-driven-development/SKILL.md` model-selection section; `skills/using-superdev/references/codex-tools.md` command-routing section.

**Files:**
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `skills/subagent-driven-development/codex-worker.md`
- Modify: `skills/subagent-driven-development/codex-model-selection.md`
- Modify: `skills/using-superdev/references/codex-tools.md`
- Modify: `tests/codex-worker/test_skill_integration.py`
- Create: `docs/superdev/reviews/2026-08-19-codex-worker-command-doc-checkpoint.md`

**Interfaces:**
- Consumes: the verified Task 5 CLI/help and exact CLI companion.
- Produces: short skill happy path (`start` then `run`), collision-resistant naming guidance, full-access/read-only/model-tier rules, preserved native Claude route, and separate advanced technical appendix.

- [ ] **Step 1: Read `superdev:writing-skills` and map each consumer**

Record which document owns product commands, model policy, SDD dispatch behavior, and
advanced recovery. Do not copy the full CLI table into multiple skills.

- [ ] **Step 2: Add only focused structural guards**

Assert the SDD skill requires randomized/numbered names, uses `start` for first message
and `run` for follow-ups, does not mention `daemon ensure`, and keeps native Claude Code
routing. Assert the operator reference links the technical appendix and the appendix
contains goal/history/limits, stop, timeout recovery, instance precedence, full/read-only,
and raw recovery.

- [ ] **Step 3: Rewrite docs against the real help/output**

Lead with:

```bash
codex-worker start --name implement-a31 --prompt-file task.md
codex-worker run --name implement-a31 --prompt "Run the focused gate and report."
```

Show optional goal/schema/tier/read-only on creation, five shell commands as harness-
owned fan-out, status/messages/steer/interrupt, non-destructive stop, and native proxies.
Move raw socket/session/turn choreography to the technical appendix. State explicitly
that Claude Code remains available and Codex is selected only when operator/plan says so.

- [ ] **Step 4: Dispatch two small semantic reviewers**

Reviewer A checks a Claude coordinator can launch/follow up/fan out/recover without
source inspection. Reviewer B checks model/access/native-Claude boundaries and exact
CLI/help agreement. Record verbatim findings/verdicts in the checkpoint and fix any
semantic blocker. Do not run a 45-call behavior campaign.

- [ ] **Step 5: Run focused/fast gates and commit**

Run: `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_skill_integration.py -v`
Expected: PASS.

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add skills/subagent-driven-development/SKILL.md \
  skills/subagent-driven-development/codex-worker.md \
  skills/subagent-driven-development/codex-model-selection.md \
  skills/using-superdev/references/codex-tools.md \
  tests/codex-worker/test_skill_integration.py \
  docs/superdev/reviews/2026-08-19-codex-worker-command-doc-checkpoint.md
git commit -m "docs(sdd): adopt named codex worker commands"
```

### Task 8: Real CLI checkride, anchor receipts, and plugin release

**Role in the build:** Prove the operator journey against real Codex and Claude, fill every anchor receipt honestly, and publish the installed plugin only after the user-facing gate passes (R1–R13; UC1–UC10; AH1–AH12).

**Read first:** Invoke `superdev:cli-checkride`; design §3 and §9; CLI surface §§0–10; decision log D45/D49; Task 7's changed sections listed in its Files block; prior live harness/checkride evidence for mechanics only.

**Files:**
- Modify: `tests/codex-worker/live_broker_check.py`
- Modify: `tests/codex-worker/live_claude_check.sh`
- Modify: `tests/codex-worker/live_claude_evidence.py`
- Modify: `tests/codex-worker/test_live_claude_evidence.py`
- Modify: `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-design.md` receipt cells only
- Create: `docs/superdev/checkrides/2026-08-19-codex-worker-command-checkride.md`
- Create: `docs/superdev/checkrides/2026-08-19-codex-worker-command-evidence/` sanitized command-by-command evidence
- Modify via release tooling: `RELEASE-NOTES.md`, versioned plugin manifests, `package.json`

**Interfaces:**
- Consumes: Tasks 1–7 complete source and installed-launcher candidate.
- Produces: re-runnable real broker/Claude checks, tracked sanitized verbatim checkride evidence, AH1–AH12 receipts, version 7.2.0 source manifests and installed Claude plugin, plus passing Codex package/sync validation.

- [ ] **Step 1: Update harness assertions before live execution**

Add scenarios for fresh implicit start, short follow-up, five simultaneous named workers
with small tasks, status/messages/control, stop/restart same thread, full/read-only
policy capture, initial/update/show goal, durable history, available-or-typed-unavailable
limits, multiple/fallback final projection, schema verdict/report/review, non-Claude
instance override, and legacy socket daemon status/shutdown.

- [ ] **Step 2: Run deterministic preflight**

Run: `python3 tests/codex-worker/live_broker_check.py --preflight`
Expected: PASS with live model IDs/efforts and selected Terra/Sol routes recorded; missing
required model/effort is BLOCKED, never substituted.

- [ ] **Step 3: Run five real named workers and focused scenarios separately**

Run each scenario as its own killable command:

```bash
python3 tests/codex-worker/live_broker_check.py --scenario common-journey
python3 tests/codex-worker/live_broker_check.py --scenario five-workers
python3 tests/codex-worker/live_broker_check.py --scenario control-recovery
python3 tests/codex-worker/live_broker_check.py --scenario native-proxies
python3 tests/codex-worker/live_broker_check.py --scenario access-schema
```

Expected: PASS per scenario. Five-workers proves exactly five simultaneous names and
does not claim 100-worker capacity. Every reported count, duration, model, effort, ID,
and token field comes from the transcript or is labelled unavailable.

- [ ] **Step 4: Run the real Claude caller**

Run separately: `bash tests/codex-worker/live_claude_check.sh`
Expected: Claude uses only the PATH `codex-worker` common commands, creates a uniquely
named worker from its cwd, follows up without repeated configuration, consumes the
complete result, checks goal/history/status, and stops non-destructively. Evidence also
asserts native Claude Code remains available and no MCP/direct Codex invocation occurs.

- [ ] **Step 5: Invoke `superdev:cli-checkride` and iterate to evaluator PASS**

The executor drives every common command and refusal one at a time, plus the advanced
socket compatibility path. The evaluator checks command syntax, exact JSON shapes,
exit codes, paths, recovery actions, lifecycle side effects, nullable-phase fallback,
and provider metadata from the operator's perspective. Commit a sanitized-but-verbatim
full transcript; no ellipses or ignored-only evidence.

- [ ] **Step 6: Run finishing gates and fill receipts**

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

Run separately: `python3 tests/codex-worker/live_broker_check.py`
Expected: PASS for all affected real-broker scenarios.

Run separately: `bash tests/codex-worker/live_claude_check.sh`
Expected: PASS.

Fill design §9 with one re-runnable test/transcript/file receipt per AH1–AH12. Preserve
any unavailable limits/token metric as unavailable; file an owned backlog item for any
unanswered hint before autonomous close.

- [ ] **Step 7: Bump, audit, validate packaging, and commit version 7.2.0**

Run:

```bash
./scripts/bump-version.sh 7.2.0
./scripts/bump-version.sh --check
./scripts/bump-version.sh --audit
bash tests/codex/test-marketplace-manifest.sh
bash tests/codex/test-package-codex-plugin.sh
bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh
```

Add measured release notes, then commit the release source before installing from
`HEAD`:

```bash
git add RELEASE-NOTES.md package.json .claude-plugin/plugin.json \
  .claude-plugin/marketplace.json .codex-plugin/plugin.json \
  .cursor-plugin/plugin.json .kimi-plugin/plugin.json gemini-extension.json
git commit -m "chore(release): bump superdev to 7.2.0"
```

- [ ] **Step 8: Reinstall Claude plugin, verify installed launcher, and commit evidence**

Run exactly:

```bash
claude plugin update superdev@superdev-dev
claude plugin list
CLAUDE_PLUGIN_ROOT="$HOME/.claude/plugins/cache/superdev-dev/superdev/7.2.0"
test -x "$CLAUDE_PLUGIN_ROOT/bin/codex-worker"
INSTALLED_CHECK_DIR="$(mktemp -d)"
(cd "$INSTALLED_CHECK_DIR" && "$CLAUDE_PLUGIN_ROOT/bin/codex-worker" --help)
(cd "$INSTALLED_CHECK_DIR" && "$CLAUDE_PLUGIN_ROOT/bin/codex-worker" daemon status)
```

Record the installed 7.2.0 version line and both outside-repository invocations in the
tracked checkride evidence. Then commit all live evidence and receipt updates:

```bash
git add tests/codex-worker/live_broker_check.py tests/codex-worker/live_claude_check.sh \
  tests/codex-worker/live_claude_evidence.py tests/codex-worker/test_live_claude_evidence.py \
  docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-design.md \
  docs/superdev/checkrides/2026-08-19-codex-worker-command-checkride.md \
  docs/superdev/checkrides/2026-08-19-codex-worker-command-evidence
git commit -m "docs(codex-worker): record installed command checkride"
```

Run `git diff --check HEAD~1..HEAD`, `./scripts/bump-version.sh --check`, and the fast
gate once more. Record only the fresh outputs in the task report.
