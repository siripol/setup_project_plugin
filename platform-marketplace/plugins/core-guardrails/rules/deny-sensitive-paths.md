# Rule: deny writes/edits to sensitive paths

Part of `core-guardrails` v1.0.0. Enforced via `permissions.deny[]` in `settings/settings.patch.json`.

## Paths covered

| Path | Reason |
|---|---|
| `/etc/**` | System config; mutation by an assistant is never an intended dev-loop action. |
| `/root/**` | Root user home; mutation implies privilege escalation or container-host confusion. |
| `~/.ssh/**` | SSH private keys + known_hosts. Mutation = key theft surface or trust-store tampering. |
| `~/.aws/**` | AWS credentials + config. Mutation = credential theft or boundary movement. |
| `~/.config/gcloud/**` | Google Cloud credentials. Same reason as AWS. |
| `~/.kube/**` | Kubernetes credentials + cluster context. Mutation = cluster compromise surface. |
| `~/.docker/**` | Docker registry credentials. Mutation = registry-auth theft. |
| `~/.netrc` | Legacy HTTP credentials file. Still consumed by curl, git, etc. |
| `~/.pgpass` | PostgreSQL credentials. |
| `**/.env` and `**/.env.*` | Environment-variable secret files; convention is one-per-repo at repo root, but pattern catches nested cases too. |

## Threat model

An assistant or workflow that gets a deceptive prompt (or has a misconfigured agent) might attempt to read AND write these paths to either exfiltrate credentials or install backdoors (e.g. adding an SSH key to `~/.ssh/authorized_keys`). Read-side is harder to block — the assistant has reason to read its own `.env` for debugging. Write-side is the chokepoint: legitimate workflows do not need to write or edit these paths during a session.

## Why these specific patterns

- `~/` patterns vs absolute: Claude Code respects the consumer's `$HOME`. Absolute `/etc` is the system path on Linux; `/root` is the root-user home (only meaningful in containers / privileged contexts but cheap to keep).
- `**/.env` covers both root-level and nested `.env` files (some monorepos).
- `**/.env.*` covers `.env.local`, `.env.production`, etc.

## What this does NOT cover

- Read-side access to credentials. Out of scope for this plugin; consider adding a `compliance-pack` policy if the service is regulated.
- Bash commands that mutate these paths via subprocess (e.g. `bash -c 'echo > ~/.ssh/foo'`). The Bash allowlist in this same patch handles the offensive surface separately by enumerating allowed commands.
- Network-level credential exfiltration. See [deny-network-exfil.md](deny-network-exfil.md).

## See also

- `platform-marketplace/docs/VERSIONING.md` — how this rule set evolves.
- Spec §7.2 (mandatory controls) — origin of the deny list.
