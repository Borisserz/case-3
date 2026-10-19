"""Named chart palettes for UI → Intent → Chart.js HTML."""

from __future__ import annotations

from typing import Any

# Preset ids used in Form/UI. ``auto`` = model picks one preset for the doc.
PALETTE_IDS = ("auto", "editorial", "ocean", "sunset", "mono")

# Concrete ink sets (no purple/indigo slop).
_PALETTES: dict[str, dict[str, Any]] = {
    "editorial": {
        "label": "Editorial",
        "primary": "#0F3D3E",
        "accents": ["#E85D04", "#2A9D8F", "#E9C46A", "#264653"],
        "muted": "#94A3B8",
        "area": "rgba(42,157,143,0.18)",
        "grid": "rgba(15,61,62,0.08)",
    },
    "ocean": {
        "label": "Ocean",
        "primary": "#023E8A",
        "accents": ["#0077B6", "#00B4D8", "#48CAE4", "#90E0EF"],
        "muted": "#8B9AAB",
        "area": "rgba(0,180,216,0.18)",
        "grid": "rgba(2,62,138,0.10)",
    },
    "sunset": {
        "label": "Sunset",
        "primary": "#6D2E46",
        "accents": ["#D62828", "#F77F00", "#FCBF49", "#003049"],
        "muted": "#A3A3A3",
        "area": "rgba(247,127,0,0.16)",
        "grid": "rgba(109,46,70,0.10)",
    },
    "mono": {
        "label": "Mono",
        "primary": "#111827",
        "accents": ["#111827", "#374151", "#6B7280", "#9CA3AF"],
        "muted": "#9CA3AF",
        "area": "rgba(17,24,39,0.12)",
        "grid": "rgba(17,24,39,0.08)",
    },
}


def normalize_palette_id(raw: str | None) -> str:
    key = (raw or "editorial").strip().lower()
    if key in PALETTE_IDS:
        return key
    return "editorial"


def palette_public() -> list[dict[str, Any]]:
    """Catalog for /api/health and the React sidebar."""
    out: list[dict[str, Any]] = [
        {
            "id": "auto",
            "label": "Auto",
            "swatches": ["#0F3D3E", "#E85D04", "#0077B6", "#F77F00"],
        }
    ]
    for pid in ("editorial", "ocean", "sunset", "mono"):
        p = _PALETTES[pid]
        out.append(
            {
                "id": pid,
                "label": p["label"],
                "swatches": [p["primary"], *p["accents"][:3]],
            }
        )
    return out


def intent_palette_lines(palette_id: str, style_notes: str = "") -> list[str]:
    """Lines appended to UI Intent for chart colors / look."""
    pid = normalize_palette_id(palette_id)
    lines: list[str] = []
    if pid == "auto":
        lines.append(
            "- палитра графиков: AUTO — выбери одну из editorial/ocean/sunset/mono "
            "на весь документ; не смешивай пресеты и не используй фиолетовый нейрослоп"
        )
    else:
        p = _PALETTES[pid]
        accents = "/".join(p["accents"])
        lines.append(
            f"- палитра графиков: {p['label']} ({pid}) — ink {p['primary']}, "
            f"accents {accents}, area {p['area']}, grid {p['grid']}; "
            "в charts[].html используй ТОЛЬКО эти hex/rgba"
        )
    notes = (style_notes or "").strip()
    if notes:
        lines.append(
            f"- стиль графиков (нюансы UI): {notes} "
            "(легенда/сетка/толщина линий — по желанию; цвета — из палитры выше)"
        )
    return lines
