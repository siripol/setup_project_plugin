# Changelog

All notable changes to `setup-project-plugin` (formerly `init-project-plugin`).

Format loosely follows [Keep a Changelog](https://keepachangelog.com/). Versions are taken from `.claude-plugin/plugin.json`. Dates are UTC.

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
