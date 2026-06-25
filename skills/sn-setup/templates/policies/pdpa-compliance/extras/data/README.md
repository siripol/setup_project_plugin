# `data/` — PDPA-tracked storage

Every file under this directory MUST have a sibling `<file>.meta.yaml` sidecar declaring its retention metadata. The `pdpa-retention-check` hook enforces this on PreToolUse Write.

## Sub-directories (created on apply)

- `subjects/` — Per-subject records keyed by opaque ID.
- `consents/` — Consent records (one YAML per subject ID); referenced by future B2.5b consent-check hook.
- `exports/` — Outbound data exports (SAR responses, regulator requests). Audit-logged via `audit-log-strict`.

## Adding a new data file

```
data/users.csv
data/users.csv.meta.yaml      # required sidecar
```

Sidecar shape: see `../docs/compliance/retention-policy-template.md`.

## What does NOT go here

- Application configuration → `config/` or `.claude/config/`.
- Test fixtures with synthetic PII → `test/fixtures/` (covered by the seeded PDPA allowlist).
- Non-PII artifacts (catalogs, public reference data) → `data/` is fine, sidecar still required.

## See also

- `../docs/compliance/data-classification-template.md`
- `../docs/compliance/retention-policy-template.md`
- `../docs/compliance/consent-records-template.md`
- `../.claude/docs/policies/pdpa-compliance.md`
