# API — ${name}

The single source of truth for what `${name}` exposes over the network.

## Transport

| Style | When to pick |
|---|---|
| REST + JSON | External callers, web/mobile, broad tool support. Default. |
| gRPC | Internal service-to-service, strict schemas, perf-sensitive. |
| Async events | Fan-out, decoupling, eventual-consistency flows. |

Pick **one primary** transport per resource. Mixing is allowed but each path must be intentional.

## Contract

- REST → `api/openapi.yaml` (OpenAPI 3.1). Generated from code or hand-edited; CI fails on drift.
- gRPC → `api/*.proto`. Generated stubs check into `gen/`.
- Events → `api/events/*.json` schemas, one file per event type.

Every public endpoint in the contract has:
1. Summary + description.
2. Request schema with required/optional fields.
3. Response schema per status code.
4. Error response schema (shared across endpoints — see "Errors" below).
5. Example request + response.

## Versioning

- URL versioning: `/v1/orders`, `/v2/orders`. Major version in the path.
- Minor/patch changes are backward-compatible and don't bump the URL.
- Deprecation: announce → grace period (≥1 release cycle) → remove. Document in `CHANGELOG.md`.

## Errors

Every error response uses the same envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Order 42 not found",
    "details": { "order_id": "42" }
  }
}
```

`code` is a stable machine-readable string. `message` is human-readable. `details` is optional and free-form.

## Auth

- Default: bearer JWT in `Authorization` header.
- Service-to-service: mTLS or signed service tokens; document in this file when wired.
- Public endpoints (no auth) are listed explicitly in the contract.

## Testing

- Contract tests live in `tests/contract/` and run on every PR.
- Breaking changes require updating both the contract and the contract tests in the same commit.
