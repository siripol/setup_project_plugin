# Policy — PDPA compliance (full enforcement)

Full enforcement layer for services handling personal data subject to Thailand's PDPA. Pairs with the regulated-data baseline (`memory-regulated` + `audit-log-strict` + `secret-scan`).

## What this enforces

### PII pattern scan (Hook A)

`.claude/hooks/pdpa-data-handler-scan.sh` runs on every `Write` and `Edit`. Blocks the write (exit 2) when payload contains any of:

- Thai NI 13-digit numbers (`\b[0-9]{13}\b`).
- Email addresses.
- Thai mobile / landline numbers (`(0|66)…`).
- Credit-card PAN shapes (4-4-4-4 / 4-4-4-1 patterns).
- Passport-shaped IDs (`[A-Z]{1,2}[0-9]{6,9}`).

The hook skips paths matching globs in `.claude/config/pdpa-allowlist.yaml`. Manage exemptions with:

```bash
sn-setup policy pdpa allowlist list
sn-setup policy pdpa allowlist add "test/fixtures/**"
sn-setup policy pdpa allowlist remove "test/fixtures/**"
sn-setup policy pdpa allowlist explain "test/fixtures/sample.md"
```

### Retention sidecar (Hook B)

`.claude/hooks/pdpa-retention-check.sh` runs on every `Write` whose target is under `data/`. Blocks (exit 2) when the file lacks a sibling `<file>.meta.yaml` sidecar with six required keys:

```yaml
retention_days: 365
data_subject: customer
lawful_basis: contract          # consent | contract | legal-obligation | vital-interest | public-task | legitimate-interest
data_categories: [name, email, phone]
controller: orders-team
last_reviewed: 2026-06-26
```

The template is `docs/compliance/retention-policy-template.md`.

## Scaffolded structure

`data/` dirs ship with `.gitkeep` so they exist on first scaffold:

```
data/
  README.md
  subjects/.gitkeep
  consents/.gitkeep
  exports/.gitkeep
```

Doc templates land under `docs/compliance/`:

- `data-classification-template.md` — per-category classification table.
- `retention-policy-template.md` — sidecar shape + per-category windows.
- `consent-records-template.md` — consent YAML shape + lookup flow.
- `breach-notification-runbook.md` — PDPA §37 detect/contain/assess/notify.

## Carved follow-ups

- B2.5a: review-staleness enforcement (≤ 365 days on `last_reviewed:`).
- B2.5b: consent-check hook (`pdpa-consent-check.sh`).
- B2.5c: audit-log breach-detection rules (cross-policy with `audit-log-strict`).
- B2.5d: CI auto-rotate `last_reviewed:` on PR approval.
- B2.5e: Luhn validation for PAN regex.

## See also

- `docs/compliance/data-classification-template.md`
- `docs/compliance/retention-policy-template.md`
- `docs/compliance/consent-records-template.md`
- `docs/compliance/breach-notification-runbook.md`
- Plugin design §8.
