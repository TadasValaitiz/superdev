# Checkride plan: codex-worker 8.6.2 research worker and codex-cli 0.158 service lifecycle

**Item:** superdev-codex-search (v8.6.0 `--search`/`--config`, v8.6.1 CWS-2/CWS-3, v8.6.2 CWS-1)
**Ruling:** D197, option 1 (supplements-orchestrator relaying the human): accept the codex-cli 0.158
symlinked socket only under owner-only rules. The acceptance is a checkride of start → run on the same
worker → daemon stop/restart under supervision.

## Checkride plan

**Surfaces this plan changes:**
- `codex-worker start` (`--search`, `--config KEY=VALUE`, `result.worker.config`)
- global service startup and readiness (the symlinked private socket)
- `daemon stop` / `daemon restart` teardown of the owned Codex process group and its link
- `install-codex-worker` (under `FORCE_COLOR`)

**Neighbouring surfaces the journey crosses:** `codex-worker --version`; the automatic service start
behind `start`; `run`; `status` / `messages` / `history`; `daemon status`; resuming a detached worker
after a restart.

**The operator's starting point:** a Claude room with codex-cli 0.158.0 installed and logged in, the
8.6.2 tool installed by the trusted preflight, the global service **stopped** (it could not start since
codex-cli 0.158.0 arrived on 2026-09-28), an empty scratch directory under `/private/tmp`, and a research
question in their own words. No worker exists for this question.

**Journeys to ride** (intent level):

| # | Operator goal | Command families crossed | What good looks like | Refusal paths that matter | Discharges |
|---|---|---|---|---|---|
| J1 | Create a durable research worker with live web search and ask one web question | `--version`, `start` (auto service start), `daemon status` | The service reaches readiness under codex-cli 0.158. One JSON object. `result.worker.config` shows live web search. Identity and attach routes are present. The answer cites real URLs and the metrics show web-search items. | `run` refuses `--search`/`--config` (creation-fixed); a duplicate name refuses with a runnable remedy | Brief §2, §4, §6; CWS-1 readiness |
| J2 | Ask a follow-up on the same worker, without reloading anything | `run` | Same session and thread ids, config unchanged, a cited answer. The operator can tell whether token usage is exposed (and honestly labelled if not). | — | Brief §6 (reuse) |
| J3 | Look back at the worker's state and history | `status`, `messages`, `history` | Attached, idle, both turns visible | — | neighbouring |
| J4 | Supervised diagnostic on an ISOLATED service: stop and restart the service a worker lives on, then continue that worker | isolated `start --app-server-listen`, `daemon status/stop/restart`, `run` | Stop reports its impact and leaves no Codex process and no private link behind. Restart reaches readiness again. `run` resumes the SAME thread with the creation config re-applied, and search still happens. | Stop while a turn is active refuses without `--force` | CWS-1 teardown; "reapplied on resume" |
| J5 | The same stop/restart on the GLOBAL service | `daemon status/stop/restart` | As J4, on the machine-wide service | — | D197 acceptance. HOLD: runs only after the human GREEN-LIGHTs the live global impact report |

**Actual data each journey needs:**

| Journey | Service / dataset | Scale | Availability check before the ride | If unavailable |
|---|---|---|---|---|
| J1–J3, J5 | Real Codex (ChatGPT login) through the real global codex-worker service and registry; the live web | One research question and one follow-up (the brief's use case) | `codex login status` → logged in (2026-09-30); web search returned live results in today's stdio check | STOP and ask the human |
| J4 | The same real Codex and web, through a disposable, freshly created service home (HOME / XDG_STATE_HOME / TMPDIR isolated per the repo's isolation wrapper; CODEX_HOME = the real `~/.codex` for auth) on a spare loopback port | One worker, one question, one follow-up after restart | The same checks | STOP and ask the human |

**Expectations the evaluator judges against:**
- Every client invocation prints exactly one JSON object; exit codes follow the surface (0 ok, 2 usage, 3 typed fault).
- A typed refusal names a remedy the operator can actually run. There are no tracebacks (the CWS-2 regression class).
- Nothing overclaims: token usage is either reported by Codex or labelled unavailable, never invented.
- The operator never needs source code, a Python one-liner, or a test helper for the main journey.
- Teardown never touches a process outside the owned group, and never unlinks a socket or link that
  differs from the one verified at readiness.

**Deliberately not ridden here:** callback delivery (`--no-callback` is used so the worker can be handed to
another room); `goal`/`limits`; legacy migration; non-loopback listeners.

## Amendment 2026-10-06 (from the ride)

- **The starting point is corrected.** A durable worker's scratch directory lives under the project or home,
  never under `/private/tmp` (F19). The ride's own J1 worker `research-5d2b8e` was created in
  `/private/tmp/cw-ride-5d2b8e`, which put the strict-loading 8.6.5 global service one macOS `/tmp` cleanup
  away from refusing to load its registry. Isolated throwaway services (J4) may stay under `/private/tmp`.
- **The re-ride scope (8.6.6 → 8.6.7, codex-cli 0.160) adds:**
  - `retire` (F18)
  - the tolerant registry load (F19)
  - `worker_attachment` on stop/restart (F15)
  - the re-attach reads (F22): `session resume` must be followed by `status`/`messages` before any `history`
- **J5 is unchanged:** it stays on HOLD until the human's GREEN-LIGHT. The machine-wide install of the fixed
  build is HUMAN-gated (D362, D367).
