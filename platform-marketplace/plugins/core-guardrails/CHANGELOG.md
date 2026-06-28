# Changelog — core-guardrails

All notable changes to the `core-guardrails` plugin. Format per [Keep a Changelog](https://keepachangelog.com/). Versions are taken from `.claude-plugin/plugin.json`.

## v1.0.0 — 2026-06-28

Initial release. Extracted from `setup_project_plugin` scaffold templates as part of B3.1 Phase 2 (REQ-MKT-002).

### Added

- 9 hook scripts (audit / chokepoint-gate / rate-limit × sh / py / ts). Byte-identical to `templates/claude/hooks/*` in the scaffold; sync guarded by `tests/test_marketplace_producer.py::test_b31_phase2_core_guardrails_hooks_match_scaffold`.
- Authoritative `settings/settings.patch.json` with `permissions.allow`, `permissions.deny`, `hooks` registrations.
- Two threat-model docs in `rules/`: `deny-sensitive-paths.md` (filesystem deny rationale) + `deny-network-exfil.md` (toolchain deny rationale).
- Catalog entry in `platform-marketplace/.claude-plugin/marketplace.json` (type: mandatory).

### Notes

- This plugin is `mandatory`; every scaffolded service receives it. Removal is a security event (B3.2 will block it mechanically).
- Dual-source with scaffold per ADR-MKT-002. Phase 6 hybrid cutover keeps `core-guardrails` template-baked forever (defense-in-depth per spec §6.2 line 233).
