# .harness/rules/

Custom lint rules. Each rule lives in a `<rule-name>.md` file with frontmatter:

```yaml
---
name: no-direct-anthropic-call
severity: error            # error | warn | info
matches: src/**/*.py       # path glob
pattern: 'anthropic\.Anthropic\('
correction: |
  Use the centralized `get_client()` helper from `src/llm.py` so the
  agent picks up retry + audit logging. Direct anthropic client
  instantiation bypasses our reliability rails.
---

## Why

(Background on why this rule exists. Reference REQ + incident if any.)
```

When the rule fires, the `correction` block is injected directly into the agent's context so it can self-correct without a human round trip.

Hook integration: a pre-commit or PreToolUse hook (see `.claude/hooks/`) reads this directory and runs each rule's match check.
