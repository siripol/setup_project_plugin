# Service-level Governance — ${name}

How this service team owns and operates the `.claude/` tree. Treat `.claude/` like code: PR-reviewed, CODEOWNERS-protected, change-logged.

## Ownership

| Surface | Owner |
|---|---|
| `.claude/skills/<slug>/` | Service team |
| `.claude/agents/<name>.md` | Service team |
| `.claude/commands/sn-*.md` | Plugin upstream (do not hand-edit; re-scaffold via `sn-setup --upgrade`) |
| `.claude/docs/policies/<slug>.md` | Plugin catalog (managed by `sn-setup policy apply/upgrade`) |
| `.claude/rules/<slug>.md` | Plugin catalog |
| `.claude/settings.json` (`installed_plugins` block) | Service team |
| `.claude/settings.json` (hooks entries with `policy: <slug>`) | Plugin catalog — strip via `sn-setup policy remove <slug>` |
| `CLAUDE.md` | Service team |

Anyone on the service team may open a PR against any service-team-owned surface. Anyone reviewing must check that:

- The change is scoped (no incidental edits to plugin-owned files).
- New skills / agents have a clear use case (link to a sprint, issue, or vault note).
- Promotion to the org marketplace has been considered if the file has matured (see `docs/PROMOTION.md`).

## CODEOWNERS

`.claude/` must be covered by a CODEOWNERS rule so every edit to the tree pings the service team. Example `.github/CODEOWNERS` entry:

```
.claude/                 @${name}-team
docs/                    @${name}-team
```

Adjust the team handle to match your org.

## Promoting local skills + agents

Use `docs/PROMOTION.md` as the checklist. Short version:

1. Confirm the asset has been used in ≥ 3 distinct sprints with no hand-edits.
2. Run `sn-knowledge summarize "<asset> use cases"` to gather value evidence.
3. Open the promotion PR against the platform-marketplace.
4. After merge, replace the local file with an entry in `.claude/settings.json#installed_plugins`, pinned to the new version.

## Signaling regulated-data status

If this service handles regulated personal data (PDPA-class):

1. Apply the regulated-data baseline:
   ```
   sn-setup policy apply memory-regulated audit-log-strict secret-scan
   ```
   These three policies form the floor.
2. Verify with `sn-setup policy status` — all three rows show `current`.
3. When the PDPA compliance pack ships (backlog **B2.5**), apply it for the full enforcement bundle: `sn-setup policy apply pdpa-compliance --with-deps`.
4. Mark the repo in your org's data-classification registry (outside the scope of this template).

The plugin's `memory-regulated` policy denies writes to `~/.claude/memory/` and `.claude/local-memory/` so auto-memory cannot accumulate non-committed context. `audit-log-strict` forces every Claude tool call into the JSONL audit log without payload-spill. `secret-scan` blocks secret-shaped writes before they hit disk.

## Migration handoff

When this service is handed to another team:

1. Update CODEOWNERS in the same PR as the handoff announcement.
2. Update the `## Repository Ecosystem` table in `CLAUDE.md` so the new owner appears (or run `sn-knowledge summarize ownership` to refresh the org-wide view in the vault).
3. Re-run `sn-knowledge update` so the vault's knowledge buckets reflect the new owner.
4. The new owner runs `sn-setup policy status` immediately to verify the regulated-data signals (if any) are still appropriate for the new owning team.

## Change log

Treat `.claude/` edits with the same rigor as application code: write an entry in `CHANGELOG.md` `[Unreleased]` for any non-trivial change (new skill, new agent, settings.json edits beyond `installed_plugins`).

## See also

- `docs/PROMOTION.md` — promotion checklist.
- `docs/PREREQUISITES.md` — tool versions everyone needs.
- `.claude/docs/policies/` — full policy bodies (load on demand).
- Plugin design `§7.4` / `§9`.
