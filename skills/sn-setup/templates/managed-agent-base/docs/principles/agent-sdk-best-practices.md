# Agent SDK best practices

Conventions every scaffolded agent in this project must follow. Sourced from Anthropic's [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) plus opinions from this scaffold.

The `/sn-verify` slash command and the `sn-agent-sdk-reviewer` subagent check this file's rules against `src/agent.{py,ts,go}`.

## 1. Whitelist tools per session

Pass an explicit `allowed_tools` list. Never run with the default — agents pick up `Bash`, `Write`, and `Edit` by accident and end up scribbling on files they should not touch.

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Glob", "Grep"],   # read-only review
)
```

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Bash", "Agent"],   # autonomous coder + delegates
)
```

`Agent` MUST appear in the parent's `allowed_tools` for any subagent to fire.

## 2. Auth via env var only

```bash
export ANTHROPIC_API_KEY=...
```

Never hardcode keys, never check `.env` into git, never accept a key from command-line args.

Third-party backend? Set the appropriate flag — Bedrock (`CLAUDE_CODE_USE_BEDROCK=1`), Vertex (`CLAUDE_CODE_USE_VERTEX=1`), Foundry (`CLAUDE_CODE_USE_FOUNDRY=1`), Claude Platform on AWS (`CLAUDE_CODE_USE_ANTHROPIC_AWS=1` + `ANTHROPIC_AWS_WORKSPACE_ID`). Each has a documented setup guide.

## 3. Lock the model id

```python
options = ClaudeAgentOptions(
    model="claude-opus-4-7",   # or whichever id the team has pinned for prod
    ...
)
```

The SDK's default is a moving target across minor versions. Pin it so behaviour is reproducible.

## 4. Set `permission_mode` deliberately

| Mode | When |
|---|---|
| `"acceptEdits"` | Trusted autonomy — known repo, scoped tools, you accept Edit/Write without per-call approval |
| `"requireApproval"` | Unknown territory — every tool call surfaces to the user before firing |

Default is conservative. Pick the right one for the use case.

## 5. Use hooks for guaranteed side effects

The hook lifecycle: `PreToolUse` → tool runs → `PostToolUse` → ... → `Stop`. Anything you want to ALWAYS happen — audit logging, rate limiting, prompt sanitization — belongs in a hook, not in the agent's prose.

```python
async def audit(input_data, tool_use_id, context):
    # write to .sn-init/logs/exec-*.jsonl
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PostToolUse": [HookMatcher(matcher="Edit|Write", hooks=[audit])],
    },
)
```

This project already wires three Stop hooks via `.claude/hooks/`: `audit.sh` (JSONL log), `rate-limit.sh` (hourly cap), `chokepoint-gate.sh` (block writes to guarded paths). They are registered in `.claude/settings.json` and fire in registration order.

## 6. Define subagents narrowly

Each subagent has its own `tools` whitelist. Keep it minimal:

```python
agents={
    "code-reviewer": AgentDefinition(
        description="...",
        prompt="...",
        tools=["Read", "Glob", "Grep"],   # NO Bash, NO Edit — review only
    ),
}
```

A review subagent that has `Bash` available will at some point run `npm install` against your machine. Strip the permission, not the discipline.

Subagent messages carry `parent_tool_use_id`; use it to trace which messages belong to which subagent execution.

## 7. Sessions are durable — write `session_id` to disk if you need it

The first message of a session is `SystemMessage(subtype="init")` with `data["session_id"]`. Capture it, persist it. Then resume:

```python
ClaudeAgentOptions(resume=session_id)
```

This scaffold's orchestrator (`scripts/orchestrator.py`) stores phase + session metadata in `.sn-init/workflow-state.json` so `/sn-req-resume` can pick up after a crash. Same pattern applies to any custom agent that needs to survive a process restart.

## 8. MCP servers are sandbox-equivalent

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]},
    }
)
```

Whatever an MCP server can read or write, your agent can read or write. Vet third-party servers like you would dependencies. For this project the only allowed MCP servers are listed in `mcp/mcp.json`.

## 9. Restrict `setting_sources` in production

```python
options = ClaudeAgentOptions(setting_sources=["project"])   # py
# or `settingSources: ["project"]` in TS
```

Default loads from `.claude/` in cwd + `~/.claude/`. In production you do not want a developer-local `~/.claude/agents/dev-debug.md` injecting into a customer-facing agent.

## 10. Disable `WebSearch` unless you need fresh data

Web search adds latency and non-determinism. If the use case is "read the codebase and answer", omit `WebSearch` from the tool whitelist. Re-enable for explicit research tasks.

## 11. Stream — don't collect

The `async for message in query(...)` loop is the supported pattern. Do not collect every message into a list before processing — you defeat streaming and double your peak memory.

```python
# correct
async for message in query(...):
    handle(message)

# wrong
messages = [m async for m in query(...)]
for m in messages:
    handle(m)
```

## 12. Catch + re-emit errors inside the loop

An unhandled exception inside the `async for` body closes the iterator. Wrap each turn:

```python
async for message in query(...):
    try:
        handle(message)
    except Exception as e:
        log.exception("handler failed")
        # keep iterating; one bad message should not kill the session
```

## Verification

Run `/sn-verify` (or `make verify`) to check `src/agent.{py,ts,go}` against rules 1, 2, 3, 5, 6, 9 (the mechanically checkable ones). The `sn-agent-sdk-reviewer` subagent reviews the harder rules (4, 7, 8, 10, 11, 12) using prose analysis.

## Source

[Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview). Re-read on every SDK minor bump:

- Python SDK changelog: https://github.com/anthropics/claude-agent-sdk-python/blob/main/CHANGELOG.md
- TypeScript SDK changelog: https://github.com/anthropics/claude-agent-sdk-typescript/blob/main/CHANGELOG.md
