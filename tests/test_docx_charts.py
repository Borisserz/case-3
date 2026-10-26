"""Native OOXML charts in post-pandoc DOCX."""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path

import pytest

from case3.docx_charts import (
    replace_docx_native_charts,
    try_replace_docx_native_charts,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "docx_with_cht_pictures.docx"


def _ensure_fixture(tmp_path: Path) -> Path:
    """Use committed fixture, or synthesize from a recent run DOCX if present."""
    if FIX.is_file():
        dest = tmp_path / "in.docx"
        shutil.copy2(FIX, dest)
        return dest
    # Fallback: clone a real run artifact (dev machines with runs/).
    root = Path(__file__).resolve().parents[1]
    sample = root / "runs/out/polish123_1792999615/01_temp_shares.docx"
    if not sample.is_file():
        pytest.skip("no DOCX fixture and no sample run")
    dest = tmp_path / "in.docx"
    shutil.copy2(sample, dest)
    return dest


def test_replace_docx_charts_writes_word_charts(tmp_path: Path) -> None:
    docx = _ensure_fixture(tmp_path)
    figures = {
        "charts": [
            {
                "id": "cht_01",
                "type": "bar",
                "series": {
                    "type": "bar",
                    "categories": ["Пн", "Вт", "Ср"],
                    "series": [{"name": "T", "values": [15.0, 16.0, 18.0]}],
                },
            },
            {
                "id": "cht_02",
                "type": "donut",
                "caption": "Бюджет",
                "series": {
                    "type": "donut",
                    "categories": ["A", "B"],
                    "series": [{"name": "Бюджет", "values": [45.0, 55.0]}],
                },
            },
        ]
    }
    fj = tmp_path / "figures.json"
    fj.write_text(json.dumps(figures), encoding="utf-8")
    replaced = replace_docx_native_charts(
        docx,
        figures_path=fj,
        series_hexes=["#2E4208", "#4F6B14", "#7A9A28"],
    )
    assert "cht_01" in replaced and "cht_02" in replaced
    with zipfile.ZipFile(docx) as zf:
        charts = [
            n
            for n in zf.namelist()
            if re.match(r"word/charts/chart\d+\.xml$", n)
        ]
        assert len(charts) >= 2, charts
        doc = zf.read("word/document.xml").decode("utf-8")
        assert "drawingml/2006/chart" in doc
        # Picture descr for cht should be gone / charts present
        assert doc.count("c:chart") >= 2 or doc.count("r:id=") >= 2

        # (1) dead PNG media + image rels removed
        media = [n for n in zf.namelist() if n.startswith("word/media/")]
        rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
        assert not media, f"expected no leftover media, got {media}"
        assert "Target=\"media/" not in rels

        # (5) no auto chart title (caption under figure stays in document body)
        for cf in charts:
            xml = zf.read(cf).decode("utf-8")
            assert 'autoTitleDeleted val="1"' in xml, cf
            assert not re.search(r"<c:title>.*?</c:title>", xml, re.S)


def test_try_replace_soft_fail_missing_series(tmp_path: Path) -> None:
    docx = _ensure_fixture(tmp_path)
    fj = tmp_path / "figures.json"
    fj.write_text(json.dumps({"charts": [{"id": "cht_01", "type": "kpi"}]}), encoding="utf-8")
    ok = try_replace_docx_native_charts(docx, figures_path=fj)
    assert ok == []  # nothing replaced, no raise
