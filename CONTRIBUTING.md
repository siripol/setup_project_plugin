# Contributing to setup-project-plugin

Thanks for opening this file — pull requests and issues are welcome.

## Quick start

```bash
git clone https://github.com/siripol/setup_project_plugin
cd setup_project_plugin
uv venv .venv
uv pip install pytest pytest-cov pre-commit
.venv/bin/python -m pytest tests/test_sn_init.py -q
pre-commit install --hook-type pre-commit --hook-type pre-push
```

All 120 cases must pass before you push.

If you touched a scaffolded `src/agent.{py,ts,go}` overlay (or expect to), also run the Agent SDK rule checker against a fresh scaffold:

```bash
cd /tmp && rm -rf check && python3 /path/to/this/repo/scripts/sn_init.py check --lang=py --no-git --no-ci --no-obsidian
cd check && python3 scripts/verify_agent_sdk.py
```

Expect `verify_agent_sdk: 1 file(s) OK`. A failure means the overlay drifted out of compliance with the 12-rule checklist shipped at `docs/principles/agent-sdk-best-practices.md`. The `pre-commit` hooks run YAML / TOML / JSON validators + ruff on `scripts/` and `tests/` on every commit; the `pre-push` stage runs `pytest` so you don't push a broken build by accident.

## Code layout

- `commands/sn-setup.md` — plugin entry slash command (frontmatter + body).
- `scripts/sn_init.py` — scaffolder logic (argv parse, mode detect, atomic write).
- `scripts/gen_subagent_index.py` — regenerates `docs/design-docs/subagents.md` from agent frontmatter.
- `skills/sn-setup/templates/` — everything the scaffolder copies into a target project.
  - `claude/commands/sn-*.md` — 18 generated slash commands.
  - `claude/agents/sn-*.md` — 9 generated subagents.
  - `managed-agent-base/` — language-agnostic project scaffold (`Makefile`, `CLAUDE.md`, `.harness/`, `scripts/`, `docs/`).
  - `lang/{go,py,ts}/` — per-stack overlay (`src/`, `mcp_server/`, `tests/`, build config).
- `tests/test_sn_init.py` — pytest cases covering scaffold, upgrade, importers, safety, Makefile rendering, orchestrator promise emission, Go/TS lang-overlay smoke tests, `/sn-verify` exit-code contract, `sn-agent-sdk-reviewer` subagent shape.
- `.claude-plugin/{plugin.json,marketplace.json}` — Claude Code manifest + marketplace catalog.

## Workflow

1. Open an issue first for anything non-trivial so we can agree on the shape.
2. Create a feature branch: `git checkout -b feat/<short-name>` (or `fix/...`, `docs/...`, `chore/...`).
3. Write tests for the new behaviour. We aim for one new test per public surface change. Keep the scaffolder behaviour deterministic — tests should not need network access.
4. Run `python -m pytest tests/test_sn_init.py -q` locally before pushing.
5. Push the branch and open a PR against `main`. The CI workflow (see `.github/workflows/ci.yml`) re-runs pytest on every push.
6. Update `CHANGELOG.md` under an `Unreleased` section (or under the current version if you are landing right before a release tag).
7. Squash-merge when CI is green.

## Commit message style

We loosely follow Conventional Commits:

```
<type>(<scope>): short summary

Optional longer body wrapped at ~72 columns. Explain *why* the change is
needed and what behaviour changes. Reference REQ-NNN ids and prior
commits where useful.
```

Common types we use here: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`, `perf`, `style`. Scope is usually the touched area: `sn-setup`, `sn-init`, `WORKFLOW`, `README`, `plugin`, `scaffold`, etc.

### Attribution

- Commits are attributed to `Siripol <siripoln.media@gmail.com>` in the git Author field.
- Every commit body ends with the trailer `Author: Siripol <siripoln.media@gmail.com>`. The `.githooks/commit-msg` hook appends it automatically if missing, and preserves any additional `Author: <other-contributor>` lines you add manually.
- The `Co-Authored-By: Claude*` trailer is **stripped automatically** by the same hook. Do not add it manually either.
- Activate the hook **per clone** (git hook config is not committed):
  ```
  git config core.hooksPath .githooks
  ```
  The same hook (with an extra REQ-id subject check) ships to every project scaffolded by `sn-setup`; activate it there with `make hooks-install`.

## Adding a new generated `sn-*` command

1. Create `skills/sn-setup/templates/claude/commands/sn-<name>.md` with frontmatter `name: sn-<name>` (matching the filename stem). Body documents args, behaviour, and side-effects.
2. If the command takes args via a Make wrapper, add a target to `skills/sn-setup/templates/managed-agent-base/Makefile` next to the related family.
3. Document the command in `COMMANDS.md` under the right family heading and update the totals in the header.
4. Add a `WORKFLOW.md` section if the command joins the spec-loop flow.
5. Add tests under `tests/test_sn_init.py`: file presence, frontmatter, key body strings, Make target (if any).

## Adding a new generated subagent

1. Create `skills/sn-setup/templates/claude/agents/sn-<name>.md` with the standard capability manifest in frontmatter (`tools`, `can_modify`, `can_delegate`, `chokepoint_gate`).
2. Wire it into `PHASE_TO_SUBAGENT` in `skills/sn-setup/templates/managed-agent-base/scripts/orchestrator.py` if it joins a spec-loop phase.
3. Update the subagent table in `README.md` and the orchestrator phase table in `WORKFLOW.md`.
4. Update the workflow-files test in `tests/test_sn_init.py`.

## Reporting bugs

Issue with a scaffolded project? Include:

- Output of `python --version` (or the equivalent for the lang overlay you used).
- The full `/sn-setup` (or `/sn-setup --upgrade`) invocation.
- Contents of `.sn-init-state.json` from the affected project.
- `make safety-status` output if the breaker tripped.
- A minimal repro path, ideally a fresh scaffold under `/tmp` that reproduces the symptom.

## License

By contributing you agree your work is licensed under the MIT License (see `LICENSE`).
