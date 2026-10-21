"""Named chart palettes for UI → Intent → Chart.js HTML."""

from __future__ import annotations

import re
from typing import Any

# Preset ids used in Form/UI. ``auto`` = model picks one preset for the doc.
PALETTE_IDS = ("auto", "editorial", "ocean", "sunset", "mono", "atelier")

_HEX = re.compile(r"#([0-9a-fA-F]{6})\b")
_RGBA = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([0-9.]+))?\s*\)",
    re.I,
)


def _lum(r: int, g: int, b: int) -> float:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _parse_hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _fmt_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def apply_palette_to_html(html: str, palette_id: str) -> str:
    """Remap #hex / rgb(a) colors in chart HTML onto a named palette.

    Keeps alpha channels. ``auto`` leaves HTML unchanged. Data arrays are
    untouched because only color tokens are rewritten.
    """
    pid = normalize_palette_id(palette_id)
    if pid == "auto" or pid not in _PALETTES:
        return html
    p = _PALETTES[pid]
    targets: list[str] = [p["primary"], *list(p["accents"])]
    # Include area/grid as soft colors for low-alpha remaps
    area = str(p.get("area") or "")
    grid = str(p.get("grid") or "")

    muted = str(p.get("muted") or "").upper()
    src = html or ""

    def _is_near_white(hx: str) -> bool:
        r, g, b = _parse_hex(hx)
        return min(r, g, b) >= 245

    def _is_ink_grey(hx: str) -> bool:
        r, g, b = _parse_hex(hx)
        if max(r, g, b) - min(r, g, b) > 28:
            return False
        return 40 <= _lum(r, g, b) <= 190

    # Nearest Chart.js color prop — avoid mistaking labels.color for borderColor.
    _PROP_NEAR = re.compile(
        r"(backgroundcolor|bordercolor|pointbackgroundcolor|pointbordercolor|"
        r"fillcolor|(?<![a-z])color)\s*[:=]",
        re.I,
    )
    _SERIES_PROPS = frozenset(
        {
            "backgroundcolor",
            "bordercolor",
            "pointbackgroundcolor",
            "pointbordercolor",
            "fillcolor",
        }
    )

    def _series_context(start: int) -> bool:
        ctx = src[max(0, start - 72) : start]
        matches = list(_PROP_NEAR.finditer(ctx))
        if not matches:
            return False
        return matches[-1].group(1).lower() in _SERIES_PROPS

    # Collect unique hex colors (order of first appearance). Skip near-white
    # so Chart.js segment borders stay clean.
    seen: list[str] = []
    series: set[str] = set()
    for m in _HEX.finditer(src):
        hx = f"#{m.group(1).upper()}"
        if _is_near_white(hx):
            continue
        if hx not in seen:
            seen.append(hx)
        if _series_context(m.start()):
            series.add(hx)
    if not seen:
        return html

    # Darkest series/ink → primary; series → accents; label greys → muted.
    ranked = sorted(seen, key=lambda h: _lum(*_parse_hex(h)))
    mapping: dict[str, str] = {}
    if ranked:
        mapping[ranked[0]] = targets[0].upper()
        accent_i = 1
        for hx in seen:
            if hx in mapping:
                continue
            if muted and _is_ink_grey(hx) and hx not in series:
                mapping[hx] = muted
                continue
            mapping[hx] = targets[min(accent_i, len(targets) - 1)].upper()
            accent_i += 1

    def _sub_hex(m: re.Match[str]) -> str:
        key = f"#{m.group(1).upper()}"
        return mapping.get(key, m.group(0))

    out = _HEX.sub(_sub_hex, html)

    def _sub_rgba(m: re.Match[str]) -> str:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = m.group(4)
        nearest = min(
            mapping.keys(),
            key=lambda h: abs(_lum(*_parse_hex(h)) - _lum(r, g, b)),
            default=None,
        )
        if nearest is None:
            return m.group(0)
        nr, ng, nb = _parse_hex(mapping[nearest])
        try:
            alpha = float(a) if a is not None else 1.0
        except ValueError:
            alpha = 1.0
        ctx = (m.string[max(0, m.start() - 20) : m.start()] or "").lower()
        if alpha < 0.35:
            if "grid" in ctx and grid.startswith("rgba"):
                return grid
            if area.startswith("rgba"):
                return area
        if a is None:
            return f"rgb({nr},{ng},{nb})"
        return f"rgba({nr},{ng},{nb},{a})"

    out = _RGBA.sub(_sub_rgba, out)
    return out


# Soft luminance ladders (Mary-inspired). No purple/indigo slop.
# atelier = Liber soft-green primary.
_PALETTES: dict[str, dict[str, Any]] = {
    "editorial": {
        "label": "Editorial",
        "primary": "#1A4A4B",
        "accents": ["#D97845", "#4AADA0", "#D9C07A", "#3D5C60"],
        "muted": "#9AA8B5",
        "area": "rgba(74,173,160,0.16)",
        "grid": "rgba(26,74,75,0.08)",
    },
    "ocean": {
        "label": "Ocean",
        "primary": "#1A5F9E",
        "accents": ["#2B8FC4", "#4DB8D4", "#7CCFDF", "#A8E0EC"],
        "muted": "#8FA0B0",
        "area": "rgba(77,184,212,0.16)",
        "grid": "rgba(26,95,158,0.09)",
    },
    "sunset": {
        "label": "Sunset",
        "primary": "#7A4058",
        "accents": ["#D65A5A", "#E8954A", "#E8C070", "#4A6070"],
        "muted": "#A8A0A0",
        "area": "rgba(232,149,74,0.15)",
        "grid": "rgba(122,64,88,0.09)",
    },
    "mono": {
        "label": "Mono",
        "primary": "#2A2F38",
        "accents": ["#3D4450", "#5C6570", "#8B939E", "#B0B6BE"],
        "muted": "#9CA3AF",
        "area": "rgba(42,47,56,0.10)",
        "grid": "rgba(42,47,56,0.07)",
    },
    # Soft olive→mist mono (Liber hues — no purple).
    "atelier": {
        "label": "Atelier",
        "primary": "#3F5210",
        "accents": ["#5A6E28", "#7A8F45", "#A8B87A", "#D5DEC0"],
        # Axis/legend ink — readable on cream paper.
        "muted": "#6A7160",
        "area": "rgba(122,143,69,0.16)",
        "grid": "rgba(63,82,16,0.08)",
    },
}


def normalize_palette_id(raw: str | None) -> str:
    key = (raw or "editorial").strip().lower()
    if key in PALETTE_IDS:
        return key
    return "editorial"


def palette_css_vars(palette_id: str) -> str:
    """CSS custom properties for frame KPI / card chrome (inject into fragment)."""
    pid = normalize_palette_id(palette_id)
    if pid == "auto" or pid not in _PALETTES:
        return ""
    p = _PALETTES[pid]
    primary = str(p["primary"])
    accents = list(p["accents"])
    value = accents[0] if accents else primary
    label = str(p.get("muted") or primary)
    ink = primary
    muted = str(p.get("muted") or "#94A3B8")
    return (
        f"--chart-ink:{ink};--chart-accent:{value};--chart-muted:{muted};"
        f"--kpi-value:{value};--kpi-label:{label};--kpi-ink:{ink};"
    )


def apply_kpi_palette_vars(html: str, palette_id: str) -> str:
    """Inject palette CSS vars so host ``.kpi`` / cards pick soft ink (not fixed orange)."""
    pid = normalize_palette_id(palette_id)
    vars_decl = palette_css_vars(pid)
    if not vars_decl or not (html or "").strip():
        return html
    # Replace prior inject; keep one block.
    cleaned = re.sub(
        r'<style\s+id=["\']case3-palette["\'][^>]*>.*?</style>\s*',
        "",
        html,
        count=1,
        flags=re.I | re.S,
    )
    block = f'<style id="case3-palette">#mount{{{vars_decl}}}</style>'
    return block + cleaned


# Intent line: "- палитра графиков: Atelier (atelier) — …" or "… AUTO — …"
_PALETTE_INTENT_RE = re.compile(
    r"палитра графиков:\s*(?:AUTO\b|[^(]*\((\w+)\))",
    re.I,
)


def palette_from_intent(intent: str) -> str:
    """Parse UI palette id from Intent block; ``auto`` when missing/AUTO."""
    m = _PALETTE_INTENT_RE.search(intent or "")
    if not m or m.group(1) is None:
        return "auto"
    return normalize_palette_id(m.group(1))


def palette_public() -> list[dict[str, Any]]:
    """Catalog for /api/health and the React sidebar."""
    out: list[dict[str, Any]] = [
        {
            "id": "auto",
            "label": "Auto",
            "swatches": ["#3F5210", "#D97845", "#1A5F9E", "#E8954A"],
        }
    ]
    for pid in ("editorial", "ocean", "sunset", "mono", "atelier"):
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
            "- палитра графиков: AUTO — выбери одну из editorial/ocean/sunset/mono/atelier "
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
