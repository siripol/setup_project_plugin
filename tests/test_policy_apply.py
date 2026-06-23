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
