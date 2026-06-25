#!/usr/bin/env bash
# PDPA Hook A — data-handler-scan
#
# PreToolUse on Write|Edit. Scans payload for PII patterns. Blocks (exit 2)
# on match unless the target path matches a glob in
# .claude/config/pdpa-allowlist.yaml.
#
# Input: Claude Code passes a JSON payload on stdin with the tool call.
# Exit code 0 = allow, 2 = block.
#
# Graceful degradation: missing jq → exit 0 + stderr warning.

set -u

# Resolve project root (walk up looking for .sn-init or CLAUDE.md).
root="$PWD"
while [ "$root" != "/" ] && [ ! -d "$root/.sn-init" ] && [ ! -f "$root/CLAUDE.md" ]; do
    root="$(dirname "$root")"
done

# Without jq we can't parse the payload — allow with a notice (matches
# rate-limit.sh pattern).
if ! command -v jq >/dev/null 2>&1; then
    echo "pdpa-data-handler-scan: jq not installed; skipping scan" >&2
    exit 0
fi

payload="$(cat 2>/dev/null || true)"
target="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)"
content="$(printf '%s' "$payload" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)"

# Compute relative path for allowlist matching + error reporting.
relative="${target#$root/}"

# Check allowlist.
allowlist_file="$root/.claude/config/pdpa-allowlist.yaml"
if [ -f "$allowlist_file" ] && [ -n "$relative" ]; then
    # Extract glob lines (under `allowlist:` block); strip indent + dashes + quotes.
    globs="$(awk '/^allowlist:/{flag=1;next} /^[^[:space:]-]/{flag=0} flag && /^[[:space:]]*-/{sub(/^[[:space:]]*-[[:space:]]*/,""); gsub(/^["'"'"']|["'"'"']$/,""); print}' "$allowlist_file")"
    while IFS= read -r pat; do
        [ -z "$pat" ] && continue
        case "$relative" in
            $pat) exit 0 ;;
        esac
    done <<< "$globs"
fi

# Patterns (regex, name).
patterns_and_names=(
  '\b[0-9]{13}\b|Thai NI 13-digit'
  '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b|email address'
  '\b(0|66)[6-9][0-9]{8}\b|Thai mobile'
  '\b(0|66)[2-7][0-9]{7}\b|Thai landline'
  '\b(?:[0-9]{4}[ -]?){3,4}[0-9]{1,4}\b|credit card PAN'
  '\b[A-Z]{1,2}[0-9]{6,9}\b|passport'
)

for entry in "${patterns_and_names[@]}"; do
    regex="${entry%|*}"
    name="${entry##*|}"
    if printf '%s' "$content" | grep -E -q -- "$regex"; then
        cat >&2 <<EOF
PDPA: 'data-handler-scan' detected a PII pattern in ${relative:-<unknown path>}.
Pattern: $name.
If this is intentional (test fixture, anonymized example), allowlist the path:
  sn-setup policy pdpa allowlist add "<suggested glob>"
Then re-run the tool call.
Background: .claude/docs/policies/pdpa-compliance.md.
EOF
        exit 2
    fi
done

exit 0
