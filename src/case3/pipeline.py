"""Full pipeline: job dir → LLM .tex → PDF/DOCX + logs."""

from __future__ import annotations

import json
import logging
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from case3.generate import find_images, generate_tex
from case3.render import render_tex

log = logging.getLogger("case3.pipeline")


def run_job(
    job_dir: Path,
    *,
    project_root: Path,
    formats: set[str] | None = None,
    dry_run: bool = False,
) -> Path:
    formats = formats or {"pdf", "docx"}
    job_dir = job_dir.resolve()
    root = project_root.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{job_dir.name}_{stamp}"

    work = root / "work" / run_id
    out = root / "out" / run_id
    logs = root / "logs" / run_id
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(logs / "pipeline.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root_logger = logging.getLogger("case3")
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    meta: dict = {
        "run_id": run_id,
        "job_dir": str(job_dir),
        "formats": sorted(formats),
        "dry_run": dry_run,
        "started_at": stamp,
    }

    try:
        tex_path = work / f"{job_dir.name}.tex"
        generate_tex(
            job_dir,
            out_tex=tex_path,
            gold_dir=root / "gold",
            dry_run=dry_run,
        )
        # stage images next to tex for latexmk
        images = find_images(job_dir)
        img_dst = work / "images"
        if images:
            img_dst.mkdir(exist_ok=True)
            for p in images:
                shutil.copy2(p, img_dst / p.name)

        shutil.copy2(tex_path, out / tex_path.name)
        if img_dst.is_dir():
            if (out / "images").exists():
                shutil.rmtree(out / "images")
            shutil.copytree(img_dst, out / "images")

        artifacts = render_tex(
            tex_path,
            out_dir=out,
            formats=formats,
            asset_dirs=[img_dst] if img_dst.is_dir() else [],
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
        (logs / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        root_logger.removeHandler(handler)
        handler.close()

    log.info("done run_id=%s out=%s", run_id, out)
    return out
