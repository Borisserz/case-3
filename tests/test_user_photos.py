"""User-attached photos → usr_* figures."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from case3.user_photos import (
    UserPhotoError,
    bytes_to_png,
    captions_from_intent,
    clip_photo_files,
    ensure_user_slots_in_tex,
    materialize_user_figures,
    merge_user_figures,
    save_user_photos,
    split_image_budget,
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


def test_ensure_slots_after_first_section() -> None:
    """Fallback must land near body prose, not only as appendix before \\end{document}."""
    tex = (
        r"\begin{document}"
        r"\maketitle"
        r"\section{Обзор}"
        r"Текст про продукт."
        r"\section{Вывод}"
        r"Итог."
        r"\end{document}"
    )
    out = ensure_user_slots_in_tex(tex, [{"id": "usr_01"}])
    assert "%CASE3_FIG:usr_01%" in out
    # Prefer first section body over trailing dump before \end{document}
    assert out.index("%CASE3_FIG:usr_01%") < out.index(r"\section{Вывод}")
    assert out.index(r"\section{Обзор}") < out.index("%CASE3_FIG:usr_01%")


def test_five_user_photos_are_kept(tmp_path: Path) -> None:
    figs = save_user_photos(tmp_path, [(f"p{i}.png", _PNG) for i in range(5)])
    assert [f["id"] for f in figs] == [f"usr_{i:02d}" for i in range(1, 6)]


def test_clip_photo_files_keeps_five() -> None:
    files = [f"p{i}" for i in range(6)]
    assert clip_photo_files(files) == files[:5]


def test_captions_from_numbered_photo_list() -> None:
    intent = (
        "сделай презентацию и вставь фото\n"
        "1. файл логотип платформы\n"
        "2. файл логотип организации\n"
        "3. 4. 5. фотки интерфейс\n"
        "\n"
        "Требования:\n"
        "- не больше 8 графиков\n"
    )
    caps = captions_from_intent(intent, 5)
    assert caps == [
        "логотип платформы",
        "логотип организации",
        "фотки интерфейс",
        "фотки интерфейс",
        "фотки интерфейс",
    ]


def test_captions_include_schema_lines() -> None:
    intent = "1. схема поступления\n2. логотип платформы"
    assert captions_from_intent(intent, 2) == [
        "схема поступления",
        "логотип платформы",
    ]


def test_captions_ignore_numbered_source_without_photo_words() -> None:
    intent = "1. Выручка выросла\n2. Брак 3.4%\n3. План на квартал"
    assert captions_from_intent(intent, 3) == []


def test_presentation_with_uploads_does_not_invent_figures() -> None:
    llm, merge = split_image_budget(5, 2, mode="presentation")
    assert llm == 0
    assert merge == 2
    llm_r, merge_r = split_image_budget(5, 2, mode="report")
    assert (llm_r, merge_r) == (3, 5)


def test_reject_too_many(tmp_path: Path) -> None:
    with pytest.raises(UserPhotoError, match="5"):
        save_user_photos(
            tmp_path,
            [("a.png", _PNG)] * 6,
        )


def test_bytes_to_png_rejects_garbage() -> None:
    with pytest.raises(UserPhotoError):
        bytes_to_png(b"not-an-image")
