---
name: sprint-add
description: Move a REQ from docs/requirements/active/ into a sprint's requirements/ subfolder. Updates sprint.md reqs list.
args:
  - SPRINT (required) — sprint id
  - REQ (required) — REQ id
---

Move `docs/requirements/active/REQ-NNN-*.md` → `docs/sprints/active/SPRINT-NNN-*/requirements/`. Appends REQ id to sprint.md `reqs:` list. Preserves traceback frontmatter.

Refuses if the REQ is already in a different sprint.
