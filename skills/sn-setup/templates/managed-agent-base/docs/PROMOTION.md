# Promotion — Local Skill / Agent → Org Marketplace

When a local capability (a `.claude/skills/<slug>/` skill or a `.claude/agents/<name>.md` agent) has earned its place by helping repeatedly, promote it to the org's internal plugin marketplace so other teams can install it.

## When to promote

A local skill or agent is a promotion candidate when **all** of these are true:

- It has been invoked across **≥ 3 distinct sprints** in this repo.
- Its outputs have not been overridden or hand-edited by reviewers in those sprints.
- It contains **no project-domain-specific content** that wouldn't make sense in another service (e.g. no hardcoded table names, customer IDs, internal URLs).
- At least one other team has indicated they want it (Slack ask, vault-summary cross-reference, etc.).

If only the first one is true, keep iterating locally. Premature promotion is more painful than late promotion.

## How to promote

1. **Sanity check** — run `sn-knowledge summarize "<slug> use cases"` to gather evidence of value from the vault. Save the result; it becomes the body of the promotion PR.
2. **Generalize** — copy the local file verbatim, then rewrite project-specific examples and assertions to be generic. Keep the slug stable across local + org versions.
3. **Bump version** — every shared marketplace asset is semver-pinned. Start at `1.0.0`.
4. **Open the PR** against the platform-marketplace repository. Use the template below.
5. **Wait for CODEOWNERS review** — at least one approver from the platform team. They'll check generalization, security, and naming.
6. **After merge** — locally replace the file with an install entry in `.claude/settings.json`'s `installed_plugins` block, pinned to the version you just published. Delete the local copy in the same commit.
7. **Announce** — drop a line in the org's #plugins channel with the new asset name + version + your evidence summary.

## Promotion PR template snippet

```markdown
## Promotion: <slug>

**Source project**: <project>
**Source path**: `.claude/{skills,agents}/<slug>/...`
**Version**: 1.0.0

### Value evidence
- Used in N distinct sprints over <time window>.
- Specific examples: <links to sprint outputs, vault summaries>.

### Generalization checklist
- [ ] No project-specific identifiers (table names, IDs, URLs) remain.
- [ ] Examples rewritten to generic personas.
- [ ] Tests / invariants live next to the asset.
- [ ] CHANGELOG entry seeded for the marketplace.

### Regression risk
- Who consumes this? (List downstream services if any.)
- Roll-back plan: pin the previous version in `.claude/settings.json`.
```

## Reverse path — demotion

If a marketplace asset turns out to be project-specific after all, run `sn-knowledge demote <topic>` to move the supporting knowledge note back into the project's vault bucket, then open a marketplace PR removing the asset (or scoping it down). A `[skip]` tag in the backlog with one-line reason is enough.

## See also

- `docs/GOVERNANCE-SERVICE-LEVEL.md` — who owns the local `.claude/` tree.
- `docs/PREREQUISITES.md` — tool versions required to participate.
- Plugin design `§6.5` for the promotion architecture.
