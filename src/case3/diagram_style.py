"""Liber Mermaid role colors — palette-aware classDef cookbook for the LLM."""

from __future__ import annotations

import re
from typing import Any

from case3.chart_style import _PALETTES, normalize_palette_id

DIAGRAM_ROLES = ("start", "process", "decision", "ok", "warn", "data")

ROLE_LABEL_RU: dict[str, str] = {
    "start": "Старт",
    "process": "Процесс",
    "decision": "Решение",
    "ok": "Успех",
    "warn": "Риск / возврат",
    "data": "Данные / система",
}

_TEXT = "#1a2e22"

# Soft role fills derived from each chart palette (no purple).
_ROLE_MAP: dict[str, dict[str, tuple[str, str]]] = {
    # role -> (fill, stroke) overrides; missing → derived from primary/accents
    "atelier": {
        "start": ("#dce8df", "#6b8f76"),
        "process": ("#eef3ef", "#5a7a64"),
        "decision": ("#f3e6c8", "#b8893a"),
        "ok": ("#cfe6d4", "#3d7a4a"),
        "warn": ("#f0ddd8", "#a85a4a"),
        "data": ("#e4ecd0", "#4f6b14"),
    },
    "editorial": {
        "start": ("#d5e8e8", "#0F3D3E"),
        "process": ("#eef4f4", "#3D5C60"),
        "decision": ("#f7e4c8", "#E8B84A"),
        "ok": ("#c8ebe6", "#2EC4B6"),
        "warn": ("#f5d9c8", "#F07A3A"),
        "data": ("#d9e4ea", "#3D5C60"),
    },
    "ocean": {
        "start": ("#d6e8f5", "#0B4F8C"),
        "process": ("#eef5fa", "#1E8AD4"),
        "decision": ("#e0f4f8", "#2EC4E0"),
        "ok": ("#cfeef5", "#0B4F8C"),
        "warn": ("#f0ddd8", "#a85a4a"),
        "data": ("#d4eef8", "#1E8AD4"),
    },
    "sunset": {
        "start": ("#f5e0e6", "#8B2E4A"),
        "process": ("#f7eeee", "#4A6070"),
        "decision": ("#f8e8c8", "#F0C040"),
        "ok": ("#e8f0e4", "#4A6070"),
        "warn": ("#f8d4c8", "#F04545"),
        "data": ("#e4e8ec", "#4A6070"),
    },
    "mono": {
        "start": ("#e8eaed", "#1A1F28"),
        "process": ("#f1f2f4", "#3A4250"),
        "decision": ("#ece8e0", "#5C6570"),
        "ok": ("#e4e8e4", "#3A4250"),
        "warn": ("#ebe4e4", "#5C6570"),
        "data": ("#e8eaed", "#3A4250"),
    },
}

_CLASSDEF_FILL = re.compile(
    r"classDef\s+([a-zA-Z][\w-]*)\s+[^;\n]*fill:\s*(#[0-9a-fA-F]{3,8})",
    re.I,
)
_NODE_CLASS = re.compile(r":::\s*([a-zA-Z][\w-]*)")


def role_colors_for_palette(palette_id: str | None) -> dict[str, dict[str, str]]:
    """Return {role: {fill, stroke, color}} for Liber Mermaid classDef."""
    pid = normalize_palette_id(palette_id)
    if pid == "auto":
        pid = "atelier"
    table = _ROLE_MAP.get(pid) or _ROLE_MAP["atelier"]
    out: dict[str, dict[str, str]] = {}
    for role in DIAGRAM_ROLES:
        fill, stroke = table.get(role, _ROLE_MAP["atelier"][role])
        out[role] = {"fill": fill, "stroke": stroke, "color": _TEXT}
    return out


def format_diagram_color_prompt(palette_id: str | None) -> str:
    """Markdown block injected into system/repair prompts."""
    pid = normalize_palette_id(palette_id)
    if pid == "auto":
        pid = "atelier"
    label = (_PALETTES.get(pid) or {}).get("label") or pid
    colors = role_colors_for_palette(pid)
    lines = [
        f"### Liber diagram colors (palette: {label} / {pid})",
        "Assign every flowchart node a role via `:::role` + matching `classDef`.",
        "Use **these hex values** (no purple/neon):",
        "",
        "| role | fill | stroke | when |",
        "|------|------|--------|------|",
    ]
    for role in DIAGRAM_ROLES:
        c = colors[role]
        lines.append(
            f"| `{role}` | `{c['fill']}` | `{c['stroke']}` | {ROLE_LABEL_RU[role]} |"
        )
    lines.append("")
    lines.append("Every classDef must include `color:#1a2e22`.")
    lines.append("Example classDef line:")
    s = colors["start"]
    lines.append(
        f"  classDef start fill:{s['fill']},stroke:{s['stroke']},color:#1a2e22"
    )
    return "\n".join(lines)


def extract_diagram_legend(mermaid: str) -> list[dict[str, Any]]:
    """Ordered legend entries from classDef fills for roles used (or defined)."""
    text = mermaid or ""
    fills: dict[str, str] = {}
    for m in _CLASSDEF_FILL.finditer(text):
        role = m.group(1).lower()
        fills[role] = m.group(2)
    used = {m.group(1).lower() for m in _NODE_CLASS.finditer(text)}
    # Prefer roles that appear on nodes; else all classDefs in DIAGRAM_ROLES order.
    order: list[str] = []
    for role in DIAGRAM_ROLES:
        if role in used or role in fills:
            if role not in order:
                order.append(role)
    for role in fills:
        if role not in order:
            order.append(role)
    # If nodes used roles without classDef, still show with palette default atelier.
    defaults = role_colors_for_palette("atelier")
    out: list[dict[str, Any]] = []
    for role in order:
        if role not in DIAGRAM_ROLES and role not in fills:
            continue
        fill = fills.get(role) or defaults.get(role, {}).get("fill") or "#dce8df"
        out.append(
            {
                "role": role,
                "fill": fill,
                "label": ROLE_LABEL_RU.get(role, role),
            }
        )
    return out
