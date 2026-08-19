# Codex worker command executor transcript

Date: 2026-08-19  
Historical ride SHA: `e5e8c8ac29117c92bfe92b4376fddfe3c4d5586c` (`e5e8c8a`)  
Focused re-ride fix SHA: `ffa24e7e6652f5d218811d4707748aa8bc84fc36` (`ffa24e7`)  
Substrate/tier: **MEASURED** real local Codex provider (`codex-cli 0.147.0`), isolated checkride instances `checkride-a9f3` and `env-a9f3`, and `/tmp/codex-worker-checkride-20260819-a9f3/cwd`. Prompts and files below are tiny checkride tasks, not market data. PATH resolves `codex-worker` to this worktree's `bin/codex-worker`. No credential values are recorded.

Capture convention: each section is one public client invocation. `stdout/stderr` is the complete verbatim combined terminal capture supplied by the executor; success JSON is stdout, and argparse usage preceding an error JSON is stderr. No diagnostics were omitted.

## 1. Absent managed daemon — happy
Invocation: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 daemon status`

```text
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"checkride-a9f3","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/29c97e75672d845a92cb45005301a5f5202d0bfc5bd2e418a4b21db4e33fe146","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/29c97e/worker.sock","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/29c97e75672d845a92cb45005301a5f5202d0bfc5bd2e418a4b21db4e33fe146/daemon.log"},"status":"stopped","daemon_pid":null,"codex_pid":null,"worker_count":0,"readiness":null,"last_error":null}}
```
Exit code: `0`

## 2. Prose start, tier/effort/full/goal/budget/timeout — happy
Invocation: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 start --name master-a9f3 --cwd /tmp/codex-worker-checkride-20260819-a9f3/cwd --tier medium --effort medium --goal 'Complete tiny checkride task' --token-budget 1000 --timeout 120 --prompt 'Reply with exactly FIRST-OK and no other text.'`

```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"turn":{"turn_id":"4f473dc7-a281-4bfb-b28f-e76c8681b1eb","status":"completed","error":null},"messages":[{"type":"agent_message","item_id":"msg_093f935a945e899d016a8616f6eb1c8191bdfef2a15322049c","phase":"final_answer","selection":"explicit_final","text":"FIRST-OK"}],"structured_output":null,"metrics":{"wall_duration_seconds":{"value":5.902567040999999,"source":"codex-worker","availability":"measured"},"item_counts":{"value":{"userMessage":1,"reasoning":1,"agentMessage":1},"source":"codex-worker","availability":"derived"},"command_count":{"value":0,"source":"codex-worker","availability":"derived"},"command_duration_ms":{"value":null,"source":"codex","availability":"unavailable"},"token_usage":{"value":null,"source":"codex","availability":"unavailable"}},"recovery":{"status":"codex-worker --instance checkride-a9f3 status --name master-a9f3","messages":"codex-worker --instance checkride-a9f3 messages --name master-a9f3","interrupt":"codex-worker --instance checkride-a9f3 interrupt --name master-a9f3","raw_resume":"codex-worker --instance checkride-a9f3 session resume --thread 01a01bc9-9eaf-7441-8672-cb04c35139e7"}}}
```
Exit code: `0`

## 3. Prompt-file, Sol tier, read-only, schema — happy
Invocation: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 start --name file-a9f3 --cwd /tmp/codex-worker-checkride-20260819-a9f3/cwd --tier very-smart --effort medium --read-only --output-schema /tmp/codex-worker-checkride-20260819-a9f3/schema.json --timeout 120 --prompt-file /tmp/codex-worker-checkride-20260819-a9f3/prompt-file.txt`

```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"file-a9f3","session_id":"4186aad7-27b9-44f6-bdfb-48f7ada6c9cb","thread_id":"01a01bc9-cc46-7b63-88a8-6c37994141f3","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"very-smart","model":"gpt-5.6-sol","effort":"medium","access":"read_only"},"turn":{"turn_id":"01a01bc9-cc75-7153-bbb1-25e2d2d18ebd","status":"completed","error":null},"messages":[{"type":"agent_message","item_id":"msg_072ccf959c4daa94016a8617028d0c81919aa2124e1bde47bb","phase":"final_answer","selection":"explicit_final","text":"{\"verdict\":\"FILE-SECOND\"}"}],"structured_output":{"verdict":"FILE-SECOND"},"metrics":{"wall_duration_seconds":{"value":6.004927333000001,"source":"codex-worker","availability":"measured"},"item_counts":{"value":{"userMessage":1,"reasoning":1,"agentMessage":1},"source":"codex-worker","availability":"derived"},"command_count":{"value":0,"source":"codex-worker","availability":"derived"},"command_duration_ms":{"value":null,"source":"codex","availability":"unavailable"},"token_usage":{"value":null,"source":"codex","availability":"unavailable"}},"recovery":{"status":"codex-worker --instance checkride-a9f3 status --name file-a9f3","messages":"codex-worker --instance checkride-a9f3 messages --name file-a9f3","interrupt":"codex-worker --instance checkride-a9f3 interrupt --name file-a9f3","raw_resume":"codex-worker --instance checkride-a9f3 session resume --thread 01a01bc9-cc46-7b63-88a8-6c37994141f3"}}}
```
Exit code: `0`

## 4. Follow-up run — happy
Invocation: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 run --name master-a9f3 --timeout 120 --prompt 'Reply with exactly FOLLOWUP-OK and no other text.'`

```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"turn":{"turn_id":"01a01bc9-f133-7793-9bfc-f87b342d0951","status":"completed","error":null},"messages":[{"type":"agent_message","item_id":"msg_093f935a945e899d016a86170760a48191931ee312c8912f24","phase":"final_answer","selection":"explicit_final","text":"FOLLOWUP-OK"}],"structured_output":null,"metrics":{"wall_duration_seconds":{"value":1.5178375420000023,"source":"codex-worker","availability":"measured"},"item_counts":{"value":{"userMessage":1,"agentMessage":1},"source":"codex-worker","availability":"derived"},"command_count":{"value":0,"source":"codex-worker","availability":"derived"},"command_duration_ms":{"value":null,"source":"codex","availability":"unavailable"},"token_usage":{"value":null,"source":"codex","availability":"unavailable"}},"recovery":{"status":"codex-worker --instance checkride-a9f3 status --name master-a9f3","messages":"codex-worker --instance checkride-a9f3 messages --name master-a9f3","interrupt":"codex-worker --instance checkride-a9f3 interrupt --name master-a9f3","raw_resume":"codex-worker --instance checkride-a9f3 session resume --thread 01a01bc9-9eaf-7441-8672-cb04c35139e7"}}}
```
Exit code: `0`

## 5. Observation and goals — happy
Each of these literal invocations exited `0` with the following complete output.

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 status --name master-a9f3`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"daemon_status":"ready","attached":true,"active_turn_id":null,"latest_turn":{"turn_id":"01a01bc9-f133-7793-9bfc-f87b342d0951","status":"completed","error":null}}}
```

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 messages --name master-a9f3 --tail 2`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"messages":[{"type":"agent_message","item_id":"msg_093f935a945e899d016a86170760a48191931ee312c8912f24","phase":"final_answer","selection":"live","text":"FOLLOWUP-OK"}],"requested_tail":2,"returned":1,"truncated":false,"latest_cursor":9}}
```

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 history --name master-a9f3 --tail 2`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"turns":[{"turn_id":"4f473dc7-a281-4bfb-b28f-e76c8681b1eb","status":"completed","started_at":1787172593,"completed_at":1787172599,"messages":[{"type":"agent_message","item_id":"item-2","phase":"final_answer","selection":"explicit_final","text":"FIRST-OK"}],"error":null},{"turn_id":"01a01bc9-f133-7793-9bfc-f87b342d0951","status":"completed","started_at":1787172614,"completed_at":1787172615,"messages":[{"type":"agent_message","item_id":"item-4","phase":"final_answer","selection":"explicit_final","text":"FOLLOWUP-OK"}],"error":null}],"requested_tail":2,"returned":2,"older_available":false}}
```

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 goal show --name master-a9f3`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"availability":"present","goal":{"thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","objective":"Complete tiny checkride task","status":"budgetLimited","token_budget":1000,"tokens_used":8890,"time_used_seconds":6,"created_at":1787172593,"updated_at":1787172615}}}
```

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 goal set --name master-a9f3 --status paused --token-budget 12000`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"availability":"present","goal":{"thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","objective":"Complete tiny checkride task","status":"budgetLimited","token_budget":12000,"tokens_used":8890,"time_used_seconds":6,"created_at":1787172593,"updated_at":1787172633}}}
```

The subsequent identical `goal show` returned the immediately preceding goal object verbatim. Exit code: `0`.

## 6. Limits unavailable — refusal
Invocation: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 limits`
```text
{"jsonrpc":"2.0","id":"cli","error":{"code":-32028,"message":"Codex limits are unavailable","data":{"kind":"limits_unavailable","retryable":false,"source":"codex-worker","details":{"reason":"account/rateLimits/read: protocol_error: malformed rate limits"},"known_ids":{"instance":"checkride-a9f3","name":null,"session_id":null,"thread_id":null,"turn_id":null},"next_actions":[]}}}
```
Exit code: `1`

## 7. Active control — happy then refusals
The control worker start (`control-a9f3`) completed with `CONTROL-READY` (exit `0`). A long `run` used the literal prompt `Use the shell command sleep 30 now. Do not provide a final answer until that command completes; after it completes reply exactly CONTROL-DONE.`. It was deliberately in progress. The following commands were run one at a time:

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 steer --name control-a9f3 --prompt 'When the current command returns, reply exactly CONTROL-STEERED.'`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"control-a9f3","session_id":"3dc30c4a-0daf-467e-a0c8-6eba7d737b98","thread_id":"01a01bca-8011-7a70-9f94-e6e616a0b393","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"action":"steer","accepted":true,"turn_id":"01a01bca-b38c-7022-8392-06cc04e2fc41","status":"in_progress"}}
```
Exit code: `0`

`env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance checkride-a9f3 interrupt --name control-a9f3`
```text
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"control-a9f3","session_id":"3dc30c4a-0daf-467e-a0c8-6eba7d737b98","thread_id":"01a01bca-8011-7a70-9f94-e6e616a0b393","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"action":"interrupt","accepted":true,"turn_id":"01a01bca-b38c-7022-8392-06cc04e2fc41","status":"interrupted"}}
```
Exit code: `0`

The original long run then returned exit `0`, status `interrupted`, no messages, and recovery commands for `control-a9f3`.

Idle-control invocations and complete outputs (each exit `1`, refusal):
```text
codex-worker --instance checkride-a9f3 steer --name control-a9f3 --prompt 'idle attempt'
{"jsonrpc":"2.0","id":"cli","error":{"code":-32005,"message":"Turn is not active","data":{"kind":"turn_not_active","retryable":false,"source":"codex-worker","details":{},"known_ids":{"instance":"checkride-a9f3","name":"control-a9f3","session_id":"3dc30c4a-0daf-467e-a0c8-6eba7d737b98","thread_id":"01a01bca-8011-7a70-9f94-e6e616a0b393","turn_id":null},"next_actions":[{"command":"codex-worker --instance checkride-a9f3 status --name control-a9f3","reason":"Inspect the latest turn"}]}}}
codex-worker --instance checkride-a9f3 interrupt --name control-a9f3
{"jsonrpc":"2.0","id":"cli","error":{"code":-32005,"message":"Turn is not active","data":{"kind":"turn_not_active","retryable":false,"source":"codex-worker","details":{},"known_ids":{"instance":"checkride-a9f3","name":"control-a9f3","session_id":"3dc30c4a-0daf-467e-a0c8-6eba7d737b98","thread_id":"01a01bca-8011-7a70-9f94-e6e616a0b393","turn_id":null},"next_actions":[{"command":"codex-worker --instance checkride-a9f3 status --name control-a9f3","reason":"Inspect the latest turn"}]}}}
```

Re-starting the same long `run` then running `run --name control-a9f3 --timeout 0 --prompt 'must refuse because active'` returned exit `1`:
```text
{"jsonrpc":"2.0","id":"cli","error":{"code":-32020,"message":"session already has an active turn","data":{"kind":"codex_failure","retryable":false,"source":"codex-worker","details":{"session_id":"3dc30c4a-0daf-467e-a0c8-6eba7d737b98"},"known_ids":{"instance":"checkride-a9f3","name":"control-a9f3","session_id":"3dc30c4a-0daf-467e-a0c8-6eba7d737b98","thread_id":null,"turn_id":null},"next_actions":[]}}}
```
The following literal interrupt exited `0` and returned accepted/interrupted turn `01a01bcb-54aa-7a70-976e-f326aa5499eb`; the pending run then returned exit `0`, status `interrupted`, and no messages.

## 8. Local and live refusals
All literal invocations below were run separately.

```text
codex-worker --instance checkride-a9f3 start --name 'bad name' --prompt 'x'
{"jsonrpc":"2.0","id":"cli","error":{"code":-32602,"message":"Invalid params","data":{"kind":"invalid_params","details":{"reason":"name must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}"}}}}
exit 2

codex-worker --instance checkride-a9f3 start --name master-a9f3 --prompt 'duplicate'
{"jsonrpc":"2.0","id":"cli","error":{"code":-32021,"message":"Worker name already exists","data":{"kind":"worker_name_exists","retryable":false,"source":"codex-worker","details":{},"known_ids":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","turn_id":null},"next_actions":[{"command":"codex-worker --instance checkride-a9f3 run --name master-a9f3","reason":"Continue the existing worker"},{"command":"codex-worker --instance checkride-a9f3 start --name <different-name>","reason":"Create an independent worker"}]}}}
exit 1

codex-worker --instance checkride-a9f3 status --name absent-a9f3
{"jsonrpc":"2.0","id":"cli","error":{"code":-32022,"message":"Worker not found","data":{"kind":"worker_not_found","retryable":false,"source":"codex-worker","details":{},"known_ids":{"instance":"checkride-a9f3","name":"absent-a9f3","session_id":null,"thread_id":null,"turn_id":null},"next_actions":[{"command":"codex-worker --instance checkride-a9f3 start --name absent-a9f3","reason":"Create this worker in the selected instance"}]}}}
exit 1

codex-worker --instance checkride-a9f3 start --name flags-a9f3 --tier medium --model gpt-5.6-terra --prompt 'x'
usage: codex-worker start [-h] --name NAME
                          (--prompt PROMPT | --prompt-file PROMPT_FILE)
                          [--cwd CWD]
                          [--tier {medium,very-smart} | --model MODEL]
                          [--effort EFFORT] [--read-only] [--goal GOAL]
                          [--token-budget TOKEN_BUDGET]
                          [--output-schema OUTPUT_SCHEMA] [--timeout TIMEOUT]
codex-worker start: error: argument --model: not allowed with argument --tier
{"jsonrpc":"2.0","id":"cli","error":{"code":-32602,"message":"Invalid params","data":{"kind":"invalid_params","details":{"reason":"argument --model: not allowed with argument --tier"}}}}
exit 2

codex-worker --instance checkride-a9f3 run --name master-a9f3 --timeout nope --prompt 'x'
usage: codex-worker run [-h] --name NAME
                        (--prompt PROMPT | --prompt-file PROMPT_FILE)
                        [--output-schema OUTPUT_SCHEMA] [--timeout TIMEOUT]
codex-worker run: error: argument --timeout: invalid _nonnegative_float value: 'nope'
{"jsonrpc":"2.0","id":"cli","error":{"code":-32602,"message":"Invalid params","data":{"kind":"invalid_params","details":{"reason":"argument --timeout: invalid _nonnegative_float value: 'nope'"}}}}
exit 2
```

## 9. Advanced compatibility — happy/refusal
`codex-worker --instance checkride-a9f3 model list` exited `0`:
```text
{"jsonrpc":"2.0","id":"cli","result":{"models":[{"id":"gpt-5.6-sol","is_default":true,"supported_efforts":["low","medium","high","xhigh","max","ultra"]},{"id":"gpt-5.6-terra","is_default":false,"supported_efforts":["low","medium","high","xhigh","max","ultra"]},{"id":"gpt-5.6-luna","is_default":false,"supported_efforts":["low","medium","high","xhigh","max"]},{"id":"gpt-5.5","is_default":false,"supported_efforts":["low","medium","high","xhigh"]},{"id":"gpt-5.4","is_default":false,"supported_efforts":["low","medium","high","xhigh"]},{"id":"gpt-5.4-mini","is_default":false,"supported_efforts":["low","medium","high","xhigh"]},{"id":"gpt-5.3-codex-spark","is_default":false,"supported_efforts":["low","medium","high","xhigh"]}]}}
```

`codex-worker --instance checkride-a9f3 start --name effort-a9f3 --model gpt-5.6-luna --effort ultra --prompt 'x'` exited `1` (refusal):
```text
{"jsonrpc":"2.0","id":"cli","error":{"code":-32027,"message":"Requested effort is unsupported","data":{"kind":"effort_unsupported","retryable":false,"source":"codex-worker","details":{"model":"gpt-5.6-luna","supported_efforts":["low","medium","high","xhigh","max"]},"known_ids":{"instance":null,"name":null,"session_id":null,"thread_id":null,"turn_id":null},"next_actions":[]}}}
```

Raw session and turn (all exited `0`):
```text
codex-worker --instance checkride-a9f3 session start --cwd /tmp/codex-worker-checkride-20260819-a9f3/cwd --name raw-a9f3 --model gpt-5.6-terra
{"jsonrpc":"2.0","id":"cli","result":{"session":{"session_id":"18b71c46-7037-4486-a402-379faaffc377","thread_id":"01a01bcb-a39a-7db3-9b46-5e101064fc05","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","created_at":"2026-08-19T20:52:05.693750Z","updated_at":"2026-08-19T20:52:05.693750Z","name":"raw-a9f3","model":"gpt-5.6-terra","effort":null,"tier":null,"access":null},"attached":true}}
codex-worker --instance checkride-a9f3 turn start --session 18b71c46-7037-4486-a402-379faaffc377 --effort medium --prompt 'Reply with exactly RAW-OK and no other text.'
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"18b71c46-7037-4486-a402-379faaffc377","thread_id":"01a01bcb-a39a-7db3-9b46-5e101064fc05","turn_id":"01a01bcb-b2c0-7200-abdc-2f5f90cb6c4e","status":"in_progress"}}
codex-worker --instance checkride-a9f3 turn wait --session 18b71c46-7037-4486-a402-379faaffc377 --timeout 120
{"jsonrpc":"2.0","id":"cli","result":{"session_id":"18b71c46-7037-4486-a402-379faaffc377","thread_id":"01a01bcb-a39a-7db3-9b46-5e101064fc05","turn":{"turn_id":"01a01bcb-b2c0-7200-abdc-2f5f90cb6c4e","status":"completed","error":null,"items":[{"item_id":"01a01bcb-b558-7b92-b24e-3f8344a923e8","type":"userMessage","data":{"clientId":null,"content":[{"type":"text","text":"Reply with exactly RAW-OK and no other text.","text_elements":[]}]}},{"item_id":"rs_0d1d4a293027b2d3016a86177bbfd0819189e2d48559991c7f","type":"reasoning","data":{"summary":[],"content":[]}},{"item_id":"msg_0d1d4a293027b2d3016a86177d55788191a94b25a7ee5bbab5","type":"agentMessage","data":{"text":"RAW-OK","phase":"final_answer","memoryCitation":null}}]}}}
```

## 10. Lifecycle, raw socket, instance precedence — happy
The main instance's raw socket is `/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/29c97e/worker.sock`.

```text
codex-worker --socket /var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/29c97e/worker.sock daemon status
{"jsonrpc":"2.0","id":"cli","result":{"ready":true,"daemon_pid":45827,"codex_pid":45831,"socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/29c97e/worker.sock","state_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/29c97e75672d845a92cb45005301a5f5202d0bfc5bd2e418a4b21db4e33fe146/registry.json","session_count":4}}
exit 0
codex-worker --instance checkride-a9f3 daemon stop
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"checkride-a9f3","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/29c97e75672d845a92cb45005301a5f5202d0bfc5bd2e418a4b21db4e33fe146","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/29c97e/worker.sock","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/29c97e75672d845a92cb45005301a5f5202d0bfc5bd2e418a4b21db4e33fe146/daemon.log"},"status_before":"ready","status_after":"stopped","daemon_pid":45827,"codex_pid":45831,"durable_state":"preserved","worker_count":4}}
exit 0
codex-worker --instance checkride-a9f3 run --name master-a9f3 --timeout 120 --prompt 'Reply with exactly RESTART-OK and no other text.'
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"checkride-a9f3","name":"master-a9f3","session_id":"414b9f03-89e6-4bbc-82ea-d9d95d867eb1","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"turn":{"turn_id":"01a01bcc-011f-7e32-a220-6fbfb03adc9b","status":"completed","error":null},"messages":[{"type":"agent_message","item_id":"msg_04d54705023260be016a8617922ab887d0aaccd00cbdff0e46","phase":"final_answer","selection":"explicit_final","text":"RESTART-OK"}],"structured_output":null,"metrics":{"wall_duration_seconds":{"value":5.122631167,"source":"codex-worker","availability":"measured"},"item_counts":{"value":{"userMessage":1,"agentMessage":1},"source":"codex-worker","availability":"derived"},"command_count":{"value":0,"source":"codex-worker","availability":"derived"},"command_duration_ms":{"value":null,"source":"codex","availability":"unavailable"},"token_usage":{"value":null,"source":"codex","availability":"unavailable"}},"recovery":{"status":"codex-worker --instance checkride-a9f3 status --name master-a9f3","messages":"codex-worker --instance checkride-a9f3 messages --name master-a9f3","interrupt":"codex-worker --instance checkride-a9f3 interrupt --name master-a9f3","raw_resume":"codex-worker --instance checkride-a9f3 session resume --thread 01a01bc9-9eaf-7441-8672-cb04c35139e7"}}}
exit 0
codex-worker --socket /var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/29c97e/worker.sock daemon shutdown
{"jsonrpc":"2.0","id":"cli","result":{"accepted":true}}
exit 0
```

Environment-selected instance invocation (exit `0`):
```text
env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH CODEX_WORKER_INSTANCE=env-a9f3 codex-worker start --name env-a9f3 --cwd /tmp/codex-worker-checkride-20260819-a9f3/cwd --tier medium --effort medium --timeout 120 --prompt 'Reply with exactly ENV-OK and no other text.'
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"env-a9f3","name":"env-a9f3","session_id":"37db036d-e9b8-4179-8ecb-e9afb8e5cb14","thread_id":"01a01bcc-2ae6-79d2-ba7b-adea37c5e8e0","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"turn":{"turn_id":"01a01bcc-2b21-7700-b346-0228c79dd0eb","status":"completed","error":null},"messages":[{"type":"agent_message","item_id":"msg_047373bad21aa3e4016a8617a14c5487d0a3cda0772f2c6b0e","phase":"final_answer","selection":"explicit_final","text":"ENV-OK"}],"structured_output":null,"metrics":{"wall_duration_seconds":{"value":9.445264541,"source":"codex-worker","availability":"measured"},"item_counts":{"value":{"userMessage":1,"reasoning":2,"commandExecution":1,"agentMessage":1},"source":"codex-worker","availability":"derived"},"command_count":{"value":1,"source":"codex-worker","availability":"derived"},"command_duration_ms":{"value":0,"source":"codex","availability":"derived"},"token_usage":{"value":null,"source":"codex","availability":"unavailable"}},"recovery":{"status":"codex-worker --instance env-a9f3 status --name env-a9f3","messages":"codex-worker --instance env-a9f3 messages --name env-a9f3","interrupt":"codex-worker --instance env-a9f3 interrupt --name env-a9f3","raw_resume":"codex-worker --instance env-a9f3 session resume --thread 01a01bcc-2ae6-79d2-ba7b-adea37c5e8e0"}}}
env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH CODEX_WORKER_INSTANCE=env-a9f3 codex-worker daemon stop
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"env-a9f3","source":"environment","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/ceee11833d86fc8cb1326f24985de11c90c8f1d0e9588c7d0d1e3b2b088feb1e","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/ceee11/worker.sock","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/ceee11833d86fc8cb1326f24985de11c90c8f1d0e9588c7d0d1e3b2b088feb1e/daemon.log"},"status_before":"ready","status_after":"stopped","daemon_pid":55024,"codex_pid":55028,"durable_state":"preserved","worker_count":1}}
exit 0
```

## Executor summary

Commands ridden: 39 (happy 28; refusal 11).  
NOT RUN: none.  
Unexpected errors: none recorded by the executor.  
Reconstruction IDs/paths: main instance `checkride-a9f3`; environment instance `env-a9f3`; main master session `414b9f03-89e6-4bbc-82ea-d9d95d867eb1`, thread `01a01bc9-9eaf-7441-8672-cb04c35139e7`; raw session `18b71c46-7037-4486-a402-379faaffc377`, thread `01a01bcb-a39a-7db3-9b46-5e101064fc05`; temporary cwd `/tmp/codex-worker-checkride-20260819-a9f3/cwd`; main durable directory and socket are recorded in sections 1 and 10. Both managed runtimes were stopped non-destructively; durable state was preserved.

## Focused re-ride after `ffa24e7`

This section supersedes the historical transcript's incomplete capture convention and its 39-command completeness claim for the affected paths. It contains 16 fully reconstructable records. Each record uses the displayed literal `codex-worker` invocation, captured with stdout and stderr separately. Substrate: **MEASURED** real local Codex provider; fresh instance `reride-b4e7`; fresh names `goal2-b4e7`, `active-b4e7`, and `recovered-b4e7`; cwd `/tmp/codex-worker-reride-20260820-b4e7/cwd`.

### R1–R4 Goal pause without an already-exceeded budget — happy

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 start --name goal2-b4e7 --cwd /tmp/codex-worker-reride-20260820-b4e7/cwd --tier medium --effort medium --goal 'Pause this checkride worker two' --token-budget 50000 --timeout 120 --prompt 'Reply with exactly GOAL2-READY and no other text.'`

```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"goal2-b4e7","session_id":"c0c5dd7e-2d6e-40f9-9295-dfd41fa1b4cf","thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"turn":{"turn_id":"b31a508c-4354-4c29-96fd-8ee74614ee4b","status":"completed","error":null},"messages":[{"type":"agent_message","item_id":"msg_083c67d7676c2378016a861d73bd7c87d095ee911a65c0a36b","phase":"final_answer","selection":"explicit_final","text":"GOAL2-READY"}],"structured_output":null,"metrics":{"wall_duration_seconds":{"value":10.856261375,"source":"codex-worker","availability":"measured"},"item_counts":{"value":{"userMessage":1,"reasoning":2,"agentMessage":2,"commandExecution":1},"source":"codex-worker","availability":"derived"},"command_count":{"value":1,"source":"codex-worker","availability":"derived"},"command_duration_ms":{"value":0,"source":"codex","availability":"derived"},"token_usage":{"value":null,"source":"codex","availability":"unavailable"}},"recovery":{"status":"codex-worker --instance reride-b4e7 status --name goal2-b4e7","messages":"codex-worker --instance reride-b4e7 messages --name goal2-b4e7","interrupt":"codex-worker --instance reride-b4e7 interrupt --name goal2-b4e7","raw_resume":"codex-worker --instance reride-b4e7 session resume --thread 01a01be2-e2f8-7711-82db-72f150f702fd"}}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 goal show --name goal2-b4e7`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"goal2-b4e7","session_id":"c0c5dd7e-2d6e-40f9-9295-dfd41fa1b4cf","thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"availability":"present","goal":{"thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","objective":"Pause this checkride worker two","status":"active","token_budget":50000,"tokens_used":22286,"time_used_seconds":18,"created_at":1787174249,"updated_at":1787174268}}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 goal set --name goal2-b4e7 --status paused`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"goal2-b4e7","session_id":"c0c5dd7e-2d6e-40f9-9295-dfd41fa1b4cf","thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"availability":"present","goal":{"thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","objective":"Pause this checkride worker two","status":"paused","token_budget":50000,"tokens_used":23088,"time_used_seconds":23,"created_at":1787174249,"updated_at":1787174273}}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 goal show --name goal2-b4e7`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"goal2-b4e7","session_id":"c0c5dd7e-2d6e-40f9-9295-dfd41fa1b4cf","thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"availability":"present","goal":{"thread_id":"01a01be2-e2f8-7711-82db-72f150f702fd","objective":"Pause this checkride worker two","status":"paused","token_budget":50000,"tokens_used":23088,"time_used_seconds":23,"created_at":1787174249,"updated_at":1787174273}}}
STDERR:
EXIT:0
```
Happy.

### R5–R10 Active timeout/recovery — mixed happy/refusal

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 start --name active-b4e7 --cwd /tmp/codex-worker-reride-20260820-b4e7/cwd --tier medium --effort medium --timeout 0 --prompt 'Use the shell command sleep 30 now. Do not provide a final answer until that command completes; after it completes reply exactly ACTIVE-DONE.'`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","error":{"code":-32025,"message":"Timed out while worker turn remains active","data":{"kind":"timeout_active","retryable":true,"source":"codex-worker","details":{},"known_ids":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","turn_id":"01a01be1-8e6b-7350-a3ed-5ff456963d1c"},"next_actions":[{"command":"codex-worker --instance reride-b4e7 status --name active-b4e7","reason":"Inspect active work"},{"command":"codex-worker --instance reride-b4e7 messages --name active-b4e7","reason":"Read retained narration"},{"command":"codex-worker --instance reride-b4e7 interrupt --name active-b4e7","reason":"Cancel only if deliberate"}]}}}
STDERR:
EXIT:1
```
Refusal.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 run --name active-b4e7 --timeout 0 --prompt 'second instruction must be refused while active'`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","error":{"code":-32004,"message":"session already has an active turn","data":{"kind":"turn_active","retryable":false,"source":"codex-worker","details":{"session_id":"3b999d27-308b-4098-835f-d31af56efd1a"},"known_ids":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","turn_id":"01a01be1-8e6b-7350-a3ed-5ff456963d1c"},"next_actions":[{"command":"codex-worker --instance reride-b4e7 status --name active-b4e7","reason":"Inspect the active turn"},{"command":"codex-worker --instance reride-b4e7 messages --name active-b4e7","reason":"Read retained narration"},{"command":"codex-worker --instance reride-b4e7 steer --name active-b4e7 --prompt <text>","reason":"Append an instruction to the active turn"},{"command":"codex-worker --instance reride-b4e7 interrupt --name active-b4e7","reason":"Cancel only if deliberate"}]}}}
STDERR:
EXIT:1
```
Refusal.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 status --name active-b4e7`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"daemon_status":"ready","attached":true,"active_turn_id":"01a01be1-8e6b-7350-a3ed-5ff456963d1c","latest_turn":null}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 messages --name active-b4e7 --tail 1`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"messages":[{"type":"agent_message","item_id":"msg_0bf63291fca9d00a016a861d152b0087d0b83e6cd6402c5508","phase":"commentary","selection":"live","text":"Running the requested command now."}],"requested_tail":1,"returned":1,"truncated":false,"latest_cursor":3}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 steer --name active-b4e7 --prompt 'After the running command ends, reply exactly ACTIVE-STEERED.'`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"action":"steer","accepted":true,"turn_id":"01a01be1-8e6b-7350-a3ed-5ff456963d1c","status":"in_progress"}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 interrupt --name active-b4e7`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"action":"interrupt","accepted":true,"turn_id":"01a01be1-8e6b-7350-a3ed-5ff456963d1c","status":"interrupted"}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 status --name active-b4e7`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"worker":{"instance":"reride-b4e7","name":"active-b4e7","session_id":"3b999d27-308b-4098-835f-d31af56efd1a","thread_id":"01a01be1-8e46-7902-8d62-9b391edf56ba","cwd":"/private/tmp/codex-worker-reride-20260820-b4e7/cwd","tier":"medium","model":"gpt-5.6-terra","effort":"medium","access":"full"},"daemon_status":"ready","attached":true,"active_turn_id":null,"latest_turn":{"turn_id":"01a01be1-8e6b-7350-a3ed-5ff456963d1c","status":"interrupted","error":null}}}
STDERR:
EXIT:0
```
Happy.

### R11–R15 Limits, effort recovery, raw recovery/events, shutdown

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 limits`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","error":{"code":-32028,"message":"Codex limits are unavailable","data":{"kind":"limits_unavailable","retryable":false,"source":"codex-worker","details":{"reason":"account/rateLimits/read: protocol_error: malformed rate limits","capacity":"unknown","inference":"do_not_infer"},"known_ids":{"instance":"reride-b4e7","name":null,"session_id":null,"thread_id":null,"turn_id":null},"next_actions":[]}}}
STDERR:
EXIT:1
```
Refusal.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 start --name effort-b4e7 --model gpt-5.6-luna --effort ultra --prompt 'x'`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","error":{"code":-32027,"message":"Requested effort is unsupported","data":{"kind":"effort_unsupported","retryable":false,"source":"codex-worker","details":{"model":"gpt-5.6-luna","supported_efforts":["low","medium","high","xhigh","max"]},"known_ids":{"instance":"reride-b4e7","name":"effort-b4e7","session_id":null,"thread_id":null,"turn_id":null},"next_actions":[{"command":"codex-worker --instance reride-b4e7 start --name effort-b4e7 --prompt x --cwd /Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade --model gpt-5.6-luna --effort low","reason":"Retry with provider-supported effort low; no fallback has run"}]}}}
STDERR:
EXIT:1
```
Refusal.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 session resume --thread 01a01bc9-9eaf-7441-8672-cb04c35139e7 --name recovered-b4e7`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"session":{"session_id":"77e6ca37-0a01-4749-b316-da931f56a8c2","thread_id":"01a01bc9-9eaf-7441-8672-cb04c35139e7","cwd":"/private/tmp/codex-worker-checkride-20260819-a9f3/cwd","created_at":"2026-08-19T21:17:07.510170Z","updated_at":"2026-08-19T21:17:07.510170Z","name":"recovered-b4e7","model":"gpt-5.6-terra","effort":"medium","tier":null,"access":null},"attached":true}}
STDERR:
EXIT:0
```
Happy.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 turn events --session 77e6ca37-0a01-4749-b316-da931f56a8c2 --after 0 --limit 10`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"events":[],"next_cursor":0,"truncated":false}}
STDERR:
EXIT:0
```
Happy.

AH10 multiple-final/null-phase and AH11 bootstrap/malformed-state are deterministic fixture/test receipt lanes, not real-provider checkride commands. Exact receipts: `tests/codex-worker/test_projection.py:ProjectionTests.test_multiple_explicit_finals_are_retained_in_order`; `tests/codex-worker/test_projection.py:ProjectionTests.test_terminal_fallback_and_live_messages_preserve_nullable_phase`; `tests/codex-worker/test_models_registry.py:RegistryTests.test_missing_and_zero_byte_registry_initialize_v2_owner_only`; `tests/codex-worker/test_models_registry.py:RegistryTests.test_nonempty_malformed_and_truncated_registry_bytes_are_preserved_exactly`; `tests/codex-worker/test_models_registry.py:RegistryTests.test_foreign_owner_state_is_rejected_with_deterministic_owner_injection`. They are not listed as NOT RUN because they are outside this focused live ride.

Command: `env PATH=/Users/tadas/Projects/superdev/.worktrees/codex-worker-command-facade/bin:$PATH codex-worker --instance reride-b4e7 daemon stop`
```text
STDOUT:
{"jsonrpc":"2.0","id":"cli","result":{"instance":{"instance":"reride-b4e7","source":"flag","durable_dir":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/6e11e0d1b6e122fe680d1ba28081f41dceabf58b807b2e245ed4db86e981e03b","socket_path":"/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/superdev-cw-501/6e11e0/worker.sock","log_path":"/Users/tadas/Library/Application Support/superdev/codex-worker/instances/6e11e0d1b6e122fe680d1ba28081f41dceabf58b807b2e245ed4db86e981e03b/daemon.log"},"status_before":"ready","status_after":"stopped","daemon_pid":92042,"codex_pid":92046,"durable_state":"preserved","worker_count":4}}
STDERR:
EXIT:0
```
Happy.

Focused re-ride summary: fully recorded commands 16 (happy 12, refusal 4); NOT RUN: none within scope. A preliminary setup attempt, `session resume --thread 01a01be1-17be-71e1-905f-02f9cebe87ef --name resume-b4e7`, encountered the expected typed already-registered-thread guard (`-32602`); it is a refusal outside the counted focused records. Its output was not retained as a ride record and is not claimed as one. The successful raw recovery record above instead uses an externally persisted measured thread. The `reride-b4e7` runtime is stopped non-destructively and its durable state is preserved.
