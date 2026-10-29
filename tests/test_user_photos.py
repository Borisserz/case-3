"""User-attached photos → usr_* figures."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from case3.user_photos import (
    UserPhotoError,
    bytes_to_png,
    ensure_user_slots_in_tex,
    materialize_user_figures,
    merge_user_figures,
    save_user_photos,
)

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_save_and_materialize(tmp_path: Path) -> None:
    figs = save_user_photos(tmp_path, [("shot.png", _PNG)], captions=["Мой кадр"])
    assert figs[0]["id"] == "usr_01"
    assert figs[0]["source"] == "upload"
    assert figs[0]["caption"] == "Мой кадр"
    dest = tmp_path / "out_figs"
    st = materialize_user_figures(figs, dest)
    assert st["usr_01"]["ok"]
    assert (dest / "usr_01.png").read_bytes().startswith(b"\x89PNG")


def test_merge_user_first() -> None:
    users = [{"id": "usr_01", "source": "upload"}]
    llm = [{"id": "fig_01"}, {"id": "fig_02"}]
    assert [f["id"] for f in merge_user_figures(llm, users, max_images=2)] == [
        "usr_01",
        "fig_01",
    ]


def test_ensure_slots() -> None:
    tex = r"\begin{document}Hi\end{document}"
    out = ensure_user_slots_in_tex(tex, [{"id": "usr_01"}])
    assert "%CASE3_FIG:usr_01%" in out
    assert out.index("%CASE3_FIG:usr_01%") < out.index(r"\end{document}")


def test_reject_too_many(tmp_path: Path) -> None:
    with pytest.raises(UserPhotoError):
        save_user_photos(
            tmp_path,
            [("a.png", _PNG), ("b.png", _PNG), ("c.png", _PNG)],
        )


def test_bytes_to_png_rejects_garbage() -> None:
    with pytest.raises(UserPhotoError):
        bytes_to_png(b"not-an-image")
