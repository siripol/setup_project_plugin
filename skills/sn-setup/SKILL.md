---
name: sn-setup
description: Scaffold a Claude-powered project (Tier 2 Agent SDK + Tier 3 Managed Agents) or add .claude/ scaffolding into an existing repo. Auto-detects mode from cwd. Use when user invokes /sn-setup or asks to "init a project".
model: claude-opus-4-8
---

# sn-setup

Slash-command skill that scaffolds Claude-powered projects following Anthropic conventions (Agent SDK + Managed Agents) and OpenAI harness engineering principles.

## When to use this skill

- User invokes `/sn-setup`
- User asks: "init a project", "scaffold a new Claude project", "set up Managed Agent project"
- User wants `.claude/` added to an existing repo

## Two modes (auto-detected from cwd)

| Mode | Trigger | Result |
|---|---|---|
| **new** | cwd empty OR `name` arg given | Full project tree + git init + commit |
| **add** | cwd non-empty + no `name` arg | Writes only `.claude/` (idempotent patch via state file) |

## Dispatch

This skill is a thin wrapper. The slash command `commands/sn-setup.md` dispatches to `scripts/sn_init.py` in the plugin root. The script handles argv parsing, mode detection, template copy, and state file management.

See `commands/sn-setup.md` for the complete flag table.
See plugin `README.md` for install instructions.

## Defaults

- `--lang=go`, `--tier=both`
- Model in generated code: `claude-opus-4-8` with `thinking: {type: "adaptive"}`
- Git init + first commit ON (opt-out via `--no-git`)
- CI workflow ON (opt-out via `--no-ci`)
- Obsidian tracking note ON (opt-out via `--no-obsidian`)
- Dep install OFF (opt-in via `--install`)

## Namespace

Generated commands and subagents land at the top of `.claude/commands/` and `.claude/agents/` with a flat `sn-` prefix on the filename (`sn-knowledge-update.md`, `sn-knowledge-curator.md`, …) so Claude Code surfaces them as `/sn-<name>` and `sn-<name>` — distinct from user-authored commands. The entry command itself stays `/sn-setup`.

## Safety

- Writes to tmp dir + atomic `mv` (crash-safe)
- Idempotent re-run via `.sn-init-state.json`
- Add mode refuses to overwrite existing `.claude/` without state file
- `--dry-run` previews without any FS write
