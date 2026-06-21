---
name: plan
description: Invoke the planner subagent to draft an execution plan for a REQ.
args:
  - REQ (required) — REQ id
---

Spawns `planner` (no tools, pure reasoning). Output saved to `docs/sprints/active/SPRINT-*/exec-plans/PLAN-*.md`.

Requires `--subagents=all` or `planner` in the `--subagents` list.
