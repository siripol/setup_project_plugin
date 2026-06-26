# PDPA Pack (Full Enforcement) — Design Spec

| Field | Value |
|---|---|
| Date | 2026-06-26 |
| Author | brainstorming session (Siripol + Claude) |
| Status | Draft — awaiting user review |
| Branch | `feat/pdpa-pack` |
| Closes | Backlog **B2.5** |
| Predecessor | `pdpa-compliance@1.0.0` (signal-only stub shipped in PR #18 policy catalog) |
| Carved follow-ups | B2.5a (review-staleness), B2.5b (consent-check), B2.5c (audit-log breach detection), B2.5d (CI auto-rotate `last_reviewed`), B2.5e (Luhn for PAN) |

---

## 0. Summary

Upgrades the catalog policy `pdpa-compliance` from signal-only `1.0.0` to enforcement `2.0.0`. Same slug + same catalog slot; existing scaffolds with `1.0.0` applied will see "obsolete" in `sn-setup policy status` and can upgrade via `sn-setup policy upgrade pdpa-compliance`.

Ships:
- **Hook A** — `pdpa-data-handler-scan.sh` (PreToolUse on Write/Edit). PII regex scan over 4 pattern families. Skip-on-allowlist-match.
- **Hook B** — `pdpa-retention-check.sh` (PreToolUse on Write to `data/`). Verifies sidecar `<file>.meta.yaml` exists with 6 required keys.
- **Allowlist sub-command** — `sn-setup policy pdpa allowlist <list|add|remove|explain>`. Manages project-local `.claude/config/pdpa-allowlist.yaml`.
- **Scaffolded dirs** — `data/{subjects,consents,exports}/` with `.gitkeep` + README.
- **4 doc templates** — classification, retention, consent records, breach-notification runbook (under `docs/compliance/`).

Why hooks: signal-only policy is documentation. Full enforcement requires PreToolUse hooks that fire BEFORE Write/Edit lands, preventing PDPA violations at the developer's keyboard.

---

## 1. Architecture

### Per-policy directory (in plugin source)

```
templates/policies/pdpa-compliance/
  policy.yaml                          # version 2.0.0; +settings_patch + extras
  claude-md.row.md                     # 1 line (version bump only)
  docs/pdpa-compliance.md              # full body (replace signal-only stub)
  rules/pdpa-compliance.md             # tiny always-on (expand 3-5 lines)
  settings.patch.json                  # NEW — wires both hooks
  extras/
    hooks/
      pdpa-data-handler-scan.sh        # NEW — A: PII regex scan
      pdpa-retention-check.sh          # NEW — B: sidecar verification
    config/
      pdpa-allowlist.yaml              # NEW — seeded allowlist
    data/
      README.md                        # NEW — data/ structure explanation
      subjects/.gitkeep
      consents/.gitkeep
      exports/.gitkeep
    docs/compliance/
      data-classification-template.md  # NEW
      retention-policy-template.md     # NEW
      consent-records-template.md      # NEW
      breach-notification-runbook.md   # NEW
```

### Layout in scaffolded project (after apply)

```
<project>/
  .claude/
    docs/policies/pdpa-compliance.md   # load-on-demand body
    rules/pdpa-compliance.md           # always-on tiny rule
    hooks/pdpa-data-handler-scan.sh    # +x
    hooks/pdpa-retention-check.sh      # +x
    config/pdpa-allowlist.yaml         # project-scoped allowlist
    settings.json                      # merged with policy:pdpa-compliance markers
  data/
    README.md
    subjects/.gitkeep
    consents/.gitkeep
    exports/.gitkeep
  docs/compliance/
    data-classification-template.md
    retention-policy-template.md
    consent-records-template.md
    breach-notification-runbook.md
```

### policy.yaml

```yaml
slug: pdpa-compliance
title: "PDPA compliance (full enforcement)"
version: 2.0.0
category: security
group: null
applies_to: [microservice, bff]   # frontend gets it as part of regulated bundles via B1.7b
requires: [memory-regulated, audit-log-strict, secret-scan]
conflicts_with: []
description: |
  Full PDPA enforcement: PreToolUse PII scan over 4 pattern families,
  PreToolUse retention-sidecar check on data/, project-managed allowlist,
  4 doc templates, scaffolded data/ dirs.
files:
  claude_md_row: claude-md.row.md
  docs: docs/pdpa-compliance.md
  rules: rules/pdpa-compliance.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/pdpa-data-handler-scan.sh:.claude/hooks/pdpa-data-handler-scan.sh
    - extras/hooks/pdpa-retention-check.sh:.claude/hooks/pdpa-retention-check.sh
    - extras/config/pdpa-allowlist.yaml:.claude/config/pdpa-allowlist.yaml
    - extras/data/README.md:data/README.md
    - extras/data/subjects/.gitkeep:data/subjects/.gitkeep
    - extras/data/consents/.gitkeep:data/consents/.gitkeep
    - extras/data/exports/.gitkeep:data/exports/.gitkeep
    - extras/docs/compliance/data-classification-template.md:docs/compliance/data-classification-template.md
    - extras/docs/compliance/retention-policy-template.md:docs/compliance/retention-policy-template.md
    - extras/docs/compliance/consent-records-template.md:docs/compliance/consent-records-template.md
    - extras/docs/compliance/breach-notification-runbook.md:docs/compliance/breach-notification-runbook.md
```

---

## 2. Hook A — `pdpa-data-handler-scan.sh`

PreToolUse on `Write|Edit`. Scans payload for PII patterns; blocks on match unless target path matches an allowlist glob.

### Settings entry

```json
{
  "policy": "pdpa-compliance",
  "version": "2.0.0",
  "matcher": "Write|Edit",
  "command": ".claude/hooks/pdpa-data-handler-scan.sh"
}
```

### Hook flow

```
1. Read tool input JSON from stdin (jq for file_path + content).
2. Project root resolution (walk up; same pattern as chokepoint-gate.sh).
3. Read allowlist file `.claude/config/pdpa-allowlist.yaml`.
4. For each `allowlist:` glob, shell-match against target path relative to root.
   On match → exit 0 (skip scan).
5. Run regex patterns on (content + file_path tail):
   - Thai NI 13-digit:   `\b[0-9]{13}\b`
   - Email:              `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`
   - Thai mobile:        `\b(0|66)[6-9][0-9]{8}\b`
   - Thai landline:      `\b(0|66)[2-7][0-9]{7}\b`
   - Credit-card PAN:    `\b(?:[0-9]{4}[ -]?){3,4}[0-9]{1,4}\b`
   - Passport:           `\b[A-Z]{1,2}[0-9]{6,9}\b`
6. On match → print blocking message + exit 2.
7. On no match → exit 0 (allow).
```

### Blocking message format

```
PDPA: 'data-handler-scan' detected a PII pattern in <relative-path>.
Pattern: <which one matched>.
If this is intentional (test fixture, anonymized example), allowlist the path:
  sn-setup policy pdpa allowlist add "<suggested glob>"
Then re-run the tool call.
Background: .claude/docs/policies/pdpa-compliance.md.
```

### Graceful degradation

- `jq` missing → exit 0 + stderr warning. Matches existing `rate-limit.sh` pattern.
- `pdpa-allowlist.yaml` missing → treat as empty allowlist, scan everything.

### Seeded allowlist

```yaml
# Project-scoped PDPA scan exemptions.
# Managed via: sn-setup policy pdpa allowlist {list|add|remove|explain}.
# Hand-edits OK but the command validates globs.
allowlist:
  - test/**
  - tests/**
  - "**/*.test.*"
  - "**/*_test.go"
  - "**/fixtures/**"
  - docs/examples/**
```

Covers common test paths so developers don't hit a wall on Day 1.

---

## 3. Hook B — `pdpa-retention-check.sh`

PreToolUse on `Write` matching `data/.*`. Verifies sidecar exists + has required keys.

### Settings entry

```json
{
  "policy": "pdpa-compliance",
  "version": "2.0.0",
  "matcher": "Write",
  "pattern": "data/.*",
  "command": ".claude/hooks/pdpa-retention-check.sh"
}
```

### Hook flow

```
1. Read tool input JSON → target file_path.
2. Project root resolution.
3. Skip rules:
   - basename matches `.gitkeep|README.md` → exit 0.
   - file_path ends with `.meta.yaml` → exit 0 (the sidecar itself).
   - relative_path NOT under `data/` → exit 0 (defensive).
4. Sidecar = `<target>.meta.yaml`.
5. If sidecar absent → block with "create sidecar" message.
6. Parse sidecar (grep + sed; no yq dep). Check required keys:
     retention_days   (integer ≥ 1)
     data_subject     (non-empty string)
     lawful_basis     (one of: consent, contract, legal-obligation,
                      vital-interest, public-task, legitimate-interest)
     data_categories  (non-empty list)
     controller       (non-empty string)
     last_reviewed    (YYYY-MM-DD)
7. On missing/invalid → block with field-by-field error.
8. On all-pass → exit 0.
```

### Sidecar example

```yaml
retention_days: 365
data_subject: customer
lawful_basis: contract
data_categories: [name, email, phone, address]
controller: orders-team
last_reviewed: 2026-06-26
```

### Why PreToolUse, not PreCommit

PreCommit catches violations at commit time — too late. PreToolUse blocks at first write; feedback is immediate.

---

## 4. Allowlist sub-command UX

New sub-sub-command under `sn-setup policy`: `pdpa allowlist <verb>`. Manages project-local `.claude/config/pdpa-allowlist.yaml`.

### CLI surface

```bash
sn-setup policy pdpa allowlist list
sn-setup policy pdpa allowlist add <glob>
sn-setup policy pdpa allowlist remove <glob>
sn-setup policy pdpa allowlist explain <path>
```

### Behaviors

| Verb | Behavior |
|---|---|
| `list` | Print every glob, one per line. Exit 0. |
| `add <glob>` | Validate glob (no `../`, no absolute paths). Refuse duplicates. Append. Exit 0. |
| `remove <glob>` | Refuse if not present (exit 2). Strip. Exit 0. |
| `explain <path>` | Match path top-down; print first hit. Exit 1 if no match. |

### Implementation

New Python module `scripts/policy_pdpa.py` (~80 lines). Dispatched from `scripts/policy_cli.py` when first positional == `pdpa`.

### Refuses

| Input | Result |
|---|---|
| `../escape/**` | exit 2 "directory traversal forbidden" |
| `/abs/path/**` | exit 2 "use repo-relative globs only" |
| add duplicate | exit 0 "already present" (no-op) |
| remove non-existent | exit 2 "not in allowlist" |
| missing file on add | create with seeded comment + new entry |
| missing file on list/remove/explain | exit 2 "PDPA allowlist not initialized" |

---

## 5. Doc templates

Four templates ship under `extras/docs/compliance/`; land at `<project>/docs/compliance/` on apply. Load-on-demand (NOT in `.claude/docs/`); meant for humans + auditors, not always-loaded prompt context.

Files:

- `data-classification-template.md` — per-category classification table.
- `retention-policy-template.md` — per-category retention windows + sidecar shape.
- `consent-records-template.md` — consent-record YAML shape + lookup flow.
- `breach-notification-runbook.md` — PDPA §37 detect/contain/assess/notify/document flow.

Full bodies in §5 of the brainstorm session; copied verbatim into the catalog.

---

## 6. Tests

### Catalog content (1)

| Test | Verifies |
|---|---|
| `test_b2_5_pdpa_pack_v2_files_present` | All new files exist in catalog dir |

### Apply integration (2)

| Test | Verifies |
|---|---|
| `test_b2_5_pdpa_apply_writes_hooks_and_config` | `.claude/hooks/pdpa-*.sh` present + `+x`, allowlist file present, `data/{subjects,consents,exports}/` with `.gitkeep`, `docs/compliance/*.md` present |
| `test_b2_5_pdpa_apply_settings_carries_policy_marker` | `.claude/settings.json` `hooks.PreToolUse` has 2 entries with `policy: "pdpa-compliance"` |

### Hook behavior (3)

| Test | Verifies |
|---|---|
| `test_b2_5_data_handler_scan_blocks_pii` | Thai NI 13-digit in payload → exit 2 |
| `test_b2_5_data_handler_scan_skips_allowlisted_path` | Email under `test/fixtures/` → exit 0 |
| `test_b2_5_retention_check_blocks_missing_sidecar` | Write to `data/users.csv` without `.meta.yaml` → exit 2 |

### Allowlist CLI (5)

`test_pdpa_allowlist_list_seeded`, `_add_writes_yaml`, `_add_refuses_traversal`, `_remove_strips_glob`, `_explain_matches_first_hit`.

### Policy upgrade (1)

`test_b2_5_pdpa_upgrade_from_v1_to_v2` — scaffold with `1.0.0` applied → upgrade → state `2.0.0`, new files land.

### Total: 12 new tests

- `tests/test_sn_init.py` extension (catalog + apply + upgrade)
- `tests/test_pdpa_hooks.py` (NEW; bash subprocess)
- `tests/test_policy_pdpa.py` (NEW; CLI)

---

## 7. Out of scope

### In-scope (this PR)

- pdpa-compliance@2.0.0 upgrade.
- Hook A + Hook B.
- Allowlist sub-command + seeded entries.
- 4 doc templates.
- Scaffolded `data/{subjects,consents,exports}/`.
- 12 new tests.

### Carved follow-ups

| ID | Item |
|---|---|
| B2.5a | Retention review-staleness enforcement (≤ 365 days on `last_reviewed:`) |
| B2.5b | Consent-check hook (`pdpa-consent-check.sh`) |
| B2.5c | Audit-log breach-detection rules (cross-policy integration with `audit-log-strict`) |
| B2.5d | CI step auto-rotating sidecar `last_reviewed:` on PR approval |
| B2.5e | Luhn validation for PAN regex (false-positive reduction) |

### Not in backlog

- PCI-DSS enforcement (separate regime).
- GDPR-specific clauses (would warrant a separate `gdpr-compliance` policy).
- Subject-access-request (SAR) workflow.
- Right-to-erasure automation.
- Per-locale PDPA variations (Thai PDPA assumed).

---

## 8. Decisions log

| Q | Topic | Locked |
|---|---|---|
| Q1 | Scope (hooks shipped) | Medium — A + B; C carved as B2.5b |
| Q2 | PII patterns | All 4 (Thai NI, email+phone, credit card PAN, passport+non-Thai NI) |
| Q3 | Hook language | Bash (matches existing hooks) |
| Q4 | PII exemption mechanism | Command-managed project-scoped allowlist at `.claude/config/pdpa-allowlist.yaml` |
| Q5 | Retention metadata format | Sidecar `<file>.meta.yaml` |
| Q6 | Scaffold `data/` dirs | Yes — `data/{subjects,consents,exports}/` with `.gitkeep` + README |
| Q7 | When does retention-check fire | PreToolUse (not PreCommit) for immediate feedback |

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Bash regex false positives blocking legitimate writes | Medium | Seeded allowlist covers common test paths; `add` command lowers friction for new exemptions; messages explain how to add |
| `jq` not installed → hook silently skips | Low | Graceful degradation with stderr warning; matches existing hook pattern |
| Sidecar parse without yq dep → grep fragility | Medium | Use simple grep + sed; validate against required-keys list only; reject ambiguous yaml |
| Upgrade from 1.0.0 → 2.0.0 surprises existing teams | Medium | Migration note in `docs/MIGRATION.md`; upgrade is opt-in via `sn-setup policy upgrade` |
| Allowlist commit policy unclear (gitignored? committed?) | Low | Documented in seeded comment as committed (team-shared); hand-edits allowed |
| Performance impact on every Write/Edit | Low | Bash regex over typically <10 KB payload; <50 ms overhead per call |

---

## 10. Rollout

1. Land this PR → catalog has `pdpa-compliance@2.0.0`.
2. Regulated services run `sn-setup policy upgrade pdpa-compliance` to pick up enforcement.
3. Allowlist seeded; day-1 friction minimal.
4. Teams add project-specific entries via `sn-setup policy pdpa allowlist add <glob>`.
5. New scaffolds with regulated profile bundles get the full pack automatically once profile defaults include it (separate decision).

---

## 11. Open follow-ups (not blocking this PR)

- B2.5a-e listed above.
- PDPA-locale variants (PDPA-SG, PDPA-MY) — separate policy slugs.
- Multi-language PII regex (Cyrillic, CJK names) — currently English/Thai only.
