"""Decode Image API string payloads without network."""

from __future__ import annotations

import base64
from pathlib import Path

from case3.image_api import ImageApiConfig, decode_image_string

# 1x1 PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _cfg() -> ImageApiConfig:
    return ImageApiConfig(
        base_url="http://192.168.4.101:8000",
        timeout_s=5,
        max_images=2,
        width=1024,
        height=1024,
        steps=4,
        guidance=3.0,
        seed=0,
        allow_url_download=False,
    )


def test_decode_raw_base64(tmp_path: Path) -> None:
    dest = tmp_path / "a.png"
    decode_image_string(base64.b64encode(_PNG).decode(), cfg=_cfg(), dest=dest)
    assert dest.read_bytes().startswith(b"\x89PNG")


def test_decode_data_url(tmp_path: Path) -> None:
    dest = tmp_path / "b.png"
    b64 = base64.b64encode(_PNG).decode()
    decode_image_string(f"data:image/png;base64,{b64}", cfg=_cfg(), dest=dest)
    assert dest.read_bytes() == _PNG


def test_decode_json_string_wrapper(tmp_path: Path) -> None:
    dest = tmp_path / "c.png"
    # FastAPI Response[str] often arrives already unquoted via json.loads
    decode_image_string({"image": base64.b64encode(_PNG).decode()}, cfg=_cfg(), dest=dest)
    assert dest.is_file()
