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
4. **Augments each top prompt** with `tunability_score` (0-100), `reason` code (`repeat` / `subagent-heavy` / `loop-thrash` / `cache-miss` / `cold-start` / `low-output` / `expensive`), `cache_hit_pct`, `cache_break_count`, `repeat_count`, and a `suggested_action` recipe.
5. **Renders Markdown** via the pure function `scripts/session_report_render.py::render_markdown` — top prompts sorted by tunability score, dedup'd by normalized text, plus a Repeated-prompts section grouping fuzzy matches with count ≥ 3.
6. **Atomic-writes** the report to `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md` (or flat `<cwd>/session-reports/<ts>.md` when the resolved path is the last-resort fallback — see `resolve_vault_path()`).
7. **Updates** the local `README.md` index in the same dir.
8. **Commits + pushes** the vault (skipped when `--no-push` or no enclosing `.git/` ancestor; `find_git_root()` walks up from the resolved vault path).
9. **Prints** the absolute report path to stdout (does NOT open the file).

## Reading the output

Top-prompts table is sorted by **`tunability_score`** (not raw tokens), so the first row is always the highest-ROI tuning target. Each row carries a `reason` code that maps to a concrete fix:

| Reason | What it means | What to do |
|---|---|---|
| `repeat` | Same text typed ≥ 3 times this window | Promote to a `/sn-<slug>` skill or CLAUDE.md macro |
| `subagent-heavy` | One prompt fanned out ≥ 3 subagents | Scope to fewer parallel agents; smaller model per call |
| `loop-thrash` | API calls ≥ 2× project median | Tighten plan, lower `max_turns`, reduce tool-use chains |
| `cache-miss` | Per-prompt cache-hit < 60% | System-prompt churn — pin CLAUDE.md, reduce hook noise |
| `cold-start` | Linked to ≥ 1 cache-break event | Avoid `/clear` mid-task; resume sessions |
| `low-output` | output/input ratio < 0.1% | Loaded big context for tiny output — use targeted Read |
| `expensive` | Costly with no clear waste signal | Right-size the question; split into smaller tasks |

The **Repeated prompts (skill candidates)** section is the highest-leverage data point: a prompt typed 4× isn't 4× more useful, it's 4× wasted cache. Bake into a skill, save the tokens forever.

The **Optimizations** section is a top-5 punch list — pick from the top.

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
