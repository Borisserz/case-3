"""Static Liber slide HTML from deck IR."""

from __future__ import annotations

from case3.slides_html import render_slide_html


def test_title_slide_dimensions_and_layout() -> None:
    html = render_slide_html(
        {"id": "s01", "layout": "title", "title": "Итоги года", "subtitle": "2024"},
        palette="atelier",
        chart_png_href=None,
    )
    assert 'id="slide"' in html
    assert 'data-layout="title"' in html
    assert "1920px" in html and "1080px" in html
    assert "Итоги года" in html
    assert "2024" in html
    assert "purple" not in html.lower()
    assert "#3f5210" in html or "--primary" in html


def test_bullets_slide() -> None:
    html = render_slide_html(
        {
            "id": "s02",
            "layout": "bullets",
            "title": "Факты",
            "bullets": ["Выручка 120 млн", "Доля 35%"],
        },
        palette="ocean",
        chart_png_href=None,
    )
    assert 'data-layout="bullets"' in html
    assert "<li>" in html
    assert "Выручка 120 млн" in html


def test_chart_hero_embeds_img() -> None:
    html = render_slide_html(
        {
            "id": "s03",
            "layout": "chart_hero",
            "title": "Доля",
            "caption": "Source",
            "chart_id": "cht_01",
        },
        palette="atelier",
        chart_png_href="chart.png",
    )
    assert 'data-layout="chart_hero"' in html
    assert 'src="chart.png"' in html
    assert "Source" in html


def test_closing_slide() -> None:
    html = render_slide_html(
        {"id": "s04", "layout": "closing", "title": "Далее", "bullets": ["Шаг 1"]},
        palette="mono",
        chart_png_href=None,
    )
    assert 'data-layout="closing"' in html
    assert "Шаг 1" in html


def test_kpi_row_slide() -> None:
    html = render_slide_html(
        {
            "id": "s05",
            "layout": "kpi_row",
            "title": "KPI",
            "kpis": [
                {"label": "Выручка", "value": "120 млн", "hint": "год"},
                {"label": "Доля", "value": "35%"},
            ],
        },
        palette="atelier",
    )
    assert 'data-layout="kpi_row"' in html
    assert "kpi-card" in html
    assert "120 млн" in html


def test_chart_split_slide() -> None:
    html = render_slide_html(
        {
            "id": "s06",
            "layout": "chart_split",
            "title": "Разбор",
            "chart_id": "cht_01",
            "body": "Короткий комментарий",
            "bullets": ["Пункт A"],
        },
        palette="ocean",
        chart_png_href="chart.png",
    )
    assert 'data-layout="chart_split"' in html
    assert "chart-split" in html
    assert "chart-col" in html
    assert 'src="chart.png"' in html


def test_media_hero_photo() -> None:
    html = render_slide_html(
        {
            "id": "s07",
            "layout": "media_hero",
            "kicker": "Контекст",
            "title": "Витрина",
            "media_id": "fig_01",
            "caption": "Магазин электроники",
        },
        palette="atelier",
        media_png_href="media.png",
    )
    assert 'data-layout="media_hero"' in html
    assert "media-frame" in html
    assert "kicker" in html
    assert 'src="media.png"' in html


def test_media_split_diagram() -> None:
    html = render_slide_html(
        {
            "id": "s08",
            "layout": "media_split",
            "kicker": "Схема",
            "title": "Процесс",
            "media_id": "dia_01",
            "body": "Короткий разбор",
            "bullets": ["Шаг один"],
        },
        palette="editorial",
        media_png_href="media.png",
    )
    assert 'data-layout="media_split"' in html
    assert "media-split__grid" in html
    assert "Шаг один" in html


def test_section_splash_twin_panel() -> None:
    html = render_slide_html(
        {
            "id": "s09",
            "layout": "section",
            "chapter": 2,
            "title": "Рост каналов",
            "subtitle": "Q3",
        },
        palette="atelier",
        style={"brand_mark": "LIBER · BOARD"},
    )
    assert 'data-layout="section"' in html
    assert "section-splash__panel" in html
    assert "02" in html
    assert "LIBER · BOARD" in html


def test_parse_hero_metrics_newlines_and_dots() -> None:
    from case3.slides_html import parse_hero_metrics, render_slide_html

    assert parse_hero_metrics("4,8 млрд\nВыручка\n27%\nE-com") == [
        ("4,8 млрд", "Выручка"),
        ("27%", "E-com"),
    ]
    assert parse_hero_metrics("$9.6M — pipeline · 8.0x — efficiency") == [
        ("$9.6M", "pipeline"),
        ("8.0x", "efficiency"),
    ]
    html = render_slide_html(
        {
            "id": "s01",
            "layout": "title",
            "title": "QBR",
            "takeaway": "4,8 млрд\nВыручка\n27%\nE-com",
        },
        palette="atelier",
        style={
            "pack_id": "relay",
            "motif": {"split": 0.55, "panels": ["#E8E0F2"]},
        },
    )
    assert "hero-metric__value" in html
    assert "4,8 млрд" in html
    assert 'data-pack="relay"' in html


def test_scorecard_pastel_kpi_cards() -> None:
    style = {
        "pack_id": "relay",
        "motif": {"panels": ["#E8E0F2", "#DDEADB", "#F6DDD0", "#DDEAF0"]},
    }
    html = render_slide_html(
        {
            "id": "s03",
            "layout": "scorecard",
            "title": "Scorecard",
            "kpis": [
                {"label": "Pipeline", "value": "$9.6M", "delta": "+12%"},
                {"label": "Spend", "value": "8.0x", "delta": "eff."},
            ],
        },
        palette="atelier",
        style=style,
        slide_index=2,
    )
    assert "background:#E8E0F2" in html  # card 0
    assert "background:#DDEADB" in html  # card 1


def test_section_panel_rotates_motif_panels() -> None:
    style = {
        "brand_mark": "MARKETING / Q3",
        "motif": {
            "split": 0.55,
            "panels": ["#E8E0F2", "#DDEADB", "#F6DDD0", "#DDEAF0"],
        },
        "colors": {"panel": "#E8E0F2", "paper": "#FBF9F4", "accent": "#416650"},
    }
    slide = {
        "id": "s02",
        "layout": "section",
        "chapter": 1,
        "title": "Search and webinars",
    }
    h0 = render_slide_html(slide, palette="atelier", style=style, slide_index=0)
    h1 = render_slide_html(slide, palette="atelier", style=style, slide_index=1)
    h5 = render_slide_html(slide, palette="atelier", style=style, slide_index=5)
    assert "--panel: #E8E0F2" in h0
    assert "--panel: #DDEADB" in h1
    assert "--panel: #DDEADB" in h5  # 5 % 4 == 1
    assert ".section-splash__panel" in h1
    assert "background: var(--panel)" in h1


def test_card_row_narr_cards_and_gate() -> None:
    html = render_slide_html(
        {
            "id": "s05",
            "layout": "card_row",
            "kicker": "Target audience",
            "title": "Start with the ritual-minded.",
            "subtitle": "Audience hypotheses to validate.",
            "caption": "VALIDATION GATE  15 interviews + 50 tasting sessions",
            "cards": [
                {
                    "kicker": "PRIMARY / THE EVENING EDITOR",
                    "title": "Design-conscious adults",
                    "body": "Ages 28–44; busy routines.",
                },
                {
                    "kicker": "SECONDARY / THE QUIET GIVER",
                    "title": "Thoughtful gift buyers",
                    "body": "Shops for hosts and care packages.",
                },
                {
                    "kicker": "CONTEXT / THE SLOW MOMENT",
                    "title": "One cup. One cue.",
                    "body": "After dinner, before a book.",
                },
            ],
        },
        palette="atelier",
        style={
            "pack_id": "botanical",
            "motif": {"panels": ["#2A4538", "#334F40", "#3A5646"]},
        },
    )
    assert 'data-layout="card_row"' in html
    assert "narr-grid" in html
    assert "narr-card" in html
    assert "Design-conscious adults" in html
    assert "narr-gate" in html
    assert "VALIDATION GATE" in html
    assert 'data-pack="botanical"' in html


def test_scorecard_callout_table() -> None:
    score = render_slide_html(
        {
            "id": "s10",
            "layout": "scorecard",
            "title": "KPI",
            "takeaway": "Рост устойчивый",
            "kpis": [
                {
                    "label": "Выручка",
                    "value": "120",
                    "delta": "+8%",
                    "status": "up",
                }
            ],
        },
        palette="atelier",
    )
    assert "scorecard-grid" in score
    assert "+8%" in score
    assert "Рост устойчивый" in score

    callout = render_slide_html(
        {
            "id": "s11",
            "layout": "callout",
            "title": "Смысл",
            "term": "NPS",
            "definition": "Лояльность клиентов",
            "body": "Источник: опрос",
        },
        palette="atelier",
    )
    assert "callout-box" in callout
    assert "NPS" in callout

    table = render_slide_html(
        {
            "id": "s12",
            "layout": "table_hero",
            "title": "Сводка",
            "rows": [["A", "B"], ["1", "2"]],
        },
        palette="atelier",
    )
    assert "deck-table" in table
    assert "<th>A</th>" in table
