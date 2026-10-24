"""Cooperative cancel for report pipeline + slides jobs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunCancelled(Exception):
    """User requested stop — exit between stages without treating as hard error."""


def read_meta(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "meta.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def is_cancel_requested(out_dir: Path) -> bool:
    return bool(read_meta(out_dir).get("cancel_requested"))


def raise_if_cancelled(out_dir: Path) -> None:
    if is_cancel_requested(out_dir):
        raise RunCancelled("cancelled by user")


def mark_cancel_requested(out_dir: Path, logs_dir: Path | None = None) -> dict[str, Any]:
    meta = read_meta(out_dir)
    meta["cancel_requested"] = True
    payload = json.dumps(meta, ensure_ascii=False, indent=2)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(payload, encoding="utf-8")
    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "meta.json").write_text(payload, encoding="utf-8")
    return meta
