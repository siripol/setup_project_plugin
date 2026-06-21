---
name: test
description: Invoke the test-writer subagent to draft + run tests for a module.
args:
  - TARGET (required) — module or function to test
---

Spawns `test-writer`. Draft tests, save under `tests/`, run them, report pass/fail. Does not modify implementation source.
