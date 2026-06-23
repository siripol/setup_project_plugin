# Policy — Memory: regulated

Tier: **regulated**. Auto-memory disabled.

## What this means

All context comes from committed files only. Every input to the assistant's
behavior must be reviewable in git.

## Enforcement

`.claude/hooks/memory-regulated.sh` runs as a `PreToolUse` hook on `Write`
and denies any write under `~/.claude/memory/` or `.claude/local-memory/`.

## Pairing

Apply alongside `audit-log-strict` + `secret-scan` for the full regulated
posture; or apply `pdpa-compliance` which bundles all three.
