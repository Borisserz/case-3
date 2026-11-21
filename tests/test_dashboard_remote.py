"""Colleague /shot JSON → file bytes. Paths on his disk are not enough."""

from __future__ import annotations

import base64

import pytest

from case3.dashboard_remote import (
    DashboardRemoteError,
    capture_documents,
    files_from_shot,
    filters_from_model,
    filtered_open_url,
    might_ask_dashboard,
    plan_dashboard_phrase,
    service_base,
    viewer_url,
)


def test_service_base_and_viewer_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHBOARD_SERVICE_URL", "http://10.0.0.8:8040/")
    assert service_base() == "http://10.0.0.8:8040"
    assert viewer_url() == "http://10.0.0.8:8040/viewer"


def test_files_from_shot_prefers_inline_bytes() -> None:
    raw = b"\x89PNG\r\nhello"
    pdf = b"%PDF-1.4 table"
    payload = {
        "ok": True,
        "png": {
            "name": "dashboard_20261122.png",
            "data_b64": base64.b64encode(raw).decode(),
            "path": "/remote/nope.png",
        },
        "pdfs": [
            {
                "name": "Оплаты_20261122.pdf",
                "data_b64": base64.b64encode(pdf).decode(),
            }
        ],
    }
    files = files_from_shot(payload, fetch_named=lambda _name: None)
    assert [(item.name, item.ext, item.data) for item in files] == [
        ("dashboard_20261122.png", "png", raw),
        ("Оплаты_20261122.pdf", "pdf", pdf),
    ]


def test_files_from_shot_reads_his_path_on_this_machine(tmp_path) -> None:
    png = tmp_path / "screen.png"
    png.write_bytes(b"\x89PNG-local")
    payload = {
        "ok": True,
        "png": {"name": "screen.png", "path": str(png), "kind": "png"},
    }
    called = False

    def fetch_named(_name: str) -> bytes | None:
        nonlocal called
        called = True
        return None

    files = files_from_shot(payload, fetch_named=fetch_named)
    assert called is False
    assert files[0].data == b"\x89PNG-local"


def test_files_from_shot_downloads_when_the_body_is_only_a_path() -> None:
    payload = {
        "ok": True,
        "png": {"name": "screen.png", "path": r"D:\exports\screen.png"},
        "pdfs": [{"name": "Table.pdf", "path": r"D:\exports\Table.pdf"}],
    }
    fetched: list[str] = []

    def fetch_named(name: str) -> bytes | None:
        fetched.append(name)
        return b"bytes:" + name.encode()

    files = files_from_shot(payload, fetch_named=fetch_named)
    assert fetched == ["screen.png", "Table.pdf"]
    assert files[0].data == b"bytes:screen.png"
    assert files[1].ext == "pdf"


def test_capture_documents_uses_one_parse_for_png_and_pdf() -> None:
    png = b"\x89PNG\r\nhello"
    pdf = b"%PDF-1.4 table"
    payload = {
        "ok": True,
        "png": {"name": "dashboard_20261122.png", "data_b64": base64.b64encode(png).decode()},
        "pdfs": [{"name": "Оплаты.pdf", "data_b64": base64.b64encode(pdf).decode()}],
    }
    seen: list[tuple[bytes | None, bytes | None]] = []

    class Parsed:
        markdown = "# Данные дашборда\n\n## Экран\n\nкарточка\n\n## Таблица PDF\n\n| a |\n"
        warnings = ["тонкая линия"]

    def parse(*, png=None, pdf=None):
        seen.append((png, pdf))
        return Parsed()

    docs = capture_documents(payload, fetch_named=lambda _name: None, parse=parse)
    assert seen == [(png, pdf)]
    assert len(docs) == 1
    assert docs[0]["name"] == "dashboard_20261122.png"
    assert docs[0]["markdown"].startswith("# Данные дашборда")
    assert "Таблица PDF" in docs[0]["markdown"]


_CATALOG = {
    "filters": [
        {
            "name": "Month",
            "alias": "Месяц",
            "choices": [
                {"key": "2", "value": "Февраль"},
                {"key": "3", "value": "Март"},
            ],
        },
        {
            "name": "Year",
            "alias": "Год",
            "choices": [
                {"key": "2024", "value": "2024"},
                {"key": "2025", "value": "2025"},
            ],
        },
        {"name": "Region", "alias": "Регион", "choices": [{"key": "7", "value": "Минск"}]},
    ]
}


def test_phrase_keeps_february_25_and_drops_an_unnamed_filter() -> None:
    phrase = "хочу данные по февраль 25"
    raw = '{"pull": true, "filters": {"Месяц": "Февраль", "Year": "2025", "Region": "Минск"}}'
    picked = filters_from_model(_CATALOG, phrase, raw)
    assert picked == {"Month": "Февраль", "Year": "2025"}
    assert might_ask_dashboard(phrase) is True
    assert might_ask_dashboard("сделай короче") is False
    assert might_ask_dashboard("куплю смартфон") is False


def test_model_refusal_stays_a_normal_message() -> None:
    def complete(**_kwargs: object) -> str:
        return '{"pull": false, "filters": {}}'

    plan = plan_dashboard_phrase("хочу данные по февраль 25", _CATALOG, complete)
    assert plan == {"pull": False}


def test_plan_skips_the_model_when_the_sentence_is_not_about_data() -> None:
    called = False

    def complete(**_kwargs):
        nonlocal called
        called = True
        return "{}"

    assert plan_dashboard_phrase("сделай короче", _CATALOG, complete) == {"pull": False}
    assert called is False


def test_plan_opens_when_the_model_maps_the_phrase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHBOARD_SERVICE_URL", "http://127.0.0.1:8040")

    def complete(**_kwargs: object) -> str:
        return '{"pull": true, "filters": {"Month": "Февраль", "Year": "2025"}}'

    plan = plan_dashboard_phrase("хочу данные по февраль 25", _CATALOG, complete)
    assert plan["pull"] is True
    assert plan["filters"] == {"Month": "Февраль", "Year": "2025"}
    assert plan["reply"] == "Сейчас открою."
    assert "/open?filters=" in plan["viewer"]


def test_filtered_open_url_carries_the_json() -> None:
    url = filtered_open_url("http://127.0.0.1:8040", {"Month": "Февраль"})
    assert url.startswith("http://127.0.0.1:8040/open?filters=")
    assert "Февраль" in url or "%D0%A4" in url


def test_files_from_shot_refuses_a_bare_remote_path() -> None:
    payload = {"ok": True, "png": {"name": "screen.png", "path": "/only/on/his/disk.png"}}
    with pytest.raises(DashboardRemoteError) as caught:
        files_from_shot(payload, fetch_named=lambda _name: None)
    assert "той же машине" in caught.value.message
    assert caught.value.code == "no_bytes"
