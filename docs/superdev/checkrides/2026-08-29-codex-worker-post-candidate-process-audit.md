# Codex worker post-candidate process audit erratum

**Date:** 2026-08-29

**Candidate audited:** `8dbe8e0`

**Result:** four exclusively identified Task 5 deterministic-fixture app-server
orphans terminated; four exact sockets and roots removed; installed and legacy
services untouched.

This is a cleanup-evidence correction, not a CLI checkride verdict. The earlier
claim that no isolated process/listener remained did not include these processes
and was therefore incomplete.

## Read-only ownership proof

| PID | PGID | Isolated root suffix | Start time (local) | Exact group membership |
|---:|---:|---|---|---|
| 35121 | 35120 | `tmpj7r_esaj` | 2026-08-28 23:16:40 | `[35121]` |
| 85580 | 85578 | `tmpnv9arkyf` | 2026-08-28 22:41:34 | `[85580]` |
| 87895 | 87894 | `tmpd6n888a3` | 2026-08-28 22:43:10 | `[87895]` |
| 97355 | 97354 | `tmpuqfdbc2l` | 2026-08-28 22:50:08 | `[97355]` |

For every row, the read-only audit observed all of the following before signalling:

- UID 501, PPID 1, and a positive one-member PGID distinct from the auditor's PGID;
- Python 3.9 executing the root-local `bin/codex app-server --listen` wrapper;
- the exact root-local private Unix listener `runtime/scw-501-global/c` as FD 4;
- root-local `HOME`, `XDG_STATE_HOME`, `TMPDIR`, and first PATH entry;
- `FAKE_CODEX_DELAY=3.0`, which is specific to
  `ManagedProcessLifecycleTests.setUp` in `test_rpc_cli.py`;
- the fixture's empty callback store, mode 0600, size 40, SHA-256
  `c5434f0e71dab332f0753ce4abc52998de387c6793466d68f228bf27a9a09fd9`.

These deterministic `TemporaryDirectory` fixtures predated and did not use the live
harness `fixture-owner.json` token mechanism. No owner-token file existed in any of
the four roots. Exclusive ownership was instead established by the complete
fixture-specific environment, argv, socket, artifact, UID, and one-member process-group
match. No installed-service or legacy-daemon process matched those roots or groups.

## Bounded cleanup result

Immediately before signalling, the audit revalidated every invariant above. It sent
SIGTERM only to pinned PGIDs 35120, 85578, 87894, and 97354. All four exited within the
bounded TERM interval; SIGKILL was not needed. It then verified:

- exact PIDs absent: 4/4;
- exact private Unix listeners absent: 4/4;
- exact isolated roots absent after removal: 4/4;
- matching residual Task 5 fake app-server processes/listeners: 0.

The removed roots were exactly:

- `/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/tmpj7r_esaj`;
- `/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/tmpnv9arkyf`;
- `/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/tmpd6n888a3`;
- `/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/tmpuqfdbc2l`.

## Regression guard

`ManagedProcessLifecycleTests` now pins the real fixture's returned
`app_server_pid` and exact private socket. Its cleanup must prove both are absent after
`daemon stop --force`, and
`test_force_stop_reaps_exact_app_server_and_private_listener` exercises the check
directly. Warning-strict results:

- selector: 1/1 PASS in 1.179 seconds;
- whole managed-process class after the final guard edit: 4/4 PASS in 11.823 seconds;
- complete final-source warning-strict deterministic suite: 552/552 PASS in 45.502 seconds;
- post-run matching fake app-server processes/listeners: 0.
