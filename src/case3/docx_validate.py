"""Validate DOCX is a readable OOXML package (Word-safe gate)."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

log = logging.getLogger("case3.docx_validate")


def docx_package_ok(path: Path | str) -> bool:
    """True if path is a zip with word/document.xml and testzip clean."""
    p = Path(path)
    if not p.is_file() or p.stat().st_size < 64:
        return False
    if p.read_bytes()[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(p) as zf:
            names = set(zf.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                return False
            if zf.testzip() is not None:
                return False
    except (OSError, zipfile.BadZipFile):
        return False
    try:
        from docx import Document  # type: ignore

        Document(str(p))
    except Exception as exc:  # noqa: BLE001
        log.debug("python-docx open failed: %s", exc)
        return False
    return True
