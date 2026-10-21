"""Outline + prompt for chat summary (no invention, CTA)."""

from __future__ import annotations

from pathlib import Path

from case3.chat_summary import SUMMARY_SYSTEM, build_outline, build_summary_user

FIXTURE = Path(__file__).parent / "fixtures" / "preview_sample.tex"


def test_build_outline_includes_title_headings_captions() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    outline = build_outline(tex)
    assert "Демография 2019–2023" in outline
    assert "Общая" in outline
    assert "Численность населения" in outline
    # No massive raw TeX dump
    assert r"\documentclass" not in outline
    assert r"\usepackage" not in outline


def test_summary_system_forbids_invention_and_asks_cta() -> None:
    s = SUMMARY_SYSTEM.lower()
    assert "не выдумыв" in s or "only from" in s or "только из" in s
    assert "полн" in SUMMARY_SYSTEM.lower() or "документ" in SUMMARY_SYSTEM.lower()
    assert "media" in s or "график" in SUMMARY_SYSTEM.lower()


def test_build_summary_user_embeds_outline_and_intent() -> None:
    user = build_summary_user("TITLE: Demo\n- Sec A", intent="Сделай краткий обзор")
    assert "Demo" in user
    assert "Sec A" in user
    assert "Сделай краткий обзор" in user


def test_build_summary_user_includes_media_delivered_counts() -> None:
    user = build_summary_user(
        "TITLE: Demo\nFIGURE: photo",
        intent="нужны 3 графика и 1 картинка",
        media={"charts_ok": 0, "figures_ok": 1, "charts_planned": 0, "figures_planned": 1},
    )
    assert "MEDIA_DELIVERED" in user
    assert "charts_ok: 0" in user
    assert "figures_ok: 1" in user
    # Intent wish must not be the only signal — media block present
    assert "нужны 3 графика" in user


def test_build_outline_marks_chart_vs_figure() -> None:
    tex = FIXTURE.read_text(encoding="utf-8")
    outline = build_outline(tex)
    # preview fixture chart id cht_01
    assert "CHART:" in outline or "FIGURE:" in outline
