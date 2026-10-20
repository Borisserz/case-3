"""intent+source → LLM tex → Kandinsky + HTML charts → inject → PDF/DOCX."""

from __future__ import annotations

import json
import logging
import shutil
import traceback
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from case3.charts import generate_all_charts, max_charts_from_env
from case3.generate import generate_document, max_images_from_env, resolve_text_file
from case3.inject import write_injected
from case3.image_api import ImageApiConfig, generate_all_figures
from case3.render import render_tex

log = logging.getLogger("case3.pipeline")


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


def _write_meta(meta: dict[str, Any], out: Path, logs: Path) -> None:
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    (logs / "meta.json").write_text(payload, encoding="utf-8")
    (out / "meta.json").write_text(payload, encoding="utf-8")


def _set_stage(
    meta: dict[str, Any],
    out: Path,
    logs: Path,
    stage: str,
    *,
    detail: str | None = None,
    status: str = "running",
) -> None:
    meta["status"] = status
    meta["stage"] = stage
    if detail:
        meta["stage_detail"] = detail
    else:
        meta.pop("stage_detail", None)
    _write_meta(meta, out, logs)


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


def run_pipeline(
    source: Path,
    *,
    project_root: Path,
    formats: set[str] | None = None,
    dry_run: bool = False,
    intent: str | None = None,
    max_images: int | None = None,
    max_charts: int | None = None,
    run_id: str | None = None,
    on_stage: Callable[[str, str | None], None] | None = None,
) -> Path:
    formats = formats or {"pdf"}
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

    handler = logging.FileHandler(logs / "pipeline.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger = logging.getLogger("case3")
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    meta: dict = {
        "run_id": run_id,
        "source": str(text_path),
        "intent": intent,
        "formats": sorted(formats),
        "dry_run": dry_run,
        "max_images": images_budget,
        "max_charts": charts_budget,
        "started_at": stamp,
        "status": "running",
        "stage": "queued",
    }
    _write_meta(meta, out, logs)

    def bump(stage: str, detail: str | None = None) -> None:
        _set_stage(meta, out, logs, stage, detail=detail)
        if on_stage:
            on_stage(stage, detail)

    try:
        bump("llm")
        tex_path = work / f"{stem}.tex"
        _, figures, charts = generate_document(
            text_path,
            out_tex=tex_path,
            intent=intent,
            gold_dir=root / "prompt" / "gold",
            dry_run=dry_run,
            max_images=images_budget,
            max_charts=charts_budget,
        )
        meta["figures_planned"] = [f["id"] for f in figures]
        meta["charts_planned"] = [c["id"] for c in charts]
        _write_meta(meta, out, logs)

        status: dict = {}
        figs_dir = work / "figures"

        if figures and not dry_run and images_budget > 0:
            bump("images")
            cfg = ImageApiConfig.from_env()
            cfg = replace(cfg, max_images=images_budget)
            if not cfg.base_url:
                log.warning("figures planned but IMAGE_API_BASE_URL empty — strip slots")
            else:

                def _img_progress(fid: str) -> None:
                    bump("images", fid)

                status.update(
                    generate_all_figures(
                        figures,
                        figs_dir,
                        cfg=cfg,
                        on_progress=_img_progress,
                    )
                )

        if charts and not dry_run and charts_budget > 0:
            bump("charts")

            def _chart_progress(cid: str) -> None:
                bump("charts", cid)

            status.update(
                generate_all_charts(
                    charts,
                    figs_dir,
                    work_root=work / "chart_work",
                    max_charts=charts_budget,
                    on_progress=_chart_progress,
                )
            )

        meta["media_status"] = status
        (work / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        bump("inject")
        write_injected(tex_path, figures, status, charts=charts)

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

        bump("latex")
        artifacts = render_tex(
            tex_path,
            out_dir=out,
            formats=formats,
            extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
            log_dir=logs,
            project_root=root,
            on_format=lambda fmt: bump("docx" if fmt == "docx" else "latex"),
        )
        meta["artifacts"] = {k: str(v) for k, v in artifacts.items()}
        meta["status"] = "ok"
        meta["stage"] = "ok"
        meta.pop("stage_detail", None)
    except Exception as exc:
        meta["status"] = "error"
        meta["stage"] = "error"
        meta["error"] = str(exc)
        meta["traceback"] = traceback.format_exc()
        log.exception("pipeline failed")
        (logs / "error.txt").write_text(meta["traceback"], encoding="utf-8")
        _write_meta(meta, out, logs)
        raise PipelineError(
            str(exc),
            run_id=run_id,
            out_dir=out,
            logs_dir=logs,
            meta=meta,
        ) from exc
    finally:
        if meta.get("status") != "error":
            _write_meta(meta, out, logs)
        root_logger.removeHandler(handler)
        handler.close()

    log.info("done run_id=%s out=%s", run_id, out)
    return out
