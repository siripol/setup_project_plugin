# Hard rule — pdpa-compliance

This service handles PDPA-regulated personal data. Never paste PII (Thai NI, email, phone, credit card, passport) into the codebase except under allowlisted paths managed by `sn-setup policy pdpa allowlist`. Every file under `data/` MUST have a `<file>.meta.yaml` sidecar with `retention_days`, `data_subject`, `lawful_basis`, `data_categories`, `controller`, `last_reviewed`. See `.claude/docs/policies/pdpa-compliance.md`.
