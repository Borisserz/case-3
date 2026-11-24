from pathlib import Path

from case3.input_validation import validate_input_heuristics
from case3.source_attach import merge_ingested_sources


def test_report_phrase_keeps_the_attached_pdf_table(tmp_path: Path):
    ingest_id = "20261124T120000Z_abcdef"
    folder = tmp_path / "runs" / "uploads" / "ingest" / ingest_id
    folder.mkdir(parents=True)
    table = (
        "# Данные дашборда\n\n"
        "## Таблица PDF\n\n"
        "| Регион | Факт |\n| --- | --- |\n| Минск | 120 |\n"
    )
    (folder / "source.txt").write_text(table, encoding="utf-8")

    merged = merge_ingested_sources(
        "сделай отчет по данным",
        [{"fileName": "PivotTableElement13.pdf", "ingestId": ingest_id, "viewMode": "document"}],
        tmp_path,
    )
    valid, msg = validate_input_heuristics(merged, "сделай отчет по данным", output_mode="report")
    assert valid, msg
    assert "120" in merged
    assert "Минск" in merged


def test_merge_leaves_a_body_that_already_has_the_table(tmp_path: Path):
    ingest_id = "20261124T120001Z_abcdef"
    folder = tmp_path / "runs" / "uploads" / "ingest" / ingest_id
    folder.mkdir(parents=True)
    table = "| Регион | Факт |\n| --- | --- |\n| Брест | 8 |\n"
    (folder / "source.txt").write_text(table, encoding="utf-8")
    body = f"===== отчёт.pdf =====\n{table}"
    assert merge_ingested_sources(body, [{"ingestId": ingest_id}], tmp_path) == body


def test_merged_pdf_table_unlocks_bare_report_and_diagram_gate(tmp_path: Path):
    ingest_id = "20261124T120003Z_abcdef"
    folder = tmp_path / "runs" / "uploads" / "ingest" / ingest_id
    folder.mkdir(parents=True)
    (folder / "source.txt").write_text("| Регион | Факт |\n| --- | --- |\n| Минск | 120 |\n", encoding="utf-8")
    intent = "сделай отчет"
    merged = merge_ingested_sources(
        intent,
        [{"fileName": "PivotTableElement13.pdf", "ingestId": ingest_id}],
        tmp_path,
    )
    assert not validate_input_heuristics(intent, intent, output_mode="report")[0]
    for mode in ("report", "diagram"):
        valid, msg = validate_input_heuristics(merged, intent, output_mode=mode)
        assert valid, msg


def test_edited_markdown_is_not_replaced_by_the_pdf_file(tmp_path: Path):
    ingest_id = "20261124T120002Z_abcdef"
    folder = tmp_path / "runs" / "uploads" / "ingest" / ingest_id
    folder.mkdir(parents=True)
    (folder / "source.txt").write_text("| Регион | Факт |\n| --- | --- |\n| Минск | 120 |\n", encoding="utf-8")
    edited = "===== отчёт.pdf =====\n| Регион | Факт |\n| --- | --- |\n| Минск | 90 |\n"
    merged = merge_ingested_sources(
        edited,
        [{"ingestId": ingest_id, "sourceEdited": True}],
        tmp_path,
    )
    assert merged == edited
    assert "120" not in merged
