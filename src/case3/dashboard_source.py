"""Stimulsoft dashboard → markdown.

PNG goes through the existing Qwen vision client. A born-digital PDF table
is read cell by cell (pdfplumber) so digits stay as printed. No HTTP route:
later the Stimulsoft service calls ``parse_dashboard``.
"""

from __future__ import annotations

import base64
import logging
import re
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Protocol

from case3 import prompts
from case3.pdf_text_gate import triage_pdf

log = logging.getLogger(__name__)

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PNG_BYTES = 15 * 1024 * 1024
MAX_TABLE_COLS = 64
MAX_TABLE_ROWS = 500

_NUM = re.compile(r"\d")
_COMPLETE_NUM = re.compile(r"^[+\-−]?\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d+)?%?$")
_SHORT_NUM = re.compile(r"^[+\-−]?\d{1,3}$")
_THOUSANDS_TAIL = re.compile(r"^\d{3}(?:[.,]\d+)?%?$")
_NUM_TOKEN = re.compile(r"[+\-−]?\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d+)?%?")
_FENCE = re.compile(r"^```(?:markdown|md)?[^\n]*\n(.*)\n?```$", re.DOTALL)
_WORD_GAP = 8.0
_LINE_BAND = 3.0

_LINE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}
_TEXT_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 4,
    "join_tolerance": 4,
}


class DashboardSourceError(Exception):
    """Stable ``code`` for a later API mapping."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class _VisionClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user_text: str,
        images: list[tuple[str, str]] | None = None,
    ) -> str: ...


@dataclass(frozen=True)
class DashboardSource:
    markdown: str
    png_markdown: str
    pdf_markdown: str
    warnings: list[str] = field(default_factory=list)
    pdf_table_count: int = 0
    pdf_numeric_cells: int = 0


def parse_dashboard(
    *,
    png: bytes | Path | None = None,
    pdf: bytes | Path | None = None,
    vision: Callable[[bytes], str] | None = None,
) -> DashboardSource:
    """One markdown document from a dashboard screenshot and/or a table PDF."""
    png_bytes = _as_bytes(png) if png is not None else None
    pdf_bytes = _as_bytes(pdf) if pdf is not None else None
    if png_bytes is None and pdf_bytes is None:
        raise DashboardSourceError(
            "Нужен PNG дашборда или PDF с таблицей.",
            code="missing_input",
        )

    png_md = ""
    pdf_md = ""
    warnings: list[str] = []
    table_count = 0
    numeric_cells = 0
    png_error: DashboardSourceError | None = None
    pdf_error: DashboardSourceError | None = None
    if png_bytes is not None:
        try:
            png_md = _screen_markdown(png_bytes, vision)
        except DashboardSourceError as exc:
            png_error = exc
    if pdf_bytes is not None:
        try:
            pdf_md, table_count, numeric_cells, warnings = _pdf_markdown(pdf_bytes)
        except DashboardSourceError as exc:
            pdf_error = exc
    if not png_md and not pdf_md:
        if png_error and pdf_error:
            raise DashboardSourceError(
                f"{png_error.message} {pdf_error.message}",
                code=pdf_error.code,
            )
        if png_error or pdf_error:
            raise png_error or pdf_error

    parts = ["# Данные дашборда", ""]
    if png_md and pdf_md:
        parts += [
            "Числа в разделе «Таблица PDF» скопированы из ячеек файла. "
            "Раздел «Экран» — подписи и числа, которые модель прочитала со снимка.",
            "",
        ]
    elif pdf_md:
        parts += ["Числа скопированы из ячеек PDF.", ""]
    else:
        parts += [
            "Текст ниже — чтение снимка. Где цифра не читается, стоит «не разобрать».",
            "",
        ]
    if png_error is not None:
        warnings.append(png_error.message)
    if pdf_error is not None:
        warnings.append(pdf_error.message)
    if png_md:
        parts += ["## Экран", "", png_md.rstrip(), ""]
    if pdf_md:
        parts += ["## Таблица PDF", "", pdf_md.rstrip(), ""]
    return DashboardSource(
        markdown="\n".join(parts).rstrip() + "\n",
        png_markdown=png_md,
        pdf_markdown=pdf_md,
        warnings=warnings,
        pdf_table_count=table_count,
        pdf_numeric_cells=numeric_cells,
    )


def read_dashboard_png(png: bytes, *, client: _VisionClient | None = None) -> str:
    """Ask Qwen for a markdown reading of one dashboard screenshot."""
    _check_png(png)
    if len(png) > MAX_PNG_BYTES:
        raise DashboardSourceError(
            "Снимок больше 15 МБ. Сожмите PNG без сильного даунскейла.",
            code="too_large",
        )
    reader = client if client is not None else _qwen_client()
    system = prompts.load("dashboard_png")
    data_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    try:
        text = reader.complete(
            system=system,
            user_text="Сними этот дашборд в markdown.",
            images=[("dashboard", data_url)],
        )
    except DashboardSourceError:
        raise
    except Exception as exc:
        raise DashboardSourceError(
            f"Модель не прочитала снимок: {exc}",
            code="vision_failed",
        ) from exc
    cleaned = _strip_fence(text or "")
    if not cleaned.strip():
        raise DashboardSourceError(
            "Модель ничего не вернула по снимку дашборда.",
            code="empty_screen",
        )
    return cleaned


def table_block(rows: list[list[object | None]]) -> tuple[str, str | None]:
    """One markdown table. A single filled first cell becomes a heading."""
    cleaned = _clean_rows(rows)
    if not cleaned:
        return "", None
    title = ""
    body = cleaned
    if _is_span_title(cleaned[0]):
        title = next(cell for cell in cleaned[0] if cell)
        body = cleaned[1:]
    if not body:
        return (f"## {title}\n" if title else ""), None

    orig_cols = max(len(row) for row in body)
    orig_rows = len(body)
    use_cols = min(orig_cols, MAX_TABLE_COLS)
    use_rows = body[:MAX_TABLE_ROWS]
    note = None
    if orig_cols > MAX_TABLE_COLS or orig_rows > MAX_TABLE_ROWS:
        note = (
            f"Таблица обрезана: было {orig_cols}×{orig_rows}, "
            f"осталось {use_cols}×{len(use_rows)}."
        )

    def fmt(row: list[str]) -> str:
        cells = row[:use_cols]
        if len(cells) < use_cols:
            cells = cells + [""] * (use_cols - len(cells))
        return "| " + " | ".join(cells) + " |"

    lines: list[str] = []
    if title:
        lines += [f"## {title}", ""]
    lines.append(fmt(use_rows[0]))
    lines.append("| " + " | ".join("---" for _ in range(use_cols)) + " |")
    for row in use_rows[1:]:
        lines.append(fmt(row))
    return "\n".join(lines) + "\n", note


def prefer_ruled_tables(
    line_rows: list[list[list[object | None]]],
    text_rows: list[list[list[object | None]]],
) -> list[list[list[object | None]]]:
    """Ruled lines win a noisy split of the same width.

    A text grid with more columns wins when the lines glued several
    headers into one cell. Stimulsoft does that on the numeric side.
    """
    line_nums = sum(_numeric_cells(table) for table in line_rows)
    text_nums = sum(_numeric_cells(table) for table in text_rows)
    if line_nums <= 0:
        return text_rows
    if text_nums <= 0:
        return line_rows
    if _width(text_rows) >= _width(line_rows) + 1 and _row_count(text_rows) >= max(
        2, _row_count(line_rows) // 2
    ):
        return text_rows
    return line_rows


def _width(tables: list[list[list[object | None]]]) -> int:
    return max((len(row) for table in tables for row in table), default=0)


def _row_count(tables: list[list[list[object | None]]]) -> int:
    return sum(len(table) for table in tables)


def join_page_tables(
    pages: list[list[list[list[object | None]]]],
) -> list[list[list[str]]]:
    """Append a later page when its header row repeats. A new header stays apart."""
    joined: list[list[list[str]]] = []
    for page in pages:
        for raw in page:
            rows = _clean_rows(raw)
            header, data = _header_and_body(rows)
            if not header or len(rows) < 2:
                continue
            if joined:
                prev_header, _prev_data = _header_and_body(joined[-1])
                if prev_header == header:
                    joined[-1].extend(data)
                    continue
            joined.append(rows)
    return joined


def _screen_markdown(png: bytes, vision: Callable[[bytes], str] | None) -> str:
    if len(png) > MAX_PNG_BYTES:
        raise DashboardSourceError(
            "Снимок больше 15 МБ. Сожмите PNG без сильного даунскейла.",
            code="too_large",
        )
    _check_png(png)
    if vision is None:
        return read_dashboard_png(png)
    try:
        text = vision(png)
    except DashboardSourceError:
        raise
    except Exception as exc:
        raise DashboardSourceError(
            f"Модель не прочитала снимок: {exc}",
            code="vision_failed",
        ) from exc
    cleaned = _strip_fence(text or "")
    if not cleaned.strip():
        raise DashboardSourceError(
            "Модель ничего не вернула по снимку дашборда.",
            code="empty_screen",
        )
    return cleaned


def _pdf_markdown(data: bytes) -> tuple[str, int, int, list[str]]:
    if len(data) > MAX_PDF_BYTES:
        raise DashboardSourceError(
            "PDF больше 20 МБ. Выгрузите таблицу отдельным файлом.",
            code="too_large",
        )
    if not data.startswith(b"%PDF"):
        raise DashboardSourceError(
            "Это не PDF. Для таблицы нужен цифровой PDF.",
            code="bad_pdf",
        )
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            path = Path(tmp.name)
        triage = triage_pdf(path)
        if not triage.usable:
            raise DashboardSourceError(
                "В PDF нет текстового слоя. Нужен цифровой экспорт таблицы, не скан.",
                code="scan_pdf",
            )
        return _extract_pdf(path)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def _extract_pdf(path: Path) -> tuple[str, int, int, list[str]]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise DashboardSourceError(
            "Не установлен pdfplumber, таблицу PDF разобрать нельзя.",
            code="ingest_dependency",
        ) from exc

    page_tables: list[list[list[list[object | None]]]] = []
    loose: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for index, page in enumerate(pdf.pages):
            tables, boxes = _page_tables(page)
            page_tables.append(tables)
            outside = _text_outside(page, boxes)
            if outside:
                loose.append(outside)
            log.info(
                "dashboard pdf page=%s tables=%s",
                index + 1,
                len(tables),
            )

    joined = join_page_tables(page_tables)
    blocks: list[str] = []
    notes: list[str] = []
    numeric = 0
    for rows in joined:
        block, note = table_block(rows)
        if block.strip():
            blocks.append(block.rstrip())
        if note:
            notes.append(note)
        numeric += _numeric_cells(rows)
    if blocks:
        parts = [text for text in loose if text]
        parts.extend(blocks)
        return "\n\n".join(parts).rstrip() + "\n", len(blocks), numeric, notes

    text = "\n\n".join(text for text in loose if text).strip()
    if not text:
        raise DashboardSourceError(
            "Из PDF не удалось извлечь текст.",
            code="empty_pdf",
        )
    notes.append("Таблица не разбилась на ячейки, оставлен текст страницы.")
    return text + "\n", 0, _numeric_in_text(text), notes


def choose_grids(
    line_rows: list[list[list[object | None]]],
    word_rows: list[list[list[object | None]]],
    text_rows: list[list[list[object | None]]],
) -> list[list[list[object | None]]]:
    """Prefer the grid that keeps a printed number whole.

    A Stimulsoft pivot often has no vertical rules. The text strategy then
    puts ``105`` and ``865,2`` in different columns. Word positions put them
    back. A real ruled grid still wins a tie.
    """
    best = line_rows
    best_score = _grid_score(line_rows)
    for candidate in (word_rows, text_rows):
        score = _grid_score(candidate)
        if score > best_score:
            best = candidate
            best_score = score
    return best


def words_to_rows(words: list[dict[str, object]]) -> list[list[str]]:
    """One grid from word boxes. A short gap is a space inside a cell."""
    if not words:
        return []
    lines = _word_lines(words)
    cell_lines = [_join_word_gaps(line) for line in lines]
    body = [
        cells
        for cells in cell_lines
        if any(_COMPLETE_NUM.fullmatch(cell["text"]) for cell in cells)
    ]
    if not body:
        return []
    edges = _column_edges(body)
    if len(edges) < 3:
        return []
    assigned = [_assign_cells(cells, edges) for cells in cell_lines]
    tops = [float(line[0]["top"]) for line in lines]
    return _clean_rows(_merge_wrapped(assigned, tops))


def _page_tables(page: object) -> tuple[list[list[list[object | None]]], list[tuple[float, float, float, float]]]:
    line_rows, line_boxes = _tables_for(page, _LINE_SETTINGS)
    word_rows, word_boxes = _word_tables(page)
    text_rows, text_boxes = _tables_for(page, _TEXT_SETTINGS)
    chosen = choose_grids(line_rows, word_rows, text_rows)
    if chosen is word_rows:
        return word_rows, word_boxes
    if chosen is text_rows:
        return text_rows, text_boxes
    return line_rows, line_boxes


def _word_tables(
    page: object,
) -> tuple[list[list[list[str]]], list[tuple[float, float, float, float]]]:
    words = page.extract_words(x_tolerance=1, y_tolerance=1) or []  # type: ignore[attr-defined]
    rows = words_to_rows(words)
    if not _plausible(rows):
        return [], []
    return [rows], [_word_bbox(words)]


def _grid_score(tables: list[list[list[object | None]]]) -> int:
    if not tables:
        return -10_000
    complete = glued = splits = 0
    for table in tables:
        for row in table:
            cells = [_clean_cell(cell) for cell in row]
            for index, cell in enumerate(cells):
                if not cell:
                    continue
                if _COMPLETE_NUM.fullmatch(cell):
                    complete += 1
                if len(_NUM_TOKEN.findall(cell)) >= 2:
                    glued += 1
                nxt = cells[index + 1] if index + 1 < len(cells) else ""
                if _SHORT_NUM.fullmatch(cell) and _THOUSANDS_TAIL.fullmatch(nxt):
                    splits += 1
    return complete - 4 * glued - 4 * splits


def _word_lines(words: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    ordered = sorted(words, key=lambda word: (float(word["top"]), float(word["x0"])))
    lines: list[list[dict[str, object]]] = []
    for word in ordered:
        if lines and abs(float(word["top"]) - float(lines[-1][0]["top"])) <= _LINE_BAND:
            lines[-1].append(word)
        else:
            lines.append([word])
    return lines


def _join_word_gaps(words: list[dict[str, object]]) -> list[dict[str, float | str]]:
    cells: list[dict[str, float | str]] = []
    for word in sorted(words, key=lambda item: float(item["x0"])):
        text = str(word["text"])
        x0 = float(word["x0"])
        x1 = float(word["x1"])
        if cells and x0 - float(cells[-1]["x1"]) < _WORD_GAP:
            cells[-1]["text"] = str(cells[-1]["text"]) + " " + text
            cells[-1]["x1"] = max(float(cells[-1]["x1"]), x1)
            continue
        cells.append({"text": text, "x0": x0, "x1": x1})
    return cells


def _column_edges(body: list[list[dict[str, float | str]]]) -> list[float]:
    cells = [cell for line in body for cell in line]
    parent = list(range(len(cells)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left in range(len(cells)):
        for right in range(left + 1, len(cells)):
            if _same_column(cells[left], cells[right]):
                parent[find(left)] = find(right)
    groups: dict[int, list[dict[str, float | str]]] = {}
    for index, cell in enumerate(cells):
        groups.setdefault(find(index), []).append(cell)
    columns = []
    for group in groups.values():
        columns.append(
            {
                "x0": min(float(cell["x0"]) for cell in group),
                "x1": max(float(cell["x1"]) for cell in group),
                "n": len(group),
                "numeric": sum(
                    1 for cell in group if _COMPLETE_NUM.fullmatch(str(cell["text"]))
                ),
            }
        )
    columns.sort(key=lambda column: column["x0"])
    edges = [columns[0]["x0"] - 1]
    for prev, column in zip(columns, columns[1:]):
        if column["numeric"] * 2 >= column["n"]:
            edges.append(prev["x1"] + 0.5)
        else:
            edges.append((prev["x1"] + column["x0"]) / 2)
    edges.append(columns[-1]["x1"] + 40)
    return edges


def _same_column(left: dict[str, float | str], right: dict[str, float | str]) -> bool:
    overlap = min(float(left["x1"]), float(right["x1"])) - max(
        float(left["x0"]), float(right["x0"])
    )
    if overlap > 0:
        return True
    return bool(
        _COMPLETE_NUM.fullmatch(str(left["text"]))
        and _COMPLETE_NUM.fullmatch(str(right["text"]))
        and abs(float(left["x1"]) - float(right["x1"])) <= _WORD_GAP
    )


def _assign_cells(cells: list[dict[str, float | str]], edges: list[float]) -> list[str]:
    row = [""] * (len(edges) - 1)
    for cell in cells:
        center = (float(cell["x0"]) + float(cell["x1"])) / 2
        index = len(edges) - 2
        for slot in range(len(edges) - 1):
            if edges[slot] <= center < edges[slot + 1]:
                index = slot
                break
        text = str(cell["text"])
        row[index] = f"{row[index]} {text}".strip() if row[index] else text
    return row


def _has_number(row: list[str]) -> bool:
    return any(_COMPLETE_NUM.fullmatch(cell) for cell in row if cell)


def _merge_wrapped(rows: list[list[str]], tops: list[float]) -> list[list[str]]:
    """Join a wrapped header with the line above it.

    The second line of «Выполнение / плана (%)» sits closer to the first
    header line than to the first sum. A full data row does not.
    """
    if not rows:
        return []
    first_num = next((index for index, row in enumerate(rows) if _has_number(row)), len(rows))
    diffs = [b - a for a, b in zip(tops, tops[1:]) if b > a]
    pitch = sorted(diffs)[len(diffs) // 2] if diffs else 999.0
    merged = [list(rows[0])]
    prev_top = tops[0]
    for index, (row, top) in enumerate(zip(rows[1:], tops[1:]), start=1):
        gap = top - prev_top
        prev_top = top
        if _has_number(row):
            merged.append(list(row))
            continue
        distance_to_data = (
            tops[first_num] - top if first_num < len(tops) else pitch
        )
        preamble = index < first_num and gap < distance_to_data
        if preamble or gap < pitch * 0.75:
            previous = merged[-1]
            for slot, cell in enumerate(row):
                if cell:
                    previous[slot] = (
                        f"{previous[slot]} {cell}".strip() if previous[slot] else cell
                    )
            continue
        merged.append(list(row))
    return merged


def _word_bbox(words: list[dict[str, object]]) -> tuple[float, float, float, float]:
    return (
        min(float(word["x0"]) for word in words),
        min(float(word["top"]) for word in words),
        max(float(word["x1"]) for word in words),
        max(float(word["bottom"]) for word in words),
    )


def _tables_for(
    page: object,
    settings: dict[str, object],
) -> tuple[list[list[list[object | None]]], list[tuple[float, float, float, float]]]:
    found = page.find_tables(settings) or []  # type: ignore[attr-defined]
    rows: list[list[list[object | None]]] = []
    boxes: list[tuple[float, float, float, float]] = []
    for table in found:
        extracted = table.extract()
        if not extracted or not _plausible(extracted):
            continue
        rows.append(extracted)
        bbox = getattr(table, "bbox", None)
        if bbox:
            boxes.append(tuple(bbox))  # type: ignore[arg-type]
    return rows, boxes


def _plausible(rows: list[list[object | None]]) -> bool:
    if len(rows) < 2:
        return False
    width = max((len(row) for row in rows), default=0)
    if width < 2:
        return False
    nonempty = [
        _clean_cell(cell)
        for row in rows
        for cell in row
        if _clean_cell(cell)
    ]
    if len(nonempty) < 4:
        return False
    return sum(1 for cell in nonempty if _NUM.search(cell)) >= 2


def _text_outside(
    page: object,
    boxes: list[tuple[float, float, float, float]],
) -> str:
    def _outside(obj: dict) -> bool:
        x0 = float(obj.get("x0", 0))
        x1 = float(obj.get("x1", x0))
        top = float(obj.get("top", 0))
        bottom = float(obj.get("bottom", top))
        cx, cy = (x0 + x1) / 2, (top + bottom) / 2
        for left, upper, right, lower in boxes:
            if left <= cx <= right and upper <= cy <= lower:
                return False
        return True

    filtered = page.filter(_outside) if boxes else page  # type: ignore[attr-defined]
    text = (filtered.extract_text() or "").strip()
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip())


def _header_and_body(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    if not rows:
        return [], []
    body = rows[1:] if _is_span_title(rows[0]) else list(rows)
    if not body:
        return [], []
    return list(body[0]), [list(row) for row in body[1:]]


def _is_span_title(row: list[str]) -> bool:
    return len(row) >= 2 and len([cell for cell in row if cell]) == 1


def _clean_rows(rows: list[list[object | None]]) -> list[list[str]]:
    if not rows:
        return []
    width = max(len(row) for row in rows)
    cleaned: list[list[str]] = []
    for row in rows:
        cells = [_clean_cell(cell) for cell in row]
        if len(cells) < width:
            cells.extend([""] * (width - len(cells)))
        else:
            cells = cells[:width]
        if any(cells):
            cleaned.append(cells)
    return cleaned


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    return " ".join(text.split())


def _numeric_cells(rows: list[list[object]]) -> int:
    return sum(1 for row in rows for cell in row if _NUM.search(_clean_cell(cell)))


def _numeric_in_text(text: str) -> int:
    return len(re.findall(r"\d+(?:[ \u00a0]\d{3})*(?:[.,]\d+)?%?", text))


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    match = _FENCE.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def _check_png(png: bytes) -> None:
    if not png.startswith(b"\x89PNG"):
        raise DashboardSourceError(
            "Снимок должен быть PNG.",
            code="bad_png",
        )


def _as_bytes(value: bytes | Path) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    path = Path(value)
    if not path.is_file():
        raise DashboardSourceError(
            f"Файл не найден: {path.name}",
            code="missing_file",
        )
    return path.read_bytes()


def _qwen_client() -> _VisionClient:
    from case3.llm_client import LLMClient, LLMConfig

    cfg = LLMConfig.from_env()
    cfg = replace(
        cfg,
        temperature=0.1,
        max_tokens=min(4096, int(cfg.max_tokens)),
        reasoning="off",
    )
    return LLMClient(cfg)
