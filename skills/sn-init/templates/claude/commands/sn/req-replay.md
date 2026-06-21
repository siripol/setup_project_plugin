---
name: req-replay
description: Re-run a completed REQ's tasks on a throwaway branch for regression check.
args:
  - REQ (required) — REQ id (e.g. REQ-003)
---

Creates a `replay/REQ-NNN` branch from the pre-REQ snapshot tag, replays each TASK via executor + tester, reports pass/fail. Useful to verify a completed REQ still passes against current dependencies.
