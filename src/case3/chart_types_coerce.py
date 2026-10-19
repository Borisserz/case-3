"""Force preferred UI chart types onto model HTML when they diverge."""

from __future__ import annotations

import logging
import re
from typing import Any

from case3.chart_html import CHART_TYPES

log = logging.getLogger("case3.charts")

# Chart.js constructor `type` (donut → doughnut).
_JS_TYPE = {
    "bar": "bar",
    "grouped_bar": "bar",
    "stacked_bar": "bar",
    "line": "line",
    "horizontal_bar": "bar",
    "donut": "doughnut",
    "area": "line",
    "scatter": "scatter",
    "kpi": "kpi",
}


def _rewrite_js_type(html: str, preferred: str) -> str:
    js = _JS_TYPE.get(preferred, preferred)
    out = re.sub(
        r"""type\s*:\s*['"](?:bar|line|doughnut|pie|scatter|radar)['"]""",
        f"type:'{js}'",
        html,
        count=1,
        flags=re.I,
    )
    if preferred == "horizontal_bar":
        if "indexAxis" not in out:
            out = re.sub(
                r"options\s*:\s*\{",
                "options:{indexAxis:'y',",
                out,
                count=1,
            )
    elif preferred == "area":
        if re.search(r"fill\s*:", out) is None:
            out = re.sub(
                r"(datasets\s*:\s*\[\s*\{)",
                r"\1fill:true,",
                out,
                count=1,
            )
    elif preferred == "stacked_bar":
        if "stacked" not in out:
            out = re.sub(
                r"options\s*:\s*\{",
                "options:{scales:{x:{stacked:true},y:{stacked:true}},",
                out,
                count=1,
            )
    return out


def coerce_chart_types(
    charts: list[dict[str, Any]],
    preferred: list[str],
) -> list[dict[str, Any]]:
    """Align charts[i].type (+ HTML) to preferred[i] when both are whitelisted."""
    prefs = [p for p in preferred if p in CHART_TYPES]
    if not prefs or not charts:
        return charts
    out: list[dict[str, Any]] = []
    for i, chart in enumerate(charts):
        c = dict(chart)
        want = prefs[i] if i < len(prefs) else None
        if not want or c.get("type") == want:
            out.append(c)
            continue
        if want == "kpi":
            # Cannot safely invent KPI markup — keep model chart, log only.
            log.warning(
                "chart %s type=%s but preferred kpi — leaving model html",
                c.get("id"),
                c.get("type"),
            )
            out.append(c)
            continue
        html = str(c.get("html") or "")
        if want != "kpi" and html:
            c["html"] = _rewrite_js_type(html, want)
        log.info(
            "coerced chart %s type %s → %s",
            c.get("id"),
            chart.get("type"),
            want,
        )
        c["type"] = want
        out.append(c)
    return out
