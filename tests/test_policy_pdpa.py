"""Tests for scripts/policy_pdpa.py — allowlist CLI."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import policy_pdpa  # type: ignore


def _scaffold(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    config_dir = project / ".claude" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "pdpa-allowlist.yaml").write_text(
        "# seeded\n"
        "allowlist:\n"
        "  - \"test/**\"\n"
        "  - \"docs/examples/**\"\n"
    )
    return project


def _run(project: Path, *argv: str) -> int:
    old = Path.cwd()
    try:
        os.chdir(project)
        return policy_pdpa.main(list(argv))
    finally:
        os.chdir(old)


def test_pdpa_allowlist_list_seeded(tmp_path: Path, capsys):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "list")
    assert rc == 0
    out = capsys.readouterr().out
    assert "test/**" in out
    assert "docs/examples/**" in out


def test_pdpa_allowlist_add_writes_yaml(tmp_path: Path):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "add", "src/**")
    assert rc == 0
    text = (project / ".claude" / "config" / "pdpa-allowlist.yaml").read_text()
    assert "src/**" in text


def test_pdpa_allowlist_add_idempotent(tmp_path: Path):
    project = _scaffold(tmp_path)
    _run(project, "allowlist", "add", "src/**")
    rc = _run(project, "allowlist", "add", "src/**")
    assert rc == 0  # idempotent no-op
    text = (project / ".claude" / "config" / "pdpa-allowlist.yaml").read_text()
    # Glob appears once.
    assert text.count("src/**") == 1


def test_pdpa_allowlist_add_refuses_traversal(tmp_path: Path, capsys):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "add", "../escape")
    assert rc == 2
    err = capsys.readouterr().err
    assert "directory traversal" in err


def test_pdpa_allowlist_add_refuses_absolute(tmp_path: Path):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "add", "/abs/path/**")
    assert rc == 2


def test_pdpa_allowlist_remove_strips_glob(tmp_path: Path):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "remove", "test/**")
    assert rc == 0
    text = (project / ".claude" / "config" / "pdpa-allowlist.yaml").read_text()
    assert "test/**" not in text


def test_pdpa_allowlist_remove_nonexistent_errors(tmp_path: Path, capsys):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "remove", "not/in/list")
    assert rc == 2


def test_pdpa_allowlist_explain_matches_first_hit(tmp_path: Path, capsys):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "explain", "test/fixtures/sample.md")
    assert rc == 0
    out = capsys.readouterr().out
    assert "test/**" in out


def test_pdpa_allowlist_explain_no_match_returns_1(tmp_path: Path):
    project = _scaffold(tmp_path)
    rc = _run(project, "allowlist", "explain", "src/handler.go")
    assert rc == 1


def test_pdpa_allowlist_list_missing_file_errors(tmp_path: Path, capsys):
    project = tmp_path / "fresh"
    project.mkdir()
    rc = _run(project, "allowlist", "list")
    assert rc == 2
    err = capsys.readouterr().err
    assert "not initialized" in err
