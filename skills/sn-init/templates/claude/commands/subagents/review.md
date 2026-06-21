---
name: review
description: Invoke the code-reviewer subagent on the current diff or a specified target.
args:
  - TARGET (optional) — file, glob, or git range; defaults to the current diff
---

Spawns the `code-reviewer` subagent with `Read, Glob, Grep` tools. Returns severity-tagged findings (P0/P1/P2/P3) with file:line, problem, and concrete fix suggestions.
