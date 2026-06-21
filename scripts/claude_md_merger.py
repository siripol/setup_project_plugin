"""Section-aware merge for CLAUDE*.md files.

Used by `sn-init --upgrade` (and --rename-ns) so existing project memory keeps
user edits while still picking up template-managed sections that have been added
or refreshed.

Parsing model
-------------
- H1 (`# ...`) is treated as the file title. Existing H1 wins.
- H2 (`## ...`) lines delimit sections. A section's body runs until the next H2
  or end of file. Content before the first H2 (the "preamble") is kept from
  existing as-is; if existing has no preamble, the template's preamble is used.
- H3+ headings live inside whatever H2 section contains them; we do not merge
  at that granularity.

Merge rules (existing vs template)
----------------------------------
- Section in both → KEEP existing content verbatim.
- Section in template only → APPEND (in template order) after existing tail.
- Section in `overwrite_sections` set → OVERWRITE with template content (used
  for template-managed sections like `## Tracking`).
- Section in existing only → KEEP.

The function is pure: returns the merged string. Caller handles backup + write.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class _Section:
    heading: str          # full line including "## "
    title: str            # normalized "Tracking" (no leading '##', stripped)
    body: list[str]       # lines after heading until next H2 (no trailing newline)


def _split_sections(text: str) -> tuple[list[str], list[_Section]]:
    lines = text.splitlines()
    preamble: list[str] = []
    sections: list[_Section] = []

    current: _Section | None = None
    body: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## ") and not line.startswith("###"):
            if current is not None:
                sections.append(_Section(current.heading, current.title, body))
            elif not in_section:
                # preamble done
                pass
            in_section = True
            title = line[3:].strip()
            current = _Section(heading=line, title=title, body=[])
            body = []
            continue
        if not in_section:
            preamble.append(line)
        else:
            body.append(line)

    if current is not None:
        sections.append(_Section(current.heading, current.title, body))

    return preamble, sections


def _strip_trailing_blank(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and out[-1].strip() == "":
        out.pop()
    return out


def merge(
    existing: str,
    template: str,
    *,
    overwrite_sections: Iterable[str] = (),
) -> str:
    """Section-aware merge of two CLAUDE*.md texts.

    `overwrite_sections` is a case-sensitive set of H2 titles (e.g. "Tracking")
    that should always take the template's content when present.
    """
    overwrite = {s.strip() for s in overwrite_sections}

    ex_preamble, ex_sections = _split_sections(existing)
    tp_preamble, tp_sections = _split_sections(template)

    # Preamble: keep existing if it has any non-blank content; else template's.
    preamble = ex_preamble if any(line.strip() for line in ex_preamble) else tp_preamble

    ex_by_title = {s.title: s for s in ex_sections}
    tp_by_title = {s.title: s for s in tp_sections}

    merged: list[_Section] = []
    used_template_titles: set[str] = set()

    # First pass: walk existing sections in order, applying overwrites.
    for sec in ex_sections:
        if sec.title in overwrite and sec.title in tp_by_title:
            merged.append(tp_by_title[sec.title])
            used_template_titles.add(sec.title)
        else:
            merged.append(sec)
            if sec.title in tp_by_title:
                used_template_titles.add(sec.title)

    # Second pass: append template sections not yet emitted, in template order.
    for sec in tp_sections:
        if sec.title in used_template_titles:
            continue
        merged.append(sec)
        used_template_titles.add(sec.title)

    out: list[str] = []
    out.extend(_strip_trailing_blank(list(preamble)))
    if out:
        out.append("")
    for sec in merged:
        out.append(sec.heading)
        out.extend(_strip_trailing_blank(sec.body))
        out.append("")

    # Collapse run of trailing blanks to a single trailing newline.
    while len(out) > 1 and out[-1] == "" and out[-2] == "":
        out.pop()
    return "\n".join(out).rstrip() + "\n"
