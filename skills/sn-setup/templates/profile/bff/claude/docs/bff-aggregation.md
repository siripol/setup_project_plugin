# BFF aggregation — ${name}

Long-form reference for typical BFF (Backend-for-Frontend) topics: downstream call orchestration, response shaping, caching strategy, error normalization. Claude reads this on demand when work touches aggregation handlers, downstream calls, or response transforms. Always-on rules live in `.claude/rules/` instead.

## What a BFF is and is not

A BFF is a **server-side aggregation layer bound to one frontend**. It composes data from N downstream services into the exact shape one specific UI needs. A BFF is NOT a generic API gateway (those route + auth + rate-limit; a BFF transforms data), NOT a microservice that owns its own data (those persist; a BFF is largely stateless), and NOT a frontend proxy (those forward; a BFF reshapes).

This `${name}` BFF serves a specific frontend; its endpoints exist to make that frontend simpler, faster, or both. When the frontend's needs diverge from another frontend's needs, build a second BFF — do not generalize this one.

## Downstream call orchestration

### Parallel vs. sequential

Downstream calls run in parallel unless one call's response is needed as input for another. The pattern:

```
async function getHomePage(userId) {
  const [user, posts, ads] = await Promise.all([
    userService.get(userId),
    postsService.list({ userId }),
    adsService.list({ userId }),
  ])
  return composeHomePage(user, posts, ads)
}
```

Sequential when:

- Second call depends on first call's result.
- Second call should only fire if the first succeeded with specific state.
- The downstream system explicitly requires session affinity.

### Timeouts per downstream

Each downstream call carries its own timeout. The default is shorter than the BFF's own request timeout — typically 80% — so a single slow downstream does not pin the BFF response. Per-downstream timeouts are tracked in config, not hardcoded per handler.

### Retry policy

Retries apply to **idempotent** reads only. Default: 1 retry on transient network errors (DNS, connection refused, TCP reset) and 5xx responses. Never retry POST/PUT/DELETE without an idempotency key.

Retry budget is shared across handler attempts: if 5 downstream calls each need 1 retry, the handler trips into the partial-response path rather than fanning out 10 attempts.

### Circuit breaker per downstream

Per-downstream circuit breaker thresholds (consecutive failures → trip → half-open after cooldown). Tripped downstream returns from cache when possible, else a degraded response (see partial-response handling below).

## Response shaping

### One endpoint, one frontend page

BFF endpoints map 1:1 to frontend pages or views. The endpoint name reflects the page (`/v1/home`, `/v1/product/{id}`, `/v1/checkout`). The response shape is exactly what that page needs — no extra fields, no nested objects the page does not consume.

### Shape lives in the BFF, not the frontend

Frontend code consumes the response as-is. No client-side reshaping. If the page needs a new field, the BFF endpoint adds it; the frontend's job is to render, not to compose.

### Schema evolution

Within a major version: add fields, do not remove or rename. The frontend ignores unknown fields, but BFF response shape stability is still a contract worth keeping.

Major bumps happen when the frontend's needs change in a way that breaks existing consumers — e.g., shipping a redesigned page that no longer needs the old shape.

## Caching strategy

### Three cache tiers

| Tier | Where | TTL | Use when |
|---|---|---|---|
| Per-request | In-memory within a single handler invocation | Request lifetime | Same downstream call would fire multiple times in one handler (deduplication). |
| Per-user | Local cache keyed by user_id | 30s – 5min | Same user's data fetched on consecutive page views. |
| Global | Shared cache (Redis, Memcached) | 1min – 1h | Reference data shared across users (taxonomies, feature flags, hot lists). |

Cache invalidation strategies: TTL is the default. Explicit invalidation on known write events (user updates profile → clear that user's cache key). Never invalidate the global cache from a single user's action.

### Cache key shape

Cache keys include the downstream service name, the operation, and the arguments. Include the BFF version in the key prefix so a major BFF release does not poison the cache with old shapes:

```
bff-v2:userService.get:userId=42
```

## Partial-response handling

When one downstream fails:

1. **Best-effort assembly.** If the failing downstream's data is non-critical (e.g., recommended-items widget on a homepage), assemble the response without it. Include a `degraded: true` flag in the response.
2. **Critical-path fail-fast.** If the failing downstream's data is essential (e.g., user identity on an authenticated page), return a structured error envelope. Do not return a half-rendered page.

Criticality is per-handler, declared explicitly. No "best-effort" defaults — every handler explicitly says which downstreams are critical.

The error envelope shape matches the microservice convention:

```json
{
  "error": {
    "code": "DOWNSTREAM_FAILURE",
    "message": "User identity service unavailable",
    "details": { "downstream": "userService" },
    "request_id": "..."
  }
}
```

## Authentication and authorization at the BFF layer

### Pass-through vs. translation

The BFF does NOT issue its own credentials to downstreams. It forwards the user's authenticated identity (typically as a signed token) so downstreams enforce their own authz.

### Aggregating across users

If a handler aggregates data across multiple users (e.g., a feed view), authorization is checked at the BFF for the requesting user and then per-item at each downstream. Never trust a downstream's per-item filter alone — if the downstream is compromised, the BFF should still refuse.

### Frontend-trusted but BFF-enforced

Some BFFs trust the frontend to send only valid user IDs (the frontend has the session). Even then, the BFF re-validates the session token. Frontends can be compromised; the BFF is the trust boundary.

## See also

- `.claude/agents/bff-integration-reviewer.md` — the seeded reviewer agent that checks PRs against these patterns.
- `docs/BFF-INTEGRATION.md`, `docs/DOWNSTREAMS.md`, `docs/PROFILE.md` — profile-level docs.
- `docs/SECURITY.md` — template-family security posture (cross-link).
