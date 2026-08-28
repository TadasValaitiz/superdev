# Angle 1 — One service owns the machine-local Codex substrate

**Purpose:** Understand why every worker and terminal attaches to one long-lived service instead of creating per-Claude daemons.
**Authority:** teaches ruled design — the decision log is the law.
**Formal anchors:** [decision log](./2026-08-28-codex-worker-shared-app-server-decisions.md) D1, D3, D5, D6, D17 · [design §5.1](./2026-08-28-codex-worker-shared-app-server-design.md)
**Series:** 1 of 4

> **Status guide:** LOCKED operator-ruled · MISMATCH current code behaves differently today · FLEXIBLE implementation detail may move inside the ruled boundary · DEFERRED explicitly owned by another design.

## The central question

Who owns the Codex app-server when many unrelated Claude sessions and human terminals need it at the same time?

## The mental model

Treat the app-server like a local database service, not like a temporary subprocess attached
to one query. Clients come and go; the service retains the conversations they address.

It is not:

- a child daemon whose lifetime follows a Claude session;
- one server per worker name;
- a pool that silently chooses any free port;
- a terminal UI subprocess owned by Codex Worker;
- an excuse to stop other processes found at the default address.

## Boundaries

This angle owns process lifetime, listener selection and client independence. Angle 2 owns
control races after clients connect. Angle 3 owns public identities. Angle 4 owns upgrades,
stops and legacy migration. Host firewall and TLS deployment remain outside this internal
tool design.

## Concrete journey

### LOCKED — ordinary work ensures one global service

A caller runs `codex-worker start`. The client validates its request, resolves the single
global runtime, and under one lifecycle lock either reuses an exact-ready service or starts
one Codex app-server on a private Unix-WebSocket plus a public gateway at
`ws://127.0.0.1:4500`. The broker uses a private initialized connection; the human TUI uses
the gateway.

**This means:** five callers can arrive concurrently without producing five servers; a caller
exit cannot tear down another caller's work; and the first successful start establishes the
listener for that live generation.

### LOCKED — the default address is deterministic, not opportunistic

If the default port is occupied by an unverified peer, startup returns a typed
`address_in_use` refusal. It neither kills the peer nor falls back to 4501. A deliberate,
connectable `ws://HOST:PORT` override is bound exactly by the service gateway before this
generation starts; Codex stays on its private Unix-WebSocket.

**This means:** the attach route printed to a human is stable, orchestration never has to
discover a randomly selected port, and an occupied address is an operator-visible conflict.

**FLEXIBLE shape around locked ownership:**

```text
Claude shells -> codex-worker Unix RPC -> GlobalWorkerService -> private Codex app-server
Human TUI    -> ws://127.0.0.1:4500 gateway -> one private backend connection ────────┘
```

### FLEXIBLE — supervision mechanics may vary without changing ownership

The process may be spawned by the client manager today and later by a login service. The
public invariant is one durable global service with the same readiness/version/listener
handshake. **This means:** implementation can evolve without bringing back per-session
lifetimes.

## What the global service cannot do

It cannot prove a non-loopback listener is safe, provide production multi-tenant isolation,
or preserve two incompatible service binaries simultaneously. It also cannot infer that an
unknown listener peer is safe merely because it responds to WebSocket frames.

## Current mismatch

Today, runtime paths and registries are derived from `--instance` or Claude session identity,
and lifecycle cleanup commonly stops the selected daemon. **SALVAGE:** keep the hardened
Unix RPC client boundary, exact version handshake, durable writes and typed faults; move them
under one global identity.

## Visible collisions

- Stable port versus arbitrary Codex listeners: default stability wins; explicit override is an operator decision.
- Persistent service versus upgrades: Angle 4 permits idle-only automatic replacement.

## Flexible and deferred

**FLEXIBLE:** foreground supervisor implementation, health-probe cadence, and internal Unix socket location.
**DEFERRED, with landing places:** production authentication/TLS belongs to a future deployment-security design if this internal tool becomes network-exposed.

## Reconciled outcome

Two LOCKED ownership rules and one FLEXIBLE supervision seam compose one machine-local
Codex substrate: durable, deterministic, and independent of any Claude room.
