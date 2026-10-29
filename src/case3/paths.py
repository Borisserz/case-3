"""Repo root resolution — one place instead of scattered ``parents[2]``."""

from __future__ import annotations

from pathlib import Path


def repo_root(*, start: Path | None = None) -> Path:
    """Return case-3 repo root (directory that contains ``Dockerfile``).

    Falls back to ``Path.cwd()`` when the sentinel is missing (editable installs
    / odd layouts).
    """
    here = (start or Path(__file__)).resolve()
    for cand in [here, *here.parents]:
        if (cand / "Dockerfile").is_file() and (cand / "src" / "case3").is_dir():
            return cand
    # Legacy depth used by api.py / cli when Dockerfile check was shallow.
    if len(here.parents) >= 2:
        shallow = here.parents[2] if here.name != "paths.py" else Path(__file__).resolve().parents[2]
        if (shallow / "Dockerfile").is_file():
            return shallow
    return Path.cwd()
