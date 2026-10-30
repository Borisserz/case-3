"""Central Liber prompt loader — edit prose under ``prompt/``, not scattered .py strings.

See ``prompt/MANIFEST.md`` for id → file → caller map.
"""

from __future__ import annotations

from pathlib import Path

from case3.paths import repo_root

# Stable ids agents / MANIFEST use. Themes & gold stay path-based (many files).
PROMPT_FILES: dict[str, str] = {
    "system_tex": "system_tex.md",
    "system_slides": "system_slides.md",
    "user_tex": "user_tex.md",
    "continuation_tex": "continuation_tex.md",
    "summary_system": "summary_system.md",
    "diagram_generate": "diagram_generate.md",
    "diagram_repair": "diagram_repair.md",
}


def prompt_dir(*, start: Path | None = None) -> Path:
    return repo_root(start=start) / "prompt"


def list_prompt_ids() -> list[str]:
    return sorted(PROMPT_FILES)


def resolve(name: str, *, start: Path | None = None) -> Path:
    """Return absolute path for a registered prompt id."""
    rel = PROMPT_FILES.get(name)
    if rel is None:
        raise KeyError(f"unknown prompt id: {name!r} (see prompt/MANIFEST.md)")
    path = prompt_dir(start=start) / rel
    if not path.is_file():
        raise FileNotFoundError(f"prompt file missing for {name!r}: {path}")
    return path


def load(name: str, *, start: Path | None = None, **vars: object) -> str:
    """Load ``prompt/<file>`` and replace ``{{KEY}}`` with ``str(vars[KEY])``."""
    text = resolve(name, start=start).read_text(encoding="utf-8")
    for key, value in vars.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def load_theme(
    kind: str,
    pack: str,
    *,
    fallback: str | None = None,
    start: Path | None = None,
) -> str:
    """Load ``prompt/themes/{kind}_{pack}.md`` (optional fallback pack)."""
    root = prompt_dir(start=start) / "themes"
    path = root / f"{kind}_{pack}.md"
    if not path.is_file() and fallback:
        path = root / f"{kind}_{fallback}.md"
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
