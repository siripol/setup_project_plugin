---
name: sn-session-report
description: Render a Markdown session-usage report (tokens, cache, subagents, skills, cache breaks, expensive prompts) for the current project into the Obsidian vault. Wraps Anthropic's upstream session-report analyzer.
---

# /sn-session-report

Generate a Markdown session-usage report for the current project, save it under `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md`, and (by default) commit + push the vault. Wraps Anthropic's upstream `session-report` plugin's analyzer.

## Invocation

```
/sn-session-report [since] [flags]
```

Defaults: window `7d`, vault auto-resolved, auto-commit on.

## Examples

```bash
# Default: last 7 days, write to vault, commit + push
/sn-session-report

# Last 24 hours
/sn-session-report 24h

# All-time
/sn-session-report all

# Dry-run — print would-be report to stdout, no write
/sn-session-report 7d --dry-run

# Write to vault but skip git push (still commits)
/sn-session-report 7d --no-push

# Override analyzer path (private fork)
/sn-session-report --analyzer=/path/to/analyze-sessions.mjs

# Override vault path
/sn-session-report --vault=$HOME/notes
```

## Flags

| Flag | Default | Description |
|---|---|---|
| `[since]` (positional) | `7d` | Window: `24h`, `7d`, `30d`, `all`, or ISO timestamp. |
| `--analyzer=<path>` | auto | Path to upstream `analyze-sessions.mjs` (overrides detection). |
| `--vault=<path>` | auto | Override vault root. Resolution chain otherwise: `$OBSIDIAN_VAULT` → `<repo>/.sn-init/knowledge` → `<repo>/session-reports/`. |
| `--project=<encoded-key>` | auto | Override the project key used to filter the JSON (the analyzer's `/`+`_` → `-` form). |
| `--dry-run` | off | Print the report to stdout, no file or git writes. |
| `--no-push` | off | Write the report + commit, but skip `git push`. |
| `--verbose` | off | Per-step trace to stderr. |

## Behavior contract

Body of this command dispatches to `scripts/session_report.py`. The script:

1. **Locates the upstream analyzer** (resolution order in `skills/session-report/SKILL.md`). If none found, prints install hint + exits `9`.
2. **Runs the analyzer** as `node <analyzer> --json --since <window>` and parses stdout as JSON.
3. **Resolves the project key** from cwd (encodes `/` and `_` as `-`). Falls back to longest-suffix match.
4. **Renders Markdown** via the pure function `scripts/session_report_render.py::render_markdown`.
5. **Atomic-writes** the report to `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md`.
6. **Updates** the local `README.md` index in the same dir.
7. **Commits + pushes** the vault (skipped when `--no-push` or vault isn't a git repo).
8. **Prints** the absolute report path to stdout (does NOT open the file).

## Dependencies

- `node` (≥ v18) on `PATH`.
- Anthropic's official `session-report` plugin installed:
  ```text
  /plugin marketplace add anthropics/claude-plugins-official
  /plugin install session-report@claude-plugins-official
  ```

## Exit codes

`0` ok, `2` usage / bad flag, `5` vault unwritable, `9` upstream analyzer missing (install hint printed), `99` internal error.

## See also

- `skills/session-report/SKILL.md` — when the skill triggers and the 8-step flow it follows.
- `scripts/session_report.py` — wrapper implementation.
- `scripts/session_report_render.py` — pure renderer (fixture-tested).
- Upstream skill — [anthropics/claude-plugins-official/plugins/session-report](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/session-report).
