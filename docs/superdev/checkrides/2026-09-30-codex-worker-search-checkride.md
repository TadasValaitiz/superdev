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
- **RUN 8a (step13):** `history --name research-5d2b8e` (no `--tail`) → exit 0. It returned ONE turn (turn 2): `requested_tail:1`, `older_available:true`. The default tail is 1, and turns carry only messages, not command or search items.
- **RUN 8b (step14):** `messages --name research-5d2b8e --tail 2` → exit 0. Two messages, both from turn 2 (a commentary message and the final answer, both `selection:"live"`); `truncated:false`; `latest_cursor` 24.
- **RUN 9a:** `mkdir -p /private/tmp/cw-iso-e7a1c4/{home,state,rt,work}` → exit 0.
- **RUN step15:** `lsof -nP -iTCP:4611 -sTCP:LISTEN` → exit 1 with no output (the port is free).
- **RUN step16:** `ls -la /private/tmp/codex-daemon-501/` → sockets `6c891589…` (19:01, the global service's target) and `a02c5d4d…` (04:56, codex's managed daemon), plus 6 `.lock` files.
- **RUN step17:** global `daemon status` → ready 8.6.2, pids 51985/52058, 7 idle workers (unchanged).
- **RUN step18:** `ps -axo pid,ppid,pgid,command | grep -i "[c]odex"` → the full list is in `step18.stdout`. The global chain: codex-worker 51985 (pgid 51985) → node codex 52058 (pgid 52058) → codex 52077 → code-mode-host 54064 (pgid 54064).
- **RUN step18b (GATE):** isolated `daemon status` → exit 0: `status:"stopped"`, pids null, worker_count 0, migration `incomplete`/`ready:false` (no import of global instances), but `listener:"ws://127.0.0.1:4500"`. The executor stopped on the literal gate rule and did not run step18c or 9c.
- **JUDGE 8a (evaluator):** OK. `older_available:true` is honest.
  - With no `--tail` the operator gets 1 turn, and the help shows no default or unit.
  - **F5 CLOSED as honest:** the 0 was Codex's `durationMs`, and turn 2 read unavailable; the surface can't show the items.
  - **F12** (advisory, RESIDUAL): item-level evidence (commands run, search queries) is unreachable through status, messages or history; only counts are visible.
- **JUDGE 8b (evaluator):** OK.
  - **F13** (advisory, RESIDUAL): `messages` covers only the latest turn but says `truncated:false` with no turn id; `--tail` counts messages here but turns in `history`.
  - F8 confirmed (`live` vs `explicit_final`), RESIDUAL.
- **JUDGE 9a, 15–18 (evaluator):** OK. The baselines are good.
  - The daemon directory is 0700 and the sockets 0600.
  - A `.lock` left per path is Codex's, and codex-worker must NOT delete it.
  - The global chain includes `codex-code-mode-host` 54064 in its OWN pgid, so J4 must check for an orphaned code-mode-host after the isolated stop.
  - Other Codex processes (VS Code, the ChatGPT app, the managed daemon, an interactive codex) must stay untouched.
- **GATE 18b RULING (evaluator):** PASS on substance. The pids are null, 0 workers and 0 migration sources, so this is a separate empty state home; the 4500 shown is a default for a never-created service. The literal criterion was the evaluator's error. This adds weight to **F2**: defaults and stored values shown as live misled a careful operator into a STOP in this ride.
  - Order from here: step18c; 9c; 9d (isolated plus global status); 9d-bis (ps, daemon dir, rt listing to record the isolated identities); then 9e onward; and `history --tail 2` before RIDE END.
- **RUN step18c:** the isolated `rt` was empty.
- **RUN 9c (step19):** isolated `start --name research-iso-e7a1c4 --cwd …/work … --read-only --search --no-callback --app-server-listen ws://127.0.0.1:4611` → exit 0, stderr empty.
  - Listener 4611; new session `9fce3bfd…` and thread `01a0f31c-1a21…`; `config {"web_search":"live"}`.
  - Answer cites the EU Register PDF.
  - webSearch 2, commandExecution 2, `command_duration_ms` 0, `token_usage` unavailable, wall 23.8 s.
- **RUN step20:** isolated `daemon status` → ready 8.6.2, pid 97884, app-server 97886, listener 4611, 1 idle worker, empty migration.
- **RUN step20g:** global `daemon status` is byte-identical to step17 (`diff` exit 0).
- **RUN step21b:** the daemon directory gained a new socket `376919b0…` and `.lock` (19:18); the 8 other entries are unchanged.
- **RUN step21c:** the isolated `rt/scw-501-global/`:
  - `c -> /private/tmp/codex-daemon-501/376919b0…`, `l`, `s`, `s.lock`
  - also `node-compile-cache/` (84 blobs) and two empty `.tmp*` directories (node/codex temp, via the isolated TMPDIR)
- **RUN step21a:** the isolated chain is 97884 (pgid 97884, codex-worker serve) → 97886 node (pgid 97886) → 97887 codex (pgid 97886) → **98221 codex-code-mode-host (pgid 98221)**. The global chain is unchanged.
- **JUDGE 18c, 9c, 20, 20g, 21 (evaluator):** OK, no findings.
  - The isolated worker and service are fully separate. step20g byte-identical to step17 is the strongest isolation evidence.
  - step21 is the D197 layout seen live: an owner-only target directly in the 0700 daemon directory.
  - **Teardown identities to check:**
    - The isolated link, target and process groups 97884/97886, and **98221 (code-mode-host, its own pgid)**, must be gone.
    - A left-behind `.lock` is Codex's own.
    - node-compile-cache and the `.tmp*` directories are ordinary scratch files.
    - The global chain, target, managed daemon and other Codex processes must be untouched.

### Step 10 (J4, 9e: active-turn stop refusal)
- **RULE (evaluator):** GO in this exact order:
  - 9e-0: `work2` directory plus the jurisdictions prompt to `step22.question.md`.
  - 9e-1 (step22): the isolated `start research-iso2-e7a1c4 … &` in the background (no `--app-server-listen`); record `$!`; never kill it.
  - 9e-2 (step23): the isolated status must show ≥1 active turn with iso2 active, otherwise a TIMING-MISS.
  - 9e-3 (step24): the isolated `daemon stop` without `--force`. Expected exit 3, a typed refusal, and an impact report naming iso2 active and iso idle; a `--force` in `next_actions` is a finding.
  - 9e-4 (step25): `wait`; iso2's turn completed unaffected.
  - 9e-5 (step26): isolated status showing 0 active, plus `ps`: the isolated chain alive with the same PIDs (the refusal sent no signal).
- **RUN 9e:** all in one Bash call, with the ISO environment on every command.
  - **step22:** `start research-iso2-e7a1c4 … &` (the six-jurisdiction prompt), background PID 1974, never signalled.
  - **step23** (+3 s): isolated status `active_turn_count` 1 (iso2, thread `01a0f31e-88b3…`, turn `01a0f31e-88e9…`); worker_count 2, iso2 active and iso idle.
  - **step24:** isolated `daemon stop` (no `--force`) → **exit 3**, `-32040 service_busy` "Global service has active work", `retryable:false`. `details.active` names the iso2 thread, session and turn; `workers` shows iso2 active and iso idle. `next_actions`: `daemon status` and `status --name research-iso2-e7a1c4` (no `--force`).
  - **step25:** `wait` → step22 exit 0. iso2's turn completed unaffected (67.1 s, webSearch 5, commandExecution 2); a six-jurisdiction answer with citations.
  - **step26:** isolated status ready, the same pids 97884/97886, 2 idle, 0 active. `ps`: the isolated chain (97884/97886/97887/98221) alive with the same PIDs; no new code-mode-host; the global chain unchanged.
- **JUDGE 9e (evaluator):** OK. The gate guards something real.
  - step23 is a live inventory at the level of detail J5 needs.
  - step24 is a typed `service_busy` refusal with a full impact report and inspect-only `next_actions`, with **no `--force` suggested**.
  - step26 proves no signal was sent; iso2 reused code-mode-host 98221.
  - **F14** (advisory, RESIDUAL): `retryable:false` next to "before retrying maintenance", and the output doesn't say stop will succeed once active reaches 0.

### Step 11 (J4 9f: isolated restart)
- **RULE (evaluator):** AMEND. First, **step26b**: inode baselines via `ls -lai` of the daemon directory and of `rt/scw-501-global/`, because the target name is likely a hash of the link path and so the name alone can't prove recreation.
  - Then **step27** isolated `daemon restart` (no `--force`, no transport args): GO.
  - Post-reads:
    - 28a: isolated status (new pids, 4611, 2 idle).
    - 28b: `ps`. The old 97886/97887 gone; **98221 gone and not re-parented to 1**; the global chain and others' Codex processes untouched.
    - 28c: the daemon directory: the isolated target has a new inode; the global `6c89…` and managed `a02c…` inodes unchanged.
    - 28d: the isolated `rt` listing: link `c` recreated.
    - 28e: global status byte-identical to step17.
    - 28f: isolated `status --name research-iso-e7a1c4`.
- **RUN 9f:** (ISO environment, no `--force`, no transport args)
  - **step26b1/2 (before):** the isolated target `376919b0…` inode 90477493; the link `c` inode 90477494; the global `6c89…` 90468854; the managed `a02c…` 89280726.
  - **step27:** `daemon restart` → exit 0. `maintenance {action restart, status completed, forced false, inventory [], workers 2 idle, durable_state preserved}`; `service` ready with new pid 8571 / app-server 8573 on 4611.
  - **step28a:** isolated status ready, 8571/8573, 2 idle.
  - **step28b:** `ps`: the old 97884/97886/97887 and **98221 all ABSENT** (no orphan). The new chain is 8571 (pgid 8571) → 8573 node (pgid 8573) → 8574 codex; no code-mode-host yet. The global chain and all others' Codex processes are PRESENT and unchanged.
  - **step28c:** the isolated target recreated under the SAME name `376919b0…` with a new inode 90488398; its `.lock` unchanged (90477492); every other entry unchanged in inode and mtime (global `6c89…` 90468854).
  - **step28d:** link `c` recreated (inode 90488399) → the same target name; `s` recreated; `l` and `s.lock` unchanged.
  - **step28e:** global status byte-identical to step17.
  - **step28f:** `status --name research-iso-e7a1c4` → **exit 3 `-32023 daemon_stopped` "Worker daemon is stopped"**, with `next_actions` `daemon start`, `status --name …`, and raw resume, while the service is ready (step28a).
  - ROOM SESSION code read: `facade.status` returns `_stopped_fault` whenever the worker is not attached in the current generation. The code dates from 2026-08-19 and is not in this branch's diff.
- **JUDGE 9f (evaluator):** the restart is OK and is the best CWS-1 evidence: the whole old owned chain is gone including code-mode-host 98221, with no orphan; the target and link were recreated (new inodes); the global target, managed daemon, foreign Codex processes and global status are all untouched.
  - **F15** (honesty, blocks-milestone, DESIGN-DOC; pre-existing from 2026-08-19; **BLOCKING for the J5 GREEN-LIGHT until disclosed**): after a restart, `status --name` says "Worker daemon is stopped" with `daemon start` as the first remedy while the service is ready. The working remedy `run --name` is missing, and the restart result doesn't say workers become detached.
  - **ROOM SESSION:** disclosed F15 to supplements-orchestrator as a J5 impact addendum for the human.

### Step 12 (J4 9g: scope F15, then resume)
- **RULE (evaluator):**
  - AMEND: first scope F15 with step28g `messages --tail 1` and step28h `history --tail 1` (do the other recovery reads fail too?), then step28i `daemon start` exactly as the remedy says, step28j `status --name` again, and step28k global status vs step17.
  - Then step29 GO: `run --name research-iso-e7a1c4` with the follow-up "Follow-up on the EU Register entries you cited (IDs 1935 and 1737): which Commission Regulation listed them as non-authorised, with its number and date? One sentence, cite the EUR-Lex URL."
    - The same session and thread with a new turn; config live.
    - **webSearch ≥1 proves the config was re-sent on resume**; commandExecution settles "skills once".
  - Then step30: `status --name` (attached) plus `ps`.
- **RUN 9g:** (ISO environment)
  - **step28g:** `messages --name research-iso-e7a1c4 --tail 1` → **exit 1**, `-32603 internal_error`, `details.reason:"AttributeError"`, no next action.
  - **step28h:** `history --name … --tail 1` → exit 3, the same false `daemon_stopped` as step28f.
  - **step28i:** `daemon start` (the offered remedy) → exit 0, already ready, the same pids 8571/8573, listener 4611 (nothing global).
  - **step28j:** `status --name` → still exit 3 `daemon_stopped`: **the remedy is a dead end**.
  - **step28k:** global status byte-identical to step17.
  - **step29:** `run --name research-iso-e7a1c4 --prompt-file step29.question.md` → exit 0.
    - The same session `9fce3bfd…` and thread `01a0f31c-1a21…`, new turn `01a0f324…`, `config {"web_search":"live"}`.
    - **webSearch 3** (the config was re-sent on resume), commandExecution 1.
    - The answer cites Commission Regulation (EU) No 432/2012 (EUR-Lex `eli/reg/2012/432/oj`); wall 27.0 s.
  - **step30:** `status --name` → exit 0, attached true, latest turn `01a0f324…`. `ps`: the isolated chain 8571/8573/8574, plus the new code-mode-host **13449 (pgid 13449)**; the global chain unchanged.
  - ROOM SESSION root cause for step28g: `facade.messages` catches `UnknownSession`/`SessionDetached` and calls `_stopped_fault(request.name, None)`. `_stopped_fault` then dereferences `record.thread_id` → AttributeError → untyped `internal_error`. Present since 2026-08-19 (631e9df); not in this branch's diff.
- **JUDGE 9g (evaluator):**
  - **F16** (honesty/safety, **blocks-publish**; pre-existing from 631e9df, 2026-08-19, but newly reachable): after a restart, `messages --name` fails with an untyped `internal_error: AttributeError`, exit 1, and no remedy.
  - **F15 upgraded to blocks-publish:** the `daemon start` remedy is a dead end (step28i no-op → step28j still "stopped"). The human may take either as an exception in their own words; if so, the J5 report and the 8.6.2 notes must disclose it.
  - **step29 meets J4's core promise:** the same session and thread after a restart, config live, **webSearch 3 (config re-sent on resume)**, continuity in the answer. The resume itself is silent (goes under F15's DESIGN-DOC).
  - The post-resume `commandExecution: 1` question was sent to the ROOM SESSION.
- **ROOM SESSION out-of-surface read** (Codex session record for thread `01a0f31c-1a21…`): the post-restart turn's one command was `sed -n '1,120p' …/using-superdev/SKILL.md`, a skill **re-read after the resume**. The codex-worker.md and RELEASE-NOTES wording is corrected to "reads its skills once per live session (a resume after a service restart may read them again)".
- **DECIDE (supplements-orchestrator, relaying the human under D197: "fix stuff" / "it's important that we fix the process and agree on the tooling"): A.**
  - Fix F16 (pass the record) and F15 (a typed `worker_detached` fault, "worker is detached from this service generation", remedy `run --name <w> --prompt …`, never `daemon start`; the stop/restart impact says workers become detached), test-first.
  - Re-ride 28f–28j after one more isolated restart; publish 8.6.2 with both fixed.
  - J5 stays on HOLD for the human's explicit GREEN-LIGHT.

### Step 13 (J4 9h: isolated stop)
- **RULE (evaluator):** GO (ruled with 9g).
- **RUN step31:** `<ISO> daemon stop` → exit 0: `{"action":"stop","status":"completed","forced":false,"listener":null,"inventory":{"items":[]},"workers":{…2 idle…},"durable_state":"preserved"}`.
- **RUN step32a:** isolated status stopped, pids null, 2 idle in the registry, listener 4611 shown (configured).
- **RUN step32b:** `ps`: 8571/8573/8574 and **13449 ABSENT**; no process mentions `cw-iso-e7a1c4` (except the executor's own shell); the global chain and all foreign processes PRESENT.
- **RUN step32c:** the isolated target `376919b0…` (90488398) gone; its `.lock` (90477492) remains; every other entry unchanged.
- **RUN step32d:** the isolated `c` and `s` gone; `l` and `s.lock` remain.
- **RUN step32e:** `lsof` 4611 → exit 1, empty (listener freed).
- **RUN step32f:** global status byte-identical to step17.
- **RUN step32g:** global `status --name research-5d2b8e` → attached, config live.
- **JUDGE 9h (evaluator):** OK. The CWS-1 teardown passes on live evidence.
  - The whole owned chain is gone, including code-mode-host 13449 outside the owned group; nothing is orphaned.
  - The target, link and control socket are gone and the port freed.
  - What remains is expected (Codex's `.lock`; codex-worker's `l` and `s.lock`).
  - Nothing else was touched.
  - F2 addition: `listener:null` in the stop result vs the configured 4611 in the stopped status.
- **FIX LANE (ROOM SESSION), commit db2405b:** F15/F16 fixed test-first (the new `WORKER_DETACHED` -32043; `messages` passes the record; `worker_attachment` on completed stop/restart; docs). One test made hermetic (the preflight launcher test assumed port 4500 was free).
- **ASK (evaluator), answered by the ROOM SESSION:** the fixed code runs in the SERVICE process. The global 51985 runs the pre-fix build labelled 8.6.2, and the trusted preflight is idempotent on an exact version, so the fix needs a distinguishable version.
- **Evaluator rulings:**
  - 8.6.3 is the only honest route; 8.6.2 stays the pre-fix checkride build.
  - It prefers installing 8.6.3 via the trusted preflight INSIDE the isolated environment, so nothing global is armed before J5.
  - R9 is GO now.
  - A concern about the literal `run` remedy (a verbatim copy restarts work on a full-access implementer).
- **FIX LANE follow-up (ROOM SESSION):** the detached remedy now leads with `codex-worker session resume --session <uuid>` ("Re-attach … without starting a turn"). The second action is `run --name <w> --prompt "Report your status; do not start new work."` ("this runs a turn, so replace the prompt…"). Docs updated.
- **DECIDE requested** from the orchestrator/human: 8.6.3 and install timing.

### Step 14 (J3 carry-over, R9 → step33)
- **RUN:** global `history --name research-5d2b8e --tail 2` → exit 0. Both turns in order (`01a0f30c-8c62…`, then `01a0f313-eae3…`) with their final answers; `older_available:false`. It closes J3's "both turns visible" (turns carry messages only; F12 stands).
- **JUDGE R9 (evaluator):** OK; **J3 done** (status, messages and history discharged). The turn timestamps agree with the measured wall time.
  - **F17** (advisory, RESIDUAL): `started_at`/`completed_at` are bare epoch seconds.
  - `history` requiring attachment is a RESIDUAL design question.
  - The remedy change is accepted in principle and judged live in R5 (the no-turn re-attach: exit 0, then status attached, history shows no new turn, and the next run still searches).
  - The doc passage on the `session` family needs reconciling; the ROOM SESSION did so (codex-worker.md: "That one command is also the ordinary no-turn re-attach offered by `worker_detached`").

## Resume, 2026-10-06 (fix re-ride)
- **DECIDE (supplements-orchestrator D362, provisional; the human may override): option 1.** Install 8.6.3 via the trusted preflight INSIDE the isolated environment only and re-ride the fix there. The machine-wide install is the first step of a supervised J5 window; J5 and any machine-wide replacement of the 8.6.2 global service stay on HOLD for the human's GREEN-LIGHT.
- **Branch:** 22f892a (8.6.3 = CWS-1 + F15 + F16 + the no-turn re-attach remedy).
- **Environment drift since 09-30:**
  - **codex-cli is now 0.160.0.**
  - macOS periodic cleanup removed parts of `/private/tmp/cw-iso-e7a1c4` (`state`, `work`, `work2`), so its registry can no longer load (the worker cwds are gone). The re-ride uses a FRESH isolated environment.
  - The global service is now pid 11784 (it was replaced or restarted since 09-30), 8.6.2, 8 workers, 0 active.
- **ROOM SESSION development probe on codex-cli 0.160.0** (not a ride step): `app-server --listen unix://PATH` still makes PATH a symlink into `/private/tmp/codex-daemon-501/<sha>`; the target is an owner-only socket in the 0700 directory; SIGTERM to the owned group removes the link and the target. Same layout as 0.158.
- **Evaluator re-ride RULING (2026-10-06):** GO with amendments (one wrapper for the ISO environment; keep the active-turn refusal on codex 0.160; R6b missing-cwd worker; R8b/R8c stopped-path variants). Plus an **ASK**: what showed that the old isolated registry "can't load"?
- **ROOM SESSION answer and URGENT finding (F19):**
  - The original statement was a code inference (`registry._record`: `Path(cwd).resolve(strict=True)` → `RegistryError("cwd must be an existing directory")`, which fails the whole registry load; daemon.log line 293 shows this exact failure on a legacy registry).
  - Then checked against the LIVE global registry with a **read-only** `SessionRegistry.read_existing()` using the installed 8.6.5 code. Result: **"LOAD FAILS: invalid registry record … cwd must be an existing directory"**; file unchanged.
  - Cause: the ride's global worker `research-5d2b8e` has cwd `/private/tmp/cw-ride-5d2b8e`, which macOS periodic `/tmp` cleanup deleted.
  - The running global service (8.6.5, pid 98477, started 2026-10-02 16:08, **40 workers, 2 active**) loaded the registry before the deletion. Its NEXT start (any restart, crash, reboot or generation replacement) would have failed for every room.
  - **Mitigation (ROOM SESSION, its own directory):** `mkdir /private/tmp/cw-ride-5d2b8e` (empty). Re-check: "LOADS OK: 40 records", no record with a missing cwd, registry file unchanged.
  - **Not a permanent fix:** the directory can be cleaned again, and any room's worker whose worktree cwd is later removed bricks the registry the same way.
- **Version drift (ROOM SESSION facts):**
  - Another session built on this branch: 22f892a is an ancestor of `fix/codex-worker-private-websocket` c2e26b1 (8.6.5, the primary checkout).
  - The machine-wide tool is **8.6.5** (installed 2026-10-02 15:33), and the global service runs 8.6.5. So the machine-wide install and global generation replacement happened outside this ride.
  - This branch's unpublished 8.6.3 is superseded, and origin/main is still 8.6.1.
  - The re-ride is PAUSED pending orchestrator direction on what to ride and publish.
- **Ledger correction:** the "Resume" entry's "global service is now pid 11784 (8.6.2, 8 workers)" was a STALE observation from the ROOM SESSION's 2026-10-02 morning status read. The current fact (2026-10-06): 8.6.5, pid 98477, started 2026-10-02 16:08, 40 workers, 2 active.
- **Evaluator:** F19 recorded (safety, HIL-NEEDED, blocks-milestone, blocks any global generation action until fixed or excepted). Draft verdict structure issued; final verdict only at RIDE END. Process finding for the orchestrator: machine-wide HOLDs are invisible to other sessions (another session installed 8.6.5 and replaced the global generation while J5 was on HOLD).
- **DECIDE (supplements-orchestrator D367, provisional; the human informed of the deadline):**
  - Implement (a) the tolerant registry load, then (b) `retire`, test-first, on a NEW branch `fix/codex-worker-registry-tolerant` cut from c2e26b1 (the 8.6.5 tip of the human's `fix/codex-worker-private-websocket`).
  - Re-ride (i) in isolation against codex-cli 0.160, which also covers the paused F15/F16 re-ride.
  - The machine-wide install stays HUMAN-gated (a HIL-NEEDED with the exact step and a quiet-window check).
  - Keep `/private/tmp/cw-ride-5d2b8e` alive (touch it).
  - (c) the docs rule goes in with (a).
- **FIX LANE (ROOM SESSION):** 951046a (tolerant load; `worker_cwd_missing` -32044; `codex-worker retire --name`; docs) and c2392ad (8.6.6 bump and notes). Test-first; 665 tests green on 3.9 and 3.12 except the 7 known unrelated pins. Branch pushed; not published.

### Fix re-ride (8.6.6, codex-cli 0.160, fresh isolated environment)
- **RULE (evaluator), re-ride plan:** GO with amendments.
  - **Wrapper discipline is the main safety gate:** every 8.6.6 command line begins with `$ISO/iso-env`, otherwise STOP before it runs.
  - R0b also captures `rev-parse HEAD`, a clean `skills/` tree, and the global symlink before and after (identical).
  - R2c: after the refused retire, `status` shows the record and turn intact; the refused stop carries `worker_attachment:"unchanged"`; no `--force` offered.
  - R5: plus `messages --tail 1`.
  - R6 reuses `step29.question.md`.
  - **R6b: an isolated `daemon restart` while the cwd is missing** (the real F19 failure is the load at generation start); then iso5 unaffected, iso6 run → `worker_cwd_missing`, retire, then not_found.
  - **R6c:** retire the idle detached iso5b.
  - **R8d:** retire the idle attached iso5 before the final stop (0 workers; the stop impact must not count the retired thread).
  - End state: an empty isolated registry.
- `/private/tmp/cw-ride-5d2b8e` was touched on 10-06 (several times). Its permanent fix (`retire --name research-5d2b8e`, global) belongs inside the human-gated install window.
- **RUN R0 (executor, ISO `/private/tmp/cw-iso-7c2d`, wrapper `$ISO/iso-env`):**
  - **R0a1:** global ready, 8.6.5, pid 98477 / app-server 98478, 42 workers (2 active: `c1-1461-4f8a`, `final-review-d817`), research-5d2b8e listed.
  - **R0a2:** 8.6.5.
  - **R0a3:** codex-cli 0.160.0.
  - **R0a4:** both started Fri Oct 2 16:08:43; the service runs on the macOS CommandLineTools Python 3.9.
  - **R0b0:** `FORCE_COLOR=3`.
  - **R0b1:** HEAD cc21fa2; `skills/` clean.
  - **R0b2 = R0b7:** the global symlink is unchanged (`diff` exit 0).
  - **R0b3:** `$ISO/iso-env …/install-codex-worker` → **exit 1**, stderr `codex-worker preflight: uv tool dir --bin returned a missing directory: /private/tmp/cw-iso-7c2d/home/.local/bin`. The preflight requires uv's bin directory to exist BEFORE installing, so on a fresh home it can't make the first install.
  - **R0b4:** exit 127 (not installed).
  - **R0b5:** only `codex` (0.160.0) is on the isolated PATH.
  - **R0b8:** global still 8.6.5.
  - The executor stopped and asked for a ruling on creating `$ISO/home/.local/bin` (omitted from the setup).
- **JUDGE R0 (evaluator):** R0a and the global baselines OK. Positive CWS-3 evidence: under `FORCE_COLOR=3` the preflight's message printed a clean path, with no ANSI.
  - **F20** (blocks-milestone, DESIGN-DOC, pre-existing since 8.1.x): the trusted preflight can't make a first install on a home without `~/.local/bin`. It checks `[ -d ]` before `uv tool install`, which would create the directory. Fix direction: validate the path's shape (absolute, no control characters), then create the directory or check after the install, with a runnable remedy. The gate itself must stay.
  - **Fixture RULING:** GO for `mkdir -p $ISO/home/.local/bin`, as fixture parity with the operator's real `~/.local/bin` (exists, `drwxr-xr-x … Oct 6 11:55`). Re-run to new ids `rr-R0b3r…R0b8r`; keep the failed evidence.
- **RUN R0b*r** (after `mkdir -p $ISO/home/.local/bin`, fixture parity):
  - R0b3r: the preflight → exit 0, `codex-worker ready: /private/tmp/cw-iso-7c2d/home/.local/share/uv/tools/codex-worker/bin/codex-worker (8.6.6)`
  - R0b4r: 8.6.6
  - R0b5r: the isolated codex-worker on PATH; codex 0.160.0
  - R0b6r: interpreter `#!…/cw-iso-7c2d/home/.local/share/uv/tools/codex-worker/bin/python` (Homebrew 3.14)
  - R0b7r: the global symlink identical to R0b2
  - R0b8r: global 8.6.5
- **RUN R1:** isolated status stopped, 8.6.6, 0 workers; no `cw-iso-7c2d` process; daemon dir baseline (global target `6c89…` inode 94656460); 4612 free; `rt` empty.
- **RUN R2:** `$ISO/iso-env codex-worker start --name research-iso5-7c2d … --read-only --search --no-callback --app-server-listen ws://127.0.0.1:4612` → exit 0.
  - Listener 4612; `config {"web_search":"live"}`; model `gpt-6.1-sol`; webSearch 3, commandExecution 2; the answer cites the EU Register PDF (p. 353).
  - The service started under codex-cli 0.160's symlinked socket.
- **RUN R2b:**
  - Isolated chain 50818 (Python 3.14, pgid 50818) → 50819 node (pgid 50819) → 50820 codex → **51435 code-mode-host (own pgid)**.
  - New target `de4d481c…` (96462386) plus its `.lock`; the global target unchanged.
  - `rt/scw-501-global/c → …/de4d481c…`.
- **RUN R2c:** iso5b in the background (PID 54301, never signalled).
  - R2c1 (+3 s): status shows 0 active (registered and idle; its turn had not begun).
  - **R2c2:** `retire --name research-iso5b-7c2d` → exit 3, `-32004 turn_active`, `known_ids.turn_id 01a11078-c7d6…`; next_actions status/messages/interrupt ("Cancel only if deliberate"); no `--force`.
  - R2c3: status → `active_turn_id 01a11078-c7d6…`, record intact.
  - **R2c4:** `daemon stop` → exit 3, `-32040 service_busy` naming the iso5b active turn; no `--force`. The details carry no `worker_attachment` field.
  - `wait` → exit 0; the turn completed unaffected (58.8 s, webSearch 14).
- **JUDGE R0b*r–R2c (evaluator):** all OK.
  - **CWS-3 DISCHARGED** (the preflight works under `FORCE_COLOR=3`).
  - **CWS-2 DISCHARGED live** (the isolated service runs on Python 3.14; typed faults render clean).
  - CWS-1 readiness holds on codex 0.160 with 8.6.6.
  - The active-work gates hold on 0.160 (retire → `turn_active`, stop → `service_busy`, no `--force`; the turn completed unaffected).
  - Procedural note: re-read the status before a gate probe.
  - The `worker_attachment` expectation on a refusal is withdrawn (the contract puts it on completed results only).
  - **F21** (open): an in-flight `start` (registered, turn not yet begun) shows as idle with 0 active turns in `daemon status`, which is J5's impact report. To be settled by **R7b** (a background `start` then an immediate stop, before R8).
- **RUN R3** (pre-read rr-R3pre: 2 idle, 0 active):
  - `daemon restart` → exit 0. maintenance `{action restart, completed, forced false, 2 idle, durable_state preserved, **worker_attachment "detached_until_next_run"**}`; new service pid 63854 / app-server 63860 on 4612.
  - R3b: 50818/50819/50820 and **51435 ABSENT**; no isolated code-mode-host left (the only one is global pid 111, child of 98479); new chain 63854 → 63860 → 63861; global chain present.
  - R3c: target `de4d481c…` has a NEW inode 96488063 (was 96462386); global 94656460 and managed 95951440 unchanged.
  - R3d: link `c` recreated (96488064).
  - R3e: global ready 8.6.5, 98477/98478, 4500 (42 workers, 2 active; other rooms).
- **RUN R4:** `status`, `messages` and `history` on iso5 AND iso5b → all six exit 3, `-32043 worker_detached` "Worker is detached from this service generation". next_actions[0] `codex-worker session resume --session <that worker's uuid>`; [1] `run --name … --prompt 'Report your status; do not start new work.'` ("this runs a turn…"). No `daemon start`, no exit 1.
- **RUN R5:**
  - `session resume --session 91358e56…` (the exact next_action) → exit 0, attached true, config live.
  - `status` → attached true, `active_turn_id` null, **`latest_turn` null** (the restarted runtime holds no turn history).
  - `history --tail 5` → only the R2 turn, `returned` 1 (no new turn).
  - `messages --tail 1` → R2's answer, **`latest_cursor` null**.
