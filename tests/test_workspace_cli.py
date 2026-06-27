"""Tests for scripts/workspace_cli.py — workspace CLI dispatcher."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import errors  # type: ignore
import sn_init  # type: ignore
import workspace_cli  # type: ignore


def _run(cwd: Path, *argv: str) -> int:
    old = Path.cwd()
    try:
        os.chdir(cwd)
        return workspace_cli.main(list(argv))
    finally:
        os.chdir(old)


def _init_env(env: dict | None = None) -> dict:
    base = {**os.environ}
    base.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    })
    if env:
        base.update(env)
    return base


def _fake_git_repo(parent: Path, name: str, *, profile: str | None = None,
                   lang: str | None = None, regulated: bool | None = None) -> Path:
    repo = parent / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, env=_init_env())
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"],
                   cwd=str(repo), check=True, env=_init_env())
    if profile or lang or regulated is not None:
        state = {"profile": profile, "lang": lang, "regulated": regulated}
        (repo / ".sn-init-state.json").write_text(json.dumps(state))
    return repo


def test_find_workspace_root_walks_up(tmp_path: Path):
    """T15: cwd inside workspace subdir finds the workspace root."""
    ws = tmp_path / "ws"
    (ws / ".workspace").mkdir(parents=True)
    (ws / ".workspace" / "registry.json").write_text('{"services":[]}')
    (ws / "scripts").mkdir()
    found = workspace_cli._find_workspace_root(start=ws / "scripts")
    assert found == ws.resolve()


def test_init_creates_workspace_dir(tmp_path: Path):
    """T1: init scaffolds the full workspace tree."""
    rc = _run(tmp_path, "init", "ws")
    assert rc == 0
    ws = tmp_path / "ws"
    assert (ws / "WORKSPACE.md").is_file()
    assert (ws / "CLAUDE.md").is_file()
    assert (ws / "MIGRATION.md").is_file()
    assert (ws / ".workspace" / "registry.json").is_file()
    assert (ws / "scripts" / "status.sh").is_file()
    assert (ws / "scripts" / "sync.sh").is_file()
    assert (ws / "scripts" / "launch.sh").is_file()


def test_init_refuses_nonempty_target(tmp_path: Path):
    """T2: refuse to clobber a non-empty target."""
    target = tmp_path / "ws"
    target.mkdir()
    (target / "foo").write_text("x")
    rc = _run(tmp_path, "init", "ws")
    assert rc == errors.EXIT_USAGE  # 2
    assert (target / "foo").read_text() == "x"


def test_init_seeds_registry_with_zero_services(tmp_path: Path):
    """T3: registry.json has workspace_version + name + empty services."""
    _run(tmp_path, "init", "ws")
    reg = json.loads((tmp_path / "ws" / ".workspace" / "registry.json").read_text())
    assert reg["workspace_version"] == "1.0.0"
    assert reg["name"] == "ws"
    assert reg["services"] == []
    assert "created_at" in reg


def test_add_registers_existing_service(tmp_path: Path):
    """T4: add registers a sibling git repo."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go", regulated=False)
    ws = tmp_path / "ws"
    rc = _run(ws, "add", str(svc))
    assert rc == 0
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert len(reg["services"]) == 1
    entry = reg["services"][0]
    assert entry["slug"] == "svc-a"
    assert entry["path"] == "../svc-a"  # relative
    assert entry["profile"] == "microservice"
    assert entry["lang"] == "go"
    assert entry["regulated"] is False
    assert "registered_at" in entry


def test_add_refuses_non_git_dir(tmp_path: Path):
    """T5: refuse non-git dirs."""
    _run(tmp_path, "init", "ws")
    not_git = tmp_path / "not-git"
    not_git.mkdir()
    ws = tmp_path / "ws"
    rc = _run(ws, "add", str(not_git))
    assert rc == errors.EXIT_USAGE


def test_add_refuses_duplicate_slug(tmp_path: Path):
    """T6: refuse adding the same slug twice."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    rc = _run(ws, "add", str(svc))
    assert rc == errors.EXIT_USAGE


def test_add_reads_sn_init_state_when_present(tmp_path: Path):
    """T7: profile/lang/regulated come from .sn-init-state.json."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-bff", profile="bff", lang="ts", regulated=True)
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    entry = reg["services"][0]
    assert entry["profile"] == "bff"
    assert entry["lang"] == "ts"
    assert entry["regulated"] is True


def test_add_handles_missing_sn_init_state(tmp_path: Path):
    """T8: missing state file → null fields, not an error."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-bare")  # no .sn-init-state.json
    ws = tmp_path / "ws"
    rc = _run(ws, "add", str(svc))
    assert rc == 0
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    entry = reg["services"][0]
    assert entry["profile"] is None
    assert entry["lang"] is None
    assert entry["regulated"] is None


def test_add_owners_flag_overrides(tmp_path: Path):
    """T9: --owners flag wins over CODEOWNERS / null default."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc), "--owners=@team-platform")
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert reg["services"][0]["owners"] == "@team-platform"


def test_add_appends_to_member_gitignore(tmp_path: Path):
    """T10: add appends `<ws>/` to member's .gitignore (idempotent)."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    gi = (svc / ".gitignore").read_text(encoding="utf-8")
    assert "ws/" in gi
    # Idempotency: a second add of the same path is refused (T6 covers),
    # but the .gitignore line is appended only once.
    assert gi.count("ws/\n") == 1


def test_remove_strips_entry(tmp_path: Path):
    """T11: remove drops the slug from services[]."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    rc = _run(ws, "remove", "svc-a")
    assert rc == 0
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert reg["services"] == []


def test_remove_unknown_slug_exits_zero(tmp_path: Path, capsys):
    """T12: unknown slug → warn on stderr, exit 0, no registry change."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    rc = _run(ws, "remove", "nope")
    assert rc == 0
    err = capsys.readouterr().err
    assert "not registered" in err


def test_list_prints_table_and_regenerates_docs(tmp_path: Path, capsys):
    """T13: list prints table + regenerates WORKSPACE.md / CLAUDE.md markers."""
    _run(tmp_path, "init", "ws")
    svc = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    ws = tmp_path / "ws"
    _run(ws, "add", str(svc))
    rc = _run(ws, "list")
    assert rc == 0
    out = capsys.readouterr().out
    assert "svc-a" in out
    workspace_md = (ws / "WORKSPACE.md").read_text(encoding="utf-8")
    assert "svc-a" in workspace_md
    assert "microservice" in workspace_md
    claude_md = (ws / "CLAUDE.md").read_text(encoding="utf-8")
    assert "svc-a" in claude_md


def test_list_preserves_hand_edits_outside_markers(tmp_path: Path):
    """T14: list regenerates between markers only; outside prose survives."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    # Inject a hand-edit BEFORE the marker block.
    workspace_md = ws / "WORKSPACE.md"
    body = workspace_md.read_text(encoding="utf-8")
    sentinel = "\n## My hand-edit\n\nPreserve me.\n\n"
    body = body.replace("<!-- registry:begin -->", sentinel + "<!-- registry:begin -->")
    workspace_md.write_text(body, encoding="utf-8")
    # Run list.
    svc = _fake_git_repo(tmp_path, "svc-a")
    _run(ws, "add", str(svc))
    _run(ws, "list")
    body2 = workspace_md.read_text(encoding="utf-8")
    assert "## My hand-edit" in body2
    assert "Preserve me." in body2


def test_subcommand_outside_workspace_fails(tmp_path: Path):
    """T16: list/status/sync/launch outside a workspace → EXIT_USAGE."""
    rc = _run(tmp_path, "list")
    assert rc == errors.EXIT_USAGE


def test_dispatch_via_sn_init_workspace_subtree(tmp_path: Path):
    """T20: sn_init.main(["workspace", "init", "ws"]) routes to workspace_cli."""
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        rc = sn_init.main(["workspace", "init", "ws"])
    finally:
        os.chdir(old)
    assert rc == 0
    assert (tmp_path / "ws" / ".workspace" / "registry.json").is_file()


def test_status_invokes_bash_script(tmp_path: Path, monkeypatch):
    """T17: status delegates to scripts/status.sh, cwd=ws."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    calls: list[tuple[list[str], str]] = []
    def fake_call(argv, cwd=None):
        calls.append((argv, cwd))
        return 0
    monkeypatch.setattr("workspace_cli.subprocess.call", fake_call)
    _run(ws, "status")
    assert calls == [(["bash", str(ws / "scripts" / "status.sh")], str(ws))]


def test_sync_invokes_bash_script(tmp_path: Path, monkeypatch):
    """T18: sync delegates to scripts/sync.sh."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    calls: list[tuple[list[str], str]] = []
    def fake_call(argv, cwd=None):
        calls.append((argv, cwd))
        return 0
    monkeypatch.setattr("workspace_cli.subprocess.call", fake_call)
    _run(ws, "sync")
    assert calls == [(["bash", str(ws / "scripts" / "sync.sh")], str(ws))]


def test_launch_invokes_bash_script(tmp_path: Path, monkeypatch):
    """T19: launch delegates to scripts/launch.sh."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    calls: list[tuple[list[str], str]] = []
    def fake_call(argv, cwd=None):
        calls.append((argv, cwd))
        return 0
    monkeypatch.setattr("workspace_cli.subprocess.call", fake_call)
    _run(ws, "launch")
    assert calls == [(["bash", str(ws / "scripts" / "launch.sh")], str(ws))]


# ---------------------------------------------------------------------------
# B2.2-FU-4 — marketplace divergence warning


def _wire_marketplace(repo: Path, *, source: str | None = "./",
                      plugins: list[str] | None = None) -> None:
    """Drop minimal .claude/settings.json + .claude-plugin/marketplace.json
    into a fake repo so the divergence check has something to compare.
    """
    if plugins is not None:
        claude_dir = repo / ".claude"
        claude_dir.mkdir(exist_ok=True)
        settings = {"installed_plugins": [{"name": n} for n in plugins]}
        (claude_dir / "settings.json").write_text(json.dumps(settings))
    if source is not None:
        plugin_dir = repo / ".claude-plugin"
        plugin_dir.mkdir(exist_ok=True)
        manifest = {"marketplace": {"name": "org-internal", "source": source}}
        (plugin_dir / "marketplace.json").write_text(json.dumps(manifest))


def test_b22fu4_no_warning_when_identical(tmp_path: Path, capsys):
    """B2.2-FU-4 — identical marketplace state across members → silent add."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="microservice", lang="go")
    _wire_marketplace(a, source="./", plugins=["core-workflow", "core-guardrails"])
    _wire_marketplace(b, source="./", plugins=["core-workflow", "core-guardrails"])

    _run(ws, "add", str(a))
    capsys.readouterr()  # clear
    rc = _run(ws, "add", str(b))
    err = capsys.readouterr().err
    assert rc == 0
    assert "marketplace source mismatch" not in err
    assert "missing mandatory" not in err
    assert "installed_plugins set differs" not in err


def test_b22fu4_no_warning_first_member(tmp_path: Path, capsys):
    """B2.2-FU-4 — first member added to empty workspace → silent (nothing to compare)."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    _wire_marketplace(a, source="./", plugins=["core-workflow", "core-guardrails"])

    rc = _run(ws, "add", str(a))
    err = capsys.readouterr().err
    assert rc == 0
    assert "⚠" not in err


def test_b22fu4_source_mismatch_critical(tmp_path: Path, capsys):
    """B2.2-FU-4 — different marketplace.source → 🔴 critical, add still succeeds."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="microservice", lang="go")
    _wire_marketplace(a, source="https://github.com/orgA/mkt.git",
                      plugins=["core-workflow", "core-guardrails"])
    _wire_marketplace(b, source="https://github.com/orgB/mkt.git",
                      plugins=["core-workflow", "core-guardrails"])

    _run(ws, "add", str(a))
    capsys.readouterr()
    rc = _run(ws, "add", str(b))
    err = capsys.readouterr().err
    assert rc == 0
    assert "⚠ critical: marketplace source mismatch" in err
    assert "orgA" in err and "orgB" in err
    assert "svc-a" in err


def test_b22fu4_missing_mandatory_critical(tmp_path: Path, capsys):
    """B2.2-FU-4 — new member missing core-guardrails → 🔴 critical."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="microservice", lang="go")
    _wire_marketplace(a, source="./", plugins=["core-workflow", "core-guardrails"])
    _wire_marketplace(b, source="./", plugins=["core-workflow"])  # missing core-guardrails

    _run(ws, "add", str(a))
    capsys.readouterr()
    rc = _run(ws, "add", str(b))
    err = capsys.readouterr().err
    assert rc == 0
    assert "⚠ critical: new member missing mandatory plugin 'core-guardrails'" in err
    assert "svc-a" in err


def test_b22fu4_plugin_set_diff_warn(tmp_path: Path, capsys):
    """B2.2-FU-4 — installed_plugins set differs (extra opt-in) → 🟡 warn."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="bff", lang="go")
    _wire_marketplace(a, source="./", plugins=["core-workflow", "core-guardrails"])
    _wire_marketplace(b, source="./",
                      plugins=["core-workflow", "core-guardrails",
                               "contracts-sync", "bff-patterns"])

    _run(ws, "add", str(a))
    capsys.readouterr()
    rc = _run(ws, "add", str(b))
    err = capsys.readouterr().err
    assert rc == 0
    assert "⚠ warn: installed_plugins set differs" in err
    assert "new-only=['bff-patterns', 'contracts-sync']" in err
    # Mandatory plugins must not appear in the yellow diff (covered in red path).
    assert "core-workflow" not in err.split("⚠ warn:")[-1]
    assert "core-guardrails" not in err.split("⚠ warn:")[-1]


def test_b22fu4_legacy_member_silent(tmp_path: Path, capsys):
    """B2.2-FU-4 — new member without marketplace state (pre-B2.3 scaffold) → silent."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="microservice", lang="go")
    _wire_marketplace(a, source="./", plugins=["core-workflow", "core-guardrails"])
    # b has no .claude/settings.json, no .claude-plugin/marketplace.json.

    _run(ws, "add", str(a))
    capsys.readouterr()
    rc = _run(ws, "add", str(b))
    err = capsys.readouterr().err
    assert rc == 0
    assert "⚠" not in err


def test_b22fu4_legacy_existing_silent_for_that_member(tmp_path: Path, capsys):
    """B2.2-FU-4 — existing member without marketplace state is skipped in
    pairwise compare; other comparable members still drive findings.
    """
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="microservice", lang="go")
    c = _fake_git_repo(tmp_path, "svc-c", profile="microservice", lang="go")
    # a is legacy (no marketplace state); b carries it; c carries a divergent source.
    _wire_marketplace(b, source="https://github.com/orgA/mkt.git",
                      plugins=["core-workflow", "core-guardrails"])
    _wire_marketplace(c, source="https://github.com/orgB/mkt.git",
                      plugins=["core-workflow", "core-guardrails"])

    _run(ws, "add", str(a))
    _run(ws, "add", str(b))
    capsys.readouterr()
    rc = _run(ws, "add", str(c))
    err = capsys.readouterr().err
    assert rc == 0
    assert "⚠ critical: marketplace source mismatch" in err
    assert "svc-b" in err
    assert "svc-a" not in err  # legacy member silently skipped


def test_b22fu4_returns_zero_on_critical_findings(tmp_path: Path, capsys):
    """B2.2-FU-4 — critical findings do NOT block add (warn-only contract)."""
    _run(tmp_path, "init", "ws")
    ws = tmp_path / "ws"
    a = _fake_git_repo(tmp_path, "svc-a", profile="microservice", lang="go")
    b = _fake_git_repo(tmp_path, "svc-b", profile="microservice", lang="go")
    _wire_marketplace(a, source="https://github.com/orgA/mkt.git",
                      plugins=["core-workflow", "core-guardrails"])
    _wire_marketplace(b, source="https://github.com/orgB/mkt.git",
                      plugins=["core-workflow"])  # also missing mandatory

    _run(ws, "add", str(a))
    capsys.readouterr()
    rc = _run(ws, "add", str(b))
    assert rc == 0  # warn-only; register succeeds regardless

    # Both findings present + registry advanced.
    err = capsys.readouterr().err
    assert "marketplace source mismatch" in err
    assert "missing mandatory plugin 'core-guardrails'" in err
    reg = json.loads((ws / ".workspace" / "registry.json").read_text())
    assert {s["slug"] for s in reg["services"]} == {"svc-a", "svc-b"}
