# Consent Records — ${name}

Consent records live at `data/consents/<subject-id>.yaml`. Each record proves a lawful basis for processing the subject's data.

## Record shape

```yaml
subject_id: <opaque ID>
subject_type: customer        # customer | employee | partner | vendor
collected_at: 2026-06-26T10:30:00Z
collected_via: web-checkout   # web-checkout | api | in-person | imported
lawful_basis: consent         # consent | contract | legal-obligation | vital-interest | public-task | legitimate-interest
purposes:
  - account-management
  - marketing-email
withdrawal_url: https://example.com/privacy/withdraw?token=...
expires_at: 2027-06-26T00:00:00Z
```

## Lookup

Process flow before any restricted-data write:

1. Compute consent-record path from subject ID.
2. Confirm it exists.
3. Confirm `purposes` includes the current operation.
4. Confirm `expires_at` is in the future.

The `pdpa-consent-check` hook (carved as **B2.5b** follow-up) automates step 1-4 at PreToolUse time.
