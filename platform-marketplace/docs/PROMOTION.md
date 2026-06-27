# Promotion — getting a plugin into the marketplace

How a project-local skill, agent, hook, or document graduates into the `platform-marketplace/` catalog.

Spec §6.5 lines 256-258: "Promotion is deliberate and reviewed, never automatic."

## Two paths in

1. **Promotion** — a local capability proven across multiple services, generalized, and published. Pattern below.
2. **Greenfield plugin** — written from scratch by the platform team (e.g. `core-guardrails`, `core-workflow`). Same final checklist; skips the "value evidence" step.

## When to promote

A local capability is a promotion candidate when **all** of these hold:

- It has been invoked across **≥ 3 distinct sprints** in a service.
- Its outputs have not been overridden by reviewers in those sprints.
- It contains **no service-specific identifiers** (table names, customer IDs, internal URLs).
- At least one other team has indicated they want it (Slack ask, vault cross-ref, etc.).

If only the first holds, keep iterating locally. Premature promotion is more painful than late promotion.

## Promotion procedure

1. **Generalize**. Copy the local files; rewrite project-specific examples to be generic. Keep the slug stable across local + marketplace versions.
2. **Pick a plugin name** — kebab-case, matches `^[a-z0-9][a-z0-9-]*$`, unique across the catalog.
3. **Author the plugin directory**:
   ```
   plugins/<new-plugin>/
     .claude-plugin/plugin.json          # source of truth manifest
     README.md                            # what + why + install effect
     CHANGELOG.md                         # version history
     <claude_components per type>
   ```
4. **Author `plugin.json`** — see `plugin.schema.json` for required fields. At minimum: `name`, `version` (start at `0.1.0` for stub, `1.0.0` for first stable), `type` (`opt-in` unless platform-team approves `mandatory`), `owners`, `claude_components`.
5. **Add catalog entry** — append to `.claude-plugin/marketplace.json::plugins[]`. Version must equal `plugin.json::version`.
6. **Validate** — `python3 scripts/validate_marketplace.py` must exit 0.
7. **Self-contain** — no path inside the plugin may reference outside its directory. Validator catches violations (exit 2). For cross-plugin coupling, use `depends_on[]` in `plugin.json`.
8. **Open PR** — single PR adding the plugin dir + catalog entry. Use the template below.
9. **Review** — single platform-team approver. Checks: generalization, security, naming, self-containment, owner correctness.
10. **Merge** + announce in `#plugins` (or equivalent channel).

## Promotion PR template

```markdown
## Promote: <plugin-name>

**Source project**: <project>
**Source path(s)**: `.claude/{skills,agents,hooks,commands}/...`
**Type**: opt-in / mandatory
**Version**: 0.1.0 (stub) / 1.0.0 (first stable)

### Value evidence

- Used in N distinct sprints over <time window>: <list>.
- Cross-team interest: <Slack thread / vault note>.

### Generalization checklist

- [ ] Slug unchanged from local; kebab-case + valid pattern.
- [ ] No project-specific identifiers (table names, IDs, URLs).
- [ ] Examples rewritten to generic personas.
- [ ] Self-contained: no path escapes outside plugin dir.
- [ ] `plugin.json` validates against `plugin.schema.json`.
- [ ] Catalog entry version matches `plugin.json::version`.
- [ ] CHANGELOG.md seeded with v<version> entry.
- [ ] README documents install effect + install_targets[].

### Regression risk

- Who consumes this? <list downstream services if any>.
- Roll-back plan: previous catalog entry version (or remove if first release).
```

## Demotion (reverse path)

A plugin can be marked `deprecated: true` in its catalog entry. Requires `deprecation_message`. Deprecated plugins:

- Stay in the catalog for ≥1 quarter.
- Continue to install for existing pinning consumers.
- New consumers see the deprecation warning at scaffold time (B3.2).
- After the quarter, may be removed from the catalog (marketplace MAJOR bump).

## See also

- [VERSIONING.md](VERSIONING.md)
- [RELEASE.md](RELEASE.md)
- Vault: `design/adr/ADR-MKT-003-plugin-self-containment.md` — strict self-containment rationale.
