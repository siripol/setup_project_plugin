---
topic: frontend-overlay-fill-requirements
bucket: projects
origin_project: setup_project_plugin
origin_req: REQ-PROF-004
first_seen: 2026-06-27
last_updated: 2026-06-27
tags: [knowledge, requirements, profile-overlay, scaffold-template, layer2, frontend, setup_project_plugin]
---

# Requirements — Frontend Profile Overlay Fill (B2.4c)

REQ-PROF-004. Fills the `claude/docs/` + `claude/skills/` gaps in `profile/frontend/` overlay against design §9.4 / §9.5. Carved from REQ-PROF-003 (B2.4b) for PR-size hygiene. Light workflow: one combined requirements + design + implementation plan note (this file) + one PR.

## Goal

Bring the `frontend` profile overlay into compliance with design §9.4 / §9.5 by adding the load-on-demand conventions doc + skill exemplar that B2.4b shipped for microservice + bff. After this lands, fresh scaffolds from `--profile=frontend [--framework=next|vite]` ship the full file set the design doc prescribes.

Source: microservices template-family design doc §9.4 / §9.5 / §5.3 (load-on-demand context) / §6.4 (project-local extension points).

## Gap analysis (verified 2026-06-27 against tree)

What `profile/frontend/` ships today:
- `default_policies.yaml`
- `docs/{ACCESSIBILITY,DESIGN,BROWSER-MATRIX,PROFILE}.md`
- `claude/agents/a11y-auditor.md` (from B2.1c)

What `framework/next/` ships today:
- `docs/FRAMEWORK.md`

What `framework/vite/` ships today:
- `docs/FRAMEWORK.md`

What's missing per design §9.4 (universal foundation already shipped in B2.4b for `managed-agent-base/`):
- `profile/frontend/claude/docs/` — load-on-demand body for frontend conventions.
- `profile/frontend/claude/skills/` — exemplar skill with SKILL.md + HOWTO.md.

## Approach

### Framework split decision: single shared body

The frontend profile spans Next.js and Vite via `--framework=` sub-overlay. Two paths considered:

| Path | Cost | Benefit |
|---|---|---|
| Per-framework split (`framework/next/claude/docs/...`, `framework/vite/claude/docs/...`) | Duplicates ~80% of content; drift risk between Next + Vite copies. | Slightly more accurate framework-specific guidance. |
| Single shared body in `profile/frontend/claude/docs/` | ~20% loss of framework-specific accuracy. | Single source of truth; no drift; framework-specific guidance stays in existing `framework/<F>/docs/FRAMEWORK.md`. |

**Locked: single shared body.** React component conventions, accessibility, performance budgets, state management discipline apply identically to Next.js and Vite at the conventions layer. Routing-specific or build-tool-specific guidance lives in `framework/<F>/docs/FRAMEWORK.md` (already shipped).

### Files

| Path | Lines | Purpose |
|---|---|---|
| `templates/profile/frontend/claude/docs/frontend-conventions.md` | ~120 | Load-on-demand reference for React component conventions, accessibility patterns, state management discipline, performance budgets, testing strategies. |
| `templates/profile/frontend/claude/skills/example-frontend/SKILL.md` | ~50 | `audit-component-coupling` skill — audits React component boundaries: prop drilling depth, state hoisting choices, context usage, component fanout. Outputs per-component coupling score + refactor recommendations. |
| `templates/profile/frontend/claude/skills/example-frontend/HOWTO.md` | ~30 | Human-facing how-to for invoking `audit-component-coupling`. |

Frontend already has `claude/agents/a11y-auditor.md` from B2.1c. No new agent needed (matches bff's pattern where B2.1c shipped the agent and B2.4b added the docs+skill).

### Distinct skill from a11y-auditor

The existing `a11y-auditor` agent (B2.1c) focuses on WCAG 2.2 AA conformance: images/icons/media, focus management, semantic HTML + ARIA, forms, color/motion/contrast. The new `audit-component-coupling` skill is **architecture-focused**, not accessibility-focused:

- Prop drilling depth.
- State hoisting decisions.
- Context usage vs explicit prop passing.
- Component fanout (one component → many children → many siblings).
- Refactor recommendations (e.g., "extract context to scope this state to subtree").

No overlap. Both ship for the same profile and they review different concerns.

## File content guidelines

- `${name}`, `${lang}`, `${profile}`, `${framework}` placeholders work.
- Real prose, not outlines. Match the tone of B2.4b's microservice + bff Group B bodies.
- `frontend-conventions.md`: ~120 lines covering component conventions, accessibility patterns (high-level; defer WCAG-level detail to `a11y-auditor`), state management (when context, when prop drilling), performance budgets (bundle size targets, code-split signals), testing (unit + integration boundaries). Framework-neutral.
- `audit-component-coupling SKILL.md`: real audit logic, not "hello world". Cite specific dispatch criteria, explicit output format (per-component table with coupling score + recommendation), explicit "what NOT to do" section.

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-1 | `frontend-conventions.md` ships when `--profile=frontend` (any framework). |
| AC-2 | `example-frontend/SKILL.md` + `HOWTO.md` ship when `--profile=frontend`. |
| AC-3 | `tests/test_sn_init.py::test_profile_frontend_default_framework_next` extended with 3 new path asserts. |
| AC-4 | Full suite passes (297 baseline + extended asserts; no new test functions; expect 297 passed + 1 skipped). |
| AC-5 | Backlog `B2.4c` marked `[x]` linking PR. No new carve-outs expected. |
| AC-6 | CHANGELOG `[Unreleased] > Added` entry. |
| AC-7 | PR merges cleanly; no plugin major version bump. |
| AC-8 | `frontend-conventions.md` content is framework-neutral; no Next-specific or Vite-specific examples that won't apply to the other. |
| AC-9 | `audit-component-coupling` skill body is real (dispatch criteria, output format, anti-patterns); no outline / placeholder / "hello world" content. |
| AC-10 | `audit-component-coupling` is distinct in scope from `a11y-auditor` (architecture-focused vs accessibility-focused); doc comment makes this explicit. |

## Out of scope

- **Per-framework `claude/docs/` split** (Next-specific or Vite-specific bodies) — locked decision; framework guidance stays in `framework/<F>/docs/FRAMEWORK.md`.
- **New agent for frontend** — `a11y-auditor` (B2.1c) is sufficient for now. Future architecture-review agent could be carved if `audit-component-coupling` skill proves valuable enough to graduate to agent shape.
- **PDPA pack frontend-specific rules** — gated on B2.5x backlog items.
- **New Python code, new test functions** — beyond extending the existing `test_profile_frontend_default_framework_next` assertion list.

## Implementation plan (light)

1. Branch `feat/frontend-overlay-fill` from `main` (`23485ef`). ✅ done.
2. Vault req+design landed (this file). ⏸ in progress.
3. Index `requirements/README.md` extended with row.
4. Vault commit + push.
5. Mirror this doc → repo `docs/superpowers/specs/2026-06-27-frontend-overlay-fill-design.md`.
6. Author 3 new files under `templates/profile/frontend/claude/`.
7. Extend `tests/test_sn_init.py::test_profile_frontend_default_framework_next` with 3 path asserts.
8. Run full suite — expect 297 passed + 1 skipped.
9. Update `docs/backlog.md`: mark `B2.4c [x]`. No carved follow-ups expected.
10. Update `CHANGELOG.md` `[Unreleased] > Added` block.
11. Commit per group — 4 commits sequenced (spec mirror + content + tests + backlog/CHANGELOG).
12. Push + open PR + watch CI green + merge.

## Execution mode

Direct write by main thread (matches B2.4 + B2.4b mode). Single sonnet reviewer at the end. Rationale: 3 prose-content files + test extension + backlog/CHANGELOG = tightest scope of the three (PR #27 = 4 docs, PR #28 = 11 files, this PR = 3 files).

## Related

- [[layer4-governance-docs]] — REQ-DOCS-002, parent (B2.4).
- [[profile-overlay-fill]] — REQ-PROF-003, immediate parent (B2.4b). This file completes the profile-overlay-fill series by handling the third profile.
- [[../design/profile-overlays]] — the additive overlay model this fills.
- [[profile-subagents]] — REQ-PROF-002, B2.1c — shipped `a11y-auditor.md` for frontend. This doc complements it with the docs+skill that B2.4b shipped for microservice + bff.
