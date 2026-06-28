# platform-marketplace

Internal-only plugin marketplace for `setup_project_plugin` scaffolds. Producer side of Layer 1 (REQ-MKT-002 / B3.1).

Scaffolded services consume this marketplace via the `--marketplace=<source>` flag shipped by B2.3 (REQ-MKT-001). When set, the scaffolded `.claude-plugin/marketplace.json` points at this catalog; `.claude/settings.json::installed_plugins[]` lists which plugins should install; a SessionStart bootstrap hook nags until the mandatory plugins are present.

## Layout

```
platform-marketplace/
├── .claude-plugin/
│   ├── marketplace.json                # the catalog — plugin index + pinned versions
│   ├── marketplace.schema.json         # JSON Schema Draft 2020-12 for catalog
│   └── plugin.schema.json              # JSON Schema Draft 2020-12 for per-plugin manifest
├── plugins/                            # one subdir per plugin; populated Phase 2+
│   ├── core-workflow/                  # (Phase 3) mandatory advisory
│   ├── core-guardrails/                # (Phase 2) mandatory enforcement
│   └── ...                             # opt-in plugins per spec §6.3
└── docs/
    ├── PROMOTION.md                    # how local skill/agent gets promoted to plugin
    ├── VERSIONING.md                   # semver policy + consumer pin syntax
    └── RELEASE.md                      # how to cut a per-plugin release
```

## Catalog source of truth

The per-plugin manifest at `plugins/<name>/.claude-plugin/plugin.json` is the source of truth (ADR-MKT-005). The catalog entry in `marketplace.json` is a lightweight pointer; the validator (`scripts/validate_marketplace.py`) enforces that catalog `version` matches per-plugin `version` exactly. Phase 7 release tooling keeps them in sync atomically.

## Plugin types

| Type | Examples | When installed |
|---|---|---|
| **mandatory** | `core-workflow`, `core-guardrails` | Always present in every consumer's `installed_plugins[]`. Removal is a security event (B3.2 will block it mechanically). |
| **opt-in** | `bff-patterns`, `contracts-sync`, `compliance-pack`, `governance-docs`, `testing-standards`, `cicd-helpers`, `service-scaffold` | Profile-driven (BFF gets `bff-patterns` + `contracts-sync`) or policy-driven (regulated service gets `compliance-pack`). |

## Self-containment (ADR-MKT-003)

Plugins are strictly self-contained at the filesystem level. A file inside `plugins/<a>/` MUST NOT reference any path outside `<a>/`. The validator exits with code 2 on any escape.

Cross-plugin coupling is expressed ONLY through `depends_on[]` in the catalog manifest. Consumer-side install ordering respects this graph.

## Validation

Run the validator before opening a PR:

```bash
python3 scripts/validate_marketplace.py
```

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Valid |
| 1 | Schema violation (catalog or per-plugin) |
| 2 | Self-containment violation (path escape, cross-plugin symlink) |
| 3 | Dependency graph violation (missing dep, cycle, unsatisfiable constraint) |
| 4 | Catalog ↔ per-plugin version desync |

CI runs the validator as part of `pytest` matrix (see `.github/workflows/ci.yml`).

## Contributing a new plugin

See [docs/PROMOTION.md](docs/PROMOTION.md).

## Releasing

See [docs/RELEASE.md](docs/RELEASE.md). Tag namespace `plugin/<name>/v<semver>`.

## References

- [requirements/marketplace-producer.md](../../obsidian_sharedknowledge/projects/setup_project_plugin/requirements/marketplace-producer.md) (vault) — REQ-MKT-002 umbrella.
- [design/marketplace-producer-design.md](../../obsidian_sharedknowledge/projects/setup_project_plugin/design/marketplace-producer-design.md) (vault) — full design.
- `design/adr/ADR-MKT-001` / `ADR-MKT-002` / `ADR-MKT-003` (vault) — locked decisions.
