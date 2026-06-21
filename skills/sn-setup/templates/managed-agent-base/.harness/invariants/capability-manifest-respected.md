---
name: capability-manifest-respected
description: Subagents only write to paths listed in their `can_modify:` capability manifest.
test: tests/invariants/test_capability_manifest.py
severity: critical
---

## Statement

Every file modified during a sprint must be reachable from the running subagent's `can_modify:` glob list declared in `.claude/agents/<subagent>.md`. The chokepoint-gate hook (`.claude/hooks/chokepoint-gate.{sh,py,ts}`) is the runtime enforcer; this invariant is the audit-time check.

## Why

The point of the per-subagent capability manifest is least-privilege. `sn-task-executor` should never overwrite `agents/main.yaml`; `sn-knowledge-curator` should never edit `src/`. Without this check a single mis-scoped agent prompt can quietly leak across boundaries — the symptom only shows up when a downstream phase blames a file the previous phase shouldn't have touched.

## Test strategy

For each REQ in `docs/sprints/completed/SPRINT-*/`, replay the audit log (`.sn-init/logs/exec-*.jsonl`) and assert every `tool_name in {Edit, Write}` event's `tool_input.file_path` matches at least one glob in the active subagent's `can_modify:` list. Mutation cases:

- A successful Write to a path inside `can_modify` → pass.
- A blocked Write to a path outside `can_modify` (PreToolUse hook returned block) → pass; the block is the expected behaviour.
- A successful Write to a path outside `can_modify` → fail. Implies the chokepoint-gate hook was bypassed or misconfigured.
