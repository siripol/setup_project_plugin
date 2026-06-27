# Governance — ${name}

**Scope of this doc — org-wide.** Policies in this file apply to every service in the org: plugin versioning, two-tier memory, marketplace promotion, tool-neutral context positioning, and the explicit out-of-scope list. For how THIS service team owns and operates ITS OWN `.claude/` tree (ownership table, CODEOWNERS coverage, signaling regulated-data status, migration handoff), see `GOVERNANCE-SERVICE-LEVEL.md` in this same folder. The two files are complements, not duplicates.

## Plugin versioning and pinning policy

The internal plugin marketplace (Layer 1) is the source of every advisory skill and enforcement hook this service runs. Every plugin declares semver. Every consuming service should pin to a specific version in `.claude/settings.json::installed_plugins` when that consumer block ships (B2.3, unshipped today). No service should run `latest`. When B3.2 (pin-verification CI) lands, CI will verify every entry resolves to a concrete version; until then, CODEOWNERS enforces this in PR review.

### Update procedure

1. Plugin upstream ships a new version. Changelog publishes to the marketplace.
2. A **breaking change** triggers a 30-day grace window. Upstream owners notify in the org chat and the platform-team's monthly sync.
3. Service teams open PRs against their own repos bumping the pinned version. The PR diff shows the version string change explicitly; CODEOWNERS reviews.
4. After the grace window, the platform team opens fallback PRs against any service still on the old major. After 60 days, the old version is removed from the marketplace.

For **non-breaking** changes (patch, minor): no grace required. Service teams update on their own cadence. Quarterly is a healthy floor.

### Rollback

If a pinned plugin version turns out to be broken in production:

1. Revert the version bump in the service's `.claude/settings.json` (or `git revert` the bump commit).
2. Open a postmortem issue against the plugin upstream.
3. Upstream issues a deprecation note on the broken version so other services see it before adopting.

## Two-tier memory policy

The org runs two tiers of Claude memory, distinguished by `regulated` flag at scaffold time:

| Tier | Trigger | Differences |
|---|---|---|
| Ordinary | Default. No `--regulated` flag at scaffold. No `memory-regulated` policy applied. | Auto-memory (`~/.claude/memory/` + `.claude/local-memory/`) free to accumulate. Audit log can be opted out per project. Standard secret-scan strictness. |
| Regulated | `--regulated` at scaffold OR `memory-regulated` policy in `applied_policies`. | Auto-memory writes BLOCKED. `audit-log-strict` forced (no opt-out). Stricter secret-scan patterns + PAN/passport/Thai NI regex. `security-auditor` subagent installed by default. PDPA pack adds Hook A (PII scan) + Hook B (retention sidecar) when applied. |

A service can be promoted from ordinary to regulated mid-life by applying the regulated policies; the reverse is **not** supported through `sn-setup policy remove` alone because the regulated tier carries audit obligations (retention, breach notification) that outlive any single applied policy. Demoting requires a separate process: prove no regulated data remains, gain platform-team sign-off, then strip the policies and document the change.

See `SECURITY.md` for the controls themselves; this doc covers the policy that mandates them.

## Marketplace promotion path

Local skills (`.claude/skills/<slug>/`) and agents (`.claude/agents/<name>.md`) graduate to the org marketplace when they have proven value across multiple services. Org policy on promotion:

- **Who decides.** The marketplace's CODEOWNERS team. The promoting service's team opens the PR; the platform team merges.
- **Criteria.** Used in at least 3 distinct sprints, no project-domain leakage in the body (no service-specific identifiers, secrets, or contracts), reviewed by at least one engineer outside the originating team, passes `sn-knowledge promote` invariants.
- **Versioning.** The promoted version starts at `0.1.0`. Subsequent versions follow semver. The originating service's local copy is replaced with an `installed_plugins` entry pinned to the new version.
- **Rollback path.** If the promoted plugin turns out to be wrong: open a postmortem, mark the version deprecated in the marketplace, optionally re-localize via `sn-knowledge demote`.

Detailed step-by-step: `PROMOTION.md`. This doc states the policy; that doc is the playbook.

## Tool-neutral context file position

`CLAUDE.md` is the canonical assistant context file for this org. Org policy:

- **`CLAUDE.md`** is mandatory. Auto-loaded by Claude Code and the Agent SDK. Source of truth for assistant identity, profile, policies table.
- **`AGENTS.md`** is a tool-neutral mirror. Mandatory when the team uses non-Claude assistants in the repo (Cursor, Codex, Continue, Aider). Content must not diverge substantively from `CLAUDE.md`.
- **Tool-specific files** (e.g., `.aider.conf.yml`, `.continue/config.json`) are at the team's discretion. Not org policy. Do not commit secrets to them.

Why tool-neutrality matters: assistants are commodity infrastructure. Locking to one vendor's file format compounds switching cost. The cost of maintaining two files (`CLAUDE.md` + `AGENTS.md`) is one well-defined merge step at promotion time, much smaller than the cost of vendor migration when the platform team decides to swap providers.

## Out of scope (explicit)

What this governance does **NOT** mandate:

| Decision | Policy |
|---|---|
| Editor choice (VS Code, JetBrains, Neovim, etc.) | Team's call. |
| Programming language within the `--lang=` matrix | Team's call, picked at scaffold. |
| CI runner choice (GitHub Actions, GitLab, CircleCI, etc.) | Team's call. Mandatory: CI must run `pytest` (or lang equivalent) + the plugin's `_dangerously-skip-permissions` block step. |
| Branching strategy (trunk-based, git-flow, feature branches) | Team's call. Mandatory: `main` must be protected with at least 1 review + passing CI. |
| Test framework (within the lang ecosystem) | Team's call. Mandatory: tests live in `tests/` and run via `make test`. |
| Logging library, metrics, tracing vendor | Team's call. Mandatory: structured logs to stdout, audit JSONL in `.sn-init/logs/`. |

What this governance **DOES** mandate:

- Plugin pinning to concrete versions; no `latest` in `installed_plugins`.
- Regulated-data signaling via the `--regulated` flag or `memory-regulated` policy when applicable.
- CODEOWNERS coverage on `.claude/` and `docs/` paths.
- Audit log opt-out only permitted for non-regulated repos AND only via `--no-audit-log` at scaffold (not via runtime hook disable).
- The `--dangerously-skip-permissions` flag is forbidden in scripts, docs, runbooks, and commit messages. CI greps for it.

## Disagreement and escalation

Local override of an org policy is allowed only through a documented exception:

1. Open an issue in the platform-team's repo describing the policy and the exception's scope and lifetime.
2. Platform team responds within one week with approval, denial, or counter-proposal.
3. Approved exceptions are documented in `docs/exceptions.md` in the affected service repo with the issue link and expiry date.

Standing exceptions: there are none today. Any exception is bounded.

## See also

- `GOVERNANCE-SERVICE-LEVEL.md` — this service team's playbook for owning `.claude/`. Companion to this doc.
- `SECURITY.md` — the controls that implement the regulated-tier and pinning policies above.
- `PROMOTION.md` — the playbook for the marketplace promotion path stated above.
