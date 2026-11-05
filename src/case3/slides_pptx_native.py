"""Native editable PPTX from Liber deck IR (python-pptx shapes + text).

Preview / deck PDF stay HTML→PNG capture. PPTX is intentionally editable —
visual parity with Liber web is not required.

Draw helpers: ``slides_pptx_draw``. Layouts: ``slides_pptx_layouts``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor

from case3 import slides_pptx_draw as draw
from case3.slides_pptx_draw import _colors_from_style, _fonts_from_style, _hex_rgb, _is_dark_pack
from case3.slides_pptx_layouts import (
    _layout_bullets,
    _layout_callout,
    _layout_card_row,
    _layout_closing,
    _layout_kpi,
    _layout_media,
    _layout_compare,
    _layout_quote,
    _layout_section,
    _layout_stat_hero,
    _layout_table,
    _layout_timeline,
    _layout_title,
)

# Re-export for tests / callers that imported helpers from this module.
__all__ = ["build_native_pptx", "_fonts_from_style"]


def build_native_pptx(
    deck: dict[str, Any],
    dest: Path,
    *,
    media_by_id: dict[str, Path] | None = None,
    chart_series_by_id: dict[str, dict[str, Any]] | None = None,
) -> Path:
    """Build editable 16:9 PPTX from validated deck IR."""
    media = media_by_id or {}
    chart_series_by_id = chart_series_by_id or {}
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    colors, title_font, body_font = _colors_from_style(deck)
    draw._PPTX_TITLE_FONT = title_font or "Georgia"
    draw._PPTX_FONT = body_font or "Calibri"
    series_rgbs: list[RGBColor] = []
    style = deck.get("style") if isinstance(deck.get("style"), dict) else None
    if style and isinstance(style.get("brand_mark"), str) and style["brand_mark"].strip():
        draw._BRAND_MARK = str(style["brand_mark"]).strip()
    else:
        draw._BRAND_MARK = "LIBER · ATELIER"
    if style and isinstance(style.get("chart_series"), list):
        for hx in style["chart_series"]:
            try:
                series_rgbs.append(_hex_rgb(str(hx)))
            except Exception:
                continue
    if not series_rgbs:
        series_rgbs = [colors["primary"], colors["accent"]]

    prs = Presentation()
    prs.slide_width = draw._SLIDE_W
    prs.slide_height = draw._SLIDE_H
    blank = prs.slide_layouts[6]

    for si, s in enumerate(deck.get("slides") or []):
        if not isinstance(s, dict):
            continue
        slide = prs.slides.add_slide(blank)
        layout = str(s.get("layout") or "")

        if layout == "title":
            mid = str(s.get("media_id") or s.get("chart_id") or "")
            _layout_title(
                slide,
                s,
                colors,
                style=style,
                slide_index=si,
                media_path=media.get(mid) if mid else None,
            )
        elif layout == "section":
            _layout_section(
                slide, s, colors, style=style, slide_index=si
            )
        elif layout == "callout":
            _layout_callout(
                slide, s, colors, style=style, slide_index=si
            )
        elif layout == "table_hero":
            _layout_table(slide, s, colors, style=style)
        elif layout == "closing":
            mid = str(s.get("media_id") or "")
            if _is_dark_pack(style) and mid and media.get(mid):
                # Closing reuses dark hero bleed when media attached.
                _layout_title(
                    slide,
                    {
                        **s,
                        "layout": "title",
                        "kicker": str(s.get("kicker") or "CLOSE"),
                    },
                    colors,
                    style=style,
                    slide_index=si,
                    media_path=media.get(mid),
                )
            else:
                _layout_closing(slide, s, colors, style=style)
        elif layout == "bullets":
            _layout_bullets(slide, s, colors, style=style)
        elif layout == "card_row":
            _layout_card_row(
                slide, s, colors, style=style, slide_index=si
            )
        elif layout == "stat_hero":
            _layout_stat_hero(slide, s, colors, style=style)
        elif layout == "timeline":
            _layout_timeline(slide, s, colors, style=style)
        elif layout == "compare":
            _layout_compare(slide, s, colors, style=style)
        elif layout == "quote":
            _layout_quote(slide, s, colors, style=style)
        elif layout in ("kpi_row", "scorecard"):
            _layout_kpi(
                slide, s, colors, style=style, slide_index=si
            )
        elif layout in ("chart_hero", "media_hero"):
            mid = str(s.get("chart_id") or s.get("media_id") or "")
            _layout_media(
                slide,
                s,
                colors,
                media_path=media.get(mid),
                split=False,
                chart_series=chart_series_by_id.get(mid),
                series_colors=series_rgbs,
                style=style,
            )
        elif layout in ("chart_split", "media_split"):
            mid = str(s.get("chart_id") or s.get("media_id") or "")
            _layout_media(
                slide,
                s,
                colors,
                media_path=media.get(mid),
                split=True,
                chart_series=chart_series_by_id.get(mid),
                series_colors=series_rgbs,
                style=style,
            )
        else:
            _layout_bullets(slide, s, colors, style=style)

    prs.save(str(dest))
    return dest
