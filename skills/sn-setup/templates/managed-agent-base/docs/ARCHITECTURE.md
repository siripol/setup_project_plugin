# Architecture — ${name}

The layered architecture this service inherits from the template family, and how the pieces fit together at runtime. Read this if you are new to the repo, leading a hand-off, or evaluating whether to adopt the optional workspace layer.

This doc is the executable companion to the template family's design document. It is intentionally shorter than the design doc and concrete to what this scaffold ships.

## The four layers in one paragraph

The org runs a **four-layer template family**. Layer 1 (Platform) is the internal plugin marketplace that distributes mandatory and opt-in plugins. Layer 2 (Service repos) is what you are reading: one repo per service, sharing a common foundation (`managed-agent-base/`) and a profile overlay (`--profile=microservice|bff|frontend`). Layer 3 (Workspace) is an optional virtual-monorepo aggregator for cross-service editing, gitignored sibling dir, only adopted when polyrepo coordination starts hurting. Layer 4 (Governance) is the doc set you are reading right now: `ARCHITECTURE.md`, `REPO-STRATEGY.md`, `GOVERNANCE.md`, `GOVERNANCE-SERVICE-LEVEL.md`, `SECURITY.md`, `PREREQUISITES.md`, `PROMOTION.md`. None of the four layers depend on the others' implementation — they communicate through narrow contracts (marketplace.json schema, `.sn-init-state.json`, `.workspace/registry.json`, scaffolded `CLAUDE.md` placeholders).

## Layer 1 — Platform (internal plugin marketplace)

Mandatory plugins land at scaffold time via the marketplace consumer surface (`--marketplace=<source>` flag, when wired). The mandatory set is:

| Plugin | Role |
|---|---|
| `core-workflow` | Advisory skill set: spec-loop discipline, write-test-first, planning shape, evaluator-optimizer loops. |
| `core-guardrails` | Enforcement: PreToolUse hooks (chokepoint-gate, secret-scan, audit log), `.claude/settings.json` permissions block, `.githooks/commit-msg`. |

Opt-in packs add narrower capabilities: `testing-standards`, `contracts-sync`, `cicd-helpers`, `bff-patterns` (BFF profile), `compliance-pack` (PDPA-class data), `service-scaffold`.

**Why marketplace, not template-baked.** Template-baked plugins drift the moment the template diverges from upstream. Marketplace plugins ship a single canonical version; service repos pin to a specific version in `.claude/settings.json::installed_plugins`. Upgrades happen through PR review with explicit version diffs, not through silent template re-runs.

The marketplace itself is a separate repository (or subdir) the org owns. The consumer side — references to it — lives in this repo's `.claude/settings.json` (`installed_plugins` block) and, once B2.3 (marketplace consumer) ships, `.claude-plugin/marketplace.json`. Today the consumer block is not yet wired; the platform team's marketplace-consumer flag (`--marketplace=<source>`) is the path that will scaffold it.

## Layer 2 — Service repos (this scaffold)

What this repo ships at the top level:

- `CLAUDE.md` — assistant-facing identity, profile, policies table, context-policy pointer. Small by design (see `## Context policy` in the file).
- `README.md` — human-facing service overview.
- `AGENTS.md` — tool-neutral mirror of `CLAUDE.md` for non-Claude assistants (Cursor, Codex, etc.).
- `Makefile` — `make agent`, `make session`, `make test`, `make validate`, `make logs-tail`.
- `.gitignore`, `.editorconfig`, `.tool-versions`, `.env.example` — boilerplate.
- `.claude/` — the Claude Code context layer (see below).
- `.githooks/{commit-msg,post-merge}` — git-side enforcement.
- `agents/`, `environments/`, `mcp/`, `scripts/` — Managed Agent + MCP server config.
- `docs/` — these governance docs plus profile-specific docs added by the overlay.
- `.harness/` — invariants + proof-bundle templates.

### `.claude/` tree

Three-tier context model, by load behavior:

| Tier | Where | Behavior |
|---|---|---|
| Always-on minimal | `CLAUDE.md` | Always loaded. Identity + policies table + pointers. Keep small. |
| Always-on rules | `.claude/rules/<slug>.md` | Always loaded. ≤ 50 tokens each. Hard rules that must fire every turn. Populated by policy catalog. |
| Load-on-demand | `.claude/docs/<slug>.md` | Read when Claude works on the relevant topic. Long bodies. Populated by policy catalog + profile overlay. |

Beyond these three: `.claude/skills/<slug>/` and `.claude/agents/<name>.md` are project-local extensions; `.claude/settings.json` carries permissions + hook wiring + `installed_plugins` block; `.claude/config/` holds policy state and tool config.

### Profile overlay

The `--profile=<microservice|bff|frontend>` flag selects an overlay applied on top of `managed-agent-base/`. Each overlay adds:

- Profile-specific `docs/PROFILE.md` (shape, conventions, anti-patterns).
- Profile-specific policy defaults (e.g., regulated profiles get `memory-regulated` + `audit-log-strict` + `secret-scan` by default).
- Profile-specific subagents (`bff-integration-reviewer` for BFF, `a11y-auditor` for frontend).
- Profile-specific load-on-demand docs (BFF: `BFF-INTEGRATION.md`, `DOWNSTREAMS.md`; frontend: `ACCESSIBILITY.md`, `DESIGN.md`, `BROWSER-MATRIX.md`).

The overlay is **additive**, not transformative — files in `managed-agent-base/` stay as-is; the overlay copies its own files on top. See the plugin's `design/profile-overlays` knowledge note for the matrix and conventions.

## Layer 3 — Workspace (optional)

A virtual-monorepo aggregator that sits as a **sibling directory** of N service repos. Adopt it when:

- More than 3 services live next to each other.
- Cross-repo `git status` and `git pull --ff-only` sweeps become routine.
- An editor needs a single workspace scope across services.

The workspace dir holds:

- `WORKSPACE.md` — human-readable explainer with a registered-services table.
- `CLAUDE.md` — workspace-level Claude memory (auto-loaded when Claude runs from the workspace dir).
- `MIGRATION.md` — adoption and exit instructions.
- `.workspace/registry.json` — machine-readable source of truth (each registered service's slug + relative path + profile + lang + regulated).
- `scripts/{status,sync,launch}.sh` — bash sweeps over registered services.

Adoption is **reversible**: `rm -rf <workspace-dir>/`. No data lives in the workspace; it is a view over independent repos. The workspace is NOT a build orchestrator — Bazel/Nx/Turborepo remain orthogonal layers users can stack on top.

CLI surface: `sn-setup workspace {init,add,remove,list,status,sync,launch}`. Pair-mode flag `--workspace` on `sn-setup new|demo` scaffolds the workspace alongside the project. See the workspace layer's `MIGRATION.md` for the adoption playbook.

## Layer 4 — Governance

The doc set in `docs/` (this folder):

- `ARCHITECTURE.md` (this file) — layered architecture overview.
- `REPO-STRATEGY.md` — polyrepo rationale and when to adopt the workspace.
- `GOVERNANCE.md` — org-wide policy: plugin versioning, two-tier memory, promotion path, tool-neutral context position, out-of-scope list.
- `GOVERNANCE-SERVICE-LEVEL.md` — this service team's playbook for owning `.claude/`.
- `SECURITY.md` — baseline controls, incident-class reasoning, pinning policy, update process.
- `PREREQUISITES.md` — minimum tool and runtime versions.
- `PROMOTION.md` — local skill/agent → marketplace checklist.

Reading order for a new contributor: `PREREQUISITES.md` (can I install this?) → `ARCHITECTURE.md` (this file, what is this?) → `REPO-STRATEGY.md` (why this shape?) → `GOVERNANCE.md` (org rules) → `GOVERNANCE-SERVICE-LEVEL.md` (our team's rules) → `SECURITY.md` (what could go wrong?) → `PROMOTION.md` (how do I share what I built?).

## What this doc is NOT

- Not the full template-family design document. The design doc lives outside this repo (local-only at `<plugin>/temp/__claude__microservices-template-design...md`). This file is its executable companion: enough context to act, not enough to design.
- Not a service-specific architecture doc. Service-specific design notes go in this repo's own `docs/` outside `managed-agent-base/` (which is the template-foundation tree). Examples: `docs/api-contract.md`, `docs/data-model.md`.
- Not a runtime architecture diagram. If you need one, draw it once and put it next to this file as `docs/RUNTIME-ARCHITECTURE.md`.

## See also

- `REPO-STRATEGY.md` — polyrepo rationale and workspace adoption triggers.
- `GOVERNANCE.md` — org-wide policy that this architecture enables.
- `PREREQUISITES.md` — what you need installed to work with each layer.
