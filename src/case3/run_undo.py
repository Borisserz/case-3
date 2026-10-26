"""One-slot undo for Liber in-run edits (B21).

Stores a snapshot under ``out/.undo/`` before a successful edit path mutates
files; ``apply_undo`` restores and optionally rebuilds PDF/DOCX.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("case3.run_undo")

_UNDO_DIR = ".undo"
_MANIFEST = "manifest.json"


class UndoError(RuntimeError):
    pass


def _undo_root(out_dir: Path) -> Path:
    return Path(out_dir).resolve() / _UNDO_DIR


def _manifest_path(out_dir: Path) -> Path:
    return _undo_root(out_dir) / _MANIFEST


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def undo_meta(out_dir: Path) -> dict[str, Any] | None:
    """Public undo descriptor if a restore slot exists."""
    out = Path(out_dir).resolve()
    if not _manifest_path(out).is_file():
        return None
    meta = _read_json(out / "meta.json")
    slot = meta.get("undo")
    if isinstance(slot, dict) and slot.get("kind"):
        return {
            "kind": slot.get("kind"),
            "target": slot.get("target"),
            "ts": slot.get("ts"),
        }
    man = _read_json(_manifest_path(out))
    if not man.get("kind"):
        return None
    return {
        "kind": man.get("kind"),
        "target": man.get("target"),
        "ts": man.get("ts"),
    }


def clear_undo(out_dir: Path) -> bool:
    """Remove undo slot + meta.undo. Returns True if something was cleared."""
    out = Path(out_dir).resolve()
    root = _undo_root(out)
    had = root.is_dir()
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
    meta_path = out / "meta.json"
    if meta_path.is_file():
        meta = _read_json(meta_path)
        if "undo" in meta:
            meta.pop("undo", None)
            _write_json(meta_path, meta)
            had = True
    return bool(had)


def _rel_files_to_snapshot(out: Path) -> list[str]:
    rels: list[str] = []
    for name in ("figures.json", "meta.json", "diagrams.json"):
        if (out / name).is_file():
            rels.append(name)
    for tex in sorted(out.glob("*.tex")):
        if tex.is_file():
            rels.append(tex.name)
    figs = out / "figures"
    if figs.is_dir():
        for png in sorted(figs.glob("*.png")):
            if png.is_file() and png.stat().st_size > 0:
                rels.append(f"figures/{png.name}")
    slides = out / "slides"
    if slides.is_dir():
        for name in ("deck.json", "deck_ir.json"):
            p = slides / name
            if p.is_file():
                rels.append(f"slides/{name}")
    return rels


def capture_before_edit(
    out_dir: Path,
    *,
    kind: str,
    target: str,
) -> dict[str, Any]:
    """Overwrite the single undo slot with current out/ state."""
    out = Path(out_dir).resolve()
    if not out.is_dir():
        raise UndoError("run out_dir missing")

    # Snapshot meta *without* an undo flag (pre-edit truth).
    meta_live = _read_json(out / "meta.json") if (out / "meta.json").is_file() else {}
    meta_snap = dict(meta_live)
    meta_snap.pop("undo", None)

    root = _undo_root(out)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    files_dir = root / "files"
    files_dir.mkdir(parents=True)

    saved: list[str] = []
    for rel in _rel_files_to_snapshot(out):
        if rel == "meta.json":
            continue
        src = out / rel
        if not src.is_file():
            continue
        dest = files_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        saved.append(rel)

    if meta_snap or (out / "meta.json").is_file():
        _write_json(files_dir / "meta.json", meta_snap)
        saved.append("meta.json")

    manifest = {
        "kind": (kind or "edit").strip() or "edit",
        "target": str(target or ""),
        "ts": int(time.time()),
        "files": saved,
    }
    _write_json(_manifest_path(out), manifest)

    meta_live["undo"] = {
        "kind": manifest["kind"],
        "target": manifest["target"],
        "ts": manifest["ts"],
        "ready": True,
    }
    _write_json(out / "meta.json", meta_live)

    log.info("undo captured kind=%s target=%s files=%d", kind, target, len(saved))
    return {"kind": manifest["kind"], "target": manifest["target"], "ts": manifest["ts"]}


def apply_undo(out_dir: Path, *, rebuild: bool = True) -> dict[str, Any]:
    """Restore snapshot; clear slot; optionally rebuild PDF/DOCX."""
    out = Path(out_dir).resolve()
    man_path = _manifest_path(out)
    if not man_path.is_file():
        raise UndoError("нечего отменять")
    manifest = _read_json(man_path)
    files_dir = _undo_root(out) / "files"
    rels = manifest.get("files")
    if not isinstance(rels, list) or not rels:
        raise UndoError("пустой undo snapshot")

    for rel in rels:
        if not isinstance(rel, str) or ".." in rel or rel.startswith(("/", "\\")):
            continue
        src = files_dir / rel
        if not src.is_file():
            continue
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    info: dict[str, Any] = {
        "kind": manifest.get("kind"),
        "target": manifest.get("target"),
        "ts": manifest.get("ts"),
    }
    shutil.rmtree(_undo_root(out), ignore_errors=True)
    if (out / "meta.json").is_file():
        meta = _read_json(out / "meta.json")
        meta.pop("undo", None)
        _write_json(out / "meta.json", meta)

    artifacts: dict[str, Any] = {}
    if rebuild:
        from case3.render import RenderError, render_tex

        texs = sorted(out.glob("*.tex"))
        if texs:
            figs_dir = out / "figures"
            try:
                artifacts = render_tex(
                    texs[0],
                    out_dir=out,
                    formats={"pdf", "docx"},
                    extra_dirs=[figs_dir] if figs_dir.is_dir() else None,
                    log_dir=out / "logs",
                    force=True,
                    project_root=out.resolve().parents[2],
                )
            except RenderError as exc:
                log.warning("undo restore ok but rebuild failed: %s", exc)
                info["rebuild_error"] = str(exc)
    info["artifacts"] = {k: str(v) for k, v in artifacts.items()} if artifacts else {}
    log.info("undo applied kind=%s target=%s", info.get("kind"), info.get("target"))
    return info
