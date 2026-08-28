#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FIXTURE="$(mktemp -d)"
trap 'rm -rf "$FIXTURE"' EXIT

mkdir -p "$FIXTURE/scripts" "$FIXTURE/package"
cp "$ROOT/scripts/bump-version.sh" "$FIXTURE/scripts/bump-version.sh"
chmod +x "$FIXTURE/scripts/bump-version.sh"

cat > "$FIXTURE/.version-bump.json" <<'JSON'
{
  "files": [
    {"path": "package.json", "field": "version"},
    {"path": "package/pyproject.toml", "field": "project.version", "format": "toml"}
  ],
  "audit": {"exclude": []}
}
JSON
cat > "$FIXTURE/package.json" <<'JSON'
{
  "version": "1.2.3",
  "untouched": "keep"
}
JSON
cat > "$FIXTURE/package/pyproject.toml" <<'TOML'
[build-system]
requires = ["hatchling>=1.27,<2"]

[project]
name = "codex-worker"
version = "1.2.3"
description = "leave 1.2.3 here unchanged"

[tool.example]
version = "also-unchanged"
TOML
cp "$FIXTURE/package/pyproject.toml" "$FIXTURE/package/pyproject.original"

"$FIXTURE/scripts/bump-version.sh" --check >/dev/null
"$FIXTURE/scripts/bump-version.sh" 2.0.0 >/dev/null

jq -e '.version == "2.0.0" and .untouched == "keep"' "$FIXTURE/package.json" >/dev/null
grep -Fx 'version = "2.0.0"' "$FIXTURE/package/pyproject.toml" >/dev/null
grep -Fx 'description = "leave 1.2.3 here unchanged"' "$FIXTURE/package/pyproject.toml" >/dev/null
grep -Fx 'version = "also-unchanged"' "$FIXTURE/package/pyproject.toml" >/dev/null
sed 's/version = "2.0.0"/version = "1.2.3"/' "$FIXTURE/package/pyproject.toml" \
  | cmp - "$FIXTURE/package/pyproject.original" >/dev/null
"$FIXTURE/scripts/bump-version.sh" --check >/dev/null

cp "$FIXTURE/package/pyproject.toml" "$FIXTURE/package/pyproject.before"
sed -i.bak '/version = "2.0.0"/d' "$FIXTURE/package/pyproject.toml"
cp "$FIXTURE/package/pyproject.toml" "$FIXTURE/package/zero.before"
if "$FIXTURE/scripts/bump-version.sh" 3.0.0 >"$FIXTURE/zero.out" 2>"$FIXTURE/zero.err"; then
  echo "expected missing TOML project.version to fail" >&2
  exit 1
fi
grep -F 'expected exactly one project.version' "$FIXTURE/zero.err" >/dev/null
cmp "$FIXTURE/package/zero.before" "$FIXTURE/package/pyproject.toml" >/dev/null
mv "$FIXTURE/package/pyproject.before" "$FIXTURE/package/pyproject.toml"

sed -i.bak '/version = "2.0.0"/a\
version = "duplicate"' "$FIXTURE/package/pyproject.toml"
cp "$FIXTURE/package/pyproject.toml" "$FIXTURE/package/multiple.before"
if "$FIXTURE/scripts/bump-version.sh" 3.0.0 >"$FIXTURE/multiple.out" 2>"$FIXTURE/multiple.err"; then
  echo "expected duplicate TOML project.version to fail" >&2
  exit 1
fi
grep -F 'expected exactly one project.version' "$FIXTURE/multiple.err" >/dev/null
cmp "$FIXTURE/package/multiple.before" "$FIXTURE/package/pyproject.toml" >/dev/null

echo "bump-version TOML fixture: PASS"
