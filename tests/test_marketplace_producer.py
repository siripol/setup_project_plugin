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
