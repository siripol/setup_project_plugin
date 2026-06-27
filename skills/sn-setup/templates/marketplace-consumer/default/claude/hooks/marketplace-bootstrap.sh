#!/usr/bin/env bash
# B2.3 marketplace-bootstrap warning hook.
#
# Runs at SessionStart. If the mandatory `core-guardrails` plugin is not yet
# installed in this repo, prints a one-line nag. Once `.claude/plugins/core-guardrails/`
# exists on disk, the hook self-deactivates (silent exit).
#
# This hook is a TEMPORARY bootstrap surface. Once core-guardrails installs,
# its own missing-plugin check takes over and warns about ALL mandatory packs
# (not just core-guardrails). Remove this hook entry from settings.json once
# you no longer need the bootstrap nag.

set -eu

if [ -d ".claude/plugins/core-guardrails" ]; then
  exit 0
fi

echo "⚠ Mandatory marketplace plugins not installed in this repo." >&2
echo "  Run:  /plugin install core-workflow core-guardrails" >&2
echo "  (marketplace source: ${marketplace_source})" >&2
exit 0
