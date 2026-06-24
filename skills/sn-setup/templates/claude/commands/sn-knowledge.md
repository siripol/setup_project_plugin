---
name: sn-knowledge
description: "Knowledge / Obsidian vault operations. Sub-commands: check, update, promote, demote, summarize. Invoke as `/sn-knowledge <verb> [args]`."
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
