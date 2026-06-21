# .harness/invariants/

Architectural invariants — rules that must hold across the codebase. Each
invariant has a paired test that proves it. `make check-invariants` runs all
tests in this directory.

Each invariant file:

```yaml
---
name: agents-only-write-into-can_modify
description: Subagents never write outside their declared can_modify paths.
test: invariants/test_capability_manifest.py
severity: critical
---

## Statement

(One sentence: the rule.)

## Why

(What goes wrong if violated.)

## Test strategy

(How `test` proves the invariant. Include mutation cases that should fail.)
```

The `sn:adversary` subagent runs after each spec-loop sprint and tries to falsify the invariants — any successful break commits a new failing test that catches the regression.
