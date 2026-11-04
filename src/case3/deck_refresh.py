"""Soft-rebuild PPTX twin after Liber media/text edits (no LLM)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("case3.deck_refresh")


def refresh_deck_from_ir(out_dir: Path) -> bool:
    """Rebuild slides from frozen ``slides/deck.json`` when present. Soft-fail."""
    out_dir = Path(out_dir).resolve()
    deck_path = out_dir / "slides" / "deck.json"
    if not deck_path.is_file():
        return False
    try:
        deck: Any = json.loads(deck_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("deck refresh: cannot read deck.json: %s", exc)
        return False
    if not isinstance(deck, dict):
        return False
    try:
        from case3.paths import repo_root
        from case3.slides_job import rebuild_slides_from_deck

        rebuild_slides_from_deck(out_dir.name, deck, root=repo_root())
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("deck refresh skipped: %s", exc)
        return False
