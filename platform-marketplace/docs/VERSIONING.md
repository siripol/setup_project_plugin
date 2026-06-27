# Versioning policy

Every plugin in `platform-marketplace/` carries an independent semver (`MAJOR.MINOR.PATCH`). Consumers pin by name + version; updates are deliberate.

## Per-plugin semver

Each plugin's version lives in two places, kept in lockstep:

- `plugins/<name>/.claude-plugin/plugin.json::version` — source of truth.
- `plugins/<name>/.claude-plugin/marketplace.json` catalog entry's `version` — validated against the manifest.

The validator (`scripts/validate_marketplace.py`) exits with code 4 if these desync. Phase 7 release script (`scripts/release_plugin.py`) updates both atomically.

### When to bump

| Change | Bump |
|---|---|
| Breaking change to hook signature, deny rule, or settings patch | **MAJOR** |
| New command, skill, agent, or hook; new optional setting | **MINOR** |
| Bug fix, doc tweak, internal refactor | **PATCH** |

Mandatory plugins (`core-workflow`, `core-guardrails`) bump MAJOR sparingly — every MAJOR bump requires every consuming service to deliberately re-pin.

## Consumer pin syntax

Consumers pin in `.claude/settings.json::installed_plugins[]`:

```json
{
  "installed_plugins": [
    {"name": "core-workflow", "version": "1.2"},
    {"name": "core-guardrails", "version": "1.0"},
    {"name": "bff-patterns", "version": "0.3"}
  ]
}
```

Pin shape is `MAJOR.MINOR` (e.g. `1.2`). This binds the consumer to the highest published `1.2.x` patch. PATCH-level updates auto-apply on re-install; MINOR or MAJOR updates require a deliberate re-pin.

No `latest` channel — per spec §7.3 line 304, "updates are not automatic; refreshing marketplace and reinstalling is a conscious, reviewable act."

## No drift guarantee

Once a service pins `name@1.2`, that service receives the same `1.2.x` content as every other service pinned to `name@1.2`. The marketplace publishes immutable versions; a published `1.2.3` is never republished or modified.

## Catalog `marketplace.version`

The catalog itself has a version (`marketplace.marketplace.version`). It bumps when:

- A new plugin is added to the catalog (MINOR).
- A plugin is removed or marked `deprecated` (MAJOR).
- Catalog schema changes (MAJOR, plus schema_version bump).

## Constraint shapes (in `depends_on[]`)

Plugins may declare dependencies on other plugins. Supported constraint shapes:

| Constraint | Means |
|---|---|
| `^1.2` | `>=1.2.0, <2.0.0` (same major) |
| `~1.2` | `>=1.2.0, <1.3.0` (same major+minor) |
| `1.2.3` | exact version |

Validator exits with code 3 on cycle, missing dep, or unsatisfiable constraint.

## Deprecation

A plugin can be marked `deprecated: true` in its catalog entry. Requires `deprecation_message`. The validator warns; consumers see the message in `/sn-verify` output (B3.2). Deprecated plugins stay in the catalog for ≥1 quarter before removal.

## See also

- [PROMOTION.md](PROMOTION.md) — how a plugin gets into the catalog.
- [RELEASE.md](RELEASE.md) — how to cut a release once the version is bumped.
