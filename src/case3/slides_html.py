"""Render Liber deck slides to offline static HTML (capture canvas)."""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Any

from case3.chart_style import _PALETTES, normalize_palette_id
from case3.color_util import accent_fields

_SLIDE_W = 1920
_SLIDE_H = 1080
_FRAME: str | None = None
_FONTS_DIR = Path(__file__).resolve().parent / "templates" / "fonts"


def _frame_template() -> str:
    global _FRAME
    if _FRAME is None:
        path = Path(__file__).resolve().parent / "templates" / "slide_frame.html"
        _FRAME = path.read_text(encoding="utf-8")
    return _FRAME


def _palette_colors(palette_id: str) -> tuple[str, str, str]:
    pid = normalize_palette_id(palette_id)
    if pid == "auto":
        pid = "atelier"
    p = _PALETTES.get(pid) or _PALETTES["atelier"]
    primary = str(p["primary"])
    accents = list(p.get("accents") or [primary])
    accent = str(accents[0] if accents else primary)
    muted = str(p.get("muted") or "#6a6f64")
    return primary, accent, muted


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _brand(mark: str | None = None) -> str:
    text = (mark or "LIBER · ATELIER").strip() or "LIBER · ATELIER"
    # Split on first · / middle dot for Liber span styling when possible.
    if "·" in text:
        left, right = text.split("·", 1)
        return (
            f'<div class="brand"><span>{_esc(left.strip())}</span> · '
            f"{_esc(right.strip())}</div>"
        )
    return f'<div class="brand">{_esc(text)}</div>'


def _bullets_html(items: list[Any]) -> str:
    lis = "".join(f"<li>{_esc(str(b))}</li>" for b in items if str(b).strip())
    return f'<ul class="bullets">{lis}</ul>' if lis else ""


def _section_head(slide: dict[str, Any], *, compact: bool = False) -> str:
    title = _esc(str(slide.get("title") or ""))
    kicker = str(slide.get("kicker") or "").strip()
    chapter = slide.get("chapter")
    takeaway = str(slide.get("takeaway") or "").strip()
    chapter_html = (
        f'<p class="chapter">{int(chapter):02d}</p>'
        if isinstance(chapter, int)
        else ""
    )
    kicker_html = f'<p class="kicker">{_esc(kicker)}</p>' if kicker else ""
    takeaway_html = (
        f'<p class="takeaway">{_esc(takeaway)}</p>' if takeaway else ""
    )
    cls = "section-head section-head--compact" if compact else "section-head"
    return (
        f'<header class="{cls}">'
        f"{chapter_html}"
        f"{kicker_html}"
        f'<h2 class="section-title">{title}</h2>'
        f"{takeaway_html}"
        f"</header>"
    )


def _media_img(href: str | None, *, kind: str = "chart") -> str:
    if href:
        return f'<img src="{_esc(href)}" alt="" />'
    label = {
        "photo": "Photo unavailable",
        "diagram": "Diagram unavailable",
    }.get(kind, "Chart unavailable")
    return f'<div class="chart-empty">{_esc(label)}</div>'


def _media_kind(media_id: str) -> str:
    if media_id.startswith(("fig_", "usr_")):
        return "photo"
    if media_id.startswith("dia_"):
        return "diagram"
    return "chart"


def _wants_split_title(style: dict[str, Any] | None) -> bool:
    if not isinstance(style, dict):
        return False
    if _is_dark_pack(style):
        return False
    motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
    if "split" in motif:
        return True
    return str(style.get("pack_id") or "") in ("relay", "pastel")


def _is_dark_pack(style: dict[str, Any] | None) -> bool:
    from case3.deck_theme import is_dark_pack

    return is_dark_pack(style)


def _motif_panels(style: dict[str, Any] | None) -> list[str]:
    if not isinstance(style, dict):
        return []
    motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
    raw = motif.get("panels") if isinstance(motif.get("panels"), list) else []
    return [str(p) for p in raw if str(p).strip()]


_STATUS_KIND = {
    "масштаб": "is-scale",
    "scale": "is-scale",
    "пауза": "is-pause",
    "pause": "is-pause",
    "держать": "is-hold",
    "hold": "is-hold",
}


def _cell_html(text: str, *, header: bool) -> str:
    tag = "th" if header else "td"
    raw = str(text or "")
    kind = None if header else _STATUS_KIND.get(raw.strip().casefold())
    inner = (
        f'<span class="status-chip {kind}">{_esc(raw)}</span>' if kind else _esc(raw)
    )
    return f"<{tag}>{inner}</{tag}>"


def _pct_from_kicker(kicker: str) -> int | None:
    """Parse leading ``68%`` / ``104% NA`` kickers for narr-card meters."""
    m = re.match(r"^(\d{1,3})\s*%", (kicker or "").strip())
    if not m:
        return None
    return max(0, min(100, int(m.group(1))))


def parse_hero_metrics(takeaway: str) -> list[tuple[str, str]]:
    """Julius title-panel KPIs: stacked (value, label) from takeaway.

    Accepts:
    - one ``VALUE — label`` per line (2–4 lines),
    - alternating bare lines ``value\\nlabel\\nvalue\\nlabel``,
    - or ``VALUE — label · VALUE — label`` on one line.
    """
    raw = (takeaway or "").strip()
    if not raw:
        return []

    def _split_pair(ch: str) -> tuple[str, str] | None:
        for sep in (" — ", " – ", " - ", ": "):
            if sep in ch:
                left, right = ch.split(sep, 1)
                if left.strip() and right.strip():
                    return left.strip(), right.strip()
        return None

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    # Prefer per-line VALUE — label (works for 2, 3, or 4 metrics).
    if len(lines) >= 2:
        dashed = [_split_pair(ln) for ln in lines]
        if all(p is not None for p in dashed):
            return [p for p in dashed if p is not None][:4]
        # Alternating bare value / label lines.
        if len(lines) >= 2 and len(lines) % 2 == 0 and all(
            _split_pair(ln) is None for ln in lines
        ):
            return [(lines[i], lines[i + 1]) for i in range(0, len(lines), 2)][:4]

    chunks = [c.strip() for c in raw.replace("|", "·").split("·") if c.strip()]
    out: list[tuple[str, str]] = []
    for ch in chunks:
        pair = _split_pair(ch)
        if pair:
            out.append(pair)
        elif ch:
            out.append((ch, ""))
    if len(out) >= 2:
        return out[:4]
    if len(out) == 1 and out[0][1]:
        return out[:1]
    return []


def _title_panel_inner(takeaway: str) -> str:
    metrics = parse_hero_metrics(takeaway)
    if metrics:
        blocks = []
        for value, label in metrics:
            lab = (
                f'<p class="hero-metric__label">{_esc(label)}</p>' if label else ""
            )
            blocks.append(
                f'<div class="hero-metric">'
                f'<p class="hero-metric__value">{_esc(value)}</p>'
                f"{lab}</div>"
            )
        return f'<div class="hero-metrics">{"".join(blocks)}</div>'
    if takeaway.strip():
        return f'<p class="takeaway takeaway--hero">{_esc(takeaway.strip())}</p>'
    return '<p class="takeaway takeaway--hero"></p>'


def _body_for_slide(
    slide: dict[str, Any],
    *,
    media_png_href: str | None,
    brand_mark: str | None = None,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> str:
    layout = str(slide.get("layout") or "")
    brand = _brand(brand_mark)
    panels = _motif_panels(style)

    if layout == "title":
        title = _esc(str(slide.get("title") or ""))
        sub = str(slide.get("subtitle") or "").strip()
        sub_html = f'<p class="subtitle">{_esc(sub)}</p>' if sub else ""
        kicker = str(slide.get("kicker") or "").strip()
        kicker_html = f'<p class="kicker">{_esc(kicker)}</p>' if kicker else ""
        takeaway = str(slide.get("takeaway") or "").strip()
        takeaway_html = (
            f'<p class="takeaway takeaway--hero">{_esc(takeaway)}</p>'
            if takeaway
            else ""
        )
        dark = _is_dark_pack(style)
        motif = style.get("motif") if isinstance(style, dict) else {}
        hero_bleed = bool(isinstance(motif, dict) and motif.get("hero_bleed"))
        split = _wants_split_title(style)
        panel_inner = _title_panel_inner(takeaway)
        panel_html = (
            f'<aside class="title-panel">{panel_inner}</aside>' if split else ""
        )
        main_takeaway = "" if split else takeaway_html
        pack = _esc(str((style or {}).get("pack_id") or ""))
        # Dark Botanical: full-bleed media behind left copy (Julius VESPER).
        if dark and hero_bleed and media_png_href:
            bg = ""
            if media_png_href:
                bg = (
                    f'<div class="title-bleed" aria-hidden="true">'
                    f'<img src="{_esc(media_png_href)}" alt="" />'
                    f'<div class="title-bleed__veil"></div></div>'
                )
            bullets_html = _bullets_html(slide.get("bullets") or [])
            return (
                f'<div class="slide-inner title-stage title-stage--bleed" data-pack="{pack}">'
                f"{bg}"
                f'<div class="title-main title-main--bleed">'
                f"{brand}"
                f"{kicker_html}"
                f"<h1>{title}</h1>"
                f"{main_takeaway or _title_panel_inner(takeaway)}"
                f"{sub_html}"
                f"{bullets_html}"
                f"</div></div>"
            )
        if not split:
            return (
                f'<div class="slide-inner title-stage title-stage--field" data-pack="{pack}">'
                f'<div class="title-field__copy">'
                f"{brand}"
                f"{kicker_html}"
                f"<h1>{title}</h1>"
                f"{main_takeaway}"
                f"{sub_html}"
                f"</div>"
                f'<aside class="title-field__rail" aria-hidden="true"></aside>'
                f"</div>"
            )
        stage_cls = "slide-inner title-stage title-stage--split"
        return (
            f'<div class="{stage_cls}" data-pack="{pack}">'
            f'<div class="title-main">'
            f"{brand}"
            f"{kicker_html}"
            f"<h1>{title}</h1>"
            f"{main_takeaway}"
            f"{sub_html}"
            f"</div>"
            f"{panel_html}"
            f"</div>"
        )

    if layout == "section":
        # Twin of PPTX _layout_section: title left, accent chapter panel right.
        sub = str(slide.get("subtitle") or slide.get("takeaway") or "").strip()
        sub_html = f'<p class="section-splash__sub">{_esc(sub)}</p>' if sub else ""
        chapter = slide.get("chapter")
        ch = f"{int(chapter):02d}" if isinstance(chapter, int) else "—"
        return (
            f'<div class="slide-inner section-splash">'
            f"{brand}"
            f'<div class="section-splash__main">'
            f'<h1 class="section-splash__title">{_esc(str(slide.get("title") or ""))}</h1>'
            f"{sub_html}"
            f"</div>"
            f'<aside class="section-splash__panel" aria-hidden="true">'
            f'<p class="section-splash__num">{ch}</p>'
            f"</aside>"
            f"</div>"
        )

    if layout == "bullets":
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(slide)}"
            f"{_bullets_html(slide.get('bullets') or [])}"
            f"</div>"
        )

    if layout == "closing":
        dark = _is_dark_pack(style)
        motif = style.get("motif") if isinstance(style, dict) else {}
        hero_bleed = bool(isinstance(motif, dict) and motif.get("hero_bleed"))
        if dark and hero_bleed and media_png_href:
            # Twin of PPTX closing→title hero bleed (Julius VESPER close).
            return _body_for_slide(
                {
                    **slide,
                    "layout": "title",
                    "kicker": str(slide.get("kicker") or "CLOSE"),
                },
                media_png_href=media_png_href,
                brand_mark=brand_mark,
                style=style,
                slide_index=slide_index,
            )
        takeaway = str(slide.get("takeaway") or "").strip()
        metrics = parse_hero_metrics(takeaway)
        hero_html = ""
        if metrics:
            value, label = metrics[0]
            lab = (
                f'<p class="closing-hero__label">{_esc(label)}</p>' if label else ""
            )
            hero_html = (
                f'<div class="closing-hero">'
                f'<p class="closing-hero__value">{_esc(value)}</p>'
                f"{lab}</div>"
            )
        elif takeaway and len(takeaway) <= 24:
            hero_html = (
                f'<div class="closing-hero">'
                f'<p class="closing-hero__value">{_esc(takeaway)}</p>'
                f"</div>"
            )
        # Head without takeaway when it became the hero number.
        head = dict(slide)
        if hero_html:
            head = {**slide, "takeaway": ""}
        return (
            f'<div class="slide-inner closing-stage">'
            f"{brand}"
            f"{_section_head(head)}"
            f"{hero_html}"
            f"{_bullets_html(slide.get('bullets') or [])}"
            f"</div>"
        )

    if layout in ("kpi_row", "scorecard"):
        cards = []
        for i, k in enumerate(slide.get("kpis") or []):
            if not isinstance(k, dict):
                continue
            hint = str(k.get("hint") or "").strip()
            delta = str(k.get("delta") or "").strip()
            status = str(k.get("status") or "").strip()
            hint_html = f'<div class="hint">{_esc(hint)}</div>' if hint else ""
            delta_html = (
                f'<div class="delta status-{_esc(status or "flat")}">'
                f"{_esc(delta)}</div>"
                if delta
                else ""
            )
            # Split Pastel: distinct pastels across KPI cards (Julius scorecard).
            pastel = ""
            if panels:
                hx = panels[i % len(panels)]
                pastel = (
                    f' style="background:{_esc(hx)};border-color:transparent;'
                    f'border-left-color:{_esc(hx)}"'
                )
            foot = f'<div class="kpi-foot">{delta_html}</div>' if delta_html else ""
            cards.append(
                f'<div class="kpi-card"{pastel}>'
                f'<div class="kpi-main">'
                f"<div class=\"value\">{_esc(str(k.get('value') or ''))}</div>"
                f"<div class=\"label\">{_esc(str(k.get('label') or ''))}</div>"
                f"{hint_html}"
                f"</div>"
                f"{foot}"
                "</div>"
            )
        cols = max(1, min(4, len(cards) or 1))
        grid_cls = "kpi-grid scorecard-grid" if layout == "scorecard" else "kpi-grid"
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(slide)}"
            f'<div class="{grid_cls}" style="--kpi-cols:{cols}">'
            f'{"".join(cards)}</div>'
            f"</div>"
        )

    if layout == "callout":
        term = _esc(str(slide.get("term") or ""))
        definition = _esc(str(slide.get("definition") or ""))
        body = str(slide.get("body") or "").strip()
        body_html = f'<p class="callout__body">{_esc(body)}</p>' if body else ""
        return (
            f'<div class="slide-inner callout-stage">'
            f'<div class="callout-stage__copy">'
            f"{brand}"
            f'<p class="callout__term">{term}</p>'
            f'<p class="callout__def">{definition}</p>'
            f"{body_html}"
            f"</div>"
            f'<aside class="title-field__rail" aria-hidden="true"></aside>'
            f"</div>"
        )

    if layout == "card_row":
        cards_html: list[str] = []
        for i, c in enumerate(slide.get("cards") or []):
            if not isinstance(c, dict):
                continue
            kicker = str(c.get("kicker") or "").strip()
            pct = _pct_from_kicker(kicker)
            kicker_html = (
                f'<p class="narr-card__kicker">{_esc(kicker)}</p>' if kicker else ""
            )
            meter_html = ""
            if pct is not None:
                meter_html = (
                    f'<div class="narr-meter" style="--pct:{pct}" aria-hidden="true">'
                    f"<i></i></div>"
                )
                kicker_html = (
                    f'<p class="narr-card__kicker is-pct">{_esc(kicker)}</p>'
                )
            body = str(c.get("body") or "").strip()
            body_html = (
                f'<p class="narr-card__body">{_esc(body)}</p>' if body else ""
            )
            pastel = ""
            if panels:
                hx = panels[i % len(panels)]
                pastel = f' style="background:{_esc(hx)}"'
            card_cls = "narr-card is-metered" if pct is not None else "narr-card"
            cards_html.append(
                f'<article class="{card_cls}"{pastel}>'
                f"{kicker_html}"
                f"{meter_html}"
                f'<p class="narr-card__title">{_esc(str(c.get("title") or ""))}</p>'
                f"{body_html}"
                f"</article>"
            )
        gate = str(slide.get("caption") or "").strip()
        gate_html = (
            f'<p class="narr-gate">{_esc(gate)}</p>' if gate else ""
        )
        # Prefer subtitle over takeaway for the audience hypothesis line.
        head = dict(slide)
        if str(slide.get("subtitle") or "").strip() and not str(
            slide.get("takeaway") or ""
        ).strip():
            head = {**slide, "takeaway": str(slide.get("subtitle") or "")}
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(head)}"
            f'<div class="narr-grid" style="--narr-cols:{max(1, min(3, len(cards_html) or 1))}">'
            f'{"".join(cards_html)}</div>'
            f"{gate_html}</div>"
        )

    if layout == "table_hero":
        rows = slide.get("rows") or []
        trs = []
        for i, row in enumerate(rows):
            if not isinstance(row, list):
                continue
            cells = "".join(
                _cell_html(str(c), header=(i == 0)) for c in row
            )
            trs.append(f"<tr>{cells}</tr>")
        cap = str(slide.get("caption") or "").strip()
        cap_html = f'<p class="caption">{_esc(cap)}</p>' if cap else ""
        data_n = max(0, len(trs) - 1)
        roomy = " is-roomy" if 0 < data_n <= 6 else ""
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(slide, compact=True)}"
            f'<div class="table-stage">'
            f'<table class="deck-table{roomy}"><tbody>{"".join(trs)}</tbody></table>'
            f"{cap_html}</div></div>"
        )

    if layout == "chart_hero":
        img = _media_img(media_png_href, kind="chart")
        cap = str(slide.get("caption") or "").strip()
        takeaway = str(slide.get("takeaway") or "").strip()
        # Caption = insight under the chart; promote takeaway when caption empty.
        head = slide
        if not cap and takeaway:
            cap = takeaway
            head = {**slide, "takeaway": ""}
        cap_html = (
            f'<p class="caption caption--insight">{_esc(cap)}</p>' if cap else ""
        )
        return (
            f'<div class="slide-inner chart-hero">'
            f"{brand}"
            f"{_section_head(head, compact=True)}"
            f'<div class="chart-stage">{img}</div>'
            f"{cap_html}"
            f"</div>"
        )

    if layout == "chart_split":
        img = _media_img(media_png_href, kind="chart")
        body = str(slide.get("body") or "").strip()
        body_html = f'<p class="body">{_esc(body)}</p>' if body else ""
        bullets = _bullets_html(slide.get("bullets") or [])
        cap = str(slide.get("caption") or "").strip()
        takeaway = str(slide.get("takeaway") or "").strip()
        head = slide
        if not cap and takeaway:
            cap = takeaway
            head = {**slide, "takeaway": ""}
        cap_html = (
            f'<p class="caption caption--insight">{_esc(cap)}</p>' if cap else ""
        )
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(head, compact=True)}"
            f'<div class="chart-split">'
            f'<div class="copy">{body_html}{bullets}</div>'
            f'<div class="chart-col">'
            f'<div class="chart-stage">{img}</div>'
            f"{cap_html}"
            f"</div></div></div>"
        )

    if layout == "media_hero":
        mid = str(slide.get("media_id") or "")
        kind = _media_kind(mid)
        frame_mod = " media-frame--photo" if kind == "photo" else " media-frame--diagram"
        img = _media_img(media_png_href, kind=kind)
        cap = str(slide.get("caption") or "").strip()
        cap_html = (
            f'<p class="media-caption"><span class="media-caption__lead">'
            f'{"Фото" if kind == "photo" else "Схема" if kind == "diagram" else "Рис."}.</span> '
            f"{_esc(cap)}</p>"
            if cap
            else ""
        )
        return (
            f'<div class="slide-inner media-hero">'
            f"{brand}"
            f"{_section_head(slide, compact=True)}"
            f'<figure class="media-frame{frame_mod}">'
            f'<div class="media-frame__inset">{img}</div>'
            f"</figure>"
            f"{cap_html}"
            f"</div>"
        )

    if layout == "media_split":
        mid = str(slide.get("media_id") or "")
        kind = _media_kind(mid)
        img = _media_img(media_png_href, kind=kind)
        body = str(slide.get("body") or "").strip()
        body_html = (
            f'<p class="media-split__body">{_esc(body)}</p>' if body else ""
        )
        bullets = _bullets_html(slide.get("bullets") or [])
        cap = str(slide.get("caption") or "").strip()
        cap_html = (
            f'<p class="media-aside-caption">{_esc(cap)}</p>' if cap else ""
        )
        frame_mod = " media-frame--diagram" if kind == "diagram" else (
            " media-frame--photo" if kind == "photo" else ""
        )
        grid_mod = " is-diagram" if kind == "diagram" else ""
        return (
            f'<div class="slide-inner media-split">'
            f"{brand}"
            f'<div class="media-split__grid{grid_mod}">'
            f'<div class="media-split__copy">'
            f"{_section_head(slide)}"
            f"{body_html}{bullets}"
            f"</div>"
            f'<aside class="media-split__aside">'
            f'<figure class="media-frame media-frame--thumb{frame_mod}">'
            f'<div class="media-frame__inset">{img}</div>'
            f"</figure>"
            f"{cap_html}"
            f"</aside></div></div>"
        )

    if layout == "quote":
        definition = _esc(str(slide.get("definition") or ""))
        term = str(slide.get("term") or "").strip()
        body = str(slide.get("body") or "").strip()
        term_html = f'<p class="pull-quote__who">{_esc(term)}</p>' if term else ""
        body_html = f'<p class="pull-quote__note">{_esc(body)}</p>' if body else ""
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(slide)}"
            f'<blockquote class="pull-quote">'
            f'<p class="pull-quote__text">{definition}</p>'
            f"{term_html}{body_html}"
            f"</blockquote></div>"
        )

    if layout == "stat_hero":
        kpi = next(
            (k for k in (slide.get("kpis") or []) if isinstance(k, dict)),
            {},
        )
        delta = str(kpi.get("delta") or "").strip()
        hint = str(kpi.get("hint") or "").strip()
        delta_html = f'<p class="stat-hero__delta">{_esc(delta)}</p>' if delta else ""
        hint_html = f'<p class="stat-hero__hint">{_esc(hint)}</p>' if hint else ""
        return (
            f'<div class="slide-inner stat-hero stat-hero--field">'
            f'<div class="stat-hero__figure">'
            f"{brand}"
            f'<p class="stat-hero__value">{_esc(str(kpi.get("value") or ""))}</p>'
            f'<p class="stat-hero__label">{_esc(str(kpi.get("label") or ""))}</p>'
            f"{delta_html}{hint_html}"
            f"</div>"
            f'<div class="stat-hero__notes">{_bullets_html(slide.get("bullets") or [])}</div>'
            f"</div>"
        )

    if layout == "timeline":
        steps = []
        for c in slide.get("cards") or []:
            if not isinstance(c, dict):
                continue
            kicker = str(c.get("kicker") or "").strip()
            body = str(c.get("body") or "").strip()
            kick = f'<p class="timeline__time">{_esc(kicker)}</p>' if kicker else ""
            body_html = f'<p class="timeline__body">{_esc(body)}</p>' if body else ""
            steps.append(
                f'<li class="timeline__step">{kick}'
                f'<p class="timeline__title">{_esc(str(c.get("title") or ""))}</p>'
                f"{body_html}</li>"
            )
        return (
            f'<div class="slide-inner">'
            f"{brand}"
            f"{_section_head(slide)}"
            f'<ol class="timeline">{"".join(steps)}</ol>'
            f"</div>"
        )

    if layout == "compare":
        cols = []
        for i, c in enumerate(slide.get("cards") or []):
            if not isinstance(c, dict):
                continue
            kicker = str(c.get("kicker") or "").strip()
            body = str(c.get("body") or "").strip()
            kick = f'<p class="compare__kicker">{_esc(kicker)}</p>' if kicker else ""
            body_html = f'<p class="compare__body">{_esc(body)}</p>' if body else ""
            side = "is-a" if i == 0 else "is-b"
            cols.append(
                f'<article class="compare__col {side}">{kick}'
                f'<p class="compare__title">{_esc(str(c.get("title") or ""))}</p>'
                f"{body_html}"
                f'<p class="compare__index">{i + 1:02d}</p></article>'
            )
        return (
            f'<div class="slide-inner compare-stage">'
            f"{brand}"
            f"{_section_head(slide)}"
            f'<div class="compare compare--fields">{"".join(cols)}</div>'
            f"</div>"
        )

    raise ValueError(f"unsupported layout: {layout!r}")


def _theme_color_map(
    palette: str, style: dict[str, Any] | None
) -> dict[str, str]:
    """Prefer deck.style.colors (ThemeTokens); fall back to chart palette."""
    colors = (style or {}).get("colors") if isinstance(style, dict) else None
    if isinstance(colors, dict) and colors.get("primary"):
        return {
            "primary": str(colors.get("primary") or "#2E4208"),
            "accent": str(colors.get("accent") or "#4F6B14"),
            "muted": str(colors.get("muted") or "#6A7160"),
            "ink": str(colors.get("ink") or "#14161a"),
            "ink2": str(colors.get("ink2") or "#2c3028"),
            "paper": str(colors.get("paper") or "#f0ede4"),
            "sheet": str(colors.get("sheet") or colors.get("background") or "#fffcf7"),
            "rule": str(colors.get("rule") or "#e6e2d8"),
            "foil": str(colors.get("foil") or "#b8a36a"),
            "panel": str(colors.get("panel") or colors.get("paper") or "#f0ede4"),
        }
    primary, accent, muted = _palette_colors(palette)
    return {
        "primary": primary,
        "accent": accent,
        "muted": muted,
        "ink": "#14161a",
        "ink2": "#2c3028",
        "paper": "#f0ede4",
        "sheet": "#fffcf7",
        "rule": "#e6e2d8",
        "foil": "#b8a36a",
        "panel": "#f0ede4",
    }


def _panel_for_slide(
    style: dict[str, Any] | None, *, slide_index: int = 0, fallback: str = "#E8E0F2"
) -> str:
    if not isinstance(style, dict):
        return fallback
    motif = style.get("motif") if isinstance(style.get("motif"), dict) else {}
    panels = motif.get("panels") if isinstance(motif.get("panels"), list) else []
    if panels:
        return str(panels[slide_index % len(panels)])
    colors = style.get("colors") if isinstance(style.get("colors"), dict) else {}
    return str(colors.get("panel") or fallback)


def render_slide_html(
    slide: dict[str, Any],
    *,
    palette: str,
    chart_png_href: str | None = None,
    media_png_href: str | None = None,
    language: str = "ru",
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> str:
    """Return a full HTML document for one slide (1920×1080)."""
    cmap = _theme_color_map(palette, style)
    href = media_png_href if media_png_href is not None else chart_png_href
    brand_mark = "LIBER · ATELIER"
    if isinstance(style, dict) and style.get("brand_mark"):
        brand_mark = str(style.get("brand_mark")).strip() or brand_mark
    body = _body_for_slide(
        slide,
        media_png_href=href,
        brand_mark=brand_mark,
        style=style,
        slide_index=slide_index,
    )
    layout = str(slide.get("layout") or "")
    footer = _esc(brand_mark)
    panel = _panel_for_slide(
        style, slide_index=slide_index, fallback=cmap.get("panel") or cmap["paper"]
    )
    pack = ""
    if isinstance(style, dict) and style.get("pack_id"):
        pack = str(style.get("pack_id") or "").strip()
    fields = accent_fields(cmap)
    return (
        _frame_template()
        .replace("{{LANG}}", _esc(language or "ru"))
        .replace("{{PRIMARY}}", cmap["primary"])
        .replace("{{ACCENT}}", cmap["accent"])
        .replace("{{MUTED}}", cmap["muted"])
        .replace("{{INK}}", cmap["ink"])
        .replace("{{INK2}}", cmap["ink2"])
        .replace("{{PAPER}}", cmap["paper"])
        .replace("{{SHEET}}", cmap["sheet"])
        .replace("{{RULE}}", cmap["rule"])
        .replace("{{FOIL}}", cmap["foil"])
        .replace("{{PANEL}}", panel)
        .replace("{{ON_ACCENT}}", fields["on_accent"])
        .replace("{{FIELD_B}}", fields["field_b"])
        .replace("{{ON_FIELD_B}}", fields["on_field_b"])
        .replace("{{RAIL}}", fields["rail"])
        .replace("{{ON_RAIL}}", fields["on_rail"])
        .replace("{{LAYOUT}}", _esc(layout))
        .replace("{{PACK}}", _esc(pack))
        .replace("{{BRAND_MARK}}", footer)
        .replace("{{BODY}}", body)
    )


def _copy_fonts(dest_fonts: Path) -> None:
    dest_fonts.mkdir(parents=True, exist_ok=True)
    if not _FONTS_DIR.is_dir():
        return
    for src in _FONTS_DIR.glob("*.woff2"):
        target = dest_fonts / src.name
        if not target.is_file() or target.stat().st_size != src.stat().st_size:
            shutil.copy2(src, target)


def write_slide_work(
    slide: dict[str, Any],
    work_dir: Path,
    *,
    palette: str,
    language: str = "ru",
    chart_png: Path | None = None,
    media_png: Path | None = None,
    style: dict[str, Any] | None = None,
    slide_index: int = 0,
) -> Path:
    """Write index.html (+ fonts + optional media.png) into work_dir."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    _copy_fonts(work_dir / "fonts")
    # Dark Botanical fern texture (Julius image2 twin) for non-hero slides.
    if isinstance(style, dict) and str(style.get("pack_id") or "") == "botanical":
        tex_src = (
            Path(__file__).resolve().parent / "deck_themes" / "botanical_bg.png"
        )
        if tex_src.is_file():
            shutil.copy2(tex_src, work_dir / "botanical_bg.png")
    src_png = media_png if media_png is not None else chart_png
    href: str | None = None
    if src_png is not None and Path(src_png).is_file():
        dest = work_dir / "media.png"
        if Path(src_png).resolve() != dest.resolve():
            dest.write_bytes(Path(src_png).read_bytes())
        # Keep chart.png alias for older allowlist / tests
        chart_alias = work_dir / "chart.png"
        if not chart_alias.is_file():
            shutil.copy2(dest, chart_alias)
        href = "media.png"
    html_doc = render_slide_html(
        slide,
        palette=palette,
        media_png_href=href,
        language=language,
        style=style,
        slide_index=slide_index,
    )
    index = work_dir / "index.html"
    index.write_text(html_doc, encoding="utf-8")
    return index


SLIDE_VIEWPORT = (_SLIDE_W, _SLIDE_H)
