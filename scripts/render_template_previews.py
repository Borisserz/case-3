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

OUT_PUBLIC = ROOT / "web" / "public" / "deck" / "previews"
WORK = ROOT / "runs" / "atelier_visual" / "template_preview_render"
CHART = ROOT / "runs" / "atelier_visual" / "atelier_bar.png"
CHART2 = ROOT / "runs" / "atelier_visual" / "atelier_line.png"
HERO = ROOT / "runs" / "atelier_visual" / "botanical_smoke" / "figures" / "fig_hero.png"


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
                "kicker": "SIGNAL",
                "title": "Spend vs return — reallocate in 90 days",
                "takeaway": "Liber Bold Signal twin",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "SPEND / RETURN",
                "title": "Channel efficiency this period",
                "kpis": [
                    {"label": "Spend", "value": "$420k", "delta": "+8%"},
                    {"label": "ROAS", "value": "3.4x", "delta": "+0.4"},
                    {"label": "CAC", "value": "$182", "delta": "−12%"},
                    {"label": "Pipe", "value": "$2.1M", "delta": "+19%"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "TREND",
                "title": "Weekly return by channel",
                "chart_id": "cht_line",
            },
            {
                "id": "s04",
                "layout": "table_hero",
                "kicker": "REALLOCATION",
                "title": "Move budget as a test",
                "rows": [
                    ["From", "To", "Δ"],
                    ["Display", "Search", "+$40k"],
                    ["Social", "Partner", "+$25k"],
                    ["Brand", "Hold", "—"],
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "90 DAYS",
                "title": "Roadmap bets",
                "cards": [
                    {"title": "Cut bottom 20%", "kicker": "CREATIVE", "body": "Pause losers; fund Hook A geo."},
                    {"title": "Double winner geo", "kicker": "MEDIA", "body": "Scale only where ROAS ≥ 4x."},
                    {"title": "Partner co-op", "kicker": "TEST", "body": "One co-funded campaign this quarter."},
                ],
                "caption": "DECISION Approve reallocation this week",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "NEXT",
                "title": "Owners assigned · review in 30 days",
                "bullets": ["Shift $65k as a test", "Kill Hook B", "Re-check CAC Friday"],
            },
        ],
    ),
    "qbr": (
        "relay",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "QUARTERLY BUSINESS REVIEW",
                "title": "Thesis → the shift that compounds",
                "takeaway": "Wins · misses · Q+1 — Liber Relay",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "SCORECARD",
                "title": "Quarter snapshot",
                "kpis": [
                    {"label": "Revenue", "value": "$4.8M", "delta": "+11%"},
                    {"label": "Margin", "value": "62%", "delta": "+2pt"},
                    {"label": "NPS", "value": "54", "delta": "+6"},
                    {"label": "Churn", "value": "2.1%", "delta": "−0.4"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "STORY 1",
                "title": "Where growth actually came from",
                "chart_id": "cht_bar",
            },
            {
                "id": "s04",
                "layout": "card_row",
                "kicker": "WINS / MISSES",
                "title": "Keep / kill / learn",
                "cards": [
                    {"title": "Keep expansion", "kicker": "WIN", "body": "Expansion motion beat new logo."},
                    {"title": "Kill unused SKU", "kicker": "MISS", "body": "Low attach — sunset in Q+1."},
                    {"title": "Learn onboarding", "kicker": "LAG", "body": "Activation still too slow."},
                ],
            },
            {
                "id": "s05",
                "layout": "table_hero",
                "kicker": "Q+1",
                "title": "Operating plan with owners",
                "rows": [
                    ["Bet", "Owner", "Target"],
                    ["Activation", "Product", "+8pt"],
                    ["Enterprise", "Sales", "$1.2M"],
                    ["Margin", "Ops", "64%"],
                ],
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "APPROVE",
                "title": "Protect the learning loop",
                "bullets": ["Shift budget", "Keep test cadence", "Revisit in 30 days"],
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
        "botanical",
        [
            {
                "id": "s01",
                "layout": "title",
                "kicker": "INVESTOR UPDATE",
                "title": "One-sentence quarter",
                "takeaway": "Growth engines · quality · ask — Liber Botanical",
                "media_id": "fig_hero",
            },
            {
                "id": "s02",
                "layout": "scorecard",
                "kicker": "QUALITY",
                "title": "Unit economics held",
                "kpis": [
                    {"label": "ARR", "value": "$18.4M", "delta": "+24%"},
                    {"label": "NRR", "value": "117%"},
                    {"label": "Gross", "value": "76%", "delta": "+1pt"},
                    {"label": "Runway", "value": "30 mo"},
                ],
            },
            {
                "id": "s03",
                "layout": "chart_hero",
                "kicker": "ENGINES",
                "title": "Where growth compounds",
                "chart_id": "cht_bar",
            },
            {
                "id": "s04",
                "layout": "table_hero",
                "kicker": "GTM",
                "title": "Motion quality",
                "rows": [
                    ["Motion", "Pipe", "Win"],
                    ["Product-led", "$3.1M", "32%"],
                    ["Sales-led", "$5.4M", "21%"],
                    ["Partner", "$1.2M", "27%"],
                ],
            },
            {
                "id": "s05",
                "layout": "card_row",
                "kicker": "RISKS",
                "title": "Watch + mitigate",
                "cards": [
                    {"title": "Cycle length", "kicker": "ENTERPRISE", "body": "Mitigate with proof packs."},
                    {"title": "Pricing pressure", "kicker": "COMPETITOR", "body": "Hold value narrative."},
                    {"title": "Key hire lag", "kicker": "TEAM", "body": "Close VP Sales search."},
                ],
                "caption": "THE ASK Extend runway narrative + intro list",
            },
            {
                "id": "s06",
                "layout": "closing",
                "kicker": "CLOSE",
                "title": "Definitions in appendix if Source has them",
                "media_id": "fig_hero",
                "bullets": ["Protect NRR", "Fund partner motion", "Name the ask"],
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


def main() -> int:
    if not CHART.is_file():
        print("missing chart", CHART, file=sys.stderr)
        return 1
    media = {
        "cht_bar": CHART,
        "cht_line": CHART2 if CHART2.is_file() else CHART,
    }
    if HERO.is_file():
        media["fig_hero"] = HERO

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.mkdir(parents=True, exist_ok=True)

    for structure_id, (pack, slides) in DECKS.items():
        print(f"== {structure_id} · {pack} ==")
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
        for i, src in enumerate(pngs[:6], start=1):
            shutil.copy2(src, dest / f"{i:02d}.png")
        print(f"  wrote {len(list(dest.glob('*.png')))} → {dest}")
    print("done — Liber twins only (no Julius rasters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
