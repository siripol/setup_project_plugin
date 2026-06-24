"""Manage the `## Policies` table inside CLAUDE.md.

Apply/upgrade inserts or replaces a row keyed by the slug column. Remove
strips the row. Section is auto-created with the documented header text
when absent.
"""
from __future__ import annotations

import re

import policy_state

SECTION_HEADER = "## Policies"
SECTION_INTRO = (
    "Service-level policies in effect. Read the linked doc on demand.\n\n"
    "| Category | Slug | Reference | Version |\n"
    "|---|---|---|---|"
)


def upsert_row(claude_md: str, slug: str, row: str) -> tuple[str, str]:
    """Insert (or replace by slug) `row` under the `## Policies` table.

    Returns the new file contents and the sha256 of the row (for state
    drift-detection of the virtual `CLAUDE.md#row:<slug>` path).
    """
    row = row.rstrip("\n")
    sha = policy_state.sha256_str(row)

    if SECTION_HEADER not in claude_md:
        # Append section to end of file.
        suffix = "" if claude_md.endswith("\n") else "\n"
        new = claude_md + f"{suffix}\n{SECTION_HEADER}\n\n{SECTION_INTRO}\n{row}\n"
        return new, sha

    # Section exists. Find and replace existing row for this slug, else
    # insert after the table's header rule line (`|---|---|...`).
    pattern = re.compile(
        r"^\|\s*[^|]+\s*\|\s*" + re.escape(slug) + r"\s*\|.*$",
        re.MULTILINE,
    )
    if pattern.search(claude_md):
        new = pattern.sub(row, claude_md)
        return new, sha

    # Insert after the header rule line.
    insert_re = re.compile(
        r"(##\s+Policies\b.*?\|---\|[-|]*\|\s*\n)", re.DOTALL,
    )
    m = insert_re.search(claude_md)
    if not m:
        # Section exists but no table yet; append the intro + row.
        new = claude_md.rstrip("\n") + f"\n\n{SECTION_INTRO}\n{row}\n"
        return new, sha
    new = claude_md[: m.end()] + row + "\n" + claude_md[m.end() :]
    return new, sha


def strip_row(claude_md: str, slug: str) -> str:
    pattern = re.compile(
        r"^\|\s*[^|]+\s*\|\s*" + re.escape(slug) + r"\s*\|.*\n",
        re.MULTILINE,
    )
    return pattern.sub("", claude_md)
