"""Extract / persist Chart.js series for native PPTX charts."""

from __future__ import annotations

import re
from typing import Any

# Types we can map to python-pptx chart kinds.
NATIVE_CHART_TYPES = frozenset(
    {
        "bar",
        "grouped_bar",
        "stacked_bar",
        "line",
        "horizontal_bar",
        "area",
        "donut",
    }
)

_LABELS = re.compile(r"labels\s*:\s*\[([^\]]*)\]", re.I | re.S)
_DATASET = re.compile(
    r"\{[^{}]*?label\s*:\s*(['\"])(?P<label>.*?)\1[^{}]*?data\s*:\s*\[(?P<data>[^\]]*)\]",
    re.I | re.S,
)
_DATASET_DATA_FIRST = re.compile(
    r"\{[^{}]*?data\s*:\s*\[(?P<data>[^\]]*)\][^{}]*?label\s*:\s*(['\"])(?P<label>.*?)\2",
    re.I | re.S,
)
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _parse_labels(blob: str) -> list[str]:
    return re.findall(r"""['"]([^'"]*)['"]""", blob or "")


def _parse_numbers(blob: str) -> list[float]:
    out: list[float] = []
    for m in _NUM.finditer(blob or ""):
        try:
            out.append(float(m.group(0)))
        except ValueError:
            continue
    return out


def normalize_series_ir(raw: Any, *, default_type: str = "bar") -> dict[str, Any] | None:
    """Validate ChartSeriesIR shape; return a clean copy or None."""
    if not isinstance(raw, dict):
        return None
    cats = list(raw.get("categories") or [])
    series = list(raw.get("series") or [])
    if not cats or not series:
        return None
    cleaned: list[dict[str, Any]] = []
    for s in series:
        if not isinstance(s, dict):
            continue
        vals = list(s.get("values") or [])
        nums: list[float] = []
        for v in vals:
            try:
                nums.append(float(v))
            except (TypeError, ValueError):
                continue
        if not nums:
            continue
        cleaned.append(
            {
                "name": str(s.get("name") or "Series").strip() or "Series",
                "values": nums,
            }
        )
    if not cleaned:
        return None
    n_cat = min(len(cats), min(len(s["values"]) for s in cleaned))
    if n_cat < 1:
        return None
    ctype = str(raw.get("type") or default_type).strip().lower() or "bar"
    if ctype not in NATIVE_CHART_TYPES:
        ctype = "bar"
    return {
        "type": ctype,
        "categories": [str(c) for c in cats[:n_cat]],
        "series": [
            {"name": s["name"], "values": s["values"][:n_cat]} for s in cleaned
        ],
    }


def extract_chart_series(
    html: str,
    *,
    chart_type: str | None = None,
) -> dict[str, Any] | None:
    """Return ChartSeriesIR or None if not extractable / not native-eligible."""
    ctype = (chart_type or "").strip().lower() or "bar"
    if ctype == "kpi" or ctype == "scatter":
        return None
    if ctype not in NATIVE_CHART_TYPES and ctype not in ("bar", "line"):
        # Still try bar/line-shaped data for unknown types
        if "labels" not in (html or "") or "data:" not in (html or ""):
            return None

    labels_m = _LABELS.search(html or "")
    if not labels_m:
        return None
    categories = _parse_labels(labels_m.group(1))
    if not categories:
        return None

    series: list[dict[str, Any]] = []
    for rx in (_DATASET, _DATASET_DATA_FIRST):
        for m in rx.finditer(html or ""):
            values = _parse_numbers(m.group("data"))
            if not values:
                continue
            n = min(len(categories), len(values))
            if n < 1:
                continue
            series.append(
                {
                    "name": (m.group("label") or "Series").strip() or "Series",
                    "values": values[:n],
                }
            )
        if series:
            break

    if not series:
        # Single anonymous data:[] near labels
        data_m = re.search(r"data\s*:\s*\[([^\]]*)\]", html or "", re.I)
        if not data_m:
            return None
        values = _parse_numbers(data_m.group(1))
        n = min(len(categories), len(values))
        if n < 1:
            return None
        series = [{"name": "Series", "values": values[:n]}]

    # Align category length to shortest series
    n_cat = min(len(categories), min(len(s["values"]) for s in series))
    return {
        "type": ctype if ctype in NATIVE_CHART_TYPES else "bar",
        "categories": categories[:n_cat],
        "series": [
            {"name": s["name"], "values": s["values"][:n_cat]} for s in series
        ],
    }


def _donut_series_name(chart: dict[str, Any], current: str) -> str:
    """Prefer caption/title over anonymous Chart.js 'Series' for donut legend."""
    cur = (current or "").strip()
    if cur and cur.lower() not in ("series", "dataset", "data"):
        return cur
    for key in ("caption", "title", "label"):
        val = str(chart.get(key) or "").strip()
        if val:
            return val[:48]
    return "Доля"


def attach_series_ir(chart: dict[str, Any]) -> dict[str, Any] | None:
    """Persist native-eligible series on a chart dict; return IR or None."""
    if not isinstance(chart, dict):
        return None
    ctype = str(chart.get("type") or "").strip().lower()
    if ctype in ("kpi", "scatter"):
        chart.pop("series", None)
        return None
    existing = normalize_series_ir(chart.get("series"), default_type=ctype or "bar")
    if existing:
        if existing["type"] == "donut":
            for s in existing["series"]:
                s["name"] = _donut_series_name(chart, str(s.get("name") or ""))
        chart["series"] = existing
        return existing
    ir = extract_chart_series(
        str(chart.get("html") or ""),
        chart_type=ctype or None,
    )
    if not ir:
        chart.pop("series", None)
        return None
    if ir["type"] == "donut":
        for s in ir["series"]:
            s["name"] = _donut_series_name(chart, str(s.get("name") or ""))
    chart["series"] = ir
    return ir


def attach_series_ir_to_charts(charts: list[Any] | None) -> int:
    """Attach series IR to each chart; return how many got IR."""
    n = 0
    for ch in charts or []:
        if isinstance(ch, dict) and attach_series_ir(ch):
            n += 1
    return n


def series_from_figures_json(
    figures: dict[str, Any],
    chart_id: str,
) -> dict[str, Any] | None:
    for ch in figures.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("id") or "") != chart_id:
            continue
        stored = normalize_series_ir(
            ch.get("series"),
            default_type=str(ch.get("type") or "bar"),
        )
        if stored:
            return stored
        ir = extract_chart_series(
            str(ch.get("html") or ""),
            chart_type=str(ch.get("type") or ""),
        )
        if ir:
            ch["series"] = ir
        return ir
    return None


def series_map_from_figures(figures: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """All native-eligible chart ids → series IR from figures.json."""
    out: dict[str, dict[str, Any]] = {}
    for ch in figures.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        cid = str(ch.get("id") or "").strip()
        if not cid.startswith("cht_"):
            continue
        ir = series_from_figures_json(figures, cid)
        if ir:
            out[cid] = ir
    return out


def _deck_chart_ids(deck: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for s in deck.get("slides") or []:
        if not isinstance(s, dict):
            continue
        for key in ("chart_id", "media_id"):
            mid = str(s.get(key) or "").strip()
            if mid.startswith("cht_"):
                out.add(mid)
    return out


def _chart_hero_slide(cid: str, *, title: str | None = None) -> dict[str, Any]:
    return {
        "id": f"s_native_{cid}",
        "layout": "chart_hero",
        "kicker": "DATA",
        "title": title or "Ключевые цифры",
        "chart_id": cid,
        "caption": "Источник — Source",
        "takeaway": "Цифры из Source",
    }


def ensure_deck_charts(
    deck: dict[str, Any],
    series_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Ensure every native-eligible cht_* appears on a slide. Return injected ids."""
    if not series_by_id:
        return []
    present = _deck_chart_ids(deck)
    missing = sorted(set(series_by_id.keys()) - present)
    if not missing:
        return []
    slides = list(deck.get("slides") or [])
    close_i = next(
        (
            i
            for i, s in enumerate(slides)
            if isinstance(s, dict) and str(s.get("layout") or "") == "closing"
        ),
        None,
    )
    if close_i is not None:
        insert_at = close_i
    elif slides and str(slides[0].get("layout") or "") == "title":
        insert_at = 1
    else:
        insert_at = len(slides)
    injected: list[str] = []
    for j, cid in enumerate(missing):
        slides.insert(
            insert_at + j,
            _chart_hero_slide(cid, title=f"График {cid}"),
        )
        injected.append(cid)
    deck["slides"] = slides
    return injected
