# ${name} — Claude memory

Committed memory file. Auto-loaded by Claude Code and the Agent SDK.

## Tier

Managed Agents (production) + Agent SDK (local dev).

## Lang

${lang}

## Default model

`${model}` with `thinking: {type: "adaptive"}`.

## Agent ID

(Populated by `make agent` / `--install`; leave blank otherwise.)

## Commands

| Make target | Action |
|---|---|
| `make agent` | `ant agents apply agents/main.yaml` |
| `make session` | start a Managed Agent session |
| `make test` | run the lang test suite |
| `make validate` | `ant agents validate` |
| `make logs-tail` | tail audit log |

## Conventions

- One acceptance criterion per requirement bullet.
- Tests live in `tests/`. Add a smoke test per new feature.
- All Claude calls write a JSONL audit log to `.sn-init/logs/`.

## Tracking

(Obsidian note path goes here when `--obsidian` is on.)

## Local notes

Also load `CLAUDE.local.md` for per-developer notes and project-fresh additions. Treat anything there as an override of this file unless contradictory.

## What sn-init created

(Auto-populated by sn-init: lang, tier, flags, file count, timestamp.)
