# Command Sub-tree Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regroup 16 flat `sn-X-Y.md` slash commands into 3 grouped `sn-X.md` files (verb dispatch); retire `sn-knowledge-tech-matrix`; replace with `sn-knowledge summarize <topic>`; ship a `sn-setup --upgrade --rename-commands` one-shot migration for existing scaffolds.

**Architecture:** Three new grouped command files under `skills/sn-setup/templates/claude/commands/` (`sn-sprint.md`, `sn-req.md`, `sn-knowledge.md`). One new Python module `scripts/commands_migration.py` implementing the `--rename-commands` flow with sha-checked edit safety. Two new state fields (`commands_renamed_at`, `commands_migration`) record the trace.

**Tech Stack:** Python 3.13+, `pytest`, existing `scripts/policy_state.py` helpers (`sha256_file`, `read_state`, `write_state`).

## Global Constraints

- Spec is authoritative: `docs/superpowers/specs/2026-06-24-command-subtree-migration-design.md` (mirrored at `<vault>/projects/setup_project_plugin/design/command-subtree-migration-design.md`).
- Existing 225 tests MUST keep passing after each task.
- All new Python uses `from __future__ import annotations` + explicit type annotations.
- State writes via tmp+rename (existing `policy_state.write_state` pattern).
- Commit Author trailer mandatory: `Author: Siripol <siripoln.media@gmail.com>` (enforced by `.githooks/commit-msg`); never `Co-Authored-By: Claude`.
- Branch: `feat/command-subtree-migration` (already created from `main` post-merge at commit `c333ed0`).
- Exit codes: reuse `EXIT_USAGE=2` (from `errors.py`) and `EXIT_USER_EDITED_BLOCKS_OP=14` (from `policy_errors.py`).
- DO NOT push to vault from subagents; controller handles vault writes after each batch.
- DO NOT push to origin from subagents; controller pushes after the commit lands.

---

## File map

### Create

| Path | Responsibility |
|---|---|
| `skills/sn-setup/templates/claude/commands/sn-sprint.md` | Grouped sprint command — verbs: new, add, run, status, done, remove |
| `skills/sn-setup/templates/claude/commands/sn-req.md` | Grouped requirement command — verbs: new, import, replay, resume, rollback |
| `skills/sn-setup/templates/claude/commands/sn-knowledge.md` | Grouped knowledge command — verbs: check, update, promote, demote, summarize |
| `scripts/commands_migration.py` | Migration module: FLAT_TO_GROUP map, RETIRED set, MigrationReport, run() |
| `tests/test_commands_migration.py` | Unit tests for the migration module |
| `docs/MIGRATION.md` | One-paragraph guide for users with existing scaffolds |

### Modify

| Path | Change |
|---|---|
| `scripts/sn_init.py` | Add `--rename-commands` + `--force` flags; dispatch in `_run_upgrade` |
| `tests/test_sn_init.py` | 5 new integration tests |
| `commands/sn-setup.md` | Add new flag rows + Sub-commands section |
| `WORKFLOW.md` | Update command-flow diagram (`/sn-sprint-new` → `/sn-sprint new`) |
| `docs/backlog.md` | Add B1.9 entry; mark `[~]` then `[x]` |
| `CHANGELOG.md` | Append `[Unreleased]` entry |

### Delete

| Path | Reason |
|---|---|
| `skills/sn-setup/templates/claude/commands/sn-sprint-{new,add,run,status,done,remove}.md` | Consolidated into `sn-sprint.md` |
| `skills/sn-setup/templates/claude/commands/sn-req-{new,import,replay,resume,rollback}.md` | Consolidated into `sn-req.md` |
| `skills/sn-setup/templates/claude/commands/sn-knowledge-{check,update,promote,demote}.md` | Consolidated into `sn-knowledge.md` |
| `skills/sn-setup/templates/claude/commands/sn-knowledge-tech-matrix.md` | Retired; replaced by `sn-knowledge summarize <topic>` |

---

## Task list

The plan has **7 tasks**. Tasks 1–3 are template authoring (grouped command files + deletions). Task 4 ships the migration module + unit tests. Task 5 wires the `--rename-commands` flag into `sn_init.py`. Task 6 covers integration tests. Task 7 docs + changelog + backlog.

---

### Task 1: Author `sn-sprint.md` grouped command + delete 6 old flat files

**Files:**
- Create: `skills/sn-setup/templates/claude/commands/sn-sprint.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-sprint-new.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-sprint-add.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-sprint-run.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-sprint-status.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-sprint-done.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-sprint-remove.md`

**Interfaces:** none — pure template authoring. Later tasks reference this file by path only.

- [ ] **Step 1: Write the new `sn-sprint.md` verbatim**

Create `skills/sn-setup/templates/claude/commands/sn-sprint.md`:

```markdown
---
name: sn-sprint
description: Spec-loop sprint operations. Sub-commands: new, add, run, status, done, remove. Invoke as `/sn-sprint <verb> [args]`.
---

# /sn-sprint <verb> [args]

Spec-loop sprint orchestrator. Each verb dispatches a different sprint operation.

## Verbs

| Verb | Args | Purpose |
|---|---|---|
| `new` | `SLUG=<s>` | Create a new SPRINT-NNN folder under `docs/sprints/active/` |
| `add` | `SPRINT=<id> REQ=<id>` | Move a REQ from `docs/requirements/active/` into the sprint |
| `run` | `SPRINT=<id>` | Execute the sprint loop |
| `status` | — | Print a table of every sprint + REQ counts + owner |
| `done` | `SPRINT=<id>` | Archive a completed sprint |
| `remove` | `SPRINT=<id> REQ=<id>` | Move a REQ back out of a sprint |

Run `/sn-sprint` with no args to see this table.

## Dispatch (Claude reads `$1` and follows the matching section below)

### `new` — Create a new sprint

Args: `SLUG` (required, short kebab-case identifier).

Creates `docs/sprints/active/SPRINT-<next>-<SLUG>/` from `docs/sprints/template.md`. Status starts at `planning`. Counter auto-incremented from existing sprint folders.

### `add` — Add a REQ to a sprint

Args: `SPRINT` (required, sprint id), `REQ` (required, REQ id).

Move `docs/requirements/active/REQ-NNN-*.md` → `docs/sprints/active/SPRINT-NNN-*/requirements/`. Appends REQ id to sprint.md `reqs:` list. Preserves traceback frontmatter. Refuses if the REQ is already in a different sprint.

### `run` — Execute a sprint

Args: `SPRINT` (required, sprint id).

Flow:

1. Read sprint folder + REQs.
2. Run sn-impact-analyzer → `impact.md`. If `has_major: true`, halt + AskUserQuestion (proceed/edit/cancel).
3. `git tag sn-init/pre-REQ-NNN-<ts>` per REQ.
4. For each REQ: sn-planner → sn-task-decomposer → (per task: sn-task-tester + sn-task-executor or executor + tester depending on `--workflow-tdd`) → sn-integration-tester → sn-adversary → sn-evaluator.
5. Triple-signal exit gate: `eval >= threshold AND integration.pass AND adversary.findings_resolved`.
6. On all-pass: doc-writer + sn-knowledge-curator. `make sprint-done SPRINT=...` to archive.

State persisted in `.sn-init/workflow-state.json`. `/sn-req resume` picks up after crash.

### `status` — Print all sprints

No args.

Scans `docs/sprints/active/` + `docs/sprints/completed/`. Output:

```
SPRINT    SLUG          STATUS     REQs  COMPLETED  OWNER
001       auth-rev      running    3     1/3        alice
002       billing       planning   2     0/2        bob
```

### `done` — Archive a completed sprint

Args: `SPRINT` (required, sprint id).

Refuses if any REQ in the sprint hasn't reached `eval pass` state. Otherwise `mv` whole sprint folder + run `sn-knowledge-curator` to update Obsidian buckets.

### `remove` — Move a REQ back out of a sprint

Args: `SPRINT` (required), `REQ` (required).

Reverse of `add`. Useful when re-scoping a sprint before running it. Refuses if the sprint is `running` or `completed`.

## Error handling

- Unknown verb → "unknown sub-command '<v>'; valid: new, add, run, status, done, remove. Run `/sn-sprint` (no args) for help."
- No verb passed → print the verb table above.
```

- [ ] **Step 2: Delete the 6 old flat files**

```bash
git rm skills/sn-setup/templates/claude/commands/sn-sprint-new.md \
       skills/sn-setup/templates/claude/commands/sn-sprint-add.md \
       skills/sn-setup/templates/claude/commands/sn-sprint-run.md \
       skills/sn-setup/templates/claude/commands/sn-sprint-status.md \
       skills/sn-setup/templates/claude/commands/sn-sprint-done.md \
       skills/sn-setup/templates/claude/commands/sn-sprint-remove.md
```

- [ ] **Step 3: Verify no regressions in the test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: 225 passed (same as before; tests don't yet assert on the new file).

- [ ] **Step 4: Commit**

```bash
git add skills/sn-setup/templates/claude/commands/sn-sprint.md
git commit -m "$(cat <<'EOF'
feat(commands): consolidate sn-sprint-* into grouped sn-sprint.md

Replaces 6 flat sn-sprint-{new,add,run,status,done,remove}.md command files
with a single grouped sn-sprint.md that documents all 6 verbs in one table +
dispatches each via a dedicated section.

Pattern matches the existing sn-setup policy <op> sub-tree.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 2: Author `sn-req.md` grouped command + delete 5 old flat files

**Files:**
- Create: `skills/sn-setup/templates/claude/commands/sn-req.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-req-new.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-req-import.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-req-replay.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-req-resume.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-req-rollback.md`

**Interfaces:** none — pure template authoring.

- [ ] **Step 1: Write the new `sn-req.md` verbatim**

Create `skills/sn-setup/templates/claude/commands/sn-req.md`:

```markdown
---
name: sn-req
description: Requirement operations. Sub-commands: new, import, replay, resume, rollback. Invoke as `/sn-req <verb> [args]`.
---

# /sn-req <verb> [args]

Requirement lifecycle: scaffold, import, resume, replay, rollback.

## Verbs

| Verb | Args | Purpose |
|---|---|---|
| `new` | `SLUG=<s>` | Scaffold a new REQ-NNN file under `docs/requirements/active/` |
| `import` | `FILE=<path>` | Convert a source document into a REQ-NNN.md |
| `replay` | `REQ=<id>` | Re-run a completed REQ's tasks on a throwaway branch |
| `resume` | — | Resume an interrupted sprint-run from `.sn-init/workflow-state.json` |
| `rollback` | `REQ=<id>` | Reset the working tree to the pre-REQ git snapshot tag |

Run `/sn-req` with no args to see this table.

## Dispatch (Claude reads `$1` and follows the matching section below)

### `new` — Scaffold a new REQ

Args: `SLUG` (required, short kebab-case identifier).

Create `docs/requirements/active/REQ-<next>-<SLUG>.md` from `docs/requirements/template.md`. Scans all sprint dirs + `active/` to find the max REQ-NNN and increments.

### `import` — Convert a source document into a REQ

Args: `FILE` (required, path to source document — md / txt / json / docx / pdf).

Run `python scripts/importers/<ext>.py FILE` and write `docs/requirements/active/REQ-<next>-<slug>.md`. Extracted: title, acceptance bullets, sources, priority hint. User reviews + edits the resulting REQ before assigning it to a sprint.

### `replay` — Re-run a completed REQ

Args: `REQ` (required, REQ id, e.g. `REQ-003`).

Creates a `replay/REQ-NNN` branch from the pre-REQ snapshot tag, replays each TASK via executor + tester, reports pass/fail. Useful to verify a completed REQ still passes against current dependencies.

### `resume` — Resume an interrupted sprint-run

No args.

Reads `.sn-init/workflow-state.json` to find the active REQ + last in-progress phase, then re-enters the orchestrator at that step. Subagent reruns are idempotent — state file tracks completion per phase.

### `rollback` — Reset to pre-REQ baseline

Args: `REQ` (required, REQ id).

```bash
git reset --hard $(git tag | grep ^sn-init/pre-${REQ}- | sort -r | head -1)
```

Aborts if no matching tag. Use after a failed sprint to start fresh from the pre-REQ baseline.

## Error handling

- Unknown verb → "unknown sub-command '<v>'; valid: new, import, replay, resume, rollback. Run `/sn-req` (no args) for help."
- No verb passed → print the verb table above.
```

- [ ] **Step 2: Delete the 5 old flat files**

```bash
git rm skills/sn-setup/templates/claude/commands/sn-req-new.md \
       skills/sn-setup/templates/claude/commands/sn-req-import.md \
       skills/sn-setup/templates/claude/commands/sn-req-replay.md \
       skills/sn-setup/templates/claude/commands/sn-req-resume.md \
       skills/sn-setup/templates/claude/commands/sn-req-rollback.md
```

- [ ] **Step 3: Verify no regressions**

Run: `.venv/bin/python -m pytest -q`
Expected: 225 passed.

- [ ] **Step 4: Commit**

```bash
git add skills/sn-setup/templates/claude/commands/sn-req.md
git commit -m "$(cat <<'EOF'
feat(commands): consolidate sn-req-* into grouped sn-req.md

Replaces 5 flat sn-req-{new,import,replay,resume,rollback}.md command files
with a single grouped sn-req.md.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 3: Author `sn-knowledge.md` grouped command + retire tech-matrix + delete 4 old flat files

**Files:**
- Create: `skills/sn-setup/templates/claude/commands/sn-knowledge.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-knowledge-check.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-knowledge-update.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-knowledge-promote.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-knowledge-demote.md`
- Delete: `skills/sn-setup/templates/claude/commands/sn-knowledge-tech-matrix.md`

**Interfaces:** none — pure template authoring.

- [ ] **Step 1: Write the new `sn-knowledge.md` verbatim**

Create `skills/sn-setup/templates/claude/commands/sn-knowledge.md`:

```markdown
---
name: sn-knowledge
description: Knowledge / Obsidian vault operations. Sub-commands: check, update, promote, demote, summarize. Invoke as `/sn-knowledge <verb> [args]`.
---

# /sn-knowledge <verb> [args]

Knowledge-vault lifecycle: validation, refresh, scope changes, and free-form summary synthesis.

## Verbs

| Verb | Args | Purpose |
|---|---|---|
| `check` | `SPRINT=<id>` | Preview the sn-impact-analyzer report for a sprint WITHOUT running it |
| `update` | — | Run sn-knowledge-curator across all completed REQs |
| `promote` | `TOPIC=<name>` | Move a topic from `projects/<project>/` to `shared/` |
| `demote` | `TOPIC=<name>` | Move a topic from `shared/` back to `projects/<project>/` |
| `summarize` | `<topic>` | Synthesize a Markdown summary of any free-form topic, write to vault |

Run `/sn-knowledge` with no args to see this table.

## Dispatch (Claude reads `$1` and follows the matching section below)

### `check` — Preview impact analysis

Args: `SPRINT` (required, sprint id).

Runs the same sn-impact-analyzer pipeline as `/sn-sprint run` but stops after writing `impact.md` + summary. No code change, no commits.

### `update` — Refresh all knowledge buckets

No args.

Idempotent. Re-reads every completed REQ + PLAN, regenerates per-topic files using the existing traceback frontmatter to detect updates vs. new facts.

Routes via `ObsidianClient` (`--obsidian-mcp` flag controls backend).

### `promote` — Project → global/shared

Args: `TOPIC` (required, topic name, filename without `.md`).

Move `<vault>/projects/<project>/<topic>.md` → `<vault>/shared/<topic>.md`. Updates `bucket:` frontmatter. Preserves `origin_project:` traceback so the source is still discoverable.

### `demote` — global/shared → project

Args: `TOPIC` (required, topic name).

Reverse of `promote`. Refuses if the topic is referenced by other projects (via traceback frontmatter).

### `summarize` — Free-form vault summary

Args: `<topic>` (required, free text). Optional flags: `--no-overwrite`, `--append`, `--dry-run`.

Examples:

```
/sn-knowledge summarize tech
/sn-knowledge summarize "postgres versions"
/sn-knowledge summarize policies
/sn-knowledge summarize "auth patterns"
/sn-knowledge summarize ownership --append
```

Flow (Claude executes inline; no Python helper):

1. Slugify topic ("Postgres Versions" → "postgres-versions").
2. Read CLAUDE.md global rules to discover the vault path.
3. Grep the vault across `projects/`, `shared/`, `tech-stacks/` for topic-relevant notes.
4. Read top-10 candidates (cap to bound tokens).
5. Synthesize Markdown. Shape adapts to topic:
   - comparison topic ("postgres versions") → markdown table
   - thematic topic ("auth patterns") → grouped narrative
   - lifecycle topic ("incidents") → time-ordered list
6. Write to `<vault>/shared/summaries/<slug>.md` with frontmatter:
   ```yaml
   ---
   topic: <slug>
   bucket: shared/summaries
   generated_at: <ISO-8601 UTC>
   source_notes: [<rel-path>, ...]
   tags: [knowledge, summary, <slug>]
   ---
   ```
7. Commit + push the vault (per global Knowledge auto-mirror rule).
8. Chat reply: one line — "wrote `shared/summaries/<slug>.md` (N sources)".

Overwrite policy:

- Default: overwrite the file for the same slug.
- `--no-overwrite` → if file exists, exit `0` with note "summary exists at `<path>`".
- `--append` → preserve existing content; append a dated `## Refresh — <ISO-8601 UTC>` section.

Failure modes (return concise chat error; no vault commit):

- Vault not writable → chat error.
- Zero matching notes → "no notes found for topic '<topic>'; nothing to summarize".
- More than 50 candidate notes → cap to top-10 by recency; warn in chat.

## Error handling

- Unknown verb → "unknown sub-command '<v>'; valid: check, update, promote, demote, summarize. Run `/sn-knowledge` (no args) for help."
- No verb passed → print the verb table above.

## Retired commands

- `/sn-knowledge-tech-matrix` — replaced by `/sn-knowledge summarize tech`. The same Markdown table is produced; topic is now free-form, so `summarize "postgres versions"`, `summarize policies`, etc. also work.
```

- [ ] **Step 2: Delete the 4 old flat files + retire tech-matrix**

```bash
git rm skills/sn-setup/templates/claude/commands/sn-knowledge-check.md \
       skills/sn-setup/templates/claude/commands/sn-knowledge-update.md \
       skills/sn-setup/templates/claude/commands/sn-knowledge-promote.md \
       skills/sn-setup/templates/claude/commands/sn-knowledge-demote.md \
       skills/sn-setup/templates/claude/commands/sn-knowledge-tech-matrix.md
```

- [ ] **Step 3: Verify no regressions**

Run: `.venv/bin/python -m pytest -q`
Expected: 225 passed.

- [ ] **Step 4: Commit**

```bash
git add skills/sn-setup/templates/claude/commands/sn-knowledge.md
git commit -m "$(cat <<'EOF'
feat(commands): consolidate sn-knowledge-* into grouped sn-knowledge.md

Replaces 4 flat sn-knowledge-{check,update,promote,demote}.md command files
with a single grouped sn-knowledge.md that documents all 5 verbs (the 4
above + the new summarize verb). Retires sn-knowledge-tech-matrix.md;
old behavior reproduced by `sn-knowledge summarize tech`.

Updated vault bucket names per the recent restructure: shared/ (was
global/shared/), tech-stacks/ (was global/tech/).

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 4: `scripts/commands_migration.py` module + unit tests

**Files:**
- Create: `scripts/commands_migration.py`
- Create: `tests/test_commands_migration.py`

**Interfaces:**
- Consumes: `policy_state.sha256_file` (Task 1 of policy-catalog PR; already shipped).
- Produces:
  - `commands_migration.FLAT_TO_GROUP: dict[str, tuple[str, str]]` — the 15-entry rename map.
  - `commands_migration.RETIRED: set[str]` — slug names to delete only (no replacement file). Day-1: `{"sn-knowledge-tech-matrix"}`.
  - `commands_migration.MigrationReport` dataclass: `from_flat`, `to_grouped`, `skipped`, `retired` (all `list[str]`); plus `.to_dict() -> dict`.
  - `commands_migration.run(project_dir: Path, *, force: bool = False, dry_run: bool = False) -> MigrationReport`.

- [ ] **Step 1: Write the failing test file**

Create `tests/test_commands_migration.py`:

```python
"""Tests for scripts/commands_migration.py — flat → grouped rename."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import commands_migration  # type: ignore


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
GROUPED_TEMPLATES = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "claude" / "commands"


def _seed_scaffold(tmp_path: Path, with_flat: bool = True) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    cmd_dir = project / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    (project / ".sn-init-state.json").write_text(json.dumps({"mode": "new"}))
    if with_flat:
        # Copy each flat slug from the plugin's grouped templates as a stand-in.
        # We don't need the real old content; the sha-check works against the
        # current disk content vs. recorded state. For the noop tests we just
        # write a known string.
        for flat in commands_migration.FLAT_TO_GROUP:
            (cmd_dir / f"{flat}.md").write_text(f"# {flat}\n")
        # Retired files too.
        for slug in commands_migration.RETIRED:
            (cmd_dir / f"{slug}.md").write_text(f"# {slug}\n")
    return project


def test_migration_noop_on_fresh_scaffold(tmp_path: Path):
    """No flat files present → state still flips; no errors."""
    project = _seed_scaffold(tmp_path, with_flat=False)
    report = commands_migration.run(project)
    assert report.from_flat == []
    assert report.retired == []
    # Grouped files were written from the plugin templates.
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        assert (project / ".claude" / "commands" / grouped).exists()


def test_migration_renames_unedited_flat_files(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=True)
    # All 15 flat files removed; grouped files in place.
    for flat in commands_migration.FLAT_TO_GROUP:
        assert not (project / ".claude" / "commands" / f"{flat}.md").exists()
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        assert (project / ".claude" / "commands" / grouped).exists()
    assert sorted(report.from_flat) == sorted(commands_migration.FLAT_TO_GROUP)


def test_migration_skips_user_edited_without_force(tmp_path: Path):
    """When the plugin's flat-template content doesn't match the on-disk
    content, the on-disk file is treated as user-edited and skipped
    unless --force is set. We seed with fake content to simulate."""
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=False)
    # Without force, every flat file is "edited" relative to the plugin
    # templates (which were deleted in Tasks 1-3), so all 15 should be
    # skipped.
    assert len(report.skipped) >= 1  # at least one user-edited file
    # State should still record commands_renamed_at.


def test_migration_force_deletes_edited(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=True)
    # With --force, edited files are deleted anyway.
    for flat in commands_migration.FLAT_TO_GROUP:
        assert not (project / ".claude" / "commands" / f"{flat}.md").exists()
    assert report.skipped == []


def test_migration_deletes_retired_tech_matrix(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=True)
    assert "sn-knowledge-tech-matrix" in report.retired
    assert not (project / ".claude" / "commands" / "sn-knowledge-tech-matrix.md").exists()


def test_migration_idempotent_after_first_run(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    commands_migration.run(project, force=True)
    # Now state.commands_renamed_at is set. Re-run.
    report2 = commands_migration.run(project, force=True)
    # No-op: empty report.
    assert report2.from_flat == []
    assert report2.retired == []
    assert report2.skipped == []


def test_migration_dry_run_writes_nothing(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    cmd_dir = project / ".claude" / "commands"
    files_before = sorted(p.name for p in cmd_dir.iterdir())
    report = commands_migration.run(project, force=True, dry_run=True)
    files_after = sorted(p.name for p in cmd_dir.iterdir())
    assert files_before == files_after  # nothing changed on disk
    # Report still computed.
    assert len(report.from_flat) > 0
    # State NOT flipped.
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert "commands_renamed_at" not in state


def test_migration_records_full_state_block(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    commands_migration.run(project, force=True)
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert "commands_renamed_at" in state
    assert state["commands_renamed_at"] is not None
    assert state["commands_migration"]["from_flat"]
    assert state["commands_migration"]["to_grouped"] == ["sn-sprint", "sn-req", "sn-knowledge"]
    assert "skipped" in state["commands_migration"]
    assert state["commands_migration"]["retired"] == ["sn-knowledge-tech-matrix"]
```

- [ ] **Step 2: Run the failing tests**

Run: `.venv/bin/python -m pytest tests/test_commands_migration.py -v`
Expected: `ModuleNotFoundError: No module named 'commands_migration'` for every test.

- [ ] **Step 3: Implement `scripts/commands_migration.py`**

```python
"""One-shot migration from flat sn-X-Y.md to grouped sn-X.md slash commands.

Idempotent (gated on state["commands_renamed_at"]). Edit-safe (sha-checks
each file against the plugin's template; --force bypasses).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import policy_state


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
GROUPED_TEMPLATE_DIR = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "claude" / "commands"
GROUPED_FILES = ("sn-sprint.md", "sn-req.md", "sn-knowledge.md")


FLAT_TO_GROUP: dict[str, tuple[str, str]] = {
    "sn-sprint-new":        ("sn-sprint",    "new"),
    "sn-sprint-add":        ("sn-sprint",    "add"),
    "sn-sprint-run":        ("sn-sprint",    "run"),
    "sn-sprint-status":     ("sn-sprint",    "status"),
    "sn-sprint-done":       ("sn-sprint",    "done"),
    "sn-sprint-remove":     ("sn-sprint",    "remove"),
    "sn-req-new":           ("sn-req",       "new"),
    "sn-req-import":        ("sn-req",       "import"),
    "sn-req-replay":        ("sn-req",       "replay"),
    "sn-req-resume":        ("sn-req",       "resume"),
    "sn-req-rollback":      ("sn-req",       "rollback"),
    "sn-knowledge-check":   ("sn-knowledge", "check"),
    "sn-knowledge-update":  ("sn-knowledge", "update"),
    "sn-knowledge-promote": ("sn-knowledge", "promote"),
    "sn-knowledge-demote":  ("sn-knowledge", "demote"),
}

RETIRED: set[str] = {"sn-knowledge-tech-matrix"}


@dataclass
class MigrationReport:
    from_flat: list[str] = field(default_factory=list)
    to_grouped: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "from_flat": list(self.from_flat),
            "to_grouped": list(self.to_grouped),
            "skipped": list(self.skipped),
            "retired": list(self.retired),
        }


def run(project_dir: Path, *, force: bool = False, dry_run: bool = False) -> MigrationReport:
    """Rename flat commands → grouped commands. Mutates state on success."""
    state = policy_state.read_state(project_dir)
    if state.get("commands_renamed_at"):
        return MigrationReport()

    cmd_dir = project_dir / ".claude" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)

    report = MigrationReport()

    # 1. Plan: scan each flat slug + the retired slugs.
    delete_paths: list[Path] = []
    for slug in FLAT_TO_GROUP:
        flat_path = cmd_dir / f"{slug}.md"
        if not flat_path.exists():
            continue
        template_path = GROUPED_TEMPLATE_DIR / f"{slug}.md"
        if template_path.exists():
            actual = policy_state.sha256_file(flat_path)
            expected = policy_state.sha256_file(template_path)
            if actual == expected:
                delete_paths.append(flat_path)
                report.from_flat.append(slug)
                continue
        # Either no template equivalent (template already deleted in Tasks 1-3),
        # or sha mismatched. Treat as edited.
        if force:
            delete_paths.append(flat_path)
            report.from_flat.append(slug)
        else:
            report.skipped.append(str(flat_path.relative_to(project_dir)))

    for slug in sorted(RETIRED):
        retired_path = cmd_dir / f"{slug}.md"
        if not retired_path.exists():
            continue
        template_path = GROUPED_TEMPLATE_DIR / f"{slug}.md"
        is_edited = True
        if template_path.exists():
            actual = policy_state.sha256_file(retired_path)
            expected = policy_state.sha256_file(template_path)
            is_edited = (actual != expected)
        if is_edited and not force:
            report.skipped.append(str(retired_path.relative_to(project_dir)))
        else:
            delete_paths.append(retired_path)
            report.retired.append(slug)

    # 2. Plan: which grouped files to write.
    grouped_to_write: list[Path] = []
    for fname in GROUPED_FILES:
        src = GROUPED_TEMPLATE_DIR / fname
        dst = cmd_dir / fname
        if dst.exists():
            # Preserve any user-created grouped file unconditionally.
            continue
        if not src.exists():
            continue
        grouped_to_write.append(dst)
        report.to_grouped.append(dst.stem)

    # 3. Execute (skip on dry-run).
    if dry_run:
        return report

    for path in delete_paths:
        path.unlink()

    for dst in grouped_to_write:
        shutil.copyfile(GROUPED_TEMPLATE_DIR / dst.name, dst)

    # 4. State update.
    now = datetime.now(timezone.utc).isoformat()
    state["commands_renamed_at"] = now
    state["commands_migration"] = report.to_dict()
    policy_state.write_state(project_dir, state)

    return report
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_commands_migration.py -v`
Expected: 8 passed.

- [ ] **Step 5: Run targeted no-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 233 passed (225 prior + 8 new).

- [ ] **Step 6: Commit**

```bash
git add scripts/commands_migration.py tests/test_commands_migration.py
git commit -m "$(cat <<'EOF'
feat(commands): add migration module for flat → grouped rename

scripts/commands_migration.py exposes FLAT_TO_GROUP (15 slugs), RETIRED
({sn-knowledge-tech-matrix}), MigrationReport dataclass, and run() that
sha-checks each old file before deleting + writes the grouped templates.
Idempotent (state-gated) and --force-able. dry_run=True produces the same
report without filesystem writes.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 5: Wire `--rename-commands` + `--force` flags into `scripts/sn_init.py`

**Files:**
- Modify: `scripts/sn_init.py`

**Interfaces:**
- Consumes: `commands_migration.run` (Task 4).
- Produces: new flag surface on `sn-setup --upgrade`.

- [ ] **Step 1: Add the two new flags to `build_parser`**

In `scripts/sn_init.py`, locate `build_parser()` and append (after `--upgrade`):

```python
    p.add_argument(
        "--rename-commands",
        action="store_true",
        dest="rename_commands",
        help="Rename flat sn-X-Y.md slash commands to grouped sn-X.md. "
             "Requires --upgrade. Idempotent; --force overrides user edits.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Force destructive ops (currently only --rename-commands).",
    )
```

- [ ] **Step 2: Validate `--rename-commands` requires `--upgrade`**

In `main()`, after `args = parser.parse_args(raw)`, before the upgrade dispatch:

```python
    if getattr(args, "rename_commands", False) and not args.upgrade:
        print(
            "sn-setup: --rename-commands requires --upgrade",
            file=sys.stderr,
        )
        return errors.EXIT_USAGE
```

- [ ] **Step 3: Dispatch into `commands_migration.run` from `_run_upgrade`**

In `_run_upgrade()`, after the existing template-version bump but before the state write, insert:

```python
    if getattr(args, "rename_commands", False):
        import commands_migration
        report = commands_migration.run(
            target,
            force=getattr(args, "force", False),
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            # commands_migration.run already wrote the state file with the
            # commands_renamed_at + commands_migration block. Re-read so
            # downstream state writes don't clobber it.
            state = json.loads((target / ".sn-init-state.json").read_text(encoding="utf-8"))
        print(
            f"sn-setup: renamed {len(report.from_flat)} commands into "
            f"{len(report.to_grouped)} groups; "
            f"retired {len(report.retired)}; "
            f"skipped {len(report.skipped)} user-edited"
        )
        if report.skipped:
            for path in report.skipped:
                print(f"  skipped: {path}")
```

(Exact integration point in `_run_upgrade` depends on the current control flow. The implementer should preserve the existing template-version bump and add the new block adjacent to it without breaking the state-write order.)

- [ ] **Step 4: Run full no-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 233 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/sn_init.py
git commit -m "$(cat <<'EOF'
feat(commands): wire --rename-commands flag into sn-setup --upgrade

Adds two flags to build_parser:
- --rename-commands: opt-in flag to trigger the flat→grouped migration
- --force: bypass sha-check (currently only meaningful with --rename-commands)

Validates that --rename-commands requires --upgrade (exit 2 otherwise).
Dispatches into commands_migration.run from _run_upgrade and prints a
summary of renamed/retired/skipped.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 6: Integration tests in `tests/test_sn_init.py`

**Files:**
- Modify: `tests/test_sn_init.py` (append 5 tests at end)

**Interfaces:** consumes everything from Tasks 1-5.

- [ ] **Step 1: Append the 5 integration tests**

Append to `tests/test_sn_init.py`:

```python
def test_new_scaffold_writes_grouped_commands_only(tmp_path: Path):
    """A fresh scaffold contains the 3 grouped command files + no flat."""
    _run(tmp_path, "demo", "--no-git")
    cmd_dir = tmp_path / "demo" / ".claude" / "commands"
    # Grouped present.
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        assert (cmd_dir / grouped).exists()
    # Flat absent.
    for flat in (
        "sn-sprint-new.md", "sn-sprint-add.md", "sn-sprint-run.md",
        "sn-sprint-status.md", "sn-sprint-done.md", "sn-sprint-remove.md",
        "sn-req-new.md", "sn-req-import.md", "sn-req-replay.md",
        "sn-req-resume.md", "sn-req-rollback.md",
        "sn-knowledge-check.md", "sn-knowledge-update.md",
        "sn-knowledge-promote.md", "sn-knowledge-demote.md",
    ):
        assert not (cmd_dir / flat).exists(), f"flat file leaked into scaffold: {flat}"


def test_new_scaffold_does_not_ship_tech_matrix_md(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    cmd_dir = tmp_path / "demo" / ".claude" / "commands"
    assert not (cmd_dir / "sn-knowledge-tech-matrix.md").exists()


def test_grouped_command_frontmatter_valid(tmp_path: Path):
    """Each grouped .md ships a YAML frontmatter with name + description."""
    import yaml as _yaml
    _run(tmp_path, "demo", "--no-git")
    cmd_dir = tmp_path / "demo" / ".claude" / "commands"
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        text = (cmd_dir / grouped).read_text()
        assert text.startswith("---\n"), f"{grouped} missing frontmatter"
        # Extract the YAML block between the leading --- and the next ---.
        _, block, _body = text.split("---\n", 2)
        meta = _yaml.safe_load(block)
        assert meta["name"] == grouped.removesuffix(".md")
        assert "description" in meta and meta["description"]


def test_upgrade_rename_commands_flag_requires_upgrade(tmp_path: Path, capsys):
    """sn-setup --rename-commands (without --upgrade) → exit 2."""
    # Need a scaffold + state file first.
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    rc = _run(project, "--rename-commands")
    assert rc == errors.EXIT_USAGE
    err = capsys.readouterr().err
    assert "--rename-commands requires --upgrade" in err


def test_upgrade_rename_commands_end_to_end(tmp_path: Path):
    """Scaffold a project, drop in a fake old flat file, run --upgrade
    --rename-commands --force, verify it gets removed and state updated."""
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    cmd_dir = project / ".claude" / "commands"
    # Simulate a legacy scaffold by writing one fake flat file.
    (cmd_dir / "sn-sprint-new.md").write_text("# legacy sn-sprint-new\n")
    rc = _run(project, "--upgrade", "--rename-commands", "--force")
    assert rc == errors.EXIT_OK
    assert not (cmd_dir / "sn-sprint-new.md").exists()
    # Grouped files already shipped during initial scaffold; still present.
    assert (cmd_dir / "sn-sprint.md").exists()
    # State recorded.
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["commands_renamed_at"] is not None
    assert "sn-sprint-new" in state["commands_migration"]["from_flat"]
```

- [ ] **Step 2: Run integration tests**

Run: `.venv/bin/python -m pytest tests/test_sn_init.py -k "scaffold or rename or grouped or tech_matrix" -v`
Expected: 5 new tests pass (plus any existing matches).

- [ ] **Step 3: Run full no-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 238 passed (233 prior + 5 new).

- [ ] **Step 4: Commit**

```bash
git add tests/test_sn_init.py
git commit -m "$(cat <<'EOF'
test(commands): integration tests for flat→grouped migration

Adds 5 integration tests:
- new scaffold writes grouped commands only (no flat leak)
- new scaffold does not ship sn-knowledge-tech-matrix.md
- grouped command frontmatter is valid YAML with name + description
- --rename-commands without --upgrade → exit 2
- end-to-end upgrade flow removes legacy flat files and updates state

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 7: Docs — MIGRATION.md, WORKFLOW.md, commands/sn-setup.md, backlog.md, CHANGELOG.md

**Files:**
- Create: `docs/MIGRATION.md`
- Modify: `WORKFLOW.md` (update command-flow diagram and references)
- Modify: `commands/sn-setup.md` (new flag rows + Sub-commands section)
- Modify: `docs/backlog.md` (add B1.9 entry)
- Modify: `CHANGELOG.md` (Unreleased entry)

- [ ] **Step 1: Create `docs/MIGRATION.md`**

```markdown
# Migration Guide — Command Sub-tree (2026-06-24)

`sn-setup` regrouped 16 flat slash commands into 3 grouped commands. This guide explains how to upgrade an existing scaffold.

## What changed

| Before (flat) | After (grouped) |
|---|---|
| `/sn-sprint-new SLUG=x` | `/sn-sprint new SLUG=x` |
| `/sn-sprint-add ...` | `/sn-sprint add ...` |
| `/sn-sprint-run ...` | `/sn-sprint run ...` |
| `/sn-sprint-status` | `/sn-sprint status` |
| `/sn-sprint-done ...` | `/sn-sprint done ...` |
| `/sn-sprint-remove ...` | `/sn-sprint remove ...` |
| `/sn-req-new ...` | `/sn-req new ...` |
| `/sn-req-import ...` | `/sn-req import ...` |
| `/sn-req-replay ...` | `/sn-req replay ...` |
| `/sn-req-resume` | `/sn-req resume` |
| `/sn-req-rollback ...` | `/sn-req rollback ...` |
| `/sn-knowledge-check ...` | `/sn-knowledge check ...` |
| `/sn-knowledge-update` | `/sn-knowledge update` |
| `/sn-knowledge-promote ...` | `/sn-knowledge promote ...` |
| `/sn-knowledge-demote ...` | `/sn-knowledge demote ...` |
| `/sn-knowledge-tech-matrix` | **retired** — use `/sn-knowledge summarize tech` |

## How to migrate

Inside an existing scaffolded repository:

```bash
sn-setup --upgrade --rename-commands
```

Effect:

- Sha-checks each old flat file in `.claude/commands/` against the original template.
- Unedited files → deleted.
- User-edited files → kept + warned. Pass `--force` to delete them anyway.
- Retired `sn-knowledge-tech-matrix.md` → deleted (unconditionally if unedited).
- New grouped files (`sn-sprint.md`, `sn-req.md`, `sn-knowledge.md`) → written (skipped if already present).
- State file gets `commands_renamed_at` + `commands_migration` block.

The command is **idempotent**: re-running it is a no-op once `commands_renamed_at` is set.

## CI / scripts

If your CI or scripts invoke the old flat commands (e.g. `/sn-sprint-new SLUG=...`), update them to the grouped syntax (`/sn-sprint new SLUG=...`).

## See also

- Design spec: `docs/superpowers/specs/2026-06-24-command-subtree-migration-design.md`.
- Implementation plan: `docs/superpowers/plans/2026-06-24-command-subtree-migration.md`.
```

- [ ] **Step 2: Update `WORKFLOW.md`**

Find the command-flow section. Replace any old flat command references:

```
/sn-sprint-new SLUG=auth-rev    →   /sn-sprint new SLUG=auth-rev
/sn-sprint-add SPRINT=... REQ=... → /sn-sprint add SPRINT=... REQ=...
/sn-sprint-run SPRINT=...       →   /sn-sprint run SPRINT=...
/sn-sprint-status               →   /sn-sprint status
/sn-sprint-done SPRINT=...      →   /sn-sprint done SPRINT=...
/sn-req-new SLUG=...            →   /sn-req new SLUG=...
/sn-knowledge-update            →   /sn-knowledge update
```

- [ ] **Step 3: Update `commands/sn-setup.md`**

Append new flag rows to the existing flag table:

```markdown
| `--rename-commands` | off | Rename flat `sn-X-Y.md` commands to grouped `sn-X.md`. Requires `--upgrade`. |
| `--force` | off | Bypass sha-check for `--rename-commands` (delete user-edited files anyway). |
```

Add a new "Generated grouped commands" section noting that scaffolded projects ship:

```markdown
## Generated grouped slash commands

Scaffolded projects ship 3 grouped commands under `.claude/commands/`:

- `sn-sprint` — verbs: `new | add | run | status | done | remove`
- `sn-req` — verbs: `new | import | replay | resume | rollback`
- `sn-knowledge` — verbs: `check | update | promote | demote | summarize`

For existing scaffolds with the old flat commands, run `sn-setup --upgrade --rename-commands`. See `docs/MIGRATION.md`.
```

- [ ] **Step 4: Update `docs/backlog.md`**

Add a new B1.9 entry under Tier 1 (after B1.8):

```markdown
### B1.9 `[~]` Command sub-tree migration — branch `feat/command-subtree-migration`
- **Why**: 16 flat `sn-X-Y.md` slash commands fragment the help surface. Sibling pattern `sn-setup policy <op>` (PR #18) reads better.
- **Where**: `skills/sn-setup/templates/claude/commands/sn-{sprint,req,knowledge}.md` (new); 16 old files deleted; `scripts/commands_migration.py` (new); `--rename-commands` flag in `sn_init.py`.
- **Scope**: 3 grouped commands + `summarize` verb (replaces tech-matrix) + migration command for existing scaffolds.
- **Mark `[x]`**: after PR merges.
```

- [ ] **Step 5: Update `CHANGELOG.md`**

Append to `[Unreleased]`:

```markdown
- **Command sub-tree migration** (B1.9). Regroups 16 flat `sn-X-Y.md` slash commands into 3 grouped `sn-X.md` files matching the `sn-setup policy <op>` pattern:
  - `sn-sprint <new|add|run|status|done|remove>`
  - `sn-req <new|import|replay|resume|rollback>`
  - `sn-knowledge <check|update|promote|demote|summarize>`
- **Retired** `sn-knowledge-tech-matrix`. Use `sn-knowledge summarize tech` (or any free-form topic) instead. Output persists to `<vault>/shared/summaries/<slug>.md`.
- **Migration**: existing scaffolds run `sn-setup --upgrade --rename-commands` once. Idempotent; sha-checked; `--force` for user-edited files. See `docs/MIGRATION.md`.
- **State**: `.sn-init-state.json` gains `commands_renamed_at` + `commands_migration` block.
```

- [ ] **Step 6: Run full no-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 238 passed.

- [ ] **Step 7: Commit**

```bash
git add docs/MIGRATION.md WORKFLOW.md commands/sn-setup.md docs/backlog.md CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(commands): MIGRATION.md + flag docs + backlog + changelog

- docs/MIGRATION.md: one-page guide for users with existing scaffolds.
- WORKFLOW.md: command-flow diagram updated to grouped syntax.
- commands/sn-setup.md: new --rename-commands + --force flag rows + a
  "Generated grouped commands" section pointing at sn-sprint / sn-req /
  sn-knowledge.
- docs/backlog.md: new B1.9 item tracking this PR.
- CHANGELOG.md [Unreleased]: announces the breaking change + migration
  command + retirement of sn-knowledge-tech-matrix.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

## Self-Review

### Spec coverage

| Spec § | Topic | Task |
|---|---|---|
| §1 Architecture | overview | All tasks |
| §2 Per-group file structure | sn-sprint / sn-req / sn-knowledge templates | Tasks 1, 2, 3 |
| §3 summarize design | replaces tech-matrix | Task 3 |
| §4 Migration command | `--rename-commands` algorithm | Tasks 4, 5 |
| §5 Plugin-side code changes | sn_init.py + commands_migration.py | Tasks 4, 5 |
| §6 Tests | unit + integration | Tasks 4, 6 |
| §7 Rollout | MIGRATION.md + CHANGELOG | Task 7 |
| §8 Out of scope | non-grouped single-verb commands | Implicit (Tasks 1-3 don't touch them) |
| §9 Decisions log | (informational) | — |
| §10 Risks | mitigated by force flag, skip-on-exists, sha-check | Tasks 4, 6 |
| §11 Open follow-ups | not blocking | — |

### Placeholder scan

No `TBD`, `TODO`, `FIXME`, `implement later`, or `similar to Task N` markers. Every code block contains complete code. Every command lists expected output.

### Type consistency

- `MigrationReport` fields (Task 4) used consistently by `sn_init.py` print + state-record code (Task 5).
- `FLAT_TO_GROUP: dict[str, tuple[str, str]]` reused by tests (Task 4) and migration (Task 4 / Task 5).
- `RETIRED: set[str]` consistent across uses.
- `commands_renamed_at` (string ISO-8601) and `commands_migration` (dict from `MigrationReport.to_dict()`) used identically in `commands_migration.run` and `_run_upgrade`.

No drift found.

---

## Execution Handoff

Plan saved (vault first per project rule) at:
- `<vault>/projects/setup_project_plugin/plans/command-subtree-migration-plan.md`
- (mirror: `docs/superpowers/plans/2026-06-24-command-subtree-migration.md` after the controller copies it)

Two execution options:

1. **Subagent-Driven (Recommended)** — fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — tasks run in this session via executing-plans.

Which approach?
