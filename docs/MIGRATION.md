# Migration Guide — Command Sub-tree (2026-06-24)

`sn-setup` regrouped 16 flat slash commands into 3 grouped commands. This guide explains how to upgrade an existing scaffold.

## What changed

| Before (flat) | After (grouped) |
|---|---|
| `/sn-sprint-new SLUG=x` | `/sn-sprint new SLUG=x` |
| `/sn-sprint-add ...` | `/sn-sprint add ...` |
| `/sn-sprint-run ...` | `/sn-sprint run ...` |
| `/sn-sprint-status` | `/sn-sprint status` |
| `/sn-sprint-done ...` | `/sn-sprint done ...` |
| `/sn-sprint-remove ...` | `/sn-sprint remove ...` |
| `/sn-req-new ...` | `/sn-req new ...` |
| `/sn-req-import ...` | `/sn-req import ...` |
| `/sn-req-replay ...` | `/sn-req replay ...` |
| `/sn-req-resume` | `/sn-req resume` |
| `/sn-req-rollback ...` | `/sn-req rollback ...` |
| `/sn-knowledge-check ...` | `/sn-knowledge check ...` |
| `/sn-knowledge-update` | `/sn-knowledge update` |
| `/sn-knowledge-promote ...` | `/sn-knowledge promote ...` |
| `/sn-knowledge-demote ...` | `/sn-knowledge demote ...` |
| `/sn-knowledge-tech-matrix` | **retired** — use `/sn-knowledge summarize tech` |

## How to migrate

Inside an existing scaffolded repository:

```bash
sn-setup --upgrade --rename-commands
```

Effect:

- Sha-checks each old flat file in `.claude/commands/` against the original template.
- Unedited files → deleted.
- User-edited files → kept + warned. Pass `--force` to delete them anyway.
- Retired `sn-knowledge-tech-matrix.md` → deleted (unconditionally if unedited).
- New grouped files (`sn-sprint.md`, `sn-req.md`, `sn-knowledge.md`) → written (skipped if already present).
- State file gets `commands_renamed_at` + `commands_migration` block.

The command is **idempotent**: re-running it is a no-op once `commands_renamed_at` is set.

## CI / scripts

If your CI or scripts invoke the old flat commands (e.g. `/sn-sprint-new SLUG=...`), update them to the grouped syntax (`/sn-sprint new SLUG=...`).

## See also

- Design spec: `docs/superpowers/specs/2026-06-24-command-subtree-migration-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-06-24-command-subtree-migration.md`.
