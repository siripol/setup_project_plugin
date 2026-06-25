#!/usr/bin/env bash
# PDPA Hook B — retention-check
#
# PreToolUse on Write to anything under data/. Verifies sidecar
# <file>.meta.yaml exists with 6 required keys.
#
# Input: Claude Code passes a JSON payload on stdin with the tool call.
# Exit code 0 = allow, 2 = block.
#
# Graceful degradation: missing jq → exit 0 + stderr warning.

set -u

root="$PWD"
while [ "$root" != "/" ] && [ ! -d "$root/.sn-init" ] && [ ! -f "$root/CLAUDE.md" ]; do
    root="$(dirname "$root")"
done

if ! command -v jq >/dev/null 2>&1; then
    echo "pdpa-retention-check: jq not installed; skipping check" >&2
    exit 0
fi

payload="$(cat 2>/dev/null || true)"
target="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)"
relative="${target#$root/}"

# Skip rules.
basename="${target##*/}"
case "$basename" in
    .gitkeep|README.md) exit 0 ;;
esac
case "$target" in
    *.meta.yaml) exit 0 ;;
esac
case "$relative" in
    data/*) ;;
    *) exit 0 ;;  # not under data/, hook shouldn't have fired; defensive.
esac

sidecar="${target}.meta.yaml"
if [ ! -f "$sidecar" ]; then
    cat >&2 <<EOF
PDPA: 'retention-check' requires a sidecar for ${relative}.
Missing sidecar: ${relative}.meta.yaml.
Create it with the keys: retention_days, data_subject, lawful_basis,
data_categories, controller, last_reviewed.
Template: docs/compliance/retention-policy-template.md.
EOF
    exit 2
fi

# Check required keys.
errors=""
for key in retention_days data_subject lawful_basis data_categories controller last_reviewed; do
    if ! grep -E -q "^[[:space:]]*${key}[[:space:]]*:" "$sidecar"; then
        errors+=$'\n- '"$key"': missing'
    fi
done

# Validate retention_days is integer ≥ 1.
rd="$(awk '/^[[:space:]]*retention_days[[:space:]]*:/ {sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$sidecar")"
if [ -n "$rd" ] && ! [[ "$rd" =~ ^[0-9]+$ ]]; then
    errors+=$'\n- retention_days: invalid (must be integer)'
elif [ -n "$rd" ] && [ "$rd" -lt 1 ]; then
    errors+=$'\n- retention_days: invalid (must be ≥ 1)'
fi

# Validate lawful_basis is in the allowed set.
lb="$(awk '/^[[:space:]]*lawful_basis[[:space:]]*:/ {sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$sidecar")"
if [ -n "$lb" ]; then
    case "$lb" in
        consent|contract|legal-obligation|vital-interest|public-task|legitimate-interest) ;;
        *) errors+=$'\n- lawful_basis: '"\"$lb\""' (must be one of consent, contract, legal-obligation, vital-interest, public-task, legitimate-interest)' ;;
    esac
fi

# Validate last_reviewed is YYYY-MM-DD.
lr="$(awk '/^[[:space:]]*last_reviewed[[:space:]]*:/ {sub(/^[^:]+:[[:space:]]*/,""); print; exit}' "$sidecar")"
if [ -n "$lr" ] && ! [[ "$lr" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    errors+=$'\n- last_reviewed: '"\"$lr\""' (must be YYYY-MM-DD)'
fi

if [ -n "$errors" ]; then
    cat >&2 <<EOF
PDPA: 'retention-check' found invalid sidecar at ${relative}.meta.yaml.${errors}
Template: docs/compliance/retention-policy-template.md.
EOF
    exit 2
fi

exit 0
