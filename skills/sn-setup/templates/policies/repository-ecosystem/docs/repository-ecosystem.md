# Policy — Repository Ecosystem

The list of services this repo is aware of. Edit the section matching your profile below. Keep tables small — this is for **cross-service awareness**, not full topology.

## How to read this doc

Each profile foregrounds different services first. Replace the example rows with your real services. The order matters: Claude reads top-to-bottom, so put the services this repo cares about MOST at the top.

If this repo is on more than one profile axis (e.g. a BFF that also exposes a small public API), include both sections.

## Microservice — foreground peers

A microservice owns one bounded context. Foreground the **peers in the same domain** (other services in the same product area) so Claude can reason about cross-service consistency, shared schemas, and joint deploys.

| Service | Purpose | Repo |
|---|---|---|
| _example-orders_ | order capture + lifecycle | `org/orders` |
| _example-order-fulfillment_ | warehouse picks + dispatch | `org/order-fulfillment` |
| _example-order-returns_ | RMA flow + restock | `org/order-returns` |

Order the rows by call frequency or domain-coupling strength, not alphabetically.

## BFF — foreground downstreams

A BFF aggregates several backend services into views shaped for one frontend. Foreground the **downstream services it calls** first. The frontend it serves can be a single linked row at the bottom.

| Service | Purpose | Repo |
|---|---|---|
| _example-catalog_ | product catalog + search | `org/catalog` |
| _example-cart_ | cart state + checkout | `org/cart` |
| _example-pricing_ | dynamic pricing + promos | `org/pricing` |
| _example-storefront-web_ | the frontend this BFF serves | `org/storefront-web` |

Treat the downstream rows as "things this repo will call this sprint." Treat the frontend row as "the consumer that defines our response shape."

## Frontend — foreground its BFF

A frontend repo talks primarily to one BFF. Foreground that BFF first; below it, list any direct-backend dependencies (auth provider, analytics SDK, etc.) only if the frontend calls them WITHOUT going through the BFF.

| Service | Purpose | Repo |
|---|---|---|
| _example-storefront-bff_ | aggregation layer for this storefront | `org/storefront-bff` |
| _example-auth-edge_ | direct auth (if BFF isn't used for login) | `org/auth-edge` |
| _example-analytics-sdk_ | client-side instrumentation | `org/analytics-sdk` |

If every backend call goes through the BFF, the table is essentially one row — and that's correct. Resist listing the BFF's downstreams here; that's the BFF's job, not the frontend's.

## See also

- `docs/PROFILE.md` — full description of this repo's profile shape.
- `docs/PROMOTION.md` — when a local skill matures into a shared marketplace asset.
- Plugin design §4.3 / §5.2.
