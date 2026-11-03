"""Sparse-fill must not dump meta-skeleton Source as the report body."""

from case3.generate import _source_lines_to_tex, fill_sparse_tex_with_source


def test_source_lines_drops_meta_framing_and_emoji_headings() -> None:
    src = (
        "Вот полный комплект исходных данных, структур и инструкций, "
        "которые вы можете использовать как «скелет» для создания отчета.\n"
        "\n"
        "Вы можете взять эти блоки и заполнить их текстом.\n"
        "\n"
        "### 📂 БЛОК 1: СТРУКТУРА ОТЧЕТА\n"
        "*Используйте эту структуру для создания оглавления.*\n"
        "* 1.1. Глобальный тренд.\n"
        "* 1.2. Специфика Беларуси.\n"
        "\n"
        "| Год | Рынок |\n"
        "| --- | --- |\n"
        "| 2024 | 30 |\n"
    )
    lines = _source_lines_to_tex(src)
    blob = "\n".join(lines)
    assert "полный комплект" not in blob
    assert "скелет" not in blob
    assert "Вы можете взять" not in blob
    assert "Используйте эту структуру" not in blob
    assert "📂" not in blob
    assert r"\begin{itemize}" in blob
    assert r"\item 1.1. Глобальный тренд." in blob
    assert r"\begin{tabularx}" in blob


def test_fill_sparse_keeps_tables_not_meta_instructions() -> None:
    preamble = (
        r"\documentclass{article}"
        "\n"
        r"\begin{document}"
        "\n"
        r"\end{document}"
        "\n"
    )
    src = (
        "Вот «полный комплект» как скелет для отчета.\n"
        "### Данные\n"
        "| Год | M2 |\n"
        "| --- | --- |\n"
        "| 2023 | 26 |\n"
        "| 2024 | 30 |\n"
    )
    out = fill_sparse_tex_with_source(
        preamble, src, chart_ids=["cht_01"], figure_ids=[]
    )
    assert "полный комплект" not in out
    assert "скелет" not in out
    assert r"\begin{tabularx}" in out
    assert "%CASE3_CHART:cht_01%" in out
