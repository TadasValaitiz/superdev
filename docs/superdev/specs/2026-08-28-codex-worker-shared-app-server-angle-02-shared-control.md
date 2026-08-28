# Angle 2 — Worker and terminal share authoritative control

**Purpose:** Understand how Codex Worker automation and a human Codex TUI can observe and control the same thread without a lease protocol.
**Authority:** teaches ruled design — the decision log is the law.
**Formal anchors:** [decision log](./2026-08-28-codex-worker-shared-app-server-decisions.md) D1, D4, D12, D13, D16, D17 · [design §5.2 and §5.4](./2026-08-28-codex-worker-shared-app-server-design.md)
**Series:** 2 of 4

> **Status guide:** LOCKED operator-ruled · MISMATCH current code behaves differently today · FLEXIBLE implementation detail may move inside the ruled boundary · DEFERRED explicitly owned by another design.

## The central question

When a human terminal and Claude-driven worker both attach to one Codex thread, who is allowed to act and who decides a race?

## The mental model

The app-server is a multiplayer event authority behind a transparent lobby door. Every client
gets a one-to-one backend connection and its own subscription, but all operations address the
same server-owned thread and turn state. The lobby can briefly stop new work for maintenance;
it cannot rewrite a conversation result.

It is not:

- screen sharing of one terminal process;
- a read-only observer attached to a private worker;
- a human-control lease that pauses Claude automatically;
- two independent conversation copies reconciled later;
- last-writer-wins logic invented by Codex Worker.

## Boundaries

This angle owns subscriptions, observations and control races. Angle 1 owns the process and
listener. Angle 3 owns how the thread ID is exposed. Angle 4 owns shutdown safety. Automatic
social arbitration between human and Claude is intentionally outside the product; the user
orchestrates the handoff.

## Concrete journey

### LOCKED — every connection can subscribe to the same thread

Codex Worker initializes a WebSocket connection and starts a thread. A human runs the printed
`codex --remote ... resume <thread_id>` command. The TUI initializes independently and resumes
the existing thread, which subscribes that connection to its events.

A measured two-client probe against Codex 0.147 showed both initialized WebSocket clients
receiving the same turn events and completion after the second client resumed the thread.
This is **MEASURED** development evidence, not a compatibility promise beyond the pinned
Codex contract.

**This means:** observation does not require polling the worker, attaching does not clone the
conversation, and either client can see subsequent authoritative events.

### LOCKED — both sides have full control

The TUI and worker may each start a follow-up, steer, or interrupt. Codex Worker captures the
turn ID it intended to control and sends that operation to the shared app-server. If another
client already changed the state, the app-server response wins.

**This means:** no local lock pretends to outrank Codex; a stale worker cannot accidentally
steer a successor turn; and ordinary races become typed `turn_active` or `turn_not_active`
outcomes rather than hidden reconciliation.

### FLEXIBLE — event fan-out can reconnect without changing authority

The worker may use one reconnecting transport per service or a managed set of connections.
Subscription restoration must be explicit after reconnect. **This means:** transport recovery
can change while thread identity and server authority remain fixed.

### FLEXIBLE — a maintained WebSocket library carries the framing contract

The isolated UV tool installs the Python-3.9-compatible `websockets` sync client/server rather
than hand-rolling masks, fragmentation, ping/pong, close and bounded frames. A measured isolated
Python 3.9.6 probe imported both sides with websockets 15.0.1. **This means:** the gateway can
remain small and protocol-focused, dependency drift is contained inside the UV tool, and every
upgrade repeats the live two-client lane.

### FLEXIBLE — overload never replays a mutation

Codex WebSocket mode may refuse ingress with `-32001`. Reads use bounded backoff and jitter.
An overloaded initialize closes the connection; a new connection gets exactly one fresh
initialize/initialized handshake. A mutation returns busy without replay. **This means:** a
retry cannot create a duplicate turn, and connection initialization never happens twice on one
transport.

### FLEXIBLE — the gateway closes the maintenance race

The public gateway accepts `ws://HOST:PORT`; the Codex child remains on a private Unix-WebSocket.
During maintenance it blocks new/unknown mutating requests, waits already-forwarded mutations,
then pages `thread/list` across every source. Client responses needed by active approvals and
interrupt/read operations still pass. **This means:** a TUI-created thread is included even
without a worker record, and ordinary stop cannot race a new public turn.

```text
worker RPC ─ broker private WS ─┐
                                ├─ private Codex app-server authority
Codex TUI ─ public WS gateway ──┘

drain: close mutation gate -> settle forwarded mutations
       -> page all threads -> active? refuse : maintain service
```

## What shared control cannot do

It cannot prevent a human and Claude from issuing contradictory instructions, determine which
intent is wiser, or guarantee both commands succeed. It does not transfer callback ownership,
Claude room identity, or filesystem cwd merely because the TUI attached. It does not terminate
TLS or make a non-loopback plain-WebSocket listener safe.

## Current mismatch

Today the worker exclusively owns a stdio app-server subprocess, so a separate Codex TUI
cannot attach to the same transport. **SALVAGE:** keep authoritative event normalization,
expected-turn checks, durable cursors and typed race faults; replace only the private transport.

## Visible collisions

- Convenience versus arbitration: full shared control wins; the human coordinates the turn-taking.
- Reconnection versus missed events: durable status/history projections close gaps after resubscription.

## Flexible and deferred

**FLEXIBLE:** reconnect backoff, subscription bookkeeping, and internal client count metrics.
**DEFERRED, with landing places:** an optional control lease belongs to a future collaboration-policy design only if real use demonstrates harmful races.

## Reconciled outcome

Two LOCKED control laws and four FLEXIBLE transport seams give the human and automation equal
access while keeping Codex app-server state authoritative.
