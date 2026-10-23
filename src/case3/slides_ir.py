"""Parse and validate Liber deck IR (executive slides, Source-bound)."""

from __future__ import annotations

import re
from typing import Any

from case3.chart_style import normalize_palette_id

SLIDE_LAYOUTS = frozenset(
    {
        "title",
        "chart_hero",
        "chart_split",
        "media_hero",
        "media_split",
        "bullets",
        "kpi_row",
        "closing",
        "section",
        "scorecard",
        "callout",
        "table_hero",
        "card_row",
    }
)

_ID_OK = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_CHART_ID_OK = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_MEDIA_ID_OK = re.compile(r"^(cht|fig|usr|dia)_[a-z0-9_]{1,28}$")
_NUMBER_RUN = re.compile(r"\d+(?:[.,]\d+)?")

_MAX_SLIDES = 12
_MIN_SLIDES_SOFT = 8  # prompt prefers 10–12; hard min stays 3
_MAX_TITLE = 80
_MAX_SUBTITLE = 120
_MAX_TAKEAWAY = 120
_MAX_KICKER = 40
_MAX_BULLET = 96
_MAX_BULLETS = 5
_MAX_CAPTION = 160
_MAX_KPI = 4
_MAX_KPI_LABEL = 40
_MAX_KPI_VALUE = 24
_MAX_DELTA = 16
_MAX_TERM = 48
_MAX_DEFINITION = 220
_MAX_CARDS = 3
_MAX_CARD_KICKER = 48
_MAX_CARD_TITLE = 56
_MAX_CARD_BODY = 160
_MAX_TABLE_ROWS = 8
_MAX_TABLE_COLS = 5
_MAX_CELL = 48
_MAX_CONSECUTIVE_BULLETS = 2
_KPI_STATUS = frozenset({"up", "down", "flat"})


class DeckIrError(ValueError):
    """Deck IR rejected."""


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _collect_text_blobs(slide: dict[str, Any]) -> list[str]:
    blobs: list[str] = []
    for key in (
        "title",
        "subtitle",
        "caption",
        "body",
        "kicker",
        "takeaway",
        "term",
        "definition",
    ):
        val = slide.get(key)
        if isinstance(val, str) and val.strip():
            blobs.append(val)
    bullets = slide.get("bullets")
    if isinstance(bullets, list):
        for b in bullets:
            if isinstance(b, str) and b.strip():
                blobs.append(b)
    kpis = slide.get("kpis")
    if isinstance(kpis, list):
        for k in kpis:
            if not isinstance(k, dict):
                continue
            for key in ("label", "value", "hint", "delta"):
                val = k.get(key)
                if isinstance(val, str) and val.strip():
                    blobs.append(val)
    rows = slide.get("rows")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, str) and cell.strip():
                        blobs.append(cell)
    return blobs


def _numbers_in_text(text: str) -> list[str]:
    return _NUMBER_RUN.findall(text or "")


def _number_variants(num: str) -> list[str]:
    n = num or ""
    return list({n, n.replace(",", "."), n.replace(".", ",")})


def _assert_numbers_allowed(
    text: str,
    *,
    source_norm: str,
    allowed: frozenset[str],
) -> None:
    for num in _numbers_in_text(text):
        ok = False
        for v in _number_variants(num):
            if v in allowed or v in source_norm:
                ok = True
                break
        if ok:
            continue
        raise DeckIrError(
            f"number {num!r} not found in Source (and not in allowed chart numbers)"
        )


def _clip_str(val: Any, *, field: str, max_len: int, required: bool = False) -> str:
    if val is None or (isinstance(val, str) and not val.strip()):
        if required:
            raise DeckIrError(f"{field} required")
        return ""
    if not isinstance(val, str):
        raise DeckIrError(f"{field} must be string")
    s = _norm_ws(val)
    if len(s) > max_len:
        raise DeckIrError(f"{field} longer than {max_len} chars")
    return s


def _parse_bullets(raw: Any, *, required: bool) -> list[str]:
    if not isinstance(raw, list) or not raw:
        if required:
            raise DeckIrError("bullets list required")
        return []
    if len(raw) > _MAX_BULLETS:
        raise DeckIrError(f"at most {_MAX_BULLETS} bullets")
    out: list[str] = []
    for i, b in enumerate(raw):
        out.append(
            _clip_str(b, field=f"bullets[{i}]", max_len=_MAX_BULLET, required=True)
        )
    return out


def _parse_cards(raw: Any) -> list[dict[str, str]]:
    """Julius VESPER-style 3-up narrative cards."""
    if not isinstance(raw, list) or not raw:
        raise DeckIrError("card_row requires non-empty cards")
    if len(raw) > _MAX_CARDS:
        raise DeckIrError(f"at most {_MAX_CARDS} cards")
    out: list[dict[str, str]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise DeckIrError(f"cards[{i}] must be object")
        title = _clip_str(
            item.get("title"),
            field=f"cards[{i}].title",
            max_len=_MAX_CARD_TITLE,
            required=True,
        )
        row: dict[str, str] = {"title": title}
        kicker = _clip_str(
            item.get("kicker"),
            field=f"cards[{i}].kicker",
            max_len=_MAX_CARD_KICKER,
        )
        if kicker:
            row["kicker"] = kicker
        body = _clip_str(
            item.get("body"), field=f"cards[{i}].body", max_len=_MAX_CARD_BODY
        )
        if body:
            row["body"] = body
        out.append(row)
    return out


def _parse_kpis(raw: Any, *, allow_delta: bool = False) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not raw:
        raise DeckIrError("kpi_row/scorecard requires non-empty kpis")
    if len(raw) > _MAX_KPI:
        raise DeckIrError(f"at most {_MAX_KPI} kpis")
    out: list[dict[str, str]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise DeckIrError(f"kpis[{i}] must be object")
        label = _clip_str(
            item.get("label"),
            field=f"kpis[{i}].label",
            max_len=_MAX_KPI_LABEL,
            required=True,
        )
        value = _clip_str(
            item.get("value"),
            field=f"kpis[{i}].value",
            max_len=_MAX_KPI_VALUE,
            required=True,
        )
        row: dict[str, str] = {"label": label, "value": value}
        hint = _clip_str(
            item.get("hint"), field=f"kpis[{i}].hint", max_len=_MAX_KPI_LABEL
        )
        if hint:
            row["hint"] = hint
        if allow_delta:
            delta = _clip_str(
                item.get("delta"), field=f"kpis[{i}].delta", max_len=_MAX_DELTA
            )
            if delta:
                row["delta"] = delta
            status = item.get("status")
            if isinstance(status, str) and status.strip().lower() in _KPI_STATUS:
                row["status"] = status.strip().lower()
        out.append(row)
    return out


def _parse_table_rows(raw: Any) -> list[list[str]]:
    if not isinstance(raw, list) or len(raw) < 2:
        raise DeckIrError("table_hero requires rows (header + ≥1 data)")
    if len(raw) > _MAX_TABLE_ROWS:
        raise DeckIrError(f"at most {_MAX_TABLE_ROWS} table rows")
    out: list[list[str]] = []
    width = 0
    for i, row in enumerate(raw):
        if not isinstance(row, list) or not row:
            raise DeckIrError(f"rows[{i}] must be non-empty list")
        if len(row) > _MAX_TABLE_COLS:
            raise DeckIrError(f"at most {_MAX_TABLE_COLS} columns")
        cells = [
            _clip_str(c, field=f"rows[{i}][{j}]", max_len=_MAX_CELL, required=True)
            for j, c in enumerate(row)
        ]
        if i == 0:
            width = len(cells)
        elif len(cells) != width:
            raise DeckIrError("table rows must share the same column count")
        out.append(cells)
    return out


def _parse_slide(
    raw: Any,
    *,
    source_norm: str,
    allowed: frozenset[str],
    seen_ids: set[str],
    allowed_media_ids: frozenset[str] | None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DeckIrError("slide must be object")

    sid = raw.get("id")
    if not isinstance(sid, str) or not _ID_OK.match(sid):
        raise DeckIrError(f"invalid slide id: {sid!r}")
    if sid in seen_ids:
        raise DeckIrError(f"duplicate slide id: {sid}")
    seen_ids.add(sid)

    layout = raw.get("layout")
    if not isinstance(layout, str) or layout not in SLIDE_LAYOUTS:
        raise DeckIrError(f"unknown or missing layout: {layout!r}")

    title = _clip_str(raw.get("title"), field="title", max_len=_MAX_TITLE, required=True)
    out: dict[str, Any] = {"id": sid, "layout": layout, "title": title}
    kicker = _clip_str(raw.get("kicker"), field="kicker", max_len=_MAX_KICKER)
    if kicker:
        out["kicker"] = kicker
    takeaway = _clip_str(raw.get("takeaway"), field="takeaway", max_len=_MAX_TAKEAWAY)
    if takeaway:
        out["takeaway"] = takeaway
    chapter = raw.get("chapter")
    if chapter is not None:
        try:
            ch_i = int(chapter)
        except (TypeError, ValueError) as exc:
            raise DeckIrError("chapter must be int") from exc
        if ch_i < 1 or ch_i > 20:
            raise DeckIrError("chapter out of range")
        out["chapter"] = ch_i
    if raw.get("appendix") is True:
        out["appendix"] = True

    if layout == "title":
        sub = _clip_str(raw.get("subtitle"), field="subtitle", max_len=_MAX_SUBTITLE)
        if sub:
            out["subtitle"] = sub
        mid = raw.get("media_id")
        if isinstance(mid, str) and mid.strip():
            if not _MEDIA_ID_OK.match(mid):
                raise DeckIrError("title media_id must be cht_/fig_/usr_/dia_")
            if allowed_media_ids is not None and mid not in allowed_media_ids:
                raise DeckIrError(f"media_id {mid!r} not available for this run")
            out["media_id"] = mid
    elif layout == "section":
        sub = _clip_str(raw.get("subtitle"), field="subtitle", max_len=_MAX_SUBTITLE)
        if sub:
            out["subtitle"] = sub
    elif layout == "scorecard":
        out["kpis"] = _parse_kpis(raw.get("kpis"), allow_delta=True)
    elif layout == "card_row":
        out["cards"] = _parse_cards(raw.get("cards"))
        sub = _clip_str(raw.get("subtitle"), field="subtitle", max_len=_MAX_SUBTITLE)
        if sub:
            out["subtitle"] = sub
        # Optional gold gate line (Julius VALIDATION GATE / DISCIPLINE).
        gate = _clip_str(raw.get("caption"), field="caption", max_len=_MAX_CAPTION)
        if gate:
            out["caption"] = gate
    elif layout == "callout":
        term = _clip_str(raw.get("term"), field="term", max_len=_MAX_TERM, required=True)
        definition = _clip_str(
            raw.get("definition"),
            field="definition",
            max_len=_MAX_DEFINITION,
            required=True,
        )
        out["term"] = term
        out["definition"] = definition
        body = _clip_str(raw.get("body"), field="body", max_len=220)
        if body:
            out["body"] = body
    elif layout == "table_hero":
        out["rows"] = _parse_table_rows(raw.get("rows"))
        cap = _clip_str(raw.get("caption"), field="caption", max_len=_MAX_CAPTION)
        if cap:
            out["caption"] = cap
    elif layout in ("chart_hero", "chart_split"):
        cid = raw.get("chart_id")
        if not isinstance(cid, str) or not _CHART_ID_OK.match(cid):
            raise DeckIrError(f"{layout} requires valid chart_id")
        if allowed_media_ids is not None and cid not in allowed_media_ids:
            raise DeckIrError(f"chart_id {cid!r} not available for this run")
        out["chart_id"] = cid
        cap = _clip_str(raw.get("caption"), field="caption", max_len=_MAX_CAPTION)
        if cap:
            out["caption"] = cap
        if layout == "chart_split":
            body = _clip_str(raw.get("body"), field="body", max_len=220)
            bullets = _parse_bullets(raw.get("bullets"), required=False)
            if body:
                out["body"] = body
            if bullets:
                out["bullets"] = bullets
            if not body and not bullets:
                # Soft heal: empty split → hero (caption optional)
                out["layout"] = "chart_hero"
                layout = "chart_hero"
    elif layout in ("media_hero", "media_split"):
        mid = raw.get("media_id")
        if not isinstance(mid, str) or not _MEDIA_ID_OK.match(mid):
            raise DeckIrError(f"{layout} requires valid media_id (cht_/fig_/usr_/dia_)")
        if allowed_media_ids is not None and mid not in allowed_media_ids:
            raise DeckIrError(f"media_id {mid!r} not available for this run")
        out["media_id"] = mid
        cap = _clip_str(raw.get("caption"), field="caption", max_len=_MAX_CAPTION)
        if cap:
            out["caption"] = cap
        if layout == "media_split":
            body = _clip_str(raw.get("body"), field="body", max_len=220)
            bullets = _parse_bullets(raw.get("bullets"), required=False)
            if body:
                out["body"] = body
            if bullets:
                out["bullets"] = bullets
            if not body and not bullets:
                out["layout"] = "media_hero"
                layout = "media_hero"
    elif layout == "kpi_row":
        out["kpis"] = _parse_kpis(raw.get("kpis"), allow_delta=False)
    elif layout in ("bullets", "closing"):
        if layout == "bullets":
            out["bullets"] = _parse_bullets(raw.get("bullets"), required=True)
        else:
            # Closing may be hero-bleed (media) or bullet checklist.
            bullets = _parse_bullets(raw.get("bullets"), required=False)
            if bullets:
                out["bullets"] = bullets
            mid = raw.get("media_id")
            if isinstance(mid, str) and mid.strip():
                if not _MEDIA_ID_OK.match(mid):
                    raise DeckIrError("closing media_id must be cht_/fig_/usr_/dia_")
                if allowed_media_ids is not None and mid not in allowed_media_ids:
                    raise DeckIrError(f"media_id {mid!r} not available for this run")
                out["media_id"] = mid
            sub = _clip_str(raw.get("subtitle"), field="subtitle", max_len=_MAX_SUBTITLE)
            if sub:
                out["subtitle"] = sub
            if not bullets and not out.get("media_id"):
                raise DeckIrError("closing requires bullets or media_id")

    for blob in _collect_text_blobs(out):
        _assert_numbers_allowed(blob, source_norm=source_norm, allowed=allowed)

    return out


def _assert_deck_arc(slides: list[dict[str, Any]]) -> None:
    if not slides:
        raise DeckIrError("slides must be a non-empty list")
    if slides[0]["layout"] != "title":
        raise DeckIrError("first slide must be layout title")
    if slides[-1]["layout"] != "closing":
        raise DeckIrError("last slide must be layout closing")
    run = 0
    for s in slides:
        if s["layout"] == "bullets":
            run += 1
            if run > _MAX_CONSECUTIVE_BULLETS:
                raise DeckIrError(
                    f"at most {_MAX_CONSECUTIVE_BULLETS} consecutive bullets slides"
                )
        else:
            run = 0


def parse_deck_ir(
    data: dict[str, Any] | Any,
    *,
    source: str,
    max_slides: int = _MAX_SLIDES,
    allowed_number_strings: frozenset[str] | None = None,
    allowed_media_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Validate and normalize deck IR.

    Raises ``DeckIrError`` on any violation.
    """
    if not isinstance(data, dict):
        raise DeckIrError("deck IR must be an object")

    max_slides = max(1, min(int(max_slides), _MAX_SLIDES))
    source_norm = _norm_ws(source)
    allowed = frozenset(allowed_number_strings or ())
    media_allow = (
        frozenset(allowed_media_ids) if allowed_media_ids is not None else None
    )

    version = data.get("version", 1)
    try:
        version_i = int(version)
    except (TypeError, ValueError) as exc:
        raise DeckIrError("version must be int") from exc
    if version_i != 1:
        raise DeckIrError("unsupported deck IR version")

    aspect = data.get("aspect") or "16:9"
    if aspect != "16:9":
        raise DeckIrError("aspect must be 16:9")

    pid = normalize_palette_id(str(data.get("palette") or "atelier"))
    if pid == "auto":
        pid = "atelier"

    language = data.get("language") or "ru"
    if not isinstance(language, str) or not language.strip():
        language = "ru"
    else:
        language = language.strip()[:16]

    slides_raw = data.get("slides")
    if not isinstance(slides_raw, list) or not slides_raw:
        raise DeckIrError("slides must be a non-empty list")
    if len(slides_raw) > max_slides:
        raise DeckIrError(f"at most {max_slides} slides")
    if len(slides_raw) < 3:
        raise DeckIrError("at least 3 slides (title … closing)")

    seen: set[str] = set()
    slides = [
        _parse_slide(
            s,
            source_norm=source_norm,
            allowed=allowed,
            seen_ids=seen,
            allowed_media_ids=media_allow,
        )
        for s in slides_raw
    ]
    _assert_deck_arc(slides)

    return {
        "version": 1,
        "aspect": "16:9",
        "palette": pid,
        "language": language,
        "slides": slides,
    }
