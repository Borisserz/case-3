#!/usr/bin/env python3
"""Run live LLM slides jobs on 10 real ok runs. Needs VISION_* in .env."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

# Load .env lightly
env_path = ROOT / ".env"
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)

from case3.slides_job import run_slides_job  # noqa: E402

OUT = ROOT / "runs" / "out"
REPORT = ROOT / "runs" / "slides_live10" / "summary.json"

# Diverse ok runs: charts, photos, diagrams
CANDIDATES = [
    "source_20261021T145955Z",  # charts + fig
    "audit_E06_release_mind_timeline",  # chart + mindmap/timeline
    "audit_T05_kitchen_sink",  # charts + flowchart/sequence
    "audit_E04_support_seq_table",  # chart + sequence
    "audit_M01_line_donut_ocean",
    "audit_M02_bar_kpi_atelier",
    "audit_M03_area_hbar_sunset",
    "audit_M04_grouped_stacked_mono",
    "audit_M05_scatter_line_editorial",
    "e2e_S05_photo_bar",
]


def _ok_run(rid: str) -> bool:
    meta = OUT / rid / "meta.json"
    if not meta.is_file():
        return False
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("status") == "ok"


def main() -> int:
    os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
    runs = [r for r in CANDIDATES if _ok_run(r)]
    if len(runs) < 10:
        # fill from recent ok runs with figures png
        for d in sorted(OUT.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not d.is_dir() or d.name in runs:
                continue
            if not _ok_run(d.name):
                continue
            figs = d / "figures"
            if figs.is_dir() and any(figs.glob("cht_*.png")):
                runs.append(d.name)
            if len(runs) >= 10:
                break
    runs = runs[:10]
    if len(runs) < 10:
        print(f"WARNING: only {len(runs)} ok runs found", flush=True)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for i, rid in enumerate(runs, 1):
        print(f"[{i}/{len(runs)}] LIVE slides {rid} …", flush=True)
        t0 = time.time()
        try:
            run_slides_job(rid, root=ROOT)
            meta = json.loads((OUT / rid / "meta.json").read_text(encoding="utf-8"))
            st = meta.get("slides_status")
            art = meta.get("slides_artifacts") or {}
            err = meta.get("slides_error")
            row = {
                "run_id": rid,
                "status": st,
                "slides": art.get("png_count"),
                "pptx": art.get("pptx"),
                "error": err,
                "sec": round(time.time() - t0, 1),
            }
        except Exception as exc:  # noqa: BLE001
            row = {
                "run_id": rid,
                "status": "exception",
                "error": str(exc),
                "sec": round(time.time() - t0, 1),
            }
        results.append(row)
        print(f"    → {row.get('status')} · {row.get('slides')} slides · {row.get('sec')}s", flush=True)
        if row.get("error"):
            print(f"       err: {row['error'][:200]}", flush=True)

    ok = sum(1 for r in results if r.get("status") == "ok")
    summary = {"ok": ok, "total": len(results), "cases": results}
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
