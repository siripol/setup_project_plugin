#!/usr/bin/env bash
# Policy: secret-scan — block writes that look like secrets.
set -euo pipefail
PAYLOAD="${CLAUDE_TOOL_INPUT:-}"
if echo "$PAYLOAD" | grep -E -q '(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}|ghp_[0-9A-Za-z]{36}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[0-9A-Za-z\-]+|-----BEGIN [A-Z ]+PRIVATE KEY-----)'; then
  echo "secret-scan: payload appears to contain a secret" >&2
  exit 1
fi
