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
        "start": ("#D4EBE8", "#1F6F66"),
        "process": ("#E7F0D8", "#6B7F45"),
        "decision": ("#F8E6D8", "#C47A3A"),
        "ok": ("#D7EDD9", "#2F7D4A"),
        "warn": ("#F6DDD6", "#C45A48"),
        "data": ("#D6E4F2", "#3E6F99"),
    },
    "editorial": {
        "start": ("#DCE6F0", "#4E79A7"),
        "process": ("#E4F2EF", "#76B7B2"),
        "decision": ("#F8E8D4", "#F28E2B"),
        "ok": ("#D8EBE4", "#59A14F"),
        "warn": ("#F5D8D4", "#E15759"),
        "data": ("#E4EEF6", "#3D6490"),
    },
    "ocean": {
        "start": ("#D6EAF5", "#0072B2"),
        "process": ("#E7F3EA", "#2E8B6A"),
        "decision": ("#F5ECD4", "#E69F00"),
        "ok": ("#D4EBE4", "#009E73"),
        "warn": ("#F5DDD0", "#D55E00"),
        "data": ("#DCEEF8", "#3A6F9A"),
    },
    "sunset": {
        "start": ("#F8E0E4", "#9A4A58"),
        "process": ("#EEF2F6", "#4477AA"),
        "decision": ("#F5EFD4", "#A89830"),
        "ok": ("#DCE8DC", "#228833"),
        "warn": ("#F5D4D8", "#EE6677"),
        "data": ("#E0F0F5", "#3A9AAD"),
    },
    "mono": {
        "start": ("#E8EAED", "#1A1F28"),
        "process": ("#F1F2F4", "#3A4250"),
        "decision": ("#ECE8E0", "#8B7355"),
        "ok": ("#E4E8E4", "#2F4A38"),
        "warn": ("#EBE4E4", "#6B4038"),
        "data": ("#E8EAED", "#5C6570"),
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


_CLASSDEF_NAME = re.compile(r"classDef\s+([A-Za-z][\w-]*)", re.I)


def ensure_role_classdefs(mermaid: str, palette: str | None = None) -> str:
    """Add missing role classDefs so a flowchart stays colorful on the slide."""
    text = mermaid or ""
    head = text.lstrip().splitlines()[:1]
    first = head[0].lower() if head else ""
    if not first.startswith("flowchart") and not first.startswith("graph"):
        return text
    used = {m.group(1).lower() for m in _NODE_CLASS.finditer(text)}
    defined = {m.group(1).lower() for m in _CLASSDEF_NAME.finditer(text)}
    missing = [role for role in DIAGRAM_ROLES if role in used and role not in defined]
    if not missing:
        return text
    colors = role_colors_for_palette(palette)
    lines = [
        (
            f"    classDef {role} fill:{colors[role]['fill']},"
            f"stroke:{colors[role]['stroke']},color:{colors[role]['color']}"
        )
        for role in missing
    ]
    return text.rstrip() + "\n" + "\n".join(lines) + "\n"


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
