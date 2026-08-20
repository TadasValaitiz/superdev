# Codex worker → Claude callbacks — Decision log

**Design doc:** ./2026-08-20-codex-worker-claude-callbacks-design.md
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — Bind one stable Claude return room at worker creation
**When:** 2026-08-20T07:17:02Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** A named Codex worker may receive later `run` calls from different shells
  or subagents, but its completion and proactive messages must return to the Claude room
  that originally delegated the work.
- **Options weighed:**
  - A: capture the Claude destination at `start` and retain it — gains stable routing and
    prevents accidental redirection / requires an explicit operation to move the route.
  - B: recapture ambient Claude messaging variables on every `run` — gains convenience
    when ownership moves / allows an unrelated follow-up invoker to hijack callbacks.
- **Decided:** Capture the return room once during `start`; later `run` calls retain it.
  Redirection is possible only through an explicit override.
- **Rests on:** the measured one-inbox-per-Claude-session protocol and the operator's
  requirement that short follow-ups not repeat routing metadata.
- **Affects:** callback configuration, worker persistence, automatic completion delivery,
  and the agent-initiated messaging command.
- **Revisit-when:** ownership transfer between live Claude rooms becomes a common rather
  than exceptional workflow.

## D2 — Relay both callback paths through the worker daemon
**When:** 2026-08-20T08:04:41Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Automatic completion and agent-initiated messages need the same route to
  Claude without exposing Claude's raw socket credential inside a Codex turn.
- **Options weighed:**
  - A: let Codex and completion wrappers send directly to Claude — gains fewer daemon
    changes / duplicates routing and exposes transport credentials to the worker.
  - B: store the callback binding per named worker and make the daemon the sole relay —
    gains one policy, one audit point, and scoped Codex commands / adds a daemon seam.
- **Decided:** Use the daemon relay for both automatic terminal notification and the
  proactive command. Keep `send_to_claude.py` as the measured transport prototype and
  build working example scripts before hardening the production CLI.
- **Rests on:** the measured one-way Claude UDS protocol and the existing named-worker
  daemon architecture.
- **Affects:** callback binding, daemon events, probe scripts, future CLI, and security.
- **Revisit-when:** Claude publishes a supported authenticated callback API.

## D3 — Allow explicit return-room override
**When:** 2026-08-20T08:04:41Z · **Phase:** brainstorm · **Status:** superseded-by D5
**Decided by:** Tadas

- **Trigger:** The initial Claude room is normally correct, but exceptional ownership
  transfers and test scenarios need a deliberate alternate destination.
- **Options weighed:**
  - A: make the captured room immutable — gains the smallest surface / cannot transfer.
  - B: retain the stable default while exposing an explicit override — gains controlled
    transfer / requires clear one-shot versus persistent semantics.
- **Decided:** Support an explicit room override while preserving the initially captured
  room as the default. The exact override lifetime remains to be designed.
- **Rests on:** D1 and the operator's stated override requirement.
- **Affects:** command models, callback persistence, recovery, and audit output.
- **Revisit-when:** room ownership becomes centrally brokered.

## D4 — Proactive messages are non-blocking notifications
**When:** 2026-08-20T08:04:41Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Codex may want to surface a question or observation without serializing
  its work on a cross-agent answer.
- **Options weighed:**
  - A: send and continue; Claude may later `steer` or `run` — gains simple broadcast-like
    behavior and parallel progress / the answer is not correlated into the same call.
  - B: block for a correlated reply — gains synchronous dialogue / requires question
    IDs, timeouts, restart recovery, and a second response protocol.
- **Decided:** Treat agentic messages as fire-and-continue notifications. Claude chooses
  whether to respond later through the worker's existing `steer` or `run` surface.
- **Rests on:** existing named-worker continuation/control commands and the user's desire
  to avoid polling or unnecessary serialization.
- **Affects:** message command result, delivery semantics, and declined reply protocol.
- **Revisit-when:** a demonstrated workflow requires the same Codex turn to await input.

## D5 — Override one message with `cc-agent-name`
**When:** 2026-08-20T08:07:28Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Exceptional notifications may target another Claude Code agent, but they
  must not silently transfer the worker's default completion destination.
- **Options weighed:**
  - A: one-message override — gains explicit local routing without mutating ownership.
  - B: persistent rebind — gains ownership transfer / risks redirecting later completion.
  - C: expose both — gains flexibility / broadens a probe before transfer is needed.
- **Decided:** Support only a one-message override. Name the public property
  `cc-agent-name`; do not expose generic `room` terminology or a persistent setter.
- **Rests on:** D1, D3, and the operator's choice of override semantics and vocabulary.
- **Affects:** agentic message command, callback request model, resolver, and examples.
- **Revisit-when:** a real workflow needs durable worker ownership transfer.

## D6 — Infer the default callback directly; reserve `cc-agent-name` for overrides
**When:** 2026-08-20T08:10:59Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Requiring a Claude agent name during ordinary worker creation would
  repeat metadata already present in the spawning Claude process's environment.
- **Options weighed:**
  - A: require `--cc-agent-name` at `start` — gains a readable label / adds launch
    friction and registry lookup to the common path.
  - B: bind the ambient messaging socket/token directly and use `cc-agent-name` only for
    one-send overrides — gains zero-config return routing / the default is address-based.
- **Decided:** Take option B. `cc-agent-name` is optional and override-only; it is not a
  required worker property and is not inferred for the normal callback path.
- **Rests on:** inherited `CLAUDE_CODE_MESSAGING_SOCKET` and
  `CLAUDE_CODE_MESSAGING_TOKEN`, measured by the protocol probe.
- **Affects:** `start` defaults, callback binding schema, message override resolution,
  and examples.
- **Revisit-when:** Claude stops exporting a scoped child callback address/credential.

## D7 — Notify every terminal outcome with the complete structured result
**When:** 2026-08-20T08:12:44Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Eliminating Claude-side polling requires failures and interruptions to be
  visible just as reliably as successful completion.
- **Options weighed:**
  - A: notify successful completion only — gains a narrower happy path / leaves Claude
    polling for failed and interrupted work.
  - B: notify every terminal state — gains complete lifecycle visibility / requires the
    event to represent non-success outcomes explicitly.
- **Decided:** Emit one versioned automatic callback for `completed`, `failed`, and
  `interrupted`. Do not emit for an observation timeout because the turn remains active.
  Include worker/session/thread/turn identities, terminal status, all selected final
  messages, structured output when present, provenance-labelled metrics, and recovery
  commands rather than a bare `done` marker.
- **Rests on:** existing terminal projection and the user's approval of the recommended
  all-terminal behavior.
- **Affects:** callback event schema, terminal transition hook, Claude prompt content,
  and failure recovery.
- **Revisit-when:** the upstream protocol adds additional terminal states.

## D8 — Enable callbacks automatically only in a Claude messaging environment
**When:** 2026-08-20T08:14:58Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Completion notification should remove launch friction without making the
  Claude-specific transport mandatory for standalone Codex worker use.
- **Options weighed:**
  - A: explicit opt-in on every `start` — gains maximum visibility / repeats boilerplate.
  - B: enable when a valid Claude socket/token is ambient, degrade cleanly when absent,
    and expose `--no-callback` — gains the short common path and explicit escape hatch.
- **Decided:** Take option B. A Claude-launched worker captures the callback
  automatically; a standalone worker continues normally with callback unavailable;
  `--no-callback` suppresses capture for that worker.
- **Rests on:** inherited Claude messaging variables and the operator's approval of all
  three recommended behaviors.
- **Affects:** `start` request, worker status, callback availability, and error handling.
- **Revisit-when:** another harness gains a compatible callback transport.

## D9 — Proactive sends identify the worker by its required unique name
**When:** 2026-08-20T08:17:02Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** A shared daemon can host several simultaneous Codex conversations, while
  their launched shell commands have no reliable per-worker OS identity.
- **Options weighed:**
  - A: infer the worker from ambient process state — gains a shorter command / can route
    to the wrong conversation under fan-out.
  - B: require the existing unique worker name and teach the exact command during
    initialization — gains deterministic routing / repeats one already-known argument.
- **Decided:** Proactive sends use `codex-worker message --name <worker> <text>`. The
  initialization instructions provide Codex its name and command. A one-send
  `--cc-agent-name` may override the destination without changing the default binding.
- **Rests on:** the measured lack of per-subagent environment identity, the existing
  required worker-name contract, and the operator's approval.
- **Affects:** agent instructions, message request model, CLI validation, and routing.
- **Revisit-when:** Codex exposes trustworthy per-thread environment injection.

## D10 — Queue by default with an explicit priority escape hatch
**When:** 2026-08-20T08:18:13Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** Callback messages must wake Claude without routinely disrupting whatever
  turn the orchestrator is already executing.
- **Options weighed:**
  - A: always deliver `now` — gains minimum latency / creates avoidable interruption.
  - B: always deliver `next` — gains orderly turns / cannot distinguish urgent blockers.
  - C: default to `next`, fix automatic completion at `next`, and allow explicit
    `now|later` on proactive sends — gains safe defaults plus deliberate escalation.
- **Decided:** Take option C. Automatic terminal callbacks always use `next`; proactive
  messages default to `next` and may explicitly request `now` or `later`.
- **Rests on:** the measured Claude message priority enum and the operator's approval.
- **Affects:** callback envelope, proactive message CLI, validation, and examples.
- **Revisit-when:** Claude changes the semantics of its inbound priority queue.

## D11 — Make the daemon the sole callback relay
**When:** 2026-08-20T08:20:11Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** The integration needs both automatic terminal callbacks and proactive
  Codex messages while supporting multiple named workers safely.
- **Options weighed:**
  - A: daemon relay — gains one binding, policy, audit, and future CLI seam / adds a
    callback component to the daemon.
  - B: direct scripts — gains the quickest isolated send / exposes credentials and
    duplicates routing.
  - C: callback sidecar — gains transport isolation / adds another lifecycle and socket.
- **Decided:** Take option A. The daemon alone holds Claude credentials and sends. Build
  two executable probe scripts for terminal and proactive paths, but make them exercise
  the same event shapes and transport boundary intended for the daemon rather than form
  an alternate production architecture.
- **Rests on:** D2, the measured protocol probe, and the operator's explicit selection.
- **Affects:** component boundaries, security, scripts, daemon RPC, and future CLI.
- **Revisit-when:** the callback transport must be shared by multiple non-worker tools.

## D12 — Use `orchestrator-original` as the live callback probe target
**When:** 2026-08-20T08:28:28Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** Tadas

- **Trigger:** The two technical probes require a live Claude Code room that will
  acknowledge receipt through independently inspectable evidence.
- **Options weighed:**
  - A: use a disposable unnamed Claude process — gains isolation / weakens stable
    addressing and requires additional launch machinery.
  - B: use `orchestrator-original`, instructed to reply, with a JSONL file as the return
    path — gains a real named-room send and inspectable pong / depends on that room live.
- **Decided:** Use `orchestrator-original`. The initial file probe produced a MEASURED
  seq=2 pong at `2026-08-20T11:27:00+03:00`, confirming the room and return-evidence
  convention before either callback script is built.
- **Rests on:** the operator-provided live target and
  `.superdev/brainstorm/codex-worker-claude-callback-ping-pong.jsonl`.
- **Affects:** probe fixtures, live acceptance flow, and evidence capture.
- **Revisit-when:** that named Claude room is no longer live or discoverable.

## D13 — Use explicit message/message-file input instead of positional prose
**When:** 2026-08-20T08:37:20Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex during approved-design authoring

- **Trigger:** D9's conversational example sketched positional `<text>`, but the existing
  common worker surface consistently validates mutually exclusive inline/file inputs and
  needs an exact strict command model.
- **Options weighed:**
  - A: positional prose — gains a shorter shell example / makes file input and future
    flags easier to misparse.
  - B: exactly one of `--message` or `--message-file` — gains parity with prompt handling
    and local validation / adds one explicit flag.
- **Decided:** Take option B. D9's routing decision remains unchanged; only the input
  spelling is refined.
- **Rests on:** existing `--prompt|--prompt-file` command conventions and the approved
  `message` family boundary.
- **Affects:** CLI companion §2/§5, `MessageWorkerRequest`, Codex initialization examples.
- **Revisit-when:** the whole common CLI adopts positional content consistently.

## D14 — Keep product authority in Superdev and measured probes at their source
**When:** 2026-08-20T08:37:48Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex during approved-design authoring

- **Trigger:** The measured protocol/reference and requested probe scripts originate in
  the trading-platform repository, while `codex-worker` product code and its canonical
  specifications live in Superdev.
- **Options weighed:**
  - A: copy research into Superdev — gains one checkout / duplicates a measured source.
  - B: keep probes/evidence in their source repository and link them from the
    authoritative Superdev design — gains one home per artifact / requires a two-repo
    execution plan and evidence handoff.
- **Decided:** Take option B. This log and the product spec live in Superdev. The exact
  initial pong evidence remains at
  `/Users/tadas/Projects/ai-ethics/ai-trading-calibration/.superdev/brainstorm/codex-worker-claude-callback-ping-pong.jsonl`.
- **Rests on:** the operator-approved repository boundary in design section 4.
- **Affects:** spec context, implementation-plan staging, probe commits, and receipts.
- **Revisit-when:** callback transport research becomes a supported Superdev library.

## D15 — Bind callbacks to Claude process identity and scrub the Codex environment
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** The current app-server inherits the daemon environment, and a PID-derived
  socket can later be reused by another Claude process. Socket permissions and an old
  child token do not prevent misdelivery on platforms where Claude authentication is
  optional.
- **Options weighed:**
  - A: retain socket/token only — gains a small binding / leaks credentials downstream
    and cannot distinguish PID reuse.
  - B: capture registry identity and config root, validate session ID + PID + process
    start before every write, then remove messaging credentials from the Codex child
    environment — gains recipient continuity and least capability / adds identity checks.
- **Decided:** Take option B. Enabled capture requires one registry record matching the
  ambient socket and captures its session ID, PID, process start, and config root. The
  daemon consumes the socket/token but launches Codex with both messaging variables
  removed. Every send revalidates the captured identity; mismatch is stale-target refusal.
- **Rests on:** MEASURED Claude registry fields and source-confirmed inherited `Popen`
  environment.
- **Affects:** binding fields, daemon spawn, default sends, restart, security tests.
- **Revisit-when:** Claude exposes a kernel-bound recipient handle or supported sender.

## D16 — Use a durable at-least-once write policy with stable duplicate identity
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** A daemon crash after socket write but before state commit is unknowable to
  the next process; the original pending-only design could neither resume without a
  payload nor avoid all duplicates.
- **Options weighed:**
  - A: at-most-once by marking before send — gains no deliberate duplicate / can lose the
    only completion callback during a crash.
  - B: durable at-least-once write policy — persist the full bounded event before send and
    retry every non-written event with the same ID; gains no intentional loss before a
    complete write / permits a duplicate in the crash window.
- **Decided:** Take option B for automatic terminal callbacks. The guarantee is about
  completing a socket write, never Claude delivery. The terminal callback payload and
  attempt counter are durable. A crash-window replay uses the same event ID and is
  explicitly documented as possibly duplicate. Proactive calls remain single bounded
  attempts; an explicit retry is a new event.
- **Rests on:** the one-way measured transport and the no-poll objective.
- **Affects:** callback outbox, attempt states, restart recovery, event schema, AH7.
- **Revisit-when:** Claude supplies an authenticated delivery acknowledgment or dedupe key.

## D17 — Spill oversized terminal results to a durable verified artifact
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** A complete terminal result can exceed Claude's single-line cap, so the
  original promise of one complete inline callback was impossible for unbounded output.
- **Options weighed:**
  - A: truncate — gains one small prompt / violates complete-report intent.
  - B: chunk into many Claude prompts — keeps bytes inline / creates ordering and repeated
    turn-trigger complexity.
  - C: atomically persist the full event and send a bounded reference envelope with path,
    digest, and exact size — keeps one notification and complete recoverability / Claude
    performs one file read after being notified.
- **Decided:** Take option C. Ordinary results stay inline. Oversized terminal results use
  `turn_terminal_reference`; the full owner-readable JSON artifact is immutable and
  digest-addressed. This is notification-driven retrieval, not polling.
- **Rests on:** same-machine full-access/read-only Claude tools and measured line cap.
- **Affects:** R3, transport, event artifacts, cleanup retention, acceptance.
- **Revisit-when:** Claude supports multipart atomic prompt injection or larger frames.

## D18 — Inject the exact worker instance into proactive commands
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** Worker name is unique only inside one instance; a Codex shell may not
  inherit the same ambient instance selector as the launching Claude command.
- **Options weighed:**
  - A: inject name only — gains brevity / may contact the wrong or stopped daemon.
  - B: inject `--instance <WorkerView.instance>` plus name — gains exact routing / adds
    one stable argument to the taught command.
- **Decided:** Take option B for every proactive command and recovery action shown to
  Codex. The instance and name together identify the relay.
- **Rests on:** existing instance-scoped daemon architecture and recovery command style.
- **Affects:** D9 refinement, initialization instructions, CLI examples, live fan-out.
- **Revisit-when:** the worker gets a trustworthy scoped command wrapper.

## D19 — Freeze exact callback event names and override scope
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** The draft diagram said `terminal` while prose said `turn_terminal`, and
  D3 remained open-ended after D5 had already selected one-message override.
- **Options weighed:** preserve aliases (compatibility with nothing shipped, more drift)
  or freeze one vocabulary and mark the broad decision superseded.
- **Decided:** Event names are exactly `turn_terminal`, `turn_terminal_reference`, and
  `worker_message`. D3 is superseded by D5: only proactive `worker_message` supports
  `cc-agent-name`, for that send only.
- **Rests on:** D5, D7, D17 and the unshipped draft status.
- **Affects:** event enum, diagram, payload tests, decision traceability.
- **Revisit-when:** a version-2 schema deliberately adds an event kind.

## D20 — Make final envelope sizing a daemon-owned protocol refusal
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** The client cannot know the final daemon-owned worker/event envelope, so it
  cannot truthfully reject oversize proactive payloads as a local exit-2 usage error.
- **Options weighed:** duplicate envelope construction in the client (drift risk) or size
  once after daemon construction (typed remote refusal).
- **Decided:** The daemon counts JavaScript UTF-16 code units on the final JSON user line
  as `len(line.encode("utf-16-le")) / 2`, excluding the newline, and enforces the measured
  1,048,576-unit cap. Oversized proactive messages return
  `callback_payload_too_large`, exit 1. Oversized terminal results follow D17.
- **Rests on:** MEASURED Claude JavaScript buffer semantics and strict CLI envelopes.
- **Affects:** R10, transport validation, fault vocabulary, Unicode boundary tests.
- **Revisit-when:** the receiver changes its decoder or counting rule.

## D21 — Persist resolver root and make disabled stronger than an override
**When:** 2026-08-20T08:45:25Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec review

- **Trigger:** Named resolution can drift with `CLAUDE_CONFIG_DIR`, and the draft did not
  say whether an explicit override bypasses `--no-callback`.
- **Options weighed:** use daemon ambient config and allow every override (convenient but
  nondeterministic/bypasses explicit suppression) or persist the capture root and enforce
  state-aware rules.
- **Decided:** Persist the canonical start-time Claude config/registry root in the
  binding whenever it can be resolved safely, and never substitute later daemon ambient
  state. Disabled rejects all callback sends, including overrides. Unavailable has no
  default route but may use an explicit named override only through that persisted root.
- **Rests on:** D8's explicit suppression and measured `CLAUDE_CONFIG_DIR` behavior.
- **Affects:** binding nullability/invariants, override resolver, faults, status, tests.
- **Revisit-when:** overrides receive a separate operator authorization policy.

## D22 — Reserve a closed callback fault-code block
**When:** 2026-08-20T09:18:00Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex during spec self-review

- **Trigger:** The existing façade validates a closed kind/code map, while the callback
  CLI companion named seven new typed faults without assigning JSON-RPC codes.
- **Options weighed:**
  - A: reuse generic `codex_failure` or `invalid_params` — gains no enum additions /
    destroys callback-specific recovery and misstates daemon-owned failures.
  - B: defer numbers to implementation — gains temporary flexibility / makes the API
    design non-exhaustive and permits test/docs drift.
  - C: reserve the next contiguous façade block — gains a closed public contract / uses
    seven codes.
- **Decided:** Take option C: `-32031 callback_unavailable`, `-32032
  callback_target_stale`, `-32033 callback_target_not_found`, `-32034
  callback_target_ambiguous`, `-32035 callback_target_unsafe`, `-32036
  callback_send_failed`, and `-32037 callback_payload_too_large`. Durable callback-store
  failures reuse existing `-32011 registry_error`.
- **Rests on:** the existing closed `FacadeFaultCode`/`FACADE_FAULT_KINDS` contract.
- **Affects:** command models, RPC errors, CLI exits, docs, and exhaustive enum tests.
- **Revisit-when:** the façade introduces a versioned error namespace.

## D23 — Scope credential isolation to product-managed propagation
**When:** 2026-08-20T09:26:00Z · **Phase:** spec · **Status:** locked
**Decided by:** Codex after independent spec re-review

- **Trigger:** R6 and earlier D11/D15 prose implied the daemon could exclusively hold
  Claude credentials even when the approved worker access mode permits the same UID to
  read `~/.claude/sessions` and peer-token files independently.
- **Options weighed:**
  - A: keep the absolute security claim — sounds stronger / is unenforceable and gives a
    future implementer a false acceptance target.
  - B: add an OS/filesystem sandbox around Codex — could enforce exclusivity / breaks the
    approved full-computer and read-only access semantics and greatly expands scope.
  - C: scope the guarantee to product-managed propagation and the supported relay —
    truthfully prevents accidental injection/logging / does not defend against a hostile
    same-UID worker independently reading user files.
- **Decided:** Take option C. The daemon is the only product component that receives,
  persists, and uses captured credentials, and Codex children have socket/token variables
  scrubbed. No product JSON, prompt, log, recovery action, or initialization text exposes
  those values. Independent same-UID filesystem discovery remains governed by the
  existing worker access mode and is outside this feature's threat boundary.
- **Rests on:** the operator-approved full/read-only access behavior and D11/D15.
- **Affects:** R6, security narrative, tests, documentation, and threat-model claims.
- **Revisit-when:** Codex workers gain a real per-process filesystem sandbox.

## D24 — Validate skill guidance with focused structure plus semantic reviewers
**When:** 2026-08-20T09:52:00Z · **Phase:** plan · **Status:** locked
**Decided by:** Tadas (earlier documentation-testing direction), recorded by Codex

- **Trigger:** Product integration updates the existing SDD skill/reference, while the
  operator explicitly rejected a large test-driven documentation campaign and preferred
  small reviewer agents at documentation checkpoints.
- **Options weighed:**
  - A: run the writing-skills multi-scenario RED/GREEN pressure campaign — strongest
    behavioral evidence / spends many agent calls on a narrow reference addition.
  - B: make unreviewed prose edits — cheapest / risks teaching an ambiguous or incorrect
    callback command.
  - C: retain focused structural integration checks and dispatch fresh semantic reviewer
    agents after the guidance checkpoint — checks exact command/behavior comprehension /
    does not claim a full behavior-shaping eval.
- **Decided:** Take option C. Code remains strict TDD. Skill/reference documentation gets
  structural tests plus independent semantic reviewers, not the large pressure campaign.
- **Rests on:** the operator's explicit documentation-testing direction and the fact this
  work extends an existing reference rather than creating a new discipline skill.
- **Affects:** documentation task, evidence labels, release gate.
- **Revisit-when:** callback guidance changes SDD control flow rather than documenting the
  new worker capability.

## D25 — Release the callback CLI as Superdev 7.3.0
**When:** 2026-08-20T09:52:00Z · **Phase:** plan · **Status:** locked
**Decided by:** Codex under autonomous implementation authority

- **Trigger:** The feature adds a top-level `message` command, `start --no-callback`, new
  RPC models/faults, and status fields, so installed users need a versioned plugin refresh.
- **Options weighed:**
  - A: no bump — avoids release files / leaves installed 7.2.0 indistinguishable and stale.
  - B: patch 7.2.1 — small bump / understates a backward-compatible public feature.
  - C: minor 7.3.0 — accurately signals additive CLI/API capability / requires the normal
    manifest, package, reinstall, and audit gates.
- **Decided:** Take option C and use existing release tooling rather than hand-editing
  generated copies.
- **Rests on:** semantic versioning and the established 7.2.0 release workflow.
- **Affects:** release notes, manifests, package tests, installed-plugin evidence.
- **Revisit-when:** implementation removes all public surface changes before release.

## D26 — Isolate product and probe commits in their owning repositories
**When:** 2026-08-20T09:52:00Z · **Phase:** plan · **Status:** locked
**Decided by:** Codex under autonomous implementation authority

- **Trigger:** D14 assigns product code to Superdev and measured probe scripts to the
  trading repository, whose active checkout already contains unrelated human work.
- **Options weighed:**
  - A: edit both active checkouts — simplest paths / risks mixing unrelated dirty state.
  - B: copy probes into Superdev — one branch / violates the source-of-truth boundary.
  - C: use one isolated branch/worktree per repository and commit only owned paths —
    preserves ownership and dirty work / requires a two-commit handoff.
- **Decided:** Take option C. The Superdev feature branch consumes the probe commit as a
  recorded evidence SHA/path rather than copying its scripts.
- **Rests on:** D14 and the operator's established worktree preference.
- **Affects:** task working directories, reports, finishing handoff, cleanup.
- **Revisit-when:** the transport probes move into a supported shared package.

## D27 — Make Claude's outer message identity stable and origin-addressed
**When:** 2026-08-20T09:58:00Z · **Phase:** plan · **Status:** locked
**Decided by:** Codex under autonomous implementation authority

- **Trigger:** D16 stabilizes the callback event ID but the measured Claude envelope also
  has `uuid`, `msg_id`, and optional `from`; leaving them regenerated or ambiguous would
  weaken duplicate correlation and alternate-room provenance.
- **Options weighed:**
  - A: regenerate every outer field per attempt and omit `from` — simplest sender /
    duplicate attempts look unrelated and an override loses origin provenance.
  - B: persist opaque full wire bytes — exact replay / couples durable state to Claude's
    current private envelope schema.
  - C: rebuild the measured envelope deterministically from the durable event — stable
    correlation without persisting auth frames / requires a fixed UUID derivation.
- **Decided:** Take option C. Set Claude `msg_id` to the callback `event_id`, derive its
  `uuid` deterministically with UUIDv5 from that event ID, set `from` to the captured
  origin socket as `uds:<path>` even for a one-send override, attest
  `from_mode:"bypass"`, and omit `session_id`. The callback JSON also carries event ID.
- **Rests on:** D16, D19 and the MEASURED 2.1.237 user envelope.
- **Affects:** transport encoder, duplicate tests, probe parity, alternate-target ride.
- **Revisit-when:** Claude documents first-class idempotency or sender identity fields.

## D28 — Pin callback UUID identity and omit nonexistent origins
**When:** 2026-08-20T10:21:00Z · **Phase:** plan · **Status:** locked
**Decided by:** Codex after independent plan review

- **Trigger:** D27 did not name its UUIDv5 namespace and assumed every permitted override
  had a captured origin socket, but D21 explicitly permits a root-only unavailable
  binding to send to one named target.
- **Options weighed:**
  - A: let each repository choose a namespace and use the target as `from` when origin is
    absent — locally deterministic / breaks cross-repository parity and misstates sender.
  - B: reject root-only overrides — keeps D27 literal / violates D21 and the public CLI.
  - C: pin one literal namespace and omit only the impossible origin field — gives stable
    cross-repository IDs and honest provenance / root-only sends have no reply address.
- **Decided:** Take option C. The namespace is
  `5b290fd0-2df0-5c73-980f-04f284476f55`, itself UUIDv5(NAMESPACE_URL,
  `codex-worker.claude-callback/v1`). Event `event-fixture-1` must map to
  `740cb30c-652d-5f4f-bc30-36c14a48d007`. Enabled bindings always preserve their captured
  origin in `from`, including overrides. Root-only unavailable overrides omit `from`,
  retain `from_mode:"bypass"`, and never substitute the destination socket. All sends
  omit `session_id`.
- **Rests on:** D21, D27 and the measured optional `from` field.
- **Affects:** transport encoder, unavailable override, probe parity, tests, checkride.
- **Revisit-when:** Claude makes sender/reply identity mandatory or provides a supported
  daemon identity.

## D29 — Update exhaustive contract consumers with the model seam
**When:** 2026-08-20T10:38:00Z · **Phase:** build · **Status:** locked
**Decided by:** Codex during Task 1 review

- **Trigger:** Task 1's planned closed fault/status additions made legacy exhaustive
  assertions in `test_rpc_cli.py` and `test_facade.py` fail, although the task's initial
  owned-file list named only `commands.py` and `test_commands.py`.
- **Options weighed:** leave the fast gate red and document it; weaken the exhaustive
  assertions; or update the exact consumers alongside the additive contract.
- **Decided:** Update the two exhaustive consumers in the same Task 1 commit. They pin
  the new public contract and preserve the fast-gate invariant; no extra production
  behavior or interface was introduced.
- **Rests on:** Task 1's exact `-32031..-32037` mapping and additive callback status.
- **Affects:** Task 1 file boundary and its review package only.
- **Revisit-when:** contract tests move to generated schema enumeration.

## D30 — Separate terminal projection, persistence, and shutdown ownership
**When:** 2026-08-20T12:24:00Z · **Phase:** build · **Status:** locked
**Decided by:** Codex after Task 4 concurrency review

- **Trigger:** The initial dispatcher coupled terminal observation, public projection,
  and durable persistence. Review exposed predecessor loss, notification-thread blocking,
  divergent completion metrics, shutdown stranding, and total-store-outage blocking.
- **Options weighed:** keep persistence on one dispatcher thread; move all persistence to
  request threads; or coordinate projection and persistence as separate once-only claims
  with bounded fallback.
- **Decided:** Use separate per-turn ownership. Runtime retains bounded exact snapshots
  and publishes copy-isolated notifications; request or dispatcher may create the one
  authoritative projection, while a healthy dispatcher alone owns normal persistence and
  retry. Stopped/exited/shutdown fallback makes one enqueue plus one redacted-fault
  attempt. Total store outage returns the unchanged completion and emits safe structured
  non-durable evidence without claiming recovery. Cleanup follows a durable boundary or
  explicit non-durable abandonment, never worker state alone.
- **Rests on:** R3, R7, R8 and D7/D16's honesty boundary.
- **Affects:** Task 4 dispatcher/runtime/facade, shared `models.copy_turn_snapshot`,
  callback-store `record_terminal_fault`, lifecycle tests, and RPC fault pin.
- **Revisit-when:** callback persistence moves to a separate process or gains a
  transactional acknowledgment with the Codex turn store.

## D31 — Use the trading repository's ignored worktree root for probes
**When:** 2026-08-20T13:54:00Z · **Phase:** build · **Status:** locked
**Decided by:** Codex during Task 6 preflight

- **Trigger:** The planned trading path `.worktrees/codex-worker-callback-probes` was not
  ignored, while the active checkout already contained unrelated operator work.
- **Options weighed:** create the unignored path; edit `.gitignore`; or use the repository's
  established ignored `.claude/worktrees` root.
- **Decided:** Use `.claude/worktrees/codex-worker-callback-probes` on the same planned
  branch. This preserves isolation without adding an unrelated ignore-policy change.
- **Rests on:** D26 and the verified `.git/info/exclude` worktree convention.
- **Affects:** Task 6 worktree/report paths only; source ownership and commit boundaries
  are unchanged.
- **Revisit-when:** the repository adopts a tracked project-level `.worktrees` policy.

## D32 — Ignore Claude idle registry records with no messaging endpoint
**When:** 2026-08-20T14:20:00Z · **Phase:** build · **Status:** locked
**Decided by:** Codex during Task 8 real-Claude acceptance

- **Trigger:** Claude Code 2.1.237 retained a live `interactive` registry record with
  `status: idle` and no `messagingSocketPath`. Treating that non-addressable record as
  malformed blocked capture for an unrelated valid live caller.
- **Options weighed:** fail the entire registry scan; mutate Claude-owned state; or ignore
  only a structurally valid idle record whose endpoint field is absent/null.
- **Decided:** Ignore only records with positive `pid`, non-empty `sessionId` and
  `procStart`, `kind: interactive`, `status: idle`, and absent/null
  `messagingSocketPath`. Continue rejecting malformed JSON, unsafe files, and all other
  incomplete records. The ignored record can never be selected or sent to.
- **Rests on:** MEASURED Claude Code 2.1.237 registry shape and R6/R9 fail-closed routing.
- **Affects:** registry scanning only; target validation, exact-match capture, and named
  override ambiguity remain unchanged.
- **Revisit-when:** Claude removes idle records or documents a different non-addressable shape.

## D33 — Normalize Claude UTC process-start records against local `ps`
**When:** 2026-08-20T14:24:00Z · **Phase:** build · **Status:** locked
**Decided by:** Codex during Task 8 real-Claude acceptance

- **Trigger:** MEASURED Claude Code 2.1.237 registry `procStart` is UTC while macOS
  `ps -o lstart=` renders local time. In Europe/Vilnius the same PID differed by exactly
  three hours and every real capture falsely refused as PID reuse.
- **Options weighed:** remove the process-start check; compare the strings literally; or
  parse the fixed timestamp shape and convert the registry UTC value to local time.
- **Decided:** Preserve exact-match support, otherwise parse both fixed English timestamp
  shapes and compare Claude's UTC instant rendered in the current local zone. Parse
  failures remain mismatches. PID, session, endpoint, and socket-inode checks remain.
- **Rests on:** MEASURED live registry/`ps` pairs and R6/R9 PID-reuse defense.
- **Affects:** capture revalidation and named-target liveness only.
- **Revisit-when:** Claude includes an explicit timezone/epoch or macOS exposes a stable
  process birth epoch through the supported stdlib boundary.

## D34 — Expose explicit managed-daemon start and keep envelope sizing daemon-owned
**When:** 2026-08-20T15:15:00Z · **Phase:** checkride · **Status:** locked
**Decided by:** Codex after independent CLI checkride evaluation

- **Trigger:** A stopped `message` correctly avoided implicit startup but offered no
  non-turn-producing recovery, while an added client-side Unicode estimate bypassed
  D14's daemon-owned final-envelope sizing and lost worker-aware recovery context.
- **Options weighed:** autostart `message`; require operators to manage foreground
  `daemon serve`; or add an explicit managed lifecycle action and preserve the daemon
  as the only final-envelope size authority.
- **Decided:** Add `codex-worker [--instance <id>] daemon start`. It invokes the existing
  safe/idempotent managed startup path, returns one `DaemonStatusResponse`, and starts no
  worker turn. Stopped common-command refusals point to it. Remove the proactive client
  UTF-16 shortcut; local file/argument validation remains client-owned, while the daemon
  sizes the serialized Claude user line and returns worker-aware `-32037` recovery. The
  local RPC request bound is 8 MiB so the largest permitted UTF-16 message and a modestly
  oversized refusal probe can reach that check even under Python's six-byte JSON escapes;
  the response bound remains independently capped at 1 MiB.
- **Rests on:** D14, D23, R7, and the non-destructive managed lifecycle contract.
- **Affects:** CLI parser/managed lifecycle, stopped-daemon next actions, Unicode ride,
  CLI companion, and checkride recovery evidence.
- **Revisit-when:** the callback relay becomes a process independent of the Codex daemon.
