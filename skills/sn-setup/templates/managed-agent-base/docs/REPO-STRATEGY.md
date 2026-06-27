# Repository Strategy — ${name}

Why this service ships as its own repo, what is shared at the template layer, and when to opt into the workspace aggregator. Read this if you are evaluating monorepo vs polyrepo for a new service, or trying to understand why cross-repo coordination feels manual.

## Polyrepo by default

One service equals one repository. Each service owns:

- Its own CI configuration and release cadence.
- Its own `CODEOWNERS` file and review policy.
- Its own deploy pipeline and environment matrix.
- Its own `.claude/` tree and policy state.
- Its own git history, audit log, and release tags.

**Why polyrepo wins for independent services.** The org runs N teams shipping at different cadences against different SLOs. A monorepo aligns all those clocks to the slowest; a polyrepo lets each team move at its own pace. Conway's law: the repo structure mirrors the team structure, which mirrors the service boundary. When the boundary blurs (one team owning two services that are joined at the hip), reconsider — but until that pain is felt, polyrepo is the cheaper default.

The price of polyrepo: cross-cutting refactors and visibility cost more. The workspace layer (Layer 3, optional) recovers most of that for editor scope and `git status`/`pull` aggregation without giving up independent release pipelines.

## Shared foundation, not shared code

This repo inherits a **template-time foundation**, not a runtime shared library:

- `managed-agent-base/` — the foundation tree: `CLAUDE.md`, `AGENTS.md`, `Makefile`, `.gitignore`, `.tool-versions`, `.githooks/`, `.harness/`, common docs.
- Profile overlay (`--profile=microservice|bff|frontend`) — adds profile-specific files on top of the foundation.
- Optional packs installed via the Layer-1 marketplace — runtime-shared plugins (advisory skills + enforcement hooks).

What is **NOT** shared:

- Git submodules.
- Symlinked source directories.
- Runtime monorepo lockfile or build graph.

The template gives each service the same starting line; nothing afterward couples them. If two services need to coordinate (e.g., a contract change), they coordinate through their interfaces (API schemas, event payloads, RPC contracts), not through shared source.

## Profile-driven divergence

The `--profile=` flag chooses an additive overlay. The same `managed-agent-base/` foundation underneath:

| Profile | When to use | Adds |
|---|---|---|
| `microservice` | Standard backend service owning its data + API. | `docs/API.md`, `docs/OBSERVABILITY.md`, microservice-specific policy defaults. |
| `bff` | Backend-for-frontend / aggregation layer bound to ONE frontend. | `docs/BFF-INTEGRATION.md`, `docs/DOWNSTREAMS.md`, `bff-integration-reviewer` subagent, BFF-specific policy defaults. |
| `frontend` | UI repo (Next.js, Vite). | `docs/ACCESSIBILITY.md`, `docs/DESIGN.md`, `docs/BROWSER-MATRIX.md`, `a11y-auditor` subagent, framework sub-overlay (`--framework=next|vite`). |

The overlay is additive; nothing in the foundation is rewritten by a profile choice. Picking a profile up-front matters because some policies and subagents only ship when the profile selects them — but switching profiles later is a manual re-scaffold, not a one-flag flip.

## Cross-repo awareness

Even in a polyrepo, services need to know about each other. The plugin's `repository-ecosystem` policy populates each `CLAUDE.md` with a Repository Ecosystem table listing sibling repos, owners, and dependency direction. Profile-aware foregrounding: a BFF repo's table foregrounds its downstream service dependencies; a frontend repo's table foregrounds the BFF it consumes; a microservice's table foregrounds its data store and the services that call it.

When the org adopts the workspace layer, the workspace's own `CLAUDE.md` aggregates this across all registered services so Claude can reason about more than one at a time.

## When to adopt the workspace (Layer 3)

The workspace is opt-in. Signals that it is worth standing up:

| Signal | Pain it removes |
|---|---|
| You run `git status` across 3+ sibling repos several times a day. | Single `sn-setup workspace status` sweep. |
| You routinely `git pull --ff-only` across siblings to stay in sync. | Single `sn-setup workspace sync`; skips dirty repos with a warning. |
| Your editor needs N tabs of repos open at once. | Single `.code-workspace` file scoping all registered folders. |
| Claude needs to reason about more than one service in a session. | Workspace-level `CLAUDE.md` aggregates the ecosystem table. |
| Cross-repo refactor: changing an interface across services touched the same week. | Single search root, single editor scope, but each repo keeps its own commit history and PR. |

Adoption is reversible: `rm -rf <workspace-dir>/`. The workspace dir holds no data; it is a view over independent repos. Each member repo's `.gitignore` gains one line so the workspace dir does not pollute the member's `git status`.

## When NOT to monorepo

Sometimes the workspace pain triggers a more radical question: should this team go full monorepo with Bazel / Nx / Turborepo? Most of the time, the answer is no:

- **Cross-team coordination cost.** A monorepo binds release cadence and CI infrastructure across teams. If teams are independent, that binding adds friction without proportional value.
- **Release pipeline complexity.** Monorepo release tools have their own learning curve, their own failure modes, and their own SRE cost. Reasonable for FAANG-scale orgs; expensive for a few dozen services.
- **Security boundaries.** Polyrepo lets `CODEOWNERS` enforce who can touch what at the repo level — strictly more granular than a monorepo's path-based ownership.
- **Vendor lock.** Bazel and Nx are well-engineered but opinionated; switching cost is real.

The workspace gives most of the polyrepo-with-monorepo-ergonomics benefits — single editor, aggregated `git status`/`pull`, cross-repo Claude context — without committing to a monorepo build orchestrator. If after a year of workspace use the team still wants the build-orchestration story a real monorepo gives, then escalate; but most teams will not get there.

## See also

- `ARCHITECTURE.md` — the four-layer architecture this strategy sits within.
- `GOVERNANCE.md` — org-wide policy on plugin pinning and promotion (Layer 1 plumbing).
- `PROMOTION.md` — moving a local skill/agent up to the org marketplace (Layer 1 upstream).
