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
    # Soft fills aligned with chart_style presets (Okabe–Ito / Tol / Tableau 10).
    "atelier": {
        "start": ("#d4ebe8", "#004D47"),
        "process": ("#eef6f5", "#009988"),
        "decision": ("#f8e6d8", "#EE7733"),
        "ok": ("#cfe8e4", "#009988"),
        "warn": ("#f5d8d0", "#CC3311"),
        "data": ("#d6e8f4", "#0077BB"),
    },
    "editorial": {
        "start": ("#dce6f0", "#4E79A7"),
        "process": ("#eef2f6", "#76B7B2"),
        "decision": ("#f8e8d4", "#F28E2B"),
        "ok": ("#d8ebe4", "#59A14F"),
        "warn": ("#f5d8d4", "#E15759"),
        "data": ("#e4ebe8", "#76B7B2"),
    },
    "ocean": {
        "start": ("#d6eaf5", "#0072B2"),
        "process": ("#eef6fb", "#56B4E9"),
        "decision": ("#f5ecd4", "#E69F00"),
        "ok": ("#d4ebe4", "#009E73"),
        "warn": ("#f5ddd0", "#D55E00"),
        "data": ("#dceef8", "#56B4E9"),
    },
    "sunset": {
        "start": ("#f8e0e4", "#EE6677"),
        "process": ("#eef2f6", "#4477AA"),
        "decision": ("#f5efd4", "#CCBB44"),
        "ok": ("#dce8dc", "#228833"),
        "warn": ("#f5d4d8", "#EE6677"),
        "data": ("#e0f0f5", "#66CCEE"),
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
