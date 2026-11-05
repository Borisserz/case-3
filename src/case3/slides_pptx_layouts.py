"""Slide layout painters for native Liber PPTX.

Imported by ``slides_pptx_native.build_native_pptx``. Draw helpers come from
``slides_pptx_draw``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches

from case3.slides_html import _pct_from_kicker, parse_hero_metrics
from case3.slides_pptx_draw import (
    _MARGIN_X,
    _PPTX_FONT,
    _SLIDE_H,
    _SLIDE_W,
    _add_bullets,
    _add_textbox,
    _apply_pack_bg,
    _brand,
    _foil_cards,
    _hex_rgb,
    _is_dark_pack,
    _kicker_title,
    _motif_dict,
    _panel_rgb,
    _picture_fit,
    _set_fill_alpha,
    _set_run,
    _set_slide_bg_picture,
    _split_ratio,
    _top_bar,
    _wants_top_bar,
)

def _layout_title(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
    media_path: Path | None = None,
) -> None:
    dark = _is_dark_pack(style)
    motif = style.get("motif") if isinstance(style, dict) else {}
    hero_bleed = bool(isinstance(motif, dict) and motif.get("hero_bleed"))
    used_photo = False
    if dark and hero_bleed and media_path:
        # Match HTML title-bleed (right 78%%), contain — not OOXML bg stretch.
        bleed_left = Inches(_SLIDE_W.inches * 0.22)
        bleed_w = Inches(_SLIDE_W.inches * 0.78)
        _picture_fit(slide, Path(media_path), bleed_left, Inches(0), bleed_w, _SLIDE_H)
        used_photo = True
    if not used_photo:
        _apply_pack_bg(slide, colors, style)
    # Dark botanical title: left column copy over full-bleed / forest (Julius VESPER).
    if dark and (used_photo or hero_bleed):
        if used_photo:
            # Twin of HTML title-bleed__veil — left forest wash for ivory type.
            veil = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(6.4), _SLIDE_H
            )
            veil.fill.solid()
            veil.fill.fore_color.rgb = colors["sheet"]
            veil.line.fill.background()
            _set_fill_alpha(veil, 0.12)
            # Soft mid band
            mid = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(5.2), Inches(0), Inches(2.4), _SLIDE_H
            )
            mid.fill.solid()
            mid.fill.fore_color.rgb = colors["sheet"]
            mid.line.fill.background()
            _set_fill_alpha(mid, 0.55)
        _brand(slide, colors)
        kicker = str(s.get("kicker") or "").strip()
        y = Inches(1.7)
        if kicker:
            _add_textbox(
                slide,
                _MARGIN_X,
                Inches(1.35),
                Inches(7),
                Inches(0.3),
                kicker.upper(),
                size_pt=11,
                bold=True,
                color=colors.get("foil", colors["accent"]),
            )
        _add_textbox(
            slide,
            _MARGIN_X,
            y,
            Inches(7.2),
            Inches(1.6),
            str(s.get("title") or ""),
            size_pt=44,
            bold=True,
            color=colors["ink"],
        )
        y2 = Inches(3.5)
        takeaway = str(s.get("takeaway") or "").strip()
        if takeaway:
            _add_textbox(
                slide,
                _MARGIN_X,
                y2,
                Inches(6.5),
                Inches(1.6),
                takeaway.replace(" · ", "\n"),
                size_pt=28,
                bold=True,
                color=colors["ink"],
            )
            y2 = Inches(5.2)
        sub = str(s.get("subtitle") or "").strip()
        if sub:
            _add_textbox(
                slide,
                _MARGIN_X,
                y2,
                Inches(6.2),
                Inches(1.0),
                sub,
                size_pt=16,
                color=colors["muted"],
            )
            y2 = y2 + Inches(0.85)
        bullets = [str(b) for b in (s.get("bullets") or []) if str(b).strip()]
        if bullets:
            _add_bullets(
                slide,
                _MARGIN_X,
                y2,
                Inches(6.5),
                Inches(2.4),
                bullets,
                size_pt=16,
                color=colors["ink2"],
            )
        return
    split = _split_ratio(style)
    left_w = Inches(11.5)
    takeaway = str(s.get("takeaway") or "").strip()
    if split is not None:
        # Julius Split Pastel: cream left + pastel right panel
        panel_w = _SLIDE_W * (1.0 - split)
        panel_left = _SLIDE_W - panel_w
        panel = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, panel_left, Inches(0), panel_w, _SLIDE_H
        )
        panel.fill.solid()
        panel.fill.fore_color.rgb = _panel_rgb(
            colors, style, slide_index=slide_index
        )
        panel.line.fill.background()
        left_w = Inches(max(5.5, 13.333 * split - 1.0))
        metrics = parse_hero_metrics(takeaway)
        if metrics:
            y_m = Inches(1.85)
            for value, label in metrics[:3]:
                _add_textbox(
                    slide,
                    panel_left + Inches(0.45),
                    y_m,
                    panel_w - Inches(0.7),
                    Inches(0.75),
                    value,
                    size_pt=40,
                    bold=True,
                    color=colors["ink"],
                )
                y_m = y_m + Inches(0.62)
                if label:
                    _add_textbox(
                        slide,
                        panel_left + Inches(0.45),
                        y_m,
                        panel_w - Inches(0.7),
                        Inches(0.4),
                        label,
                        size_pt=14,
                        color=colors["ink2"],
                    )
                    y_m = y_m + Inches(0.7)
                else:
                    y_m = y_m + Inches(0.35)
        elif takeaway:
            _add_textbox(
                slide,
                panel_left + Inches(0.45),
                Inches(2.4),
                panel_w - Inches(0.7),
                Inches(2.2),
                takeaway,
                size_pt=22,
                bold=True,
                color=colors["ink"],
            )
    elif _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    kicker = str(s.get("kicker") or "").strip()
    y = Inches(2.2)
    if kicker:
        _add_textbox(
            slide,
            _MARGIN_X,
            Inches(1.55) if split else Inches(1.9),
            left_w,
            Inches(0.3),
            kicker.upper(),
            size_pt=12,
            bold=True,
            color=colors["muted"] if split else colors["accent"],
        )
        y = Inches(2.05) if split else Inches(2.35)
    _add_textbox(
        slide,
        _MARGIN_X,
        y,
        left_w,
        Inches(2.0) if split else Inches(1.5),
        str(s.get("title") or ""),
        size_pt=44 if split else 40,
        bold=True,
        color=colors["ink"],
    )
    y2 = y + (Inches(2.1) if split else Inches(1.45))
    if not split and takeaway:
        _add_textbox(
            slide,
            _MARGIN_X,
            y2,
            left_w,
            Inches(0.55),
            takeaway,
            size_pt=16,
            color=colors["ink2"],
        )
        y2 = y2 + Inches(0.55)
    sub = str(s.get("subtitle") or "").strip()
    if sub:
        _add_textbox(
            slide,
            _MARGIN_X,
            y2,
            left_w,
            Inches(1.2),
            sub,
            size_pt=18 if not split else 20,
            color=colors["muted"],
        )


def _layout_section(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> None:
    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    chapter = s.get("chapter")
    ch = f"{int(chapter):02d}" if isinstance(chapter, int) else "—"
    # Accent panel (Julius chapter splash / Split Pastel) — ~32% width
    panel = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(8.55), Inches(0), Inches(4.8), _SLIDE_H
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = _panel_rgb(colors, style, slide_index=slide_index)
    panel.line.fill.background()
    _add_textbox(
        slide,
        Inches(9.0),
        Inches(2.8),
        Inches(3.8),
        Inches(1.2),
        ch,
        size_pt=48,
        bold=True,
        color=colors["ink"] if style and style.get("pack_id") == "relay" else colors["sheet"],
    )
    _add_textbox(
        slide,
        _MARGIN_X,
        Inches(2.6),
        Inches(7.4),
        Inches(1.4),
        str(s.get("title") or ""),
        size_pt=36,
        bold=True,
        color=colors["ink"],
    )
    sub = str(s.get("subtitle") or "").strip()
    if sub:
        _add_textbox(
            slide,
            _MARGIN_X,
            Inches(4.2),
            Inches(7.0),
            Inches(1.0),
            sub,
            size_pt=16,
            color=colors["muted"],
        )


def _layout_callout(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> None:
    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    y_in = _kicker_title(
        slide,
        colors,
        kicker=str(s.get("kicker") or ""),
        title=str(s.get("title") or ""),
        takeaway=str(s.get("takeaway") or ""),
        chapter=s.get("chapter") if isinstance(s.get("chapter"), int) else None,
    )
    box_top = Inches(max(y_in + 0.15, 2.0))
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        _MARGIN_X,
        box_top,
        Inches(11.9),
        Inches(3.4),
    )
    box.fill.solid()
    motif = _motif_dict(style)
    use_pastel = bool(motif.get("panels"))
    if use_pastel:
        box.fill.fore_color.rgb = _panel_rgb(
            colors, style, slide_index=slide_index
        )
        if _foil_cards(style):
            box.line.color.rgb = colors.get("foil", colors["accent"])
        else:
            box.line.fill.background()
    else:
        box.fill.fore_color.rgb = colors["paper"]
        box.line.color.rgb = colors["accent"]
    term = str(s.get("term") or "")
    definition = str(s.get("definition") or "")
    body = str(s.get("body") or "").strip()
    _add_textbox(
        slide,
        Inches(1.05),
        box_top + Inches(0.35),
        Inches(11),
        Inches(0.35),
        term.upper(),
        size_pt=12,
        bold=True,
        color=colors["accent"],
    )
    _add_textbox(
        slide,
        Inches(1.05),
        box_top + Inches(0.85),
        Inches(11),
        Inches(1.5),
        definition,
        size_pt=20,
        color=colors["ink"],
    )
    if body:
        _add_textbox(
            slide,
            Inches(1.05),
            box_top + Inches(2.45),
            Inches(11),
            Inches(0.7),
            body,
            size_pt=14,
            color=colors["ink2"],
        )


def _layout_table(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None,
) -> None:
    from case3.slides_pptx_tables import add_native_table

    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    y_in = _kicker_title(
        slide,
        colors,
        kicker=str(s.get("kicker") or ""),
        title=str(s.get("title") or ""),
        takeaway=str(s.get("takeaway") or ""),
        chapter=s.get("chapter") if isinstance(s.get("chapter"), int) else None,
    )
    rows = s.get("rows") or []
    table_style = (style or {}).get("table") if isinstance(style, dict) else {}
    header_fill = colors["primary"]
    header_ink = colors["sheet"]
    grid = colors["rule"]
    body_fill: RGBColor | None = None
    if _is_dark_pack(style):
        body_fill = colors.get("panel") or colors.get("paper")
    if isinstance(table_style, dict):
        if table_style.get("header_fill"):
            header_fill = _hex_rgb(str(table_style["header_fill"]))
        if table_style.get("header_ink"):
            header_ink = _hex_rgb(str(table_style["header_ink"]))
        if table_style.get("grid"):
            grid = _hex_rgb(str(table_style["grid"]))
        if table_style.get("body_fill"):
            body_fill = _hex_rgb(str(table_style["body_fill"]))
    add_native_table(
        slide,
        rows if isinstance(rows, list) else [],
        left=_MARGIN_X,
        top=Inches(max(y_in, 1.7)),
        width=Inches(11.9),
        height=Inches(4.6),
        header_fill=header_fill,
        header_ink=header_ink,
        body_ink=colors["ink"],
        body_fill=body_fill,
        grid=grid,
        font_name=_PPTX_FONT,
    )
    cap = str(s.get("caption") or "").strip()
    if cap:
        _add_textbox(
            slide,
            _MARGIN_X,
            Inches(6.5),
            Inches(11.9),
            Inches(0.4),
            cap,
            size_pt=11,
            color=colors["muted"],
        )


def _layout_bullets(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    closing: bool = False,
    style: dict[str, Any] | None = None,
) -> None:
    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    y_in = _kicker_title(
        slide,
        colors,
        kicker=str(s.get("kicker") or ""),
        title=str(s.get("title") or ""),
        takeaway=str(s.get("takeaway") or ""),
        chapter=s.get("chapter") if isinstance(s.get("chapter"), int) else None,
    )
    bullets = [str(b) for b in (s.get("bullets") or []) if str(b).strip()]
    _add_bullets(
        slide,
        _MARGIN_X,
        Inches(y_in),
        Inches(11.5),
        Inches(5.2),
        bullets,
        size_pt=20 if closing else 18,
        color=colors["ink2"],
    )


def _layout_closing(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
) -> None:
    """Closing with optional Julius hero number from takeaway + bullets."""
    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    takeaway = str(s.get("takeaway") or "").strip()
    metrics = parse_hero_metrics(takeaway)
    hero_value = ""
    hero_label = ""
    if metrics:
        hero_value, hero_label = metrics[0]
    elif takeaway and len(takeaway) <= 24 and "\n" not in takeaway:
        hero_value = takeaway
    head = dict(s)
    if hero_value:
        head = {**s, "takeaway": ""}
    y_in = _kicker_title(
        slide,
        colors,
        kicker=str(head.get("kicker") or ""),
        title=str(head.get("title") or ""),
        takeaway=str(head.get("takeaway") or ""),
        chapter=head.get("chapter") if isinstance(head.get("chapter"), int) else None,
    )
    y = Inches(max(y_in + 0.1, 1.85))
    foil = colors.get("foil", colors["accent"])
    if hero_value:
        _add_textbox(
            slide,
            _MARGIN_X,
            y,
            Inches(11.5),
            Inches(1.15),
            hero_value,
            size_pt=54,
            bold=True,
            color=foil if _is_dark_pack(style) else colors["ink"],
        )
        y = y + Inches(1.05)
        if hero_label:
            _add_textbox(
                slide,
                _MARGIN_X,
                y,
                Inches(11.5),
                Inches(0.45),
                hero_label,
                size_pt=16,
                color=colors["muted"],
            )
            y = y + Inches(0.55)
    bullets = [str(b) for b in (s.get("bullets") or []) if str(b).strip()][:3]
    if bullets:
        _add_bullets(
            slide,
            _MARGIN_X,
            y,
            Inches(11.5),
            Inches(3.8),
            bullets,
            size_pt=18,
            color=colors["ink2"],
        )


def _layout_card_row(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> None:
    """Julius VESPER 3-up narrative cards + optional gold gate caption."""
    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    y_in = _kicker_title(
        slide,
        colors,
        kicker=str(s.get("kicker") or ""),
        title=str(s.get("title") or ""),
        takeaway=str(s.get("subtitle") or s.get("takeaway") or ""),
        chapter=s.get("chapter") if isinstance(s.get("chapter"), int) else None,
    )
    cards = [c for c in (s.get("cards") or []) if isinstance(c, dict)][:3]
    n = max(1, len(cards))
    gap = Inches(0.28)
    usable = Inches(11.9)
    card_w = Emu(int((usable - gap * (n - 1)) / n))
    left = _MARGIN_X
    top = Inches(max(y_in + 0.12, 2.15))
    card_h = Inches(3.55)
    foil = colors.get("foil", colors["accent"])
    for i, c in enumerate(cards):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, card_w, card_h
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = _panel_rgb(colors, style, slide_index=i)
        if _foil_cards(style):
            shape.line.color.rgb = foil
        else:
            shape.line.fill.background()
        y_t = top + Inches(0.22)
        kicker = str(c.get("kicker") or "").strip()
        pct = _pct_from_kicker(kicker)
        if kicker:
            _add_textbox(
                slide,
                Emu(int(left) + int(Inches(0.22))),
                y_t,
                Emu(int(card_w) - int(Inches(0.4))),
                Inches(0.55) if pct is not None else Inches(0.35),
                kicker if pct is not None else kicker.upper(),
                size_pt=28 if pct is not None else 11,
                bold=True,
                color=foil,
            )
            y_t = y_t + (Inches(0.62) if pct is not None else Inches(0.4))
        if pct is not None:
            track_w = Emu(int(card_w) - int(Inches(0.44)))
            track = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Emu(int(left) + int(Inches(0.22))),
                y_t,
                track_w,
                Inches(0.09),
            )
            track.fill.solid()
            track.fill.fore_color.rgb = colors.get("rule", colors["muted"])
            track.line.fill.background()
            fill_w = Emu(max(1, int(int(track_w) * (pct / 100.0))))
            fill = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Emu(int(left) + int(Inches(0.22))),
                y_t,
                fill_w,
                Inches(0.09),
            )
            fill.fill.solid()
            fill.fill.fore_color.rgb = foil
            fill.line.fill.background()
            y_t = y_t + Inches(0.28)
        _add_textbox(
            slide,
            Emu(int(left) + int(Inches(0.22))),
            y_t,
            Emu(int(card_w) - int(Inches(0.4))),
            Inches(0.7),
            str(c.get("title") or ""),
            size_pt=20,
            bold=True,
            color=colors["ink"],
        )
        body = str(c.get("body") or "").strip()
        if body:
            _add_textbox(
                slide,
                Emu(int(left) + int(Inches(0.22))),
                y_t + Inches(0.75),
                Emu(int(card_w) - int(Inches(0.4))),
                Inches(2.15),
                body,
                size_pt=15,
                color=colors["muted"],
            )
        left = Emu(int(left) + int(card_w) + int(gap))
    gate = str(s.get("caption") or "").strip()
    if gate:
        _add_textbox(
            slide,
            _MARGIN_X,
            Inches(6.15),
            Inches(11.9),
            Inches(0.45),
            gate.upper(),
            size_pt=12,
            bold=True,
            color=foil,
        )


def _layout_kpi(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> None:
    _apply_pack_bg(slide, colors, style)
    use_pastel = False
    if isinstance(style, dict):
        motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
        use_pastel = bool(motif.get("panels"))
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    y_in = _kicker_title(
        slide,
        colors,
        kicker=str(s.get("kicker") or ""),
        title=str(s.get("title") or ""),
        takeaway=str(s.get("takeaway") or ""),
        chapter=s.get("chapter") if isinstance(s.get("chapter"), int) else None,
    )
    kpis = [k for k in (s.get("kpis") or []) if isinstance(k, dict)][:4]
    n = max(1, len(kpis))
    gap = Inches(0.28)
    usable = Inches(11.9)
    card_w = Emu(int((usable - gap * (n - 1)) / n))
    left = _MARGIN_X
    # Pin cards under the title (HTML twin) — avoid floating mid-slide void.
    card_h = Inches(3.35)
    top = Inches(max(y_in + 0.18, 2.05))
    for i, k in enumerate(kpis):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, card_w, card_h
        )
        shape.fill.solid()
        # Split Pastel scorecard: rotate motif panels across cards.
        if use_pastel:
            # Card row uses panel 0..n (distinct pastels), not slide_index offset.
            card_fill = _panel_rgb(colors, style, slide_index=i)
            shape.fill.fore_color.rgb = card_fill
            if _foil_cards(style):
                shape.line.color.rgb = colors.get("foil", colors["accent"])
            else:
                shape.line.fill.background()
        else:
            card_fill = colors["sheet"]
            shape.fill.fore_color.rgb = card_fill
            shape.line.color.rgb = colors["rule"]
            accent = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, left, top, Inches(0.08), card_h
            )
            accent.fill.solid()
            accent.fill.fore_color.rgb = colors["accent"]
            accent.line.fill.background()

        tf = shape.text_frame
        tf.clear()
        tf.word_wrap = True
        p0 = tf.paragraphs[0]
        p0.alignment = PP_ALIGN.LEFT
        r0 = p0.add_run()
        r0.text = str(k.get("value") or "")
        _set_run(r0, size_pt=32, bold=True, color=colors["ink"])
        p1 = tf.add_paragraph()
        r1 = p1.add_run()
        r1.text = str(k.get("label") or "")
        _set_run(r1, size_pt=14, bold=True, color=colors["ink2"])
        delta = str(k.get("delta") or "").strip()
        if delta:
            p_d = tf.add_paragraph()
            r_d = p_d.add_run()
            r_d.text = delta
            _set_run(r_d, size_pt=13, bold=True, color=colors["accent"])
        hint = str(k.get("hint") or "").strip()
        if hint:
            p2 = tf.add_paragraph()
            r2 = p2.add_run()
            r2.text = hint
            _set_run(r2, size_pt=11, color=colors["muted"])
        tf.margin_left = Inches(0.28)
        tf.margin_top = Inches(0.38)
        left = Emu(int(left) + int(card_w) + int(gap))


def _layout_media(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    media_path: Path | None,
    split: bool,
    chart_series: dict[str, Any] | None = None,
    series_colors: list[RGBColor] | None = None,
    style: dict[str, Any] | None = None,
) -> None:
    _apply_pack_bg(slide, colors, style)
    if _wants_top_bar(style):
        _top_bar(slide, colors, style)
    _brand(slide, colors)
    kicker = str(s.get("kicker") or "")
    title = str(s.get("title") or "")
    cap = str(s.get("caption") or "").strip()
    body = str(s.get("body") or "").strip()
    bullets = [str(b) for b in (s.get("bullets") or []) if str(b).strip()]

    takeaway = str(s.get("takeaway") or "")
    chapter = s.get("chapter") if isinstance(s.get("chapter"), int) else None
    if split:
        y_in = _kicker_title(
            slide,
            colors,
            kicker=kicker,
            title=title,
            takeaway=takeaway,
            chapter=chapter,
        )
        # left copy
        top = Inches(max(y_in, 1.9))
        if body:
            _add_textbox(
                slide,
                _MARGIN_X,
                top,
                Inches(5.4),
                Inches(1.4),
                body,
                size_pt=16,
                color=colors["ink2"],
            )
            top = top + Inches(1.3)
        if bullets:
            _add_bullets(
                slide,
                _MARGIN_X,
                top,
                Inches(5.4),
                Inches(3.5),
                bullets,
                size_pt=16,
                color=colors["ink2"],
            )
        mid = str(s.get("media_id") or s.get("chart_id") or "")
        is_dia = mid.startswith("dia_")
        is_cht = mid.startswith("cht_")
        # Diagrams get a wider right column so flowcharts stay readable.
        pic_left = Inches(5.4) if is_dia else Inches(6.6)
        pic_w = Inches(7.1) if is_dia else Inches(5.9)
        pic_h = Inches(5.0) if is_dia else Inches(4.6)
        placed = False
        if is_cht and chart_series:
            from case3.slides_pptx_charts import add_native_chart

            placed = add_native_chart(
                slide,
                chart_series,
                left=pic_left,
                top=Inches(1.55),
                width=pic_w,
                height=pic_h,
                series_colors=series_colors,
            )
        if not placed:
            _picture_fit(
                slide,
                media_path,  # type: ignore[arg-type]
                pic_left,
                Inches(1.55),
                pic_w,
                pic_h,
            )
        if cap:
            _add_textbox(
                slide,
                pic_left,
                Inches(6.45),
                pic_w,
                Inches(0.55),
                cap,
                size_pt=14,
                bold=True,
                color=colors["ink"],
            )
    else:
        y_in = _kicker_title(
            slide,
            colors,
            kicker=kicker,
            title=title,
            takeaway=takeaway,
            chapter=chapter,
        )
        mid = str(s.get("media_id") or s.get("chart_id") or "")
        is_dia = mid.startswith("dia_")
        is_cht = mid.startswith("cht_")
        placed = False
        if is_cht and chart_series:
            from case3.slides_pptx_charts import add_native_chart

            placed = add_native_chart(
                slide,
                chart_series,
                left=_MARGIN_X,
                top=Inches(max(y_in, 1.45)),
                width=Inches(11.9),
                height=Inches(5.45) if is_dia else Inches(4.8),
                series_colors=series_colors,
            )
        if not placed:
            _picture_fit(
                slide,
                media_path,  # type: ignore[arg-type]
                _MARGIN_X,
                Inches(max(y_in, 1.45)),
                Inches(11.9),
                Inches(5.45) if is_dia else Inches(4.4),
            )
        if cap:
            _add_textbox(
                slide,
                _MARGIN_X,
                Inches(6.35),
                Inches(11.9),
                Inches(0.55),
                cap,
                size_pt=15,
                bold=True,
                color=colors["ink"],
            )


