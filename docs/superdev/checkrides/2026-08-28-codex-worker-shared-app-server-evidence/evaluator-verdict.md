# Codex worker shared app-server — evaluator verdict

**Current status:** **PASS — operator-ready**

**Current frozen behavioral candidate:** `c826a1a394f170e94d0c22b99d8359dc2ac08850`

**Original verdict behavioral candidate:** `8dbe8e0`

**Evidence-only follow-up:** `f0e7340` (test/audit only; no candidate behavior change)

**Evaluator role:** independent operator-perspective judgment; no product or executor-transcript edits

**Focused command reruns:** none

The original verdict and intermediate reevaluations below are preserved as history. The latest
current-candidate reevaluation is appended last. Candidate `c826a1a` preserves the corrected
degraded force path, adds bounded complete healthy force impact, and reconciles AH8 plus the
literal public danger help. No blocking finding remains.

## Blocking findings

### 1. Blocking · DESIGN-DOC — typed operational refusals use the internal-error exit code

The governing Python canon's operator-experience law assigns exit `1` only to an internal
bug and exit `3` to a typed operational refusal with a runnable remedy
(`skills/engineering-patterns/python-patterns.md:133-140`). The companion CLI surface instead
locks typed refusals to exit `1`
(`docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-cli-surface.md:19-22`), and the
candidate implements that conflicting contract.

Literal examples include `turn_not_active` at `executor-transcript.md:70-74`,
`address_in_use` at line 89, `service_busy` at line 93, `timeout_active` at line 136,
`service_config_conflict` at lines 214-215, and `daemon_stopped` at line 219. Each is an
expected operational condition, but each exits `1`. The transcript's completed-command
distribution reconstructs as 16 exit-1 results, and these records are not internal crashes.

Why this matters: shell callers cannot distinguish a deliberately handled operational state
from a product defect, precisely the distinction the binding contract reserves. The behavior
and CLI surface must be reconciled with the governing `0/1/2/3` map through the design-doc
path; silently preserving the companion's contradictory exit map is not acceptable.

### 2. Blocking — `session resume` is coupled to unrelated global inventory and loses the selected identity

`codex-worker session list` and `session show` first return the selected session/thread and a
copyable resume route (`executor-transcript.md:188-189`). The immediately following
`codex-worker session resume --session 8e195bfa-…` exits `1` with
`kind: codex_failure`, reason `service_status_failed`, and
`active inventory turn identity is ambiguous`; it replaces every known ID with `null` and
returns `next_actions: []` (`executor-transcript.md:190`).

The failure is explained by the candidate mechanism, not by the selected session: raw-family
dispatch calls `_managed_raw_endpoint()`
(`skills/subagent-driven-development/scripts/codex_worker/cli.py:452-459,754-759`), which asks
for full service status; service status enumerates every active thread
(`skills/subagent-driven-development/scripts/codex_worker/facade.py:700-717`); and one
ambiguous `thread/read` in that global inventory fails the whole operation
(`skills/subagent-driven-development/scripts/codex_worker/broker.py:545-612`). Thus an unrelated/transient
active-inventory row can prevent an exact selected-session resume before the resume RPC is
attempted.

Why this matters: the operator supplied an unambiguous durable session, yet receives neither
that identity nor an attach/resume fallback. This violates R5's partial-failure identity and
runnable-route guarantee and R10's retained session family
(`docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md:41,46`). It is a blocking frequent-path failure, not merely
an awkward diagnostic.

### 3. Blocking — several refusal paths do not give a runnable recovery command

The refusal schema is structurally consistent, but its recovery content is not reliably
actionable:

- Default-port collision reports the exact listener but offers only `codex-worker daemon
  status` (`executor-transcript.md:89`). Locked decision D3 explicitly promises a runnable
  explicit-override action
  (`docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-decisions.md:44-55`).
- Active-work restart correctly preserves work, but emits `codex-worker status --name
  <worker>` even though `details.active[0].worker` contains the exact name
  (`executor-transcript.md:93`). That template is not a copyable command.
- Managed raw `session start/list` while stopped returns
  `recovery: "run codex-worker --socket … daemon serve"`
  (`executor-transcript.md:205-206`). `run` is prose rather than a shell command, the route
  points at the hidden foreground `daemon serve`, and it bypasses the ordinary managed
  `codex-worker daemon start` recovery path.
- A stopped named worker emits `codex-worker run --name remaining-1d81fddc --prompt <text>`
  (`executor-transcript.md:219`). `<text>` is an unevaluated placeholder (and shell
  redirection syntax), not a runnable remedy.

Why this matters: these are exactly the points where an operator needs the product to state
the next safe action. Copying the advice either fails, invokes an internal mechanism, or
does not solve the collision. This violates the canon's runnable-remedy law and leaves the
operator stuck.

### 4. Blocking · DESIGN-DOC — public help and derived-number provenance do not satisfy the governing law

The fresh ride was explicitly scoped to dangerous maintenance help
(`docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-checkride.md:22-35`), but its only help invocation
is the hidden/internal `codex-worker daemon serve --help`
(`executor-transcript.md:176`). That output has no `Limits:` block. There is no literal
`daemon stop --help` or `daemon restart --help` record, and source inspection found no
`Limits:` block on any candidate command; the parser only supplies danger prose for
stop/restart (`skills/subagent-driven-development/scripts/codex_worker/cli.py:181-193`).

The same law forbids an unexplained derived figure
(`skills/engineering-patterns/python-patterns.md:139-142`). `daemon status` emits naked
`worker_count` and `active_turn_count` without the inventory rows, basis, or a
`source/availability` wrapper (`executor-transcript.md:156,180,191,218`). In contrast, the
completion metric envelopes at lines 136 and 179 do carry useful `value`, `source`, and
`availability` fields; the status surface should meet the same explainability bar.

Why this matters: dangerous capabilities must declare their limits at the point of use, and
operators must be able to reconstruct counts before trusting maintenance decisions. Because
the published companion surface currently specifies the conflicting exit behavior and naked
status schema, the surface/design docs must be amended together with behavior rather than
patched around silently.

### 5. Blocking — the fresh checkride matrix is incomplete and internally inconsistent

Task 5 requires a fresh executor to drive every common/raw family one command at a time,
including successful `session start/list/show/resume`, every `turn` control, the composed
journey, and dangerous maintenance help (`.superdev/sdd/task-5-brief.md:90-98`; checkride
scope at
`docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-checkride.md:22-35`).
The transcript does not meet that gate:

- The fresh continuation's managed raw `session start` and `session list` fail because the
  service is stopped (`executor-transcript.md:205-206`). A later socket-bound list succeeds,
  but there is no successful fresh-executor raw session start, and the fresh resume at line
  190 fails.
- There is no fresh-executor successful `turn start`, `turn wait`, `turn status`, `turn
  steer`, or `turn interrupt`; only `turn events` is present at line 38. Public dangerous
  stop/restart help is also absent.
- The constructed second-client continuation has only a `command_start` whose argv invokes
  `codex-worker` with the Python executable as its subcommand, followed 90 seconds later by
  a literal `kind: not_run`; it has no terminal `command` record, stdout/stderr, or exit
  (`executor-transcript.md:221-222`). The narrative nevertheless says “Not run … None” while
  acknowledging that record (`executor-transcript.md:160-162`).
- The headline's `139` completed commands and `121/16/2` exit distribution do reconstruct:
  136 JSON `command` records are `118/16/2`, plus the three exit-0 cleanup corrections at
  lines 232-254. But the unmatched attempted invocation makes 140 actual attempts and is
  absent from the exit distribution. The headline also claims two live `codex_failure`
  results (`executor-transcript.md:11`); only one literal `codex_failure` record exists, at
  line 190.
- The initial cleanup correctly refuses a PID mismatch (`executor-transcript.md:224`), and
  the correction plausibly proves token/path equality before force-stopping only the isolated
  runtime. But its asserted “full command records” replace the assertion, environment, and
  repeated status invocation with placeholders and omit recorder timing/substrate fields
  (`executor-transcript.md:227-254`). The cleanup safety claim is credible; the description of
  these three records as literal and exact is not reconstructable.
- All successful live services use explicit alternate loopback ports. The transcript proves
  stopped-state default projection at line 23 and occupied-default refusal at line 89, but
  never the AH4 live happy path: start, caller exit, later attach/run, and same-thread resume
  at fixed port 4500
  (`docs/superdev/specs/2026-08-28-codex-worker-shared-app-server-design.md:459-463`).

The tracked real-Claude summary claims every required family
(`real-claude-caller-summary.json:16-38`) and hash-pins an ignored 178-line raw transcript
(lines 54-58). I inspected that local raw file: its SHA-256 and line count match, and it
contains 26 Bash tool uses with 26 successful tool results covering the listed families.
That is valuable corroboration, but the raw transcript is ignored/untracked and the tracked
summary does not contain the literal commands and outputs. It cannot substitute for the
fresh executor matrix or the checkride requirement to commit a reconstructable verbatim
transcript (`skills/engineering-patterns/process-discipline.md:15-24` and
`skills/cli-checkride/SKILL.md:37-47`).

Why this matters: an evaluator can reconstruct the behavior today only because the ignored
local raw file still exists. A later checkout cannot reproduce the claimed family-level
evidence, and several expressly required rows count as NOT RUN under the process law.

## Evidence accepted despite the failed constructed continuation

- **Second-client shared control is proved elsewhere.** The tracked common/attach literal
  record constructs an independent real `CodexConnection`, resumes the exact thread, starts
  a turn, receives an accepted steer and interrupt, and records authoritative
  `turn/started`/`turn/completed: interrupted` events
  (`scenarios/common-attach/transcript.jsonl:8`). The wrapper then observes that turn through
  `turn events` (line 9). The tracked migration/callback lane independently repeats same-thread
  resume/control (`scenarios/migration-callback-shared-control/transcript.jsonl:14`), while
  the summary binds the proactive event to the original callback destination and labels its
  simulated security/artifact sublanes
  (`scenarios/migration-callback-shared-control/summary.json:137-194`). Therefore the malformed
  line-221 attempt is an executor-record defect, not evidence that R3 itself is absent.
- **Identity isolation and fanout are credible.** The exactly-five tracked lane records five
  distinct global names and independent caller environments without crossed files, events,
  or callback destinations. Common commands from unrelated working directories return exact
  worker/session/thread identities and copyable attach routes.
- **JSON shape and honesty are mostly strong.** Completed non-help/non-version product RPC
  and local-usage invocations emit one JSON object on stdout, including the two usage refusals at
  `executor-transcript.md:177-178`; completion metrics carry explicit measured/derived/
  unavailable provenance. Fixture-only lifecycle, security, artifact, and replay checks are
  explicitly labeled `SIMULATED production ... fixture`. No simulated result is presented as
  measured.
- **No credential exposure was found.** Evidence records environment names rather than
  values; callback tokens are `[REDACTED]`; tracked scenario secret scans report no
  violations. Upstream client records include host paths/installation metadata, but no bearer,
  API-key, OAuth, or callback token value was found.
- **Persistent-service and maintenance mechanisms are substantively demonstrated.** Caller
  exit does not own the service; later lookup/control works; normal skill guidance contains no
  routine stop; active work blocks maintenance; `--force` is explicit; the occupied peer and
  unknown-port peer are preserved; restart retains durable mappings. Harness teardown stops
  only isolated owner-token fixtures.
- **The post-candidate orphan erratum adequately closes current cleanup state.** It openly
  retracts the earlier incomplete residual claim, identifies four exact deterministic-fixture
  app-server orphans through UID/PPID/PGID/argv/environment/socket/artifact evidence, revalidates
  before SIGTERM, removes exactly four roots/sockets, reports zero matching residuals, and adds
  an app-server PID/private-socket regression guard
  (`docs/superdev/checkrides/2026-08-29-codex-worker-post-candidate-process-audit.md:7-13,15-50,59-70`).
  This correction does not justify the earlier cleanup claim, but it is visible, bounded, and
  adequate closure; no installed/global or legacy service was touched.

## Required re-ride boundary

Do not rerun the whole suite as a substitute for the surface gate. After product/design
correction, re-drive only the affected CLI-contract/refusal/help/status rows, the ambiguous
selected-session resume, the missing successful raw session/turn families, and the fixed-4500
happy persistence journey. Preserve the already accepted common/attach, exactly-five,
callback/migration, unknown-peer, and orphan-audit evidence unless behavior affecting those
lanes changes.

## Observations → backlog

- `live evidence / AH11` · add a bounded live non-loopback listener projection receipt that
  shows exact listener, exposure, and auth provenance · the current live records exercise only
  loopback listeners, so the design's non-loopback honesty claim remains supported by fast
  fixtures rather than an operator-visible ride.
- `live harness teardown` · keep a host-level residual fake-app-server/socket sweep as an
  explicit final gate in addition to per-owner-token cleanup · the post-candidate audit proved
  that a fixture-local cleanup receipt can miss older orphan process groups.
- `tracked evidence minimization` · sanitize non-credential upstream host metadata (local hook
  paths, installation/server identifiers) when it is not necessary to prove control semantics
  · it is not a secret leak here, but it makes the tracked second-client records noisy and more
  host-specific than the operator needs.

---

## 2026-08-29 reevaluation — frozen candidate `194a6c3`

**Result:** **FAIL — the behavioral corrections are plausible and partly ridden, but the
locked D24–D29 evidence gate is not complete.**

**Evidence considered:** the preserved original transcript; the appended same-executor section
at `executor-transcript.md:257-420`; the tracked 26-row Claude command receipt and caller/cleanup
summaries; D24–D29; the current design, CLI surface, Task 5 brief, process discipline, and Python
canon; and the already accepted tracked scenario records and orphan audit.

**Focused command reruns:** none. I performed one offline parser diagnostic over the eleven
distinct recovery commands literally emitted by the appended exit-3 rows; all eleven parse with
the candidate's public parser without service or network contact. That diagnostic is not a
substitute for a missing live row.

### Corrected claims that now reconstruct

- The appended JSONL contains 126 objects: 102 terminal `command` records, seven
  `command_start` records, seven cleanup records, nine callback frames, and one lifecycle scope
  record. Each `command_start.attempt_id` has exactly one matching terminal record with identical
  argv. Therefore this reride reconstructs as **102 attempts, 102 completions, zero unmatched / NOT
  RUN, and exits `0:94, 1:0, 2:0, 3:8`**. The seven starts are not seven additional attempts because
  they are the start halves of those seven terminal records. There are no duplicate terminal
  attempt IDs and no appended `codex_failure` record.
- All eight observed operational refusals exit 3 as D24 requires: five `turn_not_active` rows,
  one `address_in_use` (`executor-transcript.md:335`), one `service_busy` (line 339), and one
  `timeout_active` (line 382). Their eleven distinct next-action commands contain no angle
  placeholder or `--force`, and all parse offline. The collision supplies an explicit alternate
  start, busy maintenance names the exact worker, and timeout preserves name/session/thread/turn
  IDs.
- Every appended daemon-status/count-bearing result has `value`, `source`, `availability`, and
  `basis`. Across the 20 count-bearing results, every worker value equals the unique active+idle
  names in its basis and every active-turn value equals the number of basis items. This closes the
  count-provenance half of D27.
- The fixed-default fixture starts a real service on `ws://127.0.0.1:4500`, records PID 5427
  across later independent CLI invocations, returns copyable attach/resume routes, resumes the
  same session/thread, runs a second completed turn on that thread, and only then performs
  supervised fixture teardown (`executor-transcript.md:410-419`). This closes the fixed-port
  caller-exit/persistence/same-thread AH4 gap.
- The tracked Claude receipt is now literal rather than hash-only: `real-claude-commands.jsonl`
  has 26 sequential, unique attempt/terminal IDs and 26 exit-0 command/output rows covering the
  summary's 26-command family accounting. Its SHA-256 is
  `e50cf2e337f45f1237747b84cf2d54e7b1cba3126473eb5b0c1a92f9b4b0a7f0`, exactly the summary's
  tracked hash. The cleanup file hash also matches its summary. This closes the historical
  literal-Claude-receipt part of D28, but those commands predate D24–D29 and cannot prove the
  corrected surfaces that those decisions explicitly reopened.
- The prior acceptance of second-client shared control stands. The tracked common-attach record
  and the fresh common-attach row use an independent `CodexConnection` to resume the exact thread,
  start/control it, and expose authoritative events back through the wrapper. The earlier
  malformed second-TUI attempt remains honestly preserved but does not negate the successful
  literal records elsewhere.
- The post-candidate orphan audit remains an adequate bounded correction of the old host state.
  It does not, however, supply D29 measurements for these later seven reride cleanups.

### Remaining exact blocking rows

| Severity / law | Literal record audit | Blocking gap | Minimal correction / reride |
|---|---|---|---|
| **Blocking · DESIGN-DOC · D24** | The current append's exact exit map is `0:94, 1:0, 2:0, 3:8`. Old exit-2 rows 177–178 and old exit-1 internal/operational rows belong to the superseded candidate. | The touched four-way mapping is not literally proven for current-candidate exit 1 (uncaught or peer-reported internal) or exit 2 (local usage). Unit tests are the floor, not the live surface gate. | In an isolated fixture, append one deterministic peer/internal-fault CLI row that exits 1 and one local parser/usage row that exits 2; each must preserve the one-JSON stdout law where applicable. No broad scenario rerun is needed. |
| **Blocking · DESIGN-DOC · D25 / Task 5** | After line 257, the only public raw-family commands are `turn events` at line 283 and `session resume` at lines 384 and 414. The recovery resume succeeds for its own active thread, but there is no literal construction of an *unrelated ambiguous inventory row*. | The candidate that changed managed raw endpoint selection has no fresh full raw-family ride: no `session start/list/show`, no `turn start/wait/status/steer/interrupt`, and no selected resume while unrelated inventory is demonstrably ambiguous. The historical 26-row Claude receipt predates D25. Therefore the original line-190 `active inventory turn identity is ambiguous` blocker is not literally closed for `194a6c3`. | One fresh isolated raw-family fixture: create/identify an unrelated ambiguous inventory condition, then show exact selected-session resume succeeds with the selected session/thread IDs and attach/resume routes; drive `session start/list/show/resume` and `turn start/wait/status/events/steer/interrupt` one command at a time, including terminal state. If the selected operation itself is deliberately refused, retain its known IDs/routes. |
| **Blocking · D26** | Current collision, busy, timeout, and inactive-turn remedies are literal and parser-valid. No post-line-257 row exercises the formerly bad stopped managed-service remedies at lines 205–206 or the stopped-known-worker remedy at line 219. | D26 explicitly reopened those affected rows. Source/tests cannot establish the operator-visible JSON/exit/remedy contract. | Re-drive only: managed raw command while service is stopped (must exit 3 and point to public `codex-worker daemon start`), and exact stopped-known-worker status (must exit 3 and emit only exact status/attach/resume actions). Parse every emitted command offline and record that result; do not execute a dangerous action. |
| **Blocking · DESIGN-DOC · D27** | The append contains **zero** `--help` commands. The only transcript help remains the superseded hidden `daemon serve --help` at line 176. Candidate tests enumerate 28 leaves, but no literal current-candidate help output exists. | None of the required 28 public leaf `Limits:` blocks is ridden, and the machine-wide/active-refusal/`--force` impact prose for stop/restart is not operator-visible evidence. | Record all 28 public leaf `--help` invocations and exits. Each output must contain `Limits:`; stop and restart must literally contain machine-wide scope, active refusal, and force impact. Help must not contact/start the service. |
| **Blocking · D28 / D29** | All seven appended cleanup rows (for example lines 270, 296, 324, 345, 371, 399, and 419) have the same 13-field compact shape. Each omits `argv`/literal assertion, `elapsed_seconds`, `environment_allowlist`, `stderr`, and `substrate`. None records a pre-stop comparison of owner token, exact fixture/runtime path, and the *currently live* service/app-server PIDs. Line 258 nevertheless claims every appended JSONL row carries those fields. | The new same-executor reride repeats the exact historical-cleanup deficiency D29 says cannot satisfy the final gate. Post-stop equality between `expected_pid` and `observed_pid` is not the required pre-stop ownership/PID authorization. The old orphan audit proves old residual closure, not these teardown mechanisms. | Every replacement fixture above must emit, before any stop/delete, a literal timed owner/path/live-PID assertion record with argv/assertion, stdout, stderr, exit, measured elapsed time, substrate, and environment-name allowlist; then record timed stop/status-after/deletion with the same fields and independent credential-copy cleanup. Preserve old rows as superseded history; do not invent their missing timing. |

These are evidence blockers, not a request for another broad ride or an inferred product rewrite.
The already accepted common/shared-control, five-name isolation, migration/callback, count
provenance, fixed-4500 persistence, literal Claude receipt, and orphan-audit evidence need not be
repeated unless the narrow correction changes those mechanisms.

### Reevaluation observations → backlog

- `checkride recorder / fixture headline` · derive fixture count and field claims from parsed
  records · the appended prose says “six raw fixtures” but contains seven, and says every JSONL
  row has command fields although cleanup/callback/scope rows do not. The records are countable,
  so this is advisory beyond the blocking D29 omission.
- `checkride accounting / publish summary` · append a machine-derived reride accounting footer
  with object-kind counts, attempt/completion matching, unmatched IDs, and exit distribution ·
  the present counts reconstruct exactly, but only after evaluator-side parsing.
- `raw ambiguity receipt` · give the harness an explicit, sanitized assertion record describing
  which thread is selected and which independently created inventory rows are ambiguous · a
  successful resume alone does not prove that D25's triggering condition existed.

---

## 2026-08-29 reevaluation — current candidate `0221217387fa3b43c8d4e1056607bfa4a928e536`

**Result:** **FAIL — three exact evidence gaps remain.**

The current behavioral delta from `194a6c3` is one production line in
`WorkerFacade.status`: an `UnknownSession`/`SessionDetached` stopped-worker path now passes the
already-resolved record into `_stopped_fault`. It does not change CLI parsing, the exit mapper,
managed-raw readiness, help, service lifecycle, or recorder cleanup. I therefore retained prior
literal evidence for those unchanged mechanisms and judged the new stopped-worker rows directly.

**Focused command reruns:** none.

### Prior blocking rows now closed

- **D24 / former row 300 — closed.** The focused help/exit fixture at lines 422–468 has 37
  terminal commands: 35 exit 0, one local removed-`--instance` usage error at exit 2, and one
  typed unsafe-socket refusal at exit 3. The preserved `194a6c3` stopped-worker attempt at line
  555 is a literal one-object `internal_error` / `AttributeError` at exit 1. That row is valid
  evidence of the unchanged internal-error mapping: the current delta removes that particular
  defect but does not touch the mapper. The current stopped-worker row at line 578 confirms the
  corrected condition is now a typed `daemon_stopped` refusal at exit 3 with retained IDs.
- **Full raw/active controls in former row 301 — closed except for the ambiguity trigger below.**
  Lines 503–538 drive `session start/list/show/resume` and `turn
  start/wait/status/events/steer/interrupt`; steer and interrupt both succeed while the second
  turn is active, terminal wait returns `interrupted`, and later controls refuse at exit 3 while
  preserving selected session/thread/turn IDs and attach routes. The selected resume at line 519
  succeeds at line 521 with the exact session/thread and copyable attach/resume commands.
- **D26 stopped-service half of former row 302 — closed.** Line 553 returns a one-object
  `daemon_unavailable` refusal at exit 3 with the exact public recovery
  `codex-worker daemon start`; that exact command later executes successfully at line 580. The
  current stopped-known-worker output at line 578 is also structurally corrected: exit 3,
  `daemon_stopped`, exact name/session/thread IDs, exact listener/routes, no placeholder, and
  three parser-valid public actions.
- **D27 / former row 303 — closed.** Lines 432–459 contain exactly 28 public leaf `--help`
  commands, all exit 0 and all contain `Limits:`. Stop and restart each literally state
  machine-wide scope, active-work refusal, `--force`, and impact on every reported identity.
- **D28 literal command matching — mostly closed.** The focused append contains only terminal
  commands (no unmatched `command_start` or duplicate terminal attempt ID). The five focused
  sections reconstruct as 122 terminal commands with exits `0:110, 1:1, 2:1, 3:10`; the exit-1
  row belongs to candidate `194a6c3`, and the current delta leaves its mapping mechanism
  unchanged.

### Remaining exact blocking rows

| Severity / law | Literal evidence | Why it still blocks | Exact smallest addition |
|---|---|---|---|
| **Blocking · DESIGN-DOC · D25** | The first D25 precondition at line 481 says only that two unrelated sessions exist; its own daemon status at line 479 has `active_turn_count.value: 0` and both unrelated workers idle. The corrected fixture's status at lines 513 and 530 likewise has zero active items. No post-line-422 record contains `active inventory turn identity is ambiguous`. | Two unrelated idle sessions are not the triggering condition from line 190. The successful selected resume at line 521 proves ordinary multi-session selection, but not that strict readiness bypasses a failing/ambiguous global inventory. | In one isolated current-candidate fixture, append only: (1) a literal precondition/full-status row that actually returns the unrelated `active inventory turn identity is ambiguous` failure and identifies the unrelated thread(s), then (2) the immediately following exact selected `session resume` success retaining its session/thread IDs and attach/resume routes. The already complete raw-family/control sequence need not be repeated. |
| **Blocking · D26** | Line 578 advertises three exact stopped-worker actions. `codex-worker daemon start` executes at line 580; `codex-worker status --name known-e2b989` executes at lines 581–582 and honestly repeats `daemon_stopped`. The third advertised action, `codex --remote ws://127.0.0.1:52588 resume 01a04b72-…`, has no command/PTY record anywhere in the current appendix. | The explicit acceptance condition is that every emitted action is executable, not merely parser-valid. The only action capable of actually recovering the durable thread was not driven, so the operator can still be stuck at the final promised route. | Append one literal current-candidate execution of that exact third action with argv/PTY input, visible output, exit or bounded attach-success terminal state, timing, environment-name allowlist, stderr, and substrate. If it cannot recover, fix the advertised action/reason and reride only this stopped-worker refusal plus its actions. |
| **Blocking · D28 / D29 · cleanup safety** | The five focused replacement cleanups at lines 464, 498, 535, 561, and 584 remain compact 13-field summaries without argv/assertion, elapsed time, environment allowlist, stderr, or substrate. Their preceding owner assertions and stop/status commands are timed, but no timed deletion or independent credential-copy cleanup row exists. The latest row is worse: line 584 records `expected_pid:49037`, live `observed_pid:49562`, `pid_verified:false`, `runtime_deleted:false`, and `service_stopped:false`. Line 587 then claims a `daemon stop --force` corrected cleanup while explicitly admitting its literal output was not reconstructed. | D29 requires every replacement fixture's pre-stop authorization and cleanup/deletion to be literally measured. The latest force claim has no ownership assertion bound to PID 49562 before force, no argv/output/exit/timing/substrate/env/stderr, and no post-stop status. This is precisely the dangerous operation for which narrative cannot replace evidence. The earlier post-candidate orphan audit cannot prove these later teardown events. | Do not reconstruct or invent deleted history. For each replacement fixture that remains part of the final evidence, rerun/replace its cleanup with literal timed rows for: owner token + exact root/runtime path + *current daemon and app-server PIDs before stop*; stop/force-stop; stopped status; isolated credential-copy deletion; runtime deletion/residual check. Every row needs argv/assertion, stdout, stderr, exit, elapsed time, environment-name allowlist, and substrate. For the latest fixture specifically, a new ownership assertion must bind the then-live PID before any force action. |

### Accounting correction required with the next append

Line 467 says `attempts 37`, `terminal command rows 37`, `unmatched starts 0`, and also
`NOT RUN 1`. Literal rows reconstruct as 37 attempts/completions and zero unmatched / NOT RUN;
the proposed internal-fault experiment was never represented by a `command_start`. Append a
one-line accounting erratum changing that section to `NOT RUN 0` and explaining that the
unchanged exit-1 mechanism is inherited from line 555. This is part of the D28 evidence
correction and needs no product rerun.

No other accepted scenario needs repeating. In particular, the 28-leaf help matrix, full raw
family/active control, fixed-4500 persistence, shared-client control, status count provenance,
tracked Claude receipt, and stopped-service public recovery remain valid for the current
candidate.

---

## 2026-08-29 final closure reevaluation — current candidate `0221217387fa3b43c8d4e1056607bfa4a928e536`

**Result:** **FAIL — the evidence gate is closed, but the closure ride exposed one blocking
product lifecycle defect.**

**Focused command reruns:** none. I inspected the appended literal records at
`executor-transcript.md:640-827`; I did not drive or alter any service.

### Prior exact blockers now closed

- **D25 / former row 372 — closed.** In the deterministic real-process fixture, sequence 3 at
  line 746 returns the exact full-status failure `active inventory turn identity is ambiguous`.
  The immediately following sequence 4 at line 747 resumes selected session
  `09fc0e56-dcdc-44a8-999c-9bcf922e1764` / thread `thr-fake` successfully and returns literal
  attach/resume routes. The non-reordered capture check at line 754 proves the failing
  `thread/read` targeted different thread `unrelated-active`. This is honestly labeled mechanism
  evidence over the fake app-server, not a claim about provider edge behavior. The previously
  accepted full raw-family and active steer/interrupt ride remains unchanged.
- **D26 advertised-action gap / former row 373 — closed.** The stopped known-worker refusal at
  line 763 returns exit 3, exact name/session/thread IDs, and exact recovery command
  `codex --remote ws://127.0.0.1:55366 resume 01a04b87-595b-7883-a317-275adb3e5b05`.
  After the advertised daemon start at line 764, line 765 executes that exact argv in a bounded
  real Codex 0.150.1 PTY, renders the resumed TUI, receives an ordinary Ctrl-C, and exits 0.
- **D28/D29 / former row 374 — closed as evidence safety.** The explicit map at line 650 replaces
  old rows 464, 498, 535, 561, and 584. Each fresh fixture records a timed pre-stop assertion
  binding redacted owner token, exact root/runtime, current daemon and app-server PID/argv,
  private socket, listener, and UID; then timed stop, stopped status, inode-bound isolated
  credential-copy deletion, and owned-runtime deletion/residual check. Each command carries argv,
  cwd, elapsed time, environment-name allowlist, exit/return code, stdout, stderr, timestamp, and
  substrate. The D25 fixture has the same complete chain. In the D26 failure fixture, lines
  767 and 770-773 bind the exact owned processes and PGID before maintenance/fallback; only then
  does line 774 send SIGTERM to process group 76067. Lines 775-777 verify stopped state, remove
  the inode-bound credential copy, and delete the owned runtime with `residual:false`. This
  safely closes the fixture despite product cleanup failure and does not touch an installed,
  legacy, global, or unknown service.
- **D24/D27 and other retained rows remain valid.** The prior current-candidate appendix still
  supplies exactly 28 exit-0 public leaf help rows with `Limits:` and the required danger prose.
  Its current exit 0/2/3 rows plus the unchanged mapper's preserved `194a6c3` exit-1 internal
  row prove the four-way mapping. The new stopped-worker behavior and D25 selected-resume change
  do not alter that mapper.

### Literal accounting and hygiene

The scoped closure at lines 650-777 parses to exactly **75 JSON objects: 69 terminal `command`
rows and six `cleanup_completion` rows**. It contains no `command_start` or NOT RUN row; terminal
exits reconstruct exactly as **`0:65, 1:0, 2:1, 3:3`**. All 69 command rows contain every
required command-evidence field. The later, explicitly preserved superseded-failure block at
lines 780-827 is outside that closure count; parsing the complete lines 640-827 yields 99 objects
and 93 terminal commands with exits `0:83, 1:2, 2:2, 3:6`. Thus the closure accounting is exact,
not an omission of those preserved failures.

No credential content appears in the inspected JSONL. Records contain environment variable names,
redacted owner tokens, and credential path/inode identity only; I found no bearer-like authorization
value. Every final replacement fixture reports stopped/closed service state and deleted owned
runtime, including the D26 fallback at lines 775-777. The earlier post-candidate orphan audit is
therefore neither contradicted nor being used as a substitute for these later literal cleanups.

### Exact remaining blocking row — product defect, not evidence gap

| Severity / law | Literal record | Product failure | Smallest fix and reride |
|---|---|---|---|
| **Blocking · PRODUCT · DESIGN-DOC · D8 / D24** | Before maintenance, line 766 reports `ready`, zero active turns, and one idle worker; line 767 binds the exact live daemon/app-server and listener. The syntactically valid `daemon stop` at line 768 then exits **2** as `invalid_params` / `service returned a malformed fault`. After 45 seconds, line 769 still reports daemon PID 76067 in `stopping`. With ownership freshly rebound, supervised `daemon stop --force` at line 772 exits **3** as `codex_failure` / `transport_error: connection closed`, has empty `next_actions`, and does not stop the daemon; line 773 proves PID 76067 remains live. | A safe idle stop is promised supervised maintenance, not local usage. D24 explicitly forbids exit 2 for a syntactically valid request rejected by runtime state. The force path neither delivers its promised stop nor gives a runnable remedy. The executor's exact owned-PGID fallback makes the evidence cleanup safe but cannot turn failed product maintenance into operator-ready behavior. | Fix shutdown after a remote TUI disconnect so idle `daemon stop` returns one success JSON object at exit 0 and reaches `stopped`; fix `daemon stop --force` during the observed stopping/transport-close race so it actually terminates and reports an honest success, or returns the correct typed failure with a runnable remedy without falsely completing. Reride only this D26 lifecycle slice on fresh owned fixtures: real exact remote resume and client exit, pre-stop ready/idle + ownership binding, normal stop + stopped status; and the observed stopping/race force path with fresh pre-force binding + terminal stopped status. No help/raw-family/Claude/common-control reride is needed. |

The normal and forced errors are therefore a new product blocker, not a remaining transcript or
cleanup-proof deficiency. All earlier accepted common-control, fixed-4500 persistence, full raw
family, 28-help, count-provenance, literal Claude, exit-map, and ownership-cleanup rows remain
accepted unless the lifecycle fix changes those surfaces.

### Observations → backlog

- `service shutdown / child-disconnect race` · preserve the shutdown peer's malformed/closed
  transport details internally while projecting the correct D24 class and an actionable public
  result · the present exit-2 `invalid_params` masks a runtime lifecycle defect.
- `checkride accounting / scoped append` · include an explicit line range in every appendix
  accounting statement · the closure's `75` is correct for lines 650-777, while the adjacent
  preserved-failure records make an unscoped lines-640-to-EOF count equal 99.

---

## 2026-08-29 lifecycle reevaluation — candidate `39947a57a19e9275b79537ea98f807941ac0ae51`

**Result:** **FAIL — supported ordinary/concurrent stop is corrected, but supervised force
cannot recover a degraded owned runtime.**

**Focused evaluator reruns:** none. I inspected the 58 appended objects at
`executor-transcript.md:829-914` and the governing D2/D8/D24/D26/D28/D29, CLI maintenance
contract, R7/UC8/AH8, and current candidate delta. I did not drive or alter any service.

### The previous lifecycle blocker is corrected on supported paths

- **Ordinary post-TUI stop passes.** Scenario 1 starts a real Codex worker and exact remote
  resume, records an ordinary Ctrl-C and PTY exit 0 at line 843, then reports the service still
  `ready` with zero active turns at line 844. The timed owner/root/runtime/PID/PGID/socket/listener
  assertion at line 845 precedes `daemon stop`; line 846 returns one success object at exit 0,
  line 847 reports `stopped`, and lines 848-850 prove both owned PIDs and sockets absent, listener
  refused, inode-bound credential copy removed, and owned runtime deleted with no residual.
  This directly closes the product failure previously observed at lines 768-773.
- **Concurrent force plus ordinary stop converges.** Scenario 2 binds the fresh owned daemon and
  app-server before mutation at line 893. Matched attempts `lifecycle-4` and `lifecycle-5` begin
  exact `daemon stop --force` and `daemon stop` operations at lines 894-895. Their terminal rows
  at lines 906-907 both return exit-0 completed results; repeated reads and the final status at
  line 908 are stopped. Lines 909-911 prove no live owned PID/socket/listener and independently
  remove the credential copy and runtime. The two attempt IDs each have exactly one terminal row
  with identical argv.
- All previously accepted D24-D29, 28-help, raw-family, ambiguity-selected resume, exact remote
  PTY remedy, fixed-4500 persistence, shared control, five-name isolation, callback/Claude,
  migration, provenance, and old-row replacement evidence remains valid. The candidate delta is
  confined to lifecycle/degraded-state handling and does not reopen those surfaces.

### The SIGSTOP fault injection is a valid contract probe

The literal `kill -STOP` at line 862 is an artificial, executor-created setup, not a supported
public operation. That does **not** make the resulting condition out of scope. It creates an exact,
owner-bound Codex child that remains live but cannot serve authoritative inventory—the same public
degraded-runtime class produced by a hung child or broken private transport. The governing surface
contains no exception for externally frozen or unresponsive owned children:

- D2 says `codex-worker` starts, health-checks, records, and stops its selected app-server, with
  deterministic stop/recovery as the reason for product ownership.
- D8 selected guarded stop specifically because otherwise recovery depends on manual process
  surgery; supervised force is the exceptional recovery control.
- The CLI contract says force terminates the selected global runtime after reporting impact.
- D24/D26 require an honest typed result and runnable public recovery, not an empty-action failure.

The probe therefore tests the promised ownership/recovery boundary rather than demanding support
for SIGSTOP as a user feature. An operator-ready force path cannot depend on the unhealthy child it
is meant to terminate.

### Exact remaining blocker — product, with a secondary evidence defect

| Severity / law | Literal evidence | Contract failure | Minimal fix and reride |
|---|---|---|---|
| **Blocking · PRODUCT · DESIGN-DOC · D2 / D8 / D24 / D26 · R7 / UC8** | The exact owned child is bound at lines 860-861 and stopped at line 862. Supervised force starts at line 863, but later status rows 865-878 repeatedly exit 3 as `service_status_failed` / `ConnectionClosedError` with null IDs and empty `next_actions`. The owned daemon and child remain. After exact ownership is rebound, a public force attempt recorded by the recovery tool at line 879 exits 3; after the executor reverses SIGSTOP, the literal retry at line 881 still exits 3 with the same empty-action fault. Manual TERM of exact owned process groups at line 882 is required before residual cleanup. | `daemon stop --force` still performs healthy app-server inventory/status work before it can enter owned teardown. When that peer is degraded, force cannot deliver its documented termination/recovery purpose, cannot report a useful degraded/unknown impact, and provides no runnable public route. Requiring manual OS signals is the exact outcome D8 retained public maintenance to avoid. | Make explicit supervised force enter a locally authoritative maintenance state even when Codex inventory is unavailable; represent the impact honestly from durable/last-known identities plus explicit unavailable/unmapped inventory rather than inventing zero; then perform bounded teardown of the already pinned owned daemon/child groups without waiting indefinitely on peer close. Status during teardown must report reconstructable `stopping`/degraded state without querying the broken peer. Verify exact PIDs/sockets/listener absent before returning one exit-0 completion. Reride only a fresh owned degraded-child fixture: prebind identity, deterministically hang/freeze the child, execute one exact force attempt to a terminal row, observe honest concurrent status, verify stopped/no residual, and record complete credential/runtime cleanup. The already passing ordinary and concurrent paths need rerun only if this fix changes their shared teardown mechanism. |
| **Blocking · EVIDENCE · D28 / D29** | The 58-object append contains 55 terminal commands and three starts. Only two starts have terminals; `lifecycle-6` at line 863 is unmatched. Therefore the exact accounting is **56 attempts, 55 completions, one unmatched attempt (NOT RUN)**, with completed exits `0:39, 1:1, 2:0, 3:15`. The five recovery rows at lines 879-883 omit `recorded_at`; line 882 combines two TERM invocations into pseudo-argv containing `then`, rather than literal per-command argv/output/timing. | The failure is honestly preserved, but its narrative “58 rows” is object accounting, not attempt/completion accounting, and the fallback rows do not satisfy D28/D29's literal reconstruction law. They safely identify the narrow owned targets, but they cannot be promoted as a passing cleanup replacement. | The product reride above naturally replaces this failed fixture: emit a terminal record for every start, and literal timed rows—not composite pseudo-argv—for each ownership assertion, public maintenance call, status, credential deletion, and runtime deletion. Preserve these deficient rows as failure history. |

### Literal accounting, cleanup, and hygiene

Parsing lines 829-913 yields exactly **58 JSON objects: 55 `command` and three
`command_start`**. Completed-command exits are exactly **`0:39, 1:1, 2:0, 3:15`**. Scenario 1
is 11 terminal exit-0 commands. Scenario 2 is 21 objects comprising two matched starts and 19
terminal exit-0 commands. The induced section is 26 objects: one unmatched start plus 25 terminal
commands with exits `0:9, 1:1, 3:15`. There are no duplicate terminal attempt IDs.

All three fresh fixtures end with their isolated credential copies and owned runtimes removed and
no reported live owned PID/listener. The induced fixture's fallback is plausibly bounded to the
prebound processes, but the composite/manual recovery record remains D28-deficient as stated above.
No credential content, bearer-like authorization value, unknown/global/legacy process action, or
new post-candidate residual appears in the appended records.

### Observations → backlog

- `degraded maintenance impact` · define a first-class availability field for force impact when
  live Codex inventory cannot be read, preserving durable/last-known identities and explicit
  unknown/unmapped risk · this avoids both unsafe zero-impact invention and a force path that can
  never recover its owned child.
- `checkride recorder / concurrent terminal` · always drain or terminate a started subprocess and
  emit its terminal/NOT RUN record before switching to fallback cleanup · the unmatched
  `lifecycle-6` start obscures whether the original force call timed out, hung, or was abandoned.

---

## 2026-08-29 final degraded-force reevaluation — candidate `c0047558894c43e45e3501592e739d4a633a4b40`

**Result:** **FAIL — the degraded-runtime product failure is fixed, but D30's current force
projection is not reconciled with locked AH8 or the public danger help.**

**Focused evaluator reruns:** none. I inspected the literal nine-row appendix at
`executor-transcript.md:925-933`, its ownership and cleanup mechanisms, the current candidate
implementation, and the governing D8/D24/D26/D28/D29/D30, UC8/AH8, and CLI/help contracts. I did
not drive, stop, or alter any service.

### The final degraded-force fixture passes and closes the prior product/evidence blocker

- Sequence 3 binds the fresh fixture and runtime to the redacted owner token, then proves exact
  daemon and app-server PID/PPID/PGID/UID/argv, both private sockets, and the connectable public
  listener before mutation. Sequence 4 sends `SIGSTOP` only to the already bound app-server PGID.
- Sequence 5 executes the exact public `codex-worker daemon stop --force` command once. It returns
  exit 0 after 12.136 seconds with `action: stop`, `status: completed`, `forced: true`, preserved
  durable state, and both `inventory` and `workers` explicitly unavailable for
  `upstream_inventory_unavailable`. It fabricates no names, IDs, rows, or counts. No SIGCONT,
  fallback TERM/KILL, ordinary stop, or additional force attempt was run.
- Sequence 6 reports the service stopped. Sequence 7 proves both exact owned PIDs absent, both
  service sockets absent, and the public listener refusing. Sequence 8 deletes only the
  inode-checked isolated credential copy under its proven fixture root. Sequence 9 deletes only
  the owner-token-checked runtime and reports no residual. Every operation has literal argv, cwd,
  allowlisted environment names, timestamp, elapsed time, substrate, stdout/stderr, and exit.
- This is a valid replacement for the preserved failed SIGSTOP fixture. It closes that fixture's
  unmatched public-force attempt, manual-signal fallback, and incomplete D28/D29 accounting as
  evidence gaps for the current behavior; those earlier rows correctly remain failure history.

### Exact remaining blocker

| Severity / law | Current literal mechanism | Contract failure | Smallest resolution and reride |
|---|---|---|---|
| **Blocking · DESIGN-DOC / PRODUCT / HELP · D8 / D30 · UC8 / AH8** | `MaintenanceCoordinator._maintain()` enters the `force` branch before `list_active_threads()`, terminates the owner, and always returns `MaintenanceResult.unavailable(..., "upstream_inventory_unavailable")` for a fresh forced stop/restart, whether the upstream is responsive or degraded (`broker.py:1028-1033`). D30 explicitly says forced maintenance never calls upstream inventory and the design flow likewise says force skips it (`decisions.md:669-676`; `design.md:368-370`). The final appendix proves this intended degraded result, but contains no current-candidate responsive force with active mapped and `unmapped_tui` impact. | Locked AH8 still requires force to report **every** affected thread, including `unmapped_tui`, and UC8 says the operator sees complete impact (`design.md:61,471`). The public stop/restart descriptions say force accepts global impact, while both `--force` help strings say it interrupts every **reported** active name/session/thread/turn (`cli.py:182-194,283-284`); they do not disclose that current D30 force normally reports no identities or counts at all. D30 is a legitimate degraded-recovery correction, but an operator cannot simultaneously rely on the unchanged AH8 promise and the implemented unconditional unavailable projection. For a dangerous machine-wide operation, this is material, not editorial. | First resolve the governing contract through the design-doc path: either (A) amend UC8/AH8 and danger help to say explicit force can terminate all owned work with impact unknown/unavailable even on an otherwise responsive service until D30's bounded snapshot revisit condition is met, or (B) retain AH8 and add a bounded independently responsive pre-teardown snapshot that reports all mapped/unmapped impact when measurable while preserving the proven degraded fallback. Then reride only `daemon stop --help` and `daemon restart --help`, plus one fresh responsive active mapped+unmapped force fixture if option B is chosen. Re-run the accepted SIGSTOP row only if the shared teardown path changes. |

This is the only current blocker. The latest fixture's force exit 0 is correct under D30; its
unavailable projection is honest; cleanup is fully ownership-bound and complete. The failure is
the unresolved promise presented around that behavior, not a recurrence of degraded teardown.

### Governing acceptance matrix

| Acceptance | Current judgment |
|---|---|
| UC1–UC7 / AH1–AH7 | **Realized.** Exact shared-service start/identity/routes, literal second-client same-thread control, five-name isolation, caller-exit persistence/later attach, collision preservation, version replacement/refusal, and migration evidence remain accepted. |
| UC8 / AH8 | **Partial / blocking.** Routine stop remains absent, non-force active/unavailable refusal is guarded, ordinary/concurrent lifecycle converges, and degraded explicit force now terminates safely. The locked every-thread force-impact promise and public danger help are not reconciled with D30's unconditional unavailable force result. |
| UC9 / AH9 | **Realized.** Tracked real-Claude callback receipt and session/thread/TUI independence remain accepted. |
| UC10 / AH10–AH11 | **Realized.** Installed Python 3.9 tool, full public/raw command families, fixed listener behavior, exposure reporting, and secret hygiene remain accepted. |
| AH12 | **Executed but not passed.** The changed CLI/lifecycle has a fresh executor/evaluator checkride; its gate remains FAIL solely for the UC8/AH8 row above. |

### Transcript accounting and hygiene

The final appendix reconstructs as exactly **9 JSON objects, all `command`, all exit 0**, with
all required D28 fields and no start/unmatched/retry row. The full append-only transcript
reconstructs as **626 JSON objects**, including **551 terminal `command` rows** with exits exactly
**`0:483, 1:21, 2:5, 3:42`**. Its historical starts, failures, NOT RUN declaration, and replacement
records are preserved rather than silently normalized; they do not contradict the scoped final
fixture's 9/9 accounting.

No credential value, bearer authorization, unknown/global/legacy process action, live owned PID,
service socket, connectable listener, isolated credential copy, or fixture runtime remains in the
final appendix. Environment evidence lists variable names only; `owner_token` is redacted.

### Observations → backlog

- `acceptance-table drift / D30` · when an implementation erratum deliberately changes a locked
  acceptance behavior, update the acceptance hint and literal danger help in the same candidate;
  append-only decision history does not make a contradictory current promise safe for operators.

---

## 2026-08-29 final D30 healthy-impact reevaluation — candidate `c826a1a394f170e94d0c22b99d8359dc2ac08850`

**Result:** **PASS — all blocking findings are closed; the surface is operator-ready.**

**Focused evaluator reruns:** none. I inspected the literal 12-command appendix at
`executor-transcript.md:947-958`, the preserved real degraded-force appendix at lines 925-933,
the current bounded-force mechanism, and the amended D8/D30, CLI surface, UC8/AH8, help, honesty,
accounting, and D28/D29 cleanup contracts. I did not drive or alter any service.

### The final D30 blocker is closed

- The installed `daemon stop --help` and `daemon restart --help` rows at lines 948-949 explicitly
  say healthy force reports every measured active turn and degraded force accepts an unknown
  global blast radius when inventory is unavailable. Both retain machine-wide,
  human-supervised, active-refusal wording. The dangerous behavior is now disclosed before use,
  not only in a post-action result.
- A production installed CLI, daemon, gateway, registry, maintenance coordinator, and cleanup
  path run against a clearly labeled **SIMULATED authoritative Codex app-server backend fixture**.
  Every mixed-substrate row repeats that label. It demonstrates the production composition and
  output contract without presenting fixture thread/model/token data as real Codex measurements.
- Line 950 creates exact mapped worker `mapped-idle-d30` and completes its turn. Line 951 then
  reports one mapped idle worker and exactly one active app-server-wide item:
  `thread_id: tui-authoritative-d30`, `turn_id: tui-turn-authoritative-d30`,
  `origin: unmapped_tui`, with null wrapper/session identity. The sequential attempt record has no
  concurrent start, and line 953 records the fixture request set and zero unsettled forwarded
  mutations; the production coordinator's complete-result branch independently confirms the
  zero-unsettled condition because current force reports identities only after that gate.
- The single exact `daemon stop --force` at line 954 exits 0 and returns `status: completed`,
  `forced: true`, preserved durable state, the exact complete unmapped active item, and the exact
  mapped idle worker with counts and bases consistent with the immediately preceding status. It
  invents neither an active mapped name nor a wrapper identity for the TUI thread.
- Lines 955-958 prove stopped state, both prebound owned PIDs absent, private/RPC sockets absent,
  public listener refused, inode-bound isolated credential removed, and owner-token-bound runtime
  removed with no residual. No fallback signal, retry, or extra force operation was used.
- The preserved real-Codex SIGSTOP appendix at lines 925-933 remains the complementary degraded
  half: one public force exits 0, reports both inventory and workers explicitly unavailable with
  no fabricated identities/counts, and removes the exact owned lifecycle without SIGCONT or
  manual fallback. The healthy fixture does not overclaim that degraded behavior.

Together these literal records deliver current D30 and amended AH8: bounded complete impact on a
healthy zero-unsettled runtime, explicit unknown/unavailable impact when the owned upstream is
degraded, and verified teardown in both cases. The previous D30/AH8/help finding is closed.

### Acceptance matrix

| Acceptance | Final judgment |
|---|---|
| UC1 / AH1 | **Realized.** Ordinary start exposes the fixed shared service, exact wrapper/session/thread/turn identity, and copyable attach/resume routes. |
| UC2 / AH2 | **Realized.** Literal tracked records prove a second real TUI resumes and controls the same authoritative thread while worker-side observation/reconciliation continues. |
| UC3 / AH3 | **Realized.** Five concurrent independent callers retain globally unique names and isolated state, messages, callbacks, and notifications. |
| UC4 / AH4 | **Realized.** Caller/TUI exit leaves the fixed-listener service alive; later attach and same-thread resume work. |
| UC5 / AH5 | **Realized.** Default-port collision is typed and actionable, preserves the unknown peer, and does not fall back. |
| UC6 / AH6 | **Realized.** Idle incompatible replacement is durable; active work and unavailable authoritative inventory refuse without interruption. |
| UC7 / AH7 | **Realized.** Unique legacy state imports, identical state deduplicates, and divergent identities remain explicit for resolution. |
| UC8 / AH8 | **Realized.** Stop/restart is absent from routine completion, non-force is guarded, healthy supervised force reports complete mapped/unmapped impact, degraded force declares unknown/unavailable impact, and both teardown paths are ownership-bound. |
| UC9 / AH9 | **Realized.** The tracked real-Claude receipt proves callback delivery to captured room metadata while global lookup and TUI control remain independent of Claude identity. |
| UC10 / AH10–AH11 | **Realized.** Installed Python 3.9 tooling, all public/raw command families, fixed listener override, exposure/auth projection, provenance, and secret hygiene are reconstructed. |
| AH12 | **Realized.** A separate executor/evaluator checkride iterated the changed CLI and lifecycle through literal failure preservation and focused replacement evidence to this PASS. |

All **UC1–UC10** and **AH1–AH12** are realized on the governing evidence matrix.

### Exact accounting, cleanup, and hygiene

The final appendix reconstructs as exactly **12 JSON objects, all terminal `command` rows, all
exit 0**, with sequences 1-12, zero starts, unmatched attempts, duplicates, or retries. Every row
has literal argv, cwd, elapsed time, environment-name allowlist, recorded time, return code,
stdout/stderr, and substrate. The full append-only transcript reconstructs as **638 JSON objects**,
including **563 terminal commands** with exits exactly **`0:495, 1:21, 2:5, 3:42`**. Historical
unexpected failures and deficient attempts remain preserved and are explicitly replaced rather
than erased; their accounting does not conflict with the scoped 12/12 final run.

The final run leaves no live prebound PID, private/RPC socket, connectable listener, isolated
credential copy, or fixture runtime. The transcript exposes no credential value or bearer token;
environment evidence contains names only and ownership tokens are redacted. No installed/global/
legacy service or unknown process was used for fixture cleanup.

### Observations → backlog

- `mixed-substrate checkride labels` · retain the explicit “MEASURED production CLI/service with
  SIMULATED authoritative backend fixture” wording on future composition rides · it makes the
  demonstrated mechanism and the unclaimed real-world edge immediately distinguishable.
