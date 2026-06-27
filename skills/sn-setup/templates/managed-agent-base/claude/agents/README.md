# `.claude/agents/` — project-local subagents

A **subagent** is a specialized Claude with a focused prompt, a narrow tool list, and an explicit return contract. Subagents under `.claude/agents/` are project-local: they ship with this repo, are owned by the service team, and stay here until promoted to the org marketplace.

## When to add a project-local subagent

- A class of review or analysis recurs across PRs in this repo (e.g., "every BFF contract change needs a downstream-compatibility review").
- The review benefits from isolated context — the main thread should not lose its working state to do the review.
- The reviewer's job is bounded and articulable: clear inputs, clear outputs, clear pass/fail criteria.

If the review is org-wide (every service in the org needs it), look for an existing marketplace subagent first and pin it via `installed_plugins`.

## Subagent anatomy

Each subagent lives at `.claude/agents/<name>.md` with YAML frontmatter and a Markdown body:

```yaml
---
name: <slug>
description: When to dispatch this subagent (used by Claude's natural dispatch).
tools: [Read, Glob, Grep]
---

# <Subagent Name>

Body: the prompt the subagent receives when dispatched.
```

The body is a focused prompt. It tells the subagent what to look for, in what shape to report, and what to skip. Subagents are stateless dispatch — the entire context they get is the prompt body + the dispatcher's user-side prompt + the file inputs they read.

## Frontmatter fields

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Matches the file basename. Slug, kebab-case. |
| `description` | Yes | One sentence. Claude reads this to decide whether to dispatch the subagent on a given task. Be specific. |
| `tools` | Yes | Allowlist of tools the subagent can use. Keep tight; reviewers usually need only `Read`, `Glob`, `Grep`. |
| `model` | No | Optional model override (`haiku`, `sonnet`, `opus`). Defaults to inheriting the dispatcher. |

## Naming

Subagents use `kebab-case` slugs. Convention:

- Role-suffix for reviewers: `bff-integration-reviewer`, `security-auditor`, `a11y-auditor`.
- Action-suffix for analyzers: `risk-analyzer`, `coverage-mapper`.

Avoid generic names (`reviewer`, `helper`) — they collide with marketplace subagents and confuse the dispatcher.

## Promoting to the marketplace

Same promotion path as skills (`docs/PROMOTION.md`). Subagents tend to promote more slowly than skills because their value evidence requires multiple sprints and PRs to accumulate.

## How to seed a new subagent

1. Decide the name.
2. Copy an existing exemplar (e.g., this profile's seeded reviewer) as a starting point.
3. Edit the frontmatter: new `name`, new `description`, prune the `tools` list to the minimum.
4. Rewrite the body for the new scope.
5. Test by dispatching the subagent on a real PR diff. Iterate.
6. Open a PR; CODEOWNERS reviews.

## See also

- `docs/PROMOTION.md` — the promotion path to the org marketplace.
- `docs/GOVERNANCE-SERVICE-LEVEL.md` — ownership of `.claude/` is the service team.
- The shipped exemplar in this folder (profile-specific; varies by `--profile=`).
