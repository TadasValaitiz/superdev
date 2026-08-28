#!/bin/sh
# marker-census.sh — doc-marker census over a corpus directory (D53/D70).
# Counts the THREE positional forms, per status, per file; never hand-edited output.
#   marker-census.sh <dir>                 counts per status per file + totals
#   marker-census.sh <dir> --since <ref>   totals now vs at <ref> (git), with delta
#   marker-census.sh --selftest            run against bundled fixtures; exit 1 on mismatch
set -eu

WORDS='LOCKED|FLEXIBLE|DEFERRED|BLIND|MISMATCH|SEED-ILLUSTRATIVE|SUPERSEDED'
# Form 1: claim marker  — line-initial (optionally blockquoted/listed) **WORD ...:** or **WORD:**
# Form 2: section status — line-initial **Status:** WORD
# Form 3: heading marker — line-initial #... WORD<space>—
RE_CLAIM="^[[:space:]]*(>[[:space:]]*)*(-[[:space:]]+)?\*\*($WORDS)( \([^)]*\))?:\*\*"
RE_STATUS="^[[:space:]]*(>[[:space:]]*)*\*\*Status:\*\*[[:space:]]*($WORDS)"
RE_HEAD="^#{1,6}[[:space:]]+($WORDS)[[:space:]]+—"

count_file() { # $1=file → lines "STATUS<tab>form"
  grep -oE "$RE_CLAIM"  "$1" 2>/dev/null | grep -oE "$WORDS" | sed 's/$/\tclaim/'   || true
  grep -oE "$RE_STATUS" "$1" 2>/dev/null | grep -oE "($WORDS)$" | sed 's/$/\tstatus/' || true
  grep -oE "$RE_HEAD"   "$1" 2>/dev/null | grep -oE "$WORDS" | sed 's/$/\theading/' || true
}

census_dir() { # $1=dir → per-file lines "file<tab>STATUS<tab>form"
  find "$1" -name '*.md' -type f | sort | while IFS= read -r f; do
    count_file "$f" | sed "s|^|$f\t|"
  done
}

case "${1:-}" in
  --selftest)
    DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)/fixtures
    GOT=$(census_dir "$DIR" | awk -F'\t' '{print $3}' | sort | uniq -c | awk '{print $2"="$1}' | tr '\n' ' ')
    WANT="claim=3 heading=2 status=1 "
    if [ "$GOT" = "$WANT" ]; then echo "selftest OK: $GOT"; exit 0
    else echo "selftest FAIL: got '$GOT' want '$WANT'"; census_dir "$DIR"; exit 1; fi ;;
  "") echo "usage: marker-census.sh <dir> [--since <ref>] | --selftest" >&2; exit 2 ;;
esac

DIR=$1; shift
if [ "${1:-}" = "--since" ]; then
  REF=$2
  NOW=$(census_dir "$DIR" | awk -F'\t' '{print $2}' | sort | uniq -c | awk '{printf "%s %s\n",$2,$1}')
  THEN=$(git -C "$(git -C "$DIR" rev-parse --show-toplevel)" show "$REF" --stat >/dev/null 2>&1 && \
    git -C "$DIR" ls-tree -r --name-only "$REF" -- . | grep '\.md$' | while IFS= read -r f; do
      git -C "$DIR" show "$REF:./$f" 2>/dev/null > /tmp/mc.$$ || continue
      count_file /tmp/mc.$$
    done | awk -F'\t' '{print $1}' | sort | uniq -c | awk '{printf "%s %s\n",$2,$1}'; rm -f /tmp/mc.$$) || true
  echo "== now =="; echo "$NOW"; echo "== at $REF =="; echo "${THEN:-<none>}"
else
  echo "== per file =="
  census_dir "$DIR" | awk -F'\t' '{print $1" "$2}' | sort | uniq -c | sort -k2
  echo "== totals per status =="
  census_dir "$DIR" | awk -F'\t' '{print $2}' | sort | uniq -c | sort -rn
fi
