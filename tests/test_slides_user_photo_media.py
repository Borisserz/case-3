"""Attached usr_* photos are deck-eligible media (PPTX / twin)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from case3.slides_media import collect_run_media
from case3.user_photos import save_user_photos, materialize_user_figures

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_collect_run_media_includes_usr(tmp_path: Path) -> None:
    out = tmp_path / "run"
    figs = out / "figures"
    figs.mkdir(parents=True)
    users = save_user_photos(tmp_path / "up", [("a.png", _PNG)], captions=["Кадр"])
    materialize_user_figures(users, figs)
    (out / "figures.json").write_text(
        json.dumps({"figures": users, "charts": []}), encoding="utf-8"
    )
    meta = {"figures_planned": ["usr_01"], "status": "ok"}
    _charts, figure_ids, _dias, png_by_id, _specs = collect_run_media(out, meta)
    assert "usr_01" in figure_ids
    assert "usr_01" in png_by_id
    assert png_by_id["usr_01"].is_file()
