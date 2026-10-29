#!/usr/bin/env python3
"""Full desk matrix: report + charts + photos + diagram + slides (OpenRouter + CF image).

Writes runs/e2e_full_desk_matrix/summary.json. Exit 0 only if all hard cases pass.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from case3.envfile import load_dotenv
from case3.image_api import probe_image_api
from case3.pipeline import PipelineError, run_pipeline

load_dotenv(ROOT / ".env")
# Prefer shell overrides for matrix caps
os.environ.setdefault("VISION_MAX_TOKENS", "4096")
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    for _c in (
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ):
        if _c.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_c)
            break

OUT_SUMMARY = ROOT / "runs" / "e2e_full_desk_matrix" / "summary.json"

CASES = [
    {
        "id": "R01_charts_pdf",
        "source": ROOT / "fixtures/smoke/01_temp_shares.txt",
        "intent": "Русский отчёт. ОБЯЗАТЕЛЬНО типы: line, donut. Палитра ocean. Без фото.",
        "max_charts": 2,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": {"pdf"},
        "output_mode": "report",
        "expect_charts_min": 1,
        "expect_pdf": True,
    },
    {
        "id": "R02_table_pdf",
        "source": ROOT / "fixtures/smoke/02_wide_table.txt",
        "intent": "Отчёт с широкой таблицей. Без графиков. Без фото.",
        "max_charts": 0,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": {"pdf"},
        "output_mode": "report",
        "expect_charts_min": 0,
        "expect_pdf": True,
    },
    {
        "id": "R03_photo_chart",
        "source": ROOT / "fixtures/smoke/01_temp_shares.txt",
        "intent": (
            "Отчёт: один bar + одна фотоиллюстрация офиса/данных. "
            "ОБЯЗАТЕЛЬНО bar. Палитра atelier."
        ),
        "max_charts": 1,
        "max_images": 1,
        "max_diagrams": 0,
        "formats": {"pdf"},
        "output_mode": "report",
        "expect_charts_min": 1,
        "expect_images_min": 1,
        "expect_pdf": True,
        "require_image_api": True,
    },
    {
        "id": "R04_docx_both",
        "source": ROOT / "fixtures/smoke/04_demo_dense.txt",
        "intent": "Краткий отчёт. ОБЯЗАТЕЛЬНО bar. Палитра sunset. Без фото.",
        "max_charts": 1,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": {"pdf", "docx"},
        "output_mode": "report",
        "expect_charts_min": 1,
        "expect_pdf": True,
        "expect_docx": True,
    },
    {
        "id": "D01_diagram",
        "source": ROOT / "fixtures/smoke/05_process_pipeline.txt",
        "intent": "Режим схема: flowchart процесса Liber. Без графиков Chart.js. Без фото.",
        "max_charts": 0,
        "max_images": 0,
        "max_diagrams": 2,
        "formats": set(),  # diagram mode — no print
        "output_mode": "diagram",
        "expect_diagrams_min": 1,
        "expect_pdf": False,
    },
    {
        "id": "P01_presentation",
        "source": ROOT / "fixtures/smoke/01_temp_shares.txt",
        "intent": "Презентация: 4–6 слайдов, KPI + один график. Без фото.",
        "max_charts": 1,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": set(),
        "output_mode": "presentation",
        "expect_pdf": False,
        "expect_pptx": True,
    },
]


def _audit(out: Path, case: dict) -> dict:
    meta: dict = {}
    if (out / "meta.json").is_file():
        meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    media = meta.get("media_status") or {}
    charts_ok = [
        k
        for k, v in media.items()
        if isinstance(v, dict) and v.get("ok") and v.get("kind") == "chart"
    ]
    figs_ok = [
        k
        for k, v in media.items()
        if isinstance(v, dict) and v.get("ok") and v.get("kind") == "figure"
    ]
    fj: dict = {}
    if (out / "figures.json").is_file():
        try:
            fj = json.loads((out / "figures.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            fj = {}
    diagrams = fj.get("diagrams") if isinstance(fj.get("diagrams"), list) else []
    diagrams_ok = [
        d
        for d in diagrams
        if isinstance(d, dict) and len(str(d.get("mermaid") or d.get("code") or "")) >= 40
    ]
    pdf = next((p for p in out.glob("*.pdf") if "_deck" not in p.name), None)
    docx = next(out.glob("*.docx"), None)
    pptx = next(out.glob("**/*.pptx"), None)
    if pptx is None and (out / "slides").is_dir():
        pptx = next((out / "slides").glob("*.pptx"), None)

    issues: list[str] = []
    if meta.get("status") not in {"ok", "pipeline_ok"} and case.get("expect_pptx"):
        # slides may finish as ok via slides job meta; tolerate running→ok after job
        if meta.get("status") not in {"ok", "pipeline_ok"}:
            issues.append(f"status={meta.get('status')}")
    elif case.get("expect_pdf") and meta.get("status") != "ok":
        issues.append(f"status={meta.get('status')} err={meta.get('error')}")
    elif case.get("output_mode") == "diagram" and meta.get("status") not in {
        "ok",
        "pipeline_ok",
    }:
        issues.append(f"diagram status={meta.get('status')}")

    if len(charts_ok) < int(case.get("expect_charts_min") or 0):
        issues.append(f"charts_ok={len(charts_ok)}<{case.get('expect_charts_min')}")
    if len(figs_ok) < int(case.get("expect_images_min") or 0):
        issues.append(f"figs_ok={len(figs_ok)}<{case.get('expect_images_min')}")
    if len(diagrams_ok) < int(case.get("expect_diagrams_min") or 0):
        issues.append(f"diagrams={len(diagrams_ok)}<{case.get('expect_diagrams_min')}")
    if case.get("expect_pdf") and (pdf is None or pdf.stat().st_size < 1000):
        issues.append("pdf missing/small")
    if case.get("expect_docx") and (docx is None or docx.stat().st_size < 1000):
        issues.append("docx missing/small")
    if case.get("expect_pptx") and (pptx is None or pptx.stat().st_size < 1000):
        issues.append("pptx missing/small")

    return {
        "status": meta.get("status"),
        "stage": meta.get("stage"),
        "error": meta.get("error"),
        "charts_ok": charts_ok,
        "figures_ok": figs_ok,
        "diagrams_n": len(diagrams_ok),
        "pdf_bytes": pdf.stat().st_size if pdf else 0,
        "docx_bytes": docx.stat().st_size if docx else 0,
        "pptx_bytes": pptx.stat().st_size if pptx else 0,
        "issues": issues,
        "ok": not issues,
    }


def run_case(case: dict) -> dict:
    t0 = time.time()
    run_id = f"full_{case['id']}_{int(t0)}"
    row: dict = {"id": case["id"], "run_id": run_id}
    if case.get("require_image_api"):
        ok, err = probe_image_api(timeout_s=3)
        if not ok:
            row.update(
                {
                    "ok": False,
                    "issues": [f"image API required: {err}"],
                    "seconds": 0,
                    "skipped": True,
                }
            )
            return row
    try:
        out = run_pipeline(
            case["source"],
            project_root=ROOT,
            formats=set(case["formats"]),
            intent=case["intent"],
            max_charts=case["max_charts"],
            max_images=case["max_images"],
            max_diagrams=case.get("max_diagrams", 0),
            run_id=run_id,
            output_mode=case.get("output_mode") or "report",
        )
        # Presentation: kick slides job after report/diagram pipeline prep
        if case.get("output_mode") == "presentation" or case.get("expect_pptx"):
            from case3.slides_job import run_slides_job

            run_slides_job(run_id, root=ROOT)
            out = ROOT / "runs" / "out" / run_id
        row.update(_audit(out, case))
        row["out"] = str(out)
    except PipelineError as exc:
        row["ok"] = False
        row["issues"] = [str(exc)[:300]]
        row["status"] = "error"
        row["traceback"] = traceback.format_exc()[-600:]
        if exc.out_dir.is_dir():
            try:
                row.update(
                    {
                        k: v
                        for k, v in _audit(exc.out_dir, case).items()
                        if k not in {"ok", "issues"}
                    }
                )
                # keep PipelineError issues primary
            except Exception:
                pass
    except Exception as exc:
        row["ok"] = False
        row["issues"] = [f"{type(exc).__name__}: {exc}"]
        row["traceback"] = traceback.format_exc()[-600:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


def main() -> int:
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    img_ok, img_err = probe_image_api(timeout_s=3)
    print(f"image_api={'ok' if img_ok else img_err}", flush=True)
    rows = []
    for case in CASES:
        print(f"→ {case['id']} …", flush=True)
        row = run_case(case)
        rows.append(row)
        flag = "OK" if row.get("ok") else "FAIL"
        print(
            f"  {flag} {row.get('seconds')}s "
            f"charts={row.get('charts_ok')} figs={row.get('figures_ok')} "
            f"diag={row.get('diagrams_n')} pdf={row.get('pdf_bytes')} "
            f"pptx={row.get('pptx_bytes')} issues={row.get('issues')}",
            flush=True,
        )
    summary = {
        "image_api_ok": img_ok,
        "pipeline": rows,
        "pass": sum(1 for r in rows if r.get("ok")),
        "total": len(rows),
        "all_ok": all(r.get("ok") for r in rows),
        "git_hint": "pull latest main before Win desk",
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"=== {summary['pass']}/{summary['total']} → {OUT_SUMMARY} ===",
        flush=True,
    )
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
