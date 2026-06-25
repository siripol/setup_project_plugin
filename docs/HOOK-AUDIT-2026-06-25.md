# Hook Audit — 2026-06-25

REQ-SEC-001 (B1.7). Audits the scaffold's `.claude/settings.json` + `.claude/hooks/*` + `templates/managed-agent-base/scripts/safety.py` against the design doc's **§7.2 mandatory controls** for the `core-guardrails` layer.

Method: read-and-tick. PASS = control covered today. FAIL = gap. PARTIAL = covered conditionally (opt-in flag, etc.). N-A = depends on infra not yet stood up.

## Summary

| # | Control | Verdict |
|---|---|---|
| 1 | Sensitive-path deny rules | **FAIL → fixed in this PR** |
| 2 | Network-command restriction | **PASS** (by allow-list design) |
| 3 | Marketplace allow-list | **N-A** — depends on B2.3 marketplace consumer |
| 4 | No automatic permission bypass | **PARTIAL → carved as B1.7a** |
| 5 | Supply-chain scan | **PASS** via catalog policy `supply-chain-scan` |
| 6 | In-session security review | **PARTIAL → carved as B1.7b** |
| 7 | Audit log | **PASS** via default hooks + catalog `audit-log-strict` policy |

3 PASS, 2 PARTIAL (carved), 1 FAIL (fixed in PR), 1 N-A.

## Per-control detail

### 1. Sensitive-path deny rules — FAIL → fixed

**Before**: `templates/claude/settings.json` `permissions.deny` is `[]`. No hook blocks writes under `~/.ssh/`, `/etc/`, credential files, `.env*`, or system-level paths.

**Risk**: Claude could write to a credential dir if the user accidentally allowed `Write(*)`. The chokepoint hook only fires for files listed in `.harness/chokepoints.yaml` (per-project), which doesn't cover OS-level sensitive paths.

**Fix (this PR)**: Add a default deny list to `settings.json`:

```json
"deny": [
  "Write(/etc/**)",
  "Write(/root/**)",
  "Write(~/.ssh/**)",
  "Write(~/.aws/**)",
  "Write(~/.config/gcloud/**)",
  "Write(~/.kube/**)",
  "Write(~/.docker/**)",
  "Write(~/.netrc)",
  "Write(~/.pgpass)",
  "Write(**/.env)",
  "Write(**/.env.*)",
  "Edit(/etc/**)",
  "Edit(/root/**)",
  "Edit(~/.ssh/**)",
  "Edit(~/.aws/**)",
  "Edit(~/.config/gcloud/**)",
  "Edit(~/.kube/**)",
  "Edit(~/.docker/**)",
  "Edit(~/.netrc)",
  "Edit(~/.pgpass)",
  "Edit(**/.env)",
  "Edit(**/.env.*)"
]
```

**Verdict after fix**: PASS.

### 2. Network-command restriction — PASS

**Method**: settings.json `permissions.allow` lists explicit Bash patterns (`Bash(git status:*)`, `Bash(go test:*)`, etc.). Any Bash command NOT on the allow list prompts the user. No bare `curl` / `wget` / `nc` allowed.

**Verdict**: PASS by design. Could be tightened by adding explicit `Bash(curl:*)` deny, but the allow-list already covers the floor.

### 3. Marketplace allow-list — N-A

**Status**: No marketplace consumer wired yet. Backlog item **B2.3** introduces `--marketplace=<source>` + `.claude-plugin/marketplace.json` consumer side. Until then, plugins install ad-hoc.

**When B2.3 lands**: this control becomes enforceable via the marketplace's signed-plugin verification.

### 4. No automatic permission bypass — PARTIAL → B1.7a

**Method**: chokepoint-gate hook blocks Edit/Write to paths listed in `.harness/chokepoints.yaml`. Rate-limit hook caps per-hour calls + tokens. Neither prevents the user from passing `--dangerously-skip-permissions` to the Claude Code CLI.

**Gap**: The flag bypasses the entire permission system at the harness layer, before hooks ever fire.

**Fix path**: This is a CI/team-policy concern, not a hook concern. The plugin can't directly block a user CLI flag. Recommended:

- Add a `pre-receive` git hook (or CI check) that scans repo history for invocations including the dangerous flag.
- Document the prohibition in `docs/GOVERNANCE-SERVICE-LEVEL.md` (shipped in PR #20) and link to org's security policy.

**Carved as B1.7a** — separate item; scope is "ship CI / docs guidance to discourage `--dangerously-skip-permissions`".

### 5. Supply-chain scan — PASS via policy

**Method**: The catalog policy `supply-chain-scan` (shipped in PR #18) drops a `PreToolUse` hook on Bash `(npm install|pip install|go get|cargo add)` patterns that runs `osv-scanner`. Default microservice / bff profile bundles include it.

**Verdict**: PASS. Default scaffolds get supply-chain coverage automatically. Regulated services additionally apply `audit-log-strict` for full-payload logging of dep installs.

### 6. In-session security review — PARTIAL → B1.7b

**Method**: `security-auditor` subagent ships in `OPTIONAL_SUBAGENTS` (not the default set). Spec-loop workflow includes the `sn-adversary` subagent (broader than security; tests invariants, edge cases, attack surface).

**Gap**: Without explicit `--subagents=security-auditor` (or `all`), the security review subagent isn't installed. The adversary fills part of the role but isn't security-focused.

**Fix path**:
- Promote `security-auditor` from optional to a recommended-default for regulated profiles.
- Document the recommendation in `docs/GOVERNANCE-SERVICE-LEVEL.md`.

**Carved as B1.7b** — separate item; scope is "make security-auditor default for regulated profiles + document recommendation".

### 7. Audit log — PASS

**Method**: `templates/claude/settings.json` registers `audit.sh` on PreToolUse, PostToolUse, UserPromptSubmit, SessionStart, SessionEnd, and Stop. Writes JSONL to `.sn-init/logs/exec-<date>-<session>.jsonl` with > 2 KB payload spill to `blobs/<sha256-prefix>.txt` (per CHANGELOG 1.0.0 frozen API).

Regulated services additionally apply the catalog's `audit-log-strict` policy which forces full-payload entries (no spill).

**Verdict**: PASS. The audit-log feature is a frozen 1.x public API surface.

## In-scope fix shipped in this PR

- Control 1: sensitive-path deny patterns added to `templates/claude/settings.json`.

## Out-of-scope follow-ups

| ID | Scope |
|---|---|
| **B1.7a** | CI / docs guidance against `--dangerously-skip-permissions`. |
| **B1.7b** | Make `security-auditor` default for regulated profiles + document. |

Both are added to `docs/backlog.md` under Tier 1.

## Files inspected

- `skills/sn-setup/templates/claude/settings.json`
- `skills/sn-setup/templates/claude/hooks/{audit,chokepoint-gate,rate-limit}.{sh,py,ts}`
- `skills/sn-setup/templates/claude/hooks/README.md`
- `skills/sn-setup/templates/managed-agent-base/scripts/safety.py`
- `skills/sn-setup/templates/policies/supply-chain-scan/*`
- `skills/sn-setup/templates/policies/audit-log-strict/*`

## See also

- Plugin design `§7.2` + Principle 1 — source list of mandatory controls.
- `docs/superpowers/specs/2026-06-24-policy-catalog-design.md` — supply-chain-scan + audit-log-strict policies.
- `<vault>/projects/setup_project_plugin/requirements/tier1-finish.md` — combined REQ-CTX-001 + REQ-SEC-001 requirements.
