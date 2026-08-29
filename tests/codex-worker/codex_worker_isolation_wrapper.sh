#!/bin/sh
set -eu

: "${CODEX_WORKER_UV_EXECUTABLE:?missing isolated UV executable}"
: "${CODEX_WORKER_ISOLATED_HOME:?missing isolated HOME}"
: "${CODEX_WORKER_ISOLATED_STATE:?missing isolated state root}"
: "${CODEX_WORKER_ISOLATED_RUNTIME:?missing isolated runtime root}"
: "${CODEX_WORKER_CLAUDE_CONFIG_ROOT:?missing Claude callback config root}"

for path in "$CODEX_WORKER_UV_EXECUTABLE" "$CODEX_WORKER_ISOLATED_HOME" \
  "$CODEX_WORKER_ISOLATED_STATE" "$CODEX_WORKER_ISOLATED_RUNTIME" \
  "$CODEX_WORKER_CLAUDE_CONFIG_ROOT"; do
  case "$path" in
    /*) ;;
    *) echo "codex-worker isolation path is not absolute" >&2; exit 64 ;;
  esac
done
test -x "$CODEX_WORKER_UV_EXECUTABLE"

export HOME="$CODEX_WORKER_ISOLATED_HOME"
export XDG_STATE_HOME="$CODEX_WORKER_ISOLATED_STATE"
export TMPDIR="$CODEX_WORKER_ISOLATED_RUNTIME"
export CLAUDE_CONFIG_DIR="$CODEX_WORKER_CLAUDE_CONFIG_ROOT"
exec "$CODEX_WORKER_UV_EXECUTABLE" "$@"
