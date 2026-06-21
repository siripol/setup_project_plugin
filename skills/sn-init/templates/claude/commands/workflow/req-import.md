---
name: req-import
description: Convert an md/txt/json/docx/pdf source into a REQ-NNN.md file.
args:
  - FILE (required) — path to source document
---

Run `python scripts/importers/<ext>.py FILE` and write `docs/requirements/active/REQ-<next>-<slug>.md`. Extracted: title, acceptance bullets, sources, priority hint.

User reviews + edits the resulting REQ before assigning it to a sprint.
