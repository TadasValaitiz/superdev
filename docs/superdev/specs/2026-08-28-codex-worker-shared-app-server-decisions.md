# Codex worker shared app-server — Decision log

**Design doc:** ./2026-08-28-codex-worker-shared-app-server-design.md
**Authority:** THE LAW of this work stream — rulings here outrank every other document's prose.
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — Share the worker's Codex process through a loopback WebSocket listener
**When:** 2026-08-28T11:55:06Z · **Phase:** brainstorm · **Status:** locked for the first implementation
**Decided by:** operator (live, in-session; selected the documented WebSocket pairing and asked how the worker changes)

- **Trigger:** the private stdio transport cannot be addressed by a second Codex TUI, while the operator wants to connect with `codex --remote` to the Codex process doing worker work.
- **Options weighed:**
  - A: retain private `stdio://` — gains zero implementation change / sacrifices independent TUI attachment.
  - B: share `unix://PATH` — gains a local multi-client address without TCP / sacrifices the requested familiar `ws://127.0.0.1:PORT` connection flow.
  - C: share `ws://127.0.0.1:PORT` — gains the documented `codex --remote` workflow and easy manual probing / sacrifices the current stdio-only adapter and relies on an experimental transport.
- **Decided:** C, loopback WebSocket, because it directly realizes the operator's observation workflow and matches the official Codex pairing. The ordinary private mode remains the compatibility baseline when no shared-listener option is selected.
- **Not a second unrelated app-server:** the listener must expose the same app-server process that executes the named worker's thread; otherwise the TUI can connect but cannot observe that work.
- **Extension law:** any non-loopback listener must add authenticated `wss://` handling and may not silently inherit the localhost trust policy.
- **Anti-patterns:** do not launch a decorative WebSocket app-server while leaving worker RPC on a separate stdio process; do not expose unauthenticated non-loopback TCP.
- **Rests on:** operator selection; MEASURED installed CLI help; READ official Codex App Server documentation, transport and remote-TUI sections; existing short-command/durability requirements in `design/scenarios/2026-08-28-codex-worker-global-install.md:9-23`.
- **Affects:** shared app-server process ownership, worker transport adapter, daemon CLI, readiness/status, shutdown and recovery.
- **Revisit-when:** Codex provides a supported shared local daemon API that offers the same remote-TUI attachment without an experimental WebSocket listener.

## D2 — The selected worker owns the listener and hides transport from ordinary commands
**When:** 2026-08-28T12:22:39Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected worker-owned listener, defaulted address behavior, and explicit resumable identity reporting)

- **Trigger:** external ownership would force Claude Code to coordinate a second lifecycle, while repeated WebSocket arguments would reintroduce the launch friction the common `codex-worker` surface removed. Separately, the human needs enough identity to attach or resume the exact Codex conversation.
- **Options weighed:**
  - A: worker-owned listener with transport metadata persisted once — gains short ordinary commands and deterministic stop/recovery / sacrifices arbitrary reuse of a separately managed server.
  - B: externally owned listener passed on every command — gains maximum composition / sacrifices zero-friction use and creates ambiguous failure ownership.
  - C: implicit start-or-connect — gains convenience across both cases / sacrifices deterministic ownership when an address is stale, occupied, or replaced.
- **Decided:** A. `codex-worker` remains the product surface; it starts, health-checks, records, and stops its selected app-server. Later common commands use the persisted route without WebSocket flags. An omitted address selects a product default. Every worker-creation and continuation result exposes the durable public `session_id` and Codex `thread_id`, and status/recovery output keeps them available for handoff to the human.
- **Not a WebSocket-first operator API:** WebSocket is an attachment mechanism and implementation detail; names remain the ordinary Claude Code routing key.
- **Extension law:** every new creation/resume response must preserve all known public identities, even on partial failure, and must include a directly usable human attachment/resume route when the shared listener is enabled.
- **Anti-patterns:** no address repeated on `start`, `run`, `status`, `messages`, `steer`, or `interrupt`; no success envelope that omits the created session/thread identity; no stopping externally discovered processes.
- **Rests on:** D1; operator selection; existing named-worker and durable-identity contracts.
- **Affects:** daemon lifecycle, instance metadata, common response projection, recovery actions, skill usage guidance.
- **Revisit-when:** the operator explicitly requests externally owned or cross-host app-server support.

## D3 — The default listener is fixed at loopback port 4500 and collision is a refusal
**When:** 2026-08-28T12:31:41Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected fixed default and explicit port-taken failure for deterministic orchestration/resume)

- **Trigger:** automatic free ports avoid collisions but make the human attachment address vary between runtime starts; deterministic orchestration and remembered resume commands are more valuable here than transparent fan-out.
- **Options weighed:**
  - A: `ws://127.0.0.1:0` with returned actual port — gains collision-free concurrent starts / sacrifices stable attachment and resume commands.
  - B: fixed `ws://127.0.0.1:4500` with fail-fast collision — gains deterministic addressing and legible ownership / sacrifices a second default instance until the caller provides an override.
  - C: instance-derived deterministic ports — gains multiple mostly stable endpoints / sacrifices simple mental model and introduces collision-resolution policy.
- **Decided:** B. Omitting the listener address means exactly `ws://127.0.0.1:4500`. If bind/readiness proves it occupied, startup returns a typed address-in-use refusal identifying the listener and a runnable explicit-override action. It never selects a different port silently.
- **Not global single-worker policy:** additional daemons remain possible when their startup explicitly selects a distinct loopback address.
- **Extension law:** every address default must remain observable in status and recovery output; fallback to a different address always requires an explicit operator action.
- **Anti-patterns:** no random port after collision; no killing the existing listener; no treating an arbitrary accepting peer on 4500 as this instance's server.
- **Rests on:** D1–D2; operator prioritization of deterministic orchestration/resume; MEASURED Codex support for both fixed ports and port zero.
- **Affects:** default command model, instance metadata, startup collision validation, typed faults, next actions, attach/resume projection.
- **Revisit-when:** one orchestrator must run multiple shared instances without assigning explicit ports.

## D4 — Remote TUI and worker have full shared control with app-server authority
**When:** 2026-08-28T12:35:34Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected full shared control and stated the human will orchestrate which client acts)

- **Trigger:** observation-only cannot use the normal interactive remote TUI, while a lease/handoff protocol would duplicate orchestration the human already performs. The ambiguity is how conflicting worker/TUI actions are reconciled.
- **Options weighed:**
  - A: full shared control — gains native observation, follow-up, steer, and interrupt from either client / sacrifices prevention of simultaneous conflicting actions.
  - B: observe-only viewer — gains enforced single writer / sacrifices the standard Codex TUI and the operator's steering goal.
  - C: explicit control lease — gains serialized human-versus-Claude ownership / sacrifices short commands and adds stale-lease recovery.
- **Decided:** A. Both initialized connections may act. The app-server's thread/turn state and response order are authoritative; `codex-worker` consumes the resulting notifications and maps losing races to its existing typed active/not-active outcomes. The human coordinates the practical swap between Claude Code orchestration and direct TUI orchestration.
- **Not implicit mutual exclusion:** no client-side flag claims exclusive control, and attaching the TUI does not pause Claude Code automatically.
- **Extension law:** every added control operation must reconcile against the exact target turn and authoritative post-response state; it may not infer success from local preflight state alone.
- **Anti-patterns:** no hidden lease file; no auto-interrupt when the TUI attaches; no worker rollback of a valid TUI action; no generic internal error for a legible control race.
- **Rests on:** D1–D3; operator control model; READ official per-connection subscription and thread-status protocol.
- **Affects:** notification fan-out/reconciliation, turn control errors, TUI attachment journey, concurrency acceptance probes.
- **Revisit-when:** measured multi-client behavior shows missed notifications or an app-server invariant that requires a single writer.

## D5 — Shared WebSocket is the default worker transport; creation may override its address
**When:** 2026-08-28T13:05:22Z · **Phase:** brainstorm · **Status:** locked; supersedes D1's private-mode default clause
**Decided by:** operator (live, in-session; selected shared-by-default with override capability)

- **Trigger:** an opt-in sharing command would make remote observability dependent on Claude Code remembering an extra lifecycle step, contradicting the requirement that WebSocket remain an implementation detail.
- **Options weighed:**
  - A: shared WebSocket on every ordinary first start, with explicit address override — gains zero-friction attachability and deterministic orchestration / sacrifices transport-level backward identity with the current stdio launch.
  - B: one-time `daemon start --shared` opt-in — gains compatibility / sacrifices reliable availability when callers omit the preparatory step.
  - C: an explicit listener option is always required — gains maximal visibility / sacrifices the common short-command contract.
- **Decided:** A. `codex-worker start` implicitly ensures the selected worker-owned app-server at `ws://127.0.0.1:4500`. Creation may explicitly override the loopback listener; the chosen listener is immutable instance runtime configuration and later `run`/status/control commands reuse it without transport arguments.
- **Not silent port fallback:** override capability does not weaken D3; default collision still refuses rather than selecting another port.
- **Extension law:** any future common entry point that can create a managed runtime uses the same default/override validation and returns the resolved listener plus attach/resume metadata.
- **Anti-patterns:** no preparatory `ensure --shared`; no environment-only hidden override; no changing the listener from a later follow-up command; no routine skill instructions that mention WebSocket flags.
- **Rests on:** D1–D4; operator zero-friction selection; existing implicit managed-daemon startup behavior.
- **Affects:** common start command, daemon start command, request models, immutable instance metadata, skill preflight/use examples.
- **Revisit-when:** the experimental Codex WebSocket transport proves materially less reliable than stdio under the required live checkride.

## D6 — One long-lived machine-local service outlives Claude sessions and TUI clients
**When:** 2026-08-28T13:49:38Z · **Phase:** brainstorm · **Status:** locked for architecture; namespace mechanics remain open
**Decided by:** operator (live, in-session; rejected session-owned shutdown and required simultaneous independent sessions/orchestrations)

- **Trigger:** a daemon owned by one Claude session can be stopped without another session's context, disconnecting the human TUI and unrelated orchestrations. The operator expects frequent use and does not want routine session completion to terminate shared infrastructure.
- **Options weighed:**
  - A: one daemon/app-server per Claude session — gains isolation and simple ownership / sacrifices stable port 4500 and permits one session to disrupt its own remote TUI.
  - B: one long-lived machine-local codex-worker service owning one shared app-server — gains stable endpoint, concurrent independent threads, and client-independent lifecycle / sacrifices process-level isolation and requires request namespaces.
  - C: delegate entirely to Codex's built-in managed daemon — gains native lifecycle management / sacrifices the fixed worker-controlled WebSocket endpoint and still requires a worker broker/state service.
- **Decided:** B. The physical daemon and app-server are machine-local shared infrastructure. Claude sessions, named workers, and remote TUIs are logical clients. Common commands auto-start the service if absent but never stop it on task/session completion. Routine `stop` leaves the common surface; maintenance restart/stop remains explicit and global, preserves durable state, and warns/refuses around active work as later specified.
- **Not an immortal process:** crashes, upgrades, and explicit maintenance can restart the service; “always works” means client-independent auto-start plus durable recovery, not pretending process death is impossible.
- **Extension law:** no logical client may infer authority to stop shared infrastructure from its own completion; per-client cleanup is unsubscribe/detach, never daemon termination.
- **Anti-patterns:** no callback/session hook that stops the daemon; no per-Claude-session listener on port 4500; no deletion of thread mappings during service restart; no hidden second app-server.
- **Rests on:** D1–D5; operator lifecycle direction; READ installed Codex managed-daemon commands; READ app-server per-connection subscriptions and persisted-thread behavior.
- **Affects:** instance resolution, daemon topology, registry keys, callback ownership, lifecycle commands, skill cleanup instructions, upgrades and readiness.
- **Revisit-when:** measured resource isolation or provider limits prove a single app-server cannot support the required concurrent workload.

## D7 — Worker names are globally unique; Claude session identity is callback metadata only
**When:** 2026-08-28T13:54:23Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected the globally unique name pool and explicitly decoupled worker identity from Claude session IDs)

- **Trigger:** session-scoped names would make worker lookup depend on ambient Claude identity and complicate direct human use, while the operator wants Claude session identifiers only when routing messages back to a room.
- **Options weighed:**
  - A: key workers by `(CLAUDE_CODE_SESSION_ID, name)` — gains collision isolation / sacrifices ambient-independent lookup and direct CLI simplicity.
  - B: key workers globally by `name` — gains one stable addressable identity from Claude Code or a human shell / sacrifices reuse of the same short name across concurrent orchestrations.
  - C: require an explicit namespace — gains deliberate isolation / sacrifices the short common surface.
- **Decided:** B. A worker `name` is globally unique within the machine-local service. `CLAUDE_CODE_SESSION_ID`, room name, messaging socket, and callback token are captured only in the worker's callback binding and do not participate in worker identity, daemon selection, or thread lookup.
- **Not callback decoupling:** a worker may still retain and use its originating Claude route; the route is optional delivery metadata attached to that globally named worker.
- **Extension law:** every new lookup/control command resolves the same global name; callback overrides alter delivery only and can never rename or shadow the worker.
- **Anti-patterns:** no ambient-session filtering of `status`, `run`, `messages`, `steer`, or `interrupt`; no duplicate global names hidden behind different Claude sessions; no callback token in public identity output.
- **Rests on:** D6; operator selection; existing recommendation that generated names include random/numbered suffixes.
- **Affects:** registry uniqueness, request selectors, callback binding, skill naming guidance, collision faults and recovery.
- **Revisit-when:** the global name pool becomes operationally unmanageable despite generated suffix guidance.

## D8 — Stop is guarded global maintenance and agents require supervised agreement
**When:** 2026-08-28T13:56:48Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected guarded stop and added a skill-level danger/supervision requirement)

- **Trigger:** removing stop makes recovery depend on manual process surgery, while an ordinary unconditional stop lets one context-blind agent disconnect every orchestrator using the shared service.
- **Options weighed:**
  - A: keep stop, refuse active work, and reserve force for supervised maintenance — gains recoverability with explicit blast-radius control / sacrifices a completely frictionless shutdown.
  - B: remove stop from the CLI — gains maximal accidental-shutdown resistance / sacrifices supported maintenance and port recovery.
  - C: retain unconditional stop — gains simplicity / sacrifices shared-service safety.
- **Decided:** A. `daemon stop` is machine-wide maintenance and refuses while any turn is active. `daemon stop --force` is a highly visible exceptional operation that reports affected workers. The skill marks both as dangerous and forbids agent use without explicit human supervision and agreement; neither appears in normal completion/cleanup recipes.
- **Not permission inferred from task completion:** finishing a worker, Claude session, plan, or orchestrator milestone grants no authority to stop the service.
- **Extension law:** every future service-wide destructive/disruptive command carries the same active-work preflight, impact projection, and supervised-human requirement.
- **Anti-patterns:** no automatic stop in `finally`; no stop suggested as routine recovery; no `--force` hidden in next actions; no treating absence of locally visible work as proof the global service is idle.
- **Rests on:** D6–D7; operator safety rider; existing non-destructive durable-state contract.
- **Affects:** daemon stop/force command models, runtime activity inventory, skill warnings, CLI help, typed refusal and maintenance receipts.
- **Revisit-when:** Codex provides transactional per-client service detachment that eliminates the global blast radius.

## D9 — Listener overrides pass through any Codex-supported address
**When:** 2026-08-28T14:38:19Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected unrestricted address pass-through after the non-loopback exposure warning was presented)

- **Trigger:** loopback-only validation prevents direct network listeners, while fully authenticated remote support adds a broader credential/TLS subsystem. The operator chose direct Codex address semantics rather than worker policy restriction.
- **Options weighed:**
  - A: loopback-only listener validation — gains a safe local boundary / sacrifices direct cross-machine binding.
  - B: authenticated `wss://` only for non-loopback — gains safe remote access / sacrifices initial simplicity and requires credential lifecycle design.
  - C: accept every address supported by `codex app-server --listen` — gains transparent capability and operator control / sacrifices worker-enforced network safety.
- **Decided:** C at the time: `--app-server-listen` was to be validated structurally and passed to Codex without a loopback restriction. D17 later supersedes the literal pass-through while preserving the operator's unrestricted-host intent: the service gateway binds the connectable address and the Codex child stays private. The default remains `ws://127.0.0.1:4500`. Non-loopback exposure is represented explicitly in status/start output and documentation; the worker does not silently claim it is authenticated or safe.
- **Not implicit authorization:** accepting a listener does not configure firewall, TLS, token storage, or remote-client credentials.
- **Extension law:** future authentication support must project its measured mode without printing secret material; absence of configured auth remains explicitly visible for non-loopback listeners.
- **Anti-patterns:** no label such as `secure` inferred from `wss` alone; no token value in argv/status/logs; no rewriting the requested address to loopback.
- **Rests on:** D1–D8; operator selection after explicit safety warning; READ official warning that experimental non-loopback listeners may allow unauthenticated connections.
- **Affects:** listener validation, server argv, security projection, documentation and live refusal/exposure scenarios.
- **Revisit-when:** the service is deployed beyond a human-controlled development machine or policy requires authenticated remote access.

## D10 — Internal-tool upgrades auto-restart only when globally idle
**When:** 2026-08-28T14:41:06Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; scoped the product as an internal tool and approved the simplified policy)

- **Trigger:** strict supervised restart for every version change avoids all surprise disconnections but overbuilds release coordination for an internal tool; unconditional replacement can interrupt unrelated active work.
- **Options weighed:**
  - A: every mismatch requires supervised restart — gains maximal lifecycle consent / sacrifices internal-tool convenience.
  - B: exact reuse, automatic restart only when no turns are active, refusal otherwise — gains simple safe-enough upgrades / sacrifices preservation of idle TUI connections during replacement.
  - C: tolerate mixed client/service versions — gains no restart / sacrifices protocol safety and adds a compatibility matrix.
- **Decided:** B. Same-version clients reuse the service. A version mismatch automatically restarts it only after a global zero-active-turn check, preserving durable state. Any active turn yields a typed busy refusal. Force remains supervised and dangerous. Idle TUI clients may reconnect to the same fixed address after replacement.
- **Not production rolling deployment:** no dual service, draining generation, or old/new protocol compatibility is built.
- **Extension law:** any future automatic service replacement must prove global active-turn count is zero immediately before termination and retain the fixed endpoint plus durable mappings.
- **Anti-patterns:** no restart based only on the caller's worker being idle; no active-turn interruption for preflight repair; no silent mixed-version RPC.
- **Rests on:** D6, D8; operator internal-tool scope and explicit approval.
- **Affects:** version handshake, preflight repair, daemon replacement, typed busy recovery and live upgrade scenarios.
- **Revisit-when:** the tool is distributed beyond the operator's controlled machines or needs zero-disconnect idle upgrades.

## D11 — Remove public instances and migrate to one global registry/service
**When:** 2026-08-28T15:00:34Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; approved removal of the multiple-instance concept and delegated remaining decisions/build autonomously)

- **Trigger:** retaining `--instance` preserves multiple physical daemons and partitions the name pool, contradicting the selected one-service/global-name architecture. Aliasing it would be misleading.
- **Options weighed:**
  - A: remove the public instance selector and migrate durable mappings — gains one truthful topology and global names / sacrifices compatibility with instance-addressed commands and requires conflict-aware migration.
  - B: retain advanced multiple services — gains compatibility/test convenience / sacrifices the single-service invariant.
  - C: accept but ignore the selector — gains parse compatibility / sacrifices semantic honesty.
- **Decided:** A. Common and managed raw commands address one machine-local service. The public `--instance` and `CODEX_WORKER_INSTANCE` routing concepts are removed. Existing per-instance registries are discovered once and migrated into the global registry; duplicate names with different identities refuse migration with a recovery report rather than overwrite.
- **Not deletion of legacy state:** migration copies/merges durably and leaves legacy directories intact until separately supervised cleanup; rollback remains possible.
- **Extension law:** future routing dimensions may annotate workers but cannot create hidden physical service partitions or weaken global name uniqueness.
- **Anti-patterns:** no last-writer-wins migration; no silent name renaming; no implicit deletion of old registry/callback/artifact files; no public selector that lies about topology.
- **Rests on:** D6–D7; operator approval; existing durable identity contract.
- **Affects:** CLI parser, instance manager, state layout, registry schema/migration, environment-variable guidance, recovery and checkride.
- **Revisit-when:** measured global-service resource contention requires process isolation rather than logical thread isolation.

## D12 — The global broker owns Codex and connects through a direct WebSocket client
**When:** 2026-08-28T15:02:27Z · **Phase:** brainstorm · **Status:** provisional (autonomous detail under operator-delegated architecture)
**Decided by:** author (operator delegated remaining decisions; selected direct shared transport after a measured two-client probe)

- **Trigger:** the broker must consume the same app-server as the TUI. A decorative second listener or separate stdio child fails that invariant, while Codex's built-in daemon does not expose the required worker-owned fixed listener contract.
- **Options weighed:**
  - A: broker spawns `codex app-server --listen …` and connects directly as a WebSocket client — gains one real shared process and native multi-client subscriptions / sacrifices the zero-dependency adapter.
  - B: add an internal WebSocket-to-stdio bridge — gains reuse of JSONL code / sacrifices another protocol process and recreates split ownership.
  - C: use Codex managed daemon plus a separate broker/bridge — gains native daemon lifecycle / sacrifices fixed endpoint simplicity and still needs two services.
- **Decided:** A. The global broker owns one Codex child, health-checks its listener, then initializes one worker WebSocket connection. The TUI initializes another connection to the same listener. MEASURED probe: client B resumed client A's thread, started the next turn, and both clients received the same event sequence through `turn/completed`.
- **Shape at selection:**
  ```text
  WorkerBroker ── WebSocket connection A ─┐
                                          ├─ one Codex app-server process
  Codex TUI ──── WebSocket connection B ─┘
  ```
- **Not shared TCP with separate state:** listener health is insufficient; the broker verifies child identity/version and its own initialized connection before publishing readiness.
- **Extension law:** every transport implementation must preserve request correlation, server requests/approvals, bounded frames, close semantics, and notification delivery independently per connection.
- **Anti-patterns:** no scraping TUI output; no second Codex child; no assuming listener acceptance proves compatible app-server identity.
- **Rests on:** D1–D11; MEASURED two-client WebSocket probe on Codex 0.147.0; READ official initialization/subscription protocol.
- **Affects:** app-server adapter, broker construction, child lifecycle, readiness, approval routing, transport tests.
- **Revisit-when:** Codex exposes a documented managed daemon listener/control API that eliminates the custom child lifecycle.

## D13 — Use the maintained `websockets` client inside the isolated UV tool
**When:** 2026-08-28T15:02:27Z · **Phase:** brainstorm · **Status:** provisional (autonomous detail under operator-delegated architecture)
**Decided by:** author (selected the smallest reliable implementation compatible with the existing threaded adapter)

- **Trigger:** Python's standard library has no WebSocket client; hand-rolling masking, fragmentation, ping/pong, close, TLS, limits, and handshake validation would turn transport plumbing into security-sensitive product code.
- **Options weighed:**
  - A: add the maintained `websockets` package and use its synchronous client — gains protocol correctness, bounded messages, TLS support, and thread-compatible calls / sacrifices the prior empty dependency list.
  - B: implement RFC 6455 locally — gains zero dependencies / sacrifices reliability and creates a large custom security surface.
  - C: shell out through another Codex/TUI command — gains no Python dependency / sacrifices structured lifecycle, approvals, and request correlation.
- **Decided:** A, pinned to a Python-3.9-compatible major range. Import is isolated behind the WebSocket transport module; deterministic tests inject fake connections, while the UV/live lane proves the real dependency and framing.
- **Shape at selection:**
  ```toml
  [project]
  requires-python = ">=3.9"
  dependencies = ["websockets>=14,<16"]
  ```
  ```text
  codex_worker/websocket_transport.py -> websockets.sync.client
  codex_worker/websocket_gateway.py   -> websockets.sync.server
  tests -> injected fake Connection seams
  ```
- **Not a global Python dependency:** UV owns it inside the standalone `codex-worker` environment.
- **Extension law:** dependency upgrades run the two-client live transport probe and Python 3.9 package lane.
- **Anti-patterns:** no fallback homemade WebSocket when import fails; no unbounded `recv`; no secret headers in logs.
- **Rests on:** D12; existing UV isolation requirement; Python 3.9 floor; A3 ratified by
  isolated Python 3.9.6 + websockets 15.0.1 sync client/server import.
- **Affects:** `pyproject.toml`, transport module, package/archive tests, live harness.
- **Revisit-when:** Codex ships a stable stdio proxy for arbitrary WebSocket endpoints or Python gains an adequate standard client.

## D14 — Legacy registries import non-conflicts and quarantine name conflicts without deletion
**When:** 2026-08-28T15:02:27Z · **Phase:** brainstorm · **Status:** provisional (autonomous detail under operator-delegated architecture)
**Decided by:** author (selected a recoverable migration after measuring duplicate legacy names on the operator machine)

- **Trigger:** many per-instance registries exist and at least two contain different `status-checker-abc` threads. Failing the whole service strands unrelated mappings; silently choosing or renaming a winner violates identity honesty.
- **Options weighed:**
  - A: all-or-nothing migration — gains transactional simplicity / sacrifices availability when any duplicate exists.
  - B: newest-wins or automatic suffix rename — gains immediate names / sacrifices operator intent and silently changes identities.
  - C: import non-conflicts, record duplicate-name conflict sets, and require explicit resolution — gains service availability plus lossless recovery / sacrifices one maintenance step for conflicting names.
- **Decided:** C. Identical name+thread records deduplicate. Unique names import. Divergent duplicate names become durable conflict entries; lookup returns every known session/thread/source and runnable resolution actions. Legacy directories are never deleted. Resolution selects one thread for the original name or assigns explicit new names to retained alternatives.
- **Shape at selection:**
  ```text
  for each legacy (source_path, digest, name, session_id, thread_id):
      unique name -> import copy
      identical identity -> record dedup source
      divergent identity -> LegacyConflict[name].candidates += record
  lookup(conflicted name) -> refuse until explicit thread selection/new name
  ```
- **Not routine migration on every start:** one durable migration ledger makes discovery idempotent and records source digests.
- **Extension law:** every future migration is copy/merge-first, digest-receipted, conflict-explicit, and leaves source data recoverable.
- **Anti-patterns:** no mtime winner; no silent suffix; no overwrite; no source-directory cleanup during migration.
- **Rests on:** D7, D11; MEASURED duplicate legacy name with distinct thread IDs; durable-state law.
- **Affects:** global registry schema, migration ledger/conflicts, service startup, `migration` maintenance family, lookup faults and receipts.
- **Revisit-when:** all legacy instance roots have been explicitly retired after a verified backup window.

## D15 — Reconcile the public CLI around global names, attach routes, and guarded maintenance
**When:** 2026-08-28T16:10:00Z · **Phase:** brainstorm · **Status:** provisional (autonomous detail under operator delegation)
**Decided by:** author (translated the operator-locked topology into one exhaustive command contract)

- **Trigger:** D1–D14 change ownership, identity and lifecycle together. Leaving the existing
  parser mostly intact would preserve misleading instance selectors, routine shutdown paths,
  and results that do not tell a human how to attach.
- **Options weighed:**
  - A: add only a listener flag — gains a small diff / sacrifices truthful global identity,
    safe maintenance, migration recovery, and zero-friction attach handoff.
  - B: introduce a separate `service` executable — gains surface isolation / sacrifices the
    established globally installed `codex-worker` command and duplicates common routing.
  - C: revise the existing CLI coherently — gains one product surface with short named-worker
    commands and explicit expert maintenance / sacrifices compatibility with public `--instance`.
- **Decided:** C. Common commands select globally unique names. `start` and service start may
  choose the app-server listener; later commands reuse it. Results distinguish wrapper
  `session_id` from resumable Codex `thread_id` and include attach/resume routes. Public
  `daemon shutdown` is removed; guarded stop/restart and migration status/resolve are explicit.
  Raw `--socket` remains the sole expert endpoint bypass.
- **Creation defaults and validation rider:** absence of tier/model selects the existing
  `medium` tier and `medium` effort; token budget still requires an initial goal; common commands
  still reject `--socket`. `start --cwd` becomes required because the operator explicitly asked
  that initial work use a deliberate working directory even when ambient Claude cwd is available.
- **Shape at selection:**
  ```text
  codex-worker [--pretty] [--socket ABS_PATH] <family> ...
  start --name N --cwd DIR (--prompt P|--prompt-file F) [creation policy] [--app-server-listen A]
  run|status|messages|history|steer|interrupt --name N ...
  daemon start|status|restart|stop ...
  migration status|resolve ...
  # no --instance; no public daemon shutdown
  ```
- **Supersession ledger:** D6 supersedes D2's wording that a selected worker owns the listener;
  the global service owns it. D6/D11 supersede D3's allowance for additional managed daemons
  and D5's instance-scoped configuration; one service generation owns one listener. D9
  supersedes D1's non-loopback-auth requirement for this internal-tool phase: exposure is
  passed through and reported honestly, not secured by Codex Worker.
- **Shape receipt:** the exhaustive grammar, one-object output, identity projection, fault
  codes, migration forms, and operator journeys are frozen in
  `2026-08-28-codex-worker-shared-app-server-cli-surface.md`.
- **Not loss of diagnostics:** existing model/session/turn families remain; only their managed
  service selection changes. Explicit `--socket` continues to bypass managed startup.
- **Extension law:** a new command must resolve the same singleton service/global name model,
  preserve known IDs on partial failure, and never introduce routine global stop.
- **Anti-patterns:** no accepted-but-ignored instance flag; no attach command built from wrapper
  session UUID; no recovery action that injects `--force`; no second public lifecycle surface.
- **Rests on:** D2–D14; operator delegation; existing strict JSON/exit-code contract.
- **Affects:** CLI parser/models/projection/help, skill examples, migration API, checkride matrix.
- **Revisit-when:** the operator changes the one-service topology or Codex provides a native
  attach command that no longer requires listener/thread projection.

## D16 — Accept only remotely attachable listener modes and honor bounded WebSocket backpressure
**When:** 2026-08-28T16:32:00Z · **Phase:** brainstorm · **Status:** provisional (autonomous reconciliation to current upstream contract)
**Decided by:** author (reconciled operator pass-through with current Codex 0.150.1 help and official documentation)

- **Trigger:** Codex now accepts `stdio://`, `off`, WebSocket and Unix-socket listener modes,
  but `stdio://`/`off` cannot satisfy the operator's second-client attach requirement. The
  official transport also exposes bounded-queue overload and optional non-loopback auth.
- **Options weighed:**
  - A: pass every syntactically accepted mode — gains literal passthrough / sacrifices the
    shared-control invariant for `stdio://` and `off`.
  - B: permit remotely attachable modes and preserve the address exactly — gains truthful
    attachability across WebSocket/Unix transports / sacrifices two Codex modes that cannot
    serve this product.
  - C: loopback WebSocket only — gains minimal implementation / sacrifices the operator's
    explicit override choice.
- **Decided:** B at the time. D17 supersedes the listener-mode portion: the product now accepts
  only a connectable public `ws://HOST:PORT`, while the Codex child uses a private Unix-WebSocket;
  `wss://` termination belongs to an operator proxy. `stdio://`, `off`, and public Unix paths are
  rejected. Default remains loopback WebSocket. Upstream
  WebSocket overload `-32001` receives bounded exponential-backoff-with-jitter retries for
  idempotent observation/handshake operations only; mutations return a typed busy result rather
  than risking replay. Non-loopback auth configuration remains an explicit operator-owned
  Codex concern for this internal iteration; status never calls an unauthenticated listener safe.
- **Shape at selection:**
  ```text
  open connection -> initialize once -> initialized -> ordinary calls
  overloaded idempotent read -> bounded backoff+jitter -> retry same request
  overloaded initialize -> close connection -> bounded reconnect -> fresh initialize
  overloaded mutation -> typed busy; never replay
  ```
- **Shape receipt:** one JSON-RPC object per text frame, `/readyz` readiness, one initialize
  handshake per connection, per the official Codex App Server page fetched 2026-08-28.
- **Not a security abstraction:** Codex Worker does not mint credentials, terminate TLS, or put
  raw bearer values in argv/status.
- **Extension law:** no accepted listener may make the promised attach command unusable; no
  mutating RPC may be retried without a server-provided idempotency contract.
- **Anti-patterns:** no `stdio://` attach route; no infinite retry loop; no silent downgrade from
  `wss` to `ws`; no secret in public JSON.
- **Rests on:** D3, D4, D9, D12; MEASURED Codex 0.150.1 help; READ official transport/auth/overload documentation.
- **Affects:** listener validator, connection factory, retry policy, readiness, status security projection, live matrix.
- **Revisit-when:** Codex documents a remotely attachable stdio proxy or stable idempotency keys for mutating calls.

## D17 — Put a maintenance-aware WebSocket gateway in front of a private app-server socket
**When:** 2026-08-28T17:05:00Z · **Phase:** spec review · **Status:** provisional (autonomous fix to an independently found safety gap; supersedes the public-listener parts of D5/D9/D12/D16)
**Decided by:** author after required spec reviewer proved direct-listener maintenance cannot exclude a concurrent TUI turn

- **Trigger:** the app-server's subscriptions are per connection. A TUI can start a turn on an
  unregistered thread between an inventory read and process termination. A direct Codex-owned
  public listener offers no drain gate, so R7/R8 cannot honestly promise active-work-safe stop
  or version replacement.
- **Options weighed:**
  - A: call `thread/list` twice and accept the race — gains a small implementation / sacrifices
    the operator-locked no-active-interruption promise.
  - B: remove guarded maintenance and require force for every restart — gains honesty / sacrifices
    automatic idle upgrade and safe ordinary maintenance.
  - C: service-owned public WebSocket gateway to a private Codex Unix-WebSocket listener — gains
    a gate over every external mutation and preserves one app-server/thread authority / sacrifices
    literal listener pass-through and adds a bounded forwarding component.
- **Decided:** C. The Python service owns the public connectable `ws://HOST:PORT` listener. Each external TUI
  connection maps one-to-one to a private Unix-WebSocket app-server connection; the broker uses
  its own private initialized connection. A maintenance gate atomically blocks new worker
  mutations and gateway request forwarding, waits forwarded mutations to settle, then pages
  authoritative `thread/list` with `sourceKinds: []`. Only an empty active set permits ordinary
  stop/replacement. Force still reports the active set before termination.
- **Shape at selection:**
  ```text
                       ┌─ broker private WS connection ─┐
  worker Unix RPC ─────┤                                │
                       │   private unix:// app-server   │
  Codex TUI ─ public ws gateway ─ one backend WS/client ┘

  maintenance:
    acquire gate -> block new mutating requests -> settle forwarded mutations
    -> page thread/list(sourceKinds=[]) -> active? refuse : close clients/stop
  ```
- **Gateway request law:** while draining, client JSON-RPC requests are fail-closed except an
  explicit read/interrupt allowlist; client responses to server-initiated approvals/input and
  notifications continue so active turns can finish. Unknown request methods are blocked.
- **Listener refinement:** the public override is a connectable `ws://HOST:PORT`; port `0`,
  wildcard/unspecified hosts, userinfo, path, query and fragment are rejected because the same
  stored value must be a usable `codex --remote` address. `wss://` belongs at a TLS
  reverse proxy because Codex 0.150.1 does not accept it as a server listener. Unix and stdio
  remain private/internal transports, not public attach routes in this iteration.
- **Not a second Codex state authority:** the gateway forwards frames and gates requests; it
  neither interprets conversation contents nor creates a second app-server/thread store.
- **Extension law:** every new client-initiated mutating method enters the explicit gate table
  before release; unknown methods fail closed during drain. Inventory failure always refuses
  ordinary maintenance.
- **Anti-patterns:** no double-read race; no TUI bypass path advertised; no proxy-generated
  success for a request Codex did not accept; no auth credential logging.
- **Rests on:** R7/R8; D4/D6/D8/D9/D10; required spec-review finding; MEASURED 0.150.1
  `thread/list` schema with runtime `status.type=active` and `sourceKinds: []` meaning all sources.
- **Affects:** service topology, listener meaning, app-server argv, gateway, maintenance gate,
  active inventory, CLI/security projection, transport/live tests.
- **Revisit-when:** Codex exposes an atomic drain-and-stop API or a managed public listener whose
  maintenance contract includes every client/thread.

## D18 — Evolve the strict dataclass seams in place and split new service capabilities by responsibility
**When:** 2026-08-28T18:10:00Z · **Phase:** plan · **Status:** provisional (autonomous implementation-shape decision)
**Decided by:** author under the operator-delegated autonomous build

- **Trigger:** the generic Python canon prefers frozen Pydantic seam models, but this mature
  dependency-light Python 3.9 package already enforces frozen strict dataclass serialization,
  closed fields, enum faults, and exhaustive model tests across hundreds of cases. Converting
  every existing seam while replacing topology would create an unrelated big-bang migration.
- **Options weighed:**
  - A: convert all worker seams to Pydantic during this change — gains literal generic-canon
    alignment / sacrifices bounded scope and risks every stable public JSON shape.
  - B: add gateway/service logic to existing large modules — gains fewer files / sacrifices
    dependency direction and makes lifecycle/control coupling harder to review.
  - C: retain the tested strict frozen dataclass seam for this legacy package, add exact guards
    for new models, and place new service domain, migration, WebSocket transport, gateway and
    supervision responsibilities in focused modules — gains an incremental inward-arrow lift /
    sacrifices immediate uniformity with the generic Pydantic recommendation.
- **Decided:** C. Existing public command/response models remain strict frozen dataclasses with
  exhaustive serialization and extra-field rejection. New domain models follow that same seam.
  New effects live behind typed dependency records/protocols; CLI remains wiring only. Moves
  retain compatibility re-exports where tests or internal consumers still import old homes.
- **C1 clarification (2026-08-28):** the generated Codex JSON-RPC connection and gateway are
  protocol adapters, so their approved `call(method, params, timeout)` seam retains exact open
  wire objects and typed internal transport/call exceptions. D18's strict frozen-model rule
  governs worker domain and public command seams; Task 4 converts internal service/protocol
  failures into the closed public RPC/CLI fault model.
- **Shape at selection:** `service_domain.py` owns L0 value objects; `migration.py` owns durable
  legacy discovery/import; `websocket_transport.py` owns the initialized broker connection;
  `websocket_gateway.py` owns one-to-one forwarding and drain classification; `service.py` owns
  lifecycle composition. Existing `commands.py`, `registry.py`, `app_server.py`, `instance.py`,
  `facade.py`, `rpc.py`, and `cli.py` are lifted only where touched.
- **Enforcement:** focused strict-model round trips, enum exhaustiveness, AST import-arrow guards,
  seam inventory, and Python 3.9 compile/import tests make the exception checkable rather than
  conventional.
- **Rests on:** approved §5 module boundaries; generic Python patterns §§1–3/6/9; existing
  dependency-free strict-model contract and Python 3.9 floor.
- **Affects:** implementation file map, task ordering, compatibility shims, structural tests.
- **Revisit-when:** the package adopts Pydantic for an independently justified feature or the
  strict dataclass machinery can be replaced without coupling to a topology migration.

## D19 — Reconcile the split 8.0.0 release baseline, then ship this feature as 8.1.0
**When:** 2026-08-28T18:35:00Z · **Phase:** plan · **Status:** provisional (autonomous release decision)
**Decided by:** author after the plan reviewer measured divergent version authorities

- **Trigger:** the approved design originally illustrated 7.11.0, but current main has the
  Claude plugin and marketplace at 8.0.0 while six other declared authorities, including the
  UV tool, remain 7.10.0. Treating 7.11.0 as an advance would downgrade the shipping plugin.
- **Options weighed:**
  - A: ship 7.11.0 everywhere — gains the old plan target / sacrifices monotonic plugin versioning.
  - B: ship 8.0.1 — gains a patch increment / understates a public architecture and CLI migration.
  - C: first reconcile every lower declaration to the already-shipping 8.0.0 baseline, verify
    the coupled check/audit, then advance all eight together to 8.1.0 — gains monotonic truthful
    identity / costs one explicit baseline-reconciliation commit.
- **Decided:** C. The reconciliation commit changes only the six lower declarations and any
  generated public version line; the feature release then uses the ordinary atomic bump to 8.1.0.
  No install occurs between those two commits.
- **Rests on:** measured 2026-08-28 manifest values; global-install exact-version contract;
  non-editable UV package identity.
- **Affects:** plan release task, version tests, release notes, install/checkride provenance.
- **Revisit-when:** main changes any declared version again before the release task begins; remeasure
  and choose the next monotonic minor from the highest shipping authority.

## D20 — Migrate callback state as a pre-readiness idempotent transaction
**When:** 2026-08-28T18:35:00Z · **Phase:** plan · **Status:** provisional (autonomous persistence detail)
**Decided by:** author after the plan reviewer exposed the callback/outbox/artifact gap

- **Trigger:** legacy callback stores include immutable bindings, pending/written outbox entries,
  legacy `WorkerView.instance` fields, and terminal-reference payloads pointing at absolute
  per-instance artifacts. Importing only the registry would strand callbacks; independently
  replacing several files cannot be one filesystem-atomic operation.
- **Options weighed:**
  - A: migrate bindings only — gains simplicity / loses pending terminal delivery and artifacts.
  - B: leave callbacks in legacy directories and route by source — preserves bytes / keeps the
    removed instance namespace alive and makes source retirement impossible.
  - C: validate and canonicalize the complete merge before readiness; publish verified artifacts,
    then registry, callback store and a completion ledger in an idempotent ordered transaction;
    a crash reruns from untouched sources before serving — preserves semantics and removes routing
    dependence on legacy roots / costs explicit compatibility readers and canonical rewrite.
- **Decided:** C. Only callbacks for imported/deduplicated worker sessions migrate. Bindings keyed
  by session ID and outbox entries keyed by event ID deduplicate only when canonical bytes match;
  a mismatch quarantines the associated worker candidate. Pending events are upgraded to the new
  global worker projection. Referenced artifacts must be owner-only regular files beneath their
  declared legacy artifact root and match stored digest/size; they are parsed, projected without
  instance routing, and republished content-addressed under the global artifact root. Written
  entries retain their attempt history and no event body. All sources remain untouched.
- **Transaction order:** prevalidate every source and target collision; stage canonical artifacts;
  insert-or-verify artifacts; atomically write+fsync global registry; atomically write+fsync global
  callback store; atomically write+fsync the migration completion ledger last. The service is not
  ready during migration. Missing/incomplete ledger on restart reruns the same plan idempotently,
  repairing any prefix before clients can observe it.
- **Rests on:** D14 no-delete migration, callback store insert-or-verify behavior, global service
  pre-readiness gate, process-discipline reconstructability law.
- **Affects:** `ServicePaths`, legacy compatibility models, migration planner/commit order, callback
  store import API, artifact evidence and AH7/AH9.
- **Revisit-when:** callbacks move into one transactional database with registry/migration state.

## D21 — Separate internal startup readiness from authoritative public status
**When:** 2026-08-29T00:00:00Z · **Phase:** build · **Status:** provisional (Task 4 interface erratum)
**Decided by:** operator after Task 5 isolated live startup exposed cold-inventory coupling

- **Trigger:** the managed child bound both its private RPC socket and public listener in about
  200 ms, but the parent terminated it at the two-second startup deadline. Its readiness poll used
  public `service/status`, whose authoritative projection synchronously enumerates upstream Codex
  threads; a cold or blocked inventory made a healthy service look unready.
- **Options weighed:** lengthen startup timeouts, weaken public status, or add one private liveness
  handshake. Longer waits retain the incorrect dependency, while weakening status loses the
  operator's authoritative inventory view.
- **Decided:** add private JSON-RPC `service/readiness`, absent from CLI parsing and help. It reports
  only exact readiness, service version, daemon/app-server PIDs, configured listener, and the
  pre-readiness migration invariant. The managed startup/reuse loop validates the closed response,
  listener, and exact version without enumerating threads. Malformed and wrong-version responses
  terminate only the just-spawned generation and return typed refusals.
- **Public contract:** `service/status` remains authoritative and may be slower because it retains
  inventory and migration projection. Explicit `daemon start` still returns that public shape after
  the private readiness gate; common worker commands use only the private gate.
- **Rests on:** D4/D10/D14/D17; Task 5 live evidence; strict dataclass seam exception D18.
- **Affects:** Task 4 manager/facade/RPC interface, startup regression tests, live common commands.
- **Revisit-when:** Codex exposes a constant-time authoritative thread inventory or an atomic native
  service readiness primitive.

## D22 — Own and verify the complete Codex process group
**When:** 2026-08-29T00:04:00Z · **Phase:** build · **Status:** provisional (Task 4 lifecycle erratum)
**Decided by:** operator after Task 5 lifecycle evidence exposed a reparented native child

- **Trigger:** supervised restart terminated the spawned Node `codex` wrapper but left its native
  app-server child reparented to PID 1. The replacement could become ready while an owned child and
  private listener from the prior generation remained alive.
- **Decided:** spawn Codex with a new session, pin the verified PGID equal to its positive leader PID,
  and reject group 0, the daemon's current group, or any changed leader→group mapping. Maintenance
  sends TERM, then KILL when necessary, only to that pinned group; it reaps the wrapper and verifies
  the group is absent before termination returns and replacement readiness is possible.
- **Safety law:** no unpinned, reused, current, or zero PGID is signalled. A post-spawn identity
  mismatch fails closed. Direct wrapper termination is limited to the pre-pin failure path.
- **Evidence:** deterministic descendant/reparent, group-zero/current, and reuse controls plus the
  isolated lifecycle lane's active refusal, supervised force, and no-descendant/no-listener check.
- **Affects:** Task 4 service ownership seam and Task 5 finally-safe cleanup.
- **Revisit-when:** Codex exposes a single native process whose lifecycle provably includes every
  descendant, or the launcher supplies an equivalent verified process-tree handle.

## D23 — Accept additive fields in the native rate-limit envelope
**When:** 2026-08-29T00:24:00Z · **Phase:** build · **Status:** provisional (measured compatibility erratum)
**Decided by:** implementer after the required real-Claude caller exercised Codex 0.150.1

- **Trigger:** the live `limits` command reached Codex 0.150.1 successfully, but the adapter
  rejected the response because it required the top-level envelope to contain only
  `rateLimits`. The measured response also contained `rateLimitsByLimitId` and
  `rateLimitResetCredits`, while `rateLimits` remained a JSON object with the expected data.
- **Decided:** require a present object-valued `rateLimits` field and ignore additive top-level
  fields. Missing or non-object `rateLimits` remains a typed protocol error; no limit value is
  inferred, merged, or relabelled.
- **Evidence:** a deterministic additive-field positive control plus malformed-envelope negative
  control, followed by the real Claude PATH-only `limits` success on Codex 0.150.1.
- **Affects:** the inherited limits family and Task 5 real-Claude acceptance evidence only.
- **Revisit-when:** Codex removes or retypes `rateLimits`, or the product decides to expose the
  additional limit-ID/reset-credit families publicly.

## D24 — Restore the governing four-way CLI exit contract
**When:** 2026-08-29 · **Phase:** checkride correction · **Status:** locked
**Decided by:** operator after the independent evaluator found the companion surface contradicted the binding Python canon

- **Trigger:** handled operational states such as `timeout_active`, `service_busy`, and
  `address_in_use` exited 1, which the governing canon reserves for an internal bug.
- **Decided:** 0 is success, 1 is an uncaught or peer-reported internal bug, 2 is local usage, and 3 is every
  typed operational refusal returned by the local façade, RPC peer, managed supervisor, or
  endpoint safety boundary. One structured JSON object remains the refusal output.
- **Not exit 2:** a syntactically valid request refused by current runtime state is operational,
  even when the upstream JSON-RPC code resembles invalid params.
- **Affects:** CLI surface, exhaustive error mapping, subprocess/checkride expectations.
- **Revisit-when:** never without changing the governing Python operator-experience law first.

## D25 — Raw managed commands depend on strict readiness, not global inventory
**When:** 2026-08-29 · **Phase:** checkride correction · **Status:** locked
**Decided by:** operator after an unrelated ambiguous active thread blocked an exact session resume

- **Trigger:** `_managed_raw_endpoint` used full public status, so all-thread inventory failure
  prevented dispatch of an independently selected durable session/thread operation.
- **Decided:** managed raw session/turn/model commands use the hidden strict
  `service/readiness` RPC already introduced by D21. It validates exact ready state, version,
  listener, and process identity without inventory. The selected RPC remains responsible for
  its own session/thread validity.
- **Partial-failure law:** once a selected session/thread is known, any typed failure retains
  those IDs and a literal attach/resume route; unrelated inventory never replaces them with null.
- **Affects:** managed raw endpoint selection, ambiguity regression, raw reride rows.
- **Revisit-when:** public status becomes constant-time and provably independent of inventory.

## D26 — Emit only literal, parser-valid recovery actions
**When:** 2026-08-29 · **Phase:** checkride correction · **Status:** locked
**Decided by:** operator after the evaluator found placeholders, prose prefixes, and a hidden serve command

- **Decided:** every command-valued remedy is shell-safe, contains no angle-bracket placeholder,
  resolves to a real executable/public parser path, and parses without network contact. A stopped
  managed service points to `codex-worker daemon start`. A stopped known worker points to exact
  status and attach/resume commands rather than inventing continuation text. Busy maintenance
  substitutes every known exact worker name. Address collision provides a deterministic explicit
  alternate-listener start command but never executes fallback automatically.
- **Not force:** no ordinary refusal action suggests or invokes automated `--force`.
- **Affects:** façade faults, raw RPC recoveries, service manager refusals, exhaustive action guard.
- **Revisit-when:** the CLI gains a typed interactive prompt mechanism that can safely collect a
  missing value without encoding a fake shell command.

## D27 — Put limits and reconstructable count provenance on the public surface
**When:** 2026-08-29 · **Phase:** checkride correction · **Status:** locked
**Decided by:** operator after dangerous help and naked derived counts failed the governing surface law

- **Decided:** every public leaf `--help` includes a `Limits:` block. Stop/restart explicitly
  describe machine-wide scope, active refusal, and force impact. `daemon status` wraps worker and
  active-turn counts with value/source/availability/basis; the worker basis lists exact active and
  idle names, and active basis lists exact origin/worker/session/thread/turn/flags rows.
- **Stopped-state law:** durable worker names are reconstructable from registry state; active
  inventory is explicitly available and empty rather than inferred from absence.
- **Affects:** parser help, status models/projections, live help/status reride rows.
- **Revisit-when:** a separate inventory detail command replaces the embedded basis without
  reducing exact reconstruction.

## D28 — Count attempts and track literal sanitized ride evidence
**When:** 2026-08-29 · **Phase:** checkride correction · **Status:** locked
**Decided by:** operator after the first executor record mixed completed commands, an unmatched attempt, and placeholder cleanup corrections

- **Decided:** attempt count includes every `command_start`; completion distribution includes only
  terminal command records and separately reports unmatched attempts as NOT RUN. Claims such as
  `codex_failure` are derived from literal records. Cleanup corrections retain literal sanitized
  argv/assertion/output/exit/timing/substrate sufficient for reconstruction. The tracked real-Claude
  record contains sanitized literal command/output/exit rows for all 26 commands, not only a hash
  pointer to ignored raw text.
- **Affects:** recorder/harness contracts, real-Claude tracked evidence, affected-row reride.
- **Revisit-when:** the evidence format moves to a content-addressed artifact store that remains
  available from a fresh checkout.

## D29 — Preserve unavailable historical cleanup fields and require the reride to measure them
**When:** 2026-08-29 · **Phase:** checkride correction · **Status:** locked
**Decided by:** implementation erratum under D28's no-invention rule

- **Decided:** a historical cleanup row may label timing unavailable when the original measured
  harness did not retain it; it may not synthesize a duration. Such a row does not satisfy the
  final D28 gate. The same-executor reride must replace it with measured timing, substrate,
  stderr, environment-name allowlist, and literal pre-stop owner/path/PID assertions.
- **Future harness:** verifies owner markers and exact live PIDs before stop, removes its pinned
  isolated credential copy independently, and emits every D28 field for commands and assertions.
- **Affects:** historical real-Claude cleanup erratum and affected cleanup reride rows.
- **Revisit-when:** the required reride has produced a fully measured tracked cleanup record.
