---
name: agent-sdk-conformance
description: src/agent.{py,ts,go} stays compliant with the 12 Agent SDK best-practices rules across every sprint.
test: scripts/verify_agent_sdk.py + sn-agent-sdk-reviewer subagent review
severity: high
---

## Statement

Every commit that touches `src/agent.{py,ts,go}` must leave the file passing all six mechanical rules from `docs/principles/agent-sdk-best-practices.md` (checked by `scripts/verify_agent_sdk.py`) and not introduce regressions on the six prose-analysis rules (reviewed by `sn-agent-sdk-reviewer`).

## Why

The 12 rules encode patterns Anthropic ships in the official Agent SDK documentation plus opinions from this scaffold. A drift in any rule means future SDK upgrades or third-party plugin integrations will surprise the user — e.g. an unpinned `model` field starts returning a different model after a minor SDK bump, or a missing `setting_sources` restriction lets a developer-local hook leak into a customer-facing agent. The invariant exists so `sn-adversary` will actively try to break the rules during each sprint, and any successful break commits a new failing test to `tests/adversary/`.

## Test strategy

Two layers, run in this order during the adversary phase:

1. **Mechanical** — `python3 scripts/verify_agent_sdk.py` against `src/agent.{py,ts,go}`. rc 0 = pass, rc 2 = at least one rule failed (each failure printed as `::error file=...::rule N: ...`), rc 3 = no agent files (acceptable — Tier 1 only).
2. **Prose** — invoke `sn-agent-sdk-reviewer` subagent. Verdict ladder: `PASS` → `PASS WITH WARNINGS` → `FAIL`. Any `FAIL` on rules 4, 7, 8, 10, 11, 12 trips this invariant.

Adversary mutation cases (must each produce a failure that lands a regression test in `tests/adversary/`):

- Remove `allowed_tools=[...]` from `src/agent.py` → rule 1 fail.
- Inject a literal `sk-...` key string → rule 2 fail.
- Replace `model="..."` with the SDK default → rule 3 fail.
- Drop the `HookMatcher(...)` entry → rule 5 fail.
- Set `AgentDefinition(tools=[])` → rule 6 fail.
- Remove `setting_sources=["project"]` in a `--tier=3` scaffold → rule 9 fail.
- Switch `permission_mode` to `"acceptEdits"` against an untrusted repo → rule 4 WARN.
- Collect messages into a list before processing (`messages = [m async for m in query(...)]`) → rule 11 FAIL.
- Remove the `try/except` around the loop body → rule 12 FAIL.

Each successful adversary break MUST land a corresponding failing test under `tests/adversary/agent_sdk__<rule_short>__test.{py,ts,go}` so the regression is permanent.

## Scope

- In scope: `src/agent.{py,ts,go}` and any direct caller (e.g. `src/cmd/orchestrator/main.go`).
- Out of scope: third-party MCP server code, scaffolded `.claude/hooks/*` (covered by [[capability-manifest-respected]]), template files under `skills/`.
