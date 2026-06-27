# How to use `audit-component-coupling`

This skill audits this frontend's React component architecture and outputs a per-component coupling score plus refactor recommendations. Use it before a UI refactor, on PR review for component-heavy changes, or as a periodic health check on the components directory.

## When to invoke

- A PR adds or restructures components and the diff touches > 5 files.
- The team is considering a refactor of a part of the component tree (e.g., extracting a feature into its own subtree).
- Quarterly architecture review across the components directory.
- Onboarding a new engineer — a fresh audit gives them the lay of the component land.

## When NOT to invoke

- For accessibility issues — use `a11y-auditor` agent instead (`.claude/agents/a11y-auditor.md`).
- For render performance — use the React DevTools Profiler or Chrome DevTools Performance panel.
- For bundle size — use the bundler's analyze plugin (`@next/bundle-analyzer`, `rollup-plugin-visualizer`, etc.).

## How to invoke

In a Claude Code session:

> Run the `audit-component-coupling` skill against `src/components/`.

For a focused audit on one subtree:

> Run `audit-component-coupling` against `src/components/dashboard/` only.

Claude will dispatch the skill (it reads code; it does not modify it) and return a per-component table with coupling scores plus a refactor candidate list.

## What to do with the output

- **Healthy components (score ≤ 6).** No action.
- **Review components (score 7-12).** Discuss in the next architecture review; consider the suggested refactor before adding more features to the component.
- **Refactor components (score ≥ 13).** Open a refactor PR before adding new features that touch the component. The score reflects accumulated coupling debt that compounds with each addition.

The output is informational. The skill does not modify code or open PRs.

## Promotion path

After this skill has been used in ≥ 3 sprints across different parts of the component tree with no hand-edits, evaluate promotion to the org marketplace as a generic React-coupling skill. See `docs/PROMOTION.md` for the full process.

## See also

- `SKILL.md` — the actual skill body Claude reads when dispatched.
- `.claude/docs/frontend-conventions.md` — the conventions this skill checks against.
- `.claude/agents/a11y-auditor.md` — companion accessibility-focused review.
