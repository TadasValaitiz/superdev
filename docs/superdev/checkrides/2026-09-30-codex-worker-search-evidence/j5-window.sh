#!/bin/bash
# J5 (HUMAN ruling D368; evaluator GO with amendments): the supervised global install window.
#   quiet wait -> W1 -> W2 -> W3 install -> W4 two-read gate + restart -> W5 post-reads.
# Real global environment. Never `daemon stop`, never --force, never kill.
# Deadlines keep the whole run under ~105 min so no outer timeout can cut a restart mid-way.
set -u
E=/Users/tadas/Projects/superdev/.claude/worktrees/codex-worker-search/docs/superdev/checkrides/2026-09-30-codex-worker-search-evidence
R=/Users/tadas/Projects/superdev/.claude/worktrees/codex-worker-search
CW=/Users/tadas/.local/bin/codex-worker
RT=/var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/scw-501-global
LOG=$E/j5-window.log
QUIET_MAX=${QUIET_MAX:-4800}   # 80 min to find a quiet window before installing
RESTART_MAX=${RESTART_MAX:-1200}  # 20 min after the install to get a restart through

log(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
cap(){ local id=$1; shift; "$@" > "$E/j5-$id.stdout" 2> "$E/j5-$id.stderr"; echo $? > "$E/j5-$id.exit"; }
# "<active> <version> <pid> <status> <active-names|-> <all-names-sorted>"
summ(){ /usr/bin/python3 - "$E/j5-$1.stdout" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))["result"]
    w = d["worker_count"]["basis"]
    names = ",".join(sorted(w["active_names"] + w["idle_names"]))
    print(d["active_turn_count"]["value"], d["service_version"], d["pid"], d["status"],
          ",".join(w["active_names"]) or "-", names or "-")
except Exception as e:
    print("ERR", type(e).__name__, str(e).replace(" ", "_"), "-", "-", "-")
PY
}

# Environment assertion (evaluator amendment 1): never mutate, refuse to run if wrong.
if [ "${HOME:-}" != /Users/tadas ] || [ "${TMPDIR:-}" != /var/folders/mg/j_vvh_2x33g9hxtv1v0rs1400000gn/T/ ] \
   || [ -n "${CODEX_WORKER_INSTANCE:-}" ] || [ -n "${XDG_STATE_HOME:-}" ] || case "$PATH" in *cw-iso*) true;; *) false;; esac; then
  log "STOP-ENV HOME=${HOME:-} TMPDIR=${TMPDIR:-}"; echo "STOP-ENV"; exit 2
fi
log "START window pid=$$"

# Quiet wait -> W1 -> W2 (the re-check immediately before the install).
deadline=$(( $(date +%s) + QUIET_MAX )); n=0
while :; do
  while :; do
    n=$((n+1)); touch /private/tmp/cw-ride-5d2b8e
    cap W1 "$CW" daemon status
    read -r act ver pid st an names <<< "$(summ W1)"
    log "W1 poll $n: active=$act version=$ver pid=$pid status=$st active_names=$an"
    [ "$act" = 0 ] && [ "$st" = ready ] && break
    if [ "$(date +%s)" -ge "$deadline" ]; then log "NOTQUIET nothing installed"; echo "NOTQUIET"; exit 10; fi
    sleep 20
  done
  cap W2 "$CW" daemon status
  read -r act ver pid st an names <<< "$(summ W2)"
  log "W2: active=$act version=$ver pid=$pid status=$st active_names=$an"
  [ "$act" = 0 ] && [ "$st" = ready ] && break
  log "W2 not quiet; back to waiting, nothing installed"
done

# W3: the trusted preflight (machine-wide install).
cap W3 "$R/skills/subagent-driven-development/scripts/install-codex-worker"
log "W3 exit=$(cat "$E/j5-W3.exit"): $(tr '\n' ' ' < "$E/j5-W3.stdout")"
if [ "$(cat "$E/j5-W3.exit")" != 0 ]; then log "STOP-W3"; echo "STOP-W3"; exit 20; fi
cap W3v "$CW" --version
cap W3r sh -c "ls -la $CW; readlink $CW"
cap W3i sh -c "head -1 /Users/tadas/.local/share/uv/tools/codex-worker/bin/codex-worker; /Users/tadas/.local/share/uv/tools/codex-worker/bin/python --version"
if [ "$(cat "$E/j5-W3v.stdout")" != "codex-worker 8.6.7" ]; then log "STOP-W3v $(cat "$E/j5-W3v.stdout")"; echo "STOP-W3v"; exit 21; fi

# W4: two reads ~5 s apart (0 active, same names, ready), then a non-forced restart.
deadline=$(( $(date +%s) + RESTART_MAX )); a=0
while :; do
  a=$((a+1))
  cap "W4a${a}x" "$CW" daemon status; s1=$(summ "W4a${a}x"); sleep 5
  cap "W4a${a}y" "$CW" daemon status; s2=$(summ "W4a${a}y")
  read -r act1 ver1 pid1 st1 an1 names1 <<< "$s1"; read -r act2 ver2 pid2 st2 an2 names2 <<< "$s2"
  log "W4a attempt $a: [$act1 $ver1 $pid1 $st1 $an1] [$act2 $ver2 $pid2 $st2 $an2] names_equal=$([ "$names1" = "$names2" ] && echo yes || echo no)"
  if [ "$act1" = 0 ] && [ "$act2" = 0 ] && [ "$names1" = "$names2" ] && [ "$st2" = ready ]; then
    cap "W4b${a}" "$CW" daemon restart
    rc=$(cat "$E/j5-W4b${a}.exit")
    log "W4b attempt $a exit=$rc: $(head -c 400 "$E/j5-W4b${a}.stdout")"
    if [ "$rc" = 0 ] && grep -q '"status":"completed"' "$E/j5-W4b${a}.stdout"; then break; fi
    if ! grep -q '"kind":"service_busy"' "$E/j5-W4b${a}.stdout"; then log "STOP-W4b"; echo "STOP-W4b"; exit 30; fi
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then log "INSTALLED-NOT-RESTARTED"; echo "INSTALLED-NOT-RESTARTED"; exit 31; fi
  sleep 10
done

# W5: post-reads (a 3 s settle for the code-mode-host's stdio EOF), all read-only.
sleep 3
cap W5e1 sh -c "ps -axo pid,ppid,pgid,lstart,command | grep -i '[c]odex'"
cap W5e2 ls -lai /private/tmp/codex-daemon-501/
cap W5e3 sh -c "ls -lai $RT/; readlink $RT/c"
cap W5e4 lsof -nP -iTCP:4500 -sTCP:LISTEN
cap W5e5 "$CW" daemon status
cap W5e6 "$CW" status --name research-5d2b8e
log "DONE restart_attempt=$a"
echo "DONE restart_attempt=$a"
