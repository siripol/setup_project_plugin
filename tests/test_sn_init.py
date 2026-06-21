"""Smoke + scaffold-tree tests for sn-init."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import sn_init  # type: ignore
import errors  # type: ignore


# ---------------------------------------------------------------------------
# helpers


def _run(tmp_path: Path, *cli_args: str, cwd: Path | None = None) -> int:
    cwd = cwd or tmp_path
    old = Path.cwd()
    try:
        os.chdir(cwd)
        return sn_init.main(list(cli_args))
    finally:
        os.chdir(old)


# ---------------------------------------------------------------------------
# argv + mode detect


def test_arg_parse_defaults():
    args = sn_init.build_parser().parse_args(["demo"])
    assert args.name == "demo"
    assert args.lang == "go"
    assert args.tier == "both"
    assert args.workflow == "spec-loop"
    assert args.dry_run is False


def test_detect_mode_new_with_name(tmp_path: Path):
    mode, target = sn_init.detect_mode(tmp_path, "demo")
    assert mode == "new"
    assert target == (tmp_path / "demo").resolve()


def test_detect_mode_new_when_empty(tmp_path: Path):
    mode, target = sn_init.detect_mode(tmp_path, None)
    assert mode == "new"
    assert target == tmp_path.resolve()


def test_detect_mode_add_when_non_empty(tmp_path: Path):
    (tmp_path / "existing.txt").write_text("x")
    mode, target = sn_init.detect_mode(tmp_path, None)
    assert mode == "add"
    assert target == tmp_path.resolve()


def test_detect_mode_target_non_empty_raises(tmp_path: Path):
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "existing.txt").write_text("x")
    with pytest.raises(errors.TargetNonEmptyError):
        sn_init.detect_mode(tmp_path, "demo")


# ---------------------------------------------------------------------------
# dry-run


def test_dry_run_creates_no_files(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--dry-run", "--no-git")
    assert rc == errors.EXIT_OK
    captured = capsys.readouterr()
    assert "[dry-run]" in captured.out
    # No new directories beyond cwd contents
    assert not (tmp_path / "demo").exists()


# ---------------------------------------------------------------------------
# new mode end-to-end


def _expected_top_level(name: str) -> list[str]:
    return [
        "AGENTS.md",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "Makefile",
        "README.md",
        ".env.example",
        ".gitignore",
        ".editorconfig",
        ".tool-versions",
        "agents/main.yaml",
        "agents/README.md",
        "environments/default.yaml",
        "environments/README.md",
        "mcp/mcp.json",
        "mcp/README.md",
        "skills/example-skill/SKILL.md",
        "skills/README.md",
        ".anthropic/README.md",
        "docs/principles/design.md",
        "docs/principles/plans.md",
        "docs/principles/product-sense.md",
        "docs/principles/quality.md",
        "docs/principles/reliability.md",
        "docs/principles/security.md",
        "docs/design-docs/index.md",
        "docs/design-docs/subagents.md",
        "docs/product-specs/index.md",
        "docs/references/anthropic-sdk-llms.txt",
        "docs/references/ant-cli-llms.txt",
        "docs/references/mcp-spec-llms.txt",
        "docs/references/managed-agents-api-llms.txt",
        "docs/requirements/template.md",
        "docs/sprints/template.md",
        "docs/tech-debt-tracker.md",
        # lang go overlay
        "go.mod",
        "src/agent.go",
        "src/client.go",
        "mcp_server/main.go",
        "mcp_server/README.md",
        "tests/agent_test.go",
        # .claude
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/skills/README.md",
        ".claude/commands/README.md",
        ".claude/agents/README.md",
        ".claude/agents/code-reviewer.md",
        ".claude/agents/test-writer.md",
        ".claude/hooks/README.md",
        # CI on by default
        ".github/workflows/ci.yml",
        # state file
        ".sn-init-state.json",
    ]


def test_new_mode_writes_expected_tree(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--no-git")
    assert rc == errors.EXIT_OK
    project = tmp_path / "demo"
    for rel in _expected_top_level("demo"):
        path = project / rel
        assert path.exists(), f"missing: {rel}"


def test_new_mode_state_file(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["mode"] == "new"
    assert state["lang"] == "go"
    assert state["tier"] == "both"
    assert "files_written" in state
    assert len(state["files_written"]) > 30


def test_new_mode_substitutes_placeholders(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    claude_md = (tmp_path / "demo" / "CLAUDE.md").read_text()
    assert "demo" in claude_md  # ${name} replaced
    assert "claude-opus-4-8" in claude_md
    assert "${name}" not in claude_md
    assert "${model}" not in claude_md


def test_new_mode_no_ci_skips_workflow(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--no-ci")
    assert not (tmp_path / "demo" / ".github" / "workflows" / "ci.yml").exists()


def test_new_mode_devcontainer_flag(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--devcontainer")
    assert (tmp_path / "demo" / ".devcontainer" / "devcontainer.json").exists()


def test_new_mode_license_flag(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--license=MIT")
    lic = (tmp_path / "demo" / "LICENSE").read_text()
    assert "MIT License" in lic


def test_new_mode_no_license_by_default(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    assert not (tmp_path / "demo" / "LICENSE").exists()


# ---------------------------------------------------------------------------
# add mode


def test_add_mode_writes_only_claude(tmp_path: Path):
    # non-empty cwd
    (tmp_path / "existing.txt").write_text("x")
    rc = _run(tmp_path, "--no-git")
    assert rc == errors.EXIT_OK
    assert (tmp_path / ".claude").is_dir()
    assert (tmp_path / ".claude" / "settings.json").exists()
    # Should NOT have touched a project base file
    assert not (tmp_path / "agents").exists()


def test_add_mode_refuses_when_claude_exists_no_state(tmp_path: Path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / "existing.txt").write_text("x")
    rc = _run(tmp_path, "--no-git")
    assert rc == errors.EXIT_CLAUDE_EXISTS_NO_STATE


def test_add_mode_idempotent_patch(tmp_path: Path):
    (tmp_path / "existing.txt").write_text("x")
    _run(tmp_path, "--no-git")
    # Remove one .claude file, re-run, expect it to be re-added without overwriting state
    target_file = tmp_path / ".claude" / "agents" / "code-reviewer.md"
    assert target_file.exists()
    target_file.unlink()
    rc = _run(tmp_path, "--no-git")
    assert rc == errors.EXIT_OK
    assert target_file.exists()


def test_add_mode_appends_gitignore(tmp_path: Path):
    (tmp_path / "existing.txt").write_text("x")
    (tmp_path / ".gitignore").write_text("node_modules\n")
    _run(tmp_path, "--no-git")
    gi = (tmp_path / ".gitignore").read_text()
    assert ".claude/CLAUDE.local.md" in gi
    assert ".claude/settings.local.json" in gi
    assert "node_modules" in gi  # original preserved


# ---------------------------------------------------------------------------
# lang overlays: py


def test_new_mode_py_overlay(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--lang=py", "--no-git")
    assert rc == errors.EXIT_OK
    project = tmp_path / "demo"
    expected = [
        "pyproject.toml",
        ".python-version",
        "src/agent.py",
        "src/client.py",
        "mcp_server/main.py",
        "mcp_server/README.md",
        "tests/test_agent.py",
        "tests/test_client.py",
        "Makefile.py",
    ]
    for rel in expected:
        assert (project / rel).exists(), f"missing: {rel}"


def test_new_mode_py_pyproject_substituted(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    pyproj = (tmp_path / "demo" / "pyproject.toml").read_text()
    assert 'name = "demo"' in pyproj
    assert "claude-agent-sdk" in pyproj
    assert "anthropic" in pyproj


def test_new_mode_py_state_lang(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["lang"] == "py"


# ---------------------------------------------------------------------------
# lang overlays: ts


def test_new_mode_ts_overlay(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--lang=ts", "--no-git")
    assert rc == errors.EXIT_OK
    project = tmp_path / "demo"
    expected = [
        "package.json",
        "tsconfig.json",
        "src/agent.ts",
        "src/client.ts",
        "mcp_server/main.ts",
        "mcp_server/README.md",
        "tests/agent.test.ts",
        "tests/client.test.ts",
        "Makefile.ts",
    ]
    for rel in expected:
        assert (project / rel).exists(), f"missing: {rel}"


def test_new_mode_ts_package_json_substituted(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    pkg = json.loads((tmp_path / "demo" / "package.json").read_text())
    assert pkg["name"] == "demo"
    assert "@anthropic-ai/claude-agent-sdk" in pkg["dependencies"]
    assert "@anthropic-ai/sdk" in pkg["dependencies"]
    assert "@modelcontextprotocol/sdk" in pkg["dependencies"]


def test_new_mode_ts_state_lang(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["lang"] == "ts"


# ---------------------------------------------------------------------------
# audit log hooks


def test_audit_log_default_on(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    assert (project / ".claude" / "hooks" / "audit.sh").exists()
    assert (project / ".claude" / "hooks" / "audit.py").exists()
    assert (project / ".claude" / "hooks" / "audit.ts").exists()
    assert (project / ".sn-init" / "logs" / ".gitkeep").exists()
    settings = json.loads((project / ".claude" / "settings.json").read_text())
    hooks = settings["hooks"]
    for event in ("PreToolUse", "PostToolUse", "UserPromptSubmit", "SessionStart", "SessionEnd", "Stop"):
        assert event in hooks, f"missing event registration: {event}"
        assert any(".claude/hooks/audit.sh" in (h.get("command", "")) for h in hooks[event])
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["flags"]["audit_log"] is True


def test_audit_log_opt_out(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--no-audit-log")
    project = tmp_path / "demo"
    assert not (project / ".claude" / "hooks" / "audit.sh").exists()
    assert not (project / ".claude" / "hooks" / "audit.py").exists()
    assert not (project / ".claude" / "hooks" / "audit.ts").exists()
    settings = json.loads((project / ".claude" / "settings.json").read_text())
    assert settings["hooks"] == {}
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["flags"]["audit_log"] is False


def test_audit_py_hook_signature(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    project = tmp_path / "demo"
    src = (project / ".claude" / "hooks" / "audit.py").read_text()
    assert "async def audit_hook" in src
    assert "MAX_INLINE_BYTES" in src


def test_agent_py_wires_audit_hook(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    src = (tmp_path / "demo" / "src" / "agent.py").read_text()
    assert "from audit import audit_hook" in src
    assert "HookMatcher" in src


def test_agent_ts_wires_audit_hook(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    src = (tmp_path / "demo" / "src" / "agent.ts").read_text()
    assert "auditHook" in src
    assert ".claude/hooks/audit.js" in src
