# Codex worker shared app-server — executor transcript

**Status:** PENDING fresh controller-dispatched medium executor
**Behavioral candidate:** `8dbe8e0`
**Role boundary:** demonstrate only; do not issue a PASS/FAIL verdict

This skeleton deliberately contains no claimed ride results. The executor must drive the
scope in the parent checkride one command at a time and preserve literal argv, cwd,
stdout, stderr, exit code, elapsed time, substrate/honesty label, relevant process and
listener evidence, and exact cleanup ownership verification.

Retain failed attempts as failed attempts. Do not relabel SIMULATED production fixtures
as measured live behavior. Do not target the current-user/global installed service; use
fresh owner-tokened isolation and delete only verified isolated runtime resources in
`finally` cleanup.
