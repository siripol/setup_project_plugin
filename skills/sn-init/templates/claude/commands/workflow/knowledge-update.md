---
name: knowledge-update
description: Run knowledge-curator across all completed REQs and refresh Obsidian knowledge buckets (projects/, global/shared/, global/tech/).
---

Idempotent. Re-reads every completed REQ + PLAN, regenerates per-topic files using the existing traceback frontmatter to detect updates vs. new facts. Auto-regenerates `<vault>/knowledge/global/tech/README.md` cross-project matrix.

Routes via `ObsidianClient` (`--obsidian-mcp` flag controls backend).
