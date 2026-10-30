"""FastAPI demo wrapper around run_pipeline (for React UI)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
)

from case3.chart_html import CHART_TYPES
from case3.chart_style import palette_public
from case3.charts import max_charts_from_env
from case3.diagrams import max_diagrams_from_env
from case3.envfile import load_dotenv
from case3.generate import max_images_from_env, resolve_text_file
from case3.desk_health import build_desk_probes, probe_soffice, probe_vision
from case3.image_api import image_api_configured, probe_image_api
from case3.api_photo import quick_photo_edit
from case3.run_events import EVENTS
from case3.pipeline import PipelineError, prepare_run_dirs, run_pipeline
from case3.render import IMAGE, ensure_image
from case3.run_cancel import mark_cancel_requested
from case3.user_photos import UserPhotoError, save_user_photos
from case3.intent_compose import build_intent_from_ui
from case3 import run_store
from case3.run_store import (
    RUN_ID_OK as _RUN_ID_OK,
    build_preview_payload as _build_preview_payload,
    load_diagrams_from_out as _load_diagrams_from_out,
    parse_formats_form,
    resolve_run_dir as _resolve_run_dir,
    safe_run_file as _safe_run_file,
)

log = logging.getLogger("case3.api")

load_dotenv(run_store.ROOT / ".env")


def __getattr__(name: str):
    """``api.ROOT`` always tracks ``run_store.ROOT`` (canonical for Liber runs)."""
    if name == "ROOT":
        return run_store.ROOT
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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


# Win desk: parallel daemon pipelines share case3 FileHandlers + meta lock and
# leave zombies (stage=images/inject forever). One report at a time.
_PIPELINE_SLOT = threading.Lock()
_PIPELINE_ACTIVE_ID: str | None = None
_PIPELINE_ACTIVE_GUARD = threading.Lock()


def _pipeline_active_run() -> str | None:
    with _PIPELINE_ACTIVE_GUARD:
        return _PIPELINE_ACTIVE_ID


def _claim_pipeline_slot(run_id: str) -> str | None:
    """Return None if claimed; else the run_id that still holds the slot."""
    global _PIPELINE_ACTIVE_ID
    if not _PIPELINE_SLOT.acquire(blocking=False):
        return _pipeline_active_run() or "busy"
    with _PIPELINE_ACTIVE_GUARD:
        _PIPELINE_ACTIVE_ID = run_id
    return None


def _bind_pipeline_slot(run_id: str) -> None:
    global _PIPELINE_ACTIVE_ID
    with _PIPELINE_ACTIVE_GUARD:
        _PIPELINE_ACTIVE_ID = run_id


def _release_pipeline_slot(run_id: str | None = None) -> None:
    """Drop active label (if ours) and release the desk slot lock."""
    global _PIPELINE_ACTIVE_ID
    with _PIPELINE_ACTIVE_GUARD:
        if run_id is None or _PIPELINE_ACTIVE_ID in {run_id, "pending"} or _PIPELINE_ACTIVE_ID is None:
            _PIPELINE_ACTIVE_ID = None
        elif _PIPELINE_ACTIVE_ID == run_id:
            _PIPELINE_ACTIVE_ID = None
        else:
            # finally from our thread — always clear; slot is single-owner
            _PIPELINE_ACTIVE_ID = None
    try:
        _PIPELINE_SLOT.release()
    except RuntimeError:
        pass


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
            project_root=run_store.ROOT,
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
        # Presentation: Liber UI also POSTs /slides; auto-kick so CLI/matrix
        # get PPTX without a browser (idempotent if already running).
        if (output_mode or "").strip().lower() == "presentation":
            try:
                from case3.api_slides import _kick_slides_thread
                from case3.deck_theme import normalize_pack_id
                from case3.run_events import EVENTS as _EV
                from case3.run_meta import read_meta, write_meta

                out = run_store.ROOT / "runs" / "out" / run_id
                meta = read_meta(out) or {}
                st_slides = str(meta.get("slides_status") or "idle")
                if str(meta.get("status") or "") == "ok" and st_slides in {
                    "idle",
                    "",
                    "error",
                }:
                    pack = normalize_pack_id(
                        (
                            meta.get("slides_theme_pack")
                            or meta.get("deck_pack")
                            or "atelier"
                        )
                    )
                    prev_style = meta.get("slides_style")
                    if not isinstance(prev_style, dict):
                        prev_style = {}
                    structure_id = (
                        prev_style.get("structure_id")
                        if prev_style.get("structure_id") is not None
                        else meta.get("slides_structure_id")
                    )
                    style_settings = prev_style.get("style_settings")
                    if style_settings is not None and not isinstance(
                        style_settings, dict
                    ):
                        style_settings = None
                    meta["slides_style"] = {
                        "theme_pack": pack,
                        "structure_id": structure_id,
                        "style_settings": style_settings,
                    }
                    meta["slides_theme_pack"] = pack
                    meta["slides_structure_id"] = structure_id
                    meta["slides_status"] = "running"
                    meta["slides_stage"] = "starting"
                    meta["slides_error"] = None
                    meta["slides_kick_source"] = "api_auto"
                    write_meta(
                        out,
                        meta,
                        logs_dir=run_store.ROOT / "runs" / "logs" / run_id,
                    )
                    _EV.reopen(run_id)
                    _EV.bind_out(run_id, out)
                    _EV.publish_stage(run_id, "starting", scope="slides")
                    _kick_slides_thread(run_id)
                    log.info(
                        "auto-kicked slides run_id=%s pack=%s structure=%s",
                        run_id,
                        pack,
                        structure_id,
                    )
            except Exception:  # noqa: BLE001
                log.exception("auto-kick slides failed run_id=%s", run_id)
    except PipelineError:
        # meta already written with status=error
        log.exception("background pipeline failed run_id=%s", run_id)
    except Exception:  # noqa: BLE001
        log.exception("background pipeline crashed run_id=%s", run_id)
        out = run_store.ROOT / "runs" / "out" / run_id
        logs = run_store.ROOT / "runs" / "logs" / run_id
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
    finally:
        _release_pipeline_slot(run_id)


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
    deck_structure_id: str = Form(""),
    deck_style_json: str = Form(""),
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
    upload_dir = run_store.ROOT / "runs" / "uploads" / datetime_stamp()
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
        return await quick_photo_edit(
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

    # One report at a time on Win (parallel FileHandlers + Image hang → zombies).
    busy = _claim_pipeline_slot("pending")
    if busy is not None:
        raise HTTPException(
            409,
            detail=(
                f"Уже идёт прогон {busy}. Дождись конца или убей python.exe "
                "и перезапусти api.cmd."
            ),
        )

    # Reserve run_id + write stage=llm BEFORE kick (Win: 2nd run sat on queued while
    # prior LLM thread still held the desk; Liber must not wait on thread scheduling).
    try:
        run_id, _, _, out_dir, logs_dir = prepare_run_dirs(src_path, project_root=run_store.ROOT)
        _bind_pipeline_slot(run_id)
    except Exception:
        _release_pipeline_slot("pending")
        raise

    from case3.deck_structure import normalize_structure_id
    from case3.deck_theme import normalize_pack_id

    pack0 = normalize_pack_id((deck_pack or "").strip()[:40] or "atelier")
    structure0 = normalize_structure_id((deck_structure_id or "").strip() or None)
    style_settings0: dict[str, Any] | None = None
    raw_style = (deck_style_json or "").strip()
    if raw_style:
        try:
            parsed_style = json.loads(raw_style)
            if isinstance(parsed_style, dict):
                style_settings0 = {
                    str(k): str(v)
                    for k, v in parsed_style.items()
                    if isinstance(k, str) and v is not None
                }
        except json.JSONDecodeError:
            style_settings0 = None
    slides_style0 = {
        "theme_pack": pack0,
        "structure_id": structure0,
        "style_settings": style_settings0,
    }
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
        "deck_pack": pack0,
        "slides_theme_pack": pack0,
        "slides_structure_id": structure0,
        "slides_style": slides_style0,
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

    # Slot already claimed — thread only releases in finally (do not claim again).
    threading.Thread(
        target=_bg_run_pipeline,
        kwargs={
            "src_path": src_path,
            "run_id": run_id,
            "formats": fmt_set,
            "dry_run": is_dry,
            "intent": full_intent,
            "max_images": max_images,
            "max_charts": max_charts,
            "max_diagrams": max_diagrams,
            "user_figures": user_figures,
            "output_mode": out_mode,
        },
        name=f"case3-pipeline-{run_id}",
        daemon=True,
    ).start()

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


@app.get("/api/runs/{run_id}/status")
def get_run_status(run_id: str) -> dict[str, Any]:
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    out_root = (run_store.ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    meta_path = out_dir / "meta.json"
    if not meta_path.is_file():
        logs_meta = run_store.ROOT / "runs" / "logs" / run_id / "meta.json"
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
        work_dir = run_store.ROOT / "runs" / "work" / run_id
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
        out_dir = run_store.ROOT / "runs" / "out" / run_id
    return _run_result_payload(run_id, out_dir, meta)


def _media_previews(
    run_id: str, out_dir: Path, media: dict[str, Any]
) -> list[dict[str, str]]:
    """PNG thumbnails that succeeded (charts / Image API) under out/figures/."""
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


@app.get("/api/runs/{run_id}/preview")
def get_run_preview(run_id: str) -> dict[str, Any]:
    out_dir = _resolve_run_dir(run_id)
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


def _bg_resume_pipeline(run_id: str) -> None:
    print(f"[case3] resume thread start run_id={run_id}", flush=True)
    log.info("resume thread start run_id=%s", run_id)
    from case3.pipeline import PipelineError, resume_pipeline

    try:
        resume_pipeline(run_id, project_root=run_store.ROOT)
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
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    work_dir = run_store.ROOT / "runs" / "work" / run_id
    out_root = (run_store.ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    meta_path = out_dir / "meta.json"
    if not meta_path.is_file():
        logs_meta = run_store.ROOT / "runs" / "logs" / run_id / "meta.json"
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
    logs_dir = run_store.ROOT / "runs" / "logs" / run_id
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "meta.json").write_text(payload, encoding="utf-8")
    _kick_resume_thread(run_id)
    return {"run_id": run_id, "status": "started", "resumed_from": meta.get("failed_stage")}


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, Any]:
    """Cooperative stop: UI frees immediately; pipeline/slides exit between stages."""
    if not _RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    out_root = (run_store.ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)):
        raise HTTPException(404, detail="run not found")
    logs_dir = run_store.ROOT / "runs" / "logs" / run_id
    if not (out_dir / "meta.json").is_file() and not (logs_dir / "meta.json").is_file():
        raise HTTPException(404, detail="run not found")
    meta = mark_cancel_requested(out_dir, logs_dir=logs_dir)
    from case3.api_slides import _slides_patch_lock, _slides_patch_pending

    with _slides_patch_lock:
        _slides_patch_pending.pop(run_id, None)
    return {
        "run_id": run_id,
        "status": "cancelling",
        "cancel_requested": True,
        "pipeline_status": meta.get("status"),
        "slides_status": meta.get("slides_status"),
    }


@app.get("/api/runs/{run_id}/figures/{name}")
def download_figure(run_id: str, name: str) -> FileResponse:
    if not name.lower().endswith(".png"):
        raise HTTPException(400, detail="only PNG figures")
    path = _safe_run_file(run_id, "figures", name)
    return FileResponse(path, media_type="image/png", filename=path.name)


from case3.api_edits import router as edits_router
from case3.api_photo import router as photo_router
from case3.api_slides import router as slides_router
from case3.api_stream import router as stream_router

app.include_router(edits_router)
app.include_router(photo_router)
app.include_router(slides_router)
app.include_router(stream_router)
