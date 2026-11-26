"""Office Image API: JSON bodies from the live /docs schema."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from case3.image_api import ImageApiConfig, edit_png, generate_png

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
_JOB_KEYS = {"prompt", "width", "height", "steps", "guidance", "seed"}


def _cfg() -> ImageApiConfig:
    return ImageApiConfig(
        base_url="http://192.168.4.101:8000",
        timeout_s=5,
        max_images=2,
        width=1024,
        height=1024,
        steps=4,
        guidance=0,
        seed=0,
        allow_url_download=False,
    )


class _Resp:
    def __init__(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.status_code = code
        self.content = body
        self.headers = {"content-type": ctype}
        self.text = body.decode("utf-8", errors="replace")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=MagicMock(), response=MagicMock(status_code=self.status_code)
            )


def _client(handler):
    client = MagicMock()
    client.__enter__ = lambda s: s
    client.__exit__ = MagicMock(return_value=False)
    client.post = handler
    return client


def test_generate_posts_the_documented_json(tmp_path: Path) -> None:
    dest = tmp_path / "out.png"
    calls: list[dict] = []
    payload = json.dumps(base64.b64encode(_PNG).decode("ascii")).encode()

    def _post(url: str, **kwargs):
        calls.append({"url": url, "json": kwargs.get("json"), "files": kwargs.get("files"), "data": kwargs.get("data")})
        return _Resp(200, payload)

    with patch("case3.image_api.httpx.Client", return_value=_client(_post)):
        generate_png(_cfg(), "a red car", dest)

    assert dest.read_bytes().startswith(b"\x89PNG")
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/generate")
    assert calls[0]["files"] is None
    assert calls[0]["data"] is None
    body = calls[0]["json"]
    assert set(body) == _JOB_KEYS
    assert body["width"] == 1024
    assert body["height"] == 1024
    assert body["steps"] == 4
    assert body["guidance"] == 0
    assert body["seed"] == 0
    assert "red car" in body["prompt"]


def test_edit_posts_the_saved_png_as_a_file(tmp_path: Path) -> None:
    src = tmp_path / "fig.png"
    dest = tmp_path / "out.png"
    src.write_bytes(_PNG)
    calls: list[dict] = []
    payload = json.dumps(base64.b64encode(_PNG).decode("ascii")).encode()

    def _post(url: str, **kwargs):
        calls.append({"url": url, "json": kwargs.get("json"), "files": kwargs.get("files"), "data": kwargs.get("data")})
        return _Resp(200, payload)

    with patch("case3.image_api.httpx.Client", return_value=_client(_post)):
        edit_png(_cfg(), "make the car blue", src, dest)

    assert dest.read_bytes().startswith(b"\x89PNG")
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/edit")
    assert calls[0]["json"] is None
    upload = calls[0]["files"]["image"]
    assert upload[0] == "fig.png"
    assert upload[1] == _PNG
    assert upload[2] == "image/png"
    form = calls[0]["data"]
    assert set(form) == _JOB_KEYS
    assert "blue" in form["prompt"]
    assert form["width"] == "1024"
    assert form["guidance"] == "0"


def test_rejected_body_is_retried_with_prompt_only(tmp_path: Path) -> None:
    dest = tmp_path / "out.png"
    calls: list[dict] = []
    payload = json.dumps(base64.b64encode(_PNG).decode("ascii")).encode()
    detail = b'{"detail":[{"loc":["body","guidance"],"msg":"ensure this value is less than or equal to 1"}]}'

    def _post(url: str, **kwargs):
        calls.append({"json": kwargs.get("json"), "data": kwargs.get("data")})
        if len(calls) == 1:
            return _Resp(422, detail)
        return _Resp(200, payload)

    with patch("case3.image_api.httpx.Client", return_value=_client(_post)):
        generate_png(_cfg(), "a red car", dest)

    assert dest.read_bytes().startswith(b"\x89PNG")
    assert len(calls) == 2
    assert set(calls[0]["json"]) == _JOB_KEYS
    assert set(calls[1]["json"]) == {"prompt"}
    assert "guidance" not in calls[1]["json"]
    assert "red car" in calls[1]["json"]["prompt"]
