# Codex worker command ergonomics — Decision log

**Design doc:** ./2026-08-19-codex-worker-command-ergonomics-design.md
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — Design the CLI product surface, not a skill-repair patch
**When:** 2026-08-19T13:00:07Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** The initial framing treated the observed friction as a Superdev
  self-improvement diagnosis; the operator clarified that the real subject is the CLI
  and the commands needed around its actual use.
- **Options weighed:**
  - A: treat the work as a narrow skill/documentation correction — gains a smaller
    patch / sacrifices command ergonomics and leaves callers reconstructing state.
  - B: design the Codex-worker CLI as a product surface from the recorded launch and
    observation journey — gains a coherent operator contract / requires explicit
    command, lifecycle, and output decisions before implementation.
- **Decided:** Take option B. The skill docs become a consumer of the resulting CLI;
  they do not define or constrain the product shape prematurely.
- **Rests on:** Direct operator clarification and the measured launch-friction
  transcript.
- **Affects:** CLI families, response models, lifecycle behavior, observation flow,
  and the later CLI surface document.
- **Revisit-when:** The desired outcome is reduced to documentation-only guidance with
  no CLI behavior changes.

## D2 — Make lifecycle and configuration harness-friendly
**When:** 2026-08-19T13:01:18Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** The operator clarified that the product must cover starting the worker
  server, stopping it, cleaning stale/runtime state, and passing configuration without
  forcing a harness to reproduce shell rituals.
- **Options weighed:**
  - A: improve only turn/result commands — gains a smaller surface / leaves first-launch
    lifecycle and configuration friction intact.
  - B: treat lifecycle, cleanup, configuration, dispatch, observation, and completion
    as one harness-facing CLI journey — gains an end-to-end usable product / expands the
    design beyond the original event-output complaint.
- **Decided:** Take option B. The CLI must make the complete harness journey direct and
  machine-readable, including safe cleanup rather than undocumented socket deletion.
- **Rests on:** Direct operator clarification plus the measured launch attempts.
- **Affects:** daemon commands, configuration precedence, state ownership, recovery,
  and end-to-end operator sequences.
- **Revisit-when:** A separate process supervisor becomes the sole supported lifecycle
  owner and explicitly absorbs these responsibilities.

## D3 — Provide explicit lifecycle plus idempotent ensure
**When:** 2026-08-19T13:02:09Z · **Phase:** brainstorm ·
**Status:** superseded-by D6
**Decided by:** Tadas

- **Trigger:** A harness needs a one-command setup path without losing explicit process
  control or making every unrelated client command mutate daemon state.
- **Options weighed:**
  - A: explicit `start/status/stop/clean` only — gains maximum transparency / forces
    every harness to implement readiness and reuse logic.
  - B: every worker command auto-starts — gains apparent convenience / hides lifecycle
    mutations and makes failures harder to localize.
  - C: explicit lifecycle plus idempotent `daemon ensure` — gains one safe harness
    setup command and preserves explicit operation / adds a small lifecycle verb.
- **Decided:** Take option C. `daemon ensure` starts or reuses a correctly configured
  daemon and does not return success before readiness; explicit lifecycle commands
  remain available.
- **Rests on:** Direct operator choice and the measured arbitrary-sleep startup failure.
- **Affects:** daemon command family, readiness protocol, configuration identity, and
  harness quickstart sequence.
- **Revisit-when:** Client commands gain a separately approved implicit-autostart
  contract.

## D4 — Treat daemons as independent instances, not one global singleton
**When:** 2026-08-19T13:04:53Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Configuration-mismatch handling assumed one daemon at one global
  endpoint, while real Claude Code work may need two or three concurrently configured
  worker servers and should not care about their process bookkeeping.
- **Options weighed:**
  - A: one global daemon whose configuration must match or be replaced — gains a simple
    singleton / sacrifices concurrent isolation and risks interrupting unrelated work.
  - B: independent daemon instances resolved from the requested configuration — gains
    concurrency and makes lifecycle bookkeeping a CLI responsibility / requires a
    stable instance handle and instance registry.
- **Decided:** Take option B. Claude Code passes what a worker pool needs; `daemon
  ensure` reuses or starts the matching independent instance and returns its handle.
  Differently configured daemons coexist and are never silently replaced.
- **Rests on:** Direct operator clarification and the established need for parallel,
  worktree-isolated worker roles.
- **Affects:** instance identity, daemon discovery, configuration, cleanup targeting,
  and every client command's endpoint selection.
- **Revisit-when:** The underlying Codex app-server supports safe multi-tenant
  configuration inside one process and process isolation is no longer useful.

## D5 — Derive the default daemon instance from the Claude session environment
**When:** 2026-08-19T13:09:12Z · **Phase:** brainstorm ·
**Status:** refined-by D9
**Decided by:** Tadas

- **Trigger:** Requiring Claude to retain and pass a daemon handle repeats information
  already present in every inherited command environment and adds precisely the harness
  friction this work is meant to remove.
- **Options weighed:**
  - A: return a daemon ID and require `--daemon <id>` on later calls — gains explicit
    selection / sacrifices zero-friction use and duplicates harness identity.
  - B: derive the default instance from `CLAUDE_CODE_SESSION_ID` and place runtime
    artifacts under `CLAUDE_JOB_DIR`, with flags as overrides — gains automatic
    per-Claude-session isolation and inherited sharing / depends on a documented
    non-Claude fallback.
- **Decided:** Take option B. The parent Claude session and its child commands share one
  default Codex-worker instance through inherited environment; separate Claude sessions
  naturally resolve separate instances. Explicit flags remain for other harnesses and
  exceptional isolation, but normal Claude commands carry no daemon identifier. D9
  later retains the identity rule while replacing `CLAUDE_JOB_DIR` storage with a
  separate Superdev-owned folder.
- **Rests on:** MEASURED Claude environment transcript showing inherited
  `CLAUDE_CODE_SESSION_ID`, `CLAUDE_JOB_DIR`, and identical child command environments.
- **Affects:** default socket/PID/log paths, configuration precedence, PATH packaging,
  multi-instance semantics, and quickstart examples.
- **Revisit-when:** Claude stops exporting stable session/job identity or begins
  exporting a reliable per-subagent identity that should own separate defaults.

## D6 — Make lifecycle implicit on the primary run command
**When:** 2026-08-19T13:10:42Z · **Phase:** brainstorm ·
**Status:** refined-by D18 and D23
**Decided by:** Tadas

- **Trigger:** Once daemon identity is safely derived from the Claude environment,
  requiring `daemon ensure` before sending a message becomes exposed implementation
  bookkeeping rather than useful operator control.
- **Options weighed:**
  - A: retain `daemon ensure` as the normal prerequisite — gains an explicit readiness
    boundary / sacrifices the desired one-command harness path.
  - B: let the primary message/run command resolve, bootstrap, and start or reuse the
    environment-scoped daemon internally — gains zero-friction dispatch / requires
    deterministic autostart errors and concurrency-safe startup.
- **Decided:** Take option B and supersede D3. Explicit daemon diagnostics and control
  remain, but normal dispatch begins with the message command and returns the finished
  result without a separate lifecycle step. D18 later narrowed lifecycle control to
  non-destructive `status`/`stop`; D23 split the primary message path into `start`/`run`.
- **Rests on:** D5's environment-derived instance identity and direct operator
  preference for implicit startup.
- **Affects:** primary command composition, autostart locking/readiness, registry
  bootstrap, error envelopes, and quickstart.
- **Revisit-when:** Implicit startup cannot provide equally legible failures or creates
  unsafe process ownership under a supported harness.

## D7 — Make `codex-worker run` the primary happy path
**When:** 2026-08-19T13:12:06Z · **Phase:** brainstorm ·
**Status:** superseded-by D23
**Decided by:** Tadas

- **Trigger:** The composed message-to-result path needs a short, obvious command name
  rather than exposing the existing daemon/session/turn choreography.
- **Options weighed:**
  - A: top-level `codex-worker run` — gains a clear primary entrypoint / composes several
    lower-level operations behind one verb.
  - B: `codex-worker turn run` — gains family consistency / still foregrounds an
    implementation-layer turn concept.
  - C: `codex-worker task` — gains a higher-level word / introduces a second task model
    alongside SDD tasks.
- **Decided:** Take option A. A new invocation creates a session by default; an explicit
  session selector continues an existing conversation. In both cases it starts/reuses
  the environment-scoped daemon, runs and waits, and returns the final result.
- **Rests on:** Direct operator choice and D6.
- **Affects:** top-level parser, composed broker/client workflow, output contract,
  continuation semantics, and documentation examples.
- **Revisit-when:** The CLI grows multiple equally primary execution modes that require
  a new family rather than one run path.

## D8 — Reuse only Claude session identity and process cwd behaviorally
**When:** 2026-08-19T13:16:41Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Claude exports many inherited variables, but treating all of them as
  worker configuration would couple unrelated harness settings to Codex behavior.
- **Options weighed:**
  - A: inherit session identity, job paths, effort, and runtime flags behaviorally —
    gains maximal implicit configuration / sacrifices predictability and conflates
    Claude reasoning effort with the worker's independently selected effort.
  - B: use `CLAUDE_CODE_SESSION_ID` for daemon-instance identity and the process cwd for
    default worker cwd; retain other Claude fields only as diagnostics metadata — gains
    the high-value defaults without hidden behavior / leaves model and effort explicit
    or dedicated-worker-config driven.
- **Decided:** Take option B. In particular, never inherit `CLAUDE_EFFORT` as Codex
  effort. `CLAUDE_PID`, bridge session, job directory, child/entrypoint/version, and
  agent identity may be reported as metadata but do not select model, effort, sandbox,
  or lifecycle behavior by themselves.
- **Rests on:** Direct operator decision and the MEASURED environment inventory.
- **Affects:** configuration precedence, run defaults, status metadata, model/effort
  validation, and non-Claude fallback behavior.
- **Revisit-when:** Claude exports a dedicated Codex-worker configuration contract
  rather than general Claude-session settings.

## D9 — Give each Claude session a separate worker folder keyed by the same UUID
**When:** 2026-08-19T13:18:51Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Runtime and durable worker files need isolation aligned with Claude
  session identity without living inside or depending on Claude's own job directory.
- **Options weighed:**
  - A: store worker files inside `CLAUDE_JOB_DIR` — gains proximity / couples recovery
    and cleanup to a harness-owned ephemeral directory.
  - B: create a separate Codex-worker folder under Superdev's user-owned storage,
    constructed with the same `CLAUDE_CODE_SESSION_ID` — gains predictable isolation
    and independent lifecycle / requires explicit cleanup policy.
- **Decided:** Take option B. The session UUID deterministically selects one separate
  worker-instance folder holding its owned socket/state/PID/log/readiness artifacts;
  Claude's job directory is metadata only.
- **Rests on:** Direct operator decision and D5/D8.
- **Affects:** path layout, permissions, startup locking, cleanup scope, persistence,
  diagnostics, and non-Claude instance fallback.
- **Revisit-when:** The host provides a first-class per-session plugin storage API with
  equivalent durability and ownership guarantees.

## D10 — Keep worker names optional
**When:** 2026-08-19T13:22:10Z · **Phase:** brainstorm ·
**Status:** superseded-by D11
**Decided by:** Tadas

- **Trigger:** Requiring a caller-chosen worker name on the primary run path adds
  bookkeeping even when one obvious conversation exists for the current work.
- **Options weighed:**
  - A: require a unique name and use it as the normal selector — gains a short stable
    alias / sacrifices zero-configuration first use.
  - B: make name optional and resolve the ordinary conversation from inherited Claude
    identity plus working context — gains the shortest common path / requires an
    explicit ambiguity rule for multiple conversations in the same context.
- **Decided:** Take option B. Names remain optional annotations/aliases and may help
  distinguish concurrent roles, but absence of a name never prevents ordinary first
  use or follow-up.
- **Rests on:** Direct operator decision plus D5/D8's implicit Claude identity and cwd
  inputs.
- **Affects:** session lookup, run syntax, ambiguity errors, session-list output, and
  continuation/recovery rules.
- **Revisit-when:** A supported harness cannot supply any stable working context and
  routinely hosts multiple anonymous conversations.

## D11 — Require a stable worker name on `run`
**When:** 2026-08-19T13:24:53Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** An unnamed default becomes ambiguous as soon as one Claude coordinator
  fans out multiple Codex workers, while an explicit name is a small cost and removes
  the need for a separate `--new` concept.
- **Options weighed:**
  - A: optional name plus cwd-scoped default and `--new` — gains a flag-free singleton
    path / sacrifices one uniform addressing rule.
  - B: require `--name` on the primary run command and use it as the worker key inside
    the environment-selected daemon — gains one simple rule for ordinary use and
    fan-out / requires choosing a name once per role.
- **Decided:** Take option B and supersede D10. `(Claude session identity, worker name)`
  locates the logical conversation; no `--new` flag is needed. The daemon-minted UUID
  remains authoritative recovery evidence.
- **Rests on:** Direct operator decision and the fan-out requirement.
- **Affects:** run arguments, uniqueness constraints, continuation semantics, session
  list/show/cleanup selection, and quickstart examples.
- **Revisit-when:** The host exports a stable per-worker/subagent identity that can
  replace the explicit name without ambiguity.

## D12 — Reusing a name continues; skills generate collision-resistant names
**When:** 2026-08-19T13:27:39Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** A required worker name simplifies fan-out only if its repeated-use
  semantics are predictable and accidental role-name collisions are controlled.
- **Options weighed:**
  - A: repeated name replaces the conversation — gains implicit freshness / silently
    destroys continuity and recovery context.
  - B: repeated name continues the conversation; fresh reuse requires explicit
    clearing — preserves context / requires callers to avoid accidental collisions.
- **Decided:** Take option B. Superdev skills that mint worker names must use a readable
  role/task stem plus a number or short random component so independent workers in the
  same Claude session do not collide. The exact daemon-minted session UUID remains
  available for forensic recovery.
- **Rests on:** Direct operator decision and D11.
- **Affects:** name uniqueness, run lookup, cleanup/reset commands, SDD naming guidance,
  and recovery documentation.
- **Revisit-when:** The CLI itself gains a separate atomic name-reservation/minting
  mechanism that removes collision responsibility from callers.

## D13 — Keep `run` synchronous and leave concurrency to the harness
**When:** 2026-08-19T13:28:43Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Fan-out raised the possibility of CLI-managed detach/wait or batch
  orchestration, but the calling cloud harness already owns concurrent command launch
  and joining.
- **Options weighed:**
  - A: add `--detach`, wait aggregation, or a batch command — gains CLI-owned
    concurrency / duplicates harness capabilities and expands state/control surface.
  - B: keep each `run` synchronous from message through final result — gains a simple,
    composable process contract / requires the consumer to launch multiple commands
    concurrently when desired.
- **Decided:** Take option B. One invocation blocks until its turn reaches a terminal
  state and prints the complete result; how several invocations are scheduled or joined
  is explicitly outside the CLI contract.
- **Rests on:** Direct operator decision and the harness's existing concurrent command
  machinery.
- **Affects:** run lifecycle, output timing, timeout semantics, cancellation behavior,
  and rejected scope.
- **Revisit-when:** A supported consumer lacks process-level concurrency and cannot
  safely coordinate multiple synchronous invocations.

## D14 — Demonstrate five concurrent named runs, not a token-heavy stress campaign
**When:** 2026-08-19T13:30:33Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** The daemon architecture permits independent sessions to overlap, but a
  hypothetical hundred-worker live run would spend disproportionate model tokens and
  is not the product's acceptance target.
- **Options weighed:**
  - A: require a hundred simultaneous live workers — gains a high stress number /
    sacrifices substantial tokens without matching expected use.
  - B: demonstrate five simultaneous named runs, supplementing deterministic transport
    and isolation checks — gains evidence at the intended operating scale / does not
    claim unmeasured hundred-worker capacity.
- **Decided:** Take option B. Acceptance proves five named sessions can run concurrently
  through one daemon and complete independently; overload outside the demonstrated
  envelope must fail legibly rather than silently serialize or corrupt state.
- **Rests on:** Direct operator calibration and MEASURED prior evidence for two
  concurrent worktree-isolated sessions.
- **Affects:** concurrency acceptance hint, queue/backpressure behavior, verification
  scope, and honesty wording.
- **Revisit-when:** Real usage approaches five concurrent workers or reports capacity
  failures that justify a larger measured envelope.

## D15 — Return final messages plus measured effort metadata in extensible JSON
**When:** 2026-08-19T13:33:43Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** A synchronous run must hand the harness the complete agent report and
  enough technical metadata to judge how much observable work occurred, without forcing
  another event-stream reconstruction.
- **Options weighed:**
  - A: print only final text — gains minimal output / loses identity, recovery, and
    effort observability.
  - B: return an extensible JSON result containing all authoritative final-answer
    messages plus measured turn/item/command/time/usage metadata — gains a complete
    machine contract / requires careful separation of upstream facts from derived
    metrics.
  - C: include the entire event transcript — gains maximal detail / floods the common
    response and duplicates the diagnostic surface.
- **Decided:** Take option B. Message containers are arrays from the first version so
  multiple final outputs are not collapsed. The final agent report is preserved in
  full; compact measured counts/timing/usage accompany it; detailed events remain a
  separate diagnostic command.
- **Rests on:** Direct operator decision and local protocol evidence: agent messages
  carry `commentary`/`final_answer` phases, command items carry `durationMs`, reasoning
  content may be redacted, and turn/token notifications are authoritative where present.
- **Affects:** run result model, runtime aggregation, timestamps, token/item accounting,
  schema evolution, and output documentation.
- **Revisit-when:** Upstream supplies one authoritative typed final-result object that
  subsumes the message array without losing information.

## D16 — Generic final messages by default; optional typed output schema
**When:** 2026-08-19T15:36:08Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Verdict, report, and review are useful typed outputs for some roles but
  are not universal concepts across implementation, research, and ordinary dialogue.
- **Options weighed:**
  - A: preserve only generic final-answer messages — gains universality / gives up
    structural outputs when a task has a known contract.
  - B: impose one fixed verdict/report/review schema — gains a predictable reviewer
    shape / misfits other roles.
  - C: preserve generic final messages by default and accept an optional per-run output
    schema — gains universality plus structural enforcement when requested / adds one
    optional input and nullable result field.
- **Decided:** Take option C. The CLI forwards the schema to Codex for that turn and
  returns the structured output without trying to parse prose; final-answer messages
  remain available in all cases.
- **Rests on:** Direct operator approval and verified upstream `outputSchema` support.
- **Affects:** run arguments, turn/start adapter, result JSON, validation errors, and
  reviewer/implementer invocation examples.
- **Revisit-when:** Every supported role adopts one shared structured return contract.

## D17 — Keep metrics best-effort and provenance-labelled
**When:** 2026-08-19T15:36:08Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Effort metadata is useful, but some desired figures are absent or
  redacted upstream and should not complicate or weaken the core command.
- **Options weighed:**
  - A: require every proposed metric — gains a dense report / forces unreliable
    derivation or blocks the feature on optional telemetry.
  - B: require final messages and terminal identity, while including only directly
    measured or authoritative metrics with availability/source labels — gains honesty
    and implementation flexibility / some fields may be null.
- **Decided:** Take option B. Wall time may be locally measured; item/type counts and
  command durations may be aggregated from authoritative events; token usage is
  included only when emitted. Hidden reasoning is never inferred.
- **Rests on:** Direct operator calibration and the protocol probe.
- **Affects:** result metric schema, runtime aggregation, acceptance requirements, and
  documentation honesty labels.
- **Revisit-when:** Codex publishes a stable complete per-turn usage/effort object.

## D18 — Expose only non-destructive `daemon stop`
**When:** 2026-08-19T15:37:34Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** “Clear the daemon” was clarified to mean stop the live runtime, never
  delete conversation identity or durable state.
- **Options weighed:**
  - A: `clean` removes runtime files while preserving sessions — gains a repair verb /
    names behavior that implicit startup can safely own.
  - B: offer a destructive purge/reset — gains a one-command wipe / violates the
    operator's no-destruction requirement.
  - C: expose only idempotent `daemon stop`; implicit startup repairs stale runtime
    markers and preserves all named sessions — gains clear, safe lifecycle semantics /
    deliberately omits daemon-level deletion.
- **Decided:** Take option C. `daemon stop` waits for runtime shutdown and may remove
  only owned socket/PID/readiness markers. Registry, named conversations, logs, and
  recovery identities survive. There is no daemon clean/purge command in scope.
- **Rests on:** Direct operator decision and the durable-resume requirement.
- **Affects:** daemon family, stale-start repair, instance-folder retention, recovery,
  and declined destructive scope.
- **Revisit-when:** A separately designed archival/retention policy requires explicit
  deletion with its own safety contract.

## D19 — Default initial worker cwd to the process cwd
**When:** 2026-08-19T15:39:11Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Requiring `--cwd` once improves explicitness but adds friction when the
  harness already launches the command from the intended worktree.
- **Options weighed:**
  - A: require `--cwd` on first use — gains an explicit declaration / repeats the
    command's actual location.
  - B: default to the process's canonical current directory, allow `--cwd` override,
    and return the resolved path — gains a short common path with visible identity /
    relies on the harness launching from the intended directory.
  - C: prompt interactively — gains confirmation / is unsuitable for a machine harness.
- **Decided:** Take option B. Cwd is persisted for the named worker and immutable on
  continuation. It is a starting/work context, not a filesystem access boundary.
- **Rests on:** Direct operator choice and the harness's normal per-worktree command
  execution.
- **Affects:** run defaults, session identity, response metadata, cwd mismatch errors,
  and external-path documentation.
- **Revisit-when:** A supported harness routinely invokes commands from a neutral
  launcher directory that does not represent task context.

## D20 — Default to full computer access; expose a simple read-only flag
**When:** 2026-08-19T15:46:54Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Workers must be able to follow absolute file references, inspect sibling
  worktrees, and act outside the starting cwd when the task requires it; cwd is context,
  not a security boundary.
- **Options weighed:**
  - A: broad reads with writes confined to cwd — gains write containment / prevents
    legitimate cross-directory changes.
  - B: full filesystem/runtime access by default with an explicit read-only mode — gains
    unrestricted implementation capability and structural reviewer restriction /
    places trust in the local harness and caller.
  - C: read-only by default with explicit elevation — gains least privilege / adds
    routine friction to implementation workers.
- **Decided:** Take option B. The common surface is full access or `--read-only`; cwd
  remains the starting directory. The CLI maps those choices to Codex sandbox policy
  internally rather than requiring callers to construct policy JSON.
- **Rests on:** Direct operator decision and the local, owner-scoped daemon model.
- **Affects:** run arguments, session persistence, app-server thread start/resume,
  diagnostics, reviewer guidance, and security documentation.
- **Revisit-when:** The worker is exposed beyond the local owner boundary or a supported
  task requires an intermediate public sandbox mode.

## D21 — Prefer two-tier selection with a raw-model escape hatch
**When:** 2026-08-19T15:51:55Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Normal Superdev callers should not repeat volatile model IDs, while the
  CLI must remain capable of selecting a specifically requested discovered model.
- **Options weighed:**
  - A: expose only raw `--model` — gains directness / repeats provider-specific routing
    policy in every caller.
  - B: expose only `--tier` — gains the shortest policy-aligned surface / removes the
    escape hatch for explicit live models.
  - C: support normal `--tier medium|very-smart` and a mutually exclusive raw `--model`
    escape hatch — gains both simplicity and control / adds one validation branch.
- **Decided:** Take option C. Tier resolves through the approved Terra/Sol mapping and
  live discovery; raw model must also pass discovery. The resolved model and effort are
  persisted on the named worker for short follow-ups.
- **Rests on:** Direct operator choice and the existing two-tier model policy.
- **Affects:** run arguments, model discovery, configuration persistence, mismatch
  reporting, skill examples, and result metadata.
- **Revisit-when:** The live model catalog provides stable capability tiers that can
  replace Superdev's explicit mapping.

## D22 — Default new workers to medium tier and medium effort
**When:** 2026-08-19T15:53:57Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Requiring tier/model and effort on every new worker protects against
  hidden selection but makes the common command noisier than needed.
- **Options weighed:**
  - A: require tier/model plus effort initially — gains maximal explicitness /
    sacrifices the short default path.
  - B: default to `medium` tier and `medium` effort — gains a safe balanced ordinary
    worker / relies on live validation and explicit elevation for hard roles.
  - C: rely on dedicated environment defaults and otherwise require flags — gains
    session-wide configurability / adds setup outside the command.
- **Decided:** Take option B. Resolve `medium` to Terra and validate both model and
  effort against live discovery. If unavailable, return a typed blocker; never fall
  back. Explicit tier/model and effort override the defaults.
- **Rests on:** Direct operator choice plus the two-tier policy's ordinary-work route.
- **Affects:** first-run defaults, live discovery, error handling, persisted worker
  configuration, and skill routing examples.
- **Revisit-when:** Measured usage shows the default routinely needs a different effort
  or the medium-tier model changes.

## D23 — Separate first-message `start` from follow-up `run`
**When:** 2026-08-19T16:14:58Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Overloading `run` to both create/configure and continue a worker makes
  its arguments broad and permits accidental configuration drift on later messages.
- **Options weighed:**
  - A: `initialize` stores configuration, then `run` sends the first and later messages
    — gains a narrow run command / costs two invocations for the first task.
  - B: `start` atomically creates the named immutable worker and sends its first
    message; `run` sends follow-ups only — gains one invocation per message and distinct
    contracts / adds one top-level verb.
  - C: retain create-or-continue `run` — gains one verb / keeps ambiguous broad parsing.
- **Decided:** Take option B and supersede D7's create-or-continue form. `start` fails
  if the name exists; `run` fails if it does not. Both accept exactly one of inline
  `--prompt` prose or `--prompt-file`, wait synchronously, and return the same result
  envelope.
- **Rests on:** Direct operator choice, D11/D12 naming, and immutable initial
  configuration.
- **Affects:** top-level parser, atomic session creation, follow-up lookup, prompt input,
  output symmetry, error recovery, and skill examples.
- **Revisit-when:** A transactional configuration/session API makes a separate
  initialization call materially safer than atomic start.

## D24 — Wait indefinitely by default; timeout only by request
**When:** 2026-08-19T16:15:50Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** A synchronous message command promises a final result, while an arbitrary
  default timeout can return control before that result and recreate observation
  friction.
- **Options weighed:**
  - A: retain a finite default timeout — gains bounded command duration / can expire
    healthy long work based on an arbitrary number.
  - B: wait indefinitely unless `--timeout` is supplied — gains semantic alignment with
    the final-result contract / leaves cancellation and process deadlines to the
    harness.
  - C: always return immediately — gains non-blocking operation / contradicts D13.
- **Decided:** Take option B. An explicit timeout does not cancel work; it returns a
  typed active-state result with exact status/control recovery commands.
- **Rests on:** Direct operator choice and the harness-owned scheduling boundary.
- **Affects:** run/start client timeout, RPC waiting, signal handling, active-state
  errors, and documentation.
- **Revisit-when:** A supported harness cannot impose its own process deadline or
  indefinite local commands cause measured operational failures.

## D25 — Expose worker observation and control as top-level commands
**When:** 2026-08-19T16:16:44Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** A second shell must be able to inspect or control a named worker while
  its synchronous `start`/`run` call is blocked, without reconstructing daemon session
  UUIDs and turn-family syntax.
- **Options weighed:**
  - A: keep `turn status/events/steer/interrupt` as the common surface — gains reuse /
    exposes lower-level selectors and event structure.
  - B: add top-level `status`, `messages`, `steer`, and `interrupt` by worker name while
    retaining lower-level commands for compatibility/recovery — gains concise
    harness-facing operations / adds thin composed aliases.
- **Decided:** Take option B. Top-level commands resolve the Claude-scoped named worker;
  advanced session/turn commands remain available but are not required in the normal
  journey.
- **Rests on:** Direct operator choice plus D11/D13.
- **Affects:** parser families, named-session resolution, message projection, control
  races, help text, and command documentation.
- **Revisit-when:** Lower-level command families are formally removed or another public
  transport becomes the primary operator surface.

## D26 — Keep top-level messages to a simple tail projection
**When:** 2026-08-19T16:20:02Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** The first-launch transcript proved that agent narration is the useful
  progress view, but reproducing the full event query language on the common surface
  would add premature complexity.
- **Options weighed:**
  - A: latest message only with optional `--tail N` — gains a minimal progress command /
    leaves filtering and cursor archaeology to the advanced surface.
  - B: phase filters and cursor pagination — gains precision / repeats lower-level event
    mechanics before measured demand.
  - C: return all retained messages — gains completeness / may flood caller context.
- **Decided:** Take option A. `messages` returns the latest agent message by default and
  accepts `--tail N`; full event pagination remains under `turn events`.
- **Rests on:** Direct operator decision and measured `agentMessage` phase/event data.
- **Affects:** messages arguments, projection result, event retention interaction,
  help text, and declined scope.
- **Revisit-when:** Repeated usage requires phase-specific or cursor-based message
  retrieval on the common path.

## D27 — Auto-start only from message-producing commands
**When:** 2026-08-19T16:20:53Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Implicit lifecycle removes setup friction but can make read/control
  commands surprisingly mutate process state if applied indiscriminately.
- **Options weighed:**
  - A: every command starts the daemon — gains universal availability / makes status,
    stop, and failed control attempts create processes.
  - B: only `start` and `run` start/restart; observation, control, and daemon commands
    report stopped state without mutation — gains predictable reads and a frictionless
    message path / callers cannot inspect lost in-memory events after a stop.
- **Decided:** Take option B. A later `run` restarts the runtime, resumes the named
  durable conversation, and continues; status/messages/steer/interrupt and daemon
  status/stop never autostart.
- **Rests on:** Direct operator approval and D6/D18.
- **Affects:** client bootstrap wrapper, command classification, stopped-state errors,
  recovery, and tests.
- **Revisit-when:** A command's documented purpose explicitly becomes ensuring runtime
  availability rather than observing or controlling existing state.

## D28 — Build a session-scoped instance manager and high-level facade
**When:** 2026-08-19T16:23:20Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** The agreed command contract needs implicit lifecycle, named workers,
  durable recovery, and result aggregation without replacing the proven lower-level
  broker.
- **Options weighed:**
  - A: session-scoped instance manager plus high-level facade over existing RPC core —
    gains the desired harness API while preserving tested mechanics / adds lifecycle and
    aggregation layers.
  - B: thin aliases that retain caller-owned socket/state/readiness — gains a small diff
    / preserves launch friction.
  - C: one Codex process per command — gains simple process ownership / loses efficient
    continuity and durable multi-worker coordination.
- **Decided:** Take option A. The instance manager owns environment-derived paths,
  concurrency-safe autostart/readiness, and stopped-state handling; the facade composes
  named session operations and final-result projection over the existing broker.
- **Rests on:** Direct operator choice and D5–D27.
- **Affects:** module boundaries, CLI parser, process spawn/locking, broker lookup,
  runtime aggregation, compatibility surface, and testing seams.
- **Revisit-when:** Codex's native daemon exposes the same named-worker, lifecycle, and
  aggregated-result contract directly.

## D29 — Expose Codex's native goal state through the named-worker facade
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Codex already provides persistent per-thread goal state and authoritative
  progress fields, so callers should not have to restate an objective in prompts or
  invent a parallel progress model.
- **Options weighed:**
  - A: leave goals on the raw app-server surface — gains no new CLI commands /
    sacrifices easy harness access and name-based continuity.
  - B: proxy goal set/show through the common named-worker surface — gains a durable
    objective plus provider-reported token/time progress / adds a small command family.
  - C: build a Codex-worker-specific goal tracker — gains total schema control /
    duplicates upstream state and creates synchronization risk.
- **Decided:** Take option B. Add name-scoped `goal set` and `goal show` commands that
  proxy Codex's native goal API. Accept an objective and optional token budget on set;
  report only fields supplied authoritatively by Codex. Do not invent progress metrics
  or a second durable goal store.
- **Rests on:** Direct operator decision and the measured app-server goal API.
- **Affects:** common CLI families, broker proxy methods, result schemas, capability
  reporting, and skill guidance for long-running workers.
- **Revisit-when:** Codex removes or materially changes thread goal support, or measured
  use requires goal history rather than current state.

## D30 — Caller cancellation does not implicitly interrupt the worker
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Synchronous `start` and `run` can outlive the shell command that is
  waiting for them; equating a disconnected caller with an explicit agent
  interruption would make terminal closure and harness cancellation destructive.
- **Options weighed:**
  - A: leave the active Codex turn running when the waiting client exits — gains
    recovery through status/messages and prevents accidental cancellation / requires a
    separate explicit interrupt when cancellation is intended.
  - B: automatically interrupt on client disconnect or Ctrl-C — gains coupled process
    semantics / risks losing useful work because a transport disappeared.
- **Decided:** Take option A. Client cancellation stops only the local wait. The named
  worker and its active turn continue; `interrupt --name` is the sole common-path
  cancellation command.
- **Rests on:** Direct operator choice plus D18/D24's preservation and recovery model.
- **Affects:** RPC connection lifecycle, signal handling, synchronous command docs,
  recovery envelopes, and checkride scenarios.
- **Revisit-when:** A supported harness requires parent-death cancellation and can pass
  that intent explicitly rather than inferring it from transport loss.

## D31 — Add durable history and account limits as thin native proxies
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** The app-server already exposes durable thread-turn history and current
  account rate-limit state, both of which remove harness guesswork with little new
  product machinery.
- **Options weighed:**
  - A: expose both `history` and `limits` with goals — gains durable read-back and
    fan-out awareness / adds two small read-only commands.
  - B: expose only history — gains conversation recovery / leaves callers unable to
    inspect authoritative capacity before parallel dispatch.
  - C: defer both — keeps the first release narrower / misses low-cost upstream value.
- **Decided:** Take option A. `history --name <name> [--tail N]` projects Codex's durable
  prior turns and final answers. `limits` projects provider-supplied rate-limit state
  and returns a typed unavailable result when the authentication mode does not expose
  it. Neither command estimates or caches missing upstream data.
- **Rests on:** Direct operator approval and the measured app-server methods
  `thread/turns/list` and `account/rateLimits/read`.
- **Affects:** common CLI families, broker proxy methods, result models, daemon
  non-mutation rules, and fan-out guidance.
- **Revisit-when:** Either upstream method becomes unstable or callers require richer
  pagination/capacity policy than a faithful projection provides.

## D32 — Let `start` install the native goal before the first turn
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Requiring a separate `goal set` after the initial message would mean the
  first turn runs without the very objective meant to govern the worker.
- **Options weighed:**
  - A: add optional `--goal` and `--token-budget` to `start` — gains atomic first-turn
    intent / modestly broadens the creation-only command.
  - B: expose goals only through later `goal set` — keeps `start` smaller / forces an
    extra command and cannot govern the first turn.
- **Decided:** Take option A. When supplied, `start` creates the upstream thread, sets
  the Codex-native goal successfully, then sends the first prompt. Goal failure prevents
  the first turn and returns the known worker/thread recovery identity; it is never
  silently ignored.
- **Rests on:** Direct operator approval and D23/D29.
- **Affects:** start command model, operation ordering, partial-failure recovery,
  response metadata, and goal proxy coverage.
- **Revisit-when:** Codex supports goal fields directly in thread creation or turn start
  with equivalent atomic semantics.

## D33 — Split durable instance storage from the short live socket path
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** A previously measured live run exceeded macOS's AF_UNIX path limit when
  the socket inherited a long job/worktree path; placing every artifact in the durable
  session folder would reproduce that failure.
- **Options weighed:**
  - A: keep socket and durable files together — gains conceptual locality / is not
    reliable under the measured platform limit.
  - B: keep registry/log/PID/readiness metadata in Superdev's session-keyed durable
    folder and place only the socket in a short owner-only runtime path — gains reliable
    transport plus durable recovery / requires recording the resolved socket path.
- **Decided:** Take option B and refine D9. Use a short, hashed, user-owned runtime path
  for the live socket; durable metadata records that exact path. `daemon stop` removes
  only the live socket and runtime markers while preserving registry, logs, and worker
  recovery state.
- **Rests on:** Direct operator approval and the MEASURED AF_UNIX path-length failure.
- **Affects:** instance path resolver, permissions, lifecycle cleanup, diagnostics,
  readiness, and platform tests.
- **Revisit-when:** The transport changes away from filesystem Unix sockets or the host
  provides a guaranteed short per-session socket directory.

## D34 — Resolve instance identity through flags, environment, then a local default
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Tadas

- **Trigger:** Claude Code supplies a useful session identity automatically, but the
  CLI must also work for other local harnesses and allow deliberate multi-instance
  isolation without exposing raw transport paths.
- **Options weighed:**
  - A: require Claude environment identity — gains one narrow integration / excludes
    ordinary shell and other harness use.
  - B: derive identity from cwd outside Claude — gains automatic variation / couples
    process ownership to a mutable working context and fragments shared workers.
  - C: resolve `--instance`, then `CODEX_WORKER_INSTANCE`, then
    `CLAUDE_CODE_SESSION_ID`, then a stable user-local `default` — gains explicit
    override, portable automation, frictionless Claude use, and a predictable fallback.
- **Decided:** Take option C in that exact precedence. Instance IDs select owned state;
  callers never need to pass socket or registry paths on the common surface.
- **Rests on:** Direct operator approval and D5/D8/D33.
- **Affects:** global CLI options, environment contract, path derivation, diagnostics,
  non-Claude documentation, and instance-isolation tests.
- **Revisit-when:** A host-standard agent-session identity becomes available across all
  supported harnesses.

## D35 — Return an additive, provenance-labelled completion envelope
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** Harnesses need the entire final answer even when Codex emits multiple
  final agent messages, plus useful effort evidence without pretending that hidden
  reasoning steps are observable.
- **Options weighed:**
  - A: return only the last text message — gains compactness / can discard parts of a
    multi-message verdict or report.
  - B: return the raw event stream — gains maximal detail / floods normal callers and
    makes them reconstruct completion.
  - C: preserve the JSON-RPC envelope and return ordered final messages, optional native
    structured output, stable worker/turn identity, and source-labelled metrics — gains
    completeness and extensibility / requires a projector over retained turn items.
- **Decided:** Take option C. Never parse final prose into invented verdict/report/review
  fields; callers that need those fields provide `--output-schema`. Metrics distinguish
  locally measured wall time from Codex-emitted token/item/command data and represent
  unavailable fields explicitly.
- **Rests on:** The operator's final-report requirement, D15–D17, and the measured
  `agentMessage`, `commandExecution.durationMs`, output-schema, and usage surfaces.
- **Affects:** start/run response models, item retention, output-schema forwarding,
  metrics vocabulary, compatibility, and acceptance evidence.
- **Revisit-when:** Codex exposes a canonical higher-level completion report that
  subsumes this projection without losing multiple final messages.

## D36 — Bootstrap absent or empty registries; refuse malformed durable state
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** The measured launch journey failed after a caller created an empty state
  file, while silently replacing malformed non-empty state would risk losing recovery
  identities.
- **Options weighed:**
  - A: require callers to know and write the registry schema — gains strictness /
    exposes implementation details and recreates launch friction.
  - B: initialize a missing or zero-byte registry, but return a typed path/schema error
    for non-empty invalid content — gains safe first use without destructive repair.
  - C: overwrite any invalid registry — gains self-healing / can destroy durable
    sessions.
- **Decided:** Take option B. Initialization is atomic and owner-only. A malformed
  non-empty registry is preserved byte-for-byte and the error explains the path,
  expected shape/version, and recovery options without requiring source inspection.
- **Rests on:** The measured empty-registry failure and D18's no-destruction rule.
- **Affects:** registry loading, instance bootstrap, error details, filesystem
  permissions, and recovery tests.
- **Revisit-when:** A versioned migration framework can repair additional known legacy
  shapes without ambiguity or data loss.

## D37 — Install a real `codex-worker` launcher on the plugin PATH
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** The measured Claude journey had to discover and invoke the implementation
  script by path even though the plugin already contributes its `bin/` directory to
  child-shell PATH.
- **Options weighed:**
  - A: document the nested script path — gains no packaging change / remains brittle
    and harness-specific.
  - B: add a source-controlled `bin/codex-worker` launcher that resolves the packaged
    implementation relative to itself — gains ordinary command discovery and works
    from any cwd / requires install and cache-buster verification.
- **Decided:** Take option B. The launcher is the public executable; docs never require
  callers to invoke the nested script path.
- **Rests on:** The measured PATH inventory and launch-friction transcript.
- **Affects:** plugin packaging, executable permissions, help examples, installer
  verification, and checkride setup.
- **Revisit-when:** The plugin platform gains a manifest-native executable entrypoint.

## D38 — Preserve the advanced RPC surface as an explicit compatibility layer
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** The new façade removes normal socket/session/turn choreography, but the
  proven lower-level commands remain valuable for raw-thread recovery and event-level
  diagnostics.
- **Options weighed:**
  - A: remove or silently reinterpret existing commands — gains a smaller visible
    surface / breaks recovery scripts and obscures migration.
  - B: keep existing `model`, `session`, and `turn` families as advanced compatibility
    commands while adding the common façade — gains backward compatibility and a clear
    escape hatch / carries two documented altitudes.
- **Decided:** Take option B. Common commands use instance/name selection; advanced
  commands retain raw selectors and explicit transport overrides. Help and docs label
  the boundary instead of mixing the two workflows.
- **Rests on:** D25/D28 and the existing tested broker contract.
- **Affects:** parser organization, global option precedence, documentation, regression
  coverage, and migration guidance.
- **Revisit-when:** A separately versioned major release intentionally removes the old
  surface after measured consumers migrate.

## D39 — Decode structured output only in explicit schema mode
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm self-review ·
**Status:** refined-by D41
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** Generated Codex 0.147.0 schemas confirm `turn/start.outputSchema` and
  final `agentMessage.text`, but no separate parsed structured-output field on the
  completed turn.
- **Options weighed:**
  - A: claim a native parsed field exists — gains a simpler story / contradicts the
    measured protocol.
  - B: omit structured projection and leave every caller to decode — gains no projector
    logic / repeats deterministic harness work.
  - C: only when `--output-schema` was supplied, JSON-decode the last final-answer text
    governed by that schema, retain the original message verbatim, and return a typed
    protocol error if decoding fails — gains a useful structured field without parsing
    ordinary prose.
- **Decided:** Take option C. Codex remains responsible for schema-constrained
  generation; the CLI performs JSON decoding, not heuristic extraction or semantic
  classification. `structured_output` is null when no schema was requested. D41 later
  defines the protocol-nullable message selected for decoding.
- **Rests on:** Local generated Codex 0.147.0 request/notification schemas.
- **Affects:** completion projection, output provenance, error handling, result models,
  and schema-mode acceptance evidence.
- **Revisit-when:** Codex adds an authoritative parsed structured-output field.

## D40 — Keep the plugin executable dependency-free with strict frozen seam models
**When:** 2026-08-19 (recorded at MEASURED 16:39:52Z) · **Phase:** brainstorm self-review ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** The generic Python canon prefers frozen Pydantic seam models, but this
  plugin ships a PATH script without a Python package manager or declared runtime
  dependency; system Python must run it immediately after plugin installation.
- **Options weighed:**
  - A: import Pydantic without packaging it — gains literal canon syntax / makes first
    use depend on an unrelated site package.
  - B: add a packaging/bootstrap subsystem — gains Pydantic availability / materially
    expands this CLI ergonomics project and introduces network/environment failure.
  - C: use frozen stdlib request/response models with explicit strict constructors,
    closed enums, and rejected extras at every seam — preserves portability and the
    canon's behavioral guarantees / sacrifices Pydantic's generated validation.
- **Decided:** Take option C as a scoped project-specific exception. Business decisions
  still leave the CLI leaf, every service has one request/response model, and tests pin
  strict validation and serialization.
- **Rests on:** The measured plugin layout and absence of any runtime dependency
  installation contract.
- **Affects:** domain models, parser/service seams, serialization, packaging, tests,
  and the implementation plan's engineering-pattern constraints.
- **Revisit-when:** The plugin platform supports declared Python dependencies or this
  executable becomes an installed Python package.

## D41 — Fall back to the last agent message when completion phase is unknown
**When:** 2026-08-19T16:47:02Z (MEASURED) · **Phase:** spec review ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** Codex 0.147.0 declares `agentMessage.phase` nullable, so requiring an
  explicit `final_answer` phase can discard a valid terminal response and break schema
  decoding.
- **Options weighed:**
  - A: require explicit final phase — gains a simple filter / produces false incomplete
    results for protocol-valid providers.
  - B: return every agent narration as final — avoids loss / floods normal completion
    and mislabels commentary.
  - C: select all explicit final-answer messages when present; otherwise select the last
    completed agent message as `terminal_fallback` while preserving its null/unknown
    phase — gains protocol compatibility with a visible fallback rule.
- **Decided:** Take option C for live completion and durable history. Schema mode decodes
  the last selected completion message. Only a terminal turn with no agent message at
  all is `incomplete_completion`.
- **Rests on:** Generated Codex 0.147.0 `AgentMessageThreadItem.phase` schema.
- **Affects:** completion/history projection, result fields, schema decoding, metrics,
  and acceptance evidence.
- **Revisit-when:** Codex makes completion role non-null and consistent across providers.

## D42 — Use one bounded shell-safe worker-name contract
**When:** 2026-08-19T16:47:02Z (MEASURED) · **Phase:** spec review ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** A required unique name without a field-level bound leaves validation,
  registry identity, help, and tests free to diverge.
- **Options weighed:**
  - A: accept arbitrary Unicode strings — gains expressiveness / creates shell,
    rendering, and normalization ambiguity.
  - B: require `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` — gains a portable 1–128 character
    token suitable for shell commands while still allowing readable randomized names.
- **Decided:** Take option B. Names remain data and never become path fragments.
- **Rests on:** D11–D12's role/collision use and the machine-harness CLI boundary.
- **Affects:** every name-selected command model, registry uniqueness, help, errors,
  skill examples, and tests.
- **Revisit-when:** A supported harness requires human-language labels distinct from
  the stable worker key; add a separate annotation rather than weakening identity.

## D43 — Make advanced endpoint selection additive and explicit
**When:** 2026-08-19T16:47:02Z (MEASURED) · **Phase:** spec review ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** The draft both promised unchanged raw socket commands and declared
  `--instance` for advanced commands without listing it exhaustively; `daemon status`
  also needs both a new instance view and the old raw RPC response.
- **Options weighed:**
  - A: remove advanced instance selection — preserves old parsing / makes raw recovery
    awkward against an implicitly managed daemon.
  - B: silently change old socket-selected responses to new shapes — gains uniformity /
    breaks compatibility.
  - C: allow exactly one explicit endpoint override (`--instance` or `--socket`) on
    advanced clients, retain legacy environment/default-socket behavior when neither is
    supplied in legacy mode, and let explicit `--socket daemon status/shutdown` keep the
    old wire response while instance-selected status/stop use new models.
- **Decided:** Take option C. Every advanced CLI row lists both selectors explicitly;
  common commands reject `--socket`.
- **Rests on:** R12, D34, D38, and the existing global socket contract.
- **Affects:** parser dispatch, exhaustive CLI tables, daemon dual-mode status,
  environment precedence, response models, and regression tests.
- **Revisit-when:** A major version removes the raw surface after consumer migration.

## D44 — Map access mode at both distinct Codex protocol seams
**When:** 2026-08-19T16:47:02Z (MEASURED) · **Phase:** spec review ·
**Status:** locked
**Decided by:** Codex under Tadas's autonomous handoff

- **Trigger:** Codex 0.147.0 uses kebab-case `sandbox` enum values on thread
  start/resume and tagged camel-case `sandboxPolicy` objects on turn start.
- **Options weighed:**
  - A: document one generic mapping — gains brevity / is wrong at one protocol seam.
  - B: map `full` to thread `danger-full-access` and turn
    `{type: dangerFullAccess}`, and map `read_only` to thread `read-only` and turn
    `{type: readOnly, networkAccess: false}` — gains exact, testable enforcement.
- **Decided:** Take option B. Thread creation/resume also sets
  `allowProviderModelFallback: false`; turn start resends the persisted policy so sticky
  upstream configuration cannot drift.
- **Rests on:** Local generated Codex 0.147.0 `SandboxMode`, `SandboxPolicy`,
  `ThreadStartParams`, `ThreadResumeParams`, and `TurnStartParams` schemas.
- **Affects:** app-server adapter, worker start/resume/run, access metadata, and
  protocol-fixture/live acceptance tests.
- **Revisit-when:** Codex unifies the two request encodings or replaces them with named
  permissions profiles.
