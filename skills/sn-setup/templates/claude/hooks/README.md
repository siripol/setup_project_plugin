# .claude/hooks/

Claude Code session hooks. Register handlers in `.claude/settings.json` `hooks` block.

Available event types:

- `UserPromptSubmit` — fires when the user submits a prompt.
- `SessionStart` / `SessionEnd` — session lifecycle.
- `PreToolUse` / `PostToolUse` — wrap each tool call.
- `Stop` — fires when the session is about to exit.

Register example:

```json
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Edit|Write", "command": ".claude/hooks/audit.sh"}
    ]
  }
}
```
