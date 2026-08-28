# D12 focused reride — evaluator verdict

**Verdict: PASS**
**Candidate:** `8c0a639feee5503bb46c818859adb24d7ee7ce99`
**Evidence judged:** the complete `executor-transcript.md` in this directory, the prior
global-install checkride, and the D12 code/spec/test delta
**Evaluator role:** independent judgment only; no code, install, release, or current-user
state changes

The replacement executor evidence closes all four findings from the prior evaluation.
The focused D12 ride is reconstructable, honestly labelled, and sufficient to gate the
current candidate.

## Acceptance table

| Mechanism | Result | Operator evidence |
|---|---|---|
| Real old managed peer and current raw refusal | PASS | The old package installs into and resolves from the private UV tool; while its source is retained, `rev-parse` and two successful byte comparisons tie it to `13206ef1dbdf3a87bda38740aac2aa181ceeb5ac`. The old daemon starts as PID 80461 without `worker_version`. After current HEAD is installed, both `model list` and `session list` return one exit-1 `-32038 tool_version_mismatch` object from the same selected endpoint with `actual_version: null`. The second refusal establishes that the old peer remains selected; neither raw command autostarts or replaces it. |
| Deliberate replacement and durable preservation | PASS | Only explicit `daemon start` replaces the incompatible peer, changing PID 80461 to PID 80522 and reporting immutable `worker_version: 7.10.0`. The sentinel SHA-256 is identical before and after, and runtime-only stop reports `durable_state: preserved`. |
| No target RPC before mismatch | PASS | The fixture peer is explicitly labelled **SIMULATED** and the current CLI subprocesses **MEASURED**. Cumulative method-log readbacks contain one and then two `daemon/status` calls only; neither `model/list` nor `session/list` reaches the peer. Both operator commands return the typed mismatch and no autostart occurs. This fixture corroborates the mechanism and is not presented as a production daemon. |
| Loaded-plugin-root skew and local precedence | PASS | A loaded `0.0.1` root against installed `7.10.0` returns exit 1 / `-32038`, identifies both versions, gives coordination and runnable recovery actions, and leaves the socket absent. Invalid worker syntax still returns exit 2 / `-32602 invalid_params` before the compatibility guard. Mismatched foreground `daemon serve` also refuses. |
| Exact-root foreground lifecycle | PASS | With literal `CLAUDE_PLUGIN_ROOT` equal to the candidate worktree and private UV/HOME/runtime roots, foreground `daemon serve` starts PID 91395, status reports `worker_version: 7.10.0`, shutdown is accepted, and the background wait exits 0. |
| Version-audit failures and success | PASS | The honestly labelled simulated manifest split shows seven `7.10.0` declarations and one `6.6.6` declaration and exits 1. The stale README fixture visibly contains `7.9.x`; audit exits 1 with `expected 7.10.0 or 7.10.x`. The real candidate audit exits 0 with all eight declarations synchronized at `7.10.0`. |
| Cleanup and non-destructive boundaries | PASS | Successful daemon lifecycles have matching stop/shutdown/wait evidence. The old-package and exact-serve roots have literal exit-0 deletion and absence records; an evaluator read-only check also found every named focused/exploratory temporary root absent. All UV tool, HOME, state, and runtime paths used for this reride are isolated; no current-user UV tool or durable worker state was selected. |

## Ledger and reconstructability

- **78** literal event objects parse as JSON without repair or elision.
- Exit distribution is exactly **65 exit 0, 10 exit 1, 3 exit 2**.
- No event has the former leading `+` defect.
- Exit-1 records are the intended compatibility/audit refusals. Exit-2 records are the
  local invalid-parameter result and two retained exploratory setup failures.
- MEASURED real subprocesses, SIMULATED fixtures, and measured fixture-log readbacks are
  distinguished explicitly.
- Earlier failed archive/layout and mutation attempts remain visible as incident history.
  They are not used as substitutes for any passing acceptance row above.

## Prior findings disposition

| Finding | Disposition |
|---|---|
| F1 — incorrect counts and leading `+` records | CLOSED: 78 valid events, 65/10/3, no leading `+`. |
| F2 — missing literal `13206ef` provenance | CLOSED: exact revision plus successful byte comparisons and private UV ownership/version evidence. |
| F3 — exact loaded-root success asserted only | CLOSED: literal `CLAUDE_PLUGIN_ROOT` accompanies install, serve, status, shutdown, and successful wait. |
| F4 — old temporary root retained | CLOSED: literal deletion and absence check; evaluator independently confirms absence. |

## Acceptance consequence

**AH6 and current HEAD `8c0a639` are acceptance-gated: PASS.** Combined with the prior
global-install checkride PASS, UC1–UC4 and AH1–AH7 have operator-level acceptance
evidence. The retained exploratory failures are diagnostic history only and do not carry
this verdict.

## Observations -> backlog

None new. This focused reride exposed evidence-recording defects that were corrected in
the checkride artifact; it did not reveal a remaining product UX issue requiring a new
scenario-intent or backlog record.
