from pathlib import Path

from case3.gold_select import intent_tokens, select_gold


ROOT = Path(__file__).resolve().parents[1] / "prompt" / "gold"


def test_table_intent():
    names = [p.name for p in select_gold(ROOT, "сделай отчёт с таблицами", max_images=0)]
    assert "02_table.tex" in names
    assert "image_slot.tex" not in names


def test_bez_kartinok_keeps_tables():
    t = intent_tokens("отчёт с таблицами без картинок")
    assert "table" in t
    assert "no_table" not in t


def test_bez_tables():
    t = intent_tokens("кратко без таблиц")
    assert "no_table" in t
    names = [p.name for p in select_gold(ROOT, "кратко без таблиц", max_images=0)]
    assert "02_table.tex" not in names
