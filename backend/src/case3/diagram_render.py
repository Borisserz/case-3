"""Mermaid renderability checks (syntax / structure) before Liber shows a diagram."""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path

log = logging.getLogger("case3.diagram_render")

# Shape openers that Mermaid treats as NODE_DSTART when no ASCII id precedes them.
_SHAPE_OPEN = re.compile(r"(?:\(\(|\[\[|\{\{|\(\[|\[\(|\[|\{|\()")
_FLOW_HDR = re.compile(r"^\s*(?:flowchart|graph)\b", re.IGNORECASE)
_META = re.compile(
    r"^\s*(?:%%|classDef\b|class\s|style\s|linkStyle\b|subgraph\b|end\b|"
    r"direction\b|click\b|flowchart\b|graph\b)",
    re.IGNORECASE,
)
_LABELED_NODE = re.compile(
    r"^[A-Za-z_][\w-]*\s*(?:@\{|\[\(|\(\[|\(\(|\[\[|\{\{|\[|\{|\(|>)"
)
_EDGE_ONLY = re.compile(
    r"^\s*[A-Za-z_][\w-]*\s*(?:-->|---|-\.->|==>|~~~|--o|o--|--x)"
)


def mermaid_structurally_ok(mermaid: str) -> bool:
    """Reject common LLM breakage that yields Mermaid ``NODE_DSTART`` / parse errors.

    Does not launch a browser. Fail-open for non-flowchart diagrams.
    """
    text = (mermaid or "").strip()
    if not text:
        return False
    lines = text.splitlines()
    first = ""
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith("%%") and not s.startswith("---"):
            first = s
            break
    if not _FLOW_HDR.match(first):
        return True
    for ln in lines:
        stripped = ln.strip()
        if not stripped or _META.match(stripped) or _EDGE_ONLY.match(stripped):
            continue
        if _LABELED_NODE.match(stripped):
            continue
        # Bare shape or prose-then-shape on a flowchart line → parser NODE_DSTART.
        if _SHAPE_OPEN.search(stripped):
            return False
        # Cyrillic / prose where a node id should be, then a shape later on the line.
        if re.search(r"[^\x00-\x7f].*(?:\(|\[|\{)", stripped):
            return False
    return True


def mermaid_syntax_ok(mermaid: str, *, work_dir: Path | None = None) -> bool:
    """True when Mermaid is structurally sound and (if possible) renders without error.

    Fail-open when Playwright / Chromium is unavailable so desk still returns a draft.
    """
    if not mermaid_structurally_ok(mermaid):
        return False
    try:
        from case3.diagram_svg import DiagramSvgError, render_mermaid_svg_string
    except ImportError:
        log.debug("diagram_svg unavailable — structural check only")
        return True
    work = work_dir
    tmp: tempfile.TemporaryDirectory[str] | None = None
    try:
        if work is None:
            tmp = tempfile.TemporaryDirectory(prefix="case3_mmd_check_")
            work = Path(tmp.name)
        render_mermaid_svg_string(mermaid=mermaid, work_dir=work)
        return True
    except DiagramSvgError as exc:
        log.info("mermaid syntax check failed: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001 — Playwright/Chromium missing or flake
        log.warning("mermaid render check unavailable (%s); accepting structural OK", exc)
        return True
    finally:
        if tmp is not None:
            tmp.cleanup()
