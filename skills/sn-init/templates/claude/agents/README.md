# .claude/agents/

Local Claude Code subagent definitions. Each `<name>.md` declares a subagent with frontmatter:

```yaml
---
name: my-agent
description: When to invoke this subagent
tools: [Read, Grep, Glob]
can_modify: []        # paths it may write (capability manifest)
can_delegate: []      # other subagents it may invoke
---

(System prompt body)
```

The base 2 (code-reviewer, test-writer) ship by default. Use `/sn-init --subagents=all` to ship the full library.
