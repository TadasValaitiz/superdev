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
