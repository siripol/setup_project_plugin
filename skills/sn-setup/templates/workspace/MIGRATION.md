# Workspace adoption + exit

## Adopting an existing polyrepo setup

1. Pick a workspace name (org name, team name, or product name).
2. `sn-setup workspace init <name>` creates `./<name>/`.
3. For each existing service repo (assumed to be a sibling of the workspace):
   ```
   sn-setup workspace add ../<service-repo>
   ```
4. Each `add` reads the service's `.sn-init-state.json` (if present) for profile + lang + applied policies. Pass `--owners=@team` to override.
5. `sn-setup workspace list` regenerates `WORKSPACE.md` table + `CLAUDE.md` ecosystem table.
6. (Optional) Add `<workspace-name>/` to each member repo's `.gitignore`. `sn-setup workspace add` does this automatically.

## Exiting the workspace

Workspace is opt-in and trivially reversible:

1. `rm -rf <workspace-dir>/`.
2. Remove `<workspace-name>/` from each member's `.gitignore` (manual; `sn-setup workspace remove` does not auto-strip).
3. Done. Member repos are untouched.

No data lives in the workspace itself — it's a view over independent repos.

## Why "virtual monorepo" and not Bazel / Nx / Turborepo?

This workspace is a **convenience layer**, not a build orchestrator. It does not:
- Run cross-repo builds.
- Cache cross-repo test results.
- Enforce cross-repo dependency graphs.

If your team needs those, layer a real monorepo tool on top. The workspace gives you single-editor + `git status`/`pull` aggregation; not build orchestration.

## Compatibility with B2.3 marketplace consumer (future)

When the marketplace consumer (`--marketplace=<src>`) lands, scaffolded services install plugins via marketplace. Workspace `add` will read each member's `installed_plugins` block and warn on divergence (e.g. "service A pinned `core-guardrails@1.2`, service B pinned `@1.3`"). Until B2.3, this section is informational only.
