---
name: sn-sprint-done
description: Archive a completed sprint. Moves docs/sprints/active/SPRINT-NNN-*/ to docs/sprints/completed/. Triggers sn-knowledge-update.
args:
  - SPRINT (required) — sprint id
---

Refuses if any REQ in the sprint hasn't reached `eval pass` state. Otherwise `mv` whole sprint folder + run `sn-knowledge-curator` to update Obsidian buckets.
