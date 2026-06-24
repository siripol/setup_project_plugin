# Command Sub-tree Migration — Design Spec

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Author | brainstorming session (Siripol + Claude) |
| Status | Draft — awaiting user review |
| Branch (proposed) | `feat/command-subtree-migration` |
| Related PRs | #17 (profile overlays, merged), #18 (policy catalog, merged) |
| Source design | none — direct user-driven refactor; aligns with the `sn-setup policy <op>` pattern shipped in PR #18 |

---

## 0. Summary

Regroup 16 flat `sn-X-Y` slash commands (under `.claude/commands/`) into 3 grouped `sn-X <verb>` commands, matching the pattern already used by `sn-setup policy <op>` and `sn-setup profile <op>`. Retire `sn-knowledge-tech-matrix`; replace with a more general `sn-knowledge summarize <topic>` that writes its output to the Obsidian vault.

Existing scaffolded projects opt-in to the migration via `sn-setup --upgrade --rename-commands`, which is idempotent, sha-checked for edit safety, and `--force`-able.

This is a **breaking change** for scaffolded projects' slash-command interface (e.g. `/sn-sprint-new SLUG=x` → `/sn-sprint new SLUG=x`). The plugin's frozen 1.x public API (per CHANGELOG) covers `/sn-setup` + flag table + state schema + audit log + report shape — NOT the generated slash commands inside scaffolded projects.

---

## 1. Architecture

```
BEFORE (16 flat files)                  AFTER (3 grouped files)
.claude/commands/                       .claude/commands/
  sn-sprint-new.md                        sn-sprint.md          ← new|add|run|status|done|remove
  sn-sprint-add.md
  sn-sprint-run.md
  sn-sprint-status.md
  sn-sprint-done.md
  sn-sprint-remove.md
  sn-req-new.md                           sn-req.md             ← new|import|replay|resume|rollback
  sn-req-import.md
  sn-req-replay.md
  sn-req-resume.md
  sn-req-rollback.md
  sn-knowledge-check.md                   sn-knowledge.md       ← check|update|promote|demote|summarize
  sn-knowledge-update.md
  sn-knowledge-promote.md
  sn-knowledge-demote.md
  sn-knowledge-tech-matrix.md     [DELETE — replaced by summarize]
```

Each grouped `.md` file documents its sub-commands as a verb table. Claude reads the file when `/sn-X` is invoked and dispatches based on the first positional argument. No Python wrapper is needed for slash-command dispatch — the `.md` file IS the contract that Claude follows.

Unchanged standalone slash commands (still flat because each has only one verb today): `sn-setup`, `sn-verify`, `sn-session-report`, `sn-gh-import`, `claude-local-edit`, `claude-local-show`. Promotion to grouped form is YAGNI until a second verb shows up for any of them.

---

## 2. Per-group command file structure

Each grouped `.md` file follows this shape:

```markdown
---
name: sn-sprint
description: Spec-loop sprint operations. Sub-commands: new, add, run, status, done, remove.
---

# /sn-sprint <verb> [args]

## Verbs

| Verb | Args | Purpose |
|---|---|---|
| `new` | `SLUG=<s>` | Start a new sprint |
| `add` | `REQ=<id>` | Add requirement to current sprint |
| `run` | — | Run sprint loop |
| `status` | — | Print current sprint state |
| `done` | — | Close sprint, emit DONE/BLOCKED promise |
| `remove` | `SPRINT=<id>` | Remove sprint |

## Dispatch (Claude reads `$1` and follows the matching section below)

### `new`
... (full instructions identical to the old sn-sprint-new.md body)

### `add`
... (same content as old sn-sprint-add.md)

### `run`, `status`, `done`, `remove`
... (one section per verb)

## Error handling

- Unknown verb → "unknown sub-command '<v>'; valid: new, add, run, status, done, remove. Run `/sn-sprint` (no args) for help."
- No verb passed → print verb table above.
```

Same shape for `sn-req.md` and `sn-knowledge.md`. Each grouped file is roughly 5–10× longer than one of its old flat siblings (it consolidates them), but the total command-file count drops 16 → 3.

### Template file changes in this repo

```
skills/sn-setup/templates/claude/commands/
  sn-sprint.md              NEW (consolidates 6 sn-sprint-*.md)
  sn-req.md                 NEW (consolidates 5 sn-req-*.md)
  sn-knowledge.md           NEW (consolidates 4 sn-knowledge-* + adds summarize)
  sn-gh-import.md           unchanged
  sn-session-report.md      unchanged
  sn-verify.md              unchanged
  README.md                 UPDATED (new grouping)
  claude-local-edit.md      unchanged
  claude-local-show.md      unchanged
  subagents/<...>           unchanged

DELETED:
  sn-sprint-{new,add,run,status,done,remove}.md         (16 files total)
  sn-req-{new,import,replay,resume,rollback}.md
  sn-knowledge-{check,update,promote,demote,tech-matrix}.md
```

---

## 3. `sn-knowledge summarize <topic>` (replaces tech-matrix)

### Invocation

```bash
/sn-knowledge summarize <topic>
/sn-knowledge summarize <topic> --no-overwrite     # refuse if file exists
/sn-knowledge summarize <topic> --append           # add a dated section
/sn-knowledge summarize <topic> --dry-run          # plan + candidates, no write
```

`<topic>` is free text. Examples: `tech`, `"postgres versions"`, `policies`, `"auth patterns"`, `ownership`, `"incidents 2026"`.

### Execution model — pure LLM-driven

The `sn-knowledge.md` file instructs Claude to follow this sequence under the `summarize` verb:

```
1. Slugify topic:                   "Postgres Versions" → "postgres-versions"
2. Walk vault: read CLAUDE.md global rules to discover vault path
   (default /Users/siripol/Claude/obsidian_sharedknowledge/AllSharedKnowledge/knowledge/).
3. Find topic-relevant notes via Grep across projects/, global/shared/, global/tech/.
4. Read top-N candidates (cap to ~10 to bound tokens).
5. Synthesize Markdown. Pick shape per topic:
   - comparison topic ("postgres versions") → markdown table
   - thematic topic ("auth patterns")        → grouped narrative
   - lifecycle topic ("incidents")           → time-ordered list
6. Write to <vault>/global/summaries/<slug>.md with frontmatter:
   ---
   topic: <slug>
   bucket: global/summaries
   generated_at: <ISO-8601 UTC>
   source_notes: [<rel-path>, ...]
   tags: [knowledge, summary, <slug>]
   ---
7. Commit + push vault per global Knowledge auto-mirror rule.
8. Chat reply: one line — "wrote global/summaries/<slug>.md (N sources)".
```

No Python helper. Maximum flexibility on topic matching; vault writes use Claude's existing Write tool.

### File output shape

```markdown
---
topic: postgres-versions
bucket: global/summaries
generated_at: 2026-06-24T15:00:00Z
source_notes:
  - projects/billing/tech/postgres.md
  - projects/orders/tech/postgres.md
  - projects/identity/tech/postgres.md
tags: [knowledge, summary, postgres-versions]
---

# Summary — Postgres Versions Across Projects

| Project | Version | Upgrade Plan |
|---|---|---|
| billing | 14 | Q3 → 16 |
| orders | 16 | current |
| identity | 13 | overdue (EOL Nov 2025) |

## Notes

(synthesized prose where the table is insufficient)

## Source notes

- [[../../projects/billing/tech/postgres]]
- [[../../projects/orders/tech/postgres]]
```

### Overwrite policy

- Default: overwrite. Same topic → same slug → same file → fresh content.
- `--no-overwrite` → if file exists, exit `0` with "summary exists at `<path>`; omit `--no-overwrite` to refresh".
- `--append` → preserve existing content; append a new section `## Refresh — <ISO-8601 UTC>` with the new synthesis.

### Failure modes (Claude judgment)

- Vault not writable → chat error; no commit attempt.
- Zero matching notes → chat error: "no notes found for topic '<topic>'; nothing to summarize".
- More than 50 candidate notes → cap to top-10 by recency; warn in chat: "found N notes; summarizing top 10 by recency".

### Retired

`sn-knowledge-tech-matrix.md` deleted from templates. Old behavior reproduced by `sn-knowledge summarize tech` — Claude finds the tech notes and emits the same table-shaped summary.

---

## 4. Migration command — `sn-setup --upgrade --rename-commands`

### Invocation

```bash
cd existing-scaffolded-repo
sn-setup --upgrade --rename-commands               # idempotent; sha-checks before delete
sn-setup --upgrade --rename-commands --force       # bypass sha-check; delete user-edited too
sn-setup --upgrade --rename-commands --dry-run     # preview; no fs writes
```

### Algorithm

```
1. Load .sn-init-state.json.
   If state["commands_renamed_at"] is set → no-op message + exit 0.

2. Scan .claude/commands/ for files matching the migration map:

   FLAT_TO_GROUP = {
     "sn-sprint-new":         ("sn-sprint",     "new"),
     "sn-sprint-add":         ("sn-sprint",     "add"),
     "sn-sprint-run":         ("sn-sprint",     "run"),
     "sn-sprint-status":      ("sn-sprint",     "status"),
     "sn-sprint-done":        ("sn-sprint",     "done"),
     "sn-sprint-remove":      ("sn-sprint",     "remove"),
     "sn-req-new":            ("sn-req",        "new"),
     "sn-req-import":         ("sn-req",        "import"),
     "sn-req-replay":         ("sn-req",        "replay"),
     "sn-req-resume":         ("sn-req",        "resume"),
     "sn-req-rollback":       ("sn-req",        "rollback"),
     "sn-knowledge-check":    ("sn-knowledge",  "check"),
     "sn-knowledge-update":   ("sn-knowledge",  "update"),
     "sn-knowledge-promote":  ("sn-knowledge",  "promote"),
     "sn-knowledge-demote":   ("sn-knowledge",  "demote"),
   }
   RETIRED = {"sn-knowledge-tech-matrix"}   # delete only; replaced by `summarize`

3. For each present old file:
   a. Compute current_sha.
   b. Compare to template_sha (the original template content at the version the
      scaffold was generated against; computed on the fly against the plugin's
      templates if no .sn-init/template-shas.json is present).
   c. unchanged → mark for delete.
      edited AND --force → mark for delete.
      edited AND no --force → record in skipped[]; leave the file alone.

4. Write the new grouped files from the plugin's
   skills/sn-setup/templates/claude/commands/sn-{sprint,req,knowledge}.md.
   Skip if a grouped file already exists (do not overwrite).

5. Delete every file marked-for-delete from step 3.
   Delete RETIRED files unconditionally if unedited; warn-and-skip if edited
   (same --force semantics).

6. Update .sn-init-state.json:
     state["commands_renamed_at"] = <ISO-8601 UTC>
     state["commands_migration"] = {
       "from_flat":   [...],          # removed slugs
       "to_grouped":  ["sn-sprint", "sn-req", "sn-knowledge"],
       "skipped":     [...],          # user-edited paths
       "retired":     ["sn-knowledge-tech-matrix"],
     }

7. Atomic write state file.

8. Print summary:
   "renamed 15 commands into 3 groups; retired 1 (sn-knowledge-tech-matrix);
    skipped 2 user-edited (use --force to override): <paths>"
```

### State shape addition

```diff
 {
   "sn_init_version": "0.1.0",
   "template_version": "...",
+  "commands_renamed_at": null,
+  "commands_migration": null,
   "applied_policies": [...],
   "policy_history": [...]
 }
```

After first successful `--rename-commands` run:

```json
{
  "commands_renamed_at": "2026-06-24T16:00:00.000Z",
  "commands_migration": {
    "from_flat": ["sn-sprint-new", "sn-sprint-add", "..."],
    "to_grouped": ["sn-sprint", "sn-req", "sn-knowledge"],
    "skipped": [],
    "retired": ["sn-knowledge-tech-matrix"]
  }
}
```

### Exit codes

| Code | Reason |
|---|---|
| 0 | Success or no-op (already renamed) |
| 2 | Usage error: `--rename-commands` without `--upgrade`, or unknown flag combo |
| 14 | User-edited file blocks delete; pass `--force` (reuses existing `EXIT_USER_EDITED_BLOCKS_OP` from policy catalog) |

### Idempotency

- Re-run after success → state-gated no-op.
- Run on a fresh scaffold (post-migration) → no old files found → state field set → no-op.
- Run on a partially-edited scaffold → user-edited files survive; state still flips so next clean run is a no-op too.

### Telemetry

Captured in `commands_migration` state block; readable via the existing `sn-setup --upgrade` summary print.

---

## 5. Plugin-side code changes

### `scripts/sn_init.py`

1. Add argparse flags:

```python
p.add_argument("--rename-commands", action="store_true", dest="rename_commands",
               help="Rename flat sn-X-Y.md slash commands to grouped sn-X.md. "
                    "Requires --upgrade. Idempotent; --force overrides user edits.")
p.add_argument("--force", action="store_true",
               help="Force destructive ops (currently only --rename-commands).")
```

2. Validate: `--rename-commands` without `--upgrade` → usage error exit 2.
3. After the existing template-version bump in `_run_upgrade`, dispatch:

```python
if args.rename_commands:
    from commands_migration import run as run_migration
    report = run_migration(target, force=args.force, dry_run=args.dry_run)
    state["commands_renamed_at"] = datetime.now(timezone.utc).isoformat()
    state["commands_migration"] = report.to_dict()
```

### `scripts/commands_migration.py` (NEW module)

```python
"""One-shot migration from flat sn-X-Y.md to grouped sn-X.md slash commands.

Idempotent (gated on state["commands_renamed_at"]). Edit-safe (sha-checks
each file; --force bypasses).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import policy_state  # for sha256_file


FLAT_TO_GROUP: dict[str, tuple[str, str]] = {
    "sn-sprint-new":         ("sn-sprint",     "new"),
    "sn-sprint-add":         ("sn-sprint",     "add"),
    "sn-sprint-run":         ("sn-sprint",     "run"),
    "sn-sprint-status":      ("sn-sprint",     "status"),
    "sn-sprint-done":        ("sn-sprint",     "done"),
    "sn-sprint-remove":      ("sn-sprint",     "remove"),
    "sn-req-new":            ("sn-req",        "new"),
    "sn-req-import":         ("sn-req",        "import"),
    "sn-req-replay":         ("sn-req",        "replay"),
    "sn-req-resume":         ("sn-req",        "resume"),
    "sn-req-rollback":       ("sn-req",        "rollback"),
    "sn-knowledge-check":    ("sn-knowledge",  "check"),
    "sn-knowledge-update":   ("sn-knowledge",  "update"),
    "sn-knowledge-promote":  ("sn-knowledge",  "promote"),
    "sn-knowledge-demote":   ("sn-knowledge",  "demote"),
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
            "from_flat": self.from_flat,
            "to_grouped": self.to_grouped,
            "skipped": self.skipped,
            "retired": self.retired,
        }


def run(project_dir: Path, *, force: bool = False, dry_run: bool = False) -> MigrationReport:
    ...
```

### `scripts/_render_claude` — no logic change

The function walks `templates/claude/commands/`. The template tree contains the NEW grouped files only. Old flat templates removed in the same PR. Fresh scaffolds naturally get the new shape without conditionals.

### Documentation updates

- `commands/sn-setup.md` — add `--rename-commands` + `--force` flag rows; new "Sub-commands" / "Generated grouped commands" section.
- `WORKFLOW.md` — update command-flow diagram (e.g. `/sn-sprint-new` → `/sn-sprint new`).
- `docs/principles/*` — anywhere old slug names appear.
- `docs/backlog.md` — mark this PR `[~]` then `[x]`.
- `CHANGELOG.md` — `[Unreleased]` entry calling out the breaking change.
- `docs/MIGRATION.md` (NEW) — one-paragraph guide for existing scaffolds.

---

## 6. Tests

### Unit (`tests/test_commands_migration.py`) — 8 tests

| Test | Verifies |
|---|---|
| `test_migration_noop_on_fresh_scaffold` | No flat files present → state still flips; no errors |
| `test_migration_renames_unedited_flat_files` | sha-match files → deleted; grouped files written |
| `test_migration_skips_user_edited_without_force` | Edited file remains; recorded in `skipped[]` |
| `test_migration_force_deletes_edited` | `--force=True` overrides; file deleted |
| `test_migration_deletes_retired_tech_matrix` | `sn-knowledge-tech-matrix.md` removed (unedited) |
| `test_migration_idempotent_after_first_run` | `commands_renamed_at` set → re-run is no-op |
| `test_migration_dry_run_writes_nothing` | `dry_run=True` → no fs writes; report still computed |
| `test_migration_records_full_state_block` | `state["commands_migration"]` contains `from_flat`, `to_grouped`, `skipped`, `retired` |

### Integration (`tests/test_sn_init.py`) — 5 additions

| Test | Verifies |
|---|---|
| `test_upgrade_rename_commands_flag_requires_upgrade` | `sn-setup --rename-commands` (no `--upgrade`) → exit 2 |
| `test_upgrade_rename_commands_end_to_end` | Scaffold then upgrade with rename → grouped files present, flat absent, state has `commands_renamed_at` |
| `test_new_scaffold_writes_grouped_commands_only` | Fresh scaffold contains `sn-sprint.md` + `sn-req.md` + `sn-knowledge.md`; no `sn-sprint-new.md` etc. |
| `test_new_scaffold_does_not_ship_tech_matrix_md` | `sn-knowledge-tech-matrix.md` absent from new scaffolds |
| `test_grouped_command_frontmatter_valid` | Each grouped `.md` parses as Markdown + has `name`, `description` frontmatter |

### No-regression

```
.venv/bin/python -m pytest -q
```

Target: **225 prior + ~13 new = ~238 passed**.

### Edge cases

- Scaffold without `.sn-init/template-shas.json` — sha computed against plugin templates at run time.
- Partially-edited scaffold — clean files deleted, edited files survive with warning.
- Pre-existing `.claude/commands/sn-sprint.md` (user hand-created) — preserved; warn-and-skip on write.

---

## 7. Rollout

1. Land PR1 (this spec). Branch `feat/command-subtree-migration`.
2. CHANGELOG `[Unreleased]` announces the breaking change + migration command.
3. Release notes in PR body point to `docs/MIGRATION.md`.
4. **No major plugin version bump required** — slash commands inside scaffolded projects are not part of the plugin's "Public API frozen for 1.x" surface (which covers `/sn-setup` + flag table + state file schema + audit log + report shape per CHANGELOG 1.0.0). Slash commands generated inside scaffolds are scaffold-internal artifacts.
5. Existing scaffold users: one-shot `sn-setup --upgrade --rename-commands`. Idempotent, edit-safe.
6. CI / GitHub Actions in scaffolded projects that invoke `/sn-sprint-new` etc. need their scripts updated. The CHANGELOG + MIGRATION doc call this out explicitly so users can grep-and-replace.
7. Orchestrator promise strings (`DONE: <SPRINT-id> triple-signal pass` / `BLOCKED: <SPRINT-id> <reason>`) do not reference command names — unchanged.

---

## 8. Out of scope (this PR)

- Promoting `sn-setup`, `sn-verify`, `sn-session-report`, `sn-gh-import` into grouped form — each has a single verb today; YAGNI.
- Renaming flag style (e.g. `--no-X` vs `--X=off`) — separate UX-polish refactor.
- Adding shell completion or `did-you-mean` suggestions for sub-commands — separate UX-polish refactor.
- Multi-level sub-commands (e.g. `sn-knowledge tech matrix`) — flat `verb arg` is enough; nested verbs are speculative.
- Aliases (e.g. `sn-sprint n` shorthand for `new`) — speculative; ship the canonical form first.

---

## 9. Decisions log

| Q | Topic | Locked |
|---|---|---|
| Q1 | Backward compatibility for in-wild scaffolds | **A** — hard break + migration command |
| Q2 | Slash command dispatch mechanism | Documentation-only (`.md` is the contract) |
| Q3 | `tech-matrix` naming | Retired; replaced by free-form `summarize <topic>` |
| Q4 | Group scope | All 3 (sprint + req + knowledge) in one PR |
| Q5 | Migration command shape | `sn-setup --upgrade --rename-commands` |
| Q6 | `summarize` execution model | Pure LLM-driven; persists to vault |

---

## 10. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| User-edited slash command files (custom verbs inlined) | Low–Medium | `--force` flag; `skipped[]` state record; clear warnings |
| Pre-existing `.claude/commands/sn-sprint.md` collides with the new grouped file | Low | Skip-if-exists; warn |
| Orchestrator references old command names internally | Low — verified | Promise strings don't reference command names; subagent definitions either |
| `summarize` writes to the wrong vault path | Low | Pure LLM execution reads CLAUDE.md global rules for vault location; falls back to env vars |
| Vault commit/push failures (network, auth) | Low | Same as today's auto-mirror behavior; chat error surfaced |
| Migration runs on a non-scaffold dir | Low | Already guarded by `_run_upgrade` requiring `.sn-init-state.json` |

---

## 11. Open follow-ups (not blocking this PR)

- Multi-level grouping (e.g. `sn-knowledge summarize tech detailed`) — only if a clear use case emerges.
- Shell completion for sub-commands — separate UX item.
- Per-command help (`/sn-sprint help new`) — useful but YAGNI until users ask.
- Promotion of standalone single-verb commands to grouped form when they grow a second verb.
- Per-verb deprecation warnings inside the grouped files (instead of file-level rename) — only if hard break causes user pain.
