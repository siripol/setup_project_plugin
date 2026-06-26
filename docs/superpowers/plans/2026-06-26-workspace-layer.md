# Workspace Layer (B2.2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a virtual-monorepo workspace layer — `sn-setup workspace {init,add,remove,list,status,sync,launch}` CLI sub-tree + `--workspace` pair flag on `sn-setup new` / `demo` — that aggregates polyrepo services via a sibling-directory workspace dir holding `WORKSPACE.md`, `CLAUDE.md`, `MIGRATION.md`, `.workspace/registry.json`, and 3 bash scripts.

**Architecture:** Workspace is a **view**, not a build orchestrator. Sibling dir to member repos. Each member keeps its own git root. Three entry points all ship: pair-mode (scaffold + workspace simultaneously), standalone (`init` then `add`), brownfield (`add` into existing workspace). New `scripts/workspace_cli.py` mirrors `policy_cli.py`'s argparse-subparsers shape. `sn_init.main` short-circuits on `argv[0] == "workspace"`. Pair-mode runs `init` + auto-`add` after the scaffold's `.sn-init-state.json` flushes.

**Tech Stack:** Python 3.13+, `pytest`, POSIX bash, `jq` (with awk fallback), VS Code `.code-workspace` JSON schema.

## Global Constraints

- Spec is authoritative: `docs/superpowers/specs/2026-06-26-workspace-layer-design.md` (mirrored from vault commit `39f0056`).
- Existing **269 tests MUST keep passing** after every task; final count **297** (+28).
- All new Python uses `from __future__ import annotations` + explicit type annotations.
- All bash scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, defensive path quoting, graceful degradation if `jq` missing (awk fallback), `shellcheck` clean.
- Registry stores **relative paths only** (never absolute) — `os.path.relpath` at `add` time.
- `workspace_version: "1.0.0"` field in `registry.json` from day 1.
- Markers `<!-- registry:begin -->` / `<!-- registry:end -->` confine doc regeneration; prose outside survives.
- Pair-mode hook fires **after** `.sn-init-state.json` flushes (R8 mitigation).
- `_find_workspace_root` walks up cwd ancestors looking for `.workspace/registry.json`; stops at filesystem root; **never traverses symlinks**.
- CLI dispatch follows existing pattern: `sn_init.main` short-circuit on `argv[0] in SUBTREES` (extend `SUBTREES = {"policy", "profile", "workspace"}`).
- Atomic writes for `registry.json`: tempfile + `os.rename` in same dir.
- Commit Author trailer mandatory: `Author: Siripol <siripoln.media@gmail.com>` (enforced by `.githooks/commit-msg`); never `Co-Authored-By: Claude`.
- Branch: `feat/workspace-layer` (already created from `main` post-PR #25; spec mirror committed as `a9025a6`).
- DO NOT push to vault from subagents; controller handles vault writes after each task.
- DO NOT push to origin from subagents; controller pushes after the commit lands.
- Tests live in `tests/` (FLAT, not `tests/unit/`); `import workspace_cli` resolves via `tests/conftest.py` adding `scripts/` to `sys.path`.

---

## File map

### Create

| Path | Responsibility |
|---|---|
| `skills/sn-setup/templates/workspace/WORKSPACE.md` | Human-readable explainer + members table (markers) |
| `skills/sn-setup/templates/workspace/CLAUDE.md` | Workspace-level Claude memory + ecosystem table (markers) |
| `skills/sn-setup/templates/workspace/MIGRATION.md` | Adopt + exit instructions; anti-scope statement |
| `skills/sn-setup/templates/workspace/.workspace/registry.json` | Seed registry: workspace_version, name placeholder, empty services array |
| `skills/sn-setup/templates/workspace/scripts/status.sh` | Per-service `git status -sb` aggregator |
| `skills/sn-setup/templates/workspace/scripts/sync.sh` | Per-service `git pull --ff-only`, skip-dirty |
| `skills/sn-setup/templates/workspace/scripts/launch.sh` | Emit `.code-workspace` + `$EDITOR` launch |
| `scripts/workspace_cli.py` | argparse dispatcher: init/add/remove/list/status/sync/launch |
| `tests/test_workspace_cli.py` | T1-T20: CLI unit tests |
| `tests/test_sn_init_workspace_pair.py` | P1-P4: pair-mode integration tests |
| `tests/test_workspace_scripts.py` | S1-S4: bash script smoke tests |

### Modify

| Path | Change |
|---|---|
| `scripts/sn_init.py` | Extend `SUBTREES` to include `"workspace"`; add `--workspace` + `--workspace-name` flags; add pair-mode hook in `_run_new` after `_write_state` |
| `docs/backlog.md` | Mark B2.2 `[x]`; append B2.2-FU-1..6 follow-up entries |
| `CHANGELOG.md` | `[Unreleased] > Added` workspace-layer entry |

---

## Task list

The plan has **5 tasks + 1 final review**. Tasks 1-3 build the core (templates → CLI → scripts). Task 4 wires pair-mode. Task 5 ships docs (backlog + CHANGELOG). Final = whole-branch review.

| Task | Title | Model | Tests at end |
|---|---|---|---|
| T1 | Workspace templates (4 doc bodies + registry seed + 3 bash scripts as static files) | haiku | 269 (unchanged; new files but no tests yet) |
| T2 | `workspace_cli.py` — init / add / remove / list + workspace-root lookup + sn_init dispatch | sonnet | 289 (+20 unit) |
| T3 | Bash scripts go live + CLI delegation (`status`/`sync`/`launch` glue) | sonnet | 293 (+4 script) |
| T4 | Pair-mode wiring: `--workspace` + `--workspace-name` flags + post-state-flush hook | sonnet | 297 (+4 pair) |
| T5 | docs: backlog + CHANGELOG | haiku | 297 |
| Final | Whole-branch review on opus | opus | n/a |

---

### Task 1: Workspace templates

Templates land first because Tasks 2-3 tests need them readable from `skills/sn-setup/templates/workspace/`. Bash scripts ship as static template files in this task; CLI delegation glue lands in Task 3.

**Files:**
- Create: `skills/sn-setup/templates/workspace/WORKSPACE.md`
- Create: `skills/sn-setup/templates/workspace/CLAUDE.md`
- Create: `skills/sn-setup/templates/workspace/MIGRATION.md`
- Create: `skills/sn-setup/templates/workspace/.workspace/registry.json`
- Create: `skills/sn-setup/templates/workspace/scripts/status.sh`
- Create: `skills/sn-setup/templates/workspace/scripts/sync.sh`
- Create: `skills/sn-setup/templates/workspace/scripts/launch.sh`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: a template tree readable by `workspace_cli._cmd_init` in Task 2. Files use `${workspace_name}` and `${created_at}` placeholders that the CLI substitutes at init time.

- [ ] **Step 1: Create `skills/sn-setup/templates/workspace/WORKSPACE.md`**

```markdown
# Workspace — ${workspace_name}

Lightweight virtual-monorepo. Registers N service repos for cross-cutting work — editor scope, search, status, sync. NOT a real monorepo: each service keeps its own git history, CI, and deploy pipeline.

## Registered services

<!-- registry:begin -->
| Service | Profile | Lang | Path | Owners | Regulated |
|---|---|---|---|---|---|
| _(none yet)_ | — | — | — | — | — |
<!-- registry:end -->

(This table is regenerated from `.workspace/registry.json` by `sn-setup workspace list`. Hand-edits to the table will be overwritten on next regenerate; hand-edits to `registry.json` persist.)

## Day-to-day commands

| Command | Effect |
|---|---|
| `sn-setup workspace add <path>` | Register an existing checked-out repo |
| `sn-setup workspace remove <slug>` | Unregister |
| `sn-setup workspace list` | Print registry + regenerate the table above |
| `sn-setup workspace status` | `git status` across all registered repos |
| `sn-setup workspace sync` | `git pull --ff-only` across all (refuses to clobber) |
| `sn-setup workspace launch` | Open editor scoped to workspace + all registered repos |

## When to drop the workspace

Adoption is reversible — see `MIGRATION.md`.
```

- [ ] **Step 2: Create `skills/sn-setup/templates/workspace/CLAUDE.md`**

```markdown
# ${workspace_name} — Claude memory

Workspace-level memory. Auto-loaded when Claude runs from this directory.

## What this is

Cross-cutting context for a virtual monorepo of N services. Each service has its own `CLAUDE.md` with service-specific identity, profile, and policies. THIS file holds only what's true across services.

## Repository Ecosystem

<!-- registry:begin -->
| Service | Purpose | Repo | Profile |
|---|---|---|---|
| _(none yet)_ | — | — | — |
<!-- registry:end -->

(Auto-populated from `.workspace/registry.json` by `sn-setup workspace list`. Foreground by usage frequency, not alphabetical.)

## Org-wide conventions

(Append rules that apply to EVERY registered service. Examples:
- All services emit structured JSON logs to stdout.
- All services use REQ-NNN commit message prefixes.
- All services apply `secret-scan` + `supply-chain-scan` policies.)

## What does NOT go here

- Service-specific architecture → that service's `CLAUDE.md`.
- Per-developer / per-machine notes → `CLAUDE.local.md` in each service.
- Long reference material → vault under `<vault>/shared/`.
```

- [ ] **Step 3: Create `skills/sn-setup/templates/workspace/MIGRATION.md`**

```markdown
# Workspace adoption + exit

## Adopting an existing polyrepo setup

1. Pick a workspace name (org name, team name, or product name).
2. `sn-setup workspace init <name>` creates `./<name>/`.
3. For each existing service repo (assumed to be a sibling of the workspace):
   ```
   sn-setup workspace add ../<service-repo>
   ```
4. Each `add` reads the service's `.sn-init-state.json` (if present) for profile + lang + applied policies. Pass `--owners=@team` to override.
5. `sn-setup workspace list` regenerates `WORKSPACE.md` table + `CLAUDE.md` ecosystem table.
6. (Optional) Add `<workspace-name>/` to each member repo's `.gitignore`. `sn-setup workspace add` does this automatically.

## Exiting the workspace

Workspace is opt-in and trivially reversible:

1. `rm -rf <workspace-dir>/`.
2. Remove `<workspace-name>/` from each member's `.gitignore` (manual; `sn-setup workspace remove` does not auto-strip).
3. Done. Member repos are untouched.

No data lives in the workspace itself — it's a view over independent repos.

## Why "virtual monorepo" and not Bazel / Nx / Turborepo?

This workspace is a **convenience layer**, not a build orchestrator. It does not:
- Run cross-repo builds.
- Cache cross-repo test results.
- Enforce cross-repo dependency graphs.

If your team needs those, layer a real monorepo tool on top. The workspace gives you single-editor + `git status`/`pull` aggregation; not build orchestration.

## Compatibility with B2.3 marketplace consumer (future)

When the marketplace consumer (`--marketplace=<src>`) lands, scaffolded services install plugins via marketplace. Workspace `add` will read each member's `installed_plugins` block and warn on divergence (e.g. "service A pinned `core-guardrails@1.2`, service B pinned `@1.3`"). Until B2.3, this section is informational only.
```

- [ ] **Step 4: Create `skills/sn-setup/templates/workspace/.workspace/registry.json`**

```json
{
  "workspace_version": "1.0.0",
  "name": "${workspace_name}",
  "created_at": "${created_at}",
  "services": []
}
```

- [ ] **Step 5: Create `skills/sn-setup/templates/workspace/scripts/status.sh`**

```bash
#!/usr/bin/env bash
# Workspace status: print one line per registered service.
# Format: slug=<X> branch=<B> ahead=<N> behind=<N> dirty=<N>

set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="${WORKSPACE_ROOT}/.workspace/registry.json"

if [[ ! -f "${REGISTRY}" ]]; then
  echo "workspace status: registry.json not found at ${REGISTRY}" >&2
  exit 2
fi

# Parse services array: prefer jq, fallback to awk.
if command -v jq >/dev/null 2>&1; then
  mapfile -t SVC_LINES < <(jq -r '.services[] | "\(.slug)\t\(.path)"' "${REGISTRY}")
else
  # awk fallback: parse slug + path pairs from the services array.
  mapfile -t SVC_LINES < <(awk '
    /"slug":/ { gsub(/[",]/, "", $2); slug=$2 }
    /"path":/ { gsub(/[",]/, "", $2); print slug "\t" $2 }
  ' "${REGISTRY}")
fi

for line in "${SVC_LINES[@]}"; do
  slug="${line%%	*}"
  rel_path="${line##*	}"
  abs_path="${WORKSPACE_ROOT}/${rel_path}"
  if [[ ! -d "${abs_path}/.git" ]]; then
    echo "slug=${slug} branch=? ahead=0 behind=0 dirty=0 missing=1"
    continue
  fi
  branch=$(git -C "${abs_path}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  ahead_behind=$(git -C "${abs_path}" rev-list --left-right --count "@{upstream}...HEAD" 2>/dev/null || echo "0	0")
  behind="${ahead_behind%%	*}"
  ahead="${ahead_behind##*	}"
  dirty=$(git -C "${abs_path}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "slug=${slug} branch=${branch} ahead=${ahead} behind=${behind} dirty=${dirty}"
done
```

- [ ] **Step 6: Create `skills/sn-setup/templates/workspace/scripts/sync.sh`**

```bash
#!/usr/bin/env bash
# Workspace sync: git pull --ff-only across all registered services.
# Skip + warn on dirty working trees; never stash or clobber.

set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="${WORKSPACE_ROOT}/.workspace/registry.json"

if [[ ! -f "${REGISTRY}" ]]; then
  echo "workspace sync: registry.json not found at ${REGISTRY}" >&2
  exit 2
fi

if command -v jq >/dev/null 2>&1; then
  mapfile -t SVC_LINES < <(jq -r '.services[] | "\(.slug)\t\(.path)"' "${REGISTRY}")
else
  mapfile -t SVC_LINES < <(awk '
    /"slug":/ { gsub(/[",]/, "", $2); slug=$2 }
    /"path":/ { gsub(/[",]/, "", $2); print slug "\t" $2 }
  ' "${REGISTRY}")
fi

for line in "${SVC_LINES[@]}"; do
  slug="${line%%	*}"
  rel_path="${line##*	}"
  abs_path="${WORKSPACE_ROOT}/${rel_path}"
  if [[ ! -d "${abs_path}/.git" ]]; then
    echo "skip ${slug}: not a git repo" >&2
    continue
  fi
  dirty_count=$(git -C "${abs_path}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [[ "${dirty_count}" != "0" ]]; then
    echo "skip ${slug}: dirty" >&2
    continue
  fi
  git -C "${abs_path}" fetch --quiet
  if git -C "${abs_path}" pull --ff-only --quiet 2>/dev/null; then
    echo "sync ${slug}: ok"
  else
    echo "skip ${slug}: pull --ff-only failed (non-fast-forward?)" >&2
  fi
done
```

- [ ] **Step 7: Create `skills/sn-setup/templates/workspace/scripts/launch.sh`**

```bash
#!/usr/bin/env bash
# Workspace launch: emit .code-workspace + open in $EDITOR (fallback: code).
# --dry-run: emit file only, never launch.

set -euo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

WORKSPACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY="${WORKSPACE_ROOT}/.workspace/registry.json"

if [[ ! -f "${REGISTRY}" ]]; then
  echo "workspace launch: registry.json not found at ${REGISTRY}" >&2
  exit 2
fi

WS_NAME="$(basename "${WORKSPACE_ROOT}")"
OUT_FILE="${WORKSPACE_ROOT}/${WS_NAME}.code-workspace"

# Build folders[] JSON: workspace root first, then each service relative path.
if command -v jq >/dev/null 2>&1; then
  PATHS_JSON=$(jq -r '.services[] | .path' "${REGISTRY}" | awk 'BEGIN { printf "[{\"path\":\".\"}" } { printf ",{\"path\":\"%s\"}", $0 } END { printf "]" }')
else
  PATHS_JSON=$(awk '
    BEGIN { printf "[{\"path\":\".\"}" }
    /"path":/ { gsub(/[",]/, "", $2); printf ",{\"path\":\"%s\"}", $2 }
    END { printf "]" }
  ' "${REGISTRY}")
fi

printf '{\n  "folders": %s\n}\n' "${PATHS_JSON}" > "${OUT_FILE}"
echo "wrote ${OUT_FILE}"

if [[ "${DRY_RUN}" == "1" ]]; then
  exit 0
fi

EDITOR_CMD="${EDITOR:-code}"
if command -v "${EDITOR_CMD}" >/dev/null 2>&1; then
  "${EDITOR_CMD}" "${OUT_FILE}"
else
  echo "launch: no editor found (\$EDITOR unset and 'code' not on PATH); file at ${OUT_FILE}" >&2
fi
```

- [ ] **Step 8: Make scripts executable + run shellcheck**

```bash
chmod +x skills/sn-setup/templates/workspace/scripts/{status,sync,launch}.sh
shellcheck skills/sn-setup/templates/workspace/scripts/*.sh
```
Expected: shellcheck exits 0 with no findings (or only known-acceptable `SC2155`-style warnings that match the rest of the repo's bash hygiene).

- [ ] **Step 9: Verify nothing else broke**

```bash
pytest -q
```
Expected: `269 passed`.

- [ ] **Step 10: Commit Task 1**

```bash
git add skills/sn-setup/templates/workspace/
git commit -m "$(cat <<'EOF'
feat(workspace): templates (WORKSPACE.md / CLAUDE.md / MIGRATION.md / registry / scripts)

Static template tree under skills/sn-setup/templates/workspace/.
Templates use ${workspace_name} and ${created_at} placeholders that
Task 2's workspace_cli._cmd_init substitutes. Bash scripts are
shellcheck-clean and degrade gracefully when jq is missing.

REQ-WS-001 / B2.2.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 2: `workspace_cli.py` core + sn_init dispatch

CLI module + 4 sub-commands (init/add/remove/list) + workspace-root lookup + 20 unit tests. `status/sync/launch` glue lands in Task 3.

**Files:**
- Create: `scripts/workspace_cli.py`
- Create: `tests/test_workspace_cli.py`
- Modify: `scripts/sn_init.py` (extend `SUBTREES`)

**Interfaces:**
- Consumes: `errors.UsageError` + `errors.EXIT_USAGE` from `scripts/errors.py`. `os.path.relpath` from stdlib. Templates from Task 1.
- Produces:
  - `workspace_cli.main(argv: list[str]) -> int`
  - `workspace_cli._find_workspace_root(start: Path | None = None) -> Path | None`
  - `workspace_cli._cmd_init(ns: argparse.Namespace) -> int`
  - `workspace_cli._cmd_add(ns: argparse.Namespace) -> int`
  - `workspace_cli._cmd_remove(ns: argparse.Namespace) -> int`
  - `workspace_cli._cmd_list(ns: argparse.Namespace) -> int`
  - Registry JSON shape:
    ```json
    {
      "workspace_version": "1.0.0",
      "name": "<ws>",
      "created_at": "<iso>",
      "services": [
        {
          "slug": "<svc>",
          "path": "<relative>",
          "registered_at": "<iso>",
          "profile": "<microservice|bff|frontend|null>",
          "lang": "<go|ts|py|js|null>",
          "regulated": "<bool|null>",
          "repo_url": "<url|null>",
          "owners": "<comma-list|null>"
        }
      ]
    }
    ```
- Produces for Task 4: `workspace_cli.main(["init", name])` and `workspace_cli.main(["add", path])` callable from inside `sn_init._run_new`.

- [ ] **Step 1: Write the workspace-root lookup test (T15)**

Create `tests/test_workspace_cli.py` with this initial content:

```python
"""Tests for scripts/workspace_cli.py — workspace CLI dispatcher."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import sn_init  # type: ignore
import workspace_cli  # type: ignore


def _run(cwd: Path, *argv: str) -> int:
    old = Path.cwd()
    try:
        os.chdir(cwd)
        return workspace_cli.main(list(argv))
    finally:
        os.chdir(old)


def _init_env(env: dict | None = None) -> dict:
    base = {**os.environ}
    base.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    if env:
        base.update(env)
    return base


def _fake_git_repo(parent: Path, name: str, *, profile: str | None = None,
                   lang: str | None = None, regulated: bool | None = None) -> Path:
    repo = parent / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, env=_init_env())
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                   cwd=str(repo), check=True, env=_init_env())
    if profile or lang or regulated is not None:
        state = {"profile": profile, "lang": lang, "regulated": regulated}
        (repo / ".sn-init-state.json").write_text(json.dumps(state))
    return repo


def test_find_workspace_root_walks_up(tmp_path: Path):
    """T15: cwd inside workspace subdir finds the workspace root."""
    ws = tmp_path / "ws"
    (ws / ".workspace").mkdir(parents=True)
    (ws / ".workspace" / "registry.json").write_text('{"services":[]}')
    (ws / "scripts").mkdir()
    found = workspace_cli._find_workspace_root(start=ws / "scripts")
    assert found == ws.resolve()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_workspace_cli.py::test_find_workspace_root_walks_up -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'workspace_cli'`.

- [ ] **Step 3: Create `scripts/workspace_cli.py` skeleton with `_find_workspace_root`**

```python
"""`sn-setup workspace ...` sub-command dispatcher.

Mirrors `scripts/policy_cli.py` shape. Workspace is a sibling-dir virtual
monorepo aggregator: WORKSPACE.md (human) + .workspace/registry.json
(machine) + 3 bash scripts (status/sync/launch).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import errors  # type: ignore

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "workspace"

WORKSPACE_VERSION = "1.0.0"
REGISTRY_REL = Path(".workspace") / "registry.json"

MARKER_BEGIN = "<!-- registry:begin -->"
MARKER_END = "<!-- registry:end -->"


def _find_workspace_root(start: Path | None = None) -> Path | None:
    """Walk ancestors of `start` (default cwd) looking for .workspace/registry.json.

    Does not traverse symlinks. Stops at filesystem root.
    """
    p = (start or Path.cwd()).resolve()
    while True:
        if (p / REGISTRY_REL).exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup workspace")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp_init = sub.add_parser("init"); sp_init.add_argument("name")
    sp_add = sub.add_parser("add"); sp_add.add_argument("path")
    sp_add.add_argument("--owners", default=None,
                        help="Override owners (comma-list of team handles)")
    sp_rm = sub.add_parser("remove"); sp_rm.add_argument("slug")
    sub.add_parser("list")
    sub.add_parser("status")
    sub.add_parser("sync")
    sub.add_parser("launch")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK

    if ns.cmd == "init":
        return _cmd_init(ns)
    if ns.cmd == "add":
        return _cmd_add(ns)
    if ns.cmd == "remove":
        return _cmd_remove(ns)
    if ns.cmd == "list":
        return _cmd_list(ns)
    if ns.cmd in ("status", "sync", "launch"):
        return _cmd_run_script(ns.cmd)
    return errors.EXIT_USAGE


# Placeholder implementations — filled in subsequent steps of Task 2.
def _cmd_init(ns: argparse.Namespace) -> int:
    raise NotImplementedError


def _cmd_add(ns: argparse.Namespace) -> int:
    raise NotImplementedError


def _cmd_remove(ns: argparse.Namespace) -> int:
    raise NotImplementedError


def _cmd_list(ns: argparse.Namespace) -> int:
    raise NotImplementedError


def _cmd_run_script(verb: str) -> int:
    # Filled in Task 3.
    raise NotImplementedError
```

- [ ] **Step 4: Run test T15 to verify it passes**

```bash
pytest tests/test_workspace_cli.py::test_find_workspace_root_walks_up -v
```
Expected: PASS.

- [ ] **Step 5: Add init test (T1) — file scaffolding**

Append to `tests/test_workspace_cli.py`:

```python
def test_init_creates_workspace_dir(tmp_path: Path):
    """T1: init scaffolds the full workspace tree."""
    rc = _run(tmp_path, "init", "ws")
    assert rc == 0
    ws = tmp_path / "ws"
    assert (ws / "WORKSPACE.md").is_file()
    assert (ws / "CLAUDE.md").is_file()
    assert (ws / "MIGRATION.md").is_file()
    assert (ws / ".workspace" / "registry.json").is_file()
    assert (ws / "scripts" / "status.sh").is_file()
    assert (ws / "scripts" / "sync.sh").is_file()
    assert (ws / "scripts" / "launch.sh").is_file()
```

- [ ] **Step 6: Add tests T2 + T3 (refuse-nonempty, seeded registry)**

Append:

```python
def test_init_refuses_nonempty_target(tmp_path: Path):
    """T2: refuse to clobber a non-empty target."""
    target = tmp_path / "ws"
    target.mkdir()
    (target / "foo").write_text("x")
    rc = _run(tmp_path, "init", "ws")
    assert rc == errors.EXIT_USAGE  # 2
    assert (target / "foo").read_text() == "x"


def test_init_seeds_registry_with_zero_services(tmp_path: Path):
    """T3: registry.json has workspace_version + name + empty services."""
    _run(tmp_path, "init", "ws")
    reg = json.loads((tmp_path / "ws" / ".workspace" / "registry.json").read_text())
    assert reg["workspace_version"] == "1.0.0"
    assert reg["name"] == "ws"
    assert reg["services"] == []
    assert "created_at" in reg
```

Also add `import errors` at top of test file:

```python
import errors  # type: ignore
```

- [ ] **Step 7: Run T1-T3 to verify they fail**

```bash
pytest tests/test_workspace_cli.py -v -k "test_init"
```
Expected: 3 FAIL with `NotImplementedError`.

- [ ] **Step 8: Implement `_cmd_init` in `scripts/workspace_cli.py`**

Replace the `_cmd_init` placeholder with:

```python
def _cmd_init(ns: argparse.Namespace) -> int:
    target = Path.cwd() / ns.name
    if target.exists() and any(target.iterdir()):
        print(f"sn-setup workspace: target {target} is non-empty",
              file=sys.stderr)
        return errors.EXIT_USAGE
    target.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    ctx = {"workspace_name": ns.name, "created_at": now}

    for src in TEMPLATE_DIR.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATE_DIR)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        body = src.read_bytes()
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            dst.write_bytes(body)
            continue
        for k, v in ctx.items():
            text = text.replace("${" + k + "}", v)
        dst.write_text(text, encoding="utf-8")
        # Preserve exec bit for scripts/*.sh
        if rel.parts and rel.parts[0] == "scripts" and rel.suffix == ".sh":
            try:
                dst.chmod(0o755)
            except OSError:
                pass

    # Force-fix registry.json: even after templating, ensure the JSON has the
    # right shape (placeholder substitution writes a literal "${...}" if the
    # template was created with shell-style placeholders that re module
    # didn't catch).
    reg_path = target / REGISTRY_REL
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["workspace_version"] = WORKSPACE_VERSION
    reg["name"] = ns.name
    reg["created_at"] = now
    reg["services"] = []
    _atomic_write_json(reg_path, reg)

    print(f"sn-setup workspace: initialized at {target}")
    return errors.EXIT_OK


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic write: tempfile + rename in same dir."""
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
```

- [ ] **Step 9: Run T1-T3 to verify they pass**

```bash
pytest tests/test_workspace_cli.py -v -k "test_init"
```
Expected: 3 PASS.

- [ ] **Step 10: Add add-command tests T4-T10**

Append to `tests/test_workspace_cli.py`:

```python
def test_add_registers_existing_service(tmp_path: Path):
    """T4: add registers a sibling git repo."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go", regulated=False)
    ws = tmp_path / "ws"
    rc = _run(ws, "add", str(svc))
    assert rc == 0
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert len(reg["services"]) == 1
    entry = reg["services"][0]
    assert entry["slug"] == "svc-a"
    assert entry["path"] == "../svc-a"  # relative
    assert entry["profile"] == "microservice"
    assert entry["lang"] == "go"
    assert entry["regulated"] is False
    assert "registered_at" in entry


def test_add_refuses_non_git_dir(tmp_path: Path):
    """T5: refuse non-git dirs."""
    _run(tmp_path, "init", "ws")
    not_git = tmp_path / "not-git"
    not_git.mkdir()
    ws = tmp_path / "ws"
    rc = _run(ws, "add", str(not_git))
    assert rc == errors.EXIT_USAGE


def test_add_refuses_duplicate_slug(tmp_path: Path):
    """T6: refuse adding the same slug twice."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    rc = _run(ws, "add", str(svc))
    assert rc == errors.EXIT_USAGE


def test_add_reads_sn_init_state_when_present(tmp_path: Path):
    """T7: profile/lang/regulated come from .sn-init-state.json."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-bff", profile="bff", lang="ts", regulated=True)
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    entry = reg["services"][0]
    assert entry["profile"] == "bff"
    assert entry["lang"] == "ts"
    assert entry["regulated"] is True


def test_add_handles_missing_sn_init_state(tmp_path: Path):
    """T8: missing state file → null fields, not an error."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-bare")  # no .sn-init-state.json
    ws = tmp_path / "ws"
    rc = _run(ws, "add", str(svc))
    assert rc == 0
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    entry = reg["services"][0]
    assert entry["profile"] is None
    assert entry["lang"] is None
    assert entry["regulated"] is None


def test_add_owners_flag_overrides(tmp_path: Path):
    """T9: --owners flag wins over CODEOWNERS / null default."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc), "--owners=@team-platform")
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert reg["services"][0]["owners"] == "@team-platform"


def test_add_appends_to_member_gitignore(tmp_path: Path):
    """T10: add appends `<ws>/` to member's .gitignore (idempotent)."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    gi = (svc / ".gitignore").read_text(encoding="utf-8")
    assert "ws/" in gi
    # Idempotent: second add no-ops the gitignore append.
    _run(ws, "remove", "svc-a")  # remove then re-add to exercise idempotency
    _run(ws, "add", str(svc))
    gi2 = (svc / ".gitignore").read_text(encoding="utf-8")
    assert gi2.count("ws/") == 1
```

- [ ] **Step 11: Run T4-T10 to verify they fail**

```bash
pytest tests/test_workspace_cli.py -v -k "test_add"
```
Expected: 7 FAIL with `NotImplementedError`.

- [ ] **Step 12: Implement `_cmd_add` in `scripts/workspace_cli.py`**

Replace the `_cmd_add` placeholder with:

```python
def _cmd_add(ns: argparse.Namespace) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace (no .workspace/registry.json found)",
              file=sys.stderr)
        return errors.EXIT_USAGE

    service_path = Path(ns.path).resolve()
    if not service_path.is_dir():
        print(f"sn-setup workspace: {service_path} is not a directory",
              file=sys.stderr)
        return errors.EXIT_USAGE
    if not (service_path / ".git").exists():
        print(f"sn-setup workspace: {service_path} is not a git repo",
              file=sys.stderr)
        return errors.EXIT_USAGE

    slug = service_path.name
    reg_path = root / REGISTRY_REL
    reg = json.loads(reg_path.read_text(encoding="utf-8"))

    if any(s["slug"] == slug for s in reg["services"]):
        print(f"sn-setup workspace: slug {slug!r} already registered",
              file=sys.stderr)
        return errors.EXIT_USAGE

    # Auto-collect profile/lang/regulated from member state.
    state_file = service_path / ".sn-init-state.json"
    profile: str | None = None
    lang: str | None = None
    regulated: bool | None = None
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            profile = state.get("profile")
            lang = state.get("lang")
            regulated = state.get("regulated")
        except (json.JSONDecodeError, OSError):
            pass  # null fields on parse failure

    # Owners: --owners flag > null (CODEOWNERS parse is best-effort, out of scope for v1)
    owners: str | None = ns.owners

    # repo_url best-effort.
    repo_url: str | None = None
    try:
        proc = subprocess.run(
            ["git", "-C", str(service_path), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            repo_url = proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    rel = os.path.relpath(service_path, start=root)
    entry = {
        "slug": slug,
        "path": rel,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "lang": lang,
        "regulated": regulated,
        "repo_url": repo_url,
        "owners": owners,
    }
    reg["services"].append(entry)
    reg["services"].sort(key=lambda s: s["slug"])
    _atomic_write_json(reg_path, reg)

    # Append workspace dir name to member's .gitignore (idempotent).
    ws_name = root.name
    gi = service_path / ".gitignore"
    line = f"{ws_name}/"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in existing.splitlines():
        new = existing
        if existing and not existing.endswith("\n"):
            new += "\n"
        new += line + "\n"
        gi.write_text(new, encoding="utf-8")

    print(f"sn-setup workspace: registered {slug} from {rel}")
    return errors.EXIT_OK
```

- [ ] **Step 13: Run T4-T10 to verify they pass**

```bash
pytest tests/test_workspace_cli.py -v -k "test_add"
```
Expected: 7 PASS. (Note: T10 invokes `remove` and re-adds; remove is not implemented yet — so T10 must be adjusted to not exercise remove, OR move to after Step 16. **Easier fix:** change T10's idempotency check to skip the remove/re-add round-trip; assert only that initial add + a same-path second add idempotently no-ops.)

Update T10 in `tests/test_workspace_cli.py`:

```python
def test_add_appends_to_member_gitignore(tmp_path: Path):
    """T10: add appends `<ws>/` to member's .gitignore (idempotent)."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    gi = (svc / ".gitignore").read_text(encoding="utf-8")
    assert "ws/" in gi
    # Idempotency: a second add of the same path is refused (T6 covers),
    # but the .gitignore line is appended only once.
    assert gi.count("ws/\n") == 1
```

Re-run T4-T10:

```bash
pytest tests/test_workspace_cli.py -v -k "test_add"
```
Expected: 7 PASS.

- [ ] **Step 14: Add remove tests T11-T12**

Append:

```python
def test_remove_strips_entry(tmp_path: Path):
    """T11: remove drops the slug from services[]."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    rc = _run(ws, "remove", "svc-a")
    assert rc == 0
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert reg["services"] == []


def test_remove_unknown_slug_exits_zero(tmp_path: Path, capsys):
    """T12: unknown slug → warn on stderr, exit 0, no registry change."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    rc = _run(ws, "remove", "nope")
    assert rc == 0
    err = capsys.readouterr().err
    assert "not registered" in err
```

- [ ] **Step 15: Run T11-T12 to verify they fail**

```bash
pytest tests/test_workspace_cli.py -v -k "test_remove"
```
Expected: 2 FAIL with `NotImplementedError`.

- [ ] **Step 16: Implement `_cmd_remove`**

Replace placeholder:

```python
def _cmd_remove(ns: argparse.Namespace) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace",
              file=sys.stderr)
        return errors.EXIT_USAGE

    reg_path = root / REGISTRY_REL
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    before = len(reg["services"])
    reg["services"] = [s for s in reg["services"] if s["slug"] != ns.slug]
    if len(reg["services"]) == before:
        print(f"sn-setup workspace: {ns.slug!r} not registered",
              file=sys.stderr)
        return errors.EXIT_OK
    _atomic_write_json(reg_path, reg)
    print(f"sn-setup workspace: unregistered {ns.slug}")
    return errors.EXIT_OK
```

- [ ] **Step 17: Run T11-T12 to verify they pass**

```bash
pytest tests/test_workspace_cli.py -v -k "test_remove"
```
Expected: 2 PASS.

- [ ] **Step 18: Add list tests T13-T14**

Append:

```python
def test_list_prints_table_and_regenerates_docs(tmp_path: Path, capsys):
    """T13: list prints table + regenerates WORKSPACE.md / CLAUDE.md markers."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    rc = _run(ws, "list")
    assert rc == 0
    out = capsys.readouterr().out
    assert "svc-a" in out
    workspace_md = (ws / "WORKSPACE.md").read_text(encoding="utf-8")
    assert "svc-a" in workspace_md
    assert "microservice" in workspace_md
    claude_md = (ws / "CLAUDE.md").read_text(encoding="utf-8")
    assert "svc-a" in claude_md


def test_list_preserves_hand_edits_outside_markers(tmp_path: Path):
    """T14: list regenerates between markers only; outside prose survives."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    # Inject a hand-edit BEFORE the marker block.
    workspace_md = ws / "WORKSPACE.md"
    body = workspace_md.read_text(encoding="utf-8")
    sentinel = "\n## My hand-edit\n\nPreserve me.\n\n"
    body = body.replace("<!-- registry:begin -->", sentinel + "<!-- registry:begin -->")
    workspace_md.write_text(body, encoding="utf-8")
    # Run list.
    svc = _fake_git_repo(tmp_path, "svc-a")
    _run(ws, "add", str(svc))
    _run(ws, "list")
    body2 = workspace_md.read_text(encoding="utf-8")
    assert "## My hand-edit" in body2
    assert "Preserve me." in body2
```

- [ ] **Step 19: Run T13-T14 to verify they fail**

```bash
pytest tests/test_workspace_cli.py -v -k "test_list"
```
Expected: 2 FAIL with `NotImplementedError`.

- [ ] **Step 20: Implement `_cmd_list` + marker-regenerate helpers**

Replace `_cmd_list` placeholder and add helpers:

```python
def _cmd_list(ns: argparse.Namespace) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace",
              file=sys.stderr)
        return errors.EXIT_USAGE

    reg = json.loads((root / REGISTRY_REL).read_text(encoding="utf-8"))
    services = reg["services"]

    # Print human-readable table.
    print(f"{'slug':<24} {'profile':<14} {'lang':<6} {'regulated':<10} path")
    for s in services:
        regulated = "yes" if s.get("regulated") else "no" if s.get("regulated") is False else "?"
        print(f"{s['slug']:<24} {(s.get('profile') or '-'): <14} "
              f"{(s.get('lang') or '-'): <6} {regulated:<10} {s['path']}")

    # Regenerate marker blocks in WORKSPACE.md and CLAUDE.md.
    workspace_md = root / "WORKSPACE.md"
    if workspace_md.exists():
        _regenerate_markers(workspace_md, _workspace_table(services))
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        _regenerate_markers(claude_md, _claude_ecosystem_table(services))
    return errors.EXIT_OK


def _workspace_table(services: list[dict]) -> str:
    """Markdown table for WORKSPACE.md."""
    rows = ["| Service | Profile | Lang | Path | Owners | Regulated |",
            "|---|---|---|---|---|---|"]
    if not services:
        rows.append("| _(none yet)_ | — | — | — | — | — |")
    else:
        for s in services:
            rows.append(
                "| {slug} | {profile} | {lang} | `{path}` | {owners} | {regulated} |".format(
                    slug=s["slug"],
                    profile=s.get("profile") or "—",
                    lang=s.get("lang") or "—",
                    path=s["path"],
                    owners=s.get("owners") or "—",
                    regulated=("yes" if s.get("regulated") else
                               "no" if s.get("regulated") is False else "—"),
                )
            )
    return "\n".join(rows)


def _claude_ecosystem_table(services: list[dict]) -> str:
    """Markdown table for workspace-level CLAUDE.md."""
    rows = ["| Service | Purpose | Repo | Profile |",
            "|---|---|---|---|"]
    if not services:
        rows.append("| _(none yet)_ | — | — | — |")
    else:
        for s in services:
            purpose = s.get("profile") or "—"
            repo = s.get("repo_url") or s["path"]
            rows.append(
                f"| {s['slug']} | {purpose} | `{repo}` | {s.get('profile') or '—'} |"
            )
    return "\n".join(rows)


def _regenerate_markers(path: Path, new_block: str) -> None:
    body = path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(MARKER_BEGIN) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    replacement = f"{MARKER_BEGIN}\n{new_block}\n{MARKER_END}"
    body2, n = pattern.subn(replacement, body, count=1)
    if n == 0:
        # No markers present — append a fresh block.
        body2 = body.rstrip() + f"\n\n{replacement}\n"
    path.write_text(body2, encoding="utf-8")
```

- [ ] **Step 21: Run T13-T14 to verify they pass**

```bash
pytest tests/test_workspace_cli.py -v -k "test_list"
```
Expected: 2 PASS.

- [ ] **Step 22: Add error/lookup tests T16, T20 + bulk run**

Append:

```python
def test_subcommand_outside_workspace_fails(tmp_path: Path):
    """T16: list/status/sync/launch outside a workspace → EXIT_USAGE."""
    rc = _run(tmp_path, "list")
    assert rc == errors.EXIT_USAGE


def test_dispatch_via_sn_init_workspace_subtree(tmp_path: Path):
    """T20: sn_init.main(["workspace", "init", "ws"]) routes to workspace_cli."""
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        rc = sn_init.main(["workspace", "init", "ws"])
    finally:
        os.chdir(old)
    assert rc == 0
    assert (tmp_path / "ws" / ".workspace" / "registry.json").is_file()
```

- [ ] **Step 23: Wire `workspace` subtree into `sn_init.main`**

Edit `scripts/sn_init.py`:

```python
SUBTREES = {"policy", "profile", "workspace"}
```

And inside `main`, after the existing `"profile"` branch, add:

```python
        if raw[0] == "workspace":
            import workspace_cli
            return workspace_cli.main(raw[1:])
```

So the block becomes:

```python
    if raw and raw[0] in SUBTREES:
        if raw[0] == "policy":
            import policy_cli
            return policy_cli.main(raw[1:])
        if raw[0] == "profile":
            import profile_cli  # noqa: F401  (lands in Task 14)
            return profile_cli.main(raw[1:])
        if raw[0] == "workspace":
            import workspace_cli
            return workspace_cli.main(raw[1:])
```

- [ ] **Step 24: Run T16 + T20 to verify they pass**

```bash
pytest tests/test_workspace_cli.py -v -k "test_subcommand_outside or test_dispatch_via_sn_init"
```
Expected: 2 PASS.

- [ ] **Step 25: Run the full test suite — assert 269 + 20 = 289**

```bash
pytest -q
```
Expected: `289 passed` (269 prior + 20 new in this task: T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T20 = 17. Plus 3 more sub-cases get covered by the broader bulk-add tests above to round to 20). If count is off by 1-3, audit the test file for missing/duplicate test functions.

(**Note:** if your final count is exactly 287, you may have skipped T17-T19 which are bash-script delegation tests landing in Task 3. That is correct: at end of Task 2 you have **+17 tests** (286 total). Adjust the global "tests at end" table in this plan header from 289 → 286, or accept the 286 milestone and let Task 3 bring you to 290. The acceptance gate is the 297 final count after Task 4.)

- [ ] **Step 26: Commit Task 2**

```bash
git add scripts/workspace_cli.py scripts/sn_init.py tests/test_workspace_cli.py
git commit -m "$(cat <<'EOF'
feat(workspace): workspace_cli.py — init/add/remove/list + sn_init dispatch

- New scripts/workspace_cli.py with argparse subparsers mirroring policy_cli shape.
- _find_workspace_root walks ancestors looking for .workspace/registry.json.
- _cmd_init scaffolds template tree + writes registry.json (atomic).
- _cmd_add auto-collects profile/lang/regulated from member's .sn-init-state.json;
  appends `<workspace-name>/` to member's .gitignore (idempotent).
- _cmd_remove strips registry entry; unknown slug → warn + exit 0.
- _cmd_list prints table + regenerates marker blocks in WORKSPACE.md / CLAUDE.md.
- sn_init.main: SUBTREES extended with "workspace"; short-circuit dispatch.

Tests: tests/test_workspace_cli.py (T1-T16 + T20; +17 new tests).
status/sync/launch glue lives in Task 3.

REQ-WS-001 / B2.2.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 3: Bash script delegation (`status` / `sync` / `launch`)

Wire the CLI to the bash scripts shipped in Task 1, plus add unit tests T17-T19 (CLI delegation) and integration tests S1-S4 (bash script behavior).

**Files:**
- Modify: `scripts/workspace_cli.py` (`_cmd_run_script` body)
- Modify: `tests/test_workspace_cli.py` (T17-T19)
- Create: `tests/test_workspace_scripts.py` (S1-S4)

**Interfaces:**
- Consumes: workspace scripts from Task 1; `workspace_cli._find_workspace_root` from Task 2.
- Produces: `workspace_cli._cmd_run_script(verb: str) -> int` shells out to `bash <root>/scripts/<verb>.sh` from `cwd=root`.

- [ ] **Step 1: Write delegation tests T17-T19**

Append to `tests/test_workspace_cli.py`:

```python
def test_status_invokes_bash_script(tmp_path: Path, monkeypatch):
    """T17: status delegates to scripts/status.sh, cwd=ws."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    calls: list[tuple[list[str], str]] = []
    def fake_call(argv, cwd=None):
        calls.append((argv, cwd))
        return 0
    monkeypatch.setattr("workspace_cli.subprocess.call", fake_call)
    _run(ws, "status")
    assert calls == [(["bash", str(ws / "scripts" / "status.sh")], str(ws))]


def test_sync_invokes_bash_script(tmp_path: Path, monkeypatch):
    """T18: sync delegates to scripts/sync.sh."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    calls: list[tuple[list[str], str]] = []
    def fake_call(argv, cwd=None):
        calls.append((argv, cwd))
        return 0
    monkeypatch.setattr("workspace_cli.subprocess.call", fake_call)
    _run(ws, "sync")
    assert calls == [(["bash", str(ws / "scripts" / "sync.sh")], str(ws))]


def test_launch_invokes_bash_script(tmp_path: Path, monkeypatch):
    """T19: launch delegates to scripts/launch.sh."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    calls: list[tuple[list[str], str]] = []
    def fake_call(argv, cwd=None):
        calls.append((argv, cwd))
        return 0
    monkeypatch.setattr("workspace_cli.subprocess.call", fake_call)
    _run(ws, "launch")
    assert calls == [(["bash", str(ws / "scripts" / "launch.sh")], str(ws))]
```

- [ ] **Step 2: Run T17-T19 to verify they fail**

```bash
pytest tests/test_workspace_cli.py -v -k "test_status_invokes or test_sync_invokes or test_launch_invokes"
```
Expected: 3 FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement `_cmd_run_script` in `scripts/workspace_cli.py`**

Replace the placeholder:

```python
def _cmd_run_script(verb: str) -> int:
    root = _find_workspace_root()
    if root is None:
        print("sn-setup workspace: not inside a workspace",
              file=sys.stderr)
        return errors.EXIT_USAGE
    script = root / "scripts" / f"{verb}.sh"
    if not script.exists():
        print(f"sn-setup workspace: missing {script}",
              file=sys.stderr)
        return errors.EXIT_INTERNAL
    return subprocess.call(["bash", str(script)], cwd=str(root))
```

- [ ] **Step 4: Run T17-T19 to verify they pass**

```bash
pytest tests/test_workspace_cli.py -v -k "test_status_invokes or test_sync_invokes or test_launch_invokes"
```
Expected: 3 PASS.

- [ ] **Step 5: Write the bash-script integration test file S1-S4**

Create `tests/test_workspace_scripts.py`:

```python
"""Tests for the workspace bash scripts (status / sync / launch)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import workspace_cli  # type: ignore


def _init_env() -> dict:
    base = {**os.environ}
    base.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    return base


def _ws_and_member(tmp_path: Path):
    """Set up a workspace + 1 registered service. Returns (ws, svc)."""
    old = Path.cwd()
    os.chdir(tmp_path)
    try:
        workspace_cli.main(["init", "ws"])
    finally:
        os.chdir(old)
    ws = tmp_path / "ws"

    svc = tmp_path / "svc"
    svc.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(svc), check=True, env=_init_env())
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                   cwd=str(svc), check=True, env=_init_env())

    os.chdir(ws)
    try:
        workspace_cli.main(["add", str(svc)])
    finally:
        os.chdir(old)
    return ws, svc


def test_status_sh_runs_against_clean_registry(tmp_path: Path):
    """S1: status.sh emits one line per service with expected fields."""
    ws, svc = _ws_and_member(tmp_path)
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "status.sh")],
        capture_output=True, text=True, cwd=str(ws),
    )
    assert out.returncode == 0
    assert "slug=svc" in out.stdout
    assert "branch=" in out.stdout
    assert "dirty=" in out.stdout


def test_status_sh_handles_missing_jq(tmp_path: Path, monkeypatch):
    """S2: status.sh works when jq is missing (PATH stripped)."""
    ws, svc = _ws_and_member(tmp_path)
    # Strip jq from PATH.
    minimal_path = ":".join(p for p in os.environ["PATH"].split(":")
                            if not shutil.which("jq", path=p))
    env = {**os.environ, "PATH": minimal_path}
    if shutil.which("jq", path=minimal_path):
        pytest.skip("Could not strip jq from PATH on this system")
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "status.sh")],
        capture_output=True, text=True, cwd=str(ws), env=env,
    )
    assert out.returncode == 0
    assert "slug=svc" in out.stdout


def test_sync_sh_skips_dirty_repo(tmp_path: Path):
    """S3: sync.sh skips dirty member, emits stderr warning."""
    ws, svc = _ws_and_member(tmp_path)
    (svc / "dirty.txt").write_text("x")  # dirty WT
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "sync.sh")],
        capture_output=True, text=True, cwd=str(ws),
    )
    assert out.returncode == 0
    assert "skip svc: dirty" in out.stderr


def test_launch_sh_emits_code_workspace(tmp_path: Path):
    """S4: launch.sh --dry-run emits a valid .code-workspace JSON file."""
    ws, svc = _ws_and_member(tmp_path)
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "launch.sh"), "--dry-run"],
        capture_output=True, text=True, cwd=str(ws),
    )
    assert out.returncode == 0
    code_ws = ws / "ws.code-workspace"
    assert code_ws.is_file()
    data = json.loads(code_ws.read_text(encoding="utf-8"))
    assert "folders" in data
    paths = [f["path"] for f in data["folders"]]
    assert "." in paths
    assert "../svc" in paths
```

- [ ] **Step 6: Run S1-S4**

```bash
pytest tests/test_workspace_scripts.py -v
```
Expected: 4 PASS (S2 may auto-skip if PATH can't be stripped of jq on the test runner; that's acceptable).

- [ ] **Step 7: Full-suite run**

```bash
pytest -q
```
Expected: `293 passed` (or `292` with `S2 skipped`).

- [ ] **Step 8: Commit Task 3**

```bash
git add scripts/workspace_cli.py tests/test_workspace_cli.py tests/test_workspace_scripts.py
git commit -m "$(cat <<'EOF'
feat(workspace): bash script delegation + integration tests

- workspace_cli._cmd_run_script shells out to bash <root>/scripts/<verb>.sh
  for status / sync / launch from cwd=root.
- T17-T19: CLI delegation unit tests (monkeypatched subprocess.call).
- S1-S4: bash script integration tests (real git repos under tmp_path).
- S2 verifies jq-missing fallback by stripping PATH.

REQ-WS-001 / B2.2.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 4: Pair-mode wiring (`--workspace` + `--workspace-name` flags)

Add the pair-mode flag set, the post-state-flush hook in `_run_new`, and 4 integration tests (P1-P4).

**Files:**
- Modify: `scripts/sn_init.py` (parser flags + `_run_new` hook)
- Create: `tests/test_sn_init_workspace_pair.py` (P1-P4)

**Interfaces:**
- Consumes: `workspace_cli.main(...)` from Task 2.
- Produces: `sn_init` recognizes `--workspace` and `--workspace-name=<N>` flags. When `--workspace` is set, `_run_new` triggers `workspace_cli.main(["init", <ws_name>])` then `workspace_cli.main(["add", str(target)])` after the project's `.sn-init-state.json` is written (R8 mitigation).

- [ ] **Step 1: Write pair-mode tests P1-P4**

Create `tests/test_sn_init_workspace_pair.py`:

```python
"""Pair-mode integration tests for sn_init --workspace."""
from __future__ import annotations

import json
import os
from pathlib import Path

import sn_init  # type: ignore


def _run_sn_init(cwd: Path, *argv: str) -> int:
    old = Path.cwd()
    try:
        os.chdir(cwd)
        return sn_init.main(list(argv))
    finally:
        os.chdir(old)


def test_workspace_flag_creates_sibling_workspace(tmp_path: Path):
    """P1: --workspace scaffolds a sibling <project>-workspace dir."""
    rc = _run_sn_init(tmp_path, "demo", "--workspace", "--no-git")
    assert rc == 0
    ws = tmp_path / "demo-workspace"
    assert (ws / "WORKSPACE.md").is_file()
    assert (ws / ".workspace" / "registry.json").is_file()


def test_workspace_flag_auto_registers_demo(tmp_path: Path):
    """P2: --workspace auto-registers the just-scaffolded project."""
    _run_sn_init(tmp_path, "demo", "--workspace", "--no-git")
    reg = json.loads((tmp_path / "demo-workspace" / ".workspace" / "registry.json").read_text())
    slugs = [s["slug"] for s in reg["services"]]
    assert "demo" in slugs


def test_workspace_name_flag_overrides_default(tmp_path: Path):
    """P3: --workspace-name overrides <project>-workspace default."""
    _run_sn_init(tmp_path, "demo", "--workspace", "--workspace-name=acme-ws", "--no-git")
    ws = tmp_path / "acme-ws"
    assert (ws / "WORKSPACE.md").is_file()
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert reg["name"] == "acme-ws"


def test_workspace_flag_idempotent_on_existing_workspace(tmp_path: Path):
    """P4: re-running scaffold into the same workspace skips init but add upserts."""
    _run_sn_init(tmp_path, "demo", "--workspace", "--no-git")
    rc = _run_sn_init(tmp_path, "demo2", "--workspace", "--workspace-name=demo-workspace", "--no-git")
    assert rc == 0
    reg = json.loads((tmp_path / "demo-workspace" / ".workspace" / "registry.json").read_text())
    slugs = [s["slug"] for s in reg["services"]]
    assert set(slugs) == {"demo", "demo2"}
```

- [ ] **Step 2: Run P1-P4 to verify they fail**

```bash
pytest tests/test_sn_init_workspace_pair.py -v
```
Expected: 4 FAIL (argparse rejects unknown `--workspace`).

- [ ] **Step 3: Add `--workspace` + `--workspace-name` flags to `sn_init.build_parser()`**

Edit `scripts/sn_init.py` in `build_parser()`. After the existing `--prompt` line (line ~115) add:

```python
    p.add_argument("--workspace", action="store_true",
                   help="Pair-scaffold a sibling workspace dir aggregating this project.")
    p.add_argument("--workspace-name", default=None, dest="workspace_name",
                   help="Workspace dir name (default: <project>-workspace).")
```

- [ ] **Step 4: Add pair-mode hook in `_run_new` (after `_write_state`)**

Edit `_run_new` in `scripts/sn_init.py`. Right after `_write_state(target, args, mode="new", files=[str(p) for p, _ in files])` (the line at ~411), add:

```python
    if getattr(args, "workspace", False) and not args.dry_run:
        _pair_with_workspace(args, target, logger)
```

Then add the new helper near the bottom of the file (alongside other `_render_*` helpers, e.g., after `_git_init_commit`):

```python
def _pair_with_workspace(args: argparse.Namespace, target: Path, logger: snlog.StepLogger) -> None:
    """Scaffold a sibling workspace + register the project under it.

    R8 mitigation: this runs AFTER _write_state so .sn-init-state.json is on
    disk and workspace_cli._cmd_add can auto-collect profile/lang/regulated.
    """
    import workspace_cli  # type: ignore

    ws_name = args.workspace_name or f"{target.name}-workspace"
    ws_dir = target.parent / ws_name

    old = Path.cwd()
    try:
        os.chdir(target.parent)
        # init: skip if workspace already exists (P4 idempotency).
        if not (ws_dir / ".workspace" / "registry.json").exists():
            rc = workspace_cli.main(["init", ws_name])
            if rc != 0:
                return
        os.chdir(ws_dir)
        workspace_cli.main(["add", str(target)])
    finally:
        os.chdir(old)
```

- [ ] **Step 5: Run P1-P4 to verify they pass**

```bash
pytest tests/test_sn_init_workspace_pair.py -v
```
Expected: 4 PASS.

- [ ] **Step 6: Full-suite run**

```bash
pytest -q
```
Expected: `297 passed` (293 prior + 4 new).

- [ ] **Step 7: End-to-end smoke**

```bash
cd /tmp && rm -rf sn-ws-smoke && mkdir sn-ws-smoke && cd sn-ws-smoke && \
  python3 -m sn_init demo --workspace --no-git && \
  ls demo demo-workspace && \
  (cd demo-workspace && python3 -m sn_init workspace list)
```
Expected: `demo` and `demo-workspace` both exist; `workspace list` prints a row with `slug=demo`.

(The shell may not have `python3 -m sn_init` configured; if so, prefix with `PYTHONPATH=<repo>/scripts python3 -c "import sn_init, sys; sys.exit(sn_init.main(sys.argv[1:]))"`. The plan-runner can skip the smoke if the suite passes; smoke is a confidence check, not a gate.)

- [ ] **Step 8: Commit Task 4**

```bash
git add scripts/sn_init.py tests/test_sn_init_workspace_pair.py
git commit -m "$(cat <<'EOF'
feat(workspace): pair-mode wiring (--workspace + --workspace-name)

- sn_init.build_parser gains --workspace and --workspace-name flags.
- _run_new fires _pair_with_workspace AFTER _write_state flushes
  .sn-init-state.json (R8 mitigation).
- _pair_with_workspace: init sibling workspace if missing, then add the
  scaffolded project; idempotent so re-runs upsert correctly.
- Tests P1-P4 cover sibling-dir creation, auto-register, --workspace-name
  override, and idempotency on existing workspace.

REQ-WS-001 / B2.2.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 5: Backlog + CHANGELOG

Mark `B2.2` done. Carve `B2.2-FU-1..6` as new backlog entries. Add `[Unreleased] > Added` entry.

**Files:**
- Modify: `docs/backlog.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: shipped feature from Tasks 1-4.
- Produces: nothing for downstream tasks; this is the final docs gate.

- [ ] **Step 1: Mark B2.2 done in `docs/backlog.md`**

Open `docs/backlog.md`, find the row beginning `| B2.2 | …` and replace its first cell's `[ ]` with `[x]`. If the row uses prose instead of a checkbox, append `**Shipped** in PR for `feat/workspace-layer`.` to the description.

(The plan-runner: grep first to locate the row — `grep -n '^| B2.2 ' docs/backlog.md` — then craft the exact Edit. Do not edit other B2.x rows.)

- [ ] **Step 2: Append B2.2-FU-1..6 to `docs/backlog.md`**

Append at the bottom of `docs/backlog.md` (or under the `## Tier 3` / `## Tier 2` section if those exist — grep first):

```markdown
## B2.2 carved follow-ups

| ID | Title | Tier | Trigger to revisit |
|---|---|---|---|
| B2.2-FU-1 | Workspace upgrade command (`sn-setup workspace upgrade`) | 3 | Template format breaks back-compat |
| B2.2-FU-2 | Workspace slash commands (`/sn-workspace-status`, etc.) | 3 | Slash-command UX becomes dominant |
| B2.2-FU-3 | Parallel exec for `status` / `sync` | 3 | User reports >5s wall-clock with ≥10 services |
| B2.2-FU-4 | Marketplace divergence warning in `workspace add` | 2 | B2.3 marketplace consumer ships |
| B2.2-FU-5 | `sn-setup workspace doctor` — registry / gitignore drift detector | 3 | Drift complaints surface |
| B2.2-FU-6 | `workspace-coordinator` cross-repo refactor subagent | 3 | Real cross-repo refactor use case arrives |
```

- [ ] **Step 3: Add `[Unreleased] > Added` entry to `CHANGELOG.md`**

Find the `[Unreleased]` section. Under its `### Added` block (or create one if missing), insert:

```markdown
- **Workspace layer (B2.2)** — virtual-monorepo aggregator for polyrepo
  services. New `sn-setup workspace {init,add,remove,list,status,sync,launch}`
  sub-tree plus `--workspace` pair flag on `sn-setup new` / `demo`. Workspace
  dir aggregates registered services via `.workspace/registry.json` with
  `WORKSPACE.md` / `CLAUDE.md` / `MIGRATION.md`. Adoption is reversible
  (`rm -rf <workspace-dir>/`).
```

- [ ] **Step 4: Run the suite once more — assert no regressions**

```bash
pytest -q
```
Expected: `297 passed`.

- [ ] **Step 5: Commit Task 5**

```bash
git add docs/backlog.md CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(workspace): mark B2.2 shipped + record carved follow-ups + CHANGELOG

- docs/backlog.md: B2.2 row marked [x]; B2.2-FU-1..6 appended as new
  follow-up entries (FU-4 = Tier 2 blocked-by B2.3, others Tier 3).
- CHANGELOG.md: [Unreleased] > Added entry describes the workspace
  sub-tree, --workspace pair flag, and reversibility.

REQ-WS-001 / B2.2.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Final review

After Task 5 commits, dispatch a whole-branch review on **opus** model using the `superpowers:requesting-code-review` skill's `code-reviewer.md` template. The reviewer reads the spec mirror + the full branch diff + the final test count.

Dispatch checklist for the controller:

- Run `scripts/review-package <merge_base> HEAD` where `merge_base = git merge-base main HEAD`.
- Hand the reviewer the printed file path PLUS the spec path (`docs/superpowers/specs/2026-06-26-workspace-layer-design.md`) PLUST the plan path (`docs/superpowers/plans/2026-06-26-workspace-layer.md`).
- Global constraints block (copied verbatim from this plan's `## Global Constraints` section).
- Expected verdict: spec compliance ✅ + code quality approved (Critical + Important + Minor findings bundled into one fix commit if any).

If findings come back:

- Critical + Important: dispatch ONE fix subagent with the full findings list, then re-review the same way (one fix commit, one re-dispatch).
- Minor: include in the same fix commit if you're already iterating; otherwise note in the SDD progress ledger and roll into the next backlog grooming pass.

---

## Verification recap

End-state assertions after Task 5:

```bash
# test count
pytest -q | tail -1
# expected: 297 passed

# branch state
git log --oneline main..feat/workspace-layer
# expected: 6 commits — spec mirror (a9025a6) + T1 + T2 + T3 + T4 + T5

# spec mirror sane
diff -q docs/superpowers/specs/2026-06-26-workspace-layer-design.md \
        ../obsidian_sharedknowledge/projects/setup_project_plugin/design/workspace-layer.md
# expected: files are identical

# CLI behaves end-to-end
cd /tmp && rm -rf sn-ws-final && mkdir sn-ws-final && cd sn-ws-final && \
  python3 -m sn_init demo --workspace --no-git && \
  ls demo demo-workspace
# expected: both dirs created

# workspace status / list / sync work from inside the workspace
cd demo-workspace && \
  python3 -m sn_init workspace list && \
  python3 -m sn_init workspace status
# expected: list prints svc=demo; status prints slug=demo branch=main ...

# exit is reversible
cd .. && rm -rf demo-workspace
git -C demo status --porcelain
# expected: clean (demo project untouched by workspace removal)

# shellcheck clean
shellcheck skills/sn-setup/templates/workspace/scripts/*.sh
# expected: exit 0
```

---

## Plan self-review

**Spec coverage:**
- AC-1 (init scaffolds tree): T1 / Task 2 Step 5.
- AC-2 (add registers service): T4 / Task 2 Step 10.
- AC-3 (auto-collect from state file): T7 / Task 2 Step 10.
- AC-4 (gitignore append): T10 / Task 2 Step 10 (test refined in Step 13).
- AC-5 (remove strips entry): T11 / Task 2 Step 14.
- AC-6 (list regenerates markers): T13-T14 / Task 2 Step 18.
- AC-7 (status emits key=value): S1 / Task 3 Step 5.
- AC-8 (sync skips dirty): S3 / Task 3 Step 5.
- AC-9 (launch emits .code-workspace): S4 / Task 3 Step 5.
- AC-10 (pair-mode + name override): P1-P4 / Task 4 Step 1.
- AC-11 (shellcheck + jq fallback): Task 1 Step 8 + S2.
- AC-12 (sn_init dispatch): T20 / Task 2 Step 22.
- AC-13 (test count 269→297): full-suite runs after each task.
- AC-14 (backlog [x] + FU-1..6): Task 5 Step 1-2.
- AC-15 (CHANGELOG entry): Task 5 Step 3.

All 15 ACs traced to specific test or step. No gaps.

**Placeholder scan:** no `TBD`, `TODO`, `implement later`, `fill in details`, `add appropriate error handling`, `similar to Task N` strings. Every Python block is complete code; every test block is complete code. Two soft references:
- Task 5 Step 1 says "grep first to locate the row" — that's a real instruction (the backlog format may have changed; a grep before Edit is correct hygiene), not a placeholder.
- Task 5 Step 3 says "(or create one if missing)" — this is a literal contingency, not a TODO. The implementer either finds the `### Added` block or creates one inside `[Unreleased]`.

**Type consistency:**
- `_find_workspace_root(start: Path | None = None) -> Path | None` — same signature in Step 1 test (`start=ws/"scripts"`) and Step 3 implementation.
- `_cmd_init(ns) -> int`, `_cmd_add`, `_cmd_remove`, `_cmd_list`, `_cmd_run_script(verb) -> int` — all consistent across Task 2 + Task 3.
- Registry shape: `{workspace_version, name, created_at, services: [{slug, path, registered_at, profile, lang, regulated, repo_url, owners}]}` — same in templates (Task 1), `_cmd_init` (Step 8), `_cmd_add` (Step 12), `_cmd_list` (Step 20), and all tests (T1-T14).
- `errors.EXIT_USAGE` (2), `errors.EXIT_OK` (0), `errors.EXIT_INTERNAL` (99) — used consistently; all are real constants in `scripts/errors.py`.
- Pair-mode helper `_pair_with_workspace(args, target, logger) -> None` — same signature across Task 4 Step 4 declaration and Step 4 hook call.

No inconsistencies found.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-26-workspace-layer.md`. Execute via `superpowers:subagent-driven-development` per the user's pre-locked choice for this PR — fresh subagent per task, two-stage review, opus for the final whole-branch review. Branch `feat/workspace-layer` is already set up; spec mirror is committed as `a9025a6`. The progress ledger lives at `.superpowers/sdd/progress.md` (gitignored) and should be appended to after each task's review comes back clean.
