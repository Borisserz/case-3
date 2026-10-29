"""Run filesystem + preview helpers shared by api / edits / slides routers.

Canonical ``ROOT`` for Liber runs. Tests monkeypatch ``case3.run_store.ROOT``
only — ``case3.api.ROOT`` is a ``__getattr__`` mirror of this value.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from case3.paths import repo_root
from case3.slides_media import load_figures_json
from case3.tex_preview import build_report_preview

ROOT = repo_root()

RUN_ID_OK = re.compile(r"^[A-Za-z0-9_.-]+$")
FILE_OK = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_formats_form(raw: str | None) -> set[str]:
    """Parse formats form: pdf|docx|both|none. ``none`` → no print artifacts."""
    fmt_raw = (raw or "both").strip().lower()
    if fmt_raw == "both":
        return {"pdf", "docx"}
    if fmt_raw in {"pdf", "docx"}:
        return {fmt_raw}
    if fmt_raw in {"none", "diagram", "schemas"}:
        return set()
    raise ValueError("formats must be pdf|docx|both|none")


def formats_from_edit_body(raw: str | None) -> set[str]:
    try:
        return parse_formats_form(raw)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


def artifact_downloads(run_id: str, out_dir: Path, version: int) -> dict[str, str]:
    files: dict[str, str] = {}
    for art in sorted(out_dir.iterdir()):
        if art.is_file() and art.suffix.lower() in {".pdf", ".docx"}:
            key = art.suffix.lower().lstrip(".")
            files[key] = f"/api/runs/{run_id}/files/{art.name}?v={version}"
    return files


def bust_preview_figure_urls(
    preview: dict[str, Any],
    version: int,
    *needles: str,
) -> None:
    for block in preview.get("blocks") or []:
        if isinstance(block, dict) and block.get("type") == "figure" and block.get("url"):
            url = str(block["url"])
            if any(n and n in url for n in needles):
                sep = "&" if "?" in url else "?"
                block["url"] = f"{url}{sep}v={version}"


def load_diagrams_from_out(out_dir: Path) -> list[dict[str, Any]]:
    """UI-only Mermaid payloads from figures.json (no TeX inject)."""
    fj = out_dir / "figures.json"
    if not fj.is_file():
        return []
    try:
        data = json.loads(fj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("diagrams") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        did = str(item.get("id") or "").strip()
        mermaid = str(item.get("mermaid") or "").strip()
        if not did or not mermaid:
            continue
        out.append(
            {
                "id": did,
                "title": str(item.get("title") or did).strip()[:80],
                "type": str(item.get("type") or "").strip(),
                "mermaid": mermaid,
            }
        )
    return out


def find_out_tex(out_dir: Path) -> Path | None:
    texs = sorted(out_dir.glob("*.tex"))
    return texs[0] if texs else None


def build_preview_payload(
    run_id: str, out_dir: Path, media: dict[str, Any]
) -> dict[str, Any]:
    tex_path = find_out_tex(out_dir)
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
        figures_json=load_figures_json(out_dir),
    )


def resolve_run_dir(run_id: str) -> Path:
    if not RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    out_dir = (ROOT / "runs" / "out" / run_id).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(out_dir).startswith(str(out_root)) or not out_dir.is_dir():
        raise HTTPException(404, detail="run not found")
    return out_dir


def safe_run_file(run_id: str, *parts: str) -> Path:
    if not RUN_ID_OK.match(run_id):
        raise HTTPException(400, detail="invalid run_id")
    for part in parts:
        if not FILE_OK.match(part) or ".." in part or "/" in part or "\\" in part:
            raise HTTPException(400, detail="invalid path")
    path = (ROOT / "runs" / "out" / run_id).joinpath(*parts).resolve()
    out_root = (ROOT / "runs" / "out").resolve()
    if not str(path).startswith(str(out_root)) or not path.is_file():
        raise HTTPException(404, detail="file not found")
    return path


def edit_response_envelope(
    *,
    run_id: str,
    out_dir: Path,
    result: dict[str, Any],
    bust_needles: tuple[str, ...] = (),
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shared post-edit JSON: preview + downloads + undo (+ caller extras)."""
    media = result.get("media_status") or {}
    if not isinstance(media, dict):
        media = {}
    preview = build_preview_payload(run_id, out_dir, media)
    v = int(result.get("version") or 0)
    if bust_needles:
        bust_preview_figure_urls(preview, v, *bust_needles)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": "ok",
        "media_status": media,
        "downloads": artifact_downloads(run_id, out_dir, v),
        "preview": preview,
        "undo": result.get("undo"),
        "warnings": [],
    }
    if extra:
        payload.update(extra)
    return payload
