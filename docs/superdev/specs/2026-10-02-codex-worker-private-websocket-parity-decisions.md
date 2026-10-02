# Codex worker private WebSocket parity — Decision log

**Design doc:** ./2026-10-02-codex-worker-private-websocket-parity-design.md
**Authority:** THE LAW of this work stream — rulings here outrank every other document's prose.
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — The managed Codex child uses a private TCP WebSocket endpoint
**When:** 2026-10-02T06:41:05Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; selected private WebSocket transport with an optional explicit URL and a collision-free default)

- **Trigger:** the direct `codex app-server --listen ws://127.0.0.1:4501` comparison remains stable with plugins enabled, while the worker's Unix-WebSocket path crosses a bounded Python gateway and reconnects on the oversized plugin catalog. “Make parity with ws” was ambiguous between changing only the private child transport and deleting the service gateway.
- **Options weighed:**
  - A: retain the private `unix://` child and only raise gateway frame limits — gains the smallest topology change / sacrifices WebSocket parity and preserves Unix-specific readiness and compatibility machinery.
  - B: start the managed child on a fixed private loopback `ws://127.0.0.1:<configured-port>` — gains native WebSocket behavior and direct HTTP health routes / sacrifices collision freedom and introduces another fixed port operators must coordinate.
  - C: start the managed child on an automatically allocated private loopback WebSocket endpoint, with an optional explicit URL — gains native WebSocket behavior without a default fixed-port collision / sacrifices Unix filesystem ownership as the private-authority proof and requires a race-safe reservation/handoff design.
  - D: expose the Codex child directly on the public listener and remove the gateway — gains exact native app-server surface parity / sacrifices the maintenance gate, mutation drain, public collision authority, and supervised lifecycle guarantees.
- **Decided:** C. The worker continues to own the public gateway and managed Codex lifecycle, but its backend is a native loopback TCP WebSocket endpoint. The default endpoint is allocated so concurrent or unrelated local services cannot clash; an operator may explicitly supply a URL. The gateway remains because the observed transport defect does not invalidate its maintenance and ownership responsibilities.
- **Not public direct exposure:** the child endpoint is a private backend. Human clients still attach through the service's configured public listener unless a later explicit design ruling adds a separately projected diagnostic route.
- **Extension law:** every backend-listener strategy must define allocation, readiness, ownership, collision behavior, status projection, shutdown authority, and how the gateway/broker connect to the same endpoint.
- **Anti-patterns:** no hard-coded second default port; no bind-to-port-zero followed by close-and-rebind race presented as collision-free; no silent fallback when an explicit URL collides; no removal of the maintenance gate as a transport workaround.
- **Rests on:** operator selection in this session; MEASURED stable direct 4501 comparison; MEASURED 4 MiB worker cap versus 12,045,587-byte `plugin/list`; READ prior D17 gateway safety boundary.
- **Affects:** `GlobalWorkerService` startup/readiness/teardown, backend connector validation, service paths/status, tests, documentation, and the future pipelines companion.
- **Revisit-when:** Codex provides a race-free inherited-listener/file-descriptor API or the service gateway is replaced by an equally explicit maintenance/ownership boundary.

## D2 — Use Codex's native remote Agent command center with service-local scope
**When:** 2026-10-02T06:41:57Z · **Phase:** brainstorm · **Status:** locked
**Decided by:** operator (live, in-session; accepted native remote agent browsing and confirmed that inventory is scoped to the connected service)

- **Trigger:** the normal local Codex view exposed the Agent command center while an ordinary remote chat did not show an equivalent inline option, creating ambiguity about whether remote agent browsing existed and whether all machine-wide agents had to appear together.
- **Options weighed:**
  - A: add a custom `codex-worker agents` UI and aggregate every local service — gains one machine-wide list / sacrifices native UX and incorrectly merges independently owned app-server inventories.
  - B: use `codex --remote <service-url> agents` and show only that app-server's agents — gains the native command center and preserves service ownership boundaries / requires operators to invoke the `agents` subcommand explicitly.
  - C: proxy another service's inventory into the connected service — gains a larger apparent list / sacrifices truthful ownership and risks opening threads through the wrong authority.
- **Decided:** B. The measured direct command opened the native Agent command center and reported 12 tasks; the operator confirmed that a different service's 22-task inventory should remain separate. WebSocket parity must preserve native service-local browse/open/resume behavior. No custom agent CLI is required.
- **Not machine-wide aggregation:** “all agents” means all agents on the connected WebSocket/app-server service, not every agent in every local daemon.
- **Extension law:** every projected remote-agent command must carry the exact service listener and must not combine inventories from distinct app-server authorities.
- **Anti-patterns:** no terminal scraping, cross-service thread merging, or custom duplicate command center while the native `agents` subcommand satisfies the requirement.
- **Rests on:** MEASURED `codex --remote ws://127.0.0.1:4501 agents` command-center probe; operator confirmation that 12 versus 22 is the correct service boundary; READ gateway allowance for `thread/list` and `thread/loaded/list`.
- **Affects:** acceptance tests and attach/status documentation; no new inventory domain or CLI family.
- **Revisit-when:** the native remote command omits an agent owned by the same connected app-server service or cannot browse/open/resume one it lists.
