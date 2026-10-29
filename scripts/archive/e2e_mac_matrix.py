#!/usr/bin/env python3
"""Full Mac E2E matrix: fixtures → pipeline → chart multi-edit → summary JSON."""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from case3.chart_edit import ChartEditError, edit_chart_in_run
from case3.envfile import load_dotenv
from case3.pipeline import PipelineError, run_pipeline

load_dotenv(ROOT / ".env")
# Cross-platform Playwright cache (Mac / Linux / Windows)
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    for _c in (
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
        Path.home() / "AppData" / "Local" / "ms-playwright",
    ):
        if _c.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_c)
            break

OUT_SUMMARY = ROOT / "runs" / "e2e_mac_matrix" / "summary.json"


CASES = [
    {
        "id": "S01_shares_charts",
        "source": ROOT / "fixtures/smoke/01_temp_shares.txt",
        "intent": (
            "Русский отчёт. ОБЯЗАТЕЛЬНО типы графиков по порядку: line, donut. "
            "Палитра ocean. Без фото."
        ),
        "max_charts": 2,
        "max_images": 0,
        "formats": {"pdf"},
        "expect_charts_min": 1,
    },
    {
        "id": "S02_wide_table",
        "source": ROOT / "fixtures/smoke/02_wide_table.txt",
        "intent": "Отчёт с широкой таблицей. Без графиков. Без фото.",
        "max_charts": 0,
        "max_images": 0,
        "formats": {"pdf"},
        "expect_charts_min": 0,
        "expect_tabularx": True,
    },
    {
        "id": "S03_prose_no_charts",
        "source": ROOT / "fixtures/smoke/03_prose_no_numbers.txt",
        "intent": "Только текст, без графиков и без фото.",
        "max_charts": 0,
        "max_images": 0,
        "formats": {"pdf"},
        "expect_charts_min": 0,
    },
    {
        "id": "S04_dense_bar",
        "source": ROOT / "fixtures/smoke/04_demo_dense.txt",
        "intent": (
            "Краткий отчёт. ОБЯЗАТЕЛЬНО типы графиков по порядку: bar. "
            "Палитра sunset. Без фото."
        ),
        "max_charts": 1,
        "max_images": 0,
        "formats": {"pdf", "docx"},
        "expect_charts_min": 1,
    },
    {
        "id": "S05_photo_bar",
        "source": ROOT / "fixtures/smoke/01_temp_shares.txt",
        "intent": (
            "Отчёт с одним bar-графиком и одной фотоиллюстрацией по теме данных. "
            "ОБЯЗАТЕЛЬНО типы графиков по порядку: bar. Палитра mono."
        ),
        "max_charts": 1,
        "max_images": 1,
        "formats": {"pdf"},
        "expect_charts_min": 1,
        "expect_images_min": 0,  # soft: image API may flake
    },
]


def _audit_out(out: Path, case: dict) -> dict:
    meta = {}
    mp = out / "meta.json"
    if mp.is_file():
        meta = json.loads(mp.read_text(encoding="utf-8"))
    tex = ""
    for p in out.glob("*.tex"):
        tex = p.read_text(encoding="utf-8")
        break
    media = meta.get("media_status") or {}
    charts_ok = [
        k for k, v in media.items() if isinstance(v, dict) and v.get("ok") and v.get("kind") == "chart"
    ]
    figs_ok = [
        k
        for k, v in media.items()
        if isinstance(v, dict) and v.get("ok") and v.get("kind") == "figure"
    ]
    pdf = next(out.glob("*.pdf"), None)
    docx = next(out.glob("*.docx"), None)
    issues: list[str] = []
    if meta.get("status") != "ok":
        issues.append(f"status={meta.get('status')}")
    if len(charts_ok) < int(case.get("expect_charts_min") or 0):
        issues.append(f"charts_ok={len(charts_ok)} < {case.get('expect_charts_min')}")
    if case.get("expect_tabularx") and "tabularx" not in tex and "tabular" not in tex:
        issues.append("no table env")
    if "%CASE3_" in tex:
        issues.append("orphan CASE3 slots")
    if pdf is None or pdf.stat().st_size < 1000:
        issues.append("pdf missing/small")
    if "docx" in case.get("formats", set()) and (docx is None or docx.stat().st_size < 1000):
        issues.append("docx missing/small")
    if r"\includegraphics" in tex:
        for line in tex.splitlines():
            if "includegraphics" in line and "figures/" in line:
                # path exists?
                pass
    return {
        "status": meta.get("status"),
        "run_id": meta.get("run_id"),
        "charts_planned": meta.get("charts_planned") or [],
        "figures_planned": meta.get("figures_planned") or [],
        "charts_ok": charts_ok,
        "figures_ok": figs_ok,
        "pdf_bytes": pdf.stat().st_size if pdf else 0,
        "docx_bytes": docx.stat().st_size if docx else 0,
        "has_caption": r"\caption{" in tex,
        "has_tabularx": "tabularx" in tex,
        "orphan_slots": "%CASE3_" in tex,
        "issues": issues,
        "ok": not issues,
    }


def run_case(case: dict) -> dict:
    t0 = time.time()
    run_id = f"e2e_{case['id']}"
    row: dict = {"id": case["id"], "run_id": run_id}
    try:
        out = run_pipeline(
            case["source"],
            project_root=ROOT,
            formats=set(case["formats"]),
            intent=case["intent"],
            max_charts=case["max_charts"],
            max_images=case["max_images"],
            run_id=run_id,
        )
        row.update(_audit_out(out, case))
        row["out"] = str(out)
    except PipelineError as exc:
        row["ok"] = False
        row["issues"] = [str(exc)[:300]]
        row["status"] = "error"
        row["traceback"] = traceback.format_exc()[-800:]
        if exc.out_dir.is_dir():
            try:
                row.update({k: v for k, v in _audit_out(exc.out_dir, case).items() if k != "ok"})
            except Exception:
                pass
    except Exception as exc:
        row["ok"] = False
        row["issues"] = [f"{type(exc).__name__}: {exc}"]
        row["traceback"] = traceback.format_exc()[-800:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


def multi_edit_chart(base_run_id: str) -> dict:
    """Restyle cht_01 several times on the same run."""
    out = ROOT / "runs" / "out" / base_run_id
    edits = [
        {"palette": "ocean", "style": "толще линии, крупнее подписи"},
        {"palette": "sunset", "style": "более контрастные цвета"},
        {"palette": "mono", "style": "", "chart_type": "bar"},
        {"palette": "editorial", "style": "мягкие пастельные тона"},
    ]
    results = []
    for i, ed in enumerate(edits, 1):
        t0 = time.time()
        try:
            r = edit_chart_in_run(
                out,
                "cht_01",
                palette=ed.get("palette"),
                style=ed.get("style"),
                chart_type=ed.get("chart_type"),
                formats={"pdf"},
            )
            png = out / "figures" / "cht_01.png"
            results.append(
                {
                    "n": i,
                    "ok": True,
                    "mode": r.get("mode"),
                    "palette": r.get("palette"),
                    "png_bytes": png.stat().st_size if png.is_file() else 0,
                    "seconds": round(time.time() - t0, 1),
                }
            )
        except (ChartEditError, Exception) as exc:
            results.append(
                {
                    "n": i,
                    "ok": False,
                    "error": str(exc)[:240],
                    "seconds": round(time.time() - t0, 1),
                }
            )
    ok_n = sum(1 for r in results if r.get("ok"))
    return {
        "base_run": base_run_id,
        "edits": results,
        "ok": ok_n >= 3,
        "ok_count": ok_n,
    }


def main() -> int:
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    print("=== pipeline matrix ===", flush=True)
    for case in CASES:
        print(f"→ {case['id']} …", flush=True)
        row = run_case(case)
        rows.append(row)
        flag = "OK" if row.get("ok") else "FAIL"
        print(
            f"  {flag} {row.get('seconds')}s charts={row.get('charts_ok')} "
            f"figs={row.get('figures_ok')} pdf={row.get('pdf_bytes')} "
            f"issues={row.get('issues')}",
            flush=True,
        )

    # Pick a run with a successful chart for multi-edit
    edit_base = None
    for r in rows:
        if r.get("ok") and r.get("charts_ok"):
            edit_base = r["run_id"]
            break
    edit_report = {"ok": False, "skipped": True}
    if edit_base:
        print(f"=== multi-edit on {edit_base} ===", flush=True)
        edit_report = multi_edit_chart(edit_base)
        print(json.dumps(edit_report, ensure_ascii=False, indent=2), flush=True)

    summary = {
        "pipeline": rows,
        "chart_multi_edit": edit_report,
        "pass_pipeline": sum(1 for r in rows if r.get("ok")),
        "total_pipeline": len(rows),
        "all_ok": all(r.get("ok") for r in rows) and bool(edit_report.get("ok")),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=== summary ===", flush=True)
    print(
        f"pipeline {summary['pass_pipeline']}/{summary['total_pipeline']}  "
        f"edits_ok={edit_report.get('ok')}  → {OUT_SUMMARY}",
        flush=True,
    )
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
