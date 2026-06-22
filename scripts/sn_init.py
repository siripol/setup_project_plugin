#!/usr/bin/env python3
"""sn-init — scaffold Claude-powered projects.

Auto-detects mode from cwd:
  - new mode: cwd empty OR `name` arg given → full scaffold + git init.
  - add mode: cwd non-empty + no `name` arg → writes only .claude/.

Atomic: writes to tmp dir + mv. State file .sn-init-state.json anchors idempotent re-run.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from string import Template

try:
    from . import errors, sn_logging as snlog  # type: ignore
except ImportError:
    # Allow running as plain script: `python3 scripts/sn_init.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import errors  # type: ignore
    import sn_logging as snlog  # type: ignore


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN_ROOT / "skills" / "sn-setup" / "templates"
SN_INIT_VERSION = "0.1.0"
TEMPLATE_VERSION = "2026.06.24"

LANG_CHOICES = ("go", "py", "ts")
TIER_CHOICES = ("2", "3", "both")
LICENSE_CHOICES = ("none", "MIT", "Apache-2.0")
WORKFLOW_CHOICES = ("none", "spec-loop")
OBSIDIAN_KNOWLEDGE_CHOICES = ("project", "global")
OBSIDIAN_MCP_CHOICES = ("auto", "on", "off")

# Subagent library buckets (filenames under templates/claude/agents/).
DEFAULT_SUBAGENTS = ("code-reviewer", "test-writer")
OPTIONAL_SUBAGENTS = ("doc-writer", "security-auditor", "planner")
WORKFLOW_SUBAGENTS = (
    "task-decomposer",
    "task-executor",
    "task-tester",
    "integration-tester",
    "evaluator",
    "adversary",
    "knowledge-curator",
    "impact-analyzer",
)

# Slash commands that pair with optional subagents (only ship when the
# subagent ships).
SUBAGENT_SHORTCUTS = {
    "code-reviewer": "review",
    "test-writer": "test",
    "doc-writer": "doc",
    "security-auditor": "audit",
    "planner": "plan",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sn-setup", description="Scaffold a Claude-powered project.")
    p.add_argument("name", nargs="?", default=None, help="Project name (creates ./<name>/)")
    p.add_argument("--lang", choices=LANG_CHOICES, default="go")
    p.add_argument("--tier", choices=TIER_CHOICES, default="both")
    p.add_argument("--license", choices=LICENSE_CHOICES, default="none", dest="license_kind")
    p.add_argument("--no-git", action="store_true")
    p.add_argument("--install", action="store_true")
    p.add_argument("--retry", type=int, default=3)
    p.add_argument("--no-ci", action="store_true")
    p.add_argument("--devcontainer", action="store_true")
    p.add_argument("--obsidian", nargs="?", const="__default__", default="__default__")
    p.add_argument("--no-obsidian", action="store_true")
    p.add_argument("--obsidian-knowledge", choices=OBSIDIAN_KNOWLEDGE_CHOICES,
                   default="project", dest="obsidian_knowledge")
    p.add_argument("--obsidian-mcp", choices=OBSIDIAN_MCP_CHOICES,
                   default="auto", dest="obsidian_mcp")
    p.add_argument("--prompt", default=None)
    p.add_argument("--workflow", choices=WORKFLOW_CHOICES, default="spec-loop")
    p.add_argument("--subagents", default=",".join(DEFAULT_SUBAGENTS),
                   help="Comma-list, 'all', or 'none'")
    p.add_argument("--no-audit-log", action="store_true", dest="no_audit_log")
    p.add_argument("--upgrade", action="store_true",
                   help="Patch-only: pull missing template files into an existing scaffold and "
                        "bump .sn-init-state.json template_version. Never overwrites edited files.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p


def _resolve_subagents(spec: str) -> set[str]:
    spec = spec.strip().lower()
    if spec == "all":
        return set(DEFAULT_SUBAGENTS + OPTIONAL_SUBAGENTS)
    if spec == "none":
        return set()
    names = {n.strip() for n in spec.split(",") if n.strip()}
    valid = set(DEFAULT_SUBAGENTS + OPTIONAL_SUBAGENTS)
    unknown = names - valid
    if unknown:
        raise errors.UsageError(f"unknown subagents: {sorted(unknown)}; valid: {sorted(valid)}")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK

    try:
        return run(args)
    except errors.SnInitError as e:
        print(f"sn-setup: {e}", file=sys.stderr)
        return e.exit_code
    except Exception as e:  # pragma: no cover - defensive
        print(f"sn-setup: internal error: {e!r}", file=sys.stderr)
        return errors.EXIT_INTERNAL


# ---------------------------------------------------------------------------
# mode detect


def detect_mode(cwd: Path, name: str | None) -> tuple[str, Path]:
    """Return (mode, target). mode in {'new', 'add'}."""
    if name is not None:
        target = (cwd / name).resolve()
        if target.exists() and any(target.iterdir()):
            raise errors.TargetNonEmptyError(
                f"target '{target}' is non-empty; refuse to scaffold over existing files"
            )
        return "new", target

    if not any(cwd.iterdir()):
        return "new", cwd.resolve()

    return "add", cwd.resolve()


# ---------------------------------------------------------------------------
# scaffold


def run(args: argparse.Namespace) -> int:
    cwd = Path.cwd()

    if args.upgrade:
        return _run_upgrade(args, cwd)

    mode, target = detect_mode(cwd, args.name)
    logger = snlog.StepLogger(target=target if not args.dry_run else None, verbose=args.verbose)
    logger.info(f"mode: {mode}")
    logger.info(f"target: {target}")

    if mode == "new":
        return _run_new(args, target, logger)
    else:
        return _run_add(args, target, logger)


def _run_upgrade(args: argparse.Namespace, cwd: Path) -> int:
    target = cwd.resolve()
    state_path = target / ".sn-init-state.json"
    if not state_path.exists():
        raise errors.SnInitError(
            "no .sn-init-state.json in cwd; upgrade only works on an existing sn-init scaffold."
        )
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise errors.SnInitError(f"could not read state file: {e}") from e

    prev_version = state.get("template_version", "")
    if prev_version == TEMPLATE_VERSION:
        print(f"sn-setup: already at template version {TEMPLATE_VERSION}; nothing to do.")
        return errors.EXIT_OK

    # Reuse the flags persisted in state when args weren't passed explicitly.
    persisted = state.get("flags", {})
    args.lang = state.get("lang", args.lang)
    args.tier = state.get("tier", args.tier)
    args.workflow = persisted.get("workflow", args.workflow)
    args.subagents = ",".join(persisted.get("subagents", []) or list(DEFAULT_SUBAGENTS))
    args.no_ci = not persisted.get("ci", True)
    args.devcontainer = persisted.get("devcontainer", False)
    args.license_kind = persisted.get("license", args.license_kind)
    args.no_audit_log = not persisted.get("audit_log", True)

    files = _plan_new_files(args, target)

    if args.dry_run:
        added = [(rel, c) for (rel, c) in files if not (target / rel).exists()]
        print(f"[upgrade-dry-run] would add {len(added)} missing files")
        for rel, _ in sorted(added):
            print(f"  + {rel}")
        return errors.EXIT_OK

    logger = snlog.StepLogger(target=target, verbose=args.verbose)

    added: list[str] = []
    for rel, content in files:
        path = target / rel
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with logger.step("add", rel):
            path.write_text(content, encoding="utf-8")
        if _should_be_executable(rel):
            try:
                path.chmod(0o755)
            except OSError:
                pass
        added.append(rel)

    # Bump state version + record the upgrade.
    state["template_version"] = TEMPLATE_VERSION
    upgrade_entry: dict = {
        "from": prev_version,
        "to": TEMPLATE_VERSION,
        "added": added,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    state.setdefault("upgrades", []).append(upgrade_entry)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(
        f"sn-setup: upgraded {prev_version or '(none)'} → {TEMPLATE_VERSION}; "
        f"added {len(added)} file(s)."
    )
    return errors.EXIT_OK


def _run_new(args: argparse.Namespace, target: Path, logger: snlog.StepLogger) -> int:
    files = _plan_new_files(args, target)
    if args.dry_run:
        _print_tree(target, files)
        return errors.EXIT_OK

    # Make sure target's parent exists (for nested name paths).
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp = target.parent / f"{target.name}.tmp-{secrets.token_hex(4)}"
    logger.set_target(tmp)
    try:
        _materialize(tmp, files, logger)
        # Atomic-ish swap. If target exists and is empty, drop it so rename succeeds.
        if target.exists():
            try:
                target.rmdir()
            except OSError:
                raise errors.TargetNonEmptyError(
                    f"target '{target}' became non-empty mid-scaffold"
                )
        tmp.rename(target)
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        raise
    logger.set_target(target)

    _write_state(target, args, mode="new", files=[str(p) for p, _ in files])

    if not args.no_git and not args.dry_run:
        _git_init_commit(target, logger)

    _print_summary(target, args, mode="new")
    return errors.EXIT_OK


def _run_add(args: argparse.Namespace, target: Path, logger: snlog.StepLogger) -> int:
    claude_dir = target / ".claude"
    state_path = target / ".sn-init-state.json"
    if claude_dir.exists() and not state_path.exists():
        raise errors.ClaudeExistsNoStateError(
            ".claude/ exists without sn-init state file. Refusing to overwrite. "
            "Pass --dry-run to preview, or remove the .claude/ dir first."
        )

    files = _plan_add_files(args, target)
    if args.dry_run:
        _print_tree(target, files)
        return errors.EXIT_OK

    # Patch sub-mode: only write missing files.
    written: list[str] = []
    for rel, content in files:
        path = target / rel
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with logger.step("write", rel):
            path.write_text(content, encoding="utf-8")
        if _should_be_executable(rel):
            try:
                path.chmod(0o755)
            except OSError:
                pass
        written.append(rel)

    _append_gitignore(target, [".claude/CLAUDE.local.md", ".claude/settings.local.json"], logger)
    _write_state(target, args, mode="add", files=written)
    _print_summary(target, args, mode="add", patched=written)
    return errors.EXIT_OK


# ---------------------------------------------------------------------------
# file planning


def _plan_new_files(args: argparse.Namespace, target: Path) -> list[tuple[str, str]]:
    """Return list of (relative_path, content) tuples for a fresh project."""
    project_name = target.name
    files: list[tuple[str, str]] = []

    files.extend(_render_base(args, project_name))
    files.extend(_render_lang(args, project_name))
    files.extend(_render_claude(args, project_name))

    if args.license_kind != "none":
        files.append(("LICENSE", _read_template(f"licenses/{args.license_kind}.txt")))

    if not args.no_ci:
        files.append((".github/workflows/ci.yml", _render_ci(args, project_name)))

    if args.devcontainer:
        files.append((".devcontainer/devcontainer.json", _render_devcontainer(args)))

    return files


def _plan_add_files(args: argparse.Namespace, target: Path) -> list[tuple[str, str]]:
    """Return list of (relative_path, content) tuples for add mode (.claude/ only)."""
    project_name = target.name
    return _render_claude(args, project_name)


def _render_base(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    base = TEMPLATES / "managed-agent-base"
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "tier": args.tier,
        "model": "claude-opus-4-8",
        "system_prompt": args.prompt or "You are a helpful agent. Refine this prompt for your task.",
        "date": _today(),
    }
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base)
        content = path.read_text(encoding="utf-8")
        content = _substitute(content, ctx)
        files.append((str(rel), content))
    return files


def _render_lang(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    lang_dir = TEMPLATES / "lang" / args.lang
    if not lang_dir.exists():
        raise errors.UsageError(f"no template overlay for --lang={args.lang}")
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "model": "claude-opus-4-8",
    }
    for path in sorted(lang_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(lang_dir)
        content = path.read_text(encoding="utf-8")
        content = _substitute(content, ctx)
        files.append((str(rel), content))
    return files


def _render_claude(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    claude = TEMPLATES / "claude"
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "model": "claude-opus-4-8",
    }
    subagents = _resolve_subagents(args.subagents)
    workflow_on = args.workflow == "spec-loop"

    for path in sorted(claude.rglob("*")):
        if path.is_dir():
            continue
        rel_native = path.relative_to(claude)  # native nested subdir layout
        parts = rel_native.parts

        # --- subagent filter: keep top-level base files, gate optional + workflow.
        if parts and parts[0] == "agents":
            # Drop the optional/ subdir prefix and gate by flags.
            if len(parts) == 1 and parts[0] == "agents":
                pass  # not possible — rglob yields files only
            elif len(parts) >= 2 and parts[1] == "optional":
                name = Path(parts[-1]).stem
                if name not in subagents:
                    continue
                rel_native = Path("agents") / parts[-1]
            elif len(parts) == 2:
                # Top-level agents/<file>.md — README ships always; sn-prefixed
                # workflow files gate on workflow_on; everything else gates by
                # subagent membership.
                stem = Path(parts[-1]).stem
                if stem == "README":
                    pass
                elif stem.startswith("sn-"):
                    if not workflow_on:
                        continue
                elif stem in subagents:
                    pass
                else:
                    continue

        # --- command filter: gate sn-prefixed + subagents/ subdirs.
        if parts and parts[0] == "commands":
            if len(parts) == 2 and Path(parts[-1]).stem.startswith("sn-"):
                if not workflow_on:
                    continue
                rel_native = Path("commands") / parts[-1]
            elif len(parts) >= 2 and parts[1] == "subagents":
                stem = Path(parts[-1]).stem  # e.g. "review"
                owner = _shortcut_owner(stem)
                if owner is None or owner not in subagents:
                    continue
                rel_native = Path("commands") / parts[-1]
            # Top-level commands/*.md (README, claude-local-*): always ship.

        rel = Path(".claude") / rel_native
        rel_str = str(rel)

        # Skip audit hook artifacts when the flag opts out.
        if args.no_audit_log and (
            rel_str.startswith(".claude/hooks/audit.")
            or rel_str == ".claude/settings.json"
        ):
            if rel_str == ".claude/settings.json":
                content = _read_template("claude/settings.json")
                content = _strip_audit_hooks(content)
                files.append((rel_str, content))
                continue
            # drop audit.{sh,py,ts}
            continue

        content = path.read_text(encoding="utf-8")
        content = _substitute(content, ctx)
        files.append((rel_str, content))
    return files


def _shortcut_owner(slash_name: str) -> str | None:
    for owner, shortcut in SUBAGENT_SHORTCUTS.items():
        if shortcut == slash_name:
            return owner
    return None


def _strip_audit_hooks(settings_json: str) -> str:
    """Return settings.json with the hooks block emptied."""
    try:
        data = json.loads(settings_json)
        data["hooks"] = {}
        return json.dumps(data, indent=2) + "\n"
    except Exception:
        return settings_json


def _render_ci(args: argparse.Namespace, project_name: str) -> str:
    tmpl = _read_template("ci/github-actions.yml.tmpl")
    return _substitute(tmpl, {"name": project_name, "lang": args.lang})


def _render_devcontainer(args: argparse.Namespace) -> str:
    tmpl = _read_template("devcontainer/devcontainer.json.tmpl")
    return _substitute(tmpl, {"lang": args.lang})


def _read_template(rel: str) -> str:
    path = TEMPLATES / rel
    if not path.exists():
        raise errors.SnInitError(f"missing template: {rel}")
    return path.read_text(encoding="utf-8")


def _substitute(content: str, ctx: dict) -> str:
    # Only substitute when at least one of our template variables (${name},
    # ${lang}, ${model}, ...) actually appears in the file. Files like Makefile
    # contain `${next:-000}` (shell-side default expansion) and `$$VAR` (Make
    # `$$` → shell `$VAR`) which look like Python Template syntax but are not.
    # `string.Template.safe_substitute` would (correctly per its spec) halve
    # the `$$` escapes to `$`, breaking every recipe that referenced a Make
    # variable. We sidestep the trap by only running substitution when we know
    # the file is one of ours.
    if not any(f"${{{key}}}" in content for key in ctx):
        return content
    try:
        return Template(content).safe_substitute(ctx)
    except Exception:
        return content


# ---------------------------------------------------------------------------
# materialize


def _materialize(root: Path, files: list[tuple[str, str]], logger: snlog.StepLogger) -> None:
    for rel, content in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with logger.step("write", rel):
            path.write_text(content, encoding="utf-8")
        if _should_be_executable(rel):
            try:
                path.chmod(0o755)
            except OSError:
                pass


def _should_be_executable(rel: str) -> bool:
    # Hooks under .claude/hooks/ and .githooks/ + any *.sh need the +x bit.
    return (
        rel.endswith(".sh")
        or rel.startswith(".githooks/")
        or rel.startswith(".claude/hooks/")
    )


def _append_gitignore(target: Path, lines: list[str], logger: snlog.StepLogger) -> None:
    gi = target / ".gitignore"
    existing = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    additions = [ln for ln in lines if ln not in existing]
    if not additions:
        return
    with logger.step("append", ".gitignore"):
        with gi.open("a", encoding="utf-8") as fh:
            if existing and not existing[-1] == "":
                fh.write("\n")
            for ln in additions:
                fh.write(ln + "\n")


def _write_state(target: Path, args: argparse.Namespace, mode: str, files: list[str]) -> None:
    state = {
        "sn_init_version": SN_INIT_VERSION,
        "template_version": TEMPLATE_VERSION,
        "mode": mode,
        "lang": args.lang,
        "tier": args.tier,
        "flags": {
            "license": args.license_kind,
            "ci": not args.no_ci,
            "devcontainer": args.devcontainer,
            "obsidian": (args.obsidian if args.obsidian != "__default__" else "default") if not args.no_obsidian else "off",
            "obsidian_knowledge": args.obsidian_knowledge,
            "obsidian_mcp": args.obsidian_mcp,
            "workflow": args.workflow,
            "subagents": sorted(_resolve_subagents(args.subagents)),
            "install": args.install,
            "git": not args.no_git,
            "audit_log": not args.no_audit_log,
        },
        "files_written": files,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (target / ".sn-init-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


_DEFAULT_IDENTITY_NAME = "Siripol"
_DEFAULT_IDENTITY_EMAIL = "siripoln.media@gmail.com"


def _resolve_identity(target: Path) -> tuple[str, str]:
    """Three-tier identity fallback (used for both author and committer):
      1. Env vars (GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL) — CI override path.
      2. `git config user.name` / `user.email` from the target dir — picks up
         the contributor's local identity once `git init` has run.
      3. Hard-coded Siripol — last-resort default.
    """
    name = os.environ.get("GIT_AUTHOR_NAME") or os.environ.get("GIT_COMMITTER_NAME")
    email = os.environ.get("GIT_AUTHOR_EMAIL") or os.environ.get("GIT_COMMITTER_EMAIL")
    if not (name and email):
        try:
            cfg_name = subprocess.run(
                ["git", "config", "user.name"], cwd=target, capture_output=True, text=True, check=False
            ).stdout.strip()
            cfg_email = subprocess.run(
                ["git", "config", "user.email"], cwd=target, capture_output=True, text=True, check=False
            ).stdout.strip()
        except FileNotFoundError:
            cfg_name = cfg_email = ""
        name = name or cfg_name or _DEFAULT_IDENTITY_NAME
        email = email or cfg_email or _DEFAULT_IDENTITY_EMAIL
    return name, email


def _git_init_commit(target: Path, logger: snlog.StepLogger) -> None:
    try:
        with logger.step("git init"):
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        with logger.step("git add"):
            subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        name, email = _resolve_identity(target)
        commit_message = (
            "init: scaffold via sn-init\n"
            "\n"
            f"Author: {name} <{email}>\n"
        )
        with logger.step("git commit"):
            subprocess.run(
                ["git", "commit", "-q", "-m", commit_message],
                cwd=target,
                check=True,
                env={
                    **os.environ,
                    "GIT_AUTHOR_NAME": name,
                    "GIT_AUTHOR_EMAIL": email,
                    "GIT_COMMITTER_NAME": name,
                    "GIT_COMMITTER_EMAIL": email,
                },
            )
    except FileNotFoundError:
        # git not installed; skip silently
        logger.info("git not found, skipping init+commit")
    except subprocess.CalledProcessError as e:
        logger.info(f"git step failed: {e}")


def _print_tree(target: Path, files: list[tuple[str, str]]) -> None:
    print(f"[dry-run] would create {len(files)} files under {target}/")
    for rel, content in sorted(files):
        size = len(content.encode("utf-8"))
        print(f"  {rel}  ({size} bytes)")


def _print_summary(target: Path, args: argparse.Namespace, mode: str, patched: list[str] | None = None) -> None:
    print(f"sn-setup: {mode} scaffold complete at {target}")
    if patched is not None:
        if patched:
            print(f"  patched {len(patched)} missing file(s): {', '.join(patched[:5])}{'...' if len(patched) > 5 else ''}")
        else:
            print("  no missing files (already up to date)")
    print(f"  lang={args.lang}  tier={args.tier}  workflow={args.workflow}")
    print("  Run 'make hooks-install' to activate commit-msg + post-merge hooks.")
    _print_agent_sdk_verify_hint(args)


def _print_agent_sdk_verify_hint(args: argparse.Namespace) -> None:
    """Suggest running Anthropic's official agent-sdk-dev verifier after a
    Python or TypeScript scaffold. Informational only — never auto-invoke
    because the agent-sdk-dev plugin may not be installed."""
    verifier = {"py": "agent-sdk-verifier-py", "ts": "agent-sdk-verifier-ts"}.get(args.lang)
    if verifier is None:
        return
    print("")
    print("Next step — verify your Agent SDK code against Anthropic's official patterns:")
    print("  1. Read docs/principles/agent-sdk-best-practices.md")
    print("  2. Run /sn-verify (or make verify) to check the mechanical rules")
    print(f"  3. (Optional) Install Anthropic's agent-sdk-dev plugin: /plugin install agent-sdk-dev")
    print(f"     Then ask: \"Run {verifier} on this project\"")
    print("Reference: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/agent-sdk-dev")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


if __name__ == "__main__":
    raise SystemExit(main())
