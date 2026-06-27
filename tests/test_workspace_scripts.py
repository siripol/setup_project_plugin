"""Tests for the workspace bash scripts (status / sync / launch)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import workspace_cli  # type: ignore


def _init_env() -> dict:
    base = {**os.environ}
    base.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    return base


def _ws_and_member(tmp_path: Path):
    """Set up a workspace + 1 registered service. Returns (ws, svc)."""
    old = Path.cwd()
    os.chdir(tmp_path)
    try:
        workspace_cli.main(["init", "ws"])
    finally:
        os.chdir(old)
    ws = tmp_path / "ws"

    svc = tmp_path / "svc"
    svc.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(svc), check=True, env=_init_env())
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                   cwd=str(svc), check=True, env=_init_env())

    os.chdir(ws)
    try:
        workspace_cli.main(["add", str(svc)])
    finally:
        os.chdir(old)
    return ws, svc


def test_status_sh_runs_against_clean_registry(tmp_path: Path):
    """S1: status.sh emits one line per service with expected fields."""
    ws, svc = _ws_and_member(tmp_path)
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "status.sh")],
        capture_output=True, text=True, cwd=str(ws),
    )
    assert out.returncode == 0
    assert "slug=svc" in out.stdout
    assert "branch=" in out.stdout
    assert "dirty=" in out.stdout


def test_status_sh_handles_missing_jq(tmp_path: Path, monkeypatch):
    """S2: status.sh works when jq is missing (PATH stripped)."""
    ws, svc = _ws_and_member(tmp_path)
    # Strip jq from PATH.
    minimal_path = ":".join(p for p in os.environ["PATH"].split(":")
                            if not shutil.which("jq", path=p))
    env = {**os.environ, "PATH": minimal_path}
    if shutil.which("jq", path=minimal_path):
        pytest.skip("Could not strip jq from PATH on this system")
    # Also skip if stripping jq collaterally removed standard utilities (dirname, etc.)
    if not shutil.which("dirname", path=minimal_path):
        pytest.skip("Stripping jq also removes core utilities (co-located on PATH); cannot test jq-missing fallback")
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "status.sh")],
        capture_output=True, text=True, cwd=str(ws), env=env,
    )
    assert out.returncode == 0
    assert "slug=svc" in out.stdout


def test_sync_sh_skips_dirty_repo(tmp_path: Path):
    """S3: sync.sh skips dirty member, emits stderr warning."""
    ws, svc = _ws_and_member(tmp_path)
    (svc / "dirty.txt").write_text("x")  # dirty WT
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "sync.sh")],
        capture_output=True, text=True, cwd=str(ws),
    )
    assert out.returncode == 0
    assert "skip svc: dirty" in out.stderr


def test_launch_sh_emits_code_workspace(tmp_path: Path):
    """S4: launch.sh --dry-run emits a valid .code-workspace JSON file."""
    ws, svc = _ws_and_member(tmp_path)
    out = subprocess.run(
        ["bash", str(ws / "scripts" / "launch.sh"), "--dry-run"],
        capture_output=True, text=True, cwd=str(ws),
    )
    assert out.returncode == 0
    code_ws = ws / "ws.code-workspace"
    assert code_ws.is_file()
    data = json.loads(code_ws.read_text(encoding="utf-8"))
    assert "folders" in data
    paths = [f["path"] for f in data["folders"]]
    assert "." in paths
    assert "../svc" in paths
