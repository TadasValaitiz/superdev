# Codex Worker Shared App-Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-Claude-session Codex daemons with one durable machine-local worker service whose gateway lets a human Codex TUI and Claude-driven workers share the same authoritative threads.

**Architecture:** One global service owns the existing protected Unix RPC endpoint, global durable registry, callback dispatcher, a private Codex app-server Unix-WebSocket, and a public maintenance-aware WebSocket gateway at `ws://127.0.0.1:4500`. Worker commands remain short and name-based; human attach/resume routes are projected from exact Codex thread IDs; guarded lifecycle and lossless legacy migration keep shared work safe.

**Tech Stack:** Python 3.9+, stdlib Unix RPC/persistence/process supervision, `websockets>=15,<16` synchronous client/server inside the isolated UV tool, Codex app-server JSON-RPC 0.150.1 contract, unittest and shell/live harnesses.

**Execution:** subagent-driven

**Mode:** autonomous — the operator explicitly delegated remaining decisions and build after ratifying the architecture. Unmet acceptance is filed with an owner and exact UC/AH reference; a contradiction to locked D1–D11 stops the build.

**Context pack** — downstream workers read the full set:
- Spec: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md` · Decision log: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-decisions.md`
- Angle companions: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-angle-01-service-ownership.md`; `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-angle-02-shared-control.md`; `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-angle-03-identity-and-cli.md`; `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-angle-04-lifecycle-and-migration.md`
- Census: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-census.md`
- Domain model: design §5.3
- CLI surfaces: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-cli-surface.md`; inherited raw contract `docs/superdev/specs/2026-08-18-codex-worker-server-cli-surface.md`; `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-cli-surface.md`; `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-cli-surface.md`; `docs/superdev/specs/2026-08-28-codex-worker-global-install-cli-surface.md`
- Prior art: `docs/superdev/specs/2026-08-28-codex-worker-global-install-design.md`; `docs/superdev/plans/2026-08-28-codex-worker-global-install.md`; `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-design.md`; `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-design.md`; `docs/superdev/specs/2026-08-18-codex-worker-server-design.md`

## Global Constraints

- Default public gateway is exactly `ws://127.0.0.1:4500`; collision refuses without fallback, kill, unlink, or peer trust.
- Public overrides are connectable `ws://HOST:PORT` only: port `1..65535`; no wildcard/unspecified host, userinfo, path, query, fragment, `wss`, public Unix, stdio, or `off`.
- One global service and global worker-name namespace; `CLAUDE_CODE_SESSION_ID` and other Claude values are callback metadata only.
- Common command exit never stops infrastructure. Stop/restart are supervised maintenance; force is never emitted as an automated recovery action.
- The Codex app-server is authoritative for thread/turn state. Worker mutations are never replayed; losing controls are typed.
- Legacy instance data is read-only input: unique records import, identical records deduplicate, divergent names quarantine, and no source is deleted.
- Python floor is 3.9. The isolated PEP 621 tool adds only `websockets>=15,<16`; the plugin itself remains dependency-free outside that tool environment.
- Existing strict one-JSON-object stdout, stderr, exit-code, security, callback, model-selection, raw proxy, durability, and exact-version contracts remain unless the CLI companion explicitly changes them.
- Release target is `8.1.0` under D19: first reconcile the six measured 7.10.0 declarations to the already-shipping 8.0.0 baseline without installation, then advance all eight authorities atomically only after the fresh checkride passes.

**Test lanes:** fast (the gate): `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` plus focused repository shell/package tests touched by the commit · slow-by-area (separate killable commands): the six exact `live_broker_check.py --scenario` names in Task 5, `python3 tests/codex-worker/live_uv_tool_check.py --scenario package-independence`, `bash tests/codex-worker/live_claude_check.sh`, the common-attach real two-client Codex/TUI probe, and CLI checkride executor/evaluator · scheduled sweep: none declared. Every commit gate runs the warning-strict fast suite; slow scenarios run separately only at their owning checkpoint and finishing gate.

**Engineering patterns:** `skills/engineering-patterns/python-patterns.md` (BINDING by stack detection), with the bounded D18 strict-dataclass exception, plus `skills/engineering-patterns/process-discipline.md` (ALWAYS). Implementers read the cited sections before coding and report every knowing departure.

## The Through-Line

The registry and identity arc is load-bearing: it removes session-derived infrastructure and creates one truthful global durable root before transport or CLI code can rely on it. The transport arc then replaces stdio with a private initialized WebSocket client and a transparent public gateway, sharing one maintenance gate across worker and TUI mutations. Once those two interfaces exist, the orchestration arc can reconcile TUI-originated events, inventory every active upstream thread, and preserve callback behavior. The public-surface arc finally rewires lifecycle, faults, RPC and CLI around the singleton without leaking transport mechanics. The experience arc first performs D19's behavior-neutral 8.0.0 identity reconciliation so trusted preflight can run, then teaches and acceptance-gates the finished behavior through real Codex, Claude and checkride lanes. Only after that PASS does the release arc bump 8.1.0, install the UV tool, and deliberately leave the global service running.

Tasks 1 and 2 are LOAD-BEARING because every later task consumes their exact paths, models, connection and maintenance interfaces. Tasks 3 and 4 are the behavioral composition: neither may invent a second state authority or bypass the gate. Task 5 acceptance-gates the behavior; Task 6 releases exactly that judged candidate and is not a place to repair architecture silently. If reality breaks an interface, follow the decision log's revisit hook, append a build-phase D#, update downstream Consumes/Produces, and keep locked D1–D11 intact.

## Acceptance (anchored — do not restate here)

This plan discharges design UC1–UC10 and AH1–AH12. Each checkpoint writes rerunnable receipts into the anchor §9 cells for its owned hints. C1 owns AH5/AH7/AH11 foundations; C2 owns AH1/AH3/AH4/AH6/AH8/AH9 foundations; C3 owns every live receipt and AH2/AH10/AH12; C4 verifies the installed candidate without changing those judgments. No hint may be marked by a plan assertion alone.

| Anchor item | Producing task and receipt |
|---|---|
| UC1 / AH1 | Tasks 1 and 4 produce global identity/attach projection; Task 5 records the live common start. |
| UC2 / AH2 | Tasks 2 and 3 produce shared control; Task 5 records the real two-client resume/control lane. |
| UC3 / AH3 | Tasks 1–4 produce global concurrency; Task 5 records exactly five simultaneous workers. |
| UC4 / AH4 | Tasks 2–4 produce persistent lifecycle/recovery; Task 5 records caller exit and same-thread resume. |
| UC5 / AH5 | Tasks 2 and 4 produce typed collision; Tasks 2 and 5 record isolated and live peer-preservation receipts. |
| UC6 / AH6 | Tasks 2–4 produce drain/inventory/version replacement; Task 5 records idle and active lanes. |
| UC7 / AH7 | Task 1 produces migration; Tasks 1 and 5 record fixture and live-sanitized receipts. |
| UC8 / AH8 | Tasks 2–4 produce guarded maintenance; Task 5 checkride records help/refusal/full impact. |
| UC9 / AH9 | Tasks 1 and 3 preserve callback independence; Task 5 records one composed same-worker callback-plus-TUI-control journey. |
| UC10 / AH10 | Tasks 2 and 4 preserve the full command surface; Task 5 records every common/raw family from an unrelated cwd under an isolated Python 3.9 UV install. |
| AH11 | Tasks 1–2 define/bind public listeners; Task 5 records exact override and honest exposure/auth projection. |
| AH12 | Task 5 produces the fresh executor transcript and independent evaluator PASS; Task 6 verifies the installed bytes match that candidate. |

## Operational strategy

Existing app-server/runtime/broker, instance/CLI, callback, package, and skill tests are **fix-in-place**. They encode security and durability scars and must be rewritten only where the approved topology intentionally changes an assertion. New gateway, global migration, service-domain, and shared-control tests are **keep + add focused tests**. No test is archived. Characterization tests for legacy registry discovery run before migration code; mutation negative controls prove unsafe peer paths, stale names, gateway drain classification, version replacement, and secret leakage guards actually fail.

---

## Checkpoint C1: Global durable substrate and shared transport exist

One process can load/migrate the global registry, start one private Codex WebSocket authority, and expose a drain-aware public gateway without yet changing the public CLI.

**Checkpoint gate:** frozen tree; independent adversarial review; warning-strict fast suite; isolated Python 3.9 package import; focused migration, connection, gateway, collision and security tests; AH5/AH7/AH11 foundation receipts.

### Task 1: Global service domain, paths, and lossless migration

**Role in the build:** Establish the singleton identity and durable truth consumed by every later arc, implementing R1/R4/R6/R9 and D6/D7/D11/D14/D18/D20.

**Read first:** spec §5.1 and §5.3; decisions D6–D7/D11/D14/D18/D20; shared CLI §1/§4 and callback CLI §2–§5; Angles 1, 3 and 4 “Concrete journey”, “What … cannot do”, and “Visible collisions”; Python patterns §§1–4/8–10; process discipline §§1/3.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/service_domain.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/migration.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/commands.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/registry.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/instance.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/callback_store.py`
- Test: `tests/codex-worker/test_service_domain.py`
- Test: `tests/codex-worker/test_migration.py`
- Modify tests: `test_commands.py`, `test_models_registry.py`, `test_instance.py`, `test_callback_store.py`
- Modify receipt anchor: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md`
- Create checkpoint report: `docs/superdev/reviews/2026-08-28-codex-worker-shared-app-server-c1.md`

**Interfaces:**
- Consumes: platform state/temp roots; verified owner-only path helpers; legacy `instances/{sha256}/instance.json`, `registry.json`, and callback stores; existing `SessionRecord`.
- Produces: `ServicePaths` including `callback_path` and `callback_artifact_dir`; `ServiceConfig`, `AttachView`, `LegacyCandidate`, `LegacyConflict`, `MigrationStatusView`, `derive_service_paths(platform, state_home, temp_root, uid) -> ServicePaths`, `validate_public_listener(value) -> str`, and `LegacyMigrator.scan_and_apply() -> MigrationStatusView` / `resolve(name, thread_id, as_name) -> SessionRecord`.

- [ ] **Step 1: RED — freeze singleton and migration laws**

  Add strict round-trip/extra-field tests for the new models and table-driven listener tests. Add real-temp registry fixtures covering unique import, byte-equivalent deduplication, divergent same-name quarantine, repeat idempotence, crash-safe ledger fsync, unsafe/symlink source refusal, and no source writes/deletes. Callback fixtures cover enabled/disabled/unavailable bindings, pending/written outbox, equal and conflicting event IDs, legacy `WorkerView.instance`, terminal-reference artifacts, unsafe absolute/path-escape artifacts, digest/size mismatch, and crashes after each D20 commit stage. Characterize the measured duplicate `status-checker-abc` legacy records as a sanitized fixture, with distinct session/thread identities.

  ```python
  paths = derive_service_paths("darwin", state_home, temp_root, uid=501)
  self.assertEqual(paths.durable_dir, state_home / "superdev/codex-worker/service")
  self.assertNotIn("CLAUDE_CODE_SESSION_ID", str(paths))

  status = LegacyMigrator(deps).scan_and_apply()
  self.assertEqual(status.conflict_count, 1)
  self.assertEqual({c.thread_id for c in status.conflicts[0].candidates}, {"thread-a", "thread-b"})
  self.assertEqual(source_hashes_after, source_hashes_before)
  ```

  Run focused tests and record RED failures for missing modules/types, then implement.

- [ ] **Step 2: GREEN — implement strict global domain and atomic migration**

  Use frozen strict dataclasses and closed enums. Global metadata stores exact listener/version/generation only; callback secrets remain in owner-only callback storage. Migration sorts canonical source paths, hashes raw source bytes, validates every record through current registry readers, plans the entire merge before executing D20's ordered artifact → registry → callback-store → completion-ledger commits, and records source path+digest+outcome. Conflicted names make `resolve_name` raise `legacy_name_conflict` with every candidate and non-force actions.

  ```python
  @dataclass(frozen=True)
  class ServicePaths:
      durable_dir: Path
      rpc_socket: Path
      private_codex_socket: Path
      start_lock: Path
      registry_path: Path
      config_path: Path
      migration_path: Path
      log_path: Path
      callback_path: Path
      callback_artifact_dir: Path

  @dataclass(frozen=True)
  class ServiceConfig(StrictModel):
      listener: str
      worker_version: str
      generation_id: str
  ```

  Implement D20 exactly: only imported/deduplicated sessions contribute callbacks; canonical-equal binding/event IDs deduplicate and mismatches quarantine the worker candidate; pending events and referenced completion artifacts are upgraded to the global worker projection; artifacts must be owner-only beneath the source artifact root and are republished insert-or-verify. Prevalidate all inputs, then publish artifacts, registry, callback store, and completion ledger in that order with fsync. The service remains not-ready until the ledger is complete; restart repairs any prefix idempotently from untouched sources. Leave compatibility re-exports for safe path helpers needed by existing tests, but remove instance selection from any new service API.

- [ ] **Step 3: Verify, adversarial review, and commit**

  Run focused tests, warning-strict fast gate, the exact AST import-arrow and seam-inventory guards in `test_service_domain.py`, `python3 -m compileall`, and `git diff --check`. A fresh reviewer must add negative controls for conflicting migrations, every D20 crash boundary, source mutation, unsafe paths, artifact rewriting, malformed listeners, callback-secret projection, and session-env independence. Track rerunnable commands/results in the C1 report, fill AH7's foundation receipt with that path, fold findings, rerun, and commit `feat(codex-worker): add global service state and migration`.

### Task 2: Private WebSocket connection, public gateway, and maintenance gate

**Role in the build:** Create one Codex authority that worker and TUI clients can share while making stop/restart exclusion real, implementing R2/R3/R7/R10–R12 and D1/D3–D5/D9/D12–D13/D16–D18.

**Read first:** spec §5.1–§5.2 and §5.4; decisions D1/D3–D5/D9/D12–D13/D16–D18; census transport/schema evidence; Angles 1/2/4 “What … cannot do” and “Visible collisions”; Python patterns §§1–5/7/9–10; process discipline §§1–3.

**Files:**
- Create: `skills/subagent-driven-development/scripts/codex_worker/websocket_transport.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/websocket_gateway.py`
- Create: `skills/subagent-driven-development/scripts/codex_worker/service.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/app_server.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/runtime.py`
- Modify: `skills/subagent-driven-development/scripts/pyproject.toml`
- Test: `tests/codex-worker/test_websocket_transport.py`
- Test: `tests/codex-worker/test_websocket_gateway.py`
- Test: `tests/codex-worker/test_service.py`
- Create fixture: `tests/codex-worker/fixtures/codex-0.150.1-client-request-methods.json`
- Modify tests: `test_app_server_runtime.py`, `test_runtime.py`, `test_tool_package.py`
- Modify receipt anchor: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md`
- Modify checkpoint report: `docs/superdev/reviews/2026-08-28-codex-worker-shared-app-server-c1.md`

**Interfaces:**
- Consumes: Task 1 `ServicePaths`/`ServiceConfig`; existing Codex method adapter and notification/approval callbacks.
- Produces: `CodexConnection(endpoint, on_notification, approval_handler, deps)`, `call(method, params, timeout)`, `close()`; `ServiceMaintenanceGate.mutation(method)` and `drain() -> ContextManager[DrainLease]`; `WebSocketGateway.start()/close()/ready`; `GlobalWorkerService.start()/status()` and private `terminate_owned(lease: DrainLease)` that verifies the lease belongs to its gate; private Codex argv `codex app-server --listen unix://{private_codex_socket}`. Public guarded stop/restart are deliberately deferred to Task 3 after authoritative inventory exists.

- [ ] **Step 1: RED — prove frame, handshake, overload, and drain contracts**

  Port the existing adapter characterization to a fake text-frame connection: request correlation, notification delivery, approval response, close-all-waiters, bounded frames, exactly one handshake, reconnect-only initialize overload, bounded idempotent read retry, and zero mutation replay. Gateway tests use paired fake front/back sockets and assert byte-equivalent one-to-one forwarding outside drain.

  ```python
  with gate.mutation("turn/start"):
      forwarded.set()
      release.wait()
  with gate.drain():
      self.assertEqual(inventory.active, ())
  ```

  Generate current request schemas into a private `mktemp -d` directory with `codex app-server generate-json-schema --out "$SCHEMA_DIR"` and derive `tests/codex-worker/fixtures/codex-0.150.1-client-request-methods.json`, containing every 0.150.1 client-request method plus the generating Codex version. Drive drain classification exhaustively: a small explicit read/interrupt allowlist passes; client responses to server-initiated requests pass; every other current request method and every unknown request method receives typed busy; already-forwarded mutations settle before inventory. A set-equality test fails when an upstream request method is unclassified. Bind tests prove fixed collision preservation and no port fallback.

- [ ] **Step 2: GREEN — implement the initialized connection and transparent gateway**

  Move protocol-independent upstream methods behind `CodexConnection.call`; keep `app_server.py` as a compatibility adapter/re-export during the transition. Use lazy imports from `websockets.sync.client` and `.server`. One frontend gets one backend; the gateway never rewrites successful Codex frames and inspects only JSON-RPC direction/method/id for gating.

  ```python
  DRAIN_ALLOWED_REQUESTS = frozenset({"thread/list", "thread/read", "turn/interrupt"})

  def classify_frontend_frame(value: object) -> FrameClass:
      if is_client_response(value): return FrameClass.RESPONSE
      if method in DRAIN_ALLOWED_REQUESTS: return FrameClass.ALLOWED
      return FrameClass.BLOCKED  # all other requests, including future/unknown methods
  ```

  `GlobalWorkerService` binds the gateway before reporting ready, spawns Codex only on the private socket, stamps its loaded version once, and exposes termination only through an internal authorization value constructed by Task 3 after a closed-gate inventory. Task 2 must not implement a public stop/restart path.

- [ ] **Step 3: Verify C1, review, and commit**

  Run focused tests warning-strict; the schema-method set-equality and AST/seam guards; isolated UV Python 3.9 install/import of sync client/server; real bind/collision fixture; package wheel allowlist; full fast suite. The checkpoint reviewer attacks every generated request method, unknown-method drain, queued approvals, malformed frames, frontend disconnects, private socket ownership, public collision, non-loopback projection, mutation replay, and resource leaks. Append exact commands/results to the C1 report, fill AH5/AH11 foundation receipts with that tracked path, and commit `feat(codex-worker): add shared WebSocket service`.

## Checkpoint C2: Global service is the complete public worker implementation

Every common/raw command addresses the singleton, TUI actions reconcile into worker state, guarded lifecycle sees all upstream threads, migration conflicts are actionable, and old instance routing is gone.

**Checkpoint gate:** frozen tree; independent adversarial review; warning-strict suite; five-process deterministic convergence; focused real WebSocket two-client control; lifecycle/migration refusal matrix; AH1/AH3/AH4/AH6/AH8/AH9 foundation receipts.

### Task 3: Authoritative broker reconciliation and global activity inventory

**Role in the build:** Make TUI-originated actions and worker actions converge through Codex rather than local ownership, implementing R3/R5–R8/R12 and D2/D4/D7/D10/D17.

**Read first:** spec §5.3–§5.6; decisions D2/D4/D7/D10/D17; Angle 2 entire file and Angle 4 “Concrete journey”, “What lifecycle management cannot do”, and “Visible collisions”; Python patterns §§2–5/9–10; process discipline §§1–2.

**Files:**
- Modify: `skills/subagent-driven-development/scripts/codex_worker/broker.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/runtime.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/models.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/projection.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/callback_dispatcher.py`
- Test: `tests/codex-worker/test_broker.py`
- Test: `tests/codex-worker/test_runtime.py`
- Test: `tests/codex-worker/test_projection.py`
- Test: `tests/codex-worker/test_callback_dispatcher.py`
- Modify receipt anchor: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md`
- Create checkpoint report: `docs/superdev/reviews/2026-08-28-codex-worker-shared-app-server-c2.md`

**Interfaces:**
- Consumes: Task 1 global registry/conflicts; Task 2 `CodexConnection` and `ServiceMaintenanceGate`.
- Produces: `WorkerBroker(..., gate, listener)` with every mutating method gated; `list_active_threads() -> ActiveInventory`; `MaintenanceCoordinator.stop(force) -> MaintenanceResult` / `restart(listener, force) -> MaintenanceResult`, which hold Task 2's `DrainLease`, inventory immediately, and pass the still-live lease to `terminate_owned`; `RuntimeStore` reconciliation for subscribed TUI changes; `AttachView` on worker projections/faults; exact expected-turn controls.

- [ ] **Step 1: RED — characterize cross-client state and complete inventory**

  Add deterministic response/notification interleavings for TUI-created follow-up, steer, interrupt, response-before-notification, successor-turn race, reconnect/status reconciliation, and callback terminal emission once. Inventory tests paginate `thread/list(sourceKinds=[])`, include unmapped active TUI threads, deduplicate pages, refuse malformed/cursor loops/errors, and prove an error never becomes zero active.

  ```python
  inventory = broker.list_active_threads()
  self.assertEqual(inventory.items[0].origin, "unmapped_tui")
  self.assertIsNone(inventory.items[0].worker)
  self.assertEqual(inventory.items[0].thread_id, "tui-thread")
  ```

- [ ] **Step 2: GREEN — gate mutations and reconcile from upstream authority**

  Wrap session/turn/goal mutations in the shared gate, never waits. Keep expected-turn capture. On status/history reads after reconnect, reconcile upstream thread/turn data into bounded runtime projections without synthesizing agent messages. Attach metadata uses the public gateway listener and exact thread ID. Callback bindings remain record metadata and terminal callbacks stay exactly-once.

  ```python
  def start_turn(self, spec: TurnStartSpec) -> JsonObject:
      with self.gate.mutation("turn/start"):
          return self._start_turn_authoritatively(spec)

  def list_active_threads(self) -> ActiveInventory:
      return collect_active_threads(self.codex, self.registry)

  def stop(self, force: bool) -> MaintenanceResult:
      with self.gate.drain() as lease:
          inventory = self.broker.list_active_threads()
          if inventory.items and not force:
              return MaintenanceResult.refused(inventory)
          return self.service.terminate_owned(lease)
  ```

- [ ] **Step 3: Verify, review, and commit**

  Run focused broker/runtime/callback tests warning-strict, AST/seam guards, and the full fast gate. A fresh reviewer adds delayed/out-of-order event, cursor-loop, inventory-error, mutation-during-drain, unmapped-thread, successor-turn, callback-duplication and partial-fault identity tests. Append commands/results to the C2 report, fill AH6/AH8/AH9 foundations, and commit `feat(codex-worker): reconcile shared Codex control`.

### Task 4: Global lifecycle, façade, RPC, and exhaustive CLI migration

**Role in the build:** Make the approved singleton behavior the only ordinary public path while retaining explicit raw sockets, implementing R1–R11 and D2–D3/D5–D11/D14–D15/D17.

**Read first:** shared CLI §§1–9 plus every inherited CLI companion in the Context pack, especially server CLI raw §§2–8; spec §5.1/§5.3/§5.5–§5.6; decisions D2–D3/D5–D11/D14–D15/D17; Angles 1/3/4 “What … cannot do” and “Visible collisions”; Python patterns §§3–4/6–10; process discipline §§1–3.

**Files:**
- Modify: `skills/subagent-driven-development/scripts/codex_worker/commands.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/instance.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/facade.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/rpc.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/cli.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/version.py`
- Test: `tests/codex-worker/test_commands.py`
- Test: `tests/codex-worker/test_instance.py`
- Test: `tests/codex-worker/test_facade.py`
- Test: `tests/codex-worker/test_facade_integration.py`
- Test: `tests/codex-worker/test_rpc_cli.py`
- Modify receipt anchor: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md`
- Modify checkpoint report: `docs/superdev/reviews/2026-08-28-codex-worker-shared-app-server-c2.md`

**Interfaces:**
- Consumes: Tasks 1–3 global paths/config/migration/service/broker/inventory/attach projection.
- Produces: exact CLI companion grammar; singleton `ServiceManager.status()/ensure_running(listener)/stop(force)/restart(listener, force)`; RPC `service/*` and `migration/*`; new fault codes `-32039..-32042`; removed `--instance`/public shutdown; preserved expert `--socket` raw path.

- [ ] **Step 1: RED — exhaustive parser, response, fault, and process matrix**

  Replace instance-route assertions with a complete table over every common/raw/lifecycle/migration command. Assert local exit 2 occurs before service contact; `CODEX_WORKER_INSTANCE` has no routing effect; `--instance` refuses with migration guidance; common commands reject `--socket`; explicit raw socket bypasses management. Add one-object subprocess coverage for default reuse, listener conflict, address collision, daemon status dual form, guarded stop/restart, force impact including unmapped TUI, idle version replacement, active replacement refusal, and migration resolve.

  ```python
  self.assertEqual(error["code"], -32040)
  self.assertEqual(error["data"]["details"]["active"][0]["origin"], "unmapped_tui")
  self.assertNotIn("--force", json.dumps(error["data"]["next_actions"]))
  ```

- [ ] **Step 2: GREEN — compose singleton management and strict public projections**

  Replace `InstanceManager` public use with `ServiceManager`; retain only private compatibility readers needed for legacy discovery. All common commands auto-ensure; managed raw commands require exact-ready service; status does not start. `start` persists listener only on service creation. Stop/restart enter drain, inventory, refuse or report impact, and preserve durable state. Every known worker result/fault includes `session_id`, `thread_id`, nullable `turn_id`, listener and shell-quoted attach/resume commands.

  ```python
  attach = AttachView(
      listener=config.listener,
      thread_id=record.thread_id,
      attach_command="codex --remote %s" % shlex.quote(config.listener),
      resume_command="codex --remote %s resume %s" % (
          shlex.quote(config.listener), shlex.quote(record.thread_id)),
  )
  ```

  Foreground `daemon serve` stays hidden/internal and stdout-silent. Public `daemon shutdown` is absent. Version mismatch uses the exact global inventory and never contacts/kills an unknown port peer.

- [ ] **Step 3: Verify C2, review, and commit**

  Run focused command/manager/facade/RPC tests, exact AST import-arrow and seam-inventory guards, warning-strict full gate, Python 3.9 compile, and a five-client process convergence fixture. Reviewer attacks local-validation precedence, config races, bind substitution, raw bypass, unsafe socket replacement, malformed service status, active inventory failure, force impact completeness, shell quoting, IDs on partial failures, and secret absence. Append exact commands/results to the C2 report, fill AH1/AH3/AH4 foundations with that tracked path, and commit `feat(codex-worker): expose global shared service CLI`.

## Checkpoint C3: Operator behavior is proven before release

The skill uses the global command safely, real Codex and Claude share/control threads, all common/raw families run through an isolated installed tool, and migration/lifecycle refusals are reconstructable in a fresh PASS checkride.

**Checkpoint gate:** frozen behavioral candidate; fresh executor/evaluator PASS; all AH1–AH12 receipts filled from tracked artifacts; warning-strict/package/live gates green; 8.0.0 declarations reconciled but no 8.1.0 release, current-user install, or production-service mutation yet.

### Task 5: Skill behavior, live evidence, and CLI checkride

**Role in the build:** Reconcile the trusted preflight identity, convert Tasks 1–4 into the low-friction Claude/human workflow, and prove every anchored use case before release, implementing R1–R12 and D1–D20.

**Read first:** full context pack with every inherited CLI companion; shared CLI §8–§10; design §5.7/§9; decisions D8/D10/D13/D16–D18/D20; every angle's “What … cannot do”, “Visible collisions”, and “Reconciled outcome”; `skills/writing-skills/SKILL.md`; `skills/cli-checkride/SKILL.md`; Python patterns §§6–10; process discipline §§1–3.

**Files:**
- Modify for D19 baseline: `package.json`
- Modify for D19 baseline: `.cursor-plugin/plugin.json`
- Modify for D19 baseline: `.codex-plugin/plugin.json`
- Modify for D19 baseline: `.kimi-plugin/plugin.json`
- Modify for D19 baseline: `gemini-extension.json`
- Modify for D19 baseline: `skills/subagent-driven-development/scripts/pyproject.toml`
- Modify for D19 public baseline: `README.md`
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `skills/subagent-driven-development/codex-worker.md`
- Modify: `skills/subagent-driven-development/codex-model-selection.md`
- Modify: `skills/subagent-driven-development/scripts/install-codex-worker`
- Modify: `tests/codex-worker/live_broker_check.py`
- Modify: `tests/codex-worker/live_claude_check.sh`
- Modify: `tests/codex-worker/live_uv_tool_check.py`
- Modify: `tests/codex-worker/test_live_harness_contract.py`
- Modify: `tests/codex-worker/test_live_claude_evidence.py`
- Modify: `tests/codex-worker/test_skill_integration.py`
- Modify: `tests/codex-worker/test_tool_preflight.py`
- Modify: `tests/codex-worker/test_tool_package.py`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-checkride.md`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/executor-transcript.md`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/evaluator-verdict.md`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/preflight-package/summary.json`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/preflight-package/transcript.jsonl`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/common-attach/summary.json`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/common-attach/transcript.jsonl`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/exactly-five/summary.json`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/exactly-five/transcript.jsonl`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/lifecycle/summary.json`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/lifecycle/transcript.jsonl`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/migration-callback-shared-control/summary.json`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/migration-callback-shared-control/transcript.jsonl`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/recovery/summary.json`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/recovery/transcript.jsonl`
- Create ignored raw run roots under `.superdev/codex-worker-live/`, named by the recorder as UTC timestamp, process ID, and one of the six exact scenario names above
- Modify receipt anchor: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md`

**Interfaces:**
- Consumes: complete Tasks 1–4 public command and package.
- Produces: reconciled 8.0.0 declared baseline; zero-friction skill preflight/use guidance; danger-gated maintenance prose; sanitized tracked live scenario receipts backed by ignored raw transcripts; independently judged PASS checkride; frozen behavior candidate consumed by Task 6.

- [ ] **Step 1: Reconcile the 8.0.0 preflight baseline without installation**

  Re-read all eight authorities. If the highest shipping authority remains 8.0.0, change only the six lower declaration files listed above from 7.10.0 to 8.0.0 and change README line 20 from `7.10.x` to `8.0.x`. Run `scripts/bump-version.sh --check`, `scripts/bump-version.sh --audit`, `bash tests/codex/test-marketplace-manifest.sh`, `bash tests/codex/test-package-codex-plugin.sh`, and `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh`. Commit `chore(release): reconcile superdev 8.0.0 authorities`; do not install or start/stop a current-user service. If any authority is now above 8.0.0, follow D19's revisit hook before proceeding.

- [ ] **Step 2: RED/GREEN — teach only the approved workflow**

  Use writing-skills pressure probes before edits, then structural/semantic reviewer agents after the documentation checkpoint. The skill runs the trusted UV preflight once, uses collision-resistant global names, requires explicit initial cwd, reports returned session/thread/attach/resume metadata, and never uses `--instance`, routine stop, or direct WebSocket flags after creation. It states that stop/restart are machine-wide dangerous commands requiring explicit human supervision/agreement and never appear in cleanup.

  ```text
  codex-worker start --name review-a91c --cwd /absolute/project --prompt "Review the branch"
  codex-worker run --name review-a91c --prompt "Summarize the remaining risks"
  # Report result.session_id, result.thread_id, result.attach.resume_command.
  # Never stop/restart as completion or cleanup.
  ```

  Add tests that fail on instance examples, Claude-session infrastructure claims, routine stop, missing attach handoff, missing global-name randomness, missing callback-only distinction, or any automated force action.

- [ ] **Step 3: Build six separate live scenarios and preserve raw evidence**

  Extend the harness with individually runnable, finally-safe scenarios:

  1. preflight/package: isolated UV Python 3.9, `websockets` provenance, current Codex 0.150.1 discovery;
  2. common/attach: start returns exact IDs/routes; second real initialized WebSocket client resumes same thread, follows up, steers and interrupts; both see authoritative events;
  3. exactly-five: five simultaneous global names from independent Claude-like environments, no crossed files/events/callbacks;
  4. lifecycle: occupied 4500 refusal, alternate connectable bind, idle version replacement, active worker and unmapped-TUI refusal, supervised force impact without source deletion;
  5. migration/callback/shared-control: one globally named worker imports or starts with its original Claude callback binding, a second TUI connection resumes and controls that same thread, then the same worker emits terminal/proactive delivery to the original room; the lane also exercises dedup/quarantine/resolve and proves lookup under different ambient Claude metadata;
  6. recovery: callers exit, service persists, exact thread resumes through worker and remote client, then status/history/control remain coherent.

  Run them as six separate killable commands:

  ```bash
  python3 tests/codex-worker/live_broker_check.py --scenario preflight-package
  python3 tests/codex-worker/live_broker_check.py --scenario common-attach
  python3 tests/codex-worker/live_broker_check.py --scenario exactly-five
  python3 tests/codex-worker/live_broker_check.py --scenario lifecycle
  python3 tests/codex-worker/live_broker_check.py --scenario migration-callback-shared-control
  python3 tests/codex-worker/live_broker_check.py --scenario recovery
  ```

  Each scenario records command argv, cwd, environment allowlist (never secret values), stdout, stderr, exit, elapsed time, substrate label, PIDs/IDs, durable hashes, and cleanup outcome. Each isolated root contains a random `fixture-owner.json` token; cleanup may stop/delete a service/root only after exact token+PID+path verification and records that verification. Copy sanitized-but-verbatim records into the exact tracked scenario paths above; secret scans and record counts are tests. No globally installed service is a cleanup target.

- [ ] **Step 4: Run a real Claude caller and the fresh CLI checkride**

  Run Claude Code using only PATH `codex-worker` common commands. Under the isolated Python 3.9 UV install and an unrelated cwd, record at least one successful live invocation from every inherited family: `start`, `run`, `message`, `status`, `messages`, `history`, `steer`, `interrupt`, `goal set`, `goal show`, `limits`, `model list`, `session start/list/show/resume`, and `turn start/wait/status/events/steer/interrupt`; where a control requires active timing, drive a deliberate long turn and record the terminal state afterward. Also record explicit raw `--socket` diagnostics.

  Then use `superdev:cli-checkride`: a fresh executor drives every changed family one command at a time, including successful prose/file starts, attach routes, the composed callback/shared-TUI journey, global lookup, every common/raw family above, migration, listener/config/active refusals, dangerous maintenance help, unknown port peer preservation, and restart durability. A separate evaluator reads literal output and mechanism receipts. Iterate product/evidence until PASS; never edit the evaluator verdict from the implementation role. Fill AH1–AH12 only with tracked paths/record IDs that the evaluator accepted.

- [ ] **Step 5: Freeze C3 and hand off the judged candidate**

  Run warning-strict, `bash tests/codex/test-marketplace-manifest.sh`, `bash tests/codex/test-package-codex-plugin.sh`, `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh`, Python 3.9 compile/import, every scenario separately, real Claude, secret scans, record-count guards, `git diff --check`, and the evaluator again. Commit skill changes, live receipts, checkride, evaluator verdict and anchor cells in reviewable commits. Record the exact behavioral candidate SHA in the checkride and prohibit Task 6 from changing Python/skill behavior without reopening the affected executor/evaluator lanes.

## Checkpoint C4: The accepted candidate is released and left immediately usable

The judged bytes are versioned monotonically as 8.1.0, installed through UV, verified from an unrelated cwd, and the compatible fixed-address global service remains running.

**Checkpoint gate:** baseline reconciliation and 8.1.0 audit green; current-user non-editable UV install; installed bytes equal candidate; final whole-branch review has no Critical/Important; global service ready and deliberately not stopped.

### Task 6: Version reconciliation, 8.1.0 release, installation, and integration

**Role in the build:** Release exactly the C3-approved behavior monotonically and make it immediately usable, implementing R1/R7/R8/R10 and D8/D10/D19.

**Read first:** decisions D8/D10/D19; design §5.1/§5.7/§9; global-install design §5.1–§5.4 and CLI §2–§3; Angle 1/4 “What … cannot do” and “Visible collisions”; process discipline §§2–3.

**Files:**
- Modify: `package.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.cursor-plugin/plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.kimi-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `gemini-extension.json`
- Modify: `skills/subagent-driven-development/scripts/pyproject.toml`
- Modify: `README.md`
- Modify: `RELEASE-NOTES.md`
- Modify: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-checkride.md`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/final-verification.md`
- Modify receipt anchor only if installed evidence adds a receipt: `docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md`

**Interfaces:**
- Consumes: Task 5 reconciled 8.0.0 baseline, behavioral candidate SHA, PASS evaluator, exact package directory, trusted installer, and service status contract.
- Produces: coupled 8.1.0 release; installed current-user UV command; byte-equality and unrelated-cwd verification; one running compatible service.

- [ ] **Step 1: Advance all authorities to 8.1.0 and verify the artifact**

  Run `scripts/bump-version.sh 8.1.0`, update `RELEASE-NOTES.md`, then run `scripts/bump-version.sh --check`, `scripts/bump-version.sh --audit`, `bash tests/codex/test-marketplace-manifest.sh`, `bash tests/codex/test-package-codex-plugin.sh`, `bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh`, the isolated Python 3.9 wheel/install/import test in `test_tool_package.py`, the warning-strict full gate, `bash -n skills/subagent-driven-development/scripts/install-codex-worker scripts/bump-version.sh`, and `git diff --check`. Commit the release without changing behavior.

- [ ] **Step 2: Install, verify, review, and leave the service running**

  Install the current source non-editably through `skills/subagent-driven-development/scripts/install-codex-worker`. From an unrelated temp cwd record `command -v codex-worker`, `codex-worker --version` = 8.1.0, UV ownership, package import provenance, and installed/source byte equality for every changed module. Run a short read-only globally named worker, verify exact IDs/attach route and `daemon status` ready at `ws://127.0.0.1:4500`, then leave it running and preserve the mapping. Restore any temporarily changed plugin marketplace source and verify the installed plugin/tool manifests.

  A very-smart whole-branch reviewer reads the behavioral diff, tracked checkride, D19 receipts and installed verification. Fold findings; any behavior fix reopens Task 5's affected live/checkride lane. Commit `final-verification.md` and any receipt additions only after review reports no Critical/Important.

## Finishing gate

Run the warning-strict suite fresh, exact AST/seam guards, all touched shell/package gates, `scripts/bump-version.sh --check`, `scripts/bump-version.sh --audit`, Python 3.9 compile/import, each live scenario separately, real Claude caller, and the final checkride evaluator. Generate a whole-branch review package from the design base, obtain a very-smart independent code review, and fix/re-review until no Critical/Important remains. Run the autonomous deviation/acceptance audit: every D1–D20 is either built exactly or logged with a permitted revisit trigger; every UC1–UC10/AH1–AH12 has a real tracked receipt. Integrate per `superdev:finishing-a-development-branch`, reinstall the integrated 8.1.0 bytes, verify the fixed gateway and global worker from an unrelated directory, leave the service running, and report exact version, listener, service/app-server PIDs, worker count, and attach command without exposing secrets.
