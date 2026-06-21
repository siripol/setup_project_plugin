"""Convert source documents (md/txt/json/docx/pdf) into REQ-NNN.md scaffolds.

Each importer exposes `parse(path: Path) -> RawReq` returning a normalized record.
`req_import.write_req(...)` consumes RawReq and writes the REQ file.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawReq:
    """Normalized REQ extracted from a source document."""

    title: str
    body: str
    acceptance: list[str] = field(default_factory=list)
    priority: str = "medium"
    source: str = ""
    notes: str = ""
