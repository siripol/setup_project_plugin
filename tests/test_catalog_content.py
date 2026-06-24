"""Catalog content sanity tests (spec §3 day-one set)."""
from __future__ import annotations

from pathlib import Path

import policy_loader

CATALOG = Path(__file__).resolve().parent.parent / "skills" / "sn-setup" / "templates" / "policies"


def test_catalog_present_for_tasks_10_11():
    expected = {
        "memory-ordinary", "memory-regulated", "repository-ecosystem",
        "audit-log-strict", "supply-chain-scan",
        "secret-scan", "commit-msg-gate", "branch-naming", "pdpa-compliance",
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
