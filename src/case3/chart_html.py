"""Sanitize LLM HTML chart fragments and wrap in offline Chart.js frame."""

from __future__ import annotations

import re
from pathlib import Path

CHART_TYPES = frozenset(
    {
        "bar",
        "grouped_bar",
        "stacked_bar",
        "line",
        "horizontal_bar",
        "donut",
        "kpi",
        "heatmap",
        "area",
        "scatter",
        "waterfall",
        "treemap",
    }
)

_MAX_HTML_BYTES = 80 * 1024
# Keep inline <script> for Chart.js; drop remote/host tags.
_FORBIDDEN_TAGS = re.compile(
    r"<(?:iframe|object|embed|link|base|meta|form)\b[^>]*>.*?</(?:iframe|object|embed|link|base|meta|form)>\s*"
    r"|<(?:iframe|object|embed|link|base|meta|form)\b[^>]*/?>"
    r"|<script\b[^>]+src\s*=[^>]*>.*?</script>",
    re.I | re.S,
)
_ON_ATTR = re.compile(r"\son[a-z]+\s*=\s*(['\"]).*?\1", re.I | re.S)
_ON_ATTR_UQ = re.compile(r"\son[a-z]+\s*=\s*[^\s>]+", re.I)
_REMOTE_URL = re.compile(
    r"""(?i)(?:src|href|action|data-src)\s*=\s*(['"])\s*(?:https?:|//|javascript:)[^'"]*\1"""
)
_REMOTE_URL_UQ = re.compile(
    r"""(?i)(?:src|href|action|data-src)\s*=\s*(?:https?:|//|javascript:)[^\s>]+"""
)


class ChartHtmlError(ValueError):
    """HTML chart fragment rejected."""


def sanitize_chart_html(html: str) -> str:
    text = (html or "").strip()
    if not text:
        raise ChartHtmlError("empty chart html")
    if len(text.encode("utf-8")) > _MAX_HTML_BYTES:
        raise ChartHtmlError(f"chart html exceeds {_MAX_HTML_BYTES} bytes")
    text = re.sub(r"(?is)<!DOCTYPE[^>]*>", "", text)
    text = re.sub(r"(?is)</?(?:html|head|body)\b[^>]*>", "", text)
    text = _FORBIDDEN_TAGS.sub("", text)
    text = _ON_ATTR.sub("", text)
    text = _ON_ATTR_UQ.sub("", text)
    text = _REMOTE_URL.sub("", text)
    text = _REMOTE_URL_UQ.sub("", text)
    text = text.strip()
    if not text:
        raise ChartHtmlError("chart html empty after sanitize")
    return text


def assets_charts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "charts"


def frame_template_path() -> Path:
    return Path(__file__).resolve().parent / "templates" / "chart_frame.html"


def wrap_chart_page(*, fragment: str, chart_js_href: str = "./chart.umd.min.js") -> str:
    tpl = frame_template_path().read_text(encoding="utf-8")
    return tpl.replace("{{CHART_JS}}", chart_js_href).replace("{{FRAGMENT}}", fragment)
