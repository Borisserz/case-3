#!/usr/bin/env python3
"""QA: every CHART_TYPE → PNG → TeX → DOCX → native replace → audit.

Run from repo root:
  PYTHONPATH=src .venv/bin/python scripts/archive/docx_chart_native_qa.py

Out: _qa/docx_chart_qa/{report.md, figures/, source.docx, audit.json}
     (not under runs/ — that dir is cursorignored / sandbox-blocked)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from case3.chart_coerce import polish_charts  # noqa: E402
from case3.charts import render_chart_png  # noqa: E402
from case3.docx_charts import (  # noqa: E402
    palette_hexes_for_report,
    prune_replaced_chart_pngs,
    replace_docx_native_charts,
)
from case3.docx_validate import docx_charts_word_safe, docx_package_ok  # noqa: E402
from case3.render import render_tex  # noqa: E402
from case3.slides_chart_data import (  # noqa: E402
    NATIVE_CHART_TYPES as NATIVE,
    attach_series_ir_to_charts,
)

OUT = ROOT / "_qa" / "docx_chart_qa"
PALETTE = "atelier"


def _load_specs() -> list[dict]:
    import importlib.util

    path = ROOT / "scripts/archive/chart_visual_pack.py"
    spec = importlib.util.spec_from_file_location("chart_visual_pack", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod._specs())


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("_", "\\_")
    )


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    figs = OUT / "figures"
    figs.mkdir(parents=True)

    raw = polish_charts([dict(c) for c in _load_specs()], palette_id=PALETTE)
    n_ir = attach_series_ir_to_charts(raw)
    print(f"polished {len(raw)} charts; series IR on {n_ir}")

    figures_json = {"charts": raw, "figures": []}
    (OUT / "figures.json").write_text(
        json.dumps(figures_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    work = OUT / "chart_work"
    bodies: list[str] = []
    png_mode = "playwright"
    for ch in raw:
        cid = str(ch["id"])
        ctype = str(ch.get("type") or "")
        cap = str(ch.get("caption") or cid)
        png = figs / f"{cid}.png"
        print(f"render PNG {cid} ({ctype})…")
        try:
            render_chart_png(ch, png, work_dir=work / cid)
        except Exception as exc:  # noqa: BLE001 — sandbox / missing browser
            print(f"  playwright skip ({exc.__class__.__name__}) — stub PNG")
            png_mode = "stub"
            # Minimal valid 8×8 PNG so pandoc embeds a drawing with cht_ descr.
            png.write_bytes(
                bytes.fromhex(
                    "89504e470d0a1a0a0000000d494844520000000800000008"
                    "08020000005b1fc9910000000c4944415408d763f8ffff3f"
                    "0005fe02fe0dbc17940000000049454e44ae426082"
                )
            )
        if not png.is_file() or png.stat().st_size < 20:
            raise SystemExit(f"PNG failed: {cid}")
        bodies.append(
            f"\\subsection{{{_tex_escape(cap)} ({_tex_escape(ctype)})}}\n"
            f"\\begin{{figure}}[H]\n"
            f"  \\centering\n"
            f"  \\includegraphics[width=0.92\\textwidth]{{figures/{cid}.png}}\n"
            f"  \\caption{{{_tex_escape(cap)}}}\n"
            f"  \\label{{fig:{cid}}}\n"
            f"\\end{{figure}}\n"
        )
    print(f"png_mode={png_mode}")

    tex = OUT / "source.tex"
    tex.write_text(
        r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\usepackage{geometry}
\usepackage{float}
\usepackage{graphicx}
\usepackage{caption}
\usepackage{hyperref}
\setdefaultlanguage{russian}
\setotherlanguage{english}
\setmainfont{DejaVu Serif}
\geometry{a4paper,margin=2.2cm}
\begin{document}
\section{QA native charts in DOCX}
"""
        + "\n".join(bodies)
        + "\n\\end{document}\n",
        encoding="utf-8",
    )

    # meta for render hook palette
    (OUT / "meta.json").write_text(
        json.dumps(
            {
                "run_id": "docx_chart_qa",
                "status": "ok",
                "chart_palette": PALETTE,
                "charts_planned": [c["id"] for c in raw],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("pandoc → DOCX (native off, then explicit replace)…")
    import os

    os.environ["CASE3_DOCX_NATIVE_CHARTS"] = "0"
    results = render_tex(
        tex,
        out_dir=OUT,
        formats={"docx"},
        extra_dirs=[figs],
        project_root=ROOT,
        force=True,
    )
    docx = results["docx"]
    print(f"wrote {docx} ({docx.stat().st_size} bytes)")

    replaced = replace_docx_native_charts(
        docx,
        figures_path=OUT / "figures.json",
        series_hexes=palette_hexes_for_report(PALETTE),
    )
    print(f"native replaced: {replaced}")
    prune_replaced_chart_pngs(OUT / "docx_media", replaced)

    ok_pkg = docx_package_ok(docx)
    ok_safe = docx_charts_word_safe(docx)
    print(f"package_ok={ok_pkg} word_safe={ok_safe}")

    audit: list[dict] = []
    with zipfile.ZipFile(docx) as zf:
        names = set(zf.namelist())
        chart_parts = sorted(
            n for n in names if re.match(r"word/charts/chart\d+\.xml$", n)
        )
        media = sorted(n for n in names if n.startswith("word/media/"))
        doc = zf.read("word/document.xml").decode("utf-8", errors="replace")
        drawing_n = len(re.findall(r"<w:drawing>", doc))
        chart_uri_n = doc.count("drawingml/2006/chart")

        # Map chartN.xml → series type / pt counts
        chart_meta: list[dict] = []
        for part in chart_parts:
            xml = zf.read(part).decode("utf-8", errors="replace")
            kinds = [
                k
                for k in (
                    "barChart",
                    "lineChart",
                    "areaChart",
                    "pieChart",
                    "doughnutChart",
                )
                if k in xml
            ]
            pts = len(re.findall(r"<c:pt ", xml))
            chart_meta.append(
                {
                    "part": part,
                    "kinds": kinds,
                    "pt_count": pts,
                    "has_cache": ("numCache" in xml or "strCache" in xml),
                    "has_externalData": "externalData" in xml,
                    "auto_title_deleted": 'autoTitleDeleted val="1"' in xml,
                    "bytes": len(xml),
                }
            )

        for ch in raw:
            cid = str(ch["id"])
            ctype = str(ch.get("type") or "")
            expect_native = ctype in NATIVE
            in_replaced = cid in replaced
            # PNG leftover: descr still pointing at this cht
            still_png = bool(
                re.search(
                    rf'descr="[^"]*{re.escape(cid)}\.png"',
                    doc,
                    flags=re.I,
                )
            )
            series = ch.get("series")
            has_series = isinstance(series, dict) and bool(series.get("categories"))
            row = {
                "id": cid,
                "type": ctype,
                "expect_native": expect_native,
                "has_series_ir": has_series,
                "replaced": in_replaced,
                "still_png_descr": still_png,
                "verdict": (
                    "native_ok"
                    if in_replaced and expect_native
                    else (
                        "png_ok_by_design"
                        if (not expect_native) and not in_replaced
                        else (
                            "FAIL_expected_native"
                            if expect_native and not in_replaced
                            else "unexpected_native"
                        )
                    )
                ),
            }
            audit.append(row)

        summary = {
            "docx": str(docx),
            "size_bytes": docx.stat().st_size,
            "package_ok": ok_pkg,
            "word_safe": ok_safe,
            "drawings": drawing_n,
            "chart_uris": chart_uri_n,
            "chart_parts": chart_meta,
            "media_left": media,
            "replaced_ids": replaced,
            "charts": audit,
        }

    (OUT / "audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# DOCX chart native QA",
        "",
        f"- package_ok: **{ok_pkg}** · word_safe: **{ok_safe}**",
        f"- native chart parts: **{len(chart_parts)}** · media left: **{len(media)}**",
        f"- replaced: `{', '.join(replaced) or '—'}`",
        "",
        "| id | type | expect | series IR | replaced | still PNG | verdict |",
        "|----|------|--------|-----------|----------|-----------|---------|",
    ]
    for r in audit:
        lines.append(
            f"| {r['id']} | {r['type']} | {r['expect_native']} | {r['has_series_ir']} | "
            f"{r['replaced']} | {r['still_png_descr']} | **{r['verdict']}** |"
        )
    lines.append("")
    lines.append("## Chart XML quality")
    lines.append("")
    for cm in chart_meta:
        lines.append(
            f"- `{cm['part']}` kinds={cm['kinds']} pts={cm['pt_count']} "
            f"cache={cm['has_cache']} externalData={cm['has_externalData']} "
            f"titleOff={cm['auto_title_deleted']} bytes={cm['bytes']}"
        )
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))
    fails = [r for r in audit if str(r["verdict"]).startswith("FAIL")]
    return 1 if fails or not ok_pkg or not ok_safe else 0


if __name__ == "__main__":
    raise SystemExit(main())
