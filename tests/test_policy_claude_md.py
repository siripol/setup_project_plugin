"""Tests for scripts/policy_claude_md.py — ## Policies table mgmt."""
from __future__ import annotations

import policy_claude_md as pmd  # type: ignore


def test_upsert_creates_section_when_absent():
    src = "# demo\n\n## Lang\n\ngo\n"
    out, _sha = pmd.upsert_row(
        src,
        slug="memory-ordinary",
        row="| security | memory-ordinary | `.claude/docs/policies/memory-ordinary.md` | 1.0.0 |",
    )
    assert "## Policies" in out
    assert "| security | memory-ordinary |" in out


def test_upsert_inserts_under_existing_section():
    src = (
        "# demo\n\n## Policies\n\n"
        "Service-level policies in effect. Read the linked doc on demand.\n\n"
        "| Category | Slug | Reference | Version |\n"
        "|---|---|---|---|\n"
        "| security | secret-scan | `.claude/docs/policies/secret-scan.md` | 1.3.0 |\n"
    )
    out, _sha = pmd.upsert_row(
        src, "memory-ordinary",
        "| security | memory-ordinary | `.claude/docs/policies/memory-ordinary.md` | 1.0.0 |",
    )
    # Both rows present, both under the header.
    assert "secret-scan" in out
    assert "memory-ordinary" in out
    assert out.count("## Policies") == 1


def test_upsert_replaces_existing_row_for_same_slug():
    src = (
        "## Policies\n\n"
        "| Category | Slug | Reference | Version |\n"
        "|---|---|---|---|\n"
        "| security | memory-ordinary | old | 1.0.0 |\n"
    )
    out, _sha = pmd.upsert_row(
        src, "memory-ordinary",
        "| security | memory-ordinary | new | 1.1.0 |",
    )
    assert "old" not in out
    assert "new" in out
    # Still exactly one row for that slug.
    assert out.count("| memory-ordinary |") == 1


def test_strip_removes_only_matching_row():
    src = (
        "## Policies\n\n"
        "| Category | Slug | Reference | Version |\n"
        "|---|---|---|---|\n"
        "| security | memory-ordinary | x | 1.0.0 |\n"
        "| security | secret-scan | y | 1.3.0 |\n"
    )
    out = pmd.strip_row(src, "memory-ordinary")
    assert "memory-ordinary" not in out
    assert "secret-scan" in out


def test_strip_noop_when_slug_absent():
    src = "## Policies\n\n| Category | Slug | Reference | Version |\n|---|---|---|---|\n"
    out = pmd.strip_row(src, "memory-ordinary")
    assert out == src


def test_upsert_returns_sha_of_row():
    out, sha = pmd.upsert_row(
        "",
        "memory-ordinary",
        "| security | memory-ordinary | x | 1.0.0 |",
    )
    # sha is hex string, 64 chars
    assert len(sha) == 64
    int(sha, 16)  # parseable
