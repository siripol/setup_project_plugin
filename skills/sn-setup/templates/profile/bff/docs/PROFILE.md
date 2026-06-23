# Profile: bff

`${name}` is scaffolded as a **Backend-for-Frontend (BFF)** — an aggregation layer that sits between one frontend (web or mobile) and several backend microservices.

## Shape

- Owns *no* domain data. Persists nothing of its own beyond cache/session.
- Aggregates ≥ 2 downstream services into views shaped for one specific frontend.
- Translates between the frontend's preferred protocol (typically GraphQL or REST) and downstream contracts.
- Lives and versions with its frontend, not with the downstream services.

## Conventions

- Downstream contracts are mirrored under `contracts/` and synced from each owning service (see `docs/DOWNSTREAMS.md`).
- Aggregation logic lives in `internal/aggregators/<view>/`; one folder per frontend view.
- BFF responses are tailored — never return raw downstream payloads to the frontend.
- Auth tokens are exchanged at the BFF edge; downstream calls use service identity, not the user's token.

## What this profile *isn't*

- A microservice (`--profile=microservice`) — owns a domain.
- A frontend (`--profile=frontend`) — owns UI rendering.
- An API gateway — gateways are generic and shared; a BFF is opinionated and per-frontend.

## Why go-first

The default lang for `bff` is `go` (per the scaffolder's matrix). Fan-out aggregation is concurrent-IO-heavy, and Go's goroutines + context-cancellation map cleanly onto that shape. `ts` is also supported when the team prefers Node ecosystem fit (Fastify, NestJS).

## See also

- `docs/BFF-INTEGRATION.md` — how the frontend talks to this BFF.
- `docs/DOWNSTREAMS.md` — which services this BFF depends on.
