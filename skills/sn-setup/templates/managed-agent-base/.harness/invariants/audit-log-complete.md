---
name: audit-log-complete
description: Every tool call during a sprint run produces a matching JSONL audit record under `.sn-init/logs/`.
test: tests/invariants/test_audit_log_complete.py
severity: high
---

## Statement

For each `PreToolUse` event written to `.sn-init/logs/exec-<date>-<session>.jsonl`, the same session log must contain a matching `PostToolUse` record with the same `tool_use_id`. Sessions never end with an outstanding `PreToolUse` that has no closing record.

## Why

The audit log is what `make logs-stats` reads to compute per-session token usage and per-tool counts. It is also what `[[ralph-wiggum-integration]]` relies on for the "both hooks see the same stdout" claim — Ralph's Stop hook can only re-feed safely if the audit log already captured the iteration's tool calls. A missing PostToolUse means a tool call hung, was killed, or the audit hook failed mid-write — any of those is a bug worth surfacing.

## Test strategy

For each completed sprint's session log:

- Build a multiset of `tool_use_id` from `PreToolUse` records.
- Subtract the multiset of `tool_use_id` from `PostToolUse` records.
- Assert the difference is empty.

Mutation cases:

- A matched Pre/Post pair → pass.
- A `PreToolUse` with no `PostToolUse` → fail. Possible causes: killed shell, audit hook crash, network timeout.
- A `PostToolUse` with no `PreToolUse` → fail. Indicates log corruption or tool-use-id collision across sessions.
- Multiple `PostToolUse` records for the same id → fail. Indicates a retry path that double-counts.
