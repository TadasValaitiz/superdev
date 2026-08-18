# F1 stream-accurate manual lifecycle

Substrate: MEASURED real Codex CLI 0.147.0 at implementation SHA `55c630d399efad2b520a2d4b9b037987c6ba98b7`; disposable fixture `/tmp/cw-f1.SnZYn7`. Each command was executed with stdout and stderr redirected independently. The adjacent `.stdout` and `.stderr` files are byte-for-byte captures; byte counts below include the terminal newline where present. No streams are merged.

| # | Invocation | exit | stdout bytes | stderr bytes |
|---:|---|---:|---:|---:|
| 1 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock daemon serve --state /tmp/cw-f1.SnZYn7/state.json --event-limit 40` (foreground) | 0 | 0 | 63 |
| 2 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock session show --session 00000000-0000-4000-8000-000000000000` | 1 | 321 | 0 |
| 3 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn status --turn 11111111-1111-4111-8111-111111111111` | 2 | 232 | 243 |
| 4 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock session start --cwd /tmp/cw-f1.SnZYn7/repo --name f1-timeout --model gpt-5.6-sol` | 0 | 352 | 0 |
| 5 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn start --session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39 --prompt-file /tmp/cw-f1.SnZYn7/prompt.txt --model gpt-5.6-sol --effort low` | 0 | 215 | 0 |
| 6 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn wait --session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39 --timeout 0.01` | 1 | 688 | 0 |
| 7 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock turn wait --session 7d3ca9e2-7cd7-43cb-8333-b0cf7b5e8a39 --timeout 30` | 0 | 9280 | 0 |
| 8 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock daemon shutdown` | 0 | 56 | 0 |
| 9 | `python3 skills/subagent-driven-development/scripts/codex-worker --socket /tmp/cw-f1.SnZYn7/worker.sock daemon status` (post-shutdown) | 1 | 278 | 0 |

Exact streams:

- [serve.stdout](manual-f1-streams/serve.stdout) is empty (0 bytes); [serve.stderr](manual-f1-streams/serve.stderr) is exactly `codex-worker daemon listening on /tmp/cw-f1.SnZYn7/worker.sock\n`.
- [unknown.stdout](manual-f1-streams/unknown.stdout) contains the structured unknown-session JSON; [unknown.stderr](manual-f1-streams/unknown.stderr) is empty.
- [unsupported.stdout](manual-f1-streams/unsupported.stdout) contains the structured JSON error; [unsupported.stderr](manual-f1-streams/unsupported.stderr) contains the argparse usage and diagnostic.
- [timeout.stdout](manual-f1-streams/timeout.stdout) contains the actionable `wait_timeout` JSON; [timeout.stderr](manual-f1-streams/timeout.stderr) is empty.
- [completion.stdout](manual-f1-streams/completion.stdout) is the complete terminal completion JSON (9280 bytes); [completion.stderr](manual-f1-streams/completion.stderr) is empty.
- [shutdown.stdout](manual-f1-streams/shutdown.stdout) and [post-status.stdout](manual-f1-streams/post-status.stdout) preserve their JSON responses; both stderr files are empty.

The daemon process exited 0 after shutdown. This record is the authoritative stream-level evidence for the manual sections of the main checkride.
