"""Extract Chart.js labels/series from figures.json HTML for native PPTX charts."""

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


def series_from_figures_json(
    figures: dict[str, Any],
    chart_id: str,
) -> dict[str, Any] | None:
    for ch in figures.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("id") or "") != chart_id:
            continue
        return extract_chart_series(
            str(ch.get("html") or ""),
            chart_type=str(ch.get("type") or ""),
        )
    return None
