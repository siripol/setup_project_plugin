# `.claude/skills/` — project-local skills

A **skill** is a packaged competence Claude can invoke. Skills under `.claude/skills/` are project-local: they ship with this repo, are owned by the service team, and stay in this repo until promoted to the org marketplace.

## When to add a project-local skill

- A task pattern recurs across multiple sprints in this repo (≥ 3 times) and benefits from a packaged workflow.
- The pattern is project-specific enough that it would not yet make sense as an org-wide skill.
- The pattern is small enough that the skill stays under ~200 lines of Markdown + a tight tool list.

If the pattern is already common across services in the org, skip the local skill and look for an existing marketplace skill instead.

## Skill anatomy

Each skill lives at `.claude/skills/<slug>/`:

```
<slug>/
├── SKILL.md         # the prompt Claude reads when the skill is invoked
└── HOWTO.md         # human-facing how-to for the team (optional)
```

`SKILL.md` opens with a single-paragraph description of when Claude should invoke this skill. The body lists steps, references the relevant `.claude/docs/` bodies, and ends with output expectations.

`HOWTO.md` documents for humans: what the skill does, when to use it, expected outcome. Helpful for hand-off to new team members.

## Naming

Skills use `kebab-case` slugs. Convention:

- Verb-noun for action skills: `audit-endpoint-coverage`, `validate-request-shape`.
- Topic-only for review skills: `bff-contract-review`, `accessibility-pass`.
- No tool prefix (`claude-`, `ai-`); these live under `.claude/` already.

## Promoting to the marketplace

When a project-local skill has earned its place — used in ≥ 3 distinct sprints with no hand-edits, value evidence collected, no project-specific identifiers in the body — promote it to the org marketplace per `docs/PROMOTION.md`.

After promotion, the local copy at `.claude/skills/<slug>/` is replaced by an entry in `.claude/settings.json::installed_plugins` pinned to the new version. The slug name typically stays the same so call sites do not break.

## How to seed a new skill

1. Decide the slug.
2. Copy `example/` (or `example-bff/` if profile is `bff`) as a starting point: `cp -r .claude/skills/example .claude/skills/<slug>`.
3. Edit `SKILL.md` to describe when Claude should invoke it and what the output should look like.
4. Edit `HOWTO.md` to document the human-facing usage.
5. Test by invoking Claude on a real task that should match. Iterate.
6. Open a PR; CODEOWNERS reviews.

## See also

- `example/SKILL.md` (or `example-bff/SKILL.md` for BFF profile) — the seeded exemplar this profile ships.
- `docs/PROMOTION.md` — the promotion path to the org marketplace.
- `docs/GOVERNANCE-SERVICE-LEVEL.md` — ownership of `.claude/` is the service team.
