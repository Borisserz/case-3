"""Regenerate or img2img-edit one figure PNG in an existing run, then rebuild docs."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Literal

from case3.image_api import ImageApiConfig, edit_png, generate_png
from case3.image_prompt import ImagePromptError, ensure_english_image_prompt
from case3.render import RenderError
from case3.run_rebuild import rebuild_run_docs
from case3.tex_safe import escape_tex_text

log = logging.getLogger("case3.figure_edit")

EditMode = Literal["generate", "edit"]


class FigureEditError(RuntimeError):
    pass


def patch_figure_caption_in_tex(tex: str, figure_id: str, caption: str) -> str:
    """Replace \\caption{…} for a figure identified by \\label{fig:ID}."""
    caption = (caption or "").strip()
    if not caption or not figure_id:
        return tex
    esc = escape_tex_text(caption)
    fid = re.escape(figure_id)
    # caption immediately before \label{fig:id}
    pat = re.compile(
        rf"(\\caption\{{)([^{{}}]*)(\}}\s*\\label\{{fig:{fid}\}})"
    )
    if pat.search(tex):
        return pat.sub(rf"\g<1>{esc}\g<3>", tex, count=1)
    # caption after includegraphics{…/id.png}
    pat2 = re.compile(
        rf"(\\includegraphics(?:\[[^\]]*\])?\{{(?:figures/)?{fid}\.png\}}\s*"
        rf"\\caption\{{)([^{{}}]*)(\}})",
        re.S,
    )
    if pat2.search(tex):
        return pat2.sub(rf"\g<1>{esc}\g<3>", tex, count=1)
    return tex


def edit_figure_in_run(
    out_dir: Path,
    figure_id: str,
    *,
    mode: EditMode,
    prompt: str,
    caption: str | None = None,
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
    try:
        prompt = ensure_english_image_prompt(prompt)
    except ImagePromptError as exc:
        raise FigureEditError(str(exc)) from exc

    caption_new = (caption or "").strip()

    from case3.run_undo import capture_before_edit

    capture_before_edit(out_dir, kind="figure", target=figure_id)

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
    texs = sorted(out_dir.glob("*.tex"))
    tex_bak: str | None = None
    if texs and texs[0].is_file():
        tex_bak = texs[0].read_text(encoding="utf-8")

    pack_id: str | None = None
    if meta_path.is_file():
        try:
            m0 = json.loads(meta_path.read_text(encoding="utf-8"))
            pack_id = (
                str(m0.get("image_style_pack") or m0.get("slides_theme_pack") or "")
                or str(m0.get("chart_palette") or "")
                or None
            )
        except (OSError, json.JSONDecodeError):
            pack_id = None

    try:
        if mode == "generate":
            generate_png(cfg, prompt, dest, pack_id=pack_id)
        else:
            if bak is None:
                raise FigureEditError(
                    f"нет исходного PNG для правки ({figure_id}.png) — сначала сгенерируйте"
                )
            tmp = dest.with_suffix(".edit.png")
            edit_png(cfg, prompt, dest, tmp, pack_id=pack_id)
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
        if caption_new:
            fig["caption"] = caption_new
        figures[idx] = fig
        fj["figures"] = figures
        fj_path.write_text(json.dumps(fj, ensure_ascii=False, indent=2), encoding="utf-8")
    elif caption_new or prompt:
        # figure missing from json — still ok for PNG-only runs
        pass

    if caption_new and texs:
        patched = patch_figure_caption_in_tex(
            texs[0].read_text(encoding="utf-8"), figure_id, caption_new
        )
        texs[0].write_text(patched, encoding="utf-8")

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
        "caption": (caption_new or "")[:300] or None,
        "ts": int(time.time()),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        artifacts = rebuild_run_docs(out_dir, formats=formats)
    except FileNotFoundError as exc:
        raise FigureEditError(str(exc)) from exc
    except RenderError as exc:
        if bak is not None:
            dest.write_bytes(bak)
        if fj_bak is not None:
            fj_path.write_text(fj_bak, encoding="utf-8")
        if meta_bak is not None:
            meta_path.write_text(meta_bak, encoding="utf-8")
        if tex_bak is not None:
            texs[0].write_text(tex_bak, encoding="utf-8")
        from case3.run_undo import clear_undo

        clear_undo(out_dir)
        raise FigureEditError(f"document rebuild failed: {exc}") from exc

    v = int(dest.stat().st_mtime)
    from case3.run_undo import undo_meta

    return {
        "figure_id": figure_id,
        "mode": mode,
        "prompt": prompt,
        "caption": caption_new or None,
        "media_status": media,
        "artifacts": {k: str(p) for k, p in artifacts.items()},
        "version": v,
        "undo": undo_meta(out_dir),
    }
