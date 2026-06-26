# Retention Policy — ${name}

Per-category retention windows. Every data file under `data/` requires a `.meta.yaml` sidecar referencing one of these categories.

| Category | Retention | Disposal | Lawful basis |
|---|---|---|---|
| PII Identity | 7 years post-last-interaction | crypto-shred | contract |
| PII Contact | 3 years post-last-interaction | overwrite | contract |
| PII Behavioral | 90 days | delete | legitimate-interest |
| Financial | 7 years (statutory) | crypto-shred | legal-obligation |

## Sidecar shape

```yaml
retention_days: 365
data_subject: customer
lawful_basis: contract
data_categories: [name, email, phone]
controller: orders-team
last_reviewed: 2026-06-26
```

## Review cadence

Each row in the table above is reviewed every 12 months. `last_reviewed:` on each sidecar must be within the last 365 days; the `pdpa-retention-check` hook does not enforce review staleness today (track via `B2.5a` follow-up if needed).
