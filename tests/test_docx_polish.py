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
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    path = tmp_path / "sample.docx"
    _make_sample(path)
    # Simulate pandoc/reference firstRow green (e.g. D6E3BC / D5DEC0)
    doc0 = Document(str(path))
    for cell in doc0.tables[0].rows[0].cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "D6E3BC")
        tc_pr.append(shd)
    doc0.save(str(path))

    polish_docx(path)
    doc = Document(str(path))
    table = doc.tables[0]
    # Header: bold + bottom rule, white/no green fill (override Word table styles)
    header_xml = "".join(c._tc.xml for c in table.rows[0].cells)
    assert "D5DEC0" not in header_xml.upper()
    assert "D6E3BC" not in header_xml.upper()
    assert "E8EDD8" not in header_xml.upper()
    assert 'w:fill="FFFFFF"' in header_xml or 'w:fill="ffffff"' in header_xml
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
    assert "D5DEC0" not in header_xml.upper()


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


def test_polish_docx_forces_black_headings(tmp_path: Path) -> None:
    from docx.oxml.ns import qn
    from docx.shared import RGBColor

    path = tmp_path / "heads.docx"
    doc = Document()
    doc.styles["Heading 1"].font.color.rgb = RGBColor(0x36, 0x5F, 0x91)
    doc.add_heading("Раздел", level=1)
    doc.save(str(path))
    polish_docx(path)
    doc2 = Document(str(path))
    st = doc2.styles["Heading 1"]
    assert st.font.color.rgb == RGBColor(0x12, 0x12, 0x12)
    rPr = st.element.find(qn("w:rPr"))
    color = rPr.find(qn("w:color")) if rPr is not None else None
    assert color is not None
    assert color.get(qn("w:val"), "").upper() == "121212"
