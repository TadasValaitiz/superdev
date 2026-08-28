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
