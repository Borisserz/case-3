"""Central Liber prompt loader — edit prose under ``prompt/``, not scattered .py strings.

See ``prompt/MANIFEST.md`` for id → file → caller map.
"""

from __future__ import annotations

import os
from pathlib import Path

from case3.paths import repo_root

# Single-file prompts.
PROMPT_FILES: dict[str, str] = {
    "system_slides": "system_slides.md",
    "user_tex": "user_tex.md",
    "continuation_tex": "continuation_tex.md",
    "summary_system": "summary_system.md",
    "diagram_generate": "diagram_generate.md",
    "diagram_repair": "diagram_repair.md",
    "diagram_refine": "diagram_refine.md",
}

# Multi-part prompts (joined with blank line). Edit parts under prompt/parts/.
PROMPT_COMPOSITES: dict[str, tuple[str, ...]] = {
    "system_tex": (
        "parts/tex/00_role.md",
        "parts/tex/01_output.md",
        "parts/tex/02_charts.md",
        "parts/tex/03_when_media.md",
        "parts/tex/04_diagrams.md",
        "parts/tex/05_hard_rules.md",
    ),
}


def prompt_dir(*, start: Path | None = None) -> Path:
    return repo_root(start=start) / "prompt"


def list_prompt_ids() -> list[str]:
    return sorted({*PROMPT_FILES, *PROMPT_COMPOSITES})


def resolve(name: str, *, start: Path | None = None) -> Path:
    """Return absolute path for a **single-file** prompt id (not composites)."""
    rel = PROMPT_FILES.get(name)
    if rel is None:
        if name in PROMPT_COMPOSITES:
            raise KeyError(
                f"prompt {name!r} is composite — use load() / parts under "
                f"{PROMPT_COMPOSITES[name][0]!r}"
            )
        raise KeyError(f"unknown prompt id: {name!r} (see prompt/MANIFEST.md)")
    path = prompt_dir(start=start) / rel
    if not path.is_file():
        raise FileNotFoundError(f"prompt file missing for {name!r}: {path}")
    return path


def _raw_text(name: str, *, start: Path | None = None) -> str:
    if name in PROMPT_COMPOSITES:
        root = prompt_dir(start=start)
        chunks: list[str] = []
        for rel in PROMPT_COMPOSITES[name]:
            path = root / rel
            if not path.is_file():
                raise FileNotFoundError(f"prompt part missing for {name!r}: {path}")
            chunks.append(path.read_text(encoding="utf-8").rstrip())
        return "\n\n".join(chunks) + "\n"
    return resolve(name, start=start).read_text(encoding="utf-8")


def load(name: str, *, start: Path | None = None, **vars: object) -> str:
    """Load prompt (file or composite parts) and replace ``{{KEY}}``."""
    if name not in PROMPT_FILES and name not in PROMPT_COMPOSITES:
        raise KeyError(f"unknown prompt id: {name!r} (see prompt/MANIFEST.md)")
    text = _raw_text(name, start=start)
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


def dump_enabled() -> bool:
    return os.environ.get("CASE3_DUMP_PROMPTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def dump_prompts(
    dest_dir: Path,
    *,
    system: str,
    user: str,
    continuation: str | None = None,
) -> Path | None:
    """Write final prompts under ``dest_dir/prompts_used/`` when env enabled."""
    if not dump_enabled():
        return None
    out = Path(dest_dir) / "prompts_used"
    out.mkdir(parents=True, exist_ok=True)
    (out / "system.md").write_text(system, encoding="utf-8")
    (out / "user.md").write_text(user, encoding="utf-8")
    if continuation is not None:
        (out / "continuation.md").write_text(continuation, encoding="utf-8")
    return out
