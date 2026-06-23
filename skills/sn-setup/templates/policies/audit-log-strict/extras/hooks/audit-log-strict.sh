#!/usr/bin/env bash
# Policy: audit-log-strict — append a JSONL line for every tool call.
set -euo pipefail
LOGDIR=".sn-init/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/exec-$(date -u +%F)-${CLAUDE_SESSION_ID:-unknown}.jsonl"
printf '{"timestamp":"%s","tool":"%s","request":%s,"response":%s,"duration_ms":%s}\n' \
  "$(date -u +%FT%TZ)" "${CLAUDE_TOOL:-unknown}" \
  "${CLAUDE_REQUEST_JSON:-null}" "${CLAUDE_RESPONSE_JSON:-null}" \
  "${CLAUDE_DURATION_MS:-0}" >> "$LOG"
