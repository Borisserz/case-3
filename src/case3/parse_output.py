"""Parse LLM reply: ```latex ... ``` then ```json ... ``` (figures + charts)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from case3.chart_html import CHART_TYPES, ChartHtmlError, sanitize_chart_html
from case3.image_prompt import ImagePromptError, sanitize_image_prompt
from case3.tex_safe import sanitize_width
from case3.tex_utils import extract_tex, finish_preamble_only_tex

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


def _append_missing_slots(
    tex: str,
    *,
    chart_ids: list[str],
    figure_ids: list[str],
) -> str:
    """If JSON has media but the LaTeX forgot slots, append them before \\end{document}."""
    have_c = set(_ids(_CHART_SLOT, tex))
    have_f = set(_ids(_FIG_SLOT, tex))
    lines: list[str] = []
    for fid in figure_ids:
        if fid and fid not in have_f:
            lines.append(f"%CASE3_FIG:{fid}%")
    for cid in chart_ids:
        if cid and cid not in have_c:
            lines.append(f"%CASE3_CHART:{cid}%")
    if not lines:
        return tex
    block = "\n" + "\n".join(lines) + "\n"
    if r"\end{document}" in (tex or ""):
        return tex.replace(r"\end{document}", block + r"\end{document}", 1)
    return (tex or "").rstrip() + block


def _json_candidates(raw: str) -> list[str]:
    """All JSON-looking blobs (closed fences + trailing unclosed ```json)."""
    out: list[str] = []
    for m in _FENCE.finditer(raw or ""):
        lang = (m.group(1) or "").lower()
        body = m.group(2).strip()
        if lang == "json" or (lang == "" and body.lstrip().startswith("{")):
            out.append(body)
    # Trailing unclosed ```json … (continuation cut mid-object)
    m_open = re.search(r"```json\s*\n([\s\S]*)$", raw or "", re.I)
    if m_open:
        tail = m_open.group(1).strip()
        if tail and (not out or tail != out[-1]):
            # Only if this region isn't already captured as a closed fence
            closed_spans = [m.span() for m in _FENCE.finditer(raw or "")]
            start = m_open.start(1)
            if not any(a <= start < b for a, b in closed_spans):
                out.append(tail)
    return out


def _pick_fences(raw: str) -> tuple[str | None, str | None]:
    fences = [(m.group(1).lower(), m.group(2).strip()) for m in _FENCE.finditer(raw or "")]
    tex_body = None
    json_body = None
    # Prefer a latex/tex fence that actually contains \documentclass
    for lang, body in fences:
        if lang in ("latex", "tex") and r"\documentclass" in body:
            tex_body = body
            break
    if tex_body is None:
        for lang, body in fences:
            if lang in ("latex", "tex") and tex_body is None:
                tex_body = body
            elif lang in ("",) and r"\documentclass" in body and tex_body is None:
                tex_body = body
    # Prefer the longest JSON that json.loads accepts; else longest candidate.
    best_ok: str | None = None
    best_any: str | None = None
    for body in _json_candidates(raw):
        if best_any is None or len(body) > len(best_any):
            best_any = body
        try:
            json.loads(body)
        except json.JSONDecodeError:
            continue
        if best_ok is None or len(body) > len(best_ok):
            best_ok = body
    json_body = best_ok or best_any
    return tex_body, json_body


def salvage_json_object(raw: str) -> dict[str, Any] | None:
    """Recover figures/charts from truncated or multi-fence JSON.

    Keeps only complete chart/figure objects (valid JSON object substrings).
    """
    figures: list[Any] = []
    charts: list[Any] = []
    seen_fig: set[str] = set()
    seen_cht: set[str] = set()

    blobs = _json_candidates(raw)
    if not blobs and (raw or "").lstrip().startswith("{"):
        blobs = [(raw or "").strip()]
    # Also scan the full raw (fence markers ignored by brace walker) so a chart
    # completed only after a premature ``` close is still recovered.
    if raw and raw not in blobs:
        blobs.append(raw)

    for blob in blobs:
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            for item in data.get("figures") or []:
                if isinstance(item, dict) and str(item.get("id", "")) not in seen_fig:
                    figures.append(item)
                    seen_fig.add(str(item.get("id", "")))
            for item in data.get("charts") or []:
                if isinstance(item, dict) and str(item.get("id", "")) not in seen_cht:
                    charts.append(item)
                    seen_cht.add(str(item.get("id", "")))
            continue

        # Truncated root: scan every `{`; skip unclosed spans (advance by 1).
        i = 0
        while i < len(blob):
            start = blob.find("{", i)
            if start < 0:
                break
            depth = 0
            in_str = False
            esc = False
            end = None
            for j, ch in enumerate(blob[start:], start):
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end is None:
                i = start + 1
                continue
            chunk = blob[start:end]
            i = end
            try:
                obj = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict) or "id" not in obj:
                # Root or wrapper object — keep scanning inside via next `{`.
                if i == end and chunk.startswith("{") and len(chunk) > 2:
                    # already advanced to end; nested objects were skipped.
                    # Re-scan interior by not jumping over children: step in.
                    pass
                continue
            oid = str(obj.get("id", ""))
            if "html" in obj and oid and oid not in seen_cht:
                charts.append(obj)
                seen_cht.add(oid)
            elif "prompt" in obj and oid and oid not in seen_fig:
                figures.append(obj)
                seen_fig.add(oid)

    if not figures and not charts:
        return None
    return {"figures": figures, "charts": charts}


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
        if ctype == "doughnut":
            ctype = "donut"
        if ctype == "pie":
            ctype = "donut"
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


def _merge_media_lists(primary: list[Any], extra: list[Any]) -> list[Any]:
    """Union by id; prefer the entry with longer html/prompt."""
    by_id: dict[str, Any] = {}
    for item in list(primary or []) + list(extra or []):
        if not isinstance(item, dict):
            continue
        oid = str(item.get("id", "")).strip()
        if not oid:
            continue
        prev = by_id.get(oid)
        if prev is None:
            by_id[oid] = item
            continue
        prev_len = len(str(prev.get("html") or prev.get("prompt") or ""))
        new_len = len(str(item.get("html") or item.get("prompt") or ""))
        if new_len > prev_len:
            by_id[oid] = item
    return list(by_id.values())


def _load_media_payload(raw: str, json_body: str | None) -> dict[str, Any]:
    """Load figures/charts dict; salvage complete objects if JSON is truncated."""
    data: dict[str, Any] = {}
    if json_body:
        try:
            parsed = json.loads(json_body)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            pass
    salvaged = salvage_json_object(raw)
    if salvaged:
        charts = _merge_media_lists(data.get("charts") or [], salvaged.get("charts") or [])
        figures = _merge_media_lists(
            data.get("figures") or [], salvaged.get("figures") or []
        )
        if charts or figures:
            if not (data.get("charts") or data.get("figures")):
                log.warning(
                    "salvaged truncated JSON → %d charts, %d figures",
                    len(charts),
                    len(figures),
                )
            elif len(charts) > len(data.get("charts") or []) or len(figures) > len(
                data.get("figures") or []
            ):
                log.warning(
                    "merged salvage into JSON → %d charts, %d figures",
                    len(charts),
                    len(figures),
                )
            return {"figures": figures, "charts": charts}
    return data if isinstance(data, dict) else {}


def _chart_ids_from_data(data: dict[str, Any], *, max_charts: int) -> list[str]:
    if max_charts <= 0:
        return []
    charts = _parse_charts_list(data.get("charts"), max_charts=max_charts)
    return [c["id"] for c in charts]


def _figure_ids_from_data(data: dict[str, Any], *, max_images: int) -> list[str]:
    if max_images <= 0:
        return []
    figs = _parse_figures_list(data.get("figures"), max_images=max_images)
    return [f["id"] for f in figs]


def parse_model_output(
    raw: str,
    *,
    max_images: int,
    max_charts: int = 0,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    tex_body, json_body = _pick_fences(raw)
    data = _load_media_payload(raw, json_body)

    # Peek chart/figure ids early so we can rebuild a body if preamble was truncated.
    early_charts = _chart_ids_from_data(data, max_charts=max_charts)
    early_figs = _figure_ids_from_data(data, max_images=max_images)

    try:
        if tex_body is None:
            tex = extract_tex(raw)
        else:
            if (
                r"\documentclass" in tex_body
                and r"\begin{document}" not in tex_body
            ):
                log.warning(
                    "LaTeX fence is preamble-only — synthesizing \\begin{document} "
                    "with slots for charts=%s figures=%s",
                    early_charts,
                    early_figs,
                )
                tex_body = finish_preamble_only_tex(
                    tex_body,
                    chart_ids=early_charts,
                    figure_ids=early_figs,
                )
            tex = extract_tex("```latex\n" + tex_body + "\n```")
    except ValueError as exc:
        # Last resort: valid JSON charts but unusable TeX → minimal document.
        if early_charts or early_figs:
            log.warning("extract_tex failed (%s) — building minimal doc from JSON ids", exc)
            from case3.tex_utils import _MIN_PREAMBLE

            tex = finish_preamble_only_tex(
                _MIN_PREAMBLE.rstrip() + "\n",
                chart_ids=early_charts,
                figure_ids=early_figs,
            )
        else:
            raise ParseError(str(exc)) from exc

    fig_slots = _ids(_FIG_SLOT, tex) if max_images > 0 else []
    chart_slots = _ids(_CHART_SLOT, tex) if max_charts > 0 else []
    # If caps are 0, ignore leftover slots (inject will strip unknown? we strip via empty status)
    if max_images <= 0:
        fig_slots = []
    if max_charts <= 0:
        chart_slots = []

    need_json = bool(fig_slots or chart_slots)
    if need_json and not data:
        # Truncated model output often has slots but no ```json — drop slots and
        # still return TeX so PDF can build (charts/figures empty this run).
        log.warning(
            "missing ```json with slots figures=%s charts=%s — stripping slots",
            fig_slots,
            chart_slots,
        )
        tex = re.sub(
            r"(?m)^[ \t]*%CASE3_FIG:[a-z][a-z0-9_]{0,31}%[ \t]*\r?\n?",
            "",
            tex,
        )
        tex = _CHART_SLOT_LINE.sub("", tex)
        fig_slots = []
        chart_slots = []

    figures: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    if isinstance(data, dict) and data:
        figures = _parse_figures_list(data.get("figures"), max_images=max_images)
        charts = _parse_charts_list(data.get("charts"), max_charts=max_charts)

    # Id collision across figures and charts
    fig_ids = {f["id"] for f in figures}
    chart_ids = {c["id"] for c in charts}
    clash = fig_ids & chart_ids
    if clash:
        raise ParseError(f"id collision between figures and charts: {sorted(clash)}")

    if max_images > 0 and figures:
        if not fig_slots:
            log.warning(
                "JSON figures without slots — appending %s",
                [f["id"] for f in figures],
            )
            tex = _append_missing_slots(
                tex,
                chart_ids=[],
                figure_ids=[f["id"] for f in figures[:max_images]],
            )
            fig_slots = _ids(_FIG_SLOT, tex)
        by_fig = {f["id"]: f for f in figures}
        aligned_figs = [by_fig[s] for s in fig_slots if s in by_fig][:max_images]
        missing_figs = [s for s in fig_slots if s not in by_fig]
        if missing_figs:
            log.warning("stripping figure slots without valid JSON: %s", missing_figs)
            tex = re.sub(
                r"(?m)^[ \t]*%CASE3_FIG:("
                + "|".join(re.escape(s) for s in missing_figs)
                + r")%[ \t]*\r?\n?",
                "",
                tex,
            )
        figures = aligned_figs
    else:
        if fig_slots:
            tex = re.sub(
                r"(?m)^[ \t]*%CASE3_FIG:[a-z][a-z0-9_]{0,31}%[ \t]*\r?\n?",
                "",
                tex,
            )
        figures = []

    # Charts: soft-fail — drop invalid slots from TeX instead of aborting the run.
    # Critical: if JSON has charts but LaTeX forgot slots, APPEND slots (do not wipe charts).
    if max_charts > 0 and charts:
        if not chart_slots:
            log.warning(
                "JSON charts without slots — appending %s",
                [c["id"] for c in charts],
            )
            tex = _append_missing_slots(
                tex,
                chart_ids=[c["id"] for c in charts[:max_charts]],
                figure_ids=[],
            )
            chart_slots = _ids(_CHART_SLOT, tex)
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
