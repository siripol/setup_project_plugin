---
name: knowledge-check
description: Preview the impact-analyzer report for a sprint WITHOUT running it. Use before sprint-run to spot major impacts early.
args:
  - SPRINT (required) — sprint id
---

Runs the same impact-analyzer pipeline as `/sprint-run` but stops after writing `impact.md` + summary. No code change, no commits.
