"""Force preferred UI chart types onto model HTML when they diverge."""

from __future__ import annotations

import logging
import re
from typing import Any

from case3.chart_html import CHART_TYPES
from case3.chart_style import apply_palette_to_html, normalize_palette_id

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


def _is_kpi_html(html: str) -> bool:
    return bool(re.search(r"""class\s*=\s*['"]kpi['"]""", html or "", flags=re.I))


def html_matches_type(html: str, want: str) -> bool:
    """True when fragment already looks like the catalog type."""
    h = html or ""
    if want == "kpi":
        return _is_kpi_html(h)
    if want == "donut":
        return bool(re.search(r"""type\s*:\s*['"]doughnut['"]""", h, flags=re.I))
    if want == "scatter":
        return bool(re.search(r"""type\s*:\s*['"]scatter['"]""", h, flags=re.I))
    if want == "line":
        # area is also type:line — require no fill:true for plain line
        if not re.search(r"""type\s*:\s*['"]line['"]""", h, flags=re.I):
            return False
        return not re.search(r"""fill\s*:\s*true""", h, flags=re.I)
    if want == "area":
        return bool(re.search(r"""type\s*:\s*['"]line['"]""", h, flags=re.I)) and bool(
            re.search(r"""fill\s*:\s*true""", h, flags=re.I)
        )
    if want == "horizontal_bar":
        return bool(re.search(r"""type\s*:\s*['"]bar['"]""", h, flags=re.I)) and (
            "indexAxis" in h
        )
    if want == "stacked_bar":
        return bool(re.search(r"""type\s*:\s*['"]bar['"]""", h, flags=re.I)) and (
            "stacked" in h
        )
    if want in {"bar", "grouped_bar"}:
        return bool(re.search(r"""type\s*:\s*['"]bar['"]""", h, flags=re.I))
    return True


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
        else:
            out = re.sub(r"""fill\s*:\s*false""", "fill:true", out, count=1, flags=re.I)
    elif preferred == "line":
        # drop fill:true if model emitted an area-like line
        out = re.sub(r"""fill\s*:\s*true\s*,?""", "", out, count=1, flags=re.I)
    elif preferred == "stacked_bar":
        if "stacked" not in out:
            out = re.sub(
                r"options\s*:\s*\{",
                "options:{scales:{x:{stacked:true},y:{stacked:true}},",
                out,
                count=1,
            )
    return out


def _kpi_html_from_chart(chart: dict[str, Any]) -> str:
    """Build Liber-style KPI block from caption / dataset numbers."""
    caption = str(chart.get("caption") or "").strip() or "Показатель"
    html = str(chart.get("html") or "")
    value = None
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*%?",
        caption,
    )
    if m:
        value = m.group(1).replace(",", ".")
    if value is None:
        m = re.search(r"data\s*:\s*\[\s*([\d.]+)", html)
        if m:
            value = m.group(1)
    if value is None:
        # several KPI numbers in caption: "выручка 152, рост 12"
        nums = re.findall(r"\d+(?:[.,]\d+)?", caption)
        if nums:
            value = nums[0].replace(",", ".")
    if value is None:
        value = "—"
    label = re.sub(r"\s*\d+(?:[.,]\d+)?\s*%?\s*", " ", caption).strip(" —–-") or caption
    return (
        f'<div class="kpi"><div class="value">{value}</div>'
        f'<div class="label">{label}</div></div>'
        "<script>requestAnimationFrame(function(){"
        "requestAnimationFrame(function(){"
        "window.__CASE3_CHART_READY=true;});});</script>"
    )


def _count_labels(html: str) -> int:
    m = re.search(r"labels\s*:\s*\[([^\]]*)\]", html or "")
    if not m:
        return 4
    n = len(re.findall(r"""['"]([^'"]+)['"]""", m.group(1)))
    return max(1, n)


def _solidify_pale_bar_fill(html: str) -> str:
    """Turn ghostly rgba(…,0.18) bar fills into readable solid / mid-alpha ink."""

    def _bump(m: re.Match[str]) -> str:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            alpha = float(m.group(4))
        except ValueError:
            alpha = 1.0
        if alpha >= 0.45:
            return m.group(0)
        return f"backgroundColor:'#{r:02X}{g:02X}{b:02X}'"

    # Only touch scalar backgroundColor (not arrays of segment colors).
    return re.sub(
        r"backgroundColor\s*:\s*'rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)'",
        _bump,
        html or "",
        count=1,
        flags=re.I,
    )


def harden_chart_html(html: str, chart_type: str) -> str:
    """Fix sparse / washed-out Chart.js HTML for known types (esp. horizontal_bar)."""
    want = (chart_type or "").strip()
    out = html or ""
    if want == "horizontal_bar" and out:
        n = _count_labels(out)
        h = max(300, min(420, 88 + n * 52))
        out = re.sub(
            r'(<canvas\b[^>]*\bheight=")(\d+)(")',
            rf"\g<1>{h}\3",
            out,
            count=1,
            flags=re.I,
        )
        if re.search(r"barPercentage\s*:", out):
            out = re.sub(r"barPercentage\s*:\s*[\d.]+", "barPercentage:0.78", out, count=1)
        else:
            out = re.sub(
                r"(datasets\s*:\s*\[\s*\{)",
                r"\1barPercentage:0.78,categoryPercentage:0.88,",
                out,
                count=1,
            )
        if re.search(r"categoryPercentage\s*:", out):
            out = re.sub(
                r"categoryPercentage\s*:\s*[\d.]+",
                "categoryPercentage:0.88",
                out,
                count=1,
            )
        if "borderRadius" not in out:
            out = re.sub(
                r"(datasets\s*:\s*\[\s*\{)",
                r"\1borderRadius:6,",
                out,
                count=1,
            )
        out = _solidify_pale_bar_fill(out)
    elif want in {"bar", "grouped_bar"} and out:
        out = _solidify_pale_bar_fill(out)
    return out


def polish_charts(
    charts: list[dict[str, Any]],
    *,
    palette_id: str = "auto",
) -> list[dict[str, Any]]:
    """Apply intent palette (if set) then geometry harden per chart type."""
    pid = normalize_palette_id(palette_id)
    out: list[dict[str, Any]] = []
    for chart in charts:
        c = dict(chart)
        ctype = str(c.get("type") or "").strip()
        html = str(c.get("html") or "")
        if html and ctype != "kpi" and pid != "auto":
            html = apply_palette_to_html(html, pid)
        if html:
            html = harden_chart_html(html, ctype)
        c["html"] = html
        out.append(c)
    return out


def apply_type_to_chart(chart: dict[str, Any], want: str) -> dict[str, Any]:
    """Force catalog type + matching HTML onto one chart dict."""
    if want not in CHART_TYPES:
        return chart
    c = dict(chart)
    html = str(c.get("html") or "")
    if want == "kpi":
        if not _is_kpi_html(html):
            c["html"] = _kpi_html_from_chart(c)
            log.info("forced kpi markup on %s (was type=%s)", c.get("id"), chart.get("type"))
        c["type"] = "kpi"
        return c
    if html and not html_matches_type(html, want):
        c["html"] = _rewrite_js_type(html, want)
        log.info(
            "rewrote chart %s html for type %s → %s",
            c.get("id"),
            chart.get("type"),
            want,
        )
    elif html and c.get("type") != want:
        c["html"] = _rewrite_js_type(html, want)
        log.info(
            "coerced chart %s type %s → %s",
            c.get("id"),
            chart.get("type"),
            want,
        )
    c["type"] = want
    c["html"] = harden_chart_html(str(c.get("html") or ""), want)
    return c


def coerce_chart_types(
    charts: list[dict[str, Any]],
    preferred: list[str],
) -> list[dict[str, Any]]:
    """Align charts[i] to preferred[i] when both are whitelisted.

    Also repairs HTML when the model already set the right `type` but left
    mismatched markup (classic: type=kpi + Chart.js canvas bar).
    """
    prefs = [p for p in preferred if p in CHART_TYPES]
    if not prefs or not charts:
        return [ensure_chart_html_matches_declared_type(c) for c in charts]
    out: list[dict[str, Any]] = []
    for i, chart in enumerate(charts):
        want = prefs[i] if i < len(prefs) else None
        if want:
            out.append(apply_type_to_chart(chart, want))
        else:
            out.append(ensure_chart_html_matches_declared_type(chart))
    return out


def ensure_chart_html_matches_declared_type(chart: dict[str, Any]) -> dict[str, Any]:
    """When charts[].type says X, make HTML actually look like X (auto mode too)."""
    want = str(chart.get("type") or "").strip()
    if want not in CHART_TYPES:
        return chart
    html = str(chart.get("html") or "")
    if html_matches_type(html, want):
        return chart
    return apply_type_to_chart(chart, want)


def ensure_all_charts_match_types(charts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ensure_chart_html_matches_declared_type(c) for c in charts]
