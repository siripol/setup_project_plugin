---
name: sn-sprint-new
description: Create a new SPRINT-NNN folder under docs/sprints/active/ with all subfolders (requirements, exec-plans, tasks, proof) + sprint.md manifest.
args:
  - SLUG (required) — short kebab-case identifier
---

Creates `docs/sprints/active/SPRINT-<next>-<SLUG>/` from `docs/sprints/template.md`. Status starts at `planning`. Counter auto-incremented from existing sprint folders.
