# Checkride ledger: codex-worker 8.6.2 research worker and service lifecycle

- **Date:** 2026-09-30
- **Tree:** branch `item/codex-worker-search` at 047aae8 (8.6.2 = CWS-1 fix 396be36 on top of v8.6.1 f177405)
- **Installed surface:** `codex-worker 8.6.2` (UV tool, Python 3.12.13), installed by the trusted
  preflight from the branch root
- **Substrate:** ACTUAL DATA. Real codex-cli 0.158.0 (ChatGPT login), the live web, and the real global
  service and registry (J1–J3, J5). J4 uses a disposable isolated service home with the same real Codex,
  web, and auth.
- **Data preflight (ROOM SESSION, 2026-09-30):** `codex login status` → "Logged in using ChatGPT";
  live web search returned results in today's stdio check; `daemon status` → stopped, 0 active turns,
  6 idle workers.
- **Plan:** `docs/superdev/checkrides/2026-09-30-codex-worker-search-checkride-plan.md`
- **Scenario:** `docs/superdev/scenarios/2026-09-30-codex-worker-search-research-worker.md`
- **Roles:** executor = sonnet (medium); evaluator = opus (very smart); ROOM SESSION relays and keeps this ledger.

## Steps

### Step 1 (J1 baseline)
- **PROPOSE (executor):** `codex-worker daemon status`, read-only. A baseline of the stopped global service before the first `start --search`. Expected: stopped, 0 active turns. Counts MEASURED. Writes nothing.
- **RULE (evaluator):** GO. Run it on the real global environment with no HOME/XDG_STATE_HOME/TMPDIR override, and report exit code and stdout verbatim. The next proposal must be `codex-worker --version` (scenario step 1). On `start`, say whether `--read-only` is used, since it fixes the worker's access for life.
- **RULE addendum (evaluator, answering a duplicate relay after the GO):** AMEND: `--version` first as its own step, with stdout and stderr captured separately and verbatim plus `echo "exit=$?"`, and no jq or filters. **Reconciled by the ROOM SESSION:** the read-only `daemon status` had already been GO'd and was running, so `--version` becomes step 2, before any scratch dir or `start`. The capture rules apply from step 2. `start` should use `--read-only` (docs' research example) unless the executor justifies full access.
- **RUN (executor):** `codex-worker daemon status` → exit 0, stderr empty. Stdout: one JSON object, verbatim in `2026-09-30-codex-worker-search-evidence/step01.stdout`. Key fields: `status:"stopped"`, `service_version:"8.1.0"` (the stopped service's last recorded generation), `worker_count` 6 (idle; derived), `active_turn_count` 0, migration complete with 1 name conflict (`status-checker-abc`).
- **JUDGE (evaluator):** OK with advisory FINDINGS.
  - Good: one object, empty stderr, exit 0; read-only as documented; worker counts carry source and availability; a baseline of the six other-room workers.
  - **F1** `service_version:"8.1.0"` on a stopped service has no label and isn't documented, so the operator can't tell whether it's the last generation or what `start` will run. EXPLAINABLE fails. Advisory, provisionally blocks-milestone. The next post-start `status` settles it: 8.1.0 then would be BLOCKING.
  - **F2** `active_turn_count.source:"codex app-server inventory"` while `app_server_pid:null`. The value is right, but the source overclaims a live read. `attach_command` is also offered while it can't connect, and workers show as "idle" when they are detached. This matters because J5's impact report is this same object. Advisory, blocks-milestone (honesty/labelling).
  - **F3** About 80% of the output is migration provenance, with a `status-checker-abc` conflict that has no remedy. Advisory, RESIDUAL (legacy migration is out of scope).
  - Next: `codex-worker --version` (step 2, capture rules), then the scratch dir, `start --search --no-callback --read-only`, then `daemon status` again.

### Step 2 (J1 version check)
- **PROPOSE (executor):** `codex-worker --version`, captured to `step02.stdout/.stderr/.exit`. Read-only. Expected 8.6.2.
- **RULE (evaluator):** GO. Also capture `command -v codex-worker` to `step02.path`. Anything but 8.6.2 means STOP. Plain version text is fine for `--version`.
- **RUN (executor):** `codex-worker --version` → stdout `codex-worker 8.6.2`, stderr empty, exit 0. `command -v codex-worker` → `/Users/tadas/.local/bin/codex-worker`. Evidence: `step02.*`.
- **JUDGE (evaluator):** OK, no findings. The CLI is the build under ride; `step02.path` resolves to the fresh UV tool install. F1 is reinforced (CLI 8.6.2 vs the stopped service's 8.1.0); step 05 settles it. Next: create the scratch dir, then create the research worker.

### Step 3 (J1 scratch directory)
- **PROPOSE (executor):** `mkdir -p /private/tmp/cw-ride-5d2b8e` and write the question to `question.md` inside it (for `--prompt-file`).
- **RULE (evaluator):** AMEND. Keep the scratch dir EMPTY, since that is the plan's starting point and a read-only worker could read a file placed in its cwd. Write the question to `evidence/step04.question.md` instead, which also keeps it on record.

### Step 4 (J1 `start --search`)
- **PROPOSE (executor):** `codex-worker start --name research-5d2b8e --cwd /private/tmp/cw-ride-5d2b8e --prompt-file <question> --read-only --search --no-callback --timeout 840`. The first automatic start of the global service under codex-cli 0.158.
- **RULE (evaluator):** GO with `--prompt-file $E/step04.question.md`. On a typed fault, report it verbatim with no retry and no daemon command. On a local timeout, the next step is `status --name`, never a second `start`.
  - The evaluator's read-only re-drive, `start --help` (exit 0), documents `--search`/`--config` and states in its Limits that creation policy is "fixed at creation and reapplied when the worker is resumed; run cannot change it".
  - **F4** (advisory, RESIDUAL): `--no-callback` and `--timeout` have no help text, and the timeout unit isn't stated.
- **RUN step 3 (executor):** `mkdir -p /private/tmp/cw-ride-5d2b8e` → exit 0, directory empty. Question written to `evidence/step04.question.md`.
- **RUN step 4 (executor):** `codex-worker start --name research-5d2b8e --cwd /private/tmp/cw-ride-5d2b8e --prompt-file $E/step04.question.md --read-only --search --no-callback --timeout 840` → exit 0, stderr empty. One JSON object, verbatim in `step04.stdout`:
  - worker: session `0da93a3d-…`, thread `01a0f30c-8c0f-7f00-a8a9-2756594ef13f`, access `read_only`, **`config: {"web_search":"live"}`**, attach/resume routes on ws://127.0.0.1:4500
  - turn: completed
  - answer: cites the EU Register PDF (Entry IDs 1935, 1737; EFSA 2011;9(6):2238)
  - metrics: `item_counts` webSearch 2, commandExecution 2; `command_duration_ms` 0; `token_usage` null/"unavailable"; wall 23.3 s (measured)
  - The global service was started by `start` under codex-cli 0.158 with no fault.
- **JUDGE step 3 (evaluator):** OK.
- **JUDGE step 4 (evaluator):** OK with FINDINGS, nothing blocking.
  - **Good:**
    - The stopped global service came up behind an ordinary `start` under codex-cli 0.158, with no socket fault and no operator action.
    - One object, empty stderr, exit 0.
    - `config {"web_search":"live"}` plus the help's Limits text covers "live search, fixed for life".
    - The session and thread ids are distinct; resume and recovery commands are present.
    - `webSearch: 2` shows a search actually ran; the answer is sourced.
  - **F5** `command_count` 2 alongside `command_duration_ms` 0 ("derived", source codex). Probably missing durations counted as 0, which would be an invented number. Honesty item: advisory, blocks-milestone (never RESIDUAL). It stays open until the command items are seen verbatim (J3).
  - **F6** `token_usage` null/"unavailable": honestly labelled, but with no reason or pointer, so the operator can't see the reuse saving. It becomes DESIGN-DOC if turn 2 is also unavailable.
  - **F7** `start` doesn't report that it started (or might replace) the machine-wide service. Advisory, RESIDUAL.
  - Next: `daemon status` (pre-ruled GO), then the J1 refusal paths (`run --search` → exit 2; duplicate `start` → a typed refusal with a remedy) before J2.
- **ROOM SESSION fact for F6:**
  - codex app-server does emit per-turn usage, as `thread/tokenUsage/updated` notifications. Five were observed in the 2026-09-30 stdio verification of two turns.
  - codex-worker's `derive_metrics` looks only for `tokenUsage` inside turn items, so it drops them.
  - That behaviour predates this branch.
  - Out-of-surface measurement from Codex's session record for this thread after turn 1: `total_token_usage.input_tokens` 97,001 (75,520 cached).
- **JUDGE step 4 (evaluator, final after the ROOM SESSION facts):**
  - The evaluator spot-checked the cited EU Register PDF: HEAD 200, `application/pdf`, 1,992,490 bytes.
  - **F6** re-triaged to blocks-milestone, DESIGN-DOC (honesty). The label blames Codex, but codex-worker drops the `thread/tokenUsage/updated` notifications. Proposed design: collect them into per-turn `metrics.token_usage` as measured; until then, label it `source:"codex-worker"` with a reason. It predates this branch, so it does not by itself block publishing 8.6.2.
  - J2 honesty check: the out-of-surface turn-2 read must show a real saving, or RELEASE-NOTES L18–19 overclaims.
  - **F5** is open: it blocks publish if in v8.6.x code, else blocks-milestone.
  - **F7** also covers the result not stating that config is fixed.

### Step 5 (J1 service after start: 5a `daemon status` → step05, 5b `status --name` → step06, 5c `messages --tail 1` → step07)
- **PROPOSE (executor):** three read-only reads with separate capture sets.
- **RULE (evaluator):** GO on all three.
  - 5a is judged on: `service_version` 8.6.2 (settles F1; 8.1.0 = blocking), non-null pids, live source labels, 7 workers with the six baseline names unchanged, 0 active turns.
  - Refusal paths come AFTER 5b/5c: `run --search` / `run --config` → exit 2 with no RPC; a duplicate `start` → a typed refusal with a remedy and no change. Then `status` again, compared to step06, then J2. J3's `history` must show turn 1's `commandExecution` items (F5).
- **RUN 5a (step05):** `codex-worker daemon status` → exit 0, stderr empty.
  - `status:"ready"`, **`service_version:"8.6.2"`**, pid 51985, app_server_pid 52058, listener 4500
  - worker_count 7: the six baseline names unchanged, plus `research-5d2b8e`, all idle
  - active_turn_count 0; migration block unchanged
- **RUN 5b (step06):** `codex-worker status --name research-5d2b8e` → exit 0. The same session, thread and turn as step 4; `config {"web_search":"live"}`; `read_only`; attached, `active_turn_id` null, latest turn completed; callback disabled.
- **RUN 5c (step07):** `codex-worker messages --name research-5d2b8e --tail 1` → exit 0. The same `item_id` and text as step 4's final answer. `selection:"live"` (step 4 had `explicit_final`); `truncated:true`; `latest_cursor` 12.
- **HOLD (J5):** the ROOM SESSION sent supplements-orchestrator the global impact report (ready 8.6.2; 7 idle workers, 6 of them other rooms'; 0 active turns) and asked for GREEN-LIGHT J5. The orchestrator acknowledged and relayed it to the human. Nothing machine-wide runs without "GREEN-LIGHT J5" quoting the human. If there is no answer, the ride closes on J4, with global J5 listed as a named gap.
- **JUDGE 5a (evaluator):** OK.
  - **F1 settled:** `service_version` 8.6.2, so step 1's 8.1.0 was last-generation metadata. F1 is merged into F2: in the stopped state, stored values show as if live. blocks-milestone.
  - F3 stands.
  - Noted for J5: `idle_names` doesn't distinguish attached workers from never-resumed ones.
- **JUDGE 5b (evaluator):** OK. The identity is exactly step 4's; config live; read_only; callback disabled.
- **JUDGE 5c (evaluator):** OK. The read-back is faithful.
  - **F8** (advisory, RESIDUAL): the same item shows `selection:"explicit_final"` in step 4 and `"live"` in step 7, and `selection` is undocumented.
  - F5 is provisionally honest (Codex supplied the 0) and closes when J3 `history` shows the items.
  - A new J2 criterion: `commandExecution` in turn 2 shows whether skills were loaded again.

### Step 6 (J1 refusal paths: 6a → step08, 6b → step09, 6c → step10)
- **PROPOSE (executor):** `run --search`, `run --config web_search="disabled"`, and a byte-identical duplicate `start`.
- **RULE (evaluator):**
  - 6a and 6b: AMEND, using the prompt `"REFUSAL PROBE: if you receive this, reply only PROBE-ACCEPTED"` so a failed guard is cheap and recognisable. Then GO. The evaluator's re-drive of `run --help` (exit 0) lists neither flag.
  - 6c: GO. Expected a typed refusal with a runnable remedy (not `--force` or a teardown), no new turn and no replaced thread, then `status` compared to step06.
- **RUN 6a (step08):** `run --name research-5d2b8e --search --prompt "REFUSAL PROBE…"` → exit 2. stdout: one JSON error `-32602 invalid_params`, reason "unrecognized arguments: --search". stderr: top-level argparse usage plus the error line. No turn.
- **RUN 6b (step09):** `run … --config web_search="disabled" --prompt "REFUSAL PROBE…"` → exit 2. The same shape, reason "unrecognized arguments: --config web_search=disabled".
- **RUN 6c (step10):** duplicate `start` (byte-identical to step 4) → exit 3, stderr empty. stdout: `-32021 worker_name_exists`, `retryable:false`, `known_ids` (name/session/thread, turn null), `next_actions`: `codex-worker status --name research-5d2b8e` and the raw `codex --remote … resume <thread>`.
- **JUDGE 6a/6b (evaluator):** OK; the gate works. Exit 2 and one object, rejected before any RPC.
  - **F9** (advisory, blocks-milestone): `reason:"unrecognized arguments: --search"` has no `next_actions` and doesn't say the setting is fixed at creation. The stderr usage is top-level, and `run --help` Limits lacks the creation-policy sentence. It reads as a typo, not a rule.
- **JUDGE 6c (evaluator):** OK; a good typed refusal. Exit 3; `worker_name_exists`; `known_ids`; a runnable `status --name` remedy.
  - **F10** (advisory, RESIDUAL): the second remedy is the expert raw `codex --remote … resume`. It is missing `run --name …` (continue) and "choose a new name".

### Step 7 (7a `status` re-check → step11; 7b J2 follow-up `run` → step12)
- **PROPOSE (executor):** `status --name research-5d2b8e` (compared to step06), then `run --name research-5d2b8e --prompt-file $E/step12.question.md --timeout 840`.
- **RULE (evaluator):**
  - 7a: GO, with a `diff` of the step11 result against step06. Any change to the turn, thread, config or access is BLOCKING.
  - 7b: AMEND the prompt so it depends on turn 1 and needs new web data: "Follow-up on the EFSA opinion you cited (EFSA Journal 2011;9(6):2238): what L-theanine doses and population did it consider, and why was the evidence judged insufficient? Two sentences, cite the EFSA URL." Then GO. The ROOM SESSION is to repeat the out-of-surface token read after step 12.
- **RUN 7a (step11):** `status --name research-5d2b8e` → exit 0. `diff step06.stdout step11.stdout` → no output, `diff_exit=0` (byte-identical). The refusals left the worker unchanged.
- **RUN 7b (step12):** J2 `run --name research-5d2b8e --prompt-file $E/step12.question.md --timeout 840` → exit 0, stderr empty.
  - The same session and thread, a new turn `01a0f313-…`, `config {"web_search":"live"}`, `read_only`.
  - Answer: 200 mg / 250 mg acute doses in healthy adults, with the reasons for insufficiency; cites `https://efsa.onlinelibrary.wiley.com/doi/10.2903/j.efsa.2011.2238`.
  - metrics: webSearch 3, **commandExecution 0 / command_count 0**, `command_duration_ms` null/unavailable, `token_usage` null/unavailable, wall 19.05 s.
- **ROOM SESSION out-of-surface token read** (Codex session record `rollout-2026-09-30T19-01-20-01a0f30c…jsonl`; report only, not operator surface):

  | Turn | Model requests | Input tokens | Cached | Uncached | Output |
  |---|---|---|---|---|---|
  | 1 | 5 | 97,001 | 75,520 | 21,481 | 511 |
  | 2 | 4 | 152,284 | 126,976 | 25,308 | 513 |

  - Per request, input grows from 16,833 (turn 1, first request) to 48,375 (turn 2, last request), because web results stay in the thread history.
  - Turn 2 did **not** reload the skills (0 command executions, against 2 in turn 1), but its input tokens rose because of the carried history.
- **JUDGE 7a (evaluator):** OK. step11 == step06; the refusals mutated nothing.
- **JUDGE 7b (evaluator):** OK on the surface.
  - Good: the same session and thread with a new turn; continuity is real; `webSearch: 3`; `command_count: 0` (skills not re-read); `command_duration_ms` unavailable when there are no commands; the EFSA citation verified (the DOI resolves to EFSA 2011.2238, confirmed by Crossref).
  - **F11** (blocks-publish, DESIGN-DOC, honesty): RELEASE-NOTES 8.6.0 L18–19 and codex-worker.md L86–87 imply a per-call token saving from reuse. The out-of-surface read shows input tokens *rose* per turn (the history, including search results, is re-sent). F6 means the operator can't see it.
  - F6 stays blocks-milestone with more weight.
- **FIX LANE (ROOM SESSION), F11:**
  - codex-worker.md now says reuse keeps the conversation and reads skills once, but every turn re-sends the growing history, so input tokens rise; unrelated questions may be cheaper in a fresh worker; `metrics.token_usage` doesn't report usage yet.
  - The RELEASE-NOTES 8.6.0 paragraph was corrected the same way, marked "corrected in 8.6.2".
  - The evaluator re-checks the wording before the verdict.
- **F11 re-check (evaluator):**
  - codex-worker.md: accepted. "reads its skills once" is to be proven after the J4 restart (else "once per live session").
  - RELEASE-NOTES: AMEND "does not make each turn cheaper" (it overclaims the other way; the one-shot baseline wasn't measured) to "it is not a per-turn token saving: every turn re-sends the growing thread history…". Applied by the ROOM SESSION.

### Step 8 (J3: 8a `history` → step13, 8b `messages --tail 2` → step14) and Step 9 (J4 isolated service)
- **PROPOSE (executor):** J3 reads, and the J4 plan (isolation env on every command; port 4611; baselines; isolated start; an active-turn refusal; stop and after-reads).
- **RULE (evaluator):**
  - 8a and 8b: GO.
  - J4:
    - 9a+9b: GO as one set, with amendments: `ps -axo pid,ppid,pgid,command | grep -i "[c]odex"`; **step18b** isolated `daemon status` as a GATE (it must show stopped and 0 workers with no global data, else STOP: isolation leak); **step18c** `ls -laR` of the isolated `rt`.
    - 9c: `--cwd /private/tmp/cw-iso-e7a1c4/work` (new, empty).
    - 9d: GO.
    - 9e: an active-turn refusal with a fixed six-jurisdiction prompt on `research-iso2-e7a1c4` started in the background; the isolated status must show ≥1 active turn before the stop; the stop without `--force` should refuse with exit 3; `wait` for the job. A miss is a TIMING-MISS.
    - 9f restart → 9g resume `run` (search proves the config was re-sent; `commandExecution` checks skills-once) → 9h stop plus post-reads vs 16–18c and the global untouched → 9i `run` after the full stop (auto-restart and resume) → 9j final stop plus post-reads.
    - No `--force`, and no transport args after 9c.
