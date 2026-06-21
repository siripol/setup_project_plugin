"""DOCX → RawReq importer (requires python-docx)."""
from __future__ import annotations

from pathlib import Path

from . import RawReq


def parse(path: Path) -> RawReq:
    try:
        from docx import Document  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "python-docx not installed. `pip install python-docx` to use the docx importer."
        ) from e

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    title = paragraphs[0] if paragraphs else path.stem
    body = "\n".join(paragraphs)

    acceptance: list[str] = []
    capture = False
    for p in paragraphs:
        if p.lower().startswith("acceptance"):
            capture = True
            continue
        if capture and (p.startswith(("-", "*", "•")) or (p[:2].endswith(".") and p[:1].isdigit())):
            acceptance.append(p.lstrip("-*•0123456789. ").strip())
        elif capture and not p.strip():
            break

    return RawReq(title=title.strip(), body=body, acceptance=acceptance, source=str(path))
