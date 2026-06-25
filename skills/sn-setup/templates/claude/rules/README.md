# `.claude/rules/` — Always-on rules

Short, hard rules that MUST apply every turn. Loaded into the session prompt automatically. **Stay tiny** — every byte added here costs tokens on every interaction.

## What goes here

- Hard prohibitions: "never write to `~/.ssh/`", "never commit credentials".
- Single-line invariants the assistant must honor unconditionally.
- Per-policy rules dropped by `sn-setup policy apply` (e.g. `.claude/rules/memory-regulated.md`).
- Lint-style musts that the assistant should self-check before answering.

## What does NOT go here

- Long explanations, examples, decision rationale → `.claude/docs/<topic>.md`.
- Documentation about how to do something (vs *what is forbidden*).
- Identity / Profile / Policies table → `CLAUDE.md`.
- Per-developer or per-machine notes → `CLAUDE.local.md`.

## Token budget

Aim for ≤ 50 tokens per file. Five rule files at ≤ 50 tokens each ≈ 250 tokens always-on — acceptable. Twenty rule files at ≤ 100 tokens each ≈ 2000 tokens always-on — too much. When the bucket grows, move bodies to `../docs/` and keep only the headline + pointer here.

## File naming

- One rule per file.
- `kebab-case.md`.
- Filename = the rule's slug (e.g. `secret-scan.md`, `memory-regulated.md`).

## Example shape

```markdown
# Hard rule — <slug>

<one or two sentences stating the rule>. See `.claude/docs/policies/<slug>.md`
for the full body.
```

## See also

- `../docs/README.md` — load-on-demand bucket.
- `../../CLAUDE.md` — top-level always-on doc.
- Plugin design Principle 3 / §5.3.
