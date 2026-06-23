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
