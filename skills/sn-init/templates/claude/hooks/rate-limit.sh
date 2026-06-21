#!/usr/bin/env bash
# PreToolUse hook — blocks the call when the per-hour rate limits are exceeded.
#
# Caps (override via env):
#   SN_MAX_CALLS_PER_HOUR=200
#   SN_MAX_TOKENS_PER_HOUR=2000000
#
# State: .sn-init/workflow-state.json under rate_window. Hourly reset.
# Exit code 0 = allow, 2 = block.

set -u

# Resolve project root.
root="$PWD"
while [ "$root" != "/" ] && [ ! -d "$root/.sn-init" ] && [ ! -f "$root/CLAUDE.md" ]; do
    root="$(dirname "$root")"
done
state="$root/.sn-init/workflow-state.json"

max_calls="${SN_MAX_CALLS_PER_HOUR:-200}"
max_tokens="${SN_MAX_TOKENS_PER_HOUR:-2000000}"

# Without jq we can't reliably parse — allow the call but emit a notice.
if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

# Default state when file is missing.
if [ ! -f "$state" ]; then
    exit 0
fi

now_epoch="$(date +%s)"
window_start_epoch="$(jq -r '.rate_window.window_start // empty' "$state" 2>/dev/null \
    | xargs -I {} date -j -f '%Y-%m-%dT%H:%M:%S' {} +%s 2>/dev/null \
    || echo 0)"

calls="$(jq -r '.rate_window.calls_this_hour // 0' "$state" 2>/dev/null || echo 0)"
tokens="$(jq -r '.rate_window.tokens_this_hour // 0' "$state" 2>/dev/null || echo 0)"

# Reset window every hour.
if [ -n "$window_start_epoch" ] && [ $((now_epoch - window_start_epoch)) -gt 3600 ]; then
    calls=0
    tokens=0
fi

if [ "$calls" -ge "$max_calls" ]; then
    echo "rate-limit: $calls calls in this hour (>= $max_calls). Block." >&2
    exit 2
fi
if [ "$tokens" -ge "$max_tokens" ]; then
    echo "rate-limit: $tokens tokens in this hour (>= $max_tokens). Block." >&2
    exit 2
fi
exit 0
