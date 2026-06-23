# Downstreams — ${name}

The services `${name}` depends on. Keep this file current — it is the operational map operators reach for during incidents.

## Registry

| Service | Owner | Contract | Auth | Timeout | Retries | SLA | Notes |
|---|---|---|---|---|---|---|---|
| _example-orders_ | team-orders | `contracts/orders/openapi.yaml` | mTLS | 800ms | 1 | 99.9% | replace with real entries |

Add one row per direct downstream. Indirect dependencies (downstream-of-downstream) belong on each owner's own DOWNSTREAMS file, not here.

## Contract sync

Each downstream's contract is mirrored under `contracts/<service>/`. The mirror is **read-only** in this repo — edits land in the owning repo and propagate here via `scripts/contract-sync`.

CI fails if `contracts/` is out of sync with the upstream sources. Re-run sync, commit, then re-run CI.

## Mocks

- Mocks live under `mocks/<service>/` and are generated from the contracts.
- `scripts/downstream-mock <service>` boots a mock server matching the contract's examples.
- Mock fidelity ends at the schema — semantic behavior (idempotency, side-effects) is not modeled. Integration tests must run against real or staging downstreams.

## Degradation policy

- Required downstreams: failure ⇒ BFF returns 503 with `error.code = DOWNSTREAM_UNAVAILABLE`.
- Optional downstreams: failure ⇒ BFF returns a partial view with `degraded: true` and a per-field `_omitted: true` marker on the missing pieces.
- Mark every downstream as **required** or **optional** in the registry table — there is no default.
