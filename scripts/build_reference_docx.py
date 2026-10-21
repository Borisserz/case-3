#!/usr/bin/env python3
"""Rebuild assets/docx/reference.docx for Liber (D1 + D8).

Liberation Serif, A4-ish margins (~2.2cm), heading rhythm, footer page #.
Run from repo root: python3 scripts/build_reference_docx.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "docx" / "reference.docx"

FONT = "Liberation Serif"
FONT_FALLBACK_NOTE = "DejaVu Serif / Liberation Serif — not Times"
# Match PDF geometry (tex_preamble A4 margin=2.2cm).
MARGIN_CM = 2.2


def _set_rfonts(style, font_name: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    rpr = style.element.get_or_add_rPr()
    for child in list(rpr):
        if child.tag == qn("w:rFonts"):
            rpr.remove(child)
    rfonts = OxmlElement("w:rFonts")
    rfonts.set(qn("w:ascii"), font_name)
    rfonts.set(qn("w:hAnsi"), font_name)
    rfonts.set(qn("w:cs"), font_name)
    rpr.insert(0, rfonts)


def _set_spacing(style, *, before_pt: float = 0, after_pt: float = 0, line: float | None = None) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    ppr = style.element.get_or_add_pPr()
    for child in list(ppr):
        if child.tag == qn("w:spacing"):
            ppr.remove(child)
    spacing = OxmlElement("w:spacing")
    # 1 pt = 20 twips
    spacing.set(qn("w:before"), str(int(before_pt * 20)))
    spacing.set(qn("w:after"), str(int(after_pt * 20)))
    if line is not None:
        # lineRule auto; line in twips (240 = single)
        spacing.set(qn("w:line"), str(int(240 * line)))
        spacing.set(qn("w:lineRule"), "auto")
    ppr.append(spacing)


def _add_page_field(paragraph) -> None:
    """Insert PAGE field into a paragraph (footer)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    run = paragraph.add_run()
    r = run._r

    def _fld(kind: str, instr: str | None = None) -> None:
        if kind in {"begin", "separate", "end"}:
            node = OxmlElement("w:fldChar")
            node.set(qn("w:fldCharType"), kind)
            r.append(node)
        elif kind == "instr" and instr:
            node = OxmlElement("w:instrText")
            node.set(qn("xml:space"), "preserve")
            node.text = instr
            r.append(node)

    _fld("begin")
    _fld("instr", " PAGE ")
    _fld("separate")
    # placeholder text shown until Word updates fields
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    _fld("end")


def main() -> int:
    try:
        from docx import Document
        from docx.enum.style import WD_STYLE_TYPE
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Cm, Pt, RGBColor
    except ImportError:
        print("pip install python-docx", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    def set_font(style, size_pt: float | None = None, *, italic=False, bold=False):
        style.font.name = FONT
        style.font.italic = italic
        style.font.bold = bold
        if size_pt is not None:
            style.font.size = Pt(size_pt)
        _set_rfonts(style, FONT)

    # Page setup ≈ PDF
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(MARGIN_CM)
        section.bottom_margin = Cm(MARGIN_CM)
        section.left_margin = Cm(MARGIN_CM)
        section.right_margin = Cm(MARGIN_CM)
        section.header_distance = Cm(1.0)
        section.footer_distance = Cm(1.0)

    # Base body
    normal = doc.styles["Normal"]
    set_font(normal, 12)
    _set_spacing(normal, before_pt=0, after_pt=6, line=1.15)

    for name, size, bold, before, after in (
        ("Title", 18, True, 0, 10),
        ("Heading 1", 14, True, 14, 6),
        ("Heading 2", 13, True, 12, 4),
    ):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        set_font(st, size, bold=bold)
        _set_spacing(st, before_pt=before, after_pt=after)

    try:
        h3 = doc.styles["Heading 3"]
    except KeyError:
        h3 = doc.styles.add_style("Heading 3", WD_STYLE_TYPE.PARAGRAPH)
        h3.base_style = doc.styles["Heading 2"]
    set_font(h3, 12, bold=True)
    _set_spacing(h3, before_pt=10, after_pt=4)

    try:
        quote = doc.styles["Quote"]
    except KeyError:
        quote = doc.styles.add_style("Quote", WD_STYLE_TYPE.PARAGRAPH)
        quote.base_style = doc.styles["Normal"]
    set_font(quote, 11, italic=True)
    quote.font.color.rgb = RGBColor(0x2E, 0x42, 0x08)  # vivid atelier

    for name in ("List Bullet", "List Number"):
        try:
            st = doc.styles[name]
        except KeyError:
            st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = doc.styles["Normal"]
        set_font(st, 12)
        _set_spacing(st, before_pt=0, after_pt=2)

    # D8: thin header rule feel + footer page number (≈ fancyhdr)
    section = doc.sections[0]
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = hp.add_run("")  # keep header present for pandoc
    run.font.size = Pt(9)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x6A, 0x71, 0x60)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _add_page_field(fp)

    p = doc.add_paragraph("Liber reference — " + FONT_FALLBACK_NOTE)
    p.style = doc.styles["Normal"]

    doc.save(str(OUT))
    check = Document(str(OUT))
    name = check.styles["Normal"].font.name
    print(f"wrote {OUT} Normal.font={name} margin_cm={MARGIN_CM}")
    assert name == FONT, name
    assert abs(check.sections[0].top_margin.cm - MARGIN_CM) < 0.05
    for need in ("Heading 3", "Quote", "List Bullet", "List Number"):
        _ = check.styles[need]
        print(f"  ok {need}")
    footer_xml = check.sections[0].footer._element.xml
    assert "fldChar" in footer_xml or "PAGE" in footer_xml
    print("  ok footer PAGE field")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
