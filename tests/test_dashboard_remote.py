"""Colleague /shot JSON → file bytes. Paths on his disk are not enough."""

from __future__ import annotations

import base64

import pytest

from case3.dashboard_remote import (
    DashboardRemoteError,
    capture_documents,
    files_from_shot,
    filters_from_model,
    finish_dashboard_phrase,
    might_ask_dashboard,
    open_payload,
    plan_dashboard_phrase,
    read_filter_catalog,
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


_OPEN_CATALOG = {
    "mrt": "last.mrt",
    "filters": [
        {
            "name": "trendtype",
            "choices": [
                {"key": "cumulative", "value": "накопительный"},
                {"key": "period", "value": "за период"},
            ],
        },
        {
            "name": "typenum",
            "choices": [
                {"key": "1", "value": "тыс."},
                {"key": "1000000", "value": "млн."},
            ],
        },
        {
            "name": "month",
            "choices": [{"key": "2", "value": "Февраль"}],
        },
        {
            "name": "year",
            "choices": [{"key": "2025", "value": "2025"}],
        },
        {
            "name": "vtypevd",
            "choices": [{"key": "0000000", "value": "все"}],
        },
    ],
}


def test_phrase_keeps_february_25_and_drops_an_unnamed_filter() -> None:
    phrase = "хочу данные по февраль 25"
    raw = '{"pull": true, "filters": {"Месяц": "Февраль", "Year": "2025", "Region": "Минск"}}'
    picked = filters_from_model(_CATALOG, phrase, raw)
    assert picked == {"Month": 2, "Year": 2025}
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
    assert plan["filters"] == {"Month": 2, "Year": 2025}
    assert plan["reply"] == "Сейчас открою."
    assert plan["viewer"].endswith("/viewer")


def test_open_payload_uses_choice_keys() -> None:
    phrase = "накопительный итог, тыс., февраль 2025, все виды"
    raw = (
        '{"pull": true, "filters": {'
        '"trendtype": "накопительный", "typenum": "тыс.", '
        '"month": "Февраль", "year": "2025", "vtypevd": "все"}}'
    )
    picked = filters_from_model(_OPEN_CATALOG, phrase, raw)
    assert picked == {
        "trendtype": "cumulative",
        "typenum": 1,
        "month": 2,
        "year": 2025,
        "vtypevd": "0000000",
    }
    assert open_payload(picked) == {"filters": picked}


class _Poster:
    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.posts: list[tuple[str, dict]] = []

    def post(self, url: str, json: dict | None = None):
        self.posts.append((url, json or {}))
        return type("Response", (), {"status_code": self.status})()


def test_finish_posts_the_open_body_then_points_at_the_viewer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHBOARD_SERVICE_URL", "http://127.0.0.1:8040")
    poster = _Poster()
    plan = finish_dashboard_phrase(
        {
            "pull": True,
            "filters": {"month": 2, "vtypevd": "0000000"},
            "reply": "Сейчас открою.",
            "viewer": "http://127.0.0.1:8040/open?filters=%7B%7D",
        },
        "http://127.0.0.1:8040",
        poster,
    )
    assert poster.posts == [
        (
            "http://127.0.0.1:8040/open",
            {"filters": {"month": 2, "vtypevd": "0000000"}},
        )
    ]
    assert plan["viewer"] == "http://127.0.0.1:8040/viewer"


def test_finish_does_not_post_when_the_phrase_is_not_a_pull() -> None:
    poster = _Poster()
    plan = finish_dashboard_phrase({"pull": False}, "http://127.0.0.1:8040", poster)
    assert poster.posts == []
    assert plan == {"pull": False}


def test_read_filter_catalog_uses_the_local_file(tmp_path, monkeypatch) -> None:
    catalog = tmp_path / "dashboard_filters.json"
    catalog.write_text(
        '{"filters": [{"name": "month"}], "mrt": "last.mrt"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("DASHBOARD_FILTERS_FILE", str(catalog))
    assert read_filter_catalog()["mrt"] == "last.mrt"
    monkeypatch.setenv("DASHBOARD_FILTERS_FILE", str(tmp_path / "missing.json"))
    assert read_filter_catalog() is None


def test_files_from_shot_refuses_a_bare_remote_path() -> None:
    payload = {"ok": True, "png": {"name": "screen.png", "path": "/only/on/his/disk.png"}}
    with pytest.raises(DashboardRemoteError) as caught:
        files_from_shot(payload, fetch_named=lambda _name: None)
    assert "той же машине" in caught.value.message
    assert caught.value.code == "no_bytes"
