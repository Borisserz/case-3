"""Deck / slides routes (mounted on main FastAPI app)."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from case3.deck_theme import list_public_packs, normalize_pack_id
from case3.run_meta import read_meta, write_meta
from case3 import run_store
from case3.run_store import FILE_OK, RUN_ID_OK, safe_run_file

log = logging.getLogger("case3.api_slides")
router = APIRouter(tags=["slides"])

# Coalesce concurrent IR patches: latest deck wins, one rebuild worker per run.
_slides_patch_lock = threading.Lock()
_slides_patch_pending: dict[str, dict[str, Any]] = {}
_slides_patch_busy: set[str] = set()


def _write_slides_crash(run_id: str, message: str) -> None:
    """Persist slides_status=error so UI does not sit on queued forever."""
    out = run_store.ROOT / "runs" / "out" / run_id
    logs = run_store.ROOT / "runs" / "logs" / run_id
    meta = read_meta(out) or {"run_id": run_id}
    if "run_id" not in meta:
        meta["run_id"] = run_id
    meta["slides_status"] = "error"
    meta["slides_stage"] = "error"
    meta["slides_error"] = message
    try:
        write_meta(out, meta, logs_dir=logs)
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
    logs = run_store.ROOT / "runs" / "logs" / run_id
    try:
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
    except OSError:
        pass
    return True


def _bg_run_slides(run_id: str) -> None:
    from case3.slides_job import run_slides_job

    try:
        run_slides_job(run_id, root=run_store.ROOT)
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


@router.get("/api/deck-themes")
def deck_themes() -> dict[str, Any]:
    """Public catalog of Liber deck theme packs (deck-only)."""
    from case3.deck_structure import list_structures

    return {"packs": list_public_packs(), "structures": list_structures()}


@router.post("/api/runs/{run_id}/slides")
async def start_slides(
    run_id: str,
    body: SlidesStartBody | None = Body(default=None),
) -> JSONResponse:
    if not RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    out_root = (run_store.ROOT / "runs" / "out").resolve()
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

    # Merge with desk-stamped style: Liber UI kick often omits structure_id
    # (stale deckStyle / race with auto-kick) and would freeform-collapse the deck.
    prev_style = meta.get("slides_style")
    if not isinstance(prev_style, dict):
        prev_style = {}
    body_structure = body.structure_id if body else None
    body_pack = body.theme_pack if body else None
    body_settings = body.style_settings if body else None

    structure_id = normalize_structure_id(body_structure)
    if structure_id is None:
        structure_id = normalize_structure_id(
            prev_style.get("structure_id")
            if prev_style.get("structure_id") is not None
            else meta.get("slides_structure_id")
        )

    prev_pack = normalize_pack_id(
        meta.get("slides_theme_pack") or prev_style.get("theme_pack") or "atelier"
    )
    restored_desk_pack = False
    if body_pack:
        pack = normalize_pack_id(body_pack)
        # Default atelier in the body without an explicit structure change must
        # not clobber a non-atelier pack already stamped for this run.
        if (
            body_structure is None
            and structure_id
            and pack == "atelier"
            and prev_pack != "atelier"
        ):
            pack = prev_pack
            restored_desk_pack = True
    else:
        pack = prev_pack

    settings = body_settings if isinstance(body_settings, dict) else None
    if (settings is None or restored_desk_pack) and isinstance(
        prev_style.get("style_settings"), dict
    ):
        settings = prev_style.get("style_settings")

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
    logs = run_store.ROOT / "runs" / "logs" / run_id
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


@router.get("/api/runs/{run_id}/slides")
def _chart_index(out_dir: Path) -> dict[str, dict[str, Any]]:
    """Type and palette for each chart so the deck editor opens on the real figure."""
    path = out_dir / "figures.json"
    if not path.is_file():
        return {}
    try:
        fj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for ch in fj.get("charts") or []:
        if not isinstance(ch, dict):
            continue
        cid = str(ch.get("id") or "").strip()
        if not cid:
            continue
        out[cid] = {
            "type": str(ch.get("type") or ""),
            "palette": str(ch.get("palette") or ""),
            "style_user": bool(ch.get("style_user")),
        }
    return out


def get_slides(run_id: str) -> dict[str, Any]:
    if not RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    out_root = (run_store.ROOT / "runs" / "out").resolve()
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
                stamp = int((out_dir / name).stat().st_mtime)
                downloads[key] = f"/api/runs/{run_id}/files/{name}?v={stamp}"
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
            f"/api/runs/{run_id}/slides/png/{p.name}?v={int(p.stat().st_mtime)}"
            for p in sorted((out_dir / "slides").glob("slide_*.png"))
        ]
        if (out_dir / "slides").is_dir()
        else [],
        "downloads": downloads,
        "deck_pdf_mode": deck_pdf_mode,
        "charts": _chart_index(out_dir),
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
            rebuild_slides_from_deck(run_id, deck, root=run_store.ROOT)
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


def _load_deck_for_patch(run_id: str, out_dir: Path) -> tuple[dict[str, Any], Path]:
    """Shared guards for text + structure slide patches."""
    if not RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_root = (run_store.ROOT / "runs" / "out").resolve()
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
    run_id: str,
    out_dir: Path,
    ir_path: Path,
    patched: dict[str, Any],
    *,
    undo_kind: str = "slides",
    undo_target: str = "*",
    rebuild: bool = True,
    capture_undo: bool = True,
) -> tuple[bool, dict[str, Any] | None]:
    """Snapshot undo, write IR, optionally spawn coalesce worker.

    ``rebuild=False`` → IR-only (edit session); twin/PPTX flush on Готово.
    Returns (queued_or_skipped, undo meta).
    """
    undo_desc: dict[str, Any] | None = None
    if capture_undo:
        try:
            from case3.run_undo import capture_before_edit, undo_meta

            capture_before_edit(out_dir, kind=undo_kind, target=undo_target)
            undo_desc = undo_meta(out_dir)
        except Exception as exc:  # noqa: BLE001 — edit still proceeds
            log.warning("slides patch undo capture failed: %s", exc)
    else:
        try:
            from case3.run_undo import undo_meta

            undo_desc = undo_meta(out_dir)
        except Exception:  # noqa: BLE001
            undo_desc = None

    try:
        ir_path.write_text(
            json.dumps(patched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        raise HTTPException(500, detail="could not write deck.json") from exc

    if not rebuild:
        return False, undo_desc

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
    return already, undo_desc


def _parse_rebuild_q(raw: str | None) -> bool:
    if raw is None or str(raw).strip() == "":
        return True
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


@router.patch("/api/runs/{run_id}/slides/ir")
async def patch_slides_ir(
    run_id: str,
    body: SlidesIrPatchBody,
    rebuild: str | None = None,
) -> JSONResponse:
    """Patch deck text fields; rebuild twin+PPTX unless ``rebuild=0`` (session)."""
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    base, ir_path = _load_deck_for_patch(run_id, out_dir)
    do_rebuild = _parse_rebuild_q(rebuild)

    from case3.slides_ir import DeckIrError
    from case3.slides_patch import apply_deck_text_patch

    try:
        patched = apply_deck_text_patch(base, {"slides": body.slides})
    except DeckIrError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    already, undo_desc = _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        patched,
        undo_kind="slides_text",
        undo_target=",".join(
            str(s.get("id") or "") for s in (body.slides or []) if isinstance(s, dict)
        )
        or "*",
        rebuild=do_rebuild,
    )
    if not do_rebuild:
        payload: dict[str, Any] = {
            "run_id": run_id,
            "status": "ok",
            "slides_status": "ok",
            "slides_stage": "ir",
            "rebuilt": False,
            "deck": patched,
        }
        if undo_desc:
            payload["undo"] = undo_desc
        return JSONResponse(payload, status_code=200)
    payload = {
        "run_id": run_id,
        "status": "started",
        "slides_status": "running",
        "slides_stage": "patch",
        "queued": already,
        "deck": patched,
    }
    if undo_desc:
        payload["undo"] = undo_desc
    return JSONResponse(payload, status_code=202)


@router.post("/api/runs/{run_id}/slides/rebuild")
async def rebuild_slides_docs(run_id: str) -> JSONResponse:
    """Flush twin + PPTX from current ``deck.json`` (edit-session «Готово»)."""
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    base, ir_path = _load_deck_for_patch(run_id, out_dir)
    already, undo_desc = _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        base,
        undo_kind="slides_flush",
        undo_target="*",
        rebuild=True,
        capture_undo=False,
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": "started",
        "slides_status": "running",
        "slides_stage": "patch",
        "queued": already,
        "deck": base,
    }
    if undo_desc:
        payload["undo"] = undo_desc
    return JSONResponse(payload, status_code=202)


@router.post("/api/runs/{run_id}/slides/structure")
async def post_slides_structure(
    run_id: str,
    body: SlidesStructureBody,
) -> JSONResponse:
    """Reorder / duplicate / delete slides — IR patch + rebuild twin/PPTX (no LLM)."""
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
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

    already, undo_desc = _enqueue_deck_rebuild(
        run_id,
        out_dir,
        ir_path,
        patched,
        undo_kind="slides_structure",
        undo_target=str(body.op or "*"),
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": "started",
        "slides_status": "running",
        "slides_stage": "patch",
        "queued": already,
        "op": body.op,
        "deck": patched,
    }
    if undo_desc:
        payload["undo"] = undo_desc
    return JSONResponse(payload, status_code=202)


@router.get("/api/runs/{run_id}/slides/png/{name}")
def download_slide_png(run_id: str, name: str) -> FileResponse:
    if not name.lower().endswith(".png") or not FILE_OK.match(name):
        raise HTTPException(400, detail="invalid png name")
    path = safe_run_file(run_id, "slides", name)
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.get("/api/runs/{run_id}/slides/media/{name}")
def download_slide_media(run_id: str, name: str) -> FileResponse:
    """Chart/figure PNG from figures/, or diagram PNG from slides/diagrams/."""
    if not name.lower().endswith(".png") or not FILE_OK.match(name):
        raise HTTPException(400, detail="invalid media name")
    out_dir = (run_store.ROOT / "runs" / "out" / run_id).resolve()
    for parts in (
        ("slides", "charts", name),
        ("slides", "diagrams", name),
        ("figures", name),
    ):
        try:
            path = safe_run_file(run_id, *parts)
            return FileResponse(path, media_type="image/png", filename=path.name)
        except HTTPException:
            continue
    raise HTTPException(404, detail="media not found")


