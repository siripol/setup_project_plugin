"""Tests for platform-marketplace producer side — REQ-MKT-002 Phase 1 (B3.1)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / "platform-marketplace"
VALIDATOR = REPO_ROOT / "scripts" / "validate_marketplace.py"


def _run_validator(marketplace_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--marketplace-dir", str(marketplace_dir)],
        capture_output=True,
        text=True,
    )


def test_b31_phase1_marketplace_root_layout():
    """Phase 1 layout: catalog + 2 schemas + plugins dir + 3 docs + README."""
    assert (MARKETPLACE / ".claude-plugin" / "marketplace.json").is_file()
    assert (MARKETPLACE / ".claude-plugin" / "marketplace.schema.json").is_file()
    assert (MARKETPLACE / ".claude-plugin" / "plugin.schema.json").is_file()
    assert (MARKETPLACE / "README.md").is_file()
    assert (MARKETPLACE / "plugins").is_dir()
    for doc in ("PROMOTION.md", "VERSIONING.md", "RELEASE.md"):
        assert (MARKETPLACE / "docs" / doc).is_file(), f"missing docs/{doc}"


def test_b31_phase1_marketplace_json_parses_and_matches_schema():
    """The shipped catalog parses cleanly and validates against its own schema."""
    catalog = json.loads((MARKETPLACE / ".claude-plugin" / "marketplace.json").read_text())
    schema = json.loads((MARKETPLACE / ".claude-plugin" / "marketplace.schema.json").read_text())
    assert catalog["schema_version"] == "1.0"
    assert catalog["marketplace"]["name"] == "sn-platform-marketplace"
    assert isinstance(catalog["plugins"], list)
    jsonschema.Draft202012Validator(schema).validate(catalog)


def test_b31_phase1_marketplace_schema_self_validates():
    """marketplace.schema.json + plugin.schema.json are themselves valid Draft 2020-12 schemas."""
    for name in ("marketplace.schema.json", "plugin.schema.json"):
        schema = json.loads((MARKETPLACE / ".claude-plugin" / name).read_text())
        jsonschema.Draft202012Validator.check_schema(schema)


def test_b31_phase1_validator_cli_succeeds_on_empty_catalog():
    """validate_marketplace.py exits 0 against the shipped empty catalog."""
    result = _run_validator(MARKETPLACE)
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout


def test_b31_phase1_validator_cli_fails_on_bad_json(tmp_path: Path):
    """Bad JSON → exit 1 with schema-violation message on stderr."""
    fake = tmp_path / "platform-marketplace"
    shutil.copytree(MARKETPLACE, fake)
    (fake / ".claude-plugin" / "marketplace.json").write_text("{ not valid json")
    result = _run_validator(fake)
    assert result.returncode == 1
    assert "invalid JSON" in result.stderr


def test_b31_phase1_validator_cli_fails_on_schema_violation(tmp_path: Path):
    """Catalog with a required field missing → exit 1."""
    fake = tmp_path / "platform-marketplace"
    shutil.copytree(MARKETPLACE, fake)
    catalog = json.loads((fake / ".claude-plugin" / "marketplace.json").read_text())
    catalog["marketplace"].pop("owners")  # required field
    (fake / ".claude-plugin" / "marketplace.json").write_text(json.dumps(catalog))
    result = _run_validator(fake)
    assert result.returncode == 1
    assert "schema violation" in result.stderr.lower() or "required" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Phase 2 — core-guardrails plugin lifted as first canonical plugin.
# ---------------------------------------------------------------------------

CORE_GUARDRAILS = MARKETPLACE / "plugins" / "core-guardrails"
SCAFFOLD_HOOKS = REPO_ROOT / "skills" / "sn-setup" / "templates" / "claude" / "hooks"
SCAFFOLD_SETTINGS = REPO_ROOT / "skills" / "sn-setup" / "templates" / "claude" / "settings.json"
BOOTSTRAP_HOOK = (
    REPO_ROOT / "skills" / "sn-setup" / "templates" / "marketplace-consumer"
    / "default" / "claude" / "hooks" / "marketplace-bootstrap.sh"
)

CORE_GUARDRAILS_HOOK_FILES = [
    "audit.sh", "audit.py", "audit.ts",
    "chokepoint-gate.sh", "chokepoint-gate.py", "chokepoint-gate.ts",
    "rate-limit.sh", "rate-limit.py", "rate-limit.ts",
]


def test_b31_phase2_core_guardrails_manifest_valid_and_in_catalog():
    """Plugin manifest parses, validates against plugin.schema.json, and the
    catalog entry mirrors its version exactly."""
    manifest = json.loads((CORE_GUARDRAILS / ".claude-plugin" / "plugin.json").read_text())
    schema = json.loads((MARKETPLACE / ".claude-plugin" / "plugin.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(manifest)
    assert manifest["name"] == "core-guardrails"
    assert manifest["type"] == "mandatory"

    catalog = json.loads((MARKETPLACE / ".claude-plugin" / "marketplace.json").read_text())
    entries = [p for p in catalog["plugins"] if p["name"] == "core-guardrails"]
    assert len(entries) == 1
    assert entries[0]["version"] == manifest["version"]
    assert entries[0]["source"] == "./plugins/core-guardrails"


def test_b31_phase2_core_guardrails_self_contained():
    """Validator's self-containment pass (full validate_all) succeeds with the
    plugin landed. Catches `../` escapes + cross-plugin symlinks per ADR-MKT-003."""
    result = _run_validator(MARKETPLACE)
    assert result.returncode == 0, f"stderr={result.stderr!r}"


def test_b31_phase2_core_guardrails_settings_patch_parses():
    """The settings patch parses + has the required top-level keys."""
    patch = json.loads(
        (CORE_GUARDRAILS / "settings" / "settings.patch.json").read_text()
    )
    assert "permissions" in patch
    assert "allow" in patch["permissions"]
    assert "deny" in patch["permissions"]
    assert "hooks" in patch
    # Mandatory deny patterns kept in lockstep with scaffold.
    deny_set = set(patch["permissions"]["deny"])
    for sensitive in ("Write(~/.ssh/**)", "Edit(~/.ssh/**)", "Write(**/.env)"):
        assert sensitive in deny_set, f"plugin settings.patch.json missing deny rule {sensitive!r}"


def test_b31_phase2_core_guardrails_hooks_match_scaffold():
    """ADR-MKT-002 dual-source: scaffold hook files MUST be byte-identical to
    the plugin's copies. CI guard against drift until Phase 6 cutover."""
    for fname in CORE_GUARDRAILS_HOOK_FILES:
        scaffold = (SCAFFOLD_HOOKS / fname).read_bytes()
        plugin = (CORE_GUARDRAILS / "hooks" / fname).read_bytes()
        assert scaffold == plugin, f"hook drift detected: {fname}"


def test_b31_phase2_core_guardrails_settings_patch_matches_scaffold():
    """ADR-MKT-002 + REQ-MKT-002 D-8: plugin settings.patch.json is
    authoritative for permissions + hooks; the scaffold's settings.json must
    embed identical permissions.{allow,deny} + hooks subtrees."""
    plugin_patch = json.loads(
        (CORE_GUARDRAILS / "settings" / "settings.patch.json").read_text()
    )
    scaffold_settings = json.loads(SCAFFOLD_SETTINGS.read_text())
    assert plugin_patch["permissions"]["allow"] == scaffold_settings["permissions"]["allow"]
    assert plugin_patch["permissions"]["deny"] == scaffold_settings["permissions"]["deny"]
    assert plugin_patch["hooks"] == scaffold_settings["hooks"]


def test_b31_phase2_consumer_bootstrap_hook_self_deactivates(tmp_path: Path):
    """B2.3 marketplace-bootstrap hook exits silently the moment
    `.claude/plugins/core-guardrails/` exists. Validates the day-1 silent-failure
    window closes the moment Phase 2 lands in a consumer."""
    sandbox = tmp_path / "consumer"
    (sandbox / ".claude" / "plugins" / "core-guardrails").mkdir(parents=True)
    result = subprocess.run(
        ["bash", str(BOOTSTRAP_HOOK)],
        cwd=sandbox, capture_output=True, text=True,
        env={
            "marketplace_source": "./platform-marketplace",
            "PATH": "/usr/bin:/bin",
            "HOME": str(sandbox),
        },
    )
    assert result.returncode == 0
    assert result.stdout == "", f"unexpected stdout: {result.stdout!r}"
    assert result.stderr == "", f"unexpected stderr: {result.stderr!r}"


def test_b31_phase2_full_marketplace_validates_with_one_plugin():
    """End-to-end: validator passes against a marketplace containing
    one real plugin (catalog parses, manifest parses, self-contained,
    no dep-graph issues, version-sync OK)."""
    result = _run_validator(MARKETPLACE)
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "OK" in result.stdout
