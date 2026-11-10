"""One on-disk waiter for the desk pipeline (ADR-0010).

The executing run still lives in a process lock. The single queued job is
this JSON file, so an API restart can start it again.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from case3.run_store import RUN_ID_OK

QUEUE_FILE = "pipeline_queue.json"
_LOCK = threading.Lock()
_REQUIRED = (
    "src_path",
    "run_id",
    "formats",
    "dry_run",
    "intent",
    "max_images",
    "max_charts",
    "max_diagrams",
    "user_figures",
    "output_mode",
)


def queue_path(root: Path) -> Path:
    return Path(root) / "runs" / QUEUE_FILE


def save_waiter(root: Path, payload: dict[str, Any]) -> None:
    """Atomically replace the waiter file. Caller guarantees a single waiter."""
    path = queue_path(root)
    body = {key: payload.get(key) for key in _REQUIRED}
    text = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with _LOCK:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)


def load_waiter(root: Path) -> dict[str, Any] | None:
    """Return the waiter when its source file sits inside ``root``.

    A poisoned file (bad JSON, escaped path, unknown run id) is removed.
    A missing source file is also removed; the run meta stays for the desk.
    """
    path = queue_path(root)
    with _LOCK:
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None
        job = _accept(root, raw)
        if job is None:
            path.unlink(missing_ok=True)
            return None
        return job


def clear_waiter(root: Path, *, run_id: str | None = None) -> bool:
    """Drop the file. With ``run_id``, leave a different waiter in place."""
    path = queue_path(root)
    with _LOCK:
        if not path.is_file():
            return False
        if run_id is not None:
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
            if not isinstance(current, dict) or str(current.get("run_id") or "") != run_id:
                return False
        path.unlink(missing_ok=True)
        return True


def _accept(root: Path, raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    run_id = str(raw.get("run_id") or "")
    if not RUN_ID_OK.match(run_id):
        return None
    src_raw = raw.get("src_path")
    if not isinstance(src_raw, str) or not src_raw.strip():
        return None
    root_r = Path(root).resolve()
    src = Path(src_raw).expanduser().resolve()
    try:
        src.relative_to(root_r)
    except ValueError:
        return None
    if not src.is_file():
        return None
    formats = raw.get("formats")
    if not isinstance(formats, list) or not all(isinstance(x, str) for x in formats):
        return None
    figures = raw.get("user_figures")
    if figures is None:
        figures = []
    if not isinstance(figures, list) or not all(isinstance(x, dict) for x in figures):
        return None
    mode = str(raw.get("output_mode") or "auto")
    if mode not in {"report", "diagram", "presentation", "auto"}:
        return None
    try:
        max_images = int(raw.get("max_images") or 0)
        max_charts = int(raw.get("max_charts") or 0)
        max_diagrams = int(raw.get("max_diagrams") or 0)
    except (TypeError, ValueError):
        return None
    return {
        "src_path": str(src),
        "run_id": run_id,
        "formats": list(formats),
        "dry_run": bool(raw.get("dry_run")),
        "intent": str(raw.get("intent") or ""),
        "max_images": max_images,
        "max_charts": max_charts,
        "max_diagrams": max_diagrams,
        "user_figures": figures,
        "output_mode": mode,
    }
