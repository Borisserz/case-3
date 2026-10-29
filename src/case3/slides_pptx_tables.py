"""Native OOXML tables for Liber deck PPTX."""

from __future__ import annotations

from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


def add_native_table(
    slide,
    rows: list[list[str]],
    *,
    left,
    top,
    width,
    height,
    header_fill: RGBColor,
    header_ink: RGBColor,
    body_ink: RGBColor,
    grid: RGBColor,
    body_fill: RGBColor | None = None,
    font_name: str = "Calibri",
) -> bool:
    if not rows or len(rows) < 2:
        return False
    n_rows = len(rows)
    n_cols = len(rows[0])
    try:
        table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    except Exception:
        return False
    # Light decks keep white body; dark packs pass panel/paper via body_fill.
    row_fill = body_fill if body_fill is not None else RGBColor(0xFF, 0xFF, 0xFF)
    table = table_shape.table
    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(cell_text or "")
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.RIGHT
                for run in p.runs:
                    run.font.size = Pt(12 if r else 11)
                    run.font.bold = r == 0
                    run.font.name = font_name
                    run.font.color.rgb = header_ink if r == 0 else body_ink
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = header_fill
            else:
                fill.fore_color.rgb = row_fill
    return True
