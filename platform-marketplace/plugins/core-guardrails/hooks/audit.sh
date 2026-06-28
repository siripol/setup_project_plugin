#!/usr/bin/env bash
# Claude Code session audit hook. Writes one JSONL record per fired event to
# .sn-init/logs/exec-<YYYY-MM-DD>-<session>.jsonl in the current working directory.
#
# Input: Claude Code passes hook event data on stdin as JSON.
# Output: nothing (silent). Errors swallowed so the session isn't blocked.

set -u

# Resolve project root: walk up until we find .sn-init/ or CLAUDE.md.
root="$PWD"
while [ "$root" != "/" ] && [ ! -d "$root/.sn-init" ] && [ ! -f "$root/CLAUDE.md" ]; do
    root="$(dirname "$root")"
done
log_dir="$root/.sn-init/logs"
mkdir -p "$log_dir/blobs" 2>/dev/null || exit 0

# Pull session_id + event from CLAUDE_HOOK_EVENT env if set, else fall back.
event="${CLAUDE_HOOK_EVENT:-unknown}"
session="${CLAUDE_SESSION_ID:-unknown}"
date="$(date -u +%Y-%m-%d)"
ts="$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
log_file="$log_dir/exec-${date}-${session}.jsonl"

# Read stdin payload (capped at 8KB; spill beyond to blob).
payload="$(head -c 8192 2>/dev/null || true)"
truncated="false"
blob_ref=""
payload_size="${#payload}"
if [ "$payload_size" -ge 8192 ]; then
    truncated="true"
    blob_hash="$(printf '%s' "$payload$ts" | shasum -a 256 | cut -d' ' -f1 | cut -c1-16 2>/dev/null || echo "$$")"
    blob_path="$log_dir/blobs/${blob_hash}.txt"
    printf '%s' "$payload" > "$blob_path" 2>/dev/null
    blob_ref="$blob_hash"
fi

# Build the JSON record (jq if available, else minimal shell construction).
if command -v jq >/dev/null 2>&1; then
    jq -c -n \
        --arg ts "$ts" \
        --arg session "$session" \
        --arg event "$event" \
        --arg payload "$payload" \
        --argjson truncated "$truncated" \
        --arg blob "$blob_ref" \
        '{ts:$ts, session_id:$session, event:$event, payload:$payload, truncated:$truncated} + (if $blob == "" then {} else {blob:$blob} end)' \
        >> "$log_file" 2>/dev/null || true
else
    # Fallback: escape minimally — strip newlines + double-quotes from payload.
    safe="$(printf '%s' "$payload" | tr -d '\r\n' | sed 's/"/\\"/g')"
    {
        printf '{"ts":"%s","session_id":"%s","event":"%s","payload":"%s","truncated":%s' \
            "$ts" "$session" "$event" "$safe" "$truncated"
        if [ -n "$blob_ref" ]; then
            printf ',"blob":"%s"' "$blob_ref"
        fi
        printf "}\n"
    } >> "$log_file" 2>/dev/null || true
fi

exit 0
