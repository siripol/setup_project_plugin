# Policy — Supply-chain scan

Two checkpoints:

1. **PreInstall hook** — runs before any `npm install`, `pip install`,
   `go get`, etc. Scans the lock-file diff for unknown deps.
2. **Pre-merge CI gate** — runs a vuln scanner on the lock-files; PR fails if
   any new HIGH/CRITICAL CVE appears.

Tools defaulted: `osv-scanner` (Go, Python, Node). Override per repo via
`.claude/config/supply-chain.yaml`.
