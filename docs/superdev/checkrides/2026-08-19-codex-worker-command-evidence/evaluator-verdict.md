# Codex worker command checkride evaluator verdict

Date: 2026-08-20
Historical candidate: `e5e8c8ac29117c92b4376fddfe3c4d5586c`
Fix candidate: `ffa24e7` (includes product fix `7d356e2`)
Role: CHECKRIDE EVALUATOR (judgment only; no product edits)

Evidence reviewed:

- the complete current `executor-transcript.md`, including its focused re-ride at `L201-L358`;
- the prior evaluator BLOCK and each B1–B3/A1–A3 finding;
- design §§1–3 and §9 and CLI surface §§0–10 as amended through `ffa24e7`;
- tracked Stage 1 live transcripts and summaries, always labeled below as separate Stage 1 evidence;
- one evaluator-focused deterministic re-drive for the AH10/AH11 receipt doubt, recorded below.

## VERDICT: PASS

I would hand this surface to the operator. The focused live re-ride closes all three prior blockers: authoritative goal state is demonstrated without an already-exceeded budget, active-turn overlap now returns a precise typed refusal with usable named controls, and the formerly elided control flow is replaced by fresh command-by-command stdout/stderr/exit records. The two refusal advisories are also closed. Remaining issues are evidence-file polish, not operator safety or product correctness.

## Re-review history

### Prior B1 — resolved: authoritative goal behavior is now explicit and safe

The historical over-budget attempt remains preserved at `executor-transcript.md:L59-L69`; its `budgetLimited` response is authoritative provider state, not proof that a requested status always wins an already-triggered budget invariant. The amended CLI contract makes that precedence explicit.

The focused live case starts below budget (`50000` budget, `22286` used, status `active`) at `L207-L223`, requests only `--status paused` at `L226-L232`, and an independent `goal show` returns the same paused state at `L235-L240`. The operator can inspect authoritative state and know the pause held. B1 is closed.

### Prior B2 — resolved: active overlap has typed, actionable recovery

The new live flow first returns `timeout_active` with full instance/name/session/thread/turn identity and status/messages/interrupt actions (`executor-transcript.md:L246-L253`). A second `run` is then refused as `-32004 turn_active`, preserves all identities, and offers status, messages, steer, and deliberate interrupt commands (`L255-L262`). Those actions are themselves driven successfully through active narration, steer, interrupt, and terminal interrupted status (`L264-L307`). The operator is neither stranded nor led to believe the original turn stopped. B2 is closed.

### Prior B3 — resolved for the affected surface

The focused section explicitly supersedes the historical incomplete capture for affected paths (`executor-transcript.md:L201-L204`). It records literal invocations, separate complete stdout/stderr, and exit codes for goal mutation, timeout/active collision, active observation/control, refusal recoveries, raw recovery/events, and stop (`L207-L355`). This is sufficient to reconstruct the previously elided product flow. B3 is closed.

### Prior A1 — resolved: unavailable limits forbid inference

The live refusal remains typed and now says `capacity: unknown` and `inference: do_not_infer` (`executor-transcript.md:L311-L318`). An empty executable `next_actions` list is correct because there is no honest recovery command to fabricate.

### Prior A2 — resolved: unsupported effort has a shell-safe retry

The live `effort_unsupported` refusal preserves instance/name/model, lists exact supported efforts, states that no fallback ran, and supplies a corrected `start` command (`executor-transcript.md:L320-L327`).

### Prior A3 — retained advisory: compact default JSON

Default responses remain one-line machine-oriented JSON; `--pretty` remains available for manual terminal reading. This is an intentional global contract, not a handoff blocker.

## Remaining blocking findings

None.

## Remaining advisory findings

None from E1/E2. Prior compact-JSON advisory A3 remains an intentional contract tradeoff, not required evidence cleanup.

### Evidence-polish confirmation — E1 and E2 closed

- E1 closed: the header now identifies both historical SHA `e5e8c8a` and focused fix SHA `ffa24e7` (`executor-transcript.md:L3-L6`), and both the appendix introduction and summary say 16 fully recorded commands (`L202-L204`, `L359`).
- E2 closed: the preliminary already-registered-thread attempt is correctly classified as an expected typed refusal outside the counted records, with no claim that its unretained output is ride evidence (`executor-transcript.md:L359`). The deterministic note now cites all five exact AH10/AH11 tests and explicitly labels them fixture/test rather than real-provider evidence (`L348`).

## Evaluator's one focused re-drive

Purpose: resolve only the AH10/AH11 deterministic receipt citation doubt; this was not a live re-ride.

Command:

```text
python3 -W error::ResourceWarning -m unittest \
  tests.codex-worker.test_projection.ProjectionTests.test_multiple_explicit_finals_are_retained_in_order \
  tests.codex-worker.test_projection.ProjectionTests.test_terminal_fallback_and_live_messages_preserve_nullable_phase \
  tests.codex-worker.test_models_registry.RegistryTests.test_missing_and_zero_byte_registry_initialize_v2_owner_only \
  tests.codex-worker.test_models_registry.RegistryTests.test_nonempty_malformed_and_truncated_registry_bytes_are_preserved_exactly \
  tests.codex-worker.test_models_registry.RegistryTests.test_foreign_owner_state_is_rejected_with_deterministic_owner_injection -v
```

Result: **PASS, 5 tests, exit 0**. The governing assertions are visible at `tests/codex-worker/test_projection.py:L17-L26` and `L55-L61`, and `tests/codex-worker/test_models_registry.py:L57-L65`, `L247-L258`, and `L295-L310`. This is deterministic fixture evidence, not real-provider evidence.

## Strengths

- The common path is one synchronous `start` followed by short name-only `run`; the complete final answer and stable recovery commands come back without daemon choreography (`executor-transcript.md:L17-L39`).
- Every live worker result makes instance/name/session/thread/cwd/tier/model/effort/access explicit. The fixed tier mapping is exact: medium → Terra and very-smart → Sol (`L21`, `L29`).
- The active-turn safety model is unusually good after the fix: timeout preserves work, overlap refuses precisely, inspection is observational, steering is explicit, and interruption is deliberate (`L246-L307`).
- Metrics remain provenance-labeled and unavailable tokens/capacity are never inferred (`L211`, `L314`).
- Full access is the default and read-only is structural; separate Stage 1 live evidence exercises the actual policies at `access-schema/transcript.jsonl:L1-L2`.
- Runtime stop is visibly non-destructive (`durable_state: preserved`) in both the historical restart journey and focused re-ride (`executor-transcript.md:L174-L179`, `L349-L355`).
- Advanced raw recovery is retained: an external persisted thread is resumed and cursor-level events are queried successfully (`L329-L345`).
- The ride contains no credential values or secret leakage. IDs, paths, prompts, outputs, and honesty tiers are sufficient to explain the measured records.

## UC1–UC10 coverage

“Stage 1” means a separately tracked earlier run, not executor-transcript evidence. “Deterministic” means a test/fixture lane, not a real-provider measurement.

| Use case | Status | Evidence and judgment |
|---|---|---|
| UC1 | realized | Synchronous prose and prompt-file starts: `executor-transcript.md:L17-L31`. Actual Claude Code use is separate Stage 1 evidence: `claude-caller/validated-common-evidence.json:L2-L17` and `claude-caller/summary.json:L4-L18`. |
| UC2 | realized | Name-only follow-up retains session/thread/cwd/model/effort/access: `executor-transcript.md:L33-L39`; separate Stage 1 corroboration: `common-journey/transcript.jsonl:L1-L2`. |
| UC3 | realized (Stage 1 live) | Five concurrent starts/results and one daemon: `five-workers/transcript.jsonl:L1-L13`, summarized at `five-workers/summary.json:L5-L74`. |
| UC4 | realized | Complete focused active timeout/status/messages/steer/interrupt sequence: `executor-transcript.md:L244-L307`; idle race remains at `L95-L101`. |
| UC5 | realized | Non-destructive stop and same-session/thread restart: `executor-transcript.md:L167-L179`; separate Stage 1: `common-journey/transcript.jsonl:L5-L7`. |
| UC6 | realized | Live initial goal, progress, pause/show, durable history, and typed-unavailable limits: `executor-transcript.md:L54-L76`, `L205-L242`, `L311-L318`; separate Stage 1 native evidence: `native-proxies/transcript.jsonl:L1-L6`. |
| UC7 | realized | Explicit instance throughout and environment-selected source at `executor-transcript.md:L185-L191`; neither common path requires raw socket/state arguments. |
| UC8 | realized | Worker metadata proves fixed cwd/model/effort/access (`executor-transcript.md:L17-L31`); separate Stage 1 live enforcement is `access-schema/transcript.jsonl:L1-L2`. |
| UC9 | realized (mixed live/deterministic) | Live name/model/timeout/active refusals: `executor-transcript.md:L109-L155`, `L246-L262`, `L320-L327`. One-object output, startup failure, and malformed-state preservation are deterministic lanes: `tests/codex-worker/test_rpc_cli.py:L817-L837`, `tests/codex-worker/test_instance.py:L118-L127`, and `tests/codex-worker/test_models_registry.py:L247-L258`; the Stage 1 full-suite receipt is `.superdev/sdd/task-8-report.md:L64-L69`. |
| UC10 | realized | Existing raw model/session/turn/socket flows: `executor-transcript.md:L146-L182`; successful external-thread resume and cursor events: `L329-L345`. |

## AH1–AH12 coverage

| Acceptance hint | Status | Evidence and judgment |
|---|---|---|
| AH1 | realized (Stage 1 live for Claude context) | Executor start: `executor-transcript.md:L17-L23`; separate Claude caller: `claude-caller/validated-common-evidence.json:L2-L17`. |
| AH2 | realized | Stable immutable configuration across first/follow-up turns: `executor-transcript.md:L17-L23`, `L33-L39`. |
| AH3 | realized (Stage 1 live) | `five-workers/transcript.jsonl:L1-L13`; `five-workers/summary.json:L5-L74`. |
| AH4 | realized | Active observation, narration, steer, interrupt, terminal state, and idle race: `executor-transcript.md:L244-L307`, `L95-L101`. |
| AH5 | realized | Preserved stop and same-thread restart: `executor-transcript.md:L174-L179`. |
| AH6 | realized | Native goal/progress/history and honest unavailable limits: `executor-transcript.md:L54-L76`, `L205-L242`, `L311-L318`. |
| AH7 | realized | Explicit and environment-selected non-Claude instances: `executor-transcript.md:L185-L191`, plus explicit focused instance at `L203-L207`. |
| AH8 | realized (Stage 1 live enforcement) | Reported policy: `executor-transcript.md:L17-L31`; separate enforcement: `access-schema/transcript.jsonl:L1-L2`. |
| AH9 | realized (mixed live/deterministic) | Live one-object timeout/turn-active/name/model refusals: `executor-transcript.md:L109-L155`, `L246-L262`, `L320-L327`. Deterministic one-object/startup/malformed-state receipts: `tests/codex-worker/test_rpc_cli.py:L817-L837`, `tests/codex-worker/test_instance.py:L118-L127`, `tests/codex-worker/test_models_registry.py:L247-L258`; prior full-suite pass: `.superdev/sdd/task-8-report.md:L64-L69`. |
| AH10 | realized (live + deterministic, explicitly separated) | Live schema result and honest metrics: `executor-transcript.md:L25-L31`, `L207-L213`; separate Stage 1 schema: `access-schema/transcript.jsonl:L3`. Multiple-final ordering and null-phase fallback are deterministic assertions at `tests/codex-worker/test_projection.py:L17-L26`, `L55-L61`, confirmed by the evaluator's five-test re-drive above. |
| AH11 | realized (deterministic only) | Missing/zero-byte owner-only initialization and non-empty malformed preservation are asserted at `tests/codex-worker/test_models_registry.py:L57-L65`, `L247-L258`; owner rejection at `L295-L310`. All passed in the evaluator's focused deterministic re-drive. No claim is made that these are real-provider commands. |
| AH12 | realized | Existing advanced paths and explicit-socket status/shutdown: `executor-transcript.md:L146-L182`; successful raw external-thread resume and cursor events: `L329-L345`; public PATH launcher is invoked from `/tmp` in `L157-L164`. |

## Final operator judgment

The product surface is low-friction on the frequent path, guarded and actionable on active-work collisions, non-destructive in lifecycle operations, honest about unavailable capacity/tokens, and still recoverable at the raw layer. E1/E2 evidence cleanup is complete; PASS remains valid without another product change or live re-ride.
