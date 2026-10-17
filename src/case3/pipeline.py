"""intent+source → LLM tex → Kandinsky + HTML charts → inject → PDF/DOCX."""

from __future__ import annotations

import json
import logging
import shutil
import traceback
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from case3.charts import generate_all_charts, max_charts_from_env
from case3.generate import generate_document, max_images_from_env, resolve_text_file
from case3.inject import write_injected
from case3.kandinsky import KandinskyConfig, generate_all_figures
from case3.render import render_tex

log = logging.getLogger("case3.pipeline")


def run_pipeline(
    source: Path,
    *,
    project_root: Path,
    formats: set[str] | None = None,
    dry_run: bool = False,
    intent: str | None = None,
    max_images: int | None = None,
    max_charts: int | None = None,
) -> Path:
    formats = formats or {"pdf"}
    root = project_root.resolve()
    text_path = resolve_text_file(source)
    stem = text_path.stem
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stem}_{stamp}"

    images_budget = max_images_from_env() if max_images is None else max(0, int(max_images))
    charts_budget = max_charts_from_env() if max_charts is None else max(0, int(max_charts))

    work = root / "runs" / "work" / run_id
    out = root / "runs" / "out" / run_id
    logs = root / "runs" / "logs" / run_id
    for d in (work, out, logs):
        d.mkdir(parents=True, exist_ok=True)

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
    }

    try:
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

        status: dict = {}
        figs_dir = work / "figures"

        if figures and not dry_run and images_budget > 0:
            cfg = KandinskyConfig.from_env()
            cfg = replace(cfg, max_images=images_budget)
            if not cfg.base_url:
                log.warning("figures planned but KANDINSKY_API_BASE_URL empty — strip slots")
            else:
                status.update(generate_all_figures(figures, figs_dir, cfg=cfg))

        if charts and not dry_run and charts_budget > 0:
            status.update(
                generate_all_charts(
                    charts,
                    figs_dir,
                    work_root=work / "chart_work",
                    max_charts=charts_budget,
                )
            )

        meta["media_status"] = status
        (work / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )

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

        artifacts = render_tex(
            tex_path,
            out_dir=out,
            formats=formats,
            extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
            log_dir=logs,
        )
        meta["artifacts"] = {k: str(v) for k, v in artifacts.items()}
        meta["status"] = "ok"
    except Exception as exc:
        meta["status"] = "error"
        meta["error"] = str(exc)
        meta["traceback"] = traceback.format_exc()
        log.exception("pipeline failed")
        (logs / "error.txt").write_text(meta["traceback"], encoding="utf-8")
        raise
    finally:
        payload = json.dumps(meta, ensure_ascii=False, indent=2)
        (logs / "meta.json").write_text(payload, encoding="utf-8")
        (out / "meta.json").write_text(payload, encoding="utf-8")
        root_logger.removeHandler(handler)
        handler.close()

    log.info("done run_id=%s out=%s", run_id, out)
    return out
