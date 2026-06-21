---
name: sn-knowledge-demote
description: Move a topic from global/shared/ back to projects/<project>/. Use when a "shared" fact turns out to be project-specific after all.
args:
  - TOPIC (required) — topic name
---

Reverse of `/sn-knowledge-promote`. Refuses if the topic is referenced by other projects (via traceback frontmatter).
