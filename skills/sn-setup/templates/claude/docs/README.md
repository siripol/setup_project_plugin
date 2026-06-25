# `.claude/docs/` — Load-on-demand context

Long-form reference material that Claude reads **only when work touches the topic**. Zero baseline cost — the file isn't in the session prompt until Claude opens it with the Read tool.

## What goes here

- Architecture overviews and decision records.
- Detailed coding standards (full body — not just the headline rule).
- Domain glossaries.
- Operational runbooks.
- Reference for any topic that's >50 tokens AND doesn't need to fire every turn.
- Generated catalog content: `.claude/docs/policies/<slug>.md` (managed by `sn-setup policy apply`).

## What does NOT go here

- Hard rules that must fire every turn → `.claude/rules/<slug>.md` instead.
- Identity, profile, policy table, top-level pointers → `CLAUDE.md`.
- Per-developer or per-machine notes → `CLAUDE.local.md`.
- Long-form content that exists in the Obsidian vault — link instead, don't duplicate.

## How Claude reads these

Three legitimate triggers cause Claude to open a file in this dir:

1. **User asks** — `"what's our architecture?"` → Claude greps + reads `ARCHITECTURE.md`.
2. **Skill description matches** — a skill says "review respects the project's architecture doc"; Claude invokes the skill; the skill body reads.
3. **Hook surfaces a pointer** — e.g. a deny hook emits "see `.claude/docs/policies/memory-regulated.md` for context"; Claude reads when composing the user-facing reply.

In every case the read is **on-demand**. Files here do not get auto-loaded.

## File naming

- One topic per file.
- `kebab-case.md`.
- For catalog content: `policies/<slug>.md`, `architecture/<area>.md`, etc.
- README for each sub-dir explaining what lives there.

## See also

- `../rules/README.md` — always-on rule files.
- `../../CLAUDE.md` — the always-loaded top-level doc.
- Plugin design Principle 3 / §3.3 / §5.3.
