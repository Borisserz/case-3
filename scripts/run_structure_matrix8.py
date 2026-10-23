#!/usr/bin/env python3
"""Full export QA for all 8 Liber structure×pack twins.

For each premium gallery deck:
  IR → pack-colored chart PNGs → slide PNGs → native PPTX → deck PDF

Usage:
  PYTHONPATH=src python3 scripts/run_structure_matrix8.py
"""

from __future__ import annotations

import json
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from case3.deck_theme import resolve_deck_theme  # noqa: E402
from case3.slides_export import build_deck_pdf  # noqa: E402
from case3.slides_lo import write_deck_pdf  # noqa: E402
from case3.slides_pptx_native import build_native_pptx  # noqa: E402
from case3.slides_render import render_deck_pngs  # noqa: E402
from premium_gallery_decks import PREMIUM_DECKS  # noqa: E402
from render_template_previews import _pack_charts  # noqa: E402

OUT = ROOT / "runs" / "structure_matrix8"
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


def _pdf_page_count(pdf: Path) -> int:
    raw = pdf.read_bytes()
    # Cheap count — enough for QA gate
    return max(1, raw.count(b"/Type /Page") - raw.count(b"/Type /Pages"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    failed = 0
    for structure_id, (pack, slides) in PREMIUM_DECKS.items():
        row: dict = {"id": structure_id, "pack": pack, "ok": False}
        case = OUT / structure_id
        case.mkdir(parents=True)
        print(f"== {structure_id} · {pack} ==", flush=True)
        try:
            deck = _deck(pack, slides)
            (case / "deck.json").write_text(
                json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            media = _pack_charts(pack)
            if HERO.is_file():
                media = {**media, "fig_hero": HERO}

            pngs = render_deck_pngs(
                deck,
                work_root=case / "work",
                out_dir=case / "slides",
                chart_png_by_id=media,
                media_png_by_id=media,
            )
            if len(pngs) < 6:
                raise RuntimeError(f"too few slides: {len(pngs)}")

            pptx = case / f"{structure_id}_slides.pptx"
            build_native_pptx(deck, pptx, media_by_id=media)

            pdf = case / f"{structure_id}_deck.pdf"
            _, mode = write_deck_pdf(pptx, pngs, pdf)
            # Guarantee a readable PDF even if LO wrote empty
            if not pdf.is_file() or pdf.stat().st_size < 2000:
                build_deck_pdf(pngs, pdf)
                mode = "png_stitch"

            pages = _pdf_page_count(pdf)
            row.update(
                {
                    "ok": True,
                    "slides": len(pngs),
                    "pptx_kb": pptx.stat().st_size // 1024,
                    "pdf_kb": pdf.stat().st_size // 1024,
                    "pdf_mode": mode,
                    "pdf_pages_est": pages,
                    "pptx": str(pptx.relative_to(ROOT)),
                    "pdf": str(pdf.relative_to(ROOT)),
                }
            )
            print(
                f"  ok · {len(pngs)} slides · pptx {row['pptx_kb']}kb · "
                f"pdf {row['pdf_kb']}kb ({mode})",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 — matrix continues
            failed += 1
            row["error"] = str(exc)
            row["trace"] = traceback.format_exc()[-1200:]
            print(f"  FAIL: {exc}", flush=True)
        summary.append(row)

    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok_n = sum(1 for r in summary if r.get("ok"))
    print(f"\ndone {ok_n}/{len(summary)} · failed={failed} → {OUT / 'summary.json'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
