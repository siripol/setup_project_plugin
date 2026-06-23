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

### B1.1 `[ ]` Repository Ecosystem table in scaffolded `CLAUDE.md`
- **Why**: design §4.3 / §5.2 — every scaffolded repo gets a small table of related services, purpose, repo URL. Identical across the org. Today's `CLAUDE.md` has no such table.
- **Where**: `skills/sn-setup/templates/managed-agent-base/CLAUDE.md` — add `## Repository Ecosystem` block with header + example row + "add your org's services here" note.
- **Scope**: doc template only, no code.
- **Estimate**: ~30 min.

### B1.2 `[ ]` Two-tier memory-policy signal (`ordinary` vs `regulated`)
- **Why**: design §7.5 — regulated services need auto-memory off + everything committed. Ordinary services keep auto-memory on. Today sn-setup makes no distinction.
- **Where**: add `regulated: false` field to `.sn-init-state.json` schema in `scripts/sn_init.py`. Add a `## Memory policy` block to scaffolded `CLAUDE.md` explaining both tiers + how to flip the bit.
- **Scope**: 1 schema field + 1 doc block + 1 flag (`--regulated`).
- **Estimate**: 2 h.

### B1.3 `[ ]` `docs/PROMOTION.md` — local-skill → org-marketplace path
- **Why**: design §6.5 — explicit promotion workflow (local skill proves useful → review → publish to platform marketplace → others install).
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/PROMOTION.md` (new file in scaffold template). Same doc also added to this plugin's own `docs/`.
- **Scope**: 1-page doc with a checklist + PR template snippet.
- **Estimate**: ~1 h.

### B1.4 `[ ]` `docs/PREREQUISITES.md` — minimum tool versions
- **Why**: design §9.2 / §12.1 — every scaffolded service ships a table of required CLI / runtime / tool minimums for reproducibility.
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/PREREQUISITES.md`. Cover Claude Code version, lang runtime per `--lang=`, `ant` CLI, `node`, `git`.
- **Scope**: doc table.
- **Estimate**: ~1 h.

### B1.5 `[ ]` Operationalize load-on-demand context split (`.claude/docs/` vs `.claude/rules/`)
- **Why**: design Principle 3 / §3.3 / §5.3 — keep `CLAUDE.md` minimal; push detail into `.claude/docs/` (skill-loaded on demand) + `.claude/rules/` (always-on but short). sn-setup's scaffold already has `.claude/` but the distinction isn't enforced or documented.
- **Where**: add `templates/claude/docs/ARCHITECTURE.md` stub + `templates/claude/rules/README.md` explaining the split. Update scaffolded `CLAUDE.md` with a 1-paragraph context-policy block.
- **Scope**: 2 new template files + 1 paragraph in `CLAUDE.md`.
- **Estimate**: ~2 h.

### B1.6 `[ ]` `docs/GOVERNANCE-SERVICE-LEVEL.md`
- **Why**: design §7.4 / §9 — service teams treat `.claude/` like code: who owns edits, how to promote local skills, how to signal regulated-data status. Today: no template.
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/GOVERNANCE-SERVICE-LEVEL.md`. Concrete playbook, not philosophy.
- **Scope**: 1-page doc.
- **Estimate**: ~1 h.

### B1.7 `[ ]` Audit hooks against design's mandatory controls
- **Why**: design §7.2 + Principle 1 — `core-guardrails` controls (sensitive-path deny rules, network-command restriction, marketplace allow-list, no automatic permission bypass, supply-chain scan, in-session security review, audit log) must all be present and unmissable. Need to verify the current `settings.json` + hooks scaffold covers each.
- **Where**: audit `skills/sn-setup/templates/claude/settings.json`, `templates/claude/hooks/*`, `templates/managed-agent-base/scripts/safety.py`. Produce a checklist matrix + close any gaps with new hook entries.
- **Scope**: read-and-tick exercise + small hook additions if gaps surface.
- **Estimate**: ~3 h for audit; gap-fix scope TBD.

---

## Tier 2 — next-sprint (1–3 days each)

### B2.1 `[~]` Profile overlays (`--profile=microservice|bff|frontend`) — branch `feat/profiles`
- **Why**: design §6.6 / §9.5 — repos have distinct shapes (backend microservice, BFF aggregator, frontend) but share the same foundation. Originally scoped as BFF-only; extended to cover microservice + frontend at the same time so the multi-profile concept lands as one coherent change.
- **What shipped on this branch**:
  - New `--profile=microservice|bff|frontend` flag (default `microservice`; alias `service`→`microservice`).
  - New `--framework=next|vite` sub-flag (frontend only; default `next`).
  - Overlay subtrees: `templates/profile/{microservice,bff,frontend}/` and `templates/framework/{next,vite}/`.
  - Lang × profile matrix validation in `scripts/sn_init.py` — bad combos fail fast.
  - State records `profile` + `framework`; `--upgrade` reads them.
  - Per-profile docs (PROFILE / API / OBSERVABILITY for microservice; PROFILE / BFF-INTEGRATION / DOWNSTREAMS for bff; PROFILE / DESIGN / ACCESSIBILITY / BROWSER-MATRIX for frontend) and per-framework docs (FRAMEWORK.md).
- **Follow-ups (deferred, not blocking 1.x)**:
  - **B2.1a** Repository Ecosystem table per profile (foreground downstreams for BFF, foreground BFF for frontend). Depends on **B1.1** landing first.
  - **B2.1b** Plugin install entries — wire `bff-patterns` + `contracts-sync` for BFF, `a11y-checker` for frontend. Depends on **B2.3** marketplace consumer.
  - **B2.1c** Per-profile subagents — `bff-integration-reviewer`, `a11y-auditor`. Lives under `templates/profile/<profile>/.claude/agents/`.

### B2.2 `[ ]` Optional workspace layer (Layer 3) — `--workspace`
- **Why**: design §4 / §9.6 / §12.2 step 4 — optional cross-service virtual-monorepo for orgs past a certain scale. Stays gitignored; lives sibling to repos.
- **Where**: new `--workspace` flag in `scripts/sn_init.py`. When set, scaffold sibling `<name>-workspace/` with `WORKSPACE.md` (registry template), `CLAUDE.md` (ecosystem table), `MIGRATION.md` (adoption guide), `scripts/{launch,sync,status}` (bash stubs).
- **New template subtree**: `skills/sn-setup/templates/workspace/`.
- **Estimate**: 2 days (scaffold logic, bash scripts, registry JSON format).

### B2.3 `[ ]` Internal plugin-marketplace consumer model (`--marketplace=<source>`)
- **Why**: design §6.1 / §6.2 / §9.3 — Layer 1 requires `core-workflow` + `core-guardrails` to be **installed** from an internal marketplace, not template-baked. Without the consumer side wired, the platform layer can't exist later.
- **Where**: new flag `--marketplace=<source>` in `scripts/sn_init.py`. When set: generate `.claude-plugin/marketplace.json` (consumer-side; references the org's marketplace source) + `.claude/settings.json` `installed_plugins` block listing the mandatory + chosen optional packs.
- **New template subtree**: `skills/sn-setup/templates/marketplace-consumer/`.
- **Estimate**: 2 days (scaffold logic + marketplace.json schema + docs).
- **Note**: doesn't require the platform-marketplace repo to exist — consumer can reference a `source: "./"` placeholder until the platform lands.

### B2.4 `[ ]` Layer-4 governance docs — `ARCHITECTURE.md`, `REPO-STRATEGY.md`, `SECURITY.md`, `GOVERNANCE.md`
- **Why**: design §9.2 — every scaffolded service ships these as org-facing artifacts. Today they're outlined in the design doc but not scaffolded.
- **Where**: `skills/sn-setup/templates/managed-agent-base/docs/{ARCHITECTURE,REPO-STRATEGY,SECURITY,GOVERNANCE}.md`. Real content per the design doc, not outlines.
- **Estimate**: 1 day per doc → 3–4 days bundled.

### B2.5 `[ ]` PDPA compliance pack (`--compliance=pdpa|none`)
- **Why**: design §8 — opt-in `compliance-pack` for PDPA. Provides hooks + guidance + audit-log strictness for services handling personal data.
- **Where**: new `--compliance=pdpa|none` flag (default `none`). When `pdpa`: scaffold `.claude/rules/compliance-pdpa.md` (developer-facing guidance), wire a `claude-security-guidance.md` reference into hooks, force-flip `regulated: true` in `.sn-init-state.json` (per B1.2), enforce committed-memory tier.
- **New template subtree**: `skills/sn-setup/templates/compliance/pdpa/`.
- **Estimate**: 1–2 days (rules content + hook wiring + audit-log strictness).

---

## Tier 3 — broader rethink (> 3 days)

### B3.1 `[ ]` Stand up the internal plugin marketplace (Layer 1, full)
- **Why**: design §6.1 — `core-workflow` + `core-guardrails` + opt-in packs all live in a separate platform repo, installable via `/plugin install` from an internal marketplace source. Today sn-setup template-bakes the equivalent content into the scaffold.
- **What's needed**: separate `platform-marketplace/` repo (or subdir) holding the canonical skills + agents + hooks as installable plugins. Release pipeline. Versioning + pinning policy. Promotion workflow (B1.3 documents this; B3.1 implements the receiving end).
- **Implies subsumes**: B2.3 (consumer side), B2.5 (pdpa pack as a marketplace plugin), B2.4 (governance docs as marketplace assets).
- **Estimate**: weeks, not days. Architectural shift.

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

## How to pick up an item

1. Branch `feat/<slug>` (or `chore/`, `fix/`, `docs/`).
2. Update `[ ]` → `[~]` in this file, link the branch.
3. Implement + tests + scaffold-side template copy as needed.
4. PR → CHANGELOG `[Unreleased]` entry → merge.
5. Mark `[x]` here with the merge SHA + tag (if released).

If you abandon an item, set `[skip]` and write a one-line reason — future-you wants the reason, not just the absence.
