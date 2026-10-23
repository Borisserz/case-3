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
        out = _ensure_scatter_point_size(out)
    return out


_SCATTER_RADIUS = 10
_SCATTER_HOVER = 14


def _ensure_scatter_point_size(html: str) -> str:
    """Scatter defaults are tiny (r≈3) — bump for print + Liber draft."""
    out = html or ""

    def _bump(key: str, floor: int, target: int) -> None:
        nonlocal out

        def _repl(m: re.Match[str]) -> str:
            try:
                v = float(m.group(2))
            except ValueError:
                return f"{m.group(1)}{target}"
            if v >= floor:
                return m.group(0)
            return f"{m.group(1)}{target}"

        out = re.sub(
            rf"({key}\s*:\s*)([\d.]+)",
            _repl,
            out,
            flags=re.I,
        )

    _bump("pointRadius", 8, _SCATTER_RADIUS)
    _bump("pointHoverRadius", 11, _SCATTER_HOVER)
    if not re.search(r"pointRadius\s*:", out, flags=re.I):
        out = re.sub(
            r"(datasets\s*:\s*\[\s*\{)",
            rf"\1pointRadius:{_SCATTER_RADIUS},pointHoverRadius:{_SCATTER_HOVER},borderWidth:2,",
            out,
            count=1,
            flags=re.I,
        )
    elif not re.search(r"pointHoverRadius\s*:", out, flags=re.I):
        out = re.sub(
            r"(pointRadius\s*:\s*[\d.]+)",
            rf"\1,pointHoverRadius:{_SCATTER_HOVER}",
            out,
            count=1,
            flags=re.I,
        )
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


def _ensure_stack_segment_gaps(html: str) -> str:
    """White borders between stacked segments so multi-hue series stay separable."""
    out = html or ""
    stacked = bool(
        re.search(r"stack\s*:", out, flags=re.I)
        or re.search(r"stacked\s*:\s*true", out, flags=re.I)
    )
    if not stacked:
        return out
    if re.search(r"borderColor\s*:\s*['\"]#fff", out, flags=re.I):
        return out

    def _inject_open(m: re.Match[str]) -> str:
        return m.group(1) + "borderWidth:1,borderColor:'#ffffff',"

    out = re.sub(r"(datasets\s*:\s*\[\s*\{)", _inject_open, out, count=1, flags=re.I)
    out = re.sub(
        r"(\}\s*,\s*\{)(?=[^\}]{0,200}stack\s*:)",
        r"\1borderWidth:1,borderColor:'#ffffff',",
        out,
        flags=re.I,
    )
    return out


def _count_datasets(html: str) -> int:
    """Count top-level objects in ``datasets:[...]`` (ignore scatter ``{x,y}`` points)."""
    m = re.search(r"datasets\s*:\s*\[", html or "", flags=re.I)
    if not m:
        return 0
    i = m.end()
    n = 0
    depth = 0  # brace depth relative to array contents
    in_str: str | None = None
    escape = False
    while i < len(html):
        ch = html[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
            i += 1
            continue
        if ch == "]" and depth == 0:
            break
        if ch == "{":
            if depth == 0:
                n += 1
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == "[":
            # nested array (e.g. data:[{x,y},…]) — track via braces only;
            # entering `[` at depth>0 is inside a dataset object already.
            pass
        i += 1
    return n


def _set_plugin_bool(html: str, plugin: str, key: str, value: str) -> str:
    """Set ``plugins.{plugin}.{key}`` to ``value`` (true/false), creating nests if needed."""
    src = html or ""
    # plugin:{ ... key: X → replace
    pat_key = re.compile(
        rf"({plugin}\s*:\s*\{{[^}}]*?\b{key}\s*:\s*)([^,}}\s]+)",
        flags=re.I | re.S,
    )
    if pat_key.search(src):
        return pat_key.sub(rf"\g<1>{value}", src, count=1)
    # plugin:{ → inject key
    pat_obj = re.compile(rf"({plugin}\s*:\s*\{{)", flags=re.I)
    if pat_obj.search(src):
        return pat_obj.sub(rf"\1{key}:{value},", src, count=1)
    # plugins:{ → inject plugin:{key:value}
    if re.search(r"plugins\s*:\s*\{", src, flags=re.I):
        return re.sub(
            r"plugins\s*:\s*\{",
            f"plugins:{{{plugin}:{{{key}:{value}}},",
            src,
            count=1,
            flags=re.I,
        )
    # options:{ → inject plugins
    if re.search(r"options\s*:\s*\{", src, flags=re.I):
        return re.sub(
            r"options\s*:\s*\{",
            f"options:{{plugins:{{{plugin}:{{{key}:{value}}}}},",
            src,
            count=1,
            flags=re.I,
        )
    return src


def ensure_legend_and_tooltips(html: str, chart_type: str) -> str:
    """Turn on tooltips always; Chart.js legend for multi-series (HTML valued-legend wins for donut)."""
    want = (chart_type or "").strip()
    out = html or ""
    if not out or want == "kpi":
        return out

    out = _set_plugin_bool(out, "tooltip", "enabled", "true")

    has_valued = bool(re.search(r"valued-legend", out, flags=re.I))
    n_ds = _count_datasets(out)
    want_js_legend = False
    if want == "donut" or has_valued:
        want_js_legend = False
    elif want in {"grouped_bar", "stacked_bar", "line", "area"}:
        want_js_legend = True
    elif n_ds >= 2:
        want_js_legend = True

    if want_js_legend:
        out = _set_plugin_bool(out, "legend", "display", "true")
        # Prefer bottom so it doesn't steal plot height on print.
        if not re.search(r"legend\s*:\s*\{[^}]*position\s*:", out, flags=re.I | re.S):
            out = re.sub(
                r"(legend\s*:\s*\{)",
                r"\1position:'bottom',",
                out,
                count=1,
                flags=re.I,
            )
    else:
        # Frame defaults legend:true — hide for single-series / valued-legend / scatter.
        out = _set_plugin_bool(out, "legend", "display", "false")

    return out


def _ensure_line_point_size(html: str) -> str:
    """Line/area markers readable in print (default Chart.js r≈3 is tiny)."""
    out = html or ""

    def _bump(m: re.Match[str]) -> str:
        try:
            v = float(m.group(2))
        except ValueError:
            return f"{m.group(1)}5"
        if v >= 5:
            return m.group(0)
        return f"{m.group(1)}5"

    out = re.sub(r"(pointRadius\s*:\s*)([\d.]+)", _bump, out, flags=re.I)
    if not re.search(r"pointRadius\s*:", out, flags=re.I):
        out = re.sub(
            r"(datasets\s*:\s*\[\s*\{)",
            r"\1pointRadius:5,pointHoverRadius:8,",
            out,
            count=1,
            flags=re.I,
        )
    return out


def _colorize_hbar_categories(html: str, palette_id: str = "atelier") -> str:
    """Single-series hbar: one accent per category bar (not one flat wash)."""
    out = html or ""
    if re.search(r"backgroundColor\s*:\s*\[", out, flags=re.I):
        return out
    n = _count_labels(out)
    if n < 2:
        return out
    from case3.chart_style import _PALETTES

    pid = normalize_palette_id(palette_id)
    if pid == "auto" or pid not in _PALETTES:
        pid = "atelier"
    p = _PALETTES[pid]
    ladder = [str(p["primary"]).upper(), *[str(a).upper() for a in p["accents"]]]
    colors_list = [ladder[i % len(ladder)] for i in range(n)]
    colors = ",".join(f"'{c}'" for c in colors_list)
    out = re.sub(
        r"backgroundColor\s*:\s*'[^']+'",
        f"backgroundColor:[{colors}]",
        out,
        count=1,
        flags=re.I,
    )
    out = re.sub(r"borderWidth\s*:\s*\d+\s*,?", "", out, count=1, flags=re.I)
    out = re.sub(r"borderColor\s*:\s*'[^']+'\s*,?", "", out, count=1, flags=re.I)
    return out


def harden_chart_html(
    html: str,
    chart_type: str,
    *,
    palette_id: str = "auto",
) -> str:
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
        out = _colorize_hbar_categories(out, palette_id)
    elif want in {"bar", "grouped_bar", "stacked_bar"} and out:
        out = _solidify_pale_bar_fill(out)
        if want == "stacked_bar":
            out = _ensure_stack_segment_gaps(out)
    elif want == "scatter" and out:
        out = _ensure_scatter_point_size(out)
    elif want in {"line", "area"} and out:
        out = _ensure_line_point_size(out)
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


def _clean_slice_label(label: str) -> str:
    """Strip embedded % / absolutes so valued-legend columns stay single-purpose."""
    s = (label or "").strip()
    if not s:
        return s
    # "Retail 42% (210)" / "Food (140)" / "Pharma — 18%"
    s = re.sub(r"\s*[\(（]\s*[\d\s.,]+\s*[\)）]\s*$", "", s)
    s = re.sub(r"\s*[-–—·|:]\s*\d+(?:[.,]\d+)?\s*%\s*$", "", s)
    s = re.sub(r"\s+\d+(?:[.,]\d+)?\s*%\s*$", "", s)
    s = re.sub(r"\s+\d+(?:[.,]\d+)?\s*%", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ·—-|:")
    return s or (label or "").strip()


def _rewrite_chart_labels_array(html: str, labels: list[str]) -> str:
    if not labels:
        return html or ""
    quoted = ",".join("'" + lab.replace("\\", "\\\\").replace("'", "\\'") + "'" for lab in labels)
    return re.sub(
        r"labels\s*:\s*\[[^\]]*\]",
        f"labels:[{quoted}]",
        html or "",
        count=1,
        flags=re.I,
    )


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

    clean_slices = [
        (_clean_slice_label(lab), val, color) for lab, val, color in slices
    ]
    src = _rewrite_chart_labels_array(src, [lab for lab, _, _ in clean_slices])

    total = sum(v for _, v, _ in clean_slices) or 1.0
    focus_i = max(range(len(clean_slices)), key=lambda i: clean_slices[i][1])
    focus_label, focus_val, _ = clean_slices[focus_i]
    focus_pct = int(round(100.0 * focus_val / total))

    rows: list[str] = []
    for label, val, color in clean_slices:
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


def _hide_legend_if_unnamed_dataset(html: str) -> str:
    """Donut→bar leaves datasets without ``label`` → Chart.js legend shows «undefined»."""
    src = html or ""
    # Count dataset objects that already have an explicit label key.
    ds_blocks = re.findall(r"datasets\s*:\s*\[([^\]]*)\]", src, flags=re.I)
    if not ds_blocks:
        return src
    body = ds_blocks[0]
    # Multiple labeled series keep the legend; unlabeled single series → hide.
    labeled = len(re.findall(r"""\blabel\s*:\s*['"]""", body))
    series = len(re.findall(r"\{", body))
    if series >= 2 and labeled >= 1:
        return src
    if re.search(r"legend\s*:\s*\{[^}]*display\s*:", src, flags=re.I):
        return re.sub(
            r"(legend\s*:\s*\{[^}]*?display\s*:\s*)[^,}\s]+",
            r"\1false",
            src,
            count=1,
        )
    if re.search(r"legend\s*:\s*\{", src, flags=re.I):
        return re.sub(r"legend\s*:\s*\{", "legend:{display:false,", src, count=1)
    if re.search(r"plugins\s*:\s*\{", src, flags=re.I):
        return re.sub(
            r"plugins\s*:\s*\{",
            "plugins:{legend:{display:false},",
            src,
            count=1,
        )
    if re.search(r"options\s*:\s*\{", src, flags=re.I):
        return re.sub(
            r"options\s*:\s*\{",
            "options:{plugins:{legend:{display:false}},",
            src,
            count=1,
        )
    return src


def _landscape_canvas_if_square(html: str, *, width: int = 1100, height: int = 560) -> str:
    """Donut print uses 520×520 — after leaving donut, restore a landscape bitmap."""

    def _repl(m: re.Match[str]) -> str:
        attrs = m.group(1) or ""
        wm = re.search(r"\bwidth\s*=\s*[\"']?(\d+)", attrs, flags=re.I)
        hm = re.search(r"\bheight\s*=\s*[\"']?(\d+)", attrs, flags=re.I)
        if not wm or not hm:
            return m.group(0)
        try:
            w, h = int(wm.group(1)), int(hm.group(1))
        except ValueError:
            return m.group(0)
        if w != h or w > 640:
            return m.group(0)
        attrs = re.sub(r"\s*width\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)", "", attrs, flags=re.I)
        attrs = re.sub(r"\s*height\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)", "", attrs, flags=re.I)
        attrs = attrs.rstrip()
        return f'<canvas{attrs} width="{width}" height="{height}">'

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
            html = harden_chart_html(html, ctype, palette_id=pid)
            html = ensure_legend_and_tooltips(html, ctype)
        c["html"] = html
        if pid != "auto":
            c["palette"] = pid
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
        # KPI cards are not Chart.js — drop donut chrome if present.
        html = _unwrap_donut_layout(html) if "donut-layout" in html.lower() else html
        c["html"] = html
        if not _is_kpi_html(html):
            c["html"] = _kpi_html_from_chart(c)
            log.info("forced kpi markup on %s (was type=%s)", c.get("id"), chart.get("type"))
        c["type"] = "kpi"
        return c
    # Leaving donut (or any leftover Mary wrap) → plain canvas+script first.
    left_donut = False
    if want != "donut" and html and re.search(r"donut-layout", html, flags=re.I):
        html = _unwrap_donut_layout(html)
        html = _landscape_canvas_if_square(html)
        c["html"] = html
        left_donut = True
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
    html_out = str(c.get("html") or "")
    if want == "donut" and html_out:
        html_out = enhance_donut_html(html_out)
    elif left_donut or (
        want in {"bar", "horizontal_bar", "line", "area"} and html_out
    ):
        html_out = _hide_legend_if_unnamed_dataset(html_out)
    c["html"] = ensure_legend_and_tooltips(harden_chart_html(html_out, want), want)
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
