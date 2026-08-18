# Codex Worker Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Unix-socket JSON-RPC broker that lets Claude Code control multiple durable Codex worker conversations with real steer, interrupt, recovery, and multi-model worktree validation.

**Architecture:** A thin `codex-worker` executable delegates to a Python 3.9-compatible standard-library package. The foreground threaded RPC daemon owns one `codex app-server` stdio child, a crash-safe UUID↔thread registry, and per-session observable turn state; short-lived CLI clients issue one JSON-RPC request and print one JSON response.

**Tech Stack:** Python 3.9 standard library (`argparse`, `dataclasses`, `json`, `socket`, `socketserver`, `subprocess`, `threading`, `unittest`), Codex app-server JSON-RPC, POSIX AF_UNIX, git worktrees, shell-driven Claude Code/Codex live checks.

**Execution:** subagent-driven

**Mode:** autonomous

**Context pack** — the artifacts downstream workers read:
- Spec: `docs/superdev/specs/2026-08-18-codex-worker-server-design.md` · Decision log: `docs/superdev/specs/2026-08-18-codex-worker-server-decisions.md`
- Domain model: design doc §5.8
- CLI surface: `docs/superdev/specs/2026-08-18-codex-worker-server-cli-surface.md`
- Prior art: `skills/subagent-driven-development/scripts/codex-worker`; `/Users/tadas/Downloads/codex-app-server-reference.md`; generated Codex 0.147.0 schema obtainable with `codex app-server generate-json-schema --experimental --out DIR`

## Global Constraints

- The broker control plane is local-only AF_UNIX; it never exposes TCP/WebSocket. The installed Codex CLI may use its configured model-provider service.
- Python 3.9 compatibility is mandatory; use only the standard library plus the installed Codex CLI.
- The daemon starts explicitly in the foreground and owns one directly launched, injectable `codex app-server` stdio child.
- One daemon manages multiple sessions. Daemon-minted UUID is stable identity; name is a non-unique annotation; raw thread ID is diagnostic/recovery identity.
- Session cwd is immutable. Raw recovery takes cwd only from the required Codex resume response, validates it, and never accepts a caller override.
- Turn start is non-blocking. No public streaming surface: status, cursor events, bounded wait, steer, and interrupt are separate operations.
- Every CLI client command emits exactly one JSON object; RPC/domain errors exit 1, usage/validation errors exit 2, success exits 0.
- Model IDs and supported efforts come only from live `model/list`; completion evidence requires at least two distinct model IDs and two distinct effort values.
- Unexpected approvals are declined and recorded; registry/state writes are atomic and owner-only; a live socket is never unlinked as stale.
- Use `superdev:writing-skills` before modifying `SKILL.md` or its behavior-shaping references.

**Test lanes:** fast (the affected-area gate): `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'` · slow-by-area (separate killable commands): `python3 tests/codex-worker/live_broker_check.py` and `bash tests/codex-worker/live_claude_check.sh` · scheduled sweep: none declared by this repository. Every commit runs the fast gate plus its focused tests; the two live checks run separately at their owning task and finishing gate.

**Engineering patterns:** none declared/detected — generic review rubric only. The repository has no `pyproject.toml`, `setup.py`, or declared binding canon; implementers follow the spec's explicit seams and domain invariants.

## The Through-Line

Task 1 is LOAD-BEARING: it defines stable domain/wire models and the crash-safe registry every later layer consumes. Task 2 is also LOAD-BEARING: it hardens the measured Codex transport and replaces consuming queues with multi-waiter runtime state. Task 3 composes those foundations into session/turn semantics without any socket or CLI concerns. Task 4 exposes that broker through the approved JSON-RPC and CLI contracts. Task 5 teaches Claude Code's SDD workflow to use the finished surface and pressure-tests the skill wording. Task 6 proves the whole arc against real Codex models, distinct efforts, multiple git worktrees, daemon restarts, file/command tasks, steering, interruption, raw recovery, and a real Claude Code caller; it produces the receipts the finishing gate writes into the anchor.

When reality diverges from a task, do not patch locally and press on. Follow the threatened interface back through this Through-Line, check the governing decision's revisit hook in the spec, append a phase `build` decision to the decision log, and amend downstream Consumes/Produces blocks before continuing. A change that breaks session identity, immutable cwd, local-only transport, non-blocking control, or the exact live model gate breaks the anchor and must follow autonomous soften-but-own routing.

## Acceptance (anchored — do not restate here)

This plan discharges UC1–UC7 and AH1–AH12 from the design anchor. Task 4 produces deterministic CLI/RPC receipts; Task 5 produces Claude-facing behavior receipts; Task 6 produces every live receipt. The finishing gate fills one re-runnable receipt per hint into design §9. An unanswered hint is named and, in autonomous mode, gets an owned backlog item naming its UC#/AH# before close; AH2/R10 cannot be softened into a passing skip because D14 defines missing model multiplicity as BLOCKED.

---

### Task 1: Domain models and crash-safe session registry

**Role in the build:** Establish the stable identity, response, event, and persistence contracts that every other task consumes (R4–R5, R12–R13; D5–D6, D10, D12–D16).

**Read first:** Spec §5.3 and §5.8.1–5.8.4; CLI surface §3; decision log D12–D16.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/__init__.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/models.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/registry.py`
- Create: `tests/codex-worker/test_models_registry.py`

**Interfaces:**
- Consumes: only Python 3.9 standard library.
- Produces: `JsonObject = Dict[str, Any]`; frozen `IdentifierSelector`, `ErrorDetail`, `ItemRecord`, `TurnSnapshot`, `EventRecord`, `EventPage`, `RuntimeStatus`, and `SessionRecord` dataclasses; `RpcFault(code: int, message: str, kind: str, recovery: Optional[str] = None, details: Optional[JsonObject] = None)` with `to_dict() -> JsonObject`; the sole `rpc_response(request_id: Optional[Union[str, int]], result: Optional[JsonObject] = None, fault: Optional[RpcFault] = None) -> JsonObject` serializer; `session_result(record: SessionRecord, attached: bool) -> JsonObject`; `SessionRegistry(path)` with `list() -> List[SessionRecord]`, `try_resolve(selector: IdentifierSelector) -> Optional[SessionRecord]`, `resolve(selector: IdentifierSelector) -> SessionRecord`, `create(thread_id: str, cwd: str, name: Optional[str], model: Optional[str], effort: Optional[str], session_id: Optional[str] = None) -> SessionRecord`, and `update_annotations(session_id: str, model: Optional[str] = None, effort: Optional[str] = None) -> SessionRecord`.

- [ ] **Step 1: Write failing model-invariant tests**

```python
class ModelTests(unittest.TestCase):
    def test_identifier_selector_requires_exactly_one_namespace(self):
        with self.assertRaises(ValueError):
            IdentifierSelector()
        with self.assertRaises(ValueError):
            IdentifierSelector(session_id="a", thread_id="b")
        self.assertEqual(IdentifierSelector(session_id="a").kind, "session")

    def test_rpc_error_response_supports_null_id(self):
        response = rpc_response(None, fault=RpcFault(-32700, "Parse error", "parse_error"))
        self.assertEqual(response["id"], None)
        self.assertIn("error", response)
        self.assertNotIn("result", response)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python3 -m unittest tests/codex-worker/test_models_registry.py -v`
Expected: FAIL because `codex_worker.models` and `SessionRegistry` do not exist.

- [ ] **Step 3: Implement Python 3.9-compatible domain and wire models**

```python
@dataclass(frozen=True)
class IdentifierSelector:
    session_id: Optional[str] = None
    thread_id: Optional[str] = None

    def __post_init__(self) -> None:
        if (self.session_id is None) == (self.thread_id is None):
            raise ValueError("exactly one of session_id or thread_id is required")

    @property
    def kind(self) -> str:
        return "session" if self.session_id is not None else "thread"


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    thread_id: str
    cwd: str
    created_at: str
    updated_at: str
    name: Optional[str] = None
    model: Optional[str] = None
    effort: Optional[str] = None
```

Implement explicit `to_dict`/`from_dict` functions; do not use `asdict` recursively across the wire seam because optional/sum-type validation must remain explicit.

- [ ] **Step 4: Add failing registry uniqueness, corruption, permissions, and atomicity tests**

```python
def test_registry_rejects_duplicate_thread_ids(self):
    registry = SessionRegistry(self.state_path)
    first = registry.create("thr-1", self.cwd, "one", None, None)
    with self.assertRaises(RegistryConflict):
        registry.create("thr-1", self.cwd, "two", None, None)
    self.assertEqual(registry.resolve(IdentifierSelector(session_id=first.session_id)), first)

def test_failed_replace_preserves_previous_snapshot(self):
    registry = SessionRegistry(self.state_path)
    record = registry.create("thr-1", self.cwd, None, None, None)
    with mock.patch("os.replace", side_effect=OSError("boom")):
        with self.assertRaises(OSError):
            registry.update_annotations(record.session_id, model="changed")
    restored = SessionRegistry(self.state_path)
    self.assertIsNone(restored.resolve(IdentifierSelector(session_id=record.session_id)).model)
```

- [ ] **Step 5: Implement schema-versioned atomic registry persistence**

```python
class SessionRegistry:
    SCHEMA_VERSION = 1

    def _save_locked(self, records: Sequence[SessionRecord]) -> None:
        parent = self.path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name + ".", dir=str(parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"schema_version": 1, "sessions": [session_to_dict(x) for x in records]}, handle)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, str(self.path))
        except BaseException:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
            raise
```

Validate UUID syntax, absolute existing directory cwd, duplicate session/thread IDs, schema version, and exact field types on load.

- [ ] **Step 6: Run focused and fast gates**

Run: `python3 -m unittest tests/codex-worker/test_models_registry.py -v`
Expected: PASS.

Run: `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/subagent-driven-development/scripts/codex_worker tests/codex-worker/test_models_registry.py
git commit -m "feat(codex-worker): add durable session domain"
```

### Task 2: Hardened Codex adapter and observable runtime state

**Role in the build:** Turn the measured one-shot transport into a thread-safe shared adapter and non-consuming multi-waiter runtime (R3, R6–R9, R11; D7–D8, D10–D11, D13).

**Read first:** Spec §5.2, §5.4, §5.6 and §5.8.3–5.8.4; supplied reference §§4–5, 7–8, 11–13, 17–18; prototype module docstring and dispatch code.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/app_server.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/runtime.py`
- Create: `tests/codex-worker/fake_codex.py`
- Create: `tests/codex-worker/test_app_server_runtime.py`

**Interfaces:**
- Consumes: Task 1 `TurnSnapshot`, `ItemRecord`, `EventRecord`, `ErrorDetail`.
- Produces: `CodexAppServer(cwd: str, codex_argv: Sequence[str], on_notification: Callable[[JsonObject], None], approval_handler: Optional[Callable[[JsonObject], JsonObject]] = None)`; `list_models() -> List[JsonObject]`; `start_thread(cwd: str, model: Optional[str] = None) -> JsonObject`; `resume_thread(thread_id: str, approval_policy: str = "never", sandbox: str = "workspace-write") -> JsonObject`; `start_turn(thread_id: str, prompt: str, model: Optional[str] = None, effort: Optional[str] = None) -> str`; `steer(thread_id: str, turn_id: str, prompt: str) -> str`; `interrupt(thread_id: str, turn_id: str) -> None`; `shutdown() -> None`. `RuntimeStore(event_limit: int)` produces `attach(record: SessionRecord) -> None`, `detach_all(reason: ErrorDetail) -> None`, `on_notification(message: JsonObject) -> None`, `status(session_id: str) -> RuntimeStatus`, `reserve_start(session_id: str) -> None`, `cancel_start(session_id: str) -> None`, `reconcile_start(session_id: str, returned_turn_id: str) -> None`, `require_idle(session_id: str) -> None`, `wait(session_id: str, timeout: float) -> TurnSnapshot`, and `events(session_id: str, after: int, limit: int) -> EventPage`.

- [ ] **Step 1: Build a fake Codex executable and write failing handshake/concurrency tests**

```python
def test_concurrent_calls_do_not_interleave_json_lines(self):
    client = self.make_client()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: client.list_models(), range(20)))
    self.assertTrue(all(result[0]["id"] == "fake-model-a" for result in results))

def test_unexpected_approval_is_declined_and_emitted(self):
    client = self.make_client(fake_mode="approval")
    client.start_thread(self.cwd)
    result = client.run_fake_approval_turn()
    self.assertEqual(result["decision"], "decline")
    self.assertTrue(any(event["event"] == "approval_declined" for event in self.events))
```

The fake executable must implement initialize/initialized, model/list, thread/start/resume, turn/start/steer/interrupt, configurable delayed completion, item events, malformed output, child exit, and server-initiated approval requests.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests/codex-worker/test_app_server_runtime.py -v`
Expected: FAIL because the adapter/runtime modules do not exist.

- [ ] **Step 3: Implement locked stdio transport and fail-all-pending shutdown**

```python
def call(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 120.0) -> Dict[str, Any]:
    request_id = next(self._ids)
    pending = queue.Queue(maxsize=1)
    with self._state_lock:
        self._require_open()
        self._pending[request_id] = pending
    self._send({"method": method, "id": request_id, "params": params or {}})
    try:
        message = pending.get(timeout=timeout)
    except queue.Empty:
        with self._state_lock:
            self._pending.pop(request_id, None)
        raise CodexCallError("timeout", method)
    if "error" in message:
        raise CodexCallError.from_response(method, message["error"])
    return message["result"]

def _send(self, message: Dict[str, Any]) -> None:
    encoded = json.dumps(message, separators=(",", ":")) + "\n"
    with self._write_lock:
        self._require_open()
        self.proc.stdin.write(encoded)
        self.proc.stdin.flush()
```

On EOF or JSON framing failure, atomically close the adapter and place one transport exception into every pending queue. The stderr drain records diagnostics without prompts or secrets.

- [ ] **Step 4: Write failing multi-waiter/event-truncation/race tests**

```python
def test_all_waiters_observe_same_completion(self):
    store = RuntimeStore(event_limit=3)
    store.attach(self.session)
    with ThreadPoolExecutor(max_workers=2) as pool:
        waits = [pool.submit(store.wait, self.session.session_id, 2.0) for _ in range(2)]
        store.on_notification(self.completed_message("turn-1"))
    self.assertEqual([future.result().turn_id for future in waits], ["turn-1", "turn-1"])

def test_event_page_marks_evicted_cursor(self):
    store = RuntimeStore(event_limit=2)
    store.attach(self.session)
    for index in range(3):
        store.record_test_event(self.session.session_id, "item_completed", str(index))
    page = store.events(self.session.session_id, after=0, limit=10)
    self.assertTrue(page.truncated)
    self.assertEqual([event.cursor for event in page.events], [2, 3])
```

- [ ] **Step 5: Implement condition-based runtime state and authoritative normalization**

```python
@dataclass
class _SessionRuntime:
    record: SessionRecord
    condition: threading.Condition = field(default_factory=threading.Condition)
    active_turn_id: Optional[str] = None
    start_pending: bool = False
    latest_turn: Optional[TurnSnapshot] = None
    next_cursor: int = 1
    events: Deque[EventRecord] = field(default_factory=deque)

def wait(self, session_id: str, timeout: float) -> TurnSnapshot:
    runtime = self._get(session_id)
    deadline = time.monotonic() + timeout
    with runtime.condition:
        while runtime.active_turn_id is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WaitTimeout(session_id, runtime.active_turn_id)
            runtime.condition.wait(remaining)
        if runtime.latest_turn is None:
            raise NoTurn(session_id)
        return runtime.latest_turn
```

Normalize only `turn_started`, `turn_completed`, `item_completed`, `approval_declined`, and `transport_error`; keep upstream item-specific JSON inside `ItemRecord.data`.

`reserve_start` atomically sets `start_pending` before the upstream call. Notification dispatch owns active/terminal identity: `turn/started` clears `start_pending` and sets `active_turn_id`; `turn/completed` clears both and sets `latest_turn`. `reconcile_start` accepts response-after-notification and response-after-completion when IDs match, synthesizes active state only when no notification arrived, and raises a protocol fault on mismatched IDs. `cancel_start` clears the reservation after an upstream start failure.

- [ ] **Step 6: Run focused and fast gates**

Run: `python3 -m unittest tests/codex-worker/test_app_server_runtime.py -v`
Expected: PASS, including concurrent requests and two waiters.

Run: `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/subagent-driven-development/scripts/codex_worker tests/codex-worker/fake_codex.py tests/codex-worker/test_app_server_runtime.py
git commit -m "feat(codex-worker): add shared Codex transport runtime"
```

### Task 3: Broker session and turn semantics

**Role in the build:** Compose registry and runtime into the high-level worker contract, including explicit attach/recovery and immutable sandbox identity (R3–R9, R13; D5–D8, D12–D14).

**Read first:** Spec §4, §5.2–5.6, domain invariants §5.8.4, result table §5.8.1; CLI surface workflows §5.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/broker.py`
- Create: `tests/codex-worker/test_broker.py`

**Interfaces:**
- Consumes: Task 1 `SessionRegistry` and command/result models; Task 2 `CodexAppServer`, `RuntimeStore`.
- Produces: `WorkerBroker` with exact methods/results: `daemon_status() -> {ready, daemon_pid, codex_pid, socket_path, state_path, session_count}`; `model_list() -> {models}`; `session_start(cwd: str, name: Optional[str], model: Optional[str]) -> {session, attached}`; `session_resume(selector: IdentifierSelector, name: Optional[str]) -> {session, attached}`; `session_list() -> {sessions}`; `session_show(selector: IdentifierSelector) -> {session, attached, active_turn_id, latest_turn}`; `turn_start(selector: IdentifierSelector, prompt: str, model: Optional[str], effort: Optional[str]) -> {session_id, thread_id, turn_id, status}`; `turn_status(selector: IdentifierSelector) -> {session_id, thread_id, attached, active_turn_id, latest_turn}`; `turn_wait(selector: IdentifierSelector, timeout: float) -> {session_id, thread_id, turn}`; `turn_events(selector: IdentifierSelector, after: int, limit: int) -> {events, next_cursor, truncated}`; `turn_steer(selector: IdentifierSelector, prompt: str) -> {session_id, thread_id, turn_id, accepted}`; `turn_interrupt(selector: IdentifierSelector) -> {session_id, thread_id, turn_id, accepted}`; `shutdown() -> {accepted}`. Every brace shape is a `JsonObject` serialized with Task 1 model serializers.

- [ ] **Step 1: Write failing session start/resume and selector-intent tests**

```python
def test_raw_thread_recovery_uses_returned_cwd_and_persists_mapping(self):
    self.codex.resume_result = {"thread": {"id": "thr-9", "cwd": self.cwd}, "cwd": self.cwd}
    result = self.broker.session_resume(IdentifierSelector(thread_id="thr-9"), name="recovered")
    self.assertEqual(result["session"]["thread_id"], "thr-9")
    self.assertEqual(result["session"]["cwd"], self.cwd)
    self.assertEqual(self.codex.resume_calls[0]["cwd"], None)
    self.assertEqual(self.codex.resume_calls[0]["sandbox"], "workspace-write")

def test_turn_with_unknown_thread_refuses_instead_of_implicit_recovery(self):
    with self.assertRaisesRegex(RpcFault, "session resume --thread"):
        self.broker.turn_status(IdentifierSelector(thread_id="unknown"))
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests/codex-worker/test_broker.py -v`
Expected: FAIL because `WorkerBroker` does not exist.

- [ ] **Step 3: Implement explicit session attachment and raw recovery**

```python
def session_resume(self, selector: IdentifierSelector, name: Optional[str] = None) -> Dict[str, Any]:
    existing = self.registry.try_resolve(selector)
    if existing is not None:
        response = self.codex.resume_thread(existing.thread_id)
        self._validate_resume_cwd(existing.cwd, response)
        self.runtime.attach(existing)
        return session_result(existing, attached=True)
    if selector.thread_id is None:
        raise unknown_session(selector.session_id)
    response = self.codex.resume_thread(selector.thread_id, approval_policy="never", sandbox="workspace-write")
    recovered_cwd = validate_recovered_cwd(response["thread"]["cwd"])
    record = self.registry.create(selector.thread_id, recovered_cwd, name, response.get("model"), response.get("reasoningEffort"))
    self.runtime.attach(record)
    return session_result(record, attached=True)
```

Persist mappings only after upstream resume and cwd validation succeed. Existing logical-session resume must reject upstream cwd drift.

- [ ] **Step 4: Add failing active-turn, model/effort, wait, steer, and interrupt tests**

```python
def test_turn_start_validates_effort_against_live_model_list(self):
    session = self.start_session()
    with self.assertRaises(ModelSelectionError):
        self.broker.turn_start(session, "task", model="fake-model-a", effort="unsupported")

def test_wait_does_not_block_steer(self):
    session = self.start_active_turn()
    with ThreadPoolExecutor(max_workers=2) as pool:
        waiter = pool.submit(self.broker.turn_wait, session, 2.0)
        steered = self.broker.turn_steer(session, "narrow the task")
        self.codex.complete_active_turn()
    self.assertTrue(steered["accepted"])
    self.assertEqual(waiter.result()["turn"]["status"], "completed")
```

- [ ] **Step 5: Implement broker routing without holding locks across blocking calls**

```python
def turn_start(self, selector: IdentifierSelector, prompt: str, model: Optional[str], effort: Optional[str]) -> Dict[str, Any]:
    record = self._require_attached(selector)
    self._validate_model_effort(model, effort)
    self.runtime.reserve_start(record.session_id)
    try:
        turn_id = self.codex.start_turn(record.thread_id, prompt, model=model, effort=effort)
        self.runtime.reconcile_start(record.session_id, turn_id)
    except BaseException:
        self.runtime.cancel_start(record.session_id)
        raise
    self.registry.update_annotations(record.session_id, model=model, effort=effort)
    return {"session_id": record.session_id, "thread_id": record.thread_id, "turn_id": turn_id, "status": "in_progress"}
```

Treat interrupt completion races as typed `turn_not_active` faults carrying `latest_turn`; never implicitly steer/start a replacement turn.

Add a test mode where fake Codex emits `turn/started` and `turn/completed` before replying to `turn/start`. Assert the literal `turn_start` response returns the matching ID with `status: "in_progress"`, while the runtime/status projection is terminal, no active turn remains, and the next turn can reserve successfully. Add a mismatched-response-ID case that fails as `codex_protocol_error`.

- [ ] **Step 6: Run focused and fast gates**

Run: `python3 -m unittest tests/codex-worker/test_broker.py -v`
Expected: PASS.

Run: `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/subagent-driven-development/scripts/codex_worker/broker.py tests/codex-worker/test_broker.py
git commit -m "feat(codex-worker): add durable worker broker"
```

### Task 4: Unix JSON-RPC server and exhaustive CLI

**Role in the build:** Expose the approved local service and every Claude-facing daemon/model/session/turn operation with stable JSON and exit behavior (R1–R3, R6–R7, R12–R13; D1–D3, D7–D8, D12, D15).

**Read first:** Spec §5.1, §5.5–5.6, §5.8.1 and §5.8.5; entire CLI surface companion; decision log D15–D16.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/rpc.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/cli.py`
- Modify: `skills/subagent-driven-development/scripts/codex-worker`
- Create: `tests/codex-worker/test_rpc_cli.py`

**Interfaces:**
- Consumes: Task 3 `WorkerBroker`; Task 1 `IdentifierSelector`, `RpcFault`, and sole `rpc_response` serializer.
- Produces: `RpcServer(socket_path, broker)`, `rpc_call(socket_path, method, params, timeout)`, `build_parser()`, `main(argv=None) -> int`, and the exact CLI/RPC methods in the companion.

- [ ] **Step 1: Write failing JSON-RPC and socket-safety tests**

```python
def test_parse_error_uses_null_id_and_standard_code(self):
    response = self.send_raw(b"not-json\n")
    self.assertEqual(response, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error", "data": {"kind": "parse_error"}}})

def test_live_socket_is_never_unlinked(self):
    first = self.start_server()
    with self.assertRaises(SocketInUse):
        RpcServer(self.socket_path, self.other_broker).serve_forever()
    self.assertTrue(self.ping(first))

def test_stale_socket_is_replaced_with_owner_only_mode(self):
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(self.socket_path)
    stale.close()
    server = self.start_server()
    self.assertEqual(stat.S_IMODE(os.stat(self.socket_path).st_mode), 0o600)
    self.assertTrue(self.ping(server))

def test_non_socket_collision_is_never_removed(self):
    Path(self.socket_path).write_text("owned by another process")
    with self.assertRaises(SocketPathUnsafe):
        self.start_server()
    self.assertEqual(Path(self.socket_path).read_text(), "owned by another process")
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests/codex-worker/test_rpc_cli.py -v`
Expected: FAIL because `rpc.py` and `cli.py` do not exist.

- [ ] **Step 3: Implement one-request-per-connection threaded AF_UNIX JSON-RPC**

```python
class ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

def encode_response(request_id: Optional[Union[str, int]], result: Optional[JsonObject] = None, fault: Optional[RpcFault] = None) -> bytes:
    envelope = rpc_response(request_id, result=result, fault=fault)
    return (json.dumps(envelope, separators=(",", ":")) + "\n").encode("utf-8")
```

Probe an existing socket with a bounded `daemon/status` RPC. Refuse if live or if the path is not a socket; unlink only a socket that fails the probe. Set `0o600` after bind. Signal/RPC shutdown preserves state and terminates the child.

- [ ] **Step 4: Write failing exhaustive parser/output/exit tests**

```python
def test_every_client_command_emits_one_json_object(self):
    cases = documented_client_argv_cases(self.session_id, self.thread_id, self.prompt_file)
    self.assertEqual(len(cases), 13)
    self.assertEqual({case.method for case in cases}, DOCUMENTED_CLIENT_METHODS)
    for case in cases:
        argv = case.argv
        completed = self.run_cli(argv)
        self.assertEqual(completed.returncode, case.expected_exit, argv)
        lines = completed.stdout.splitlines()
        self.assertEqual(len(lines), 1, argv)
        payload = json.loads(lines[0])
        self.assertEqual(("result" in payload, "error" in payload), case.expected_envelope)

def test_daemon_absent_is_structured_and_exit_one(self):
    completed = self.run_cli(["daemon", "status"], daemon_running=False)
    self.assertEqual(completed.returncode, 1)
    self.assertEqual(json.loads(completed.stdout)["error"]["data"]["kind"], "daemon_unavailable")

def test_pretty_is_rejected_for_foreground_serve(self):
    completed = self.run_cli(["--pretty", "daemon", "serve"])
    self.assertEqual(completed.returncode, 2)
```

- [ ] **Step 5: Implement noun-first CLI and thin executable bootstrap**

```python
#!/usr/bin/env python3
from codex_worker.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

Build mutually exclusive `--session`/`--thread` and `--prompt`/`--prompt-file` groups for every documented command. Preserve selector field names in RPC params. `daemon serve` logs to stderr and produces no stdout object; all client commands produce one result/error object.

Define `DOCUMENTED_CLIENT_METHODS` explicitly as `{daemon/status, daemon/shutdown, model/list, session/start, session/resume, session/list, session/show, turn/start, turn/status, turn/wait, turn/events, turn/steer, turn/interrupt}` and a 13-row `CliCase` manifest with one successful fake-daemon argv/result assertion per method. Add separate fixed expectations for usage exit 2 and domain/RPC exit 1; never accept a set of possible exit codes.

- [ ] **Step 6: Run help-contract, focused, and fast gates**

Run: `python3 skills/subagent-driven-development/scripts/codex-worker --help`
Expected: exit 0; lists daemon, model, session, turn.

Run: `python3 -m unittest tests/codex-worker/test_rpc_cli.py -v`
Expected: PASS.

Run: `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/subagent-driven-development/scripts/codex-worker skills/subagent-driven-development/scripts/codex_worker tests/codex-worker/test_rpc_cli.py
git commit -m "feat(codex-worker): expose local RPC daemon and CLI"
```

### Task 5: Claude Code workflow integration and skill pressure tests

**Role in the build:** Make the new local broker discoverable and safely operable from the SDD workflow without changing brainstorming's main-session design law (R2, R8–R9, R12; D1–D3, D9, D14).

**Read first:** `skills/subagent-driven-development/SKILL.md` sections Model Selection, Handling Implementer Status, File Handoffs, Red Flags; spec §5.5–5.7; CLI surface §5–6; `skills/writing-skills/SKILL.md` in full before any skill edit.

**Files:**
- Create: `skills/subagent-driven-development/codex-worker.md`
- Modify: `skills/subagent-driven-development/SKILL.md`
- Create: `tests/codex-worker/test_skill_integration.py`

**Interfaces:**
- Consumes: Task 4 executable and exact CLI surface.
- Produces: a concise SDD reference defining when a Claude Code coordinator may choose a Codex worker, explicit daemon ownership, model discovery, file handoffs, status mapping, recovery, and prohibition on using Codex as the required independent reviewer of its own changes.

- [ ] **Step 1: Invoke `superdev:writing-skills` and write failing structural/pressure tests**

```python
def test_sdd_links_codex_worker_reference(self):
    text = Path("skills/subagent-driven-development/SKILL.md").read_text()
    self.assertIn("[Codex worker broker](codex-worker.md)", text)

def test_reference_names_required_control_and_recovery_commands(self):
    text = Path("skills/subagent-driven-development/codex-worker.md").read_text()
    for fragment in ("model list", "turn start", "turn steer", "turn interrupt", "session resume", "turn wait"):
        self.assertIn(fragment, text)
```

Pressure scenarios must cover: daemon absent; model requested without discovery; same Codex session proposed as implementer and reviewer; lost daemon with retained UUID; raw-thread registry repair; and attempting to retarget cwd.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests/codex-worker/test_skill_integration.py -v`
Expected: FAIL because the reference/link do not exist.

- [ ] **Step 3: Write the minimal reference and SDD link**

```markdown
## Codex workers from Claude Code

When the operator or plan selects a Codex worker, read [Codex worker broker](codex-worker.md). Start its daemon explicitly, discover models live, give each implementer/reviewer a distinct session and worktree, and preserve the normal task brief/report/review-package contracts. A worker never reviews its own diff, and a resumed session never changes cwd.
```

The reference must present operator sequences from the CLI companion, map Codex terminal states to DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED report handling, and state that brainstorming design reasoning remains in the main session.

- [ ] **Step 4: Run deterministic pressure checks and one real Claude description check**

Run: `python3 -m unittest tests/codex-worker/test_skill_integration.py -v`
Expected: PASS.

Run separately: `bash tests/claude-code/test-subagent-driven-development.sh`
Expected: PASS and describe SDD without losing its mandatory review gates.

- [ ] **Step 5: Run fast gate and commit**

Run: `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

```bash
git add skills/subagent-driven-development/SKILL.md skills/subagent-driven-development/codex-worker.md tests/codex-worker/test_skill_integration.py
git commit -m "docs(sdd): add local Codex worker workflow"
```

### Task 6: Real multi-model, worktree, recovery, steering, and Claude Code checkride

**Role in the build:** Prove UC1–UC7 and AH1–AH12 through the real surfaces the operator named, producing measured receipts rather than mock-backed claims (R8–R10; D9, D14, D16).

**Read first:** Design §3 and §9, spec §5.7, CLI surface §5, decision log D9/D14/D16; invoke `superdev:cli-checkride` and read its resolved `SKILL.md` before running the user-facing gate.

**Files:**
- Create: `tests/codex-worker/live_broker_check.py`
- Create: `tests/codex-worker/live_claude_check.sh`
- Create during execution (git-ignored): `.superdev/codex-worker-live/` transcripts, generated prompts, state, sockets, and receipt summary.
- Modify at finishing gate: `docs/superdev/specs/2026-08-18-codex-worker-server-design.md` receipt column only.

**Interfaces:**
- Consumes: Tasks 1–5 complete broker/CLI and reference.
- Produces: independently re-runnable live scripts and `.superdev/codex-worker-live/receipts.json` mapping AH1–AH12 to command/transcript evidence.

- [ ] **Step 1: Write the live harness assertions before running Codex**

```python
models = client("model", "list")["models"]
selected = choose_two_distinct_models_and_efforts(models)
if len({item["model"] for item in selected}) < 2 or len({item["effort"] for item in selected}) < 2:
    raise SystemExit("BLOCKED: D14 requires two distinct models and two distinct efforts")

assert run_a["turn"]["status"] == "completed"
assert (worktree_a / "hello-output.txt").read_text() == "Hello from Codex\n"
assert run_b["turn"]["status"] == "completed"
assert subprocess.run([sys.executable, str(worktree_b / "math_cli.py"), "2", "5"], check=True, capture_output=True, text=True).stdout == "7\n"
assert resumed_token.read_text().strip() == recovery_token
assert interrupted["turn"]["status"] == "interrupted"
```

The script creates one temporary git repository with two named branches/worktrees, starts the broker explicitly, stores the returned UUID/thread IDs, and validates every path before cleanup.

- [ ] **Step 2: Run the live model discovery preflight**

Run: `python3 tests/codex-worker/live_broker_check.py --preflight`
Expected: PASS with JSON naming at least two distinct live model IDs and two effort values; otherwise BLOCKED exactly as D14 requires.

- [ ] **Step 3: Implement and run the hello-world and second-worktree tasks concurrently**

Worker A prompt must require `hello.py` to write exactly `Hello from Codex\n` to `hello-output.txt`, execute it, and report the command. It also gives a random recovery token and says to remember but not write it. Worker B prompt requires a tested `math_cli.py` that prints the sum of integer arguments; it uses the other discovered model and a different effort. Start both before waiting for either.

Run: `python3 tests/codex-worker/live_broker_check.py --scenario concurrent-worktrees`
Expected: PASS; transcript records model IDs, efforts, session/thread/turn IDs, commands, output files, and no cross-worktree files.

- [ ] **Step 4: Implement and run live steer and interrupt scenarios**

Start a deliberately broad file-generation turn, immediately steer it to create only `steered.txt` with exact content `steer accepted\n`, then wait and verify. Start a separate analysis turn, immediately interrupt it, wait, and require terminal `interrupted`. Then call idle steer/interrupt and assert typed non-zero errors.

Run: `python3 tests/codex-worker/live_broker_check.py --scenario control`
Expected: PASS with one accepted in-flight steer, one interrupted turn, and honest idle refusals.

- [ ] **Step 5: Implement and run live observation and socket-safety scenarios**

Start a real Codex turn, launch two independent `turn wait` client processes before completion, sample `turn status` while active, and page `turn events` with an intentionally small event limit. Assert both waiters return the same terminal turn ID/status, status remains non-consuming, cursors increase, and requesting an evicted cursor returns `truncated: true`.

Inspect the running daemon with `stat`/Python `socket` APIs: the endpoint is a Unix socket with mode `0600`. Start a second daemon against the live socket and require refusal without unlinking it. Shut down, bind-and-close a real stale AF_UNIX socket, restart successfully, and verify replacement. Run `lsof -Pan -p DAEMON_PID -iTCP -sTCP:LISTEN` and require no TCP listener owned by the broker process; record the command/output in the receipt.

Run: `python3 tests/codex-worker/live_broker_check.py --scenario observe-socket`
Expected: PASS with two identical waiter results, bounded-event truncation, live-collision refusal, stale-socket recovery, owner-only mode, and no broker TCP listener.

- [ ] **Step 6: Implement and run UUID restart and raw-thread registry repair**

Shut down the daemon, restart it with the same registry, resume Worker A by UUID, and ask it to write the remembered recovery token to `resumed-token.txt`. Shut down again, start with a fresh empty registry, resume the same raw thread ID, and ask a context-dependent follow-up; verify the returned new UUID, authoritative recovered cwd, and retained context.

Run: `python3 tests/codex-worker/live_broker_check.py --scenario recovery`
Expected: PASS with both resume paths and no caller-supplied cwd.

- [ ] **Step 7: Implement and run fail-closed approval requests through the real daemon surface**

Launch the actual broker/CLI processes with the injectable `tests/codex-worker/fake_codex.py` child in each of three modes: command approval, file-change approval, and user-input request. For every mode, start a session/turn through the Unix RPC client, require the fake upstream to receive the decline/empty-answer response, wait without a stall, and assert `turn events` contains `approval_declined` with the approval method and no prompt/secret content. Label this receipt `deterministic live broker + fake upstream`; do not report it as a real-model approval event.

Run: `python3 tests/codex-worker/live_broker_check.py --scenario approvals`
Expected: PASS for all three server-initiated request kinds with inspectable decline events and completed/non-stalled turns.

- [ ] **Step 8: Implement and run the Claude Code caller scenario**

`live_claude_check.sh` starts the daemon, creates a disposable repo/worktree, then invokes Claude Code with only Bash access and a prompt directing it to use the documented `codex-worker` CLI to discover a model, start a session, ask Codex to create `from-claude.txt`, wait, inspect events, and report IDs. The script asserts the file and parses Claude's transcript for actual command invocations.

Run separately: `bash tests/codex-worker/live_claude_check.sh`
Expected: PASS; transcript proves Claude Code, not the test harness, invoked the broker successfully.

- [ ] **Step 9: Invoke `superdev:cli-checkride` and iterate until evaluator approval**

The executor drives every documented command family against the real foreground daemon, including usage errors, daemon absence, status, graceful shutdown, raw recovery, wait timeout, and benign control races. The evaluator compares JSON, exit codes, recovery text, and mechanisms to the CLI companion. Fix any failure with focused RED→GREEN tests, re-run fast gate, and repeat the checkride until approved.

- [ ] **Step 10: Run final affected-area gates and write measured receipts**

Run: `python3 -m unittest discover -s tests/codex-worker -p 'test_*.py'`
Expected: PASS.

Run separately: `python3 tests/codex-worker/live_broker_check.py`
Expected: PASS for all live broker scenarios.

Run separately: `bash tests/codex-worker/live_claude_check.sh`
Expected: PASS.

Populate `.superdev/codex-worker-live/receipts.json` from actual command outputs, then fill the design §9 receipt cells with one re-runnable command/transcript path per AH#; do not invent counts, IDs, timings, or model availability.

- [ ] **Step 11: Commit**

```bash
git add tests/codex-worker/live_broker_check.py tests/codex-worker/live_claude_check.sh docs/superdev/specs/2026-08-18-codex-worker-server-design.md docs/superdev/specs/2026-08-18-codex-worker-server-decisions.md
git commit -m "test(codex-worker): prove live Claude and Codex workflows"
```
