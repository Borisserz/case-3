"""FastAPI demo wrapper around run_pipeline (for React UI)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel, Field

from case3.chart_edit import ChartEditError, edit_chart_in_run, preview_chart_html
from case3.chart_html import CHART_TYPES
from case3.chart_style import intent_palette_lines, normalize_palette_id, palette_public
from case3.charts import max_charts_from_env
from case3.deck_theme import list_public_packs, normalize_pack_id
from case3.diagram_edit import (
    DiagramEditError,
    edit_diagram_in_run,
    regenerate_diagrams_in_run,
)
from case3.diagrams import max_diagrams_from_env
from case3.envfile import load_dotenv
from case3.figure_edit import FigureEditError, edit_figure_in_run
from case3.paragraph_edit import ParagraphEditError, edit_paragraph_in_run
from case3.table_edit import TableEditError, edit_table_in_run
from case3.generate import max_images_from_env, resolve_text_file
from case3.desk_health import build_desk_probes, probe_soffice, probe_vision
from case3.image_api import (
    ImageApiConfig,
    edit_png,
    image_api_configured,
    probe_image_api,
)
from case3.run_events import EVENTS, seed_events_from_steps
from case3.llm_client import LLMClient, LLMConfig, LLMConfigError, LLMError
from case3.parse_output import ParseError
from case3.pipeline import PipelineError, prepare_run_dirs, run_pipeline
from case3.render import IMAGE, RenderError, ensure_image
from case3.run_cancel import mark_cancel_requested
from case3.summary_bus import BUS
from case3.tex_preview import build_report_preview
from case3.user_photos import UserPhotoError, save_user_photos

log = logging.getLogger("case3.api")

_RUN_ID_OK = re.compile(r"^[A-Za-z0-9_.-]+$")
_FILE_OK = re.compile(r"^[A-Za-z0-9_.-]+$")

# Coalesce concurrent IR patches: latest deck wins, one rebuild worker per run.
_slides_patch_lock = threading.Lock()
_slides_patch_pending: dict[str, dict[str, Any]] = {}
_slides_patch_busy: set[str] = set()


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


def parse_formats_form(raw: str | None) -> set[str]:
    """Parse formats form: pdf|docx|both|none. ``none`` → no print artifacts."""
    fmt_raw = (raw or "both").strip().lower()
    if fmt_raw == "both":
        return {"pdf", "docx"}
    if fmt_raw in {"pdf", "docx"}:
        return {fmt_raw}
    if fmt_raw in {"none", "diagram", "schemas"}:
        return set()
    raise ValueError("formats must be pdf|docx|both|none")


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
    chart_palette: str = "atelier",
    chart_style: str = "",
    doc_title: str = "",
    max_diagrams: int = 2,
    output_mode: str = "auto",
    deck_pack: str = "",
) -> str:
    """Compose Intent from chat + UI controls.

    chart_auto / empty chart_types → model picks type from CHART_TYPES by Source.
    chart_hints → free-text wishes (pie, «воронка»…); model maps to whitelist or skips.
    chart_palette / chart_style → color preset + optional look notes.
    doc_title → forced \\title (also applied post-LLM).
    max_* are ceilings, not quotas.
    max_diagrams → Liber Mermaid schemas (UI-only); independent of charts.
    output_mode → report|diagram|presentation|auto (Liber composer pills).
    """
    parts: list[str] = []
    chat = (chat or "").strip()
    if chat:
        parts.append(chat)
    mode = (output_mode or "auto").strip().lower()
    if mode not in {"report", "diagram", "presentation", "auto"}:
        mode = "auto"
    req: list[str] = ["Требования UI:"]
    if mode == "diagram":
        req.append(
            "- РЕЖИМ СХЕМА (output_mode=diagram): только Mermaid diagrams[] (1–3) "
            "и короткий LaTeX-stub — \\title + 1–2 абзаца описания схем; "
            "без таблиц KPI, без полного отчёта; PDF/DOCX не нужны"
        )
    elif mode == "presentation":
        pack = (deck_pack or "").strip() or "atelier"
        req.append(
            f"- РЕЖИМ ПРЕЗЕНТАЦИЯ: без PDF/DOCX — сразу дек (pack «{pack}»). "
            "Короткий LaTeX-stub + цифры/графики из Source; "
            "takeaways и KPI слайдопригодные (slides job соберёт PPTX)"
        )
    elif mode == "report":
        req.append("- РЕЖИМ ОТЧЁТ: полный PDF/DOCX как обычно")
    hints = (chart_hints or "").strip()
    clean = [t for t in chart_types if t in CHART_TYPES]
    auto = bool(chart_auto) or (not clean and not hints)
    palette = normalize_palette_id(chart_palette)
    title = (doc_title or "").strip()
    md = max(0, min(int(max_diagrams), 3))
    if title:
        # Marker parsed by generate.doc_title_from_intent — keep format stable.
        req.append(f"- CASE3_DOC_TITLE: {title}")
        req.append(
            f"- заголовок документа (\\title): «{title}» — ОБЯЗАТЕЛЬНО этот текст, "
            "не подменяй и не сокращай"
        )

    if forbid_charts or max_charts <= 0:
        req.append("- без HTML-графиков (charts: []; Chart.js) — это не про Mermaid-схемы")
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
            "или p{…}/X; если всё ещё не влезает (≈6+ колонок) — "
            "только эту table в \\begin{landscape}…\\end{landscape}; "
            "не весь документ; не tabular{lll}"
        )
        if auto and not hints:
            req.append(
                "- типы на усмотрение модели по смыслу данных (playbook time→line, "
                "share→donut, compare→bar/grouped_bar)"
            )
        elif clean:
            req.append(
                "- ОБЯЗАТЕЛЬНО типы графиков по порядку (charts[0], charts[1], …): "
                + ", ".join(clean)
                + " — не подменяй на line/donut без причины"
            )
        if hints:
            req.append(f"- пожелания по виду/типу: {hints} (сведи к whitelist или пропусти)")
    if forbid_images or max_images <= 0:
        req.append("- без фото/иллюстраций (figures: [])")
    else:
        req.append(
            f"- до {max_images} фото/иллюстраций (figures); DEFAULT-ON: если в Source "
            "есть место/объект/сцена/процесс/продукт — сделай ≥1 фото (лучше до "
            f"{max_images}, если визуальных зацепок хватает); пустой figures[] только "
            "при «без фото» в Intent или чисто числовом Source без сцены"
        )
        req.append(
            "- figures[].caption — русская подпись; "
            "figures[].prompt — English, photorealistic, detailed lighting/subject, "
            "no Cyrillic/watermark/tiny text; не дублируй числами charts; "
            "слот %CASE3_FIG:id% рядом с абзацем, не в конце документа"
        )
    # Liber Mermaid — independent of charts/photos; default-on when budget ≥ 1.
    if md <= 0:
        req.append("- без Mermaid-схем (diagrams: []) — CASE3_MAX_DIAGRAMS=0")
    else:
        req.append(
            f"- до {md} Mermaid-схем (JSON diagrams[], Liber UI only, не в PDF); "
            "DEFAULT-ON: если в Source есть шаги/роли/ветвления/структура/≥3 раздела — "
            "сделай ≥1 схему; пустой diagrams[] только при «без схем» в Intent "
            "или чисто числовом Source без структуры"
        )
        req.append(
            "- diagrams[].type: flowchart|sequence|mindmap|timeline|stateDiagram; "
            "первая строка mermaid соответствует type; id узлов ASCII, подписи RU из Source; "
            "для flowchart: каждый узел :::start|process|decision|ok|warn|data + classDef "
            "(Liber hex, без фиолетового); цвета задаёт модель"
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
    playwright_err: str | None = None
    try:
        from playwright.sync_api import sync_playwright

        from case3.charts import _prefer_stable_playwright_browsers, _run_sync_playwright

        _prefer_stable_playwright_browsers()

        def _probe() -> None:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()

        _run_sync_playwright(_probe)
        playwright_ok = True
    except Exception as exc:  # noqa: BLE001
        playwright_err = str(exc)[:200]
        log.info("playwright check failed: %s", exc)

    vision_cfg, vision_live, vision_err = probe_vision()
    images_configured = image_api_configured()
    image_base = (os.environ.get("IMAGE_API_BASE_URL") or os.environ.get("KANDINSKY_API_BASE_URL") or "").strip()
    image_live_ok = False
    image_live_err: str | None = None
    if images_configured:
        image_live_ok, image_live_err = probe_image_api(timeout_s=1.5)
    else:
        image_live_err = "IMAGE_API_BASE_URL empty"
    soffice_ok, soffice_path, soffice_hint = probe_soffice()
    probes = build_desk_probes(
        docker_ok=docker_ok,
        docker_error=docker_err,
        playwright_ok=playwright_ok,
        playwright_error=playwright_err,
        vision_configured=vision_cfg,
        vision_ok=vision_live,
        vision_error=vision_err,
        image_configured=images_configured,
        image_ok=bool(image_live_ok),
        image_error=image_live_err,
        soffice_ok=soffice_ok,
        soffice_path=soffice_path,
        soffice_hint=soffice_hint,
    )
    # ok = desk can run a report (Vision + Docker). Image red/amber does not block.
    return {
        "ok": docker_ok and vision_cfg,
        "docker_image": IMAGE,
        "docker_ok": docker_ok,
        "docker_error": docker_err,
        "playwright_ok": playwright_ok,
        "playwright_error": playwright_err,
        "vision_configured": vision_cfg,
        "vision_ok": vision_live,
        "vision_error": vision_err,
        "image_api_configured": images_configured,
        # live probe (short timeout) — UI chip Image · ok / down
        "image_api_ok": bool(image_live_ok),
        "image_api_error": image_live_err,
        # so Windows desk can verify .env without opening the file
        "image_api_base_url": image_base or None,
        # alias for Liber UI that still reads kandinsky_configured
        "kandinsky_configured": images_configured,
        "soffice_ok": soffice_ok,
        "soffice_path": soffice_path,
        "soffice_hint": soffice_hint,
        "probes": probes,
        "defaults": {
            "max_charts": max_charts_from_env(),
            "max_images": max_images_from_env(),
            "max_diagrams": max_diagrams_from_env(),
        },
        "chart_types": sorted(CHART_TYPES),
        "chart_palettes": palette_public(),
    }


@app.get("/api/chart-types")
def chart_types() -> dict[str, Any]:
    return {"types": sorted(CHART_TYPES), "palettes": palette_public()}


def _load_diagrams_from_out(out_dir: Path) -> list[dict[str, Any]]:
    """UI-only Mermaid payloads from figures.json (no TeX inject)."""
    fj = out_dir / "figures.json"
    if not fj.is_file():
        return []
    try:
        data = json.loads(fj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("diagrams") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        did = str(item.get("id") or "").strip()
        mermaid = str(item.get("mermaid") or "").strip()
        if not did or not mermaid:
            continue
        out.append(
            {
                "id": did,
                "title": str(item.get("title") or did).strip()[:80],
                "type": str(item.get("type") or "").strip(),
                "mermaid": mermaid,
            }
        )
    return out


def _run_result_payload(
    run_id: str,
    out_dir: Path,
    meta: dict[str, Any],
    *,
    intent: str | None = None,
    max_charts: int | None = None,
    max_images: int | None = None,
    max_diagrams: int | None = None,
) -> dict[str, Any]:
    files: dict[str, str] = {}
    for art in out_dir.iterdir():
        if not art.is_file():
            continue
        suf = art.suffix.lower()
        name = art.name
        # Report PDF/DOCX only — never map *_deck.pdf onto key "pdf".
        if suf == ".pdf" and not name.endswith("_deck.pdf"):
            files["pdf"] = f"/api/runs/{run_id}/files/{name}"
        elif suf == ".docx":
            files["docx"] = f"/api/runs/{run_id}/files/{name}"

    slides_art = meta.get("slides_artifacts") or {}
    if isinstance(slides_art, dict):
        pptx_name = slides_art.get("pptx")
        deck_pdf_name = slides_art.get("deck_pdf")
        if isinstance(pptx_name, str) and (out_dir / pptx_name).is_file():
            files["pptx"] = f"/api/runs/{run_id}/files/{pptx_name}"
        if isinstance(deck_pdf_name, str) and (out_dir / deck_pdf_name).is_file():
            files["deck_pdf"] = f"/api/runs/{run_id}/files/{deck_pdf_name}"

    media = meta.get("media_status") or {}
    if not isinstance(media, dict):
        media = {}
    chart_ids = set(meta.get("charts_planned") or [])
    fig_ids = set(meta.get("figures_planned") or [])
    charts_ok = sum(
        1 for cid in chart_ids if isinstance(media.get(cid), dict) and media[cid].get("ok")
    )
    figs_ok = sum(
        1 for fid in fig_ids if isinstance(media.get(fid), dict) and media[fid].get("ok")
    )
    mc = int(max_charts if max_charts is not None else meta.get("max_charts") or 0)
    mi = int(max_images if max_images is not None else meta.get("max_images") or 0)
    md = int(
        max_diagrams if max_diagrams is not None else meta.get("max_diagrams") or 0
    )
    diagrams = _load_diagrams_from_out(out_dir)
    chat_summary = str(meta.get("chat_summary") or "")
    summary_status = str(meta.get("summary_status") or "")
    if not summary_status and chat_summary:
        summary_status = "ok"
    return {
        "run_id": run_id,
        "status": meta.get("status", "ok"),
        "stage": meta.get("stage"),
        "stage_detail": meta.get("stage_detail"),
        "intent": intent if intent is not None else meta.get("intent"),
        "max_charts": mc,
        "max_images": mi,
        "max_diagrams": md,
        "figures_planned": meta.get("figures_planned") or [],
        "charts_planned": meta.get("charts_planned") or [],
        "diagrams_planned": meta.get("diagrams_planned") or [d["id"] for d in diagrams],
        "diagrams": diagrams,
        "diagrams_ok": int(meta.get("diagrams_ok") or len(diagrams)),
        "media_status": media,
        "charts_ok": charts_ok,
        "figures_ok": figs_ok,
        "files": files,
        "downloads": files,
        "previews": _media_previews(run_id, out_dir, media),
        "preview": _build_preview_payload(run_id, out_dir, media),
        "chat_summary": chat_summary,
        "summary_status": summary_status or None,
        "slides_status": meta.get("slides_status") or "idle",
        "slides_stage": meta.get("slides_stage"),
        "slides_error": meta.get("slides_error"),
        "slides_artifacts": meta.get("slides_artifacts"),
        "output_mode": meta.get("output_mode") or "auto",
        "error": meta.get("error"),
        "warnings": _warnings(meta, max_images=mi),
    }


def _bg_run_pipeline(
    src_path: Path,
    *,
    run_id: str,
    formats: set[str],
    dry_run: bool,
    intent: str,
    max_images: int,
    max_charts: int,
    max_diagrams: int = 0,
    user_figures: list[dict[str, Any]] | None = None,
    output_mode: str = "auto",
) -> None:
    # print+flush: uvicorn often hides case3.api INFO; Win desk needs a visible line.
    print(f"[case3] pipeline thread start run_id={run_id}", flush=True)
    log.info("pipeline thread start run_id=%s", run_id)
    try:
        run_pipeline(
            src_path,
            project_root=ROOT,
            formats=formats,
            dry_run=dry_run,
            intent=intent,
            max_images=max_images,
            max_charts=max_charts,
            max_diagrams=max_diagrams,
            run_id=run_id,
            user_figures=user_figures,
            output_mode=output_mode,
        )
    except PipelineError:
        # meta already written with status=error
        log.exception("background pipeline failed run_id=%s", run_id)
    except Exception:  # noqa: BLE001
        log.exception("background pipeline crashed run_id=%s", run_id)
        out = ROOT / "runs" / "out" / run_id
        logs = ROOT / "runs" / "logs" / run_id
        meta_path = out / "meta.json"
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {"run_id": run_id}
        meta.update({"status": "error", "stage": "error", "error": "pipeline crashed"})
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        logs.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
        (out / "meta.json").write_text(payload, encoding="utf-8")


def _kick_pipeline_thread(
    src_path: Path,
    *,
    run_id: str,
    formats: set[str],
    dry_run: bool,
    intent: str,
    max_images: int,
    max_charts: int,
    max_diagrams: int = 0,
    user_figures: list[dict[str, Any]] | None = None,
    output_mode: str = "auto",
) -> None:
    """Start report pipeline on a daemon thread.

    BackgroundTasks + asyncio.to_thread can stall on Windows (same bug as slides);
    Liber then polls 200 forever with status=running, stage=queued, error=null.
    """
    threading.Thread(
        target=_bg_run_pipeline,
        kwargs={
            "src_path": src_path,
            "run_id": run_id,
            "formats": formats,
            "dry_run": dry_run,
            "intent": intent,
            "max_images": max_images,
            "max_charts": max_charts,
            "max_diagrams": max_diagrams,
            "user_figures": user_figures,
            "output_mode": output_mode,
        },
        name=f"case3-pipeline-{run_id}",
        daemon=True,
    ).start()


async def _quick_photo_edit(
    fig: dict[str, Any],
    *,
    prompt: str,
    caption: str,
) -> JSONResponse:
    """Img2img one attached photo → chat preview (no TeX/PDF)."""
    cfg = ImageApiConfig.from_env()
    if not cfg.base_url:
        raise HTTPException(400, detail="IMAGE_API_BASE_URL пуст")
    src = Path(str(fig.get("path") or ""))
    if not src.is_file():
        raise HTTPException(400, detail="upload missing on disk")
    stamp = datetime_stamp()
    run_id = f"photo_edit_{stamp}"
    out = ROOT / "runs" / "out" / run_id
    figs = out / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    dest = figs / "edited.png"
    try:
        await asyncio.to_thread(edit_png, cfg, prompt, src, dest)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, detail=f"image edit failed: {exc}") from exc
    v = int(dest.stat().st_mtime)
    meta = {
        "run_id": run_id,
        "status": "ok",
        "stage": "ok",
        "mode": "photo_edit",
        "prompt": prompt[:500],
        "caption": caption,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return JSONResponse(
        {
            "run_id": run_id,
            "status": "ok",
            "mode": "photo_edit",
            "prompt": prompt,
            "caption": caption,
            "preview_figure": {
                "id": "edited",
                "kind": "figure",
                "url": f"/api/runs/{run_id}/figures/edited.png?v={v}",
                "caption": caption,
            },
            "downloads": {},
            "preview": {
                "title": caption,
                "blocks": [
                    {
                        "type": "figure",
                        "id": "edited",
                        "kind": "figure",
                        "url": f"/api/runs/{run_id}/figures/edited.png?v={v}",
                        "caption": caption,
                    }
                ],
            },
            "figures_ok": 1,
            "figures_planned": ["edited"],
            "charts_ok": 0,
            "charts_planned": [],
            "warnings": [],
        }
    )


@app.post("/api/photo/edit")
async def api_photo_edit(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    caption: str = Form(""),
) -> JSONResponse:
    """Standalone chat-only img2img (same as photo_mode=edit on /api/run)."""
    upload_dir = ROOT / "runs" / "uploads" / datetime_stamp()
    upload_dir.mkdir(parents=True, exist_ok=True)
    raw = await image.read()
    try:
        figs = save_user_photos(
            upload_dir,
            [(image.filename or "photo.png", raw)],
            captions=[caption] if caption.strip() else None,
        )
    except UserPhotoError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return await _quick_photo_edit(
        figs[0],
        prompt=(prompt or "").strip(),
        caption=(caption or figs[0].get("caption") or "Правка фото"),
    )


@app.post("/api/run")
async def api_run(
    source: UploadFile | None = File(None),
    source_text: str | None = Form(None),
    intent: str = Form(""),
    max_charts: int | None = Form(None),
    max_images: int | None = Form(None),
    max_diagrams: int | None = Form(None),
    chart_types: str = Form(""),
    chart_hints: str = Form(""),
    chart_auto: str = Form("false"),
    chart_palette: str = Form("atelier"),
    chart_style: str = Form(""),
    doc_title: str = Form(""),
    forbid_charts: str = Form("false"),
    forbid_images: str = Form("false"),
    formats: str = Form("both"),
    dry_run: str = Form("false"),
    photo_mode: str = Form("document"),
    output_mode: str = Form("auto"),
    deck_pack: str = Form(""),
    photos: list[UploadFile] = File(default_factory=list),
    photo_captions: str = Form(""),
) -> JSONResponse:
    no_charts = _as_bool(forbid_charts)
    no_images = _as_bool(forbid_images)
    is_dry = _as_bool(dry_run)
    is_auto = _as_bool(chart_auto)
    mode = (photo_mode or "document").strip().lower()
    if mode not in {"document", "edit"}:
        raise HTTPException(400, detail="photo_mode must be document|edit")
    out_mode = (output_mode or "auto").strip().lower()
    if out_mode not in {"report", "diagram", "presentation", "auto"}:
        raise HTTPException(
            400, detail="output_mode must be report|diagram|presentation|auto"
        )

    if max_charts is None:
        max_charts = max_charts_from_env()
    if max_images is None:
        max_images = max_images_from_env()
    if max_diagrams is None:
        max_diagrams = max_diagrams_from_env()
    if no_charts:
        max_charts = 0
    if no_images:
        max_images = 0
    max_charts = max(0, min(int(max_charts), 8))
    max_images = max(0, min(int(max_images), 8))
    max_diagrams = max(0, min(int(max_diagrams), 3))
    # Composer «Схема»: Mermaid + short prose only — no charts/photos/PDF.
    if out_mode == "diagram":
        max_charts = 0
        max_images = 0
        no_charts = True
        no_images = True
        max_diagrams = max(1, max_diagrams)
        formats = "none"
    # Composer «Презентация»: no print PDF/DOCX — slides job builds the deck.
    # Liber Mermaid diagrams[] stay off so UI shows only PPTX + deck PDF.
    if out_mode == "presentation":
        formats = "none"
        max_diagrams = 0

    # Persist as .../uploads/<stamp>/source.txt so run_id stem stays "source_*"
    upload_dir = ROOT / "runs" / "uploads" / datetime_stamp()
    upload_dir.mkdir(parents=True, exist_ok=True)

    # FastAPI may pass a single UploadFile when the client sends one file.
    if isinstance(photos, list):
        photo_files = list(photos)
    elif photos is None:
        photo_files = []
    else:
        photo_files = [photos]
    cap_list = [c.strip() for c in (photo_captions or "").split("\n") if c.strip()]
    user_figures: list[dict[str, Any]] = []
    if photo_files:
        blobs: list[tuple[str, bytes]] = []
        for uf in photo_files[:2]:
            raw = await uf.read()
            blobs.append((uf.filename or "photo.png", raw))
        try:
            user_figures = save_user_photos(upload_dir, blobs, captions=cap_list)
        except UserPhotoError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        # Attached photos force image budget on
        max_images = max(max_images, len(user_figures))
        no_images = False

    # Chat-only edit: one photo + prompt → /edit → preview message (no full report)
    if mode == "edit":
        if not user_figures:
            raise HTTPException(400, detail="прикрепи фото для режима «Только правка»")
        prompt = (intent or "").strip()
        if not prompt:
            raise HTTPException(400, detail="нужен текст: что изменить на фото")
        return await _quick_photo_edit(
            user_figures[0],
            prompt=prompt,
            caption=(cap_list[0] if cap_list else user_figures[0].get("caption") or "Правка фото"),
        )

    types = [] if is_auto else _parse_chart_types(chart_types)
    full_intent = build_intent_from_ui(
        chat=intent,
        chart_types=types,
        max_charts=max_charts,
        max_images=max_images,
        max_diagrams=max_diagrams,
        forbid_charts=no_charts,
        forbid_images=no_images,
        chart_hints=chart_hints or "",
        chart_auto=is_auto,
        chart_palette=chart_palette or "atelier",
        chart_style=chart_style or "",
        doc_title=(doc_title or "").strip()[:200],
        output_mode=out_mode,
        deck_pack=(deck_pack or "").strip()[:40],
    )
    if user_figures:
        ids = ", ".join(f["id"] for f in user_figures)
        caps = "; ".join(f"{f['id']}: {f['caption']}" for f in user_figures)
        full_intent = (
            full_intent
            + "\n\nЗагруженные фото пользователя (уже есть PNG, не вызывай генерацию для них):\n"
            + f"- слоты {ids} — обязательно вставь %CASE3_FIG:id% в документ\n"
            + f"- подписи: {caps}\n"
            + "- дополнительные fig_* через Image API только если остался бюджет картинок"
        )

    try:
        fmt_set = parse_formats_form(formats)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

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

    # Reserve run_id + write stage=llm BEFORE kick (Win: 2nd run sat on queued while
    # prior LLM thread still held the desk; Liber must not wait on thread scheduling).
    run_id, _, _, out_dir, logs_dir = prepare_run_dirs(src_path, project_root=ROOT)
    meta0 = {
        "run_id": run_id,
        "source": str(resolve_text_file(src_path)),
        "intent": full_intent,
        "formats": sorted(fmt_set),
        "output_mode": out_mode,
        "dry_run": is_dry,
        "max_images": max_images,
        "max_charts": max_charts,
        "max_diagrams": max_diagrams,
        "user_figures": [f.get("id") for f in user_figures],
        "status": "running",
        "stage": "llm",
        "stage_detail": "жду модель…",
    }
    from case3.run_events import write_meta_atomic

    payload0 = json.dumps(meta0, ensure_ascii=False, indent=2)
    write_meta_atomic(out_dir / "meta.json", payload0, logs_meta=logs_dir / "meta.json")
    EVENTS.start(run_id)
    EVENTS.bind_out(run_id, out_dir)
    EVENTS.publish_stage(run_id, "llm", detail="жду модель…", scope="pipeline")

    _kick_pipeline_thread(
        src_path,
        run_id=run_id,
        formats=fmt_set,
        dry_run=is_dry,
        intent=full_intent,
        max_images=max_images,
        max_charts=max_charts,
        max_diagrams=max_diagrams,
        user_figures=user_figures,
        output_mode=out_mode,
    )

    return JSONResponse(
        status_code=202,
        content={
            "run_id": run_id,
            "status": "started",
            "stage": "llm",
            "output_mode": out_mode,
            "max_charts": max_charts,
            "max_images": max_images,
            "max_diagrams": max_diagrams,
        },
    )


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/runs/{run_id}/events")
def stream_run_events(run_id: str) -> StreamingResponse:
    """SSE: stage / artifact / done|error|cancelled (no model thoughts)."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    work = ROOT / "runs" / "work" / run_id
    if not out_dir.is_dir() and not work.is_dir():
        raise HTTPException(404, detail="run not found")

    def gen():
        import time as _time

        # Late join: seed bus from meta if empty (API restart / missed start).
        snap = EVENTS.snapshot(run_id)
        meta_path = out_dir / "meta.json"
        if meta_path.is_file() and snap.get("count", 0) == 0:
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
            EVENTS.bind_out(run_id, out_dir)
            durable = meta.get("steps") if isinstance(meta.get("steps"), list) else []
            st = str(meta.get("status") or "")
            stage = str(meta.get("stage") or "queued")
            detail = meta.get("stage_detail")
            if durable:
                # While still running, drop terminal entries so SSE stays open
                # (pipeline may have logged done before slides reopen).
                playable = (
                    [
                        s
                        for s in durable
                        if isinstance(s, dict)
                        and str(s.get("event") or "")
                        not in {"done", "error", "cancelled"}
                    ]
                    if st == "running"
                    or (
                        st == "ok"
                        and str(meta.get("slides_status") or "")
                        in {"running", "queued"}
                    )
                    else durable
                )
                seeded = seed_events_from_steps(EVENTS, run_id, playable)
                if seeded and (
                    st == "running"
                    or (
                        st == "ok"
                        and str(meta.get("slides_status") or "")
                        in {"running", "queued"}
                    )
                ):
                    EVENTS.ensure(run_id)
                    EVENTS.scan_artifacts(run_id, out_dir)
                elif seeded and st in {"ok", "error", "cancelled"}:
                    # Terminal already in seeded events — subscribe will flush & end.
                    pass
                elif st == "running":
                    EVENTS.publish_stage(
                        run_id,
                        stage,
                        detail=str(detail) if detail else None,
                        scope="pipeline",
                    )
                    EVENTS.scan_artifacts(run_id, out_dir)
            elif st == "running":
                EVENTS.publish_stage(
                    run_id, stage, detail=str(detail) if detail else None, scope="pipeline"
                )
                EVENTS.scan_artifacts(run_id, out_dir)
            elif st in {"ok", "error", "cancelled"}:
                slides_st = str(meta.get("slides_status") or "idle")
                out_mode = str(meta.get("output_mode") or "")
                if st == "ok" and slides_st in {"running", "queued"}:
                    EVENTS.reopen(run_id)
                    EVENTS.publish_stage(
                        run_id,
                        str(meta.get("slides_stage") or "starting"),
                        scope="slides",
                    )
                    EVENTS.scan_artifacts(run_id, out_dir)
                elif (
                    st == "ok"
                    and out_mode == "presentation"
                    and slides_st in {"idle", ""}
                ):
                    # Pipeline done; slides not kicked yet — keep SSE open.
                    EVENTS.ensure(run_id)
                    EVENTS.publish_stage(run_id, "pipeline_ok", scope="pipeline")
                    EVENTS.scan_artifacts(run_id, out_dir)
                else:
                    kind = "done" if st == "ok" else st
                    payload: dict[str, Any] = {"status": st, "t": _time.time()}
                    if meta.get("error"):
                        payload["error"] = meta.get("error")
                    yield _sse_pack(kind, payload)
                    return

        for ev in EVENTS.subscribe(run_id, timeout_s=1200.0, keepalive_s=15.0):
            kind = str(ev.get("event") or "stage")
            # SSE comment — keeps Vite proxy / TCP alive during long llm waits
            if kind == "ping":
                yield ": keepalive\n\n"
                continue
            data = {k: v for k, v in ev.items() if k != "event"}
            yield _sse_pack(kind, data)
            if kind in {"done", "error", "cancelled"}:
                return

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/runs/{run_id}/summary/stream")
def stream_run_summary(run_id: str) -> StreamingResponse:
    """SSE: chat summary deltas while PDF renders (replay-safe)."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    # Allow stream as soon as run dirs exist (work or out)
    work = ROOT / "runs" / "work" / run_id
    if not out_dir.is_dir() and not work.is_dir():
        raise HTTPException(404, detail="run not found")

    def gen():
        # If bus already finished, subscribe still replays.
        # If meta already has final summary and bus never started (restart), emit once.
        snap = BUS.snapshot(run_id)
        meta_path = out_dir / "meta.json"
        if meta_path.is_file() and not snap.get("done") and not snap.get("text"):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
            final = str(meta.get("chat_summary") or "")
            st = str(meta.get("summary_status") or "")
            if final and st in {"ok", "error", "skipped"}:
                if final:
                    yield _sse_pack("delta", {"text": final})
                yield _sse_pack("done", {"text": final, "status": st or "ok"})
                return

        for ev in BUS.subscribe(run_id, timeout_s=180.0):
            kind = ev.get("event") or "delta"
            if kind == "delta":
                yield _sse_pack("delta", {"text": ev.get("text") or ""})
            else:
                yield _sse_pack(
                    "done",
                    {
                        "text": ev.get("text") or "",
                        "status": ev.get("status") or "ok",
                    },
                )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/runs/{run_id}/status")
def get_run_status(run_id: str) -> dict[str, Any]:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    meta_path = out_dir / "meta.json"
    if not meta_path.is_file():
        logs_meta = ROOT / "runs" / "logs" / run_id / "meta.json"
        if logs_meta.is_file():
            meta_path = logs_meta
        else:
            raise HTTPException(404, detail="run not found")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, detail="corrupt meta.json") from exc

    status = meta.get("status") or "running"
    if status == "running":
        return {
            "run_id": run_id,
            "status": "running",
            "stage": meta.get("stage") or "queued",
            "stage_detail": meta.get("stage_detail"),
            "max_charts": meta.get("max_charts"),
            "max_images": meta.get("max_images"),
            "chat_summary": str(meta.get("chat_summary") or ""),
            "summary_status": meta.get("summary_status"),
            "slides_status": meta.get("slides_status") or "idle",
            "slides_stage": meta.get("slides_stage"),
            "cancel_requested": bool(meta.get("cancel_requested")),
            "steps": meta.get("steps") if isinstance(meta.get("steps"), list) else [],
        }
    if status == "cancelled":
        err = meta.get("error") or "Остановлено"
        return {
            "run_id": run_id,
            "status": "cancelled",
            "stage": "cancelled",
            "error": err,
            "message": err,
            "slides_status": meta.get("slides_status") or "idle",
            "slides_stage": meta.get("slides_stage"),
            "slides_error": meta.get("slides_error"),
        }
    if status == "error":
        err = meta.get("error") or "pipeline failed"
        failed_c = meta.get("failed_charts")
        failed_f = meta.get("failed_figures")
        if not isinstance(failed_c, list) or not isinstance(failed_f, list):
            media = meta.get("media_status") or {}
            if not isinstance(media, dict):
                media = {}
            if not isinstance(failed_c, list):
                failed_c = [
                    cid
                    for cid in (meta.get("charts_planned") or [])
                    if not (isinstance(media.get(cid), dict) and media[cid].get("ok"))
                ]
            if not isinstance(failed_f, list):
                failed_f = [
                    fid
                    for fid in (meta.get("figures_planned") or [])
                    if not (isinstance(media.get(fid), dict) and media[fid].get("ok"))
                ]
        work_dir = ROOT / "runs" / "work" / run_id
        from case3.pipeline import can_resume_run

        return {
            "run_id": run_id,
            "status": "error",
            "stage": "error",
            "error": err,
            "message": err,
            "hint": f"logs: runs/logs/{run_id}",
            "failed_charts": failed_c,
            "failed_figures": failed_f,
            "failed_stage": meta.get("failed_stage"),
            "can_resume": can_resume_run(meta, work=work_dir, out=out_dir),
            "latex_log_tail": meta.get("latex_log_tail") or "",
            "max_charts": meta.get("max_charts"),
            "max_images": meta.get("max_images"),
        }
    # ok (or unknown → treat as result payload if out exists)
    if not out_dir.is_dir():
        out_dir = ROOT / "runs" / "out" / run_id
    return _run_result_payload(run_id, out_dir, meta)


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


def _find_out_tex(out_dir: Path) -> Path | None:
    texs = sorted(out_dir.glob("*.tex"))
    return texs[0] if texs else None


def _load_figures_json(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "figures.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _build_preview_payload(
    run_id: str, out_dir: Path, media: dict[str, Any]
) -> dict[str, Any]:
    tex_path = _find_out_tex(out_dir)
    if tex_path is None:
        return {"title": "", "blocks": []}
    try:
        tex = tex_path.read_text(encoding="utf-8")
    except OSError:
        return {"title": "", "blocks": []}
    return build_report_preview(
        tex,
        run_id=run_id,
        media_status=media,
        figures_json=_load_figures_json(out_dir),
    )


@app.get("/api/runs/{run_id}/preview")
def get_run_preview(run_id: str) -> dict[str, Any]:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not out_dir.is_dir():
        raise HTTPException(404, detail="run not found")
    meta: dict[str, Any] = {}
    meta_path = out_dir / "meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    media = meta.get("media_status") or {}
    preview = _build_preview_payload(
        run_id, out_dir, media if isinstance(media, dict) else {}
    )
    # Cache-bust figure URLs (edit responses already add ?v=; GET must too).
    bust = 0
    figs = out_dir / "figures"
    if figs.is_dir():
        for p in figs.glob("*.png"):
            try:
                bust = max(bust, int(p.stat().st_mtime))
            except OSError:
                continue
    if not bust:
        try:
            bust = int((meta.get("chart_edit_last") or {}).get("ts") or 0)
        except (TypeError, ValueError):
            bust = 0
    if bust:
        for block in preview.get("blocks") or []:
            if (
                isinstance(block, dict)
                and block.get("type") == "figure"
                and block.get("url")
            ):
                url = str(block["url"])
                if "v=" in url:
                    continue
                sep = "&" if "?" in url else "?"
                block["url"] = f"{url}{sep}v={bust}"
    return preview


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


def _resolve_run_dir(run_id: str) -> Path:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not out_dir.is_dir():
        raise HTTPException(404, detail="run not found")
    return out_dir


@app.get("/api/runs/{run_id}/charts/{chart_id}")
def get_run_chart(run_id: str, chart_id: str) -> dict[str, Any]:
    """Chart fragment + meta for Liber live Chart.js (G9/G12)."""
    if not _FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = _resolve_run_dir(run_id)
    fj = _load_figures_json(out_dir)
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


@app.post("/api/runs/{run_id}/charts/{chart_id}/preview")
def preview_run_chart(
    run_id: str, chart_id: str, body: ChartPreviewBody
) -> dict[str, Any]:
    """Local palette/type preview — no PNG/PDF write (Apply still commits)."""
    if not _FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = _resolve_run_dir(run_id)
    try:
        return preview_chart_html(
            out_dir,
            chart_id,
            palette=body.palette,
            chart_type=body.chart_type,
        )
    except ChartEditError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/diagrams/{diagram_id}/edit")
async def edit_run_diagram(
    run_id: str, diagram_id: str, body: DiagramEditBody
) -> dict[str, Any]:
    """Save edited Mermaid for one Liber diagram (no PDF/TeX)."""
    if not _FILE_OK.match(diagram_id):
        raise HTTPException(400, detail="invalid diagram_id")
    out_dir = _resolve_run_dir(run_id)
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
        "diagrams": _load_diagrams_from_out(out_dir),
        "undo": undo,
    }


@app.get("/api/runs/{run_id}/diagrams/{diagram_id}/svg")
async def download_diagram_svg(run_id: str, diagram_id: str) -> Response:
    """Mermaid → SVG for Liber schema download (no PNG raster)."""
    from case3.diagram_svg import DiagramSvgError, export_diagram_svg, load_diagram_spec

    if not _FILE_OK.match(diagram_id):
        raise HTTPException(400, detail="invalid diagram_id")
    out_dir = _resolve_run_dir(run_id)
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


@app.post("/api/runs/{run_id}/diagrams/regenerate")
async def regenerate_run_diagrams(
    run_id: str, body: DiagramRegenBody | None = None
) -> dict[str, Any]:
    """Full LLM regenerate of diagrams[] (+ repair). No TeX/PDF."""
    out_dir = _resolve_run_dir(run_id)
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
        "diagrams": result.get("diagrams") or _load_diagrams_from_out(out_dir),
        "diagrams_repaired": bool(result.get("diagrams_repaired")),
        "diagrams_ok": int(result.get("diagrams_ok") or 0),
    }


@app.post("/api/runs/{run_id}/charts/{chart_id}/edit")
async def edit_run_chart(run_id: str, chart_id: str, body: ChartEditBody) -> dict[str, Any]:
    """Restyle one chart in-place and rebuild PDF/DOCX (same PNG path → docs update)."""
    if not _FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = _resolve_run_dir(run_id)

    fmt_raw = (body.formats or "both").strip().lower()
    if fmt_raw == "both":
        fmt_set = {"pdf", "docx"}
    elif fmt_raw in {"pdf", "docx"}:
        fmt_set = {fmt_raw}
    else:
        raise HTTPException(400, detail="formats must be pdf|docx|both")

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

    media = result.get("media_status") or {}
    preview = _build_preview_payload(run_id, out_dir, media if isinstance(media, dict) else {})
    v = int(result.get("version") or 0)
    # Cache-bust figure URLs in preview blocks
    for block in preview.get("blocks") or []:
        if isinstance(block, dict) and block.get("type") == "figure" and block.get("url"):
            url = str(block["url"])
            if "cht_" in url or chart_id in url:
                sep = "&" if "?" in url else "?"
                block["url"] = f"{url}{sep}v={v}"

    files: dict[str, str] = {}
    for art in sorted(out_dir.iterdir()):
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            key = art.suffix.lower().lstrip(".")
            files[key] = f"/api/runs/{run_id}/files/{art.name}?v={v}"

    return {
        "run_id": run_id,
        "chart_id": chart_id,
        "status": "ok",
        "mode": result.get("mode"),
        "palette": result.get("palette"),
        "style": result.get("style"),
        "media_status": media,
        "downloads": files,
        "preview": preview,
        "preview_figure": {
            "id": chart_id,
            "kind": "chart",
            "url": f"/api/runs/{run_id}/figures/{chart_id}.png?v={v}",
        },
        "undo": result.get("undo"),
        "warnings": [],
    }


@app.post("/api/runs/{run_id}/figures/{figure_id}/edit")
async def edit_run_figure(run_id: str, figure_id: str, body: FigureEditBody) -> dict[str, Any]:
    """Regenerate (generate) or img2img-edit one photo; rebuild PDF/DOCX."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    if not _FILE_OK.match(figure_id):
        raise HTTPException(400, detail="invalid figure_id")
    if figure_id.startswith("cht_"):
        raise HTTPException(400, detail="use /charts/{id}/edit for charts")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not out_dir.is_dir():
        raise HTTPException(404, detail="run not found")

    mode = (body.mode or "generate").strip().lower()
    if mode not in {"generate", "edit"}:
        raise HTTPException(400, detail="mode must be generate|edit")
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, detail="prompt required")

    fmt_raw = (body.formats or "both").strip().lower()
    if fmt_raw == "both":
        fmt_set = {"pdf", "docx"}
    elif fmt_raw in {"pdf", "docx"}:
        fmt_set = {fmt_raw}
    else:
        raise HTTPException(400, detail="formats must be pdf|docx|both")

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

    media = result.get("media_status") or {}
    preview = _build_preview_payload(run_id, out_dir, media if isinstance(media, dict) else {})
    v = int(result.get("version") or 0)
    for block in preview.get("blocks") or []:
        if isinstance(block, dict) and block.get("type") == "figure" and block.get("url"):
            url = str(block["url"])
            if figure_id in url:
                sep = "&" if "?" in url else "?"
                block["url"] = f"{url}{sep}v={v}"

    files: dict[str, str] = {}
    for art in sorted(out_dir.iterdir()):
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            key = art.suffix.lower().lstrip(".")
            files[key] = f"/api/runs/{run_id}/files/{art.name}?v={v}"

    return {
        "run_id": run_id,
        "figure_id": figure_id,
        "status": "ok",
        "mode": result.get("mode"),
        "prompt": result.get("prompt"),
        "caption": result.get("caption"),
        "media_status": media,
        "downloads": files,
        "preview": preview,
        "preview_figure": {
            "id": figure_id,
            "kind": "figure",
            "url": f"/api/runs/{run_id}/figures/{figure_id}.png?v={v}",
        },
        "undo": result.get("undo"),
        "warnings": [],
    }


@app.post("/api/runs/{run_id}/tables/{table_index}/edit")
async def edit_run_table(
    run_id: str, table_index: int, body: TableEditBody
) -> dict[str, Any]:
    """Replace one preview table (caption + grid) and rebuild PDF/DOCX."""
    out_dir = _resolve_run_dir(run_id)
    if table_index < 1:
        raise HTTPException(400, detail="table_index must be ≥ 1")

    fmt_raw = (body.formats or "both").strip().lower()
    if fmt_raw == "both":
        fmt_set = {"pdf", "docx"}
    elif fmt_raw in {"pdf", "docx"}:
        fmt_set = {fmt_raw}
    else:
        raise HTTPException(400, detail="formats must be pdf|docx|both")

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

    media = result.get("media_status") or {}
    preview = _build_preview_payload(
        run_id, out_dir, media if isinstance(media, dict) else {}
    )
    v = int(result.get("version") or 0)

    files: dict[str, str] = {}
    for art in sorted(out_dir.iterdir()):
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            key = art.suffix.lower().lstrip(".")
            files[key] = f"/api/runs/{run_id}/files/{art.name}?v={v}"

    return {
        "run_id": run_id,
        "table_index": table_index,
        "status": "ok",
        "caption": result.get("caption"),
        "media_status": media,
        "downloads": files,
        "preview": preview,
        "undo": result.get("undo"),
        "warnings": [],
    }


@app.post("/api/runs/{run_id}/paragraphs/{paragraph_index}/edit")
async def edit_run_paragraph(
    run_id: str, paragraph_index: int, body: ParagraphEditBody
) -> dict[str, Any]:
    """Replace one preview paragraph (para-N) and rebuild PDF/DOCX."""
    out_dir = _resolve_run_dir(run_id)
    if paragraph_index < 1:
        raise HTTPException(400, detail="paragraph_index must be ≥ 1")

    fmt_raw = (body.formats or "both").strip().lower()
    if fmt_raw == "both":
        fmt_set = {"pdf", "docx"}
    elif fmt_raw in {"pdf", "docx"}:
        fmt_set = {fmt_raw}
    else:
        raise HTTPException(400, detail="formats must be pdf|docx|both")

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

    media = result.get("media_status") or {}
    preview = _build_preview_payload(
        run_id, out_dir, media if isinstance(media, dict) else {}
    )
    v = int(result.get("version") or 0)

    files: dict[str, str] = {}
    for art in sorted(out_dir.iterdir()):
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            key = art.suffix.lower().lstrip(".")
            files[key] = f"/api/runs/{run_id}/files/{art.name}?v={v}"

    return {
        "run_id": run_id,
        "paragraph_index": paragraph_index,
        "status": "ok",
        "text": result.get("text"),
        "media_status": media,
        "downloads": files,
        "preview": preview,
        "undo": result.get("undo"),
        "warnings": [],
    }


@app.post("/api/runs/{run_id}/undo")
async def undo_last_edit(run_id: str) -> dict[str, Any]:
    """Restore the single undo snapshot from the last successful Liber edit."""
    from case3.run_undo import UndoError, apply_undo

    out_dir = _resolve_run_dir(run_id)
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
    preview = _build_preview_payload(run_id, out_dir, media)
    v = int(time.time())
    files: dict[str, str] = {}
    for art in sorted(out_dir.iterdir()):
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            key = art.suffix.lower().lstrip(".")
            files[key] = f"/api/runs/{run_id}/files/{art.name}?v={v}"
    # Cache-bust figures in preview
    for block in preview.get("blocks") or []:
        if isinstance(block, dict) and block.get("type") == "figure" and block.get("url"):
            url = str(block["url"])
            sep = "&" if "?" in url else "?"
            block["url"] = f"{url}{sep}v={v}"

    return {
        "run_id": run_id,
        "status": "ok",
        "undone": {"kind": result.get("kind"), "target": result.get("target")},
        "downloads": files,
        "preview": preview,
        "undo": None,
        "warnings": (
            [str(result["rebuild_error"])] if result.get("rebuild_error") else []
        ),
    }


def _warnings(meta: dict[str, Any], *, max_images: int) -> list[str]:
    warnings: list[str] = []
    planned = meta.get("figures_planned") or []
    media = meta.get("media_status") or {}
    if planned and max_images > 0:
        if not image_api_configured():
            warnings.append(
                "Image API не настроен — слоты fig_* пропущены (отчёт без блокировки)"
            )
        else:
            failed = [
                fid
                for fid in planned
                if not (isinstance(media.get(fid), dict) and media[fid].get("ok"))
            ]
            if failed:
                warnings.append(
                    f"фото пропущены / не сгенерировались (Image API): {', '.join(failed)}"
                )
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
    suf = path.suffix.lower()
    media = "application/octet-stream"
    if suf == ".pdf":
        media = "application/pdf"
    elif suf == ".docx":
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif suf == ".png":
        media = "image/png"
    elif suf == ".pptx":
        media = (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    return FileResponse(path, media_type=media, filename=path.name)


def _write_slides_crash(run_id: str, message: str) -> None:
    """Persist slides_status=error so UI does not sit on queued forever."""
    out = ROOT / "runs" / "out" / run_id
    logs = ROOT / "runs" / "logs" / run_id
    meta_path = out / "meta.json"
    meta: dict[str, Any] = {"run_id": run_id}
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta = loaded
        except (OSError, json.JSONDecodeError):
            pass
    meta["slides_status"] = "error"
    meta["slides_stage"] = "error"
    meta["slides_error"] = message
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    try:
        out.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(payload, encoding="utf-8")
        (logs / "meta.json").write_text(payload, encoding="utf-8")
    except OSError:
        log.exception("could not write slides crash meta run_id=%s", run_id)


def _clear_stale_slides_running(meta: dict[str, Any], *, run_id: str, out_dir: Path) -> bool:
    """Clear zombie slides_status=running left by API kill / hung LLM (not live patch).

    Returns True if the lock was cleared so a PATCH may proceed.
    """
    if meta.get("slides_status") != "running":
        return False
    stage = str(meta.get("slides_stage") or "")
    # Live text-edit rebuild — caller must serialize / 409.
    if stage == "patch":
        return False
    ir = out_dir / "slides" / "deck.json"
    # No IR yet → real first-time job may still be running.
    if not ir.is_file() and stage in {"starting", "queued", "llm", "llm_retry", "plan", "ir"}:
        return False
    log.warning(
        "clearing stale slides lock run_id=%s stage=%s (deck exists=%s)",
        run_id,
        stage or "?",
        ir.is_file(),
    )
    meta["slides_status"] = "ok" if ir.is_file() else "error"
    meta["slides_stage"] = "ok" if ir.is_file() else "error"
    if not ir.is_file():
        meta["slides_error"] = meta.get("slides_error") or "slides job interrupted"
    else:
        meta["slides_error"] = None
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    (out_dir / "meta.json").write_text(payload, encoding="utf-8")
    logs = ROOT / "runs" / "logs" / run_id
    try:
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
    except OSError:
        pass
    return True


def _bg_run_slides(run_id: str) -> None:
    from case3.slides_job import run_slides_job

    try:
        run_slides_job(run_id, root=ROOT)
    except Exception as exc:  # noqa: BLE001
        log.exception("slides background job crashed run_id=%s", run_id)
        _write_slides_crash(run_id, f"slides crashed: {exc}")


def _kick_slides_thread(run_id: str) -> None:
    """Start slides job on a daemon thread (BackgroundTasks+to_thread can stall on Windows)."""
    threading.Thread(
        target=_bg_run_slides,
        args=(run_id,),
        name=f"case3-slides-{run_id}",
        daemon=True,
    ).start()


class SlidesStartBody(BaseModel):
    theme_pack: str | None = Field(default=None)
    structure_id: str | None = Field(default=None)
    style_settings: dict[str, Any] | None = Field(default=None)


@app.get("/api/deck-themes")
def deck_themes() -> dict[str, Any]:
    """Public catalog of Liber deck theme packs (deck-only)."""
    from case3.deck_structure import list_structures

    return {"packs": list_public_packs(), "structures": list_structures()}


@app.post("/api/runs/{run_id}/slides")
async def start_slides(
    run_id: str,
    body: SlidesStartBody | None = Body(default=None),
) -> JSONResponse:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not (out_dir / "meta.json").is_file():
        raise HTTPException(404, detail="run not found")
    try:
        meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, detail="corrupt meta.json") from exc
    if meta.get("status") != "ok":
        raise HTTPException(409, detail="report run is not ok")
    # Live worker — do not start a second thread. Stuck "queued" (old bug) is retriable.
    if meta.get("slides_status") == "running":
        return JSONResponse(
            {
                "run_id": run_id,
                "status": "started",
                "slides_status": "running",
                "slides_stage": meta.get("slides_stage") or "queued",
            },
            status_code=202,
        )
    from case3.deck_structure import normalize_structure_id

    pack = normalize_pack_id((body.theme_pack if body else None) or "atelier")
    structure_id = normalize_structure_id(body.structure_id if body else None)
    settings = (body.style_settings if body else None) or None
    if settings is not None and not isinstance(settings, dict):
        settings = None
    meta["slides_style"] = {
        "theme_pack": pack,
        "structure_id": structure_id,
        "style_settings": settings,
    }
    meta["slides_theme_pack"] = pack
    meta["slides_structure_id"] = structure_id
    # Mark running before kick so a dead BackgroundTask cannot leave meta at queued.
    meta["slides_status"] = "running"
    meta["slides_stage"] = "starting"
    meta["slides_error"] = None
    meta.pop("cancel_requested", None)
    # Write meta first, then SSE stage (persist appends into meta.steps).
    with _slides_patch_lock:
        _slides_patch_pending.pop(run_id, None)
        _slides_patch_busy.discard(run_id)
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    (out_dir / "meta.json").write_text(payload, encoding="utf-8")
    logs = ROOT / "runs" / "logs" / run_id
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "meta.json").write_text(payload, encoding="utf-8")
    from case3.run_events import EVENTS

    EVENTS.reopen(run_id)
    EVENTS.bind_out(run_id, out_dir)
    EVENTS.publish_stage(run_id, "starting", scope="slides")
    _kick_slides_thread(run_id)
    return JSONResponse(
        {
            "run_id": run_id,
            "status": "started",
            "slides_status": "running",
            "slides_stage": "starting",
            "slides_style": meta["slides_style"],
        },
        status_code=202,
    )


@app.get("/api/runs/{run_id}/slides")
def get_slides(run_id: str) -> dict[str, Any]:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not (out_dir / "meta.json").is_file():
        raise HTTPException(404, detail="run not found")
    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    deck = None
    ir_path = out_dir / "slides" / "deck.json"
    if ir_path.is_file():
        try:
            deck = json.loads(ir_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            deck = None
    art = meta.get("slides_artifacts") or {}
    downloads: dict[str, str] = {}
    deck_pdf_mode: str | None = None
    if isinstance(art, dict):
        for key in ("pptx", "deck_pdf"):
            name = art.get(key)
            if isinstance(name, str) and (out_dir / name).is_file():
                downloads[key] = f"/api/runs/{run_id}/files/{name}"
        mode = art.get("deck_pdf_mode")
        if isinstance(mode, str) and mode.strip():
            deck_pdf_mode = mode.strip()
    return {
        "run_id": run_id,
        "slides_status": meta.get("slides_status") or "idle",
        "slides_stage": meta.get("slides_stage"),
        "slides_error": meta.get("slides_error"),
        "deck": deck,
        "slide_pngs": [
            f"/api/runs/{run_id}/slides/png/{p.name}"
            for p in sorted((out_dir / "slides").glob("slide_*.png"))
        ]
        if (out_dir / "slides").is_dir()
        else [],
        "downloads": downloads,
        "deck_pdf_mode": deck_pdf_mode,
    }


class SlidesIrPatchBody(BaseModel):
    """Text-only IR patch — edit existing fields; no add/delete slides."""

    slides: list[dict[str, Any]] = Field(default_factory=list)


class SlidesStructureBody(BaseModel):
    """Structural IR op — reorder / duplicate / delete; rebuild twin+PPTX only."""

    op: str = Field(default="")
    id: str | None = Field(default=None)
    order: list[str] | None = Field(default=None)


def _slides_patch_worker(run_id: str, out_dir: Path) -> None:
    """Drain coalesced IR patches — latest deck wins; no 409 on concurrent edits."""
    from case3.run_cancel import RunCancelled
    from case3.slides_job import rebuild_slides_from_deck

    while True:
        with _slides_patch_lock:
            pending = _slides_patch_pending.pop(run_id, None)
            if pending is None:
                _slides_patch_busy.discard(run_id)
                return
            deck = pending["deck"]
            _slides_patch_busy.add(run_id)

        try:
            meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {"run_id": run_id, "status": "ok"}
        meta["slides_status"] = "running"
        meta["slides_stage"] = "patch"
        meta["slides_error"] = None
        meta.pop("cancel_requested", None)
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        try:
            (out_dir / "meta.json").write_text(payload, encoding="utf-8")
        except OSError:
            log.exception("slides patch meta write failed run_id=%s", run_id)

        try:
            rebuild_slides_from_deck(run_id, deck, root=ROOT)
        except RunCancelled:
            log.info("slides patch cancelled run_id=%s", run_id)
            with _slides_patch_lock:
                _slides_patch_pending.pop(run_id, None)
                _slides_patch_busy.discard(run_id)
            return
        except Exception:
            log.exception("slides IR patch rebuild failed run_id=%s", run_id)
            try:
                m = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
                m["slides_status"] = "error"
                m["slides_stage"] = "error"
                m["slides_error"] = "rebuild after edit failed"
                (out_dir / "meta.json").write_text(
                    json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception:
                pass

        with _slides_patch_lock:
            if run_id not in _slides_patch_pending:
                _slides_patch_busy.discard(run_id)
                return


def _bg_resume_pipeline(run_id: str) -> None:
    print(f"[case3] resume thread start run_id={run_id}", flush=True)
    log.info("resume thread start run_id=%s", run_id)
    from case3.pipeline import PipelineError, resume_pipeline

    try:
        resume_pipeline(run_id, project_root=ROOT)
    except PipelineError:
        log.exception("background resume failed run_id=%s", run_id)
    except Exception:  # noqa: BLE001
        log.exception("background resume crashed run_id=%s", run_id)


def _kick_resume_thread(run_id: str) -> None:
    threading.Thread(
        target=_bg_resume_pipeline,
        kwargs={"run_id": run_id},
        name=f"case3-resume-{run_id}",
        daemon=True,
    ).start()


@app.post("/api/runs/{run_id}/resume")
def resume_run(run_id: str) -> dict[str, Any]:
    """Continue a failed run from failed_stage (same run_id, no LLM)."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    work_dir = ROOT / "runs" / "work" / run_id
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    meta_path = out_dir / "meta.json"
    if not meta_path.is_file():
        logs_meta = ROOT / "runs" / "logs" / run_id / "meta.json"
        if logs_meta.is_file():
            meta_path = logs_meta
        else:
            raise HTTPException(404, detail="run not found")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, detail="corrupt meta.json") from exc
    if not isinstance(meta, dict):
        meta = {}
    from case3.pipeline import can_resume_run

    if not can_resume_run(meta, work=work_dir, out=out_dir):
        raise HTTPException(
            409,
            detail="run is not eligible to resume (need error after LLM on media/render)",
        )
    # Flip to running so Liber poll leaves the error card immediately.
    meta["status"] = "running"
    meta["stage"] = meta.get("failed_stage") or "queued"
    meta.pop("cancel_requested", None)
    meta.pop("error", None)
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(payload, encoding="utf-8")
    logs_dir = ROOT / "runs" / "logs" / run_id
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "meta.json").write_text(payload, encoding="utf-8")
    _kick_resume_thread(run_id)
    return {"run_id": run_id, "status": "started", "resumed_from": meta.get("failed_stage")}


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, Any]:
    """Cooperative stop: UI frees immediately; pipeline/slides exit between stages."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    logs_dir = ROOT / "runs" / "logs" / run_id
    if not (out_dir / "meta.json").is_file() and not (logs_dir / "meta.json").is_file():
        raise HTTPException(404, detail="run not found")
    meta = mark_cancel_requested(out_dir, logs_dir=logs_dir)
    with _slides_patch_lock:
        _slides_patch_pending.pop(run_id, None)
    return {
        "run_id": run_id,
        "status": "cancelling",
        "cancel_requested": True,
        "pipeline_status": meta.get("status"),
        "slides_status": meta.get("slides_status"),
    }


def _load_deck_for_patch(run_id: str, out_dir: Path) -> tuple[dict[str, Any], Path]:
    """Shared guards for text + structure slide patches."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir.resolve()).startswith(str(out_root)) or not (
        out_dir / "meta.json"
    ).is_file():
        raise HTTPException(404, detail="run not found")
    ir_path = out_dir / "slides" / "deck.json"
    if not ir_path.is_file():
        raise HTTPException(404, detail="deck IR not found — generate presentation first")
    try:
        meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, detail="corrupt meta.json") from exc
    if meta.get("status") != "ok":
        raise HTTPException(409, detail="report run is not ok")
    if meta.get("slides_status") == "running" and meta.get("slides_stage") != "patch":
        _clear_stale_slides_running(meta, run_id=run_id, out_dir=out_dir)
        if meta.get("slides_status") == "running":
            raise HTTPException(409, detail="slides job already running")

    with _slides_patch_lock:
        base = (_slides_patch_pending.get(run_id) or {}).get("deck")
    if base is None:
        try:
            base = json.loads(ir_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(500, detail="corrupt deck.json") from exc
    if not isinstance(base, dict):
        raise HTTPException(500, detail="corrupt deck.json")
    return base, ir_path


def _enqueue_deck_rebuild(
    run_id: str, out_dir: Path, ir_path: Path, patched: dict[str, Any]
) -> bool:
    """Write IR + queue coalesce worker. Returns True if already queued."""
    try:
        ir_path.write_text(
            json.dumps(patched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        raise HTTPException(500, detail="could not write deck.json") from exc

    with _slides_patch_lock:
        _slides_patch_pending[run_id] = {"deck": patched}
        already = run_id in _slides_patch_busy
        if not already:
            _slides_patch_busy.add(run_id)

    if not already:
        threading.Thread(
            target=_slides_patch_worker,
            args=(run_id, out_dir),
            name=f"case3-slides-patch-{run_id}",
            daemon=True,
        ).start()
    return already


@app.patch("/api/runs/{run_id}/slides/ir")
async def patch_slides_ir(
    run_id: str,
    body: SlidesIrPatchBody,
) -> JSONResponse:
    """Patch deck text fields and rebuild native PPTX + twin preview.

    Concurrent PATCHes coalesce: latest IR wins, one rebuild worker per run (no 409).
    """
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    base, ir_path = _load_deck_for_patch(run_id, out_dir)

    from case3.slides_ir import DeckIrError
    from case3.slides_patch import apply_deck_text_patch

    try:
        patched = apply_deck_text_patch(base, {"slides": body.slides})
    except DeckIrError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    already = _enqueue_deck_rebuild(run_id, out_dir, ir_path, patched)
    return JSONResponse(
        {
            "run_id": run_id,
            "status": "started",
            "slides_status": "running",
            "slides_stage": "patch",
            "queued": already,
            "deck": patched,
        },
        status_code=202,
    )


@app.post("/api/runs/{run_id}/slides/structure")
async def post_slides_structure(
    run_id: str,
    body: SlidesStructureBody,
) -> JSONResponse:
    """Reorder / duplicate / delete slides — IR patch + rebuild twin/PPTX (no LLM)."""
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    base, ir_path = _load_deck_for_patch(run_id, out_dir)

    from case3.slides_ir import DeckIrError
    from case3.slides_patch import apply_deck_structure

    op_body: dict[str, Any] = {"op": body.op}
    if body.id is not None:
        op_body["id"] = body.id
    if body.order is not None:
        op_body["order"] = body.order

    try:
        patched = apply_deck_structure(base, op_body)
    except DeckIrError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    already = _enqueue_deck_rebuild(run_id, out_dir, ir_path, patched)
    return JSONResponse(
        {
            "run_id": run_id,
            "status": "started",
            "slides_status": "running",
            "slides_stage": "patch",
            "queued": already,
            "op": body.op,
            "deck": patched,
        },
        status_code=202,
    )


@app.get("/api/runs/{run_id}/slides/png/{name}")
def download_slide_png(run_id: str, name: str) -> FileResponse:
    if not name.lower().endswith(".png") or not _FILE_OK.match(name):
        raise HTTPException(400, detail="invalid png name")
    path = _safe_run_file(run_id, "slides", name)
    return FileResponse(path, media_type="image/png", filename=path.name)


@app.get("/api/runs/{run_id}/slides/media/{name}")
def download_slide_media(run_id: str, name: str) -> FileResponse:
    """Chart/figure PNG from figures/, or diagram PNG from slides/diagrams/."""
    if not name.lower().endswith(".png") or not _FILE_OK.match(name):
        raise HTTPException(400, detail="invalid media name")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    for parts in (("figures", name), ("slides", "diagrams", name)):
        try:
            path = _safe_run_file(run_id, *parts)
            return FileResponse(path, media_type="image/png", filename=path.name)
        except HTTPException:
            continue
    raise HTTPException(404, detail="media not found")


@app.get("/api/runs/{run_id}/figures/{name}")
def download_figure(run_id: str, name: str) -> FileResponse:
    if not name.lower().endswith(".png"):
        raise HTTPException(400, detail="only PNG figures")
    path = _safe_run_file(run_id, "figures", name)
    return FileResponse(path, media_type="image/png", filename=path.name)
