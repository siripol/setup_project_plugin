---
name: session-report
description: Render Claude Code session usage (tokens, cache, subagents, skills, cache breaks, expensive prompts) for the current project as a Markdown report into the Obsidian vault. Wraps Anthropic's upstream session-report analyzer.
---

# session-report (Markdown / Obsidian variant)

Local port of Anthropic's [`session-report`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/session-report) skill, adapted for `setup_project_plugin`'s Obsidian vault. Renders to Markdown (not HTML) and filters to the current project so reports live alongside other knowledge files at `projects/<project>/session-reports/` — wiki-linked, diff-able week-over-week, auto-committed.

## When to use

- User invokes `/sn-session-report`.
- User asks: "how many tokens did I burn this week?", "what's eating cache?", "session report", "token usage report".
- Periodic review (weekly retro), token-budget audit, cache-break debugging, subagent calibration.

## What it produces

A single Markdown file at `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md` with:

- Standard knowledge-file frontmatter (`topic`, `bucket`, `origin_project`, `first_seen`, `last_updated`, `tags`, `window`).
- Headline table (total tokens, cache-hit %, sessions, API calls, wall-clock + active hours, subagent calls).
- Anomalies (up to 5 Obsidian `> [!warning|info|success]` callouts) — cache-hit < 85%, prompt > 2% of total, subagent > 1M tokens / call, cache-break clustering.
- Token breakdown table (uncached / cache-create / cache-read / output).
- **Top prompts (by tunability)** — top 10 for this project, sorted by a 0-100 composite `tunability_score`, NOT raw tokens. Each row carries a `reason` code (`repeat`, `subagent-heavy`, `loop-thrash`, `cache-miss`, `cold-start`, `low-output`, `expensive`), the cache-hit % for that prompt, cache-break count, repeat count, plus the usual API/subagent counts. Tells you which prompt is *worth* tuning, not just which was expensive.
- **Repeated prompts** — fuzzy-grouped (normalized: lowercased, whitespace-collapsed, first 80 chars, trailing-punctuation-stripped) and counted; surfaces prompts typed ≥ 3 times with total token spend. Highest-ROI tuning targets — type once, save N× tokens by promoting to a `/sn-<slug>` skill or CLAUDE.md macro.
- Subagent activity (cross-project — upstream analyzer doesn't split by project).
- Skill invocations (cross-project, with caveat).
- Cache-break events filtered to this project, with the originating prompt.
- **Optimizations (per-prompt action list)** — top-5 highest-tunability rows, each one a `> [!tip]` callout pairing the `reason` code with a concrete recipe (e.g. `repeat` → promote to skill; `subagent-heavy` → scope fewer parallel agents; `loop-thrash` → lower `max_turns`; `cache-miss` → pin CLAUDE.md before commits).
- See-also cross-links to `[[implementation-log]]`, `[[project-requirements]]`, and the upstream skill card.

The vault's `session-reports/README.md` index is appended on each run; an Obsidian-linked entry shows up automatically.

## Dependencies

- `node` (≥ v18) on `PATH`.
- Anthropic's official `session-report` plugin installed (the wrapper depends on its `analyze-sessions.mjs`):
  ```text
  /plugin marketplace add anthropics/claude-plugins-official
  /plugin install session-report@claude-plugins-official
  ```
- Override via `--analyzer=<path>` or `$SN_SESSION_REPORT_ANALYZER=<path>` if you keep a private fork.

If the analyzer can't be located, the wrapper prints the install hint and exits with code `9` (`EXIT_MISSING_DEP`).

## Steps Claude follows when the skill triggers

1. **Locate the analyzer.** First hit wins from: `--analyzer` flag → `$SN_SESSION_REPORT_ANALYZER` env → glob `~/.claude/plugins/marketplaces/*/plugins/session-report/skills/session-report/analyze-sessions.mjs` → recursive search under `~/.claude/plugins/`.
2. **Run the analyzer.** `node <analyzer> --json --since <window>` (window from positional arg; default `7d`, also accepts `24h`, `30d`, ISO timestamp, `all`).
3. **Filter to the current project.** Encode `cwd` to the analyzer's project key (`/` and `_` → `-`); fall back to longest-suffix match if exact key isn't present.
4. **Render Markdown.** Pure function in `scripts/session_report_render.py` builds the body from the JSON.
5. **Resolve the vault path.** First hit: `--vault` flag → `$OBSIDIAN_VAULT` → `<repo>/.sn-init/knowledge` symlink target's parent → `<repo>/session-reports/` fallback (no commit in fallback mode).
6. **Write the file.** Atomic write to `<vault>/projects/<project>/session-reports/YYYY-MM-DD_HHMM.md`. Append a one-line entry to the local `README.md` index.
7. **Auto-commit + push the vault.** `knowledge: session report <project> YYYY-MM-DD_HHMM` prefix per CLAUDE.md auto-mirror rule; skipped when `--no-push` is set or when the vault isn't a git repo.
8. **Report the saved path.** Print absolute path on stdout; do NOT open the file.

## Flags

| Flag | Default | Notes |
|---|---|---|
| `[since]` (positional) | `7d` | Window: `24h`, `7d`, `30d`, `all`, or ISO timestamp. |
| `--analyzer=<path>` | (auto) | Override analyzer path. |
| `--vault=<path>` | (auto) | Override vault root. |
| `--project=<key>` | (auto from cwd) | Override the project key used to filter the JSON. |
| `--dry-run` | off | Print the would-be report to stdout; no file or git writes. |
| `--no-push` | off | Write the file but skip git commit + push. |
| `--verbose` | off | Per-step trace to stderr. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Report written (or dry-run completed). |
| `2` | Bad flag / usage error. |
| `5` | Vault unwritable (when `--vault` points at a non-existent path). |
| `9` | Upstream analyzer not found. Install hint printed to stderr. |
| `99` | Internal error. |

## Limitations (known)

- **Per-project skill rollup not available** — upstream analyzer doesn't bucket skill invocations by project. The skill table reports global counts with an `> [!info]` caveat.
- **Subagent rollup is global** for the same reason; same caveat in the table.
- **Node runtime required** — the analyzer is .mjs; no pure-Python alternative is shipped (Option C from the design discussion).

## See also

- [[../../global/shared/session-report-skill]] — upstream Anthropic skill reference.
- [[../../global/tech/setup_project_plugin/session-report-port]] — port design + decisions log.
- `commands/sn-session-report.md` — the slash command + flag table.
- `scripts/session_report.py` — wrapper (analyzer detection, vault + git glue).
- `scripts/session_report_render.py` — pure renderer (testable with fixtures).
