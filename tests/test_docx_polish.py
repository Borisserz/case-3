"""D5/D8: post-pandoc DOCX table + chrome polish."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("docx")

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402

from case3.docx_polish import polish_docx  # noqa: E402


def _make_sample(path: Path) -> None:
    doc = Document()
    doc.add_heading("Отчёт", level=1)
    table = doc.add_table(rows=3, cols=2)
    table.rows[0].cells[0].text = "Метрика"
    table.rows[0].cells[1].text = "Значение"
    table.rows[1].cells[0].text = "A"
    table.rows[1].cells[1].text = "12"
    table.rows[2].cells[0].text = "B"
    table.rows[2].cells[1].text = "28.5"
    doc.save(str(path))


def test_polish_docx_bolds_header_and_right_aligns_numbers(tmp_path: Path) -> None:
    path = tmp_path / "sample.docx"
    _make_sample(path)
    polish_docx(path)
    doc = Document(str(path))
    header = doc.tables[0].rows[0]
    assert any(run.bold for cell in header.cells for p in cell.paragraphs for run in p.runs)
    num_cell = doc.tables[0].rows[1].cells[1]
    assert num_cell.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT
    num_cell2 = doc.tables[0].rows[2].cells[1]
    assert num_cell2.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT


def test_polish_docx_header_fill_and_booktabs_borders(tmp_path: Path) -> None:
    path = tmp_path / "sample.docx"
    _make_sample(path)
    polish_docx(path)
    doc = Document(str(path))
    table = doc.tables[0]
    # Soft atelier mist fill on header
    header_xml = "".join(c._tc.xml for c in table.rows[0].cells)
    assert "D5DEC0" in header_xml.upper() or "E8EDD8" in header_xml.upper()
    assert "shd" in header_xml or "w:fill" in header_xml
    # Grid: outer + insideH + insideV so Word shows column/row dividers
    tbl_xml = table._tbl.xml
    assert "tblBorders" in tbl_xml
    assert "insideV" in tbl_xml
    assert "insideH" in tbl_xml
    # Verticals must be real lines (not nil/none)
    assert 'w:insideV w:val="nil"' not in tbl_xml
    assert 'w:insideV w:val="none"' not in tbl_xml
    assert 'w:val="single"' in tbl_xml
    # Full-ish width
    assert 'w:type="pct"' in tbl_xml or "tblW" in tbl_xml


def test_polish_docx_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "sample.docx"
    _make_sample(path)
    polish_docx(path)
    polish_docx(path)
    doc = Document(str(path))
    assert len(doc.tables) == 1
    assert doc.tables[0].rows[0].cells[0].text == "Метрика"
    header_xml = "".join(c._tc.xml for c in doc.tables[0].rows[0].cells)
    assert header_xml.upper().count("D5DEC0") + header_xml.upper().count("E8EDD8") >= 1


def test_reference_docx_has_liber_margins_and_header() -> None:
    root = Path(__file__).resolve().parents[1]
    ref = root / "assets" / "docx" / "reference.docx"
    assert ref.is_file(), "run scripts/build_reference_docx.py"
    doc = Document(str(ref))
    sec = doc.sections[0]
    # ~2.2cm = 793700 EMUs; allow small float noise
    assert abs(sec.top_margin.cm - 2.2) < 0.15
    assert abs(sec.left_margin.cm - 2.2) < 0.15
    header_text = "\n".join(p.text for p in sec.header.paragraphs)
    # Header may be empty visually but must exist / not linked blindly
    assert sec.header is not None
    footer_xml = sec.footer._element.xml
    assert "PAGE" in footer_xml or "fldChar" in footer_xml or "w:instrText" in footer_xml
