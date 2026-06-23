# BFF Integration — ${name}

How the frontend integrates with `${name}` (the BFF) and how `${name}` integrates with its downstreams.

## Frontend ↔ BFF

| Concern | Default |
|---|---|
| Transport | REST + JSON, or GraphQL when the frontend benefits from field-level selection. |
| Auth | Frontend sends a short-lived user token (JWT or cookie); BFF validates and exchanges for downstream service identity. |
| Errors | Single envelope `{ error: { code, message, details } }` regardless of which downstream failed. |
| Versioning | URL-versioned (`/v1/...`). The BFF can ship breaking changes in lock-step with the frontend. |
| Caching | BFF may cache aggregated views; downstream caching is the downstream's concern. |

The BFF response is shaped for the frontend's view, not the downstream's storage. Two principles:

1. **No raw passthrough.** If you find yourself proxying a downstream payload unchanged, the call belongs in the frontend (or a gateway), not the BFF.
2. **One BFF endpoint, one view.** Resist generic "fetch anything" endpoints — they invite over-fetching and erode the BFF's reason to exist.

## BFF ↔ Downstreams

- Every downstream service is declared in `docs/DOWNSTREAMS.md` with: owner, contract path, SLA, auth mode.
- Contracts live under `contracts/<service>/` — mirrored from each owning service, never hand-authored locally.
- All downstream calls go through generated clients; do not hand-roll HTTP in business code.
- Timeouts and retries are explicit per dependency, never defaulted globally.
- A downstream outage degrades the BFF response, not the BFF's availability — return partial views with a `degraded: true` marker.

## Local development

- Downstream mocks live under `mocks/<service>/`. See `scripts/downstream-mock` for spinning them up.
- The frontend can point at the BFF in mock-mode for offline UI work.

## Observability

- Inherit the microservice profile's three pillars (logs / metrics / traces).
- Add a `downstream_call_duration_seconds` histogram labeled `{downstream, op, outcome}` — operators read it before reading anything else when a view is slow.
- Each aggregated response includes a `Server-Timing` header with per-downstream timings.
