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
import re
import secrets
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from string import Template

try:
    from . import claude_md_merger, errors, sn_logging as snlog  # type: ignore
except ImportError:
    # Allow running as plain script: `python3 scripts/sn_init.py ...`
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import claude_md_merger  # type: ignore
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
    p.add_argument("--rename-ns", action="store_true", dest="rename_ns",
                   help="During --upgrade: rename generated commands and agents to the flat "
                        "`sn-<name>` prefix layout (so they show as `/sn-<name>`). Handles both "
                        "legacy layouts (bare flat names and the mid-2026 `sn/` colon namespace). "
                        "Rewrites cross-references in Makefile/orchestrator.py/docs and "
                        "section-merges every CLAUDE*.md against the latest template. Refuses "
                        "unless --upgrade.")
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

    if getattr(args, "rename_ns", False) and not args.upgrade:
        raise errors.UsageError("--rename-ns requires --upgrade")

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
    rename_ns = bool(getattr(args, "rename_ns", False))
    if prev_version == TEMPLATE_VERSION and not rename_ns:
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

    rename_plan = _plan_rename_ns(target) if rename_ns else _RenamePlan()
    merge_plan = _plan_claude_md_merge(args, target) if rename_ns else []

    files = _plan_new_files(args, target)

    if args.dry_run:
        added = [(rel, c) for (rel, c) in files if not (target / rel).exists()]
        print(f"[upgrade-dry-run] would add {len(added)} missing files")
        for rel, _ in sorted(added):
            print(f"  + {rel}")
        if rename_ns:
            print(f"[upgrade-dry-run] would rename {len(rename_plan.renames)} files into sn/")
            for src, dst in rename_plan.renames:
                print(f"  ~ {src} → {dst}")
            print(f"[upgrade-dry-run] would rewrite refs in {len(rename_plan.rewrites)} files")
            for rel in sorted(rename_plan.rewrites):
                print(f"  * {rel}")
            print(f"[upgrade-dry-run] would section-merge {len(merge_plan)} CLAUDE*.md files")
            for rel, _, _ in merge_plan:
                print(f"  M {rel}")
        return errors.EXIT_OK

    logger = snlog.StepLogger(target=target, verbose=args.verbose)
    renamed: list[str] = []
    rewritten: list[str] = []
    merged: list[str] = []

    if rename_ns:
        # Rewrite first while files are still at their original paths — that way
        # renamed command/agent files carry their fixed-up content to the new
        # location automatically.
        for rel in rename_plan.rewrites:
            path = target / rel
            try:
                original = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                continue
            new_text = _rewrite_ns_refs(original)
            if new_text != original:
                with logger.step("rewrite", rel):
                    path.write_text(new_text, encoding="utf-8")
                rewritten.append(rel)

        for src, dst in rename_plan.renames:
            src_path = target / src
            dst_path = target / dst
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            with logger.step("rename", f"{src} → {dst}"):
                src_path.rename(dst_path)
            renamed.append(f"{src} -> {dst}")

        # Clean up the empty `sn/` subdir left behind by the mid-2026
        # colon-namespace layout.
        for sub in (target / ".claude/commands/sn", target / ".claude/agents/sn"):
            if sub.exists() and sub.is_dir() and not any(sub.iterdir()):
                sub.rmdir()

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for rel, existing, template_text in merge_plan:
            path = target / rel
            backup = path.with_suffix(path.suffix + f".pre-upgrade-{ts}.bak")
            try:
                backup.write_text(existing, encoding="utf-8")
            except OSError as e:
                logger.info(f"could not write backup for {rel}: {e}")
            try:
                merged_text = claude_md_merger.merge(
                    existing, template_text,
                    overwrite_sections=OVERWRITE_CLAUDE_SECTIONS,
                )
            except Exception as e:
                logger.info(f"merge failed for {rel}: {e}; keeping existing")
                continue
            if merged_text != existing:
                with logger.step("merge", rel):
                    path.write_text(merged_text, encoding="utf-8")
                merged.append(rel)

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
    if rename_ns:
        upgrade_entry["renamed"] = renamed
        upgrade_entry["rewritten"] = rewritten
        upgrade_entry["merged_files"] = merged
    state.setdefault("upgrades", []).append(upgrade_entry)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    summary = (
        f"sn-setup: upgraded {prev_version or '(none)'} → {TEMPLATE_VERSION}; "
        f"added {len(added)} file(s)"
    )
    if rename_ns:
        summary += (
            f"; renamed {len(renamed)}, rewrote {len(rewritten)} ref(s), "
            f"merged {len(merged)} CLAUDE*.md"
        )
    print(summary + ".")
    return errors.EXIT_OK


# ---------------------------------------------------------------------------
# --rename-ns helpers
# ---------------------------------------------------------------------------


RENAMED_COMMANDS = (
    "knowledge-update", "knowledge-promote", "knowledge-demote",
    "knowledge-check", "knowledge-tech-matrix",
    "sprint-new", "sprint-run", "sprint-add", "sprint-done",
    "sprint-status", "sprint-remove",
    "req-new", "req-import", "req-replay", "req-resume", "req-rollback",
    "gh-import",
    "verify",
)
RENAMED_AGENTS = (
    "knowledge-curator", "impact-analyzer", "task-decomposer",
    "task-executor", "task-tester", "integration-tester",
    "adversary", "evaluator", "agent-sdk-reviewer",
)
OVERWRITE_CLAUDE_SECTIONS = ("Tracking", "What sn-init created")

# Bare-name → sn:bare-name agent rewrites, applied only in known files (so we
# never touch a free-text mention in an unrelated user doc).
_AGENT_REWRITE_TARGETS = (
    "scripts/orchestrator.py",
    ".harness/README.md",
    ".harness/invariants/README.md",
)


@dataclass
class _RenamePlan:
    renames: list[tuple[str, str]] = field(default_factory=list)
    rewrites: list[str] = field(default_factory=list)


def _plan_rename_ns(target: Path) -> "_RenamePlan":
    """Return the set of file moves + files to rewrite for --rename-ns.

    Handles two legacy layouts in one pass:
      * flat bare names: `.claude/commands/<cmd>.md`
      * colon namespace (mid-2026 attempt): `.claude/commands/sn/<cmd>.md`
    Both converge on the new dash-prefix flat layout:
      `.claude/commands/sn-<cmd>.md`.
    """
    plan = _RenamePlan()

    for cmd in RENAMED_COMMANDS:
        dst = Path(".claude/commands") / f"sn-{cmd}.md"
        if (target / dst).exists():
            continue
        for src in (
            Path(".claude/commands") / f"{cmd}.md",
            Path(".claude/commands/sn") / f"{cmd}.md",
        ):
            if (target / src).exists():
                plan.renames.append((str(src), str(dst)))
                break

    for agent in RENAMED_AGENTS:
        dst = Path(".claude/agents") / f"sn-{agent}.md"
        if (target / dst).exists():
            continue
        for src in (
            Path(".claude/agents") / f"{agent}.md",
            Path(".claude/agents/sn") / f"{agent}.md",
        ):
            if (target / src).exists():
                plan.renames.append((str(src), str(dst)))
                break

    candidates = [
        "Makefile",
        *_AGENT_REWRITE_TARGETS,
    ]
    cmd_dir = target / ".claude/commands"
    if cmd_dir.exists():
        for path in cmd_dir.rglob("*.md"):
            candidates.append(str(path.relative_to(target)))

    seen: set[str] = set()
    for rel in candidates:
        if rel in seen:
            continue
        if (target / rel).exists():
            plan.rewrites.append(rel)
            seen.add(rel)
    return plan


def _rewrite_ns_refs(text: str) -> str:
    """Apply the fixed sn: namespace rewrites to a file's text."""
    out = text
    for cmd in RENAMED_COMMANDS:
        out = re.sub(rf"(?<![A-Za-z0-9_:])/{re.escape(cmd)}(?![A-Za-z0-9_-])",
                     f"/sn-{cmd}", out)
    for agent in RENAMED_AGENTS:
        # Backtick-wrapped bare-name (prose / docs).
        out = re.sub(rf"`{re.escape(agent)}`", f"`sn-{agent}`", out)
        # Dict/YAML *value* position only — preceded by `:` so we don't touch
        # keys that happen to share the agent's name (e.g. PHASE "adversary").
        out = re.sub(
            rf'(:\s*)"{re.escape(agent)}"',
            rf'\1"sn-{agent}"', out,
        )
        out = re.sub(
            rf"(:\s*)'{re.escape(agent)}'",
            rf"\1'sn-{agent}'", out,
        )
    return out


def _plan_claude_md_merge(
    args: argparse.Namespace, target: Path,
) -> list[tuple[str, str, str]]:
    """Return [(rel_path, existing_text, template_text)] for every CLAUDE*.md.

    Template text is rendered against the project's persisted vars where
    possible; if no template counterpart exists for a nested file we skip it.
    """
    pairs: list[tuple[str, str, str]] = []
    project_name = target.name
    tpl_vars = {"name": project_name, "lang": args.lang, "model": "claude-opus-4-8",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}

    tpl_root = TEMPLATES / "managed-agent-base"

    candidates: list[tuple[Path, Path]] = []
    for tpl_name in ("CLAUDE.md", "CLAUDE.local.md"):
        existing_path = target / tpl_name
        tpl_path = tpl_root / tpl_name
        if existing_path.exists() and tpl_path.exists():
            candidates.append((existing_path, tpl_path))

    # Nested CLAUDE*.md without a known template counterpart — merge against
    # the root template so they at least pick up template-managed sections.
    for path in target.rglob("CLAUDE*.md"):
        rel = path.relative_to(target)
        if rel.as_posix() in ("CLAUDE.md", "CLAUDE.local.md"):
            continue
        if any(part.startswith(".") and part not in (".claude", ".harness") for part in rel.parts):
            continue
        tpl_path = tpl_root / "CLAUDE.md"
        if tpl_path.exists():
            candidates.append((path, tpl_path))

    for existing_path, tpl_path in candidates:
        existing = existing_path.read_text(encoding="utf-8")
        raw = tpl_path.read_text(encoding="utf-8")
        rendered = string.Template(raw).safe_substitute(tpl_vars)
        rel = str(existing_path.relative_to(target))
        pairs.append((rel, existing, rendered))
    return pairs


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


def _git_init_commit(target: Path, logger: snlog.StepLogger) -> None:
    try:
        with logger.step("git init"):
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        with logger.step("git add"):
            subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        with logger.step("git commit"):
            subprocess.run(
                ["git", "commit", "-q", "-m", "init: scaffold via sn-init"],
                cwd=target,
                check=True,
                env={**os.environ, "GIT_COMMITTER_NAME": os.environ.get("GIT_COMMITTER_NAME", "sn-init"),
                     "GIT_COMMITTER_EMAIL": os.environ.get("GIT_COMMITTER_EMAIL", "sn-init@local")},
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
