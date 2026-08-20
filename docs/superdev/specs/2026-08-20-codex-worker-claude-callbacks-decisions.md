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
**When:** 2026-08-20T08:04:41Z · **Phase:** brainstorm · **Status:** locked
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
