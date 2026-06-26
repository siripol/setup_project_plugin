"""Pair-mode integration tests for sn_init --workspace."""
from __future__ import annotations

import json
import os
from pathlib import Path

import sn_init  # type: ignore


def _run_sn_init(cwd: Path, *argv: str) -> int:
    old = Path.cwd()
    try:
        os.chdir(cwd)
        return sn_init.main(list(argv))
    finally:
        os.chdir(old)


def test_workspace_flag_creates_sibling_workspace(tmp_path: Path):
    """P1: --workspace scaffolds a sibling <project>-workspace dir."""
    rc = _run_sn_init(tmp_path, "demo", "--workspace", "--no-git")
    assert rc == 0
    ws = tmp_path / "demo-workspace"
    assert (ws / "WORKSPACE.md").is_file()
    assert (ws / ".workspace" / "registry.json").is_file()


def test_workspace_flag_auto_registers_demo(tmp_path: Path):
    """P2: --workspace auto-registers the just-scaffolded project."""
    _run_sn_init(tmp_path, "demo", "--workspace", "--no-git")
    reg = json.loads((tmp_path / "demo-workspace" / ".workspace" / "registry.json").read_text())
    slugs = [s["slug"] for s in reg["services"]]
    assert "demo" in slugs


def test_workspace_name_flag_overrides_default(tmp_path: Path):
    """P3: --workspace-name overrides <project>-workspace default."""
    _run_sn_init(tmp_path, "demo", "--workspace", "--workspace-name=acme-ws", "--no-git")
    ws = tmp_path / "acme-ws"
    assert (ws / "WORKSPACE.md").is_file()
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert reg["name"] == "acme-ws"


def test_workspace_flag_idempotent_on_existing_workspace(tmp_path: Path):
    """P4: re-running scaffold into the same workspace skips init; subsequent add registers the new project (no duplicate slug)."""
    _run_sn_init(tmp_path, "demo", "--workspace", "--no-git")
    rc = _run_sn_init(tmp_path, "demo2", "--workspace", "--workspace-name=demo-workspace", "--no-git")
    assert rc == 0
    reg = json.loads((tmp_path / "demo-workspace" / ".workspace" / "registry.json").read_text())
    slugs = [s["slug"] for s in reg["services"]]
    assert set(slugs) == {"demo", "demo2"}
