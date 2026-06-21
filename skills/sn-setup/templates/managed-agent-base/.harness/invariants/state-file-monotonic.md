---
name: state-file-monotonic
description: `.sn-init/workflow-state.json` `phase_history[REQ-NNN]` only grows; phases are never erased or reordered.
test: tests/invariants/test_workflow_state_monotonic.py
severity: high
---

## Statement

For every REQ, the `phase_history` array in `.sn-init/workflow-state.json` is append-only across a sprint run. Phases land in topological order (impact → plan → decompose → execute → test → integrate → adversary → evaluate → curate), each entry carries a UTC timestamp, and earlier entries are never mutated.

## Why

`/sn-req-resume` relies on the state file to know where to pick up after a crash. If a previous phase entry can be overwritten, resume picks a stale verdict; if entries can be deleted, resume runs a phase twice and clobbers proof-bundle artefacts. The monotonic invariant is what makes resume safe.

## Test strategy

Snapshot `phase_history[REQ-NNN]` at every `record_phase()` call (instrumented in `scripts/orchestrator.py`) and assert:

- Length only increases between snapshots — `len(after) >= len(before)`.
- All prior entries are unchanged — `after[: len(before)] == before`.
- Each new entry has `ts` strictly greater than the previous entry.
- Phase order matches the `PHASES` tuple ordering.

Mutation cases:

- Append a new phase entry → pass.
- Replace an entry in place → fail.
- Reorder phases (e.g. evaluate before integrate) → fail.
- Backwards timestamp → fail.
