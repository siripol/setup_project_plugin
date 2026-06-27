# Security — ${name}

**This doc is the baseline.** Controls every service inherits, with the reasoning from real incident classes that motivated each one. For PDPA-specific controls applied when the `pdpa-compliance` policy is on (Hook A PII scan, Hook B retention sidecar, allowlist CLI, compliance doc templates), see `docs/compliance/data-classification-template.md` and its siblings — those are the operational PDPA pack and they sit beside this file in scaffolds that applied B2.5.

Read this if you are reviewing security posture, evaluating a new plugin, or writing a postmortem.

## Baseline controls

Every scaffolded service starts with the following enforcement layer, populated by the policy catalog and the platform's mandatory plugins:

| Control | Plugin / hook | What it does |
|---|---|---|
| Audit log | `audit-log-strict` policy + `audit.sh` PostToolUse hook | Every Claude tool call writes a JSONL line to `.sn-init/logs/`. Payloads spilling 2 KB go to `blobs/`. Cannot be disabled in regulated repos. |
| Secret scan | `secret-scan` policy + `secret-scan.sh` PreToolUse hook | Blocks `Write`/`Edit` whose content matches secret-shaped patterns (AWS keys, private keys, JWT tokens, bearer headers). |
| Supply-chain scan | `supply-chain-scan` policy + dependabot integration | Pre-merge check that no dependency in lockfiles matches a known-bad CVE list. Default for regulated profiles. |
| Chokepoint gate | `core-guardrails` plugin's `chokepoint-gate.sh` PreToolUse hook | Rate-limit + circuit-breaker: 200 calls / hour, 2M tokens / hour, 5 same-error → 5 min cooldown. |
| Permission boundary | `.claude/settings.json::permissions` block + plugin hook list | Explicit allow/deny rules per tool. Deny by default for `Bash(rm -rf /)` and similar destructive shapes. |
| Commit-msg gate | `.githooks/commit-msg` | Strips `Co-Authored-By: Claude` lines, enforces `Author:` trailer, blocks commits without one. |

The `core-guardrails` plugin from the Layer-1 marketplace ships the enforcement set as a single installable bundle. `core-workflow` from the same marketplace ships the advisory complement (spec-loop discipline, write-test-first skill). Together they make up the mandatory plugin pair.

## Reasoning from real incident classes

Each baseline control exists because of an incident class that recurs across orgs. Brief catalog:

| Incident class | Example | Mitigation in baseline |
|---|---|---|
| Leaked secret in git history | AWS access key committed to a config file; published to a public repo; auto-scraped within minutes; compromised account before rotation. | `secret-scan` hook catches the write before the file lands. `.gitignore` defaults exclude `.env`, `*.key`, `credentials.json`. |
| Supply-chain compromise | Transitive dep on a popular npm package gets a malicious update; downstream service runs it next deploy. | `supply-chain-scan` pre-merge check; pinning to concrete versions in `installed_plugins`; CVE feed integration. |
| Audit-log opt-out hides misuse | Engineer disables audit log "to debug a flaky test"; never re-enables; misuse goes unnoticed. | `audit-log-strict` policy in regulated repos cannot be disabled at runtime; opt-out only at scaffold via explicit `--no-audit-log` (blocked for regulated). |
| Prompt-injected Claude session | External user submits content that overrides system instructions; assistant exfiltrates context. | Chokepoint gate rate-limits + circuit-breaks; PostToolUse audit catches the exfil tool call; `security-auditor` subagent reviews diffs for AuthZ regressions. |
| PDPA breach via training data | Training data scraped from logs contains regulated personal data; data subject discovers it; org faces fine. | `memory-regulated` policy blocks auto-memory writes; PDPA pack (B2.5) adds Hook A PII scan + Hook B retention sidecar. |
| Permission bypass | Engineer adds `--dangerously-skip-permissions` to a debug script; script lands in CI; entire permission system bypassed. | CI's `Block --dangerously-skip-permissions` step greps every push + PR; `GOVERNANCE-SERVICE-LEVEL.md` documents the policy. |

This is not a complete threat catalog. It is the set of incident shapes the baseline directly addresses. Specialized incidents (network/host-level intrusion, social engineering of operators, insider threats with full repo write access) are out of scope here — they belong to the standard infosec stack, the org training programme, and HR processes respectively.

## Pinning policy

Every plugin in `.claude/settings.json::installed_plugins` is pinned to a concrete version. No tags, no ranges, no `latest`. CI verifies this on every push.

Why pinning matters: an unpinned plugin can break or compromise a service silently when its upstream ships a new version. Pinning makes every change explicit, reviewable, and rollbackable.

For dependencies (the lang-level `requirements.txt` / `package.json` / `go.mod`): same policy. Lockfiles must be committed. `dependabot` opens PRs on out-of-date dependencies, including security updates.

## Update process

### Quarterly review

Every quarter the service team reviews its pinned plugin versions:

1. Read the marketplace changelog since the last review.
2. Identify versions with breaking changes; schedule a PR per breaking change.
3. Apply non-breaking updates in one PR (low risk, fast review).
4. Run the full test suite + smoke tests against staging.

### Out-of-cycle update (CVE-driven)

When a CVE lands on a pinned plugin's dependency tree:

1. Dependabot opens a PR with the upgrade.
2. The `security-auditor` subagent reviews the diff (if installed; default for regulated repos).
3. CODEOWNERS reviews the diff and the CVE description.
4. Merge, deploy to staging, smoke-test, deploy to production.
5. Document the update in `CHANGELOG.md`.

For CVEs on the underlying language runtime, container base image, or OS package: same process driven by image-scanner output instead of dependabot.

## Threat model boundary

What is **in scope** for this baseline:

- Claude session-level threats: prompt injection, tool misuse, secret leak via output.
- Repo-level supply-chain: dependency CVEs, plugin compromise.
- Local enforcement: hooks, permission boundary, audit log.
- Commit-time integrity: signed-off-by, author trailer, no co-author lines.

What is **out of scope** (left to other teams / processes):

- Network and host-level threats: firewalls, IDS, container escape — standard infosec stack.
- Social engineering of human operators — org training and phishing simulations.
- Insider threats with full repo write access — HR processes and access reviews.
- Compromise of upstream tooling (Anthropic API itself, GitHub, the package registries) — vendor responsibility plus disaster-recovery planning.

These boundaries matter because they tell you when to escalate vs when to handle in-repo.

## Escalation

When to page org security:

- Pinned plugin shows evidence of compromise (unexpected behavior, surprising network calls, unexplained file writes).
- Secret has actually leaked (not just blocked at write time). Rotate immediately, then file the postmortem.
- Audit log shows a pattern of misuse across multiple sessions (large volumes of regulated reads, attempts to disable hooks, repeated `--dangerously-skip-permissions` greps in PRs).
- Compliance violation (regulated data in non-regulated repo, retention sidecar staleness exceeded).

Org security's contact path is documented separately in the org's incident-response runbook (not in this repo). If you are not sure, page anyway — false-positive escalations cost a meeting; missed escalations cost the org.

## See also

- `GOVERNANCE.md` — the two-tier memory policy and pinning policy this doc implements.
- `GOVERNANCE-SERVICE-LEVEL.md` — the `--dangerously-skip-permissions` policy and CI block this doc references.
- `docs/compliance/*` — PDPA-specific controls when the `pdpa-compliance` policy is applied (B2.5).
