---
name: diagnose-downstream-failure
description: Diagnose a failing downstream call in this BFF — root cause, affected handlers, propagation to frontend, mitigations. Invoke when a downstream is reporting elevated errors, when CI integration tests show flaky downstream calls, or when the on-call gets paged for BFF latency.
tools: [Read, Glob, Grep]
---

# Diagnose downstream failure — ${name}

You are diagnosing a downstream call failure in this BFF. Output a structured root-cause analysis with affected handlers, propagation behavior, and recommended mitigations. You read code and logs; you do not modify code.

## What to diagnose

1. **Identify the failing downstream.** Either the user names it, or you infer from recent logs / error messages.
2. **Find every handler that calls it.** Use `Grep` across the handlers directory.
3. **Classify the criticality per handler.** From the handler code: is the downstream marked critical (hard-fail) or non-critical (best-effort assembly with `degraded: true`)?
4. **Trace the failure surface.** What does the frontend see for each handler? A degraded response? A 503? A timeout?
5. **Identify the timeout config.** Per-downstream timeout for the failing call. Is it appropriate, too tight, too loose?
6. **Identify the retry config.** Idempotent reads only? Is retry budget contributing to or relieving the failure?
7. **Identify the circuit breaker state.** Where in the code is the breaker; what threshold; what's the cooldown? Is the breaker tripping correctly?
8. **Cache state.** Could cache serve stale data during the outage? Is cache invalidation correctly scoped?

## How to find the relevant code

Start with `Grep` for the downstream service name in handler files (`src/handlers/`, `internal/handlers/`, or the framework's equivalent). Then read each match's surrounding context — `Read` the file from 20 lines before to 20 lines after the call site to understand the orchestration shape.

For BFF orchestration patterns (`Promise.all`, `await asyncio.gather`, `errgroup`), trace how the call site composes with siblings: parallel or sequential, whether sibling failures abort the group.

## Output format

```
Downstream: <name>
Calls found: <N> across <M> handlers

| Handler | Criticality | Timeout | Retry | Failure visible to frontend |
|---|---|---|---|---|
| /v1/home | non-critical | 800ms | 1x on 5xx | degraded: true, missing recommended items |
| /v1/checkout | CRITICAL | 1500ms | 0 | 503 with DOWNSTREAM_FAILURE envelope |
| ... | ... | ... | ... | ... |

Root cause hypothesis: <one-paragraph>
Affected user flows: <bullet list>

Mitigations:
1. Short-term (minutes-hours): <bullet list>
2. Medium-term (hours-days): <bullet list>
3. Long-term (days-weeks): <bullet list>

Recommended next steps:
- <bullet list>
```

## What NOT to do

- Do not modify code. This is diagnosis, not remediation.
- Do not propose fixes that change criticality classification without surfacing the trade-off.
- Do not generalize across all BFFs — this analysis is for THIS BFF and THIS downstream.
- Do not include raw log data in the output; summarize patterns.
- Do not page the on-call. The user reads the output and decides who to escalate to.

## See also

- `.claude/docs/bff-aggregation.md` — the patterns this skill checks against.
- `.claude/agents/bff-integration-reviewer.md` — companion PR-time reviewer.
