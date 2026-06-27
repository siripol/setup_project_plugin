# Changelog

All notable changes to `setup-project-plugin` (formerly `init-project-plugin`).

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Versions are taken from `.claude-plugin/plugin.json`. Dates are UTC.

## [Unreleased]

### Added

- **Layer-4 governance docs (B2.4, REQ-DOCS-002).** Four governance / architecture template docs landing in every scaffold's `docs/` tree:
  - `ARCHITECTURE.md` — layered architecture tour (Platform / Service / Workspace / Governance).
  - `REPO-STRATEGY.md` — polyrepo-by-default rationale + workspace adoption triggers + when-not-to-monorepo counter-arguments.
  - `GOVERNANCE.md` — org-wide policy: plugin pinning, two-tier memory, marketplace promotion, tool-neutral context positioning, explicit out-of-scope list.
  - `SECURITY.md` — baseline controls, reasoning from real incident classes, pinning policy, update process, threat-model boundary, escalation path.
  - `GOVERNANCE.md` and `GOVERNANCE-SERVICE-LEVEL.md` cross-reference each other in opening paragraphs (disambiguate org-wide vs service-team scope). `SECURITY.md` cross-references PDPA pack docs.
  - `tests/test_sn_init.py::_expected_top_level` extended with the 4 new paths. No new test functions.
  - Carved follow-up `B2.4b` (service/bff profile overlay fill per design §9.4 / §9.5) on the backlog.

- **Workspace layer (B2.2)** — virtual-monorepo aggregator for polyrepo
  services. New `sn-setup workspace {init,add,remove,list,status,sync,launch}`
  sub-tree plus `--workspace` pair flag on `sn-setup new` / `demo`. Workspace
  dir aggregates registered services via `.workspace/registry.json` with
  `WORKSPACE.md` / `CLAUDE.md` / `MIGRATION.md`. Adoption is reversible
  (`rm -rf <workspace-dir>/`).

- **Per-profile subagents** (B2.1c, REQ-PROF-002). BFF and frontend profiles now ship profile-specific reviewer subagents:
  - `--profile=bff` → `.claude/agents/bff-integration-reviewer.md` (downstream contract drift, error-envelope shape, retry/timeout config, partial-response handling, authn/authz boundary).
  - `--profile=frontend` → `.claude/agents/a11y-auditor.md` (WCAG 2.2 AA: images, focus management, semantic HTML + ARIA, forms, color/motion/contrast).
  - `--profile=microservice` unchanged — generic subagent set remains sufficient.
  - No scaffold-logic change required; `_render_profile`'s rglob walker auto-copies anything under `templates/profile/<P>/.claude/agents/`.

- **PDPA pack — full enforcement** (B2.5, REQ-PDPA-001). Upgrades `pdpa-compliance` catalog policy from `1.0.0` (signal-only) to `2.0.0` (full enforcement). Ships:
  - **Hook A** `pdpa-data-handler-scan.sh` — PreToolUse on Write/Edit. Bash regex over 6 PII patterns (Thai NI 13-digit, email, Thai mobile/landline, credit-card PAN, passport). Skip-on-allowlist-match.
  - **Hook B** `pdpa-retention-check.sh` — PreToolUse on Write to `data/*`. Verifies sibling `<file>.meta.yaml` sidecar with 6 required keys (`retention_days`, `data_subject`, `lawful_basis`, `data_categories`, `controller`, `last_reviewed`).
  - **`sn-setup policy pdpa allowlist <list|add|remove|explain>`** — manages project-local `.claude/config/pdpa-allowlist.yaml`.
  - Scaffolded `data/{subjects,consents,exports}/` with `.gitkeep` + README.
  - Four doc templates under `docs/compliance/`: data-classification-template, retention-policy-template, consent-records-template, breach-notification-runbook.
  - Upgrade path: `sn-setup policy upgrade pdpa-compliance` on a `1.0.0` scaffold → `2.0.0`.
  - Carved follow-ups: **B2.5a** review-staleness, **B2.5b** consent-check hook, **B2.5c** audit-log breach detection, **B2.5d** CI auto-rotate `last_reviewed`, **B2.5e** Luhn validation.

- **Profile-aware Repo Ecosystem foregrounding** (B2.1a, REQ-PROF-001). `repository-ecosystem` policy doc gains three profile-specific sections (microservice peers / BFF downstreams / frontend BFF + direct deps) so Claude has profile-appropriate cross-service guidance from the always-on policies table. Policy version bumps `1.0.0` → `1.1.0`.

- **B1.7 follow-ups** (B1.7a + B1.7b, REQ-SEC-002 + REQ-SEC-003). Closes the two Tier 1 items carved during B1.7's hook audit:
  - **B1.7a — CI guard against `--dangerously-skip-permissions`**: scaffolded `.github/workflows/ci.yml` greps the diff + commit messages on every push/PR; CI fails on match. `docs/GOVERNANCE-SERVICE-LEVEL.md` gains a `## Permission bypass — forbidden` section explaining why the flag is prohibited.
  - **B1.7b — `security-auditor` default for regulated profiles**: when a scaffold's resolved policy set includes `memory-regulated` (or future `pdpa-compliance`), `security-auditor` is automatically added to `args.subagents` so the scaffold ships `.claude/agents/security-auditor.md` by default. Honors explicit `--subagents=none` opt-out. Documented in `GOVERNANCE-SERVICE-LEVEL.md` under `## Security-auditor subagent — regulated default`.

- **Layer 4 service docs** (B1.3 + B1.4 + B1.6, REQ-DOCS-001). Every scaffolded project now ships three new doc templates under `docs/`:
  - `PROMOTION.md` — local-skill → org-marketplace checklist + PR template snippet.
  - `PREREQUISITES.md` — minimum tool / runtime / lang versions table.
  - `GOVERNANCE-SERVICE-LEVEL.md` — `.claude/` ownership, CODEOWNERS, regulated-data signaling, migration handoff playbook.

- **Load-on-demand context split** (B1.5, REQ-CTX-001). Codifies the design's three-tier context model in every fresh scaffold:
  - `CLAUDE.md` — always-on, minimal (identity + profile + policies table + section pointers).
  - `.claude/rules/<slug>.md` — always-on, ≤ 50 tokens each. Hard rules only.
  - `.claude/docs/<slug>.md` — load-on-demand. Long bodies; Claude reads when work touches the topic.
  - Ships `.claude/docs/{README,ARCHITECTURE}.md`, `.claude/rules/README.md`, and a `## Context policy` paragraph in scaffolded `CLAUDE.md`.

- **Mandatory-controls hook audit** (B1.7, REQ-SEC-001). Audited the scaffold's `.claude/settings.json` + `.claude/hooks/*` + `scripts/safety.py` against the design's §7.2 list. Audit doc at `docs/HOOK-AUDIT-2026-06-25.md`. Verdict: 3 PASS / 2 PARTIAL (carved as **B1.7a** + **B1.7b**) / 1 FAIL (fixed in PR) / 1 N-A.
  - **Fixed in PR**: sensitive-path deny patterns added to default `settings.json` `permissions.deny`. Now blocks Write/Edit to `~/.ssh/`, `~/.aws/`, `~/.config/gcloud/`, `~/.kube/`, `~/.docker/`, `~/.netrc`, `~/.pgpass`, `**/.env`, `**/.env.*`, `/etc/**`, `/root/**`.

- **Command sub-tree migration** (B1.9). Regroups 16 flat `sn-X-Y.md` slash commands into 3 grouped `sn-X.md` files matching the `sn-setup policy <op>` pattern:
  - `sn-sprint <new|add|run|status|done|remove>`
  - `sn-req <new|import|replay|resume|rollback>`
  - `sn-knowledge <check|update|promote|demote|summarize>`
- **Retired** `sn-knowledge-tech-matrix`. Use `sn-knowledge summarize tech` (or any free-form topic) instead. Output persists to `<vault>/shared/summaries/<slug>.md`.
- **Migration**: existing scaffolds run `sn-setup --upgrade --rename-commands` once. Idempotent; sha-checked; `--force` for user-edited files. See `docs/MIGRATION.md`.
- **State**: `.sn-init-state.json` gains `commands_renamed_at` + `commands_migration` block.

- **Profile overlays** — new `--profile=microservice|bff|frontend` flag (default `microservice`; alias `service` → `microservice`). Picks one of three template overlays under `skills/sn-setup/templates/profile/<profile>/`:
  - `microservice` — backend service shape. Ships `docs/PROFILE.md`, `docs/API.md`, `docs/OBSERVABILITY.md`.
  - `bff` — Backend-for-Frontend shape (go-first; ts also supported). Ships `docs/PROFILE.md`, `docs/BFF-INTEGRATION.md`, `docs/DOWNSTREAMS.md`.
  - `frontend` — web UI shape (ts only). Ships `docs/PROFILE.md`, `docs/DESIGN.md`, `docs/ACCESSIBILITY.md`, `docs/BROWSER-MATRIX.md`.
- **Framework sub-flag** — `--framework=next|vite` (frontend profile only; default `next`). Drops `docs/FRAMEWORK.md` matching the choice from `skills/sn-setup/templates/framework/<framework>/`.
- **Lang × profile validation** — invalid combos (e.g. `--profile=frontend --lang=go`) fail fast with a usage error before any write.
- **State schema** — `.sn-init-state.json` now records `profile` + `framework` at the top level and inside `flags`. Older state files default to `microservice` / `next` on `--upgrade`.
- **Scaffolded `CLAUDE.md`** — adds a `## Profile` section pointing at `docs/PROFILE.md`.

- **Policy catalog** (PR1; supersedes B1.1 + B1.2). Composable, versioned policies under `skills/sn-setup/templates/policies/<slug>/`. Two new CLI sub-trees:
  - `sn-setup policy <list|show|apply|remove|upgrade|status|show-applied|history|lint>` — operate on the current project.
  - `sn-setup profile <list|show|add|remove|swap>` — edit profile defaults (auto-detect plugin source vs project-local).
  - Nine day-one policies spanning security, conventions, workflow, and observability.
  - Profile-bundled defaults applied automatically; override with `--policies=` (replace) or `--add-policies=` / `--remove-policies=` (delta).
  - State extensions: `applied_policies` + append-only `policy_history` in `.sn-init-state.json`. Legacy state files auto-migrate.

### References

- Closes part of backlog **B2.1** (BFF template profile); extends scope with `microservice` + `frontend` siblings and a `--framework` sub-flag.

## [1.0.0] — 2026-06-23

First stable release. The public surface — slash commands, scaffold tree, generated `/sn-*` commands + subagents, hook contracts, exit codes, `.sn-init-state.json` schema, Markdown report shape — is committed for the 1.x line. Breaking changes only behind a major bump.

### Public API (frozen for 1.x)

- **Entry slash commands**: `/sn-setup` and `/sn-session-report`. Flag tables in `commands/sn-setup.md` and `commands/sn-session-report.md` are the contract.
- **Generated commands** (18 `sn-*` under `.claude/commands/`): the slash names + their primary `SLUG=` / `REQ=` / `SPRINT=` arg conventions.
- **Subagents** (9 `sn-*` under `.claude/agents/`): the capability manifest fields (`tools`, `can_modify`, `can_delegate`, `chokepoint_gate`) and the spec-loop phase contract (impact → plan → decompose → execute + test → integrate → adversary → evaluate → curate → done).
- **Spec-loop promise strings**: `DONE: <SPRINT-id> triple-signal pass` / `BLOCKED: <SPRINT-id> <reason>`. Consumed by ralph-wiggum and similar autonomous loops.
- **Triple-signal exit gate**: `eval_score ≥ threshold` AND `integration.pass` AND `adversary.findings_resolved`.
- **Safety rails defaults**: `SN_MAX_CALLS_PER_HOUR=200`, `SN_MAX_TOKENS_PER_HOUR=2_000_000`, circuit breaker (3 no-progress OR 5 same-error → 5 min cooldown). Tunable via env.
- **Audit log location + shape**: `.sn-init/logs/exec-<date>-<session>.jsonl`, payloads > 2 KB spill to `blobs/<sha256-prefix>.txt`.
- **State file**: `.sn-init-state.json` — `template_version`, `lang`, `tier`, `flags`, `upgrades[]` — readable by the upgrade path.
- **Exit codes**: `0` ok, `2` usage, `3` target non-empty, `4` `.claude/` exists without state, `5` vault unwritable, `6` install failed, `7` validation failed, `8` template-version mismatch, `9` upstream dep missing, `99` internal.
- **Report Markdown shape**: frontmatter (`topic`, `bucket`, `origin_project`, `first_seen`, `last_updated`, `tags`, `window`) + Headline / Anomalies / Token breakdown / Top prompts (by tunability) / Repeated prompts / Subagent activity / Skill invocations / Cache breaks / Optimizations / See also. Tunability columns: `Score / Reason / Tokens / % proj / Cache-hit / Cache breaks / API calls / Subagent / Repeats / Prompt`.
- **Reason codes**: `repeat` / `subagent-heavy` / `loop-thrash` / `cache-miss` / `cold-start` / `low-output` / `expensive`.

### Headline (accumulated through 0.5.0 → 0.6.1, now declared stable)

- **Scaffolder `/sn-setup`** (since 0.1.0) — Tier 2 Agent SDK + Tier 3 Managed Agents projects across Go / Python / TypeScript. Auto-detects new vs add mode; atomic write; idempotent state.
- **18 generated slash commands + 9 subagents** scaffolded into every project under flat `sn-` prefix.
- **Spec-loop orchestrator** + triple-signal exit gate + `DONE:` / `BLOCKED:` promise strings.
- **Safety rails** (since 0.2.0) — rate limit, chokepoint gate (PreToolUse), circuit breaker.
- **Audit JSONL log** + payload-blob spill.
- **REQ schema validator** + REQ importers (md / txt / json / docx / pdf).
- **`/sn-verify`** + Agent SDK 12-rule conformance (6 mechanical, 6 prose via `sn-agent-sdk-reviewer`).
- **`/sn-session-report`** (since 0.5.0) — wraps Anthropic's upstream `session-report` analyzer, renders project-scoped Markdown into the Obsidian vault, auto-commits + pushes.
- **Tunability rewrite** (since 0.6.0) — top-prompts sorted by a 0-100 tunability_score (composite of repeat count, cache-miss share, subagent fan-out, API-call thrash, cache-break recurrence). Per-row reason code + suggested-action. Repeats grouped + dedup'd. Optimizations as a top-5 per-prompt punch list.
- **Vault knowledge buckets** — `projects/<project>/`, `global/shared/`, `global/tech-stacks/<project>/` with traceback frontmatter; `/sn-knowledge-{check,update,promote,demote,tech-matrix}`.
- **Git hooks** + commit-msg REQ-NNN gate + post-merge issue closer.

### Repo hygiene (since 0.6.1)

- Claude-delivered artifacts land under `temp/` and are gitignored (PRs #12 → #13 → #14).
- `docs/backlog.md` captures the microservices template-family gap analysis as a tiered, status-tracked checklist (PR #15).

### Tests

134 pytest cases. Ubuntu CI matrix on Python 3.11 / 3.12 / 3.13.

### Compatibility note

No breaking changes between 0.6.1 and 1.0.0 — this release is a stability declaration covering everything already shipped. Anything in `docs/backlog.md` Tier 2 / Tier 3 that would break a 1.x contract (e.g. plugin marketplace consumer model, BFF profile flag) will land behind a major bump to 2.0.0 if and when it changes the public surface.

## [0.6.1] — 2026-06-23

### Docs

- Cross-reference `/sn-session-report` (v0.6.0) across the remaining user-facing surfaces so the plugin no longer reads as scaffolder-only:
  - `WORKFLOW.md` — command-flow diagram extended with `/sn-session-report` after `/sn-sprint-done`; new `## 9. Session-usage analysis — /sn-session-report (v0.6.0+)` section with the reading guide (7 reason codes, Repeats as skill-candidate generator, Optimizations as per-prompt punch list, upstream-install dependency).
  - `skills/sn-setup/SKILL.md` — Companion-skill line pointing at `../session-report/SKILL.md` so Claude surfaces the second entry skill when `sn-setup` triggers.
  - `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — description, keywords, and tags advertise `session-report` + `observability`. Marketplace catalogs now show the plugin as a two-skill bundle.

No code or template changes. Tests still 134 green.

## [0.6.0] — 2026-06-23

### Fixed (caught in pre-release regression sweep)

- `/sn-session-report` fallback mode previously wrote to a triple-nested path `<cwd>/session-reports/projects/<project>/session-reports/<ts>.md` when no real Obsidian vault was configured (no `--vault`, no `$OBSIDIAN_VAULT`, no `.sn-init/knowledge` symlink). `resolve_vault_path` now returns `(path, is_fallback)`; in fallback mode the wrapper writes directly to `<cwd>/session-reports/<ts>.md`. Normal-vault behaviour unchanged. Surfaced during the v0.6.0 regression test (`make session-report` on a `--no-obsidian` scaffold).

### Added — `/sn-session-report` tunability enhancements

The session report now tells you **which prompts to tune**, not just which were expensive. Big prompts on hard tasks are fine; small prompts repeated 30× cold-cache are bleeding. The enhancements surface that distinction directly in the Markdown output and in the underlying renderer's per-prompt augmentation.

- **`tunability_score` (0-100) per prompt** — composite of repeat count, cache-miss share, subagent fan-out, API-call thrash vs project median, and cache-break recurrence. Top prompts now sort by this score (not raw tokens), so the table's top row is the highest-ROI tuning target rather than just the most-expensive one.
- **`reason` code per prompt** — one of `repeat`, `subagent-heavy`, `loop-thrash`, `cache-miss`, `cold-start`, `low-output`, `expensive`. Priority-ordered: the dominant signal wins. Renders as a code-formatted column in the top-prompts table and as the heading of every per-prompt optimization callout.
- **`cache-hit %` per prompt** — `cache_read / total_input * 100` per row. Surfaces which specific prompts blew cache (vs the global project cache-hit % in the headline).
- **`cache breaks` count per prompt** — counts cache-break events whose `context[here:true]` entry matches the prompt by `(ts, text)`. Cold-start cost made concrete per row.
- **`repeats` count per prompt + dedicated Repeats section** — prompts grouped by `_normalize_prompt_text` (lowercased, whitespace-collapsed, trailing-punctuation-stripped, first 80 chars). Top-prompts table collapses repeated rows into one (token totals summed, repeat count surfaced). New "Repeated prompts (skill candidates)" section lists every group with count ≥ 3 sorted by total spend — these are the highest-ROI tuning targets.
- **Per-prompt `suggested_action`** — one-line recipe keyed off the reason code: `repeat` → promote to a `/sn-<slug>` skill or CLAUDE.md macro; `subagent-heavy` → scope fewer parallel agents; `loop-thrash` → tighter plan / lower `max_turns`; `cache-miss` → pin CLAUDE.md before commits; `cold-start` → group related work, avoid `/clear` mid-task; `low-output` → targeted Read instead of spraying files; `expensive` → split / right-size.
- **Optimizations section reshaped** — was 1-4 generic `> [!tip]` callouts. Now top-5 highest-tunability prompts as `> [!tip] **[<score>] \`<reason>\`** — <prompt-text> (<tokens> tokens). <suggested-action>`. Reads as a punch list.

### Tunability heuristics + thresholds

| Constant | Default | Used by |
|---|---|---|
| `REPEAT_MIN_COUNT` | 3 | Repeats section + `repeat` reason code + `_REASON_TO_ACTION["repeat"]` |
| `LOW_OUTPUT_RATIO` | 0.001 (0.1%) | `low-output` reason code |
| `PROMPT_CACHE_TARGET` | 60.0% | `cache-miss` reason code (note: project-wide target is still 85%) |

### Tests

11 new pytest cases (123 → 134):

- `test_session_report_resolve_vault_path_signals_fallback` — the new `(path, is_fallback)` return-shape across all 3 resolution branches.
- `test_session_report_fallback_writes_flat_path` — fallback writes to `<cwd>/session-reports/<ts>.md` and never creates a `projects/` subtree.

- `test_session_report_normalize_prompt_text_collapses_variants` — whitespace/case/punctuation normalization for repeat grouping.
- `test_session_report_compute_repeat_groups_counts` — group counting + empty filter.
- `test_session_report_cache_hit_pct` — formula correctness for high/low/empty input.
- `test_session_report_cache_break_count_links_by_ts_text` — `(ts, text)` matching against `here:true` context.
- `test_session_report_determine_reason_priority` — reason priority order across all 7 codes.
- `test_session_report_tunability_score_bounded` — worst-case ≥ 80, clean prompt < 10, always ∈ [0, 100].
- `test_session_report_suggested_action_repeat_inlines_count` — repeat suggestions surface the count.
- `test_session_report_render_includes_tunability_columns` — Markdown output has the new columns + sections + reason codes.
- `test_session_report_dedup_collapses_repeated_rows` — table shows ONE row per logical intent even when the prompt appears N times in the analyzer payload.

Plus the 2 fallback-path regressions listed above.

### Fixture

`tests/fixtures/session-report-payload.json` extended with synthetic prompts that exercise every reason code: `cache-miss` (`/clear`), `loop-thrash` (`scan this project…`), `repeat` (`commit and push` × 3), `subagent-heavy` (`build the whole feature…`), plus a cross-project prompt for filter verification.

### Verified end-to-end against real data

Real 7d run on the user's transcripts surfaced the actual top tuning candidates: `all of them` (4×, 44.8M tokens, score 37), `ok` (3×, 23.9M tokens, score 24) — combined 68.7M wasted tokens promotable to a skill or macro.

## [0.5.2] — 2026-06-22

### Fixed

- Scaffolded `Makefile` — `make sprint-status` returned exit code 2 (and tripped Make's error reporting) whenever `docs/sprints/completed/` was empty. The bash `for` loop iterated over the literal unmatched glob, the trailing `[ -d ]` test failed, and the recipe inherited rc 1. The fix prepends `shopt -s nullglob` so unmatched globs collapse to zero iterations; both ACTIVE + COMPLETED loops now return 0 cleanly. Affects every freshly-scaffolded project regardless of lang.

### Tests

- 1 new pytest case (122 → 123): `test_sprint_status_returns_zero_when_completed_empty` — scaffolds a fresh project and asserts `make sprint-status` returns rc 0 even when both sprint dirs are empty.

### Regression-test sweep

Full end-to-end pass against the plugin + scaffolded projects (py, ts, go):

| Surface | Status |
|---|---|
| 122-case pytest | ✓ green |
| Plugin `/sn-session-report --dry-run` | ✓ writes correct frontmatter |
| Scaffolder (`/sn-setup demo-{py,ts,go}`) | ✓ tree present, scripts copied incl. `session_report.py`, `session_report_render.py` |
| `make help` | ✓ ~30 targets |
| `make verify` (Agent SDK 6 mechanical rules) | ✓ py/ts: `1 file(s) OK`, go: `2 file(s) OK` |
| `make req-validate` (PyYAML missing case) | ✓ friendly skip |
| `make req-new SLUG=…` | ✓ writes REQ-NNN |
| `make sprint-new SLUG=…` / `sprint-add` / `sprint-remove` / `sprint-done` | ✓ |
| `make safety-status` | ✓ JSON shape |
| `make sprint-status` | ✗ rc 2 on empty — **fixed in this release** |

## [0.5.1] — 2026-06-22

### Fixed

- `/sn-session-report` — **vault directory name mismatch**. The renderer's `_human_project()` derived the display name from the lossy encoded project key (the upstream analyzer encodes both `/` and `_` as `-`), so a cwd of `setup_project_plugin` produced an output directory of `setup-project-plugin` (dash) and orphaned reports next to the real `projects/setup_project_plugin/` (underscore) folder. The wrapper now uses `Path.cwd().name` (the actual directory basename) for both the vault path and the frontmatter; the encoded form is kept only for matching against the analyzer's `by_project` JSON keys. The renderer accepts a new keyword-only `project_name` argument; `_human_project` is retained as a fallback for callers that don't pass one.
- `/sn-session-report` — **vault commit skipped when `.git` is a parent of the resolved vault path**. The previous `commit_and_push` only checked `vault_root / ".git"`, but Obsidian vaults commonly nest the knowledge tree under a repo root (e.g. `<repo>/AllSharedKnowledge/knowledge/`). The new `find_git_root()` walks up from the resolved vault path until it finds the enclosing `.git`; `git -C` is then invoked against that root with relative paths computed from it. Falls back to a `[commit] no enclosing git repo found` notice when no ancestor has `.git`.

### Tests

- 2 new pytest cases (120 → 122):
  - `test_session_report_render_uses_explicit_project_name` — confirms `project_name` kwarg overrides the lossy derivation in frontmatter, body, tags.
  - `test_session_report_find_git_root_walks_up` — exercises `find_git_root` for the nested-vault, root, and no-repo cases.

## [0.5.0] — 2026-06-22

### Added

- `/sn-session-report` slash command (+ supporting skill at `skills/session-report/SKILL.md`) — renders Claude Code session usage (tokens, cache, subagents, skill invocations, cache-break events, expensive prompts) for the **current project** as a Markdown report and writes it into the Obsidian vault at `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md`. Auto-commits + pushes the vault per the knowledge auto-mirror rule.
- `scripts/session_report.py` — thin Python wrapper. Detects the upstream analyzer (4-step resolution: `--analyzer` flag → `$SN_SESSION_REPORT_ANALYZER` env → `~/.claude/plugins/marketplaces/*/plugins/session-report/.../analyze-sessions.mjs` glob → recursive search). Runs `node <analyzer> --json --since <window>`. Filters by project. Resolves vault path (`--vault` → `$OBSIDIAN_VAULT` → `<repo>/.sn-init/knowledge` → `<repo>/session-reports/`). Atomic write + `README.md` index update + git commit/push.
- `scripts/session_report_render.py` — pure stdlib renderer. `render_markdown(payload, project, window, today)` builds the Markdown body (frontmatter, headline table, anomalies, token breakdown, top prompts, subagent activity, skill invocations, cache breaks, optimizations, see-also). Anomaly heuristics: cache-hit < 85%, single prompt > 2% of total, subagent > 1M tokens / call, cache breaks ≥ 3 (clustered).
- Scaffold-side: every project generated by `/sn-setup` now also ships `/sn-session-report` (template under `skills/sn-setup/templates/claude/commands/sn-session-report.md` + `claude/skills/session-report/SKILL.md` + `managed-agent-base/scripts/session_report.py` + `session_report_render.py`) plus a `make session-report` Make target.
- `tests/fixtures/session-report-payload.json` — small synthetic analyzer JSON for fixture-driven renderer tests.
- `scripts/errors.py`: `EXIT_MISSING_DEP = 9` + `MissingAnalyzerError(exit_code=9)`.

### Changed

- Depends on the upstream Anthropic `session-report` plugin (`anthropics/claude-plugins-official`) being installed; the wrapper prints an install hint and exits `9` when the analyzer can't be located. **No code is vendored** — the analyzer lives upstream.
- `COMMANDS.md` totals bumped: 19 → **20** slash commands (`/sn-setup` + `/sn-session-report` are now both plugin-level entries, 18 generated commands unchanged). Subagent count stays at 9.

### Tests

- 12 new pytest cases (108 → 120): scaffold-tree presence (plugin + template copies), Makefile target wiring, error-class shape, renderer fixture coverage (headline math, anomaly text, cache-break rows, caveat strings), unknown-project graceful render, analyzer locate via env override / missing-file path, missing-analyzer exit-code `9`, project-key encoding (`/` and `_` → `-`), suffix-match key resolution.

## [0.4.0] — 2026-06-22

### Added

- `docs/principles/agent-sdk-best-practices.md` — 12-rule checklist for every scaffolded Agent SDK app. Sourced from Anthropic's [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview). Six rules are mechanically checked by `/sn-verify`; six need prose analysis from `sn-agent-sdk-reviewer`.
- `/sn-verify` slash command + scaffolded `scripts/verify_agent_sdk.py` + `make verify` Make target. Checks `src/agent.{py,ts,go}` against rules 1, 2, 3, 5, 6, 9 with `::error file=…::` annotations for CI.
- `sn-agent-sdk-reviewer` subagent (`tools: [Read, Grep]`, `can_modify: []`). Reviews rules 4, 7, 8, 10, 11, 12 (permission_mode, sessions, MCP vetting, WebSearch necessity, streaming, error handling). Read-only, ad-hoc — not in `PHASE_TO_SUBAGENT`; invoke on demand.
- Post-scaffold banner suggests three verify paths in order: (1) read the doc, (2) run `/sn-verify`, (3) optionally install Anthropic's official `agent-sdk-dev` plugin. Skipped for `--lang=go` since Anthropic only ships verifiers for py + ts.
- `WORKFLOW.md` new `## Verify Agent SDK code against best practices` section covering mechanical + prose + third-party check paths.

### Changed

- Scaffolded `src/agent.py` (py overlay) and `src/agent.ts` (ts overlay) updated to be compliant with the rules they ship — `model="${model}"` keyword and `setting_sources=["project"]` (py) / `settingSources: ["project"]` (ts) added. A new test (`test_verify_agent_sdk_passes_on_compliant_py_overlay`) drives `python3 scripts/verify_agent_sdk.py` against a fresh scaffold and asserts rc 0; future overlay drift surfaces immediately.
- `COMMANDS.md` totals bumped 18 → 19 slash commands (+`/sn-verify` family "Verification"), 8 → 9 subagents (+`sn-agent-sdk-reviewer` ad-hoc).
- README + CONTRIBUTING test counts bumped 98 → 110.

## [0.3.0] — 2026-06-22

### Added

- `.github/workflows/release.yml` — on `v*.*.*` tag push, extracts the matching `## [<version>]` block from `CHANGELOG.md` and creates a GitHub Release with those notes. Falls back to `--generate-notes` when no matching section is found.
- `.github/dependabot.yml` — weekly check of GitHub Actions versions; opens PRs with `chore(...)` commit messages and `dependencies` / `github-actions` labels.
- `pytest-cov` in CI plus `codecov/codecov-action@v4` upload (Python 3.13 only). README gains a Codecov coverage badge alongside the CI + License badges.
- `.pre-commit-config.yaml` — YAML / TOML / JSON / merge-conflict / large-file checks, ruff on `scripts/` + `tests/` with `--fix`, and a `pre-push` stage that runs the full pytest suite. CONTRIBUTING.md updated with `pre-commit install --hook-type pre-commit --hook-type pre-push`.
- `.harness/invariants/` seed examples — three concrete invariants ship now instead of an empty README:
  - `capability-manifest-respected.md` — every Edit/Write hits a path inside the active subagent's `can_modify:` glob list.
  - `state-file-monotonic.md` — `.sn-init/workflow-state.json` `phase_history` is append-only with monotonic timestamps.
  - `audit-log-complete.md` — every `PreToolUse` audit record has a matching `PostToolUse` with the same `tool_use_id`.
- REQ schema validation — `docs/requirements/req-schema.json` (Draft 2020-12) plus `scripts/req_validate.py` that walks every active + assigned REQ file, parses YAML frontmatter, validates it. Optional `PyYAML` + `jsonschema` deps; missing deps print an install hint and exit 0 so contributors who haven't synced their venv aren't blocked. New `make req-validate` target.
- Lang-overlay smoke tests — `test_integration_scaffold_runs_make_test_go` and `test_integration_scaffold_runs_make_test_ts` extend the existing Python integration test to Go and TypeScript. Scaffold + `make -f Makefile.<lang> test` must reach the lang toolchain entry-point (`go test` / `npm test`) without shell mangling.
- `.github/workflows/ci.yml` — GitHub Actions workflow runs `pytest` on push and pull request across Python 3.11/3.12/3.13. README gains CI + License badges.
- `LICENSE` file — explicit MIT text (previously only declared in `plugin.json`).
- `CONTRIBUTING.md` — code layout, dev workflow, commit-message convention, recipe for adding new `sn-*` commands or subagents, bug-report template.
- `.github/PULL_REQUEST_TEMPLATE.md` — auto-populates PR description with scope / tests / docs / migration checklists.
- Orchestrator promise emission — `scripts/orchestrator.py` and the scaffolded `templates/managed-agent-base/scripts/orchestrator.py` now emit `DONE: <SPRINT-id> triple-signal pass` on full-pass and `BLOCKED: <SPRINT-id> <reason>` on phase failures / breaker trips. Makes the `WORKFLOW.md` "Autonomous mode" pattern with `/ralph-loop` real — Ralph can now pattern-match the orchestrator's stdout instead of relying on documented-only behaviour.
- 6 new tests (96 total): `test_makefile_preserves_double_dollar_shell_vars`, `test_makefile_targets_runnable`, `test_integration_scaffold_runs_make_test`, `test_orchestrator_emits_done_promise_on_pass`, `test_orchestrator_emits_blocked_promise_on_phase_failure`, `test_orchestrator_promise_strings_match_ralph_contract`.

### Fixed

- `_substitute` in `scripts/sn_init.py` no longer runs `string.Template.safe_substitute` on files that don't reference one of the known context keys (`${name}`, `${lang}`, `${model}`, `${tier}`, `${system_prompt}`, `${date}`). Previously any file with `${...}` in it triggered substitution, which halved every `$$VAR` shell escape to `$VAR` and silently broke every `make` recipe (most visibly `make req-new SLUG=...`, `make sprint-add SPRINT=... REQ=...`, `make sprint-concurrent SPRINT=... N=...`). The Makefile contains `$${next:-000}` for shell-side default expansion, which was enough to trip the original heuristic.
- `CLAUDE.local.md` template — `"initial scaffold from sn-init"` → `"initial scaffold from sn-setup"` (last stale `sn-init` user-facing branding).

### Chore

- Removed leftover `~/.claude/plugins/cache/temp_local_*` entries that surfaced the `setup-project-plugin:sn-setup` skill twice in autocomplete.

## [0.2.0] — 2026-06-21

### Renamed

- GitHub repo `init_project_plugin` → `setup_project_plugin` (`gh repo rename`, local remote URL updated).
- Plugin manifest name `init-project-plugin` → `setup-project-plugin`.
- Entry slash command `/sn-init` → `/sn-setup` (`commands/sn-init.md` → `commands/sn-setup.md`; frontmatter `name:` follows).
- Skill directory `skills/sn-init/` → `skills/sn-setup/` (151 files via `git mv`).
- Vault project bucket `projects/init_project_plugin/` → `projects/setup_project_plugin/`; topic `sn-init-skill` → `sn-setup-skill`; per-file frontmatter `origin_project:` and `bucket:` updated.

### Kept (internal — stable across the rename)

- `scripts/sn_init.py` module name (so `import sn_init` keeps working).
- `.sn-init/` runtime directory (logs, worktrees, knowledge symlink).
- `.sn-init-state.json` scaffold state file.
- `sn-init/pre-REQ-NNN-<ts>` git tag prefix for snapshot rollback.

### Added

- `COMMANDS.md` — top-level reference for every `sn-*` slash command (1 entry + 17 generated) and the 8 `sn-*` subagents dispatched by the spec-loop orchestrator. Includes per-command usage, exit codes, Make-target mirror table, and a migration recipe for moving older scaffolds onto the current `sn-` flat layout.
- `scripts/claude_md_merger.py` — pure `merge(existing, template, *, overwrite_sections)` for section-aware merge of `CLAUDE*.md` during `--upgrade --rename-ns`. Existing sections keep, template-only sections append, whitelist (`## Tracking`, `## What sn-setup created`) overwrites.
- `--rename-ns` flag on `/sn-setup --upgrade`: migrates scaffolded projects from any of three legacy layouts (bare flat names, the mid-2026 `sn:` colon namespace, the original `sn-init` branding) to the current `sn-<name>` flat layout. Rewrites `/cmd` and `/sn:cmd` references in `Makefile`, `scripts/orchestrator.py`, and every command doc. Refuses without `--upgrade`. State records `renamed[]`, `rewritten[]`, `merged_files[]` in `.sn-init-state.json`. Backups land at `<file>.pre-upgrade-<UTC-ts>.bak`.
- 6 new tests (90 total, all green): merger preserve/overwrite, `--rename-ns` requires `--upgrade`, dry-run plan output, applied migration smoke, no `workflow/` subdir in plan.

### Changed

- Generated commands and subagents land at the flat `sn-` prefix layout (`.claude/commands/sn-<name>.md`, `.claude/agents/sn-<name>.md`). Replaces the brief mid-2026 `sn:` colon namespace (`commands/sn/<name>.md` → `/sn:<name>`), which was rolled back because `/`-autocomplete groups dashes alphabetically but splits namespaces by `:`.
- `scripts/sn_init.py`: `_plan_new_files` recognises the flat `sn-<file>.md` layout; `_rewrite_ns_refs` writes `/sn-` and `"sn-"` (value-only regex preserved so phase keys named after agents aren't double-prefixed); `_plan_rename_ns` handles all legacy layouts in one pass.
- `scripts/gen_subagent_index.py`: walks via `rglob` and trusts the frontmatter `name:` field; subdir → namespace derivation reverted.
- `scripts/sn_init.py` argparse `prog="sn-setup"` and stdout banner strings (`sn-setup: new scaffold complete`, `sn-setup: upgraded`).
- `TEMPLATE_VERSION` bumped to `2026.06.23`.
- Template scaffold base `.gitignore`: recursive `**/.DS_Store` and `**/Thumbs.db` patterns so OS clutter is ignored in every subdirectory of a scaffolded project.

### Fixed

- Untracked `.DS_Store` at the plugin repo root — the file was committed before the gitignore covered it.

### Vault (`obsidian_sharedknowledge`)

Knowledge mirror updates that ship alongside this plugin release. Vault commits are in a separate repo (`siripol/obsidian_sharedknowledge`).

- `eeba428` (`chore: untrack Obsidian UI state, extend gitignore to nested vaults`) — untracks `AllSharedKnowledge/.obsidian/workspace.json` and extends `.gitignore` with `**/.obsidian/workspace*`, `**/.obsidian/cache`, `**/.trash/` so nested vaults are covered automatically.
- `9755b30` (`knowledge: rename project bucket init_project_plugin → setup_project_plugin (batch 15)`) — folder rename via `git mv`, frontmatter `origin_project:` + `bucket:` rewritten in 11 topic files, `sn-init-skill.md` → `sn-setup-skill.md` with a naming-history table, vault README index updated to `[[sn-setup-skill]]`, `implementation-log.md` Batch 15 entry recording the rename.
- `9464705` (`knowledge: roll back sn: colon namespace to sn- flat prefix (init_project_plugin batch 14)`) — `sn-namespace.md` rewritten as the flat `sn-` decision; `sn-init-skill.md` Generated-names table flipped to `.claude/commands/sn-<name>.md`; `implementation-log.md` Batch 14 entry.
- `6a7a236` (`knowledge: sn: namespace + claude-md merger (init_project_plugin batch 13)`) — adds `sn-namespace.md` and `claude-md-merger.md` topics, updates `sn-init-skill.md` to surface the generated `/sn:` names, vault README index updated, `implementation-log.md` Batch 13 entry.

## [0.1.0] — 2026-06-21

### Added

- Plugin skeleton: `.claude-plugin/plugin.json`, `commands/sn-init.md`, `hooks/README.md`, `skills/sn-init/SKILL.md`.
- `scripts/{sn_init,errors,sn_logging}.py` — argv parse, mode auto-detect, atomic tmp-dir + mv, `.sn-init-state.json` idempotent re-run anchor.
- Mode auto-detect: empty cwd OR `name` → new scaffold; non-empty cwd → patch `.claude/` only (add mode).
- Lang overlays: `lang/go/`, `lang/py/`, `lang/ts/` with real `claude-agent-sdk` / `@anthropic-ai/sdk` / `anthropic-sdk-go` wire-up, `beta.sessions` client, and a working `mcp_server/main.{py,ts,go}` MCP stub.
- Audit hooks `.claude/hooks/audit.{sh,py,ts}` writing JSONL to `.sn-init/logs/exec-<date>-<session>.jsonl` (blob spill >2KB to `blobs/<sha256-prefix>.txt`). Registered across `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `SessionEnd`, `Stop`.
- Spec-loop orchestrator (`scripts/orchestrator.py`): phases `impact → plan → decompose → execute → test → integrate → adversary → evaluate → curate → done`, `PHASE_TO_SUBAGENT` mapping, state persisted to `.sn-init/workflow-state.json`.
- 13 subagents grouped into 3 buckets — default (`code-reviewer`, `test-writer`), optional (`doc-writer`, `security-auditor`, `planner`), workflow (`task-decomposer`, `task-executor`, `task-tester`, `integration-tester`, `evaluator`, `adversary`, `knowledge-curator`, `impact-analyzer`).
- 22 slash commands in the scaffold: `claude-local-edit/show`, the subagent-shortcut quintet (`review/test/doc/audit/plan`), and the workflow set (`sprint-*`, `req-*`, `knowledge-*`, `gh-import`).
- `.harness/` scaffold — `chokepoints.yaml`, `rules/`, `invariants/`, `normal-forms/`, `proof-bundle-template.md`. PreToolUse `chokepoint-gate.{sh,py,ts}` hooks read the YAML and block Edit/Write to gated paths.
- REQ importers (`scripts/importers/{md,txt,json,docx,pdf}.py`) + `scripts/req_import.py` CLI that auto-increments REQ-NNN across all dirs.
- Obsidian client (`scripts/obsidian_client.py`) with MCP probe → filesystem fallback, gated by `--obsidian-mcp=auto|on|off`. Writes to `projects/<project>/`, `global/shared/`, `global/tech/<project>/` per `--obsidian-knowledge` scope.
- Safety rails (`scripts/safety.py`): hourly rolling rate limit (`SN_MAX_CALLS_PER_HOUR=200`, `SN_MAX_TOKENS_PER_HOUR=2_000_000`), circuit breaker (3 cycles w/o progress → pause, 5 same-error cycles → rollback, 5-minute cooldown), CLI for status / reset / trip.
- Make targets: `worktree-*`, `safety-*`, `gh-close`, `sprint-concurrent`, `subagent-index`, `orchestrate`, `help` (self-documenting via `## description` annotations).
- Git hooks scaffold (`.githooks/{commit-msg,post-merge}`): commit-msg requires REQ-NNN unless prefixed `chore:` / `wip:` / `docs:`; post-merge closes GitHub issue for `req/REQ-NNN` branches.
- `--upgrade` flag: detects `template_version` mismatch in state file, adds missing template files, never overwrites edits, records `upgrades[]` history.
- `scripts/gen_subagent_index.py`: regenerates `docs/design-docs/subagents.md` from `.claude/agents/*.md` frontmatter, preserves custom appendices after the `<!-- sn-init:auto-table -->` marker.
- 84 pytest cases (grows to 90 in `0.2.0`).
- Obsidian knowledge vault bootstrap — 19 starter topics across `projects/<project>/`, `global/shared/`, `global/tech/<project>/` with traceback frontmatter (`origin_project`, `origin_req`, `origin_sprint`, `first_seen`, `last_updated`) and `[[wiki-links]]`.

### Notes

- Tier 1 standalone is out of scope for this plugin. Tier 2 (Agent SDK) and Tier 3 (Managed Agents) ship together by default (`--tier=both`).
- Default model: `claude-opus-4-8` with `thinking: {type: "adaptive"}`.
