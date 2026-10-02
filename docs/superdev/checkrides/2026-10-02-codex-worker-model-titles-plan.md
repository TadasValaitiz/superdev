# Worker model/title verification plan

Operator goal: start a worker with the requested default model and effort, find its
exact name through the native remote agent view, and continue the same worker.

Changed surfaces: named worker creation policy and native thread naming.
Neighbouring surfaces: remote agents, run, and non-forced daemon cleanup.
Starting point: a disposable empty service store with real Codex authentication,
installed plugins enabled, and no existing worker assigned to this verification.

| Journey | Surface | Expected behavior | Refusal path |
|---|---|---|---|
| J1 | start, remote agents | Default gpt-6.1-sol/medium; exact worker name visible; read-only and no callbacks | Missing model/auth/service pauses verification; no substitution |
| J2 | run | Same thread/model/effort; new completed turn | Native naming failure is covered by fail-closed CLI integration tests |
| J3 | daemon stop | Only the disposable service exits, without force | Active work refuses cleanup |

Actual substrate: real Codex CLI/app-server, real account model catalog and short
operator-authored prompts. A temporary HOME stores service state; CODEX_HOME remains
the real authenticated Codex directory. No fake provider, fixture or recorded response.
TMPDIR is also scoped to that disposable directory to isolate runtime sockets.
Preflight: installed Codex CLI works; live model discovery advertises the requested
model and medium effort. Ports 4500 and 4501 are excluded from all writes.
The native remote view is inspected through its actual terminal interface.
Not ridden: user-managed services restart, old worker renaming, or Claude callbacks
(unchanged here; existing 8.6.4 callback verification remains the evidence).
Non-blocking observations are recorded in the scenario's Residuals section, not
left only in the ride ledger.
