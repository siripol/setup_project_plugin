# Policy — Audit log: strict

Every Claude tool call is appended to `.sn-init/logs/exec-<date>-<session>.jsonl`
with the full request + response payloads. No blob spill; the JSONL line
contains everything.

## Format

Single JSON object per line. Required keys: `timestamp`, `session`, `tool`,
`request`, `response`, `duration_ms`. Optional: `error`, `metadata`.

## Cost

Larger logs and slightly higher disk IO. Acceptable for regulated services
where reproducibility outranks throughput.
