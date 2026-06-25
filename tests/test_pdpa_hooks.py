"""Tests for the pdpa-compliance bash hooks (B2.5)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK_DIR = (
    PLUGIN_ROOT
    / "skills"
    / "sn-setup"
    / "templates"
    / "policies"
    / "pdpa-compliance"
    / "extras"
    / "hooks"
)
CONFIG_DIR = (
    PLUGIN_ROOT
    / "skills"
    / "sn-setup"
    / "templates"
    / "policies"
    / "pdpa-compliance"
    / "extras"
    / "config"
)


def _stage_project(tmp_path: Path) -> Path:
    """Make tmp_path look like a scaffolded project: CLAUDE.md + .claude/config/."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "CLAUDE.md").write_text("# proj\n")
    (project / ".claude" / "config").mkdir(parents=True)
    shutil.copy(CONFIG_DIR / "pdpa-allowlist.yaml",
                project / ".claude" / "config" / "pdpa-allowlist.yaml")
    return project


def _run_hook(hook_name: str, project: Path, payload: dict) -> subprocess.CompletedProcess:
    hook = HOOK_DIR / hook_name
    return subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(project),
        check=False,
    )


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed in CI sandbox")
def test_b2_5_data_handler_scan_blocks_pii_thai_ni(tmp_path: Path):
    project = _stage_project(tmp_path)
    payload = {
        "tool_input": {
            "file_path": str(project / "src" / "userdata.go"),
            "content": "// Sample customer record\nid=1234567890123",
        }
    }
    result = _run_hook("pdpa-data-handler-scan.sh", project, payload)
    assert result.returncode == 2, f"expected block, got {result.returncode}; stderr={result.stderr}"
    assert "Thai NI 13-digit" in result.stderr


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed in CI sandbox")
def test_b2_5_data_handler_scan_skips_allowlisted_path(tmp_path: Path):
    project = _stage_project(tmp_path)
    fixture = project / "test" / "fixtures" / "sample.md"
    fixture.parent.mkdir(parents=True)
    payload = {
        "tool_input": {
            "file_path": str(fixture),
            "content": "Email: user@example.com",
        }
    }
    result = _run_hook("pdpa-data-handler-scan.sh", project, payload)
    assert result.returncode == 0, f"expected allow, got {result.returncode}; stderr={result.stderr}"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed in CI sandbox")
def test_b2_5_data_handler_scan_no_jq_degrades_gracefully(tmp_path: Path, monkeypatch):
    """Smoke test that the hook exits 0 with a stderr warning when jq is masked."""
    project = _stage_project(tmp_path)
    # Create a stub PATH without jq.
    stub_dir = tmp_path / "stub-path"
    stub_dir.mkdir()
    for tool in ("bash", "awk", "grep", "cat", "dirname", "printf", "command"):
        src = shutil.which(tool)
        if src:
            os.symlink(src, stub_dir / tool)
    monkeypatch.setenv("PATH", str(stub_dir))
    payload = {"tool_input": {"file_path": str(project / "x"), "content": "Email: u@e.com"}}
    result = _run_hook("pdpa-data-handler-scan.sh", project, payload)
    assert result.returncode == 0
    assert "jq not installed" in result.stderr


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed in CI sandbox")
def test_b2_5_retention_check_blocks_missing_sidecar(tmp_path: Path):
    project = _stage_project(tmp_path)
    target = project / "data" / "users.csv"
    target.parent.mkdir(parents=True)
    payload = {"tool_input": {"file_path": str(target), "content": "id,name\n"}}
    result = _run_hook("pdpa-retention-check.sh", project, payload)
    assert result.returncode == 2
    assert "Missing sidecar" in result.stderr


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed in CI sandbox")
def test_b2_5_retention_check_allows_valid_sidecar(tmp_path: Path):
    project = _stage_project(tmp_path)
    target = project / "data" / "users.csv"
    target.parent.mkdir(parents=True)
    sidecar = target.with_name(target.name + ".meta.yaml")
    sidecar.write_text(
        "retention_days: 365\n"
        "data_subject: customer\n"
        "lawful_basis: contract\n"
        "data_categories: [name, email]\n"
        "controller: orders-team\n"
        "last_reviewed: 2026-06-26\n"
    )
    payload = {"tool_input": {"file_path": str(target), "content": "id,name\n"}}
    result = _run_hook("pdpa-retention-check.sh", project, payload)
    assert result.returncode == 0, f"stderr: {result.stderr}"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not installed in CI sandbox")
def test_b2_5_retention_check_blocks_invalid_lawful_basis(tmp_path: Path):
    project = _stage_project(tmp_path)
    target = project / "data" / "users.csv"
    target.parent.mkdir(parents=True)
    sidecar = target.with_name(target.name + ".meta.yaml")
    sidecar.write_text(
        "retention_days: 365\n"
        "data_subject: customer\n"
        "lawful_basis: unknown\n"
        "data_categories: [name]\n"
        "controller: orders-team\n"
        "last_reviewed: 2026-06-26\n"
    )
    payload = {"tool_input": {"file_path": str(target), "content": "x"}}
    result = _run_hook("pdpa-retention-check.sh", project, payload)
    assert result.returncode == 2
    assert "lawful_basis" in result.stderr
