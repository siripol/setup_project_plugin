---
name: sprint-run
description: Execute a sprint. Runs mandatory impact-analyzer pre-check; halts on major impact. Then runs the full spec-loop per REQ (topo-sorted by requires:).
args:
  - SPRINT (required) — sprint id
---

Flow:

1. Read sprint folder + REQs.
2. Run impact-analyzer → `impact.md`. If `has_major: true`, halt + AskUserQuestion (proceed/edit/cancel).
3. `git tag sn-init/pre-REQ-NNN-<ts>` per REQ.
4. For each REQ: planner → task-decomposer → (per task: tester + executor or executor + tester depending on `--workflow-tdd`) → integration-tester → adversary → evaluator.
5. Triple-signal exit gate: `eval >= threshold AND integration.pass AND adversary.findings_resolved`.
6. On all-pass: doc-writer + knowledge-curator. `make sprint-done SPRINT=...` to archive.

State persisted in `.sn-init/workflow-state.json`. `/req-resume` picks up after crash.
