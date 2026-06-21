#!/usr/bin/env bash
# PreToolUse chokepoint gate — blocks Edit/Write tool calls that target a path
# listed in .harness/chokepoints.yaml.
#
# Input: Claude Code passes a JSON payload on stdin with the tool call.
# Exit code 0 = allow, 2 = block.

set -u

root="$PWD"
while [ "$root" != "/" ] && [ ! -d "$root/.sn-init" ] && [ ! -f "$root/CLAUDE.md" ]; do
    root="$(dirname "$root")"
done
chokes="$root/.harness/chokepoints.yaml"
[ -f "$chokes" ] || exit 0

# Pull the target file path from the tool input.
payload="$(cat 2>/dev/null || true)"
target=""
if command -v jq >/dev/null 2>&1; then
    target="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)"
fi
[ -z "$target" ] && exit 0

# Pull chokepoint patterns out of the YAML (lines under `chokepoints:` indented `- ...`).
patterns="$(awk '/^chokepoints:/{flag=1;next} /^[^[:space:]-]/{flag=0} flag && /^-/{sub(/^- */,""); print}' "$chokes")"
[ -z "$patterns" ] && exit 0

# Compare via shell glob match.
relative="${target#$root/}"
while IFS= read -r pat; do
    [ -z "$pat" ] && continue
    case "$relative" in
        $pat) echo "chokepoint-gate: '$relative' matches '$pat' — human approval required." >&2
              exit 2 ;;
    esac
done <<< "$patterns"
exit 0
