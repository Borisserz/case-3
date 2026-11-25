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
    assert "hire" in ids
    assert normalize_structure_id("hire") == "hire"


def test_normalize_aliases() -> None:
    assert normalize_structure_id("board") == "board_update"
    assert normalize_structure_id("Investor Update") == "investor"
    assert normalize_structure_id("nope") is None


def test_appledouble_sidecar_does_not_break_the_catalog(tmp_path, monkeypatch) -> None:
    (tmp_path / "hire.json").write_text(
        '{"id":"hire","label":"Hire"}',
        encoding="utf-8",
    )
    (tmp_path / "._hire.json").write_bytes(b"\x00\x05\x16\x07\xa3not-utf8")
    monkeypatch.setattr("case3.deck_structure._structures_dir", lambda: tmp_path)
    monkeypatch.setattr("case3.deck_structure._CACHE", None)
    ids = {row["id"] for row in list_structures()}
    assert ids == {"hire"}


def test_eight_templates_do_not_share_arc_or_pack() -> None:
    wanted = {
        "board_update": "board",
        "performance": "signal",
        "qbr": "relay",
        "survey": "voltage",
        "council": "studio",
        "campaign": "atelier",
        "quarter": "botanical",
        "investor": "ink",
    }
    rows = {s["id"]: s for s in list_structures()}
    arcs = []
    packs = []
    for sid, pack in wanted.items():
        row = rows[sid]
        assert row["default_pack"] == pack
        arcs.append(tuple(row["arc"]))
        packs.append(pack)
    assert len(set(arcs)) == len(arcs)
    assert len(set(packs)) == len(packs)
    assert "chart_hero" not in rows["survey"]["arc"]
    assert "table_hero" not in rows["council"]["arc"]
    assert rows["quarter"]["arc"] != rows["qbr"]["arc"]
    assert rows["council"]["arc"] != rows["board_update"]["arc"]


def test_structure_overlay_nonempty() -> None:
    text = structure_overlay("board_update")
    assert "Scorecard" in text or "scorecard" in text.lower()
    assert "invent" in text.lower() or "Source" in text
