# Commands — `sn-*` reference

Every plugin-provided slash command starts with `sn-`. `/sn-setup` and `/sn-session-report` are entry commands at the plugin level. The other 18 generated commands are scaffolded into a target project under `.claude/commands/sn-<name>.md` by `/sn-setup` and only show up inside scaffolded projects.

Eight matching subagents live under `.claude/agents/sn-<name>.md` and are dispatched by the spec-loop orchestrator; users normally do not invoke them directly.

## Quick map

| Family | Count | Slash commands |
|---|---|---|
| Entry | 2 | `/sn-setup` `/sn-session-report` |
| Sprint lifecycle | 6 | `/sn-sprint-new` `/sn-sprint-add` `/sn-sprint-remove` `/sn-sprint-run` `/sn-sprint-done` `/sn-sprint-status` |
| REQ lifecycle | 5 | `/sn-req-new` `/sn-req-import` `/sn-req-rollback` `/sn-req-resume` `/sn-req-replay` |
| Knowledge (Obsidian) | 5 | `/sn-knowledge-check` `/sn-knowledge-update` `/sn-knowledge-promote` `/sn-knowledge-demote` `/sn-knowledge-tech-matrix` |
| GitHub | 1 | `/sn-gh-import` |
| Verification | 1 | `/sn-verify` |

Total: **20 slash commands** (2 entry + 18 generated) + **9 subagents**.

---

## Entry command

### `/sn-setup [name] [flags]`

Scaffold a Claude-powered project, or add `.claude/` scaffolding into an existing repo. Auto-detects mode from the current working directory.

**Modes**
- **new** — `name` given OR cwd is empty → creates a full project tree at `<cwd>/<name>/` (or in cwd if empty).
- **add** — cwd non-empty and no `name` → writes only `.claude/` into cwd. Idempotent — patches missing files using `.sn-init-state.json`.

**Main flags** (see `commands/sn-setup.md` for the complete table)

| Flag | Default | Purpose |
|---|---|---|
| `--lang=go\|py\|ts` | `go` | Stack overlay |
| `--tier=2\|3\|both` | `both` | Anthropic tier (Tier 1 standalone is out of scope) |
| `--license=none\|MIT\|Apache-2.0` | `none` | Write a `LICENSE` file when not `none` |
| `--no-git` | git on | Skip `git init` + first commit in new mode |
| `--install` | off | Run dep install + `ant agents apply` after scaffold |
| `--no-ci` | CI on | Skip `.github/workflows/ci.yml` |
| `--devcontainer` | off | Write `.devcontainer/devcontainer.json` |
| `--obsidian[=VAULT_PATH]` / `--no-obsidian` | on | Obsidian tracking note. Vault resolution: explicit → `$OBSIDIAN_VAULT` → `<target>/docs/exec-plans/active/` |
| `--obsidian-knowledge=project\|global` | `project` | Default scope of generated knowledge facts |
| `--obsidian-mcp=auto\|on\|off` | `auto` | Backend (MCP server or filesystem) |
| `--workflow=spec-loop\|none` | `spec-loop` | Spec-driven autonomous dev loop scaffold |
| `--prompt="..."` | placeholder | Seed `agents/main.yaml` system block |
| `--upgrade` | off | Patch-only: pull missing template files into an existing scaffold, bump `template_version`. Never overwrites edited files |
| `--dry-run` | off | Print planned tree + diffs, no FS writes |
| `--verbose` | off | Per-step log to target's `.sn-setup.log` |

**Examples**

```bash
# New project, default Go stack
/sn-setup demo

# Python, no git, no CI
/sn-setup demo --lang=py --no-git --no-ci

# Add .claude/ to existing repo
cd existing-repo && /sn-setup

# Pull newer template files into an existing scaffold
cd existing-sn-setup-project && /sn-setup --upgrade

# Preview an upgrade without writing
/sn-setup --upgrade --dry-run
```

**Exit codes**: `0` ok, `2` usage / bad flag, `3` target dir non-empty + name given, `4` `.claude/` exists in add mode without state file, `5` Obsidian vault unwritable (only when explicit), `6` `--install` failed after retries, `7` validation gate failed, `8` template version mismatch, `9` upstream dep missing, `99` internal error.

---

### `/sn-session-report [since] [flags]`

Render a Markdown session-usage report for the current project into the Obsidian vault. Wraps Anthropic's upstream `session-report` analyzer (`analyze-sessions.mjs`), filters its JSON to the current project, writes Markdown to `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md`, then commits + pushes the vault.

Since v0.6.0 the report is tuned for **actionability**: top-prompts table is sorted by a 0-100 `tunability_score` (composite of repeat count, cache-miss share, subagent fan-out, API-call thrash, cache-break recurrence), each row carries a `reason` code (`repeat` / `subagent-heavy` / `loop-thrash` / `cache-miss` / `cold-start` / `low-output` / `expensive`), repeated prompts are surfaced in a dedicated section, and Optimizations is a per-prompt punch list with a concrete suggested action per row. See `commands/sn-session-report.md` for the full reading guide.

**Flags**

| Flag | Default | Description |
|---|---|---|
| `[since]` (positional) | `7d` | Window: `24h`, `7d`, `30d`, `all`, or ISO timestamp. |
| `--analyzer=<path>` | auto | Override the analyzer path (else `$SN_SESSION_REPORT_ANALYZER` → glob under `~/.claude/plugins/`). |
| `--vault=<path>` | auto | Override vault root (else `$OBSIDIAN_VAULT` → `<repo>/.sn-init/knowledge` → `<repo>/session-reports/`). |
| `--project=<key>` | auto | Override the analyzer's encoded project key. |
| `--dry-run` | off | Print would-be report to stdout, no file or git writes. |
| `--no-push` | off | Write + commit, but skip `git push`. |
| `--verbose` | off | Per-step trace to stderr. |

**Examples**

```bash
# Default: last 7 days, write to vault, commit + push
/sn-session-report

# Last 24 hours, dry-run preview
/sn-session-report 24h --dry-run

# Write to vault but skip git push
/sn-session-report 7d --no-push
```

**Dependencies**: `node` ≥ v18 on `PATH` + the upstream `session-report` plugin installed (`/plugin marketplace add anthropics/claude-plugins-official` then `/plugin install session-report@claude-plugins-official`). Missing analyzer → rc `9` with install hint.

**Exit codes**: `0` ok, `2` usage, `5` vault unwritable, `9` analyzer not found, `99` internal.

---

## Sprint lifecycle commands

### `/sn-sprint-new SLUG=<slug>`

Create a new `SPRINT-NNN-<slug>/` folder under `docs/sprints/active/` with the standard subfolders (`requirements/`, `exec-plans/`, `tasks/`, `proof/`) and a `sprint.md` manifest seeded from `docs/sprints/template.md`. Sprint counter auto-increments from existing folders. Status starts as `planning`.

```bash
/sn-sprint-new SLUG=auth-rev
# → docs/sprints/active/SPRINT-001-auth-rev/
```

### `/sn-sprint-add SPRINT=<id> REQ=<id>`

Move a REQ from `docs/requirements/active/` into a sprint's `requirements/` subfolder. Appends the REQ id to the sprint's `reqs:` list in `sprint.md`. Preserves traceback frontmatter. Refuses if the REQ is already in a different sprint.

```bash
/sn-sprint-add SPRINT=SPRINT-001 REQ=REQ-003
```

### `/sn-sprint-remove SPRINT=<id> REQ=<id>`

Reverse of `/sn-sprint-add` — move a REQ back to `docs/requirements/active/`. Refuses if the sprint is `running` or `completed`.

```bash
/sn-sprint-remove SPRINT=SPRINT-001 REQ=REQ-003
```

### `/sn-sprint-run SPRINT=<id>`

Execute a sprint. The spec-loop driver:

1. Reads the sprint folder + REQs.
2. Runs `sn-impact-analyzer` → writes `impact.md`. If `has_major: true`, halts and asks the user (proceed / edit / cancel).
3. Tags pre-REQ git snapshots: `sn-init/pre-REQ-NNN-<ts>`.
4. For each REQ (topo-sorted by `requires:`): `sn-planner → sn-task-decomposer → (per task: sn-task-tester + sn-task-executor) → sn-integration-tester → sn-adversary → sn-evaluator`.
5. **Triple-signal exit gate**: `eval >= threshold AND integration.pass AND adversary.findings_resolved`.
6. On all-pass: `doc-writer` + `sn-knowledge-curator`. Run `/sn-sprint-done` to archive.

State persists to `.sn-init/workflow-state.json`. `/sn-req-resume` resumes after a crash.

```bash
/sn-sprint-run SPRINT=SPRINT-001
```

### `/sn-sprint-done SPRINT=<id>`

Archive a completed sprint by moving `docs/sprints/active/SPRINT-NNN-*/` to `docs/sprints/completed/`. Refuses if any REQ in the sprint hasn't reached `eval pass`. Triggers `sn-knowledge-curator` to refresh the Obsidian buckets.

```bash
/sn-sprint-done SPRINT=SPRINT-001
```

### `/sn-sprint-status`

No args. Print a table of every sprint (active + completed) with REQ counts, status, owner, and last update.

```
SPRINT    SLUG          STATUS     REQs  COMPLETED  OWNER
001       auth-rev      running    3     1/3        alice
002       billing       planning   2     0/2        bob
```

---

## REQ lifecycle commands

### `/sn-req-new SLUG=<slug>`

Scaffold a new `REQ-NNN-<slug>.md` under `docs/requirements/active/`. Counter is auto-incremented from the max REQ-NNN across `docs/requirements/active/` and all sprint dirs. Template body comes from `docs/requirements/template.md`.

```bash
/sn-req-new SLUG=login-flow
# → docs/requirements/active/REQ-007-login-flow.md
```

### `/sn-req-import FILE=<path>`

Convert an `md` / `txt` / `json` / `docx` / `pdf` source into a REQ file. Runs `python scripts/importers/<ext>.py FILE` and writes `docs/requirements/active/REQ-<next>-<slug>.md`. Extracted: title, acceptance bullets, sources, priority hint. Review and edit before assigning the REQ to a sprint.

```bash
/sn-req-import FILE=docs/external-spec.pdf
```

### `/sn-req-rollback REQ=<id>`

Reset the working tree to the pre-REQ git snapshot tag created by `/sn-sprint-run`. Effectively:

```bash
git reset --hard $(git tag | grep ^sn-init/pre-${REQ}- | sort -r | head -1)
```

Aborts if no matching tag exists. Use after a failed sprint to start fresh from the pre-REQ baseline.

```bash
/sn-req-rollback REQ=REQ-003
```

### `/sn-req-resume`

No args. Reads `.sn-init/workflow-state.json` to find the active REQ + last in-progress phase, then re-enters the orchestrator at that step. Subagent reruns are idempotent — the state file tracks completion per phase.

```bash
/sn-req-resume
```

### `/sn-req-replay REQ=<id>`

Re-run a completed REQ's tasks on a throwaway `replay/REQ-NNN` branch for a regression check. Creates the branch from the pre-REQ snapshot tag, replays each TASK via executor + tester, reports pass/fail. Useful to verify a completed REQ still passes against current dependencies.

```bash
/sn-req-replay REQ=REQ-003
```

---

## Knowledge (Obsidian) commands

All five route through `ObsidianClient` (`scripts/obsidian_client.py`). Backend selection is controlled by the `--obsidian-mcp=auto|on|off` flag (defaults to `auto` — uses the Obsidian MCP server when reachable, falls back to direct filesystem writes).

### `/sn-knowledge-check SPRINT=<id>`

Preview the `sn-impact-analyzer` report for a sprint **without** running it. Uses the same pipeline as `/sn-sprint-run` but stops after writing `impact.md` + a summary. No code change, no commits. Use before kicking off a sprint to spot major impacts early.

```bash
/sn-knowledge-check SPRINT=SPRINT-001
```

### `/sn-knowledge-update`

No args. Idempotent. Re-reads every completed REQ + PLAN, regenerates per-topic files using the existing traceback frontmatter to detect updates vs. new facts. Auto-regenerates `<vault>/knowledge/global/tech/README.md` cross-project matrix.

```bash
/sn-knowledge-update
```

### `/sn-knowledge-promote TOPIC=<topic>`

Promote a project-domain fact to org-wide:

```
mv <vault>/knowledge/projects/<project>/<topic>.md → <vault>/knowledge/global/shared/<topic>.md
```

Updates `bucket:` frontmatter; preserves `origin_project:` traceback so the source is still discoverable.

```bash
/sn-knowledge-promote TOPIC=auth-policy
```

### `/sn-knowledge-demote TOPIC=<topic>`

Reverse of `/sn-knowledge-promote`. Refuses if the topic is referenced by other projects (via traceback frontmatter).

```bash
/sn-knowledge-demote TOPIC=auth-policy
```

### `/sn-knowledge-tech-matrix`

No args. Regenerate the cross-project tech matrix at `<vault>/knowledge/global/tech/README.md`. Scans every `<vault>/knowledge/global/tech/<project>/*.md` and emits a markdown table:

```
| Project   | Postgres | Redis | Node | Go   |
|-----------|----------|-------|------|------|
| demo-app  | 16       | 7     | 22   | —    |
| billing   | 14       | 7     | —    | 1.23 |
```

Drift across projects is visible at a glance. Auto-runs at the end of each sprint via `sn-knowledge-curator`.

```bash
/sn-knowledge-tech-matrix
```

---

## GitHub command

### `/sn-gh-import`

No args. Pull GitHub issues labeled `req` into `docs/requirements/active/` as REQ-NNN files. Runs:

```bash
gh issue list --label req --state open --json number,title,body
```

and converts each issue into a REQ scaffold:

- Title → REQ title
- Body bullets → acceptance criteria
- Issue number → REQ id suffix
- Label set → priority hint

Requires the `gh` CLI to be authenticated. Paired with `--workflow-pr` + `make gh-close` for auto-close on merge.

```bash
/sn-gh-import
```

---

## Verification command

### `/sn-verify`

No args. Shells to `scripts/verify_agent_sdk.py` and checks every `src/agent.{py,ts,go}` against the six mechanically-checkable rules from `docs/principles/agent-sdk-best-practices.md`:

| # | Rule | Check |
|---|---|---|
| 1 | Whitelist tools | `allowed_tools=[...]` (py) / `allowedTools: [...]` (ts) |
| 2 | No hardcoded API key | No literal `sk-...` string |
| 3 | Lock the model id | `model="..."` keyword present |
| 5 | Hooks for guaranteed side effects | At least one `HookMatcher` or `hooks:` block |
| 6 | Subagents narrowly defined | `AgentDefinition` has non-empty `tools=[...]` |
| 9 | Restrict `setting_sources` in prod | `setting_sources=["project"]` (when `--tier=3`/`both`) |

Exit codes: `0` all pass, `2` one or more rule failures (each printed as `::error file=…:: rule N: <description>` for CI), `3` no `src/agent.*` files found.

For the six rules that need prose analysis (`permission_mode`, sessions, MCP vetting, `WebSearch` necessity, streaming, error handling) — invoke the `sn-agent-sdk-reviewer` subagent.

```bash
make verify          # same as /sn-verify
```

---

## Subagents (dispatched by the orchestrator, not user-invoked)

The spec-loop orchestrator (`scripts/orchestrator.py`) dispatches these eight subagents in order during `/sn-sprint-run`. A ninth subagent — `sn-agent-sdk-reviewer` — is read-only and ad-hoc (you ask Claude to invoke it; no orchestrator phase fires it).

| Phase | Subagent | Purpose |
|---|---|---|
| impact | `sn-impact-analyzer` | Pre-sprint check. Reads sprint REQs + Obsidian knowledge + parallel sprints; flags major impacts |
| plan | `sn-planner` (optional, ships when `--subagents=all` or named) | Produces `exec-plans/PLAN-NNN.md` per REQ |
| decompose | `sn-task-decomposer` | Splits a PLAN into small task files |
| execute | `sn-task-executor` | Implements a single task (writes code) |
| test | `sn-task-tester` | Writes / runs tests for a task |
| integrate | `sn-integration-tester` | Cross-task integration test pass |
| adversary | `sn-adversary` | Adversarial testing — tries to falsify invariants under `.harness/invariants/` |
| evaluate | `sn-evaluator` | Scores the REQ result against acceptance criteria (0-100) |
| curate | `sn-knowledge-curator` | Extracts durable facts from completed REQs into Obsidian buckets |
| _ad-hoc_ | `sn-agent-sdk-reviewer` | Reviews `src/agent.{py,ts,go}` against the 6 prose-analysis Agent SDK best-practices rules (rules 4, 7, 8, 10, 11, 12); complements `/sn-verify` which handles the 6 mechanical rules |

The orchestrator phases reference subagents via `PHASE_TO_SUBAGENT` in `scripts/orchestrator.py`. `sn-agent-sdk-reviewer` is not in that map — invoke it on demand ("Review `src/agent.py` against Agent SDK best practices").

---

## Make targets that mirror these commands

The scaffolded `Makefile` exposes a thin wrapper for every command (so you can run them from a regular shell, not just inside Claude Code):

| Make target | Equivalent slash command |
|---|---|
| `make sprint-new SLUG=...` | `/sn-sprint-new SLUG=...` |
| `make sprint-add SPRINT=... REQ=...` | `/sn-sprint-add` |
| `make sprint-remove SPRINT=... REQ=...` | `/sn-sprint-remove` |
| `make sprint-run SPRINT=...` | `/sn-sprint-run` (Make target prints a hint; orchestrator runs inside Claude Code) |
| `make sprint-done SPRINT=...` | `/sn-sprint-done` |
| `make sprint-status` | `/sn-sprint-status` |
| `make req-new SLUG=...` | `/sn-req-new` |
| `make req-import FILE=...` | `/sn-req-import` |
| `make req-rollback REQ=...` | `/sn-req-rollback` |
| `make req-resume` | `/sn-req-resume` |
| `make req-replay REQ=...` | `/sn-req-replay` |
| `make knowledge-check SPRINT=...` | `/sn-knowledge-check` |
| `make knowledge-update` | `/sn-knowledge-update` |
| `make knowledge-promote TOPIC=...` | `/sn-knowledge-promote` |
| `make knowledge-demote TOPIC=...` | `/sn-knowledge-demote` |
| `make knowledge-tech-matrix` | `/sn-knowledge-tech-matrix` |
| `make gh-import` | `/sn-gh-import` |
| `make verify` | `/sn-verify` |

See the scaffolded `Makefile` for the `safety-*`, `worktree-*`, `hooks-*`, `logs-*`, and `orchestrate` targets too — they don't have matching slash commands.

---

## See also

- `commands/sn-setup.md` — full flag table for the entry command (machine-parseable form).
- `skills/sn-setup/SKILL.md` — when the skill triggers and what defaults it applies.
- `README.md` — top-level overview, file tree, safety rails, Obsidian KB layout.
- `WORKFLOW.md` — step-by-step walkthrough using the `sn-*` commands to take a new requirement through scaffolding, a sprint, the spec-loop, the triple-signal gate, and archival.
- `CHANGELOG.md` — versioned release notes, including the vault commits shipped alongside each plugin batch.
- `skills/sn-setup/templates/managed-agent-base/Makefile` — every Make target shipped to a scaffolded project.
