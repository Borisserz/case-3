"""Structural deck ops: reorder / duplicate / delete (no LLM)."""

from __future__ import annotations

import pytest

from case3.slides_ir import DeckIrError
from case3.slides_patch import apply_deck_structure


def _base() -> dict:
    return {
        "version": 1,
        "aspect": "16:9",
        "palette": "atelier",
        "language": "ru",
        "slides": [
            {"id": "s01", "layout": "title", "title": "A"},
            {"id": "s02", "layout": "bullets", "title": "B", "bullets": ["x"]},
            {"id": "s03", "layout": "closing", "title": "C"},
        ],
    }


def test_reorder_permutation() -> None:
    out = apply_deck_structure(
        _base(), {"op": "reorder", "order": ["s03", "s01", "s02"]}
    )
    assert [s["id"] for s in out["slides"]] == ["s03", "s01", "s02"]
    assert out["slides"][0]["title"] == "C"


def test_reorder_rejects_missing_or_extra() -> None:
    with pytest.raises(DeckIrError, match="order"):
        apply_deck_structure(_base(), {"op": "reorder", "order": ["s01", "s02"]})
    with pytest.raises(DeckIrError, match="order"):
        apply_deck_structure(
            _base(), {"op": "reorder", "order": ["s01", "s02", "s03", "s99"]}
        )


def test_duplicate_inserts_after_with_new_id() -> None:
    out = apply_deck_structure(_base(), {"op": "duplicate", "id": "s02"})
    ids = [s["id"] for s in out["slides"]]
    assert len(ids) == 4
    assert ids[0] == "s01"
    assert ids[1] == "s02"
    assert ids[2] != "s02"
    assert ids[3] == "s03"
    assert out["slides"][2]["title"] == "B"
    assert out["slides"][2]["bullets"] == ["x"]
    assert out["slides"][2]["id"] != out["slides"][1]["id"]


def test_delete_removes_slide() -> None:
    out = apply_deck_structure(_base(), {"op": "delete", "id": "s02"})
    assert [s["id"] for s in out["slides"]] == ["s01", "s03"]


def test_delete_refuses_last_slide() -> None:
    deck = {
        "version": 1,
        "slides": [{"id": "s01", "layout": "title", "title": "Only"}],
    }
    with pytest.raises(DeckIrError, match="last"):
        apply_deck_structure(deck, {"op": "delete", "id": "s01"})


def test_unknown_op() -> None:
    with pytest.raises(DeckIrError, match="op"):
        apply_deck_structure(_base(), {"op": "explode"})


def test_insert_slide_after_id_with_layout() -> None:
    out = apply_deck_structure(
        _base(), {"op": "insert", "id": "s02", "layout": "quote"}
    )
    ids = [s["id"] for s in out["slides"]]
    assert len(ids) == 4
    assert ids[0] == "s01"
    assert ids[1] == "s02"
    assert ids[2] not in ("s01", "s02", "s03")
    assert ids[3] == "s03"
    new_slide = out["slides"][2]
    assert new_slide["layout"] == "quote"
    assert new_slide["title"]
    assert "definition" in new_slide


def test_insert_slide_appends_when_no_id() -> None:
    out = apply_deck_structure(
        _base(), {"op": "insert", "layout": "scorecard"}
    )
    assert len(out["slides"]) == 4
    assert out["slides"][-1]["layout"] == "scorecard"
    assert len(out["slides"][-1]["kpis"]) >= 2


def test_insert_rejects_unknown_layout() -> None:
    with pytest.raises(DeckIrError, match="layout"):
        apply_deck_structure(_base(), {"op": "insert", "layout": "invalid_layout"})

