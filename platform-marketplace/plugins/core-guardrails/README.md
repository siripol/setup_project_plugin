# core-guardrails

**Type**: mandatory
**Version**: 1.0.0
**Owners**: @siripol/security

Mandatory enforcement plugin for every `sn-setup` scaffolded service. Provides the Layer-1 guardrails the spec §6.2 calls out as deterministic, non-bypassable controls: audit logging, chokepoint gating, rate limiting, sensitive-path deny rules, network-exfil deny rules.

## What it installs

| Target | Files |
|---|---|
| `.claude/hooks/` | 9 hook scripts (3 events × 3 langs: `sh`/`py`/`ts`). See [Hook map](#hook-map). |
| `.claude/settings.json` (merged) | `permissions.allow`, `permissions.deny`, `hooks` registrations from `settings/settings.patch.json`. |

Docs in `rules/` describe what each deny block prevents and the threat model.

## Hook map

| Hook | Triggers on | Purpose |
|---|---|---|
| `rate-limit.{sh,py,ts}` | PreToolUse `.*` | Cap tool-call frequency; deny when over budget. |
| `chokepoint-gate.{sh,py,ts}` | PreToolUse `Edit|Write` | Block writes to chokepoint paths declared in `.harness/chokepoints.yaml`. |
| `audit.{sh,py,ts}` | PreToolUse `.*` + PostToolUse `.*` + UserPromptSubmit + SessionStart + SessionEnd + Stop | JSONL audit trail to `.sn-init/logs/exec-<date>-<session>.jsonl`. |

Three language variants per hook; the consumer-side installer picks the variant matching the scaffold's `lang`.

## Settings patch

The plugin's `settings/settings.patch.json` is **authoritative** for:

- `permissions.allow[]` baseline (git, make, language toolchain commands).
- `permissions.deny[]` for sensitive-path writes (`/etc/**`, `~/.ssh/**`, `~/.aws/**`, `~/.config/gcloud/**`, `~/.kube/**`, `~/.docker/**`, `~/.netrc`, `~/.pgpass`, `**/.env`, `**/.env.*`) on Write + Edit.
- `hooks` registrations for all 6 events.

Per ADR-MKT-002 (dual-source migration), the scaffold's `templates/claude/settings.json` mirrors the same content; CI byte-identity test in `tests/test_marketplace_producer.py` blocks drift.

## Self-containment (ADR-MKT-003)

This plugin references nothing outside `plugins/core-guardrails/`. Validator (`scripts/validate_marketplace.py`) enforces strict containment; exit 2 on any path escape.

## Version policy

Bumps MAJOR sparingly — every MAJOR forces every consuming service to deliberately re-pin. See `platform-marketplace/docs/VERSIONING.md`.

## Source of truth

Per ADR-MKT-005, `.claude-plugin/plugin.json` here is the source of truth for version + identity. The catalog entry in `platform-marketplace/.claude-plugin/marketplace.json::plugins[]` is a derived pointer; validator exits 4 on desync.

## Threat model

See `rules/deny-sensitive-paths.md` + `rules/deny-network-exfil.md`.
