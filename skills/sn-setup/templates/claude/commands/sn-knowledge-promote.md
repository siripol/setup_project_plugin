---
name: sn-knowledge-promote
description: Move a topic from projects/<project>/ to global/shared/ in the Obsidian vault. Use when a project-domain fact turns out to apply org-wide.
args:
  - TOPIC (required) — topic name (filename without .md)
---

`mv <vault>/knowledge/projects/<project>/<topic>.md → <vault>/knowledge/global/shared/<topic>.md`. Updates `bucket:` frontmatter. Preserves `origin_project:` traceback so the source is still discoverable.
