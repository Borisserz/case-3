#!/usr/bin/env python3
"""Full Liber Atelier audit: ~30 pipeline probes → charts/diagrams/TeX/PDF/DOCX.

Writes:
  runs/full_audit_oct21/summary.json
  docs/audits/2026-10-21-full-audit-findings.md  (caller may overwrite with richer text)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from case3.chart_edit import ChartEditError, edit_chart_in_run
from case3.chart_html import CHART_TYPES
from case3.diagrams import DIAGRAM_TYPES
from case3.envfile import load_dotenv
from case3.pipeline import PipelineError, run_pipeline

load_dotenv(ROOT / ".env")
# Cross-platform Playwright cache (Mac / Linux / Windows)
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    for c in (
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
        Path.home() / "AppData" / "Local" / "ms-playwright",
    ):
        if c.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(c)
            break

OUT_DIR = ROOT / "runs" / "full_audit_oct21"
OUT_SUMMARY = OUT_DIR / "summary.json"
SMOKE = ROOT / "fixtures" / "smoke"

PURPLE_RE = re.compile(
    r"#(?:[89a-fA-F][0-9a-fA-F]{2}|[bB][0-9a-fA-F]{2})[0-9a-fA-F]{3}"
    r"|purple|violet|indigo|#6[Bb]2[1-9a-fA-F]{3}|#7[Cc]3?[Aa][Ee][Dd]",
    re.I,
)


def _cases() -> list[dict]:
    """30 probes covering charts, palettes, diagrams, tables, formats, edges."""
    s01 = SMOKE / "01_temp_shares.txt"
    s02 = SMOKE / "02_wide_table.txt"
    s03 = SMOKE / "03_prose_no_numbers.txt"
    s04 = SMOKE / "04_demo_dense.txt"
    s05 = SMOKE / "05_process_pipeline.txt"
    s06 = SMOKE / "06_product_release.txt"
    s07 = SMOKE / "07_support_flow.txt"
    s08 = SMOKE / "08_scatter_pairs.txt"

    cases: list[dict] = []

    # --- 1–9: each whitelist chart type alone ---
    chart_sources = {
        "bar": (s04, "bar"),
        "grouped_bar": (s04, "grouped_bar"),
        "stacked_bar": (s04, "stacked_bar"),
        "line": (s01, "line"),
        "horizontal_bar": (s01, "horizontal_bar"),
        "donut": (s01, "donut"),
        "kpi": (s04, "kpi"),
        "area": (s04, "area"),
        "scatter": (s08, "scatter"),
    }
    palettes_cycle = ["atelier", "ocean", "sunset", "mono", "editorial", "atelier", "ocean", "sunset", "editorial"]
    for i, (ctype, (src, _)) in enumerate(chart_sources.items()):
        cases.append(
            {
                "id": f"C{i+1:02d}_chart_{ctype}",
                "source": src,
                "intent": (
                    f"Русский краткий отчёт. ОБЯЗАТЕЛЬНО один график типа {ctype}. "
                    f"Палитра {palettes_cycle[i]}. Без фото. Без схем."
                ),
                "max_charts": 1,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 1,
                "expect_chart_types": [ctype],
            }
        )

    # --- 10–14: multi-chart + palette stress ---
    cases.extend(
        [
            {
                "id": "M01_line_donut_ocean",
                "source": s01,
                "intent": (
                    "Русский отчёт. ОБЯЗАТЕЛЬНО типы: line, donut. Палитра ocean. "
                    "Без фото. Без схем."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf", "docx"},
                "expect_charts_min": 2,
            },
            {
                "id": "M02_bar_kpi_atelier",
                "source": s04,
                "intent": (
                    "Отчёт. ОБЯЗАТЕЛЬНО типы: bar, kpi. Палитра atelier. Без фото. Без схем."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 1,
            },
            {
                "id": "M03_area_hbar_sunset",
                "source": s06,
                "intent": (
                    "Квартальный обзор. ОБЯЗАТЕЛЬНО типы: area, horizontal_bar. "
                    "Палитра sunset. Без фото. Без схем."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 1,
            },
            {
                "id": "M04_grouped_stacked_mono",
                "source": s04,
                "intent": (
                    "Демография. ОБЯЗАТЕЛЬНО типы: grouped_bar, stacked_bar. "
                    "Палитра mono. Без фото. Без схем."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 1,
            },
            {
                "id": "M05_scatter_line_editorial",
                "source": s08,
                "intent": (
                    "Маркетинг. ОБЯЗАТЕЛЬНО типы: scatter, line. Палитра editorial. "
                    "Без фото. Без схем."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf", "docx"},
                "expect_charts_min": 1,
            },
        ]
    )

    # --- 15–19: Mermaid diagram types (Liber UI-only) ---
    diag_specs = [
        ("flowchart", s05, "flowchart TD процесса Liber"),
        ("sequence", s07, "sequenceDiagram актёров поддержки"),
        ("mindmap", s06, "mindmap рисков и каналов релиза"),
        ("timeline", s06, "timeline этапов discovery→GA"),
        ("stateDiagram", s07, "stateDiagram статусов тикета"),
    ]
    for dtype, src, hint in diag_specs:
        cases.append(
            {
                "id": f"D_{dtype}",
                "source": src,
                "intent": (
                    f"Русский отчёт со структурой. ОБЯЗАТЕЛЬНО Mermaid-схема type={dtype}: {hint}. "
                    "Без графиков. Без фото. Схемы только в Liber (не в TeX)."
                ),
                "max_charts": 0,
                "max_images": 0,
                "max_diagrams": 2,
                "formats": {"pdf"},
                "expect_charts_min": 0,
                "expect_diagrams_min": 1,
                "expect_diagram_types": [dtype],
            }
        )

    # --- 20–24: structure / tables / formats / edges ---
    cases.extend(
        [
            {
                "id": "T01_wide_table",
                "source": s02,
                "intent": "Широкая сравнительная таблица tabularx на A4. Без графиков. Без схем. Без фото.",
                "max_charts": 0,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf", "docx"},
                "expect_charts_min": 0,
                "expect_tabularx": True,
            },
            {
                "id": "T02_prose_only",
                "source": s03,
                "intent": "Только проза и списки. Без графиков, схем и фото. Без выдуманных чисел.",
                "max_charts": 0,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 0,
            },
            {
                "id": "T03_docx_only",
                "source": s01,
                "intent": "Краткий отчёт. ОБЯЗАТЕЛЬНО тип: bar. Палитра ocean. Без схем. Без фото.",
                "max_charts": 1,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"docx"},
                "expect_charts_min": 1,
            },
            {
                "id": "T04_pdf_only_full",
                "source": s06,
                "intent": (
                    "Полный обзор: разделы, таблица KPI, 2 графика (line, donut), "
                    "1 flowchart-схема. Палитра atelier. Без фото."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 1,
                "formats": {"pdf"},
                "expect_charts_min": 1,
                "expect_diagrams_min": 1,
            },
            {
                "id": "T05_kitchen_sink",
                "source": s06,
                "intent": (
                    "Максимальный отчёт: оглавление-логика (разделы), таблица, "
                    "графики bar+line, схемы flowchart+sequence, палитра sunset. Без фото."
                ),
                "max_charts": 2,
                "max_images": 0,
                "max_diagrams": 2,
                "formats": {"pdf", "docx"},
                "expect_charts_min": 1,
                "expect_diagrams_min": 1,
            },
        ]
    )

    # --- 25–28: photos / dry-run / forbid / auto ---
    cases.extend(
        [
            {
                "id": "E01_with_photo",
                "source": s01,
                "intent": (
                    "Отчёт с bar-графиком и одной фотоиллюстрацией по теме данных. "
                    "ОБЯЗАТЕЛЬНО тип: bar. Палитра mono. Без схем."
                ),
                "max_charts": 1,
                "max_images": 1,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 1,
                "expect_images_min": 0,  # soft
            },
            {
                "id": "E02_dry_run",
                "source": s01,
                "intent": "Dry-run проверка: bar + ocean. Без фото.",
                "max_charts": 1,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "dry_run": True,
                "expect_charts_min": 0,
                "expect_status": "ok",
            },
            {
                "id": "E03_no_diagrams_explicit",
                "source": s05,
                "intent": "Опиши процесс текстом. Без схем. Без графиков. Без фото.",
                "max_charts": 0,
                "max_images": 0,
                "max_diagrams": 0,
                "formats": {"pdf"},
                "expect_charts_min": 0,
                "expect_diagrams_min": 0,
                "expect_diagrams_max": 0,
            },
            {
                "id": "E04_support_seq_table",
                "source": s07,
                "intent": (
                    "Отчёт поддержки: таблица SLA, donut по метрикам, "
                    "sequenceDiagram эскалации. Палитра ocean. Без фото."
                ),
                "max_charts": 1,
                "max_images": 0,
                "max_diagrams": 1,
                "formats": {"pdf", "docx"},
                "expect_charts_min": 1,
                "expect_diagrams_min": 1,
            },
        ]
    )

    # --- 29–30: process + release coverage ---
    cases.extend(
        [
            {
                "id": "E05_process_flow_state",
                "source": s05,
                "intent": (
                    "Технический обзор пайплайна: flowchart шагов + stateDiagram статусов run. "
                    "Без графиков. Без фото. Палитра atelier."
                ),
                "max_charts": 0,
                "max_images": 0,
                "max_diagrams": 2,
                "formats": {"pdf"},
                "expect_diagrams_min": 1,
            },
            {
                "id": "E06_release_mind_timeline",
                "source": s06,
                "intent": (
                    "Релиз Desk Notes: mindmap рисков + timeline этапов + line по выручке. "
                    "Палитра editorial. Без фото."
                ),
                "max_charts": 1,
                "max_images": 0,
                "max_diagrams": 2,
                "formats": {"pdf"},
                "expect_charts_min": 1,
                "expect_diagrams_min": 1,
            },
        ]
    )

    assert len(cases) == 30, f"expected 30 cases, got {len(cases)}"
    return cases


def _audit_out(out: Path, case: dict) -> dict:
    meta: dict = {}
    mp = out / "meta.json"
    if mp.is_file():
        meta = json.loads(mp.read_text(encoding="utf-8"))
    fj: dict = {}
    fjp = out / "figures.json"
    if fjp.is_file():
        fj = json.loads(fjp.read_text(encoding="utf-8"))

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

    charts_meta = fj.get("charts") or []
    chart_types_got = [
        c.get("type") for c in charts_meta if isinstance(c, dict) and c.get("type")
    ]
    diagrams = fj.get("diagrams") or meta.get("diagrams") or []
    if not diagrams and isinstance(meta.get("diagrams_planned"), list):
        # reconstruct from figures.json preferred
        pass
    diag_types = [
        d.get("type") for d in diagrams if isinstance(d, dict) and d.get("type")
    ]
    diag_ids = [d.get("id") for d in diagrams if isinstance(d, dict)]

    pdf = next(out.glob("*.pdf"), None)
    docx = next(out.glob("*.docx"), None)
    dry = bool(case.get("dry_run"))

    issues: list[str] = []
    status = meta.get("status")
    want_status = case.get("expect_status")
    if want_status and status != want_status:
        issues.append(f"status={status} want={want_status}")
    elif not dry and status not in {None, "ok"} and status != "ok":
        if status != "ok":
            issues.append(f"status={status}")

    if not dry and len(charts_ok) < int(case.get("expect_charts_min") or 0):
        issues.append(f"charts_ok={len(charts_ok)} < {case.get('expect_charts_min')}")

    dmin = case.get("expect_diagrams_min")
    if dmin is not None and len(diag_ids) < int(dmin):
        issues.append(f"diagrams={len(diag_ids)} < {dmin}")
    dmax = case.get("expect_diagrams_max")
    if dmax is not None and len(diag_ids) > int(dmax):
        issues.append(f"diagrams={len(diag_ids)} > {dmax}")

    if case.get("expect_tabularx") and "tabularx" not in tex and "tabular" not in tex:
        issues.append("no table env")
    if "%CASE3_" in tex:
        issues.append("orphan CASE3 slots")

    # Diagrams must never appear as TeX inject slots
    if "%CASE3_DIAG" in tex or "CASE3_DIAGRAM" in tex:
        issues.append("diagram leaked into TeX slots")

    if not dry:
        if "pdf" in case.get("formats", set()):
            if pdf is None or pdf.stat().st_size < 1000:
                issues.append("pdf missing/small")
        if "docx" in case.get("formats", set()):
            if docx is None or docx.stat().st_size < 1000:
                issues.append("docx missing/small")

    # Purple neuroslop in chart HTML
    purple_hits = 0
    for html in out.glob("work/*/index.html"):
        try:
            body = html.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if PURPLE_RE.search(body):
            purple_hits += 1
    if purple_hits:
        issues.append(f"purple_palette_hits={purple_hits}")

    # Unknown chart types
    for t in chart_types_got:
        if t not in CHART_TYPES:
            issues.append(f"unknown_chart_type={t}")

    for t in diag_types:
        if t not in DIAGRAM_TYPES:
            issues.append(f"unknown_diagram_type={t}")

    # Prefer expected types when specified (soft warn → issue)
    want_ctypes = case.get("expect_chart_types")
    if want_ctypes and chart_types_got:
        if not any(t in chart_types_got for t in want_ctypes):
            issues.append(f"chart_types_got={chart_types_got} want≈{want_ctypes}")

    want_dtypes = case.get("expect_diagram_types")
    if want_dtypes and diag_types:
        if not any(t in diag_types for t in want_dtypes):
            issues.append(f"diagram_types_got={diag_types} want≈{want_dtypes}")

    # Caption / document basics
    if not dry and tex and r"\begin{document}" not in tex:
        issues.append("no begin{document}")
    if not dry and tex and r"\documentclass" not in tex:
        issues.append("no documentclass")

    return {
        "status": status,
        "run_id": meta.get("run_id"),
        "charts_planned": meta.get("charts_planned") or [],
        "figures_planned": meta.get("figures_planned") or [],
        "diagrams_planned": meta.get("diagrams_planned") or diag_ids,
        "diagrams_ok": meta.get("diagrams_ok", len(diag_ids)),
        "diagrams_dropped": meta.get("diagrams_dropped") or fj.get("diagrams_dropped") or [],
        "chart_types": chart_types_got,
        "diagram_types": diag_types,
        "charts_ok": charts_ok,
        "figures_ok": figs_ok,
        "pdf_bytes": pdf.stat().st_size if pdf else 0,
        "docx_bytes": docx.stat().st_size if docx else 0,
        "has_caption": r"\caption{" in tex,
        "has_tabularx": "tabularx" in tex,
        "has_section": r"\section" in tex or r"\subsection" in tex,
        "orphan_slots": "%CASE3_" in tex,
        "tex_chars": len(tex),
        "summary_status": meta.get("summary_status"),
        "issues": issues,
        "ok": not issues,
    }


def run_case(case: dict) -> dict:
    t0 = time.time()
    run_id = f"audit_{case['id']}"
    row: dict = {"id": case["id"], "run_id": run_id}
    try:
        out = run_pipeline(
            case["source"],
            project_root=ROOT,
            formats=set(case["formats"]),
            intent=case["intent"],
            max_charts=case["max_charts"],
            max_images=case["max_images"],
            max_diagrams=case.get("max_diagrams", 0),
            dry_run=bool(case.get("dry_run")),
            run_id=run_id,
        )
        row.update(_audit_out(out, case))
        row["out"] = str(out)
    except PipelineError as exc:
        row["ok"] = False
        row["issues"] = [str(exc)[:400]]
        row["status"] = "error"
        row["traceback"] = traceback.format_exc()[-1000:]
        if exc.out_dir.is_dir():
            try:
                audited = _audit_out(exc.out_dir, case)
                for k, v in audited.items():
                    if k not in {"ok", "issues"}:
                        row[k] = v
                row["issues"] = list(dict.fromkeys((row.get("issues") or []) + audited.get("issues", [])))
            except Exception:
                pass
    except Exception as exc:
        row["ok"] = False
        row["issues"] = [f"{type(exc).__name__}: {exc}"]
        row["traceback"] = traceback.format_exc()[-1000:]
    row["seconds"] = round(time.time() - t0, 1)
    return row


def multi_edit_chart(base_run_id: str) -> dict:
    out = ROOT / "runs" / "out" / base_run_id
    edits = [
        {"palette": "ocean", "style": "крупнее подписи осей"},
        {"palette": "sunset", "style": "более контрастные заливки"},
        {"palette": "mono", "style": "", "chart_type": "bar"},
        {"palette": "atelier", "style": "мягче сетка"},
    ]
    results = []
    for i, ed in enumerate(edits, 1):
        t0 = time.time()
        try:
            chart_id = "cht_01"
            pngs = list((out / "figures").glob("cht_*.png")) if (out / "figures").is_dir() else []
            if pngs:
                chart_id = pngs[0].stem
            r = edit_chart_in_run(
                out,
                chart_id,
                palette=ed.get("palette"),
                style=ed.get("style"),
                chart_type=ed.get("chart_type"),
                formats={"pdf"},
            )
            png = out / "figures" / f"{chart_id}.png"
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
            results.append({"n": i, "ok": False, "error": str(exc)[:240], "seconds": round(time.time() - t0, 1)})
    ok_n = sum(1 for r in results if r.get("ok"))
    return {"base_run": base_run_id, "edits": results, "ok": ok_n >= 3, "ok_count": ok_n}


def write_findings_stub(summary: dict) -> Path:
    path = ROOT / "docs" / "audits" / "2026-10-21-full-audit-findings.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fails = [r for r in summary["pipeline"] if not r.get("ok")]
    lines = [
        "# Full audit findings — 2026-10-21",
        "",
        f"Pipeline: **{summary['pass_pipeline']}/{summary['total_pipeline']}** ok. "
        f"Chart multi-edit: `{summary['chart_multi_edit'].get('ok')}`.",
        "",
        "## Failures",
        "",
    ]
    if not fails:
        lines.append("_No hard failures in matrix._")
    else:
        for r in fails:
            lines.append(f"- `{r['id']}` — {r.get('issues')}")
    lines.extend(["", "## Per-case", ""])
    for r in summary["pipeline"]:
        flag = "OK" if r.get("ok") else "FAIL"
        lines.append(
            f"- **{flag}** `{r['id']}` {r.get('seconds')}s "
            f"charts={r.get('chart_types')} diagrams={r.get('diagram_types')} "
            f"pdf={r.get('pdf_bytes')} issues={r.get('issues')}"
        )
    lines.extend(
        [
            "",
            "## Windows desk check (static)",
            "",
            "- `scripts/api.cmd` / `web.cmd` / `setup.cmd` / `run.cmd` — present",
            "- Playwright cache: Mac / Linux / Windows candidates in `charts._prefer_stable_playwright_browsers`",
            "- Pathlib throughout pipeline (no hardcoded `/tmp` in src)",
            "- Do not commit `.env` / `runs/` artifacts",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = _cases()
    rows = []
    print(f"=== full audit matrix ({len(cases)} cases) ===", flush=True)
    for case in cases:
        print(f"→ {case['id']} …", flush=True)
        row = run_case(case)
        rows.append(row)
        flag = "OK" if row.get("ok") else "FAIL"
        print(
            f"  {flag} {row.get('seconds')}s charts={row.get('chart_types')} "
            f"diags={row.get('diagram_types')} pdf={row.get('pdf_bytes')} "
            f"issues={row.get('issues')}",
            flush=True,
        )
        # incremental save
        OUT_SUMMARY.write_text(
            json.dumps({"pipeline": rows, "partial": True}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    edit_base = None
    for r in rows:
        if r.get("ok") and r.get("charts_ok"):
            edit_base = r["run_id"]
            break
    edit_report: dict = {"ok": False, "skipped": True}
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
        "chart_types_whitelist": sorted(CHART_TYPES),
        "diagram_types_whitelist": sorted(DIAGRAM_TYPES),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    findings = write_findings_stub(summary)
    print("=== summary ===", flush=True)
    print(
        f"pipeline {summary['pass_pipeline']}/{summary['total_pipeline']}  "
        f"edits_ok={edit_report.get('ok')}  → {OUT_SUMMARY}",
        flush=True,
    )
    print(f"findings → {findings}", flush=True)
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
