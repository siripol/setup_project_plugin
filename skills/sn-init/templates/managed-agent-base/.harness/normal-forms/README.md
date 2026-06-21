# .harness/normal-forms/

Allowed and forbidden shapes per component kind. Each file enforces the
"engineering normal form" for one kind of artifact (subagent, MCP server,
skill, etc.).

Pattern:

```yaml
---
component: subagent
path: .claude/agents/*.md
allowed:
  - frontmatter has: [name, description, tools, can_modify]
forbidden:
  - tool list includes "Bash" without can_modify scoping
  - body length > 500 lines
---

## Rationale

(Why this normal form. Reference RELIABILITY.md / SECURITY.md.)
```

A `normal-form-check` Makefile target (TBD) runs the rules. Violations block PR merge in CI.
