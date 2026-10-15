"""Text file → LLM .tex → PDF/DOCX + logs."""

from __future__ import annotations

import json
import logging
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from case3.generate import generate_tex, resolve_text_file
from case3.render import render_tex

log = logging.getLogger("case3.pipeline")


def run_pipeline(
    source: Path,
    *,
    project_root: Path,
    formats: set[str] | None = None,
    dry_run: bool = False,
) -> Path:
    formats = formats or {"pdf", "docx"}
    root = project_root.resolve()
    text_path = resolve_text_file(source)
    stem = text_path.stem
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stem}_{stamp}"

    work = root / "work" / run_id
    out = root / "out" / run_id
    logs = root / "logs" / run_id
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
        "formats": sorted(formats),
        "dry_run": dry_run,
        "started_at": stamp,
    }

    try:
        tex_path = work / f"{stem}.tex"
        generate_tex(text_path, out_tex=tex_path, gold_dir=root / "gold", dry_run=dry_run)
        shutil.copy2(tex_path, out / tex_path.name)
        raw = work / f"{stem}.raw_model.txt"
        if raw.is_file():
            shutil.copy2(raw, out / raw.name)

        artifacts = render_tex(tex_path, out_dir=out, formats=formats)
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
