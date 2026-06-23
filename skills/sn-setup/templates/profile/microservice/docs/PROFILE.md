# Profile: microservice

`${name}` is scaffolded as a **microservice** — a backend service owning a single bounded context, exposing a versioned API to other services.

## Shape

- Owns one domain (e.g. orders, billing, identity).
- Exposes REST or gRPC over the wire; no UI.
- Persists its own data; never reads another service's DB directly.
- Communicates with peers via published contracts (OpenAPI / proto / async events).
- Ships health, readiness, and metrics endpoints from day one.

## Conventions

- API contract lives in `docs/API.md` and (when generated) `api/openapi.yaml` or `api/*.proto`.
- Observability defaults in `docs/OBSERVABILITY.md` — logs, metrics, traces.
- Breaking API changes require a version bump and a deprecation window; see `docs/API.md`.
- DB migrations are versioned, forward-only, and reviewed before merge.

## What this profile *isn't*

- A BFF (`--profile=bff`) — aggregates downstream services for one frontend.
- A frontend (`--profile=frontend`) — owns UI, not domain state.

## Switching profiles

Profile is recorded in `.sn-init-state.json` under `profile`. Re-scaffolding into a fresh repo with a different `--profile=…` is the supported migration path; in-place flips are not.
