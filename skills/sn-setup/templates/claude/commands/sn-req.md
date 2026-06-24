---
name: sn-req
description: "Requirement operations. Sub-commands: new, import, replay, resume, rollback. Invoke as `/sn-req <verb> [args]`."
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
