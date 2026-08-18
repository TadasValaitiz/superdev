#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd -P)
CLI="$ROOT/skills/subagent-driven-development/scripts/codex-worker"
LIVE_ROOT="$ROOT/.superdev/codex-worker-live"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$-claude-caller"
RUN_DIR="$LIVE_ROOT/$RUN_ID"
SOCKET_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/cw-claude.XXXXXX")
SOCKET="$SOCKET_ROOT/worker.sock"
STATE="$RUN_DIR/sessions.json"
REPO="$RUN_DIR/disposable-repo"
DAEMON_STDERR="$RUN_DIR/daemon.stderr"
CLAUDE_TRANSCRIPT="$RUN_DIR/claude.stream.jsonl"
CLAUDE_STDERR="$RUN_DIR/claude.stderr"
COMMANDS_JSON="$RUN_DIR/claude-bash-commands.json"
EVIDENCE_JSON="$RUN_DIR/validated-broker-evidence.json"
DAEMON_PID=""

mkdir -p "$RUN_DIR" "$REPO"
chmod 700 "$RUN_DIR" "$SOCKET_ROOT"

cleanup() {
  local cleanup_rc=0
  if [[ -n "$DAEMON_PID" ]] && kill -0 "$DAEMON_PID" 2>/dev/null; then
    python3 "$CLI" --socket "$SOCKET" daemon shutdown \
      >"$RUN_DIR/shutdown.json" 2>"$RUN_DIR/shutdown.stderr" || cleanup_rc=$?
    wait "$DAEMON_PID" || cleanup_rc=$?
  fi
  case "$SOCKET_ROOT" in
    "${TMPDIR:-/tmp}"/cw-claude.*)
      rm -f "$SOCKET_ROOT/worker.sock" "$SOCKET_ROOT/worker.sock.lock"
      rmdir "$SOCKET_ROOT" 2>/dev/null || true
      ;;
    *)
      printf 'refusing to clean unexpected socket root: %s\n' "$SOCKET_ROOT" >&2
      cleanup_rc=1
      ;;
  esac
  return "$cleanup_rc"
}
trap cleanup EXIT INT TERM

git -C "$REPO" init -b main >"$RUN_DIR/git-init.stdout" 2>"$RUN_DIR/git-init.stderr"
git -C "$REPO" config user.name "Claude Caller Live Check"
git -C "$REPO" config user.email "claude-caller@example.invalid"
printf '# Disposable Claude caller repository\n' >"$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -m seed >"$RUN_DIR/git-commit.stdout" 2>"$RUN_DIR/git-commit.stderr"

set +e
python3 "$CLI" --socket "$SOCKET" daemon status \
  >"$RUN_DIR/daemon-absent.json" 2>"$RUN_DIR/daemon-absent.stderr"
absent_rc=$?
set -e
[[ "$absent_rc" == 1 ]]
python3 - "$RUN_DIR/daemon-absent.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["error"]["data"]["kind"] == "daemon_unavailable"
assert isinstance(payload["error"]["data"]["recovery"], str)
PY

python3 "$CLI" --socket "$SOCKET" daemon serve --state "$STATE" --event-limit 40 \
  >"$RUN_DIR/daemon.stdout" 2>"$DAEMON_STDERR" &
DAEMON_PID=$!

ready=0
for _attempt in $(seq 1 100); do
  if ! kill -0 "$DAEMON_PID" 2>/dev/null; then
    break
  fi
  if python3 "$CLI" --socket "$SOCKET" daemon status >"$RUN_DIR/daemon-status.json" 2>/dev/null; then
    ready=1
    break
  fi
  sleep 0.1
done
if [[ "$ready" != 1 ]]; then
  printf 'daemon did not become ready\n' >&2
  exit 1
fi

PROMPT=$(printf '%s\n' \
  'Use only the Bash tool. You are the caller validating a documented local CLI; do not create or edit files yourself.' \
  "The codex-worker executable is: $CLI" \
  "Every command must put these global arguments before the family: python3 $CLI --socket $SOCKET" \
  "The disposable worker cwd is: $REPO" \
  'Perform these steps through codex-worker, preserving every returned identifier:' \
  '1. Run model list. Choose one returned model ID and one effort explicitly supported by that model.' \
  '2. Run session start with the absolute cwd above, name claude-caller, and the chosen model.' \
  '3. Run turn start by returned --session UUID, chosen model/effort, and an inline prompt requiring Codex to create from-claude.txt as exactly 28 UTF-8 bytes with hex `63726561746564207468726f75676820436c6175646520436f64650a`; explicitly say the final byte must be LF (0a), must not be trimmed, and must be verified before finishing.' \
  '4. Run turn wait for that UUID with --timeout 900. The wait command selects by --session; it does not accept --turn.' \
  '5. Run turn events for that UUID with --after 0 --limit 100. The events command selects by --session; it does not accept --turn.' \
  '6. Report the session_id, thread_id, turn_id, model, effort, terminal status, and event count.' \
  'Do not bypass the broker, do not invoke codex directly, and do not return until all five command families succeeded.')

claude -p \
  --safe-mode \
  --strict-mcp-config \
  --mcp-config '{"mcpServers":{}}' \
  --tools Bash \
  --allowedTools Bash \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --verbose \
  "$PROMPT" \
  >"$CLAUDE_TRANSCRIPT" 2>"$CLAUDE_STDERR"

python3 - "$CLAUDE_TRANSCRIPT" "$COMMANDS_JSON" "$CLI" <<'PY'
import json
import sys
from pathlib import Path

transcript = Path(sys.argv[1])
commands_path = Path(sys.argv[2])
cli = sys.argv[3]
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
joined = "\n".join(commands)
assert cli in joined, joined
for fragment in ("model list", "session start", "turn start", "turn wait", "turn events"):
    assert fragment in joined, "Claude did not invoke %s; commands=%r" % (fragment, commands)
assert "codex app-server" not in joined
PY

python3 "$CLI" --socket "$SOCKET" daemon shutdown \
  >"$RUN_DIR/shutdown.json" 2>"$RUN_DIR/shutdown.stderr"
python3 - "$RUN_DIR/shutdown.json" "$STATE" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["result"] == {"accepted": True}
assert Path(sys.argv[2]).is_file()
PY
wait "$DAEMON_PID"
DAEMON_PID=""

python3 "$ROOT/tests/codex-worker/live_claude_evidence.py" \
  --transcript "$CLAUDE_TRANSCRIPT" \
  --state "$STATE" \
  --cwd "$REPO" \
  --cli "$CLI" \
  --output "$EVIDENCE_JSON"

python3 - "$REPO/from-claude.txt" "$CLAUDE_TRANSCRIPT" "$COMMANDS_JSON" "$EVIDENCE_JSON" "$RUN_DIR" "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
transcript = Path(sys.argv[2])
commands = Path(sys.argv[3])
evidence_path = Path(sys.argv[4])
run_dir = Path(sys.argv[5])
root = Path(sys.argv[6])
assert output.read_text(encoding="utf-8") == "created through Claude Code\n"
evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
summary = {
    "status": "PASS",
    "scenario": "claude-code-caller",
    "output": output.read_text(encoding="utf-8"),
    "claude_transcript": str(transcript.relative_to(root)),
    "bash_commands": str(commands.relative_to(root)),
    "validated_evidence": str(evidence_path.relative_to(root)),
    "session_id": evidence["session_id"],
    "thread_id": evidence["thread_id"],
    "turn_id": evidence["turn_id"],
    "model": evidence["model"],
    "effort": evidence["effort"],
    "event_count": evidence["event_count"],
    "registry_session_persisted": evidence["registry_session_persisted"],
}
(run_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
receipts_path = root / ".superdev" / "codex-worker-live" / "receipts.json"
receipts = json.loads(receipts_path.read_text(encoding="utf-8")) if receipts_path.exists() else {}
receipts["CLAUDE_CODE_CALLER"] = {
    "command": "bash tests/codex-worker/live_claude_check.sh",
    "status": "PASS",
    "transcript": str(transcript.relative_to(root)),
    "bash_commands": str(commands.relative_to(root)),
    "validated_evidence": str(evidence_path.relative_to(root)),
    "session_id": evidence["session_id"],
    "thread_id": evidence["thread_id"],
    "turn_id": evidence["turn_id"],
}
receipts["AH1"] = {
    "command": "bash tests/codex-worker/live_claude_check.sh",
    "status": "PASS",
    "transcript": str(transcript.relative_to(root)),
    "bash_commands": str(commands.relative_to(root)),
    "validated_evidence": str(evidence_path.relative_to(root)),
    "session_id": evidence["session_id"],
    "thread_id": evidence["thread_id"],
    "turn_id": evidence["turn_id"],
}
receipts_path.write_text(json.dumps(receipts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
PY
