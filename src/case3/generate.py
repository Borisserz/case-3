"""Generate .tex (+ optional Kandinsky figure prompts) from intent ∥ source."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from case3.gold_select import format_gold_appendix, select_gold
from case3.llm_client import LLMClient, LLMConfig
from case3.parse_output import parse_model_output

log = logging.getLogger("case3.generate")

DEFAULT_INTENT = (
    "Оформи документ как понятный русскоязычный отчёт: "
    "структура, таблицы где уместны числа, без лишней воды."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def max_images_from_env() -> int:
    try:
        return max(0, int(os.environ.get("KANDINSKY_MAX_IMAGES", "0") or "0"))
    except ValueError:
        return 0


def load_system_prompt(*, max_images: int) -> str:
    path = _repo_root() / "prompts" / "system_tex.md"
    text = path.read_text(encoding="utf-8")
    return text.replace("{{MAX_IMAGES}}", str(max_images))


def resolve_text_file(path: Path) -> Path:
    path = path.resolve()
    if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
        return path
    raise FileNotFoundError(f"expected .txt/.md file: {path}")


def build_user_prompt(*, intent: str, source: str, max_images: int) -> str:
    lines = [
        "## Intent",
        intent.strip() or DEFAULT_INTENT,
        "",
        f"## Limits",
        f"- max_images (Kandinsky slots): {max_images}",
        "- Follow system output format exactly (latex fence, then json fence).",
        "",
        "## Source",
        "<<<SOURCE",
        source.strip(),
        "SOURCE",
    ]
    return "\n".join(lines)


def generate_document(
    source: Path,
    *,
    out_tex: Path,
    intent: str | None = None,
    gold_dir: Path | None = None,
    client: LLMClient | None = None,
    dry_run: bool = False,
) -> tuple[Path, list[dict[str, Any]]]:
    """Returns (tex_path, figures list)."""
    text_path = resolve_text_file(source)
    source_text = text_path.read_text(encoding="utf-8")
    stem = text_path.stem
    root = _repo_root()
    gold_dir = gold_dir or (root / "gold")
    intent_text = (intent or DEFAULT_INTENT).strip()
    max_images = max_images_from_env()

    gold_paths = select_gold(gold_dir, intent_text, max_items=3, max_images=max_images)
    system = load_system_prompt(max_images=max_images) + format_gold_appendix(gold_paths)
    user = build_user_prompt(intent=intent_text, source=source_text, max_images=max_images)
    log.info(
        "source=%s intent_len=%d gold=%s max_images=%d",
        text_path.name,
        len(intent_text),
        [p.name for p in gold_paths],
        max_images,
    )

    out_tex.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        stub = Path(__file__).resolve().parent / "templates" / "article_skeleton.tex"
        body = stub.read_text(encoding="utf-8")
        body = body.replace("%%CONTENT%%", source_text[:2000].replace("\\", "/"))
        out_tex.write_text(body, encoding="utf-8")
        (out_tex.parent / "figures.json").write_text('{"figures":[]}\n', encoding="utf-8")
        log.info("dry-run wrote %s", out_tex)
        return out_tex, []

    cfg = LLMConfig.from_env()
    llm = client or LLMClient(cfg)
    raw = llm.complete(system=system, user_text=user)
    (out_tex.parent / f"{stem}.raw_model.txt").write_text(raw, encoding="utf-8")

    tex, figures = parse_model_output(raw, max_images=max_images)
    out_tex.write_text(tex, encoding="utf-8")
    (out_tex.parent / "figures.json").write_text(
        json.dumps({"figures": figures}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log.info("wrote %s (%d chars, %d figures)", out_tex, len(tex), len(figures))
    return out_tex, figures


# backward name
def generate_tex(*args, **kwargs):
    path, _figs = generate_document(*args, **kwargs)
    return path
