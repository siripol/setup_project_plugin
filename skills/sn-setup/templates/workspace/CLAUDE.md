# ${workspace_name} — Claude memory

Workspace-level memory. Auto-loaded when Claude runs from this directory.

## What this is

Cross-cutting context for a virtual monorepo of N services. Each service has its own `CLAUDE.md` with service-specific identity, profile, and policies. THIS file holds only what's true across services.

## Repository Ecosystem

<!-- registry:begin -->
| Service | Repo | Profile |
|---|---|---|
| _(none yet)_ | — | — |
<!-- registry:end -->

(Auto-populated from `.workspace/registry.json` by `sn-setup workspace list`. Foreground by usage frequency, not alphabetical.)

## Org-wide conventions

(Append rules that apply to EVERY registered service. Examples:
- All services emit structured JSON logs to stdout.
- All services use REQ-NNN commit message prefixes.
- All services apply `secret-scan` + `supply-chain-scan` policies.)

## What does NOT go here

- Service-specific architecture → that service's `CLAUDE.md`.
- Per-developer / per-machine notes → `CLAUDE.local.md` in each service.
- Long reference material → vault under `<vault>/shared/`.
