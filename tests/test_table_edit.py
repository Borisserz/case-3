"""Structured TeX table patch for Liber Preview edit."""

from __future__ import annotations

import pytest

from case3.table_edit import (
    TableEditError,
    find_table_spans,
    patch_table_in_tex,
    validate_table_payload,
)
from case3.tex_preview import tex_to_preview_blocks

SAMPLE = r"""
\documentclass{article}
\begin{document}
\title{T}
\section{S}

\begin{table}[H]
  \centering
  \caption{Ключевые показатели}
  \begin{tabularx}{\textwidth}{lXX}
    \toprule
    Показатель & Значение & Комментарий \\
    \midrule
    Население & 9330 & Конец периода \\
    Рождения & 72\,000 & Зарегистрировано \\
    \bottomrule
  \end{tabularx}
\end{table}

\begin{table}[H]
  \centering
  \caption{Вторая}
  \begin{tabular}{ll}
    \toprule
    A & B \\
    \midrule
    1 & 2 \\
    \bottomrule
  \end{tabular}
\end{table}

\end{document}
"""


def test_find_table_spans_counts_two() -> None:
    spans = find_table_spans(SAMPLE)
    assert len(spans) == 2
    assert "Ключевые показатели" in SAMPLE[spans[0][0] : spans[0][1]]
    assert "Вторая" in SAMPLE[spans[1][0] : spans[1][1]]


def test_validate_rejects_mismatched_row() -> None:
    with pytest.raises(TableEditError):
        validate_table_payload(
            caption="x",
            headers=["a", "b"],
            rows=[["1"]],
        )


def test_validate_rejects_empty_headers() -> None:
    with pytest.raises(TableEditError):
        validate_table_payload(caption="", headers=[], rows=[])


def test_validate_rejects_too_large() -> None:
    headers = [f"c{i}" for i in range(41)]
    with pytest.raises(TableEditError):
        validate_table_payload(caption="", headers=headers, rows=[])


def test_patch_round_trip_caption_and_cell() -> None:
    patched = patch_table_in_tex(
        SAMPLE,
        1,
        caption="Новая подпись",
        headers=["Показатель", "Значение", "Комментарий"],
        rows=[
            ["Население", "9400", "Обновлено"],
            ["Рождения", "72000", "Зарегистрировано"],
        ],
    )
    blocks = tex_to_preview_blocks(patched)["blocks"]
    tables = [b for b in blocks if b["type"] == "table"]
    assert tables[0]["caption"] == "Новая подпись"
    assert tables[0]["rows"][0][1] == "9400"
    assert tables[0]["rows"][0][2] == "Обновлено"
    # second table untouched
    assert tables[1]["caption"] == "Вторая"


def test_patch_add_and_delete_column() -> None:
    patched = patch_table_in_tex(
        SAMPLE,
        2,
        caption="Вторая",
        headers=["A", "B", "C"],
        rows=[["1", "2", "3"]],
    )
    tables = [
        b
        for b in tex_to_preview_blocks(patched)["blocks"]
        if b["type"] == "table"
    ]
    assert tables[1]["headers"] == ["A", "B", "C"]
    assert tables[1]["rows"] == [["1", "2", "3"]]

    patched2 = patch_table_in_tex(
        patched,
        2,
        caption="Вторая",
        headers=["A", "C"],
        rows=[["1", "3"]],
    )
    tables2 = [
        b
        for b in tex_to_preview_blocks(patched2)["blocks"]
        if b["type"] == "table"
    ]
    assert tables2[1]["headers"] == ["A", "C"]
    assert tables2[1]["rows"] == [["1", "3"]]


def test_patch_empty_cell_becomes_tilde_round_trips_empty() -> None:
    patched = patch_table_in_tex(
        SAMPLE,
        2,
        caption="Вторая",
        headers=["A", "B"],
        rows=[["", "2"]],
    )
    span = find_table_spans(patched)[1]
    chunk = patched[span[0] : span[1]]
    assert "~" in chunk
    tables = [
        b
        for b in tex_to_preview_blocks(patched)["blocks"]
        if b["type"] == "table"
    ]
    assert tables[1]["rows"][0][0] == ""


def test_patch_escapes_specials() -> None:
    patched = patch_table_in_tex(
        SAMPLE,
        2,
        caption="100% & more",
        headers=["A_1", "B"],
        rows=[["x & y", "50%"]],
    )
    span = find_table_spans(patched)[1]
    chunk = patched[span[0] : span[1]]
    assert r"\%" in chunk
    assert r"\&" in chunk
    assert r"\_" in chunk
    tables = [
        b
        for b in tex_to_preview_blocks(patched)["blocks"]
        if b["type"] == "table"
    ]
    assert tables[1]["caption"] == "100% & more"
    assert tables[1]["headers"][0] == "A_1"
    assert tables[1]["rows"][0][0] == "x & y"


def test_patch_oob_raises() -> None:
    with pytest.raises(TableEditError):
        patch_table_in_tex(
            SAMPLE,
            9,
            caption="x",
            headers=["A"],
            rows=[["1"]],
        )
