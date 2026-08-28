# Codex worker global install — Design (anchor)

**Date:** 2026-08-28 · **Status:** draft
**Mode:** human-in-loop
**Decision log:** ./2026-08-28-codex-worker-global-install-decisions.md
**Companions:** ./2026-08-28-codex-worker-global-install-cli-surface.md
**Origin:** brainstorm with Tadas

## 1. Problem & intent   [ANCHOR]

`codex-worker` is a capable local service and CLI, but its repository launcher resolves
the runtime relative to the Superdev checkout or plugin cache. In a shell where plugin
bin paths are absent, `command -v codex-worker` fails and an agent must invoke a long
absolute path. That defeats the intended low-friction Claude Code workflow.

This work makes `codex-worker` a genuine persistent UV tool. UV owns an isolated Python
environment and exposes a short executable on the user's PATH; neither the active
project environment nor the system Python package set is modified. The Superdev skill
performs a bounded preflight and installs the bundled package when the command is absent
or incompatible. After installation, every normal operation uses plain
`codex-worker ...` from any working directory.

## 2. Requirements   [ANCHOR]

| ID | Requirement | Source | Priority | Acceptance signal |
|----|-------------|--------|----------|-------------------|
| R1 | `codex-worker` is invocable by name from unrelated working directories. | stated | must | An external-directory invocation reaches the CLI and returns its normal JSON/help contract. |
| R2 | Installation produces a persistent UV-managed tool environment rather than modifying a project or system Python environment. | stated | must | UV reports the installed tool and its executable resolves from UV's tool bin. |
| R3 | The subagent-driven-development skill checks availability before first Codex-worker use and installs the tool when needed. | stated | must | A clean isolated tool location reaches a successful short-command invocation through the documented preflight. |
| R4 | The installed runtime does not depend on the originating checkout or versioned plugin-cache path. | stated | must | A non-editable install executes from UV's environment and contains the runtime package. |
| R5 | The tool declares Python 3.9 as its compatibility floor and owns its Python dependencies; `codex` remains an explicit external PATH prerequisite. | stated + `2026-08-18-codex-worker-server-decisions.md` D10 | must | Package metadata requires Python >=3.9, isolated imports work on the compatibility lane, and absence of `codex` produces the existing honest refusal. |
| R6 | Existing raw/common CLI behavior, daemon durability, Python compatibility floor, and plugin packaging remain compatible. | discovered | must | Existing deterministic suites plus package/install checks pass without CLI regressions. |
| R7 | Installation and upgrade failures are visible and actionable; the skill never silently falls back to a long source-path invocation. | stated | must | Missing UV, install failure, PATH failure, and version mismatch have documented recovery. |

## 3. Use cases   [ANCHOR]

| UC | As a role, I do this and see this | Exercises R# | Realized by §5 area(s) |
|----|------------------------------------|--------------|------------------------|
| UC1 | As Claude Code, I select a Codex worker and then use short `codex-worker` commands without knowing a plugin path. | R1, R3, R7 | 5.2, 5.3 |
| UC2 | As an operator, I install or upgrade the worker with UV and see it listed as an isolated persistent tool. | R2, R4, R5 | 5.1, 5.2 |
| UC3 | As a developer, I install the current checkout for testing without publishing it and can remove or replace that installation cleanly. | R2, R4, R6 | 5.1, 5.4 |
| UC4 | As an operator in an unrelated repository, I start a named worker and receive its report without any absolute launcher path. | R1, R4, R6 | 5.1, 5.3, 5.4 |

## 4. Approach narrative

The runtime already forms a Python package but lacks distribution metadata, so the
smallest durable move is to package that existing canonical source rather than copy it
(D4). A PEP 621 project and console-script entry point let UV install it non-editably
into a persistent isolated environment (D3). A standard `--version` surface makes the
installed artifact self-identifying against the loaded plugin's manifest (D5). The
skill preflight resolves that plugin through its loaded-skill trust anchor (D6), checks
the short command and its UV ownership, and invokes `uv tool install` from the bundled
source only when repair is needed (D1, D2). Normal task instructions then forget the
source path and talk solely to the installed command. Packaging and live
external-directory checks close the loop so the source shipped by both plugin forms is
exactly what UV can install.

## 5. Design

### 5.1 Standalone Python distribution

This area turns the existing runtime into the independently installed artifact that the
preflight and all later commands rely on.
**Status:** `DOC-MARK[LOCKED][D3]`

- **Design:** Add PEP 621/build metadata beside the canonical `codex_worker` package,
  declare `requires-python = ">=3.9"` and dependencies, and expose
  `codex-worker = codex_worker.cli:main`. The initial dependency set remains empty.
- **Interface / contract:** The built wheel contains the whole runtime and installs one
  `codex-worker` executable. Its distribution version exactly equals the shipping
  Superdev manifest version. It imports no modules from the source checkout at runtime.
- **Depends on:** UV and a compatible Python chosen by UV; external `codex` on PATH for
  daemon/model operations.
- **Serves:** R2, R4, R5, R6 · **Governed by:** D3, D4, D5 · **Realizes:** UC2, UC3, UC4

### 5.2 Version-aware skill preflight

This area bridges the plugin-delivered source into a ready short command before Claude
dispatches any Codex work.
**Status:** `DOC-MARK[LOCKED][D2]`

- **Design:** The Codex-worker runbook begins with one per-session preflight. It resolves
  the trusted root from `CLAUDE_PLUGIN_ROOT` when present, otherwise from the exact
  filesystem path of the loaded `SKILL.md`; canonical validation requires that root to
  contain the loaded skill, `.claude-plugin/plugin.json` or `.codex-plugin/plugin.json`,
  and the bundled package `pyproject.toml`. It reads the required version from the
  manifest, locates UV's tool bin, and accepts the PATH command only when its canonical
  path is the UV-bin executable and its `--version` equals the manifest exactly. A
  missing or mismatched UV-owned tool is installed/reinstalled non-editably from the
  bundled source. An older or newer version is deliberately replaced because the loaded
  skill and runtime ship as one compatibility unit (D5).
- **Interface / contract:** Missing UV, untrusted source, install failure, or a UV bin
  absent from PATH stops before dispatch with a short recovery instruction. A same-named
  non-UV or PATH-shadowing executable is never overwritten and reports its resolved path
  plus the UV-bin path that must precede it. There is no source-launcher fallback.
- **Depends on:** §5.1 package, the loaded skill filesystem locator, optional
  `CLAUDE_PLUGIN_ROOT`, and UV tool-bin configuration.
- **Serves:** R1, R2, R3, R7 · **Governed by:** D1, D2, D3, D5, D6 · **Realizes:** UC1, UC2

### 5.3 Short-command operating contract

This area makes the installed executable the only operational vocabulary after
preflight, which is the friction reduction the design exists to deliver.
**Status:** `DOC-MARK[LOCKED][D1]`

- **Design:** Every example, prompt, and recovery path uses `codex-worker` directly.
  Absolute repository/plugin paths are limited to the preflight installation source.
- **Interface / contract:** Existing common and raw command families are unchanged.
  `codex-worker --version` is a terminal parser action outside RPC: it writes exactly
  `codex-worker <distribution-version>\n` to stdout, writes nothing to stderr, and exits
  0 without starting or contacting a daemon.
- **Depends on:** successful §5.2 preflight.
- **Serves:** R1, R3, R6, R7 · **Governed by:** D1, D2, D5 · **Realizes:** UC1, UC4

### 5.4 Distribution and verification boundary

This area proves that what Superdev ships is installable and remains independent after
installation, completing the story from bundled source to real terminal use.
**Status:** `DOC-MARK[FLEXIBLE][D4]`

- **Design:** Extend package/sync checks to include the tool metadata and runtime. Test
  wheel construction and an isolated UV tool directory. Run the user-facing CLI from
  an unrelated temporary directory, including a real named read-only status worker.
- **Interface / contract:** Deterministic packaging tests are the fast floor; a separate
  CLI checkride and installed-command probe are the release gate.
- **Depends on:** §5.1–§5.3 and existing plugin release machinery.
- **Serves:** R1–R7 · **Governed by:** D1–D5 · **Realizes:** UC2, UC3, UC4

## 6. Decisions

### D1 — Install a standalone user command   (status: locked)

- **Decision:** Normal operation uses a persistent PATH command, independent of source layout.
- **Alternatives:** Absolute plugin/checkout launcher avoids packaging but preserves the friction and cache coupling.
- **Why:** The operator explicitly requires short commands available to Claude Code globally.
- **Revisit-when:** A platform-native package manager becomes Superdev's canonical distribution mechanism.

### D2 — Skill preflight installs only when needed   (status: locked)

- **Decision:** The skill verifies availability and repairs it before first use.
- **Alternatives:** A manual prerequisite is simpler but makes first dispatch unreliable.
- **Why:** Installation mechanics should not leak into every Codex task command.
- **Revisit-when:** User-level writes are prohibited or installs become centrally managed.

### D3 — Use UV's persistent tool environments   (status: locked)

- **Decision:** Package and install the CLI with `uv tool install`.
- **Alternatives:** File copying avoids UV but gives up isolated lifecycle, audit, and proper entry points.
- **Why:** UV is present, purpose-built for globally callable isolated Python tools, and explicitly selected by the operator.
- **Revisit-when:** UV drops the tool environment contract or a different cross-harness manager is adopted.

### D4 — Keep distributable source inside the shipped skill payload   (status: locked)

- **Decision:** Put package metadata beside the existing canonical runtime under `skills/`.
- **Alternatives:** A top-level tool tree is conventional but currently omitted by the Codex plugin packager.
- **Why:** One canonical source already reaches every plugin format and UV removes source-path runtime coupling.
- **Revisit-when:** The worker is published from its own repository or registry package.

### D5 — Bind compatibility to the shipping Superdev version   (status: locked)

- **Decision:** The package version equals the loaded manifest and preflight requires
  exact equality from an executable canonically located in UV's tool bin.
- **Alternatives:** Accepting arbitrary/newer versions avoids replacement but can pair a
  skill with a runtime contract it was not written for.
- **Why:** Exact coupling makes preflight deterministic; PATH-shadowing is reported
  rather than overwritten.
- **Revisit-when:** The worker gains an independent compatibility API or release cadence.

### D6 — Resolve install source from the loaded skill trust anchor   (status: locked)

- **Decision:** Prefer `CLAUDE_PLUGIN_ROOT`; otherwise derive the root from the harness's
  exact loaded-skill path, then validate canonical layout before installation.
- **Alternatives:** Requiring only Claude's variable is shorter but excludes other
  filesystem-backed harnesses.
- **Why:** The skill locator is the portable trust anchor already used to load these
  instructions.
- **Revisit-when:** Supported harnesses standardize one plugin-root variable.

## 7. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | Claude Code supplies `CLAUDE_PLUGIN_ROOT` and filesystem-backed harnesses supply the exact loaded `SKILL.md` locator. | R3 / UC1 / §5.2 | ratified by measured `hooks/session-start` contract and this harness's skill catalog; source still canonicalized and structurally validated |
| A2 | UV's tool bin can be made visible to Claude's shell PATH without restarting the active room. | R1, R3 / UC1 / §5.2 | ratified by measured current harness: `uv tool dir --bin` is `/Users/tadas/.local/bin` and that directory is already on PATH; retain typed recovery for other hosts |

## 7b. Test disposition

| area touched | disposition | if archiving: what the harvest must capture |
|---|---|---|
| Existing Codex-worker behavioral suite | keep and extend | — |
| Package/plugin distribution tests | fix-in-place and extend | — |
| Skill integration tests | fix-in-place and extend | — |

## 8. Not doing

- Publishing to PyPI in this slice — local/plugin-source and Git-compatible packaging
  establish the product boundary first; publish when ownership and release cadence are chosen.
- Bundling the external Codex binary — it has its own installation, authentication, and
  update lifecycle.
- Automatically downloading UV — silently executing a network bootstrap exceeds a skill
  preflight; absence receives an actionable refusal.
- Adding runtime dependencies speculatively — isolation enables them later but does not
  justify them now.

## 9. Acceptance — hints & receipts   [ANCHOR: the hints]

| # | Acceptance hint (operator terms) | Proves | Lane | Receipt (filled at gate) |
|---|----------------------------------|--------|------|--------------------------|
| AH1 | Claude can begin with no `codex-worker` command, perform its preflight, and then use the short command successfully. | UC1 / R1, R3, R7 | live | |
| AH2 | The installed worker is visibly owned by an isolated UV tool environment, not the current repository environment. | UC2 / R2, R5 | fast + live | |
| AH3 | A developer can install the current source non-editably, move the source away, and see both the imported package and short command remain owned by UV's environment. | UC3 / R2, R4, R6 | fast | |
| AH4 | From an unrelated repository, the short command starts a named read-only worker that reports Git status without a long path. | UC4 / R1, R4, R6 | live checkride | |
| AH5 | Missing UV, installation failure, stale/incompatible command, and absent external Codex each produce an honest recovery path. | UC1, UC2 / R3, R5, R7 | fast + checkride | |
| AH6 | Existing common/raw commands, daemon durability, and both plugin packages remain intact. | UC1–UC4 / R6 | fast + package | |
| AH7 | Reinstalling the UV tool leaves an existing named worker/session mapping observable afterward. | UC2, UC4 / R2, R4, R6 | live | |

## 10. Drift protocol

If build reality contradicts §5, inspect the governing D# and append the new fork to the
decision log before changing the design. Amend §5 and supersede, never erase, the prior
decision. If R1–R7, UC1–UC4, or AH1–AH7 cannot hold, stop and push the material anchor
change to the operator because this is a human-in-loop design.
