---
topic: profile-overlay-fill-requirements
bucket: projects
origin_project: setup_project_plugin
origin_req: REQ-PROF-003
first_seen: 2026-06-27
last_updated: 2026-06-27
tags: [knowledge, requirements, profile-overlay, scaffold-template, layer2, setup_project_plugin]
---

# Requirements — Profile Overlay Fill (B2.4b)

REQ-PROF-003. Fills the gaps in `profile/microservice/` and `profile/bff/` overlays against design §9.4 / §9.5. Carved from REQ-DOCS-002 (B2.4) to keep PR sizes reviewable. Light workflow: one combined requirements + light design + implementation plan note (this file) + one PR.

## Goal

Bring the `microservice` and `bff` profile overlays into compliance with design §9.4 / §9.5 by adding the missing universal foundation files (Group A) and the missing per-profile content (Group B). After this lands, fresh scaffolds from `--profile=microservice` and `--profile=bff` ship the full file set the design doc prescribes.

Source: microservices template-family design doc §9.4 / §9.5 / §5.2 (CLAUDE.md shape) / §5.3 (load-on-demand context) / §6.4 (project-local extension points).

## Gap analysis (verified 2026-06-27 against tree)

What `profile/microservice/` ships today:
- `default_policies.yaml`
- `docs/{API,OBSERVABILITY,PROFILE}.md`

What `profile/bff/` ships today:
- `default_policies.yaml`
- `docs/{BFF-INTEGRATION,DOWNSTREAMS,PROFILE}.md`
- `claude/agents/bff-integration-reviewer.md` (from B2.1c)

What `managed-agent-base/` ships today:
- Top level: `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`, `Makefile`, `README.md`, `.editorconfig`, `.env.example`, `.gitignore`, `.tool-versions`
- `docs/`: `PROMOTION.md`, `PREREQUISITES.md`, `GOVERNANCE-SERVICE-LEVEL.md`, `ARCHITECTURE.md`, `REPO-STRATEGY.md`, `GOVERNANCE.md`, `SECURITY.md`
- `.githooks/`, `.harness/`, `.anthropic/`, `agents/`, `environments/`, `mcp/`, `scripts/`

What design §9.4 prescribes that is MISSING:
- `claude-security-guidance.md` (top-level, design §9.4 bullet 4)
- `.claude/docs/` README + load-on-demand bodies
- `.claude/rules/` (covered by policy catalog at scaffold time — not a template file)
- `.claude/skills/` README + exemplar with how-to
- `.claude/agents/` README + exemplar (microservice has no agent; bff already has one)

## Approach

Split into two groups:

### Group A — universal foundation (lands in `managed-agent-base/`)

These files are identical across profiles per design §9.5 ("All other files ... identical in form to the standard template"). Putting them in `managed-agent-base/` avoids duplication and drift.

| Path | Lines | Per design |
|---|---|---|
| `templates/managed-agent-base/claude-security-guidance.md` | ~80 | §9.4 bullet 4: "repository-level security rules the in-session review enforces; the hook point where the compliance pack's rules attach" |
| `templates/managed-agent-base/claude/docs/README.md` | ~40 | §9.4 bullet 6 + §5.3: explains the load-on-demand pattern; indexes the per-profile bodies; "the single source the skills reference" |
| `templates/managed-agent-base/claude/skills/README.md` | ~40 | §9.4 bullet 8 + §6.4: project-local skill conventions; how-to seed a new skill |
| `templates/managed-agent-base/claude/agents/README.md` | ~40 | §9.4 bullet 8 + §6.4: project-local agent conventions; how-to seed a new agent |

The render walk for `managed-agent-base/` already copies the whole tree without filter. The `claude/` → `.claude/` rename happens during `_render_base` (analogous to the existing `_render_profile` rename added in B2.1c).

**Action item:** verify `_render_base` already does the rename; if not, extend it. Check `scripts/sn_init.py::_render_base` source before authoring.

### Group B — profile-specific bodies

#### Microservice (`templates/profile/microservice/`)

| Path | Lines |
|---|---|
| `claude/docs/microservice-conventions.md` | ~100 |
| `claude/skills/example/SKILL.md` | ~40 |
| `claude/skills/example/HOWTO.md` | ~20 |
| `claude/agents/microservice-reviewer.md` | ~50 |

Microservice has NO project-local agent today. Add `microservice-reviewer` as the seeded exemplar matching the pattern bff already established with `bff-integration-reviewer`.

#### BFF (`templates/profile/bff/`)

| Path | Lines |
|---|---|
| `claude/docs/bff-aggregation.md` | ~100 |
| `claude/skills/example-bff/SKILL.md` | ~40 |
| `claude/skills/example-bff/HOWTO.md` | ~20 |

BFF already has `claude/agents/bff-integration-reviewer.md` from B2.1c. No new agent needed.

## File content guidelines

- `${name}`, `${lang}`, `${profile}` placeholders work; same substitution as existing managed-agent-base + profile templates.
- Real prose, not outlines. Match the tone of existing peers (`docs/PROFILE.md`, `claude/agents/bff-integration-reviewer.md`).
- `claude-security-guidance.md`: concrete rules + the hook point where compliance-pack rules attach. NOT a duplicate of `docs/SECURITY.md` — that doc is template-family-level governance; `claude-security-guidance.md` is per-repo in-session review rules.
- `claude/docs/README.md`: 30-50 lines. Explains: what `.claude/docs/` is for, when Claude reads it, how to add a new doc, how it relates to `.claude/rules/`.
- `claude/skills/README.md`: how to add a project-local skill. Pointer to `docs/PROMOTION.md` for the promotion path to the marketplace.
- `claude/agents/README.md`: how to add a project-local subagent. Same promotion pointer.
- Microservice conventions: typical microservice topics — request handling, database access, observability, API versioning. Load-on-demand (Claude reads when work touches the area).
- BFF aggregation: typical BFF topics — downstream call orchestration, response shaping, caching strategies, error envelope normalization. Load-on-demand.
- Example skill (microservice) — a useful one for the profile, e.g. `claude/skills/example/SKILL.md` could be a "validate-request-shape" or "audit-endpoint-coverage" skill. Avoid trivial "hello world" placeholders — real content per backlog rule.
- Example skill (bff) — similarly real, e.g. "diagnose-downstream-failure" or "aggregate-response-shape".
- Microservice reviewer agent: profile-tailored review prompt covering API contract drift, error response envelope, observability tags. ~50 lines matching the existing `bff-integration-reviewer.md` tone.

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-1 | All 4 Group A files ship in every `sn-setup demo --no-git` scaffold under the universal paths above. |
| AC-2 | All 3 microservice Group B files ship when `--profile=microservice` (default). |
| AC-3 | All 2 bff Group B files ship when `--profile=bff`. |
| AC-4 | `tests/test_sn_init.py::_expected_top_level` extended with Group A + microservice paths (microservice is the default profile in that test). |
| AC-5 | `tests/test_sn_init.py::test_profile_bff_default_lang_go` extended to assert the 2 bff Group B files ship. |
| AC-6 | Full test suite passes (297 baseline + extended assertion list; no new test functions; expect 297 passed + 1 skipped). |
| AC-7 | Backlog `B2.4b` marked `[x]` linking PR. Optional: new `B2.4c` carved for frontend profile overlay fill. |
| AC-8 | CHANGELOG `[Unreleased] > Added` entry. |
| AC-9 | PR merges cleanly; no plugin major version bump. |
| AC-10 | `claude-security-guidance.md` first paragraph explicitly distinguishes itself from `docs/SECURITY.md` (different scope: in-session review rules vs template-family governance). |
| AC-11 | Each file uses real prose per backlog rule (no `TODO` / outline / placeholder content). |
| AC-12 | `_render_base` correctly renames `claude/` to `.claude/` in the scaffold output (verify before authoring or extend the rename). |

## Out of scope

- **Frontend profile overlay fill** — same gap applies (frontend has no `claude/` content at all). Carved to **B2.4c** as a follow-up. Reason: bundled scope already 9 files; adding frontend = +3-5 more files plus framework-specific overlay considerations. Separate PR.
- **B2.3 marketplace consumer wiring** for bff's `.claude/settings.json` adding `contracts-sync` + `bff-patterns` by default — gated on B2.3.
- Literal top-level `service-template/` or `bff-template/` dirs — confirmed out by B2.4 decision (conflicts with overlay model).
- Filling out `managed-agent-base/.claude/rules/` template files — those are populated at scaffold time by the policy catalog, not template-baked.
- New Python code; new test functions (beyond extending the existing assertion lists).

## Implementation plan (light)

1. Branch `feat/profile-overlay-fill` from `main` (`c4f83d4`). ⏸ next.
2. Vault req+design landed (this file). ⏸ in progress.
3. Index `requirements/README.md` extended with row.
4. Vault commit + push.
5. Verify `_render_base` does the `claude/` → `.claude/` rename. If not, extend.
6. Mirror this doc → repo `docs/superpowers/specs/2026-06-27-profile-overlay-fill-design.md`.
7. Author 4 Group A files.
8. Author 4 microservice Group B files.
9. Author 3 bff Group B files (2 new + verify existing bff-integration-reviewer.md stays).
10. Extend `tests/test_sn_init.py::_expected_top_level` with Group A + microservice paths.
11. Extend `tests/test_sn_init.py::test_profile_bff_default_lang_go` with bff Group B asserts.
12. Run full suite — expect 297 passed + 1 skipped.
13. Update `docs/backlog.md`: mark `B2.4b [x]` + optionally add `B2.4c` carved entry for frontend.
14. Update `CHANGELOG.md` `[Unreleased] > Added` block.
15. Commit per group — 5-6 commits sequenced (spec mirror + Group A + microservice + bff + tests + backlog/CHANGELOG).
16. Push + open PR + watch CI green + merge.

## Execution mode

Direct write by main thread (matches B2.4 mode). Single sonnet reviewer at the end. Rationale: ~9 prose-content files + test extensions + backlog/CHANGELOG = within main-thread context budget; subagent isolation buys little for content-heavy work; matches the velocity of the B2.4 PR.

## Related

- [[layer4-docs]] — REQ-DOCS-001, predecessor doc bundle (B1.3 + B1.4 + B1.6).
- [[layer4-governance-docs]] — REQ-DOCS-002, B2.4 parent. This file fulfills its carved follow-up B2.4b.
- [[../design/profile-overlays]] — the additive overlay model this fills.
- [[profile-subagents]] — REQ-PROF-002, B2.1c — shipped `bff-integration-reviewer.md` and `a11y-auditor.md`. This doc extends the pattern.
- [[ecosystem-foregrounding]] — REQ-PROF-001, B2.1a — profile-aware foregrounding in `repository-ecosystem` policy. Referenced by `claude/docs/microservice-conventions.md` and `bff-aggregation.md`.
- B2.4c (carved, frontend profile overlay fill) — same shape, separate PR.
