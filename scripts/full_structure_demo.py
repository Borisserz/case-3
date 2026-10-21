#!/usr/bin/env python3
"""Offline Liber matrix: all chrome + tables + whitelist chart types → PDF/DOCX."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from case3.chart_types_coerce import polish_charts  # noqa: E402
from case3.charts import render_chart_png  # noqa: E402
from case3.inject import inject_media  # noqa: E402
from case3.render import render_tex  # noqa: E402
from case3.tex_preamble import ensure_document_preamble  # noqa: E402

OUT_ROOT = ROOT / "runs" / "full_structure_demo"
WORK = OUT_ROOT / "work"
FIGS = OUT_ROOT / "figures"
OUT = OUT_ROOT / "out"


def _bar(cid: str = "c1") -> str:
    return f"""<canvas id="{cid}" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('{cid}'),{{type:'bar',data:{{labels:['Янв','Фев','Мар','Апр'],datasets:[{{label:'N',data:[12,28,19,34],backgroundColor:['#E85D04','#0077B6','#2A9D8F','#E9C46A'],borderRadius:6}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true}},x:{{grid:{{display:false}}}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _line(cid: str = "c1") -> str:
    return f"""<canvas id="{cid}" width="1100" height="720"></canvas><script>
new Chart(document.getElementById('{cid}'),{{type:'line',data:{{labels:['Q1','Q2','Q3','Q4'],datasets:[{{label:'Запросы',data:[1400,2100,3100,2800],borderColor:'#023E8A',backgroundColor:'rgba(0,180,216,0.16)',fill:true,tension:0.28,borderWidth:3,pointRadius:4}}]}},options:{{plugins:{{legend:{{display:true}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _area(cid: str = "c1") -> str:
    return f"""<canvas id="{cid}" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('{cid}'),{{type:'line',data:{{labels:['Пн','Вт','Ср','Чт','Пт'],datasets:[{{label:'Трафик',data:[40,55,48,70,62],borderColor:'#023E8A',backgroundColor:'rgba(0,180,216,0.16)',fill:true,tension:0.35,borderWidth:3}}]}},options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _hbar(cid: str = "c1") -> str:
    return f"""<canvas id="{cid}" width="1100" height="560"></canvas><script>
new Chart(document.getElementById('{cid}'),{{type:'bar',data:{{labels:['Север','Юг','Запад','Восток'],datasets:[{{label:'Доля',data:[32,24,18,26],backgroundColor:'rgba(0,180,216,0.18)',borderColor:'#023E8A',borderWidth:1}}]}},options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _grouped(cid: str = "c1") -> str:
    return f"""<canvas id="{cid}" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('{cid}'),{{type:'bar',data:{{labels:['2023','2024','2025'],datasets:[
{{label:'A',data:[12,18,22],backgroundColor:'#E85D04',borderRadius:4}},
{{label:'B',data:[9,14,19],backgroundColor:'#0077B6',borderRadius:4}},
{{label:'C',data:[6,11,15],backgroundColor:'#2A9D8F',borderRadius:4}}
]}},options:{{plugins:{{legend:{{display:true}}}},scales:{{y:{{beginAtZero:true}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _stacked(cid: str = "c1") -> str:
    return f"""<div class="chart-card"><div class="chart-kpi-header"><div class="eyebrow">Итого</div><div class="big">152</div><div class="context">за период · из Source</div></div>
<canvas id="{cid}" width="1100" height="480"></canvas></div><script>
new Chart(document.getElementById('{cid}'),{{type:'bar',data:{{labels:['Q1','Q2','Q3'],datasets:[
{{label:'Онлайн',data:[40,50,55],backgroundColor:'#E85D04',stack:'s'}},
{{label:'Офлайн',data:[30,28,32],backgroundColor:'#0077B6',stack:'s'}}
]}},options:{{plugins:{{legend:{{display:true}}}},scales:{{x:{{stacked:true}},y:{{stacked:true,beginAtZero:true}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _donut(cid: str = "c1") -> str:
    return f"""<div class="chart-card donut-layout"><div class="donut-viz"><div class="donut-center"><div class="pct">48%</div><div class="lbl">Сегмент A</div></div>
<canvas id="{cid}" width="520" height="520"></canvas></div>
<ul class="valued-legend">
<li class="valued-legend__row"><span class="valued-legend__swatch" style="background:#111"></span><span class="valued-legend__label">A</span><span class="valued-legend__pct">48%</span><span class="valued-legend__abs">48</span></li>
<li class="valued-legend__row"><span class="valued-legend__swatch" style="background:#444"></span><span class="valued-legend__label">B</span><span class="valued-legend__pct">32%</span><span class="valued-legend__abs">32</span></li>
<li class="valued-legend__row"><span class="valued-legend__swatch" style="background:#888"></span><span class="valued-legend__label">C</span><span class="valued-legend__pct">20%</span><span class="valued-legend__abs">20</span></li>
</ul></div><script>
new Chart(document.getElementById('{cid}'),{{type:'doughnut',data:{{labels:['A','B','C'],datasets:[{{data:[48,32,20],backgroundColor:['#111','#444','#888'],borderWidth:2,borderColor:'#fff'}}]}},options:{{plugins:{{legend:{{display:false}}}},cutout:'60%',animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _scatter(cid: str = "c1") -> str:
    return f"""<canvas id="{cid}" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('{cid}'),{{type:'scatter',data:{{datasets:[
{{label:'Кластер',data:[{{x:1,y:12}},{{x:2,y:19}},{{x:3,y:15}},{{x:4,y:28}},{{x:5,y:24}}],backgroundColor:'#E85D04',borderColor:'#023E8A'}}
]}},options:{{plugins:{{legend:{{display:true}}}},scales:{{x:{{title:{{display:true,text:'X'}}}},y:{{title:{{display:true,text:'Y'}},beginAtZero:true}}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>"""


def _kpi() -> str:
    return """<div class="kpi"><div class="value">28</div><div class="label">Клиенты 2025</div></div>
<script>window.__CASE3_CHART_READY=true;</script>"""


SPECS = [
    ("cht_bar", "bar", "Столбцы (ocean)", _bar(), "ocean"),
    ("cht_line", "line", "Линия (editorial)", _line(), "editorial"),
    ("cht_area", "area", "Area (sunset)", _area(), "sunset"),
    ("cht_hbar", "horizontal_bar", "Горизонтальные (atelier)", _hbar(), "atelier"),
    ("cht_grp", "grouped_bar", "Grouped bar (ocean)", _grouped(), "ocean"),
    ("cht_stk", "stacked_bar", "Stacked + KPI header (editorial)", _stacked(), "editorial"),
    ("cht_donut", "donut", "Donut + легенда (atelier)", _donut(), "atelier"),
    ("cht_scat", "scatter", "Scatter (sunset)", _scatter(), "sunset"),
    ("cht_kpi", "kpi", "KPI cards (atelier)", _kpi(), "atelier"),
]


def main() -> int:
    for d in (WORK, FIGS, OUT):
        d.mkdir(parents=True, exist_ok=True)

    status: dict = {}
    charts_meta: list = []
    for cid, ctype, cap, html, pal in SPECS:
        ch = polish_charts(
            [
                {
                    "id": cid,
                    "type": ctype,
                    "caption": cap,
                    "html": html,
                    "width": r"0.90\textwidth",
                }
            ],
            palette_id=pal,
        )[0]
        work = WORK / cid
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        print(f"→ PNG {cid} ({ctype}/{pal})", flush=True)
        try:
            render_chart_png(ch, FIGS / f"{cid}.png", work_dir=work)
            status[cid] = {"ok": True}
            charts_meta.append(ch)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {cid}: {exc}", flush=True)
            status[cid] = {"ok": False, "error": str(exc)}

    ok_charts = [c for c in charts_meta if status.get(c["id"], {}).get("ok")]
    densed = polish_charts(ok_charts, palette_id="auto")
    width_by_id = {c["id"]: c["width"] for c in densed}
    for c in charts_meta:
        if c["id"] in width_by_id:
            c["width"] = width_by_id[c["id"]]

    slots = "\n\n".join(
        f"\\subsection{{{cap}}}\n%CASE3_CHART:{cid}%"
        for cid, _t, cap, _h, _p in SPECS
    )

    # Plain string — avoid f-string brace fights with TeX
    tex = r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\usepackage{geometry}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{float}
\usepackage{graphicx}
\usepackage{setspace}
\usepackage{microtype}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{caption}
\usepackage{hyperref}
\setdefaultlanguage{russian}
\setotherlanguage{english}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
\geometry{a4paper,margin=2.2cm}
\title{Полная матрица оформления Liber}
\author{}
\date{\today}
\begin{document}
\maketitle

\noindent Этот документ — \textbf{офлайн-матрица} всех структур PDF после polish 2026-10-21:
chrome 2.0, списки, таблицы (в т.ч. wide + двойные \texttt{hline}), все whitelist-графики.

\begin{itemize}
  \item Title rule (D4) + \texttt{parskip} / секции
  \item Tables: booktabs + harden \texttt{hlinehline} + tabularx
  \item Charts: vivid palettes, легенда, multi-width 0.82
\end{itemize}

\section{Проза и акценты}
Краткий абзац: метрика \textbf{выручка} выросла; термин \emph{backend} оставлен курсивом.
Второй абзац для проверки воздуха между блоками.

\begin{enumerate}
  \item Собрать Source
  \item Выбрать палитру
  \item Проверить PDF постранично
\end{enumerate}

\section{Таблицы}
\subsection{Узкая booktabs}
\begin{table}[H]
\centering
\begin{tabular}{lrr}
\toprule
Регион & 2024 & 2025 \\
\midrule
Север & 12{,}4 & 15{,}1 \\
Юг & 9{,}8 & 11{,}0 \\
\bottomrule
\end{tabular}
\caption{Узкая таблица}
\end{table}

\subsection{Мусорные hline (до harden)}
\begin{table}[H]
\centering
\begin{tabular}{ll}
\hline\hline
Метрика & Значение \\
\hline\hline
Клиенты & 28 \\
\hline\hline
NPS & 42 \\
\hline\hline
\end{tabular}
\caption{После harden не должно быть двойных линий}
\end{table}

\subsection{Широкая tabular → tabularx}
\begin{table}[H]
\centering
\begin{tabular}{l l l l l}
\toprule
Показатель & 2021 & 2022 & 2023 & 2024 \\
\midrule
Рождения & 78\,000 & 74\,000 & 72\,000 & 70\,500 \\
Смертность & 61\,000 & 59\,500 & 58\,200 & 57\,800 \\
\bottomrule
\end{tabular}
\caption{Wide table (pipeline → tabularx)}
\end{table}

\section{Графики (все типы)}
""" + slots + r"""

\section{Заключение}
Конец матрицы. PDF — истина печати; DOCX — pandoc + reference + table polish.

\end{document}
"""

    tex_path = OUT_ROOT / "full_structure.tex"
    injected = inject_media(tex, [], charts_meta, status, rel_dir="figures")
    hardened = ensure_document_preamble(injected)
    tex_path.write_text(hardened, encoding="utf-8")
    assert r"\hline\hline" not in hardened.replace(" ", "")
    print("→ latexmk pdf+docx…", flush=True)
    arts = render_tex(
        tex_path,
        out_dir=OUT,
        formats={"pdf", "docx"},
        extra_dirs=[FIGS],
        log_dir=OUT_ROOT / "logs",
        project_root=ROOT,
        force=True,
    )
    for k, v in arts.items():
        print(k, v, v.stat().st_size if v.is_file() else 0, flush=True)
    ok_n = sum(1 for s in status.values() if s.get("ok"))
    print(f"charts_ok={ok_n}/{len(SPECS)}", flush=True)
    (OUT_ROOT / "summary.json").write_text(
        json.dumps(
            {"charts": status, "arts": {k: str(v) for k, v in arts.items()}},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if ok_n == len(SPECS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
