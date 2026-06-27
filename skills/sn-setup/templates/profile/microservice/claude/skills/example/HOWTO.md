# How to use `audit-endpoint-coverage`

This skill audits the service's HTTP/gRPC endpoints against the microservice review checklist. Use it before merging a PR that adds or modifies endpoints, or as a periodic health check.

## When to invoke

- A PR adds new endpoints or changes existing handler signatures.
- The team is auditing a service before handoff to another team.
- Quarterly review sweep across endpoints to catch drift from conventions.
- Onboarding a new engineer — a fresh sweep gives them the lay of the land.

## How to invoke

In a Claude Code session, ask:

> Run the `audit-endpoint-coverage` skill against this service.

Claude will dispatch the skill (it reads code; it does not modify it) and return a per-endpoint table.

For a focused audit on a single endpoint or path prefix:

> Run `audit-endpoint-coverage` against `/v1/users/*` only.

## What to do with the output

- ✅ rows: nothing to do.
- ⚠ rows: track in the PR description; resolve before merge.
- ❌ rows: BLOCK the PR. Open a fix-up commit or revert; do not merge with ❌ rows on regulated paths.

The output is informational. The skill does not modify code or open PRs.

## Promotion path

After this skill has been used in ≥ 3 sprints across different parts of the service with no hand-edits, evaluate promotion to the org marketplace as a generic `audit-endpoint-coverage` skill. See `docs/PROMOTION.md` for the full process.

## See also

- `SKILL.md` — the actual skill body Claude reads when dispatched.
- `.claude/docs/microservice-conventions.md` — the standards this skill checks against.
