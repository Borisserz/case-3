"""Shares and ranks computed from dashboard cells become Source."""

from case3.dashboard_source import derivative_block
from case3.fact_ground import ground_generated

_TEX = """
\\documentclass{article}
\\begin{document}
%s
\\end{document}
"""


def _kept(prose: str, source: str) -> str:
    tex, _charts, _figures, _diagrams, _dropped = ground_generated(
        _TEX % prose,
        [],
        [],
        [],
        source=source,
        intent="",
    )
    return tex


def test_two_regions_keep_their_share_in_the_report() -> None:
    table = (
        "| Область | Сумма |\n"
        "| --- | --- |\n"
        "| Минская | 60 |\n"
        "| Гомельская | 40 |\n"
    )
    block = derivative_block(table)
    assert "Минская" in block
    assert "60%" in block
    assert "место 1" in block
    assert "Гомельская" in block
    assert "40%" in block
    assert "место 2" in block
    source = table + "\n## Производные\n" + block
    kept = _kept("Доля Минской составляет 60%. Гомельская — 40%.", source)
    assert "60%" in kept
    assert "40%" in kept


def test_equal_parts_round_so_the_shares_sum_to_100() -> None:
    table = (
        "| Область | Сумма |\n"
        "| --- | --- |\n"
        "| Брестская | 1 |\n"
        "| Витебская | 1 |\n"
        "| Гомельская | 1 |\n"
    )
    block = derivative_block(table)
    assert block.count("33,3%") == 2
    assert block.count("33,4%") == 1
    kept = _kept("Брестская 33,3%. Витебская 33,3%. Гомельская 33,4%.", table + block)
    assert "33,4%" in kept


def test_total_row_is_not_a_region_and_a_year_is_not_a_sum() -> None:
    table = (
        "| Область | Год | Сумма |\n"
        "| --- | --- | --- |\n"
        "| Минская | 2024 | 105 865,2 |\n"
        "| Гомельская | 2025 | 94 073,0 |\n"
        "| Итого |  | 199 938,2 |\n"
    )
    block = derivative_block(table)
    assert "Итого" not in block
    assert "2024" not in block
    assert "52,9%" in block
    assert "47,1%" in block


def test_a_column_that_is_already_a_share_is_not_divided_again() -> None:
    table = (
        "| Область | Доля |\n"
        "| --- | --- |\n"
        "| Минская | 60% |\n"
        "| Гомельская | 40% |\n"
    )
    block = derivative_block(table)
    assert "доля" not in block.casefold()
