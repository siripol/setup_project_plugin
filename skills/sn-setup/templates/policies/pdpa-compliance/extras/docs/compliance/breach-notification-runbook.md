# Breach Notification Runbook — ${name}

PDPA §37 requires notification of a personal-data breach to the regulator (PDPC) within **72 hours** and, when high-risk, to affected subjects without undue delay.

## Detect

Triggers that require this runbook:

- Suspected exfiltration (audit log shows external data egress).
- Lost device with personal data.
- Unauthorized access to `data/subjects/**` or `data/consents/**`.
- Third-party processor incident.
- Public exposure via misconfigured storage.

## Contain (≤ 2 hours)

1. Identify affected systems and revoke access.
2. Rotate credentials for the compromised access path.
3. Preserve forensic state (logs, snapshots).

## Assess (≤ 24 hours)

1. Scope: how many subjects, which categories.
2. Likelihood of harm.
3. Cross-reference incident with `data/consents/` to identify notification targets.

## Notify

| Audience | When | Required content |
|---|---|---|
| PDPC | ≤ 72 hours | Nature, categories, approximate number of subjects, likely consequences, measures taken |
| Affected subjects | Without undue delay (when high-risk) | Same as above, in plain language |
| Internal: legal + DPO | Immediately | Full incident details |
| Internal: security team | Immediately | Forensic snapshot, IoCs |

## Document

Record in `data/incidents/<YYYY-MM-DD>-<slug>.md`:

- Timeline (detect / contain / assess / notify timestamps).
- Decisions and decision-makers.
- Notification copies sent (with timestamps).
- Lessons-learned + remediation tasks.

## Practice

Run a tabletop exercise every 6 months. Last exercise: `<date>`.
