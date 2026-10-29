"""Deck structure catalog + prompt overlays."""

from __future__ import annotations

from case3.deck_structure import (
    list_structures,
    normalize_structure_id,
    structure_overlay,
)


def test_list_structures_has_julius_arcs() -> None:
    ids = {s["id"] for s in list_structures()}
    assert "board_update" in ids
    assert "investor" in ids
    assert "qbr" in ids
    assert "launch" in ids


def test_normalize_aliases() -> None:
    assert normalize_structure_id("board") == "board_update"
    assert normalize_structure_id("Investor Update") == "investor"
    assert normalize_structure_id("nope") is None


def test_structure_overlay_nonempty() -> None:
    text = structure_overlay("board_update")
    assert "Scorecard" in text or "scorecard" in text.lower()
    assert "invent" in text.lower() or "Source" in text
