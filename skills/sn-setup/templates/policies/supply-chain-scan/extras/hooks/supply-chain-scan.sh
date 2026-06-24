#!/usr/bin/env bash
# Policy: supply-chain-scan — verify any dep install passes osv-scanner.
set -euo pipefail
if ! command -v osv-scanner >/dev/null 2>&1; then
  echo "supply-chain-scan: osv-scanner not installed; allowing with warning" >&2
  exit 0
fi
osv-scanner --skip-git ./ || {
  echo "supply-chain-scan: osv-scanner found vulnerable deps" >&2
  exit 1
}
