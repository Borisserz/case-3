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

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from case3.chart_edit import ChartEditError, edit_chart_in_run
from case3.chart_html import CHART_TYPES
from case3.chart_style import intent_palette_lines, normalize_palette_id, palette_public
from case3.charts import max_charts_from_env
from case3.envfile import load_dotenv
from case3.figure_edit import FigureEditError, edit_figure_in_run
from case3.generate import max_images_from_env, resolve_text_file
from case3.image_api import ImageApiConfig, edit_png, image_api_configured
from case3.llm_client import LLMConfigError, LLMError
from case3.parse_output import ParseError
from case3.pipeline import PipelineError, prepare_run_dirs, run_pipeline
from case3.render import IMAGE, RenderError, ensure_image
from case3.tex_preview import build_report_preview
from case3.user_photos import UserPhotoError, save_user_photos

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
    doc_title: str = "",
) -> str:
    """Compose Intent from chat + UI controls.

    chart_auto / empty chart_types → model picks type from CHART_TYPES by Source.
    chart_hints → free-text wishes (pie, «воронка»…); model maps to whitelist or skips.
    chart_palette / chart_style → color preset + optional look notes.
    doc_title → forced \\title (also applied post-LLM).
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
    title = (doc_title or "").strip()
    if title:
        # Marker parsed by generate.doc_title_from_intent — keep format stable.
        req.append(f"- CASE3_DOC_TITLE: {title}")
        req.append(
            f"- заголовок документа (\\title): «{title}» — ОБЯЗАТЕЛЬНО этот текст, "
            "не подменяй и не сокращай"
        )

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
            f"- до {max_images} фото/иллюстраций (figures): сцена/объект из Source "
            "или явная просьба в Intent («сгенерируй фото…»)"
        )
        req.append(
            "- figures[].caption — русская подпись; "
            "figures[].prompt — English, photorealistic, detailed lighting/subject, "
            "no Cyrillic/watermark/tiny text; не дублируй числами charts"
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
    images_ok = image_api_configured()
    image_base = (os.environ.get("IMAGE_API_BASE_URL") or os.environ.get("KANDINSKY_API_BASE_URL") or "").strip()
    return {
        "ok": docker_ok and vision,
        "docker_image": IMAGE,
        "docker_ok": docker_ok,
        "docker_error": docker_err,
        "playwright_ok": playwright_ok,
        "vision_configured": vision,
        "image_api_configured": images_ok,
        # so Windows desk can verify .env without opening the file
        "image_api_base_url": image_base or None,
        # alias for Liber UI that still reads kandinsky_configured
        "kandinsky_configured": images_ok,
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


def _run_result_payload(
    run_id: str,
    out_dir: Path,
    meta: dict[str, Any],
    *,
    intent: str | None = None,
    max_charts: int | None = None,
    max_images: int | None = None,
) -> dict[str, Any]:
    files: dict[str, str] = {}
    for art in out_dir.iterdir():
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            files[art.suffix.lower().lstrip(".")] = f"/api/runs/{run_id}/files/{art.name}"

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
    return {
        "run_id": run_id,
        "status": meta.get("status", "ok"),
        "stage": meta.get("stage"),
        "stage_detail": meta.get("stage_detail"),
        "intent": intent if intent is not None else meta.get("intent"),
        "max_charts": mc,
        "max_images": mi,
        "figures_planned": meta.get("figures_planned") or [],
        "charts_planned": meta.get("charts_planned") or [],
        "media_status": media,
        "charts_ok": charts_ok,
        "figures_ok": figs_ok,
        "files": files,
        "downloads": files,
        "previews": _media_previews(run_id, out_dir, media),
        "preview": _build_preview_payload(run_id, out_dir, media),
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
    user_figures: list[dict[str, Any]] | None = None,
) -> None:
    try:
        run_pipeline(
            src_path,
            project_root=ROOT,
            formats=formats,
            dry_run=dry_run,
            intent=intent,
            max_images=max_images,
            max_charts=max_charts,
            run_id=run_id,
            user_figures=user_figures,
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
    background_tasks: BackgroundTasks,
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
    doc_title: str = Form(""),
    forbid_charts: str = Form("false"),
    forbid_images: str = Form("false"),
    formats: str = Form("both"),
    dry_run: str = Form("false"),
    photo_mode: str = Form("document"),
    photos: list[UploadFile] | None = File(None),
    photo_captions: str = Form(""),
) -> JSONResponse:
    no_charts = _as_bool(forbid_charts)
    no_images = _as_bool(forbid_images)
    is_dry = _as_bool(dry_run)
    is_auto = _as_bool(chart_auto)
    mode = (photo_mode or "document").strip().lower()
    if mode not in {"document", "edit"}:
        raise HTTPException(400, detail="photo_mode must be document|edit")

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

    # Persist as .../uploads/<stamp>/source.txt so run_id stem stays "source_*"
    upload_dir = ROOT / "runs" / "uploads" / datetime_stamp()
    upload_dir.mkdir(parents=True, exist_ok=True)

    photo_files = list(photos or [])
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
        forbid_charts=no_charts,
        forbid_images=no_images,
        chart_hints=chart_hints or "",
        chart_auto=is_auto,
        chart_palette=chart_palette or "editorial",
        chart_style=chart_style or "",
        doc_title=(doc_title or "").strip()[:200],
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

    fmt_raw = (formats or "both").strip().lower()
    if fmt_raw == "both":
        fmt_set = {"pdf", "docx"}
    elif fmt_raw in {"pdf", "docx"}:
        fmt_set = {fmt_raw}
    else:
        raise HTTPException(400, detail="formats must be pdf|docx|both")

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

    # Reserve run_id + write meta stage=queued so Liber can poll immediately.
    run_id, _, _, out_dir, logs_dir = prepare_run_dirs(src_path, project_root=ROOT)
    meta0 = {
        "run_id": run_id,
        "source": str(resolve_text_file(src_path)),
        "intent": full_intent,
        "formats": sorted(fmt_set),
        "dry_run": is_dry,
        "max_images": max_images,
        "max_charts": max_charts,
        "user_figures": [f.get("id") for f in user_figures],
        "status": "running",
        "stage": "queued",
    }
    payload0 = json.dumps(meta0, ensure_ascii=False, indent=2)
    (logs_dir / "meta.json").write_text(payload0, encoding="utf-8")
    (out_dir / "meta.json").write_text(payload0, encoding="utf-8")

    async def _spawn() -> None:
        # Keep the asyncio loop free; Playwright/LLM run in a worker thread.
        await asyncio.to_thread(
            partial(
                _bg_run_pipeline,
                src_path,
                run_id=run_id,
                formats=fmt_set,
                dry_run=is_dry,
                intent=full_intent,
                max_images=max_images,
                max_charts=max_charts,
                user_figures=user_figures,
            )
        )

    background_tasks.add_task(_spawn)

    return JSONResponse(
        status_code=202,
        content={
            "run_id": run_id,
            "status": "started",
            "stage": "queued",
            "max_charts": max_charts,
            "max_images": max_images,
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
        }
    if status == "error":
        return {
            "run_id": run_id,
            "status": "error",
            "stage": "error",
            "error": meta.get("error") or "pipeline failed",
            "message": meta.get("error") or "pipeline failed",
            "hint": f"logs: runs/logs/{run_id}",
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
    return _build_preview_payload(run_id, out_dir, media if isinstance(media, dict) else {})


class ChartEditBody(BaseModel):
    palette: str | None = Field(default="editorial")
    style: str | None = Field(default="")
    chart_type: str | None = Field(default="")
    formats: str = Field(default="both")


class FigureEditBody(BaseModel):
    """mode=generate → POST /generate; mode=edit → POST /edit with current PNG."""

    mode: str = Field(default="generate")
    prompt: str = Field(default="")
    caption: str | None = Field(default=None)
    formats: str = Field(default="both")


@app.post("/api/runs/{run_id}/charts/{chart_id}/edit")
async def edit_run_chart(run_id: str, chart_id: str, body: ChartEditBody) -> dict[str, Any]:
    """Restyle one chart in-place and rebuild PDF/DOCX (same PNG path → docs update)."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    if not _FILE_OK.match(chart_id):
        raise HTTPException(400, detail="invalid chart_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not out_dir.is_dir():
        raise HTTPException(404, detail="run not found")

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
        "warnings": [],
    }


def _warnings(meta: dict[str, Any], *, max_images: int) -> list[str]:
    warnings: list[str] = []
    planned = meta.get("figures_planned") or []
    media = meta.get("media_status") or {}
    if planned and max_images > 0:
        if not image_api_configured():
            warnings.append("IMAGE_API_BASE_URL empty — figure slots stripped")
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
