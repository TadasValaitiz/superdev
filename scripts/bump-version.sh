#!/usr/bin/env bash
#
# bump-version.sh — bump version numbers across all declared files,
# with drift detection and repo-wide audit for missed files.
#
# Usage:
#   bump-version.sh <new-version>   Bump all declared files to new version
#   bump-version.sh --check         Report current versions (detect drift)
#   bump-version.sh --audit         Check + grep repo for old version strings
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$REPO_ROOT/.version-bump.json"

if [[ ! -f "$CONFIG" ]]; then
  echo "error: .version-bump.json not found at $CONFIG" >&2
  exit 1
fi

# --- helpers ---

# Read a dotted field path from a JSON file.
# Handles both simple ("version") and nested ("plugins.0.version") paths.
read_json_field() {
  local file="$1" field="$2"
  # Convert dot-path to jq path: "plugins.0.version" -> .plugins[0].version
  local jq_path
  jq_path=$(echo "$field" | sed -E 's/\.([0-9]+)/[\1]/g' | sed 's/^/./' | sed 's/\.\././g')
  jq -r "$jq_path" "$file"
}

# Write a dotted field path in a JSON file, preserving formatting.
write_json_field() {
  local file="$1" field="$2" value="$3"
  local jq_path
  jq_path=$(echo "$field" | sed -E 's/\.([0-9]+)/[\1]/g' | sed 's/^/./' | sed 's/\.\././g')
  local tmp="${file}.tmp"
  jq "$jq_path = \"$value\"" "$file" > "$tmp" && mv "$tmp" "$file"
}

toml_field() {
  local operation="$1" file="$2" field="$3" value="${4:-}"
  if [[ "$field" != "project.version" ]]; then
    echo "error: unsupported TOML field '$field' in $file" >&2
    return 1
  fi
  # Python 3.9 has no tomllib. Validate the repository-controlled package metadata
  # subset fail-closed: bare tables/keys, scalar values, and single-line scalar arrays.
  # This is deliberately not a general-purpose TOML parser.
  python3 - "$operation" "$file" "$value" <<'PY'
import re
import sys
from pathlib import Path

operation = sys.argv[1]
path = Path(sys.argv[2])
new_value = sys.argv[3]
text = path.read_text(encoding="utf-8")
section = None
matches = []
seen_sections = set()
seen_keys = set()
offset = 0


def invalid(line_number, reason):
    print("error: invalid TOML in %s at line %d: %s" % (path, line_number, reason), file=sys.stderr)
    raise SystemExit(1)


def without_comment(line, line_number):
    quote = None
    escaped = False
    for index, character in enumerate(line):
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif quote == "'":
            if character == quote:
                quote = None
        elif character in ("'", '"'):
            quote = character
        elif character == "#":
            return line[:index].rstrip()
    if quote is not None:
        invalid(line_number, "unterminated string")
    return line.rstrip()


def string_end(value, start, line_number):
    quote = value[start]
    escaped = False
    index = start + 1
    while index < len(value):
        character = value[index]
        if quote == '"' and escaped:
            escaped = False
        elif quote == '"' and character == "\\":
            escaped = True
        elif character == quote:
            return index + 1
        index += 1
    invalid(line_number, "unterminated string")


def validate_scalar(value, line_number):
    value = value.strip()
    if not value:
        invalid(line_number, "missing value")
    if value[0] in ("'", '"'):
        if string_end(value, 0, line_number) != len(value):
            invalid(line_number, "characters after string value")
        return
    if value in ("true", "false"):
        return
    if re.fullmatch(r"[+-]?[0-9](?:_?[0-9])*(?:\.[0-9](?:_?[0-9])*)?", value):
        return
    invalid(line_number, "unsupported or malformed value")


def validate_value(value, line_number):
    value = value.strip()
    if not value:
        invalid(line_number, "missing value")
    if not value.startswith("["):
        validate_scalar(value, line_number)
        return
    if not value.endswith("]"):
        invalid(line_number, "unterminated array")
    inner = value[1:-1].strip()
    if not inner:
        return
    items = []
    start = 0
    index = 0
    while index < len(inner):
        if inner[index] in ("'", '"'):
            index = string_end(inner, index, line_number)
            continue
        if inner[index] in "[]{}":
            invalid(line_number, "nested collections are outside the supported package metadata subset")
        if inner[index] == ",":
            items.append(inner[start:index])
            start = index + 1
        index += 1
    items.append(inner[start:])
    if not items[-1].strip():
        items.pop()
    for item in items:
        validate_scalar(item, line_number)


for line_number, line in enumerate(text.splitlines(keepends=True), 1):
    body = line.rstrip("\r\n")
    logical = without_comment(body, line_number).strip()
    if not logical:
        offset += len(line)
        continue
    header = re.fullmatch(r"\[([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\]", logical)
    if header:
        section = header.group(1)
        if section in seen_sections:
            invalid(line_number, "duplicate table [%s]" % section)
        seen_sections.add(section)
        offset += len(line)
        continue
    assignment = re.fullmatch(
        r"([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)[ \t]*=[ \t]*(.+)", logical
    )
    if not assignment:
        invalid(line_number, "expected a complete table header or key/value assignment")
    key = assignment.group(1)
    validate_value(assignment.group(2), line_number)
    identity = (section, key)
    if identity in seen_keys and identity != ("project", "version"):
        invalid(line_number, "duplicate key %s" % key)
    seen_keys.add(identity)
    if identity == ("project", "version"):
        exact = re.fullmatch(
            r'([ \t]*version[ \t]*=[ \t]*")([^"\r\n]+)("[ \t]*(?:#.*)?)', body
        )
        if not exact:
            invalid(line_number, "project.version must be one exact double-quoted assignment")
        matches.append((offset + exact.start(2), offset + exact.end(2), exact.group(2)))
    offset += len(line)

if len(matches) != 1:
    print("error: expected exactly one project.version in %s; found %d" % (path, len(matches)), file=sys.stderr)
    raise SystemExit(1)
start, end, current_value = matches[0]
if operation == "read":
    print(current_value)
elif operation == "write":
    updated = text[:start] + new_value + text[end:]
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        handle.write(updated)
    temporary.replace(path)
else:
    print("error: unsupported TOML operation '%s'" % operation, file=sys.stderr)
    raise SystemExit(1)
PY
}

read_toml_field() {
  toml_field read "$1" "$2"
}

write_toml_field() {
  toml_field write "$1" "$2" "$3"
}

read_field() {
  local file="$1" field="$2" format="${3:-json}"
  case "$format" in
    json) read_json_field "$file" "$field" ;;
    toml) read_toml_field "$file" "$field" ;;
    *) echo "error: unsupported format '$format' for $file" >&2; return 1 ;;
  esac
}

write_field() {
  local file="$1" field="$2" value="$3" format="${4:-json}"
  case "$format" in
    json) write_json_field "$file" "$field" "$value" ;;
    toml) write_toml_field "$file" "$field" "$value" ;;
    *) echo "error: unsupported format '$format' for $file" >&2; return 1 ;;
  esac
}

# Read the list of declared files from config.
# Outputs lines of "path<TAB>field<TAB>format". Format defaults to JSON.
declared_files() {
  jq -r '.files[] | [.path, .field, (.format // "json")] | @tsv' "$CONFIG"
}

# Read the audit exclude patterns from config.
audit_excludes() {
  jq -r '.audit.exclude[]' "$CONFIG" 2>/dev/null
}

# --- commands ---

cmd_check() {
  local has_drift=0
  local versions=()

  echo "Version check:"
  echo ""

  while IFS=$'\t' read -r path field format; do
    local fullpath="$REPO_ROOT/$path"
    if [[ ! -f "$fullpath" ]]; then
      printf "  %-45s  MISSING\n" "$path ($field)"
      has_drift=1
      continue
    fi
    local ver
    ver=$(read_field "$fullpath" "$field" "$format")
    printf "  %-45s  %s\n" "$path ($field)" "$ver"
    versions+=("$ver")
  done < <(declared_files)

  echo ""

  # Check if all versions match
  local unique
  unique=$(printf '%s\n' "${versions[@]}" | sort -u | wc -l | tr -d ' ')
  if [[ "$unique" -gt 1 ]]; then
    echo "DRIFT DETECTED — versions are not in sync:"
    printf '%s\n' "${versions[@]}" | sort | uniq -c | sort -rn | while read -r count ver; do
      echo "  $ver ($count files)"
    done
    has_drift=1
  else
    echo "All declared files are in sync at ${versions[0]}"
  fi

  return $has_drift
}

cmd_audit() {
  # First run check
  cmd_check || true
  echo ""

  # Determine the current version (most common across declared files)
  local current_version
  current_version=$(
    while IFS=$'\t' read -r path field format; do
      local fullpath="$REPO_ROOT/$path"
      [[ -f "$fullpath" ]] && read_field "$fullpath" "$field" "$format"
    done < <(declared_files) | sort | uniq -c | sort -rn | head -1 | awk '{print $2}'
  )

  if [[ -z "$current_version" ]]; then
    echo "error: could not determine current version" >&2
    return 1
  fi

  echo "Audit: scanning repo for version string '$current_version'..."
  echo ""

  # Build grep exclude args
  local -a exclude_args=()
  while IFS= read -r pattern; do
    exclude_args+=("--exclude=$pattern" "--exclude-dir=$pattern")
  done < <(audit_excludes)

  # Also always exclude binary files and .git
  exclude_args+=("--exclude-dir=.git" "--exclude-dir=node_modules" "--binary-files=without-match")

  # Get list of declared paths for comparison
  local -a declared_paths=()
  while IFS=$'\t' read -r path _field _format; do
    declared_paths+=("$path")
  done < <(declared_files)

  # Grep for the version string
  local found_undeclared=0
  while IFS= read -r match; do
    local match_file
    match_file=$(echo "$match" | cut -d: -f1)
    # Make path relative to repo root
    local rel_path="${match_file#$REPO_ROOT/}"

    # Check if this file is in the declared list
    local is_declared=0
    for dp in "${declared_paths[@]}"; do
      if [[ "$rel_path" == "$dp" ]]; then
        is_declared=1
        break
      fi
    done

    if [[ "$is_declared" -eq 0 ]]; then
      if [[ "$found_undeclared" -eq 0 ]]; then
        echo "UNDECLARED files containing '$current_version':"
        found_undeclared=1
      fi
      echo "  $match"
    fi
  done < <(grep -rn "${exclude_args[@]}" -F "$current_version" "$REPO_ROOT" 2>/dev/null || true)

  if [[ "$found_undeclared" -eq 0 ]]; then
    echo "No undeclared files contain the version string. All clear."
  else
    echo ""
    echo "Review the above files — if they should be bumped, add them to .version-bump.json"
    echo "If they should be skipped, add them to the audit.exclude list."
  fi
}

cmd_bump() {
  local new_version="$1"

  # Validate semver-ish format
  if ! echo "$new_version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "error: '$new_version' doesn't look like a version (expected X.Y.Z)" >&2
    exit 1
  fi

  echo "Bumping all declared files to $new_version..."
  echo ""

  local -a paths=() fields=() formats=() old_versions=()
  local count=0
  while IFS=$'\t' read -r path field format; do
    local fullpath="$REPO_ROOT/$path"
    if [[ ! -f "$fullpath" ]]; then
      echo "error: declared version file is missing: $path" >&2
      return 1
    fi
    local old_ver
    old_ver=$(read_field "$fullpath" "$field" "$format")
    paths[$count]="$path"
    fields[$count]="$field"
    formats[$count]="$format"
    old_versions[$count]="$old_ver"
    count=$((count + 1))
  done < <(declared_files)

  if [[ "$count" -eq 0 ]]; then
    echo "error: no declared version files found" >&2
    return 1
  fi

  local stage_dir
  stage_dir=$(mktemp -d "$REPO_ROOT/.version-bump.XXXXXX")
  local i
  for ((i = 0; i < count; i++)); do
    local staged="$stage_dir/staged-$i"
    local backup="$stage_dir/backup-$i"
    cp -p "$REPO_ROOT/${paths[$i]}" "$staged"
    cp -p "$REPO_ROOT/${paths[$i]}" "$backup"
    if ! write_field "$staged" "${fields[$i]}" "$new_version" "${formats[$i]}"; then
      find "$stage_dir" -depth -delete
      return 1
    fi
  done

  local committed=0
  for ((i = 0; i < count; i++)); do
    if ! mv -f "$stage_dir/staged-$i" "$REPO_ROOT/${paths[$i]}"; then
      local rollback
      for ((rollback = 0; rollback < committed; rollback++)); do
        cp -p "$stage_dir/backup-$rollback" "$REPO_ROOT/${paths[$rollback]}" || true
      done
      echo "error: version update failed; restored previously written declarations" >&2
      find "$stage_dir" -depth -delete
      return 1
    fi
    committed=$((committed + 1))
  done

  for ((i = 0; i < count; i++)); do
    printf "  %-45s  %s -> %s\n" \
      "${paths[$i]} (${fields[$i]})" "${old_versions[$i]}" "$new_version"
  done
  find "$stage_dir" -depth -delete

  echo ""
  echo "Done. Running audit to check for missed files..."
  echo ""
  cmd_audit
}

# --- main ---

case "${1:-}" in
  --check)
    cmd_check
    ;;
  --audit)
    cmd_audit
    ;;
  --help|-h|"")
    echo "Usage: bump-version.sh <new-version> | --check | --audit"
    echo ""
    echo "  <new-version>  Bump all declared files to the given version"
    echo "  --check        Show current versions, detect drift"
    echo "  --audit        Check + scan repo for undeclared version references"
    exit 0
    ;;
  --*)
    echo "error: unknown flag '$1'" >&2
    exit 1
    ;;
  *)
    cmd_bump "$1"
    ;;
esac
