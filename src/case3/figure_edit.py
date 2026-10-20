"""Regenerate or img2img-edit one figure PNG in an existing run, then rebuild docs."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Literal

from case3.image_api import ImageApiConfig, edit_png, generate_png
from case3.render import RenderError, render_tex

log = logging.getLogger("case3.figure_edit")

EditMode = Literal["generate", "edit"]


class FigureEditError(RuntimeError):
    pass


def edit_figure_in_run(
    out_dir: Path,
    figure_id: str,
    *,
    mode: EditMode,
    prompt: str,
    formats: set[str] | None = None,
    cfg: ImageApiConfig | None = None,
) -> dict[str, Any]:
    out_dir = out_dir.resolve()
    cfg = cfg or ImageApiConfig.from_env()
    if not cfg.base_url:
        raise FigureEditError("IMAGE_API_BASE_URL пуст — укажи URL офисного Image API")
    prompt = (prompt or "").strip()
    if not prompt:
        raise FigureEditError("нужен текст промпта")
    if mode not in ("generate", "edit"):
        raise FigureEditError("mode must be generate|edit")
    if figure_id.startswith("cht_"):
        raise FigureEditError("это график — используйте правку charts, не figures")

    figs_dir = out_dir / "figures"
    dest = figs_dir / f"{figure_id}.png"
    figs_dir.mkdir(parents=True, exist_ok=True)

    # Update figures.json prompt when present
    fj_path = out_dir / "figures.json"
    fj: dict[str, Any] = {}
    fj_bak: str | None = None
    if fj_path.is_file():
        try:
            fj_bak = fj_path.read_text(encoding="utf-8")
            fj = json.loads(fj_bak)
        except (OSError, json.JSONDecodeError):
            fj = {}
    figures = list(fj.get("figures") or [])
    idx = next(
        (i for i, f in enumerate(figures) if isinstance(f, dict) and f.get("id") == figure_id),
        -1,
    )

    bak: bytes | None = dest.read_bytes() if dest.is_file() else None
    meta_path = out_dir / "meta.json"
    meta_bak: str | None = meta_path.read_text(encoding="utf-8") if meta_path.is_file() else None

    try:
        if mode == "generate":
            generate_png(cfg, prompt, dest)
        else:
            if bak is None:
                raise FigureEditError(
                    f"нет исходного PNG для правки ({figure_id}.png) — сначала сгенерируйте"
                )
            tmp = dest.with_suffix(".edit.png")
            edit_png(cfg, prompt, dest, tmp)
            tmp.replace(dest)
    except FigureEditError:
        raise
    except Exception as exc:  # noqa: BLE001
        if bak is not None:
            dest.write_bytes(bak)
        raise FigureEditError(f"image API failed: {exc}") from exc

    if idx >= 0:
        fig = dict(figures[idx])
        fig["prompt"] = prompt
        figures[idx] = fig
        fj["figures"] = figures
        fj_path.write_text(json.dumps(fj, ensure_ascii=False, indent=2), encoding="utf-8")

    meta: dict[str, Any] = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    media = dict(meta.get("media_status") or {})
    media[figure_id] = {"ok": True, "path": str(dest), "kind": "figure"}
    meta["media_status"] = media
    meta["last_figure_edit"] = {
        "id": figure_id,
        "mode": mode,
        "prompt": prompt[:500],
        "ts": int(time.time()),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    fmt = formats or {"pdf", "docx"}
    texs = sorted(out_dir.glob("*.tex"))
    if not texs:
        raise FigureEditError("no .tex in run")
    try:
        artifacts = render_tex(
            texs[0],
            out_dir=out_dir,
            formats=fmt,
            extra_dirs=[figs_dir],
            log_dir=out_dir / "logs",
            force=True,
            project_root=out_dir.resolve().parents[2],
        )
    except RenderError as exc:
        if bak is not None:
            dest.write_bytes(bak)
        if fj_bak is not None:
            fj_path.write_text(fj_bak, encoding="utf-8")
        if meta_bak is not None:
            meta_path.write_text(meta_bak, encoding="utf-8")
        raise FigureEditError(f"document rebuild failed: {exc}") from exc

    v = int(dest.stat().st_mtime)
    return {
        "figure_id": figure_id,
        "mode": mode,
        "prompt": prompt,
        "media_status": media,
        "artifacts": {k: str(p) for k, p in artifacts.items()},
        "version": v,
    }
