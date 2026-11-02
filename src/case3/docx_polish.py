"""Post-pandoc DOCX polish (D5 tables, light chrome). Soft-fail friendly."""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger("case3.docx_polish")

_NUM = re.compile(
    r"^[-+]?(?:\d{1,3}(?:[ \u00a0]\d{3})*|\d+)(?:[.,]\d+)?%?$"
)

# Header cells: white fill (override pandoc/reference firstRow greens).
_HEADER_FILL = "FFFFFF"
_RULE_COLOR = "3F5210"  # readable olive ink on white
_BODY_RULE = "C5CDB0"
_INK = "121212"


def _cell_text(cell) -> str:  # noqa: ANN001
    return (cell.text or "").strip()


def _is_numeric(text: str) -> bool:
    t = (text or "").strip().replace("\u00a0", " ")
    if not t:
        return False
    compact = t.replace(" ", "")
    return bool(_NUM.match(compact))


def _ensure_runs_bold(cell) -> None:  # noqa: ANN001
    for p in cell.paragraphs:
        if p.runs:
            for run in p.runs:
                run.bold = True
            continue
        text = p.text or ""
        if not text:
            continue
        run = p.add_run(text)
        run.bold = True


def _qn(tag: str):
    from docx.oxml.ns import qn

    return qn(tag)


def _set_cell_shading(cell, fill_hex: str) -> None:  # noqa: ANN001
    from docx.oxml import OxmlElement

    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    for child in list(tc_pr):
        if child.tag == _qn("w:shd"):
            tc_pr.remove(child)
    shd = OxmlElement("w:shd")
    shd.set(_qn("w:val"), "clear")
    shd.set(_qn("w:color"), "auto")
    shd.set(_qn("w:fill"), fill_hex.upper())
    tc_pr.append(shd)


def _set_cell_margins(cell, *, dxa: int = 80) -> None:  # noqa: ANN001
    """Comfortable cell padding (dxa = twentieths of a point)."""
    from docx.oxml import OxmlElement

    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    for child in list(tc_pr):
        if child.tag == _qn("w:tcMar"):
            tc_pr.remove(child)
    mar = OxmlElement("w:tcMar")
    for edge in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{edge}")
        node.set(_qn("w:w"), str(dxa))
        node.set(_qn("w:type"), "dxa")
        mar.append(node)
    tc_pr.append(mar)


def _border(tag: str, *, sz: int, color: str, val: str = "single") -> object:
    from docx.oxml import OxmlElement

    el = OxmlElement(f"w:{tag}")
    el.set(_qn("w:val"), val)
    el.set(_qn("w:sz"), str(sz))  # eighths of a point
    el.set(_qn("w:space"), "0")
    el.set(_qn("w:color"), color)
    return el


def _apply_booktabs_table(table) -> None:  # noqa: ANN001
    """Full width + Liber grid: outer frame + row/column dividers (Word-visible)."""
    from docx.oxml import OxmlElement

    tbl = table._tbl
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)

    # Width ~100% of text
    for child in list(tbl_pr):
        if child.tag in {_qn("w:tblW"), _qn("w:tblBorders"), _qn("w:jc")}:
            tbl_pr.remove(child)
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(_qn("w:type"), "pct")
    tbl_w.set(_qn("w:w"), "5000")  # 5000 = 100%
    tbl_pr.append(tbl_w)
    jc = OxmlElement("w:jc")
    jc.set(_qn("w:val"), "center")
    tbl_pr.append(jc)

    borders = OxmlElement("w:tblBorders")
    # Outer frame + insideH/V so columns and rows read as a grid in Word.
    borders.append(_border("top", sz=12, color=_RULE_COLOR))
    borders.append(_border("left", sz=8, color=_BODY_RULE))
    borders.append(_border("bottom", sz=12, color=_RULE_COLOR))
    borders.append(_border("right", sz=8, color=_BODY_RULE))
    borders.append(_border("insideH", sz=6, color=_BODY_RULE))
    borders.append(_border("insideV", sz=6, color=_BODY_RULE))
    tbl_pr.append(borders)


def _style_header_row(row) -> None:  # noqa: ANN001
    for cell in row.cells:
        _ensure_runs_bold(cell)
        # Force white — Word table styles (reference.docx) tint firstRow green.
        _set_cell_shading(cell, _HEADER_FILL)
        _set_cell_margins(cell, dxa=90)
        # Slight bottom emphasis via cell bottom border
        from docx.oxml import OxmlElement

        tc_pr = cell._tc.get_or_add_tcPr()
        for child in list(tc_pr):
            if child.tag == _qn("w:tcBorders"):
                tc_pr.remove(child)
        tc_borders = OxmlElement("w:tcBorders")
        tc_borders.append(_border("bottom", sz=12, color=_RULE_COLOR))
        tc_pr.append(tc_borders)



def _force_black_headings(doc) -> None:  # noqa: ANN001
    """Title / Heading styles → black ink (reference.docx used theme blue)."""
    from docx.oxml import OxmlElement
    from docx.shared import RGBColor

    ink = RGBColor(0x12, 0x12, 0x12)
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        st.font.color.rgb = ink
        rpr = st.element.get_or_add_rPr()
        for child in list(rpr):
            if child.tag == _qn("w:color"):
                rpr.remove(child)
        color = OxmlElement("w:color")
        color.set(_qn("w:val"), _INK)
        rpr.append(color)
    # Also pin runs on heading paragraphs (pandoc may set theme color on runs).
    for p in doc.paragraphs:
        style_name = (p.style.name if p.style else "") or ""
        if style_name not in {"Title", "Heading 1", "Heading 2", "Heading 3"}:
            continue
        for run in p.runs:
            run.font.color.rgb = ink


def polish_docx(path: Path | str) -> Path:
    """Liber table look: white header, visible grid borders, numeric align."""
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError as exc:
        raise RuntimeError("python-docx required for DOCX polish") from exc

    path = Path(path)
    doc = Document(str(path))
    _force_black_headings(doc)
    for table in doc.tables:
        if not table.rows:
            continue
        _apply_booktabs_table(table)
        _style_header_row(table.rows[0])
        for row in table.rows[1:]:
            for cell in row.cells:
                _set_cell_margins(cell, dxa=80)
                if not _is_numeric(_cell_text(cell)):
                    continue
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.save(str(path))
    log.info("polished DOCX tables → %s", path)
    return path


def try_polish_docx(path: Path | str) -> bool:
    """Best-effort polish; never raise into render."""
    try:
        polish_docx(path)
        return True
    except Exception as exc:  # noqa: BLE001 — soft-fail
        log.warning("docx polish skipped: %s", exc)
        return False
