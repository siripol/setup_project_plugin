---
name: audit
description: Invoke the security-auditor subagent.
args:
  - TARGET (optional) — file or glob; defaults to the full src tree
---

Spawns `security-auditor`. Hunts secrets, injection gaps, unsafe defaults, known-bad deps. Read-only findings only.

Requires `--subagents=all` or `security-auditor` in the `--subagents` list.
