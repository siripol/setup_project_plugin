# ${name} — Claude memory

Committed memory file. Auto-loaded by Claude Code and the Agent SDK.

## Tier

Managed Agents (production) + Agent SDK (local dev).

## Lang

${lang}

## Profile

`${profile}` — see `docs/PROFILE.md` for shape, conventions, and what this profile isn't.

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

## Policies

Service-level policies in effect. Read the linked doc on demand.

| Category | Slug | Reference | Version |
|---|---|---|---|

## Context policy

Three tiers of context, by load behavior:

- **This file** — always-on, deliberately minimal. Identity, profile, the policies table, and section pointers only.
- **`.claude/rules/<slug>.md`** — always-on, short (≤ 50 tokens each). Hard rules that must fire every turn. See `.claude/rules/README.md`.
- **`.claude/docs/<slug>.md`** — load-on-demand. Long bodies; Claude reads when work touches the topic. See `.claude/docs/README.md`.

Free-form vault syntheses via `/sn-knowledge summarize <topic>` write to `<vault>/shared/summaries/<slug>.md` and are zero-cost until referenced.

## Local notes

Also load `CLAUDE.local.md` for per-developer notes and project-fresh additions. Treat anything there as an override of this file unless contradictory.

## What sn-setup created

(Auto-populated by sn-setup: lang, tier, flags, file count, timestamp.)
