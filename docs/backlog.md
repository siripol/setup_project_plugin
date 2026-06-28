# Backlog

Living list of work the plugin should pick up. Items here are scoped but not yet started. Once started, they move to a feature branch + PR + CHANGELOG `[Unreleased]` entry.

## Status legend

- `[ ]` = not started
- `[~]` = in progress (branch exists, PR open or in-flight)
- `[x]` = shipped (link to PR + tag)
- `[skip]` = considered, intentionally not doing — keep the reason

## Source

Most current items derive from the **microservices template-family design doc** (local, gitignored under `temp/__claude__microservices-template-design_*.md`). The gap analysis comparing that design vs the current sn-setup implementation is mirrored to the vault at `global/tech/setup_project_plugin/microservices-template-gap-analysis.md`. Read either before picking up an item.

---

## Tier 1 — same-week (≤ 1 day each)

### B1.1 `[x]` Repository Ecosystem table — shipped as the `repository-ecosystem` policy in **PR1 policy catalog** (`docs/superpowers/specs/2026-06-24-policy-catalog-design.md`).

### B1.2 `[x]` Two-tier memory-policy signal — shipped as `memory-ordinary` + `memory-regulated` policies (exclusive group `memory-tier`) in **PR1 policy catalog**.

### NEW B1.8 `[~]` Policy catalog (PR1) — branch `feat/policy-catalog`
- **Why**: composable, versioned policies (spec §0).
- **Where**: `scripts/policy_*.py`, `skills/sn-setup/templates/policies/<slug>/`, `skills/sn-setup/templates/profile/<P>/default_policies.yaml`.
- **Scope**: 9 day-one policies, `sn-setup policy` + `sn-setup profile` CLI, lint, status, upgrade, history, profile-bundled defaults.
- **Follow-ups**: PR2 profile expansion (worker/cli/library/gateway/mcp-server); PR3 default bundles for new profiles.

### B1.9 `[x]` Command sub-tree migration — **shipped PR #19** (merge `ede959b`, 2026-06-25)
- Regrouped 16 flat `sn-X-Y.md` → 3 grouped `sn-X.md` (`sn-sprint`, `sn-req`, `sn-knowledge`).
- Retired `sn-knowledge-tech-matrix`; replaced by `sn-knowledge summarize <topic>` (pure LLM, persists to `<vault>/shared/summaries/<slug>.md`).
- Migration command: `sn-setup --upgrade --rename-commands` (idempotent, sha-checked via `OLD_FLAT_SHAS` snapshot, `--force` for user-edited).
- 238/238 tests (was 225). Spec + plan + requirements + post-merge retrospective in vault.

### B1.3 `[x]` `docs/PROMOTION.md` — **shipped feat/layer4-docs** (REQ-DOCS-001)
- **Why**: design §6.5 — explicit promotion workflow (local skill proves useful → review → publish to platform marketplace → others install).
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/PROMOTION.md` (new file in scaffold template). Same doc also added to this plugin's own `docs/`.
- **Scope**: 1-page doc with a checklist + PR template snippet.
- **Estimate**: ~1 h.

### B1.4 `[x]` `docs/PREREQUISITES.md` — **shipped feat/layer4-docs** (REQ-DOCS-001)
- **Why**: design §9.2 / §12.1 — every scaffolded service ships a table of required CLI / runtime / tool minimums for reproducibility.
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/PREREQUISITES.md`. Cover Claude Code version, lang runtime per `--lang=`, `ant` CLI, `node`, `git`.
- **Scope**: doc table.
- **Estimate**: ~1 h.

### B1.5 `[x]` Load-on-demand context split — **shipped feat/tier1-finish** (REQ-CTX-001)
- Adds `templates/claude/docs/{README,ARCHITECTURE}.md` + `templates/claude/rules/README.md` + `## Context policy` paragraph in scaffolded `CLAUDE.md`.

### B1.6 `[x]` `docs/GOVERNANCE-SERVICE-LEVEL.md` — **shipped feat/layer4-docs** (REQ-DOCS-001)
- **Why**: design §7.4 / §9 — service teams treat `.claude/` like code: who owns edits, how to promote local skills, how to signal regulated-data status. Today: no template.
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/GOVERNANCE-SERVICE-LEVEL.md`. Concrete playbook, not philosophy.
- **Scope**: 1-page doc.
- **Estimate**: ~1 h.

### B1.7 `[x]` Mandatory-controls hook audit — **shipped feat/tier1-finish** (REQ-SEC-001)
- Audit doc at `docs/HOOK-AUDIT-2026-06-25.md`. Verdict: 3 PASS / 2 PARTIAL (carved) / 1 FAIL (fixed in PR) / 1 N-A.
- In-scope fix: sensitive-path deny patterns added to `templates/claude/settings.json` (closes control 1).
- Carved follow-ups: **B1.7a** CI guard against `--dangerously-skip-permissions`; **B1.7b** make `security-auditor` default for regulated profiles.

### B1.7a `[x]` CI guard against `--dangerously-skip-permissions` — **shipped feat/b1.7-followups** (REQ-SEC-002)
- Scaffolded `.github/workflows/ci.yml` greps the diff + commit messages for the flag on every push/PR; fails the job on match.
- `docs/GOVERNANCE-SERVICE-LEVEL.md` gains a `## Permission bypass — forbidden` section.

### B1.7b `[x]` `security-auditor` default for regulated profiles — **shipped feat/b1.7-followups** (REQ-SEC-003)
- `scripts/sn_init.py` resolves the planned policy set early; if `memory-regulated` or `pdpa-compliance` is present, appends `security-auditor` to `args.subagents` (honors `--subagents=none`).
- `docs/GOVERNANCE-SERVICE-LEVEL.md` documents the auto-add.

---

## Tier 2 — next-sprint (1–3 days each)

### B2.1 `[x]` Profile overlays (`--profile=microservice|bff|frontend`) — **shipped PR #17** (merge `e07a713`, 2026-06-23)
- **Why**: design §6.6 / §9.5 — repos have distinct shapes (backend microservice, BFF aggregator, frontend) but share the same foundation. Originally scoped as BFF-only; extended to cover microservice + frontend at the same time so the multi-profile concept lands as one coherent change.
- **What shipped on this branch**:
  - New `--profile=microservice|bff|frontend` flag (default `microservice`; alias `service`→`microservice`).
  - New `--framework=next|vite` sub-flag (frontend only; default `next`).
  - Overlay subtrees: `templates/profile/{microservice,bff,frontend}/` and `templates/framework/{next,vite}/`.
  - Lang × profile matrix validation in `scripts/sn_init.py` — bad combos fail fast.
  - State records `profile` + `framework`; `--upgrade` reads them.
  - Per-profile docs (PROFILE / API / OBSERVABILITY for microservice; PROFILE / BFF-INTEGRATION / DOWNSTREAMS for bff; PROFILE / DESIGN / ACCESSIBILITY / BROWSER-MATRIX for frontend) and per-framework docs (FRAMEWORK.md).
- **Follow-ups (deferred, not blocking 1.x)**:
  - **B2.1a** `[x]` Repository Ecosystem table per profile — **shipped feat/b2.1a-ecosystem-foregrounding** (REQ-PROF-001). `repository-ecosystem` policy doc now has 3 profile sections (microservice/BFF/frontend); version bumps to 1.1.0.
  - **B2.1b** Plugin install entries — wire `bff-patterns` + `contracts-sync` for BFF, `a11y-checker` for frontend. Depends on **B2.3** marketplace consumer.
  - **B2.1c** `[x]` Per-profile subagents — **shipped feat/b2.1c-subagents** (REQ-PROF-002). `bff-integration-reviewer.md` ships with `--profile=bff`; `a11y-auditor.md` ships with `--profile=frontend`. `_render_profile`'s rglob already copied them; no scaffold-logic change needed.

### B2.2 `[x]` Optional workspace layer (Layer 3) — `--workspace` — **Shipped** in PR for `feat/workspace-layer`.
- **Why**: design §4 / §9.6 / §12.2 step 4 — optional cross-service virtual-monorepo for orgs past a certain scale. Stays gitignored; lives sibling to repos.
- **Where**: new `--workspace` flag in `scripts/sn_init.py`. When set, scaffold sibling `<name>-workspace/` with `WORKSPACE.md` (registry template), `CLAUDE.md` (ecosystem table), `MIGRATION.md` (adoption guide), `scripts/{launch,sync,status}` (bash stubs).
- **New template subtree**: `skills/sn-setup/templates/workspace/`.
- **Estimate**: 2 days (scaffold logic, bash scripts, registry JSON format).

### B2.3 `[x]` Internal plugin-marketplace consumer model (`--marketplace=<source>`) — **shipped feat/marketplace-consumer** (REQ-MKT-001)
- Flag `--marketplace=<source>` in `scripts/sn_init.py` accepts git URL or local path; org/repo shorthand rejected (platform-ambiguous).
- New template subtree `skills/sn-setup/templates/marketplace-consumer/default/` ships `.claude-plugin/marketplace.json` (consumer manifest) + `claude/hooks/marketplace-bootstrap.sh` (SessionStart warn-then-self-deactivate) + `settings.patch.json` (documentation only — actual merge happens inline in `_inject_marketplace_into_settings`).
- `installed_plugins` block in `.claude/settings.json` seeded with `core-workflow` + `core-guardrails` (mandatory) + per-profile opt-ins (`contracts-sync`, `bff-patterns` for bff) + `compliance-pack` when regulated policy planned.
- Catalog itself (which plugins exist + semver pins) lives inside `core-workflow` (human doc) and `core-guardrails` (machine manifest + missing-plugin check hook). Both packs ship in **B3.1**; this PR is consumer wiring only.
- Bootstrap hook self-deactivates once `.claude/plugins/core-guardrails/` exists on disk.
- 12 new tests; baseline 297 → 309 passed + 1 skipped.
- Vault: [[../obsidian_sharedknowledge/projects/setup_project_plugin/requirements/marketplace-consumer.md]] (REQ-MKT-001).
- Carved follow-ups (Tier 2/3): `B2.3-FU-1` multiple-marketplace support, `B2.3-FU-2` plugin version pinning syntax (waits on B3.1+B3.2), `B2.3-FU-3` auto-install on first session (explicitly out of scope — bootstrap is warn-only).
- Unblocks `B2.2-FU-4` (marketplace divergence warning in `workspace add`).

### B2.4 `[x]` Layer-4 governance docs — `ARCHITECTURE.md`, `REPO-STRATEGY.md`, `SECURITY.md`, `GOVERNANCE.md` — **shipped feat/layer4-governance-docs** (REQ-DOCS-002)
- 4 docs land under `skills/sn-setup/templates/managed-agent-base/docs/`. Each ~120-180 lines real prose per design §3 / §4 / §7 / §9.2.
- `GOVERNANCE.md` (org-wide) and `GOVERNANCE-SERVICE-LEVEL.md` (per-team) each cross-reference the other in their opening paragraphs to disambiguate.
- `SECURITY.md` cross-references `docs/compliance/*` shipped by B2.5 PDPA pack.
- Tests: `tests/test_sn_init.py::_expected_top_level` extended with the 4 new paths.
- Vault: [[../obsidian_sharedknowledge/projects/setup_project_plugin/requirements/layer4-governance-docs.md]] (REQ-DOCS-002).

### B2.4b `[x]` Service/BFF profile overlay fill — **shipped feat/profile-overlay-fill** (REQ-PROF-003)
- 4 universal foundation files in `managed-agent-base/`: `claude-security-guidance.md` + `claude/{docs,skills,agents}/README.md`.
- 4 microservice files in `profile/microservice/claude/`: `docs/microservice-conventions.md` + `skills/example/{SKILL,HOWTO}.md` + `agents/microservice-reviewer.md`.
- 3 bff files in `profile/bff/claude/`: `docs/bff-aggregation.md` + `skills/example-bff/{SKILL,HOWTO}.md`. (bff already had `claude/agents/bff-integration-reviewer.md` from B2.1c.)
- `scripts/sn_init.py::_render_base` extended with the `claude/` → `.claude/` rename matching `_render_profile`'s pattern from B2.1c.
- Vault: [[../obsidian_sharedknowledge/projects/setup_project_plugin/requirements/profile-overlay-fill.md]] (REQ-PROF-003).

### B2.4c `[x]` Frontend profile overlay fill — **shipped feat/frontend-overlay-fill** (REQ-PROF-004)
- 1 conventions doc + 1 skill (SKILL + HOWTO) under `profile/frontend/claude/`:
  - `docs/frontend-conventions.md` (~150 lines) — framework-neutral conventions covering component composition, accessibility (high-level), state management discipline, performance budgets, testing strategies.
  - `skills/example-frontend/{SKILL,HOWTO}.md` — `audit-component-coupling` skill; architecture-focused (prop drilling, context usage, state hoisting, fanout). Distinct from `a11y-auditor` agent (B2.1c, WCAG-focused).
- Framework-neutral by locked design decision; framework-specific guidance stays in `framework/<F>/docs/FRAMEWORK.md`.
- Frontend already had `claude/agents/a11y-auditor.md` from B2.1c.
- Vault: [[../obsidian_sharedknowledge/projects/setup_project_plugin/requirements/frontend-overlay-fill.md]] (REQ-PROF-004).

### B2.5 `[x]` PDPA compliance pack (full enforcement) — **shipped feat/pdpa-pack** (REQ-PDPA-001)
- pdpa-compliance@1.0.0 (signal-only) → 2.0.0 (full enforcement).
- Hook A `pdpa-data-handler-scan.sh` (PreToolUse on Write|Edit; PII regex over 6 patterns; skip-on-allowlist-match).
- Hook B `pdpa-retention-check.sh` (PreToolUse on Write to `data/`; sidecar verification).
- `sn-setup policy pdpa allowlist <list|add|remove|explain>` sub-sub-command (`scripts/policy_pdpa.py`).
- Scaffolded `data/{subjects,consents,exports}/` + 4 doc templates under `docs/compliance/`.

### B2.5a `[ ]` Retention review-staleness enforcement
- Hook B today only validates `last_reviewed:` shape (`YYYY-MM-DD`). Enforce ≤ 365 days.
- **Where**: `pdpa-retention-check.sh`.
- **Estimate**: ~1 h.

### B2.5b `[ ]` Consent-check hook
- New `pdpa-consent-check.sh` (PreToolUse on `data/subjects/<id>/**`) verifying `data/consents/<id>.yaml` exists with valid `purposes` + `expires_at`.
- **Estimate**: ~2 h.

### B2.5c `[ ]` Audit-log breach detection rules
- Cross-policy integration with `audit-log-strict` to flag exfiltration patterns (sudden large Read on `data/**`).
- **Estimate**: ~1 day.

### B2.5d `[ ]` CI auto-rotate sidecar `last_reviewed:` on PR approval
- GitHub Actions step that bumps the date when a reviewer approves a sidecar.
- **Estimate**: ~2 h.

### B2.5e `[ ]` Luhn validation for PAN regex
- Today: pattern catches PAN shapes. Add Luhn check to reduce false positives.
- **Where**: `pdpa-data-handler-scan.sh`.
- **Estimate**: ~1 h.

---

## Tier 3 — broader rethink (> 3 days)

### B3.1 `[~]` Stand up the internal plugin marketplace (Layer 1, full) — in-progress on `feat/marketplace-producer-scaffold` (Phase 1 of 7); REQ-MKT-002
- **Why**: design §6.1 — `core-workflow` + `core-guardrails` + opt-in packs all live in a separate platform repo, installable via `/plugin install` from an internal marketplace source. Today sn-setup template-bakes the equivalent content into the scaffold.
- **What's needed**: separate `platform-marketplace/` repo (or subdir) holding the canonical skills + agents + hooks as installable plugins. Release pipeline. Versioning + pinning policy. Promotion workflow (B1.3 documents this; B3.1 implements the receiving end).
- **Implies subsumes**: B2.3 (consumer side), B2.5 (pdpa pack as a marketplace plugin), B2.4 (governance docs as marketplace assets).
- **Estimate**: weeks, not days. Architectural shift.
- **Approach**: subdir monorepo (ADR-MKT-001). 7-phase / 9-PR roadmap per REQ-MKT-002 (vault). Phase 0 vault docs landed `5ed18f5` (vault). Phase 1 lands `platform-marketplace/` scaffolding + catalog JSON Schema + validator + 6 tests + extended `ci.yml` (merged `8bd7f24` PR #32). Phase 2 (this PR) lifts `core-guardrails` first — 9 hooks + authoritative settings.patch.json + 2 threat-model rules + 7 tests + catalog entry. Phase 3 lifts `core-workflow` next.

### B3.2 `[ ]` Org-wide enforcement of advice-vs-enforcement split (Principle 1)
- **Why**: design Principle 1 + §6.2 — `core-guardrails` is the enforcement plugin and **must** be installed in every service; `core-workflow` is advisory and optional-detailed. Today both live as templated content inside the scaffold, so they're trivially editable / removable per-repo.
- **What's needed**: depends on B3.1 (marketplace) being in place. Once marketplace exists, mark `core-guardrails` as mandatory (install pinned, removal blocked at hook level). Add a verification step in `/sn-verify` that fails if `core-guardrails` isn't installed.
- **Estimate**: depends on B3.1.

### B3.3 `[ ]` Plugin versioning + pinning + opt-in packs catalog
- **Why**: design §7.3 — plugins declare versions, consumers pin them, updates are not automatic. Need a catalog + version policy.
- **What's needed**: depends on B3.1 (marketplace) being in place. Wire pinning into `.claude/settings.json` `installed_plugins` block; document update procedure in `docs/GOVERNANCE.md` (B2.4).
- **Estimate**: depends on B3.1.

---

## Top 3 recommended shipping order (next week)

1. **B1.1 + B1.2** (~3 h total) — Repository Ecosystem table + memory-policy signal. Force-multipliers; tiny code.
2. **B2.1** (1–2 days) — BFF template profile. Design-mandated; clean extension; sets multi-profile precedent.
3. **B2.2** (2 days) — Optional workspace layer. Off-by-default, light to build, valuable when teams scale.

The biggest single architectural gap (B3.1 marketplace) feeds every later Tier-2 item. Shipping B1.* + Tier-2 first prepares the ground without locking in a marketplace shape prematurely.

---

## B2.2 carved follow-ups

| ID | Title | Tier | Trigger to revisit |
|---|---|---|---|
| B2.2-FU-1 | Workspace upgrade command (`sn-setup workspace upgrade`) | 3 | Template format breaks back-compat |
| B2.2-FU-2 | Workspace slash commands (`/sn-workspace-status`, etc.) | 3 | Slash-command UX becomes dominant |
| B2.2-FU-3 | Parallel exec for `status` / `sync` | 3 | User reports >5s wall-clock with ≥10 services |
| B2.2-FU-4 | Marketplace divergence warning in `workspace add` `[x]` | 2 | Shipped `feat/marketplace-divergence-warning` (REQ-WS-002) |
| B2.2-FU-5 | `sn-setup workspace doctor` — registry / gitignore drift detector | 3 | Drift complaints surface |
| B2.2-FU-6 | `workspace-coordinator` cross-repo refactor subagent | 3 | Real cross-repo refactor use case arrives |

---

## B2.3 carved follow-ups

| ID | Title | Tier | Trigger to revisit |
|---|---|---|---|
| B2.3-FU-1 | Multi-marketplace support (comma-separated `--marketplace=A,B`) | 3 | Real demand for vendor-shared marketplace alongside org-internal |
| B2.3-FU-2 | Plugin version pinning syntax in `installed_plugins` entries | 2 | B3.1 catalog + B3.2 CI pin verification land |
| B2.3-FU-3 | Auto-install on first session (replace warn-only hook) | 3 | Explicitly out — manual install is the design choice; reopen only if friction reports dominate |

---

## How to pick up an item

1. Branch `feat/<slug>` (or `chore/`, `fix/`, `docs/`).
2. Update `[ ]` → `[~]` in this file, link the branch.
3. Implement + tests + scaffold-side template copy as needed.
4. PR → CHANGELOG `[Unreleased]` entry → merge.
5. Mark `[x]` here with the merge SHA + tag (if released).

If you abandon an item, set `[skip]` and write a one-line reason — future-you wants the reason, not just the absence.
