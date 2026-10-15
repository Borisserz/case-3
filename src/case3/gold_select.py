"""Pick 2–3 gold exemplars by tag overlap with intent text."""

from __future__ import annotations

import re
from pathlib import Path

# Minimal YAML-ish parser for our flat index (no PyYAML dependency).
_TAG_SPLIT = re.compile(r"[,\s]+")


def _parse_index(text: str) -> list[dict]:
    items: list[dict] = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- id:"):
            if cur:
                items.append(cur)
            cur = {"id": line.split(":", 1)[1].strip(), "file": "", "tags": []}
        elif cur is not None and line.startswith("file:"):
            cur["file"] = line.split(":", 1)[1].strip()
        elif cur is not None and line.startswith("tags:"):
            inside = line.split(":", 1)[1].strip()
            inside = inside.strip("[]")
            cur["tags"] = [t.strip() for t in _TAG_SPLIT.split(inside) if t.strip()]
    if cur:
        items.append(cur)
    return items


def intent_tokens(intent: str) -> set[str]:
    low = (intent or "").lower()
    tokens = set(re.findall(r"[a-zа-яё0-9_]+", low, flags=re.I))
    # synonym boosts
    mapping = {
        "таблиц": "table",
        "таблица": "table",
        "таблицу": "table",
        "таблицы": "table",
        "список": "list",
        "списки": "list",
        "разделы": "sections",
        "отчёт": "report",
        "отчет": "report",
        "кратко": "short",
        "заметка": "memo",
        "картинк": "image",
        "рисунк": "figure",
        "фото": "photo",
        "иллюстрац": "illustration",
        "без": "no_table",  # weak; refined below
    }
    for ru, en in mapping.items():
        if ru in low:
            tokens.add(en)
    if "без таблиц" in low or "без таблицы" in low:
        tokens.add("no_table")
        tokens.discard("table")
    if not tokens:
        tokens.add("default")
    return tokens


def select_gold(
    gold_dir: Path,
    intent: str,
    *,
    max_items: int = 3,
    max_images: int = 0,
) -> list[Path]:
    index_path = gold_dir / "index.yaml"
    if not index_path.is_file():
        return sorted(gold_dir.glob("*.tex"))[:max_items]

    items = _parse_index(index_path.read_text(encoding="utf-8"))
    tokens = intent_tokens(intent)
    scored: list[tuple[int, dict]] = []
    for it in items:
        tags = set(it.get("tags") or [])
        if it.get("id") == "image_slot" and max_images <= 0:
            continue
        score = len(tokens & tags)
        if "default" in tags:
            score += 1
        if score > 0:
            scored.append((score, it))
    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    chosen = scored[:max_items] if scored else [(1, items[0])] if items else []

    paths: list[Path] = []
    for _, it in chosen:
        p = gold_dir / it["file"]
        if p.is_file():
            paths.append(p)
    return paths


def format_gold_appendix(paths: list[Path]) -> str:
    if not paths:
        return ""
    chunks = []
    for p in paths:
        body = p.read_text(encoding="utf-8").strip()
        chunks.append(f"### {p.name}\n```latex\n{body}\n```\n")
    return "\n\n## Gold examples (follow style; do not copy unrelated content)\n\n" + "\n".join(chunks)
