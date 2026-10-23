"""Native editable PPTX from Liber deck IR (python-pptx shapes + text).

Preview / deck PDF stay HTML→PNG capture. PPTX is intentionally editable —
visual parity with Liber web is not required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Inches, Pt

from case3.chart_style import _PALETTES, normalize_palette_id
from case3.slides_html import parse_hero_metrics

_SLIDE_W = Inches(13.333)
_SLIDE_H = Inches(7.5)
_MARGIN_X = Inches(0.7)
_MARGIN_TOP = Inches(0.55)


def _as_inches(val: Any) -> float:
    """python-pptx Length: ``float(Inches(0.85))`` is EMUs (~777240), not 0.85.

    Always convert via ``.inches`` before arithmetic that expects inch floats.
    """
    if val is None:
        return 0.0
    if hasattr(val, "inches"):
        return float(val.inches)
    return float(val)


def _hex_rgb(hex_color: str) -> RGBColor:
    h = (hex_color or "#14161a").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _palette(palette_id: str) -> dict[str, RGBColor]:
    pid = normalize_palette_id(palette_id)
    if pid == "auto":
        pid = "atelier"
    p = _PALETTES.get(pid) or _PALETTES["atelier"]
    primary = str(p["primary"])
    accents = list(p.get("accents") or [primary])
    accent = str(accents[0] if accents else primary)
    muted = str(p.get("muted") or "#6a6f64")
    return {
        "primary": _hex_rgb(primary),
        "accent": _hex_rgb(accent),
        "muted": _hex_rgb(muted),
        "ink": _hex_rgb("#14161a"),
        "ink2": _hex_rgb("#2c3028"),
        "paper": _hex_rgb("#f0ede4"),
        "sheet": _hex_rgb("#fffcf7"),
        "rule": _hex_rgb("#e6e2d8"),
        "panel": _hex_rgb("#f0ede4"),
    }


def _fonts_from_style(deck: dict[str, Any]) -> tuple[str, str]:
    """Return (title_font, body_font) for PPTX. Prefer Office-safe fallbacks."""
    style = deck.get("style") if isinstance(deck.get("style"), dict) else None
    title, body = "Georgia", "Calibri"
    if not style:
        return title, body
    fonts = style.get("fonts") if isinstance(style.get("fonts"), dict) else {}
    raw_title = str(fonts.get("title") or fonts.get("display") or "").strip()
    raw_body = str(
        fonts.get("fallback_pptx") or fonts.get("body") or fonts.get("sans") or ""
    ).strip()
    # Strip CSS stacks → first family; map web fonts to Office-ish names.
    def _first(name: str, default: str) -> str:
        if not name:
            return default
        part = name.split(",")[0].strip().strip("\"'")
        low = part.lower()
        if low in {"fraunces", "iowan old style", "libre baskerville", "playfair display"}:
            return "Georgia"
        if low in {"source sans 3", "source sans pro", "inter", "dm sans", "manrope"}:
            return "Calibri"
        return part or default

    return _first(raw_title, title), _first(raw_body, body)


def _colors_from_style(
    deck: dict[str, Any],
) -> tuple[dict[str, RGBColor], str, str]:
    """ThemeTokens from deck.style when present; else chart palette. Fonts = title, body."""
    style = deck.get("style") if isinstance(deck.get("style"), dict) else None
    title_font, body_font = _fonts_from_style(deck)
    if style and isinstance(style.get("colors"), dict):
        c = style["colors"]
        return {
            "primary": _hex_rgb(str(c.get("primary") or "#2E4208")),
            "accent": _hex_rgb(str(c.get("accent") or "#4F6B14")),
            "muted": _hex_rgb(str(c.get("muted") or "#6A7160")),
            "ink": _hex_rgb(str(c.get("ink") or c.get("text") or "#14161a")),
            "ink2": _hex_rgb(str(c.get("ink2") or "#2c3028")),
            "paper": _hex_rgb(str(c.get("paper") or "#f0ede4")),
            "sheet": _hex_rgb(
                str(c.get("sheet") or c.get("background") or "#fffcf7")
            ),
            "rule": _hex_rgb(str(c.get("rule") or "#e6e2d8")),
            "panel": _hex_rgb(
                str(c.get("panel") or c.get("paper") or "#f0ede4")
            ),
        }, title_font, body_font
    return _palette(str(deck.get("palette") or "atelier")), title_font, body_font


_PPTX_FONT = "Calibri"
_PPTX_TITLE_FONT = "Georgia"
_BRAND_MARK = "LIBER · ATELIER"


def _set_run(
    run,
    *,
    size_pt: float,
    bold: bool = False,
    color: RGBColor | None = None,
    title: bool = False,
) -> None:
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.name = _PPTX_TITLE_FONT if title else _PPTX_FONT
    if color is not None:
        run.font.color.rgb = color


def _add_textbox(
    slide,
    left,
    top,
    width,
    height,
    text: str,
    *,
    size_pt: float,
    bold: bool = False,
    color: RGBColor | None = None,
    align=PP_ALIGN.LEFT,
    title: bool | None = None,
) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text or ""
    # Titles / display sizes use title face; kickers stay body.
    use_title = bool(title) if title is not None else (bold and size_pt >= 24)
    _set_run(run, size_pt=size_pt, bold=bold, color=color, title=use_title)


def _add_bullets(
    slide,
    left,
    top,
    width,
    height,
    bullets: list[str],
    *,
    size_pt: float,
    color: RGBColor,
) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = 0
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = f"• {item}"
        _set_run(run, size_pt=size_pt, color=color)
        p.space_after = Pt(8)


def _top_bar(slide, colors: dict[str, RGBColor]) -> None:
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), _SLIDE_W, Inches(0.08)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = colors["primary"]
    shape.line.fill.background()


def _brand(slide, colors: dict[str, RGBColor]) -> None:
    _add_textbox(
        slide,
        _MARGIN_X,
        Inches(0.22),
        Inches(5.5),
        Inches(0.3),
        _BRAND_MARK,
        size_pt=9,
        bold=True,
        color=colors["muted"],
    )


def _kicker_title(
    slide,
    colors: dict[str, RGBColor],
    *,
    kicker: str,
    title: str,
    top=_MARGIN_TOP,
    takeaway: str = "",
    chapter: int | None = None,
) -> float:
    """Paint brand kicker + title (+ optional takeaway). Returns next Y in inches."""
    y = _as_inches(top)
    top_in = _as_inches(top)
    margin_top_in = _as_inches(_MARGIN_TOP)
    if chapter is not None:
        _add_textbox(
            slide,
            _MARGIN_X,
            Inches(y),
            Inches(1.2),
            Inches(0.28),
            f"{int(chapter):02d}",
            size_pt=12,
            bold=True,
            color=colors["accent"],
        )
    if kicker:
        _add_textbox(
            slide,
            _MARGIN_X + (Inches(0.7) if chapter is not None else Inches(0)),
            Inches(y),
            Inches(11),
            Inches(0.28),
            kicker.upper(),
            size_pt=11,
            bold=True,
            color=colors["accent"],
        )
        y = 0.85 if abs(top_in - margin_top_in) < 1e-6 else y + 0.32
    _add_textbox(
        slide,
        _MARGIN_X,
        Inches(y),
        Inches(12),
        Inches(0.7),
        title,
        size_pt=28 if kicker else 32,
        bold=True,
        color=colors["ink"],
    )
    y2 = y + 0.85
    if takeaway:
        _add_textbox(
            slide,
            _MARGIN_X,
            Inches(y2),
            Inches(11.5),
            Inches(0.45),
            takeaway,
            size_pt=14,
            color=colors["ink2"],
        )
        y2 += 0.5
    return y2


def _is_dark_pack(style: dict[str, Any] | None) -> bool:
    if not isinstance(style, dict):
        return False
    if str(style.get("pack_id") or "") in ("botanical", "signal"):
        return True
    motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
    return str(motif.get("atmosphere") or "") == "dark"


def _motif_dict(style: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(style, dict):
        return {}
    motif = style.get("motif")
    return motif if isinstance(motif, dict) else {}


def _foil_cards(style: dict[str, Any] | None) -> bool:
    """Gold/accent card borders — botanical bar; any pack with motif.foil_cards."""
    motif = _motif_dict(style)
    if "foil_cards" in motif:
        return bool(motif.get("foil_cards"))
    pack = str((style or {}).get("pack_id") or "")
    return pack == "botanical"


def _botanical_texture_path() -> Path:
    return Path(__file__).resolve().parent / "deck_themes" / "botanical_bg.png"


def _apply_pack_bg(
    slide,
    colors: dict[str, RGBColor],
    style: dict[str, Any] | None,
    *,
    prefer_texture: bool = True,
) -> None:
    """Dark Botanical: fern texture bg (Julius image2) when available."""
    if (
        prefer_texture
        and isinstance(style, dict)
        and str(style.get("pack_id") or "") == "botanical"
    ):
        tex = _botanical_texture_path()
        if tex.is_file() and _set_slide_bg_picture(slide, tex):
            return
    _fill_bg(slide, colors)


def _fill_bg(slide, colors: dict[str, RGBColor]) -> None:
    # Blank layout has no fill control easily; add full-slide rect behind
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), _SLIDE_W, _SLIDE_H
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = colors["sheet"]
    bg.line.fill.background()
    # send to back
    spTree = slide.shapes._spTree
    sp = bg._element
    spTree.remove(sp)
    spTree.insert(2, sp)


def _set_fill_alpha(shape, alpha: float) -> None:
    """Set solid fill transparency (0=opaque, 1=invisible)."""
    try:
        solid = shape.fill._xPr.solidFill
        srgb = solid.find(qn("a:srgbClr"))
        if srgb is None:
            return
        # remove existing alpha
        for child in list(srgb):
            if "alpha" in child.tag:
                srgb.remove(child)
        alpha_el = parse_xml(
            f'<a:alpha {nsdecls("a")} val="{int(max(0, min(1, alpha)) * 100000)}"/>'
        )
        srgb.append(alpha_el)
    except Exception:
        pass


def _set_slide_bg_picture(slide, path: Path) -> bool:
    """Julius-style: full-slide image as OOXML slide background (editable PPTX)."""
    p = Path(path) if path else None
    if p is None or not p.is_file():
        return False
    try:
        _, rid = slide.part.get_or_add_image_part(str(p))
        el = parse_xml(
            f'<p:bg {nsdecls("a", "p", "r")}>'
            f"<p:bgPr>"
            f'<a:blipFill dpi="0" rotWithShape="1">'
            f'<a:blip r:embed="{rid}"/>'
            f"<a:stretch><a:fillRect/></a:stretch>"
            f"</a:blipFill>"
            f"<a:effectLst/>"
            f"</p:bgPr>"
            f"</p:bg>"
        )
        slide._element.cSld.insert(0, el)
        return True
    except Exception:
        return False


def _picture_fit(
    slide,
    path: Path,
    left,
    top,
    width,
    height,
) -> None:
    if not path or not Path(path).is_file():
        return
    slide.shapes.add_picture(str(path), left, top, width=width, height=height)


def _split_ratio(style: dict[str, Any] | None) -> float | None:
    if not isinstance(style, dict):
        return None
    motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
    if "split" not in motif:
        # Panel color alone implies Julius split-pastel title.
        colors = style.get("colors") if isinstance(style.get("colors"), dict) else {}
        if colors.get("panel") and style.get("pack_id") in ("relay", "pastel"):
            return 0.55
        return None
    try:
        return max(0.35, min(0.8, float(motif["split"])))
    except (TypeError, ValueError):
        return 0.55


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
        used_photo = _set_slide_bg_picture(slide, Path(media_path))
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
    else:
        _top_bar(slide, colors)
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


def _panel_rgb(
    colors: dict[str, RGBColor],
    style: dict[str, Any] | None,
    *,
    slide_index: int = 0,
) -> RGBColor:
    """Rotate Split Pastel panels (lilac/green/peach/blue) like Julius QBR."""
    if isinstance(style, dict):
        motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
        panels = motif.get("panels") if isinstance(motif.get("panels"), list) else []
        if panels:
            hx = str(panels[slide_index % len(panels)])
            try:
                return _hex_rgb(hx)
            except Exception:
                pass
    return colors.get("panel", colors["accent"])


def _layout_section(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> None:
    _apply_pack_bg(slide, colors, style)
    if not _is_dark_pack(style):
        _top_bar(slide, colors)
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
    pack = str((style or {}).get("pack_id") or "") if style else ""
    _apply_pack_bg(slide, colors, style)
    if pack not in ("relay", "pastel", "botanical", "signal", "board", "atelier"):
        _top_bar(slide, colors)
    elif pack in ("board", "atelier") and not _motif_dict(style).get("panels"):
        _top_bar(slide, colors)
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
    if not _is_dark_pack(style):
        _top_bar(slide, colors)
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
    if not _is_dark_pack(style):
        _top_bar(slide, colors)
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


def _layout_card_row(
    slide,
    s: dict[str, Any],
    colors: dict[str, RGBColor],
    *,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> None:
    """Julius VESPER 3-up narrative cards + optional gold gate caption."""
    pack = str((style or {}).get("pack_id") or "") if style else ""
    _apply_pack_bg(slide, colors, style)
    if pack not in ("botanical", "relay", "pastel", "signal") and not _motif_dict(style).get(
        "panels"
    ):
        _top_bar(slide, colors)
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
    top = Inches(max(y_in + 0.1, 2.85))
    card_h = Inches(2.85)
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
        if kicker:
            _add_textbox(
                slide,
                Emu(int(left) + int(Inches(0.22))),
                y_t,
                Emu(int(card_w) - int(Inches(0.4))),
                Inches(0.35),
                kicker.upper(),
                size_pt=11,
                bold=True,
                color=foil,
            )
            y_t = y_t + Inches(0.4)
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
                Inches(1.4),
                body,
                size_pt=14,
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
    pack = str((style or {}).get("pack_id") or "") if style else ""
    _apply_pack_bg(slide, colors, style)
    use_pastel = False
    if isinstance(style, dict):
        motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
        use_pastel = bool(motif.get("panels"))
    if not use_pastel and not _foil_cards(style):
        _top_bar(slide, colors)
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
    card_h = Inches(2.8)
    # Vertically center the card row in the content band (Julius calm density).
    content_top = Inches(max(y_in + 0.15, 1.85))
    content_bottom = Inches(6.6)
    top = Emu(int(content_top) + max(0, (int(content_bottom) - int(content_top) - int(card_h)) // 2))
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
        _set_run(r0, size_pt=28, bold=True, color=colors["ink"])
        p1 = tf.add_paragraph()
        r1 = p1.add_run()
        r1.text = str(k.get("label") or "")
        _set_run(r1, size_pt=14, bold=True, color=colors["ink2"])
        delta = str(k.get("delta") or "").strip()
        if delta:
            p_d = tf.add_paragraph()
            r_d = p_d.add_run()
            r_d.text = delta
            _set_run(r_d, size_pt=12, bold=True, color=colors["accent"])
        hint = str(k.get("hint") or "").strip()
        if hint:
            p2 = tf.add_paragraph()
            r2 = p2.add_run()
            r2.text = hint
            _set_run(r2, size_pt=11, color=colors["muted"])
        tf.margin_left = Inches(0.25)
        tf.margin_top = Inches(0.3)
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
    if not _is_dark_pack(style):
        _top_bar(slide, colors)
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
                Inches(6.55),
                pic_w,
                Inches(0.5),
                cap,
                size_pt=11,
                color=colors["muted"],
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
                Inches(6.4),
                Inches(11.9),
                Inches(0.55),
                cap,
                size_pt=12,
                color=colors["muted"],
            )


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

    global _PPTX_FONT, _PPTX_TITLE_FONT, _BRAND_MARK
    colors, title_font, body_font = _colors_from_style(deck)
    _PPTX_TITLE_FONT = title_font or "Georgia"
    _PPTX_FONT = body_font or "Calibri"
    series_rgbs: list[RGBColor] = []
    style = deck.get("style") if isinstance(deck.get("style"), dict) else None
    if style and isinstance(style.get("brand_mark"), str) and style["brand_mark"].strip():
        _BRAND_MARK = str(style["brand_mark"]).strip()
    else:
        _BRAND_MARK = "LIBER · ATELIER"
    if style and isinstance(style.get("chart_series"), list):
        for hx in style["chart_series"]:
            try:
                series_rgbs.append(_hex_rgb(str(hx)))
            except Exception:
                continue
    if not series_rgbs:
        series_rgbs = [colors["primary"], colors["accent"]]

    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H
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
                _layout_bullets(slide, s, colors, closing=True, style=style)
        elif layout == "bullets":
            _layout_bullets(slide, s, colors, style=style)
        elif layout == "card_row":
            _layout_card_row(
                slide, s, colors, style=style, slide_index=si
            )
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
