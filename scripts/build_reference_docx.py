#!/usr/bin/env python3
"""Rebuild assets/docx/reference.docx for Liber (D1): Liberation/DejaVu, not Times.

Creates Heading 3, Quote, List Bullet, List Number if missing.
Run from repo root: python3 scripts/build_reference_docx.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "docx" / "reference.docx"

# Prefer Liberation (Windows desk); DejaVu matches PDF preamble.
FONT = "Liberation Serif"
FONT_FALLBACK_NOTE = "DejaVu Serif / Liberation Serif — not Times"


def main() -> int:
    try:
        from docx import Document
        from docx.enum.style import WD_STYLE_TYPE
        from docx.shared import Pt, RGBColor
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
        # Force rFonts for Word East Asian / ASCII
        rpr = style.element.get_or_add_rPr()
        # remove existing rFonts
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        for child in list(rpr):
            if child.tag == qn("w:rFonts"):
                rpr.remove(child)
        rfonts = OxmlElement("w:rFonts")
        rfonts.set(qn("w:ascii"), FONT)
        rfonts.set(qn("w:hAnsi"), FONT)
        rfonts.set(qn("w:cs"), FONT)
        rpr.insert(0, rfonts)

    # Base
    set_font(doc.styles["Normal"], 12)
    for name, size, bold in (
        ("Title", 18, True),
        ("Heading 1", 14, True),
        ("Heading 2", 13, True),
    ):
        try:
            set_font(doc.styles[name], size, bold=bold)
        except KeyError:
            pass

    # Heading 3
    try:
        h3 = doc.styles["Heading 3"]
    except KeyError:
        h3 = doc.styles.add_style("Heading 3", WD_STYLE_TYPE.PARAGRAPH)
        h3.base_style = doc.styles["Heading 2"]
    set_font(h3, 12, bold=True)

    # Quote
    try:
        quote = doc.styles["Quote"]
    except KeyError:
        quote = doc.styles.add_style("Quote", WD_STYLE_TYPE.PARAGRAPH)
        quote.base_style = doc.styles["Normal"]
    set_font(quote, 11, italic=True)
    quote.font.color.rgb = RGBColor(0x3F, 0x52, 0x10)

    # Lists
    for name in ("List Bullet", "List Number"):
        try:
            st = doc.styles[name]
        except KeyError:
            st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = doc.styles["Normal"]
        set_font(st, 12)

    # Tiny body so pandoc has something
    p = doc.add_paragraph("Liber reference — " + FONT_FALLBACK_NOTE)
    p.style = doc.styles["Normal"]

    doc.save(str(OUT))
    # Verify
    check = Document(str(OUT))
    name = check.styles["Normal"].font.name
    print(f"wrote {OUT} Normal.font={name}")
    assert name == FONT, name
    for need in ("Heading 3", "Quote", "List Bullet", "List Number"):
        _ = check.styles[need]
        print(f"  ok {need}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
