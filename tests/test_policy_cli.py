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


def test_policy_apply_use_profile_defaults_applies_missing(tmp_path: Path):
    project = _scaffold_project(tmp_path)
    # Seed project-local profile-defaults with one slug.
    (project / ".claude" / "profile-defaults.yaml").write_text(
        "profile: microservice\npolicies:\n  - sample-policy\n",
        encoding="utf-8",
    )
    rc = _run_cli(tmp_path, "apply", "--use-profile-defaults", cwd=project)
    assert rc == 0
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert any(p["slug"] == "sample-policy" for p in state["applied_policies"])


def test_policy_apply_use_profile_defaults_noop_when_all_applied(tmp_path: Path, capsys):
    project = _scaffold_project(tmp_path)
    (project / ".claude" / "profile-defaults.yaml").write_text(
        "profile: microservice\npolicies:\n  - sample-policy\n",
        encoding="utf-8",
    )
    # Apply once.
    _run_cli(tmp_path, "apply", "sample-policy", cwd=project)
    capsys.readouterr()
    rc = _run_cli(tmp_path, "apply", "--use-profile-defaults", cwd=project)
    assert rc == 0
    out = capsys.readouterr().out
    assert "applied 0" in out
    assert "already up-to-date" in out


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
