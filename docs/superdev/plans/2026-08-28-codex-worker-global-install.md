# Codex Worker Global UV Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package `codex-worker` as a standalone UV-managed tool, make the Superdev skill install/repair it before use, and leave a verified plain command available globally.

**Architecture:** The canonical runtime stays in the already-shipped subagent-driven-development scripts tree and gains PEP 621 metadata plus a console entry point. An internal preflight executable owns trust-root resolution, UV-bin ownership, exact plugin/tool version matching, install/reinstall, and actionable refusal; the skill invokes it once and then uses only plain `codex-worker`. Existing runtime state remains outside UV so replacement is non-destructive.

**Tech Stack:** Python 3.9+ standard library, PEP 621, hatchling build backend, UV persistent tools, POSIX shell, unittest, existing Superdev package/release scripts.

**Execution:** subagent-driven

**Mode:** human-in-loop

**Context pack** — the artifacts downstream workers read:
- Spec: `docs/superdev/specs/2026-08-28-codex-worker-global-install-design.md` · Decision log: `docs/superdev/specs/2026-08-28-codex-worker-global-install-decisions.md`
- Domain model: none; `--version` is deliberately a terminal parser action, not an RPC/domain command.
- CLI surface: `docs/superdev/specs/2026-08-28-codex-worker-global-install-cli-surface.md`
- Prior art: `docs/superdev/specs/2026-08-18-codex-worker-server-design.md` D10; `docs/superdev/specs/2026-08-19-codex-worker-command-ergonomics-design.md`; `docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-design.md`

## Global Constraints

- Python compatibility floor is exactly 3.9; production code remains standard-library-only.
- `codex-worker` Python packages live only in UV's persistent isolated tool environment; do not modify a project `.venv` or system Python.
- The worker distribution version exactly equals the loaded Superdev manifest version; first reconcile the measured baseline drift (five declared manifests at 7.3.0, two at 7.9.0) to 7.9.0, then advance every declared version together to 7.10.0 at release.
- A same-named executable outside UV's canonical tool bin is an actionable refusal, never an overwrite target.
- `codex` remains an external PATH prerequisite; do not bundle, install, or replace it.
- The internal preflight may reference its own plugin path; every operating example after it uses only `codex-worker`.
- Install/reinstall/uninstall never deletes daemon registries, named sessions, callback state, or other durable worker data.
- Existing CLI request/response/error contracts and common/raw commands are unchanged except the parser-only `--version` action.
- Superdev remains dependency-free for users who do not select a Codex worker; UV is checked only at the Codex-worker preflight boundary.

**Test lanes:** fast (the gate): `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` plus focused repository shell tests touched by the commit · slow-by-area (separate killable commands): `python3 tests/codex-worker/live_uv_tool_check.py --scenario <name>`, `python3 tests/codex-worker/live_broker_check.py --preflight`, and the CLI checkride executor/evaluator · scheduled sweep: none declared by this repository. Every commit runs the fast worker gate plus its focused shell/package tests; each live scenario runs separately at its owning gate.

**Engineering patterns:** `skills/engineering-patterns/python-patterns.md` (BINDING by Python stack detection) plus `skills/engineering-patterns/process-discipline.md` (ALWAYS; never overridden). Implementers read §1, §4, §6, §9, §10 and process-discipline §§1–3 before coding.

## The Through-Line

Task 1 is load-bearing: it makes the current runtime a real installable distribution and gives that artifact one observable identity tied into release tooling. Task 2 consumes that identity to build the testable preflight boundary and updates the skill under writing-skills RED/GREEN discipline; after it lands, agents can reliably move from a loaded skill to a short global command without duplicating installation logic. Task 3 proves the artifact survives packaging and source removal, then drives the real command from another repository while preserving named state across reinstall. Task 4 is the release/integration gate: independent executor and evaluator ride the public surface, the plugin/tool version advances together, the current user receives the non-editable UV install, and receipts close every anchor hint.

Task 1's PEP 621 metadata and `distribution_version()` are the main Produced interfaces. Task 2's `install-codex-worker` is the second load-bearing interface; Tasks 3–4 must call it, not reconstruct its policy. Package-test and live-check mechanics are flexible, but they may not weaken exact ownership/version/source-removal or durable-state assertions.

**When reality diverges from a task:** re-read this through-line, inspect the governing D# revisit hook in the decision log, append a build-phase decision before changing the interface, and update downstream Consumes/Produces blocks. A change that breaks exact UV ownership, standalone runtime independence, or plain-command operation returns to the operator.

## Acceptance (anchored — do not restate here)

This plan discharges UC1–UC4 and AH1–AH7 from the anchor. Task 1 produces AH2/AH3 identity and isolation evidence; Task 2 produces AH1/AH5 preflight and recovery evidence; Task 3 produces AH3/AH4/AH6/AH7 package/live receipts; Task 4 independently re-rides and fills every receipt. Any unanswered hint stops the human-in-loop finishing gate.

---

### Task 1: Package identity, `--version`, and release coupling

**Role in the build:** Establish the standalone artifact and exact identity that all preflight/install behavior consumes, including reconciliation of measured baseline manifest drift, implementing R2, R4–R6 and D3–D5/D8–D9.

**Read first:** spec §5.1 and §5.3; decisions D3–D5 and D8–D9; CLI surface §1 `--version`; Python patterns §§1, 6, 9, 10; process discipline §1.

**Files:**
- Create: `skills/subagent-driven-development/scripts/pyproject.toml`
- Create: `skills/subagent-driven-development/scripts/codex_worker/version.py`
- Modify: `skills/subagent-driven-development/scripts/codex_worker/cli.py`
- Modify: `.version-bump.json`
- Modify: `scripts/bump-version.sh`
- Create: `tests/codex-worker/test_tool_package.py`
- Create: `tests/version/test-bump-version.sh`
- Test: `tests/codex-worker/test_rpc_cli.py`

**Interfaces:**
- Consumes: existing `codex_worker.cli.main(argv: Optional[Sequence[str]]) -> int`; current plugin version `7.9.0`; existing `.version-bump.json` JSON-field entries.
- Produces: PEP 621 distribution `codex-worker`; console entry point `codex-worker = "codex_worker.cli:main"`; `distribution_version() -> str`; exact stdout `codex-worker <version>\n`; version-config entries supporting `format: "json"` and `format: "toml"`.

- [ ] **Step 1: RED — pin package and terminal identity contracts**

  Add focused tests that require:

  ```python
  class ToolPackageTests(unittest.TestCase):
      def test_pyproject_declares_isolated_console_tool(self):
          text = PYPROJECT.read_text(encoding="utf-8")
          self.assertIn('name = "codex-worker"', text)
          self.assertIn('requires-python = ">=3.9"', text)
          self.assertIn('dependencies = []', text)
          self.assertIn('codex-worker = "codex_worker.cli:main"', text)

      def test_source_cli_version_matches_plugin_manifest(self):
          expected = json.loads(CLAUDE_MANIFEST.read_text())["version"]
          completed = subprocess.run(
              [sys.executable, str(SOURCE_LAUNCHER), "--version"],
              text=True, capture_output=True, check=False,
          )
          self.assertEqual(completed.returncode, 0)
          self.assertEqual(completed.stdout, "codex-worker %s\n" % expected)
          self.assertEqual(completed.stderr, "")
  ```

  Extend `test_rpc_cli.py` to prove `--version` does not connect, spawn, read state, or emit JSON. Add a temporary-fixture shell test that expects `bump-version.sh` to read/write one TOML `project.version` entry alongside JSON entries without touching any other TOML key. Add a repository-level assertion that all declared version files and the new package metadata agree; it must initially report the measured 7.3.0/7.9.0 baseline drift.

  Run:

  ```bash
  python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_tool_package.py tests/codex-worker/test_rpc_cli.py -v
  bash tests/version/test-bump-version.sh
  ```

  Expected: RED because metadata/version support and TOML release handling do not exist.

- [ ] **Step 2: GREEN — add minimal distribution/version implementation**

  Create metadata shaped as:

  ```toml
  [build-system]
  requires = ["hatchling>=1.27,<2"]
  build-backend = "hatchling.build"

  [project]
  name = "codex-worker"
  version = "7.9.0"
  description = "Local durable Codex app-server worker broker"
  requires-python = ">=3.9"
  dependencies = []

  [project.scripts]
  codex-worker = "codex_worker.cli:main"

  [tool.hatch.build.targets.wheel]
  packages = ["codex_worker"]
  ```

  Implement `distribution_version()` with `importlib.metadata.version("codex-worker")`
  and a source-checkout fallback that reads only the adjacent `pyproject.toml` exact
  `project.version` assignment. Add argparse's terminal version action before family
  dispatch. Extend version config entries with optional `format` defaulting to JSON and
  a TOML handler constrained to one exact field under `[project]`; reject zero or
  multiple matches and preserve all unrelated bytes. Once the handler and config entry
  exist, run `scripts/bump-version.sh 7.9.0` to reconcile all seven declared manifests
  and the package metadata before Task 2 tests either Claude or Codex plugin sources.

- [ ] **Step 3: Verify artifact isolation and compatibility**

  Run the RED commands until GREEN, then separately:

  ```bash
  uv build --wheel skills/subagent-driven-development/scripts --out-dir /tmp/codex-worker-wheel-check
  UV_TOOL_DIR="$(mktemp -d)/tools" UV_TOOL_BIN_DIR="$(mktemp -d)/bin" \
    uv tool install --python 3.9 --reinstall skills/subagent-driven-development/scripts
  uv run --python 3.9 python -m compileall -q skills/subagent-driven-development/scripts/codex_worker
  python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
  ```

  Expected: one wheel containing only `codex_worker` plus metadata/entry point; an
  isolated Python 3.9 tool environment imports the installed package and its
  `codex-worker --version` exits 0; Python 3.9 compile succeeds; every declared version
  reports 7.9.0; fast worker suite passes warning-strict. Capture temp roots explicitly
  and remove them in a trap rather than relying on the illustrative inline `mktemp` form.

- [ ] **Step 4: Self-review, independent checkpoint review, and commit**

  Check wheel contents, parser/RPC separation, TOML update failure modes, Python 3.9
  syntax, `git diff --check`, and no generated wheel in the repository. A fresh reviewer
  must independently break version equality and TOML uniqueness and watch guards fail.
  Fix findings, rerun focused + fast gates, and commit:

  ```bash
  git add .version-bump.json scripts/bump-version.sh \
    package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json \
    .cursor-plugin/plugin.json .codex-plugin/plugin.json \
    .kimi-plugin/plugin.json gemini-extension.json \
    skills/subagent-driven-development/scripts/pyproject.toml \
    skills/subagent-driven-development/scripts/codex_worker/version.py \
    skills/subagent-driven-development/scripts/codex_worker/cli.py \
    tests/codex-worker/test_tool_package.py tests/codex-worker/test_rpc_cli.py \
    tests/version/test-bump-version.sh
  git commit -m "feat(codex-worker): package standalone UV tool"
  ```

### Task 2: Executable preflight and skill behavior

**Role in the build:** Turn the bundled package into a zero-friction, testable Claude/Codex preflight and teach the skill to use only the resulting command, implementing R1–R3/R7 and D1–D3/D5–D7.

**Read first:** spec §5.2–§5.3; decisions D1–D3 and D5–D7; CLI surface §2–§3; `skills/writing-skills/SKILL.md`; Python patterns §§4, 6, 9, 10; process discipline §§1–3.

**Files:**
- Create: `skills/subagent-driven-development/scripts/install-codex-worker`
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `skills/subagent-driven-development/codex-worker.md`
- Modify: `README.md`
- Create: `tests/codex-worker/test_tool_preflight.py`
- Modify: `tests/codex-worker/test_skill_integration.py`
- Create: `docs/superdev/reviews/2026-08-28-codex-worker-global-install-skill-eval.md`

**Interfaces:**
- Consumes: Task 1 package directory and exact `codex-worker --version`; loaded script location; optional `CLAUDE_PLUGIN_ROOT`; UV commands `tool dir --bin`, `tool install --reinstall`.
- Produces: internal executable `install-codex-worker` with exit 0 only when the expected UV-owned short command is usable; one-per-session skill preflight; actionable stderr and nonzero exit for missing UV, untrusted root, shadowing, install failure, and PATH invisibility.

- [ ] **Step 1: RED — executable behavior and skill pressure baseline**

  Create subprocess tests with isolated `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`, `UV_CACHE_DIR`,
  temp PATH, a fixture plugin containing matching manifest/pyproject/skill, and a fake UV
  that records argv and creates a selected executable only when instructed. The complete
  matrix is:

  | Test | Fixture and invocation | Required assertions |
  |---|---|---|
  | absent command | PATH has fake UV but no worker; run fixture preflight | exit 0; exactly one recorded `tool install --reinstall <canonical-package>`; no `--editable`; created UV-bin command reports expected version |
  | matching UV command | UV-bin worker already reports expected version; run twice | both exit 0; install log remains empty; success output is stable |
  | old/new UV versions | parameterize worker output to one lower and one higher version | each run records exactly one reinstall and ends on exact expected version |
  | foreign shadow | PATH resolves a non-UV worker before UV bin | nonzero; no install; foreign bytes unchanged; stderr contains both canonical paths and PATH repair |
  | missing UV | PATH has basic shell utilities but no UV | nonzero; no mutation; stderr names `uv` installation prerequisite |
  | root disagreement | set `CLAUDE_PLUGIN_ROOT` to a second valid-looking root | nonzero before UV; stderr names both roots; no install |
  | UV bin off PATH | fake `uv tool dir --bin` returns a directory omitted from PATH | nonzero after any needed install; stderr names `uv tool update-shell` and current-shell PATH recovery |
  | install failure | fake UV exits nonzero and a prior UV-bin worker/durable sentinel exist | nonzero; prior executable and sentinel hashes unchanged; stderr includes UV failure exit/output |
  | external Codex absent | real installed worker is on PATH but `codex` is removed; invoke `--instance <isolated> daemon start` | one JSON refusal with existing typed daemon-start failure, actionable missing-`codex` detail, nonzero exit, no traceback |

  **Build erratum (2026-08-28, D10):** measured `model list` is an RPC-only read and
  correctly does not autostart a stopped managed daemon. The external-prerequisite
  negative therefore uses explicit `daemon start`; this corrects the test route without
  changing public lifecycle semantics.

  Before editing the skill, run at least two fresh-agent pressure scenarios against the
  current skill: (a) no PATH worker but a loaded plugin package; (b) a shadowing old
  source launcher. Record exact baseline choices/rationalizations in the skill-eval doc.
  Run focused tests and confirm RED for missing preflight/instructions.

- [ ] **Step 2: GREEN — implement one hardened preflight**

  The executable must:

  ```text
  derive real plugin root from its own path
  if CLAUDE_PLUGIN_ROOT is set, require its real path to equal the derived root
  require SKILL.md + one/matching manifest + package pyproject beneath that root
  require command -v uv
  read exactly one project.version from pyproject
  require manifest version equality
  obtain canonical UV bin from `uv tool dir --bin`
  classify absent / UV-owned matching / UV-owned mismatched / foreign-shadowing
  install only absent or mismatched via non-editable `uv tool install --reinstall PACKAGE`
  verify canonical executable, exact version output, empty stderr, and current PATH
  print one concise success line; otherwise print actionable stderr and exit nonzero
  ```

  Preserve the old tool until UV reports successful replacement. Never invoke the
  source launcher as an operational fallback and never touch state/socket/registry paths.

- [ ] **Step 3: GREEN — edit skill with writing-skills discipline**

  Add a concise mandatory preflight immediately before the first Codex-worker dispatch:

  ```bash
  "$SUPERDEV_PLUGIN_ROOT/skills/subagent-driven-development/scripts/install-codex-worker"
  codex-worker --version
  ```

  Define `SUPERDEV_PLUGIN_ROOT` from `CLAUDE_PLUGIN_ROOT` or the exact loaded skill path;
  say the preflight runs once per session when Codex is selected, never for native
  Claude-only work. All following examples remain short. Document local, Git, future
  registry, upgrade, audit, and uninstall opportunities in `codex-worker.md` without
  making them routine dispatch ceremony. Update README prerequisites to make UV
  conditional on Codex-worker selection.

  Rerun the same fresh-agent scenarios with the edited skill and add a shadowing/missing
  UV scenario. Record GREEN decisions and any loophole-closing iteration in the eval doc.

- [ ] **Step 4: Verify and commit checkpoint**

  Run:

  ```bash
  python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_tool_preflight.py tests/codex-worker/test_skill_integration.py -v
  python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
  bash -n skills/subagent-driven-development/scripts/install-codex-worker
  git diff --check
  ```

  A fresh reviewer replays at least missing-command and shadowing pressure cases and
  confirms native Claude remains untouched. Fix findings, rerun gates, and commit:

  ```bash
  git add skills/subagent-driven-development/scripts/install-codex-worker \
    skills/subagent-driven-development/SKILL.md \
    skills/subagent-driven-development/codex-worker.md README.md \
    tests/codex-worker/test_tool_preflight.py \
    tests/codex-worker/test_skill_integration.py \
    docs/superdev/reviews/2026-08-28-codex-worker-global-install-skill-eval.md
  git commit -m "feat(codex-worker): install UV tool at skill preflight"
  ```

### Task 3: Packaged-source and live global-command proof

**Role in the build:** Prove the shipped source installs independently, survives source removal/reinstall, and drives a real named worker from another repository, implementing R1–R7 and producing AH1–AH7 receipts.

**Read first:** spec §5.4 and §9; CLI surface §3; decisions D4–D9; Python patterns §§1, 4, 6, 9, 10; process discipline §§2–3.

**Files:**
- Modify: `tests/codex/test-package-codex-plugin.sh`
- Modify: `tests/codex-plugin-sync/test-sync-to-codex-plugin.sh`
- Create: `tests/codex-worker/live_uv_tool_check.py`
- Modify: `tests/codex-worker/test_live_harness_contract.py`
- Modify receipt cells only: `docs/superdev/specs/2026-08-28-codex-worker-global-install-design.md`

**Interfaces:**
- Consumes: Task 1 wheel/package, Task 2 preflight, existing plugin archive/sync tools, existing managed daemon/common CLI.
- Produces: separately runnable scenarios `package-independence`, `preflight-recovery`, `durable-reinstall`, and `external-status-worker`; sanitized JSONL transcripts and summaries under `.superdev/codex-worker-live/<run>/`.

- [ ] **Step 1: RED — package and harness contracts**

  Extend archive/sync assertions to require executable preflight, `pyproject.toml`, and
  all `codex_worker` modules in the shipped `skills/` payload. Add structural harness
  tests requiring each named live scenario, isolated UV dirs, source-move proof,
  command provenance, an actual Python 3.9 installed import/run, no editable install,
  absent-Codex refusal, no durable-state deletion, and exact `status-checker-abc`
  external-repository journey. Observe focused RED.

- [ ] **Step 2: GREEN — build isolated live scenarios**

  Implement each scenario as a separate process boundary. `package-independence` installs
  from a copied packaged source using `uv tool install --python 3.9`, moves that source
  away, asserts the installed interpreter is Python 3.9, imports `codex_worker` from the
  UV environment rather than the moved source, and runs `--version`.
  `preflight-recovery` drives absent, mismatch, shadow, forced installation failure,
  and absent-external-`codex` refusals. `durable-reinstall` creates a named mapping, stops the runtime,
  reinstalls, and reads the same mapping. `external-status-worker` runs from
  `/Users/tadas/Projects/ai-ethics/ai-trading-calibration` with instance
  `uv-global-install` and name `status-checker-abc`, read-only/no-callback, asking for
  branch/staged/unstaged/untracked/clean status without modification; it validates the
  returned report and stops only the runtime afterward.

- [ ] **Step 3: Run deterministic and slow-by-area gates separately**

  ```bash
  python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_live_harness_contract.py -v
  bash tests/codex/test-package-codex-plugin.sh
  bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh
  python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
  python3 tests/codex-worker/live_uv_tool_check.py --scenario package-independence
  python3 tests/codex-worker/live_uv_tool_check.py --scenario preflight-recovery
  python3 tests/codex-worker/live_uv_tool_check.py --scenario durable-reinstall
  python3 tests/codex-worker/live_uv_tool_check.py --scenario external-status-worker
  python3 tests/codex-worker/live_broker_check.py --preflight
  ```

  Expected: every command exits 0 independently; transcripts identify real vs fake
  substrate; external worker response contains a coherent Git status report and no
  file/state mutation beyond worker-owned runtime metadata.

- [ ] **Step 4: Independent checkpoint review and commit**

  A fresh reviewer checks archive completeness, source-removal proof, UV provenance,
  that the external scenario creates exactly one worker named `status-checker-abc` and
  no additional worker names, state preservation, transcript sanitation, and
  external-cwd honesty. Fix, rerun affected commands plus fast gate, fill AH receipts,
  and commit source/tests (ignored raw evidence remains cited, not force-added):

  ```bash
  git add tests/codex/test-package-codex-plugin.sh \
    tests/codex-plugin-sync/test-sync-to-codex-plugin.sh \
    tests/codex-worker/live_uv_tool_check.py \
    tests/codex-worker/test_live_harness_contract.py \
    docs/superdev/specs/2026-08-28-codex-worker-global-install-design.md
  git commit -m "test(codex-worker): prove standalone UV installation"
  ```

### Task 4: Checkride, release 7.10.0, user install, and integration

**Role in the build:** Independently validate the real operator surface, publish the coupled plugin/tool version, install it for the current user, and close every acceptance receipt, implementing the full R1–R7/UC1–UC4 goal.

**Read first:** spec §1–§3 and §9; full CLI companion; decisions D1–D9; `skills/cli-checkride/SKILL.md`; `skills/verification-before-completion/SKILL.md`; `skills/finishing-a-development-branch/SKILL.md`; Python patterns §§4, 6, 9, 10; process discipline §§2–3.

**Files:**
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-global-install-checkride.md`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-global-install-evidence/executor-transcript.md`
- Create: `docs/superdev/checkrides/2026-08-28-codex-worker-global-install-evidence/evaluator-verdict.md`
- Modify via release tooling: `.version-bump.json` declared manifests, `package.json`, and package `pyproject.toml`
- Modify: `RELEASE-NOTES.md`
- Modify receipts only: `docs/superdev/specs/2026-08-28-codex-worker-global-install-design.md`

**Interfaces:**
- Consumes: all prior tasks, existing version/package/marketplace/plugin installation tooling, real UV/Codex/Claude CLIs.
- Produces: independently evaluated verbatim checkride; version 7.10.0 plugin + tool; current-user non-editable UV install; global short command verified from unrelated cwd; clean integrated main.

- [ ] **Step 1: Fresh executor/evaluator CLI checkride**

  Use the CLI-checkride skill. The executor drives one command at a time with separate
  stdout/stderr/exit records: `--version`, absent preflight install, idempotent preflight,
  old/new mismatch replacement, shadow refusal, missing-UV refusal, forced installation
  failure, absent-external-`codex` refusal, UV list/audit,
  source removal, unrelated-cwd `status-checker-abc`, durable state across reinstall,
  and non-destructive stop. A fresh evaluator judges mechanism and outputs; fix and
  reride until PASS. No elisions or invented command output.

- [ ] **Step 2: Release version and package gates**

  Run `scripts/bump-version.sh 7.10.0`; expected output names every declared JSON file
  plus `skills/subagent-driven-development/scripts/pyproject.toml` changing from 7.9.0
  to 7.10.0 with no drift. Verify it updates package metadata and all
  manifests exactly. Add release notes for standalone UV installation and skill
  preflight. Commit the release source, then run separately:

  ```bash
  scripts/bump-version.sh --check
  scripts/bump-version.sh --audit
  bash tests/codex/test-marketplace-manifest.sh
  bash tests/codex/test-package-codex-plugin.sh
  bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh
  ```

  Record every command's real output/exit in the release report; do not infer a pass
  from a neighboring package gate.

- [ ] **Step 3: Install for the current user and verify instantly**

  Preserve the user's existing UV tool metadata and durable worker state. Run the
  bundled preflight from the release worktree, then verify:

  ```bash
  command -v codex-worker
  codex-worker --version
  uv tool list
  ```

  From `/Users/tadas/Projects/ai-ethics/ai-trading-calibration`, run plain
  `codex-worker --instance uv-global-install status --name status-checker-abc` and, if
  the worker does not yet exist in the final installed instance, run the exact read-only
  start journey once. Confirm executable/import paths resolve inside UV, version is
  7.10.0, and no absolute launcher is used. Stop only the daemon runtime afterward;
  preserve the named mapping.

- [ ] **Step 4: Final verification, receipts, commit, and integration**

  Run fresh:

  ```bash
  python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'
  bash tests/version/test-bump-version.sh
  bash tests/codex/test-package-codex-plugin.sh
  bash tests/codex-plugin-sync/test-sync-to-codex-plugin.sh
  python3 tests/codex-worker/live_uv_tool_check.py --scenario package-independence
  python3 tests/codex-worker/live_uv_tool_check.py --scenario durable-reinstall
  python3 tests/codex-worker/live_uv_tool_check.py --scenario external-status-worker
  python3 -m compileall -q skills/subagent-driven-development/scripts/codex_worker
  bash -n skills/subagent-driven-development/scripts/install-codex-worker
  git diff --check
  ```

  Fill AH1–AH7 with one rerunnable receipt each. Dispatch a fresh whole-branch reviewer;
  fix every Critical/Important and rerun affected gates. Commit checkride/release/
  receipts, follow finishing-a-development-branch to integrate into main without
  destructive cleanup, reinstall from integrated main, repeat `command -v`, `--version`,
  external-cwd status, and leave every touched checkout clean.

## Operational strategy

All existing Codex-worker behavioral, packaging, release, and skill-integration tests
are **keep and fix-in-place**. New package/preflight/live tests extend those lanes; no
legacy tests are archived, regenerated, skipped, or deleted. The package move is not a
domain replacement: the canonical `codex_worker` modules stay in place, so no harvest
manifest is required. Skill prose follows writing-skills RED/GREEN pressure scenarios
in Task 2; deterministic executable checks are the enforcement floor, and the Task 4
checkride is the real-surface gate.
