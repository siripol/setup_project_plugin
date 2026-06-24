# Policy — Secret scan

Two checkpoints:

1. **PreToolUse on Write/Edit** — scans the new content for high-entropy
   strings + known token shapes (AWS, GCP, GH, Slack, Stripe, JWT). Blocks
   on match.
2. **Pre-commit** — scans the staged diff. Blocks the commit on match.

Default scanner: `gitleaks`. Repo can override via `.claude/config/secret-scan.yaml`.
