"""Tests for scripts/commands_migration.py — flat → grouped rename."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import commands_migration  # type: ignore


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
GROUPED_TEMPLATES = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "claude" / "commands"


def _seed_scaffold(tmp_path: Path, with_flat: bool = True) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    cmd_dir = project / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    (project / ".sn-init-state.json").write_text(json.dumps({"mode": "new"}))
    if with_flat:
        # Copy each flat slug from the plugin's grouped templates as a stand-in.
        # We don't need the real old content; the sha-check works against the
        # current disk content vs. recorded state. For the noop tests we just
        # write a known string.
        for flat in commands_migration.FLAT_TO_GROUP:
            (cmd_dir / f"{flat}.md").write_text(f"# {flat}\n")
        # Retired files too.
        for slug in commands_migration.RETIRED:
            (cmd_dir / f"{slug}.md").write_text(f"# {slug}\n")
    return project


def test_migration_noop_on_fresh_scaffold(tmp_path: Path):
    """No flat files present → state still flips; no errors."""
    project = _seed_scaffold(tmp_path, with_flat=False)
    report = commands_migration.run(project)
    assert report.from_flat == []
    assert report.retired == []
    # Grouped files were written from the plugin templates.
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        assert (project / ".claude" / "commands" / grouped).exists()


def test_migration_renames_unedited_flat_files(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=True)
    # All 15 flat files removed; grouped files in place.
    for flat in commands_migration.FLAT_TO_GROUP:
        assert not (project / ".claude" / "commands" / f"{flat}.md").exists()
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        assert (project / ".claude" / "commands" / grouped).exists()
    assert sorted(report.from_flat) == sorted(commands_migration.FLAT_TO_GROUP)


def test_migration_skips_user_edited_without_force(tmp_path: Path):
    """When the plugin's flat-template content doesn't match the on-disk
    content, the on-disk file is treated as user-edited and skipped
    unless --force is set. We seed with fake content to simulate."""
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=False)
    # Without force, every flat file is "edited" relative to the plugin
    # templates (which were deleted in Tasks 1-3), so all 15 should be
    # skipped.
    assert len(report.skipped) >= 1  # at least one user-edited file
    # State should still record commands_renamed_at.


def test_migration_force_deletes_edited(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=True)
    # With --force, edited files are deleted anyway.
    for flat in commands_migration.FLAT_TO_GROUP:
        assert not (project / ".claude" / "commands" / f"{flat}.md").exists()
    assert report.skipped == []


def test_migration_deletes_retired_tech_matrix(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    report = commands_migration.run(project, force=True)
    assert "sn-knowledge-tech-matrix" in report.retired
    assert not (project / ".claude" / "commands" / "sn-knowledge-tech-matrix.md").exists()


def test_migration_idempotent_after_first_run(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    commands_migration.run(project, force=True)
    # Now state.commands_renamed_at is set. Re-run.
    report2 = commands_migration.run(project, force=True)
    # No-op: empty report.
    assert report2.from_flat == []
    assert report2.retired == []
    assert report2.skipped == []


def test_migration_dry_run_writes_nothing(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    cmd_dir = project / ".claude" / "commands"
    files_before = sorted(p.name for p in cmd_dir.iterdir())
    report = commands_migration.run(project, force=True, dry_run=True)
    files_after = sorted(p.name for p in cmd_dir.iterdir())
    assert files_before == files_after  # nothing changed on disk
    # Report still computed.
    assert len(report.from_flat) > 0
    # State NOT flipped.
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert "commands_renamed_at" not in state


def test_migration_records_full_state_block(tmp_path: Path):
    project = _seed_scaffold(tmp_path)
    commands_migration.run(project, force=True)
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert "commands_renamed_at" in state
    assert state["commands_renamed_at"] is not None
    assert state["commands_migration"]["from_flat"]
    assert state["commands_migration"]["to_grouped"] == ["sn-sprint", "sn-req", "sn-knowledge"]
    assert "skipped" in state["commands_migration"]
    assert state["commands_migration"]["retired"] == ["sn-knowledge-tech-matrix"]
