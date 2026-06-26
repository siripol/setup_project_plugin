# Workspace — ${workspace_name}

Lightweight virtual-monorepo. Registers N service repos for cross-cutting work — editor scope, search, status, sync. NOT a real monorepo: each service keeps its own git history, CI, and deploy pipeline.

## Registered services

<!-- registry:begin -->
| Service | Profile | Lang | Path | Owners | Regulated |
|---|---|---|---|---|---|
| _(none yet)_ | — | — | — | — | — |
<!-- registry:end -->

(This table is regenerated from `.workspace/registry.json` by `sn-setup workspace list`. Hand-edits to the table will be overwritten on next regenerate; hand-edits to `registry.json` persist.)

## Day-to-day commands

| Command | Effect |
|---|---|
| `sn-setup workspace add <path>` | Register an existing checked-out repo |
| `sn-setup workspace remove <slug>` | Unregister |
| `sn-setup workspace list` | Print registry + regenerate the table above |
| `sn-setup workspace status` | `git status` across all registered repos |
| `sn-setup workspace sync` | `git pull --ff-only` across all (refuses to clobber) |
| `sn-setup workspace launch` | Open editor scoped to workspace + all registered repos |

## When to drop the workspace

Adoption is reversible — see `MIGRATION.md`.
