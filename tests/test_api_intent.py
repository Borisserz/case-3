from case3.api import build_intent_from_ui


def test_build_intent_prefers_whitelist_types():
    text = build_intent_from_ui(
        chat="сделай отчёт с таблицами",
        chart_types=["bar", "donut", "spider"],
        max_charts=2,
        max_images=1,
        forbid_charts=False,
        forbid_images=False,
    )
    assert "таблицами" in text
    assert "не более 2" in text
    assert "предпочитаемые типы" in text
    assert "bar" in text and "donut" in text
    assert "spider" not in text
    assert "не более 1" in text
    assert "Kandinsky" in text


def test_auto_mode_wording():
    text = build_intent_from_ui(
        chat="короткий отчёт",
        chart_types=[],
        max_charts=3,
        max_images=0,
        forbid_charts=False,
        forbid_images=True,
        chart_auto=True,
    )
    assert "на усмотрение модели" in text
    assert "не более 3" in text
    assert "0 допустимо" in text
    assert "без картинок" in text


def test_chart_hints_mapped_not_as_enum():
    text = build_intent_from_ui(
        chat="",
        chart_types=[],
        max_charts=2,
        max_images=0,
        forbid_charts=False,
        forbid_images=True,
        chart_hints="pie, воронка, сравнение долей",
        chart_auto=False,
    )
    assert "пожелания по визуализации" in text
    assert "pie" in text and "воронка" in text
    assert "сведи пожелания" in text
    assert "charts[].type — строго" in text


def test_forbid_flags():
    text = build_intent_from_ui(
        chat="",
        chart_types=["bar"],
        max_charts=3,
        max_images=2,
        forbid_charts=True,
        forbid_images=True,
    )
    assert "без графиков" in text
    assert "без картинок" in text
