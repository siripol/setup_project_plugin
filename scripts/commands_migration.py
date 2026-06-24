"""One-shot migration from flat sn-X-Y.md to grouped sn-X.md slash commands.

Idempotent (gated on state["commands_renamed_at"]). Edit-safe (sha-checks
each file against the OLD_FLAT_SHAS snapshot captured before deletion in
Tasks 1-3; --force bypasses).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import policy_state


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
GROUPED_TEMPLATE_DIR = PLUGIN_ROOT / "skills" / "sn-setup" / "templates" / "claude" / "commands"
GROUPED_FILES = ("sn-sprint.md", "sn-req.md", "sn-knowledge.md")


FLAT_TO_GROUP: dict[str, tuple[str, str]] = {
    "sn-sprint-new":        ("sn-sprint",    "new"),
    "sn-sprint-add":        ("sn-sprint",    "add"),
    "sn-sprint-run":        ("sn-sprint",    "run"),
    "sn-sprint-status":     ("sn-sprint",    "status"),
    "sn-sprint-done":       ("sn-sprint",    "done"),
    "sn-sprint-remove":     ("sn-sprint",    "remove"),
    "sn-req-new":           ("sn-req",       "new"),
    "sn-req-import":        ("sn-req",       "import"),
    "sn-req-replay":        ("sn-req",       "replay"),
    "sn-req-resume":        ("sn-req",       "resume"),
    "sn-req-rollback":      ("sn-req",       "rollback"),
    "sn-knowledge-check":   ("sn-knowledge", "check"),
    "sn-knowledge-update":  ("sn-knowledge", "update"),
    "sn-knowledge-promote": ("sn-knowledge", "promote"),
    "sn-knowledge-demote":  ("sn-knowledge", "demote"),
}

RETIRED: set[str] = {"sn-knowledge-tech-matrix"}

# SHA-256 snapshots of the flat files captured BEFORE they were deleted in
# Tasks 1-3.  Used instead of re-reading the (now-absent) plugin templates to
# determine whether a user has edited their local copy.
OLD_FLAT_SHAS: dict[str, str] = {
    "sn-knowledge-check":    "7c42e58e9e6d29de08c51b15e3c1a87887738609c68ccbc82b8374a02cc5eb2a",
    "sn-knowledge-demote":   "044205bf260c263bf0af9076c9b96acaaadf368220523170a161f329e31f6815",
    "sn-knowledge-promote":  "825559efd7e1de88b80cfba1d69c34ecaca72c9cfc4e6764fab5f23732a02927",
    "sn-knowledge-tech-matrix": "8a67dc26d5399fb531c5cd17801730c66da87f96e5f823d581fd6eba4e47ff6f",
    "sn-knowledge-update":   "06e0a46b5c49c7cdb3b2aaa52b3351dc26fdbb02540ea97946bfc4bae416d98a",
    "sn-req-import":         "d8f975e2b28c6fc866f761d9a09f37022535880b42db64262d73e6f02cc671a4",
    "sn-req-new":            "2f38d8c0d823f707fc93fedc08366551e0436bb327183893524a51c1e8c995f8",
    "sn-req-replay":         "db6ca1b1bd5d487f8b5393f33c3eb030780f04a2ea1fa0c8342fdfd3a3ef8590",
    "sn-req-resume":         "d896ffafac8b755cd8efb35c91437c4c1104314ab226add5b7c318531894777f",
    "sn-req-rollback":       "8430530995cbb59bf55e260dc5dfce96513f8efd055b565b80c24403033aee73",
    "sn-sprint-add":         "e2d189977c815bd6c39ed98c0f974bffb30ec3a35be64b0e972d96d45e23c82b",
    "sn-sprint-done":        "c45941334dafb3d4732b89b8104828b2b5de347df24d967a67fb36c8a6792d07",
    "sn-sprint-new":         "dd604badf0ad42db38d62ec8a579df50126ca185858a237e5846d07efa17ab92",
    "sn-sprint-remove":      "0ef50a6545b20cabb2bbd61997a1c8d9bb3dd8b2655cad85934bd10ed4cc1ce6",
    "sn-sprint-run":         "abd2de1551bd012ee1bc27058ee436a762f15c60a460a8efcf611eb8243f15e7",
    "sn-sprint-status":      "e9d01f8ae65e199e8bc15ceb3a1195b0e67a1b5b26924d5da6f69668ece7a4e2",
}


@dataclass
class MigrationReport:
    from_flat: list[str] = field(default_factory=list)
    to_grouped: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "from_flat": list(self.from_flat),
            "to_grouped": list(self.to_grouped),
            "skipped": list(self.skipped),
            "retired": list(self.retired),
        }


def run(project_dir: Path, *, force: bool = False, dry_run: bool = False) -> MigrationReport:
    """Rename flat commands → grouped commands. Mutates state on success."""
    state = policy_state.read_state(project_dir)
    if state.get("commands_renamed_at"):
        return MigrationReport()

    cmd_dir = project_dir / ".claude" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)

    report = MigrationReport()

    # 1. Plan: scan each flat slug.
    delete_paths: list[Path] = []
    for slug in FLAT_TO_GROUP:
        flat_path = cmd_dir / f"{slug}.md"
        if not flat_path.exists():
            continue
        expected = OLD_FLAT_SHAS.get(slug)
        if expected is None:
            # Slug not in our snapshot — treat as edited.
            pass
        else:
            actual = policy_state.sha256_file(flat_path)
            if actual == expected:
                delete_paths.append(flat_path)
                report.from_flat.append(slug)
                continue
        # Sha mismatched or no snapshot → treat as edited.
        if force:
            delete_paths.append(flat_path)
            report.from_flat.append(slug)
        else:
            report.skipped.append(str(flat_path.relative_to(project_dir)))

    # 2. Plan: scan retired slugs.
    for slug in sorted(RETIRED):
        retired_path = cmd_dir / f"{slug}.md"
        if not retired_path.exists():
            continue
        expected = OLD_FLAT_SHAS.get(slug)
        if expected is None:
            is_edited = True
        else:
            actual = policy_state.sha256_file(retired_path)
            is_edited = (actual != expected)
        if is_edited and not force:
            report.skipped.append(str(retired_path.relative_to(project_dir)))
        else:
            delete_paths.append(retired_path)
            report.retired.append(slug)

    # 3. Plan: which grouped files to write.
    grouped_to_write: list[Path] = []
    for fname in GROUPED_FILES:
        src = GROUPED_TEMPLATE_DIR / fname
        dst = cmd_dir / fname
        if dst.exists():
            # Preserve any user-created grouped file unconditionally.
            continue
        if not src.exists():
            continue
        grouped_to_write.append(dst)
        report.to_grouped.append(dst.stem)

    # 4. Execute (skip on dry-run).
    if dry_run:
        return report

    for path in delete_paths:
        path.unlink()

    for dst in grouped_to_write:
        shutil.copyfile(GROUPED_TEMPLATE_DIR / dst.name, dst)

    # 5. State update.
    now = datetime.now(timezone.utc).isoformat()
    state["commands_renamed_at"] = now
    state["commands_migration"] = report.to_dict()
    policy_state.write_state(project_dir, state)

    return report
