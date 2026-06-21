---
name: sn-verify
description: Check src/agent.{py,ts,go} against the 6 mechanically-checkable Agent SDK best-practices rules shipped in docs/principles/agent-sdk-best-practices.md. Exits 0 on pass, 2 on failure with `::error file=…::` annotations for CI.
---

Runs `scripts/verify_agent_sdk.py` on every agent source file under `src/`. Six checks:

| # | Rule | Check |
|---|---|---|
| 1 | Whitelist tools | `allowed_tools=[...]` (Python) or `allowedTools: [...]` (TS) present |
| 2 | No hardcoded API key | No `ANTHROPIC_API_KEY` literal string in source |
| 3 | Lock the model id | `model="..."` keyword present, not relying on SDK default |
| 5 | Hooks for guaranteed side effects | At least one `HookMatcher(...)` (py) or `hooks:` block (ts) |
| 6 | Define subagents narrowly | Every `AgentDefinition` has non-empty `tools=[...]` |
| 9 | Restrict setting_sources in prod | `setting_sources=["project"]` (py) or `settingSources: ["project"]` (ts) when scaffolded with `--tier=3` |

Each failure prints `::error file=src/agent.py::rule N: <description>` so CI surfaces them in the GitHub UI.

The other six rules (`permission_mode`, session persistence, MCP vetting, `WebSearch` necessity, streaming, error catch) require prose analysis — invoke the `sn-agent-sdk-reviewer` subagent for those.

```bash
make verify          # same thing via Make
```

For broader checks (Python env, TS config, dep hygiene), install Anthropic's official plugin and run its verifiers:

```
/plugin install agent-sdk-dev
```

Then: `"Run agent-sdk-verifier-py on this project"`.
