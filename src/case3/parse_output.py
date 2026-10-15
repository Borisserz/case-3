"""Parse LLM reply: ```latex ... ``` then ```json ... ``` (figures + charts)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from case3.chart_html import CHART_TYPES, ChartHtmlError, sanitize_chart_html
from case3.image_prompt import ImagePromptError, sanitize_image_prompt
from case3.tex_safe import sanitize_width
from case3.tex_utils import extract_tex

log = logging.getLogger("case3.parse")

_FENCE = re.compile(r"```(\w*)\s*([\s\S]*?)```", re.I)
_ID_OK = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
# Same line-anchored pattern as inject (slots must be alone on a line).
_FIG_SLOT = re.compile(r"(?m)^[ \t]*%CASE3_FIG:([a-z][a-z0-9_]{0,31})%[ \t]*\r?$")
_CHART_SLOT = re.compile(r"(?m)^[ \t]*%CASE3_CHART:([a-z][a-z0-9_]{0,31})%[ \t]*\r?$")
_CHART_SLOT_LINE = re.compile(
    r"(?m)^[ \t]*%CASE3_CHART:([a-z][a-z0-9_]{0,31})%[ \t]*\r?\n?"
)


class ParseError(ValueError):
    """Model output does not satisfy the dual-fence / slot contract."""


def _ids(pattern: re.Pattern[str], tex: str) -> list[str]:
    seen: list[str] = []
    for m in pattern.finditer(tex or ""):
        fid = m.group(1)
        if fid not in seen:
            seen.append(fid)
    return seen


def _strip_chart_slots(tex: str, keep: set[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        return m.group(0) if m.group(1) in keep else ""

    return _CHART_SLOT_LINE.sub(repl, tex)


def _pick_fences(raw: str) -> tuple[str | None, str | None]:
    fences = [(m.group(1).lower(), m.group(2).strip()) for m in _FENCE.finditer(raw or "")]
    tex_body = None
    json_body = None
    for lang, body in fences:
        if lang in ("latex", "tex") and tex_body is None:
            tex_body = body
        elif lang == "json" and json_body is None:
            json_body = body
        elif lang in ("",) and json_body is None and body.lstrip().startswith("{"):
            json_body = body
    return tex_body, json_body


def _parse_figures_list(raw_figs: Any, *, max_images: int) -> list[dict[str, Any]]:
    figures: list[dict[str, Any]] = []
    if not isinstance(raw_figs, list) or max_images <= 0:
        return figures
    for item in raw_figs:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("id", "")).strip()
        prompt_raw = str(item.get("prompt", "")).strip()
        if not _ID_OK.match(fid) or not prompt_raw:
            continue
        try:
            prompt = sanitize_image_prompt(prompt_raw)
        except ImagePromptError as exc:
            log.warning("drop figure %s: bad prompt (%s)", fid, exc)
            continue
        figures.append(
            {
                "id": fid,
                "caption": str(item.get("caption", "")).strip() or fid,
                "prompt": prompt,
                "width": sanitize_width(str(item.get("width", "")) or None),
            }
        )
        if len(figures) >= max_images:
            break
    return figures


def _parse_charts_list(raw_charts: Any, *, max_charts: int) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    if not isinstance(raw_charts, list) or max_charts <= 0:
        return charts
    for item in raw_charts:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id", "")).strip()
        ctype = str(item.get("type", "")).strip().lower()
        html_raw = str(item.get("html", "")).strip()
        if not _ID_OK.match(cid) or ctype not in CHART_TYPES or not html_raw:
            continue
        try:
            html = sanitize_chart_html(html_raw)
        except ChartHtmlError as exc:
            log.warning("drop chart %s: bad html (%s)", cid, exc)
            continue
        charts.append(
            {
                "id": cid,
                "type": ctype,
                "caption": str(item.get("caption", "")).strip() or cid,
                "html": html,
                "width": sanitize_width(str(item.get("width", "")) or None),
            }
        )
        if len(charts) >= max_charts:
            break
    return charts


def _align(
    slots: list[str],
    items: list[dict[str, Any]],
    *,
    kind: str,
    max_n: int,
) -> list[dict[str, Any]]:
    by_id = {x["id"]: x for x in items}
    aligned = [by_id[s] for s in slots if s in by_id]
    missing = [s for s in slots if s not in by_id]
    if missing:
        raise ParseError(
            f"{kind} slot(s) without valid JSON entry: {missing}"
        )
    return aligned[:max_n]


def parse_model_output(
    raw: str,
    *,
    max_images: int,
    max_charts: int = 0,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    tex_body, json_body = _pick_fences(raw)

    if tex_body is None:
        tex = extract_tex(raw)
        if r"\documentclass" not in tex and r"\begin{document}" not in tex:
            raise ParseError("missing ```latex fence with full document")
    else:
        tex = extract_tex("```latex\n" + tex_body + "\n```")

    fig_slots = _ids(_FIG_SLOT, tex) if max_images > 0 else []
    chart_slots = _ids(_CHART_SLOT, tex) if max_charts > 0 else []
    # If caps are 0, ignore leftover slots (inject will strip unknown? we strip via empty status)
    if max_images <= 0:
        fig_slots = []
    if max_charts <= 0:
        chart_slots = []

    need_json = bool(fig_slots or chart_slots)
    if need_json and json_body is None:
        raise ParseError(
            f"TeX has slots (figures={fig_slots}, charts={chart_slots}) but missing ```json fence"
        )

    figures: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    data: Any = {}
    if json_body is not None:
        try:
            data = json.loads(json_body)
        except json.JSONDecodeError as exc:
            if need_json:
                raise ParseError(f"invalid JSON fence while slots present: {exc}") from exc
            log.warning("invalid JSON fence ignored (no slots): %s", exc)
            data = {}
        if isinstance(data, dict):
            figures = _parse_figures_list(data.get("figures"), max_images=max_images)
            charts = _parse_charts_list(data.get("charts"), max_charts=max_charts)

    # Id collision across figures and charts
    fig_ids = {f["id"] for f in figures}
    chart_ids = {c["id"] for c in charts}
    clash = fig_ids & chart_ids
    if clash:
        raise ParseError(f"id collision between figures and charts: {sorted(clash)}")

    if max_images > 0 and fig_slots:
        figures = _align(fig_slots, figures, kind="figure", max_n=max_images)
    else:
        figures = []

    # Charts: soft-fail — drop invalid slots from TeX instead of aborting the run.
    if max_charts > 0 and chart_slots:
        by_id = {c["id"]: c for c in charts}
        aligned = [by_id[s] for s in chart_slots if s in by_id][:max_charts]
        missing = [s for s in chart_slots if s not in by_id]
        if missing:
            log.warning("stripping chart slots without valid JSON/html: %s", missing)
        keep = {c["id"] for c in aligned}
        tex = _strip_chart_slots(tex, keep)
        charts = aligned
    else:
        if chart_slots or _ids(_CHART_SLOT, tex):
            tex = _strip_chart_slots(tex, set())
        charts = []

    return tex, figures, charts
