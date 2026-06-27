---
topic: marketplace-divergence-warning-requirements
bucket: projects
origin_project: setup_project_plugin
origin_req: REQ-WS-002
first_seen: 2026-06-27
last_updated: 2026-06-27
status: planned
tags: [knowledge, requirements, workspace, marketplace, scaffold, b2.2-fu-4, setup_project_plugin]
---

# Requirements — Marketplace divergence warning in `workspace add` (B2.2-FU-4)

REQ-WS-002. Carved follow-up `B2.2-FU-4` from `workspace-layer` (REQ-WS-001). Unblocked by `marketplace-consumer` (REQ-MKT-001, shipped B2.3). Light workflow: single combined requirements + design + implementation plan note + one PR.

## Goal

When `sn-setup workspace add <path>` registers a new member service into a workspace, compare the new member's marketplace configuration against existing members and emit severity-tagged stderr warnings on divergence. **Warn-only**; the `add` operation always succeeds.

The warnings exist because a workspace is a virtual monorepo — services in it are expected to interoperate. If member A pulls plugins from one marketplace and member B pulls from another, the cross-repo Claude sessions in the workspace see two different toolchains and the "shared but pick what you need" model (design §6.1) silently breaks.

## Decisions locked (brainstorm)

| # | Question | Choice |
|---|---|---|
| D-1 | What counts as divergence? | **Both**: `marketplace.source` mismatch → 🔴 critical; mandatory plugin (`core-workflow` / `core-guardrails`) missing → 🔴 critical; `installed_plugins` name-set mismatch → 🟡 informational diff. |
| D-2 | Where does the check fire? | **`workspace add` only**. Cheapest surface; matches FU-4 backlog scope. Not `status`/`sync` (alert fatigue). |
| D-3 | Strict or warn-only? | **Warn-only**. `add` succeeds regardless of divergence; user decides whether to intervene. No `--force` needed because nothing is being blocked. |
| D-4 | Read `installed_plugins` from where? | **`.claude/settings.json`** (truthier; reflects live state including post-scaffold edits). Not `.sn-init-state.json` (stale-prone). |

## What ships in this PR

### Scaffolder

`scripts/workspace_cli.py::_cmd_add` gains a divergence-check phase between the existing "auto-collect profile/lang/regulated from state" block and the "register entry" block:

1. Read the new member's `<service_path>/.claude/settings.json`. Extract `installed_plugins[].name` set + `marketplace.json::marketplace.source` (read separately from `<service_path>/.claude-plugin/marketplace.json` if present).
2. For each already-registered service in the workspace registry, resolve its absolute path and read its own `.claude/settings.json` + `.claude-plugin/marketplace.json`. Skip silently if either file is absent (member predates B2.3 wiring).
3. Compute the divergence findings:
   - 🔴 **source mismatch**: new member's `marketplace.source` differs from any existing member's.
   - 🔴 **mandatory missing**: new member's `installed_plugins` set lacks `core-workflow` and/or `core-guardrails` while at least one other member has them.
   - 🟡 **plugin set diff**: symmetric set difference between new member's `installed_plugins` names and the **union** of names across existing members (mandatory plugins already covered above are reported once at the higher severity, not double-counted in the yellow set).
4. Print findings to stderr with the standard tag prefixes (`sn-setup workspace: ⚠ critical:` for red, `sn-setup workspace: ⚠ warn:` for yellow). Each finding on its own line.
5. Continue to the existing entry-append step — `add` succeeds regardless.

No registry schema change. The check pulls from each member's filesystem at `add` time.

### Tests

`tests/test_workspace_*.py` (or the existing `tests/test_workspace_add.py`) gains B2.2-FU-4 cases:

- New member with identical marketplace source + installed_plugins to existing members → no stderr divergence warnings.
- First member added to an empty workspace → no divergence warnings (nothing to compare against).
- New member with different `marketplace.source` than existing members → 🔴 critical warning printed; `add` still returns `EXIT_OK`.
- New member missing `core-guardrails` while existing members have it → 🔴 critical warning; `add` succeeds.
- New member with extra opt-in plugin (e.g. `bff-patterns`) not present in any existing member → 🟡 plugin set diff warning; `add` succeeds.
- New member without `.claude/settings.json` / `.claude-plugin/marketplace.json` → silent (legacy member predates B2.3).
- Existing member without those files → silent for that one comparison; other comparisons still run.

### Backlog + CHANGELOG

- `docs/backlog.md`: `B2.2-FU-4` row marked `[x]` with the PR / merge SHA reference.
- `CHANGELOG.md`: `[Unreleased] > Added` entry.

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-1 | `sn-setup workspace add <path>` always exits 0 on a valid service path regardless of divergence findings (warn-only). |
| AC-2 | When the new member's `.claude-plugin/marketplace.json::marketplace.source` differs from any existing member's, a 🔴 critical stderr warning is printed naming both sources + the conflicting member slug. |
| AC-3 | When the new member's `.claude/settings.json::installed_plugins` is missing `core-workflow` and/or `core-guardrails` while at least one existing member ships them, a 🔴 critical stderr warning names the missing mandatory plugin(s). |
| AC-4 | When the new member's `installed_plugins` name set differs from the union of existing members' name sets (excluding the mandatory plugins covered by AC-3), a 🟡 informational stderr warning prints the symmetric difference. |
| AC-5 | New member with no `.claude/settings.json` (pre-B2.3 scaffold or `--no-marketplace`) emits no divergence warnings. Existing members with no settings file are skipped silently during pairwise compares. |
| AC-6 | First member added to an empty workspace produces no divergence output. |
| AC-7 | All existing workspace tests pass; new tests pass; full suite green on Python 3.11/3.12/3.13. |
| AC-8 | Backlog row marked `[x]`; CHANGELOG `[Unreleased] > Added` entry. |

## Out of scope

- **`status` / `sync` divergence re-check** — explicitly Q2-locked out. Re-check at `add` only.
- **Block-on-divergence mode** — Q3-locked warn-only. No `--force` flag.
- **Pin version comparison** — pin syntax itself is `B2.3-FU-2` (waits on B3.1 + B3.2). When pins land, this check should extend to compare versions, but not in this PR.
- **`registry.json` schema additions** — leaving the registry as-is. Each compare reads filesystems live; no caching layer.
- **CODEOWNERS divergence check** — orthogonal concern; unrelated.

## Implementation plan (light)

Branch: `feat/marketplace-divergence-warning` from `main`.

1. Vault req+design+plan (this file) committed + pushed. **← first step.**
2. `requirements/README.md` index updated with row.
3. Branch created.
4. Spec mirror commit: copy this doc → `docs/superpowers/specs/2026-06-27-marketplace-divergence-warning-design.md`.
5. Implement `_collect_marketplace_state(service_path)` helper + `_check_divergence(new_state, existing_states)` in `scripts/workspace_cli.py`. Wire into `_cmd_add` between auto-collect and registry append.
6. Author tests in `tests/test_workspace_add.py` (or whichever test file currently houses `_cmd_add` cases).
7. Run full suite, fix anything red.
8. Mark backlog `[x]`, append CHANGELOG.
9. Final sonnet reviewer pass; bundle findings into one fix commit if needed.
10. Push + open PR + watch CI green.
11. Merge on user "ok".
12. Bump `shipped_in` frontmatter on this doc; append Batch 32 entry to `implementation-log.md`; push vault.

## Execution mode

Direct write by main thread. No SDD subagents. Single sonnet reviewer at end. Scope is narrow: ~60 LOC in `workspace_cli.py` + ~6 test cases.

## Related

- [[workspace-layer]] — REQ-WS-001 (parent).
- [[marketplace-consumer]] — REQ-MKT-001 (B2.3, the unblocker).
- `B2.3-FU-2` plugin version pinning syntax — future extension to this check once pins land.
- `B3.1` platform marketplace — once standing, the source-mismatch warning becomes more meaningful (today most workspaces use `./` placeholder).
