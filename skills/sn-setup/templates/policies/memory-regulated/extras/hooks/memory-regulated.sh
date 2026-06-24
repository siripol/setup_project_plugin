#!/usr/bin/env bash
# Policy: memory-regulated — deny writes under auto-memory dirs.
set -euo pipefail
echo "memory-regulated: write under auto-memory dirs is denied" >&2
exit 1
