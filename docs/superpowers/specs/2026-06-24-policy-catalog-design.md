# Policy Catalog — Design Spec

| Field | Value |
|---|---|
| Date | 2026-06-24 |
| Author | brainstorming session (Siripol + Claude) |
| Status | Draft — awaiting user review |
| Branch | `feat/ecosystem-memory-policy` (will be repurposed as `feat/policy-catalog`) |
| Supersedes | Backlog items **B1.1** (Repository Ecosystem table) + **B1.2** (two-tier memory policy) |
| Decomposed from | Three-PR sequence **D1**: PR1 = this spec; PR2 = profile expansion (worker / cli / library / gateway / mcp-server); PR3 = default bundles for the new profiles |
| Source design | `temp/__claude__microservices-template-design_20260623133500.md` §§ 4.3, 5.2, 5.3, 3.5#4, 7.5, 7.2 |

---

## 0. Summary

The scaffolder gains a **catalog of composable, versioned, layered policies** that can be applied to or removed from any scaffolded project. Each policy ships:

1. A one-line row injected into a `## Policies` table in `CLAUDE.md` (always-on, ~10 tokens).
2. Optional always-on **rule** under `.claude/rules/<slug>.md` (≤ 50 tokens; only for must-fire-every-turn rules).
3. **Full body** under `.claude/docs/policies/<slug>.md` (load-on-demand; 0 baseline tokens).
4. Optional **`settings.json` patch** merged into `.claude/settings.json` (hook layer; 0 context cost).
5. Optional **extra files** copied verbatim into the project.

State of the world is recorded in `.sn-init-state.json` under `applied_policies` (current) + `policy_history` (append-only audit log).

Two new CLI sub-trees:

- `sn-setup policy <list|show|apply|remove|upgrade|status|show-applied|history|lint>` — operate on the current project.
- `sn-setup profile <list|show|add|remove|swap>` — manage profile→default-policies mapping (auto-detect: plugin source vs project-local).

Day-one catalog ships **9 policies** spanning security, conventions, workflow, observability. Profile-bundled defaults pre-apply a sensible subset for each of the three existing profiles (`microservice`, `bff`, `frontend`).

---

## 1. Architecture

```
                              CATALOG  (templates/policies/<slug>/)
                             ┌──────────────────────────────────────┐
                             │ policy.yaml    (metadata + version)  │
                             │ claude-md.row.md  ─┐                 │
                             │ rules/<slug>.md    │  always-on tier │
                             │ docs/<slug>.md     │  on-demand tier │
                             │ settings.patch.json│  hook-layer     │
                             │ extras/...         │  optional files │
                             └────────┬─────────────────────────────┘
                                      │ apply
                                      ▼
                              SCAFFOLDED PROJECT
                             ┌──────────────────────────────────────┐
                             │ CLAUDE.md (## Policies table row)    │
                             │ .claude/rules/<slug>.md              │
                             │ .claude/docs/policies/<slug>.md      │
                             │ .claude/settings.json (merged entry) │
                             │ .sn-init-state.json (applied + log)  │
                             └──────────────────────────────────────┘
```

### Token-economy guarantee

Per session, after applying 5 policies, the always-loaded surface added by the catalog is:

| Surface | Cost |
|---|---|
| Table rows in CLAUDE.md | ~50 tokens always-on |
| `.claude/rules/*.md` | ≤ 50 tokens each, only when policy declares a rule |
| `.claude/docs/policies/*.md` | 0 baseline (read on demand) |
| `.claude/settings.json` | 0 (parsed in hook layer, not prompt context) |

The rest of policy detail loads only when:
- the user asks ("what's our memory policy?");
- a skill description matches;
- a hook fires and reads the doc to compose its deny/warn message;
- Claude touches a topic governed by the policy.

### Lifecycle

The catalog ships in the plugin. `sn-setup policy apply` writes selected policies to the project. `sn-setup policy upgrade` re-applies at the catalog's newer version. `sn-setup policy remove` reverses. All operations are idempotent, atomic, and recorded in append-only history.

---

## 2. Components

### Per-policy directory

```
skills/sn-setup/templates/policies/<slug>/
  policy.yaml                # required: metadata + version + layer flags
  claude-md.row.md           # required: ONE table row to inject into CLAUDE.md
  docs/<slug>.md             # required: full body (load-on-demand)
  rules/<slug>.md            # optional: tiny always-on rule
  settings.patch.json        # optional: hook/settings additions
  extras/                    # optional: any files copied as-is to project
    hooks/<slug>.sh          # → .claude/hooks/<slug>.sh (chmod +x on apply)
    docs/<human-readable>.md # → docs/<human-readable>.md
```

### `policy.yaml` schema

```yaml
slug: memory-regulated                # unique key; lowercase-hyphen
title: "Memory: regulated (auto-memory off)"
version: 1.0.0                        # semver; bumped on any content change
category: security                    # security | conventions | workflow | observability
group: memory-tier                    # exclusive-group key; null if independent
applies_to: [microservice, bff, frontend]   # profiles that may apply this
requires: []                          # other slugs that must be present
conflicts_with: []                    # other slugs that block this
description: |
  Auto-memory disabled. All context must be committed. Pairs with --compliance=pdpa.
files:                                # explicit file manifest
  claude_md_row: claude-md.row.md
  docs: docs/memory-regulated.md
  rules: rules/memory-regulated.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/memory-regulated.sh:.claude/hooks/memory-regulated.sh
```

`extras` list format is `<src>:<dst>` where `src` is relative to the policy directory and `dst` is relative to the project root. Catalog lint rejects paths containing `:` outside the separator.

### Layer rules

| File | Always-on? | Tokens | Use when |
|---|---|---|---|
| `claude-md.row.md` | ✓ (table row in CLAUDE.md) | ~10 | Always — every policy has one |
| `rules/<slug>.md` | ✓ (in `.claude/rules/`) | ≤ 50 | Hard rule Claude must obey every turn |
| `docs/<slug>.md` | — (Read on demand) | 0 baseline | Full policy text, examples, exceptions |
| `settings.patch.json` | — (hook layer) | 0 | Enforce via hook (deny / transform / log) |
| `extras/` | — | 0 | Shipped files (hook scripts, docs, configs) |

### `claude-md.row.md` format

ONE markdown line, no header:

```markdown
| memory | regulated | `.claude/docs/policies/memory-regulated.md` | 1.0.0 |
```

Columns: `category | slug | reference | version`. Concatenated into the `## Policies` table managed by sn-setup. Apply detects existing row by slug column and replaces (for upgrade) or skips (for re-apply at same version).

### `settings.patch.json` format

Every entry carries `policy: <slug>` marker for reversibility:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "policy": "memory-regulated",
        "version": "1.0.0",
        "matcher": "Write",
        "pattern": "(~/.claude/memory/|\\.claude/local-memory/)",
        "command": ".claude/hooks/memory-regulated.sh"
      }
    ]
  }
}
```

Removal walks `.claude/settings.json` arrays and strips entries where `policy == <slug>`. Object keys (non-array) are deep-merged on apply and left alone on remove (a policy may not own a top-level config key cleanly).

---

## 3. Catalog content (9 policies day-1)

| # | Slug | Group | Cat | Rule? | Settings patch? | What it ships |
|---|---|---|---|---|---|---|
| 1 | `memory-ordinary` | `memory-tier` | security | tiny | — | Auto-memory permitted; promote learnings to commit via PR |
| 2 | `memory-regulated` | `memory-tier` | security | tiny | ✓ deny write to memory dirs | Auto-memory off; commit-only context |
| 3 | `repository-ecosystem` | — | conventions | — | — | Cross-service table doc; row in `## Policies` table points at it |
| 4 | `audit-log-strict` | — | observability | — | ✓ force all calls to JSONL log; no payload spill | Full-payload audit log |
| 5 | `supply-chain-scan` | — | security | — | ✓ PreCommit + pre-merge: scan deps | Block install of unscanned deps |
| 6 | `secret-scan` | — | security | tiny | ✓ PreToolUse: scan Write/Edit content; PreCommit: scan staged diff | Block commit/write of secrets |
| 7 | `commit-msg-gate` | — | workflow | — | ✓ wraps existing `.githooks/commit-msg` | Enforce REQ-NNN / conventional-commit subject |
| 8 | `branch-naming` | — | workflow | — | ✓ pre-push hook | Enforce `feat/* fix/* chore/* docs/*` prefixes |
| 9 | `pdpa-compliance` | — | security | tiny | ✓ requires `memory-regulated` + `audit-log-strict` + `secret-scan` | Signal only in v1; full pack = B2.5 |

### Group rules

- `memory-tier`: `memory-ordinary` XOR `memory-regulated` — at most one applied at a time. Apply auto-swaps with warn (see §7).
- All other policies are independent and may co-apply.

### Cross-policy requirements

`pdpa-compliance` requires `memory-regulated`, `audit-log-strict`, `secret-scan`. Apply auto-installs deps with `--with-deps`; otherwise errors with exit 13 and lists the missing slugs.

### Default profile bundles (PR1 scope, 3 existing profiles)

```yaml
# templates/profile/microservice/default_policies.yaml
policies:
  - repository-ecosystem
  - memory-ordinary
  - audit-log-strict
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate

# templates/profile/bff/default_policies.yaml
policies:
  - repository-ecosystem
  - memory-ordinary
  - audit-log-strict
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate

# templates/profile/frontend/default_policies.yaml
policies:
  - repository-ecosystem
  - memory-ordinary
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate
  - branch-naming
```

---

## 4. CLI surface

### `sn-setup policy` — project-level ops

```bash
# Catalog inspection
sn-setup policy list                           # all 9 with version + group + category
sn-setup policy list --category=security       # filter
sn-setup policy show memory-regulated          # metadata + section preview + file list

# Apply to current project
sn-setup policy apply <slug>...                # 1+ slugs; idempotent; auto-swaps exclusive group with warn
sn-setup policy apply memory-regulated repository-ecosystem
sn-setup policy apply --use-profile-defaults   # apply the project's profile-bundled set (idempotent)
sn-setup policy apply --with-deps memory-regulated   # also installs required deps

# Remove
sn-setup policy remove <slug>...               # warn + skip user-edited files
sn-setup policy remove --force <slug>          # delete even if edited

# Status / drift
sn-setup policy show-applied                   # current applied set (slug + version + content_sha state)
sn-setup policy status                         # diff vs catalog: current / obsolete / unknown / drifted

# Upgrade
sn-setup policy upgrade <slug>                 # re-apply at current catalog version (skip user-edited unless --force)
sn-setup policy upgrade --all                  # upgrade every obsolete one
sn-setup policy upgrade --dry-run --all        # preview

# History
sn-setup policy history                        # tail the policy_history audit log
sn-setup policy history --slug=memory-regulated --limit=20

# Lint catalog (CI-friendly)
sn-setup policy lint                           # validates every policy.yaml + manifest + cross-refs
```

### `sn-setup profile` — default bundle ops

Auto-detects cwd:
- `.claude-plugin/plugin.json` present → edits `skills/sn-setup/templates/profile/<P>/default_policies.yaml` (plugin source; affects future scaffolds).
- `.sn-init-state.json` present → edits `.claude/profile-defaults.yaml` (project-local copy; affects re-application).
- Neither → error (exit 15).
- Both → error unless `--target=plugin|project`.

```bash
sn-setup profile list                                          # all profiles + their defaults
sn-setup profile show microservice                             # one profile's defaults
sn-setup profile add branch-naming --profile=microservice      # validate slug; dedup; write
sn-setup profile remove audit-log-strict --profile=microservice
sn-setup profile swap --profile=microservice memory-ordinary memory-regulated
```

### `sn-setup` — scaffold extensions

```bash
# Default — profile defaults auto-applied
sn-setup demo --profile=microservice

# Replace defaults entirely
sn-setup demo --policies=memory-regulated,secret-scan

# Delta against defaults
sn-setup demo --add-policies=branch-naming --remove-policies=audit-log-strict

# Combining replace + delta = usage error
sn-setup demo --policies=foo --add-policies=bar
# → exit 17 with "--policies replaces the default set; --add/--remove cannot combine with it"
```

---

## 5. Data flow

### Apply

```
1. Load catalog: parse policy.yaml from templates/policies/<slug>/
2. Validate:
   a. slug exists                  → else exit 10
   b. profile applies               → else error "policy '<slug>' not for profile=<P>"
   c. requires satisfied            → else error 13 or auto-install (--with-deps)
   d. conflicts_with absent         → else error
   e. exclusive group               → if filled, plan auto-swap
3. Load project state (.sn-init-state.json) + existing CLAUDE.md + settings.json
4. For each new slug:
   a. If exclusive-swap planned: queue remove-then-add
   b. Append/replace row in CLAUDE.md ## Policies table (idempotent: match by slug column)
   c. Write .claude/docs/policies/<slug>.md       (skip if exists; never overwrite)
   d. Write .claude/rules/<slug>.md (if present)  (skip if exists)
   e. Copy extras/* paths per manifest             (skip if exists; chmod +x for *.sh)
   f. Merge settings.patch.json into .claude/settings.json (see §8)
   g. Record content_sha of every written file (for later drift detection)
5. Update state:
   a. applied_policies += {slug, version, applied_at, content_sha, settings_marker}
   b. policy_history += {action: "apply", slug, version, at, source}
6. Atomic write: state file written via tmp+rename
7. Print summary
```

### Remove

```
1. Load state; verify slug in applied_policies → else exit 16
2. For each file in policy manifest:
   a. Compute current sha vs state.content_sha
   b. unedited (equal) → delete
   c. edited (diff) AND no --force → warn + skip
   d. edited AND --force → delete anyway
3. Strip row from CLAUDE.md ## Policies table by slug column
4. Strip entries from .claude/settings.json arrays where policy == slug
5. Update state:
   a. applied_policies -= entry
   b. policy_history += {action: "remove", slug, at, skipped_files}
6. Print summary
```

### Upgrade

```
1. Load state; verify slug in applied_policies → else exit 16
2. Compare state.version vs catalog policy.yaml version
   a. equal → no-op message, exit 0
   b. catalog newer → proceed
   c. state newer → exit 18 "applied <v_state> > catalog <v_catalog>"
3. For each file:
   a. unedited → overwrite with new template content; record new sha
   b. edited → warn + skip + record in skipped_files (unless --force)
4. Re-merge settings.patch.json (replaces by (matcher, policy) tuple; updates version)
5. Update state:
   a. applied_policies entry: version, applied_at, content_sha refreshed
   b. policy_history += {action: "upgrade", slug, from, to, at, skipped_files}
6. Print summary
```

### Status

```
1. Load state.applied_policies
2. For each entry:
   a. Look up catalog policy.yaml
   b. version match?           → ✓ current
   c. catalog newer?           → ⚠ obsolete (catalog v vs applied v)
   d. catalog unknown?         → ✗ unknown (plugin downgraded or slug removed)
   e. file content_sha diff?   → ◆ drifted (user-edited since apply)
3. Print table
```

---

## 6. State shape

Additions to `.sn-init-state.json`:

```json
{
  "applied_policies": [
    {
      "slug": "memory-ordinary",
      "version": "1.0.0",
      "applied_at": "2026-06-24T03:15:21.842Z",
      "content_sha": {
        "CLAUDE.md#row:memory-ordinary": "abc123…",
        ".claude/rules/memory-ordinary.md": "def456…",
        ".claude/docs/policies/memory-ordinary.md": "789abc…"
      },
      "settings_marker": "memory-ordinary"
    }
  ],

  "policy_history": [
    {
      "action": "apply",
      "slug": "memory-ordinary",
      "version": "1.0.0",
      "at": "2026-06-24T03:15:21.842Z",
      "source": "profile-default"
    },
    {
      "action": "swap",
      "from": "memory-ordinary",
      "from_version": "1.0.0",
      "to": "memory-regulated",
      "to_version": "1.0.0",
      "at": "2026-06-24T05:42:10.001Z",
      "source": "cli"
    },
    {
      "action": "upgrade",
      "slug": "memory-regulated",
      "from": "1.0.0",
      "to": "1.2.0",
      "at": "2026-06-25T08:00:00.000Z",
      "skipped_files": [".claude/rules/memory-regulated.md"],
      "source": "cli"
    }
  ],

  "flags": {
    "profile": "microservice",
    "policies_source": "profile-default"
  }
}
```

### Field rules

- `applied_policies` — current state. List, sorted by slug for deterministic diff.
- `applied_policies[].content_sha` — keys are file paths; values are sha256 hex of the *applied* content. The synthetic key `CLAUDE.md#row:<slug>` represents the policy's table row inside `CLAUDE.md`, hashed in isolation from the rest of the file (so user edits to other parts of `CLAUDE.md` don't show up as drift for this policy).
- `applied_policies[].settings_marker` — the `policy:` value used in `.claude/settings.json`; null if policy has no settings patch.
- `policy_history` — append-only, ordered by `at`. Actions: `apply | remove | upgrade | swap`. Never trimmed.
- `policy_history[].source` — `profile-default | cli | scaffold-override | dependency-auto-install`.

### Migration for legacy scaffolds

On first `sn-setup policy *` invocation in a project missing these fields:
- Add empty `applied_policies: []` and empty `policy_history: []`.
- No retroactive scan — old projects start fresh.
- Print "migrated state to policy-catalog schema" notice.

---

## 7. Idempotency + edit-safety

### Definitions

| Term | Meaning |
|---|---|
| **template_sha** | sha256 of the file as it ships from the catalog at a given policy version |
| **applied_sha** | template_sha recorded in `state.applied_policies[<slug>].content_sha[<path>]` at apply time |
| **current_sha** | sha256 of the file as it exists on disk right now |
| **unedited** | `current_sha == applied_sha` |
| **edited** | `current_sha != applied_sha` |

### Per-operation truth table

| Op | File state | Behavior |
|---|---|---|
| `apply` | absent | Write template content; record applied_sha |
| `apply` | present, unedited | Idempotent: skip; log "already up-to-date" |
| `apply` | present, edited | Skip + warn (state for that file unchanged; continues to other files) |
| `remove` | unedited | Delete; state strips entry |
| `remove` | edited | Skip + warn unless `--force`; `--force` → delete; `skipped_files` recorded |
| `remove` | missing | Skip; state strips entry |
| `upgrade` | unedited | Overwrite; refresh applied_sha + version |
| `upgrade` | edited | Skip + warn unless `--force`; `--force` → overwrite; state version still bumps |
| `upgrade` | missing | Treat as fresh apply for that file |

### CLAUDE.md table row idempotency

Row format: `| <category> | <slug> | <ref> | <version> |`. Regex match `\| [^|]+ \| <slug> \| ` → if found, replace whole row (upgrade); else insert under `## Policies` (creating the table if absent).

### Atomic state writes

- Every state mutation: write to `.sn-init-state.json.tmp`, rename.
- `.claude/settings.json` mutations: same tmp+rename pattern.
- If mid-apply fails: tmp file lingers; warn; user re-runs to retry. State on disk remains the last successful one.

### Already-applied detection

Before running apply for a slug:
- Same version applied → "already applied; no-op" (exit 0).
- Older version applied → "applied <v_a>; catalog has <v_c>; use upgrade" (exit 0).

---

## 8. Settings merge algebra

Apply rule per array (e.g. `hooks.PreToolUse`):

```
for each entry in incoming patch:
  if exists entry in target where (matcher, policy) match:
    if version field differs → replace target entry (upgrade)
    else → skip (idempotent)
  else:
    append entry to target array
```

Remove rule:

```
for each array in target:
  strip all entries where policy == <slug>
```

Object keys (non-array): deep-merge on apply; not touched on policy-remove (because removing an object key safely is hard; only array entries are policy-tagged).

### Worked example

Start: `{"hooks": {}}`.

After applying `memory-regulated` + `secret-scan`:
```json
{
  "hooks": {
    "PreToolUse": [
      {"policy": "memory-regulated", "version": "1.0.0", "matcher": "Write", "pattern": "(~/.claude/memory/|\\.claude/local-memory/)", "command": ".claude/hooks/memory-regulated.sh"},
      {"policy": "secret-scan", "version": "1.3.0", "matcher": "Write|Edit", "command": ".claude/hooks/secret-scan.sh"}
    ],
    "PreCommit": [
      {"policy": "secret-scan", "version": "1.3.0", "command": ".claude/hooks/secret-scan-staged.sh"}
    ]
  }
}
```

After upgrading `memory-regulated` to 1.1.0: the matching `(Write, memory-regulated)` entry is replaced with the 1.1.0 entry; `secret-scan` untouched.

After removing `memory-regulated`: every entry with `policy: "memory-regulated"` is stripped; arrays may become empty but are left in place.

### Edge cases

- Patch entry without `policy:` field → reject at apply (exit 19).
- Two policies emit identical `(matcher, policy)` tuple via author error → linted with `sn-setup policy lint`.
- User hand-edits an entry → flagged as `◆ drifted` in status; remove with `--force` still works (matches by `policy:` tag regardless of other field edits).

---

## 9. Profile defaults flow

### Resolution at scaffold time

`sn-setup demo --profile=microservice`:

```
1. Load default_policies.yaml from templates/profile/microservice/
   → base_set = [repository-ecosystem, memory-ordinary, audit-log-strict,
                 supply-chain-scan, secret-scan, commit-msg-gate]

2. Apply CLI overrides:
   a. if --policies=<list> passed:
        if --add-policies or --remove-policies also passed → exit 17
        else: applied_set = <list> (ignore base_set entirely)
   b. else:
        applied_set = base_set
        applied_set += --add-policies list
        applied_set -= --remove-policies list

3. Validate applied_set (see §5 step 2)

4. Materialize:
   a. Write .claude/profile-defaults.yaml = base_set (the original profile bundle, NOT applied_set)
      → records "what the profile said at scaffold time"
   b. Apply each policy in applied_set (idempotent; shares code with `policy apply`)
   c. policy_history entries: source = "profile-default" | "scaffold-override" | "scaffold-delta"
```

### `.claude/profile-defaults.yaml`

Written by `sn-setup` at scaffold time. Editable by `sn-setup profile add/remove --profile=<P>` post-scaffold. Format:

```yaml
# Project-local override of the plugin's profile defaults.
# Edit via: sn-setup profile add/remove --profile=microservice <slug>
# Read by: sn-setup policy apply --use-profile-defaults
profile: microservice
policies:
  - repository-ecosystem
  - memory-ordinary
  - audit-log-strict
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate
```

The plugin's `templates/profile/<P>/default_policies.yaml` is the **factory** default; this project-local file is the **project's chosen** default. They can diverge.

### `sn-setup policy apply --use-profile-defaults`

```
1. Read .claude/profile-defaults.yaml → target_set
2. Compute diff vs state.applied_policies:
   - missing = target_set - applied  → apply each
   - extra = applied - target_set    → NOT removed (additive only)
3. Print "applied N missing; M already up-to-date; K extra policies present (not removed)"
```

Extra-policies are NOT auto-removed because removal is destructive and would surprise users who added policies on top.

---

## 10. Errors + exit codes

### New exit codes (additions to existing schema)

| Code | Name | Cause | Remediation |
|---|---|---|---|
| 10 | `UNKNOWN_POLICY` | Slug not in catalog | `sn-setup policy list` |
| 11 | `UNKNOWN_PROFILE` | Profile unknown to `sn-setup profile` | `sn-setup profile list` |
| 12 | `EXCLUSIVE_GROUP_CONFLICT` | Group constraint violated AND auto-swap suppressed (reserved for future `--no-swap`) | Drop one of the conflicting slugs |
| 20 | `CONFLICTS_WITH_VIOLATION` | Apply violates a `conflicts_with` entry against an already-applied policy | Remove the conflicting policy first, or drop this apply |
| 13 | `REQUIRES_NOT_SATISFIED` | Apply needs other policies first | Add `--with-deps` |
| 14 | `USER_EDITED_BLOCKS_OP` | Remove/upgrade hit edited file without `--force` | Inspect diff; decide |
| 15 | `CWD_AMBIGUOUS_OR_INVALID` | `sn-setup profile` cwd is not plugin or scaffolded project, or both | cd to correct dir, or pass `--target=plugin\|project` |
| 16 | `POLICY_NOT_APPLIED` | Remove/upgrade for a slug not in `applied_policies` | Apply first, or check `show-applied` |
| 17 | `MIXED_OVERRIDE_FLAGS` | `--policies=` combined with `--add/-remove-policies` | Pick one mode |
| 18 | `CATALOG_DOWNGRADE` | State version > catalog version for a slug | Reinstall newer plugin, or remove the slug |
| 19 | `MALFORMED_PATCH` | `settings.patch.json` entry missing `policy:` field | Fix author bug; `sn-setup policy lint` |

### Worked error messages

```
$ sn-setup policy apply foobar
sn-setup: error: unknown policy 'foobar' [exit 10]
  available: memory-ordinary, memory-regulated, repository-ecosystem,
             audit-log-strict, supply-chain-scan, secret-scan,
             commit-msg-gate, branch-naming, pdpa-compliance
  see: sn-setup policy list

$ sn-setup policy apply pdpa-compliance
sn-setup: error: 'pdpa-compliance' requires 3 policies not applied [exit 13]
  missing: memory-regulated, audit-log-strict, secret-scan
  retry:   sn-setup policy apply pdpa-compliance --with-deps

$ sn-setup policy remove memory-regulated
sn-setup: warning: skipped 2 user-edited files [exit 14]
  skipped:
    .claude/docs/policies/memory-regulated.md
    .claude/rules/memory-regulated.md
  state still updated; use --force to delete edited files

$ sn-setup demo --policies=foo --add-policies=bar
sn-setup: error: --policies replaces the default set; --add/--remove cannot combine with it [exit 17]
  pick one:
    --policies=X,Y,Z              (replace default)
    --add-policies=X --remove-policies=Y   (delta against default)
```

### Warnings (non-fatal)

- Apply of already-applied slug at same version → "no-op" (exit 0).
- Apply of already-applied slug at older version → "use upgrade" (exit 0).
- Upgrade skipped one or more files → printed to stderr; state still bumped.

### Lint command

`sn-setup policy lint` validates the catalog itself. Checks:

- Every `policy.yaml` parses, has required fields, version is semver.
- Every referenced file exists.
- No two policies in same exclusive group with overlapping `applies_to` AND identical `(matcher)` keys.
- No circular `requires`.
- No `conflicts_with` mentioning a non-existent slug.

---

## 11. Tests

### Unit tests (`tests/test_policy_catalog.py`)

| Test | Verifies |
|---|---|
| `test_catalog_loads_all_9_policies` | Every `policy.yaml` parses; required fields; semver version |
| `test_catalog_lint_passes` | `policy lint` exit 0; no circular requires, no orphan conflicts_with, no settings-marker collisions |
| `test_policy_list_outputs_all_with_metadata` | `policy list` shows slug+category+version+group |
| `test_policy_show_renders_section_preview` | `policy show memory-regulated` contains slug + version + first ~10 lines |
| `test_apply_new_writes_all_layers` | CLAUDE.md row, docs/rules files, settings.json merged with `policy:` marker, state updated |
| `test_apply_idempotent_same_version` | Two consecutive applies → second is no-op |
| `test_apply_swaps_exclusive_group_with_warn` | Apply memory-regulated when memory-ordinary applied → swap; history records `swap` event |
| `test_apply_requires_with_deps_auto_installs` | `apply pdpa-compliance --with-deps` installs three deps first |
| `test_apply_requires_without_deps_errors` | Same without `--with-deps` → exit 13 |
| `test_apply_unknown_slug_errors` | `apply foobar` → exit 10 |
| `test_remove_unedited_files_deletes` | Files gone, settings stripped, state stripped |
| `test_remove_user_edited_warns_skips` | Edited file remains; exit 14; state strips entry |
| `test_remove_force_overrides_edits` | `--force` → file deleted |
| `test_upgrade_obsolete_refreshes_state` | State version bumps, applied_at refreshed, sha refreshed |
| `test_upgrade_skips_user_edited_files` | skipped_files recorded; state version still bumps |
| `test_status_classifies_current_obsolete_unknown_drifted` | Output matches expected glyphs |
| `test_settings_merge_dedupes_by_matcher_policy` | Re-apply → no duplicate entries |
| `test_settings_merge_array_append_distinct` | Two policies, different matchers → both present |
| `test_remove_strips_only_matching_policy_marker` | Other policy's entries survive |
| `test_state_migration_for_existing_scaffold` | Pre-catalog state → adds empty arrays |

### Profile-level tests

| Test | Verifies |
|---|---|
| `test_scaffold_with_profile_applies_defaults` | `--profile=microservice` → applied = default_policies.yaml content |
| `test_scaffold_policies_flag_replaces_defaults` | `--policies=secret-scan` → applied = only secret-scan |
| `test_scaffold_add_remove_policies_deltas` | Delta against default applied |
| `test_scaffold_policies_combined_with_delta_errors` | `--policies=X --add-policies=Y` → exit 17 |
| `test_scaffold_writes_project_local_profile_defaults` | `.claude/profile-defaults.yaml` written |
| `test_apply_use_profile_defaults_idempotent` | Second run is no-op |
| `test_apply_use_profile_defaults_does_not_remove_extras` | Manual extras left alone |

### `sn-setup profile` cwd-detect tests

| Test | Verifies |
|---|---|
| `test_profile_add_in_plugin_repo_edits_template` | cwd plugin → edits template YAML |
| `test_profile_add_in_scaffolded_project_edits_local` | cwd project → edits `.claude/profile-defaults.yaml` |
| `test_profile_add_ambiguous_cwd_requires_target` | Both markers → exit 15 unless `--target=` |
| `test_profile_add_neither_marker_errors` | Plain dir → exit 15 |
| `test_profile_add_unknown_profile_errors` | `--profile=mainframe` → exit 11 |
| `test_profile_add_unknown_policy_errors` | `add foobar` → exit 10 |

### CLI smoke (golden file)

`tests/golden/scaffolded-microservice/` — snapshot of `sn-setup demo --profile=microservice --no-git`:
- `.sn-init-state.json` (sorted `applied_policies`; `applied_at` redacted)
- `CLAUDE.md` (with `## Policies` table)
- `.claude/profile-defaults.yaml`
- `.claude/settings.json` (merged entries)

Regenerate via `SN_GOLDEN_REGEN=1 pytest tests/test_policy_catalog.py::test_microservice_golden`.

### Coverage target

≥ 90% for catalog code paths. Settings-merge algebra: aim 100% branch coverage.

---

## 12. Out of scope (this PR)

- **Profile expansion** (`worker`, `cli`, `library`, `gateway`, `mcp-server`) — PR2 in the D1 decomposition.
- **Default bundles for new profiles** — PR3.
- **Per-language policy variants** — handled today by `applies_to` listing profiles, not languages; revisit if a real need surfaces.
- **Policy marketplace / consumer side** — covered by backlog B2.3 (marketplace consumer model). The catalog is currently template-baked; marketplace move is a future architectural shift (B3.1).
- **PDPA full pack** — backlog B2.5. This spec ships `pdpa-compliance` as a thin signal-only policy that gates on its three required policies; the full enforcement is a separate item.
- **Cross-repo policy propagation** — the catalog is per-repo. Org-wide rollouts happen via the marketplace (deferred).

---

## 13. Migration & rollout

1. Land PR1 (this spec) — catalog code + 9 policies + CLI + tests + docs.
2. Mark backlog B1.1 + B1.2 as **superseded** with a pointer to this spec.
3. Add a one-paragraph migration note in `CHANGELOG.md` for existing scaffolded projects:
   - First `sn-setup policy *` invocation auto-migrates state.
   - Old hand-edited `## Repository Ecosystem` content (if any) is left in place; running `sn-setup policy apply repository-ecosystem` writes the doc without touching CLAUDE.md if the row already exists.
4. PR2 + PR3 land per the D1 plan in subsequent sprints.

---

## 14. Decisions log

Maps brainstorm Qs to locked answers.

| Q | Topic | Locked |
|---|---|---|
| Q1 | Categories spanned | All 4: security, conventions, workflow, observability |
| Q2 | Per-policy effect scope | Option C with token-economy layers (CLAUDE.md row + on-demand docs + always-on rule + settings patch + extras) |
| Q3 | Catalog v1 size | 9 policies (all proposed) |
| Q3a | Scope decomposition | **D1** — three sequential PRs; this spec = PR1 |
| Q4 | Default behavior | **A**: profile-bundled defaults via `default_policies.yaml`; plus future edit via `sn-setup profile add/remove` |
| Q4a | Naming scheme | **B** — unified `sn-setup` with `policy` + `profile` sub-trees |
| Q5 | Per-scaffold override | **C** — `--policies=` replace OR `--add/-remove-policies` delta; combining = exit 17 |
| Q6 | Exclusive-group conflict | **A** — auto-swap with warn |
| Q7 | Removal of user-edited files | **A** — warn + skip; `--force` overrides |
| Q8 | Settings merge algebra | **A** — custom deep-merge with `policy: <slug>` markers |
| Q9 | Versioning | **A** — per-policy semver + `status` + `upgrade` commands |
| Q10 | History / audit trail | **A** — `applied_policies` + `policy_history` (append-only) |

---

## 15. Open follow-ups (not blocking PR1)

- **B2.1a** — profile-aware foregrounding of the Repository Ecosystem table (BFF foregrounds downstreams, frontend foregrounds its BFF). Catalog hooks into this via `claude-md.row.md` being profile-aware — deferred.
- **B2.1b** — per-profile plugin install entries via the (still-TBD) marketplace consumer.
- **B2.1c** — per-profile subagents under `templates/profile/<profile>/.claude/agents/`.
- **B2.5** — PDPA compliance pack: replaces the signal-only `pdpa-compliance` policy with full enforcement.
- **Catalog promotion** — local-project policy graduating into the shared catalog (design doc §6.5 promotion path).
