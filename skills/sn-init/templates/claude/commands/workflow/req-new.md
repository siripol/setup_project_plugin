---
name: req-new
description: Scaffold a new REQ-NNN file under docs/requirements/active/. Auto-increments NNN.
args:
  - SLUG (required) — short kebab-case identifier
---

Create `docs/requirements/active/REQ-<next>-<SLUG>.md` from `docs/requirements/template.md`. Scans all sprint dirs + active/ to find max REQ-NNN and increments.
