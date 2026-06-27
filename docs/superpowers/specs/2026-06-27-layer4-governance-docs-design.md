---
topic: layer4-governance-docs-requirements
bucket: projects
origin_project: setup_project_plugin
origin_req: REQ-DOCS-002
first_seen: 2026-06-27
last_updated: 2026-06-27
tags: [knowledge, requirements, docs, scaffold-template, layer4, governance, setup_project_plugin]
---

# Requirements — Layer 4 Governance Docs (B2.4)

REQ-DOCS-002. Ships the **remaining four Layer 4 governance docs** carved out of REQ-DOCS-001 (see [[layer4-docs]]'s out-of-scope section). Bundles backlog item **B2.4** only. Light workflow: one combined requirements + light design + implementation plan note (this file) + one PR.

## Goal

Ship four governance / architecture template docs into every scaffolded project's `docs/` tree so service teams inherit org-facing artifacts:

1. **ARCHITECTURE.md** — the layered architecture and how the pieces interact.
2. **REPO-STRATEGY.md** — polyrepo rationale, the optional workspace, and cross-repo awareness.
3. **GOVERNANCE.md** — org-wide ownership, plugin versioning + pinning policy, the two-tier memory policy, the promotion path, the position on tool-neutral context files, and the explicit out-of-scope list.
4. **SECURITY.md** — baseline controls, reasoning from real incident classes, pinning, and the update process.

Source: microservices template-family design doc (local-only at `temp/__claude__microservices-template-design_20260623133500.md`) — §3 (Solution Architecture), §4 (Repository Strategy), §7 (Security and Governance), §9.2 (file-by-file spec), with pointers to §6.3 (opt-in packs), §7.3 (plugin versioning), §7.5 (two-tier memory), §8 (PDPA).

## Files to ship

All under `skills/sn-setup/templates/managed-agent-base/docs/`. The render walk in `scripts/sn_init.py::_render_base` copies the entire tree into every new scaffold without filter changes — no scaffolder code edits needed.

### `ARCHITECTURE.md` (~150 lines, design §3 + §9.2)

Concrete tour of the layered architecture for someone reading the repo for the first time:

- **Layer 1 (Platform).** Internal plugin marketplace (advisory + enforcement split). Mandatory plugins (`core-workflow`, `core-guardrails`) + opt-in packs (`testing-standards`, `bff-patterns`, `compliance-pack`, etc.). Why marketplace, not template-baked: pinning, versioning, rollback.
- **Layer 2 (Service repos).** What ships in this repo: `CLAUDE.md` + `.claude/` tree + `docs/` + `scripts/`. Profile overlay model (`--profile=microservice|bff|frontend`). Reference to [[../design/profile-overlays]].
- **Layer 3 (Optional workspace).** Virtual-monorepo aggregator, gitignored sibling. Reference to [[../design/workspace-layer]] (shipped B2.2).
- **Layer 4 (Governance).** This doc, plus `GOVERNANCE.md` (org policy), `GOVERNANCE-SERVICE-LEVEL.md` (this team's playbook), `SECURITY.md`, `REPO-STRATEGY.md`, `PREREQUISITES.md`, `PROMOTION.md`.
- **How the layers interact.** Service repos install plugins from Layer 1; reference Layer 4 docs for org context; opt into Layer 3 workspace when polyrepo coordination gets painful.
- **What this doc is NOT.** Not the full design doc (lives at `temp/__claude__microservices-template-design...md` — local-only). Not service-specific architecture (that goes in this repo's own `docs/` outside `managed-agent-base/`).

### `REPO-STRATEGY.md` (~120 lines, design §4 + §9.4-9.6)

Polyrepo-by-default rationale + workspace escape valve:

- **One service = one repo.** Why polyrepo wins for independent services: own CI, own release cadence, own CODEOWNERS, own deploy. Conway's law alignment.
- **Shared foundation, not shared code.** `managed-agent-base/` is the template-time foundation; runtime sharing is via Layer 1 marketplace plugins, not git submodules or symlinks.
- **Profile-driven divergence.** `--profile=microservice` vs `--profile=bff` produce different overlays sharing the foundation. Reference to [[../design/profile-overlays]].
- **Cross-repo awareness.** Each scaffold's `CLAUDE.md` has a Repository Ecosystem table per the foregrounding policy in [[../design/policy-catalog]] (`repository-ecosystem` policy). Workspace amplifies this when adopted.
- **When to adopt the workspace (Layer 3).** Triggers: >3 services, repeated `git status` across siblings, cross-repo refactor. Reference to [[../design/workspace-layer]]'s adoption section.
- **When NOT to monorepo.** Counter-arguments to a real monorepo (Bazel/Nx/Turborepo): cross-team coordination cost, release pipeline complexity, security boundaries. The workspace gives polyrepo benefits with monorepo ergonomics for editor scope + status aggregation.

### `GOVERNANCE.md` (~180 lines, design §7 + §6.3 + §7.3 + §7.5)

**Opening paragraph cross-references `GOVERNANCE-SERVICE-LEVEL.md`:** "This doc covers ORG-wide governance — policies that span every service in the org. For how THIS service team owns its own `.claude/` tree, see `GOVERNANCE-SERVICE-LEVEL.md` in this same folder."

Content:

- **Plugin versioning + pinning policy.** All Layer-1 plugins declare semver. Service repos pin in `.claude/settings.json::installed_plugins`. Update procedure: announce breaking change in marketplace changelog → 30-day grace → CODEOWNERS approves bump per service. Reference to `B3.2` (pinning unwired today).
- **Two-tier memory policy.** Ordinary tier vs regulated tier. Regulated = `--regulated` flag at scaffold OR `policy_state` includes `memory-regulated` policy. Differences: retention defaults, secret-redaction strictness, audit-log opt-out blocked. Reference to [[../design/policy-catalog]].
- **Promotion path.** Local skill / agent → org marketplace. Pointer to `PROMOTION.md` for the steps; this doc states the policy: who decides (CODEOWNERS), criteria (≥ 3 sprints, no project leakage), versioning (semver), rollback path.
- **Tool-neutral context file position.** Org policy: `CLAUDE.md` is canonical; `AGENTS.md` mirror SHOULD exist when the team uses non-Claude assistants (Cursor, Codex). `.aider.conf.yml` etc. are project-team's choice, not org policy. Why: tool-neutrality reduces lock-in while letting teams move fast.
- **Out-of-scope list (explicit).** What governance does NOT mandate: editor choice, language choice within `--lang=` matrix, CI runner choice, branching strategy. What it DOES mandate: plugin pinning, regulated-data signaling, CODEOWNERS coverage on `.claude/`, audit-log opt-out only for non-regulated repos.

### `SECURITY.md` (~150 lines, design §7 + §8 pointer-only)

**Opening paragraph cross-references the operational PDPA pack docs** (`docs/compliance/*` shipped by B2.5): "This doc is the baseline; for PDPA-specific controls when the `pdpa-compliance` policy is applied, see `docs/compliance/data-classification-template.md` and siblings."

Content:

- **Baseline controls (per design §7.2).** Hooks-based enforcement: `audit-log-strict` (default), `secret-scan` (default), `supply-chain-scan` (default for regulated profiles). Reference to [[../design/policy-catalog]].
- **Reasoning from real incident classes.** Brief catalog: leaked secrets in git history, supply-chain compromise of a transitive dep, audit-log opt-out hiding misuse, social-engineered Claude session, PDPA breach via training data. Each incident class → which baseline control mitigates it.
- **Pinning policy.** All Layer-1 plugins pinned in `.claude/settings.json::installed_plugins`. Pre-merge CI verifies pins are concrete versions (not `latest`). Reference to `B3.2`.
- **Update process.** Quarterly review of pinned versions. Out-of-cycle update when a CVE lands on a pinned plugin's dependency tree: dependabot opens PR → security-auditor subagent reviews → CODEOWNERS approves.
- **Threat model boundary.** What's in scope: Claude session-level threats (prompt injection, tool misuse, secret leak via output). What's NOT: network/host-level (left to standard infosec stack), social engineering of human operators (left to org training), insider threats with full repo write access.
- **Escalation.** When to escalate to org security: secret regen needed across repos, compromised plugin in marketplace, audit log shows pattern of misuse.

## Disambiguation: `GOVERNANCE.md` vs `GOVERNANCE-SERVICE-LEVEL.md`

Both files live in `templates/managed-agent-base/docs/`. Both ship in every scaffold. Distinct purposes:

| File | Scope | Audience |
|---|---|---|
| `GOVERNANCE.md` (this PR) | **Org-wide** policy: plugin versioning, memory tiers, marketplace, promotion path, tool-neutral position, out-of-scope list. | Tech leads / architects / platform-team across services. |
| `GOVERNANCE-SERVICE-LEVEL.md` (B1.6, already shipped) | **This service team's** playbook: who owns `.claude/`, how to promote local skills, how to signal regulated-data status, CODEOWNERS coverage, migration handoff. | The team owning this repo. |

Each file's first paragraph cross-links the sibling so readers don't conflate them.

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-1 | All 4 docs ship in `sn-setup demo --no-git` scaffold under `docs/` |
| AC-2 | Existing test `tests/test_sn_init.py::_expected_top_level` (or sibling helper) lists the 4 new doc paths |
| AC-3 | Full test suite passes (297 passed + 1 skipped baseline post-PR #26 merge) |
| AC-4 | Backlog `B2.4` marked `[x]` linking the PR; new `B2.4b` carved entry for service/bff overlay fill |
| AC-5 | CHANGELOG `[Unreleased] > Added` entry |
| AC-6 | PR merges cleanly; no plugin major version bump (scaffold-internal docs only) |
| AC-7 | Each doc opens with a 1-sentence purpose statement so casual readers know whether to keep reading |
| AC-8 | `GOVERNANCE.md` first paragraph explicitly cross-references `GOVERNANCE-SERVICE-LEVEL.md` and vice-versa (B1.6 file gets a tiny touch-up too) |
| AC-9 | `SECURITY.md` first paragraph explicitly cross-references `docs/compliance/*` (PDPA pack) |
| AC-10 | Each doc has a `## See also` footer with 2-3 sibling-doc relative paths; no inline body cross-links |

## Out of scope (carved to B2.4b)

`B2.4b` — Service-template / BFF-template profile overlay fill — adds ~10 missing files per design §9.4 / §9.5 to `profile/microservice/` and `profile/bff/`:

- `claude-security-guidance.md` per profile.
- `.claude/docs/` load-on-demand conventions per profile.
- `.claude/skills/` exemplar per profile.
- `.claude/agents/` exemplar where missing (microservice has none today).
- Possibly `.claude/rules/` per-profile content (currently populated only by policy catalog at scaffold time).

Filed in `docs/backlog.md` as a new Tier 2 entry. Estimated 4-6h. Separate PR after this one merges.

Also out of scope:
- Updating the source design doc itself (`temp/...md` is intentionally gitignored + frozen).
- Marketplace + promotion CI flow — `B3.1` + `B3.2`, depends on marketplace standing up.
- New Python code, new tests beyond the `_expected_top_level` extension.

## Implementation plan (light)

1. Branch `feat/layer4-governance-docs` created from `main` (`94ad92c`). ✅ done.
2. Vault req+design landed (this file). ⏸ in progress.
3. Index `requirements/README.md` extended with row.
4. Vault commit + push.
5. Mirror this doc → repo `docs/superpowers/specs/2026-06-27-layer4-governance-docs-design.md`.
6. Author 4 new docs at `skills/sn-setup/templates/managed-agent-base/docs/{ARCHITECTURE,REPO-STRATEGY,GOVERNANCE,SECURITY}.md`.
7. Touch up `GOVERNANCE-SERVICE-LEVEL.md` first paragraph to cross-reference the new `GOVERNANCE.md` (AC-8).
8. Extend `tests/test_sn_init.py::_expected_top_level` (or sibling) to include the 4 new doc paths.
9. Run full suite — expect 297 passed + 1 skipped.
10. Update `docs/backlog.md`: mark `B2.4 [x]` + add new `B2.4b` carved entry under Tier 2.
11. Update `CHANGELOG.md` `[Unreleased] > Added` block.
12. Commit per file or bundled — recommend 6 commits (one per doc + one for tests + one for backlog/CHANGELOG).
13. Push + open PR + watch CI green + merge.

## Execution mode

Direct write by main thread (per locked plan from brainstorm) — no SDD subagents. Single sonnet reviewer at the end. Rationale: 4 prose docs + ~5 LOC test extension + backlog/CHANGELOG = within main-thread context budget; subagent isolation buys little for content-heavy work.

## Related

- [[layer4-docs]] — REQ-DOCS-001, predecessor (B1.3 + B1.4 + B1.6). This doc fulfills the carve-out from there.
- [[../design/policy-catalog]] — referenced by `GOVERNANCE.md` (plugin pinning) and `SECURITY.md` (baseline controls).
- [[../design/workspace-layer]] — referenced by `REPO-STRATEGY.md` (Layer 3) and `ARCHITECTURE.md` (Layer 3).
- [[../design/profile-overlays]] — referenced by `ARCHITECTURE.md` (Layer 2 overlay model).
- B2.5 PDPA pack (shipped) — referenced by `SECURITY.md` opening cross-link.
- `B2.4b` (new, carved) — service/bff template overlay fill.
