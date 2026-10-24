"""Infer a narrative beat plan when no deck structure template is selected.

Keeps gallery structures as optional DNA; freeform runs get a Source+media
driven skeleton so LLM decks do not collapse to scorecard spam.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from case3.deck_structure import normalize_structure_id, structure_meta

# mode → default visual pack (Julius pairs)
_MODE_PACK: dict[str, str] = {
    "board_update": "board",
    "performance": "signal",
    "qbr": "relay",
    "survey": "voltage",
    "investor": "ink",
    "launch": "botanical",
    "campaign": "atelier",
    "workshop": "studio",
    "general": "atelier",
}

_MODE_ARCS: dict[str, list[str]] = {
    "board_update": [
        "title",
        "callout",
        "scorecard",
        "table_hero",
        "table_hero",
        "card_row",
        "section",
        "table_hero",
        "callout",
        "closing",
    ],
    "performance": [
        "title",
        "chart_hero",
        "scorecard",
        "chart_split",
        "table_hero",
        "table_hero",
        "card_row",
        "callout",
        "table_hero",
        "closing",
    ],
    "qbr": [
        "title",
        "section",
        "scorecard",
        "chart_hero",
        "card_row",
        "callout",
        "section",
        "table_hero",
        "card_row",
        "closing",
    ],
    "survey": [
        "title",
        "callout",
        "scorecard",
        "card_row",
        "card_row",
        "callout",
        "table_hero",
        "card_row",
        "closing",
    ],
    "investor": [
        "title",
        "section",
        "chart_hero",
        "scorecard",
        "table_hero",
        "callout",
        "card_row",
        "closing",
    ],
    "launch": [
        "title",
        "callout",
        "card_row",
        "media_hero",
        "table_hero",
        "scorecard",
        "card_row",
        "closing",
    ],
    "campaign": [
        "title",
        "scorecard",
        "chart_hero",
        "table_hero",
        "card_row",
        "bullets",
        "closing",
    ],
    "workshop": [
        "title",
        "card_row",
        "table_hero",
        "card_row",
        "card_row",
        "section",
        "bullets",
        "closing",
    ],
    "general": [
        "title",
        "scorecard",
        "callout",
        "table_hero",
        "card_row",
        "section",
        "bullets",
        "closing",
    ],
}


@dataclass(frozen=True)
class BeatPlan:
    mode: str
    pack_hint: str
    target_slides: int
    beats: tuple[str, ...]
    rationale: str
    from_structure: bool = False


def _blob(*parts: str) -> str:
    return " ".join(p for p in parts if p).lower()


def _score_modes(
    text: str,
    *,
    n_charts: int,
    n_figs: int,
    n_dias: int,
) -> dict[str, float]:
    scores = {m: 0.0 for m in _MODE_ARCS}
    # Keyword / shape signals (RU+EN)
    rules: list[tuple[str, Sequence[str], float]] = [
        (
            "board_update",
            (
                "board",
                "совет",
                "hiring",
                "найм",
                "ask:",
                "approve",
                "утверд",
                "nrr",
                "burn",
                "runway",
                "arr ",
            ),
            2.0,
        ),
        (
            "performance",
            (
                "roas",
                "spend",
                "cac",
                "attributed",
                "канал",
                "campaign",
                "кампан",
                "media spend",
                "pipeline /",
            ),
            2.2,
        ),
        (
            "qbr",
            ("qbr", "quarterly", "квартал", "q3", "q4", "reallocate", "перераспред"),
            2.0,
        ),
        (
            "survey",
            (
                "survey",
                "опрос",
                "csat",
                "nps",
                "feedback",
                "респондент",
                "friction",
                "% love",
                "satisfaction",
            ),
            2.4,
        ),
        (
            "investor",
            ("investor", "инвестор", "arr", "series", "runway", "fundraising"),
            1.8,
        ),
        (
            "launch",
            ("launch", "запуск", "product launch", "waitlist", "ритуал", "vesper"),
            2.0,
        ),
        (
            "campaign",
            ("weekly", "this week", "creative", "pause", "scale", "roas", "cpa"),
            1.6,
        ),
        (
            "workshop",
            ("workshop", "facilitat", "agenda", "упражнен", "ретро", "exercise"),
            2.2,
        ),
    ]
    for mode, keys, w in rules:
        hits = sum(1 for k in keys if k in text)
        if hits:
            scores[mode] += w * hits

    # Media shapes
    if n_charts >= 2:
        scores["performance"] += 3.0
        scores["qbr"] += 1.5
        scores["campaign"] += 1.0
    elif n_charts == 1:
        scores["performance"] += 1.5
        scores["investor"] += 1.0
        scores["campaign"] += 1.0
        scores["general"] += 0.5

    if n_figs >= 1:
        scores["launch"] += 2.5
    if n_dias >= 1:
        scores["workshop"] += 1.5
        scores["general"] += 1.0

    # Percent-heavy survey fingerprint
    pcts = len(re.findall(r"\b\d{1,3}\s*%", text))
    if pcts >= 3 and n_charts <= 1:
        scores["survey"] += 3.0

    # Thin source → shorter general arc
    if len(text) < 280 and n_charts == 0 and n_figs == 0:
        scores["general"] += 2.0
        scores["campaign"] += 1.0

    scores["general"] += 0.1  # never empty winner
    return scores


def _trim_beats(
    beats: list[str],
    *,
    n_charts: int,
    n_figs: int,
    n_dias: int,
    target: int,
) -> list[str]:
    """Drop media layouts the run cannot fill; keep title/closing; hit target length."""
    out: list[str] = []
    charts_left = n_charts
    figs_left = n_figs + n_dias
    for b in beats:
        if b in ("chart_hero", "chart_split"):
            if charts_left <= 0:
                # substitute a table or callout so variety holds
                out.append("table_hero" if "table_hero" not in out[-2:] else "callout")
                continue
            charts_left -= 1
        if b in ("media_hero", "media_split"):
            if figs_left <= 0:
                out.append("callout")
                continue
            figs_left -= 1
        out.append(b)

    # Ensure bookends
    if not out or out[0] != "title":
        out = ["title", *out]
    if out[-1] != "closing":
        out = [*out, "closing"]

    # Shrink toward target (prefer dropping middle duplicates)
    while len(out) > target and len(out) > 6:
        # drop a duplicate table_hero / card_row from the middle
        dropped = False
        for layout in ("table_hero", "card_row", "bullets", "section"):
            idxs = [i for i, x in enumerate(out) if x == layout and 0 < i < len(out) - 1]
            if len(idxs) >= 2:
                del out[idxs[-1]]
                dropped = True
                break
        if not dropped:
            # drop middle callout
            mid = len(out) // 2
            if out[mid] not in ("title", "closing"):
                del out[mid]
            else:
                break

    # Grow if too short
    fillers = ["callout", "card_row", "table_hero", "section", "bullets"]
    fi = 0
    while len(out) < max(6, min(target, 10)):
        insert_at = max(1, len(out) - 1)
        out.insert(insert_at, fillers[fi % len(fillers)])
        fi += 1
        if fi > 12:
            break

    return out


def plan_beats(
    *,
    source: str,
    intent: str = "",
    chart_ids: Sequence[str] | None = None,
    figure_ids: Sequence[str] | None = None,
    diagram_ids: Sequence[str] | None = None,
    structure_id: str | None = None,
) -> BeatPlan:
    """Build a layout skeleton from structure template or Source+media signals."""
    charts = [str(x) for x in (chart_ids or []) if str(x).strip()]
    figs = [str(x) for x in (figure_ids or []) if str(x).strip()]
    dias = [str(x) for x in (diagram_ids or []) if str(x).strip()]
    sid = normalize_structure_id(structure_id)

    if sid:
        meta = structure_meta(sid) or {}
        arc = [str(x) for x in (meta.get("arc") or []) if str(x).strip()]
        if not arc:
            arc = list(_MODE_ARCS.get(sid, _MODE_ARCS["general"]))
        pack = str(meta.get("default_pack") or _MODE_PACK.get(sid, "atelier"))
        slides_range = meta.get("slides") or [8, 12]
        try:
            lo, hi = int(slides_range[0]), int(slides_range[-1])
        except (TypeError, ValueError, IndexError):
            lo, hi = 8, 12
        target = max(lo, min(hi, 10 if len(charts) + len(figs) >= 1 else 8))
        beats = _trim_beats(
            arc, n_charts=len(charts), n_figs=len(figs), n_dias=len(dias), target=target
        )
        return BeatPlan(
            mode=sid,
            pack_hint=pack,
            target_slides=len(beats),
            beats=tuple(beats),
            rationale=f"structure template {sid}",
            from_structure=True,
        )

    text = _blob(source, intent)
    scores = _score_modes(
        text, n_charts=len(charts), n_figs=len(figs), n_dias=len(dias)
    )
    mode = max(scores, key=lambda m: scores[m])
    arc = list(_MODE_ARCS[mode])
    pack = _MODE_PACK[mode]
    # Richer media → longer deck
    richness = len(charts) + len(figs) + len(dias) + (1 if len(text) > 600 else 0)
    target = 10 if richness >= 2 else (8 if richness >= 1 or len(text) > 400 else 7)
    target = max(6, min(12, target))
    beats = _trim_beats(
        arc, n_charts=len(charts), n_figs=len(figs), n_dias=len(dias), target=target
    )
    top = sorted(scores.items(), key=lambda kv: -kv[1])[:3]
    rationale = (
        f"inferred mode={mode} from Source/media; "
        f"scores=" + ", ".join(f"{m}:{s:.1f}" for m, s in top)
    )
    return BeatPlan(
        mode=mode,
        pack_hint=pack,
        target_slides=len(beats),
        beats=tuple(beats),
        rationale=rationale,
        from_structure=False,
    )


def format_beat_overlay(plan: BeatPlan) -> str:
    """Markdown block injected into system_slides as STRUCTURE_OVERLAY stand-in."""
    skeleton = " → ".join(plan.beats)
    lines = [
        "# BEAT PLAN (mandatory skeleton — fill copy from Source only)",
        "",
        f"**Mode:** `{plan.mode}` · **target slides:** {plan.target_slides} · "
        f"**visual pack hint:** `{plan.pack_hint}`",
        f"**Why:** {plan.rationale}",
        "",
        f"**Layout skeleton (follow order; may drop a beat only if Source lacks facts):**",
        f"`{skeleton}`",
        "",
        "Rules:",
        "1. Emit one slide per beat above (same `layout` values). Do not invent extra scorecards.",
        "2. Titles = insights (Julius). Chart slides need insight `caption`. Closing: "
        "`VALUE — label` takeaway when Source has a headline number + 3 bullets.",
        "3. Numbers ⊆ Source / chart captions only. Prefer ≥5 distinct layouts when ≥8 slides.",
        "4. If a beat needs media you lack, replace that one beat with `callout` or `table_hero` "
        "— keep variety.",
    ]
    if plan.mode == "survey":
        lines.append(
            "5. Survey: `%` kickers on `card_row` (`68%`) so meters render; ≤1 chart."
        )
    if plan.mode == "performance":
        lines.append("5. Performance: put `chart_hero` before the first scorecard.")
    if plan.mode == "board_update":
        lines.append("5. Board: early `callout` ASK; table bridges over chart spam.")
    return "\n".join(lines)


def maybe_apply_pack_hint(
    *,
    structure_id: str | None,
    current_pack: str | None,
    plan: BeatPlan,
    pack_explicit: bool = False,
) -> str:
    """When freeform (no structure) and pack not explicitly chosen, use plan hint."""
    if structure_id or pack_explicit:
        return (current_pack or "atelier").strip() or "atelier"
    cur = (current_pack or "atelier").strip().lower() or "atelier"
    # Default atelier on freeform → upgrade to narrative DNA pack
    if cur in ("", "atelier", "auto"):
        return plan.pack_hint
    return cur
