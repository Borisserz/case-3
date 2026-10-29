"""Liber edit / chart / diagram routes (mounted on main FastAPI app)."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from functools import partial
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from case3.chart_edit import ChartEditError, edit_chart_in_run, preview_chart_html
from case3.chart_html import CHART_TYPES
from case3.chart_style import normalize_palette_id
from case3.diagram_edit import (
    DiagramEditError,
    edit_diagram_in_run,
    regenerate_diagrams_in_run,
)
from case3.figure_edit import FigureEditError, edit_figure_in_run
from case3.llm_client import LLMClient, LLMConfig, LLMConfigError, LLMError
from case3.paragraph_edit import ParagraphEditError, edit_paragraph_in_run
from case3.render import RenderError
from case3.table_edit import TableEditError, edit_table_in_run
from case3.run_store import (
    FILE_OK,
    artifact_downloads,
    build_preview_payload,
    edit_response_envelope,
    formats_from_edit_body,
    load_diagrams_from_out,
    load_figures_json,
    resolve_run_dir,
)

log = logging.getLogger("case3.api_edits")
router = APIRouter(tags=["edits"])


class ChartEditBody(BaseModel):
    palette: str | None = Field(default="atelier")
    style: str | None = Field(default="")
    chart_type: str | None = Field(default="")
    formats: str = Field(default="both")


class ChartPreviewBody(BaseModel):
    """Local live preview (palette + type coerce). Style notes deferred to Apply."""

    palette: str | None = Field(default="atelier")
    chart_type: str | None = Field(default="")


class DiagramEditBody(BaseModel):
    mermaid: str = Field(default="")
    title: str | None = Field(default=None)


class DiagramRegenBody(BaseModel):
    palette: str | None = Field(default="atelier")


class FigureEditBody(BaseModel):
    """mode=generate → POST /generate; mode=edit → POST /edit with current PNG."""

    mode: str = Field(default="generate")
    prompt: str = Field(default="")
    caption: str | None = Field(default=None)
    formats: str = Field(default="both")


class TableEditBody(BaseModel):
    """Structured table replace → patch TeX → rebuild PDF/DOCX."""

    caption: str = Field(default="")
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    formats: str = Field(default="both")


class ParagraphEditBody(BaseModel):
    """Plain prose replace → patch TeX paragraph → rebuild PDF/DOCX."""

    text: str = Field(default="")
    formats: str = Field(default="both")


@router.get("/api/runs/{run_id}/charts/{chart_id}")
def get_run_chart(run_id: str, chart_id: str) -> dict[str, Any]:
    """Chart fragment + meta for Liber live Chart.js (G9/G12)."""
    if not FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = resolve_run_dir(run_id)
    fj = load_figures_json(out_dir)
    charts = fj.get("charts") or []
    chart = next(
        (c for c in charts if isinstance(c, dict) and c.get("id") == chart_id),
        None,
    )
    if not chart:
        raise HTTPException(404, detail="chart not found")
    html = str(chart.get("html") or "").strip()
    if not html:
        raise HTTPException(404, detail="chart html missing")
    return {
        "id": chart_id,
        "type": str(chart.get("type") or "").strip(),
        "caption": str(chart.get("caption") or "").strip(),
        "html": html,
    }


@router.post("/api/runs/{run_id}/charts/{chart_id}/preview")
def preview_run_chart(
    run_id: str, chart_id: str, body: ChartPreviewBody
) -> dict[str, Any]:
    """Local palette/type preview — no PNG/PDF write (Apply still commits)."""
    if not FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = resolve_run_dir(run_id)
    try:
        return preview_chart_html(
            out_dir,
            chart_id,
            palette=body.palette,
            chart_type=body.chart_type,
        )
    except ChartEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/diagrams/{diagram_id}/edit")
async def edit_run_diagram(
    run_id: str, diagram_id: str, body: DiagramEditBody
) -> dict[str, Any]:
    """Save edited Mermaid for one Liber diagram (no PDF/TeX)."""
    if not FILE_OK.match(diagram_id):
        raise HTTPException(400, detail="invalid diagram_id")
    out_dir = resolve_run_dir(run_id)
    try:
        diagram = await asyncio.to_thread(
            partial(
                edit_diagram_in_run,
                out_dir,
                diagram_id,
                mermaid=body.mermaid or "",
                title=body.title,
            )
        )
    except DiagramEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    undo = None
    if isinstance(diagram, dict):
        undo = diagram.pop("undo", None)
    return {
        "diagram": diagram,
        "diagrams": load_diagrams_from_out(out_dir),
        "undo": undo,
    }


@router.get("/api/runs/{run_id}/diagrams/{diagram_id}/svg")
async def download_diagram_svg(run_id: str, diagram_id: str) -> Response:
    """Mermaid → SVG for Liber schema download (no PNG raster)."""
    from case3.diagram_svg import DiagramSvgError, export_diagram_svg, load_diagram_spec

    if not FILE_OK.match(diagram_id):
        raise HTTPException(400, detail="invalid diagram_id")
    out_dir = resolve_run_dir(run_id)
    try:
        meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        meta = {}
    palette = normalize_palette_id(str(meta.get("chart_palette") or "atelier"))
    try:
        spec = load_diagram_spec(out_dir, diagram_id)
        svg = await asyncio.to_thread(
            partial(export_diagram_svg, out_dir, diagram_id, palette=palette)
        )
    except DiagramSvgError as exc:
        raise HTTPException(404 if "not found" in str(exc) else 400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — Playwright missing browsers, etc.
        log.exception("diagram svg render failed run_id=%s id=%s", run_id, diagram_id)
        raise HTTPException(
            503, detail=f"svg render unavailable: {exc}"
        ) from exc
    # ASCII-only filename (Starlette headers are latin-1); UTF-8 title → slug fallback
    raw_title = spec.get("title") or diagram_id
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(raw_title)).strip("-_.")[:48] or diagram_id
    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}.svg"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/api/runs/{run_id}/diagrams/regenerate")
async def regenerate_run_diagrams(
    run_id: str, body: DiagramRegenBody | None = None
) -> dict[str, Any]:
    """Full LLM regenerate of diagrams[] (+ repair). No TeX/PDF."""
    out_dir = resolve_run_dir(run_id)
    palette = normalize_palette_id((body.palette if body else None) or "atelier")
    try:
        result = await asyncio.to_thread(
            partial(
                regenerate_diagrams_in_run,
                out_dir,
                palette=palette,
                client=LLMClient(LLMConfig.from_env()),
            )
        )
    except DiagramEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except (LLMError, LLMConfigError) as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    return {
        "diagrams": result.get("diagrams") or load_diagrams_from_out(out_dir),
        "diagrams_repaired": bool(result.get("diagrams_repaired")),
        "diagrams_ok": int(result.get("diagrams_ok") or 0),
    }


@router.post("/api/runs/{run_id}/charts/{chart_id}/edit")
async def edit_run_chart(run_id: str, chart_id: str, body: ChartEditBody) -> dict[str, Any]:
    """Restyle one chart in-place and rebuild PDF/DOCX (same PNG path → docs update)."""
    if not FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = resolve_run_dir(run_id)
    fmt_set = formats_from_edit_body(body.formats)

    palette = normalize_palette_id(body.palette)
    style = (body.style or "").strip()
    chart_type = (body.chart_type or "").strip()
    if chart_type and chart_type not in CHART_TYPES:
        raise HTTPException(400, detail=f"unknown chart_type: {chart_type}")
    if palette == "auto" and not style and not chart_type:
        raise HTTPException(400, detail="укажите палитру, тип или текст «как изменить»")

    try:
        result = await asyncio.to_thread(
            partial(
                edit_chart_in_run,
                out_dir,
                chart_id,
                palette=palette,
                style=style or None,
                chart_type=chart_type or None,
                formats=fmt_set,
            )
        )
    except ChartEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except (LLMError, LLMConfigError) as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    except RenderError as exc:
        raise HTTPException(500, detail=str(exc)) from exc

    v = int(result.get("version") or 0)
    return edit_response_envelope(
        run_id=run_id,
        out_dir=out_dir,
        result=result,
        bust_needles=(chart_id, "cht_"),
        extra={
            "chart_id": chart_id,
            "mode": result.get("mode"),
            "palette": result.get("palette"),
            "style": result.get("style"),
            "preview_figure": {
                "id": chart_id,
                "kind": "chart",
                "url": f"/api/runs/{run_id}/figures/{chart_id}.png?v={v}",
            },
        },
    )


@router.post("/api/runs/{run_id}/figures/{figure_id}/edit")
async def edit_run_figure(run_id: str, figure_id: str, body: FigureEditBody) -> dict[str, Any]:
    """Regenerate (generate) or img2img-edit one photo; rebuild PDF/DOCX."""
    if not FILE_OK.match(figure_id):
        raise HTTPException(400, detail="invalid figure_id")
    if figure_id.startswith("cht_"):
        raise HTTPException(400, detail="use /charts/{id}/edit for charts")
    out_dir = resolve_run_dir(run_id)

    mode = (body.mode or "generate").strip().lower()
    if mode not in {"generate", "edit"}:
        raise HTTPException(400, detail="mode must be generate|edit")
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, detail="prompt required")

    fmt_set = formats_from_edit_body(body.formats)
    caption = (body.caption or "").strip() or None

    try:
        result = await asyncio.to_thread(
            partial(
                edit_figure_in_run,
                out_dir,
                figure_id,
                mode=mode,  # type: ignore[arg-type]
                prompt=prompt,
                caption=caption,
                formats=fmt_set,
            )
        )
    except FigureEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except RenderError as exc:
        raise HTTPException(500, detail=str(exc)) from exc

    v = int(result.get("version") or 0)
    return edit_response_envelope(
        run_id=run_id,
        out_dir=out_dir,
        result=result,
        bust_needles=(figure_id,),
        extra={
            "figure_id": figure_id,
            "mode": result.get("mode"),
            "prompt": result.get("prompt"),
            "caption": result.get("caption"),
            "preview_figure": {
                "id": figure_id,
                "kind": "figure",
                "url": f"/api/runs/{run_id}/figures/{figure_id}.png?v={v}",
            },
        },
    )


@router.post("/api/runs/{run_id}/tables/{table_index}/edit")
async def edit_run_table(
    run_id: str, table_index: int, body: TableEditBody
) -> dict[str, Any]:
    """Replace one preview table (caption + grid) and rebuild PDF/DOCX."""
    out_dir = resolve_run_dir(run_id)
    if table_index < 1:
        raise HTTPException(400, detail="table_index must be ≥ 1")

    fmt_set = formats_from_edit_body(body.formats)
    headers = [str(h) for h in (body.headers or [])]
    rows = [[str(c) for c in row] for row in (body.rows or [])]
    caption = str(body.caption or "")

    try:
        result = await asyncio.to_thread(
            partial(
                edit_table_in_run,
                out_dir,
                table_index,
                caption=caption,
                headers=headers,
                rows=rows,
                formats=fmt_set,
            )
        )
    except TableEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except RenderError as exc:
        raise HTTPException(500, detail=str(exc)) from exc

    return edit_response_envelope(
        run_id=run_id,
        out_dir=out_dir,
        result=result,
        extra={
            "table_index": table_index,
            "caption": result.get("caption"),
        },
    )


@router.post("/api/runs/{run_id}/paragraphs/{paragraph_index}/edit")
async def edit_run_paragraph(
    run_id: str, paragraph_index: int, body: ParagraphEditBody
) -> dict[str, Any]:
    """Replace one preview paragraph (para-N) and rebuild PDF/DOCX."""
    out_dir = resolve_run_dir(run_id)
    if paragraph_index < 1:
        raise HTTPException(400, detail="paragraph_index must be ≥ 1")

    fmt_set = formats_from_edit_body(body.formats)

    try:
        result = await asyncio.to_thread(
            partial(
                edit_paragraph_in_run,
                out_dir,
                paragraph_index,
                text=str(body.text or ""),
                formats=fmt_set,
            )
        )
    except ParagraphEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except RenderError as exc:
        raise HTTPException(500, detail=str(exc)) from exc

    return edit_response_envelope(
        run_id=run_id,
        out_dir=out_dir,
        result=result,
        extra={
            "paragraph_index": paragraph_index,
            "text": result.get("text"),
        },
    )


@router.post("/api/runs/{run_id}/undo")
async def undo_last_edit(run_id: str) -> dict[str, Any]:
    """Restore the single undo snapshot from the last successful Liber edit."""
    from case3.run_undo import UndoError, apply_undo

    out_dir = resolve_run_dir(run_id)
    try:
        result = await asyncio.to_thread(partial(apply_undo, out_dir, rebuild=True))
    except UndoError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    media: dict[str, Any] = {}
    meta_path = out_dir / "meta.json"
    if meta_path.is_file():
        try:
            media = (json.loads(meta_path.read_text(encoding="utf-8")) or {}).get(
                "media_status"
            ) or {}
        except (OSError, json.JSONDecodeError):
            media = {}
    if not isinstance(media, dict):
        media = {}
    v = int(time.time())
    preview = build_preview_payload(run_id, out_dir, media)
    for block in preview.get("blocks") or []:
        if isinstance(block, dict) and block.get("type") == "figure" and block.get("url"):
            url = str(block["url"])
            sep = "&" if "?" in url else "?"
            block["url"] = f"{url}{sep}v={v}"

    return {
        "run_id": run_id,
        "status": "ok",
        "undone": {"kind": result.get("kind"), "target": result.get("target")},
        "downloads": artifact_downloads(run_id, out_dir, v),
        "preview": preview,
        "undo": None,
        "warnings": (
            [str(result["rebuild_error"])] if result.get("rebuild_error") else []
        ),
    }


