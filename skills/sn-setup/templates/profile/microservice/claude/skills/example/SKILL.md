---
name: audit-endpoint-coverage
description: Audit this microservice's HTTP/gRPC endpoints for authorization coverage, input validation, error envelope consistency, and observability. Invoke before merging a PR that adds or modifies endpoints.
tools: [Read, Glob, Grep]
---

# Audit endpoint coverage — ${name}

You are auditing this service's external endpoints against the microservice review checklist. Output a per-endpoint table with verdicts; do not modify code.

## What to audit

For each handler in the service:

1. **Authentication boundary.** Confirm the handler receives an authenticated identity type (e.g., `AuthenticatedRequest`) rather than raw request data. Flag endpoints that accept anonymous requests when they should not.

2. **Authorization check.** Confirm an explicit authorization check runs after object lookup but before mutation or return. Flag handlers that scope by query filter alone (potential IDOR).

3. **Input validation.** Confirm request bodies, query strings, and path parameters are validated at the boundary. Flag unknown-field-tolerance, missing numeric bounds, missing string length bounds, and missing path normalization.

4. **Error envelope.** Confirm errors emit the service-wide envelope shape `{ "error": { "code", "message", "details?", "request_id" } }` with stable `code` values. Flag inconsistent envelopes, raw-error leaks, and user-input echo.

5. **Observability.** Confirm structured log lines fire at start + completion of each request, with the standard field set (timestamp, level, service, request_id, route, event). Flag handlers that log unstructured strings or omit fields.

6. **Audit log.** For endpoints touching regulated data: confirm a dedicated audit log line fires per access, distinct from operational logs. Flag missing audit events on regulated paths.

## How to find the handlers

Start with the framework convention (e.g., for Go HTTP: `http.HandleFunc` calls, `mux.HandleFunc`, `chi.Router` routes; for Python FastAPI: `@app.get`, `@app.post`; for Node Express: `app.get`, `router.post`). Use `Grep` to find the call sites, then `Read` each handler to evaluate.

If the framework's routing is non-obvious, ask the user before starting the sweep.

## Output format

```
| Endpoint | AuthN | AuthZ | Input | Error envelope | Logs | Audit | Notes |
|---|---|---|---|---|---|---|---|
| POST /v1/users | ✅ | ✅ | ⚠ missing email max length | ✅ | ✅ | n/a | — |
| GET /v1/users/{id} | ✅ | ❌ scopes by query filter only | ✅ | ✅ | ✅ | n/a | IDOR risk — fix before merge |
```

Use ✅ for compliant, ⚠ for partial (works but has a gap), ❌ for missing. The Notes column flags critical issues for PR review.

Summary at the bottom: count of ✅ / ⚠ / ❌ across all endpoints, plus a recommendation (approve / fix-before-merge / block).

## What NOT to do

- Do not modify code. This is an audit, not a refactor.
- Do not propose fixes inline. If the user wants fixes, they will dispatch a separate task.
- Do not chase issues outside the endpoint boundary (database schema, downstream service contracts). Those belong to dedicated reviewers.
- Do not flag style issues. The audit is about correctness and security, not formatting.

## See also

- `.claude/docs/microservice-conventions.md` — the standards this skill checks against.
- `.claude/agents/microservice-reviewer.md` — broader PR review subagent that may invoke this skill as part of its sweep.
