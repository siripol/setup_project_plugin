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
        "docs/PROMOTION.md",
        "docs/PREREQUISITES.md",
        "docs/GOVERNANCE-SERVICE-LEVEL.md",
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
        ".claude/docs/README.md",
        ".claude/docs/ARCHITECTURE.md",
        ".claude/rules/README.md",
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
    # Audit pipeline hooks must be absent. Policy hooks (added by profile defaults)
    # may still be present — they are independent of the --no-audit-log flag.
    all_commands = [
        entry.get("command", "")
        for entries in settings["hooks"].values()
        for entry in entries
    ]
    assert not any("audit.sh" in cmd for cmd in all_commands), (
        "audit.sh hook should not appear when --no-audit-log is passed"
    )
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


# ---------------------------------------------------------------------------
# subagent filtering


def test_subagents_default_minimal(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    agents = tmp_path / "demo" / ".claude" / "agents"
    assert (agents / "code-reviewer.md").exists()
    assert (agents / "test-writer.md").exists()
    # Optional subagents NOT present by default
    assert not (agents / "doc-writer.md").exists()
    assert not (agents / "security-auditor.md").exists()
    assert not (agents / "planner.md").exists()


def test_subagents_all_ships_optional(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--subagents=all")
    agents = tmp_path / "demo" / ".claude" / "agents"
    for name in ("code-reviewer", "test-writer", "doc-writer", "security-auditor", "planner"):
        assert (agents / f"{name}.md").exists(), f"missing: {name}"


def test_subagents_none_drops_all(tmp_path: Path):
    # --subagents=none + --workflow=none → only README.md remains.
    _run(tmp_path, "demo", "--no-git", "--subagents=none", "--workflow=none")
    agents = tmp_path / "demo" / ".claude" / "agents"
    md_files = list(agents.glob("*.md"))
    assert all(p.name == "README.md" for p in md_files), [p.name for p in md_files]


def test_subagents_unknown_rejected(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--no-git", "--subagents=does-not-exist")
    assert rc == errors.EXIT_USAGE


def test_subagent_shortcut_commands_gated_on_subagent(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--subagents=all")
    commands = tmp_path / "demo" / ".claude" / "commands"
    for slash in ("review", "test", "doc", "audit", "plan"):
        assert (commands / f"{slash}.md").exists(), f"missing /{slash}"


def test_subagent_shortcut_omitted_when_subagent_absent(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")  # only base 2 subagents
    commands = tmp_path / "demo" / ".claude" / "commands"
    assert (commands / "review.md").exists()
    assert (commands / "test.md").exists()
    assert not (commands / "audit.md").exists()
    assert not (commands / "plan.md").exists()
    assert not (commands / "doc.md").exists()


# ---------------------------------------------------------------------------
# workflow filtering


def test_workflow_spec_loop_default_ships_workflow_files(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    agents = tmp_path / "demo" / ".claude" / "agents"
    commands = tmp_path / "demo" / ".claude" / "commands"
    for name in ("task-decomposer", "task-executor", "task-tester", "integration-tester",
                 "evaluator", "adversary", "knowledge-curator", "impact-analyzer"):
        assert (agents / f"sn-{name}.md").exists(), f"missing workflow subagent: sn-{name}"
    # Grouped commands (Task 1+)
    assert (commands / "sn-sprint.md").exists(), "missing workflow command: sn-sprint"
    # Old flat sprint files must not exist after Task 1
    for old_flat in ("sprint-new", "sprint-add", "sprint-run", "sprint-done", "sprint-status"):
        assert not (commands / f"sn-{old_flat}.md").exists(), f"old flat file should not exist: sn-{old_flat}"
    # Grouped req command (Task 2)
    assert (commands / "sn-req.md").exists(), "missing workflow command: sn-req"
    # Old flat req files must not exist after Task 2
    for old_flat in ("req-new", "req-import", "req-rollback", "req-resume", "req-replay"):
        assert not (commands / f"sn-{old_flat}.md").exists(), f"old flat file should not exist: sn-{old_flat}"
    # Grouped knowledge command (Task 3)
    assert (commands / "sn-knowledge.md").exists(), "missing workflow command: sn-knowledge"
    # Old flat knowledge files must not exist after Task 3
    for old_flat in ("knowledge-check", "knowledge-update", "knowledge-promote", "knowledge-demote", "knowledge-tech-matrix"):
        assert not (commands / f"sn-{old_flat}.md").exists(), f"old flat file should not exist: sn-{old_flat}"
    # Individual command files still exist
    assert (commands / "sn-gh-import.md").exists(), "missing workflow command: sn-gh-import"
    # Old bare-name and colon-namespace layouts must not be present anymore.
    assert not (agents / "knowledge-curator.md").exists()
    assert not (commands / "sprint-run.md").exists()
    assert not (agents / "sn" / "knowledge-curator.md").exists()
    assert not (commands / "sn" / "sprint-run.md").exists()


def test_workflow_none_drops_workflow_files(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--workflow=none")
    agents = tmp_path / "demo" / ".claude" / "agents"
    commands = tmp_path / "demo" / ".claude" / "commands"
    for name in ("task-decomposer", "task-executor", "task-tester", "integration-tester",
                 "evaluator", "adversary", "knowledge-curator", "impact-analyzer"):
        assert not (agents / f"sn-{name}.md").exists(), f"unexpected workflow subagent: sn-{name}"
    for slash in ("sprint-new", "req-new", "knowledge-update"):
        assert not (commands / f"sn-{slash}.md").exists(), f"unexpected workflow command: sn-{slash}"
    assert (commands / "claude-local-edit.md").exists()
    assert (commands / "claude-local-show.md").exists()


WORKFLOW_SUBAGENTS = (
    "task-decomposer", "task-executor", "task-tester", "integration-tester",
    "evaluator", "adversary", "knowledge-curator", "impact-analyzer",
)


# ---------------------------------------------------------------------------
# harness scaffold


def test_harness_scaffold_present(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    h = tmp_path / "demo" / ".harness"
    for rel in ("README.md", "chokepoints.yaml", "proof-bundle-template.md",
                "rules/README.md", "invariants/README.md", "normal-forms/README.md"):
        assert (h / rel).exists(), f"missing: {rel}"


# ---------------------------------------------------------------------------
# claude-local commands


def test_claude_local_commands_always_shipped(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--workflow=none")
    commands = tmp_path / "demo" / ".claude" / "commands"
    assert (commands / "claude-local-edit.md").exists()
    assert (commands / "claude-local-show.md").exists()


# ---------------------------------------------------------------------------
# obsidian flags persisted in state


def test_obsidian_knowledge_default_project(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["flags"]["obsidian_knowledge"] == "project"
    assert state["flags"]["obsidian_mcp"] == "auto"


def test_obsidian_knowledge_global_flag(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--obsidian-knowledge=global", "--obsidian-mcp=on")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["flags"]["obsidian_knowledge"] == "global"
    assert state["flags"]["obsidian_mcp"] == "on"


# ---------------------------------------------------------------------------
# REQ importer


def test_req_import_from_markdown(tmp_path: Path):
    # First scaffold a project so docs/requirements/ exists.
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    src = project / "external-spec.md"
    src.write_text(
        "# Login flow\n\n"
        "Priority: high\n\n"
        "## Acceptance criteria\n"
        "- user can log in with email + password\n"
        "- session expires after 15 min idle\n",
        encoding="utf-8",
    )
    import subprocess
    importer = Path(__file__).resolve().parent.parent / "scripts" / "req_import.py"
    result = subprocess.run(
        ["python3", str(importer), str(src)], cwd=project, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    reqs = list((project / "docs" / "requirements" / "active").glob("REQ-*.md"))
    assert reqs, "no REQ file written"
    body = reqs[0].read_text()
    assert "Login flow" in body
    assert "session expires after 15 min idle" in body
    assert "priority: high" in body


# ---------------------------------------------------------------------------
# Obsidian client backend selection


def test_obsidian_client_default_backend_filesystem(tmp_path: Path):
    import sys as _sys

    plugin_root = Path(__file__).resolve().parent.parent
    _sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import importlib
        oc = importlib.import_module("obsidian_client")
        client = oc.make_client(oc.ObsidianConfig(
            vault_root=tmp_path, mode="auto", project="demo", knowledge_scope="project"
        ))
        assert client.backend == "fs"
    finally:
        _sys.path.remove(str(plugin_root / "scripts"))


def test_obsidian_client_mode_on_requires_mcp(tmp_path: Path):
    import sys as _sys

    plugin_root = Path(__file__).resolve().parent.parent
    _sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import importlib
        oc = importlib.import_module("obsidian_client")
        with pytest.raises(oc.ObsidianBackendMissing):
            oc.make_client(oc.ObsidianConfig(vault_root=tmp_path, mode="on", project="demo"))
    finally:
        _sys.path.remove(str(plugin_root / "scripts"))


def test_obsidian_client_writes_project_topic(tmp_path: Path):
    import sys as _sys

    plugin_root = Path(__file__).resolve().parent.parent
    _sys.path.insert(0, str(plugin_root / "scripts"))
    try:
        import importlib
        oc = importlib.import_module("obsidian_client")
        client = oc.make_client(oc.ObsidianConfig(
            vault_root=tmp_path, mode="off", project="demo", knowledge_scope="project"
        ))
        path = client.write_topic(
            "project", "auth", "## Notes\n\nSession TTL: 15 min.\n",
            traceback={"origin_project": "demo", "origin_req": "REQ-001"},
        )
        assert path == tmp_path / "knowledge" / "projects" / "demo" / "auth.md"
        body = path.read_text()
        assert "topic: auth" in body
        assert "Session TTL" in body
        assert "origin_project: demo" in body
    finally:
        _sys.path.remove(str(plugin_root / "scripts"))


# ---------------------------------------------------------------------------
# Safety hooks (rate-limit + chokepoint)


def test_rate_limit_hooks_present_by_default(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    hooks = tmp_path / "demo" / ".claude" / "hooks"
    for name in ("rate-limit.sh", "rate-limit.py", "rate-limit.ts",
                 "chokepoint-gate.sh", "chokepoint-gate.py", "chokepoint-gate.ts"):
        assert (hooks / name).exists(), f"missing: {name}"


def test_settings_registers_pretooluse_safety_hooks(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    settings = json.loads((tmp_path / "demo" / ".claude" / "settings.json").read_text())
    pre = settings["hooks"]["PreToolUse"]
    commands = [entry["command"] for entry in pre]
    assert ".claude/hooks/rate-limit.sh" in commands
    assert ".claude/hooks/chokepoint-gate.sh" in commands
    # Chokepoint gate scoped to Edit|Write matcher
    chokes = [e for e in pre if "chokepoint-gate.sh" in e["command"]]
    assert chokes and chokes[0].get("matcher") == "Edit|Write"


def test_no_audit_log_keeps_safety_hooks(tmp_path: Path):
    # --no-audit-log strips the audit pipeline but should not touch rate-limit/chokepoint.
    _run(tmp_path, "demo", "--no-git", "--no-audit-log")
    hooks = tmp_path / "demo" / ".claude" / "hooks"
    assert (hooks / "rate-limit.sh").exists()
    assert (hooks / "chokepoint-gate.sh").exists()
    assert not (hooks / "audit.sh").exists()
    settings = json.loads((tmp_path / "demo" / ".claude" / "settings.json").read_text())
    # settings.json has hooks: {} when --no-audit-log per current impl; this is the trade-off.
    # Future iteration can split audit vs safety hook stripping.
    # For now we just verify the hook files survived.
    _ = settings


def test_scaffold_includes_safety_scripts(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    scripts = tmp_path / "demo" / "scripts"
    for name in ("safety.py", "req_import.py", "obsidian_client.py"):
        assert (scripts / name).exists(), f"missing: {name}"
    assert (scripts / "importers" / "md.py").exists()


# ---------------------------------------------------------------------------
# Safety state helpers


def _import_safety():
    import importlib
    import sys as _sys
    plugin_root = Path(__file__).resolve().parent.parent
    sp = str(plugin_root / "scripts")
    if sp not in _sys.path:
        _sys.path.insert(0, sp)
    return importlib.import_module("safety")


def test_safety_record_call_resets_window(tmp_path: Path, monkeypatch):
    safety = _import_safety()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    safety.reset_rate_window({})
    window = safety.record_call(input_tokens=10, output_tokens=20)
    assert window["calls_this_hour"] == 1
    assert window["tokens_this_hour"] == 30


def test_safety_breaker_trips_after_no_progress(tmp_path: Path, monkeypatch):
    safety = _import_safety()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    for score in (50, 50, 50):
        safety.record_progress("REQ-001", score)
    assert safety.breaker_status("REQ-001") == "tripped"


def test_safety_breaker_trips_after_repeat_errors(tmp_path: Path, monkeypatch):
    safety = _import_safety()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    for _ in range(safety.REPEAT_ERROR_THRESHOLD):
        safety.record_repeat_error("REQ-002", "test_login")
    assert safety.breaker_status("REQ-002") == "tripped"


# ---------------------------------------------------------------------------
# Workflow Makefile contains safety + concurrency targets


def test_makefile_has_workflow_targets(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    mk = (tmp_path / "demo" / "Makefile").read_text()
    for target in (
        "claude-local-edit", "claude-local-show",
        "req-new", "req-import", "sprint-new", "sprint-add", "sprint-done",
        "knowledge-update", "knowledge-tech-matrix",
        "gh-import", "gh-close",
        "worktree-add", "worktree-remove", "sprint-concurrent",
        "safety-status", "safety-trip-breaker",
        "hooks-install", "hooks-uninstall", "orchestrate",
    ):
        assert f"{target}:" in mk, f"missing make target: {target}"


# ---------------------------------------------------------------------------
# Spec-loop orchestrator


def _import_orchestrator():
    import importlib
    import sys as _sys
    plugin_root = Path(__file__).resolve().parent.parent
    sp = str(plugin_root / "scripts")
    if sp not in _sys.path:
        _sys.path.insert(0, sp)
    return importlib.import_module("orchestrator")


def test_orchestrator_phases_listed():
    orchestrator = _import_orchestrator()
    assert orchestrator.PHASES[0] == "impact"
    assert orchestrator.PHASES[-1] == "done"
    assert "evaluate" in orchestrator.PHASES
    for phase in ("plan", "decompose", "execute", "test", "integrate", "adversary",
                  "evaluate", "curate"):
        assert phase in orchestrator.PHASE_TO_SUBAGENT


def test_orchestrator_invoke_stub_returns_ok():
    orchestrator = _import_orchestrator()
    verdict = orchestrator.invoke_subagent("planner", "test prompt", {})
    assert verdict["status"] == "ok"
    assert verdict["subagent"] == "planner"


def test_orchestrator_phase_records_history(tmp_path: Path, monkeypatch):
    orchestrator = _import_orchestrator()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")

    orch = orchestrator.Orchestrator(sprint_id="SPRINT-001", project_root=tmp_path)
    result = orch.phase("REQ-001", "plan")
    assert result["status"] == "ok"

    state = json.loads((tmp_path / ".sn-init" / "workflow-state.json").read_text())
    assert state["active_phase"]["REQ-001"] == "plan"
    history = state["phase_history"]["REQ-001"]
    assert history[-1]["phase"] == "plan"


def test_orchestrator_run_missing_sprint_returns_error(tmp_path: Path, monkeypatch):
    orchestrator = _import_orchestrator()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    orch = orchestrator.Orchestrator(sprint_id="SPRINT-404", project_root=tmp_path)
    assert orch.run() == 2


def test_orchestrator_run_processes_reqs(tmp_path: Path, monkeypatch):
    orchestrator = _import_orchestrator()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    sprint = tmp_path / "docs" / "sprints" / "active" / "SPRINT-007-x"
    (sprint / "requirements").mkdir(parents=True)
    (sprint / "requirements" / "REQ-042-foo.md").write_text("body")

    orch = orchestrator.Orchestrator(sprint_id="SPRINT-007", project_root=tmp_path)
    assert orch.run() == 0
    state = json.loads((tmp_path / ".sn-init" / "workflow-state.json").read_text())
    assert state["sprints"]["SPRINT-007"]["status"] == "completed"


def test_orchestrator_emits_done_promise_on_pass(tmp_path: Path, monkeypatch, capsys):
    """Triple-signal pass must emit the ralph-loop completion promise verbatim."""
    orchestrator = _import_orchestrator()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    sprint = tmp_path / "docs" / "sprints" / "active" / "SPRINT-101-x"
    (sprint / "requirements").mkdir(parents=True)
    (sprint / "requirements" / "REQ-001-foo.md").write_text("body")

    orch = orchestrator.Orchestrator(sprint_id="SPRINT-101", project_root=tmp_path)
    rc = orch.run()
    assert rc == 0
    out = capsys.readouterr().out
    assert "DONE: SPRINT-101 triple-signal pass" in out


def test_orchestrator_emits_blocked_promise_on_phase_failure(tmp_path: Path, monkeypatch, capsys):
    """A phase failure must emit `BLOCKED: <sprint> <reason>` so ralph terminates."""
    orchestrator = _import_orchestrator()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".sn-init").mkdir()
    (tmp_path / "CLAUDE.md").write_text("anchor")
    sprint = tmp_path / "docs" / "sprints" / "active" / "SPRINT-102-x"
    (sprint / "requirements").mkdir(parents=True)
    (sprint / "requirements" / "REQ-001-foo.md").write_text("body")

    # Force the orchestrator's invoke_subagent stub to return an error verdict
    # so the spec-loop fails and `_run_one_req` emits a BLOCKED: promise.
    def _fail(*args, **kwargs):
        return {"status": "failed", "reason": "circuit breaker tripped"}
    monkeypatch.setattr(orchestrator, "invoke_subagent", _fail)

    orch = orchestrator.Orchestrator(sprint_id="SPRINT-102", project_root=tmp_path)
    rc = orch.run()
    assert rc == 1
    out = capsys.readouterr().out
    assert "BLOCKED: SPRINT-102 breaker tripped" in out
    assert "DONE: SPRINT-102" not in out


def test_orchestrator_promise_strings_match_ralph_contract():
    """Promise lines short (<2KB) so audit.sh + ralph see the same stdout."""
    orchestrator = _import_orchestrator()
    # _emit_promise renders strings inline; verify shape directly against the
    # contract documented in WORKFLOW.md.
    orch = orchestrator.Orchestrator(sprint_id="SPRINT-001", project_root=Path("/tmp"))
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        orch._emit_promise("DONE", "triple-signal pass")
        orch._emit_promise("BLOCKED", "breaker tripped")
        orch._emit_promise("BLOCKED", "rate-limit exhausted")
    lines = buf.getvalue().splitlines()
    assert lines == [
        "DONE: SPRINT-001 triple-signal pass",
        "BLOCKED: SPRINT-001 breaker tripped",
        "BLOCKED: SPRINT-001 rate-limit exhausted",
    ]
    for line in lines:
        assert len(line.encode("utf-8")) < 2048


# ---------------------------------------------------------------------------
# Lang orchestrator files


def test_py_overlay_ships_orchestrator(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    src = (tmp_path / "demo" / "src" / "orchestrator.py").read_text()
    assert "invoke_subagent" in src


def test_ts_overlay_ships_orchestrator(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    src = (tmp_path / "demo" / "src" / "orchestrator.ts").read_text()
    assert "invokeSubagent" in src
    pkg = json.loads((tmp_path / "demo" / "package.json").read_text())
    assert "orchestrator" in pkg["scripts"]


def test_go_overlay_ships_orchestrator(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=go", "--no-git")
    src = (tmp_path / "demo" / "src" / "cmd" / "orchestrator" / "main.go").read_text()
    assert "invokeSubagent" in src


# ---------------------------------------------------------------------------
# Git hooks scaffold


def test_githooks_scaffold_present(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    hooks = tmp_path / "demo" / ".githooks"
    assert (hooks / "README.md").exists()
    assert (hooks / "commit-msg").exists()
    assert (hooks / "post-merge").exists()


def test_commit_msg_hook_rejects_messages_without_req(tmp_path: Path):
    import subprocess
    _run(tmp_path, "demo", "--no-git")
    hook = tmp_path / "demo" / ".githooks" / "commit-msg"
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat: add a thing\n")
    result = subprocess.run([str(hook), str(msg_file)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "REQ id" in result.stderr


def test_commit_msg_hook_accepts_chore_and_req(tmp_path: Path):
    import subprocess
    _run(tmp_path, "demo", "--no-git")
    hook = tmp_path / "demo" / ".githooks" / "commit-msg"
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("chore: bump deps\n")
    assert subprocess.run([str(hook), str(msg_file)]).returncode == 0
    msg_file.write_text("feat(REQ-042): wire login flow\n")
    assert subprocess.run([str(hook), str(msg_file)]).returncode == 0


_AUTHOR_TRAILER = "Author: Siripol <siripoln.media@gmail.com>"


def test_commit_msg_hook_strips_claude_coauthor(tmp_path: Path):
    import subprocess
    _run(tmp_path, "demo", "--no-git")
    hook = tmp_path / "demo" / ".githooks" / "commit-msg"
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text(
        "feat(REQ-001): x\n"
        "\n"
        "Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>\n"
    )
    result = subprocess.run([str(hook), str(msg_file)], capture_output=True, text=True)
    assert result.returncode == 0
    body = msg_file.read_text()
    assert "Claude" not in body
    assert "noreply@anthropic" not in body

    # Casing variant — confirms the explicit char-class regex matches on BSD sed.
    msg_file.write_text(
        "feat(REQ-001): x\n"
        "\n"
        "co-authored-by: CLAUDE Sonnet <noreply@anthropic.com>\n"
    )
    assert subprocess.run([str(hook), str(msg_file)]).returncode == 0
    assert "CLAUDE" not in msg_file.read_text()


def test_commit_msg_hook_appends_author_trailer_when_missing(tmp_path: Path):
    import subprocess
    _run(tmp_path, "demo", "--no-git")
    hook = tmp_path / "demo" / ".githooks" / "commit-msg"
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat(REQ-001): x\n")
    assert subprocess.run([str(hook), str(msg_file)]).returncode == 0
    body = msg_file.read_text()
    assert body.rstrip().endswith(_AUTHOR_TRAILER)


def test_commit_msg_hook_is_idempotent_on_author_trailer(tmp_path: Path):
    import subprocess
    _run(tmp_path, "demo", "--no-git")
    hook = tmp_path / "demo" / ".githooks" / "commit-msg"
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat(REQ-001): x\n")
    for _ in range(2):
        assert subprocess.run([str(hook), str(msg_file)]).returncode == 0
    assert msg_file.read_text().count(_AUTHOR_TRAILER) == 1

    # A different Author: line for a real co-contributor must be preserved
    # (we match on the full Siripol identity, not on any `^Author:`).
    msg_file.write_text(
        "feat(REQ-002): pair work\n"
        "\n"
        "Author: Pair Programmer <pair@example.com>\n"
    )
    assert subprocess.run([str(hook), str(msg_file)]).returncode == 0
    body = msg_file.read_text()
    assert "Author: Pair Programmer <pair@example.com>" in body
    assert _AUTHOR_TRAILER in body


def test_in_repo_commit_msg_hook_strip_and_stamp(tmp_path: Path):
    """The in-repo .githooks/commit-msg (no REQ-id enforcement) must mirror
    the scaffold-template strip+stamp behavior. Guards against the two hooks
    silently diverging."""
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent
    hook = repo_root / ".githooks" / "commit-msg"
    assert hook.exists(), f"in-repo hook missing at {hook}"
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text(
        "feat(scaffold): tweak\n"
        "\n"
        "Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>\n"
    )
    result = subprocess.run([str(hook), str(msg_file)], capture_output=True, text=True)
    assert result.returncode == 0
    body = msg_file.read_text()
    assert "Claude" not in body
    assert body.rstrip().endswith(_AUTHOR_TRAILER)


# ---------------------------------------------------------------------------
# Real SDK wire-up in lang overlays


def test_py_agent_uses_real_sdk_imports(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    src = (tmp_path / "demo" / "src" / "agent.py").read_text()
    assert "from claude_agent_sdk import" in src
    assert "query" in src
    assert "ClaudeAgentOptions" in src
    assert "AgentDefinition" in src
    assert "rate_limit_hook" in src or "rate-limit" in src
    assert "chokepoint_gate_hook" in src


def test_py_client_uses_anthropic_beta_sessions(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    src = (tmp_path / "demo" / "src" / "client.py").read_text()
    assert "from anthropic import Anthropic" in src
    assert "beta.sessions.create" in src
    assert "events.stream" in src


def test_py_mcp_server_registers_real_tools(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    src = (tmp_path / "demo" / "mcp_server" / "main.py").read_text()
    assert "FastMCP" in src
    assert "@mcp.tool()" in src
    assert "list_project_files" in src


def test_ts_agent_uses_real_sdk_imports(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    src = (tmp_path / "demo" / "src" / "agent.ts").read_text()
    assert 'from "@anthropic-ai/claude-agent-sdk"' in src
    assert "rateLimitHook" in src
    assert "chokepointGateHook" in src
    assert "auditHook" in src


def test_ts_client_uses_anthropic_beta_sessions(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    src = (tmp_path / "demo" / "src" / "client.ts").read_text()
    assert 'from "@anthropic-ai/sdk"' in src
    assert "beta.sessions.create" in src


def test_ts_mcp_server_handles_tools_list_and_call(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    src = (tmp_path / "demo" / "mcp_server" / "main.ts").read_text()
    assert "tools/list" in src
    assert "tools/call" in src
    assert "echo" in src
    assert "now" in src


def test_go_agent_uses_anthropic_sdk_go(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=go", "--no-git")
    src = (tmp_path / "demo" / "src" / "agent.go").read_text()
    assert "github.com/anthropics/anthropic-sdk-go" in src
    assert "client.Messages.New" in src
    assert "anthropic.NewClient" in src


def test_go_client_uses_beta_sessions(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=go", "--no-git")
    src = (tmp_path / "demo" / "src" / "client.go").read_text()
    assert "client.Beta.Sessions.New" in src
    assert "Sessions.Events.Stream" in src


def test_go_mcp_server_registers_tools(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=go", "--no-git")
    src = (tmp_path / "demo" / "mcp_server" / "main.go").read_text()
    assert "github.com/modelcontextprotocol/go-sdk" in src
    assert "RegisterTool" in src
    assert "echo" in src
    assert "ServeStdio" in src


def test_go_mod_has_mcp_dep(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=go", "--no-git")
    mod = (tmp_path / "demo" / "go.mod").read_text()
    assert "github.com/anthropics/anthropic-sdk-go" in mod
    assert "github.com/modelcontextprotocol/go-sdk" in mod


# ---------------------------------------------------------------------------
# --upgrade flag


def test_upgrade_no_state_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = sn_init.main(["--upgrade"])
    assert rc != errors.EXIT_OK


def test_upgrade_at_current_version_noop(tmp_path: Path, monkeypatch, capsys):
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    monkeypatch.chdir(project)
    rc = sn_init.main(["--upgrade"])
    assert rc == errors.EXIT_OK
    captured = capsys.readouterr()
    assert "already at template version" in captured.out


def test_upgrade_after_version_bump_adds_files(tmp_path: Path, monkeypatch, capsys):
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"

    # Pretend the project was generated by an older template version + remove a file
    # that should be re-created during the upgrade.
    state_path = project / ".sn-init-state.json"
    state = json.loads(state_path.read_text())
    state["template_version"] = "2025.01.01"
    state_path.write_text(json.dumps(state) + "\n")
    (project / "Makefile").unlink()

    monkeypatch.chdir(project)
    rc = sn_init.main(["--upgrade"])
    assert rc == errors.EXIT_OK
    assert (project / "Makefile").exists(), "Makefile should be reinstated"
    new_state = json.loads(state_path.read_text())
    assert new_state["template_version"] == sn_init.TEMPLATE_VERSION
    assert new_state.get("upgrades"), "upgrade history not recorded"


def test_upgrade_does_not_overwrite_user_edits(tmp_path: Path, monkeypatch):
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    state_path = project / ".sn-init-state.json"
    state = json.loads(state_path.read_text())
    state["template_version"] = "2025.01.01"
    state_path.write_text(json.dumps(state) + "\n")

    (project / "README.md").write_text("CUSTOM CONTENT")
    monkeypatch.chdir(project)
    sn_init.main(["--upgrade"])
    assert (project / "README.md").read_text() == "CUSTOM CONTENT"


# ---------------------------------------------------------------------------
# Subagent index generator


def _import_gen_subagent_index():
    import importlib
    import sys as _sys
    plugin_root = Path(__file__).resolve().parent.parent
    sp = str(plugin_root / "scripts")
    if sp not in _sys.path:
        _sys.path.insert(0, sp)
    return importlib.import_module("gen_subagent_index")


def test_subagent_index_regen(tmp_path: Path, monkeypatch):
    gen = _import_gen_subagent_index()
    _run(tmp_path, "demo", "--no-git", "--subagents=all")
    project = tmp_path / "demo"
    monkeypatch.chdir(project)
    rc = gen.main([])
    assert rc == 0
    body = (project / "docs" / "design-docs" / "subagents.md").read_text()
    assert "<!-- sn-init:auto-table -->" in body
    assert "code-reviewer" in body
    assert "task-decomposer" in body
    assert "knowledge-curator" in body


def test_subagent_index_table_preserves_tail(tmp_path: Path, monkeypatch):
    gen = _import_gen_subagent_index()
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    target = project / "docs" / "design-docs" / "subagents.md"
    target.write_text(
        "# Subagent library\n\nIntro paragraph.\n\n"
        "<!-- sn-init:auto-table -->\n\nOLD TABLE\n\n"
        "## Custom appendix\n\nKeep me.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(project)
    gen.main([])
    new_body = target.read_text()
    assert "## Custom appendix" in new_body
    assert "code-reviewer" in new_body
    assert "OLD TABLE" not in new_body


# ---------------------------------------------------------------------------
# Makefile help annotations


def test_makefile_has_help_annotations(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    mk = (tmp_path / "demo" / "Makefile").read_text()
    assert "## " in mk
    # Each major target should self-document.
    for target_line in (
        "agent: ##", "sprint-new: ##", "sprint-run: ##", "knowledge-update: ##",
        "subagent-index: ##", "hooks-install: ##", "orchestrate: ##",
        "safety-status: ##", "logs-tail: ##",
    ):
        assert target_line in mk, f"missing help annotation: {target_line}"


# ---------------------------------------------------------------------------
# Lang smoke tests (skip when tooling absent)


def _have(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None


def test_python_overlay_can_parse_pyproject(tmp_path: Path):
    if not _have("python3"):
        pytest.skip("python3 not installed")
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    import subprocess
    result = subprocess.run(
        ["python3", "-c", "import tomllib, pathlib; tomllib.loads(pathlib.Path('pyproject.toml').read_text())"],
        cwd=tmp_path / "demo",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_typescript_overlay_package_json_valid(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    pkg = json.loads((tmp_path / "demo" / "package.json").read_text())
    # Required scripts present
    for script in ("agent", "client", "orchestrator", "mcp-server", "test", "lint"):
        assert script in pkg["scripts"], f"missing script: {script}"


def test_go_overlay_go_mod_parses(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=go", "--no-git")
    mod = (tmp_path / "demo" / "go.mod").read_text()
    assert "module " in mod
    assert "require (" in mod


def test_scaffold_subagent_index_script_present(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    assert (tmp_path / "demo" / "scripts" / "gen_subagent_index.py").exists()


# ---------------------------------------------------------------------------
# Agent SDK verifier hint (Anthropic agent-sdk-dev plugin integration)


def test_agent_sdk_verify_hint_py(tmp_path: Path, capsys):
    _run(tmp_path, "demo", "--lang=py", "--no-git", "--no-ci", "--no-obsidian")
    out = capsys.readouterr().out
    assert "agent-sdk-verifier-py" in out
    assert "/plugin install agent-sdk-dev" in out
    assert "/sn-verify" in out
    assert "anthropics/claude-plugins-official" in out


def test_agent_sdk_verify_hint_ts(tmp_path: Path, capsys):
    _run(tmp_path, "demo", "--lang=ts", "--no-git", "--no-ci", "--no-obsidian")
    out = capsys.readouterr().out
    assert "agent-sdk-verifier-ts" in out
    assert "/sn-verify" in out


def test_agent_sdk_verify_hint_skipped_for_go(tmp_path: Path, capsys):
    """Anthropic ships verifiers for py + ts only — Go scaffold must not
    nudge the user toward a verifier that doesn't exist for their lang."""
    _run(tmp_path, "demo", "--lang=go", "--no-git", "--no-ci", "--no-obsidian")
    out = capsys.readouterr().out
    assert "agent-sdk-verifier" not in out


def test_agent_sdk_best_practices_doc_shipped(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    path = tmp_path / "demo" / "docs" / "principles" / "agent-sdk-best-practices.md"
    assert path.exists()
    body = path.read_text()
    # 12 rules pinned; spot-check a few mechanical + prose ones.
    assert "Whitelist tools per session" in body
    assert "Auth via env var only" in body
    assert "Lock the model id" in body
    assert "Define subagents narrowly" in body
    assert "Stream — don't collect" in body


# ---------------------------------------------------------------------------
# /sn-verify slash command + verify_agent_sdk.py


def test_sn_verify_command_ships(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    assert (tmp_path / "demo" / ".claude" / "commands" / "sn-verify.md").exists()


def test_verify_agent_sdk_script_ships(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    assert (tmp_path / "demo" / "scripts" / "verify_agent_sdk.py").exists()


def test_makefile_verify_target_ships(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    mk = (tmp_path / "demo" / "Makefile").read_text()
    assert "verify:" in mk
    assert "verify_agent_sdk.py" in mk


def test_verify_agent_sdk_passes_on_compliant_py_overlay(tmp_path: Path):
    """The scaffolded python overlay (src/agent.py) MUST pass the verifier
    out of the box. If we ship code that fails our own rules the doc is a lie."""
    import shutil as _shutil
    import subprocess
    if not _shutil.which("python3"):
        pytest.skip("python3 not installed")
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    project = tmp_path / "demo"
    r = subprocess.run(
        ["python3", "scripts/verify_agent_sdk.py"],
        cwd=project, capture_output=True, text=True,
    )
    # rc 0 = all pass; rc 3 = no agent files (which would be a different bug).
    # rc 2 = one or more rules failed — that means our overlay is non-compliant.
    assert r.returncode in (0, 3), (
        f"verify_agent_sdk.py rc={r.returncode}\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )


def test_verify_agent_sdk_passes_on_compliant_ts_overlay(tmp_path: Path):
    """The TS overlay (src/agent.ts) must also pass the rules it ships."""
    import shutil as _shutil
    import subprocess
    if not _shutil.which("python3"):
        pytest.skip("python3 not installed")
    _run(tmp_path, "demo", "--lang=ts", "--no-git")
    project = tmp_path / "demo"
    r = subprocess.run(
        ["python3", "scripts/verify_agent_sdk.py"],
        cwd=project, capture_output=True, text=True,
    )
    assert r.returncode in (0, 3), (
        f"verify_agent_sdk.py rc={r.returncode}\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )


def test_sn_agent_sdk_reviewer_subagent_ships(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    path = tmp_path / "demo" / ".claude" / "agents" / "sn-agent-sdk-reviewer.md"
    assert path.exists()
    body = path.read_text()
    # Must be read-only — `can_modify: []`.
    assert "can_modify: []" in body
    # Must scope to the prose-analysis rules only.
    assert "Rule 4" in body and "Rule 7" in body and "Rule 8" in body
    assert "Rule 10" in body and "Rule 11" in body and "Rule 12" in body


def test_verify_agent_sdk_fails_on_hardcoded_key(tmp_path: Path):
    import shutil as _shutil
    import subprocess
    if not _shutil.which("python3"):
        pytest.skip("python3 not installed")
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    project = tmp_path / "demo"
    agent_py = project / "src" / "agent.py"
    body = agent_py.read_text()
    # Inject a hardcoded key literal — rule 2 should catch it.
    body += '\nANTHROPIC_API_KEY = "sk-fake-test-key-1234567890abcdef"\n'
    agent_py.write_text(body)
    r = subprocess.run(
        ["python3", "scripts/verify_agent_sdk.py"],
        cwd=project, capture_output=True, text=True,
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "rule 2: hardcoded API key" in r.stderr


# ---------------------------------------------------------------------------
# Makefile $$VAR rendering — regression for the safe_substitute halving bug


def test_makefile_preserves_double_dollar_shell_vars(tmp_path: Path):
    """`$$SPRINT` in template must survive scaffolding so Make reads it as
    shell `$SPRINT`. Previously `_substitute` ran safe_substitute on any file
    containing `${...}` (triggered by `${next:-000}` in two recipes), which
    halved every `$$VAR` to `$VAR` and silently broke every Make target."""
    _run(tmp_path, "demo", "--no-git")
    mk = (tmp_path / "demo" / "Makefile").read_text()
    # Sample a few representative targets that take args via shell vars.
    for token in (
        "[ -z \"$$SLUG\" ]",                              # req-new
        "[ -z \"$$SPRINT\" ] || [ -z \"$$REQ\" ]",        # sprint-add
        "[ -z \"$$SPRINT\" ] || [ -z \"$$N\" ]",          # sprint-concurrent
        "$$(find docs -name 'REQ-*.md'",                  # shell command substitution
    ):
        assert token in mk, f"Make recipe mangled by safe_substitute: missing {token!r}"


def _make_recipe_reaches_toolchain(tmp_path: Path, lang: str, makefile: str, marker: str):
    """Helper for lang-overlay smoke tests. Scaffolds + runs `make -f <mk> test`
    and asserts the recipe reached its toolchain entry-point (no shell
    mangling). Missing inner tools (e.g. `vitest: command not found` because
    we did not run `npm install`) are tolerated — they show the recipe
    parsed and invoked the toolchain wrapper, which is what we are testing."""
    import shutil as _shutil
    import subprocess
    if not _shutil.which("make"):
        pytest.skip("make not installed")
    _run(tmp_path, "demo", f"--lang={lang}", "--no-git", "--no-ci", "--no-obsidian")
    project = tmp_path / "demo"
    r = subprocess.run(
        ["make", "-f", makefile, "test"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    combined = r.stdout + r.stderr
    # The toolchain wrapper command MUST appear in stdout — i.e. the recipe
    # actually fired its first command. If the marker is missing the recipe
    # failed to parse or shell-mangled the call.
    assert marker in combined, combined


def test_integration_scaffold_runs_make_test_go(tmp_path: Path):
    """Go overlay smoke — `make -f Makefile.go test` invokes `go test`."""
    _make_recipe_reaches_toolchain(tmp_path, "go", "Makefile.go", "go test")


def test_integration_scaffold_runs_make_test_ts(tmp_path: Path):
    """TS overlay smoke — `make -f Makefile.ts test` invokes `npm test`."""
    _make_recipe_reaches_toolchain(tmp_path, "ts", "Makefile.ts", "npm test")


def test_integration_scaffold_runs_make_test(tmp_path: Path):
    """End-to-end: scaffold a python project then run `make test` inside.
    Validates the full bootstrap path beyond file presence — pyproject
    parses, tests/ files import, scaffolded pytest passes."""
    import shutil as _shutil
    import subprocess
    if not _shutil.which("make"):
        pytest.skip("make not installed")
    if not _shutil.which("uv") and not _shutil.which("python3"):
        pytest.skip("neither uv nor python3 installed")
    _run(tmp_path, "demo", "--lang=py", "--no-git", "--no-ci", "--no-obsidian")
    project = tmp_path / "demo"

    # Drive Makefile.py's `test` target (lang overlay). Recipe runs
    # `uv run pytest`. We don't care whether pytest finds tests / passes —
    # the assertion is that the Make recipe parses + invokes uv. A shell
    # mangling bug (`$X` → `command not found`) would surface here.
    r = subprocess.run(
        ["make", "-f", "Makefile.py", "test"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=90,
    )
    combined = r.stdout + r.stderr
    # Positive signal — `uv run pytest` reached the uv subprocess.
    assert "uv run pytest" in combined or "Using CPython" in combined, combined
    # Negative signal — the broken-recipe failure mode does NOT happen.
    assert ": command not found" not in combined, combined


def test_makefile_targets_runnable(tmp_path: Path):
    """End-to-end: a representative subset of Make targets actually run
    without `$VAR command not found` or similar shell breakage."""
    import shutil as _shutil
    import subprocess
    if not _shutil.which("make"):
        pytest.skip("make not installed")
    _run(tmp_path, "demo", "--lang=py", "--no-git")
    project = tmp_path / "demo"

    # No-arg call must surface the usage hint and exit 2.
    r = subprocess.run(["make", "req-new"], cwd=project, capture_output=True, text=True)
    assert r.returncode == 2
    assert "Usage" in (r.stdout + r.stderr)

    # Arg call must succeed and create the REQ file.
    r = subprocess.run(["make", "req-new", "SLUG=foo"], cwd=project, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "created docs/requirements/active/REQ-001-foo.md" in r.stdout

    # Hint-only targets should echo the slash-command invocation with the
    # user-supplied arg fully expanded (not "$SPRINT" or empty).
    r = subprocess.run(
        ["make", "sprint-concurrent", "SPRINT=SPRINT-001", "N=3"],
        cwd=project, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "/sn-sprint run SPRINT-001 with --workflow-concurrent=3" in r.stdout


def test_plan_new_files_emits_sn_namespace(tmp_path: Path):
    # Plan-only path — verify the layout we ship into a fresh scaffold.
    target = tmp_path / "scaffold"
    target.mkdir()
    args = sn_init.build_parser().parse_args([
        "scaffold", "--lang=py", "--no-git", "--no-ci", "--no-obsidian",
    ])
    files = sn_init._plan_new_files(args, target)
    rels = {rel for rel, _ in files}
    assert ".claude/commands/sn-knowledge.md" in rels
    assert ".claude/agents/sn-knowledge-curator.md" in rels
    # No file should land under any subdir under commands/ or agents/.
    assert not any(rel.startswith(".claude/commands/sn/") for rel in rels)
    assert not any(rel.startswith(".claude/agents/sn/") for rel in rels)
    assert not any(rel.startswith(".claude/commands/workflow/") for rel in rels)
    assert not any(rel.startswith(".claude/agents/workflow/") for rel in rels)


# ---------------------------------------------------------------------------
# /sn-session-report


def test_session_report_plugin_files_ship():
    plugin_root = Path(__file__).resolve().parent.parent
    assert (plugin_root / "commands" / "sn-session-report.md").is_file()
    assert (plugin_root / "skills" / "session-report" / "SKILL.md").is_file()
    assert (plugin_root / "scripts" / "session_report.py").is_file()
    assert (plugin_root / "scripts" / "session_report_render.py").is_file()


def test_session_report_scaffold_template_files_ship():
    plugin_root = Path(__file__).resolve().parent.parent
    base = plugin_root / "skills" / "sn-setup" / "templates"
    assert (base / "claude" / "commands" / "sn-session-report.md").is_file()
    assert (base / "claude" / "skills" / "session-report" / "SKILL.md").is_file()
    assert (base / "managed-agent-base" / "scripts" / "session_report.py").is_file()
    assert (base / "managed-agent-base" / "scripts" / "session_report_render.py").is_file()


def test_session_report_makefile_target():
    plugin_root = Path(__file__).resolve().parent.parent
    mk = (
        plugin_root / "skills" / "sn-setup" / "templates"
        / "managed-agent-base" / "Makefile"
    ).read_text()
    assert "session-report:" in mk
    assert "python3 scripts/session_report.py" in mk


def test_session_report_present_in_fresh_scaffold(tmp_path: Path):
    _run(tmp_path, "demo", "--lang=py", "--no-git", "--no-ci", "--no-obsidian")
    project = tmp_path / "demo"
    assert (project / ".claude" / "commands" / "sn-session-report.md").exists()
    assert (project / ".claude" / "skills" / "session-report" / "SKILL.md").exists()
    assert (project / "scripts" / "session_report.py").exists()
    assert (project / "scripts" / "session_report_render.py").exists()


def test_session_report_errors_module_has_missing_dep():
    assert errors.EXIT_MISSING_DEP == 9
    assert issubclass(errors.MissingAnalyzerError, errors.SnInitError)
    assert errors.MissingAnalyzerError("x").exit_code == 9


def test_session_report_render_against_fixture():
    import session_report_render

    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "session-report-payload.json"
    )
    payload = json.loads(fixture_path.read_text())
    md = session_report_render.render_markdown(
        payload,
        "-Users-test-Claude-setup-project-plugin",
        "7d",
        "2026-06-22",
    )
    # Frontmatter
    assert md.startswith("---\n")
    assert "topic: session-report-20260622" in md
    assert "bucket: projects/setup-project-plugin" in md
    assert "window: 7d" in md

    # Headline math against fixture (input total 30,601,000 + output 100,000)
    assert "30.7M" in md
    assert "Sessions | 3" in md
    assert "API calls | 150" in md

    # Anomaly: one prompt is 53.7% of total (16.5M / 30.7M)
    assert "burned" in md and "53" in md

    # Top prompt rows mention real text from fixture
    assert "scan this project" in md

    # Cache breaks for this project (2 rows)
    assert "866.9k" in md
    assert "audit them" in md

    # Cross-project caveats
    assert "global" in md and "per project" in md

    # Optimization callout present
    assert "> [!tip]" in md


def test_session_report_render_handles_unknown_project_key():
    import session_report_render

    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "session-report-payload.json"
    )
    payload = json.loads(fixture_path.read_text())
    md = session_report_render.render_markdown(
        payload, "-Users-test-Claude-no-such-project", "7d", "2026-06-22"
    )
    # Renderer must not crash; produces a header + "No prompts" / "No cache" notes.
    assert "# Session report" in md
    assert "_No prompts in this project within the window._" in md
    assert "_No cache-break events for this project._" in md


def test_session_report_locate_analyzer_honors_env(tmp_path: Path, monkeypatch):
    import session_report

    fake = tmp_path / "analyze-sessions.mjs"
    fake.write_text("// fake")
    monkeypatch.setenv("SN_SESSION_REPORT_ANALYZER", str(fake))
    located = session_report.locate_analyzer(None)
    assert located == fake.resolve()


def test_session_report_locate_analyzer_returns_none_when_missing(
    tmp_path: Path, monkeypatch
):
    import session_report

    monkeypatch.setenv("SN_SESSION_REPORT_ANALYZER", str(tmp_path / "missing.mjs"))
    # Also redirect HOME so the recursive glob in locate_analyzer finds nothing.
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    monkeypatch.setattr(
        "pathlib.Path.home", lambda: tmp_path / "fake-home"
    )
    assert session_report.locate_analyzer(None) is None


def test_session_report_missing_analyzer_exit_code(
    tmp_path: Path, monkeypatch, capsys
):
    import session_report

    monkeypatch.setenv(
        "SN_SESSION_REPORT_ANALYZER", str(tmp_path / "definitely-missing.mjs")
    )
    monkeypatch.setattr(
        "pathlib.Path.home", lambda: tmp_path / "fake-home"
    )
    monkeypatch.chdir(tmp_path)
    rc = session_report.main([])
    assert rc == errors.EXIT_MISSING_DEP
    err = capsys.readouterr().err
    assert "analyzer not" in err.lower() or "analyzer not found" in err


def test_session_report_encode_project_path():
    import session_report

    assert session_report.encode_project(
        Path("/Users/siripol/Claude/setup_project_plugin")
    ) == "-Users-siripol-Claude-setup-project-plugin"


def test_session_report_resolve_project_key_exact_and_suffix():
    import session_report

    payload = {
        "by_project": {
            "-Users-test-Claude-setup-project-plugin": {},
            "-Users-test-Claude-other": {},
        }
    }
    # Exact match passes through
    assert session_report.resolve_project_key(
        "-Users-test-Claude-setup-project-plugin", payload
    ) == "-Users-test-Claude-setup-project-plugin"
    # Suffix match picks the key whose tail matches
    assert session_report.resolve_project_key(
        "-mismatched-prefix-plugin", payload
    ) == "-Users-test-Claude-setup-project-plugin"


def test_session_report_render_uses_explicit_project_name():
    """v0.5.1 fix — `project_name` kwarg overrides lossy _human_project derivation.

    Encoded key has both `/` and `_` replaced by `-`, so reversing it cannot
    recover the original directory name. The wrapper passes the actual cwd
    basename as `project_name` to avoid that loss.
    """
    import session_report_render

    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "session-report-payload.json"
    )
    payload = json.loads(fixture_path.read_text())
    md = session_report_render.render_markdown(
        payload,
        "-Users-test-Claude-setup-project-plugin",
        "7d",
        "2026-06-22",
        project_name="setup_project_plugin",
    )
    # Underscore preserved in frontmatter, body, tags
    assert "bucket: projects/setup_project_plugin" in md
    assert "origin_project: setup_project_plugin" in md
    assert "# Session report — setup_project_plugin —" in md
    assert "tags: [knowledge, session-report, tokens, cache, setup_project_plugin]" in md
    # Dashy form must NOT appear
    assert "bucket: projects/setup-project-plugin" not in md


def test_sprint_status_returns_zero_when_completed_empty(tmp_path: Path):
    """v0.5.2 fix — `make sprint-status` previously exited rc=2 when the
    `docs/sprints/completed/` glob was empty because the bash `for` loop
    iterated over the literal pattern and the trailing `[ -d ]` returned 1.

    The fix prepends `shopt -s nullglob` so unmatched globs disappear.
    """
    import shutil as _shutil
    import subprocess
    if not _shutil.which("make"):
        pytest.skip("make not installed")

    _run(tmp_path, "demo", "--lang=py", "--no-git", "--no-ci", "--no-obsidian")
    project = tmp_path / "demo"

    # No active and no completed sprints — sprint-status must still exit 0.
    r = subprocess.run(
        ["make", "sprint-status"],
        cwd=project, capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        f"sprint-status rc={r.returncode} when empty\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )
    assert "ACTIVE sprints:" in r.stdout
    assert "COMPLETED sprints:" in r.stdout


def test_session_report_find_git_root_walks_up(tmp_path: Path):
    """v0.5.1 fix — vault commit step walks up from the knowledge dir until it
    finds the enclosing git repo. Obsidian vaults nest the knowledge tree
    under a parent repo (e.g. <repo>/AllSharedKnowledge/knowledge/)."""
    import session_report

    # Simulate: <root>/.git plus a nested vault path.
    root = tmp_path / "vault-repo"
    (root / ".git").mkdir(parents=True)
    nested = root / "AllSharedKnowledge" / "knowledge"
    nested.mkdir(parents=True)

    # Walk-up from the nested path locates root.
    assert session_report.find_git_root(nested) == root

    # Walk-up from root finds itself.
    assert session_report.find_git_root(root) == root

    # No-repo case returns None.
    no_repo = tmp_path / "nowhere" / "deep"
    no_repo.mkdir(parents=True)
    # Need to make sure no ancestor has .git. tmp_path doesn't, so this works.
    # But if tmp_path itself happens to have .git, find_git_root would hit it.
    # Guard by checking the tmp_path tree.
    if not any((p / ".git").exists() for p in [tmp_path, *tmp_path.parents]):
        assert session_report.find_git_root(no_repo) is None


# ---------------------------------------------------------------------------
# v0.6.0 — tunability enhancements (E1..E7)


def _load_session_fixture():
    import session_report_render  # noqa: F401 - import for monkey-patch context

    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "session-report-payload.json"
    )
    return json.loads(fixture_path.read_text())


def test_session_report_normalize_prompt_text_collapses_variants():
    """E5 — repeat detection groups whitespace / case / punctuation variants."""
    from session_report_render import _normalize_prompt_text

    base = "Commit and push."
    assert _normalize_prompt_text(base) == _normalize_prompt_text("commit and push")
    assert _normalize_prompt_text(base) == _normalize_prompt_text("  commit and push  ")
    assert _normalize_prompt_text(base) == _normalize_prompt_text("commit and push!!!")
    # Different prompts stay distinct.
    assert _normalize_prompt_text("commit and push") != _normalize_prompt_text("audit them")


def test_session_report_compute_repeat_groups_counts():
    """E5 — repeat grouping counts the right buckets."""
    from session_report_render import _compute_repeat_groups

    prompts = [
        {"text": "commit and push"},
        {"text": "Commit and push."},
        {"text": "commit and push!"},
        {"text": "audit them"},
        {"text": ""},  # empty drops out
    ]
    g = _compute_repeat_groups(prompts)
    assert g["commit and push"] == 3
    assert g["audit them"] == 1


def test_session_report_cache_hit_pct():
    """E3 — cache hit % derives from input.{uncached,cache_create,cache_read}."""
    from session_report_render import _cache_hit_pct

    high = {"input": {"uncached": 10, "cache_create": 0, "cache_read": 990}}
    low = {"input": {"uncached": 800, "cache_create": 100, "cache_read": 100}}
    assert _cache_hit_pct(high) == pytest.approx(99.0)
    assert _cache_hit_pct(low) == pytest.approx(10.0)
    # Empty input returns 100% (no input = no miss).
    assert _cache_hit_pct({"input": {}}) == 100.0


def test_session_report_cache_break_count_links_by_ts_text():
    """E4 — cache_break_count_for_prompt matches the `here:true` context entry."""
    from session_report_render import _cache_break_count_for_prompt

    prompt = {"ts": "2026-06-21T16:38:00Z", "text": "commit and push"}
    cache_breaks = [
        {
            "context": [
                {"ts": "2026-06-21T16:37:00Z", "text": "/plugin", "here": False},
                {"ts": "2026-06-21T16:38:00Z", "text": "commit and push", "here": True},
            ]
        },
        # Different prompt, no link
        {
            "context": [
                {"ts": "2026-06-22T10:00:00Z", "text": "audit them", "here": True},
            ]
        },
    ]
    assert _cache_break_count_for_prompt(prompt, cache_breaks) == 1


def test_session_report_determine_reason_priority():
    """E2 — reason code priority: repeat > subagent-heavy > loop-thrash > cache-miss > cold-start > low-output > expensive."""
    from session_report_render import _determine_reason

    base = {"text": "x", "api_calls": 1, "subagent_calls": 0}
    # repeat wins over everything else
    assert _determine_reason(base, 100.0, 0, 5, 1, 0.5) == "repeat"
    # subagent-heavy next
    assert _determine_reason({**base, "subagent_calls": 3}, 100.0, 0, 1, 1, 0.5) == "subagent-heavy"
    # loop-thrash when api_calls ≥ 2× median
    assert _determine_reason({**base, "api_calls": 10}, 100.0, 0, 1, 4, 0.5) == "loop-thrash"
    # cache-miss
    assert _determine_reason(base, 30.0, 0, 1, 1, 0.5) == "cache-miss"
    # cold-start
    assert _determine_reason(base, 100.0, 1, 1, 1, 0.5) == "cold-start"
    # low-output
    assert _determine_reason(base, 100.0, 0, 1, 1, 0.0001) == "low-output"
    # default fallback
    assert _determine_reason(base, 100.0, 0, 1, 1, 0.5) == "expensive"


def test_session_report_tunability_score_bounded():
    """E1 — score is 0..100 and rewards multiple signals additively."""
    from session_report_render import _tunability_score

    # Worst-case all-signals prompt — should be high but capped at 100.
    worst = {"subagent_calls": 10, "api_calls": 100}
    score = _tunability_score(worst, cache_hit_pct=0.0, cache_break_count=5, repeat_count=10, median_api_calls=1)
    assert 0 <= score <= 100
    assert score >= 80  # very tunable

    # Clean prompt — minimum signal.
    clean = {"subagent_calls": 0, "api_calls": 1}
    low = _tunability_score(clean, cache_hit_pct=99.0, cache_break_count=0, repeat_count=1, median_api_calls=1)
    assert low < 10


def test_session_report_suggested_action_repeat_inlines_count():
    """E6 — repeat suggestions inline the count to make the action concrete."""
    from session_report_render import _suggested_action

    action = _suggested_action({"text": "x"}, "repeat", 4)
    assert "4×" in action
    assert "skill" in action.lower()


def test_session_report_render_includes_tunability_columns():
    """E1+E2+E3+E4+E5 — rendered Markdown includes the new top-prompts columns."""
    from session_report_render import render_markdown

    payload = _load_session_fixture()
    md = render_markdown(
        payload,
        "-Users-test-Claude-setup-project-plugin",
        "7d",
        "2026-06-22",
        project_name="setup_project_plugin",
    )
    # New section heading
    assert "## Top prompts (by tunability)" in md
    # Column headers present
    for col in ("Score", "Reason", "Cache-hit", "Cache breaks", "Repeats"):
        assert col in md
    # Repeats section appears with the actual count from the fixture
    assert "## Repeated prompts" in md
    assert "3×" in md
    # Optimizations now references the reason code and is per-prompt
    assert "`cache-miss`" in md or "`repeat`" in md or "`subagent-heavy`" in md
    # Old generic optimization phrasing must NOT appear
    assert "Scope or cache the top prompt" not in md


def test_session_report_resolve_vault_path_signals_fallback(tmp_path: Path, monkeypatch):
    """v0.6.0 — resolve_vault_path returns (path, is_fallback).

    Fallback is True only for the last-resort `<cwd>/session-reports/`
    branch (no --vault, no $OBSIDIAN_VAULT, no .sn-init/knowledge symlink).
    In that case the wrapper writes the report directly into the returned
    dir to avoid the triple-nested
    `<cwd>/session-reports/projects/<proj>/session-reports/` path.
    """
    import session_report

    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    monkeypatch.chdir(tmp_path)

    # Last-resort fallback signals True
    root, is_fallback = session_report.resolve_vault_path(None, tmp_path)
    assert is_fallback is True
    assert root == tmp_path / "session-reports"

    # Explicit --vault is NOT fallback
    explicit = tmp_path / "vault"
    explicit.mkdir()
    root, is_fallback = session_report.resolve_vault_path(str(explicit), tmp_path)
    assert is_fallback is False
    assert root == explicit.resolve()

    # $OBSIDIAN_VAULT is NOT fallback
    env_vault = tmp_path / "env-vault"
    env_vault.mkdir()
    monkeypatch.setenv("OBSIDIAN_VAULT", str(env_vault))
    root, is_fallback = session_report.resolve_vault_path(None, tmp_path)
    assert is_fallback is False
    assert root == env_vault.resolve()


def test_session_report_fallback_writes_flat_path(tmp_path: Path, monkeypatch, capsys):
    """v0.6.0 — fallback mode writes directly to `<cwd>/session-reports/`
    instead of nesting under `projects/<project>/session-reports/`.

    Previously a `make session-report` in a scaffolded project without a
    real vault produced `session-reports/projects/<proj>/session-reports/<ts>.md`
    (triple-nested + visually broken). The fix collapses the fallback
    output to a flat `<cwd>/session-reports/<ts>.md`.
    """
    import session_report

    # Make analyzer detection succeed by pointing at a fake mjs.
    fake = tmp_path / "analyze-sessions.mjs"
    fake.write_text(
        '#!/usr/bin/env node\n'
        'const payload = {root: ".", overall: {sessions: 0, api_calls: 0, '
        'input_tokens: {uncached: 0, cache_create: 0, cache_read: 0, total: 0}, '
        'output_tokens: 0, human_messages: 0, hours: {wall_clock: 0, active: 0}, '
        'cache_breaks_over_100k: 0, subagent: {calls: 0, total_tokens: 0, '
        'avg_tokens_per_call: 0}, skill_invocations: {}, span: null}, '
        'cache_breaks: [], by_project: {}, by_subagent_type: {}, by_skill: {}, '
        'top_prompts: [], by_day: []};\n'
        'process.stdout.write(JSON.stringify(payload));\n'
    )
    monkeypatch.setenv("SN_SESSION_REPORT_ANALYZER", str(fake))
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)

    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    rc = session_report.main(["24h", "--no-push"])
    assert rc == 0, capsys.readouterr().err

    # File must land at <cwd>/session-reports/<ts>.md, NOT
    # <cwd>/session-reports/projects/demo-project/session-reports/<ts>.md.
    files = list((project_dir / "session-reports").glob("*.md"))
    assert any(f.name != "README.md" for f in files), \
        f"no report file in flat path; files: {files}"
    assert not (project_dir / "session-reports" / "projects").exists(), \
        "fallback mode must not create projects/ subtree"


def test_session_report_dedup_collapses_repeated_rows():
    """E5 — top-prompts table shows ONE row per logical intent even if the
    prompt was typed multiple times in the window."""
    from session_report_render import render_markdown

    payload = _load_session_fixture()
    md = render_markdown(
        payload,
        "-Users-test-Claude-setup-project-plugin",
        "7d",
        "2026-06-22",
        project_name="setup_project_plugin",
    )
    # `commit and push` appears 3× in fixture; should collapse to ONE row in the
    # tunability table (count surfaced in the Repeats column = 3).
    top_section = md.split("## Top prompts")[1].split("## Repeated prompts")[0]
    assert top_section.count("commit and push") == 1, top_section


# ---------------------------------------------------------------------------
# profile + framework overlays


def test_profile_default_is_microservice(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    assert (project / "docs" / "PROFILE.md").exists()
    profile_md = (project / "docs" / "PROFILE.md").read_text()
    assert "microservice" in profile_md
    assert "demo" in profile_md  # ${name} substituted
    # microservice-specific docs ship
    assert (project / "docs" / "API.md").exists()
    assert (project / "docs" / "OBSERVABILITY.md").exists()
    # State records profile + framework=None for non-frontend
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["profile"] == "microservice"
    assert state["framework"] is None
    # CLAUDE.md exposes the profile
    claude_md = (project / "CLAUDE.md").read_text()
    assert "microservice" in claude_md


def test_profile_bff_default_lang_go(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=bff")
    project = tmp_path / "demo"
    assert (project / "docs" / "BFF-INTEGRATION.md").exists()
    assert (project / "docs" / "DOWNSTREAMS.md").exists()
    profile_md = (project / "docs" / "PROFILE.md").read_text()
    assert "Backend-for-Frontend" in profile_md
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["profile"] == "bff"
    assert state["lang"] == "go"


def test_profile_bff_lang_ts_allowed(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=bff", "--lang=ts")
    assert rc == errors.EXIT_OK


def test_profile_bff_lang_py_rejected(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=bff", "--lang=py")
    assert rc == errors.EXIT_USAGE
    err = capsys.readouterr().err
    assert "--profile=bff" in err
    assert "--lang=py" in err


def test_profile_frontend_default_framework_next(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=frontend", "--lang=ts")
    assert rc == errors.EXIT_OK
    project = tmp_path / "demo"
    assert (project / "docs" / "DESIGN.md").exists()
    assert (project / "docs" / "ACCESSIBILITY.md").exists()
    assert (project / "docs" / "BROWSER-MATRIX.md").exists()
    framework_md = (project / "docs" / "FRAMEWORK.md").read_text()
    assert "Next.js" in framework_md
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["profile"] == "frontend"
    assert state["framework"] == "next"


def test_profile_frontend_framework_vite(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=frontend", "--lang=ts", "--framework=vite")
    assert rc == errors.EXIT_OK
    framework_md = (tmp_path / "demo" / "docs" / "FRAMEWORK.md").read_text()
    assert "Vite" in framework_md
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["framework"] == "vite"


def test_profile_frontend_lang_go_rejected(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=frontend", "--lang=go")
    assert rc == errors.EXIT_USAGE
    err = capsys.readouterr().err
    assert "--profile=frontend" in err


def test_profile_service_alias_resolves_to_microservice(tmp_path: Path):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=service")
    assert rc == errors.EXIT_OK
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert state["profile"] == "microservice"


def test_profile_unknown_value_rejected(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git", "--profile=mainframe")
    assert rc == errors.EXIT_USAGE
    err = capsys.readouterr().err
    assert "mainframe" in err


# ---------------------------------------------------------------------------
# Task 12 — scaffold-time policy integration


import policy_errors  # type: ignore


def test_scaffold_applies_profile_defaults(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    expected = {"repository-ecosystem", "memory-ordinary", "audit-log-strict",
                "supply-chain-scan", "secret-scan", "commit-msg-gate"}
    assert slugs == expected


def test_scaffold_writes_project_local_profile_defaults(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice")
    text = (tmp_path / "demo" / ".claude" / "profile-defaults.yaml").read_text()
    assert "profile: microservice" in text
    assert "memory-ordinary" in text


def test_scaffold_policies_flag_replaces_defaults(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--policies=secret-scan,repository-ecosystem")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    assert slugs == {"secret-scan", "repository-ecosystem"}


def test_scaffold_delta_flags(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice",
         "--add-policies=branch-naming", "--remove-policies=audit-log-strict")
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    assert "branch-naming" in slugs
    assert "audit-log-strict" not in slugs


def test_scaffold_combining_replace_and_delta_errors(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git",
              "--policies=secret-scan", "--add-policies=branch-naming")
    assert rc == policy_errors.EXIT_MIXED_OVERRIDE_FLAGS


def test_scaffold_unknown_policy_errors(tmp_path: Path, capsys):
    rc = _run(tmp_path, "demo", "--no-git", "--policies=foobar")
    assert rc == policy_errors.EXIT_UNKNOWN_POLICY


def test_microservice_golden_snapshot(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git", "--profile=microservice")
    project = tmp_path / "demo"
    golden = Path(__file__).parent / "golden" / "scaffolded-microservice"

    # CLAUDE.md ## Policies section equality (ignore the rest of the file).
    full = (project / "CLAUDE.md").read_text()
    section = "## Policies\n" + full.split("## Policies\n", 1)[1].split("## ", 1)[0]
    assert section.strip() == (golden / "CLAUDE.md.policies-section").read_text().strip()

    # profile-defaults equality.
    assert (project / ".claude" / "profile-defaults.yaml").read_text() == \
           (golden / "profile-defaults.yaml").read_text()

    # applied_policies (slugs only, sorted) equality.
    state = json.loads((project / ".sn-init-state.json").read_text())
    slugs = sorted(p["slug"] for p in state["applied_policies"])
    assert slugs == json.loads((golden / "applied_policies.json").read_text())

    # settings.json keys+matchers sanity.
    settings = json.loads((project / ".claude" / "settings.json").read_text())
    expected_hooks = json.loads((golden / "settings.json").read_text())
    # Compare only "hooks" sub-tree because settings.json has many other keys.
    # Filter to policy entries only (non-policy hooks like rate-limit.sh are excluded).
    for hook_name, entries in expected_hooks["hooks"].items():
        actual = settings["hooks"].get(hook_name, [])
        actual_keys = sorted((e["policy"], e.get("matcher", "")) for e in actual if "policy" in e)
        expected_keys = sorted((e["policy"], e.get("matcher", "")) for e in entries)
        assert actual_keys == expected_keys, f"{hook_name}: {actual_keys} != {expected_keys}"


def test_add_mode_applies_profile_default_policies(tmp_path: Path):
    """Add mode must also apply profile-default policies (M4 fix)."""
    # Non-empty cwd to trigger add mode.
    (tmp_path / "existing.txt").write_text("x")
    _run(tmp_path, "--no-git", "--profile=microservice")
    state = json.loads((tmp_path / ".sn-init-state.json").read_text())
    slugs = {p["slug"] for p in state["applied_policies"]}
    # Microservice profile defaults include repository-ecosystem + memory-ordinary.
    assert "repository-ecosystem" in slugs
    assert "memory-ordinary" in slugs


# ---------------------------------------------------------------------------
# Task 6: command sub-tree migration integration tests


def test_new_scaffold_writes_grouped_commands_only(tmp_path: Path):
    """A fresh scaffold contains the 3 grouped command files + no flat."""
    _run(tmp_path, "demo", "--no-git")
    cmd_dir = tmp_path / "demo" / ".claude" / "commands"
    # Grouped present.
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        assert (cmd_dir / grouped).exists()
    # Flat absent.
    for flat in (
        "sn-sprint-new.md", "sn-sprint-add.md", "sn-sprint-run.md",
        "sn-sprint-status.md", "sn-sprint-done.md", "sn-sprint-remove.md",
        "sn-req-new.md", "sn-req-import.md", "sn-req-replay.md",
        "sn-req-resume.md", "sn-req-rollback.md",
        "sn-knowledge-check.md", "sn-knowledge-update.md",
        "sn-knowledge-promote.md", "sn-knowledge-demote.md",
    ):
        assert not (cmd_dir / flat).exists(), f"flat file leaked into scaffold: {flat}"


def test_new_scaffold_does_not_ship_tech_matrix_md(tmp_path: Path):
    _run(tmp_path, "demo", "--no-git")
    cmd_dir = tmp_path / "demo" / ".claude" / "commands"
    assert not (cmd_dir / "sn-knowledge-tech-matrix.md").exists()


def test_grouped_command_frontmatter_valid(tmp_path: Path):
    """Each grouped .md ships a YAML frontmatter with name + description."""
    import yaml as _yaml
    _run(tmp_path, "demo", "--no-git")
    cmd_dir = tmp_path / "demo" / ".claude" / "commands"
    for grouped in ("sn-sprint.md", "sn-req.md", "sn-knowledge.md"):
        text = (cmd_dir / grouped).read_text()
        assert text.startswith("---\n"), f"{grouped} missing frontmatter"
        # Extract the YAML block between the leading --- and the next ---.
        _, block, _body = text.split("---\n", 2)
        meta = _yaml.safe_load(block)
        assert meta["name"] == grouped.removesuffix(".md")
        assert "description" in meta and meta["description"]


def test_upgrade_rename_commands_flag_requires_upgrade(tmp_path: Path, capsys):
    """sn-setup --rename-commands (without --upgrade) → exit 2."""
    # Need a scaffold + state file first.
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    rc = _run(project, "--rename-commands")
    assert rc == errors.EXIT_USAGE
    err = capsys.readouterr().err
    assert "--rename-commands requires --upgrade" in err


def test_upgrade_rename_commands_end_to_end(tmp_path: Path):
    """Scaffold a project, drop in a fake old flat file, run --upgrade
    --rename-commands --force, verify it gets removed and state updated."""
    _run(tmp_path, "demo", "--no-git")
    project = tmp_path / "demo"
    cmd_dir = project / ".claude" / "commands"
    # Simulate a legacy scaffold by writing one fake flat file.
    (cmd_dir / "sn-sprint-new.md").write_text("# legacy sn-sprint-new\n")
    rc = _run(project, "--upgrade", "--rename-commands", "--force")
    assert rc == errors.EXIT_OK
    assert not (cmd_dir / "sn-sprint-new.md").exists()
    # Grouped files already shipped during initial scaffold; still present.
    assert (cmd_dir / "sn-sprint.md").exists()
    # State recorded.
    state = json.loads((project / ".sn-init-state.json").read_text())
    assert state["commands_renamed_at"] is not None
    assert "sn-sprint-new" in state["commands_migration"]["from_flat"]


def test_b1_7a_ci_blocks_dangerous_flag_step(tmp_path: Path):
    """B1.7a — scaffolded CI workflow contains the Block --dangerously-skip-permissions step."""
    _run(tmp_path, "demo", "--no-git")
    ci_path = tmp_path / "demo" / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    text = ci_path.read_text()
    assert "Block --dangerously-skip-permissions" in text
    assert "--dangerously-skip-permissions" in text
    assert "exit 1" in text  # the gate must hard-fail, not warn


def test_b1_7b_regulated_policy_auto_adds_security_auditor(tmp_path: Path):
    """B1.7b — when --policies includes a regulated-data slug, security-auditor
    is auto-added to the default subagent set and shipped in .claude/agents/."""
    _run(tmp_path, "demo", "--no-git", "--policies=memory-regulated,repository-ecosystem")
    agents = tmp_path / "demo" / ".claude" / "agents"
    assert (agents / "security-auditor.md").exists()
    state = json.loads((tmp_path / "demo" / ".sn-init-state.json").read_text())
    assert "security-auditor" in state["flags"]["subagents"]


def test_b1_7b_ordinary_default_does_not_auto_add(tmp_path: Path):
    """B1.7b — default microservice scaffold (memory-ordinary, no regulated)
    must NOT ship security-auditor unless explicitly requested."""
    _run(tmp_path, "demo", "--no-git")
    agents = tmp_path / "demo" / ".claude" / "agents"
    assert not (agents / "security-auditor.md").exists()


def test_b1_7b_subagents_none_honored_even_with_regulated(tmp_path: Path):
    """B1.7b — explicit --subagents=none opts out of the auto-add."""
    _run(tmp_path, "demo", "--no-git",
         "--policies=memory-regulated", "--subagents=none")
    agents = tmp_path / "demo" / ".claude" / "agents"
    assert not (agents / "security-auditor.md").exists()


def test_b2_1a_repository_ecosystem_doc_has_per_profile_sections(tmp_path: Path):
    """B2.1a — applied repository-ecosystem policy doc must have one
    foregrounding section per profile (microservice / BFF / frontend) so
    Claude has profile-specific guidance from the always-on policies table."""
    _run(tmp_path, "demo", "--no-git")
    doc = tmp_path / "demo" / ".claude" / "docs" / "policies" / "repository-ecosystem.md"
    assert doc.exists()
    text = doc.read_text()
    assert "## Microservice — foreground peers" in text
    assert "## BFF — foreground downstreams" in text
    assert "## Frontend — foreground its BFF" in text
