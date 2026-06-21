---
name: doc
description: Invoke the doc-writer subagent to update README + CHANGELOG for a git range or PLAN id.
args:
  - SCOPE (required) — git range (HEAD~3..HEAD) or PLAN id
---

Spawns `doc-writer`. Updates `README.md`, `CHANGELOG.md`, docstrings. Logic source untouched.

Requires `--subagents=all` or `doc-writer` in the `--subagents` list.
