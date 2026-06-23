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
