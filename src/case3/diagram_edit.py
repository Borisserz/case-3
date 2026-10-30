"""Edit / regenerate Liber Mermaid diagrams in an existing run (UI-only)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Protocol

from case3.diagram_repair import parse_repair_response, repair_diagrams
from case3.diagram_style import format_diagram_color_prompt
from case3.diagrams import DIAGRAM_TYPES, parse_diagrams, sanitize_mermaid
from case3.diagrams import DiagramError

log = logging.getLogger("case3.diagram_edit")

_ID_OK = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class DiagramEditError(RuntimeError):
    pass


class _Completer(Protocol):
    def complete(
        self, *, system: str, user_text: str, reasoning: str | None = None
    ) -> str: ...


def _load_fj(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "figures.json"
    if not path.is_file():
        raise DiagramEditError("figures.json missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiagramEditError(f"figures.json unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise DiagramEditError("figures.json invalid")
    return data


def _save_fj(out_dir: Path, data: dict[str, Any]) -> None:
    path = out_dir / "figures.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_meta(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "meta.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def edit_diagram_in_run(
    out_dir: Path,
    diagram_id: str,
    *,
    mermaid: str,
    title: str | None = None,
) -> dict[str, Any]:
    """Replace one diagram's mermaid/title in figures.json (sanitize)."""
    out_dir = out_dir.resolve()
    did = (diagram_id or "").strip()
    if not _ID_OK.match(did):
        raise DiagramEditError("invalid diagram id")
    from case3.run_undo import capture_before_edit

    capture_before_edit(out_dir, kind="diagram", target=did)
    fj = _load_fj(out_dir)
    diagrams = list(fj.get("diagrams") or [])
    idx = next(
        (
            i
            for i, d in enumerate(diagrams)
            if isinstance(d, dict) and str(d.get("id") or "") == did
        ),
        None,
    )
    if idx is None:
        raise DiagramEditError(f"diagram {did!r} not found")
    item = dict(diagrams[idx])
    dtype = str(item.get("type") or "flowchart").strip() or "flowchart"
    try:
        clean = sanitize_mermaid(mermaid)
    except DiagramError as exc:
        raise DiagramEditError(str(exc)) from exc
    # Re-validate via parse_diagrams
    parsed = parse_diagrams(
        [
            {
                "id": did,
                "title": (title if title is not None else item.get("title") or did),
                "type": dtype if dtype in DIAGRAM_TYPES else "flowchart",
                "mermaid": clean,
            }
        ],
        max_diagrams=1,
    )
    if not parsed:
        raise DiagramEditError("mermaid failed validation (type/header)")
    diagrams[idx] = parsed[0]
    fj["diagrams"] = diagrams
    _save_fj(out_dir, fj)
    from case3.run_undo import undo_meta

    out = dict(parsed[0])
    out["undo"] = undo_meta(out_dir)
    return out


def _load_generate_system(*, max_diagrams: int, palette: str) -> str:
    from case3.prompts import load as load_prompt

    return load_prompt(
        "diagram_generate",
        MAX_DIAGRAMS=max_diagrams,
        DIAGRAM_COLOR_TABLE=format_diagram_color_prompt(palette),
    )


def regenerate_diagrams_in_run(
    out_dir: Path,
    *,
    palette: str = "atelier",
    client: _Completer,
    skip_repair: bool = False,
) -> dict[str, Any]:
    """Full LLM regenerate of diagrams[] (+ optional repair). No TeX/PDF."""
    out_dir = out_dir.resolve()
    meta = _load_meta(out_dir)
    source_path = Path(str(meta.get("source") or ""))
    if not source_path.is_file():
        raise DiagramEditError("source file missing for regenerate")
    source = source_path.read_text(encoding="utf-8")
    intent = str(meta.get("intent") or "")
    max_d = int(meta.get("max_diagrams") or 2)
    max_d = max(1, min(max_d, 3))

    system = _load_generate_system(max_diagrams=max_d, palette=palette)
    user = (
        f"## Intent\n{intent.strip() or '(none)'}\n\n"
        f"## Source\n{source[:12000]}\n\n"
        f"{format_diagram_color_prompt(palette)}\n"
    )
    try:
        raw = client.complete(system=system, user_text=user)
    except Exception as exc:
        raise DiagramEditError(f"LLM generate failed: {exc}") from exc

    diagrams = parse_repair_response(raw or "", max_diagrams=max_d)
    if not diagrams:
        raise DiagramEditError("model returned no valid diagrams")

    repaired = False
    if not skip_repair:
        diagrams, rmeta = repair_diagrams(
            diagrams,
            source=source,
            intent=intent,
            max_diagrams=max_d,
            client=client,
            palette=palette,
        )
        repaired = bool(rmeta.get("diagrams_repaired"))

    fj = _load_fj(out_dir)
    fj["diagrams_draft"] = fj.get("diagrams")
    fj["diagrams"] = diagrams
    _save_fj(out_dir, fj)

    meta_path = out_dir / "meta.json"
    if meta_path.is_file():
        meta["diagrams_planned"] = [d["id"] for d in diagrams]
        meta["diagrams_ok"] = len(diagrams)
        meta["diagrams_repaired"] = repaired
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "diagrams": diagrams,
        "diagrams_repaired": repaired,
        "diagrams_ok": len(diagrams),
    }
