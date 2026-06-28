# Release process

How to cut a per-plugin release in `platform-marketplace/`.

> Phase 7 of REQ-MKT-002 will ship `scripts/release_plugin.py` to automate the steps below. Until then, releases are manual; the validator + CI guards the invariants.

## Tag namespace

Per-plugin tags use the namespace `plugin/<name>/v<semver>`. Examples:

- `plugin/core-guardrails/v1.0.0`
- `plugin/bff-patterns/v0.3.1`
- `plugin/compliance-pack/v2.0.0`

This avoids collision with the repo's own `v*.*.*` tags used by `release.yml` (the `sn-setup` CLI release pipeline).

`release.yml` is gated `if: !startsWith(github.ref_name, 'plugin/')` so it never fires on plugin tags.

## Manual release steps (interim, pre-Phase-7)

1. **Pick the bump kind** — major / minor / patch, per [VERSIONING.md](VERSIONING.md) rules.
2. **Bump the per-plugin manifest** — edit `plugins/<name>/.claude-plugin/plugin.json::version`.
3. **Bump the catalog entry** — edit `.claude-plugin/marketplace.json::plugins[]` matching name, set `version` to the new value.
4. **Append to plugin CHANGELOG** — `plugins/<name>/CHANGELOG.md`, new section header `## v<new-version> — <YYYY-MM-DD>`, body describes user-facing changes.
5. **Run validator** — `python3 scripts/validate_marketplace.py` must exit 0.
6. **Run pytest** — `python3 -m pytest -q` must pass.
7. **Commit** — `chore(marketplace): release <name>@v<new-version>` with the 3-file change (plugin.json, catalog entry, CHANGELOG).
8. **Push to main via PR** — release tags are cut from `main` only, never from feature branches.
9. **Tag from main** — `git tag plugin/<name>/v<new-version> -m "Release"` then `git push origin plugin/<name>/v<new-version>`.
10. **GitHub release** — once Phase 7 lands `marketplace-release.yml`, the tag push auto-creates a GitHub release with CHANGELOG content. Until then, create the release manually via `gh release create`.

## Automated release (Phase 7+)

Once `scripts/release_plugin.py` lands:

```bash
python3 scripts/release_plugin.py <plugin-name> --bump=patch
python3 -m pytest -q
git add . && git commit -m "chore(marketplace): release <plugin-name>@v<version>"
# open PR, merge, then:
git tag plugin/<plugin-name>/v<version> -m "Release"
git push origin plugin/<plugin-name>/v<version>
```

`.github/workflows/marketplace-release.yml` triggers on `plugin/*/v*.*.*`, validates the marketplace, extracts the CHANGELOG section, calls `gh release create plugin/<plugin-name>/v<version> --notes-file <extracted>`.

## What NOT to do

- **Never** modify a published tag. Versions are immutable.
- **Never** delete a tag. Use `deprecated: true` in the catalog entry instead.
- **Never** bump a manifest without bumping the catalog entry. Validator catches this (exit 4) but CI doesn't recover gracefully — `main` will be broken until the desync is fixed.
- **Never** release from a feature branch — tag from `main` after merge.

## See also

- [PROMOTION.md](PROMOTION.md)
- [VERSIONING.md](VERSIONING.md)
