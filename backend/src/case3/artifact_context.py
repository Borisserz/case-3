"""Deterministic artifact target resolution for GCP Phase B."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from case3.chat_memory import load_chain_dirs
from case3.context_packet import ArtifactTarget

_MEDIA_ID = re.compile(r"\b(?:cht|dia|usr)_[A-Za-z0-9_]+\b", re.IGNORECASE)
_HEADING = re.compile(
    r"\\(?:sub)*section\*?\{([^{}\n]+)\}",
    re.IGNORECASE,
)
_CHART_OPS = frozenset(
    {
        "retype_chart",
        "retype_charts",
        "recolor_charts",
        "recolor_hue",
        "fade_chart",
        "filter_chart",
        "restyle_chart",
    }
)
_SECTION_OPS = frozenset(
    {
        "rewrite",
        "rename_heading",
        "delete_section",
        "add_paragraph",
    }
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _target(run_id: str, locator: str, label: str) -> ArtifactTarget:
    return ArtifactTarget(
        artifact_id=f"artifact:{run_id}:{locator}",
        label=label,
        number_evidence=False,
    )


def parse_artifact_target_id(artifact_id: str) -> tuple[str, str] | None:
    """``artifact:{run_id}:{locator}`` from :func:`resolve_artifact_targets`."""
    raw = str(artifact_id or "").strip()
    if not raw.startswith("artifact:"):
        return None
    body = raw[len("artifact:") :]
    run_id, _, locator = body.partition(":")
    if not run_id or not locator:
        return None
    return run_id, locator


def _clean_label(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _media_catalog(out_dir: Path, meta: dict[str, Any]) -> list[dict[str, str]]:
    """Return media in persisted order, with filesystem fallbacks."""
    payload = _read_json(out_dir / "figures.json")
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(raw: object, kind: str) -> None:
        if not isinstance(raw, dict):
            return
        media_id = _clean_label(raw.get("id"))
        if not _MEDIA_ID.fullmatch(media_id) or media_id.casefold() in seen:
            return
        seen.add(media_id.casefold())
        if kind == "diagram":
            title = _clean_label(raw.get("title") or raw.get("caption"))
        else:
            title = _clean_label(raw.get("caption") or raw.get("title"))
        found.append({"id": media_id, "kind": kind, "title": title})

    for raw in payload.get("charts") or []:
        add(raw, "chart")
    for raw in payload.get("diagrams") or []:
        add(raw, "diagram")
    for raw in payload.get("figures") or []:
        figure_id = str(raw.get("id") or "") if isinstance(raw, dict) else ""
        add(raw, "photo" if figure_id.startswith("usr_") else "figure")

    planned = meta.get("charts_planned")
    if isinstance(planned, list):
        for chart_id in planned:
            add({"id": chart_id}, "chart")

    figures_dir = out_dir / "figures"
    if figures_dir.is_dir():
        for pattern, kind in (
            ("cht_*.*", "chart"),
            ("dia_*.*", "diagram"),
            ("usr_*.*", "photo"),
        ):
            for path in sorted(figures_dir.glob(pattern)):
                add({"id": path.stem}, kind)
    return found


def _media_label(item: dict[str, str]) -> str:
    names = {
        "chart": "График",
        "diagram": "Схема",
        "photo": "Фото",
        "figure": "Иллюстрация",
    }
    label = f"{names.get(item['kind'], 'Артефакт')} {item['id']}"
    if item.get("title"):
        label += f" — {item['title']}"
    return label


def _explicit_media_id(act: object) -> str:
    for field in ("section", "title", "chart", "say"):
        match = _MEDIA_ID.search(str(getattr(act, field, "") or ""))
        if match:
            return match.group(0)
    return ""


def _resolve_explicit_media(
    rows: list[tuple[str, Path, dict[str, Any]]],
    media_id: str,
) -> list[ArtifactTarget]:
    needle = media_id.casefold()
    for run_id, out_dir, meta in reversed(rows):
        matches = [
            item
            for item in _media_catalog(out_dir, meta)
            if item["id"].casefold() == needle
        ]
        if len(matches) == 1:
            item = matches[0]
            return [_target(run_id, item["id"], _media_label(item))]
        if len(matches) > 1:
            return []
    return []


def _is_deck(out_dir: Path, meta: dict[str, Any]) -> bool:
    return bool(
        str(meta.get("output_mode") or "").strip().lower() == "presentation"
        or str(meta.get("slides_status") or "").strip().lower()
        in {"ok", "running", "error"}
        or (out_dir / "slides" / "deck.json").is_file()
    )


def _resolve_slide(
    rows: list[tuple[str, Path, dict[str, Any]]],
    index: int,
) -> list[ArtifactTarget]:
    if index < 1:
        return []
    for run_id, out_dir, meta in reversed(rows):
        if not _is_deck(out_dir, meta):
            continue
        deck_path = out_dir / "slides" / "deck.json"
        if deck_path.is_file():
            slides = _read_json(deck_path).get("slides")
            if not isinstance(slides, list) or index > len(slides):
                return []
            raw_slide = slides[index - 1]
            title = (
                _clean_label(raw_slide.get("title"))
                if isinstance(raw_slide, dict)
                else ""
            )
        else:
            title = ""
        label = f"Слайд {index}"
        if title:
            label += f" — {title}"
        return [_target(run_id, f"slide:{index}", label)]
    return []


def _heading_key(value: str) -> str:
    plain = re.sub(r"\\[A-Za-z]+\*?", " ", value or "")
    plain = plain.replace("ё", "е").replace("Ё", "Е").casefold()
    return " ".join(re.findall(r"[a-zа-я0-9]+", plain))


def _headings(out_dir: Path) -> list[str]:
    found: list[str] = []
    for tex_path in sorted(out_dir.glob("*.tex")):
        try:
            tex = tex_path.read_text(encoding="utf-8")
        except OSError:
            continue
        found.extend(_clean_label(match.group(1)) for match in _HEADING.finditer(tex))
    return list(dict.fromkeys(title for title in found if title))


def _resolve_section(
    rows: list[tuple[str, Path, dict[str, Any]]],
    requested: str,
) -> list[ArtifactTarget]:
    needle = _heading_key(requested)
    if not needle:
        return []
    for run_id, out_dir, _meta in reversed(rows):
        headings = _headings(out_dir)
        exact = [title for title in headings if _heading_key(title) == needle]
        if len(exact) == 1:
            title = exact[0]
            return [_target(run_id, f"section:{title}", f"Раздел «{title}»")]
        if len(exact) > 1:
            return []
    return []


def _resolve_chart(
    rows: list[tuple[str, Path, dict[str, Any]]],
    index: int,
) -> list[ArtifactTarget]:
    for run_id, out_dir, meta in reversed(rows):
        charts = [
            item
            for item in _media_catalog(out_dir, meta)
            if item["kind"] == "chart"
        ]
        if not charts:
            continue
        if index:
            if index > len(charts):
                return []
            item = charts[index - 1]
        elif len(charts) == 1:
            item = charts[0]
        else:
            return []
        return [_target(run_id, item["id"], _media_label(item))]
    return []


def _resolve_single_kind(
    rows: list[tuple[str, Path, dict[str, Any]]],
    kind: str,
) -> list[ArtifactTarget]:
    for run_id, out_dir, meta in reversed(rows):
        items = [
            item
            for item in _media_catalog(out_dir, meta)
            if item["kind"] == kind
        ]
        if not items:
            continue
        if len(items) != 1:
            return []
        item = items[0]
        return [_target(run_id, item["id"], _media_label(item))]
    return []


def resolve_artifact_targets(
    *,
    plan: object,
    root: Path,
    prior_run_id: str | None,
) -> list[ArtifactTarget]:
    """Resolve the exact artifact slice addressed by a routed edit plan.

    An empty list means the locator is absent, missing, or ambiguous. The
    caller owns the clarification wording.
    """
    run_id = (prior_run_id or "").strip()
    act = getattr(plan, "edit_act", None)
    if not run_id or act is None:
        return []
    rows = load_chain_dirs(Path(root), run_id)
    if not rows:
        return []

    media_id = _explicit_media_id(act)
    if media_id:
        return _resolve_explicit_media(rows, media_id)

    slide = int(getattr(act, "slide", 0) or 0)
    if slide:
        return _resolve_slide(rows, slide)

    op = str(getattr(act, "op", "") or "")
    section = _clean_label(getattr(act, "section", ""))
    if section and op in _SECTION_OPS:
        return _resolve_section(rows, section)

    if op in _CHART_OPS:
        return _resolve_chart(rows, int(getattr(act, "chart_at", 0) or 0))
    if op == "refine_diagram":
        return _resolve_single_kind(rows, "diagram")
    if op == "edit_photo":
        return _resolve_single_kind(rows, "photo")
    return []
