"""Apply / remove / upgrade orchestration across the five policy layers.

This module owns the lifecycle of a single policy in a single project.
Exclusive-group, requires, and conflicts_with handling are layered on top
in Task 8 (`apply_many`).
"""
from __future__ import annotations

import json
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import policy_claude_md
import policy_loader
import policy_settings_merge
import policy_state

DOCS_DIR = ".claude/docs/policies"
RULES_DIR = ".claude/rules"
SETTINGS_PATH = ".claude/settings.json"


@dataclass
class ApplyReport:
    slug: str = ""
    applied_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    swap_from: str | None = None
    swap_to: str | None = None
    was_noop: bool = False


def apply(project_dir: Path, meta: policy_loader.PolicyMeta, source: str = "cli") -> ApplyReport:
    state = policy_state.read_state(project_dir)
    report = ApplyReport(slug=meta.slug)

    # Already applied at same version?
    existing = _find_applied(state, meta.slug)
    if existing and existing["version"] == meta.version:
        report.was_noop = True
        return report

    content_sha: dict[str, str] = {}

    # CLAUDE.md row.
    claude_md_path = project_dir / "CLAUDE.md"
    src_text = claude_md_path.read_text(encoding="utf-8") if claude_md_path.exists() else ""
    row = (meta.root / meta.files["claude_md_row"]).read_text(encoding="utf-8").strip("\n")
    new_text, row_sha = policy_claude_md.upsert_row(src_text, meta.slug, row)
    claude_md_path.write_text(new_text, encoding="utf-8")
    content_sha[f"CLAUDE.md#row:{meta.slug}"] = row_sha
    report.applied_files.append("CLAUDE.md#row")

    # Docs.
    docs_dst = project_dir / DOCS_DIR / f"{meta.slug}.md"
    docs_dst.parent.mkdir(parents=True, exist_ok=True)
    docs_src = meta.root / meta.files["docs"]
    if docs_dst.exists():
        report.skipped_files.append(str(docs_dst.relative_to(project_dir)))
    else:
        shutil.copyfile(docs_src, docs_dst)
        content_sha[str(docs_dst.relative_to(project_dir))] = policy_state.sha256_file(docs_dst)
        report.applied_files.append(str(docs_dst.relative_to(project_dir)))

    # Rules (optional).
    if meta.files.get("rules"):
        rules_dst = project_dir / RULES_DIR / f"{meta.slug}.md"
        rules_dst.parent.mkdir(parents=True, exist_ok=True)
        if rules_dst.exists():
            report.skipped_files.append(str(rules_dst.relative_to(project_dir)))
        else:
            shutil.copyfile(meta.root / meta.files["rules"], rules_dst)
            content_sha[str(rules_dst.relative_to(project_dir))] = policy_state.sha256_file(rules_dst)
            report.applied_files.append(str(rules_dst.relative_to(project_dir)))

    # Settings patch (optional).
    settings_marker: str | None = None
    if meta.files.get("settings_patch"):
        patch = json.loads((meta.root / meta.files["settings_patch"]).read_text(encoding="utf-8"))
        settings_path = project_dir / SETTINGS_PATH
        existing_settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        policy_settings_merge.apply_patch(existing_settings, patch, expected_policy=meta.slug)
        settings_path.write_text(json.dumps(existing_settings, indent=2) + "\n", encoding="utf-8")
        settings_marker = meta.slug
        report.applied_files.append(SETTINGS_PATH)

    # Extras (optional).
    for pair in meta.files.get("extras") or []:
        src_rel, dst_rel = pair.split(":", 1)
        dst = project_dir / dst_rel
        if dst.exists():
            report.skipped_files.append(dst_rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(meta.root / src_rel, dst)
        if dst_rel.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        content_sha[dst_rel] = policy_state.sha256_file(dst)
        report.applied_files.append(dst_rel)

    # Record in state.
    now = datetime.now(timezone.utc).isoformat()
    state["applied_policies"] = [p for p in state["applied_policies"] if p["slug"] != meta.slug]
    state["applied_policies"].append({
        "slug": meta.slug,
        "version": meta.version,
        "applied_at": now,
        "content_sha": content_sha,
        "settings_marker": settings_marker,
    })
    state["applied_policies"].sort(key=lambda p: p["slug"])
    state["policy_history"].append({
        "action": "apply",
        "slug": meta.slug,
        "version": meta.version,
        "at": now,
        "source": source,
    })
    policy_state.write_state(project_dir, state)
    return report


def _find_applied(state: dict, slug: str) -> dict | None:
    for p in state["applied_policies"]:
        if p["slug"] == slug:
            return p
    return None
