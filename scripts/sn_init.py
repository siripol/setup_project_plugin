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

# Profile = high-level shape of the scaffolded repo. Overlays land in
# templates/profile/<profile>/ on top of base + lang.
PROFILE_CHOICES = ("microservice", "bff", "frontend")
PROFILE_ALIASES = {"service": "microservice"}

# Frontend-only sub-flag. Overlays land in templates/framework/<framework>/.
FRAMEWORK_CHOICES = ("next", "vite")
DEFAULT_FRAMEWORK = "next"

# Which (lang, profile) combinations are supported. Anything outside this map
# fails fast at parse time.
PROFILE_LANG_MATRIX: dict[str, tuple[str, ...]] = {
    "microservice": ("go", "py", "ts"),
    "bff": ("go", "ts"),
    "frontend": ("ts",),
}

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

# B2.3: Internal plugin-marketplace consumer model. When --marketplace=<source>
# is set, the scaffold seeds `.claude/settings.json::installed_plugins` with
# the two mandatory plugins (per design §6.2) plus profile-specific opt-ins
# (per design §6.3 + §6.6). The catalog itself (which plugins exist + their
# semver pins) lives inside the `core-workflow` + `core-guardrails` plugins
# themselves, shipped by B3.1; this consumer wiring only records pointers.
MARKETPLACE_MANDATORY_PLUGINS: tuple[str, ...] = ("core-workflow", "core-guardrails")
MARKETPLACE_PROFILE_PLUGINS: dict[str, tuple[str, ...]] = {
    "microservice": (),
    "bff": ("contracts-sync", "bff-patterns"),
    "frontend": (),
}
MARKETPLACE_REGULATED_PLUGINS: tuple[str, ...] = ("compliance-pack",)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sn-setup", description="Scaffold a Claude-powered project.")
    p.add_argument("name", nargs="?", default=None, help="Project name (creates ./<name>/)")
    p.add_argument("--lang", choices=LANG_CHOICES, default="go")
    p.add_argument(
        "--profile",
        default="microservice",
        help="Repo shape: microservice | bff | frontend (alias: service → microservice).",
    )
    p.add_argument(
        "--framework",
        choices=FRAMEWORK_CHOICES,
        default=DEFAULT_FRAMEWORK,
        help="Frontend framework (only used when --profile=frontend).",
    )
    p.add_argument("--tier", choices=TIER_CHOICES, default="both")
    p.add_argument("--license", choices=LICENSE_CHOICES, default="none", dest="license_kind")
    p.add_argument("--no-git", action="store_true",
                   help="Skip git init + initial commit. Note: pairing this with --workspace will "
                        "still create a bare .git/ dir on the project so the workspace can register "
                        "it (no commit is made).")
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
    p.add_argument("--workspace", action="store_true",
                   help="Pair-scaffold a sibling workspace dir aggregating this project.")
    p.add_argument("--workspace-name", default=None, dest="workspace_name",
                   help="Workspace dir name (default: <project>-workspace).")
    p.add_argument("--marketplace", default=None, dest="marketplace_source",
                   help="Internal plugin-marketplace source (git URL like "
                        "https://github.com/org/marketplace.git OR a local path "
                        "like './'). When set, emits .claude-plugin/marketplace.json, "
                        "an installed_plugins block in .claude/settings.json, and a "
                        "self-deactivating SessionStart bootstrap warning hook. "
                        "org/repo shorthand is rejected (platform-ambiguous).")
    p.add_argument("--workflow", choices=WORKFLOW_CHOICES, default="spec-loop")
    p.add_argument("--subagents", default=",".join(DEFAULT_SUBAGENTS),
                   help="Comma-list, 'all', or 'none'")
    p.add_argument("--no-audit-log", action="store_true", dest="no_audit_log")
    p.add_argument("--upgrade", action="store_true",
                   help="Patch-only: pull missing template files into an existing scaffold and "
                        "bump .sn-init-state.json template_version. Never overwrites edited files.")
    p.add_argument(
        "--rename-commands",
        action="store_true",
        dest="rename_commands",
        help="Rename flat sn-X-Y.md slash commands to grouped sn-X.md. "
             "Requires --upgrade. Idempotent; --force overrides user edits.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Force destructive ops (currently only --rename-commands).",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--policies", default=None,
                   help="Comma-separated list of policies to apply (replaces profile defaults).")
    p.add_argument("--add-policies", default=None, dest="add_policies",
                   help="Comma-separated list of policies to add to profile defaults.")
    p.add_argument("--remove-policies", default=None, dest="remove_policies",
                   help="Comma-separated list of policies to remove from profile defaults.")
    p.add_argument("--with-deps", action="store_true", dest="with_deps",
                   help="When applying, also install required-by policies.")
    return p


def _resolve_profile(raw: str) -> str:
    """Apply aliases and validate against PROFILE_CHOICES."""
    if raw is None:
        return "microservice"
    canonical = PROFILE_ALIASES.get(raw, raw)
    if canonical not in PROFILE_CHOICES:
        raise errors.UsageError(
            f"unknown --profile={raw!r}; valid: {sorted(PROFILE_CHOICES)} "
            f"(aliases: {sorted(PROFILE_ALIASES)})"
        )
    return canonical


def _validate_profile_lang(profile: str, lang: str) -> None:
    allowed = PROFILE_LANG_MATRIX.get(profile, ())
    if lang not in allowed:
        raise errors.UsageError(
            f"--profile={profile} does not support --lang={lang}; "
            f"allowed: {sorted(allowed)}"
        )


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


SUBTREES = {"policy", "profile", "workspace"}


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else list(argv)
    if raw and raw[0] in SUBTREES:
        if raw[0] == "policy":
            import policy_cli
            return policy_cli.main(raw[1:])
        if raw[0] == "profile":
            import profile_cli  # noqa: F401  (lands in Task 14)
            return profile_cli.main(raw[1:])
        if raw[0] == "workspace":
            import workspace_cli
            return workspace_cli.main(raw[1:])

    parser = build_parser()
    try:
        args = parser.parse_args(raw)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK

    if getattr(args, "rename_commands", False) and not args.upgrade:
        print(
            "sn-setup: --rename-commands requires --upgrade",
            file=sys.stderr,
        )
        return errors.EXIT_USAGE

    try:
        return run(args)
    except errors.SnInitError as e:
        print(f"sn-setup: {e}", file=sys.stderr)
        return e.exit_code
    except Exception as e:
        import policy_errors
        if isinstance(e, policy_errors.PolicyError):
            print(f"sn-setup: {e}", file=sys.stderr)
            return e.exit_code
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

    # Normalize + validate profile/framework before any I/O.
    args.profile = _resolve_profile(getattr(args, "profile", "microservice"))
    _validate_profile_lang(args.profile, args.lang)
    if args.profile != "frontend":
        # Framework only meaningful for frontend; pin to the default for
        # state/logging consistency but skip the overlay later.
        args.framework = DEFAULT_FRAMEWORK

    # B2.3: Validate --marketplace=<source> shape before any I/O.
    if getattr(args, "marketplace_source", None):
        args.marketplace_source = _validate_marketplace_source(args.marketplace_source)

    # B1.7b: regulated-data policies auto-add security-auditor to the default
    # subagent set, so the scaffold ships .claude/agents/security-auditor.md.
    # Must run BEFORE _render_claude builds the scaffold tree. Skipped when
    # the user explicitly opted out via --subagents=none.
    _auto_add_security_auditor_for_regulated(args)

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
    if prev_version == TEMPLATE_VERSION and not getattr(args, "rename_commands", False):
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
    # B2.3: marketplace_source persists across upgrades. Without this,
    # `--upgrade` on a scaffold originally built with --marketplace=<url>
    # silently drops the marketplace consumer files (no marketplace.json,
    # no installed_plugins, no bootstrap hook entry). Honor explicit
    # --marketplace on the upgrade invocation, else restore from state.
    args.marketplace_source = (
        getattr(args, "marketplace_source", None)
        or persisted.get("marketplace_source")
    )
    # Profile + framework: older state files predate these keys; default to
    # microservice/next so re-upgrades on legacy scaffolds keep working.
    args.profile = _resolve_profile(state.get("profile") or persisted.get("profile") or "microservice")
    args.framework = (
        state.get("framework") or persisted.get("framework") or DEFAULT_FRAMEWORK
    )
    _validate_profile_lang(args.profile, args.lang)

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

    if getattr(args, "rename_commands", False):
        import commands_migration
        report = commands_migration.run(
            target,
            force=getattr(args, "force", False),
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            # commands_migration.run already wrote the state file with the
            # commands_renamed_at + commands_migration block. Re-read so the
            # downstream state write below merges those fields rather than
            # clobbering them.
            state = json.loads(state_path.read_text(encoding="utf-8"))
        if report.already_done:
            ts = state.get("commands_renamed_at", "unknown")
            print(f"sn-setup: commands already renamed at {ts}; no-op.")
        else:
            print(
                f"sn-setup: renamed {len(report.from_flat)} commands into "
                f"{len(report.to_grouped)} groups; "
                f"retired {len(report.retired)}; "
                f"skipped {len(report.skipped)} user-edited"
            )
            for path in report.skipped:
                print(f"  skipped: {path}")

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

    if getattr(args, "workspace", False) and not args.dry_run:
        _pair_with_workspace(args, target, logger)

    if not args.no_git and not args.dry_run:
        _git_init_commit(target, logger)

    _apply_initial_policies(args, target, logger)
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
    _apply_initial_policies(args, target, logger)
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
    files.extend(_render_profile(args, project_name))
    if args.profile == "frontend":
        files.extend(_render_framework(args, project_name))
    if getattr(args, "marketplace_source", None):
        files.extend(_render_marketplace(args, project_name))
    files.extend(_render_claude(args, project_name))

    if args.license_kind != "none":
        files.append(("LICENSE", _read_template(f"licenses/{args.license_kind}.txt")))

    if not args.no_ci:
        files.append((".github/workflows/ci.yml", _render_ci(args, project_name)))

    if args.devcontainer:
        files.append((".devcontainer/devcontainer.json", _render_devcontainer(args)))

    return files


def _plan_add_files(args: argparse.Namespace, target: Path) -> list[tuple[str, str]]:
    """Return list of (relative_path, content) tuples for add mode (.claude/ only).

    B2.3 note: add mode deliberately does NOT call _render_marketplace.
    Add mode's contract is "drop a .claude/ overlay into an existing repo
    without touching anything else"; marketplace wiring is a new-scaffold
    concern (it owns top-level .claude-plugin/ + settings.json shape).
    Add mode users who want the marketplace block can run --upgrade instead,
    which preserves the persisted marketplace_source and re-renders.
    """
    project_name = target.name
    return _render_claude(args, project_name)


def _render_base(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    base = TEMPLATES / "managed-agent-base"
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "tier": args.tier,
        "profile": args.profile,
        "framework": args.framework,
        "model": "claude-opus-4-8",
        "system_prompt": args.prompt or "You are a helpful agent. Refine this prompt for your task.",
        "date": _today(),
    }
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base)
        rel_str = str(rel)
        # Mirror the `templates/profile/<P>/claude/` → `.claude/` rename
        # used by `_render_profile`. Source dir uses no-dot prefix because
        # `.claude/` is gitignored in this repo; the scaffold needs the
        # dotted form.
        if rel_str.startswith("claude/"):
            rel_str = ".claude/" + rel_str[len("claude/"):]
        content = path.read_text(encoding="utf-8")
        content = _substitute(content, ctx)
        files.append((rel_str, content))
    return files


def _render_lang(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    lang_dir = TEMPLATES / "lang" / args.lang
    if not lang_dir.exists():
        raise errors.UsageError(f"no template overlay for --lang={args.lang}")
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "profile": args.profile,
        "framework": args.framework,
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


def _render_profile(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    profile_dir = TEMPLATES / "profile" / args.profile
    if not profile_dir.exists():
        raise errors.UsageError(f"no template overlay for --profile={args.profile}")
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "profile": args.profile,
        "framework": args.framework,
        "model": "claude-opus-4-8",
    }
    for path in sorted(profile_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(profile_dir)
        # Mirror the `templates/claude/` → `.claude/` rename used by
        # `_render_claude`; profile overlays can ship a `claude/` subtree
        # (e.g. profile-specific subagents) without tripping the repo's
        # `.claude/` gitignore rule.
        rel_str = str(rel)
        if rel_str.startswith("claude/"):
            rel_str = ".claude/" + rel_str[len("claude/"):]
        content = path.read_text(encoding="utf-8")
        content = _substitute(content, ctx)
        files.append((rel_str, content))
    return files


def _validate_marketplace_source(source: str) -> str:
    """B2.3: Accept git URL (http/https/git@) or local path (./, /, ~/).
    Reject org/repo shorthand (platform-ambiguous: github vs gitlab vs bitbucket).
    Returns the source string unchanged on success.
    """
    if not source or not source.strip():
        raise errors.UsageError("--marketplace=<source> requires a non-empty value")
    s = source.strip()
    if s.startswith(("http://", "https://", "git@", "ssh://", "git+")):
        return s  # git URL form
    if s.startswith(("./", "../", "/", "~")) or s in (".", ".."):
        return s  # local path form
    raise errors.UsageError(
        f"--marketplace={source!r}: org/repo shorthand is rejected (platform-ambiguous). "
        "Use a git URL (https://github.com/org/repo.git) or local path (./)."
    )


def _resolve_marketplace_plugins(args: argparse.Namespace) -> list[str]:
    """B2.3: Return the ordered list of plugins to seed into installed_plugins.
    Mandatory first, then profile-specific, then compliance-pack if any
    regulated policy is planned. Deduplicates while preserving order.
    """
    plugins: list[str] = list(MARKETPLACE_MANDATORY_PLUGINS)
    for p in MARKETPLACE_PROFILE_PLUGINS.get(args.profile, ()):
        if p not in plugins:
            plugins.append(p)
    if REGULATED_POLICY_SLUGS.intersection(_resolve_planned_policy_set(args)):
        for p in MARKETPLACE_REGULATED_PLUGINS:
            if p not in plugins:
                plugins.append(p)
    return plugins


def _render_marketplace(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    """B2.3: Render the marketplace-consumer template subtree. Only invoked
    when args.marketplace_source is set. Mirrors `_render_profile` shape.

    The default subtree at templates/marketplace-consumer/default/ ships:
    - .claude-plugin/marketplace.json (consumer manifest)
    - claude/hooks/marketplace-bootstrap.sh (SessionStart warn-then-self-deactivate)
    The settings.patch.json LIVES in the same subtree but is NOT walked here;
    it is merged directly into the rendered settings.json inside _render_claude
    via _inject_marketplace_into_settings.
    """
    source = args.marketplace_source
    mkt_dir = TEMPLATES / "marketplace-consumer" / "default"
    if not mkt_dir.exists():
        raise errors.SnInitError(
            "missing template: marketplace-consumer/default/ "
            "(expected when --marketplace is set)"
        )
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "profile": args.profile,
        "framework": args.framework,
        "model": "claude-opus-4-8",
        "marketplace_source": source,
    }
    for path in sorted(mkt_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(mkt_dir)
        rel_str = str(rel)
        # The settings patch is merged inline by _render_claude, not emitted
        # as a file in the scaffold output.
        if rel_str == "settings.patch.json":
            continue
        # Same `claude/` → `.claude/` rename used by _render_base /
        # _render_profile (templates use no-dot prefix because `.claude/`
        # is in this repo's .gitignore).
        if rel_str.startswith("claude/"):
            rel_str = ".claude/" + rel_str[len("claude/"):]
        content = path.read_text(encoding="utf-8")
        content = _substitute(content, ctx)
        files.append((rel_str, content))
    return files


def _inject_marketplace_into_settings(data: dict, args: argparse.Namespace) -> dict:
    """B2.3: Mutate settings dict to add installed_plugins block + SessionStart
    bootstrap hook entry. Idempotent. Returns the (mutated) dict.
    """
    plugins = _resolve_marketplace_plugins(args)
    data["installed_plugins"] = [{"name": p} for p in plugins]

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks
    session_start = hooks.setdefault("SessionStart", [])
    if not isinstance(session_start, list):
        session_start = []
        hooks["SessionStart"] = session_start
    bootstrap_cmd = ".claude/hooks/marketplace-bootstrap.sh"
    if not any(
        isinstance(e, dict) and e.get("command") == bootstrap_cmd
        for e in session_start
    ):
        session_start.append({"command": bootstrap_cmd})
    return data


def _render_framework(args: argparse.Namespace, project_name: str) -> list[tuple[str, str]]:
    framework_dir = TEMPLATES / "framework" / args.framework
    if not framework_dir.exists():
        raise errors.UsageError(f"no template overlay for --framework={args.framework}")
    files: list[tuple[str, str]] = []
    ctx = {
        "name": project_name,
        "lang": args.lang,
        "profile": args.profile,
        "framework": args.framework,
        "model": "claude-opus-4-8",
    }
    for path in sorted(framework_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(framework_dir)
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
        "profile": args.profile,
        "framework": args.framework,
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

        # Drop audit hook scripts when the flag opts out (settings.json is
        # mutated below, not skipped here).
        if args.no_audit_log and rel_str.startswith(".claude/hooks/audit."):
            continue

        # Settings.json takes the mutation path: strip audit hooks if opted
        # out, inject marketplace installed_plugins + SessionStart bootstrap
        # entry when --marketplace is set. Both transforms are JSON-level so
        # they compose.
        if rel_str == ".claude/settings.json":
            raw = path.read_text(encoding="utf-8")
            try:
                data = json.loads(raw)
            except Exception:
                # Malformed template — preserve as-is so the failure is loud
                # downstream rather than masked by a partial mutation.
                files.append((rel_str, raw))
                continue
            if args.no_audit_log:
                data["hooks"] = {}
            if getattr(args, "marketplace_source", None):
                _inject_marketplace_into_settings(data, args)
            files.append((rel_str, json.dumps(data, indent=2) + "\n"))
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
        "profile": args.profile,
        "framework": args.framework if args.profile == "frontend" else None,
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
            "profile": args.profile,
            "framework": args.framework if args.profile == "frontend" else None,
            "marketplace_source": getattr(args, "marketplace_source", None),
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


def _pair_with_workspace(args: argparse.Namespace, target: Path, logger: snlog.StepLogger) -> None:
    """Scaffold a sibling workspace + register the project under it.

    R8 mitigation: this runs AFTER _write_state so .sn-init-state.json is on
    disk and workspace_cli._cmd_add can auto-collect profile/lang/regulated.
    """
    import workspace_cli  # type: ignore

    ws_name = args.workspace_name or f"{target.name}-workspace"
    if ws_name == target.name:
        raise errors.UsageError(
            f"--workspace-name {ws_name!r} collides with project name; pick a different name"
        )
    ws_dir = target.parent / ws_name

    # workspace_cli._cmd_add requires a git repo. If --no-git was passed we do
    # a bare `git init` here so the registration step can succeed. The commit
    # is omitted (same as --no-git semantics).
    if not (target / ".git").exists():
        try:
            subprocess.run(["git", "init", "-q"], cwd=target, check=True,
                           capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass  # git not available; add will fail gracefully

    old = Path.cwd()
    try:
        os.chdir(target.parent)
        # init: skip if workspace already exists (P4 idempotency).
        if not (ws_dir / ".workspace" / "registry.json").exists():
            rc = workspace_cli.main(["init", ws_name])
            if rc != 0:
                logger.info(f"workspace init failed: rc={rc}")
                return
        os.chdir(ws_dir)
        rc = workspace_cli.main(["add", str(target)])
        if rc != 0:
            logger.info(f"workspace add failed: rc={rc}")
    finally:
        os.chdir(old)


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
    profile_str = args.profile
    if args.profile == "frontend":
        profile_str = f"{args.profile}+{args.framework}"
    print(f"  lang={args.lang}  profile={profile_str}  tier={args.tier}  workflow={args.workflow}")
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


REGULATED_POLICY_SLUGS = frozenset({"memory-regulated", "pdpa-compliance"})


def _resolve_planned_policy_set(args: argparse.Namespace) -> list[str]:
    """Compute which policies WILL be applied at scaffold time.

    Mirrors the resolution in `_apply_initial_policies` but runs early
    (before the scaffold materializes) so other steps can react to the
    final set. Pure function; no filesystem mutation.
    """
    import yaml as _yaml

    if getattr(args, "policies", None) is not None:
        return [s.strip() for s in args.policies.split(",") if s.strip()]

    base_set: list[str] = []
    profile_defaults_path = (
        TEMPLATES / "profile" / getattr(args, "profile", "microservice") / "default_policies.yaml"
    )
    if profile_defaults_path.exists():
        data = _yaml.safe_load(profile_defaults_path.read_text(encoding="utf-8")) or {}
        base_set = list(data.get("policies") or [])

    final = list(base_set)
    if getattr(args, "add_policies", None):
        for s in args.add_policies.split(","):
            s = s.strip()
            if s and s not in final:
                final.append(s)
    if getattr(args, "remove_policies", None):
        drop = {s.strip() for s in args.remove_policies.split(",")}
        final = [s for s in final if s not in drop]
    return final


def _auto_add_security_auditor_for_regulated(args: argparse.Namespace) -> None:
    """B1.7b: when the scaffold will apply a regulated-data policy, append
    `security-auditor` to args.subagents so the scaffold ships
    .claude/agents/security-auditor.md by default. Honors --subagents=none.
    """
    subagents_spec = getattr(args, "subagents", "") or ""
    if subagents_spec.strip().lower() == "none":
        return  # explicit opt-out

    planned = _resolve_planned_policy_set(args)
    if not REGULATED_POLICY_SLUGS.intersection(planned):
        return

    requested = {s.strip() for s in subagents_spec.split(",") if s.strip()}
    if "security-auditor" in requested or "all" in requested:
        return  # already covered

    requested.add("security-auditor")
    args.subagents = ",".join(sorted(requested))
    print(
        "sn-setup: regulated policy detected — added security-auditor to default subagents.",
        file=sys.stderr,
    )


def _apply_initial_policies(args: argparse.Namespace, target: Path,
                            logger: snlog.StepLogger) -> None:
    """Resolve and apply the project's initial policy set per spec §9."""
    import yaml as _yaml

    import policy_apply
    import policy_cli
    import policy_errors

    # 1. Reject mixed override flags.
    if args.policies is not None and (args.add_policies or args.remove_policies):
        raise policy_errors.MixedOverrideFlags(
            "--policies replaces the default set; --add/--remove cannot combine with it"
        )

    # 2. Load profile default YAML if --policies is not provided.
    base_set: list[str] = []
    profile_defaults_path = (
        TEMPLATES / "profile" / args.profile / "default_policies.yaml"
    )
    if profile_defaults_path.exists():
        data = _yaml.safe_load(profile_defaults_path.read_text(encoding="utf-8")) or {}
        base_set = list(data.get("policies") or [])

    # 3. Resolve final set.
    if args.policies is not None:
        final = [s.strip() for s in args.policies.split(",") if s.strip()]
    else:
        final = list(base_set)
        if args.add_policies:
            for s in args.add_policies.split(","):
                s = s.strip()
                if s and s not in final:
                    final.append(s)
        if args.remove_policies:
            drop = {s.strip() for s in args.remove_policies.split(",")}
            final = [s for s in final if s not in drop]

    if not final:
        return

    # 4. Write project-local profile-defaults.yaml (always the original
    #    profile bundle, not the resolved final set).
    proj_defaults = target / ".claude" / "profile-defaults.yaml"
    proj_defaults.parent.mkdir(parents=True, exist_ok=True)
    proj_defaults.write_text(
        f"profile: {args.profile}\npolicies:\n"
        + "".join(f"  - {s}\n" for s in base_set),
        encoding="utf-8",
    )

    # 5. Apply.
    catalog = policy_cli._load_catalog()
    source = (
        "scaffold-default" if args.policies is None and not args.add_policies and not args.remove_policies
        else "scaffold-override" if args.policies is not None
        else "scaffold-delta"
    )
    policy_apply.apply_many(target, final, catalog, with_deps=args.with_deps, source=source)


if __name__ == "__main__":
    raise SystemExit(main())
