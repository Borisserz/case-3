"""Apply text-only patches to deck IR (edit existing fields; no structural mutate)."""

from __future__ import annotations

import copy
from typing import Any

from case3.slides_ir import DeckIrError, _norm_ws

_TEXT_KEYS = (
    "title",
    "subtitle",
    "kicker",
    "takeaway",
    "body",
    "caption",
    "term",
    "definition",
)
_KPI_KEYS = ("label", "value", "hint", "delta")


def apply_deck_text_patch(
    deck: dict[str, Any],
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Merge text fields from ``patch`` into a copy of ``deck``.

    Allowed: string fields, bullets[i] (same length), kpis[i] text keys
    (same length), rows[r][c] (same shape). Forbidden: layout, media/chart
    ids, slide add/remove, chapter, style.
    """
    if not isinstance(deck, dict) or not isinstance(patch, dict):
        raise DeckIrError("deck/patch must be objects")
    out = copy.deepcopy(deck)
    slides = out.get("slides")
    if not isinstance(slides, list):
        raise DeckIrError("deck.slides required")
    by_id = {
        str(s.get("id")): s
        for s in slides
        if isinstance(s, dict) and s.get("id")
    }
    patch_slides = patch.get("slides")
    if not isinstance(patch_slides, list):
        raise DeckIrError("patch.slides must be a list")

    for ps in patch_slides:
        if not isinstance(ps, dict):
            raise DeckIrError("patch slide must be object")
        sid = str(ps.get("id") or "")
        if not sid or sid not in by_id:
            raise DeckIrError(f"unknown slide id in patch: {sid!r}")
        target = by_id[sid]
        if "layout" in ps and str(ps.get("layout")) != str(target.get("layout")):
            raise DeckIrError("cannot change layout")
        for forbidden in (
            "chart_id",
            "media_id",
            "chapter",
            "appendix",
            "id",
        ):
            if forbidden == "id":
                continue
            if forbidden in ps and ps.get(forbidden) != target.get(forbidden):
                raise DeckIrError(f"cannot change {forbidden}")

        for key in _TEXT_KEYS:
            if key not in ps:
                continue
            val = ps.get(key)
            if val is None:
                continue
            if not isinstance(val, str):
                raise DeckIrError(f"{key} must be string")
            target[key] = _norm_ws(val)

        if "bullets" in ps:
            _patch_bullets(target, ps["bullets"])
        if "kpis" in ps:
            _patch_kpis(target, ps["kpis"])
        if "cards" in ps:
            _patch_cards(target, ps["cards"])
        if "rows" in ps:
            _patch_rows(target, ps["rows"])

    return out


def _patch_bullets(target: dict[str, Any], bullets: Any) -> None:
    cur = target.get("bullets")
    if not isinstance(cur, list):
        raise DeckIrError("slide has no bullets to patch")
    if not isinstance(bullets, list):
        raise DeckIrError("bullets must be list")
    if len(bullets) != len(cur):
        raise DeckIrError("cannot change bullets length")
    out: list[str] = []
    for b in bullets:
        if not isinstance(b, str):
            raise DeckIrError("bullet must be string")
        out.append(_norm_ws(b))
    target["bullets"] = out


_CARD_KEYS = ("kicker", "title", "body")


def _patch_cards(target: dict[str, Any], cards: Any) -> None:
    cur = target.get("cards")
    if not isinstance(cur, list):
        raise DeckIrError("slide has no cards to patch")
    if not isinstance(cards, list):
        raise DeckIrError("cards must be list")
    if len(cards) != len(cur):
        raise DeckIrError("cannot change cards length")
    for i, nc in enumerate(cards):
        if not isinstance(nc, dict) or not isinstance(cur[i], dict):
            raise DeckIrError("card must be object")
        for key in _CARD_KEYS:
            if key not in nc:
                continue
            val = nc.get(key)
            if val is None:
                continue
            if not isinstance(val, str):
                raise DeckIrError(f"card.{key} must be string")
            cur[i][key] = _norm_ws(val)


def _patch_kpis(target: dict[str, Any], kpis: Any) -> None:
    cur = target.get("kpis")
    if not isinstance(cur, list):
        raise DeckIrError("slide has no kpis to patch")
    if not isinstance(kpis, list):
        raise DeckIrError("kpis must be list")
    if len(kpis) != len(cur):
        raise DeckIrError("cannot change kpis length")
    for i, nk in enumerate(kpis):
        if not isinstance(nk, dict) or not isinstance(cur[i], dict):
            raise DeckIrError("kpi must be object")
        for key in _KPI_KEYS:
            if key not in nk:
                continue
            val = nk.get(key)
            if val is None:
                continue
            if not isinstance(val, str):
                raise DeckIrError(f"kpi.{key} must be string")
            cur[i][key] = _norm_ws(val)
        if "status" in nk:
            # allow only if already present or valid — keep existing if omitted
            st = nk.get("status")
            if isinstance(st, str) and st in ("up", "down", "flat"):
                cur[i]["status"] = st


def _patch_rows(target: dict[str, Any], rows: Any) -> None:
    cur = target.get("rows")
    if not isinstance(cur, list):
        raise DeckIrError("slide has no rows to patch")
    if not isinstance(rows, list):
        raise DeckIrError("rows must be list")
    if len(rows) != len(cur):
        raise DeckIrError("cannot change table row count")
    for r, nrow in enumerate(rows):
        if not isinstance(nrow, list) or not isinstance(cur[r], list):
            raise DeckIrError("table row must be list")
        if len(nrow) != len(cur[r]):
            raise DeckIrError("cannot change table column count")
        for c, cell in enumerate(nrow):
            if not isinstance(cell, str):
                raise DeckIrError("table cell must be string")
            cur[r][c] = _norm_ws(cell)
