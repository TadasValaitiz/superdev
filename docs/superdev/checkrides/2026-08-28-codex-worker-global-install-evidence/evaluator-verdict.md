# Codex worker global install — evaluator verdict

**Verdict: PASS**
**Candidate:** `de425d7a072805bca26cf4d5f8b761d0a701d578`
**Evidence judged:** `executor-transcript.md` at the same path, including all focused
appendices and retained incident records
**Evaluator role:** independent judgment only; no implementation fixes, release changes,
or current-user global UV mutations

All four blocking findings from the first evaluation are closed by literal tracked
evidence. I would hand this global-install surface to the operator as exercised here.

## Final closure

### F1 — CLOSED: the plain PATH journey succeeds end to end from an unrelated cwd

The final provider-home appendix states the necessary substrate boundary explicitly:
`CODEX_HOME=/Users/tadas/.codex` preserves the existing provider authentication location,
while UV tools/bin/cache, HOME, worker state, runtime, and PATH remain fresh and isolated;
no authentication contents are printed (`executor-transcript.md:224-231`).

From `/Users/tadas/Projects/ai-ethics/ai-trading-calibration`:

- `command -v codex-worker` resolves to the isolated UV bin (`:237`).
- Literal `codex-worker ... start --name status-checker-abc --read-only --no-callback`
  exits 0 and returns the exact structured Git report: branch `main`, staged false,
  unstaged false, untracked `[".claude/settings.local.json"]`, clean false (`:238`).
- Literal short-command status returns the same worker/cwd/session/thread, read-only
  access, completed turn, and callback `disabled` (`:239`).
- The isolated registry contains exactly `["status-checker-abc"]` (`:240`).
- Independent Git observations before and after are byte-for-byte equivalent in meaning:
  branch `main`, no staged/unstaged changes, and the same single pre-existing untracked
  path (`:232-236`, `:241-245`).
- Literal `codex-worker ... daemon stop` exits 0, reports ready -> stopped,
  `durable_state: preserved`, and `worker_count: 1` (`:246`).

This directly satisfies D1/R1/UC4 without an absolute launcher or UV-bin executable in
the operational argv.

### F2 — CLOSED: absence, lower/higher repair, idempotence, and preservation are reconstructable

- Absence is literal: `command -v` exits 1, preflight succeeds, PATH then resolves the UV
  command, short `--version` returns 7.9.0, and the UV-call log contains exactly one
  `tool install --reinstall` (`:142-146`).
- Lower mismatch is explicitly a 0.0.1 fixture; the before probe, one reinstall log, and
  measured 7.9.0 after probe are present (`:147-151`).
- Higher mismatch is explicitly a 9999.0.0 fixture with the same before/one-reinstall/
  measured-after chain (`:152-156`).
- The next exact-version preflight is idempotent: its UV-call log contains only
  `tool dir --bin`, with no install (`:157-158`).
- Shadow refusal leaves the foreign executable's SHA-256 unchanged (`:159-161`). Forced
  exit-47 install failure leaves both the prior command and durable sentinel hashes
  unchanged (`:162-164`).

The final cumulative count is internally consistent: 117 command records and 124 total
records/events after the 16-command/17-event provider-home appendix (`:249-251`).

### F3 — CLOSED: source removal and Python 3.9 provenance are literal

The focused appendix records fixture-source presence, a real non-editable UV/Python-3.9
install, literal `mv`, an exit-0 old-path absence check, UV-bin PATH lookup, literal short
`codex-worker --version`, and a Python 3.9 import from isolated UV site-packages
(`:165-172`). Execution therefore occurs after the installation source is unavailable.

### F4 — CLOSED: fixture and measured boundaries are labelled precisely

Lower and higher starting versions are labelled `SIMULATED fixture version over
MEASURED real subprocess behavior`; their post-repair probes are labelled MEASURED real
isolated UV/tool subprocesses (`:147-156`). The forced install failure retains its
SIMULATED-over-MEASURED label (`:163`), while the real UV source install/move/import lane
is separately labelled (`:165-172`). The evidence proves the mechanism without claiming
that registry-distributed lower/higher packages were installed.

## Other operator checks

- Shadow, missing UV, forced install failure, and missing external Codex refusals are
  actionable and honest in the original ride (`:30-33`, `:76-84`); the focused appendix
  supplies the before/after preservation evidence.
- D11 is directly proven by original Scenario 3: session
  `60966e60-833e-43fc-bcfc-9b3ce66513ea` and thread
  `01a0474b-959b-74d1-8497-54873047a7f2` are identical at creation, post-reinstall
  `run`, and status (`:95`, `:98-99`), and both runtime-only stops preserve durable state
  (`:96`, `:100`).
- UV audit output and canonical executable/import provenance are visible (`:17-20`,
  `:27`, `:93-94`, `:107-108`, `:170-172`, `:231`, `:237`).
- Existing response figures label measured/derived/unavailable provenance, while
  success/refusal exit codes follow this area's retained CLI contract.
- The final structured report is scannable as one JSON object, and every recovery command
  emitted on its success surface uses the live short command (`:238`).

## Iteration history and retained incidents

1. **Initial verdict — NEEDS FIXES.** The original ride used absolute UV-bin executable
   paths for operations; it elided absence/mismatch/idempotence/preservation mechanics;
   source removal appeared only in a heading; and fixture version conditions were not
   tiered precisely.
2. **Focused F1–F4 appendix.** F2–F4 closed. Plain PATH lookup and invocation were shown,
   but the unrelated-cwd start returned `incomplete_completion/no_agent_message`
   (`:179-181`), so F1 remained open.
3. **Fresh plain-PATH attempt with isolated HOME but omitted provider home.** The attempt
   honestly retained its `incomplete_completion` and external Codex 401 results
   (`:194-218`). This was a harness-auth omission, not accepted product evidence: unlike
   the canonical live harness, replacing HOME also hid the existing provider credentials.
4. **Final provider-home appendix.** Explicit `CODEX_HOME` corrected the harness while
   retaining all UV/worker isolation and produced the successful F1 journey (`:224-251`).

The separate durable exploratory attempt remains honestly marked incomplete and is not
used as a substitute for original Scenario 3 (`:257-279`). Its literal runtime-only stop
succeeded and preserved one worker. The retained
`/tmp/cw-reride-durable-2pdl66d5` root is a disclosed cleanup handoff: the controller must
remove it safely after preserving the tracked evidence. It is not a product-surface
finding and does not weaken the direct D11 proof.

## Observations → backlog

- **Preflight success output · distinguish mutation from no-op.** Absent install,
  lower/higher repair, and exact-version idempotence render the same
  `codex-worker ready: <path> (<version>)` line. Because D5 may deliberately replace a
  newer tool, file an **experience-class backlog item** for concise `installed` /
  `repaired <from> -> <to>` / `already ready` status.
- **Incomplete completion recovery · retain the known worker route.** The retained plain
  start incident created `status-checker-abc`, but its error returned empty
  `next_actions` and null `known_ids` despite the registry containing that name
  (`:180-181`; repeated with the harness-auth failure at `:207-208`). File an
  **experience-class backlog item** so `incomplete_completion` emits runnable
  status/history recovery with every known name/session/thread/turn identity.

Neither observation blocks this global-install PASS: the final intended journey succeeds,
and the incidents are preserved rather than used to overclaim. Per the CLI-checkride
skill, the controller must also create the dated global-install scenario-intent document
under `design/scenarios/`, carrying at least these reusable criteria:

- normal operation uses literal short PATH commands from an unrelated repository;
- install/repair/no-op state is distinguishable to the operator;
- source-independent Python 3.9/UV provenance and exact version remain visible;
- lower/higher fixtures are labelled separately from measured UV behavior;
- incomplete completions retain runnable known-worker recovery;
- read-only/no-callback status work leaves the repository unchanged and runtime stop
  preserves the one durable mapping.
