---
name: claude-local-edit
description: Append a timestamped entry to the project's CLAUDE.local.md. Gitignored, auto-loaded into Claude memory. Use for per-developer notes, local env, or fresh project conventions not yet ready for the committed CLAUDE.md.
args:
  - ENTRY (required) — the note to append
---

# /claude-local-edit

Add a per-developer / per-machine note to `CLAUDE.local.md` at the project root.

## Usage

```
/claude-local-edit ENTRY="DB url is postgres://localhost:5432/demo_dev"
```

## Behavior

Appends two entries to `CLAUDE.local.md` (creating the file from template if missing):

- `## Recent additions` — timestamped: `YYYY-MM-DD HH:MM — <ENTRY>`
- `## New common claude data` — bullet: `- <ENTRY>`

File is gitignored. Both Claude Code and the Agent SDK auto-load it on session start. Promote stable items to root `CLAUDE.md` when they harden.
