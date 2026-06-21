---
name: sprint-remove
description: Move a REQ back out of a sprint to docs/requirements/active/.
args:
  - SPRINT (required) — sprint id
  - REQ (required) — REQ id
---

Reverse of `/sprint-add`. Useful when re-scoping a sprint before running it. Refuses if the sprint is `running` or `completed`.
