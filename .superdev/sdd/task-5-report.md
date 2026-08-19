# Task 5 report

- RED receipts:
  - `python3 -W error::ResourceWarning -m unittest tests.codex-worker.test_rpc_cli.CliTests.test_common_parser_exhaustively_validates_names_prompts_and_turn_options tests.codex-worker.test_rpc_cli.CliTests.test_endpoint_selector_matrix_and_absolute_socket_validation -v` failed because explicit `--tier medium --model` bypassed argparse mutual exclusion and relative socket/state/session-cwd paths reached execution.
  - `python3 -W error::ResourceWarning -m unittest tests.codex-worker/test_rpc_cli.py -v` initially hung in the relative-socket foreground-serve case, proving validation happened after the blocking leaf. The run was terminated, the test was converted to a deterministic serve sentinel, and the empty `relative.sock.lock` artifact from that run was removed.
  - `python3 -W error::ResourceWarning -m unittest tests.codex-worker.test_rpc_cli.ManagedProcessLifecycleTests.test_concurrent_clients_share_one_daemon_without_crossing_results -v` failed with client exit `1` because the fake returned one shared `thr-fake` identity.
  - `python3 -W error::ResourceWarning -m unittest tests.codex-worker.test_rpc_cli.ManagedProcessLifecycleTests.test_repeated_stop_then_run_restarts_the_same_thread -v` failed with `-32020/codex_failure` and `unknown runtime session`, proving a fresh daemon did not resume durable state before `run`.
  - `python3 -W error::ResourceWarning -m unittest tests.codex-worker.test_rpc_cli.RpcServerTests.test_socket_is_owner_only_immediately_when_bound -v` failed with bind-time mode `0755` rather than `0600`; a subsequent process rerun independently observed `-32017/socket_endpoint_unsafe` during restart readiness.
- GREEN changes:
  - Parser leaves now reject invalid instance IDs and non-absolute explicit socket/state/raw-session cwd paths locally, preserve exact one-object `id: "cli"` envelopes, and distinguish the default tier from an explicitly supplied mutually exclusive tier.
  - The fake Codex deterministically mints distinct thread/turn/item identities and preserves per-thread active-turn/cwd/message correlation while retaining the original first `thr-fake` fixture identity and configurable modes.
  - Five real concurrent client processes converge on one daemon PID with five distinct names, session IDs, thread IDs, cwd values, and prompt-correlated finals. Disconnect and finite-timeout cases leave daemon work active.
  - A fresh daemon resumes an unknown/detached in-memory session from durable state before `run`, so stop/stop/run keeps the original thread.
  - RPC sockets are created owner-only at bind time under a temporary `0177` umask, eliminating the readiness race without weakening endpoint checks.
- Fresh verification:
  - `python3 -W error::ResourceWarning -m unittest tests/codex-worker/test_rpc_cli.py -v` — PASS, 57 tests.
  - `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` — PASS, 238 tests, 1 skipped.
  - `python3 -m py_compile skills/subagent-driven-development/scripts/codex_worker/rpc.py skills/subagent-driven-development/scripts/codex_worker/cli.py skills/subagent-driven-development/scripts/codex_worker/facade.py tests/codex-worker/fake_codex.py tests/codex-worker/test_rpc_cli.py` — PASS.
  - `git diff --check` — PASS.
- Files changed: `.superdev/sdd/task-5-report.md`, `skills/subagent-driven-development/scripts/codex_worker/cli.py`, `skills/subagent-driven-development/scripts/codex_worker/facade.py`, `skills/subagent-driven-development/scripts/codex_worker/rpc.py`, `tests/codex-worker/fake_codex.py`, and `tests/codex-worker/test_rpc_cli.py`.
