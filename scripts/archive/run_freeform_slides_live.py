#!/usr/bin/env python3
"""Live freeform slides (no structure template) on real ok runs.

Usage:
  PYTHONPATH=src python3 scripts/run_freeform_slides_live.py
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import os  # noqa: E402

from case3.envfile import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
# Live freeform decks can be long — give the Vision proxy more headroom.
os.environ.setdefault("VISION_TIMEOUT_S", "600")
# Cap completion size so low OpenRouter credit balances still accept the request.
# (load_dotenv override=True would clobber a shell export — set after load.)
_cap = os.environ.get("VISION_MAX_TOKENS", "").strip()
if not _cap or int(_cap) > 8192:
    os.environ["VISION_MAX_TOKENS"] = "6144"

from case3.slides_beat_planner import plan_beats  # noqa: E402
from case3.slides_job import run_slides_job  # noqa: E402

OUT = ROOT / "runs" / "freeform_slides_live"
CASES = [
    # (label, source_run_id_or_path under runs/out)
    ("perf_charts", "audit_M01_line_donut_ocean"),
    ("dense_bar", "e2e_S04_dense_bar"),
    ("shares", "e2e_S01_shares_charts"),
]


def _prepare(label: str, src_name: str) -> Path:
    src = ROOT / "runs" / "out" / src_name
    if not src.is_dir():
        raise FileNotFoundError(src)
    run_id = f"freeform_{label}_{int(time.time())}"
    dest = ROOT / "runs" / "out" / run_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in ("meta.json", "figures.json"):
        shutil.copy2(src / name, dest / name)
    if (src / "figures").is_dir():
        shutil.copytree(src / "figures", dest / "figures")
    for name in ("source.txt", "intent.txt", "source.md", "intent.md"):
        if (src / name).is_file():
            shutil.copy2(src / name, dest / name)
    # Prefer real Source from meta path (never TeX/raw_model as Source).
    meta_preview = json.loads((dest / "meta.json").read_text(encoding="utf-8"))
    src_path = meta_preview.get("source")
    if isinstance(src_path, str) and src_path.strip():
        sp = Path(src_path)
        if sp.is_file() and not (dest / "source.txt").is_file():
            shutil.copy2(sp, dest / "source.txt")
    if not any((dest / n).is_file() for n in ("source.txt", "source.md")):
        # Fall back: chart captions as Source so numbers validate
        fj = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
        caps = []
        for ch in fj.get("charts") or []:
            if isinstance(ch, dict):
                caps.append(str(ch.get("caption") or ch.get("id") or ""))
        (dest / "source.txt").write_text(
            "Liber run facts.\n" + "\n".join(caps),
            encoding="utf-8",
        )
    if not (dest / "intent.txt").is_file():
        (dest / "intent.txt").write_text(
            "Freeform executive deck — no structure template.",
            encoding="utf-8",
        )
    meta = json.loads((dest / "meta.json").read_text(encoding="utf-8"))
    meta["run_id"] = run_id
    meta["status"] = "ok"
    # No template: atelier default, no structure
    meta["slides_style"] = {
        "theme_pack": "atelier",
        "structure_id": None,
        "style_settings": None,
    }
    meta["slides_theme_pack"] = "atelier"
    meta["slides_structure_id"] = None
    meta.pop("slides_pack_explicit", None)
    (dest / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return dest


def _analyze(out_dir: Path) -> dict:
    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    art = meta.get("slides_artifacts") or {}
    deck_path = out_dir / "slides" / "deck.json"
    layouts: list[str] = []
    if deck_path.is_file():
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
        layouts = [
            str(s.get("layout"))
            for s in (deck.get("slides") or [])
            if isinstance(s, dict)
        ]
    pdf = out_dir / str(art.get("deck_pdf") or "")
    pptx = out_dir / str(art.get("pptx") or "")
    return {
        "run_id": out_dir.name,
        "status": meta.get("slides_status"),
        "error": meta.get("slides_error"),
        "beat": meta.get("slides_beat"),
        "png_count": art.get("png_count"),
        "pdf_mode": art.get("deck_pdf_mode"),
        "pdf_kb": pdf.stat().st_size // 1024 if pdf.is_file() else 0,
        "pptx_kb": pptx.stat().st_size // 1024 if pptx.is_file() else 0,
        "layouts": layouts,
        "n_layouts": len(layouts),
        "distinct": sorted(set(layouts)),
        "pack": (meta.get("slides_beat") or {}).get("pack_applied")
        or (deck.get("theme_id") if deck_path.is_file() else None),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, src in CASES:
        print(f"\n== {label} ← {src} ==", flush=True)
        try:
            dest = _prepare(label, src)
            source = ""
            for n in ("source.txt", "source.md"):
                if (dest / n).is_file():
                    source = (dest / n).read_text(encoding="utf-8", errors="replace")[
                        :2000
                    ]
                    break
            intent = ""
            if (dest / "intent.txt").is_file():
                intent = (dest / "intent.txt").read_text(
                    encoding="utf-8", errors="replace"
                )[:500]
            fj = json.loads((dest / "figures.json").read_text(encoding="utf-8"))
            cids = [
                str(c.get("id"))
                for c in (fj.get("charts") or [])
                if isinstance(c, dict) and c.get("html")
            ]
            preview = plan_beats(
                source=source,
                intent=intent,
                chart_ids=cids,
                figure_ids=[],
                diagram_ids=[],
            )
            print(
                f"  beat preview: {preview.mode} / {preview.pack_hint} / "
                f"{len(preview.beats)} beats",
                flush=True,
            )
            t0 = time.time()
            run_slides_job(dest.name, root=ROOT)
            sec = round(time.time() - t0, 1)
            row = _analyze(dest)
            row["sec"] = sec
            row["label"] = label
            # copy artifacts
            case_out = OUT / label
            if case_out.exists():
                shutil.rmtree(case_out)
            case_out.mkdir(parents=True)
            for key in ("pptx", "deck_pdf"):
                name = (json.loads((dest / "meta.json").read_text()).get(
                    "slides_artifacts"
                )
                or {}).get(key)
                if name and (dest / name).is_file():
                    shutil.copy2(dest / name, case_out / name)
            if (dest / "slides" / "deck.json").is_file():
                shutil.copy2(dest / "slides" / "deck.json", case_out / "deck.json")
            # first + chart-ish slide PNGs
            pngs = sorted((dest / "slides").glob("slide_*.png"))
            for i, p in enumerate(pngs[:3]):
                shutil.copy2(p, case_out / p.name)
            if pngs:
                shutil.copy2(pngs[-1], case_out / "slide_last.png")
            print(
                f"  → {row['status']} · {row['n_layouts']} slides · "
                f"distinct={row['distinct']} · pack={row.get('pack')} · "
                f"pdf={row['pdf_mode']} {row['pdf_kb']}kb · {sec}s",
                flush=True,
            )
            if row.get("error"):
                print(f"  error: {row['error']}", flush=True)
            rows.append(row)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {exc}", flush=True)
            rows.append({"label": label, "status": "error", "error": str(exc)})

    (OUT / "summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = sum(1 for r in rows if r.get("status") == "ok")
    print(f"\ndone {ok}/{len(rows)} → {OUT / 'summary.json'}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
