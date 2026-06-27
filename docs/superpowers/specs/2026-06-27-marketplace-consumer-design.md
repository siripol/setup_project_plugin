---
topic: marketplace-consumer-requirements
bucket: projects
origin_project: setup_project_plugin
origin_req: REQ-MKT-001
first_seen: 2026-06-27
last_updated: 2026-06-27
status: planned
tags: [knowledge, requirements, marketplace, scaffold-template, layer1-consumer, b2.3, setup_project_plugin]
---

# Requirements — Internal Plugin-Marketplace Consumer (B2.3)

REQ-MKT-001. Backlog item **B2.3**. Light workflow: single combined requirements + design + implementation plan note (this file) + one PR.

## Goal

Wire the **consumer side** of the org's internal plugin marketplace into every scaffolded project. Add a CLI flag `--marketplace=<source>` to `sn-setup new|demo`. When set, the scaffold writes:

1. `.claude-plugin/marketplace.json` — a tiny consumer manifest that points to the org's marketplace source (so future `/plugin install` calls know where to look).
2. A new top-level key `installed_plugins` in `.claude/settings.json` listing the **two mandatory plugins** every service should run with (`core-workflow`, `core-guardrails`) plus profile-specific opt-in packs.
3. A small **SessionStart bootstrap warning hook** at `.claude/hooks/marketplace-bootstrap.sh` that prints a one-line nag if `core-guardrails` is not yet installed. The hook self-deactivates the moment `.claude/plugins/core-guardrails/` exists on disk.

The catalog list of org plugins (which packs exist, which are mandatory, which are opt-in by profile) does **NOT** ship in this PR. Per the design lock, that catalog lives **inside** `core-workflow` (human-facing markdown doc) and `core-guardrails` (machine-readable manifest + missing-plugin check hook). Both packs themselves are shipped by **B3.1** (platform marketplace stand-up, Tier 3). B2.3 only wires the consumer-side hook so the wiring is in place the moment B3.1 ships and users `/plugin install` the mandatory packs.

Source: microservices template-family design doc (local-only at `temp/__claude__microservices-template-design_20260623133500.md`) — §6.1 (internal marketplace), §6.2 (the two mandatory plugins), §6.3 (opt-in plugins), §9.3 (`platform-marketplace/` Layer 1 spec). Plus design-lock decisions captured during the brainstorm in this session (split catalog, bootstrap hook, SessionStart trigger, URL-or-path source format).

## Decisions locked (brainstorm)

| # | Question | Choice |
|---|---|---|
| D-1 | Where does the marketplace catalog live? | **Split across both packs**: `core-workflow` carries the human-facing markdown catalog; `core-guardrails` carries the machine-readable manifest + missing-plugin check hook. (Both packs are shipped by B3.1, not B2.3.) |
| D-2 | How do we warn the user about missing mandatory packs BEFORE the packs are installed? | **Scaffold ships a tiny bootstrap hook** that warns at SessionStart until `core-guardrails` is present, then self-deactivates. Bounded, temporary, single-purpose. Accepts a small Principle-1 break in exchange for closing the day-1 silent-failure window. |
| D-3 | When does the warning fire? | **SessionStart** only. Pre-commit is the wrong layer (`.githooks/` is git's, not the plugin layer's). |
| D-4 | What format does `--marketplace=<source>` take? | **Git URL OR local path placeholder**. Detect by prefix: starts with `http`/`git@`/`/`/`./` → passthrough. Skip `org/repo` shorthand (platform-ambiguous). Default to omitting the block entirely when the flag is absent (no surprise side-effects). |

## What ships in this PR

Concrete file changes:

### Scaffolder

- `scripts/sn_init.py`:
  - `build_parser()` gains `--marketplace=<source>` flag (`dest="marketplace_source"`, `default=None`).
  - New `_render_marketplace(args, project_name)` function modelled on `_render_profile()` (sn_init.py:557-583). Walks `skills/sn-setup/templates/marketplace-consumer/default/` and emits files into the scaffold; renames the `claude/` subtree prefix → `.claude/` exactly like `_render_base` / `_render_profile` already do; substitutes `{marketplace_source}` token.
  - `_plan_new_files()` calls `_render_marketplace(...)` only when `args.marketplace_source` is set, slotted between profile/framework rendering and `_render_claude()`.
  - Inside `_render_claude()` (sn_init.py:608-685), after the canonical `settings.json` is read, if `args.marketplace_source` is set, `_inject_marketplace_into_settings(data, args)` adds the `installed_plugins` block + the SessionStart bootstrap hook entry. The plugin list is composed in code from `MARKETPLACE_MANDATORY_PLUGINS` + `MARKETPLACE_PROFILE_PLUGINS[args.profile]` + `MARKETPLACE_REGULATED_PLUGINS` (the last when a regulated policy is in the planned set per `_resolve_planned_policy_set`). The template `settings.patch.json` file in the subtree is REFERENCE ONLY — it documents the shape of the injection for future maintainers but is not read by the renderer.

### Template subtree

- `skills/sn-setup/templates/marketplace-consumer/default/.claude-plugin/marketplace.json` — minimal consumer manifest with placeholder `source` set from substitution. The schema field is a placeholder — the canonical consumer-side marketplace JSON schema lives in the platform marketplace repo shipped by B3.1 and will be wired in once that lands.
- `skills/sn-setup/templates/marketplace-consumer/default/settings.patch.json` — `{"installed_plugins": [{"name": "core-workflow", ...}, {"name": "core-guardrails", ...}]}`. REFERENCE ONLY (the actual merge is derived from constants in `sn_init.py`). Profile-specific opt-ins (`contracts-sync`, `bff-patterns`, `compliance-pack`) are added at render time based on `args.profile` and on whether `_resolve_planned_policy_set(args)` intersects `REGULATED_POLICY_SLUGS` (i.e. `--policies=memory-regulated` or `--policies=pdpa-compliance` is present).
- `skills/sn-setup/templates/marketplace-consumer/default/claude/hooks/marketplace-bootstrap.sh` — single bash script. On run: `if [ ! -d ".claude/plugins/core-guardrails" ]; then echo "⚠ Mandatory plugins missing. Run: /plugin install core-workflow core-guardrails (marketplace: {marketplace_source})"; fi`. Marked executable. SessionStart hook entry added to `settings.json` via the patch above.

### Tests

`tests/test_sn_init.py` gains:

- `test_marketplace_flag_emits_consumer_files` — scaffold with `--marketplace=./` → `.claude-plugin/marketplace.json` + `.claude/hooks/marketplace-bootstrap.sh` exist; bootstrap hook is executable.
- `test_marketplace_flag_writes_installed_plugins` — scaffold with `--marketplace=./` → `.claude/settings.json::installed_plugins` is a list of length ≥ 2, containing entries named `core-workflow` + `core-guardrails`.
- `test_marketplace_flag_url_form_accepted` — scaffold with `--marketplace=https://github.com/org/marketplace.git` → `marketplace.json` records the URL verbatim.
- `test_marketplace_omitted_leaves_no_block` — scaffold without `--marketplace=` → no `installed_plugins` key in `settings.json`, no `.claude-plugin/` dir, no `marketplace-bootstrap.sh`.
- `test_marketplace_bff_adds_contracts_sync` — `--marketplace=./ --profile=bff` → `installed_plugins` also lists `contracts-sync` + `bff-patterns`.
- `test_marketplace_regulated_adds_compliance_pack` — `--marketplace=./ --policies=memory-regulated,repository-ecosystem` → `installed_plugins` also lists `compliance-pack`. (Regulated is signaled by the planned policy set intersecting `REGULATED_POLICY_SLUGS`, not by a dedicated CLI flag.)
- `test_marketplace_bootstrap_hook_registered_at_session_start` — `settings["hooks"]["SessionStart"]` includes an entry pointing at `.claude/hooks/marketplace-bootstrap.sh`.

`_expected_top_level` helper extended if new top-level paths appear (they don't here — `.claude-plugin/` is new but lives below project root).

### Backlog + CHANGELOG

- `docs/backlog.md`: B2.3 marked `[x]` with merge SHA.
- `CHANGELOG.md`: `[Unreleased] > Added` entry.

## What does NOT ship in this PR

- **The catalog itself.** Catalog manifest + human doc both live inside the `core-workflow` + `core-guardrails` plugins. Those plugins live in the platform marketplace repo (B3.1) which does not yet exist.
- **Pinning / version checks** — pinning policy is documented in `GOVERNANCE.md` (B2.4) and `SECURITY.md` (B2.4) but the CI-level pin verification is **B3.2**.
- **Marketplace divergence warning in `workspace add`** — `B2.2-FU-4`. This is unblocked by B2.3, separate PR.
- **Anything in the platform marketplace repo** — B3.1.
- **org/repo shorthand format** — explicitly rejected (platform-ambiguous).

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-1 | `sn-setup new demo --no-git --marketplace=./` produces a scaffold containing `.claude-plugin/marketplace.json`, `.claude/settings.json` with `installed_plugins` key, and `.claude/hooks/marketplace-bootstrap.sh` (executable). |
| AC-2 | `installed_plugins` always contains `core-workflow` + `core-guardrails`. `--profile=bff` adds `contracts-sync` + `bff-patterns`. A regulated policy in the planned set (`--policies=memory-regulated` or `--policies=pdpa-compliance`) adds `compliance-pack`. |
| AC-3 | `marketplace-bootstrap.sh` self-deactivates: when `.claude/plugins/core-guardrails/` exists, the hook exits silently. |
| AC-4 | The SessionStart hook entry in `settings.json` references `.claude/hooks/marketplace-bootstrap.sh` and does NOT clash with the existing audit SessionStart entry (both fire). |
| AC-5 | `--marketplace=` accepts both a git URL (`https://github.com/...`, `git@github.com:...`) and a path (`./`, `/abs/path`). org/repo shorthand is rejected with a clear error message. |
| AC-6 | Omitting `--marketplace=` leaves the scaffold unchanged — no new files, no new settings keys, no new hooks. |
| AC-7 | All existing tests pass (297 passed + 1 skipped baseline); new tests pass; net total ≥ 304 passed + 1 skipped. |
| AC-8 | B2.3 marked `[x]` in `docs/backlog.md` with the merge SHA. CHANGELOG `[Unreleased] > Added` entry. |
| AC-9 | Single sonnet reviewer at end of branch; findings (if any) bundled into one fix commit. |
| AC-10 | PR merges cleanly; CI green on Python 3.11/3.12/3.13. |

## Out of scope (carved follow-ups)

- **B2.3-FU-1** — Multiple-marketplace support. Today `--marketplace=` is a single source. A future PR may accept comma-separated list when a service wants both org-internal and a vendor-shared marketplace.
- **B2.3-FU-2** — Plugin version pinning syntax. `installed_plugins` entries today are name-only stubs (e.g. `{"name": "core-workflow"}`); pin syntax (`"version": "1.2.3"` or `"version_constraint": "^1"`) waits for B3.1 catalog + B3.2 CI verification.
- **B2.3-FU-3** — Auto-install on first `claude` session in the repo. The brainstorm explicitly chose manual user install; the bootstrap hook is warn-only, never invokes `/plugin install`.

## Implementation plan (light)

Branch: `feat/marketplace-consumer` from `main`.

1. Vault req+design+plan (this file) committed + pushed. **← first step.**
2. `requirements/README.md` index updated with row.
3. Branch created.
4. Spec mirror commit: copy this doc → `docs/superpowers/specs/2026-06-27-marketplace-consumer-design.md`.
5. Author template subtree under `skills/sn-setup/templates/marketplace-consumer/default/`.
6. Implement `_render_marketplace()` + flag wiring in `scripts/sn_init.py`.
7. Implement `settings.json` `installed_plugins` injection.
8. Author tests in `tests/test_sn_init.py`.
9. Run full suite, fix anything red.
10. Mark backlog `[x]`, append CHANGELOG.
11. Final sonnet reviewer pass; bundle findings into one fix commit if needed.
12. Push + open PR + watch CI green.
13. Merge on user "ok".
14. Bump `shipped_in` frontmatter on this doc; append Batch 31 entry to `implementation-log.md`; push vault.

## Execution mode

Direct write by main thread (matches the workflow that worked through B2.4 / B2.4b / B2.4c). No SDD subagents. Single sonnet reviewer at end. Rationale: scope is narrow (~1 new template subtree + ~60 LOC in `sn_init.py` + ~80 LOC of tests), main-thread context budget is sufficient.

## Related

- [[layer4-governance-docs]] — REQ-DOCS-002. B2.4's `ARCHITECTURE.md` + `GOVERNANCE.md` + `SECURITY.md` already document B2.3's `installed_plugins` block; this PR honors that contract.
- [[workspace-layer]] — REQ-WS-001. `B2.2-FU-4` (marketplace divergence warning in `workspace add`) is unblocked by this PR.
- [[../design/plugin-layout]] — plugin layout reference.
- [[../design/policy-catalog]] — settings-merge pattern reused (simple-array merge, no `policy` marker).
- `B3.1` — platform marketplace stand-up. Ships the `core-workflow` + `core-guardrails` plugins this PR points at.
- `B3.2` — CI pin verification.
- `B2.2-FU-4` — marketplace divergence warning. Tier 2, unblocked by this PR.
