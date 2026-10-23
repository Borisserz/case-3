#!/usr/bin/env python3
"""Render Liber twin PNGs for template gallery (not Julius screenshots).

Usage:
  PYTHONPATH=src python3 scripts/render_template_previews.py

Writes web/public/deck/previews/{structureId}/01.png … 06.png
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from case3.deck_theme import resolve_deck_theme  # noqa: E402
from case3.slides_render import render_deck_pngs  # noqa: E402

# Prefer repo scripts/ on sys.path for premium decks
sys.path.insert(0, str(ROOT / "scripts"))
from premium_gallery_decks import PREMIUM_DECKS  # noqa: E402

OUT_PUBLIC = ROOT / "web" / "public" / "deck" / "previews"
WORK = ROOT / "runs" / "atelier_visual" / "template_preview_render"
CHART_FALLBACK = ROOT / "runs" / "atelier_visual" / "atelier_bar.png"
CHART2_FALLBACK = ROOT / "runs" / "atelier_visual" / "atelier_line.png"
GALLERY_CHARTS = ROOT / "runs" / "atelier_visual" / "gallery_charts"
HERO = ROOT / "runs" / "atelier_visual" / "botanical_smoke" / "figures" / "fig_hero.png"


def _pack_charts(pack: str) -> dict[str, Path]:
    """Prefer pack-colored gallery charts; fall back to atelier placeholders."""
    bar = GALLERY_CHARTS / f"{pack}_bar.png"
    line = GALLERY_CHARTS / f"{pack}_line.png"
    bar_p = bar if bar.is_file() else CHART_FALLBACK
    line_p = line if line.is_file() else (
        CHART2_FALLBACK if CHART2_FALLBACK.is_file() else bar_p
    )
    return {"cht_bar": bar_p, "cht_line": line_p}


def _deck(pack: str, slides: list[dict]) -> dict:
    tok = resolve_deck_theme(pack)
    return {
        "version": 1,
        "aspect": "16:9",
        "palette": "atelier",
        "language": "en",
        "theme_id": pack,
        "style": tok.as_dict(),
        "slides": slides,
    }


# Liber-owned copy (inspired by Julius arcs, not their slides verbatim).
DECKS: dict[str, tuple[str, list[dict]]] = {
    "board_update": (
        "board",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "Q4 · BOARD",
                "title": "ARR $18.4M on two record quarters",
                "takeaway": "NRR 117% · Burn 0.9x · Liber board pack",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "01 / EXECUTIVE SCORECARD",
                "title": "Plan vs actuals — three greens, one watch",
                "kpis": [
                    {"label": "ARR", "value": "$18.4M", "delta": "+24%", "status": "up"},
                    {"label": "NRR", "value": "117%", "delta": "+3pt", "status": "up"},
                    {"label": "Burn", "value": "0.9x", "delta": "−0.2", "status": "up"},
                    {"label": "Cash", "value": "$21.3M", "delta": "30 mo", "status": "flat"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "02 / GROWTH",
                "title": "ARR bridge — new logo carried the quarter",
                "chart_id": "cht_bar",
                "takeaway": "Illustrative series for gallery twin",
            },
            {
                "id": "s04",
                "layout": "table_hero",
                "kicker": "03 / GTM",
                "title": "Pipeline by segment",
                "rows": [
                    ["Segment", "Pipe", "Win"],
                    ["Mid-market", "$4.2M", "28%"],
                    ["Enterprise", "$6.1M", "19%"],
                    ["Expansion", "$2.8M", "41%"],
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "04 / PRIORITIES",
                "title": "Three owned bets for Q+1",
                "cards": [
                    {"title": "Workflow wedge", "kicker": "PRODUCT", "body": "Ship automation path that expands seats."},
                    {"title": "Partner mid-market", "kicker": "GTM", "body": "Co-sell motion with two design partners."},
                    {"title": "Gross margin 78%", "kicker": "OPS", "body": "Cut infra waste without slowing delivery."},
                ],
                "caption": "BOARD ASK Approve hiring plan this meeting",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "05 / DECISIONS",
                "title": "Approve hiring plan + Series narrative",
                "takeaway": "Liber · Board pack — numbers ⊆ Source on real runs",
                "bullets": [
                    "Lock Q+1 operating plan owners",
                    "Green-light two partner intros",
                    "Hold cash burn under 1.0x",
                ],
            },
        ],
    ),
    "performance": (
        "signal",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "BOLD SIGNAL · GROWTH INTELLIGENCE",
                "title": "Spend. Return. Next move.",
                "takeaway": "Scale the strongest signals · Liber Bold Signal twin",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "01 / EXECUTIVE SIGNAL",
                "title": "More return. Better efficiency.",
                "kpis": [
                    {"label": "Media spend", "value": "$2.09M", "delta": "+32%"},
                    {"label": "Attr. revenue", "value": "$6.99M", "delta": "+57%"},
                    {"label": "Blended ROAS", "value": "3.34×", "delta": "+0.3"},
                    {"label": "Channels", "value": "6", "delta": "3 regions"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "02 / SPEND & RETURN",
                "title": "Revenue is growing faster than spend",
                "chart_id": "cht_line",
                "takeaway": "Indexed Jan=100 — gallery twin series",
            },
            {
                "id": "s04",
                "layout": "table_hero",
                "kicker": "04 / CHANNEL COMPARISON",
                "title": "Search anchors scale. CRM leads ROAS.",
                "rows": [
                    ["Channel", "Spend", "ROAS"],
                    ["Paid Search", "$660k", "4.2×"],
                    ["Email / CRM", "$96k", "7.1×"],
                    ["Paid Social", "$410k", "2.8×"],
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "08 / RECOMMENDATIONS",
                "title": "Make the next dollar measurable",
                "cards": [
                    {"title": "Scale selectively", "kicker": "01", "body": "Search + affiliates; watch marginal ROAS."},
                    {"title": "Build lifecycle", "kicker": "02", "body": "CRM journeys with holdout proof."},
                    {"title": "Fund a test", "kicker": "03", "body": "Move ±5pp — not a wholesale shift."},
                ],
                "caption": "GATE Prove incremental return before scaling",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "10 / DATA & DEFINITIONS",
                "title": "Read the signal with the right caveats",
                "bullets": [
                    "Numbers ⊆ Source on real runs",
                    "Attributed revenue as defined in brief",
                    "90-day gates before next realloc",
                ],
            },
        ],
    ),
    "qbr": (
        "relay",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "MARKETING · Q3",
                "title": "More pipeline. Better efficiency.",
                "takeaway": "$9.6M — marketing-sourced pipeline\n8.0× — pipeline / marketing spend",
            },
            {
                "id": "s02",
                "layout": "section",
                "kicker": "THESIS",
                "title": "Growth improved; target attainment did not",
                "subtitle": "Reallocate, then prove — Liber Split Pastel",
            },
            {
                "id": "s03",
                "layout": "scorecard",
                "kicker": "SCORECARD",
                "title": "Efficient growth, narrow misses",
                "kpis": [
                    {"label": "Spend", "value": "$1.20M", "delta": "−4% vs goal"},
                    {"label": "Pipeline", "value": "$9.6M", "delta": "96% of goal"},
                    {"label": "Efficiency", "value": "8.0×", "delta": "+0.9"},
                    {"label": "SQLs", "value": "720", "delta": "30% MQL→SQL"},
                ],
            },
            {
                "id": "s04",
                "layout": "chart_hero",
                "kicker": "CHANNELS",
                "title": "Search and webinars earned the next dollar",
                "chart_id": "cht_bar",
                "takeaway": "56% of pipeline from 45% of spend",
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "WINS / MISSES",
                "title": "Wins to repeat. Misses to correct.",
                "cards": [
                    {"title": "Search + webinars", "kicker": "REPEAT", "body": "10.0× pipeline / spend each."},
                    {"title": "North America", "kicker": "REPEAT", "body": "Above pipeline goal."},
                    {"title": "Field & events", "kicker": "CORRECT", "body": "25% spend → 16% pipeline."},
                ],
                "caption": "DECISION Shift $120K · keep total $1.20M",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "ASK",
                "title": "Approve the shift. Protect the learning loop.",
                "bullets": [
                    "Approve $120K event → search/webinars",
                    "Commit to SQL quality gates",
                    "Success = pipeline + SQLs, not leads alone",
                ],
            },
        ],
    ),
    "survey": (
        "relay",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "SURVEY READOUT",
                "title": "Findings → actions",
                "takeaway": "n from Source only — Liber gallery twin",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "METHOD",
                "title": "Who answered",
                "kpis": [
                    {"label": "n", "value": "428", "delta": "82%"},
                    {"label": "CSAT", "value": "4.2", "delta": "+0.3"},
                    {"label": "NPS", "value": "41", "delta": "+5"},
                    {"label": "Effort", "value": "2.1", "delta": "−0.4"},
                ],
            },
            {
                "id": "s03",
                "layout": "callout",
                "kicker": "FINDING 1",
                "title": "Activation friction",
                "term": "THEME",
                "definition": "Onboarding still feels like homework.",
                "body": "Illustrative quote for gallery — real runs use Source only.",
            },
            {
                "id": "s04",
                "layout": "card_row",
                "kicker": "TOP THEMES",
                "title": "Three cards from the data",
                "cards": [
                    {"title": "Setup time", "kicker": "01", "body": "Day-1 path too long."},
                    {"title": "Support wait", "kicker": "02", "body": "SLA miss on first reply."},
                    {"title": "Value clarity", "kicker": "03", "body": "Aha moment buried."},
                ],
            },
            {
                "id": "s05",
                "layout": "table_hero",
                "kicker": "ACTIONS",
                "title": "Priority matrix",
                "rows": [
                    ["Action", "Owner", "When"],
                    ["Simplify day-1", "Product", "Sprint 12"],
                    ["SLA to 4h", "Support", "Nov"],
                    ["Value tour", "CS", "Pilot"],
                ],
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "NEXT",
                "title": "Ship two fixes before next pulse",
                "bullets": ["Re-field in 60 days", "Track activation time", "Publish owners"],
            },
        ],
    ),
    "investor": (
        "ink",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "RELAY / INVESTOR UPDATE",
                "title": "Growth, with more signal.",
                "takeaway": "Q3 · Liber Relay Ink twin",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "THE QUARTER IN ONE SENTENCE",
                "title": "Marketing scaled the engine. Expansion increased the yield.",
                "kpis": [
                    {"label": "Q3 revenue", "value": "$2.08M", "delta": "+20.9% QoQ"},
                    {"label": "Ending ARR", "value": "$12.0M", "delta": "+25.0% QoQ"},
                    {"label": "Mkt-sourced", "value": "70%", "delta": "of new ARR"},
                    {"label": "NRR", "value": "112%", "delta": "+3pt"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "COMPOUNDING",
                "title": "Revenue is compounding — not spiking",
                "chart_id": "cht_bar",
                "takeaway": "+20.9% QoQ · +96% YoY — gallery twin",
            },
            {
                "id": "s04",
                "layout": "table_hero",
                "kicker": "CONVERSION",
                "title": "Better conversion. Lower acquisition cost.",
                "rows": [
                    ["Metric", "Prior", "Now"],
                    ["Qualified opps", "180", "240"],
                    ["New customers", "36", "48"],
                    ["Blended CAC", "$29k", "$26k"],
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "Q+1 PRIORITIES",
                "title": "Turn momentum into repeatability",
                "cards": [
                    {"title": "Grow efficiently", "kicker": "01", "body": "ARR $14.0–14.5M · CAC ≤$26K."},
                    {"title": "Deepen product", "kicker": "02", "body": "Analytics GA · NRR ≥112%."},
                    {"title": "Protect runway", "kicker": "03", "body": "Burn ≤$600K · margin ≥80%."},
                ],
                "caption": "ASK Approve operating plan gates",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "DEFINITIONS",
                "title": "Sample-data basis on gallery twin",
                "bullets": [
                    "ARR = contracted recurring at period end",
                    "NRR trailing-12m with expansion",
                    "Real runs: numbers ⊆ Source only",
                ],
            },
        ],
    ),
    "launch": (
        "botanical",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "PRODUCT LAUNCH",
                "title": "Story rooted in ritual",
                "takeaway": "Liber Dark Botanical — gallery twin",
                "media_id": "fig_hero",
            },
            {
                "id": "s02",
                "layout": "card_row",
                "kicker": "AUDIENCES",
                "title": "Three who feel the pain",
                "cards": [
                    {"title": "Ops leads", "kicker": "01", "body": "Need calmer evening tools."},
                    {"title": "Finance partners", "kicker": "02", "body": "Want clear ROI stories."},
                    {"title": "Frontline coaches", "kicker": "03", "body": "Teach the ritual weekly."},
                ],
                "caption": "VALIDATION GATE Interviews before message lock",
            },
            {
                "id": "s03",
                "layout": "table_hero",
                "kicker": "CHANNELS",
                "title": "Where we show up",
                "rows": [
                    ["Channel", "Role", "Bet"],
                    ["Product", "Aha", "High"],
                    ["Email", "Nurture", "Med"],
                    ["Partner", "Trust", "High"],
                ],
            },
            {
                "id": "s04",
                "layout": "scorecard",
                "kicker": "TRACTION GOALS",
                "title": "Planning goals (illustrative)",
                "kpis": [
                    {"label": "Waitlist", "value": "1.5k"},
                    {"label": "Pilot", "value": "50"},
                    {"label": "NPS", "value": "50+"},
                    {"label": "Spend", "value": "$20k"},
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "LEARNING",
                "title": "What we must learn in 30 days",
                "cards": [
                    {"title": "Activation time", "kicker": "A", "body": "Minutes to first aha."},
                    {"title": "Willingness to pay", "kicker": "B", "body": "Price ladder test."},
                    {"title": "Support load", "kicker": "C", "body": "Tickets per 100 users."},
                ],
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "LAUNCH DECISION",
                "title": "Go / hold — owners named",
                "media_id": "fig_hero",
                "bullets": ["Confirm blend", "Fund learning plan", "Name launch lead"],
            },
        ],
    ),
    "campaign": (
        "atelier",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "CAMPAIGN STATUS",
                "title": "Winners vs pauses",
                "takeaway": "Liber Atelier — olive paper twin",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "THIS WEEK",
                "title": "Efficiency snapshot",
                "kpis": [
                    {"label": "Spend", "value": "$86k", "delta": "+5%"},
                    {"label": "ROAS", "value": "4.1x", "delta": "+0.3"},
                    {"label": "CPA", "value": "$64", "delta": "−8%"},
                    {"label": "Pipe", "value": "$410k", "delta": "+12%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "TREND",
                "title": "Daily return",
                "chart_id": "cht_line",
            },
            {
                "id": "s04",
                "layout": "table_hero",
                "kicker": "CREATIVES",
                "title": "Scale / pause",
                "rows": [
                    ["Creative", "ROAS", "Action"],
                    ["Hook A", "5.2x", "Scale"],
                    ["Hook B", "1.1x", "Pause"],
                    ["UGC C", "3.8x", "Hold"],
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "NEXT WEEK",
                "title": "Three bets",
                "cards": [
                    {"title": "Double Hook A", "kicker": "SCALE", "body": "Geo expand where ROAS holds."},
                    {"title": "New offer test", "kicker": "TEST", "body": "One creative, one landing."},
                    {"title": "Cut Hook B", "kicker": "PAUSE", "body": "Reallocate spend Friday."},
                ],
                "caption": "ASK Approve budget shift",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "REVIEW",
                "title": "Review Friday",
                "bullets": ["Owners named", "Freeze losers", "Report ROAS delta"],
            },
        ],
    ),
    "workshop": (
        "relay",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "WORKSHOP",
                "title": "Goals → exercises → outputs",
                "takeaway": "Facilitator pack — Liber Relay",
            },
            {
                "id": "s02",
                "layout": "card_row",
                "kicker": "GOALS",
                "title": "What success looks like today",
                "cards": [
                    {"title": "Shared frame", "kicker": "01", "body": "One problem statement."},
                    {"title": "Prioritized bets", "kicker": "02", "body": "Force-rank three."},
                    {"title": "Owners + dates", "kicker": "03", "body": "Leave with names."},
                ],
            },
            {
                "id": "s03",
                "layout": "table_hero",
                "kicker": "AGENDA",
                "title": "Blocks",
                "rows": [
                    ["Block", "Min", "Output"],
                    ["Frame", "20", "Problem"],
                    ["Diverge", "35", "Ideas"],
                    ["Converge", "30", "Bets"],
                ],
            },
            {
                "id": "s04",
                "layout": "card_row",
                "kicker": "EXERCISE A",
                "title": "Map the friction",
                "cards": [
                    {"title": "Solo notes", "kicker": "A1", "body": "5 minutes silent."},
                    {"title": "Pair share", "kicker": "A2", "body": "Cluster themes."},
                    {"title": "Cluster", "kicker": "A3", "body": "Name the pattern."},
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "EXERCISE B",
                "title": "Force-rank bets",
                "cards": [
                    {"title": "Impact", "kicker": "B1", "body": "Score 1–5."},
                    {"title": "Effort", "kicker": "B2", "body": "Score 1–5."},
                    {"title": "Owner", "kicker": "B3", "body": "Name one person."},
                ],
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "FOLLOW-UPS",
                "title": "Parking lot → next ritual",
                "bullets": ["Send notes in 24h", "Book next session", "Clear blockers"],
            },
        ],
    ),
}

# Premium Julius-DNA decks (10–12 slides) override short stubs for the four packs.
DECKS.update(PREMIUM_DECKS)


def main() -> int:
    if not CHART_FALLBACK.is_file() and not GALLERY_CHARTS.is_dir():
        print("missing charts — run scripts/render_premium_gallery_charts.py", file=sys.stderr)
        return 1

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.mkdir(parents=True, exist_ok=True)

    for structure_id, (pack, slides) in DECKS.items():
        print(f"== {structure_id} · {pack} ==")
        media = _pack_charts(pack)
        if HERO.is_file():
            media = {**media, "fig_hero": HERO}
        deck = _deck(pack, slides)
        case_dir = WORK / structure_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "deck.json").write_text(
            json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        pngs = render_deck_pngs(
            deck,
            work_root=case_dir / "work",
            out_dir=case_dir / "slides",
            chart_png_by_id=media,
            media_png_by_id=media,
        )
        dest = OUT_PUBLIC / structure_id
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        # Gallery filmstrip: up to 12 Liber twins (premium four packs are 11–12).
        for i, src in enumerate(pngs[:12], start=1):
            shutil.copy2(src, dest / f"{i:02d}.png")
        print(f"  wrote {len(list(dest.glob('*.png')))}/{len(pngs)} → {dest}")
    print("done — Liber twins only (no Julius rasters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
