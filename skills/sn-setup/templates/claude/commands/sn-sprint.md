---
name: sn-sprint
description: "Spec-loop sprint operations. Sub-commands: new, add, run, status, done, remove. Invoke as `/sn-sprint <verb> [args]`."
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
