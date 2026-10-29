#!/usr/bin/env python3
"""Owner review pack: 3 reports + 3 diagrams + 3 presentations → one folder.

Usage (from repo root, .env with VISION_*):
  .venv/bin/python scripts/archive/owner_review_matrix.py

Writes: runs/_qa/owner_review_2026-10-25/{reports,diagrams,presentations}/…
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from case3.envfile import load_dotenv
from case3.pipeline import PipelineError, run_pipeline
from case3.slides_job import run_slides_job

load_dotenv(ROOT / ".env")
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    for c in (
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ):
        if c.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(c)
            break

SMOKE = ROOT / "fixtures" / "smoke"
REVIEW = ROOT / "runs" / "_qa" / "owner_review_2026-10-25"
STAMP = time.strftime("%Y%m%dT%H%M%SZ")

CASES: list[dict] = [
    # --- reports ---
    {
        "bucket": "reports",
        "id": "R01_temp_line_donut",
        "source": SMOKE / "01_temp_shares.txt",
        "mode": "report",
        "intent": (
            "Русский краткий отчёт. Графики: line по температуре и donut по бюджету. "
            "Палитра atelier. Без фото. Без схем."
        ),
        "max_charts": 2,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": {"pdf", "docx"},
    },
    {
        "bucket": "reports",
        "id": "R02_wide_table",
        "source": SMOKE / "02_wide_table.txt",
        "mode": "report",
        "intent": (
            "Русский отчёт с широкой таблицей (можно landscape). "
            "Один bar-график если есть числа. Палитра ocean. Без фото. Без схем."
        ),
        "max_charts": 1,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": {"pdf"},
    },
    {
        "bucket": "reports",
        "id": "R03_dense_kpi",
        "source": SMOKE / "04_demo_dense.txt",
        "mode": "report",
        "intent": (
            "Русский executive-отчёт: kpi + bar. Палитра sunset. Без фото. Без схем."
        ),
        "max_charts": 2,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": {"pdf"},
    },
    # --- diagrams ---
    {
        "bucket": "diagrams",
        "id": "D01_pipeline_flow",
        "source": SMOKE / "05_process_pipeline.txt",
        "mode": "diagram",
        "intent": (
            "Только схема flowchart процесса Liber Atelier по Source. "
            "Русские подписи. Без PDF, без графиков, без фото."
        ),
        "max_charts": 0,
        "max_images": 0,
        "max_diagrams": 1,
        "formats": set(),
    },
    {
        "bucket": "diagrams",
        "id": "D02_support_seq",
        "source": SMOKE / "07_support_flow.txt",
        "mode": "diagram",
        "intent": (
            "Только sequence-схема поддержки по Source. Русские роли. "
            "Без PDF, без графиков, без фото."
        ),
        "max_charts": 0,
        "max_images": 0,
        "max_diagrams": 1,
        "formats": set(),
    },
    {
        "bucket": "diagrams",
        "id": "D03_release_mind",
        "source": SMOKE / "06_product_release.txt",
        "mode": "diagram",
        "intent": (
            "Только mindmap или flowchart релиза продукта по Source. "
            "Без PDF, без графиков, без фото."
        ),
        "max_charts": 0,
        "max_images": 0,
        "max_diagrams": 1,
        "formats": set(),
    },
    # --- presentations ---
    {
        "bucket": "presentations",
        "id": "P01_temp_atelier",
        "source": SMOKE / "01_temp_shares.txt",
        "mode": "presentation",
        "intent": (
            "Презентация: температура и бюджет. Pack atelier. "
            "3–6 слайдов. Числа только из Source."
        ),
        "max_charts": 2,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": set(),
        "deck_pack": "atelier",
    },
    {
        "bucket": "presentations",
        "id": "P02_release_board",
        "source": SMOKE / "06_product_release.txt",
        "mode": "presentation",
        "intent": (
            "Презентация релиза продукта. Pack board. "
            "Структура launch/brief. Числа только из Source."
        ),
        "max_charts": 1,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": set(),
        "deck_pack": "board",
    },
    {
        "bucket": "presentations",
        "id": "P03_pipeline_botanical",
        "source": SMOKE / "05_process_pipeline.txt",
        "mode": "presentation",
        "intent": (
            "Презентация пайплайна Liber. Pack botanical (vesper). "
            "Слайды про этапы. Без выдуманных метрик."
        ),
        "max_charts": 0,
        "max_images": 0,
        "max_diagrams": 0,
        "formats": set(),
        "deck_pack": "botanical",
    },
]


def _copy_tree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if not src.is_dir():
        return
    for p in src.iterdir():
        if p.name.startswith("."):
            continue
        target = dest / p.name
        if p.is_dir():
            if p.name in {"figures", "slides"}:
                shutil.copytree(p, target, dirs_exist_ok=True)
        elif p.suffix.lower() in {
            ".pdf",
            ".docx",
            ".pptx",
            ".png",
            ".svg",
            ".json",
            ".txt",
            ".mmd",
        }:
            shutil.copy2(p, target)


def _write_readme(case: dict, out_dir: Path, meta: dict, sec: float, err: str | None) -> None:
    lines = [
        f"# {case['id']}",
        "",
        f"- mode: `{case['mode']}`",
        f"- source: `{case['source'].name}`",
        f"- run_id: `{meta.get('run_id')}`",
        f"- status: `{meta.get('status')}`",
        f"- stage: `{meta.get('stage')}`",
        f"- slides_status: `{meta.get('slides_status')}`",
        f"- elapsed_s: {sec:.1f}",
        "",
        "## Intent",
        "",
        case["intent"],
        "",
    ]
    if err:
        lines.extend(["## Error", "", err, ""])
    arts = []
    for name in sorted(out_dir.iterdir()) if out_dir.is_dir() else []:
        if name.is_file():
            arts.append(f"- `{name.name}` ({name.stat().st_size} bytes)")
    if arts:
        lines.extend(["## Files", ""] + arts + [""])
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    for b in ("reports", "diagrams", "presentations"):
        (REVIEW / b).mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    print(f"Owner review → {REVIEW}", flush=True)

    for i, case in enumerate(CASES, 1):
        rid = f"owner_{case['id']}_{STAMP}"
        dest = REVIEW / case["bucket"] / case["id"]
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        print(f"\n[{i}/{len(CASES)}] {case['id']} ({case['mode']}) …", flush=True)
        t0 = time.time()
        err: str | None = None
        meta: dict = {"run_id": rid, "status": "error"}
        try:
            out = run_pipeline(
                case["source"],
                project_root=ROOT,
                formats=case["formats"] or None,
                dry_run=False,
                intent=case["intent"],
                max_images=case["max_images"],
                max_charts=case["max_charts"],
                max_diagrams=case["max_diagrams"],
                run_id=rid,
                output_mode=case["mode"],
            )
            meta_path = out / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if case["mode"] == "presentation":
                pack = case.get("deck_pack") or "atelier"
                meta["slides_style"] = {"theme_pack": pack, "structure_id": "freeform"}
                meta["slides_theme_pack"] = pack
                meta_path.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"  slides job pack={pack} …", flush=True)
                run_slides_job(rid, root=ROOT)
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            _copy_tree(out, dest)
            # diagrams: also copy mermaid from figures.json / diagrams
            fj = out / "figures.json"
            if fj.is_file():
                shutil.copy2(fj, dest / "figures.json")
        except PipelineError as exc:
            err = str(exc)
            meta = getattr(exc, "meta", None) or meta
            traceback.print_exc()
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            traceback.print_exc()
        sec = time.time() - t0
        _write_readme(case, dest, meta, sec, err)
        row = {
            "id": case["id"],
            "bucket": case["bucket"],
            "mode": case["mode"],
            "run_id": meta.get("run_id") or rid,
            "status": meta.get("status"),
            "slides_status": meta.get("slides_status"),
            "error": err or meta.get("error") or meta.get("slides_error"),
            "sec": round(sec, 1),
            "path": str(dest.relative_to(ROOT)),
        }
        summary.append(row)
        print(
            f"  → {row['status']} slides={row['slides_status']} {row['sec']}s",
            flush=True,
        )

    index_lines = [
        "# Owner review — 2026-10-25",
        "",
        "3 отчёта · 3 схемы · 3 презентации (live Vision).",
        "",
        f"Папка: `{REVIEW.relative_to(ROOT)}`",
        "",
        "| id | mode | status | slides | sec | path |",
        "|----|------|--------|--------|-----|------|",
    ]
    for r in summary:
        index_lines.append(
            f"| {r['id']} | {r['mode']} | {r['status']} | {r.get('slides_status') or '—'} | "
            f"{r['sec']} | `{r['path']}` |"
        )
    index_lines.extend(
        [
            "",
            "## Как смотреть",
            "",
            "1. **reports/** — открой `*.pdf` (и docx у R01).",
            "2. **diagrams/** — `figures.json` → поле `diagrams[].mermaid`; PNG если есть.",
            "3. **presentations/** — `*.pptx` + `deck.pdf` + `slides/*.png`.",
            "",
        ]
    )
    (REVIEW / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")
    (REVIEW / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = sum(1 for r in summary if r["status"] == "ok")
    print(f"\nDone: {ok}/{len(summary)} ok → {REVIEW / 'INDEX.md'}", flush=True)
    return 0 if ok == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
