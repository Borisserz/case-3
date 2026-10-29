"""intent+source → LLM tex → Kandinsky + HTML charts → inject → PDF/DOCX."""

from __future__ import annotations

import json
import logging
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable  # Any used by user_figures metas

from case3.charts import generate_all_charts, max_charts_from_env
from case3.chat_summary import try_generate_chat_summary
from case3.diagrams import max_diagrams_from_env
from case3.generate import generate_document, max_images_from_env, resolve_text_file
from case3.inject import write_injected
from case3.image_api import ImageApiConfig, generate_all_figures
from case3.render import RenderError, render_tex
from case3.run_cancel import RunCancelled, raise_if_cancelled
from case3.run_events import EVENTS
from case3.summary_bus import BUS
from case3.user_photos import (
    ensure_user_slots_in_tex,
    materialize_user_figures,
    merge_user_figures,
)
log = logging.getLogger("case3.pipeline")

# Stages eligible for POST /resume (after LLM artifacts exist).
RESUME_STAGES = frozenset({"images", "charts", "inject", "latex", "docx"})


def resolve_pipeline_formats(formats: set[str] | None) -> set[str]:
    """Default print formats. ``None`` → ``{pdf}``; empty set stays empty (none)."""
    if formats is None:
        return {"pdf"}
    return set(formats)


def _find_run_tex(work: Path, out: Path) -> Path | None:
    for d in (work, out):
        if not d.is_dir():
            continue
        cands = sorted(
            p for p in d.glob("*.tex") if ".raw_model" not in p.name
        )
        if cands:
            return cands[0]
    return None


def _media_ok_on_disk(mid: str, status: dict[str, Any], figs_dir: Path) -> bool:
    st = status.get(mid)
    if not (isinstance(st, dict) and st.get("ok")):
        return False
    return (figs_dir / f"{mid}.png").is_file()


def can_resume_run(
    meta: dict[str, Any], *, work: Path, out: Path
) -> bool:
    """True when Liber may offer «Продолжить» for this failed run."""
    if str(meta.get("status") or "") != "error":
        return False
    if str(meta.get("failed_stage") or "") not in RESUME_STAGES:
        return False
    if _find_run_tex(work, out) is None:
        return False
    fj = work / "figures.json"
    if not fj.is_file():
        fj = out / "figures.json"
    return fj.is_file()


def _record_failed_stage(meta: dict[str, Any]) -> None:
    """Keep the real craft stage when flipping status to error."""
    prev = str(meta.get("stage") or "").strip()
    if prev and prev not in {"error", "ok", "cancelled", "queued"}:
        meta["failed_stage"] = prev
    elif not meta.get("failed_stage"):
        meta["failed_stage"] = prev or "error"


class PipelineError(RuntimeError):
    """Pipeline failed after writing meta/logs — includes run_id for debug upload."""

    def __init__(
        self,
        message: str,
        *,
        run_id: str,
        out_dir: Path,
        logs_dir: Path,
        meta: dict,
    ) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.out_dir = out_dir
        self.logs_dir = logs_dir
        self.meta = meta


def _latex_log_tail(path: Path | None, *, lines: int = 40) -> str:
    """Last N lines of a TeX log (C8 diagnostics)."""
    if path is None or not Path(path).is_file():
        return ""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    parts = text.splitlines()
    if not parts:
        return ""
    return "\n".join(parts[-max(1, lines) :])


def _find_latex_log(logs_dir: Path) -> Path | None:
    if not logs_dir.is_dir():
        return None
    preferred = sorted(logs_dir.glob("*.log"))
    for p in preferred:
        if p.name != "pipeline.log":
            return p
    pipe = logs_dir / "pipeline.log"
    return pipe if pipe.is_file() else None


def _attach_error_diagnostics(
    meta: dict[str, Any],
    *,
    logs_dir: Path,
    error: str,
    log_path: Path | None = None,
) -> dict[str, Any]:
    """Enrich meta with failed media ids + latex log tail (C8)."""
    out = dict(meta)
    media = out.get("media_status") or {}
    if not isinstance(media, dict):
        media = {}
    failed_c = [
        cid
        for cid in (out.get("charts_planned") or [])
        if not (isinstance(media.get(cid), dict) and media[cid].get("ok"))
    ]
    failed_f = [
        fid
        for fid in (out.get("figures_planned") or [])
        if not (isinstance(media.get(fid), dict) and media[fid].get("ok"))
    ]
    out["failed_charts"] = failed_c
    out["failed_figures"] = failed_f
    bits = [str(error).strip()]
    if failed_c:
        bits.append(f"charts failed: {', '.join(failed_c)}")
    if failed_f:
        bits.append(f"figures failed: {', '.join(failed_f)}")
    out["error"] = "; ".join(b for b in bits if b)
    lp = Path(log_path) if log_path else _find_latex_log(logs_dir)
    tail = _latex_log_tail(lp)
    if tail:
        out["latex_log_tail"] = tail
        out["latex_log_path"] = str(lp) if lp else None
    return out


def _diagram_chat_blurb(diagrams: list[dict[str, Any]] | None) -> str:
    """Short Liber chat line without a second Vision round-trip."""
    items = [d for d in (diagrams or []) if isinstance(d, dict)]
    if not items:
        return "Схема готова — откройте вкладку «Схема» в панели."
    titles = [
        str(d.get("title") or d.get("id") or "схема").strip() for d in items
    ]
    titles = [t for t in titles if t]
    if len(titles) == 1:
        return f"Готово: схема «{titles[0]}». Ниже — превью Mermaid."
    shown = ", ".join(f"«{t}»" for t in titles[:3])
    more = f" и ещё {len(titles) - 3}" if len(titles) > 3 else ""
    return f"Готово: {len(titles)} схем — {shown}{more}."


def _presentation_chat_blurb(
    *,
    charts: list[dict[str, Any]] | None = None,
    figures: list[dict[str, Any]] | None = None,
) -> str:
    """Local blurb for presentation — skip second LLM; slides job is the product."""
    n_ch = len([c for c in (charts or []) if isinstance(c, dict)])
    n_fig = len([f for f in (figures or []) if isinstance(f, dict)])
    bits: list[str] = []
    if n_ch:
        bits.append(f"графиков: {n_ch}")
    if n_fig:
        bits.append(f"фото: {n_fig}")
    media = f" ({', '.join(bits)})" if bits else ""
    return f"Ок, собираем презентацию{media}…"


def _write_meta(meta: dict[str, Any], out: Path, logs: Path) -> None:
    from case3.run_events import _meta_file_lock, write_meta_atomic

    with _meta_file_lock:
        # Drop internal craft cursor from on-disk payload noise (optional keep).
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        write_meta_atomic(out / "meta.json", payload, logs_meta=logs / "meta.json")


def _set_stage(
    meta: dict[str, Any],
    out: Path,
    logs: Path,
    stage: str,
    *,
    detail: str | None = None,
    status: str = "running",
    project_root: Path | None = None,
) -> None:
    meta["status"] = status
    meta["stage"] = stage
    if detail:
        meta["stage_detail"] = detail
    else:
        meta.pop("stage_detail", None)
    from case3.run_events import note_craft_stage

    # One steps[] row per stage id — not per cht_/fig_ detail bump.
    note_craft_stage(meta, stage=stage, scope="pipeline", detail=detail)
    _write_meta(meta, out, logs)
    run_id = str(meta.get("run_id") or "")
    if run_id:
        from case3.stage_eta import note_stage_enter

        # Only roll ETA when the stage id changes (not every cht_* detail bump).
        prev = str(meta.get("_eta_stage") or "")
        eta = None
        if stage != prev:
            eta = note_stage_enter(run_id, stage, project_root=project_root)
            meta["_eta_stage"] = stage
            timings = list(meta.get("stage_timings") or [])
            if isinstance(timings, list):
                timings.append({"stage": stage, "t": __import__("time").time()})
                meta["stage_timings"] = timings[-40:]
        EVENTS.publish_stage(
            run_id, stage, detail=detail, scope="pipeline", eta_s=eta
        )
        # Phase 2A: fine steps for charts / photos
        det = (detail or "").strip()
        if stage == "charts" and det.startswith("cht_"):
            EVENTS.publish_step(
                run_id, parent="charts", step_id=det, status="active", label=det
            )
        elif stage == "images" and det.startswith(("fig_", "usr_")):
            EVENTS.publish_step(
                run_id, parent="photos", step_id=det, status="active", label=det
            )
        EVENTS.scan_artifacts(run_id, out)


def prepare_run_dirs(
    source: Path,
    *,
    project_root: Path,
    run_id: str | None = None,
) -> tuple[str, Path, Path, Path, Path]:
    """Create work/out/logs for a run. Returns run_id, text_path, work, out, logs."""
    root = project_root.resolve()
    text_path = resolve_text_file(source)
    stem = text_path.stem
    if run_id is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{stem}_{stamp}"
    work = root / "runs" / "work" / run_id
    out = root / "runs" / "out" / run_id
    logs = root / "runs" / "logs" / run_id
    for d in (work, out, logs):
        d.mkdir(parents=True, exist_ok=True)
    return run_id, text_path, work, out, logs


def resume_pipeline(
    run_id: str,
    *,
    project_root: Path,
    on_stage: Callable[[str, str | None], None] | None = None,
) -> Path:
    """Continue a failed run without LLM: missing media → inject → render.

    Requires ``meta.status=error``, ``failed_stage`` in ``RESUME_STAGES``, and
    existing TeX + ``figures.json`` under work/out.
    """
    root = project_root.resolve()
    work = root / "runs" / "work" / run_id
    out = root / "runs" / "out" / run_id
    logs = root / "runs" / "logs" / run_id
    for d in (work, out, logs):
        d.mkdir(parents=True, exist_ok=True)

    meta_path = out / "meta.json"
    if not meta_path.is_file():
        meta_path = logs / "meta.json"
    if not meta_path.is_file():
        raise PipelineError(
            "resume: meta.json missing",
            run_id=run_id,
            out_dir=out,
            logs_dir=logs,
            meta={"run_id": run_id, "status": "error"},
        )
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(
            f"resume: corrupt meta.json ({exc})",
            run_id=run_id,
            out_dir=out,
            logs_dir=logs,
            meta={"run_id": run_id, "status": "error"},
        ) from exc
    if not isinstance(meta, dict):
        meta = {"run_id": run_id}

    if not can_resume_run(meta, work=work, out=out):
        raise PipelineError(
            "resume: run is not eligible",
            run_id=run_id,
            out_dir=out,
            logs_dir=logs,
            meta=meta,
        )

    tex_path = _find_run_tex(work, out)
    assert tex_path is not None  # can_resume_run checked
    # Prefer work copy for inject mutability
    if tex_path.parent != work:
        work_tex = work / tex_path.name
        shutil.copy2(tex_path, work_tex)
        tex_path = work_tex

    fj_path = work / "figures.json"
    if not fj_path.is_file():
        src_fj = out / "figures.json"
        shutil.copy2(src_fj, fj_path)
    try:
        fj = json.loads(fj_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fj = {}
    if not isinstance(fj, dict):
        fj = {}
    figures = [f for f in (fj.get("figures") or []) if isinstance(f, dict)]
    charts = [c for c in (fj.get("charts") or []) if isinstance(c, dict)]
    diagrams = [d for d in (fj.get("diagrams") or []) if isinstance(d, dict)]

    status: dict[str, Any] = {}
    for candidate in (work / "status.json", out / "status.json"):
        if candidate.is_file():
            try:
                loaded = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    status = dict(loaded)
                    break
            except (OSError, json.JSONDecodeError):
                pass
    if not status and isinstance(meta.get("media_status"), dict):
        status = dict(meta["media_status"])

    raw_fmt = meta.get("formats")
    if isinstance(raw_fmt, list):
        formats = set(str(x) for x in raw_fmt)
    elif isinstance(raw_fmt, (set, frozenset)):
        formats = set(raw_fmt)
    else:
        formats = {"pdf"}
    formats = resolve_pipeline_formats(formats)
    intent = meta.get("intent")
    if intent is not None:
        intent = str(intent)
    images_budget = int(meta.get("max_images") if meta.get("max_images") is not None else max_images_from_env())
    charts_budget = int(meta.get("max_charts") if meta.get("max_charts") is not None else max_charts_from_env())
    mode = str(meta.get("output_mode") or "auto").strip().lower()
    if mode not in {"report", "diagram", "presentation", "auto"}:
        mode = "auto"
    dry_run = bool(meta.get("dry_run"))
    failed_from = str(meta.get("failed_stage") or "")

    handler = logging.FileHandler(logs / "pipeline.log", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root_logger = logging.getLogger("case3")
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    meta["status"] = "running"
    meta["stage"] = "queued"
    meta.pop("error", None)
    meta.pop("traceback", None)
    meta.pop("latex_log_tail", None)
    meta.pop("cancel_requested", None)
    meta["resumed_from_stage"] = failed_from
    meta["resume_count"] = int(meta.get("resume_count") or 0) + 1
    meta["run_id"] = run_id
    stem = tex_path.stem
    figs_dir = work / "figures"
    figs_dir.mkdir(parents=True, exist_ok=True)
    # Restore PNGs from out/figures if work is empty but out has them
    out_figs = out / "figures"
    if out_figs.is_dir():
        for png in out_figs.glob("*.png"):
            dest = figs_dir / png.name
            if not dest.is_file():
                shutil.copy2(png, dest)

    from case3.stage_eta import load_timings

    load_timings(root)
    EVENTS.ensure(run_id)
    _write_meta(meta, out, logs)
    EVENTS.publish_stage(run_id, "queued", scope="pipeline")

    def bump(stage: str, detail: str | None = None) -> None:
        raise_if_cancelled(out)
        _set_stage(meta, out, logs, stage, detail=detail, project_root=root)
        if on_stage:
            on_stage(stage, detail)

    try:
        need_media = failed_from in {"images", "charts"} or any(
            not _media_ok_on_disk(str(x.get("id") or ""), status, figs_dir)
            for x in figures + charts
            if isinstance(x, dict) and x.get("id")
        )

        if need_media and figures and not dry_run and images_budget > 0:
            bump("images")
            status.update(materialize_user_figures(figures, figs_dir))
            need_api = [
                f
                for f in figures
                if str(f.get("source") or "") != "upload"
                and not _media_ok_on_disk(str(f.get("id") or ""), status, figs_dir)
            ]
            cfg = ImageApiConfig.from_env()
            cfg = replace(cfg, max_images=images_budget)
            if need_api and not cfg.base_url:
                for f in need_api:
                    fid = str(f.get("id") or "")
                    if fid:
                        status[fid] = {
                            "ok": False,
                            "error": "IMAGE_API_BASE_URL empty",
                            "kind": "figure",
                        }
            elif need_api:

                def _img_progress(fid: str) -> None:
                    bump("images", fid)

                from case3.chart_style import palette_from_intent

                pack_for_photos = (
                    str(meta.get("image_style_pack") or "")
                    or palette_from_intent(intent or "")
                    or "atelier"
                )
                status.update(
                    generate_all_figures(
                        need_api,
                        figs_dir,
                        cfg=cfg,
                        on_progress=_img_progress,
                        pack_id=pack_for_photos,
                    )
                )

        if need_media and charts and not dry_run and charts_budget > 0:
            bump("charts")
            need_charts = [
                c
                for c in charts
                if not _media_ok_on_disk(str(c.get("id") or ""), status, figs_dir)
            ]

            def _chart_progress(cid: str) -> None:
                bump("charts", cid)

            if need_charts:
                status.update(
                    generate_all_charts(
                        need_charts,
                        figs_dir,
                        work_root=work / "chart_work",
                        max_charts=charts_budget,
                        on_progress=_chart_progress,
                    )
                )
            from case3.slides_chart_data import attach_series_ir_to_charts

            attach_series_ir_to_charts(charts)
            fj["charts"] = charts
            fj_path.write_text(
                json.dumps(fj, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # Keep prior ok entries for ids we skipped
        meta["media_status"] = status
        (work / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        bump("inject")
        write_injected(tex_path, figures, status, charts=charts)
        shutil.copy2(tex_path, out / tex_path.name)
        for name in ("figures.json", "status.json"):
            p = work / name
            if p.is_file():
                shutil.copy2(p, out / name)
        if figs_dir.is_dir() and any(figs_dir.glob("*.png")):
            dest = out / "figures"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(figs_dir, dest)

        bump("latex" if formats else "summary")
        skip_print = not formats

        def _do_summary() -> tuple[str, str]:
            def on_delta(piece: str) -> None:
                BUS.publish(run_id, piece)

            media_facts = {
                "charts_planned": len(charts),
                "figures_planned": len(figures),
                "diagrams_planned": len(diagrams),
                "charts_ok": sum(
                    1
                    for c in charts
                    if _media_ok_on_disk(str(c.get("id") or ""), status, figs_dir)
                ),
                "figures_ok": sum(
                    1
                    for f in figures
                    if _media_ok_on_disk(str(f.get("id") or ""), status, figs_dir)
                ),
            }
            text, status_sum = try_generate_chat_summary(
                tex_path.read_text(encoding="utf-8"),
                intent=intent,
                media=media_facts,
                on_delta=on_delta,
            )
            BUS.finish(run_id, text, status_sum)
            return text, status_sum

        if dry_run or skip_print:
            artifacts = (
                {}
                if skip_print
                else render_tex(
                    tex_path,
                    out_dir=out,
                    formats=formats,
                    extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
                    log_dir=logs,
                    project_root=root,
                    force=True,
                    on_format=lambda fmt: bump(
                        "docx" if fmt == "docx" else "latex"
                    ),
                )
            )
            if dry_run:
                meta["chat_summary"] = ""
                meta["summary_status"] = "skipped"
                BUS.start(run_id)
                BUS.finish(run_id, "", "skipped")
            else:
                BUS.start(run_id)
                bump("summary")
                if mode == "diagram":
                    summary_text = _diagram_chat_blurb(diagrams)
                    summary_status = "ok"
                elif mode == "presentation":
                    summary_text = _presentation_chat_blurb(
                        charts=charts, figures=figures
                    )
                    summary_status = "ok"
                else:
                    summary_text, summary_status = _do_summary()
                BUS.finish(run_id, summary_text or "", summary_status)
                meta["chat_summary"] = summary_text or ""
                meta["summary_status"] = summary_status
        else:
            meta["summary_status"] = "streaming"
            meta["chat_summary"] = ""
            _write_meta(meta, out, logs)
            BUS.start(run_id)

            def _do_render() -> dict:
                return render_tex(
                    tex_path,
                    out_dir=out,
                    formats=formats,
                    extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
                    log_dir=logs,
                    project_root=root,
                    force=True,
                    on_format=lambda fmt: bump(
                        "docx" if fmt == "docx" else "latex"
                    ),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_r = pool.submit(_do_render)
                fut_s = pool.submit(_do_summary)
                artifacts = fut_r.result()
                bump("summary")
                summary_text, summary_status = fut_s.result()
            meta["chat_summary"] = summary_text or ""
            meta["summary_status"] = summary_status
            if summary_text:
                (out / "chat_summary.txt").write_text(
                    summary_text, encoding="utf-8"
                )

        raise_if_cancelled(out)
        meta["artifacts"] = {k: str(v) for k, v in artifacts.items()}
        meta["status"] = "ok"
        meta["stage"] = "ok"
        meta.pop("stage_detail", None)
        meta.pop("failed_stage", None)
        EVENTS.scan_artifacts(run_id, out)
        if mode != "presentation":
            EVENTS.publish_terminal(
                run_id,
                "ok",
                recap=EVENTS.success_recap(
                    run_id,
                    charts=sum(
                        1
                        for c in charts
                        if _media_ok_on_disk(str(c.get("id") or ""), status, figs_dir)
                    ),
                    figures=sum(
                        1
                        for f in figures
                        if _media_ok_on_disk(str(f.get("id") or ""), status, figs_dir)
                    ),
                ),
            )
        else:
            EVENTS.publish_stage(run_id, "pipeline_ok", scope="pipeline")
    except RunCancelled:
        meta["status"] = "cancelled"
        meta["stage"] = "cancelled"
        meta["error"] = "Остановлено"
        meta.pop("stage_detail", None)
        _write_meta(meta, out, logs)
        EVENTS.publish_terminal(run_id, "cancelled", error="Остановлено")
        return out
    except Exception as exc:
        _record_failed_stage(meta)
        meta["status"] = "error"
        meta["stage"] = "error"
        log_path = getattr(exc, "log_path", None) if isinstance(exc, RenderError) else None
        meta.update(
            _attach_error_diagnostics(
                meta,
                logs_dir=logs,
                error=str(exc),
                log_path=Path(log_path) if log_path else None,
            )
        )
        meta["traceback"] = traceback.format_exc()
        log.exception("resume pipeline failed")
        (logs / "error.txt").write_text(meta["traceback"], encoding="utf-8")
        _write_meta(meta, out, logs)
        from case3.stage_eta import error_hint

        EVENTS.publish_terminal(
            run_id,
            "error",
            error=str(meta.get("error") or exc),
            hint=error_hint(exc, stage=str(meta.get("failed_stage") or "")),
        )
        raise PipelineError(
            str(meta.get("error") or exc),
            run_id=run_id,
            out_dir=out,
            logs_dir=logs,
            meta=meta,
        ) from exc
    finally:
        if meta.get("status") not in {"error", "cancelled"}:
            _write_meta(meta, out, logs)
        root_logger.removeHandler(handler)
        handler.close()

    log.info("resume done run_id=%s out=%s", run_id, out)
    return out


def run_pipeline(
    source: Path,
    *,
    project_root: Path,
    formats: set[str] | None = None,
    dry_run: bool = False,
    intent: str | None = None,
    max_images: int | None = None,
    max_charts: int | None = None,
    max_diagrams: int | None = None,
    run_id: str | None = None,
    on_stage: Callable[[str, str | None], None] | None = None,
    user_figures: list[dict[str, Any]] | None = None,
    output_mode: str = "auto",
) -> Path:
    formats = resolve_pipeline_formats(formats)
    root = project_root.resolve()
    run_id, text_path, work, out, logs = prepare_run_dirs(
        source, project_root=root, run_id=run_id
    )
    stem = text_path.stem
    stamp = run_id.rsplit("_", 1)[-1] if "_" in run_id else datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    images_budget = max_images_from_env() if max_images is None else max(0, int(max_images))
    charts_budget = max_charts_from_env() if max_charts is None else max(0, int(max_charts))
    diagrams_budget = (
        max_diagrams_from_env()
        if max_diagrams is None
        else max(0, min(int(max_diagrams), 3))
    )
    mode = (output_mode or "auto").strip().lower()
    if mode not in {"report", "diagram", "presentation", "auto"}:
        mode = "auto"
    user_figs = list(user_figures or [])
    # Uploads always need figure budget even if UI had «без фото» half-checked
    if user_figs:
        images_budget = max(images_budget, len(user_figs))
        images_budget = min(images_budget, 8)

    # Heartbeat BEFORE FileHandler / load_timings: on Win those can stall (AV lock)
    # and Liber sat forever on status=running stage=queued («Читаю Source»).
    meta: dict = {
        "run_id": run_id,
        "source": str(text_path),
        "intent": intent,
        "formats": sorted(formats),
        "output_mode": mode,
        "dry_run": dry_run,
        "max_images": images_budget,
        "max_charts": charts_budget,
        "max_diagrams": diagrams_budget,
        "user_figures": [f.get("id") for f in user_figs],
        "started_at": stamp,
        "status": "running",
        "stage": "llm",
        "stage_detail": "жду модель…",
    }
    EVENTS.ensure(run_id)
    from case3.run_events import note_craft_stage

    note_craft_stage(meta, stage="llm", scope="pipeline", detail="жду модель…")
    _write_meta(meta, out, logs)
    EVENTS.publish_stage(run_id, "llm", detail="жду модель…", scope="pipeline")

    handler = logging.FileHandler(logs / "pipeline.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger = logging.getLogger("case3")
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    from case3.stage_eta import load_timings

    load_timings(root)

    def bump(stage: str, detail: str | None = None) -> None:
        raise_if_cancelled(out)
        _set_stage(
            meta, out, logs, stage, detail=detail, project_root=root
        )
        if on_stage:
            on_stage(stage, detail)

    try:
        # Re-enter llm for ETA / craft cursor (stage id unchanged → light bump).
        bump("llm", "жду модель…")
        tex_path = work / f"{stem}.tex"
        # Reserve slots for uploads so the LLM plans fewer generated photos.
        llm_image_budget = max(0, images_budget - len(user_figs))
        _, figures, charts, diagrams = generate_document(
            text_path,
            out_tex=tex_path,
            intent=intent,
            gold_dir=root / "prompt" / "gold",
            dry_run=dry_run,
            max_images=llm_image_budget,
            max_charts=charts_budget,
            max_diagrams=diagrams_budget,
            cancel_check=lambda: raise_if_cancelled(out),
        )
        figures = merge_user_figures(figures, user_figs, max_images=images_budget)
        # Mode «Схема»: product is Mermaid in chat — never wait on Image API / charts
        # (LLM often still emits figures[]; that was the 10min Win hang after diagrams ready).
        if mode == "diagram":
            if figures or charts:
                log.info(
                    "diagram mode: dropping %d figures / %d charts (schema-only)",
                    len(figures),
                    len(charts),
                )
            figures = []
            charts = []
        raw_tex = tex_path.read_text(encoding="utf-8")
        tex_path.write_text(ensure_user_slots_in_tex(raw_tex, user_figs), encoding="utf-8")
        # Persist merged figures.json for Liber edit / preview
        fj_path = work / "figures.json"
        if fj_path.is_file():
            try:
                fj = json.loads(fj_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                fj = {}
        else:
            fj = {}

        # Mode «Схема»: optional second LLM pass. Skip when draft already has Mermaid
        # (default) — set CASE3_DIAGRAM_REPAIR=1 to force. Soft-fail keeps draft.
        if mode == "diagram" and diagrams and not dry_run:
            import os as _os

            force_repair = (_os.environ.get("CASE3_DIAGRAM_REPAIR") or "").strip() == "1"

            def _draft_has_mermaid(d: dict) -> bool:
                body = str(d.get("mermaid") or d.get("code") or "").strip()
                return len(body) >= 40

            if not force_repair and all(
                isinstance(d, dict) and _draft_has_mermaid(d) for d in diagrams
            ):
                meta["diagrams_repair_skipped"] = "draft_has_mermaid"
                log.info(
                    "diagram_repair skipped — draft mermaid present "
                    "(CASE3_DIAGRAM_REPAIR=1 to force)"
                )
            else:
                bump("diagram_repair", "второй вызов модели…")
                from case3.diagram_repair import repair_diagrams
                from case3.llm_client import LLMClient, LLMConfig

                fj["diagrams_draft"] = diagrams
                source_text = text_path.read_text(encoding="utf-8")
                from case3.chart_style import palette_from_intent

                diagrams, repair_meta = repair_diagrams(
                    diagrams,
                    source=source_text,
                    intent=intent or "",
                    max_diagrams=diagrams_budget,
                    client=LLMClient(LLMConfig.from_env()),
                    palette=palette_from_intent(intent or ""),
                )
                meta["diagrams_repaired"] = bool(repair_meta.get("diagrams_repaired"))
                meta["diagrams_draft_slop"] = bool(repair_meta.get("diagrams_draft_slop"))

        fj["figures"] = figures
        fj["charts"] = charts
        fj["diagrams"] = diagrams
        # Persist ChartSeriesIR for native PPTX (prefer over HTML regex later).
        from case3.slides_chart_data import attach_series_ir_to_charts

        attach_series_ir_to_charts(charts)
        fj["charts"] = charts
        # Keep diagrams_dropped from generate if present (soft-fail telemetry).
        fj_path.write_text(json.dumps(fj, ensure_ascii=False, indent=2), encoding="utf-8")

        meta["figures_planned"] = [f["id"] for f in figures]
        meta["charts_planned"] = [c["id"] for c in charts]
        meta["diagrams_planned"] = [d["id"] for d in diagrams]
        meta["diagrams_ok"] = len(diagrams)
        dropped = fj.get("diagrams_dropped") if isinstance(fj.get("diagrams_dropped"), list) else []
        if dropped:
            meta["diagrams_dropped"] = dropped
        _write_meta(meta, out, logs)

        status: dict = {}
        figs_dir = work / "figures"

        if figures and not dry_run and images_budget > 0:
            bump("images")
            status.update(materialize_user_figures(figures, figs_dir))
            need_api = [
                f
                for f in figures
                if str(f.get("source") or "") != "upload"
            ]
            cfg = ImageApiConfig.from_env()
            cfg = replace(cfg, max_images=images_budget)
            if need_api and not cfg.base_url:
                log.warning("figures planned but IMAGE_API_BASE_URL empty — strip slots")
                for f in need_api:
                    fid = str(f.get("id") or "")
                    if fid:
                        status[fid] = {
                            "ok": False,
                            "error": "IMAGE_API_BASE_URL empty",
                            "kind": "figure",
                        }
                EVENTS.publish_step(
                    run_id,
                    parent="photos",
                    step_id="photos",
                    status="skipped",
                    reason="IMAGE_API_BASE_URL empty",
                    label="Фото",
                )
            elif need_api:

                def _img_progress(fid: str) -> None:
                    bump("images", fid)
                    if fid:
                        EVENTS.publish_step(
                            run_id,
                            parent="photos",
                            step_id=fid,
                            status="done",
                            label=fid,
                        )

                from case3.chart_style import palette_from_intent

                pack_for_photos = palette_from_intent(intent or "") or "atelier"
                meta["image_style_pack"] = pack_for_photos
                status.update(
                    generate_all_figures(
                        figures,
                        figs_dir,
                        cfg=cfg,
                        on_progress=_img_progress,
                        pack_id=pack_for_photos,
                    )
                )

        if charts and not dry_run and charts_budget > 0:
            bump("charts")

            def _chart_progress(cid: str) -> None:
                bump("charts", cid)
                if cid:
                    EVENTS.publish_step(
                        run_id,
                        parent="charts",
                        step_id=cid,
                        status="done",
                        label=cid,
                    )

            status.update(
                generate_all_charts(
                    charts,
                    figs_dir,
                    work_root=work / "chart_work",
                    max_charts=charts_budget,
                    on_progress=_chart_progress,
                )
            )
            # Re-attach after harden/render path may have rewritten HTML.
            from case3.slides_chart_data import attach_series_ir_to_charts

            attach_series_ir_to_charts(charts)
            fj["charts"] = charts
            fj_path.write_text(
                json.dumps(fj, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        meta["media_status"] = status
        (work / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        bump("inject")
        # Win desk: hangs here looked like «документ» forever with no pipeline.log lines.
        log.info("inject: write_injected start run_id=%s", run_id)
        write_injected(tex_path, figures, status, charts=charts)
        log.info("inject: write_injected done, copy → out/")

        shutil.copy2(tex_path, out / tex_path.name)
        for name in ("figures.json", "status.json", f"{stem}.raw_model.txt"):
            p = work / name
            if p.is_file():
                shutil.copy2(p, out / name)
        if figs_dir.is_dir() and any(figs_dir.glob("*.png")):
            dest = out / "figures"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(figs_dir, dest)

        bump("latex" if formats else "summary")
        log.info(
            "post-inject stage=%s formats=%s (docker next if pdf/docx)",
            "latex" if formats else "summary",
            sorted(formats),
        )
        injected_tex = tex_path.read_text(encoding="utf-8")
        # formats=∅ (output_mode=diagram): skip Docker TeX — Mermaid + summary only.
        skip_print = not formats

        def _do_summary() -> tuple[str, str]:
            def on_delta(piece: str) -> None:
                BUS.publish(run_id, piece)

            chart_ids = [
                str(c.get("id") or "")
                for c in (charts or [])
                if isinstance(c, dict) and c.get("id")
            ]
            fig_ids = [
                str(f.get("id") or "")
                for f in (figures or [])
                if isinstance(f, dict) and f.get("id")
            ]
            media_facts = {
                "charts_planned": len(chart_ids),
                "figures_planned": len(fig_ids),
                "diagrams_planned": len(diagrams or []),
                "charts_ok": sum(
                    1
                    for cid in chart_ids
                    if isinstance(status.get(cid), dict) and status[cid].get("ok")
                ),
                "figures_ok": sum(
                    1
                    for fid in fig_ids
                    if isinstance(status.get(fid), dict) and status[fid].get("ok")
                ),
            }

            text, status_sum = try_generate_chat_summary(
                injected_tex,
                intent=intent,
                media=media_facts,
                on_delta=on_delta,
            )
            BUS.finish(run_id, text, status_sum)
            return text, status_sum

        # Chat summary streams in parallel with PDF/DOCX (does not block print truth).
        if dry_run:
            meta["chat_summary"] = ""
            meta["summary_status"] = "skipped"
            BUS.start(run_id)
            BUS.finish(run_id, "", "skipped")
            artifacts = (
                {}
                if skip_print
                else render_tex(
                    tex_path,
                    out_dir=out,
                    formats=formats,
                    extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
                    log_dir=logs,
                    project_root=root,
                    on_format=lambda fmt: bump(
                        "docx" if fmt == "docx" else "latex"
                    ),
                )
            )
        elif skip_print:
            # Diagram + presentation: no second Vision call (slides/Mermaid are the product).
            # LLM summary was the long hang after charts/images («В очереди…» forever).
            artifacts = {}
            BUS.start(run_id)
            bump("summary")
            if mode == "diagram":
                summary_text = _diagram_chat_blurb(diagrams)
                summary_status = "ok"
            elif mode == "presentation":
                summary_text = _presentation_chat_blurb(
                    charts=charts, figures=figures
                )
                summary_status = "ok"
            else:
                meta["summary_status"] = "streaming"
                meta["chat_summary"] = ""
                _write_meta(meta, out, logs)
                summary_text, summary_status = _do_summary()
            BUS.finish(run_id, summary_text or "", summary_status)
            meta["chat_summary"] = summary_text or ""
            meta["summary_status"] = summary_status
            if summary_text:
                (out / "chat_summary.txt").write_text(
                    summary_text, encoding="utf-8"
                )
                (logs / "chat_summary.txt").write_text(
                    summary_text, encoding="utf-8"
                )
        else:
            meta["summary_status"] = "streaming"
            meta["chat_summary"] = ""
            _write_meta(meta, out, logs)
            BUS.start(run_id)

            def _do_render() -> dict:
                return render_tex(
                    tex_path,
                    out_dir=out,
                    formats=formats,
                    extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
                    log_dir=logs,
                    project_root=root,
                    on_format=lambda fmt: bump(
                        "docx" if fmt == "docx" else "latex"
                    ),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_r = pool.submit(_do_render)
                fut_s = pool.submit(_do_summary)
                artifacts = fut_r.result()
                # Print is done — don't leave UI stuck on «Собираю DOCX…»
                # while OpenRouter still streams the chat summary.
                bump("summary")
                summary_text, summary_status = fut_s.result()

            meta["chat_summary"] = summary_text or ""
            meta["summary_status"] = summary_status
            if summary_text:
                (out / "chat_summary.txt").write_text(
                    summary_text, encoding="utf-8"
                )
                (logs / "chat_summary.txt").write_text(
                    summary_text, encoding="utf-8"
                )

        raise_if_cancelled(out)
        meta["artifacts"] = {k: str(v) for k, v in artifacts.items()}
        meta["status"] = "ok"
        meta["stage"] = "ok"
        meta.pop("stage_detail", None)
        meta.pop("cancel_requested", None)
        EVENTS.scan_artifacts(run_id, out)
        # Presentation: slides job continues on the same bus — defer terminal.
        if mode != "presentation":
            chart_ids = [
                str(c.get("id") or "")
                for c in (charts or [])
                if isinstance(c, dict) and c.get("id")
            ]
            fig_ids = [
                str(f.get("id") or "")
                for f in (figures or [])
                if isinstance(f, dict) and f.get("id")
            ]
            charts_ok = sum(
                1
                for cid in chart_ids
                if isinstance(status.get(cid), dict) and status[cid].get("ok")
            )
            figures_ok = sum(
                1
                for fid in fig_ids
                if isinstance(status.get(fid), dict) and status[fid].get("ok")
            )
            EVENTS.publish_terminal(
                run_id,
                "ok",
                recap=EVENTS.success_recap(
                    run_id, charts=charts_ok, figures=figures_ok
                ),
            )
        else:
            EVENTS.publish_stage(run_id, "pipeline_ok", scope="pipeline")
    except RunCancelled:
        meta["status"] = "cancelled"
        meta["stage"] = "cancelled"
        meta["error"] = "Остановлено"
        meta.pop("stage_detail", None)
        log.info("pipeline cancelled run_id=%s", run_id)
        _write_meta(meta, out, logs)
        EVENTS.publish_terminal(run_id, "cancelled", error="Остановлено")
        return out
    except Exception as exc:
        _record_failed_stage(meta)
        meta["status"] = "error"
        meta["stage"] = "error"
        log_path = getattr(exc, "log_path", None) if isinstance(exc, RenderError) else None
        meta.update(
            _attach_error_diagnostics(
                meta,
                logs_dir=logs,
                error=str(exc),
                log_path=Path(log_path) if log_path else None,
            )
        )
        meta["traceback"] = traceback.format_exc()
        log.exception("pipeline failed")
        (logs / "error.txt").write_text(meta["traceback"], encoding="utf-8")
        _write_meta(meta, out, logs)
        from case3.stage_eta import error_hint

        EVENTS.publish_terminal(
            run_id,
            "error",
            error=str(meta.get("error") or exc),
            hint=error_hint(exc, stage=str(meta.get("stage") or "")),
        )
        raise PipelineError(
            str(meta.get("error") or exc),
            run_id=run_id,
            out_dir=out,
            logs_dir=logs,
            meta=meta,
        ) from exc
    finally:
        if meta.get("status") not in {"error", "cancelled"}:
            _write_meta(meta, out, logs)
        root_logger.removeHandler(handler)
        handler.close()

    log.info("done run_id=%s out=%s", run_id, out)
    return out
