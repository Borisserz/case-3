#!/usr/bin/env python3
"""Offline freeform deck QA: beat plan → Source-faithful IR → PNG/PPTX/PDF (no LLM)."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from case3.deck_theme import resolve_deck_theme  # noqa: E402
from case3.slides_beat_planner import maybe_apply_pack_hint, plan_beats  # noqa: E402
from case3.slides_ir import parse_deck_ir  # noqa: E402
from case3.slides_job import (  # noqa: E402
    _materialize_deck_artifacts,
    _read_meta,
    _write_meta,
)
from case3.slides_media import (  # noqa: E402
    collect_run_media,
    load_figures_json,
    numbers_from_media_json,
)

OUT = ROOT / "runs" / "freeform_offline"
CASES = [
    ("perf", "audit_M01_line_donut_ocean"),
    ("dense", "e2e_S04_dense_bar"),
    ("shares", "e2e_S01_shares_charts"),
]


def _build_slides(plan, source: str, cids: list[str]) -> list[dict]:
    nums = re.findall(r"\d+(?:[.,]\d+)?", source)[:16]
    # Prefer non chrome-looking nums for KPI values
    vals = [n for n in nums if not re.fullmatch(r"0\d{1,2}", n)] or nums or ["—"]

    def kpi(i: int, label: str) -> dict:
        return {"label": label, "value": str(vals[i % len(vals)])}

    slides: list[dict] = []
    ci = 0
    for i, lay in enumerate(plan.beats):
        sid = f"s{i + 1:02d}"
        if lay == "title":
            line = (source.split(".")[0] if source else "Overview").strip()[:80]
            slides.append(
                {
                    "id": sid,
                    "layout": "title",
                    "title": "Run readout",
                    "takeaway": line or "Overview",
                }
            )
        elif lay == "closing":
            slides.append(
                {
                    "id": sid,
                    "layout": "closing",
                    "title": "Next steps",
                    "takeaway": f"{vals[0]} — headline to defend",
                    "bullets": [
                        "Confirm owners",
                        "Track gates",
                        "Re-check Source numbers",
                    ],
                }
            )
        elif lay == "scorecard":
            slides.append(
                {
                    "id": sid,
                    "layout": "scorecard",
                    "title": "Headline metrics",
                    "kpis": [
                        kpi(0, "A"),
                        kpi(1, "B"),
                        kpi(2, "C"),
                        kpi(3, "D"),
                    ],
                }
            )
        elif lay in ("chart_hero", "chart_split"):
            if not cids:
                slides.append(
                    {
                        "id": sid,
                        "layout": "callout",
                        "title": "Signal",
                        "term": "NOTE",
                        "definition": "No chart in run",
                    }
                )
            else:
                cid = cids[ci % len(cids)]
                ci += 1
                s: dict = {
                    "id": sid,
                    "layout": lay,
                    "title": "Trend from chart",
                    "chart_id": cid,
                    "caption": "Insight from chart series",
                }
                if lay == "chart_split":
                    s["body"] = "Read the series against the plan."
                slides.append(s)
        elif lay == "table_hero":
            slides.append(
                {
                    "id": sid,
                    "layout": "table_hero",
                    "title": "Breakdown",
                    "rows": [
                        ["Item", "Value"],
                        ["A", vals[0]],
                        ["B", vals[1 % len(vals)]],
                    ],
                }
            )
        elif lay == "card_row":
            slides.append(
                {
                    "id": sid,
                    "layout": "card_row",
                    "title": "Three moves",
                    "cards": [
                        {"kicker": "01", "title": "Move one", "body": "Owned next step"},
                        {"kicker": "02", "title": "Move two", "body": "Owned next step"},
                        {"kicker": "03", "title": "Move three", "body": "Owned next step"},
                    ],
                }
            )
        elif lay == "callout":
            slides.append(
                {
                    "id": sid,
                    "layout": "callout",
                    "title": "Decision",
                    "term": "ASK",
                    "definition": "Approve the next gate from Source",
                }
            )
        elif lay == "section":
            slides.append(
                {
                    "id": sid,
                    "layout": "section",
                    "chapter": min(9, max(1, i // 3 or 1)),
                    "title": "Chapter",
                }
            )
        elif lay == "bullets":
            slides.append(
                {
                    "id": sid,
                    "layout": "bullets",
                    "title": "Notes",
                    "bullets": [
                        "Keep numbers in Source",
                        "Name an owner",
                        "Set a date",
                    ],
                }
            )
        else:
            slides.append(
                {
                    "id": sid,
                    "layout": "callout",
                    "title": lay,
                    "term": "NOTE",
                    "definition": lay,
                }
            )
    return slides


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, src_name in CASES:
        src = ROOT / "runs" / "out" / src_name
        run_id = f"freeform_off_{label}"
        dest = ROOT / "runs" / "out" / run_id
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir()
        shutil.copy2(src / "meta.json", dest / "meta.json")
        shutil.copy2(src / "figures.json", dest / "figures.json")
        if (src / "figures").is_dir():
            shutil.copytree(src / "figures", dest / "figures")
        raw = sorted(src.glob("*.raw_model.txt"))
        source = (
            raw[0].read_text(encoding="utf-8", errors="replace")[:8000]
            if raw
            else "Metrics 10 20 30"
        )
        fj = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
        caps = "\n".join(
            str(c.get("caption") or "")
            for c in (fj.get("charts") or [])
            if isinstance(c, dict)
        )
        source = source + "\n" + caps + "\n10 20 30 40 50"
        (dest / "source.txt").write_text(source, encoding="utf-8")
        (dest / "intent.txt").write_text(
            "Freeform offline beat materialize", encoding="utf-8"
        )
        cids = [
            str(c.get("id"))
            for c in (fj.get("charts") or [])
            if isinstance(c, dict) and c.get("html")
        ]
        plan = plan_beats(
            source=source,
            intent="freeform",
            chart_ids=cids,
            figure_ids=[],
            diagram_ids=[],
            structure_id=None,
        )
        pack = maybe_apply_pack_hint(
            structure_id=None,
            current_pack="atelier",
            plan=plan,
            pack_explicit=False,
        )
        tok = resolve_deck_theme(pack)
        slides = _build_slides(plan, source, cids)
        ir = {
            "version": 1,
            "aspect": "16:9",
            "language": "en",
            "palette": "atelier",
            "slides": slides,
        }
        allowed = numbers_from_media_json(load_figures_json(dest))
        deck = parse_deck_ir(
            ir,
            source=source,
            allowed_media_ids=frozenset(cids),
            allowed_number_strings=allowed,
        )
        deck["theme_id"] = tok.pack_id
        deck["style"] = tok.as_dict()
        meta = _read_meta(dest)
        meta["status"] = "ok"
        meta["run_id"] = run_id
        meta["slides_style"] = {"theme_pack": pack, "structure_id": None}
        meta["slides_beat"] = {
            "mode": plan.mode,
            "pack_hint": plan.pack_hint,
            "beats": list(plan.beats),
        }
        _write_meta(dest, meta)
        chart_ids, _, _, png_by_id, diagram_specs = collect_run_media(dest, meta)
        _materialize_deck_artifacts(
            dest,
            meta,
            deck=deck,
            palette="atelier",
            chart_ids=chart_ids,
            png_by_id=png_by_id,
            diagram_specs=diagram_specs,
            logs_dir=None,
        )
        meta = _read_meta(dest)
        art = meta.get("slides_artifacts") or {}
        layouts = [s["layout"] for s in deck["slides"]]
        case = OUT / label
        if case.exists():
            shutil.rmtree(case)
        case.mkdir(parents=True)
        for k in ("pptx", "deck_pdf"):
            n = art.get(k)
            if n and (dest / n).is_file():
                shutil.copy2(dest / n, case / n)
        shutil.copy2(dest / "slides" / "deck.json", case / "deck.json")
        for p in sorted((dest / "slides").glob("slide_*.png"))[:2]:
            shutil.copy2(p, case / p.name)
        if list((dest / "slides").glob("slide_*.png")):
            last = sorted((dest / "slides").glob("slide_*.png"))[-1]
            shutil.copy2(last, case / "slide_last.png")
        row = {
            "label": label,
            "status": meta.get("slides_status"),
            "mode": plan.mode,
            "pack": pack,
            "slides": len(layouts),
            "distinct": sorted(set(layouts)),
            "pdf_mode": art.get("deck_pdf_mode"),
            "pdf_kb": (
                (case / art["deck_pdf"]).stat().st_size // 1024
                if art.get("deck_pdf") and (case / art["deck_pdf"]).is_file()
                else 0
            ),
        }
        print(row, flush=True)
        rows.append(row)
    (OUT / "summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = sum(1 for r in rows if r.get("status") == "ok")
    print(f"offline {ok}/{len(rows)} → {OUT / 'summary.json'}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
