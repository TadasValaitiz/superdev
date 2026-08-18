# Codex worker server — Decision log

**Design doc:** ./2026-08-18-codex-worker-server-design.md
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — Claude-facing boundary is local RPC, not MCP
**When:** 2026-08-18T18:15:19Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The initial proposal exposed the Codex worker through a stdio MCP server.
- **Options weighed:**
  - A: MCP server — gains native Claude Code tool discovery / sacrifices the intended direct local-RPC architecture and risks implying a hosted MCP dependency.
  - B: Local RPC service backed by the local Codex CLI — gains a persistent local worker boundary and direct control of the installed CLI / sacrifices native MCP tool presentation.
- **Decided:** Use local RPC, not MCP. The service and Codex CLI both run locally; Claude Code interacts with that local surface.
- **Rests on:** Human-stated requirement.
- **Affects:** R1, spec §5 architecture and transport, Claude Code integration surface.
- **Revisit-when:** Only if Claude Code gains a more direct supported local RPC client mechanism or the operator explicitly requests MCP integration.

## D2 — Unix-socket daemon with a CLI client
**When:** 2026-08-18T18:15:52Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** Local RPC still required a concrete transport and a Claude Code-accessible invocation surface.
- **Options weighed:**
  - A: JSON-RPC daemon over a Unix-domain socket with a companion CLI — gains durable local state, filesystem-scoped access, and ordinary shell invocation from Claude Code / sacrifices Windows portability in the first increment.
  - B: One-shot CLI processes talking directly to `codex app-server` over stdio — gains fewer moving parts / sacrifices cross-command persistence and reliable mid-turn steering.
- **Decided:** Run a background JSON-RPC daemon over a Unix socket; use `codex-worker` as the local CLI client with start, turn, steer, interrupt, wait, and shutdown operations.
- **Rests on:** D1 and human confirmation.
- **Affects:** R1–R3, spec §5 architecture, process lifecycle, RPC schema, CLI surface.
- **Revisit-when:** Windows support becomes an explicit requirement or Codex app-server's supported Unix transport can replace the wrapper without losing the Claude-facing command contract.

## D3 — Daemon startup is explicit
**When:** 2026-08-18T18:43:11Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The client needed defined behavior when its Unix socket has no healthy server behind it.
- **Options weighed:**
  - A: Auto-start on first client request — gains convenience / sacrifices explicit process ownership and makes startup failures less legible.
  - B: Explicit daemon start — gains observable lifecycle and predictable ownership / sacrifices one-command first use.
- **Decided:** Require an explicit daemon-start command in the first increment. Client operations fail clearly and name the recovery command when no daemon is reachable.
- **Rests on:** Human preference.
- **Affects:** R2, spec §5 lifecycle and error handling, CLI operator sequence.
- **Revisit-when:** Repeated usage shows explicit startup is the dominant usability cost and daemon supervision semantics are defined.

## D4 — One daemon manages multiple named workers
**When:** 2026-08-18T18:56:10Z · **Phase:** brainstorm ·
**Status:** superseded-by D12
**Decided by:** human

- **Trigger:** The daemon needed a worker-cardinality boundary.
- **Options weighed:**
  - A: One worker thread per daemon — gains minimal state management / sacrifices concurrent Claude-directed workers and requires multiple daemon/socket pairs.
  - B: Multiple named workers per daemon — gains one control plane and concurrent durable Codex threads / sacrifices a slightly richer registry and routing contract.
- **Decided:** One local daemon may manage multiple named worker threads concurrently. Worker name is the stable Claude-facing handle; Codex thread and active-turn IDs remain internal state.
- **Rests on:** D2 and human direction that the service can match multiple workers.
- **Affects:** R3–R5, spec §5 worker registry, concurrency, RPC and CLI schemas.
- **Revisit-when:** Resource isolation or fault containment requires one app-server process per worker.

## D5 — Worker conversations are crash-resumable
**When:** 2026-08-18T18:57:38Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** Multiple named workers needed continuity when Claude Code, the wrapper daemon, or a local session shuts down unexpectedly.
- **Options weighed:**
  - A: In-memory registry only — gains minimal implementation / sacrifices recovery and can strand otherwise durable Codex conversations.
  - B: Persist logical-session-to-Codex-thread mappings — gains restart recovery and conversation continuity / sacrifices persistence and reconciliation complexity.
- **Decided:** Persist each logical worker session's Codex thread identity and metadata. After restart, the daemon can resume the durable Codex thread from a stable session identifier; accidental shutdown must not discard the conversation.
- **Rests on:** Human-stated recovery requirement and Codex app-server's durable `thread/resume` primitive.
- **Affects:** R4–R6, spec §5 persistence, startup reconciliation, resume RPC, failure handling.
- **Revisit-when:** Codex changes thread durability semantics or the registry becomes externally managed.

## D6 — Daemon-minted session UUID with raw-thread recovery
**When:** 2026-08-18T19:27:53Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** Crash recovery required deciding which identity callers hold and what survives damage to the wrapper registry.
- **Options weighed:**
  - A: Expose only Codex thread IDs — gains no translation layer / sacrifices wrapper-owned identity and future backend flexibility.
  - B: Expose only daemon session UUIDs — gains encapsulation / sacrifices recovery when the wrapper registry is missing or corrupt.
  - C: Daemon-minted UUID as the public handle plus exposed raw Codex thread ID — gains stable abstraction and a diagnostic recovery escape hatch / sacrifices dual-identifier validation.
- **Decided:** The daemon mints and returns an opaque session UUID, persists its mapping to the Codex thread ID, exposes both, and accepts either identifier for resume. Normal commands use the session UUID.
- **Rests on:** D5 and human approval.
- **Affects:** R4–R6, spec §5 RPC models, registry schema, resume/recovery behavior.
- **Revisit-when:** A second worker backend is introduced or raw Codex IDs become unsafe to expose.

## D7 — No public streaming protocol in the first version
**When:** 2026-08-18T19:28:53Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The Claude-facing protocol needed an observation model for long-running turns.
- **Options weighed:**
  - A: Stream Codex notifications to clients — gains live output / sacrifices protocol and reconnection simplicity without a demonstrated SDD or brainstorming need.
  - B: Request/response operations with non-blocking start plus status/events/wait — gains simple durable control while retaining steer/interrupt windows / sacrifices token-by-token visibility.
- **Decided:** Do not expose streaming in the first version. `turn-start` returns immediately; callers use bounded `status`, `events`, and `wait` requests to observe progress and completion.
- **Rests on:** Human assessment of subagent-driven-development and brainstorming needs.
- **Affects:** R3, R7, spec §5 RPC protocol, event retention, CLI behavior.
- **Revisit-when:** A workflow demonstrates that polling or bounded waits cannot provide timely intervention.

## D8 — Shared local broker over alternative process shapes
**When:** 2026-08-18T19:31:40Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The approved boundary still admitted multiple internal process topologies.
- **Options weighed:**
  - A: One shared broker and one Codex app-server subprocess managing multiple threads — gains low overhead and follows Codex's native model / sacrifices process-level worker isolation.
  - B: One Codex app-server subprocess per worker — gains fault isolation / sacrifices resource efficiency and adds supervision/recovery complexity.
  - C: Thin raw-RPC proxy — gains minimal wrapper code / sacrifices stable session identity and pushes Codex protocol details into Claude Code.
- **Decided:** Use the shared local broker. It owns one Codex app-server subprocess, a persistent logical-session registry, and the higher-level RPC contract.
- **Rests on:** D2, D4, D5 and human approval of the recommended approach.
- **Affects:** R1–R8, spec §5 architecture, concurrency and recovery.
- **Revisit-when:** A measured app-server fault crosses worker boundaries or one process becomes a throughput bottleneck.

## D9 — Autonomous build must prove real agent workflows
**When:** 2026-08-18T19:31:40Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The operator delegated autonomous implementation and defined the evidence expected before completion.
- **Options weighed:**
  - A: Protocol/unit tests only — gains deterministic speed / sacrifices evidence that Claude Code can drive real Codex sessions.
  - B: Unit tests plus live local scenarios — gains deterministic defect coverage and end-to-end proof / sacrifices runtime and model usage.
- **Decided:** Build test-first, then exercise the real local Codex CLI with multiple models/efforts, multiple sessions and isolated worktrees. Scenarios include writing and running a hello-world app, creating files, executing commands, steering, interrupting, daemon restart, and conversation resume.
- **Rests on:** Human instruction and the repository's requirement that integrations be proven end-to-end.
- **Affects:** R8–R10, UC1–UC7, §9 acceptance and implementation verification.
- **Revisit-when:** A required model is unavailable locally; substitute only from live `model/list` output and record the measured substitution.

## D10 — Target the measured default Python 3.9 runtime
**When:** 2026-08-18T19:34:19Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** agent under autonomous mandate

- **Trigger:** `python3 --version` reported Python 3.9.6, while the prototype contains Python 3.10-only `X | None` annotation syntax.
- **Options weighed:**
  - A: Require Python 3.10+ — gains modern annotation syntax / sacrifices out-of-box operation on the measured host and weakens the zero-dependency plugin contract.
  - B: Support Python 3.9 with `typing.Optional`/`Union` where required — gains compatibility with the measured default runtime / sacrifices minor annotation concision.
- **Decided:** The shipped broker and tests support Python 3.9 and use only the standard library.
- **Rests on:** MEASURED local runtime (`Python 3.9.6`) and R11.
- **Affects:** R10–R11, spec §5.2, §5.7, implementation syntax and test commands.
- **Revisit-when:** The plugin declares and enforces a newer minimum Python version across every supported harness.

## D11 — Keep direct stdio ownership for the first increment
**When:** 2026-08-18T19:34:19Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** agent under autonomous mandate

- **Trigger:** Codex CLI 0.147.0 exposes native `app-server daemon` and `proxy` commands that could replace direct child-process ownership.
- **Options weighed:**
  - A: Depend on native daemon/proxy now — gains upstream process supervision / sacrifices compatibility with earlier Codex installs and introduces a second independently managed daemon lifecycle beneath the approved broker.
  - B: Retain direct `codex app-server` stdio ownership with an injectable command — gains compatibility with the measured prototype and deterministic test control / sacrifices upstream daemon reuse.
- **Decided:** The broker directly owns one stdio app-server child in this increment. The launch argv is injectable for tests and future proxy transport, but the public RPC contract is transport-independent.
- **Rests on:** D8, the working prototype, and MEASURED `codex-cli 0.147.0` help output.
- **Affects:** R2–R3, R11, spec §5.2, §8 declined scope.
- **Revisit-when:** Supporting multiple wrapper processes against one Codex server becomes required or the native daemon interface reaches a compatibility floor the plugin can mandate.

## D12 — Multiple workers use UUID identity; names are annotations
**When:** 2026-08-18T19:42:26Z · **Phase:** spec ·
**Status:** locked
**Decided by:** agent resolving independent spec-review contradiction

- **Trigger:** D4 called worker name the stable Claude-facing handle, contradicting approved D6's public daemon-minted UUID and the registry/domain design.
- **Options weighed:**
  - A: Make names unique public identity — gains mnemonic handles / sacrifices renameability and conflicts with the approved UUID recovery design.
  - B: Preserve multi-worker cardinality but supersede D4's identity clause — gains consistent durable UUID identity while retaining optional human labels / sacrifices name-only command lookup.
- **Decided:** One daemon still manages multiple workers, but `session_id` is the only stable wrapper identity; `name` is a non-unique annotation and never accepted as a lookup key. D12 supersedes only D4's stable-name sentence.
- **Rests on:** D6 and spec reviewer finding.
- **Affects:** R3–R5, spec §5.3, §5.8, CLI session/turn identifiers.
- **Revisit-when:** A separately namespaced alias registry with explicit collision semantics is required.

## D13 — Raw-thread recovery trusts and validates Codex's persisted cwd
**When:** 2026-08-18T19:42:26Z · **Phase:** spec ·
**Status:** locked
**Decided by:** agent resolving independent spec-review gap

- **Trigger:** Raw-thread recovery could not safely mint a `SessionRecord` without the immutable cwd that defines its sandbox.
- **Options weighed:**
  - A: Require the caller to restate `--cwd` — gains explicit input / sacrifices proof it matches the durable thread and permits accidental retargeting.
  - B: Resume by thread ID without a cwd override, read Codex's required returned `thread.cwd`, validate it, and persist that value — gains authoritative recovery / sacrifices recovery when the original cwd no longer exists.
- **Decided:** Raw recovery calls `thread/resume` with `approvalPolicy=never` and `sandbox=workspace-write` but no cwd override, validates the absolute existing directory returned in `thread.cwd`, then creates the wrapper mapping. Missing/invalid cwd is a hard recovery failure.
- **Rests on:** MEASURED Codex 0.147.0 generated schema: `Thread.cwd` and `ThreadResumeResponse.cwd` are required.
- **Affects:** R4–R5, R9, R13, spec §5.2–5.3, UC5.
- **Revisit-when:** Codex removes persisted cwd from resume responses or supports a cryptographically bound caller-supplied workspace migration.

## D14 — Live gate requires two distinct models and two effort values
**When:** 2026-08-18T19:47:26Z · **Phase:** spec ·
**Status:** locked
**Decided by:** agent resolving independent spec-review ambiguity

- **Trigger:** "Two model/effort pairs" could be satisfied by one model at two efforts, which would not prove the operator's explicit multiple-model requirement.
- **Options weighed:**
  - A: Any two distinct `(model, effort)` pairs — gains availability / sacrifices proof that routing crosses model families.
  - B: At least two distinct live-discovered model IDs and at least two distinct effort values across the exercised scenarios — gains exact evidence for the requested routing / sacrifices the ability to pass on a single-model installation.
- **Decided:** AH2/R10 require at least two distinct model IDs and two distinct effort values selected from live `model/list`. If unavailable, the autonomous acceptance gate is BLOCKED, not skipped or passed.
- **Rests on:** D9, human instruction, and spec-review finding.
- **Affects:** R8–R10, UC2, AH2, verification plan.
- **Revisit-when:** The operator explicitly relaxes the multiple-model acceptance requirement.
