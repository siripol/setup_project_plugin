# How to use `diagnose-downstream-failure`

This skill diagnoses a failing downstream call in this BFF and produces a structured root-cause analysis. Use it when a downstream is reporting elevated errors, when integration tests show flaky downstream calls, or when on-call gets paged for BFF latency.

## When to invoke

- A downstream service has reported degraded status; you want to know what flows are affected.
- Integration tests are flaky in CI and the failures cluster around one downstream.
- On-call paging mentions BFF latency or downstream timeouts.
- Pre-incident drill: practice mapping a hypothetical downstream outage.

## How to invoke

In a Claude Code session:

> Run the `diagnose-downstream-failure` skill for the `userService` downstream.

Claude will:

1. Find every handler that calls `userService`.
2. Classify each call's criticality, timeout, retry, and circuit-breaker state.
3. Trace how a failure surfaces to the frontend per handler.
4. Output a structured analysis with mitigations at three time horizons.

## What to do with the output

- **Short-term mitigations** typically include circuit-breaker tuning, cache-warm trigger, or degraded-mode fallback verification.
- **Medium-term mitigations** typically include retry budget reassessment, timeout review, or extracting a hot path into a separate handler.
- **Long-term mitigations** typically include criticality reclassification (do we really need this downstream?), or refactoring the orchestration shape (parallel ↔ sequential).

The output is informational. The skill does not modify code, page on-call, or open PRs.

## Promotion path

After this skill has been used in ≥ 3 incident debriefs across different downstreams with no hand-edits to the skill body, evaluate promotion to the org marketplace as a generic BFF diagnostic. See `docs/PROMOTION.md` for the full process.

## See also

- `SKILL.md` — the actual skill body Claude reads when dispatched.
- `.claude/docs/bff-aggregation.md` — the patterns this skill diagnoses against.
- `.claude/agents/bff-integration-reviewer.md` — companion PR-time reviewer (catches issues before they ship).
