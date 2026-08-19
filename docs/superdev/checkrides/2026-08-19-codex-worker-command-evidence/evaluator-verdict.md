# Codex worker command checkride evaluator verdict

Date: 2026-08-20
Final candidate product SHA: `b4ca0c9a5243a8e9d2405f663f9ddd4f7ed0ac66`
Sole final executor evidence: `docs/superdev/checkrides/2026-08-19-codex-worker-command-evidence/executor-final-transcript.md`
Final executor count: **47 records — 35 happy, 12 refusal**
Role: CHECKRIDE EVALUATOR (judgment only; no product edits)

The historical `executor-transcript.md` is retained only as a precursor. It is not used as final executor evidence. The final transcript identifies 16 copied focused-source records from `ffa24e7`, 25 fresh records at `b4ca0c9`, and 6 candidate-SHA focused appendix records (`executor-final-transcript.md:L3-L10`, `L166`, `L505-L519`). No command was re-driven in this evaluation because the appendix directly resolves the two prior doubts.

## VERDICT: PASS

I would hand this surface to the operator. All 47 records are reconstructable and correctly counted. The candidate appendix directly proves both `b4ca0c9` review fixes through public output, preserves the runtime non-destructively, and closes the prior final-evidence block. Prior B1–B3/A1–A2 and task-review Critical/Important surface concerns are closed; A3 remains only an accepted formatting advisory.

## Final blocker closure

### FB1 — closed: schema-bearing effort recovery is complete and non-executable

F26 supplies the exact schema fixture and literal invocation with `--output-schema`, raw Luna, and unsupported `ultra` effort (`executor-final-transcript.md:L509-L523`). The exit-1 refusal preserves model and `supported_efforts`, returns structured `schema_retry` requiring the caller's original `--output-schema` file, and has `next_actions: []` (`L524-L530`). It cannot silently advertise a retry that drops the schema. The task-review Critical concern is closed.

### FB2 — closed: native pause preserves authoritative budget/status semantics

F27 creates the goal with a `50000` budget (`executor-final-transcript.md:L532-L543`). F28 shows authoritative `active`, budget `50000`, usage `8422` (`L545-L556`). F29 sends only `goal set --status paused`; the response is `paused` with the same `50000` budget and unchanged authoritative usage (`L558-L569`). F30 independently confirms the same paused/budget state (`L571-L582`). The task-review Important concern is closed.

### FB3 — closed: final evidence and summary now agree

The sole final transcript now contains the candidate appendix and reconciles 47 records as 16 + 25 + 6 (`executor-final-transcript.md:L505-L519`). F31 stops the candidate runtime with `durable_state: preserved` and exit 0 (`L584-L595`). The summary's PASS is supported.

## Remaining blocking findings

None.

## Advisories

### A3 — compact default JSON remains an intentional tradeoff

Default output is dense one-line JSON, especially raw `turn wait` (`executor-final-transcript.md:L453-L464`). It is complete and machine-readable, `--pretty` exists, and this remains advisory rather than blocking.

### A4 — fresh record numbering is non-sequential but reconstructable

The fresh section jumps from F18 to F20, then F19b, then F21 (`executor-final-transcript.md:L401-L440`). The final declared count is nevertheless correct: 16 copied + 25 fresh + 6 candidate-focused = 47, with 35 Happy and 12 Refusal labels (`L505-L507`). Renumbering would improve scanning but is not necessary for trust.

## What passed in the 41-record audit

- Every counted record has a literal invocation, complete stdout, explicit stderr (including `(empty)`), exact exit, and Happy/Refusal label. No material output is elided.
- Count reconciliation passes: copied records are 12 happy/4 refusal; fresh records are 18 happy/7 refusal; candidate appendix records are 5 happy/1 refusal; total 35/12 (`executor-final-transcript.md:L10-L163`, `L166-L507`, `L509-L595`).
- Common happy paths include stopped status, prose start, prompt-file/schema/read-only start, short follow-up, status/messages/history, non-destructive stop, and same-thread restart (`L168-L257`, `L375-L412`).
- Refusal paths include timeout-active, turn-active, limits-unavailable, effort-unsupported, duplicate/missing names, local validation, and idle control (`L51-L134`, `L259-L360`).
- Advanced compatibility includes raw resume/events in the copied records and fresh model/session/turn/socket status/shutdown (`L136-L152`, `L362-L373`, `L414-L490`).
- Provenance/IDs are explicit; metrics label their source or unavailability; capacity stays explicitly unknown; stop preserves durable state.
- No credential, authentication token, private key, or other secret is exposed. The long PATH and the raw worker's skill-file read are environment/debug data, not secrets.

## Prior review history retained

### Historical BLOCK at `e5e8c8a`

- B1: an over-budget `goal set --status paused --token-budget ...` returned authoritative `budgetLimited`, initially interpreted as a failed pause.
- B2: overlapping `run` surfaced generic `codex_failure` without named recovery.
- B3: affected control commands were summarized instead of captured.
- A1/A2: limits lacked explicit no-inference details; unsupported effort lacked executable recovery.
- A3: compact JSON was noted as terminal-reading friction.

### Focused repair/PASS at `ffa24e7`

- B1 closed by a below-budget status-only pause and confirming show; the contract now explains provider budget precedence.
- B2 closed by typed `-32004 turn_active` with full known identity and status/messages/steer/interrupt actions.
- B3 closed by 16 complete focused records.
- A1 closed with `capacity: unknown` / `inference: do_not_infer`; A2 closed for schema-free requests with a shell-safe corrected action; A3 remained advisory.
- Evidence-polish E1/E2 were later closed: SHA/count metadata was normalized, the preliminary already-registered raw-resume refusal was correctly classified, and deterministic AH10/AH11 receipt citations were completed.
- The evaluator ran one focused deterministic command for AH10/AH11: five named tests passed, exit 0. That was deterministic fixture evidence, not real-provider evidence.

### Task-review fix at `b4ca0c9`

- Critical: schema-bearing unsupported-effort recovery must not advertise an executable retry missing `--output-schema`; it now requires structured `schema_retry` guidance.
- Important: the native-proxies pause must send status only and preserve the provider's authoritative budget.
- Both are now proven on the public surface by F26–F30 at candidate SHA `b4ca0c9`; F31 proves non-destructive shutdown.

## UC1–UC10 status

The original use cases remain realized across the 47-record final transcript plus the explicitly separate Stage 1/deterministic lanes. Candidate-specific coverage of both later review fixes is now complete.

| Use case | Status | Final evidence |
|---|---|---|
| UC1 | realized | Synchronous prose and prompt-file starts: `executor-final-transcript.md:L181-L218`; real Claude caller remains separate Stage 1 evidence. |
| UC2 | realized | Short name-only run and same-identity restart: `L207-L218`, `L388-L399`. |
| UC3 | realized (separate Stage 1 live) | Five-worker transcript/summary remain the measured five-worker evidence; no capacity inference. |
| UC4 | realized | Active timeout/control and idle race: `L51-L114`, `L336-L360`. |
| UC5 | realized | Preserved stop and same-thread restart: `L375-L399`. |
| UC6 | realized | Goal/history/limits behavior exists at `L12-L49`, `L116-L125`, `L246-L257`; candidate-SHA status-only pause preserves budget at `L532-L582`. |
| UC7 | realized | Explicit and environment-selected instances: `L168-L179`, `L401-L438`. |
| UC8 | realized | Exact Terra/full and Sol/read-only/cwd metadata: `L181-L205`; policy enforcement remains separate Stage 1 live evidence. |
| UC9 | realized | Typed refusals: `L51-L134`, `L259-L360`; candidate-SHA schema-bearing unsupported-effort refusal is complete at `L509-L530`. |
| UC10 | realized | Raw resume/events and fresh advanced model/session/turn/socket operations: `L136-L152`, `L362-L490`. |

## AH1–AH12 status

AH1–AH12 remain realized at their designed live/deterministic lanes, now including final-candidate public receipts for AH6's budget-preserving pause and AH9's schema-safe retry.

| Hint | Status | Judgment |
|---|---|---|
| AH1 | realized (Stage 1 live for Claude context) | Final transcript supplies common start; Stage 1 supplies the real Claude caller. |
| AH2 | realized | Stable identity/configuration across run/restart at `executor-final-transcript.md:L207-L218`, `L388-L399`. |
| AH3 | realized (Stage 1 live) | Exactly five concurrent named workers; five only. |
| AH4 | realized | Complete active and idle controls at `L51-L114`, `L336-L360`. |
| AH5 | realized | Non-destructive stop/restart at `L375-L399`. |
| AH6 | realized | Native goal/history/limits exist; candidate-SHA show/set/show preserves budget and returns paused at `L545-L582`. |
| AH7 | realized | Explicit/environment selectors at `L401-L438`. |
| AH8 | realized (Stage 1 live enforcement) | Metadata at `L181-L205`; separate enforcement transcript remains labeled Stage 1. |
| AH9 | realized | Refusal vocabulary is broad; candidate-SHA schema retry is typed, actionable, and non-executable at `L519-L530`. |
| AH10 | realized (live + deterministic) | Schema success/metrics are live; multi-final/null fallback remain explicitly deterministic. |
| AH11 | realized (deterministic only) | Atomic owner-only initialization and malformed preservation remain fixture/test evidence. |
| AH12 | realized | Raw recovery/events and advanced compatibility are present at `L136-L152`, `L362-L490`. |

## Final operator judgment

The 47-record final transcript is handoff-ready. It covers the frequent common path, refusal recovery, non-destructive lifecycle, advanced compatibility, and both candidate-specific review fixes with complete public outputs. UC1–UC10 and AH1–AH12 are all realized, with Stage 1 and deterministic lanes still honestly distinguished.
