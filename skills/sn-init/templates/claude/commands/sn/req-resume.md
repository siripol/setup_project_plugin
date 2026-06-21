---
name: req-resume
description: Resume an interrupted sprint-run cycle from .sn-init/workflow-state.json.
---

Reads `.sn-init/workflow-state.json` to find the active REQ + last in-progress phase, then re-enters the orchestrator at that step. Subagent reruns are idempotent — state file tracks completion per phase.
