---
name: sn-knowledge-check
description: Preview the sn-impact-analyzer report for a sprint WITHOUT running it. Use before sn-sprint-run to spot major impacts early.
args:
  - SPRINT (required) — sprint id
---

Runs the same sn-impact-analyzer pipeline as `/sn-sprint-run` but stops after writing `impact.md` + summary. No code change, no commits.
