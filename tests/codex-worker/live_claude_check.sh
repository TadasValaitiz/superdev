#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd -P)
LIVE_ROOT="$ROOT/.superdev/codex-worker-live"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$-claude-caller"
RUN_DIR="$LIVE_ROOT/$RUN_ID"
REPO="$RUN_DIR/disposable-repo"
CLAUDE_TRANSCRIPT="$RUN_DIR/claude.stream.jsonl"
CLAUDE_STDERR="$RUN_DIR/claude.stderr"
COMMANDS_JSON="$RUN_DIR/claude-bash-commands.json"
EVIDENCE_JSON="$RUN_DIR/validated-common-evidence.json"
CLAUDE_VERSION="$RUN_DIR/claude-version.txt"
INSTANCE="task8-claude-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
WORKER="claude-caller-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"

mkdir -p "$RUN_DIR" "$REPO"
chmod 700 "$RUN_DIR"
export PATH="$ROOT/bin:$PATH"
export CLAUDE_CODE_SESSION_ID="$INSTANCE"
unset CODEX_WORKER_INSTANCE

cleanup() {
  local cleanup_rc=0
  codex-worker daemon stop >"$RUN_DIR/cleanup-stop.json" \
    2>"$RUN_DIR/cleanup-stop.stderr" || cleanup_rc=$?
  return "$cleanup_rc"
}
trap cleanup EXIT INT TERM

command -v codex-worker >"$RUN_DIR/codex-worker-path.txt"
[[ "$(cat "$RUN_DIR/codex-worker-path.txt")" == "$ROOT/bin/codex-worker" ]]
claude --version >"$CLAUDE_VERSION" 2>"$RUN_DIR/claude-version.stderr"

git -C "$REPO" init -b main >"$RUN_DIR/git-init.stdout" 2>"$RUN_DIR/git-init.stderr"
git -C "$REPO" config user.name "Claude Caller Live Check"
git -C "$REPO" config user.email "claude-caller@example.invalid"
printf '# Disposable Claude caller repository\n' >"$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -m seed >"$RUN_DIR/git-commit.stdout" 2>"$RUN_DIR/git-commit.stderr"

PROMPT=$(printf '%s\n' \
  'Use only the Bash tool. Native Claude Code remains the caller; codex-worker is an opt-in local command.' \
  'Invoke only the PATH spelling `codex-worker`. Do not use an absolute path, python wrapper, --socket, MCP, direct codex, or model/session/turn advanced commands.' \
  "Your current directory is the disposable repository $REPO and the unique worker name is $WORKER." \
  'Run these commands one at a time and read each complete one-object JSON response:' \
  "1. codex-worker start --name $WORKER --prompt 'Reply with exactly CLAUDE-FIRST and no other text.'" \
  "2. codex-worker run --name $WORKER --prompt 'Reply with exactly CLAUDE-FOLLOWUP and no other text.'" \
  "3. codex-worker goal show --name $WORKER" \
  "4. codex-worker history --name $WORKER --tail 2" \
  "5. codex-worker status --name $WORKER" \
  '6. codex-worker daemon stop' \
  'Then report the worker name, session_id, thread_id, first turn_id, model, effort, access, cwd, both complete final messages, goal availability, history count, and durable_state. Do not omit or abbreviate any command output while reasoning.')

(cd "$REPO" && claude -p \
  --safe-mode \
  --strict-mcp-config \
  --mcp-config '{"mcpServers":{}}' \
  --tools Bash \
  --allowedTools Bash \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --verbose \
  "$PROMPT") \
  >"$CLAUDE_TRANSCRIPT" 2>"$CLAUDE_STDERR"

python3 - "$CLAUDE_TRANSCRIPT" "$COMMANDS_JSON" <<'PY'
import json
import sys
from pathlib import Path

transcript = Path(sys.argv[1])
commands_path = Path(sys.argv[2])
commands = []

def visit(value):
    if isinstance(value, dict):
        if value.get("type") == "tool_use" and value.get("name") == "Bash":
            command = value.get("input", {}).get("command")
            if isinstance(command, str):
                commands.append(command)
        for nested in value.values():
            visit(nested)
    elif isinstance(value, list):
        for nested in value:
            visit(nested)

for line in transcript.read_text(encoding="utf-8").splitlines():
    if line.strip():
        visit(json.loads(line))

commands_path.write_text(json.dumps(commands, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

python3 "$ROOT/tests/codex-worker/live_claude_evidence.py" \
  --transcript "$CLAUDE_TRANSCRIPT" \
  --cwd "$REPO" \
  --cli codex-worker \
  --output "$EVIDENCE_JSON"

python3 - "$CLAUDE_TRANSCRIPT" "$COMMANDS_JSON" "$EVIDENCE_JSON" "$CLAUDE_VERSION" "$RUN_DIR" "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

transcript = Path(sys.argv[1])
commands = Path(sys.argv[2])
evidence_path = Path(sys.argv[3])
version_path = Path(sys.argv[4])
run_dir = Path(sys.argv[5])
root = Path(sys.argv[6])
evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
summary = {
    "status": "PASS",
    "scenario": "claude-code-common-caller",
    "claude_version": version_path.read_text(encoding="utf-8").strip(),
    "claude_transcript": str(transcript.relative_to(root)),
    "bash_commands": str(commands.relative_to(root)),
    "validated_evidence": str(evidence_path.relative_to(root)),
    "worker_name": evidence["worker_name"],
    "session_id": evidence["session_id"],
    "thread_id": evidence["thread_id"],
    "turn_id": evidence["turn_id"],
    "model": evidence["model"],
    "effort": evidence["effort"],
    "message_count": evidence["message_count"],
    "durable_state": evidence["durable_state"],
    "native_claude_available": evidence["native_claude_available"],
    "direct_codex_invocation": evidence["direct_codex_invocation"],
    "mcp_invocation": evidence["mcp_invocation"],
}
(run_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
receipts_path = root / ".superdev" / "codex-worker-live" / "receipts.json"
receipts = json.loads(receipts_path.read_text(encoding="utf-8")) if receipts_path.exists() else {}
receipt = {
    "command": "bash tests/codex-worker/live_claude_check.sh",
    "status": "PASS",
    "transcript": str(transcript.relative_to(root)),
    "bash_commands": str(commands.relative_to(root)),
    "validated_evidence": str(evidence_path.relative_to(root)),
    "session_id": evidence["session_id"],
    "thread_id": evidence["thread_id"],
    "turn_id": evidence["turn_id"],
}
receipts["CLAUDE_CODE_CALLER"] = receipt
receipts["AH1"] = receipt
receipts_path.write_text(json.dumps(receipts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
PY

trap - EXIT INT TERM
cleanup
