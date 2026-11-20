"""Dashboard screen (Qwen) + born-digital table PDF → one markdown source."""

from __future__ import annotations

from pathlib import Path

import pytest

from case3 import prompts
from case3.dashboard_source import (
    DashboardSourceError,
    join_page_tables,
    parse_dashboard,
    prefer_ruled_tables,
    read_dashboard_png,
    table_block,
)


def test_table_keeps_russian_headers_duplicate_numbers_and_spaces() -> None:
    md, note = table_block(
        [
            ["Поступления за январь 2025", "", "", "", ""],
            [
                "Наименование платежа",
                "Вид бюджета",
                "Факт (руб.)",
                "План (руб.)",
                "Выполнение плана (%)",
            ],
            ["НДС", "Республиканский", "142 597,4", "100,0", "17,8%"],
            ["НДС", "Местный", "100,0", "100,0", "8,6%"],
        ]
    )
    assert md.startswith("## Поступления за январь 2025")
    assert "| Наименование платежа | Вид бюджета | Факт (руб.) |" in md
    assert "142 597,4" in md
    assert md.count("100,0") == 3
    assert "17,8%" in md
    assert note is None


def test_pipe_in_a_cell_is_escaped() -> None:
    md, _note = table_block([["A|B", "n"], ["x", "1"]])
    assert r"A\|B" in md
    assert "| A|B |" not in md


def test_overwide_table_is_cut_and_noted() -> None:
    header = [f"c{i}" for i in range(65)]
    row = [str(i) for i in range(65)]
    md, note = table_block([header, row])
    assert "| c63 |" in md
    assert "| c64 |" not in md
    assert note is not None
    assert "65" in note


def test_ruled_grid_beats_a_noisier_text_split() -> None:
    ruled = [[["Налог", "Факт"], ["НДС", "10"]]]
    noisy = [
        [["Налог", "Факт"], ["НДС", "10"], ["10", "10"], ["11", "12"]],
    ]
    chosen = prefer_ruled_tables(ruled, noisy)
    assert chosen == ruled


def test_wider_text_grid_beats_merged_ruled_columns() -> None:
    ruled = [
        [
            ["Налог", "Вид", "Факт (руб.) План (руб.)"],
            ["НДС", "Респ", "105 865,2 94 073,0"],
        ]
    ]
    text = [
        [
            ["Налог", "Вид", "Факт", "План"],
            ["НДС", "Респ", "105 865,2", "94 073,0"],
        ]
    ]
    assert prefer_ruled_tables(ruled, text) is text


def test_png_miss_keeps_the_pdf_table(tmp_path: Path) -> None:
    path = tmp_path / "one.pdf"
    _write_grid_pdf(
        path,
        [["Tax", "Fact"], ["VAT", "10"]],
        caption="Payments table for the dashboard export",
    )

    def boom(_raw: bytes) -> str:
        raise RuntimeError("qwen down")

    result = parse_dashboard(png=_tiny_png(), pdf=path, vision=boom)
    assert "VAT" in result.pdf_markdown
    assert result.png_markdown == ""
    assert any("qwen down" in note for note in result.warnings)
    assert "## Таблица PDF" in result.markdown
    assert "## Экран" not in result.markdown


def test_continuation_page_appends_under_the_same_header() -> None:
    header = ["Налог", "Факт"]
    page1 = [header, ["НДС", "10"]]
    page2 = [["Повтор заголовка страницы", ""], header, ["Акциз", "20"]]
    other = [["Регион", "Доля"], ["Брест", "31,8%"]]
    joined = join_page_tables([[page1], [page2, other]])
    assert joined[0] == [header, ["НДС", "10"], ["Акциз", "20"]]
    assert joined[1][0] == ["Регион", "Доля"]


def test_pdf_keeps_every_column_and_the_line_above_the_grid(tmp_path: Path) -> None:
    header = [f"c{i}" for i in range(14)]
    row = ["1 234,56" if i == 0 else ("77" if i in (1, 2) else str(i)) for i in range(14)]
    path = tmp_path / "wide.pdf"
    _write_grid_pdf(path, [header, row], caption="January 2025 payments")
    result = parse_dashboard(pdf=path)
    assert "January 2025 payments" in result.markdown
    assert "1 234,56" in result.markdown
    assert "| c13 |" in result.markdown
    assert "| 77 | 77 |" in result.markdown
    assert result.pdf_table_count == 1
    assert result.pdf_numeric_cells >= 14
    assert "## Таблица PDF" in result.markdown
    assert "## Экран" not in result.markdown
    assert result.warnings == []


def test_scan_pdf_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "blank.pdf"
    _write_blank_pdf(path)
    with pytest.raises(DashboardSourceError) as caught:
        parse_dashboard(pdf=path)
    assert caught.value.code == "scan_pdf"


def test_png_vision_text_becomes_the_screen_section() -> None:
    seen: list[bytes] = []

    def vision(raw: bytes) -> str:
        seen.append(raw)
        return "```markdown\n## Заголовок и фильтры\n\nБрестская область\n```"

    result = parse_dashboard(png=_tiny_png(), vision=vision)
    assert seen and seen[0].startswith(b"\x89PNG")
    assert "Брестская область" in result.markdown
    assert "```" not in result.markdown
    assert "## Экран" in result.markdown
    assert "## Таблица PDF" not in result.markdown
    assert result.png_markdown.startswith("## Заголовок")


def test_png_and_pdf_land_in_one_document(tmp_path: Path) -> None:
    path = tmp_path / "one.pdf"
    _write_grid_pdf(
        path,
        [["Tax", "Fact"], ["VAT", "10"]],
        caption="Payments table for the dashboard export",
    )
    result = parse_dashboard(
        png=_tiny_png(),
        pdf=path,
        vision=lambda _raw: "Карточка 100%",
    )
    assert result.markdown.index("## Экран") < result.markdown.index("## Таблица PDF")
    assert "Карточка 100%" in result.png_markdown
    assert "VAT" in result.pdf_markdown
    assert "Карточка 100%" in result.markdown and "VAT" in result.markdown


def test_missing_files_and_bad_bytes() -> None:
    with pytest.raises(DashboardSourceError) as missing:
        parse_dashboard()
    assert missing.value.code == "missing_input"
    with pytest.raises(DashboardSourceError) as bad_pdf:
        parse_dashboard(pdf=b"hello")
    assert bad_pdf.value.code == "bad_pdf"
    with pytest.raises(DashboardSourceError) as bad_png:
        parse_dashboard(png=b"not-a-png", vision=lambda _raw: "x")
    assert bad_png.value.code == "bad_png"


def test_oversize_pdf_stops_before_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("case3.dashboard_source.MAX_PDF_BYTES", 8)
    with pytest.raises(DashboardSourceError) as caught:
        parse_dashboard(pdf=b"%PDF-1.4\n" + b"x" * 20)
    assert caught.value.code == "too_large"


def test_dashboard_prompt_tells_qwen_not_to_invent() -> None:
    text = prompts.load("dashboard_png")
    assert "не разобрать" in text
    assert "markdown" in text.lower()
    assert "Не округляй" in text


def test_qwen_reader_sends_the_png_and_the_prompt() -> None:
    class _Fake:
        def complete(self, *, system: str, user_text: str, images=None, **_kwargs):
            assert "не разобрать" in system
            assert images and images[0][0] == "dashboard"
            assert str(images[0][1]).startswith("data:image/png;base64,")
            assert "дашборд" in user_text.lower()
            return "Фильтр: все"

    md = read_dashboard_png(_tiny_png(), client=_Fake())
    assert md == "Фильтр: все"


def _tiny_png() -> bytes:
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + chunk(b"IEND", b"")
    )


def _write_blank_pdf(path: Path) -> None:
    stream = b"q Q"
    _finish_pdf(path, stream, width=200, height=200)


def _write_grid_pdf(
    path: Path,
    rows: list[list[str]],
    *,
    caption: str = "",
) -> None:
    cols = max(len(row) for row in rows)
    col_w = 70
    row_h = 18
    margin = 36
    caption_h = 22 if caption else 0
    width = margin * 2 + col_w * cols
    height = margin * 2 + caption_h + row_h * len(rows)
    ops: list[str] = ["0.6 w"]
    top = margin + row_h * len(rows)
    for r in range(len(rows) + 1):
        y = margin + r * row_h
        ops.append(f"{margin} {y} m {margin + col_w * cols} {y} l S")
    for c in range(cols + 1):
        x = margin + c * col_w
        ops.append(f"{x} {margin} m {x} {top} l S")
    ops.append("BT /F1 8 Tf")
    if caption:
        ops.append(f"1 0 0 1 {margin} {top + 8} Tm ({_pdf_text(caption)}) Tj")
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            x = margin + ci * col_w + 3
            y = margin + (len(rows) - ri - 1) * row_h + 5
            ops.append(f"1 0 0 1 {x} {y} Tm ({_pdf_text(cell)}) Tj")
    ops.append("ET")
    _finish_pdf(path, "\n".join(ops).encode("latin-1"), width=width, height=height)


def _pdf_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _finish_pdf(path: Path, stream: bytes, *, width: int, height: int) -> None:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ).encode("ascii"),
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode("ascii")
    path.write_bytes(out)
