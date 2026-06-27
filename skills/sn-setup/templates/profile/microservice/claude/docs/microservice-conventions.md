# Microservice conventions — ${name}

Long-form reference for typical microservice topics. Claude reads this on demand when work touches request handling, persistence, observability, API versioning, or related concerns. Always-on rules live in `.claude/rules/` instead.

## Request handling

### Boundary validation

External request bodies (HTTP, gRPC, queue payloads) are validated at the boundary handler before any business logic runs. The validator:

- Rejects unknown fields by default; do not silently drop them.
- Bounds numeric inputs explicitly (min, max).
- Bounds string lengths explicitly (max length, ideally minimum too).
- Normalizes path-shaped inputs and rejects directory-traversal patterns.

The validation error response uses the standard error envelope (`{ "error": { "code": "...", "message": "..." } }`) and never echoes raw user input back unsanitized.

### Authentication and authorization

Authentication runs in middleware before any handler is invoked. Handlers receive a typed identity object (`AuthenticatedRequest`); the type system prevents accidental unauthenticated access.

Authorization runs **inside** the handler, after object lookup but before object mutation or return. Object-level authz prevents IDOR (Insecure Direct Object Reference): scoping by query filter alone is insufficient because a missing filter yields a silent 200 instead of a 403.

### Error envelope

The service-wide error envelope is fixed across all endpoints:

```json
{
  "error": {
    "code": "MACHINE_READABLE_SLUG",
    "message": "Human-readable summary",
    "details": { "field": "optional, when validation"  },
    "request_id": "uuid, copied from X-Request-Id or generated"
  }
}
```

`code` is stable across releases. `message` is human-readable and may change. Callers branch on `code`, never on `message`.

## Persistence

### Transactions

Each request that mutates state runs in a single database transaction. The handler opens the transaction, executes business logic, and commits or rolls back before returning. Long-running transactions (> 5s) are an anti-pattern; refactor the operation into smaller atomic units.

### Migrations

Schema changes ship as numbered, forward-only migrations. Down-migrations are not maintained (they encourage rollback as a debugging tool, which is worse than rolling forward).

### N+1 queries

Every read endpoint that returns a list is reviewed for N+1 query patterns. The review tool of choice (e.g., `pg_stat_statements` for Postgres) runs in CI on the integration test suite; any endpoint adding > 10 queries triggers a review.

### Connection pooling

The pool size is sized to the deployment's concurrency, not to the database's max connections. Over-pooling pushes connection limits at the database; under-pooling serializes requests in front of the pool.

## Observability

### Structured logging

Logs are JSON, written to stdout. Fields:

- `timestamp` (ISO 8601, UTC)
- `level` (`debug` | `info` | `warn` | `error`)
- `service` (this service's name)
- `request_id` (from the request envelope)
- `user_id` (when authenticated; null otherwise)
- `route` (path template, not interpolated)
- `event` (lowercase verb-noun, e.g., `request_completed`, `validation_failed`)
- `duration_ms` (numeric, for terminal events)

No PII in log fields. No SQL strings. No stack traces in info-level logs (errors only).

### Metrics

RED metrics per endpoint: **R**ate, **E**rrors, **D**uration. Plus a fourth: saturation (queue depth, pool utilization). Push to whatever metrics backend the org runs.

### Traces

Distributed trace spans wrap each handler. Spans carry the request_id and propagate via the standard `traceparent` header. Internal calls (DB, cache, downstream services) get their own child spans.

### Audit log

The plugin's audit hook writes a JSONL line per Claude tool call. Service-side audit events (login, role change, regulated-data access) write a separate JSONL stream with field-named records, distinct from operational logs. The audit stream's retention follows the regulated-tier policy when applicable.

## API versioning

### Strategy

URL versioning: `/v1/resource`, `/v2/resource`. URL versioning is easier to cache and easier to reason about than header versioning, at the cost of slightly noisier paths.

### Forward compatibility

Within a major version: add fields, do not remove or rename. Clients ignore unknown fields. Server enforces this contract — no silent breaking changes within a major.

### Deprecation

Deprecated endpoints emit a `Deprecation` and `Sunset` header (per RFC 8594 / 9745) plus a structured log line per call. After the sunset date, the endpoint returns 410 Gone.

## When to escalate to a major version bump

- Renaming or removing a field in a response.
- Changing the semantics of an existing field.
- Tightening validation in a way that rejects previously-accepted inputs.
- Changing the auth model (e.g., requiring a new scope).

Adding a new endpoint, adding a new optional field, or loosening validation does NOT require a major bump.

## See also

- `.claude/agents/microservice-reviewer.md` — the seeded reviewer agent that checks PRs against these conventions.
- `docs/API.md`, `docs/OBSERVABILITY.md`, `docs/PROFILE.md` — profile-level docs.
- `docs/SECURITY.md` — template-family security posture (cross-link).
