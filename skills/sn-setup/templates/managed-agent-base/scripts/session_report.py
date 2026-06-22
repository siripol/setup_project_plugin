#!/usr/bin/env python3
"""sn-session-report — render Claude Code session usage to Obsidian.

Thin Python wrapper around the upstream Anthropic `session-report` plugin's
`analyze-sessions.mjs`. Locates the analyzer, runs it, filters the JSON to
the current project, renders Markdown, writes the report into the Obsidian
vault under `projects/<project>/session-reports/`, and (unless --no-push)
commits + pushes the vault.

No external Python deps. Requires `node` on PATH and the upstream plugin
installed at `~/.claude/plugins/marketplaces/.../analyze-sessions.mjs`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from . import errors  # type: ignore
    from . import session_report_render as renderer  # type: ignore
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import errors  # type: ignore
    except ImportError:
        # Scaffolded projects don't ship `errors.py`. Inline a minimal stub
        # that exposes the same surface this module touches.
        import types

        errors = types.SimpleNamespace(
            EXIT_OK=0,
            EXIT_USAGE=2,
            EXIT_VAULT_UNWRITABLE=5,
            EXIT_MISSING_DEP=9,
            EXIT_INTERNAL=99,
            SnInitError=Exception,
            MissingAnalyzerError=type(
                "MissingAnalyzerError", (Exception,), {"exit_code": 9}
            ),
            VaultUnwritableError=type(
                "VaultUnwritableError", (Exception,), {"exit_code": 5}
            ),
        )
    import session_report_render as renderer  # type: ignore


INSTALL_HINT = (
    "sn-session-report: upstream analyzer not found.\n"
    "Install:\n"
    "  /plugin marketplace add anthropics/claude-plugins-official\n"
    "  /plugin install session-report@claude-plugins-official\n"
    "Or set $SN_SESSION_REPORT_ANALYZER=<path> to point at an existing copy."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sn-session-report")
    p.add_argument(
        "since", nargs="?", default="7d",
        help="Window: 7d (default), 24h, 30d, all, or an ISO timestamp.",
    )
    p.add_argument(
        "--analyzer", default=None,
        help="Path to analyze-sessions.mjs (overrides detection).",
    )
    p.add_argument(
        "--vault", default=None,
        help="Vault path override (else $OBSIDIAN_VAULT then .sn-init/knowledge).",
    )
    p.add_argument(
        "--project", default=None,
        help="Project encoded key (else derived from cwd basename).",
    )
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--no-push", action="store_true", dest="no_push")
    p.add_argument("--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return errors.EXIT_USAGE if e.code else errors.EXIT_OK
    try:
        return run(args)
    except errors.SnInitError as e:
        print(f"sn-session-report: {e}", file=sys.stderr)
        return getattr(e, "exit_code", errors.EXIT_INTERNAL)
    except Exception as e:  # pragma: no cover - defensive
        print(f"sn-session-report: internal error: {e!r}", file=sys.stderr)
        return errors.EXIT_INTERNAL


def run(args: argparse.Namespace) -> int:
    analyzer = locate_analyzer(args.analyzer)
    if analyzer is None:
        print(INSTALL_HINT, file=sys.stderr)
        raise errors.MissingAnalyzerError("upstream analyzer not located")

    cwd = Path.cwd().resolve()
    project_encoded = args.project or encode_project(cwd)
    # The cwd basename is the human-readable project name. The encoded key
    # used for analyzer JSON lookup loses underscores (both `/` and `_` are
    # encoded as `-`), so we cannot reverse it reliably — keep the raw name.
    project_name = cwd.name
    if args.verbose:
        print(f"[locate] analyzer: {analyzer}", file=sys.stderr)
        print(f"[locate] project key: {project_encoded}", file=sys.stderr)
        print(f"[locate] project name: {project_name}", file=sys.stderr)

    payload = run_analyzer(analyzer, args.since)
    if args.verbose:
        keys = list((payload.get("by_project") or {}).keys())
        print(f"[analyze] projects in payload: {keys}", file=sys.stderr)

    # Allow loose match — if exact key not present but a similar one is, use it.
    project_encoded = resolve_project_key(project_encoded, payload)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md = renderer.render_markdown(
        payload, project_encoded, args.since, today, project_name=project_name,
    )

    if args.dry_run:
        print(f"[dry-run] would write report ({len(md)} chars)")
        print(md[:1200])
        if len(md) > 1200:
            print("...")
        return errors.EXIT_OK

    vault_root = resolve_vault_path(args.vault, cwd)
    out_dir = vault_root / "projects" / project_name / "session-reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out_path = out_dir / f"{stamp}.md"
    write_atomic(out_path, md)
    update_index(out_dir, out_path, args.since)

    if not args.no_push:
        commit_and_push(vault_root, out_path, stamp, project_name)

    print(str(out_path))
    return errors.EXIT_OK


# ----- analyzer detection ------------------------------------------------


def locate_analyzer(override: str | None) -> Path | None:
    """Return the first hit per the documented resolution order."""
    if override:
        p = Path(override).expanduser().resolve()
        return p if p.is_file() else None

    env = os.environ.get("SN_SESSION_REPORT_ANALYZER")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_file():
            return p
        return None

    home = Path.home() / ".claude" / "plugins"
    for path in (home / "marketplaces").glob(
        "*/plugins/session-report/skills/session-report/analyze-sessions.mjs"
    ):
        if path.is_file():
            return path

    if home.exists():
        for path in home.rglob("analyze-sessions.mjs"):
            if path.is_file():
                return path

    return None


def run_analyzer(analyzer: Path, since: str) -> dict:
    cmd = ["node", str(analyzer), "--json"]
    if since and since != "all":
        cmd += ["--since", since]
    res = subprocess.run(
        cmd, capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        raise errors.SnInitError(
            f"analyzer failed (rc={res.returncode}): {res.stderr.strip()[:400]}"
        )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise errors.SnInitError(f"analyzer returned non-JSON: {e}") from e


# ----- project key resolution -------------------------------------------


def encode_project(cwd: Path) -> str:
    """Mimic the analyzer's project key encoding from a directory path.

    The analyzer encodes Claude Code's project root as
    `<path with / and _ replaced by ->`. Example:
    `/Users/siripol/Claude/setup_project_plugin` →
    `-Users-siripol-Claude-setup-project-plugin`.
    """
    return re.sub(r"[/_]", "-", str(cwd))


def resolve_project_key(want: str, payload: dict) -> str:
    """Return the best-matching key in payload['by_project'] for `want`.

    Exact match wins; otherwise the longest common-suffix key; otherwise
    return `want` unchanged so the renderer can still produce a header (with
    zero stats).
    """
    keys = list((payload.get("by_project") or {}).keys())
    if want in keys:
        return want
    # suffix match: pick the project key whose value shares the last few
    # path segments with `want`.
    want_tail = want.rsplit("-", 3)[-1] if want else ""
    if want_tail:
        for k in keys:
            if k.endswith(want_tail):
                return k
    return want


# ----- vault path -------------------------------------------------------


def resolve_vault_path(explicit: str | None, cwd: Path) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise errors.VaultUnwritableError(f"vault path does not exist: {p}")
        return p

    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p

    symlink = cwd / ".sn-init" / "knowledge"
    if symlink.exists():
        target = symlink.resolve()
        # The symlink points at <vault>/knowledge — climb one to vault root,
        # but only if the parent looks like a vault (has .git or AllShared* dir).
        if target.name == "knowledge" and (target.parent / ".git").exists():
            return target.parent
        return target

    # Last-resort fallback: write reports inside the repo itself.
    fallback = cwd / "session-reports"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


# ----- write + index + commit -------------------------------------------


def write_atomic(path: Path, content: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp-{secrets.token_hex(4)}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def update_index(out_dir: Path, latest: Path, window: str) -> None:
    """Append a one-line entry to out_dir/README.md (create on first run)."""
    index = out_dir / "README.md"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"- [[{latest.stem}]] — {window} window, generated {today}"
    if not index.exists():
        header = (
            f"# Session reports\n\n"
            f"Auto-generated by `/sn-session-report`. Each entry is one weekly "
            f"or ad-hoc report against the upstream Anthropic session-report "
            f"analyzer ([[../../../global/shared/session-report-skill]]).\n\n"
        )
        index.write_text(header + entry + "\n", encoding="utf-8")
        return
    body = index.read_text(encoding="utf-8")
    if entry not in body:
        if not body.endswith("\n"):
            body += "\n"
        body += entry + "\n"
        index.write_text(body, encoding="utf-8")


def find_git_root(start: Path) -> Path | None:
    """Walk up from `start` until a directory containing `.git` is found.

    Returns the first such ancestor, or None if none exists. Used by the
    commit step because the vault's `.git/` is often a parent of the
    knowledge dir (Obsidian vaults commonly live under
    `<repo>/AllSharedKnowledge/knowledge/`).
    """
    cur = start.resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def commit_and_push(vault_root: Path, out_path: Path, stamp: str, project: str) -> None:
    """Stage the new report, commit with knowledge: prefix, push.

    Walks up from `vault_root` to locate the enclosing git repo so that
    Obsidian vaults nested under a parent repo (e.g.
    `<repo>/AllSharedKnowledge/knowledge/`) commit correctly. No-op (with
    stderr note) when no enclosing git repo exists.
    """
    git_root = find_git_root(vault_root)
    if git_root is None:
        print(
            f"[commit] no enclosing git repo found above {vault_root}; "
            f"skipping commit.",
            file=sys.stderr,
        )
        return

    rel = out_path.relative_to(git_root)
    index_rel = (out_path.parent / "README.md").relative_to(git_root)
    msg = (
        f"knowledge: session report {project} {stamp}\n\n"
        f"Auto-generated by /sn-session-report.\n"
    )
    try:
        subprocess.run(
            ["git", "-C", str(git_root), "add", str(rel), str(index_rel)],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(git_root), "commit", "-m", msg],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(git_root), "push"],
            check=False, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[commit] failed: {e.stderr.strip()[:300]}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
