"""Session history and folder persistence router."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from case3 import run_store
from case3.run_store import RUN_ID_OK

log = logging.getLogger("case3.api_history")
router = APIRouter(tags=["history"])

_HISTORY_FILE = "user_history.json"


def _history_path() -> Path:
    return run_store.ROOT / "runs" / _HISTORY_FILE


def _load_user_history() -> dict[str, Any]:
    hp = _history_path()
    if not hp.is_file():
        return {"pinned": [], "folders": [], "item_folders": {}}
    try:
        data = json.loads(hp.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"pinned": [], "folders": [], "item_folders": {}}


def _save_user_history(data: dict[str, Any]) -> None:
    hp = _history_path()
    hp.parent.mkdir(parents=True, exist_ok=True)
    temp_p = hp.with_suffix(".tmp")
    temp_p.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_p.replace(hp)


def _parse_timestamp(raw: str | None, fallback: float) -> int:
    if not raw:
        return int(fallback * 1000)
    # Check format: YYYYMMDDTHHMMSSZ
    try:
        dt = datetime.strptime(raw.strip(), "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass
    # Check ISO format
    try:
        dt = datetime.fromisoformat(raw.strip())
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        pass
    return int(fallback * 1000)


class HistorySyncItem(BaseModel):
    runId: str
    pinned: bool | None = None
    folderId: str | None = None


class HistoryFolderModel(BaseModel):
    id: str
    name: str
    createdAt: int | None = None


class HistorySyncBody(BaseModel):
    items: list[HistorySyncItem] = Field(default_factory=list)
    folders: list[HistoryFolderModel] | None = None


@router.get("/api/history")
def get_history() -> dict[str, Any]:
    """Scan disk for runs and merge with user pins and folders."""
    out_dir = run_store.ROOT / "runs" / "out"
    user_data = _load_user_history()
    pinned_set = set(user_data.get("pinned", []))
    item_folders = user_data.get("item_folders", {})
    folders = user_data.get("folders", [])

    items: list[dict[str, Any]] = []
    if out_dir.is_dir():
        for run_dir in out_dir.iterdir():
            if not run_dir.is_dir() or not RUN_ID_OK.match(run_dir.name):
                continue
            meta_path = run_dir / "meta.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(meta, dict):
                continue

            run_id = str(meta.get("run_id") or run_dir.name)
            title = ""
            prev = meta.get("preview")
            if isinstance(prev, dict) and prev.get("title"):
                title = str(prev.get("title")).strip()
            elif meta.get("title"):
                title = str(meta.get("title")).strip()
            elif meta.get("intent"):
                intent_line = str(meta.get("intent")).strip().split("\n")[0]
                title = intent_line[:60]
            if not title:
                title = run_id

            mtime = meta_path.stat().st_mtime
            saved_at = _parse_timestamp(meta.get("started_at"), fallback=mtime)

            is_pinned = run_id in pinned_set
            folder_id = item_folders.get(run_id)

            items.append(
                {
                    "id": run_id,
                    "runId": run_id,
                    "title": title,
                    "savedAt": saved_at,
                    "pinned": is_pinned,
                    "folderId": folder_id,
                    "status": meta.get("status", "ok"),
                }
            )

    # Pinned first, then latest savedAt
    items.sort(
        key=lambda x: (
            1 if x["pinned"] else 0,
            x["savedAt"],
        ),
        reverse=True,
    )

    return {
        "items": items,
        "folders": folders,
    }


@router.post("/api/history/sync")
def sync_history(body: HistorySyncBody) -> dict[str, Any]:
    """Persist user organization (pinned status, folders) across sessions."""
    current = _load_user_history()
    pinned_set = set(current.get("pinned", []))
    item_folders = dict(current.get("item_folders", {}))

    for it in body.items:
        if it.pinned is True:
            pinned_set.add(it.runId)
        elif it.pinned is False:
            pinned_set.discard(it.runId)

        if it.folderId is not None:
            if it.folderId:
                item_folders[it.runId] = it.folderId
            else:
                item_folders.pop(it.runId, None)

    if body.folders is not None:
        folders_list = [f.model_dump() for f in body.folders]
        valid_folder_ids = {f["id"] for f in folders_list}
        item_folders = {k: v for k, v in item_folders.items() if v in valid_folder_ids}
    else:
        folders_list = current.get("folders", [])

    new_data = {
        "pinned": sorted(pinned_set),
        "folders": folders_list,
        "item_folders": item_folders,
    }
    _save_user_history(new_data)

    return {"ok": True}
