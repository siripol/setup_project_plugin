# Observability — ${name}

Defaults every microservice ships from day one. Tune per environment, never drop.

## Three pillars

### Logs

- Structured JSON. One event per line.
- Required fields: `timestamp` (RFC3339), `level`, `service`, `trace_id`, `message`.
- Levels: `debug`, `info`, `warn`, `error`. `info` is the production default.
- Never log secrets, tokens, PII, or full request bodies for endpoints that carry user data.
- Local dev may use pretty/console formatting; production is always JSON.

### Metrics

Minimum set, emitted via Prometheus or the org's preferred sink:

| Metric | Type | Labels |
|---|---|---|
| `http_requests_total` | counter | method, path, status |
| `http_request_duration_seconds` | histogram | method, path, status |
| `dependency_call_duration_seconds` | histogram | dependency, op, outcome |
| `inflight_requests` | gauge | — |
| `build_info` | gauge | version, commit, lang |

Add domain metrics (e.g. `orders_placed_total`) as the service grows; keep cardinality bounded.

### Traces

- OpenTelemetry SDK, OTLP exporter to the org's collector.
- Auto-instrument the HTTP server, the DB driver, and outbound HTTP/gRPC clients.
- Every span carries `service.name=${name}`, `service.version`, `deployment.environment`.
- Propagate `traceparent` headers on every outbound call.

## Health endpoints

| Path | Returns |
|---|---|
| `GET /healthz` | 200 if the process is up. No dependency checks. |
| `GET /readyz` | 200 only if all required dependencies (DB, queues, downstream services) are reachable. |
| `GET /metrics` | Prometheus exposition format. |

## Dashboards & alerts

- Each service ships a default dashboard JSON under `ops/dashboards/`.
- Critical SLO alerts: `error_rate > 1%` over 5m, `p99_latency > SLO` over 5m.
- Page criteria live in `docs/RUNBOOK.md` (add it before the first production deploy).
