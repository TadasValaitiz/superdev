# Codex worker global install — Decision log

**Design doc:** ./2026-08-28-codex-worker-global-install-design.md
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — Install a standalone user command
**When:** 2026-08-28T05:13:02Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** Invoking the repository launcher required a long absolute path and the
  operator requires Claude Code to use `codex-worker` directly from any working
  directory.
- **Options weighed:**
  - A: Keep invoking the plugin or checkout launcher by absolute path — gains no new
    packaging / sacrifices the intended short global command and couples every call to
    source layout.
  - B: Install a standalone user command and runtime — gains stable PATH usage and
    independence from a versioned plugin-cache location / sacrifices a small install
    and update mechanism.
- **Decided:** B. The plugin carries the installation source, but ordinary calls use
  only the installed `codex-worker` command.
- **Rests on:** stated operator requirement.
- **Affects:** R1–R3, spec §5.1–§5.3, installer, and the subagent-driven-development
  Codex-worker preflight.
- **Revisit-when:** a platform-native package manager becomes the canonical Superdev
  distribution mechanism.

## D2 — Skill preflight installs only when needed
**When:** 2026-08-28T05:13:02Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** Claude Code must not need an operator-run setup step before using a
  Codex worker.
- **Options weighed:**
  - A: Document a manual prerequisite — gains simpler skill logic / sacrifices
    first-use reliability.
  - B: Have the skill run a short preflight and invoke the bundled installer when the
    command is absent — gains zero-friction first use / sacrifices one bounded mutation
    during preflight.
- **Decided:** B. After preflight, every example and operation invokes the installed
  command, never the plugin-relative worker launcher.
- **Rests on:** stated operator requirement.
- **Affects:** R2–R4, spec §5.2, `skills/subagent-driven-development/`.
- **Revisit-when:** installs must be centrally administered or user-level writes are
  prohibited.

## D3 — Use UV's persistent tool environments
**When:** 2026-08-28T05:26:18Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The operator identified UV's tool-management surface as the appropriate
  way to make a Python CLI globally available without sharing project or system Python
  dependencies.
- **Options weighed:**
  - A: Copy the runtime with a POSIX shell installer — gains no packaging dependency /
    sacrifices isolated dependency management, upgrades, audit, and standard entry
    points.
  - B: Package the worker and install it with `uv tool install` — gains an isolated
    interpreter/environment and standard lifecycle / sacrifices a required UV
    prerequisite and Python package metadata.
- **Decided:** B. The installed command is a real Python tool with its own dependency
  declaration. The external `codex` executable remains a PATH dependency because it is
  not a Python library.
- **Rests on:** stated operator requirement and measured local UV 0.11.5 availability.
- **Affects:** R1–R6, spec §5.1–§5.4, package metadata and skill preflight.
- **Revisit-when:** UV drops persistent tool environments or Superdev adopts another
  cross-harness tool manager.

## D4 — Keep the distributable source inside the shipped skill payload
**When:** 2026-08-28T05:26:18Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** agent, derived from packaging evidence

- **Trigger:** The Codex plugin packager archives `.codex-plugin`, assets, README,
  LICENSE, and `skills/`, but excludes a repository-root `tools/` tree.
- **Options weighed:**
  - A: Move the package to repository-root `tools/` and expand every plugin packaging
    path — gains conventional repository layout / sacrifices a much broader packaging
    migration and raises distribution-drift risk.
  - B: Add package metadata beside the existing runtime under the shipped
    `skills/subagent-driven-development/scripts/` tree — gains one canonical runtime
    already included in every plugin payload / sacrifices the conventional top-level
    package location.
- **Decided:** B. UV copies the package into its own persistent environment, so the
  installed command has no runtime dependency on the plugin-cache path even though that
  path is its installation source.
- **Rests on:** measured `scripts/package-codex-plugin.sh` archive allowlist and current
  runtime layout.
- **Affects:** R2, R4, R6, spec §5.1 and §5.4.
- **Revisit-when:** the standalone worker is published from its own repository or
  registry package.

## D5 — Bind compatibility to the shipping Superdev version
**When:** 2026-08-28T05:33:25Z · **Phase:** spec ·
**Status:** locked
**Decided by:** agent, closing independent spec-review finding

- **Trigger:** “Compatible” was undefined, so preflight could retain a worker whose
  runtime contract differed from the skill instructing it, or unpredictably downgrade a
  newer executable.
- **Options weighed:**
  - A: Accept any installed worker that answers `--version` — gains fewer reinstalls /
    sacrifices deterministic skill/runtime compatibility.
  - B: Require exact equality between the worker distribution version and the loaded
    Superdev manifest version — gains one authoritative compatibility rule / sacrifices
    retaining an independently newer worker on PATH.
- **Decided:** B. The shipping manifest and Python distribution versions must match.
  Preflight replaces an older or newer UV-owned worker with the loaded plugin's bundled
  package. A same-named executable outside UV's tool bin is a PATH-shadowing refusal,
  not an overwrite target.
- **Rests on:** R3, R6, R7 and the plugin/runtime behavioral coupling.
- **Affects:** spec §5.1–§5.3 and CLI `--version`/preflight contracts.
- **Revisit-when:** `codex-worker` gains an independently versioned compatibility API
  or registry release cadence.

## D6 — Resolve install source from the loaded skill trust anchor
**When:** 2026-08-28T05:33:25Z · **Phase:** spec ·
**Status:** locked
**Decided by:** agent, closing independent spec-review finding

- **Trigger:** `CLAUDE_PLUGIN_ROOT` is present in Claude Code but is not a portable
  assumption for every harness that can load this filesystem-backed skill.
- **Options weighed:**
  - A: Require `CLAUDE_PLUGIN_ROOT` — gains a single environment lookup / sacrifices
    Codex and other filesystem-backed harness support.
  - B: Use `CLAUDE_PLUGIN_ROOT` when present and otherwise derive the root from the exact
    `SKILL.md` locator supplied by the harness — gains cross-harness determinism /
    sacrifices a small documented resolution branch.
- **Decided:** B. The resolved real path must contain the loaded skill, a Superdev
  manifest, and the bundled package metadata before it is trusted as an install source.
- **Rests on:** measured `hooks/session-start` Claude root contract and filesystem skill
  locators supplied by this harness.
- **Affects:** R3, R7, spec §5.2 and skill preflight.
- **Revisit-when:** all supported harnesses expose one standardized plugin-root variable.

## D7 — Make preflight an executable policy boundary
**When:** 2026-08-28T05:44:24Z · **Phase:** plan ·
**Status:** locked
**Decided by:** agent

- **Trigger:** Encoding path ownership, version comparison, UV invocation, and recovery
  only as prose would make the skill behavior untestable and invite divergent shell
  snippets across agents.
- **Options weighed:**
  - A: Put the shell sequence inline in `codex-worker.md` — gains no extra file /
    sacrifices one canonical testable implementation and concise skill instructions.
  - B: Ship an internal `install-codex-worker` preflight executable beside the package —
    gains one hardened policy boundary and short skill invocation / sacrifices one
    internal script to maintain.
- **Decided:** B. The skill runs this internal preflight once before its first worker
  command; the script self-resolves and validates its plugin root, and only normal
  operations use the globally installed executable.
- **Rests on:** R3, R7 and the repository's existing executable-script pattern.
- **Affects:** spec §5.2, Task 2, skill runbook.
- **Revisit-when:** UV exposes a declarative tool manifest that performs equivalent
  ownership/version/source checks.

## D8 — Store package version in PEP 621 metadata and teach release tooling TOML
**When:** 2026-08-28T05:44:24Z · **Phase:** plan ·
**Status:** locked
**Decided by:** agent

- **Trigger:** Preflight must read the expected version without importing an uninstalled
  package or requiring global Python, while the existing release tool updates JSON only.
- **Options weighed:**
  - A: Add a second plain version file or Python constant — gains simple shell reading /
    sacrifices a second authoritative mirror and custom build indirection.
  - B: Use static PEP 621 `project.version` as the tool authority and extend the existing
    version-bump configuration/tool for a narrowly parsed TOML field — gains one package
    authority and normal wheel metadata / sacrifices a small release-tool extension.
- **Decided:** B. `codex-worker --version` reads installed distribution metadata;
  source-launcher fallback reads the same project metadata only for development. Release
  checks require exact equality with all plugin manifests.
- **Rests on:** D5 and the existing `.version-bump.json` controlled-file mechanism.
- **Affects:** Task 1, Task 4, package metadata and release scripts.
- **Revisit-when:** the worker adopts an independently versioned registry release.

## D9 — Use hatchling as the wheel build boundary
**When:** 2026-08-28T05:53:39Z · **Phase:** plan ·
**Status:** locked
**Decided by:** agent

- **Trigger:** A PEP 517 backend must turn the existing package directory into a wheel
  with a console entry point and an explicit package allowlist.
- **Options weighed:**
  - A: setuptools — gains maximum historical familiarity / sacrifices more discovery
    configuration around the mixed scripts directory and commonly arrives from the
    ambient interpreter rather than the selected UV toolchain.
  - B: hatchling — gains concise PEP 621 support, explicit wheel package selection, and
    isolated build requirements resolved by UV / sacrifices one build-only dependency.
- **Decided:** B with `hatchling>=1.27,<2`. It is build-time only; the installed worker
  retains `dependencies = []` and standard-library runtime behavior.
- **Rests on:** D3, D4, R4–R6 and UV's PEP 517 build contract.
- **Affects:** Task 1 package metadata and Task 3 wheel/package checks.
- **Revisit-when:** hatchling drops Python 3.9-source build support or the tool moves to
  a dedicated repository with another established backend.

## D10 — Probe the external Codex prerequisite through explicit daemon start
**When:** 2026-08-28T06:45:31Z · **Phase:** build ·
**Status:** locked
**Decided by:** human

- **Trigger:** Task 2's planned negative probe said `model list` in an isolated managed
  instance should produce `daemon_start_failed` when external `codex` is absent.
  Measured runtime behavior showed that `model list` is an RPC-only read: it does not
  autostart a stopped managed daemon and correctly returns `daemon_unavailable`.
- **Options weighed:**
  - A: Make `model list` autostart — would satisfy the original test route / sacrifices
    established read-only lifecycle semantics and creates an unrequested public change.
  - B: Preserve `model list` semantics and drive `--instance X daemon start` — exercises
    the existing explicit lifecycle boundary and its typed start refusal / sacrifices
    the original test command only.
- **Decided:** B. The external-prerequisite negative uses explicit managed daemon start,
  requires one actionable `daemon_start_failed` JSON object, and leaves `model list`
  RPC-only.
- **Rests on:** measured CLI behavior, D1, R5–R7, and the existing command-ergonomics
  lifecycle contract.
- **Affects:** Task 2 test route and evidence only; no public CLI surface changes.
- **Revisit-when:** managed read commands deliberately adopt autostart semantics.

## D11 — Resume a durable mapping before post-reinstall status
**When:** 2026-08-28T07:23:03Z · **Phase:** build ·
**Status:** locked
**Decided by:** human

- **Trigger:** The planned upgrade recipe called `status --name` immediately after a
  reinstall and daemon restart. Measured behavior proved that durable registry bytes,
  session ID, and thread ID survive, while the fresh daemon intentionally has no runtime
  attachment for that worker; direct status therefore returns `daemon_stopped`.
- **Options weighed:**
  - A: Change status to load or reattach detached mappings — would make the original
    test route pass / sacrifices the established read-only lifecycle semantics.
  - B: Preserve lifecycle semantics and deliberately call `run --name` to resume and
    reattach the existing mapping before status — proves continuity through the public
    resume path / costs one short real continuation in the live proof.
- **Decided:** B. The durable-reinstall scenario first proves the registry file bytes
  survived replacement, then runs one short continuation under the same name, requires
  exact session/thread ID equality, and only then reads status.
- **Rests on:** measured daemon restart behavior, D4, D10, and the existing common-command
  resume contract.
- **Affects:** Task 3 evidence route and CLI §3 upgrade recipe only; no public CLI change.
- **Revisit-when:** detached mappings gain a separately designed read-only inspection
  surface.

## D12 — Fail closed across cached-plugin and managed-runtime version skew
**When:** 2026-08-28T12:30:00Z · **Phase:** build ·
**Status:** locked
**Decided by:** human, closing final review findings

- **Trigger:** A UV reinstall replaces one mutable global command, while older Claude
  rooms and already-running managed daemons can retain a different Superdev version.
  The original preflight proved executable identity only, so either mismatch could be
  used silently.
- **Options weighed:**
  - A: Namespace every executable by version — supports simultaneous skew / violates the
    required plain `codex-worker` surface and overbuilds the current release boundary.
  - B: Keep automatic trusted-root repair, but fail every operational invocation whose
    `CLAUDE_PLUGIN_ROOT` manifest differs from the installed distribution and require an
    exact managed-daemon version handshake — preserves zero-friction upgrades and the
    plain command / does not promise simultaneous operation of skewed cached rooms.
- **Decided:** B. `--version` remains a daemon-free diagnostic. Every other invocation
  with `CLAUDE_PLUGIN_ROOT` must exactly match that loaded manifest before runtime
  contact or return typed `tool_version_mismatch` (`-32038`) with coordination and
  trusted-preflight recovery. Preflight may still automatically replace an older or
  newer UV-owned tool; operators must understand that doing so coordinates the single
  global version. A selected managed daemon reports its distribution version: an exact
  peer is reused, while an incompatible peer is gracefully stopped and respawned under
  the selected instance lock. Durable state is preserved; unrelated instances and raw
  socket lifecycles are not stopped.
- **Rests on:** D1–D5, D11, one mutable UV tool, and per-room `CLAUDE_PLUGIN_ROOT`.
- **Affects:** spec §5.2–§5.3, CLI §1/§3, skill preflight, managed daemon readiness.
- **Revisit-when:** simultaneous operation across different cached Superdev versions is
  required, or a separately versioned compatibility protocol replaces exact equality.
