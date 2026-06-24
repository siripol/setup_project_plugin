---
name: sn-setup
description: Scaffold a Claude-powered project (Tier 2 Agent SDK + Tier 3 Managed Agents), or add .claude/ scaffolding into an existing repo. Auto-detects mode from cwd. Use when the user invokes /sn-setup or asks to init a project.
---

# /sn-setup

Scaffold a Claude-powered project at Tier 2 (Agent SDK) and/or Tier 3 (Managed Agents). Auto-detects mode from the current working directory.

## Invocation

```
/sn-setup [name] [flags]
```

- If `name` is given OR cwd is empty → **new mode**: creates `<cwd>/<name>/` (or scaffolds into cwd if no name + empty) with the full project tree.
- If cwd is non-empty and no `name` → **add mode**: writes only `.claude/` into cwd. Idempotent — patches missing files using `.sn-init-state.json`.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--lang=go\|py\|ts` | `go` | Stack overlay |
| `--tier=2\|3\|both` | `both` | Anthropic tier (Tier 1 standalone is out of scope) |
| `--license=none\|MIT\|Apache-2.0` | `none` | Write `LICENSE` if not `none` |
| `--no-git` | git on | Skip `git init` + first commit in new mode |
| `--install` | off | Run dep install + `ant agents apply` after scaffold |
| `--retry=N` | `3` | Retries for `--install` step on transient failure |
| `--no-ci` | CI on | Skip `.github/workflows/ci.yml` |
| `--devcontainer` | off | Write `.devcontainer/devcontainer.json` |
| `--obsidian[=VAULT_PATH]` / `--no-obsidian` | on | Obsidian tracking note. Vault resolution: explicit → `$OBSIDIAN_VAULT` → `<target>/docs/exec-plans/active/` |
| `--prompt="..."` | placeholder | Seed `agents/main.yaml` system block |
| `--workflow=spec-loop\|none` | `spec-loop` | Spec-driven autonomous dev loop scaffold |
| `--dry-run` | off | Print planned tree + diffs, no FS writes |
| `--verbose` | off | Per-step log to target's `.sn-setup.log` |
| `--upgrade` | off | Patch-only: pull missing template files into an existing scaffold and bump `template_version`. Never overwrites edited files. |
| `--rename-commands` | off | Rename flat `sn-X-Y.md` commands to grouped `sn-X.md`. Requires `--upgrade`. |
| `--force` | off | Bypass sha-check for `--rename-commands` (delete user-edited files anyway). |
| `--policies=<csv>` | Replace profile defaults with this exact list. | none |
| `--add-policies=<csv>` | Add policies to the profile defaults. Cannot combine with `--policies=`. | none |
| `--remove-policies=<csv>` | Remove policies from the profile defaults. Cannot combine with `--policies=`. | none |
| `--with-deps` | When applying, also install required-by policies. | false |

## Generated grouped slash commands

Scaffolded projects ship 3 grouped commands under `.claude/commands/`:

- `sn-sprint` — verbs: `new | add | run | status | done | remove`
- `sn-req` — verbs: `new | import | replay | resume | rollback`
- `sn-knowledge` — verbs: `check | update | promote | demote | summarize`

For existing scaffolds with the old flat commands, run `sn-setup --upgrade --rename-commands`. See `docs/MIGRATION.md`.

## Sub-commands

After the initial scaffold, two sub-trees manage policies in the current
project:

- `sn-setup policy <list|show|apply|remove|upgrade|status|show-applied|history|lint>` — apply or remove individual policies; see spec §4 for full reference.
- `sn-setup profile <list|show|add|remove|swap>` — edit the profile→default-policies mapping (auto-detects plugin repo vs scaffolded project).

See `docs/superpowers/specs/2026-06-24-policy-catalog-design.md` for the full design.

## Behavior contract

Body of this command dispatches to `scripts/sn_init.py`. The script:

1. Parses argv, validates flags (`exit 2` on usage error).
2. Detects mode from cwd state.
3. Writes to a tmp dir `target.tmp-<rand>/` then `mv` to final path (atomic).
4. Writes `.sn-init-state.json` last (idempotent re-run anchor).
5. Optionally runs `git init` + first commit (unless `--no-git`).
6. Optionally runs lang dep install + `ant agents apply` (when `--install`).
7. Prints success summary or remediation hints on failure.

## Exit codes

`0` ok, `2` usage / bad flag, `3` target dir non-empty + name given, `4` `.claude/` exists in add mode without state file, `5` Obsidian vault unwritable (only when explicit), `6` `--install` failed after retries, `7` validation gate failed, `8` template version mismatch, `99` internal error.

### Additional exit codes (policy / profile sub-trees)

The `sn-setup policy` and `sn-setup profile` sub-commands and scaffold-time `--policies` / `--add-policies` / `--remove-policies` flags introduce these codes (per spec §10):

| Code | Name | When it fires |
|---|---|---|
| 10 | `UNKNOWN_POLICY` | Slug not in catalog |
| 11 | `UNKNOWN_PROFILE` | Profile name unknown |
| 12 | `EXCLUSIVE_GROUP_CONFLICT` | Group constraint violated (reserved for future `--no-swap`) |
| 13 | `REQUIRES_NOT_SATISFIED` | Policy needs prerequisite slugs not applied; retry with `--with-deps` |
| 14 | `USER_EDITED_BLOCKS_OP` | Remove/upgrade hit a user-edited file; pass `--force` to override |
| 15 | `CWD_AMBIGUOUS_OR_INVALID` | `sn-setup profile` cwd is neither a plugin repo nor a scaffolded project |
| 16 | `POLICY_NOT_APPLIED` | Remove/upgrade for a slug not in `applied_policies` |
| 17 | `MIXED_OVERRIDE_FLAGS` | `--policies=` combined with `--add-policies` / `--remove-policies` |
| 18 | `CATALOG_DOWNGRADE` | State version > catalog version for a slug |
| 19 | `MALFORMED_PATCH` | `settings.patch.json` entry missing `policy:` field |
| 20 | `CONFLICTS_WITH_VIOLATION` | Apply violates a `conflicts_with` entry against already-applied policy |

See `skills/sn-setup/SKILL.md` for full design + `README.md` for plugin install.
