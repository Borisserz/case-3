"""Force preferred UI chart types onto model HTML when they diverge."""

from __future__ import annotations

import logging
import re
from typing import Any

from case3.chart_html import CHART_TYPES
from case3.chart_style import (
    apply_kpi_palette_vars,
    apply_palette_to_html,
    normalize_palette_id,
)

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
    elif preferred == "scatter":
        out = _scalar_series_to_scatter_points(out)
    return out


def _scalar_series_to_scatter_points(html: str) -> str:
    """Chart.js scatter needs ``data:[{x,y},…]`` — coerce categorical scalars."""

    def _points(m: re.Match[str]) -> str:
        raw = m.group(1)
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", raw)]
        if not nums:
            return m.group(0)
        # Already point objects?
        if re.search(r"\{\s*x\s*:", raw):
            return m.group(0)
        pts = ",".join(f"{{x:{i},y:{v}}}" for i, v in enumerate(nums))
        return f"data:[{pts}]"

    out = re.sub(
        r"data\s*:\s*\[([^\]]*)\]",
        _points,
        html or "",
        flags=re.I,
    )
    # Scatter ignores category labels; drop to avoid Chart.js axis confusion.
    out = re.sub(r"labels\s*:\s*\[[^\]]*\]\s*,?", "", out, count=1, flags=re.I)
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
    # All datasets — grouped/stacked often ship N pale fills.
    return re.sub(
        r"backgroundColor\s*:\s*'rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)'",
        _bump,
        html or "",
        flags=re.I,
    )


_MAX_CANVAS_H = 560  # D7: tall canvases waste A4 vertical space


def _clamp_canvas_height(html: str, *, max_h: int = _MAX_CANVAS_H) -> str:
    def _cap(m: re.Match[str]) -> str:
        try:
            h = int(m.group(2))
        except ValueError:
            return m.group(0)
        if h <= max_h:
            return m.group(0)
        return f'{m.group(1)}{max_h}{m.group(3)}'

    return re.sub(
        r'(<canvas\b[^>]*\bheight=")(\d+)(")',
        _cap,
        html or "",
        count=1,
        flags=re.I,
    )


def harden_chart_html(html: str, chart_type: str) -> str:
    """Fix sparse / washed-out Chart.js HTML for known types (esp. horizontal_bar)."""
    want = (chart_type or "").strip()
    out = html or ""
    # D7: clamp over-tall print canvases (hbar has its own denser height).
    if want != "horizontal_bar" and out:
        out = _clamp_canvas_height(out)
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
    elif want in {"bar", "grouped_bar", "stacked_bar"} and out:
        out = _solidify_pale_bar_fill(out)
    return out


def _fmt_slice_num(n: float) -> str:
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.1f}".rstrip("0").rstrip(".")


def _parse_donut_slices(
    html: str,
) -> list[tuple[str, float, str]] | None:
    """Pull labels / values / colors from a doughnut Chart.js fragment."""
    if not re.search(r"""type\s*:\s*['"]doughnut['"]""", html or "", flags=re.I):
        return None
    labels_m = re.search(r"labels\s*:\s*\[([^\]]*)\]", html or "")
    data_m = re.search(r"data\s*:\s*\[([^\]]*)\]", html or "")
    colors_m = re.search(r"backgroundColor\s*:\s*\[([^\]]*)\]", html or "", flags=re.I)
    if not labels_m or not data_m:
        return None
    labels = re.findall(r"""['"]([^'"]+)['"]""", labels_m.group(1))
    values = [float(x) for x in re.findall(r"-?[\d.]+", data_m.group(1))]
    colors: list[str] = []
    if colors_m:
        colors = re.findall(
            r"""['"](#[0-9a-fA-F]{3,8}|rgba?\([^)'"]+\))['"]""",
            colors_m.group(1),
            flags=re.I,
        )
    n = min(len(labels), len(values))
    if n < 2:
        return None
    while len(colors) < n:
        colors.append("#6A7160")
    return list(zip(labels[:n], values[:n], colors[:n]))


def _unwrap_donut_layout(html: str) -> str:
    """Strip a prior enhance wrap so palette/LLM edits can rebuild layout."""
    src = html or ""
    if not re.search(r"donut-layout", src, flags=re.I):
        return src
    # Nested .pct/.lbl — non-greedy </div> would stop at the first child.
    src = re.sub(
        r'<div\s+class=["\']donut-center["\']\s*>\s*'
        r'<div\s+class=["\']pct["\']\s*>[\s\S]*?</div>\s*'
        r'<div\s+class=["\']lbl["\']\s*>[\s\S]*?</div>\s*'
        r"</div>",
        "",
        src,
        flags=re.I,
    )
    # Orphan leftovers from older broken unwraps
    src = re.sub(
        r'<div\s+class=["\']lbl["\']\s*>[\s\S]*?</div>\s*',
        "",
        src,
        flags=re.I,
    )
    src = re.sub(
        r'<ul\s+class=["\']valued-legend["\'][\s\S]*?</ul>',
        "",
        src,
        flags=re.I,
    )
    src = re.sub(r"</?div[^>]*\bdonut-viz\b[^>]*>", "", src, flags=re.I)
    src = re.sub(r"</?div[^>]*\bdonut-layout\b[^>]*>", "", src, flags=re.I)
    # Only unwrap outer chart-card when it was the donut shell (avoid nested cards).
    src = re.sub(
        r'<div\s+class=["\'][^"\']*\bchart-card\b[^"\']*["\']\s*>',
        "",
        src,
        count=1,
        flags=re.I,
    )
    src = re.sub(r"</div>\s*$", "", src.strip(), count=1)
    return src.strip()


def enhance_donut_html(html: str) -> str:
    """Wrap doughnut fragment with center % + valued HTML legend when parseable.

    No Chart.js plugins — CSS overlay + list. Rebuilds after unwrap so palette /
    LLM edits keep Mary layout. If JS is too exotic to parse, returns html
    unchanged (prompt recipes still emit the structure).
    """
    src = _unwrap_donut_layout(html or "")
    if not src.strip():
        return src
    slices = _parse_donut_slices(src)
    if not slices:
        return src

    total = sum(v for _, v, _ in slices) or 1.0
    focus_i = max(range(len(slices)), key=lambda i: slices[i][1])
    focus_label, focus_val, _ = slices[focus_i]
    focus_pct = int(round(100.0 * focus_val / total))

    rows: list[str] = []
    for label, val, color in slices:
        pct = int(round(100.0 * val / total))
        rows.append(
            '<li class="valued-legend__row">'
            f'<span class="valued-legend__swatch" style="background:{color}"></span>'
            f'<span class="valued-legend__label">{label}</span>'
            f'<span class="valued-legend__pct">{pct}%</span>'
            f'<span class="valued-legend__abs">{_fmt_slice_num(val)}</span>'
            "</li>"
        )
    legend = '<ul class="valued-legend">' + "".join(rows) + "</ul>"
    center = (
        '<div class="donut-center">'
        f'<div class="pct">{focus_pct}%</div>'
        f'<div class="lbl">{focus_label}</div>'
        "</div>"
    )

    # Canvas + scripts only — ignore leftover unwrap junk around them.
    script_m = re.search(r"(<script\b)", src, flags=re.I)
    tail = src[script_m.start() :] if script_m else ""
    canvas_m = re.search(
        r"<canvas\b[^>]*>\s*</canvas>|<canvas\b[^>]*/?>",
        src,
        flags=re.I,
    )
    if not canvas_m:
        return html or src
    head = canvas_m.group(0)

    # Prefer HTML legend over Chart.js legend to avoid double keys.
    if re.search(r"legend\s*:\s*\{[^}]*display\s*:", tail):
        # Already has display — force false without duplicating the key.
        tail = re.sub(
            r"(legend\s*:\s*\{[^}]*?display\s*:\s*)[^,}\s]+",
            r"\1false",
            tail,
            count=1,
        )
    elif re.search(r"legend\s*:\s*\{", tail):
        tail = re.sub(
            r"legend\s*:\s*\{",
            "legend:{display:false,",
            tail,
            count=1,
        )
    else:
        tail = re.sub(
            r"plugins\s*:\s*\{",
            "plugins:{legend:{display:false},",
            tail,
            count=1,
        )

    # Print frame uses responsive:false — canvas width/height attrs ARE the
    # bitmap. LLM often emits 1100×560 → oval donut + empty right gutter.
    head_sq = _force_square_canvas(head.strip(), size=520)

    wrapped = (
        '<div class="chart-card donut-layout">'
        f'<div class="donut-viz">{center}{head_sq}</div>'
        f"{legend}{tail}"
        "</div>"
    )
    return wrapped


def _force_square_canvas(html: str, *, size: int = 520) -> str:
    """Set first <canvas> to a square bitmap (print Chart.js defaults)."""

    def _repl(m: re.Match[str]) -> str:
        attrs = m.group(1) or ""
        attrs = re.sub(r"\s*width\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)", "", attrs, flags=re.I)
        attrs = re.sub(r"\s*height\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)", "", attrs, flags=re.I)
        attrs = attrs.rstrip()
        return f'<canvas{attrs} width="{size}" height="{size}">'

    return re.sub(r"<canvas(\s[^>]*)?>", _repl, html or "", count=1, flags=re.I)


def polish_charts(
    charts: list[dict[str, Any]],
    *,
    palette_id: str = "auto",
) -> list[dict[str, Any]]:
    """Apply intent palette (if set), donut layout enhance, then geometry harden."""
    from case3.tex_safe import multi_chart_max_frac, sanitize_width

    pid = normalize_palette_id(palette_id)
    dense = len(charts or []) >= 2
    max_w = multi_chart_max_frac() if dense else None
    default_w = r"0.82\textwidth" if dense else r"0.85\textwidth"
    out: list[dict[str, Any]] = []
    for chart in charts:
        c = dict(chart)
        ctype = str(c.get("type") or "").strip()
        html = str(c.get("html") or "")
        if html and pid != "auto" and ctype != "kpi":
            html = apply_palette_to_html(html, pid)
        if html and ctype == "donut":
            html = enhance_donut_html(html)
        # CSS vars after layout wrap so #mount{--kpi-*} sits outside .donut-layout.
        if html and pid != "auto":
            html = apply_kpi_palette_vars(html, pid)
        if html:
            html = harden_chart_html(html, ctype)
        c["html"] = html
        c["width"] = sanitize_width(
            str(c.get("width") or "") or None,
            default=default_w,
            max_frac=max_w,
        )
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
