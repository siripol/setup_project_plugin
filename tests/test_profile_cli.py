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
