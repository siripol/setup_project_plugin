---
topic: workspace-layer-design
bucket: projects
origin_project: setup_project_plugin
origin_req: REQ-WS-001
first_seen: 2026-06-26
last_updated: 2026-06-26
tags: [knowledge, design, workspace, monorepo, cli, scaffold, setup_project_plugin]
---

# Design — Workspace Layer (B2.2)

Virtual-monorepo aggregator. Spec captures architecture, registry schema, CLI surface, bash scripts, doc bodies, pair-mode wiring, risks, and the decisions log.

## 1. Architecture

```
parent-dir/
├── my-workspace/                ← workspace dir (gitignored from members)
│   ├── WORKSPACE.md             ← human-readable explainer + member table
│   ├── CLAUDE.md                ← workspace-level Claude memory
│   ├── MIGRATION.md             ← adoption + exit instructions
│   ├── .workspace/
│   │   └── registry.json        ← machine-readable source of truth
│   └── scripts/
│       ├── status.sh
│       ├── sync.sh
│       └── launch.sh
├── service-a/                   ← member repo (own git)
│   └── .gitignore               ← +1 line: `my-workspace/`
└── service-b/                   ← member repo (own git)
    └── .gitignore               ← +1 line: `my-workspace/`
```

Key properties:

- Workspace dir is a sibling, not a parent. Each member keeps its own git root + identity.
- Workspace itself is NOT a git repo. It's a view.
- Adoption = `sn-setup workspace init <name>` + `sn-setup workspace add ../<svc>` per service. Exit = `rm -rf <workspace-dir>/`.
- WORKSPACE.md is for humans, registry.json is for scripts; markers in WORKSPACE.md + CLAUDE.md confine auto-regeneration to specific blocks.

## 2. Registry schema (`.workspace/registry.json`)

```json
{
  "workspace_version": "1.0.0",
  "name": "my-workspace",
  "created_at": "2026-06-26T10:00:00Z",
  "services": [
    {
      "slug": "service-a",
      "path": "../service-a",
      "registered_at": "2026-06-26T10:05:00Z",
      "profile": "microservice",
      "lang": "go",
      "regulated": false,
      "repo_url": "git@github.com:org/service-a.git",
      "owners": "@team-platform"
    }
  ]
}
```

Notes:

- `workspace_version` enables future format-upgrade migrations (`B2.2-FU-1`).
- `path` is **always relative** to the workspace dir (portable across machines).
- `slug` = service repo basename. Duplicates rejected at `add`.
- `profile` / `lang` / `regulated` auto-collected from member's `.sn-init-state.json`; null when absent.
- `repo_url` best-effort: `git -C <path> remote get-url origin`.
- `owners` source priority: `--owners=` flag > first CODEOWNERS rule matching `.claude/` > null.

## 3. Bash scripts

Three scripts under `<workspace>/scripts/`, all callable via `sn-setup workspace <verb>` CLI delegation:

### `status.sh`
- Iterates `services[]` from `registry.json`.
- Per service: `git -C <path> status -sb --porcelain=v2` parsed for branch + ahead/behind + dirty count.
- Output one line per service: `slug=<X> branch=<B> ahead=<N> behind=<N> dirty=<N>`.
- Graceful degradation if `jq` missing (awk fallback parse of registry.json).

### `sync.sh`
- For each service: `git -C <path> fetch --quiet`, then `git -C <path> status --porcelain` check.
- If dirty: stderr `skip <slug>: dirty`, continue.
- If clean: `git -C <path> pull --ff-only`.
- Never pushes. Never stashes. Never rewrites history.

### `launch.sh`
- Reads `$EDITOR`, falls back to `code`.
- Emits `<workspace>/<workspace-name>.code-workspace` with minimal `{"folders":[{"path":"."},{"path":"<svc1>"},...]}`.
- Runs `$EDITOR <file>` if editor found; else prints path + exits 0.
- `--dry-run`: emit file only, never launch.

All scripts respect `set -euo pipefail` and quote paths defensively for unicode / spaces.

## 4. Workspace docs

### `WORKSPACE.md`

Human-readable. Sections:

- Title + 1-line description.
- "Registered services" table (auto-regenerated between `<!-- registry:begin -->` / `<!-- registry:end -->` markers).
- "Day-to-day commands" reference.
- "When to drop the workspace" → pointer to MIGRATION.md.

### `CLAUDE.md` (workspace-level)

Auto-loaded by Claude when invoked from the workspace dir. Sections:

- Title.
- "Repository Ecosystem" table (auto-regenerated between markers; same data as WORKSPACE.md table but reformatted for Claude context).
- "Org-wide conventions" (manually-appended block; survives regenerates).
- "What does NOT go here" (anti-scope guide).

### `MIGRATION.md`

Static doc. Sections:

- Adopting an existing polyrepo setup (1..6 steps).
- Exiting the workspace (3 steps).
- Why "virtual monorepo" and not Bazel/Nx/Turborepo (the workspace's anti-scope statement).
- Compatibility with B2.3 marketplace consumer (forward-reference; informational).

## 5. CLI

New module `scripts/workspace_cli.py`. Top-level dispatcher mirroring `scripts/policy_cli.py` shape (`argparse` sub-parsers).

Sub-commands:

| Verb | Effect |
|---|---|
| `init <name>` | Create workspace dir + seed templates + empty registry. |
| `add <path> [--owners=<value>]` | Register a sibling repo. Refuses non-git dirs or duplicate slugs. |
| `remove <slug>` | Strip registry entry. Idempotent: unknown slug → warning + exit 0. |
| `list` | Print table + regenerate markers in `WORKSPACE.md` + `CLAUDE.md`. |
| `status` / `sync` / `launch` | Delegate to `scripts/<verb>.sh` via `subprocess`. |

Workspace-root lookup: walk cwd ancestors for the first `.workspace/registry.json`. Sub-commands except `init` require this.

Dispatch in `sn_init.main`: short-circuit on `argv[0] == "workspace"` → `workspace_cli.main(raw[1:])`.

## 6. Pair-mode wiring (`--workspace` flag)

`sn_init` gains:
- `--workspace` (bool flag)
- `--workspace-name=<N>` (override default `<project>-workspace`)

After `_run_new` writes `.sn-init-state.json` and finishes scaffolding, if `--workspace`:

1. `cd` to `target.parent`.
2. `workspace_cli.main(["init", <ws_name>])` — creates sibling workspace.
3. `cd` into the new workspace.
4. `workspace_cli.main(["add", str(target)])` — auto-registers the just-scaffolded project.

`.sn-init-state.json` MUST be flushed BEFORE the pair-mode hook fires (see Risk R8). Pair-mode is idempotent: re-running re-`add`s harmlessly because `add` is a no-op when slug already present (after the duplicate-rejection refactor).

## 7. Tests (28 new)

| Suite | New tests | Coverage |
|---|---|---|
| `tests/unit/test_workspace_cli.py` | T1..T20 | init / add / remove / list / lookup / dispatch |
| `tests/unit/test_sn_init_workspace_pair.py` | P1..P4 | `--workspace` flag + auto-register |
| `tests/unit/test_workspace_scripts.py` | S1..S4 | status / sync / launch bash scripts |

Helpers in `tests/conftest.py`: `fake_git_repo` fixture (minimal `git init` + optional `.sn-init-state.json`), `workspace_dir` fixture (pre-initialized empty workspace).

Total project test count: 269 → 297.

## 8. Risks (top 6 of 16; full table lives in the brainstorm log)

| # | Risk | Mitigation |
|---|---|---|
| R1 | Member `.gitignore` polluted with stranded workspace line after exit | Documented in MIGRATION.md; `remove` does NOT auto-strip; `B2.2-FU-5 doctor` will detect orphans. |
| R3 | `sync.sh` clobbers in-flight work on dirty member | Pre-check `git status --porcelain`; skip + stderr-warn. Test S3 covers. |
| R6 | jq missing → all bash scripts fail | Awk-based JSON fallback (same pattern as PDPA hooks). Test S2 covers. |
| R8 | Pair-mode `add` runs before member's `.sn-init-state.json` flushes | Flush state file BEFORE pair-mode hook fires in `_run_new`. Test P2 covers. |
| R14 | Workspace accidentally git-tracked → absolute paths leak `$HOME` | Registry stores **relative** paths only. Computed via `os.path.relpath` at add time. Test T4 asserts. |
| R15 | Future template breaking change strands existing users | `workspace_version: "1.0.0"` field enables `B2.2-FU-1 upgrade` migration. |

Full risk table (R1-R16) and full mitigations in the brainstorm working notes; reduced here to the load-bearing six.

## 9. Decisions log

25 decisions locked during brainstorm. Source of truth for "why" questions in code review. Most load-bearing:

| # | Decision | Rationale (short) |
|---|---|---|
| D1 | Pair + standalone + add command (all three) | Three real flows; carving one cripples adoption. |
| D2 | WORKSPACE.md human + registry.json machine | Two-file split: humans read prose, scripts read JSON. |
| D3 | Sibling dir, not parent | Sibling preserves member git root; adoption / exit is `mkdir` / `rm`. |
| D6 | Registry stores relative paths | Portable across machines + safe under git tracking. |
| D11 | jq graceful degradation | Same convention as PDPA hooks; don't block thin envs. |
| D12 | `sync.sh` skips dirty repos | Don't clobber in-flight work. |
| D19 | NO `git push` aggregator, ever | Push is intentional + can deploy. Aggregating lowers safety floor. |
| D22 | Workspace is NOT a git repo | It's a view. Each member owns its git state. |

Full D1..D25 in the spec mirror under `docs/superpowers/specs/2026-06-26-workspace-layer-design.md` and in the brainstorm transcript.

## 10. Out of scope

Itemized in [[../requirements/workspace-layer#out-of-scope]]. Highlights:

- No cross-repo build / test / dep-graph orchestration.
- No `workspace push` aggregator.
- No marketplace divergence warning (blocked-by B2.3).

## 11. Carved follow-ups

| ID | Title | Tier | Trigger |
|---|---|---|---|
| B2.2-FU-1 | `workspace upgrade` command | 3 | template format breaks back-compat |
| B2.2-FU-2 | `/sn-workspace-*` slash commands | 3 | slash-command UX becomes dominant |
| B2.2-FU-3 | Parallel `status` / `sync` | 3 | >5s wall-clock with ≥10 services |
| B2.2-FU-4 | Marketplace divergence warning | 2 | B2.3 ships |
| B2.2-FU-5 | `workspace doctor` | 3 | drift complaints surface |
| B2.2-FU-6 | `workspace-coordinator` subagent | 3 | real cross-repo refactor use case |

## Related

- [[../requirements/workspace-layer]] — REQ-WS-001 acceptance criteria.
- [[../plans/workspace-layer]] — task decomposition.
- [[../design/policy-catalog]] — CLI sub-tree pattern this mirrors.
- [[../design/profile-overlays]] — `.sn-init-state.json` shape consumed by `add`.
