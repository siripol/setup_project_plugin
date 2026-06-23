# Policy Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a composable, versioned policy catalog to `sn-setup`, with `sn-setup policy` + `sn-setup profile` CLI sub-trees, 9 day-one policies, profile-bundled defaults, and idempotent apply/remove/upgrade ops.

**Architecture:** Each policy lives at `skills/sn-setup/templates/policies/<slug>/` and ships up to five layers (CLAUDE.md table row, optional always-on rule, on-demand doc, optional `settings.json` patch with `policy: <slug>` markers, optional extras). State recorded in `.sn-init-state.json` under `applied_policies` (current) + `policy_history` (append-only). Token economy is the design pillar: always-on surface is ~10 tokens per applied policy; full bodies load on demand.

**Tech Stack:** Python 3.13+, `pytest`, `argparse`, `pyyaml` (new runtime dep). All new code under `scripts/`. Tests use the same pattern as `tests/test_sn_init.py`.

## Global Constraints

- Spec is authoritative: `docs/superpowers/specs/2026-06-24-policy-catalog-design.md`. All field names, exit codes, and behaviors copied verbatim from there.
- Existing 143 tests in `tests/test_sn_init.py` MUST keep passing after each task.
- Every state mutation uses tmp+rename atomic write (existing pattern in `scripts/sn_init.py`).
- All written code is type-annotated (`from __future__ import annotations` + explicit types). Match existing style.
- Catalog YAML is parsed with `yaml.safe_load` only; never `yaml.load`. `pyyaml` ≥ 6.0.
- Every commit message ends with `Author: Siripol <siripoln.media@gmail.com>` trailer (enforced by `.githooks/commit-msg`); never include `Co-Authored-By: Claude`.
- Branch: `feat/policy-catalog` (already created from `feat/profiles`; spec committed as `7d840c0`).
- Exit codes from spec §10 — `UNKNOWN_POLICY=10`, `UNKNOWN_PROFILE=11`, `EXCLUSIVE_GROUP_CONFLICT=12`, `REQUIRES_NOT_SATISFIED=13`, `USER_EDITED_BLOCKS_OP=14`, `CWD_AMBIGUOUS_OR_INVALID=15`, `POLICY_NOT_APPLIED=16`, `MIXED_OVERRIDE_FLAGS=17`, `CATALOG_DOWNGRADE=18`, `MALFORMED_PATCH=19`, `CONFLICTS_WITH_VIOLATION=20`.
- `.claude/settings.json` arrays dedup by `(matcher, policy)` tuple; removal strips entries where `policy == <slug>`; missing `policy:` field rejects with exit 19.

---

## File map

### Create

| Path | Responsibility |
|---|---|
| `scripts/policy_errors.py` | New error classes + exit codes 10-20 (extends `scripts/errors.py` patterns) |
| `scripts/policy_loader.py` | Read `policy.yaml`, validate schema, return typed `PolicyMeta` dataclass |
| `scripts/policy_state.py` | Read/write `applied_policies` + `policy_history` in `.sn-init-state.json`; sha256 helpers; legacy-state migration |
| `scripts/policy_settings_merge.py` | Deep-merge `settings.patch.json` into `.claude/settings.json`; array dedup by `(matcher, policy)`; reverse-strip on remove |
| `scripts/policy_claude_md.py` | Manage the `## Policies` table in `CLAUDE.md`: insert/replace/strip rows; create section if absent |
| `scripts/policy_apply.py` | Orchestrate apply / remove / upgrade across all five layers; exclusive-group swap; requires/conflicts validation |
| `scripts/policy_cli.py` | `sn-setup policy <op>` dispatcher (list / show / apply / remove / upgrade / status / show-applied / history / lint) |
| `scripts/profile_cli.py` | `sn-setup profile <op>` dispatcher; cwd-detect plugin vs project |
| `skills/sn-setup/templates/policies/memory-ordinary/policy.yaml` + `claude-md.row.md` + `docs/memory-ordinary.md` + `rules/memory-ordinary.md` | Policy 1 |
| `skills/sn-setup/templates/policies/memory-regulated/policy.yaml` + `claude-md.row.md` + `docs/memory-regulated.md` + `rules/memory-regulated.md` + `settings.patch.json` + `extras/hooks/memory-regulated.sh` | Policy 2 |
| `skills/sn-setup/templates/policies/repository-ecosystem/policy.yaml` + `claude-md.row.md` + `docs/repository-ecosystem.md` | Policy 3 |
| `skills/sn-setup/templates/policies/audit-log-strict/policy.yaml` + `claude-md.row.md` + `docs/audit-log-strict.md` + `settings.patch.json` + `extras/hooks/audit-log-strict.sh` | Policy 4 |
| `skills/sn-setup/templates/policies/supply-chain-scan/policy.yaml` + `claude-md.row.md` + `docs/supply-chain-scan.md` + `settings.patch.json` + `extras/hooks/supply-chain-scan.sh` | Policy 5 |
| `skills/sn-setup/templates/policies/secret-scan/policy.yaml` + `claude-md.row.md` + `docs/secret-scan.md` + `rules/secret-scan.md` + `settings.patch.json` + `extras/hooks/secret-scan.sh` | Policy 6 |
| `skills/sn-setup/templates/policies/commit-msg-gate/policy.yaml` + `claude-md.row.md` + `docs/commit-msg-gate.md` + `settings.patch.json` | Policy 7 |
| `skills/sn-setup/templates/policies/branch-naming/policy.yaml` + `claude-md.row.md` + `docs/branch-naming.md` + `settings.patch.json` + `extras/hooks/branch-naming.sh` | Policy 8 |
| `skills/sn-setup/templates/policies/pdpa-compliance/policy.yaml` + `claude-md.row.md` + `docs/pdpa-compliance.md` + `rules/pdpa-compliance.md` | Policy 9 |
| `skills/sn-setup/templates/profile/microservice/default_policies.yaml` | Profile default bundle |
| `skills/sn-setup/templates/profile/bff/default_policies.yaml` | Profile default bundle |
| `skills/sn-setup/templates/profile/frontend/default_policies.yaml` | Profile default bundle |
| `tests/test_policy_loader.py` | Catalog schema + lint tests |
| `tests/test_policy_settings_merge.py` | Settings merge algebra unit tests |
| `tests/test_policy_claude_md.py` | CLAUDE.md row insert/replace/strip tests |
| `tests/test_policy_state.py` | State migration + content_sha tests |
| `tests/test_policy_apply.py` | Apply / remove / upgrade integration tests |
| `tests/test_policy_cli.py` | `sn-setup policy ...` CLI tests |
| `tests/test_profile_cli.py` | `sn-setup profile ...` CLI tests |
| `tests/golden/scaffolded-microservice/CLAUDE.md` etc. | Golden snapshot |

### Modify

| Path | Change |
|---|---|
| `scripts/sn_init.py` | Add `--policies` / `--add-policies` / `--remove-policies` / `--with-deps` flags; resolve final policy set per spec §9; dispatch `sn-setup policy ...` and `sn-setup profile ...` sub-trees; call `policy_apply` for new scaffolds |
| `scripts/errors.py` | Re-export new exit codes from `policy_errors` for the central code table |
| `skills/sn-setup/templates/managed-agent-base/CLAUDE.md` | Add empty `## Policies` table stub so apply has a target |
| `commands/sn-setup.md` | Document new flags + new sub-trees |
| `docs/backlog.md` | Mark B1.1 + B1.2 as superseded → `[x] PR1 catalog`; link spec |
| `CHANGELOG.md` | Append `[Unreleased]` entry |
| `requirements.txt` (new) | Add `pyyaml>=6.0` |

---

## Task list

The plan has **14 tasks**. Tasks 1–9 are core machinery (TDD, each ends in a green test). Tasks 10–11 are catalog content (templates only, no code). Tasks 12–14 are scaffold integration, docs, and the golden snapshot.

### Task 1: Add `pyyaml` dependency + state schema migration

**Files:**
- Create: `requirements.txt`
- Create: `scripts/policy_state.py`
- Create: `tests/test_policy_state.py`
- Modify: `.venv/` will need `pyyaml` installed for tests (one-time)

**Interfaces:**
- Consumes: nothing (foundation task)
- Produces:
  - `policy_state.read_state(target: Path) -> dict` — loads `.sn-init-state.json`, runs migration if `applied_policies` missing.
  - `policy_state.write_state(target: Path, state: dict) -> None` — atomic tmp+rename write.
  - `policy_state.sha256_file(path: Path) -> str` — sha256 hex of a file's contents.
  - `policy_state.sha256_str(s: str) -> str` — sha256 hex of an arbitrary string (used for CLAUDE.md table rows).
  - `policy_state.migrate(state: dict) -> dict` — adds `applied_policies: []` and `policy_history: []` if missing; returns the same dict.

- [ ] **Step 1: Create `requirements.txt`**

```text
pyyaml>=6.0
```

- [ ] **Step 2: Install the dep in the local venv (one-time)**

Run: `.venv/bin/python -m pip install pyyaml`
Expected: `Successfully installed pyyaml-6.0.x` (or already-satisfied).

- [ ] **Step 3: Write the failing test for migration + sha256 helpers**

Create `tests/test_policy_state.py`:

```python
"""Tests for scripts/policy_state.py — state file migration + sha256 helpers."""
from __future__ import annotations

import json
from pathlib import Path

import policy_state  # type: ignore


def test_migrate_adds_empty_arrays_when_missing():
    state = {"sn_init_version": "0.1.0", "mode": "new"}
    migrated = policy_state.migrate(state)
    assert migrated["applied_policies"] == []
    assert migrated["policy_history"] == []


def test_migrate_idempotent_when_arrays_present():
    state = {"applied_policies": [{"slug": "x"}], "policy_history": [{"action": "apply"}]}
    migrated = policy_state.migrate(state)
    assert migrated["applied_policies"] == [{"slug": "x"}]
    assert migrated["policy_history"] == [{"action": "apply"}]


def test_read_state_runs_migration(tmp_path: Path):
    sp = tmp_path / ".sn-init-state.json"
    sp.write_text(json.dumps({"mode": "new"}))
    state = policy_state.read_state(tmp_path)
    assert state["applied_policies"] == []
    assert state["policy_history"] == []


def test_write_state_round_trips(tmp_path: Path):
    state = {"mode": "new", "applied_policies": [], "policy_history": []}
    policy_state.write_state(tmp_path, state)
    loaded = json.loads((tmp_path / ".sn-init-state.json").read_text())
    assert loaded == state


def test_write_state_is_atomic(tmp_path: Path):
    """Writer must use tmp+rename so a partial write never corrupts the file."""
    state = {"mode": "new"}
    policy_state.write_state(tmp_path, state)
    assert not (tmp_path / ".sn-init-state.json.tmp").exists()


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("hello\n")
    h = policy_state.sha256_file(p)
    assert h == "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"


def test_sha256_str():
    assert policy_state.sha256_str("hello\n") == \
        "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
```

- [ ] **Step 4: Run the test — expected to fail (module missing)**

Run: `.venv/bin/python -m pytest tests/test_policy_state.py -v`
Expected: `ModuleNotFoundError: No module named 'policy_state'` for every test.

- [ ] **Step 5: Implement `scripts/policy_state.py`**

```python
"""State-file helpers for the policy catalog.

Owns the read/write of `.sn-init-state.json` for everything under
`applied_policies` + `policy_history`. Atomic writes (tmp+rename) match the
pattern in `scripts/sn_init.py`. Migration silently adds the new arrays to
state files written by older sn-setup versions.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

STATE_FILENAME = ".sn-init-state.json"


def migrate(state: dict) -> dict:
    """Add policy-catalog arrays to a state dict if absent. Mutates + returns."""
    state.setdefault("applied_policies", [])
    state.setdefault("policy_history", [])
    return state


def read_state(target: Path) -> dict:
    """Read state file at `target / .sn-init-state.json`, migrate, return."""
    path = target / STATE_FILENAME
    if not path.exists():
        return migrate({})
    state = json.loads(path.read_text(encoding="utf-8"))
    return migrate(state)


def write_state(target: Path, state: dict) -> None:
    """Atomic write: tmp file + rename, so a partial write never corrupts."""
    path = target / STATE_FILENAME
    tmp = path.with_suffix(f".json.tmp-{secrets.token_hex(4)}")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    """sha256 hex of the file's bytes."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_str(s: str) -> str:
    """sha256 hex of an arbitrary string (UTF-8)."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
```

- [ ] **Step 6: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_state.py -v`
Expected: 7 passed.

- [ ] **Step 7: Verify existing tests still green**

Run: `.venv/bin/python -m pytest -q`
Expected: 150 passed (143 original + 7 new).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt scripts/policy_state.py tests/test_policy_state.py
git commit -m "$(cat <<'EOF'
feat(policy): add pyyaml dependency + state migration helpers

scripts/policy_state.py owns the applied_policies + policy_history arrays in
.sn-init-state.json. Migrate is idempotent + safe on legacy state files.
sha256_file/_str helpers feed later drift detection.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 2: Catalog loader + `policy.yaml` schema

**Files:**
- Create: `scripts/policy_errors.py`
- Create: `scripts/policy_loader.py`
- Create: `tests/test_policy_loader.py`
- Create: `tests/fixtures/policies-valid/sample-policy/policy.yaml` + `claude-md.row.md` + `docs/sample-policy.md`
- Create: `tests/fixtures/policies-invalid/bad-version/policy.yaml`
- Create: `tests/fixtures/policies-invalid/missing-files/policy.yaml`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `policy_errors` module re-exports exit codes 10-20 + `UnknownPolicy`, `MalformedPolicy`, etc.
  - `policy_loader.PolicyMeta` dataclass with fields per spec §2 (`slug`, `title`, `version`, `category`, `group`, `applies_to`, `requires`, `conflicts_with`, `description`, `files`).
  - `policy_loader.load_policy(dir_path: Path) -> PolicyMeta` — parses policy.yaml, validates, returns dataclass.
  - `policy_loader.load_catalog(catalog_root: Path) -> dict[str, PolicyMeta]` — discovers all sub-dirs, loads each.
  - `policy_loader.lint(catalog_root: Path) -> list[str]` — returns list of human-readable lint failures; empty list = OK.

- [ ] **Step 1: Write the failing test**

Create `tests/test_policy_loader.py`:

```python
"""Tests for scripts/policy_loader.py — policy.yaml parsing + catalog lint."""
from __future__ import annotations

from pathlib import Path

import pytest

import policy_errors  # type: ignore
import policy_loader  # type: ignore


FIX = Path(__file__).parent / "fixtures"


def test_load_policy_parses_required_fields():
    meta = policy_loader.load_policy(FIX / "policies-valid" / "sample-policy")
    assert meta.slug == "sample-policy"
    assert meta.version == "1.0.0"
    assert meta.category == "security"
    assert meta.applies_to == ["microservice"]
    assert meta.requires == []
    assert meta.conflicts_with == []


def test_load_policy_rejects_bad_semver():
    with pytest.raises(policy_errors.MalformedPolicy) as e:
        policy_loader.load_policy(FIX / "policies-invalid" / "bad-version")
    assert "semver" in str(e.value).lower()


def test_load_policy_rejects_missing_referenced_files():
    with pytest.raises(policy_errors.MalformedPolicy) as e:
        policy_loader.load_policy(FIX / "policies-invalid" / "missing-files")
    assert "missing" in str(e.value).lower()


def test_load_catalog_discovers_all_subdirs(tmp_path: Path):
    # Symlink valid fixture under tmp catalog root, then load.
    root = tmp_path / "policies"
    root.mkdir()
    (root / "sample-policy").symlink_to(FIX / "policies-valid" / "sample-policy")
    catalog = policy_loader.load_catalog(root)
    assert "sample-policy" in catalog
    assert catalog["sample-policy"].slug == "sample-policy"


def test_lint_passes_on_valid_catalog(tmp_path: Path):
    root = tmp_path / "policies"
    root.mkdir()
    (root / "sample-policy").symlink_to(FIX / "policies-valid" / "sample-policy")
    assert policy_loader.lint(root) == []


def test_lint_flags_circular_requires(tmp_path: Path):
    # Build a tiny catalog: A requires B; B requires A.
    root = tmp_path / "policies"
    for slug, requires in [("a", ["b"]), ("b", ["a"])]:
        d = root / slug
        d.mkdir(parents=True)
        (d / "policy.yaml").write_text(
            f"slug: {slug}\ntitle: t\nversion: 1.0.0\ncategory: security\n"
            f"group: null\napplies_to: [microservice]\nrequires: {requires}\n"
            f"conflicts_with: []\ndescription: x\nfiles:\n"
            f"  claude_md_row: claude-md.row.md\n  docs: docs/{slug}.md\n"
        )
        (d / "claude-md.row.md").write_text(f"| sec | {slug} | x | 1.0.0 |\n")
        docs = d / "docs"
        docs.mkdir()
        (docs / f"{slug}.md").write_text("# x\n")
    failures = policy_loader.lint(root)
    assert any("circular" in f.lower() for f in failures)
```

Create the valid fixture `tests/fixtures/policies-valid/sample-policy/policy.yaml`:

```yaml
slug: sample-policy
title: "Sample"
version: 1.0.0
category: security
group: null
applies_to: [microservice]
requires: []
conflicts_with: []
description: A test fixture.
files:
  claude_md_row: claude-md.row.md
  docs: docs/sample-policy.md
```

Create `tests/fixtures/policies-valid/sample-policy/claude-md.row.md`:

```markdown
| security | sample-policy | `.claude/docs/policies/sample-policy.md` | 1.0.0 |
```

Create `tests/fixtures/policies-valid/sample-policy/docs/sample-policy.md`:

```markdown
# Sample

Test fixture body.
```

Create `tests/fixtures/policies-invalid/bad-version/policy.yaml`:

```yaml
slug: bad-version
title: "Bad"
version: not-a-semver
category: security
group: null
applies_to: [microservice]
requires: []
conflicts_with: []
description: x
files:
  claude_md_row: claude-md.row.md
  docs: docs/bad-version.md
```

Create `tests/fixtures/policies-invalid/missing-files/policy.yaml`:

```yaml
slug: missing-files
title: "Missing"
version: 1.0.0
category: security
group: null
applies_to: [microservice]
requires: []
conflicts_with: []
description: x
files:
  claude_md_row: nonexistent.md
  docs: docs/nonexistent.md
```

- [ ] **Step 2: Run tests — expected to fail (modules missing)**

Run: `.venv/bin/python -m pytest tests/test_policy_loader.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `scripts/policy_errors.py`**

```python
"""Error classes + exit codes for the policy catalog. Mirrors scripts/errors.py."""
from __future__ import annotations

EXIT_UNKNOWN_POLICY = 10
EXIT_UNKNOWN_PROFILE = 11
EXIT_EXCLUSIVE_GROUP_CONFLICT = 12
EXIT_REQUIRES_NOT_SATISFIED = 13
EXIT_USER_EDITED_BLOCKS_OP = 14
EXIT_CWD_AMBIGUOUS_OR_INVALID = 15
EXIT_POLICY_NOT_APPLIED = 16
EXIT_MIXED_OVERRIDE_FLAGS = 17
EXIT_CATALOG_DOWNGRADE = 18
EXIT_MALFORMED_PATCH = 19
EXIT_CONFLICTS_WITH_VIOLATION = 20


class PolicyError(Exception):
    exit_code: int = 99


class UnknownPolicy(PolicyError):
    exit_code = EXIT_UNKNOWN_POLICY


class UnknownProfile(PolicyError):
    exit_code = EXIT_UNKNOWN_PROFILE


class ExclusiveGroupConflict(PolicyError):
    exit_code = EXIT_EXCLUSIVE_GROUP_CONFLICT


class RequiresNotSatisfied(PolicyError):
    exit_code = EXIT_REQUIRES_NOT_SATISFIED


class UserEditedBlocksOp(PolicyError):
    exit_code = EXIT_USER_EDITED_BLOCKS_OP


class CwdAmbiguousOrInvalid(PolicyError):
    exit_code = EXIT_CWD_AMBIGUOUS_OR_INVALID


class PolicyNotApplied(PolicyError):
    exit_code = EXIT_POLICY_NOT_APPLIED


class MixedOverrideFlags(PolicyError):
    exit_code = EXIT_MIXED_OVERRIDE_FLAGS


class CatalogDowngrade(PolicyError):
    exit_code = EXIT_CATALOG_DOWNGRADE


class MalformedPatch(PolicyError):
    exit_code = EXIT_MALFORMED_PATCH


class ConflictsWithViolation(PolicyError):
    exit_code = EXIT_CONFLICTS_WITH_VIOLATION


class MalformedPolicy(PolicyError):
    """Catalog-side error: policy.yaml is malformed (used by loader + lint)."""
    exit_code = 99
```

- [ ] **Step 4: Implement `scripts/policy_loader.py`**

```python
"""Catalog loader + lint for scripts/policy_*.py.

Reads policy.yaml from a per-policy directory, validates schema, returns a
typed PolicyMeta dataclass. lint() walks an entire catalog directory and
returns human-readable failure strings (empty list on success).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

import policy_errors

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[\w.]+)?$")
VALID_CATEGORIES = {"security", "conventions", "workflow", "observability"}
REQUIRED_FIELDS = (
    "slug", "title", "version", "category", "group", "applies_to",
    "requires", "conflicts_with", "description", "files",
)


@dataclass
class PolicyMeta:
    slug: str
    title: str
    version: str
    category: str
    group: str | None
    applies_to: list[str]
    requires: list[str]
    conflicts_with: list[str]
    description: str
    files: dict[str, object]
    root: Path = field(default_factory=Path)


def load_policy(dir_path: Path) -> PolicyMeta:
    yaml_path = dir_path / "policy.yaml"
    if not yaml_path.exists():
        raise policy_errors.MalformedPolicy(f"{dir_path}: missing policy.yaml")
    try:
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise policy_errors.MalformedPolicy(f"{yaml_path}: YAML parse error: {e}") from e

    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: missing required fields: {missing}"
        )

    if not SEMVER.match(str(raw["version"])):
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: version {raw['version']!r} is not semver"
        )

    if raw["category"] not in VALID_CATEGORIES:
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: category {raw['category']!r} not in {sorted(VALID_CATEGORIES)}"
        )

    files = raw["files"] or {}
    # Required entries inside `files`.
    for key in ("claude_md_row", "docs"):
        if key not in files:
            raise policy_errors.MalformedPolicy(
                f"{yaml_path}: files.{key} is required"
            )

    # Existence check for every referenced path.
    referenced = []
    for key, val in files.items():
        if key == "extras":
            for pair in val or []:
                src = pair.split(":", 1)[0]
                referenced.append(src)
        elif val:
            referenced.append(val)
    missing_paths = [p for p in referenced if not (dir_path / p).exists()]
    if missing_paths:
        raise policy_errors.MalformedPolicy(
            f"{yaml_path}: referenced files missing: {missing_paths}"
        )

    return PolicyMeta(
        slug=str(raw["slug"]),
        title=str(raw["title"]),
        version=str(raw["version"]),
        category=str(raw["category"]),
        group=raw["group"] if raw["group"] is None else str(raw["group"]),
        applies_to=list(raw["applies_to"] or []),
        requires=list(raw["requires"] or []),
        conflicts_with=list(raw["conflicts_with"] or []),
        description=str(raw["description"]),
        files=dict(files),
        root=dir_path,
    )


def load_catalog(catalog_root: Path) -> dict[str, PolicyMeta]:
    out: dict[str, PolicyMeta] = {}
    for child in sorted(catalog_root.iterdir()):
        if not child.is_dir():
            continue
        meta = load_policy(child)
        if meta.slug in out:
            raise policy_errors.MalformedPolicy(
                f"duplicate slug {meta.slug!r} ({out[meta.slug].root} vs {child})"
            )
        out[meta.slug] = meta
    return out


def lint(catalog_root: Path) -> list[str]:
    failures: list[str] = []
    try:
        catalog = load_catalog(catalog_root)
    except policy_errors.MalformedPolicy as e:
        return [str(e)]

    # Circular requires detection.
    def visit(slug: str, stack: list[str]) -> None:
        if slug in stack:
            failures.append(f"circular requires: {' -> '.join(stack + [slug])}")
            return
        meta = catalog.get(slug)
        if meta is None:
            return
        for req in meta.requires:
            visit(req, stack + [slug])

    for slug in catalog:
        visit(slug, [])

    # conflicts_with referencing non-existent slug.
    for slug, meta in catalog.items():
        for c in meta.conflicts_with:
            if c not in catalog:
                failures.append(f"{slug}: conflicts_with unknown slug {c!r}")

    return failures
```

- [ ] **Step 5: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_loader.py -v`
Expected: 6 passed.

- [ ] **Step 6: Verify no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 156 passed (150 + 6 new).

- [ ] **Step 7: Commit**

```bash
git add scripts/policy_errors.py scripts/policy_loader.py tests/test_policy_loader.py tests/fixtures/policies-valid tests/fixtures/policies-invalid
git commit -m "$(cat <<'EOF'
feat(policy): add catalog loader + lint with policy.yaml schema validation

PolicyMeta dataclass mirrors spec §2 fields. lint() catches circular requires
and orphan conflicts_with slugs. MalformedPolicy carries fixture-friendly
error messages.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 3: Settings.json merge algebra

**Files:**
- Create: `scripts/policy_settings_merge.py`
- Create: `tests/test_policy_settings_merge.py`

**Interfaces:**
- Consumes: `policy_errors`
- Produces:
  - `policy_settings_merge.apply_patch(target: dict, patch: dict, expected_policy: str) -> dict` — deep-merge `patch` into `target`; reject if any array entry lacks `policy:` key OR if its `policy:` value disagrees with `expected_policy`; dedup by `(matcher, policy)` tuple; replace when version differs; append otherwise.
  - `policy_settings_merge.remove_policy(target: dict, slug: str) -> dict` — strip every array entry where `policy == slug`. Empty arrays preserved.
  - Both return the same `target` dict (mutated).

- [ ] **Step 1: Write the failing test**

Create `tests/test_policy_settings_merge.py`:

```python
"""Tests for scripts/policy_settings_merge.py."""
from __future__ import annotations

import pytest

import policy_errors  # type: ignore
import policy_settings_merge as sm  # type: ignore


def test_apply_patch_appends_into_empty_target():
    target: dict = {"hooks": {}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}
    sm.apply_patch(target, patch, expected_policy="p1")
    assert target == {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}


def test_apply_patch_appends_distinct_matcher():
    target = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "a.sh"}
    ]}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "p2", "version": "1.0.0", "matcher": "Edit", "command": "b.sh"}
    ]}}
    sm.apply_patch(target, patch, expected_policy="p2")
    assert len(target["hooks"]["PreToolUse"]) == 2


def test_apply_patch_dedupes_same_matcher_same_policy_same_version():
    base = {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "a.sh"}
    target = {"hooks": {"PreToolUse": [base.copy()]}}
    sm.apply_patch(target, {"hooks": {"PreToolUse": [base.copy()]}}, expected_policy="p1")
    assert len(target["hooks"]["PreToolUse"]) == 1


def test_apply_patch_replaces_on_version_change():
    target = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "old.sh"}
    ]}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "p1", "version": "1.1.0", "matcher": "Write", "command": "new.sh"}
    ]}}
    sm.apply_patch(target, patch, expected_policy="p1")
    assert target["hooks"]["PreToolUse"] == [
        {"policy": "p1", "version": "1.1.0", "matcher": "Write", "command": "new.sh"}
    ]


def test_apply_patch_rejects_entry_without_policy_field():
    target: dict = {"hooks": {}}
    patch = {"hooks": {"PreToolUse": [
        {"version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}
    with pytest.raises(policy_errors.MalformedPatch):
        sm.apply_patch(target, patch, expected_policy="p1")


def test_apply_patch_rejects_entry_with_wrong_policy_field():
    target: dict = {"hooks": {}}
    patch = {"hooks": {"PreToolUse": [
        {"policy": "wrong-slug", "version": "1.0.0", "matcher": "Write", "command": "x.sh"}
    ]}}
    with pytest.raises(policy_errors.MalformedPatch):
        sm.apply_patch(target, patch, expected_policy="p1")


def test_remove_policy_strips_matching_entries_only():
    target = {"hooks": {
        "PreToolUse": [
            {"policy": "p1", "version": "1.0.0", "matcher": "Write", "command": "a.sh"},
            {"policy": "p2", "version": "1.0.0", "matcher": "Edit", "command": "b.sh"},
        ],
        "PreCommit": [
            {"policy": "p1", "version": "1.0.0", "command": "c.sh"},
        ],
    }}
    sm.remove_policy(target, "p1")
    assert target["hooks"]["PreToolUse"] == [
        {"policy": "p2", "version": "1.0.0", "matcher": "Edit", "command": "b.sh"}
    ]
    assert target["hooks"]["PreCommit"] == []  # emptied, not deleted


def test_apply_patch_deep_merges_object_keys():
    target = {"permissions": {"allow": ["Read"]}}
    patch = {"permissions": {"allow": ["Write"], "deny": ["Bash"]}}
    sm.apply_patch(target, patch, expected_policy="p1")
    assert target["permissions"] == {"allow": ["Read", "Write"], "deny": ["Bash"]}
```

- [ ] **Step 2: Run tests — expected to fail (module missing)**

Run: `.venv/bin/python -m pytest tests/test_policy_settings_merge.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `scripts/policy_settings_merge.py`**

```python
"""Merge algebra for .claude/settings.json.

Each policy's settings.patch.json is applied with `apply_patch` and reversed
with `remove_policy`. Array entries must carry `policy: <slug>` markers;
dedup is by (matcher, policy) tuple. Object keys are deep-merged.
"""
from __future__ import annotations

import policy_errors


def _is_array_of_entries(val: object) -> bool:
    return isinstance(val, list) and all(isinstance(x, dict) for x in val)


def apply_patch(target: dict, patch: dict, expected_policy: str) -> dict:
    """Deep-merge `patch` into `target`. Mutates + returns `target`."""
    _merge(target, patch, expected_policy)
    return target


def _merge(target: dict, patch: dict, expected_policy: str) -> None:
    for key, val in patch.items():
        if isinstance(val, dict):
            sub = target.setdefault(key, {})
            if not isinstance(sub, dict):
                # Type mismatch — replace.
                target[key] = val
                continue
            _merge(sub, val, expected_policy)
        elif _is_array_of_entries(val):
            existing = target.setdefault(key, [])
            if not isinstance(existing, list):
                target[key] = val
                continue
            for entry in val:
                _check_policy_field(entry, expected_policy)
                _merge_array_entry(existing, entry)
        elif isinstance(val, list):
            existing = target.setdefault(key, [])
            if isinstance(existing, list):
                existing.extend(x for x in val if x not in existing)
            else:
                target[key] = val
        else:
            target[key] = val


def _check_policy_field(entry: dict, expected_policy: str) -> None:
    if "policy" not in entry:
        raise policy_errors.MalformedPatch(
            f"settings patch entry missing required 'policy' field: {entry}"
        )
    if entry["policy"] != expected_policy:
        raise policy_errors.MalformedPatch(
            f"settings patch entry has policy={entry['policy']!r} but the "
            f"patch is being applied for policy={expected_policy!r}"
        )


def _merge_array_entry(existing: list[dict], entry: dict) -> None:
    key = (entry.get("matcher"), entry["policy"])
    for i, other in enumerate(existing):
        other_key = (other.get("matcher"), other.get("policy"))
        if other_key == key:
            if other.get("version") != entry.get("version"):
                existing[i] = entry
            return
    existing.append(entry)


def remove_policy(target: dict, slug: str) -> dict:
    """Strip every array entry where policy == slug. Leaves empty arrays in place."""
    _strip(target, slug)
    return target


def _strip(node: dict, slug: str) -> None:
    for key, val in list(node.items()):
        if isinstance(val, dict):
            _strip(val, slug)
        elif _is_array_of_entries(val):
            node[key] = [e for e in val if e.get("policy") != slug]
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_settings_merge.py -v`
Expected: 8 passed.

- [ ] **Step 5: Verify no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 164 passed (156 + 8 new).

- [ ] **Step 6: Commit**

```bash
git add scripts/policy_settings_merge.py tests/test_policy_settings_merge.py
git commit -m "$(cat <<'EOF'
feat(policy): settings.json merge algebra with policy: markers

apply_patch deep-merges objects + dedupes arrays by (matcher, policy).
remove_policy strips every entry matching the slug. Rejects patches whose
entries miss the policy field or carry the wrong slug.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 4: CLAUDE.md table-row manager

**Files:**
- Create: `scripts/policy_claude_md.py`
- Create: `tests/test_policy_claude_md.py`

**Interfaces:**
- Consumes: `policy_state.sha256_str`
- Produces:
  - `policy_claude_md.upsert_row(claude_md: str, slug: str, row: str) -> tuple[str, str]` — returns `(new_claude_md, virtual_path_sha)`. Inserts/replaces a row in the `## Policies` table; creates the section if absent. `row` is the line from `claude-md.row.md` (no trailing newline). The returned `virtual_path_sha` is `sha256_str(row)` for state-recording.
  - `policy_claude_md.strip_row(claude_md: str, slug: str) -> str` — removes the matching row by slug column (the second column in the row). Leaves the section header and other rows intact.

- [ ] **Step 1: Write the failing test**

Create `tests/test_policy_claude_md.py`:

```python
"""Tests for scripts/policy_claude_md.py — ## Policies table mgmt."""
from __future__ import annotations

import policy_claude_md as pmd  # type: ignore


def test_upsert_creates_section_when_absent():
    src = "# demo\n\n## Lang\n\ngo\n"
    out, _sha = pmd.upsert_row(
        src,
        slug="memory-ordinary",
        row="| security | memory-ordinary | `.claude/docs/policies/memory-ordinary.md` | 1.0.0 |",
    )
    assert "## Policies" in out
    assert "| security | memory-ordinary |" in out


def test_upsert_inserts_under_existing_section():
    src = (
        "# demo\n\n## Policies\n\n"
        "Service-level policies in effect. Read the linked doc on demand.\n\n"
        "| Category | Slug | Reference | Version |\n"
        "|---|---|---|---|\n"
        "| security | secret-scan | `.claude/docs/policies/secret-scan.md` | 1.3.0 |\n"
    )
    out, _sha = pmd.upsert_row(
        src, "memory-ordinary",
        "| security | memory-ordinary | `.claude/docs/policies/memory-ordinary.md` | 1.0.0 |",
    )
    # Both rows present, both under the header.
    assert "secret-scan" in out
    assert "memory-ordinary" in out
    assert out.count("## Policies") == 1


def test_upsert_replaces_existing_row_for_same_slug():
    src = (
        "## Policies\n\n"
        "| Category | Slug | Reference | Version |\n"
        "|---|---|---|---|\n"
        "| security | memory-ordinary | old | 1.0.0 |\n"
    )
    out, _sha = pmd.upsert_row(
        src, "memory-ordinary",
        "| security | memory-ordinary | new | 1.1.0 |",
    )
    assert "old" not in out
    assert "new" in out
    # Still exactly one row for that slug.
    assert out.count("| memory-ordinary |") == 1


def test_strip_removes_only_matching_row():
    src = (
        "## Policies\n\n"
        "| Category | Slug | Reference | Version |\n"
        "|---|---|---|---|\n"
        "| security | memory-ordinary | x | 1.0.0 |\n"
        "| security | secret-scan | y | 1.3.0 |\n"
    )
    out = pmd.strip_row(src, "memory-ordinary")
    assert "memory-ordinary" not in out
    assert "secret-scan" in out


def test_strip_noop_when_slug_absent():
    src = "## Policies\n\n| Category | Slug | Reference | Version |\n|---|---|---|---|\n"
    out = pmd.strip_row(src, "memory-ordinary")
    assert out == src


def test_upsert_returns_sha_of_row():
    out, sha = pmd.upsert_row(
        "",
        "memory-ordinary",
        "| security | memory-ordinary | x | 1.0.0 |",
    )
    # sha is hex string, 64 chars
    assert len(sha) == 64
    int(sha, 16)  # parseable
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_policy_claude_md.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `scripts/policy_claude_md.py`**

```python
"""Manage the `## Policies` table inside CLAUDE.md.

Apply/upgrade inserts or replaces a row keyed by the slug column. Remove
strips the row. Section is auto-created with the documented header text
when absent.
"""
from __future__ import annotations

import re

import policy_state

SECTION_HEADER = "## Policies"
SECTION_INTRO = (
    "Service-level policies in effect. Read the linked doc on demand.\n\n"
    "| Category | Slug | Reference | Version |\n"
    "|---|---|---|---|"
)


def upsert_row(claude_md: str, slug: str, row: str) -> tuple[str, str]:
    """Insert (or replace by slug) `row` under the `## Policies` table.

    Returns the new file contents and the sha256 of the row (for state
    drift-detection of the virtual `CLAUDE.md#row:<slug>` path).
    """
    row = row.rstrip("\n")
    sha = policy_state.sha256_str(row)

    if SECTION_HEADER not in claude_md:
        # Append section to end of file.
        suffix = "" if claude_md.endswith("\n") else "\n"
        new = claude_md + f"{suffix}\n{SECTION_HEADER}\n\n{SECTION_INTRO}\n{row}\n"
        return new, sha

    # Section exists. Find and replace existing row for this slug, else
    # insert after the table's header rule line (`|---|---|...`).
    pattern = re.compile(
        r"^\|\s*[^|]+\s*\|\s*" + re.escape(slug) + r"\s*\|.*$",
        re.MULTILINE,
    )
    if pattern.search(claude_md):
        new = pattern.sub(row, claude_md)
        return new, sha

    # Insert after the header rule line.
    insert_re = re.compile(
        r"(##\s+Policies\b.*?\|---\|[-|]*\|\s*\n)", re.DOTALL,
    )
    m = insert_re.search(claude_md)
    if not m:
        # Section exists but no table yet; append the intro + row.
        new = claude_md.rstrip("\n") + f"\n\n{SECTION_INTRO}\n{row}\n"
        return new, sha
    new = claude_md[: m.end()] + row + "\n" + claude_md[m.end() :]
    return new, sha


def strip_row(claude_md: str, slug: str) -> str:
    pattern = re.compile(
        r"^\|\s*[^|]+\s*\|\s*" + re.escape(slug) + r"\s*\|.*\n",
        re.MULTILINE,
    )
    return pattern.sub("", claude_md)
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_claude_md.py -v`
Expected: 6 passed.

- [ ] **Step 5: Verify no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 170 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/policy_claude_md.py tests/test_policy_claude_md.py
git commit -m "$(cat <<'EOF'
feat(policy): manage ## Policies table in CLAUDE.md

upsert_row inserts or replaces a row keyed by slug column; auto-creates the
section + table when absent. strip_row removes only the matching row.
Returns the virtual-row sha for state drift detection.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 5: Apply core (single-policy happy path + idempotency)

**Files:**
- Create: `scripts/policy_apply.py`
- Create: `tests/test_policy_apply.py` (add only happy-path + idempotency tests in this task)

**Interfaces:**
- Consumes: `policy_loader.PolicyMeta`, `policy_settings_merge`, `policy_claude_md`, `policy_state`
- Produces:
  - `policy_apply.apply(project_dir: Path, meta: PolicyMeta, source: str = "cli") -> ApplyReport`
  - `ApplyReport` dataclass: `applied_files`, `skipped_files`, `swap_from`, `swap_to`, `was_noop`.
  - The function is **single-policy only** in this task — exclusive-group + requires/conflicts handled in Task 8.

- [ ] **Step 1: Write the failing test**

Create `tests/test_policy_apply.py`:

```python
"""Tests for scripts/policy_apply.py (Task 5 covers single-policy happy path
+ idempotency only; exclusive-group + requires land in Task 8)."""
from __future__ import annotations

import json
from pathlib import Path

import policy_apply  # type: ignore
import policy_loader  # type: ignore
import policy_state  # type: ignore


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "CLAUDE.md").write_text("# proj\n\n## Lang\n\ngo\n")
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}))
    (project / ".sn-init-state.json").write_text(json.dumps({"mode": "new"}))
    return project


def _make_minimal_policy(catalog_root: Path, slug: str = "p1") -> policy_loader.PolicyMeta:
    d = catalog_root / slug
    (d / "docs").mkdir(parents=True)
    (d / "policy.yaml").write_text(
        f"slug: {slug}\ntitle: t\nversion: 1.0.0\ncategory: security\n"
        f"group: null\napplies_to: [microservice]\nrequires: []\n"
        f"conflicts_with: []\ndescription: x\nfiles:\n"
        f"  claude_md_row: claude-md.row.md\n  docs: docs/{slug}.md\n"
    )
    (d / "claude-md.row.md").write_text(
        f"| security | {slug} | `.claude/docs/policies/{slug}.md` | 1.0.0 |\n"
    )
    (d / "docs" / f"{slug}.md").write_text(f"# {slug}\n\nbody\n")
    return policy_loader.load_policy(d)


def test_apply_writes_claude_md_row(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    text = (project / "CLAUDE.md").read_text()
    assert "| security | p1 |" in text


def test_apply_writes_docs_file(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    docs = project / ".claude" / "docs" / "policies" / "p1.md"
    assert docs.exists()
    assert "body" in docs.read_text()


def test_apply_records_state(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta, source="cli")
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert any(p["slug"] == "p1" for p in state["applied_policies"])
    assert state["policy_history"][-1]["action"] == "apply"
    assert state["policy_history"][-1]["source"] == "cli"


def test_apply_idempotent_same_version_returns_noop(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    report = policy_apply.apply(project, meta)
    assert report.was_noop is True


def test_apply_idempotent_does_not_grow_state(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    policy_apply.apply(project, meta)
    state = json.loads((project / ".sn-init-state.json").read_text())
    # exactly one applied entry, one history event
    assert len([p for p in state["applied_policies"] if p["slug"] == "p1"]) == 1
    assert len([h for h in state["policy_history"] if h.get("slug") == "p1"]) == 1
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `scripts/policy_apply.py`**

```python
"""Apply / remove / upgrade orchestration across the five policy layers.

This module owns the lifecycle of a single policy in a single project.
Exclusive-group, requires, and conflicts_with handling are layered on top
in Task 8 (`apply_many`).
"""
from __future__ import annotations

import json
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import policy_claude_md
import policy_loader
import policy_settings_merge
import policy_state

DOCS_DIR = ".claude/docs/policies"
RULES_DIR = ".claude/rules"
SETTINGS_PATH = ".claude/settings.json"


@dataclass
class ApplyReport:
    slug: str = ""
    applied_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    swap_from: str | None = None
    swap_to: str | None = None
    was_noop: bool = False


def apply(project_dir: Path, meta: policy_loader.PolicyMeta, source: str = "cli") -> ApplyReport:
    state = policy_state.read_state(project_dir)
    report = ApplyReport(slug=meta.slug)

    # Already applied at same version?
    existing = _find_applied(state, meta.slug)
    if existing and existing["version"] == meta.version:
        report.was_noop = True
        return report

    content_sha: dict[str, str] = {}

    # CLAUDE.md row.
    claude_md_path = project_dir / "CLAUDE.md"
    src_text = claude_md_path.read_text(encoding="utf-8") if claude_md_path.exists() else ""
    row = (meta.root / meta.files["claude_md_row"]).read_text(encoding="utf-8").strip("\n")
    new_text, row_sha = policy_claude_md.upsert_row(src_text, meta.slug, row)
    claude_md_path.write_text(new_text, encoding="utf-8")
    content_sha[f"CLAUDE.md#row:{meta.slug}"] = row_sha
    report.applied_files.append("CLAUDE.md#row")

    # Docs.
    docs_dst = project_dir / DOCS_DIR / f"{meta.slug}.md"
    docs_dst.parent.mkdir(parents=True, exist_ok=True)
    docs_src = meta.root / meta.files["docs"]
    if docs_dst.exists():
        report.skipped_files.append(str(docs_dst.relative_to(project_dir)))
    else:
        shutil.copyfile(docs_src, docs_dst)
        content_sha[str(docs_dst.relative_to(project_dir))] = policy_state.sha256_file(docs_dst)
        report.applied_files.append(str(docs_dst.relative_to(project_dir)))

    # Rules (optional).
    if meta.files.get("rules"):
        rules_dst = project_dir / RULES_DIR / f"{meta.slug}.md"
        rules_dst.parent.mkdir(parents=True, exist_ok=True)
        if rules_dst.exists():
            report.skipped_files.append(str(rules_dst.relative_to(project_dir)))
        else:
            shutil.copyfile(meta.root / meta.files["rules"], rules_dst)
            content_sha[str(rules_dst.relative_to(project_dir))] = policy_state.sha256_file(rules_dst)
            report.applied_files.append(str(rules_dst.relative_to(project_dir)))

    # Settings patch (optional).
    settings_marker: str | None = None
    if meta.files.get("settings_patch"):
        patch = json.loads((meta.root / meta.files["settings_patch"]).read_text(encoding="utf-8"))
        settings_path = project_dir / SETTINGS_PATH
        existing_settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        policy_settings_merge.apply_patch(existing_settings, patch, expected_policy=meta.slug)
        settings_path.write_text(json.dumps(existing_settings, indent=2) + "\n", encoding="utf-8")
        settings_marker = meta.slug
        report.applied_files.append(SETTINGS_PATH)

    # Extras (optional).
    for pair in meta.files.get("extras") or []:
        src_rel, dst_rel = pair.split(":", 1)
        dst = project_dir / dst_rel
        if dst.exists():
            report.skipped_files.append(dst_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(meta.root / src_rel, dst)
        if dst_rel.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content_sha[dst_rel] = policy_state.sha256_file(dst)
        report.applied_files.append(dst_rel)

    # Record in state.
    now = datetime.now(timezone.utc).isoformat()
    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != meta.slug]
    state["applied_policies"].append({
        "slug": meta.slug,
        "version": meta.version,
        "applied_at": now,
        "content_sha": content_sha,
        "settings_marker": settings_marker,
    })
    state["applied_policies"].sort(key=lambda p: p["slug"])
    state["policy_history"].append({
        "action": "apply",
        "slug": meta.slug,
        "version": meta.version,
        "at": now,
        "source": source,
    })
    policy_state.write_state(project_dir, state)
    return report


def _find_applied(state: dict, slug: str) -> dict | None:
    for p in state["applied_policies"]:
        if p["slug"] == slug:
            return p
    return None
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 5 passed.

- [ ] **Step 5: Verify no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 175 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/policy_apply.py tests/test_policy_apply.py
git commit -m "$(cat <<'EOF'
feat(policy): single-policy apply (claude-md row + docs + rules + settings + extras)

ApplyReport tracks applied/skipped files per layer. Idempotent: re-apply at
same version is a no-op (state grows by exactly one entry the first time and
zero thereafter). Exclusive-group + requires/conflicts handling lands in
Task 8.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 6: Remove core (with edit-detection + `--force`)

**Files:**
- Modify: `scripts/policy_apply.py` (add `remove` function)
- Modify: `tests/test_policy_apply.py` (add remove tests)

**Interfaces:**
- Consumes: state's `content_sha` map
- Produces:
  - `policy_apply.remove(project_dir: Path, slug: str, *, force: bool = False, source: str = "cli") -> RemoveReport`
  - `RemoveReport` dataclass: `slug`, `deleted_files`, `skipped_files`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_policy_apply.py`:

```python
import pytest
import policy_errors  # type: ignore


def test_remove_deletes_unedited_files(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    report = policy_apply.remove(project, "p1")
    assert ".claude/docs/policies/p1.md" in report.deleted_files
    assert not (project / ".claude" / "docs" / "policies" / "p1.md").exists()
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert not any(p["slug"] == "p1" for p in state["applied_policies"])
    assert state["policy_history"][-1]["action"] == "remove"


def test_remove_skips_user_edited_without_force(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    edited = project / ".claude" / "docs" / "policies" / "p1.md"
    edited.write_text("# edited by user\n")
    report = policy_apply.remove(project, "p1")
    assert ".claude/docs/policies/p1.md" in report.skipped_files
    assert edited.exists()  # not deleted
    state = json.loads((project / ".sn-init-state.json").read_text())
    # State still strips the entry.
    assert not any(p["slug"] == "p1" for p in state["applied_policies"])


def test_remove_force_overrides_edits(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    edited = project / ".claude" / "docs" / "policies" / "p1.md"
    edited.write_text("# edited by user\n")
    policy_apply.remove(project, "p1", force=True)
    assert not edited.exists()


def test_remove_unknown_slug_errors(tmp_path: Path):
    project = _setup_project(tmp_path)
    with pytest.raises(policy_errors.PolicyNotApplied):
        policy_apply.remove(project, "never-applied")


def test_remove_strips_claude_md_row(tmp_path: Path):
    project = _setup_project(tmp_path)
    meta = _make_minimal_policy(tmp_path / "catalog")
    policy_apply.apply(project, meta)
    policy_apply.remove(project, "p1")
    assert "| security | p1 |" not in (project / "CLAUDE.md").read_text()
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 5 new tests fail (`remove` not defined).

- [ ] **Step 3: Add `remove` to `scripts/policy_apply.py`**

Append to `scripts/policy_apply.py`:

```python
@dataclass
class RemoveReport:
    slug: str = ""
    deleted_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


def remove(project_dir: Path, slug: str, *, force: bool = False, source: str = "cli") -> RemoveReport:
    import policy_errors

    state = policy_state.read_state(project_dir)
    entry = _find_applied(state, slug)
    if entry is None:
        raise policy_errors.PolicyNotApplied(
            f"'{slug}' is not applied to this project"
        )

    report = RemoveReport(slug=slug)
    content_sha: dict = entry.get("content_sha") or {}

    for rel, expected_sha in content_sha.items():
        if rel.startswith("CLAUDE.md#row:"):
            # Handled below alongside the actual CLAUDE.md edit.
            continue
        path = project_dir / rel
        if not path.exists():
            continue
        actual_sha = policy_state.sha256_file(path)
        if actual_sha != expected_sha and not force:
            report.skipped_files.append(rel)
            continue
        path.unlink()
        report.deleted_files.append(rel)

    # Strip CLAUDE.md row + settings.json entries.
    claude_md = project_dir / "CLAUDE.md"
    if claude_md.exists():
        claude_md.write_text(
            policy_claude_md.strip_row(claude_md.read_text(encoding="utf-8"), slug),
            encoding="utf-8",
        )
    if entry.get("settings_marker"):
        settings_path = project_dir / SETTINGS_PATH
        if settings_path.exists():
            data = json.loads(settings_path.read_text())
            policy_settings_merge.remove_policy(data, slug)
            settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != slug]
    now = datetime.now(timezone.utc).isoformat()
    state["policy_history"].append({
        "action": "remove",
        "slug": slug,
        "version": entry["version"],
        "at": now,
        "skipped_files": report.skipped_files,
        "source": source,
    })
    policy_state.write_state(project_dir, state)
    return report
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 10 passed.

- [ ] **Step 5: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 180 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/policy_apply.py tests/test_policy_apply.py
git commit -m "$(cat <<'EOF'
feat(policy): remove with edit detection + --force override

Removal walks recorded content_sha and skips files whose sha drifted (user
edits). Strips CLAUDE.md row + settings.json entries unconditionally. State
always loses the applied entry; history records skipped_files.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 7: Upgrade core + status

**Files:**
- Modify: `scripts/policy_apply.py` (add `upgrade` + `status` functions)
- Modify: `tests/test_policy_apply.py` (add upgrade + status tests)

**Interfaces:**
- Produces:
  - `policy_apply.upgrade(project_dir: Path, new_meta: PolicyMeta, *, force: bool = False) -> UpgradeReport`
  - `policy_apply.status(project_dir: Path, catalog: dict[str, PolicyMeta]) -> list[StatusEntry]`
  - `UpgradeReport`: `slug`, `from_version`, `to_version`, `refreshed_files`, `skipped_files`.
  - `StatusEntry`: `slug`, `applied_version`, `catalog_version`, `state` (`"current" | "obsolete" | "unknown" | "drifted"`).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_policy_apply.py`:

```python
def _make_policy_with_version(catalog_root: Path, slug: str, version: str) -> policy_loader.PolicyMeta:
    d = catalog_root / slug
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "policy.yaml").write_text(
        f"slug: {slug}\ntitle: t\nversion: {version}\ncategory: security\n"
        f"group: null\napplies_to: [microservice]\nrequires: []\n"
        f"conflicts_with: []\ndescription: x\nfiles:\n"
        f"  claude_md_row: claude-md.row.md\n  docs: docs/{slug}.md\n"
    )
    (d / "claude-md.row.md").write_text(
        f"| security | {slug} | `.claude/docs/policies/{slug}.md` | {version} |\n"
    )
    (d / "docs" / f"{slug}.md").write_text(f"# {slug}\n\nbody {version}\n")
    return policy_loader.load_policy(d)


def test_upgrade_refreshes_files_and_state(tmp_path: Path):
    project = _setup_project(tmp_path)
    v1 = _make_policy_with_version(tmp_path / "cat1", "p1", "1.0.0")
    policy_apply.apply(project, v1)
    v2 = _make_policy_with_version(tmp_path / "cat2", "p1", "1.1.0")
    report = policy_apply.upgrade(project, v2)
    assert report.from_version == "1.0.0"
    assert report.to_version == "1.1.0"
    assert "body 1.1.0" in (project / ".claude" / "docs" / "policies" / "p1.md").read_text()
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert any(p["slug"] == "p1" and p["version"] == "1.1.0" for p in state["applied_policies"])
    assert state["policy_history"][-1]["action"] == "upgrade"


def test_upgrade_skips_user_edited_files(tmp_path: Path):
    project = _setup_project(tmp_path)
    v1 = _make_policy_with_version(tmp_path / "cat1", "p1", "1.0.0")
    policy_apply.apply(project, v1)
    (project / ".claude" / "docs" / "policies" / "p1.md").write_text("# user edit\n")
    v2 = _make_policy_with_version(tmp_path / "cat2", "p1", "1.1.0")
    report = policy_apply.upgrade(project, v2)
    assert ".claude/docs/policies/p1.md" in report.skipped_files
    # Version still bumps in state (spec §7).
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert any(p["slug"] == "p1" and p["version"] == "1.1.0" for p in state["applied_policies"])


def test_upgrade_force_overrides_edited(tmp_path: Path):
    project = _setup_project(tmp_path)
    v1 = _make_policy_with_version(tmp_path / "cat1", "p1", "1.0.0")
    policy_apply.apply(project, v1)
    (project / ".claude" / "docs" / "policies" / "p1.md").write_text("# user edit\n")
    v2 = _make_policy_with_version(tmp_path / "cat2", "p1", "1.1.0")
    policy_apply.upgrade(project, v2, force=True)
    assert "body 1.1.0" in (project / ".claude" / "docs" / "policies" / "p1.md").read_text()


def test_upgrade_downgrade_errors(tmp_path: Path):
    project = _setup_project(tmp_path)
    v2 = _make_policy_with_version(tmp_path / "cat2", "p1", "1.1.0")
    policy_apply.apply(project, v2)
    v1 = _make_policy_with_version(tmp_path / "cat1", "p1", "1.0.0")
    with pytest.raises(policy_errors.CatalogDowngrade):
        policy_apply.upgrade(project, v1)


def test_status_classifies(tmp_path: Path):
    project = _setup_project(tmp_path)
    v1 = _make_policy_with_version(tmp_path / "cat", "current", "1.0.0")
    v1_obsolete = _make_policy_with_version(tmp_path / "cat", "obsolete-one", "1.0.0")
    policy_apply.apply(project, v1)
    policy_apply.apply(project, v1_obsolete)

    catalog = {
        "current": v1,
        "obsolete-one": _make_policy_with_version(tmp_path / "cat-new", "obsolete-one", "2.0.0"),
        # "current" still 1.0.0; obsolete-one bumped to 2.0.0; another slug in
        # state would be unknown if absent here. Add "ghost":
    }
    # Add a ghost entry to state — applied but no catalog match.
    state = json.loads((project / ".sn-init-state.json").read_text())
    state["applied_policies"].append({
        "slug": "ghost", "version": "1.0.0", "applied_at": "now",
        "content_sha": {}, "settings_marker": None,
    })
    (project / ".sn-init-state.json").write_text(json.dumps(state))

    rows = policy_apply.status(project, catalog)
    by_slug = {r.slug: r for r in rows}
    assert by_slug["current"].state == "current"
    assert by_slug["obsolete-one"].state == "obsolete"
    assert by_slug["ghost"].state == "unknown"
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 5 new tests fail.

- [ ] **Step 3: Add `upgrade` + `status` to `scripts/policy_apply.py`**

Append:

```python
@dataclass
class UpgradeReport:
    slug: str = ""
    from_version: str = ""
    to_version: str = ""
    refreshed_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


@dataclass
class StatusEntry:
    slug: str
    applied_version: str
    catalog_version: str | None
    state: str  # "current" | "obsolete" | "unknown" | "drifted"


def upgrade(project_dir: Path, new_meta: policy_loader.PolicyMeta, *, force: bool = False) -> UpgradeReport:
    import policy_errors

    state = policy_state.read_state(project_dir)
    entry = _find_applied(state, new_meta.slug)
    if entry is None:
        raise policy_errors.PolicyNotApplied(f"'{new_meta.slug}' is not applied")
    if entry["version"] == new_meta.version:
        return UpgradeReport(
            slug=new_meta.slug, from_version=entry["version"], to_version=new_meta.version,
        )
    if _semver_tuple(entry["version"]) > _semver_tuple(new_meta.version):
        raise policy_errors.CatalogDowngrade(
            f"state has {new_meta.slug}@{entry['version']} but catalog only "
            f"has {new_meta.version}"
        )

    report = UpgradeReport(
        slug=new_meta.slug,
        from_version=entry["version"],
        to_version=new_meta.version,
    )

    content_sha: dict[str, str] = {}

    # CLAUDE.md row.
    claude_md = project_dir / "CLAUDE.md"
    src = claude_md.read_text(encoding="utf-8")
    row = (new_meta.root / new_meta.files["claude_md_row"]).read_text(encoding="utf-8").strip("\n")
    new_text, row_sha = policy_claude_md.upsert_row(src, new_meta.slug, row)
    claude_md.write_text(new_text, encoding="utf-8")
    content_sha[f"CLAUDE.md#row:{new_meta.slug}"] = row_sha
    report.refreshed_files.append("CLAUDE.md#row")

    # File-by-file refresh.
    file_entries: list[tuple[str, str]] = []  # (rel_path, src_path)
    file_entries.append(
        (f"{DOCS_DIR}/{new_meta.slug}.md", str(new_meta.root / new_meta.files["docs"]))
    )
    if new_meta.files.get("rules"):
        file_entries.append(
            (f"{RULES_DIR}/{new_meta.slug}.md", str(new_meta.root / new_meta.files["rules"]))
        )
    for pair in new_meta.files.get("extras") or []:
        src_rel, dst_rel = pair.split(":", 1)
        file_entries.append((dst_rel, str(new_meta.root / src_rel)))

    for rel, src in file_entries:
        dst = project_dir / rel
        recorded = (entry.get("content_sha") or {}).get(rel)
        if dst.exists():
            actual = policy_state.sha256_file(dst)
            if recorded and actual != recorded and not force:
                report.skipped_files.append(rel)
                continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        if rel.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content_sha[rel] = policy_state.sha256_file(dst)
        report.refreshed_files.append(rel)

    # Settings patch (replace by (matcher, policy); _settings_merge handles version bump).
    settings_marker = entry.get("settings_marker")
    if new_meta.files.get("settings_patch"):
        patch = json.loads((new_meta.root / new_meta.files["settings_patch"]).read_text())
        settings_path = project_dir / SETTINGS_PATH
        data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        policy_settings_merge.apply_patch(data, patch, expected_policy=new_meta.slug)
        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        settings_marker = new_meta.slug

    now = datetime.now(timezone.utc).isoformat()
    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != new_meta.slug]
    state["applied_policies"].append({
        "slug": new_meta.slug,
        "version": new_meta.version,
        "applied_at": now,
        "content_sha": content_sha,
        "settings_marker": settings_marker,
    })
    state["applied_policies"].sort(key=lambda p: p["slug"])
    state["policy_history"].append({
        "action": "upgrade",
        "slug": new_meta.slug,
        "from": entry["version"],
        "to": new_meta.version,
        "at": now,
        "skipped_files": report.skipped_files,
        "source": "cli",
    })
    policy_state.write_state(project_dir, state)
    return report


def status(project_dir: Path, catalog: dict[str, policy_loader.PolicyMeta]) -> list[StatusEntry]:
    state = policy_state.read_state(project_dir)
    out: list[StatusEntry] = []
    for p in state["applied_policies"]:
        slug = p["slug"]
        meta = catalog.get(slug)
        if meta is None:
            out.append(StatusEntry(slug, p["version"], None, "unknown"))
            continue
        # drift detection
        drift = False
        for rel, sha in (p.get("content_sha") or {}).items():
            if rel.startswith("CLAUDE.md#row:"):
                continue
            path = project_dir / rel
            if path.exists() and policy_state.sha256_file(path) != sha:
                drift = True
                break
        cv = meta.version
        if p["version"] == cv:
            out.append(StatusEntry(slug, p["version"], cv, "drifted" if drift else "current"))
        elif _semver_tuple(p["version"]) < _semver_tuple(cv):
            out.append(StatusEntry(slug, p["version"], cv, "obsolete"))
        else:
            out.append(StatusEntry(slug, p["version"], cv, "unknown"))
    return out


def _semver_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("-")[0].split("."))
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 15 passed.

- [ ] **Step 5: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 185 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/policy_apply.py tests/test_policy_apply.py
git commit -m "$(cat <<'EOF'
feat(policy): upgrade + status

Upgrade refreshes files in place; skips user-edited files (sha mismatch);
state version always bumps. CatalogDowngrade raised when state newer than
catalog. Status classifies each applied policy as current/obsolete/
unknown/drifted by comparing recorded sha + applied version vs catalog.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 8: Multi-policy apply with exclusive-group swap, requires, conflicts

**Files:**
- Modify: `scripts/policy_apply.py` (add `apply_many` orchestrator)
- Modify: `tests/test_policy_apply.py` (add 6 multi-policy tests)

**Interfaces:**
- Produces:
  - `policy_apply.apply_many(project_dir: Path, slugs: list[str], catalog: dict[str, PolicyMeta], *, with_deps: bool = False, source: str = "cli") -> list[ApplyReport]`
  - Resolves exclusive-group swaps (remove incumbent, apply new).
  - Resolves `requires` (with `--with-deps`) or raises `RequiresNotSatisfied`.
  - Resolves `conflicts_with` (raises `ConflictsWithViolation`).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_policy_apply.py`:

```python
def test_apply_many_swaps_exclusive_group(tmp_path: Path):
    project = _setup_project(tmp_path)
    cat = tmp_path / "catalog"
    p_ord = _make_minimal_policy(cat, "p-ordinary")
    p_reg = _make_minimal_policy(cat, "p-regulated")
    # Put both in group "tier" — rewrite their yaml.
    for p in (p_ord, p_reg):
        text = (p.root / "policy.yaml").read_text().replace("group: null", "group: tier")
        (p.root / "policy.yaml").write_text(text)
        # Reload after edit.
    p_ord = policy_loader.load_policy(cat / "p-ordinary")
    p_reg = policy_loader.load_policy(cat / "p-regulated")
    catalog = {"p-ordinary": p_ord, "p-regulated": p_reg}

    policy_apply.apply_many(project, ["p-ordinary"], catalog)
    policy_apply.apply_many(project, ["p-regulated"], catalog)
    state = json.loads((project / ".sn-init-state.json").read_text())
    slugs = [p["slug"] for p in state["applied_policies"]]
    assert "p-regulated" in slugs
    assert "p-ordinary" not in slugs
    assert any(h["action"] == "swap" for h in state["policy_history"])


def test_apply_many_requires_without_with_deps_errors(tmp_path: Path):
    project = _setup_project(tmp_path)
    cat = tmp_path / "catalog"
    dep = _make_minimal_policy(cat, "dep")
    head = _make_minimal_policy(cat, "head")
    text = (head.root / "policy.yaml").read_text().replace("requires: []", "requires: [dep]")
    (head.root / "policy.yaml").write_text(text)
    head = policy_loader.load_policy(cat / "head")
    catalog = {"dep": dep, "head": head}
    with pytest.raises(policy_errors.RequiresNotSatisfied):
        policy_apply.apply_many(project, ["head"], catalog)


def test_apply_many_with_deps_auto_installs(tmp_path: Path):
    project = _setup_project(tmp_path)
    cat = tmp_path / "catalog"
    dep = _make_minimal_policy(cat, "dep")
    head = _make_minimal_policy(cat, "head")
    text = (head.root / "policy.yaml").read_text().replace("requires: []", "requires: [dep]")
    (head.root / "policy.yaml").write_text(text)
    head = policy_loader.load_policy(cat / "head")
    catalog = {"dep": dep, "head": head}
    policy_apply.apply_many(project, ["head"], catalog, with_deps=True)
    state = json.loads((project / ".sn-init-state.json").read_text())
    slugs = [p["slug"] for p in state["applied_policies"]]
    assert "dep" in slugs
    assert "head" in slugs


def test_apply_many_conflicts_with_errors(tmp_path: Path):
    project = _setup_project(tmp_path)
    cat = tmp_path / "catalog"
    a = _make_minimal_policy(cat, "a")
    b = _make_minimal_policy(cat, "b")
    text = (b.root / "policy.yaml").read_text().replace("conflicts_with: []", "conflicts_with: [a]")
    (b.root / "policy.yaml").write_text(text)
    b = policy_loader.load_policy(cat / "b")
    catalog = {"a": a, "b": b}
    policy_apply.apply_many(project, ["a"], catalog)
    with pytest.raises(policy_errors.ConflictsWithViolation):
        policy_apply.apply_many(project, ["b"], catalog)


def test_apply_many_unknown_slug_errors(tmp_path: Path):
    project = _setup_project(tmp_path)
    cat = tmp_path / "catalog"
    catalog = {"only": _make_minimal_policy(cat, "only")}
    with pytest.raises(policy_errors.UnknownPolicy):
        policy_apply.apply_many(project, ["never-heard-of"], catalog)


def test_apply_many_returns_one_report_per_slug(tmp_path: Path):
    project = _setup_project(tmp_path)
    cat = tmp_path / "catalog"
    catalog = {
        "a": _make_minimal_policy(cat, "a"),
        "b": _make_minimal_policy(cat, "b"),
    }
    reports = policy_apply.apply_many(project, ["a", "b"], catalog)
    assert {r.slug for r in reports} == {"a", "b"}
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 6 new tests fail (`apply_many` not defined).

- [ ] **Step 3: Add `apply_many` to `scripts/policy_apply.py`**

Append:

```python
def apply_many(
    project_dir: Path,
    slugs: list[str],
    catalog: dict[str, policy_loader.PolicyMeta],
    *,
    with_deps: bool = False,
    source: str = "cli",
) -> list[ApplyReport]:
    import policy_errors

    # 1. Validate every slug exists in catalog.
    for s in slugs:
        if s not in catalog:
            raise policy_errors.UnknownPolicy(
                f"unknown policy {s!r}; see `sn-setup policy list`"
            )

    # 2. Expand requires (BFS) when --with-deps; else verify they are already
    #    in applied_policies.
    state = policy_state.read_state(project_dir)
    applied_slugs = {p["slug"] for p in state["applied_policies"]}

    ordered: list[str] = []
    seen: set[str] = set()

    def visit(slug: str) -> None:
        if slug in seen:
            return
        meta = catalog[slug]
        for req in meta.requires:
            if req in applied_slugs:
                continue
            if not with_deps:
                if req not in slugs:
                    raise policy_errors.RequiresNotSatisfied(
                        f"'{slug}' requires {req!r} which is not applied; "
                        "pass --with-deps to auto-install"
                    )
            else:
                if req in catalog:
                    visit(req)
                else:
                    raise policy_errors.UnknownPolicy(
                        f"required dep {req!r} of {slug!r} not in catalog"
                    )
        if slug not in seen:
            ordered.append(slug)
            seen.add(slug)

    for s in slugs:
        visit(s)

    # 3. Plan exclusive-group swaps.
    swap_plan: list[tuple[str, str]] = []  # (incumbent, replacement)
    for s in ordered:
        meta = catalog[s]
        if meta.group is None:
            continue
        for p in list(state["applied_policies"]):
            if p["slug"] == s:
                continue
            other_meta = catalog.get(p["slug"])
            if other_meta and other_meta.group == meta.group:
                swap_plan.append((p["slug"], s))

    # 4. conflicts_with check.
    for s in ordered:
        meta = catalog[s]
        for c in meta.conflicts_with:
            if c in applied_slugs and not any(c == inc for inc, _ in swap_plan):
                raise policy_errors.ConflictsWithViolation(
                    f"'{s}' conflicts with already-applied '{c}'"
                )

    # 5. Execute swaps (remove incumbent) — non-force; user-edited files preserved.
    for incumbent, replacement in swap_plan:
        remove(project_dir, incumbent, source=source)
        # Re-read state after each remove to keep history clean.
        state = policy_state.read_state(project_dir)
        # Record explicit swap event (replaces the earlier `remove`).
        now = datetime.now(timezone.utc).isoformat()
        state["policy_history"].append({
            "action": "swap",
            "from": incumbent,
            "to": replacement,
            "at": now,
            "source": source,
        })
        policy_state.write_state(project_dir, state)

    # 6. Apply in dependency order.
    reports: list[ApplyReport] = []
    for s in ordered:
        reports.append(apply(project_dir, catalog[s], source=source))
    return reports
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_apply.py -v`
Expected: 21 passed.

- [ ] **Step 5: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 191 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/policy_apply.py tests/test_policy_apply.py
git commit -m "$(cat <<'EOF'
feat(policy): apply_many with exclusive-group swap + requires + conflicts

apply_many resolves dependency order, validates conflicts_with, swaps any
exclusive-group incumbents, then applies each policy in turn. --with-deps
walks the requires graph; otherwise a missing dep raises
RequiresNotSatisfied.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 9: `sn-setup policy` CLI sub-tree

**Files:**
- Create: `scripts/policy_cli.py`
- Create: `tests/test_policy_cli.py`
- Modify: `scripts/sn_init.py` (dispatch `policy` first positional → `policy_cli.main`)

**Interfaces:**
- Produces:
  - `policy_cli.main(argv: list[str]) -> int` — accepts argv beginning with a sub-command (`list`, `show`, `apply`, `remove`, `upgrade`, `status`, `show-applied`, `history`, `lint`).
  - Returns process exit code.
  - Catalog root is `skills/sn-setup/templates/policies/` relative to the plugin root.

- [ ] **Step 1: Write failing tests**

Create `tests/test_policy_cli.py`:

```python
"""Tests for scripts/policy_cli.py — top-level sub-command dispatcher."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

import policy_cli  # type: ignore
import policy_errors  # type: ignore
import sn_init  # type: ignore

CATALOG_FIX = Path(__file__).parent / "fixtures" / "policies-valid"


def _scaffold_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "CLAUDE.md").write_text("# proj\n")
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}))
    (project / ".sn-init-state.json").write_text(json.dumps({"mode": "new"}))
    return project


def _run_cli(tmp_path: Path, *argv: str, cwd: Path | None = None,
             catalog: Path = CATALOG_FIX) -> int:
    old = Path.cwd()
    os.environ["SN_POLICY_CATALOG_ROOT"] = str(catalog)
    try:
        os.chdir(cwd or tmp_path)
        return policy_cli.main(list(argv))
    finally:
        os.chdir(old)
        del os.environ["SN_POLICY_CATALOG_ROOT"]


def test_policy_list_outputs_slugs(tmp_path: Path, capsys):
    rc = _run_cli(tmp_path, "list")
    assert rc == 0
    out = capsys.readouterr().out
    assert "sample-policy" in out


def test_policy_show_prints_metadata(tmp_path: Path, capsys):
    rc = _run_cli(tmp_path, "show", "sample-policy")
    assert rc == 0
    out = capsys.readouterr().out
    assert "sample-policy" in out
    assert "1.0.0" in out


def test_policy_show_unknown_returns_10(tmp_path: Path, capsys):
    rc = _run_cli(tmp_path, "show", "foobar")
    assert rc == policy_errors.EXIT_UNKNOWN_POLICY


def test_policy_apply_writes_files(tmp_path: Path):
    project = _scaffold_project(tmp_path)
    rc = _run_cli(tmp_path, "apply", "sample-policy", cwd=project)
    assert rc == 0
    assert (project / ".claude" / "docs" / "policies" / "sample-policy.md").exists()


def test_policy_apply_unknown_returns_10(tmp_path: Path):
    project = _scaffold_project(tmp_path)
    rc = _run_cli(tmp_path, "apply", "never-heard-of", cwd=project)
    assert rc == policy_errors.EXIT_UNKNOWN_POLICY


def test_policy_remove_strips_state(tmp_path: Path):
    project = _scaffold_project(tmp_path)
    _run_cli(tmp_path, "apply", "sample-policy", cwd=project)
    rc = _run_cli(tmp_path, "remove", "sample-policy", cwd=project)
    assert rc == 0
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert not any(p["slug"] == "sample-policy" for p in state["applied_policies"])


def test_policy_show_applied_prints_current(tmp_path: Path, capsys):
    project = _scaffold_project(tmp_path)
    _run_cli(tmp_path, "apply", "sample-policy", cwd=project)
    capsys.readouterr()
    rc = _run_cli(tmp_path, "show-applied", cwd=project)
    assert rc == 0
    out = capsys.readouterr().out
    assert "sample-policy" in out


def test_policy_status_classifies(tmp_path: Path, capsys):
    project = _scaffold_project(tmp_path)
    _run_cli(tmp_path, "apply", "sample-policy", cwd=project)
    capsys.readouterr()
    rc = _run_cli(tmp_path, "status", cwd=project)
    assert rc == 0
    out = capsys.readouterr().out
    assert "current" in out


def test_policy_lint_passes_on_valid_fixture(tmp_path: Path, capsys):
    rc = _run_cli(tmp_path, "lint")
    assert rc == 0


def test_sn_setup_dispatches_policy_subtree(tmp_path: Path, capsys):
    """sn-setup policy list should reach policy_cli.main."""
    old = Path.cwd()
    os.environ["SN_POLICY_CATALOG_ROOT"] = str(CATALOG_FIX)
    try:
        os.chdir(tmp_path)
        rc = sn_init.main(["policy", "list"])
    finally:
        os.chdir(old)
        del os.environ["SN_POLICY_CATALOG_ROOT"]
    assert rc == 0
    out = capsys.readouterr().out
    assert "sample-policy" in out
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_policy_cli.py -v`
Expected: ModuleNotFoundError for `policy_cli`.

- [ ] **Step 3: Implement `scripts/policy_cli.py`**

```python
"""`sn-setup policy ...` sub-command dispatcher.

Real catalog root resolves to
`<plugin_root>/skills/sn-setup/templates/policies/`; tests override via the
SN_POLICY_CATALOG_ROOT env var.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import policy_apply
import policy_errors
import policy_loader

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_ROOT = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "policies"


def _catalog_root() -> Path:
    override = os.environ.get("SN_POLICY_CATALOG_ROOT")
    return Path(override) if override else DEFAULT_CATALOG_ROOT


def _load_catalog() -> dict[str, policy_loader.PolicyMeta]:
    return policy_loader.load_catalog(_catalog_root())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup policy", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    sp_show = sub.add_parser("show"); sp_show.add_argument("slug")
    sp_app = sub.add_parser("apply"); sp_app.add_argument("slugs", nargs="+")
    sp_app.add_argument("--with-deps", action="store_true")
    sp_rm = sub.add_parser("remove"); sp_rm.add_argument("slugs", nargs="+")
    sp_rm.add_argument("--force", action="store_true")
    sp_up = sub.add_parser("upgrade")
    g = sp_up.add_mutually_exclusive_group(required=True)
    g.add_argument("slug", nargs="?")
    g.add_argument("--all", dest="all_flag", action="store_true")
    sp_up.add_argument("--force", action="store_true")
    sub.add_parser("status")
    sub.add_parser("show-applied")
    sp_hist = sub.add_parser("history")
    sp_hist.add_argument("--slug", default=None)
    sp_hist.add_argument("--limit", type=int, default=20)
    sub.add_parser("lint")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    try:
        return _dispatch(ns)
    except policy_errors.PolicyError as e:
        print(f"sn-setup policy: {e}", file=sys.stderr)
        return e.exit_code


def _dispatch(ns: argparse.Namespace) -> int:
    project = Path.cwd().resolve()
    catalog = _load_catalog()

    if ns.cmd == "list":
        for slug in sorted(catalog):
            m = catalog[slug]
            group = f" group={m.group}" if m.group else ""
            print(f"{slug:24s} {m.version:8s} {m.category:14s}{group}")
        return 0

    if ns.cmd == "show":
        if ns.slug not in catalog:
            raise policy_errors.UnknownPolicy(f"unknown policy {ns.slug!r}")
        m = catalog[ns.slug]
        print(f"slug:    {m.slug}")
        print(f"version: {m.version}")
        print(f"group:   {m.group}")
        print(f"title:   {m.title}")
        print(f"category: {m.category}")
        print(f"applies_to: {m.applies_to}")
        print(f"requires: {m.requires}")
        print(f"conflicts_with: {m.conflicts_with}")
        print(f"description: {m.description.strip()}")
        return 0

    if ns.cmd == "apply":
        policy_apply.apply_many(
            project, ns.slugs, catalog, with_deps=ns.with_deps,
        )
        return 0

    if ns.cmd == "remove":
        for slug in ns.slugs:
            policy_apply.remove(project, slug, force=ns.force)
        return 0

    if ns.cmd == "upgrade":
        targets = sorted(catalog) if ns.all_flag else [ns.slug]
        for slug in targets:
            if slug not in catalog:
                raise policy_errors.UnknownPolicy(f"unknown policy {slug!r}")
            try:
                policy_apply.upgrade(project, catalog[slug], force=ns.force)
            except policy_errors.PolicyNotApplied:
                if ns.all_flag:
                    continue  # skip un-applied slugs in bulk upgrade
                raise
        return 0

    if ns.cmd == "status":
        rows = policy_apply.status(project, catalog)
        for r in rows:
            glyph = {"current": "✓", "obsolete": "⚠", "drifted": "◆", "unknown": "✗"}[r.state]
            cv = r.catalog_version or "—"
            print(f"  {glyph} {r.slug:24s} applied={r.applied_version:8s} catalog={cv:8s} ({r.state})")
        return 0

    if ns.cmd == "show-applied":
        import json as _json, policy_state as _ps
        state = _ps.read_state(project)
        print(_json.dumps(state["applied_policies"], indent=2))
        return 0

    if ns.cmd == "history":
        import policy_state as _ps
        state = _ps.read_state(project)
        events = state["policy_history"]
        if ns.slug:
            events = [e for e in events if e.get("slug") == ns.slug or e.get("from") == ns.slug or e.get("to") == ns.slug]
        for e in events[-ns.limit :]:
            print(e)
        return 0

    if ns.cmd == "lint":
        failures = policy_loader.lint(_catalog_root())
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        return 0 if not failures else 1

    return 2
```

- [ ] **Step 4: Wire `sn-setup policy ...` dispatch in `scripts/sn_init.py`**

Open `scripts/sn_init.py`. Near the top of `main`, after `argv = sys.argv[1:] if argv is None else argv` is implied — actually the function signature is `def main(argv: list[str] | None = None)`. Add a sub-tree pre-check before `parser.parse_args(argv)`:

Modify the existing `main` function. Replace:

```python
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK
```

with:

```python
SUBTREES = {"policy", "profile"}


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else list(argv)
    if raw and raw[0] in SUBTREES:
        if raw[0] == "policy":
            import policy_cli
            return policy_cli.main(raw[1:])
        if raw[0] == "profile":
            import profile_cli  # noqa: F401  (lands in Task 14)
            return profile_cli.main(raw[1:])

    parser = build_parser()
    try:
        args = parser.parse_args(raw)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK
```

Since `profile_cli` lands in Task 14, the `profile` branch will hit ImportError until then. The test in this task only exercises `policy`, so leave the import behind the branch.

- [ ] **Step 5: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_policy_cli.py -v`
Expected: 10 passed.

- [ ] **Step 6: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 201 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/policy_cli.py scripts/sn_init.py tests/test_policy_cli.py
git commit -m "$(cat <<'EOF'
feat(policy): sn-setup policy CLI sub-tree (list/show/apply/remove/upgrade/status/show-applied/history/lint)

Top-level `sn-setup` dispatches the first positional `policy` to
policy_cli.main. Catalog root resolves under skills/sn-setup/templates/policies/
in production and via SN_POLICY_CATALOG_ROOT in tests.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 10: Catalog content — policies 1-5

**Files:** create the policy directories listed in the file map for slugs 1-5 (`memory-ordinary`, `memory-regulated`, `repository-ecosystem`, `audit-log-strict`, `supply-chain-scan`).

For each policy:
- `policy.yaml` — schema from spec §2 + entries from spec §3 table.
- `claude-md.row.md` — `| <category> | <slug> | .claude/docs/policies/<slug>.md | <version> |`
- `docs/<slug>.md` — full policy text matching the design intent in spec §3.
- (when present) `rules/<slug>.md` — ≤ 50 token always-on rule.
- (when present) `settings.patch.json` — every entry tagged `policy: <slug>`.
- (when present) `extras/hooks/<slug>.sh` — chmod-+x hook stub that exits 0 with a placeholder echo.

- [ ] **Step 1: Write content tests first (TDD against the catalog)**

Create `tests/test_catalog_content.py`:

```python
"""Catalog content sanity tests (spec §3 day-one set)."""
from __future__ import annotations

from pathlib import Path

import policy_loader

CATALOG = Path(__file__).resolve().parent.parent / "skills" / "sn-setup" / "templates" / "policies"


def test_catalog_present_for_tasks_10_11():
    expected = {
        "memory-ordinary", "memory-regulated", "repository-ecosystem",
        "audit-log-strict", "supply-chain-scan",
    }
    present = {p.name for p in CATALOG.iterdir() if p.is_dir()}
    missing = expected - present
    assert not missing, f"task 10 expects {expected} present; missing: {missing}"


def test_catalog_loads_all_present_policies():
    catalog = policy_loader.load_catalog(CATALOG)
    assert "memory-ordinary" in catalog
    assert "memory-regulated" in catalog
    assert catalog["memory-regulated"].group == "memory-tier"
    assert catalog["memory-ordinary"].group == "memory-tier"


def test_catalog_lint_passes():
    assert policy_loader.lint(CATALOG) == []
```

- [ ] **Step 2: Run — expected fail (directories not present)**

Run: `.venv/bin/python -m pytest tests/test_catalog_content.py -v`
Expected: fail on first test, "missing: {...}".

- [ ] **Step 3: Create policy 1 — `memory-ordinary`**

Create `skills/sn-setup/templates/policies/memory-ordinary/policy.yaml`:

```yaml
slug: memory-ordinary
title: "Memory: ordinary (auto-memory permitted)"
version: 1.0.0
category: security
group: memory-tier
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Auto-memory may be enabled per developer for personal convenience. Anything
  team-wide must be promoted into committed CLAUDE.md or a skill via PR
  within the sprint.
files:
  claude_md_row: claude-md.row.md
  docs: docs/memory-ordinary.md
  rules: rules/memory-ordinary.md
```

Create `claude-md.row.md`:
```markdown
| security | memory-ordinary | `.claude/docs/policies/memory-ordinary.md` | 1.0.0 |
```

Create `docs/memory-ordinary.md`:
```markdown
# Policy — Memory: ordinary

Tier: **ordinary**.

## What this means

Auto-memory MAY be enabled per developer for personal convenience.

## Promotion rule

Anything that should hold team-wide must be promoted into committed
`CLAUDE.md` or a skill via PR within the sprint. Personal preferences stay
local; shared learnings become shared artifacts.

## Switching to regulated

Apply `memory-regulated` instead. The exclusive `memory-tier` group means
applying it auto-swaps this one out.
```

Create `rules/memory-ordinary.md`:
```markdown
# Hard rule — memory-ordinary

Promote team-wide context to committed `CLAUDE.md` or a skill within the
sprint. Personal preferences may stay in auto-memory.
```

- [ ] **Step 4: Create policy 2 — `memory-regulated`**

Create `policy.yaml`:
```yaml
slug: memory-regulated
title: "Memory: regulated (auto-memory off)"
version: 1.0.0
category: security
group: memory-tier
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Auto-memory disabled. All context must be committed. Pairs with the
  PDPA compliance policy.
files:
  claude_md_row: claude-md.row.md
  docs: docs/memory-regulated.md
  rules: rules/memory-regulated.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/memory-regulated.sh:.claude/hooks/memory-regulated.sh
```

`claude-md.row.md`:
```markdown
| security | memory-regulated | `.claude/docs/policies/memory-regulated.md` | 1.0.0 |
```

`docs/memory-regulated.md`:
```markdown
# Policy — Memory: regulated

Tier: **regulated**. Auto-memory disabled.

## What this means

All context comes from committed files only. Every input to the assistant's
behavior must be reviewable in git.

## Enforcement

`.claude/hooks/memory-regulated.sh` runs as a `PreToolUse` hook on `Write`
and denies any write under `~/.claude/memory/` or `.claude/local-memory/`.

## Pairing

Apply alongside `audit-log-strict` + `secret-scan` for the full regulated
posture; or apply `pdpa-compliance` which bundles all three.
```

`rules/memory-regulated.md`:
```markdown
# Hard rule — memory-regulated

Do NOT write to `~/.claude/memory/` or `.claude/local-memory/`. All context
MUST be committed. See `.claude/docs/policies/memory-regulated.md`.
```

`settings.patch.json`:
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

`extras/hooks/memory-regulated.sh`:
```sh
#!/usr/bin/env bash
# Policy: memory-regulated — deny writes under auto-memory dirs.
set -euo pipefail
echo "memory-regulated: write under auto-memory dirs is denied" >&2
exit 1
```

- [ ] **Step 5: Create policy 3 — `repository-ecosystem`**

`policy.yaml`:
```yaml
slug: repository-ecosystem
title: "Repository Ecosystem table"
version: 1.0.0
category: conventions
group: null
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Cross-service awareness from inside a single repo. The full table of
  related services lives in the policy doc; the CLAUDE.md row points at it.
files:
  claude_md_row: claude-md.row.md
  docs: docs/repository-ecosystem.md
```

`claude-md.row.md`:
```markdown
| conventions | repository-ecosystem | `.claude/docs/policies/repository-ecosystem.md` | 1.0.0 |
```

`docs/repository-ecosystem.md`:
```markdown
# Policy — Repository Ecosystem

The list of services this repo is aware of. Edit the table below to reflect
your org. Keep it small — this is for cross-service awareness, not full
topology.

| Service | Purpose | Repo |
|---|---|---|
| _example-orders_ | order capture + lifecycle | `org/orders` |
| _example-billing_ | invoicing, payments | `org/billing` |

## Per-profile foregrounding

- microservice → list peers in the same domain.
- BFF → foreground downstream services.
- frontend → foreground its BFF.
```

- [ ] **Step 6: Create policy 4 — `audit-log-strict`**

`policy.yaml`:
```yaml
slug: audit-log-strict
title: "Audit log: strict (full payload, no spill)"
version: 1.0.0
category: observability
group: null
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Force every Claude tool call into the JSONL audit log with full payloads.
  No 2 KB blob spill. Useful for regulated services.
files:
  claude_md_row: claude-md.row.md
  docs: docs/audit-log-strict.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/audit-log-strict.sh:.claude/hooks/audit-log-strict.sh
```

`claude-md.row.md`:
```markdown
| observability | audit-log-strict | `.claude/docs/policies/audit-log-strict.md` | 1.0.0 |
```

`docs/audit-log-strict.md`:
```markdown
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
```

`settings.patch.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "policy": "audit-log-strict",
        "version": "1.0.0",
        "matcher": "*",
        "command": ".claude/hooks/audit-log-strict.sh"
      }
    ]
  }
}
```

`extras/hooks/audit-log-strict.sh`:
```sh
#!/usr/bin/env bash
# Policy: audit-log-strict — append a JSONL line for every tool call.
set -euo pipefail
LOGDIR=".sn-init/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/exec-$(date -u +%F)-${CLAUDE_SESSION_ID:-unknown}.jsonl"
printf '{"timestamp":"%s","tool":"%s","request":%s,"response":%s,"duration_ms":%s}\n' \
  "$(date -u +%FT%TZ)" "${CLAUDE_TOOL:-unknown}" \
  "${CLAUDE_REQUEST_JSON:-null}" "${CLAUDE_RESPONSE_JSON:-null}" \
  "${CLAUDE_DURATION_MS:-0}" >> "$LOG"
```

- [ ] **Step 7: Create policy 5 — `supply-chain-scan`**

`policy.yaml`:
```yaml
slug: supply-chain-scan
title: "Supply-chain scan"
version: 1.0.0
category: security
group: null
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Pre-install + pre-merge dependency scan. Blocks adding unscanned deps and
  flags newly-introduced CVEs at PR time.
files:
  claude_md_row: claude-md.row.md
  docs: docs/supply-chain-scan.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/supply-chain-scan.sh:.claude/hooks/supply-chain-scan.sh
```

`claude-md.row.md`:
```markdown
| security | supply-chain-scan | `.claude/docs/policies/supply-chain-scan.md` | 1.0.0 |
```

`docs/supply-chain-scan.md`:
```markdown
# Policy — Supply-chain scan

Two checkpoints:

1. **PreInstall hook** — runs before any `npm install`, `pip install`,
   `go get`, etc. Scans the lock-file diff for unknown deps.
2. **Pre-merge CI gate** — runs a vuln scanner on the lock-files; PR fails if
   any new HIGH/CRITICAL CVE appears.

Tools defaulted: `osv-scanner` (Go, Python, Node). Override per repo via
`.claude/config/supply-chain.yaml`.
```

`settings.patch.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "policy": "supply-chain-scan",
        "version": "1.0.0",
        "matcher": "Bash",
        "pattern": "(npm install|pip install|go get|cargo add)",
        "command": ".claude/hooks/supply-chain-scan.sh"
      }
    ]
  }
}
```

`extras/hooks/supply-chain-scan.sh`:
```sh
#!/usr/bin/env bash
# Policy: supply-chain-scan — verify any dep install passes osv-scanner.
set -euo pipefail
if ! command -v osv-scanner >/dev/null 2>&1; then
  echo "supply-chain-scan: osv-scanner not installed; allowing with warning" >&2
  exit 0
fi
osv-scanner --skip-git ./ || {
  echo "supply-chain-scan: osv-scanner found vulnerable deps" >&2
  exit 1
}
```

- [ ] **Step 8: Run catalog tests — expected PASS for these 5**

Run: `.venv/bin/python -m pytest tests/test_catalog_content.py -v`
Expected: 3 passed.

- [ ] **Step 9: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 204 passed.

- [ ] **Step 10: Commit**

```bash
git add skills/sn-setup/templates/policies/{memory-ordinary,memory-regulated,repository-ecosystem,audit-log-strict,supply-chain-scan} tests/test_catalog_content.py
git commit -m "$(cat <<'EOF'
feat(policy): catalog content — memory-ordinary, memory-regulated, repository-ecosystem, audit-log-strict, supply-chain-scan

First batch of day-one catalog (5 of 9). Each policy ships its required
layers per spec §3. Hook stubs ship under extras/ and gain chmod +x at apply
time.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 11: Catalog content — policies 6-9 + `## Policies` stub in base CLAUDE.md

**Files:**
- Create: `templates/policies/{secret-scan,commit-msg-gate,branch-naming,pdpa-compliance}/...`
- Modify: `skills/sn-setup/templates/managed-agent-base/CLAUDE.md` (add empty `## Policies` table stub so apply has a target)
- Modify: `tests/test_catalog_content.py` (extend the expected-present set)

- [ ] **Step 1: Update expected set in `tests/test_catalog_content.py`**

Replace the set in `test_catalog_present_for_tasks_10_11`:

```python
    expected = {
        "memory-ordinary", "memory-regulated", "repository-ecosystem",
        "audit-log-strict", "supply-chain-scan",
        "secret-scan", "commit-msg-gate", "branch-naming", "pdpa-compliance",
    }
```

- [ ] **Step 2: Run — expected fail on the four new slugs**

Run: `.venv/bin/python -m pytest tests/test_catalog_content.py::test_catalog_present_for_tasks_10_11 -v`
Expected: missing four slugs.

- [ ] **Step 3: Create policy 6 — `secret-scan`**

`policy.yaml`:
```yaml
slug: secret-scan
title: "Secret scan"
version: 1.0.0
category: security
group: null
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Pre-tool Write/Edit scan + pre-commit staged-diff scan. Blocks secrets at
  the closest possible point to authorship.
files:
  claude_md_row: claude-md.row.md
  docs: docs/secret-scan.md
  rules: rules/secret-scan.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/secret-scan.sh:.claude/hooks/secret-scan.sh
```

`claude-md.row.md`:
```markdown
| security | secret-scan | `.claude/docs/policies/secret-scan.md` | 1.0.0 |
```

`docs/secret-scan.md`:
```markdown
# Policy — Secret scan

Two checkpoints:

1. **PreToolUse on Write/Edit** — scans the new content for high-entropy
   strings + known token shapes (AWS, GCP, GH, Slack, Stripe, JWT). Blocks
   on match.
2. **Pre-commit** — scans the staged diff. Blocks the commit on match.

Default scanner: `gitleaks`. Repo can override via `.claude/config/secret-scan.yaml`.
```

`rules/secret-scan.md`:
```markdown
# Hard rule — secret-scan

Never paste, commit, or write API keys / tokens / passwords / private keys
into files. The PreToolUse hook will block; please reach for env vars or a
secret manager instead.
```

`settings.patch.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "policy": "secret-scan",
        "version": "1.0.0",
        "matcher": "Write|Edit",
        "command": ".claude/hooks/secret-scan.sh"
      }
    ]
  }
}
```

`extras/hooks/secret-scan.sh`:
```sh
#!/usr/bin/env bash
# Policy: secret-scan — block writes that look like secrets.
set -euo pipefail
PAYLOAD="${CLAUDE_TOOL_INPUT:-}"
if echo "$PAYLOAD" | grep -E -q '(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}|ghp_[0-9A-Za-z]{36}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[0-9A-Za-z\-]+|-----BEGIN [A-Z ]+PRIVATE KEY-----)'; then
  echo "secret-scan: payload appears to contain a secret" >&2
  exit 1
fi
```

- [ ] **Step 4: Create policy 7 — `commit-msg-gate`**

`policy.yaml`:
```yaml
slug: commit-msg-gate
title: "Commit-msg gate (REQ-NNN / Conventional Commits)"
version: 1.0.0
category: workflow
group: null
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Wraps the existing .githooks/commit-msg hook so commit subjects match the
  REQ-NNN convention OR a Conventional Commits prefix.
files:
  claude_md_row: claude-md.row.md
  docs: docs/commit-msg-gate.md
  settings_patch: settings.patch.json
```

`claude-md.row.md`:
```markdown
| workflow | commit-msg-gate | `.claude/docs/policies/commit-msg-gate.md` | 1.0.0 |
```

`docs/commit-msg-gate.md`:
```markdown
# Policy — Commit-msg gate

Subjects must match one of:

- `REQ-NNN: <text>` for a ticket-tracked change.
- `<type>(<scope>?): <text>` where `<type>` ∈ `{feat, fix, chore, docs, refactor, test, perf, build, ci, style, revert}` (Conventional Commits).

Wraps `.githooks/commit-msg`. If the hook already exists, this policy adds
its own line and exits 0 from the policy's wrapper when the inner script
passes.
```

`settings.patch.json`:
```json
{
  "hooks": {
    "PreCommit": [
      {
        "policy": "commit-msg-gate",
        "version": "1.0.0",
        "matcher": "*",
        "command": ".githooks/commit-msg"
      }
    ]
  }
}
```

(No `extras/` for this policy — the existing repo-shipped `.githooks/commit-msg` is reused; the policy only wires it into the policy settings layer.)

- [ ] **Step 5: Create policy 8 — `branch-naming`**

`policy.yaml`:
```yaml
slug: branch-naming
title: "Branch naming"
version: 1.0.0
category: workflow
group: null
applies_to: [microservice, bff, frontend]
requires: []
conflicts_with: []
description: |
  Pre-push hook that rejects branches not matching feat/* fix/* chore/*
  docs/* refactor/* test/* prefix.
files:
  claude_md_row: claude-md.row.md
  docs: docs/branch-naming.md
  settings_patch: settings.patch.json
  extras:
    - extras/hooks/branch-naming.sh:.githooks/pre-push
```

`claude-md.row.md`:
```markdown
| workflow | branch-naming | `.claude/docs/policies/branch-naming.md` | 1.0.0 |
```

`docs/branch-naming.md`:
```markdown
# Policy — Branch naming

Pre-push hook rejects pushes from branches whose name doesn't match one of:

- `feat/<slug>`
- `fix/<slug>`
- `chore/<slug>`
- `docs/<slug>`
- `refactor/<slug>`
- `test/<slug>`

`main` is always allowed. Override per push with `git push --no-verify` (not
recommended).
```

`settings.patch.json`:
```json
{
  "hooks": {
    "PrePush": [
      {
        "policy": "branch-naming",
        "version": "1.0.0",
        "matcher": "*",
        "command": ".githooks/pre-push"
      }
    ]
  }
}
```

`extras/hooks/branch-naming.sh`:
```sh
#!/usr/bin/env bash
# Policy: branch-naming — reject pushes from non-conforming branches.
set -euo pipefail
BR=$(git rev-parse --abbrev-ref HEAD)
[[ "$BR" == "main" ]] && exit 0
if ! [[ "$BR" =~ ^(feat|fix|chore|docs|refactor|test)/ ]]; then
  echo "branch-naming: branch '$BR' must start with feat/, fix/, chore/, docs/, refactor/, or test/" >&2
  exit 1
fi
```

- [ ] **Step 6: Create policy 9 — `pdpa-compliance`**

`policy.yaml`:
```yaml
slug: pdpa-compliance
title: "PDPA compliance (signal-only stub)"
version: 1.0.0
category: security
group: null
applies_to: [microservice, bff]
requires: [memory-regulated, audit-log-strict, secret-scan]
conflicts_with: []
description: |
  Signal-only stub in v1. Requires memory-regulated + audit-log-strict +
  secret-scan. Full PDPA enforcement is backlog item B2.5.
files:
  claude_md_row: claude-md.row.md
  docs: docs/pdpa-compliance.md
  rules: rules/pdpa-compliance.md
```

`claude-md.row.md`:
```markdown
| security | pdpa-compliance | `.claude/docs/policies/pdpa-compliance.md` | 1.0.0 |
```

`docs/pdpa-compliance.md`:
```markdown
# Policy — PDPA compliance

Signal-only in v1. Confirms that this service has adopted the three
prerequisite policies:

- `memory-regulated` (auto-memory off)
- `audit-log-strict` (full-payload audit)
- `secret-scan` (block secret writes)

Full PDPA enforcement (data-mapping templates, retention hooks, consent
records, breach notification runbooks) lives in backlog item **B2.5**.
```

`rules/pdpa-compliance.md`:
```markdown
# Hard rule — pdpa-compliance

This service handles PDPA-regulated personal data. Confirm
`memory-regulated`, `audit-log-strict`, and `secret-scan` are applied
(`sn-setup policy status`) before merging changes that touch the data path.
```

- [ ] **Step 7: Modify base CLAUDE.md to add `## Policies` stub**

Open `skills/sn-setup/templates/managed-agent-base/CLAUDE.md` and insert before `## Local notes`:

```markdown
## Policies

Service-level policies in effect. Read the linked doc on demand.

| Category | Slug | Reference | Version |
|---|---|---|---|

```

(Empty table; rows arrive via `sn-setup policy apply`.)

- [ ] **Step 8: Run catalog tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_catalog_content.py -v`
Expected: 3 passed (all 9 slugs present, catalog loads, lint passes).

- [ ] **Step 9: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 204 passed (no test count change; same tests now exercise larger fixture).

- [ ] **Step 10: Commit**

```bash
git add skills/sn-setup/templates/policies/{secret-scan,commit-msg-gate,branch-naming,pdpa-compliance} skills/sn-setup/templates/managed-agent-base/CLAUDE.md tests/test_catalog_content.py
git commit -m "$(cat <<'EOF'
feat(policy): catalog content — secret-scan, commit-msg-gate, branch-naming, pdpa-compliance

Second batch of day-one catalog (4 of 9). pdpa-compliance is signal-only;
full PDPA pack is backlog B2.5. Base CLAUDE.md gains an empty ## Policies
table stub so apply has a target.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 12: Scaffold integration — `--policies` / `--add-policies` / `--remove-policies` + profile defaults

**Files:**
- Modify: `scripts/sn_init.py`
- Create: `skills/sn-setup/templates/profile/{microservice,bff,frontend}/default_policies.yaml`
- Modify: `tests/test_sn_init.py` (existing test file; add 6 new tests for scaffold-time policy resolution)

**Interfaces:**
- New flags on `sn-setup` scaffold:
  - `--policies=<csv>` — replace profile defaults entirely.
  - `--add-policies=<csv>` — delta against defaults.
  - `--remove-policies=<csv>` — delta against defaults.
  - `--with-deps` — pass-through to `apply_many`.
- Combining `--policies` with `--add/--remove` → exit 17 (`MixedOverrideFlags`).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_sn_init.py`:

```python
import policy_errors  # type: ignore


def test_scaffold_applies_profile_defaults(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    expected = {"repository-ecosystem", "memory-ordinary", "audit-log-strict",
                "supply-chain-scan", "secret-scan", "commit-msg-gate"}
    assert slugs == expected


def test_scaffold_writes_project_local_profile_defaults(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice")
    text = (tmp_path / "demo" / ".claude" / "profile-defaults.yaml").read_text()
    assert "profile: microservice" in text
    assert "memory-ordinary" in text


def test_scaffold_policies_flag_replaces_defaults(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--policies=secret-scan,repository-ecosystem")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    assert slugs == {"secret-scan", "repository-ecosystem"}


def test_scaffold_delta_flags(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice",
         "--add-policies=branch-naming", "--remove-policies=audit-log-strict")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    assert "branch-naming" in slugs
    assert "audit-log-strict" not in slugs


def test_scaffold_combining_replace_and_delta_errors(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git",
              "--policies=secret-scan", "--add-policies=branch-naming")
    assert rc == policy_errors.EXIT_MIXED_OVERRIDE_FLAGS


def test_scaffold_unknown_policy_errors(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git", "--policies=foobar")
    assert rc == policy_errors.EXIT_UNKNOWN_POLICY
```

- [ ] **Step 2: Create profile default YAMLs**

`skills/sn-setup/templates/profile/microservice/default_policies.yaml`:
```yaml
profile: microservice
policies:
  - repository-ecosystem
  - memory-ordinary
  - audit-log-strict
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate
```

`skills/sn-setup/templates/profile/bff/default_policies.yaml`:
```yaml
profile: bff
policies:
  - repository-ecosystem
  - memory-ordinary
  - audit-log-strict
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate
```

`skills/sn-setup/templates/profile/frontend/default_policies.yaml`:
```yaml
profile: frontend
policies:
  - repository-ecosystem
  - memory-ordinary
  - supply-chain-scan
  - secret-scan
  - commit-msg-gate
  - branch-naming
```

- [ ] **Step 3: Modify `scripts/sn_init.py`**

In `build_parser`, add flags:

```python
    p.add_argument("--policies", default=None,
                   help="Comma-separated list of policies to apply (replaces profile defaults).")
    p.add_argument("--add-policies", default=None, dest="add_policies",
                   help="Comma-separated list of policies to add to profile defaults.")
    p.add_argument("--remove-policies", default=None, dest="remove_policies",
                   help="Comma-separated list of policies to remove from profile defaults.")
    p.add_argument("--with-deps", action="store_true", dest="with_deps",
                   help="When applying, also install required-by policies.")
```

In `_run_new`, after the scaffold materializes but before the final summary, add a call to a new helper `_apply_initial_policies`. Insert just before `_print_summary`:

```python
    _apply_initial_policies(args, target, logger)
```

Then add the helper at the bottom of the file:

```python
def _apply_initial_policies(args: argparse.Namespace, target: Path,
                            logger: snlog.StepLogger) -> None:
    """Resolve and apply the project's initial policy set per spec §9."""
    import yaml as _yaml

    import policy_apply
    import policy_cli
    import policy_errors

    # 1. Reject mixed override flags.
    if args.policies is not None and (args.add_policies or args.remove_policies):
        raise policy_errors.MixedOverrideFlags(
            "--policies replaces the default set; --add/--remove cannot combine with it"
        )

    # 2. Load profile default YAML if --policies is not provided.
    base_set: list[str] = []
    profile_defaults_path = (
        TEMPLATES / "profile" / args.profile / "default_policies.yaml"
    )
    if profile_defaults_path.exists():
        data = _yaml.safe_load(profile_defaults_path.read_text(encoding="utf-8")) or {}
        base_set = list(data.get("policies") or [])

    # 3. Resolve final set.
    if args.policies is not None:
        final = [s.strip() for s in args.policies.split(",") if s.strip()]
    else:
        final = list(base_set)
        if args.add_policies:
            for s in args.add_policies.split(","):
                s = s.strip()
                if s and s not in final:
                    final.append(s)
        if args.remove_policies:
            drop = {s.strip() for s in args.remove_policies.split(",")}
            final = [s for s in final if s not in drop]

    if not final:
        return

    # 4. Write project-local profile-defaults.yaml (always the original
    #    profile bundle, not the resolved final set).
    proj_defaults = target / ".claude" / "profile-defaults.yaml"
    proj_defaults.parent.mkdir(parents=True, exist_ok=True)
    proj_defaults.write_text(
        f"profile: {args.profile}\npolicies:\n"
        + "".join(f"  - {s}\n" for s in base_set),
        encoding="utf-8",
    )

    # 5. Apply.
    catalog = policy_cli._load_catalog()
    source = (
        "scaffold-default" if args.policies is None and not args.add_policies and not args.remove_policies
        else "scaffold-override" if args.policies is not None
        else "scaffold-delta"
    )
    policy_apply.apply_many(target, final, catalog, with_deps=args.with_deps, source=source)
```

Update the `main` function's exception handler to also catch `PolicyError`:

```python
def main(argv: list[str] | None = None) -> int:
    ...
    try:
        return run(args)
    except errors.SnInitError as e:
        print(f"sn-setup: {e}", file=sys.stderr)
        return e.exit_code
    except Exception as e:
        # Surface PolicyError exit codes.
        import policy_errors
        if isinstance(e, policy_errors.PolicyError):
            print(f"sn-setup: {e}", file=sys.stderr)
            return e.exit_code
        print(f"sn-setup: internal error: {e!r}", file=sys.stderr)
        return errors.EXIT_INTERNAL
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_sn_init.py -v -k "scaffold"`
Expected: 6 new tests pass; existing scaffold tests still pass.

- [ ] **Step 5: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 210 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/sn_init.py skills/sn-setup/templates/profile/{microservice,bff,frontend}/default_policies.yaml tests/test_sn_init.py
git commit -m "$(cat <<'EOF'
feat(policy): scaffold integration — profile defaults + --policies / --add / --remove

sn-setup demo --profile=<P> applies the profile's default_policies.yaml.
--policies replaces; --add-policies / --remove-policies are deltas. Combining
replace + delta raises MixedOverrideFlags (exit 17).
.claude/profile-defaults.yaml is written with the ORIGINAL profile bundle.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 13: `sn-setup profile` CLI sub-tree

**Files:**
- Create: `scripts/profile_cli.py`
- Create: `tests/test_profile_cli.py`

**Interfaces:**
- `profile_cli.main(argv: list[str]) -> int` — `list | show | add | remove | swap` sub-commands.
- cwd-detection per spec §9.

- [ ] **Step 1: Write failing tests**

Create `tests/test_profile_cli.py`:

```python
"""Tests for scripts/profile_cli.py."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import policy_errors  # type: ignore
import profile_cli  # type: ignore
import sn_init  # type: ignore


def _run(cwd: Path, *argv: str) -> int:
    old = Path.cwd()
    try:
        os.chdir(cwd)
        return profile_cli.main(list(argv))
    finally:
        os.chdir(old)


def _seed_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    (project / ".sn-init-state.json").write_text(json.dumps({"mode": "new"}))
    (project / ".claude").mkdir()
    (project / ".claude" / "profile-defaults.yaml").write_text(
        "profile: microservice\npolicies:\n  - memory-ordinary\n"
    )
    return project


def _seed_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / ".claude-plugin").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text("{}")
    profile_dir = plugin / "skills" / "sn-setup" / "templates" / "profile" / "microservice"
    profile_dir.mkdir(parents=True)
    (profile_dir / "default_policies.yaml").write_text(
        "profile: microservice\npolicies:\n  - memory-ordinary\n"
    )
    return plugin


def test_profile_add_in_project_edits_local_file(tmp_path: Path):
    project = _seed_project(tmp_path)
    rc = _run(project, "add", "branch-naming", "--profile=microservice")
    assert rc == 0
    text = (project / ".claude" / "profile-defaults.yaml").read_text()
    assert "branch-naming" in text


def test_profile_remove_in_project_edits_local_file(tmp_path: Path):
    project = _seed_project(tmp_path)
    rc = _run(project, "remove", "memory-ordinary", "--profile=microservice")
    assert rc == 0
    text = (project / ".claude" / "profile-defaults.yaml").read_text()
    assert "memory-ordinary" not in text


def test_profile_add_in_plugin_edits_template(tmp_path: Path):
    plugin = _seed_plugin(tmp_path)
    rc = _run(plugin, "add", "branch-naming", "--profile=microservice")
    assert rc == 0
    text = (plugin / "skills" / "sn-setup" / "templates" / "profile" / "microservice" /
            "default_policies.yaml").read_text()
    assert "branch-naming" in text


def test_profile_add_unknown_profile_errors(tmp_path: Path):
    project = _seed_project(tmp_path)
    rc = _run(project, "add", "branch-naming", "--profile=mainframe")
    assert rc == policy_errors.EXIT_UNKNOWN_PROFILE


def test_profile_add_neither_marker_errors(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    rc = _run(plain, "add", "branch-naming", "--profile=microservice")
    assert rc == policy_errors.EXIT_CWD_AMBIGUOUS_OR_INVALID


def test_profile_swap_replaces_member(tmp_path: Path):
    project = _seed_project(tmp_path)
    rc = _run(project, "swap", "--profile=microservice", "memory-ordinary", "memory-regulated")
    assert rc == 0
    text = (project / ".claude" / "profile-defaults.yaml").read_text()
    assert "memory-regulated" in text
    assert "memory-ordinary" not in text


def test_sn_setup_dispatches_profile_subtree(tmp_path: Path, capsys):
    project = _seed_project(tmp_path)
    old = Path.cwd()
    try:
        os.chdir(project)
        rc = sn_init.main(["profile", "list"])
    finally:
        os.chdir(old)
    assert rc == 0
```

- [ ] **Step 2: Run tests — expected fail**

Run: `.venv/bin/python -m pytest tests/test_profile_cli.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `scripts/profile_cli.py`**

```python
"""`sn-setup profile ...` CLI sub-tree.

Auto-detects cwd:
  - .claude-plugin/plugin.json present → edits the template YAML.
  - .sn-init-state.json present → edits .claude/profile-defaults.yaml.
  - Neither → exit 15.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

import policy_errors

VALID_PROFILES = ("microservice", "bff", "frontend")


def _detect_target(cwd: Path) -> tuple[str, Path | None]:
    plugin = cwd / ".claude-plugin" / "plugin.json"
    project = cwd / ".sn-init-state.json"
    if plugin.exists() and project.exists():
        return "ambiguous", None
    if plugin.exists():
        return "plugin", cwd
    if project.exists():
        return "project", cwd
    return "invalid", None


def _yaml_path(target_kind: str, root: Path, profile: str) -> Path:
    if target_kind == "plugin":
        return root / "skills" / "sn-setup" / "templates" / "profile" / profile / "default_policies.yaml"
    return root / ".claude" / "profile-defaults.yaml"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _save(path: Path, profile: str, slugs: list[str]) -> None:
    body = f"profile: {profile}\npolicies:\n" + "".join(f"  - {s}\n" for s in slugs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="sn-setup profile", add_help=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")
    sp_show = sub.add_parser("show"); sp_show.add_argument("profile")
    sp_add = sub.add_parser("add"); sp_add.add_argument("slug"); sp_add.add_argument("--profile", required=True)
    sp_rm = sub.add_parser("remove"); sp_rm.add_argument("slug"); sp_rm.add_argument("--profile", required=True)
    sp_sw = sub.add_parser("swap"); sp_sw.add_argument("--profile", required=True)
    sp_sw.add_argument("from_slug"); sp_sw.add_argument("to_slug")

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    try:
        return _dispatch(ns)
    except policy_errors.PolicyError as e:
        print(f"sn-setup profile: {e}", file=sys.stderr)
        return e.exit_code


def _dispatch(ns: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    kind, root = _detect_target(cwd)
    if kind == "ambiguous":
        raise policy_errors.CwdAmbiguousOrInvalid(
            "cwd has both .claude-plugin/plugin.json and .sn-init-state.json; "
            "pass --target=plugin|project"
        )
    if kind == "invalid":
        raise policy_errors.CwdAmbiguousOrInvalid(
            "sn-setup profile must run inside a plugin repo or a scaffolded project"
        )

    if ns.cmd == "list":
        if kind == "plugin":
            base = root / "skills" / "sn-setup" / "templates" / "profile"
            for child in sorted(p for p in base.iterdir() if p.is_dir()):
                y = child / "default_policies.yaml"
                if y.exists():
                    data = _load(y)
                    print(f"{child.name}: {data.get('policies', [])}")
        else:
            data = _load(root / ".claude" / "profile-defaults.yaml")
            print(f"{data.get('profile', '?')}: {data.get('policies', [])}")
        return 0

    if ns.cmd == "show":
        path = _yaml_path(kind, root, ns.profile)
        if not path.exists():
            raise policy_errors.UnknownProfile(f"profile {ns.profile!r} has no defaults file at {path}")
        print(path.read_text())
        return 0

    profile = ns.profile
    if profile not in VALID_PROFILES:
        raise policy_errors.UnknownProfile(
            f"unknown profile {profile!r}; valid: {VALID_PROFILES}"
        )

    path = _yaml_path(kind, root, profile)
    data = _load(path)
    policies = list(data.get("policies") or [])

    if ns.cmd == "add":
        if ns.slug not in policies:
            policies.append(ns.slug)
        _save(path, profile, policies)
        return 0

    if ns.cmd == "remove":
        policies = [p for p in policies if p != ns.slug]
        _save(path, profile, policies)
        return 0

    if ns.cmd == "swap":
        policies = [ns.to_slug if p == ns.from_slug else p for p in policies]
        if ns.to_slug not in policies:
            policies.append(ns.to_slug)
        _save(path, profile, policies)
        return 0

    return 2
```

- [ ] **Step 4: Run tests — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_profile_cli.py -v`
Expected: 7 passed.

- [ ] **Step 5: No-regression**

Run: `.venv/bin/python -m pytest -q`
Expected: 217 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/profile_cli.py tests/test_profile_cli.py
git commit -m "$(cat <<'EOF'
feat(policy): sn-setup profile sub-tree (list/show/add/remove/swap)

Auto-detects plugin repo vs scaffolded project; edits the appropriate YAML.
Validates profile names and rejects ambiguous cwd with exit 15.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

### Task 14: Golden snapshot + docs + changelog + backlog

**Files:**
- Create: `tests/golden/scaffolded-microservice/{CLAUDE.md,profile-defaults.yaml,settings.json,applied_policies.json}`
- Modify: `tests/test_sn_init.py` (add golden snapshot test)
- Modify: `commands/sn-setup.md` (document new flags + sub-trees)
- Modify: `docs/backlog.md` (mark B1.1 + B1.2 superseded; link spec + PR1)
- Modify: `CHANGELOG.md` (Unreleased entry)

- [ ] **Step 1: Write the golden snapshot test (failing)**

Append to `tests/test_sn_init.py`:

```python
def test_microservice_golden_snapshot(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice")
    project = tmp_path / "demo"
    golden = Path(__file__).parent / "golden" / "scaffolded-microservice"

    # CLAUDE.md ## Policies section equality (ignore the rest of the file).
    full = (project / "CLAUDE.md").read_text()
    section = "## Policies\n" + full.split("## Policies\n", 1)[1].split("## ", 1)[0]
    assert section.strip() == (golden / "CLAUDE.md.policies-section").read_text().strip()

    # profile-defaults equality.
    assert (project / ".claude" / "profile-defaults.yaml").read_text() == \
           (golden / "profile-defaults.yaml").read_text()

    # applied_policies (slugs only, sorted) equality.
    state = json.loads((project / ".sn-init-state.json").read_text())
    slugs = sorted(p["slug"] for p in state["applied_policies"])
    assert slugs == json.loads((golden / "applied_policies.json").read_text())

    # settings.json keys+matchers sanity.
    settings = json.loads((project / ".claude" / "settings.json").read_text())
    expected_hooks = json.loads((golden / "settings.json").read_text())
    # Compare only "hooks" sub-tree because settings.json has many other keys.
    for hook_name, entries in expected_hooks["hooks"].items():
        actual = settings["hooks"].get(hook_name, [])
        actual_keys = sorted((e["policy"], e.get("matcher", "")) for e in actual)
        expected_keys = sorted((e["policy"], e.get("matcher", "")) for e in entries)
        assert actual_keys == expected_keys, f"{hook_name}: {actual_keys} != {expected_keys}"
```

- [ ] **Step 2: Run — expected fail (golden missing)**

Run: `.venv/bin/python -m pytest tests/test_sn_init.py::test_microservice_golden_snapshot -v`
Expected: FileNotFoundError.

- [ ] **Step 3: Run a scaffold once + capture golden**

```bash
mkdir -p tests/golden/scaffolded-microservice
.venv/bin/python -c "
import os, json, sys
sys.path.insert(0, 'scripts')
os.chdir('/tmp')
import shutil; shutil.rmtree('/tmp/golden-cap', ignore_errors=True)
os.makedirs('/tmp/golden-cap')
os.chdir('/tmp/golden-cap')
import sn_init
sn_init.main(['demo', '--no-git', '--profile=microservice'])
"

# CLAUDE.md ## Policies section
.venv/bin/python -c "
text = open('/tmp/golden-cap/demo/CLAUDE.md').read()
section = '## Policies\n' + text.split('## Policies\n', 1)[1].split('## ', 1)[0]
open('tests/golden/scaffolded-microservice/CLAUDE.md.policies-section', 'w').write(section)
"

# profile-defaults.yaml
cp /tmp/golden-cap/demo/.claude/profile-defaults.yaml tests/golden/scaffolded-microservice/profile-defaults.yaml

# applied_policies (slugs only, sorted)
.venv/bin/python -c "
import json
state = json.load(open('/tmp/golden-cap/demo/.sn-init-state.json'))
slugs = sorted(p['slug'] for p in state['applied_policies'])
open('tests/golden/scaffolded-microservice/applied_policies.json', 'w').write(json.dumps(slugs, indent=2) + '\n')
"

# settings.json
cp /tmp/golden-cap/demo/.claude/settings.json tests/golden/scaffolded-microservice/settings.json

rm -rf /tmp/golden-cap
```

- [ ] **Step 4: Verify each golden file makes sense — review by eye**

Read the four files in `tests/golden/scaffolded-microservice/` and confirm:
- `CLAUDE.md.policies-section` has 6 rows under the table header.
- `profile-defaults.yaml` has `profile: microservice` + 6 policies.
- `applied_policies.json` lists those 6 slugs sorted alphabetically.
- `settings.json` has hook entries from `memory-regulated`/`audit-log-strict`/`supply-chain-scan`/`secret-scan`/`commit-msg-gate` that ship `settings.patch.json` (NOT `memory-regulated` because microservice defaults pick `memory-ordinary`).

If anything looks wrong, the test will fail anyway — fix the bug upstream rather than hand-editing the golden.

- [ ] **Step 5: Run golden test — expected PASS**

Run: `.venv/bin/python -m pytest tests/test_sn_init.py::test_microservice_golden_snapshot -v`
Expected: 1 passed.

- [ ] **Step 6: Update `commands/sn-setup.md`**

Open `commands/sn-setup.md`. Find the flag table and append rows:

```markdown
| `--policies=<csv>` | Replace profile defaults with this exact list. | none |
| `--add-policies=<csv>` | Add policies to the profile defaults. Cannot combine with `--policies=`. | none |
| `--remove-policies=<csv>` | Remove policies from the profile defaults. Cannot combine with `--policies=`. | none |
| `--with-deps` | When applying, also install required-by policies. | false |
```

Add a new section after the flag table:

```markdown
## Sub-commands

After the initial scaffold, two sub-trees manage policies in the current
project:

- `sn-setup policy <list|show|apply|remove|upgrade|status|show-applied|history|lint>` — apply or remove individual policies; see spec §4 for full reference.
- `sn-setup profile <list|show|add|remove|swap>` — edit the profile→default-policies mapping (auto-detects plugin repo vs scaffolded project).

See `docs/superpowers/specs/2026-06-24-policy-catalog-design.md` for the full design.
```

- [ ] **Step 7: Update `docs/backlog.md`**

Replace the B1.1 + B1.2 entries with a single `[x]` line each pointing at PR1:

```markdown
### B1.1 `[x]` Repository Ecosystem table — shipped as the `repository-ecosystem` policy in **PR1 policy catalog** (`docs/superpowers/specs/2026-06-24-policy-catalog-design.md`).

### B1.2 `[x]` Two-tier memory-policy signal — shipped as `memory-ordinary` + `memory-regulated` policies (exclusive group `memory-tier`) in **PR1 policy catalog**.

### NEW B1.8 `[~]` Policy catalog (PR1) — branch `feat/policy-catalog`
- **Why**: composable, versioned policies (spec §0).
- **Where**: `scripts/policy_*.py`, `skills/sn-setup/templates/policies/<slug>/`, `skills/sn-setup/templates/profile/<P>/default_policies.yaml`.
- **Scope**: 9 day-one policies, `sn-setup policy` + `sn-setup profile` CLI, lint, status, upgrade, history, profile-bundled defaults.
- **Follow-ups**: PR2 profile expansion (worker/cli/library/gateway/mcp-server); PR3 default bundles for new profiles.
```

- [ ] **Step 8: Update `CHANGELOG.md`**

Append to the existing `[Unreleased]` section:

```markdown
- **Policy catalog** (PR1; supersedes B1.1 + B1.2). Composable, versioned policies under `skills/sn-setup/templates/policies/<slug>/`. Two new CLI sub-trees:
  - `sn-setup policy <list|show|apply|remove|upgrade|status|show-applied|history|lint>` — operate on the current project.
  - `sn-setup profile <list|show|add|remove|swap>` — edit profile defaults (auto-detect plugin source vs project-local).
  - Nine day-one policies spanning security, conventions, workflow, and observability.
  - Profile-bundled defaults applied automatically; override with `--policies=` (replace) or `--add-policies=` / `--remove-policies=` (delta).
  - State extensions: `applied_policies` + append-only `policy_history` in `.sn-init-state.json`. Legacy state files auto-migrate.
```

- [ ] **Step 9: Run full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: 218 passed (golden test added).

- [ ] **Step 10: Commit**

```bash
git add tests/golden tests/test_sn_init.py commands/sn-setup.md docs/backlog.md CHANGELOG.md
git commit -m "$(cat <<'EOF'
docs(policy): golden snapshot + commands.md + backlog + changelog

Microservice profile snapshot pins the catalog wiring across CLAUDE.md
section, profile-defaults.yaml, applied_policies, and settings.json hooks.
B1.1 + B1.2 marked [x] (shipped as repository-ecosystem and
memory-ordinary/memory-regulated policies). New backlog item B1.8 covers the
catalog itself.

Author: Siripol <siripoln.media@gmail.com>
EOF
)"
```

---

## Self-Review

### Spec coverage

| Spec §  | Topic | Task(s) |
|---|---|---|
| §0 | Summary | All |
| §1 | Architecture overview | Task 5 (apply), Task 6 (remove), Task 7 (upgrade), Task 8 (multi-policy) |
| §2 | Per-policy components + schema | Task 2 (loader + schema), Task 10-11 (content) |
| §3 | Catalog content + defaults | Tasks 10-12 |
| §4 | CLI surface | Task 9 (policy), Task 13 (profile), Task 12 (scaffold flags) |
| §5 | Data flow apply/remove/upgrade/status | Tasks 5, 6, 7 |
| §6 | State shape | Task 1 (migration) + Task 5 (state writes) |
| §7 | Idempotency + edit-safety | Task 5 (idempotent apply), Task 6 (edit-safe remove), Task 7 (edit-safe upgrade) |
| §8 | Settings merge algebra | Task 3 |
| §9 | Profile defaults flow | Task 12 (scaffold), Task 13 (profile CLI) |
| §10 | Errors + exit codes | Task 2 (error classes), Task 8 (multi-policy errors), Task 9 (CLI error mapping), Task 12 (scaffold error mapping) |
| §11 | Tests | Each task adds tests; Task 14 adds the golden snapshot |
| §12 | Out of scope | Not implemented (correct) |
| §13 | Migration & rollout | Task 1 (legacy state migration) + Task 14 (changelog note) |
| §14 | Decisions log | All locked into task behaviors |
| §15 | Open follow-ups | Not implemented (correct) |

### Placeholder scan

- No `TODO`, `TBD`, `FIXME`, `implement later`, or "similar to Task N" markers in the plan body.
- Every code block contains complete code.
- Every command lists expected output.

### Type consistency

- `PolicyMeta` fields (Task 2) used unchanged in Task 5 (`apply`), Task 6 (`remove`), Task 7 (`upgrade`), Task 8 (`apply_many`).
- `ApplyReport` / `RemoveReport` / `UpgradeReport` / `StatusEntry` dataclasses defined in Tasks 5-7; consumers (Task 9 CLI) reference the same fields (`slug`, `was_noop`, `state`).
- `policy_state.read_state` / `write_state` / `sha256_file` / `sha256_str` signatures (Task 1) used consistently in Tasks 4-8.
- Error class names (Task 2) referenced in Tasks 5-13.
- Exit codes (constants from `policy_errors`) used in scaffold tests (Task 12) + CLI tests (Tasks 9, 13).

No drift found. Plan is internally consistent.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-24-policy-catalog.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
