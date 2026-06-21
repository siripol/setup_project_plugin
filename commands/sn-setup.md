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
| `--rename-ns` | off | (Use with `--upgrade`) Rename generated commands/agents to `sn-<name>` so they show as `/sn-<name>`. Handles both legacy layouts: flat bare names (`.claude/commands/<cmd>.md`) and the mid-2026 colon namespace (`.claude/commands/sn/<cmd>.md`). Rewrites cross-references in Makefile/orchestrator.py/docs and section-merges every `CLAUDE*.md` against the latest template (backups written next to each file). |

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

See `skills/sn-setup/SKILL.md` for full design + `README.md` for plugin install.
