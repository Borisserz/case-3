"""FastAPI demo wrapper around run_pipeline (for React UI)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from case3.chart_html import CHART_TYPES
from case3.chart_style import intent_palette_lines, normalize_palette_id, palette_public
from case3.charts import max_charts_from_env
from case3.envfile import load_dotenv
from case3.generate import max_images_from_env
from case3.llm_client import LLMConfigError, LLMError
from case3.parse_output import ParseError
from case3.pipeline import PipelineError, run_pipeline
from case3.render import IMAGE, RenderError, ensure_image

log = logging.getLogger("case3.api")

_RUN_ID_OK = re.compile(r"^[A-Za-z0-9_.-]+$")
_FILE_OK = re.compile(r"^[A-Za-z0-9_.-]+$")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    cand = here.parents[2]
    if (cand / "Dockerfile").is_file():
        return cand
    return Path.cwd()


ROOT = _repo_root()
load_dotenv(ROOT / ".env")

app = FastAPI(title="case-3 demo", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> RedirectResponse:
    """Redirect API root to OpenAPI docs; UI is on :5173."""
    return RedirectResponse("/docs")


_CHART_TYPE_LIST = ", ".join(sorted(CHART_TYPES))


def build_intent_from_ui(
    *,
    chat: str,
    chart_types: list[str],
    max_charts: int,
    max_images: int,
    forbid_charts: bool,
    forbid_images: bool,
    chart_hints: str = "",
    chart_auto: bool = False,
    chart_palette: str = "editorial",
    chart_style: str = "",
) -> str:
    """Compose Intent from chat + UI controls.

    chart_auto / empty chart_types → model picks type from CHART_TYPES by Source.
    chart_hints → free-text wishes (pie, «воронка»…); model maps to whitelist or skips.
    chart_palette / chart_style → color preset + optional look notes.
    max_* are ceilings, not quotas.
    """
    parts: list[str] = []
    chat = (chat or "").strip()
    if chat:
        parts.append(chat)
    req: list[str] = ["Требования UI:"]
    hints = (chart_hints or "").strip()
    clean = [t for t in chart_types if t in CHART_TYPES]
    auto = bool(chart_auto) or (not clean and not hints)
    palette = normalize_palette_id(chart_palette)

    if forbid_charts or max_charts <= 0:
        req.append("- без графиков и диаграмм")
    else:
        req.append(
            f"- не больше {max_charts} HTML-графиков (Chart.js); 0 OK если чисел мало; "
            "если в Source есть числа/даты/доли — сделай полезные диаграммы, "
            "не раздувай charts ради квоты"
        )
        req.append(
            f"- JSON charts[].type — только: {_CHART_TYPE_LIST} "
            "(pie→donut, столбцы→bar, тренд→line, топ-N→horizontal_bar, KPI→kpi)"
        )
        req.append(
            "- при 2+ графиках — РАЗНЫЕ типы (например line+donut или bar+horizontal_bar)"
        )
        req.extend(intent_palette_lines(palette, chart_style))
        req.append(
            "- caption на русском, конкретный (что сравниваем); "
            "canvas 1100×560; без фиолетового нейрослопа"
        )
        req.append(
            "- слот %CASE3_CHART:id% один на строке, БЕЗ обёртки \\begin{figure}; "
            "числа только из Source"
        )
        req.append(
            "- вёрстка: A4 portrait; широкие таблицы — tabularx{\\textwidth}{…} "
            "или колонки p{…}/X, не landscape и не tabular{lll} с длинным текстом"
        )
        if auto and not hints:
            req.append(
                "- типы на усмотрение модели по смыслу данных (playbook time→line, "
                "share→donut, compare→bar/grouped_bar)"
            )
        elif clean:
            req.append("- предпочитай типы: " + ", ".join(clean))
        if hints:
            req.append(f"- пожелания по виду/типу: {hints} (сведи к whitelist или пропусти)")
    if forbid_images or max_images <= 0:
        req.append("- без картинок и иллюстраций Kandinsky")
    else:
        req.append(
            f"- до {max_images} Kandinsky figures: только конкретная сцена/объект из Source"
        )
        req.append(
            "- figures[].caption — русская подпись к рисунку; "
            "figures[].prompt — English, visual, no Cyrillic/watermark/tiny text; "
            "не дублируй числами то, что уже в charts"
        )
    parts.append("\n".join(req))
    return "\n\n".join(parts).strip()


def _parse_chart_types(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;\s]+", raw.strip())
    return [p for p in parts if p in CHART_TYPES]


def _as_bool(raw: str | bool | None) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


@app.get("/api/health")
def health() -> dict[str, Any]:
    docker_ok = False
    docker_err = None
    try:
        ensure_image()
        docker_ok = True
    except Exception as exc:  # noqa: BLE001
        docker_err = str(exc)[:200]

    playwright_ok = False
    try:
        from playwright.sync_api import sync_playwright

        from case3.charts import _run_sync_playwright

        def _probe() -> None:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()

        _run_sync_playwright(_probe)
        playwright_ok = True
    except Exception as exc:  # noqa: BLE001
        log.info("playwright check failed: %s", exc)

    vision = bool(os.environ.get("VISION_API_BASE_URL", "").strip())
    kandinsky = bool(
        os.environ.get("KANDINSKY_API_BASE_URL", "").strip()
        or os.environ.get("IMAGE_API_BASE_URL", "").strip()
    )
    return {
        "ok": docker_ok and vision,
        "docker_image": IMAGE,
        "docker_ok": docker_ok,
        "docker_error": docker_err,
        "playwright_ok": playwright_ok,
        "vision_configured": vision,
        "kandinsky_configured": kandinsky,
        "defaults": {
            "max_charts": max_charts_from_env(),
            "max_images": max_images_from_env(),
        },
        "chart_types": sorted(CHART_TYPES),
        "chart_palettes": palette_public(),
    }


@app.get("/api/chart-types")
def chart_types() -> dict[str, Any]:
    return {"types": sorted(CHART_TYPES), "palettes": palette_public()}


@app.post("/api/run")
async def api_run(
    source: UploadFile | None = File(None),
    source_text: str | None = Form(None),
    intent: str = Form(""),
    max_charts: int | None = Form(None),
    max_images: int | None = Form(None),
    chart_types: str = Form(""),
    chart_hints: str = Form(""),
    chart_auto: str = Form("false"),
    chart_palette: str = Form("editorial"),
    chart_style: str = Form(""),
    forbid_charts: str = Form("false"),
    forbid_images: str = Form("false"),
    formats: str = Form("both"),
    dry_run: str = Form("false"),
) -> dict[str, Any]:
    no_charts = _as_bool(forbid_charts)
    no_images = _as_bool(forbid_images)
    is_dry = _as_bool(dry_run)
    is_auto = _as_bool(chart_auto)
    if max_charts is None:
        max_charts = max_charts_from_env()
    if max_images is None:
        max_images = max_images_from_env()
    if no_charts:
        max_charts = 0
    if no_images:
        max_images = 0
    max_charts = max(0, min(int(max_charts), 8))
    max_images = max(0, min(int(max_images), 8))

    types = [] if is_auto else _parse_chart_types(chart_types)
    full_intent = build_intent_from_ui(
        chat=intent,
        chart_types=types,
        max_charts=max_charts,
        max_images=max_images,
        forbid_charts=no_charts,
        forbid_images=no_images,
        chart_hints=chart_hints or "",
        chart_auto=is_auto,
        chart_palette=chart_palette or "editorial",
        chart_style=chart_style or "",
    )

    fmt_raw = (formats or "both").strip().lower()
    if fmt_raw == "both":
        fmt_set = {"pdf", "docx"}
    elif fmt_raw in {"pdf", "docx"}:
        fmt_set = {fmt_raw}
    else:
        raise HTTPException(400, detail="formats must be pdf|docx|both")

    # Persist as .../uploads/<stamp>/source.txt so run_id stem stays "source_*"
    upload_dir = ROOT / "runs" / "uploads" / datetime_stamp()
    upload_dir.mkdir(parents=True, exist_ok=True)
    src_path = upload_dir / "source.txt"

    if source is not None and source.filename:
        name = Path(source.filename).name
        if not name.lower().endswith((".txt", ".md")):
            raise HTTPException(400, detail="source file must be .txt or .md")
        data = await source.read()
        if len(data) > 2 * 1024 * 1024:
            raise HTTPException(400, detail="source file too large (>2 MiB)")
        src_path.write_bytes(data)
    elif source_text and source_text.strip():
        src_path.write_text(source_text.strip(), encoding="utf-8")
    else:
        raise HTTPException(400, detail="provide source file or source_text")

    try:
        # Playwright sync API cannot run inside FastAPI's asyncio loop.
        out_dir = await asyncio.to_thread(
            partial(
                run_pipeline,
                src_path,
                project_root=ROOT,
                formats=fmt_set,
                dry_run=is_dry,
                intent=full_intent,
                max_images=max_images,
                max_charts=max_charts,
            )
        )
    except PipelineError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(exc),
                "run_id": exc.run_id,
                "max_charts": (exc.meta or {}).get("max_charts"),
                "max_images": (exc.meta or {}).get("max_images"),
                "dry_run": (exc.meta or {}).get("dry_run"),
                "hint": "logs: runs\\logs\\"
                + exc.run_id
                + " — then scripts\\push-debug.cmd",
            },
        ) from exc
    except (LLMConfigError, LLMError, ParseError, RenderError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("api run failed")
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc

    run_id = out_dir.name
    meta_path = out_dir / "meta.json"
    meta: dict[str, Any] = {}
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    files: dict[str, str] = {}
    for art in out_dir.iterdir():
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            files[art.suffix.lower().lstrip(".")] = f"/api/runs/{run_id}/files/{art.name}"

    media = meta.get("media_status") or {}
    chart_ids = set(meta.get("charts_planned") or [])
    fig_ids = set(meta.get("figures_planned") or [])
    charts_ok = sum(
        1 for cid in chart_ids if isinstance(media.get(cid), dict) and media[cid].get("ok")
    )
    figs_ok = sum(
        1 for fid in fig_ids if isinstance(media.get(fid), dict) and media[fid].get("ok")
    )

    previews = _media_previews(run_id, out_dir, media)

    return {
        "run_id": run_id,
        "status": meta.get("status", "ok"),
        "intent": full_intent,
        "max_charts": max_charts,
        "max_images": max_images,
        "figures_planned": meta.get("figures_planned") or [],
        "charts_planned": meta.get("charts_planned") or [],
        "media_status": media,
        "charts_ok": charts_ok,
        "figures_ok": figs_ok,
        "files": files,
        "downloads": files,
        "previews": previews,
        "error": meta.get("error"),
        "warnings": _warnings(meta, max_images=max_images),
    }


def _media_previews(
    run_id: str, out_dir: Path, media: dict[str, Any]
) -> list[dict[str, str]]:
    """PNG thumbnails that succeeded (charts / Kandinsky) under out/figures/."""
    figs = out_dir / "figures"
    if not figs.is_dir():
        return []
    out: list[dict[str, str]] = []
    for png in sorted(figs.glob("*.png")):
        mid = png.stem
        st = media.get(mid) if isinstance(media.get(mid), dict) else {}
        if st and not st.get("ok"):
            continue
        if not png.is_file():
            continue
        kind = str(st.get("kind") or ("chart" if mid.startswith("cht_") else "figure"))
        out.append(
            {
                "id": mid,
                "kind": kind,
                "url": f"/api/runs/{run_id}/figures/{png.name}",
            }
        )
    return out


def _warnings(meta: dict[str, Any], *, max_images: int) -> list[str]:
    warnings: list[str] = []
    planned = meta.get("figures_planned") or []
    media = meta.get("media_status") or {}
    if planned and max_images > 0:
        if not os.environ.get("KANDINSKY_API_BASE_URL", "").strip():
            warnings.append("Kandinsky API URL empty — figure slots stripped")
        else:
            failed = [
                fid
                for fid in planned
                if not (isinstance(media.get(fid), dict) and media[fid].get("ok"))
            ]
            if failed:
                warnings.append(f"figures failed/skipped: {', '.join(failed)}")
    c_planned = meta.get("charts_planned") or []
    if c_planned:
        failed_c = [
            cid
            for cid in c_planned
            if not (isinstance(media.get(cid), dict) and media[cid].get("ok"))
        ]
        if failed_c:
            warnings.append(f"charts failed/skipped: {', '.join(failed_c)}")
    return warnings


def datetime_stamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_run_file(run_id: str, *parts: str) -> Path:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    for part in parts:
        if not _FILE_OK.match(part) or ".." in part or "/" in part or "\\" in part:
            raise HTTPException(400, detail="invalid path")
    path = (ROOT / "runs" / "out" / run_id).joinpath(*parts).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(path).startswith(str(out_root)) or not path.is_file():
        raise HTTPException(404, detail="file not found")
    return path


@app.get("/api/runs/{run_id}/files/{name}")
def download_file(run_id: str, name: str) -> FileResponse:
    path = _safe_run_file(run_id, name)
    media = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    if path.suffix.lower() == ".docx":
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif path.suffix.lower() == ".png":
        media = "image/png"
    return FileResponse(path, media_type=media, filename=path.name)


@app.get("/api/runs/{run_id}/figures/{name}")
def download_figure(run_id: str, name: str) -> FileResponse:
    if not name.lower().endswith(".png"):
        raise HTTPException(400, detail="only PNG figures")
    path = _safe_run_file(run_id, "figures", name)
    return FileResponse(path, media_type="image/png", filename=path.name)
