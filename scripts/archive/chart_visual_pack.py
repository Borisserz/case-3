#!/usr/bin/env python3
"""Offline matrix: all CHART_TYPES × palettes → polish → PNG + assert checks.

Run:  python3 scripts/archive/chart_visual_pack.py
Out:  runs/chart_visual_pack/<palette>/<id>.png
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from case3.chart_html import CHART_TYPES  # noqa: E402
from case3.chart_style import _PALETTES  # noqa: E402
from case3.chart_types_coerce import polish_charts  # noqa: E402
from case3.charts import render_chart_png  # noqa: E402

OUT = ROOT / "runs" / "chart_visual_pack"
PALETTES = ("atelier", "ocean", "editorial", "sunset")


def _specs() -> list[dict]:
    """Varied Source-like RU data; some messy model habits polish must fix."""
    return [
        {
            "id": "cht_bar",
            "type": "bar",
            "caption": "Клиенты по кварталам",
            "html": """
<canvas id="c_bar" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('c_bar'),{type:'bar',data:{labels:['Q1','Q2','Q3','Q4'],datasets:[
{label:'Новые',data:[42,58,71,88],backgroundColor:'#111111',borderRadius:8},
{label:'Повторные',data:[18,22,30,35],backgroundColor:'#888888',borderRadius:8}
]},options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{y:{beginAtZero:true,ticks:{maxTicksLimit:5}},x:{grid:{display:false}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_grouped",
            "type": "grouped_bar",
            "caption": "Каналы × квартал",
            "html": """
<canvas id="c_grp" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('c_grp'),{type:'bar',data:{labels:['Q1','Q2','Q3'],datasets:[
{label:'Direct',data:[90,110,130],backgroundColor:'#E85D04',borderRadius:6},
{label:'Partner',data:[60,70,85],backgroundColor:'#0077B6',borderRadius:6},
{label:'Marketplace',data:[40,55,48],backgroundColor:'#2A9D8F',borderRadius:6}
]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_stack",
            "type": "stacked_bar",
            "caption": "Расход за 7 дней",
            "html": """
<div class="chart-card">
  <div class="chart-kpi-header"><div class="eyebrow">Расход за 7 дней</div><div class="big">64 Br</div>
  <div class="context">≈ 3 470 Br удержанной выручки · 32 часа</div></div>
  <canvas id="c_stack" width="1100" height="420"></canvas>
</div><script>
new Chart(document.getElementById('c_stack'),{type:'bar',data:{labels:['1 сен','2 сен','3 сен','4 сен','5 сен','6 сен','7 сен'],datasets:[
{label:'Запись',data:[4,3,5,2,3,3,2],backgroundColor:'#1E8AD4',stack:'s',borderRadius:4},
{label:'Возврат',data:[2,1,2,1,2,2,1],backgroundColor:'#2EC4B6',stack:'s'},
{label:'Ответы',data:[1,2,1,2,1,1,2],backgroundColor:'#E8A838',stack:'s'},
{label:'Напоминания',data:[1,1,2,1,1,2,1],backgroundColor:'#E85D04',stack:'s'},
{label:'Прочее',data:[1,0,1,1,0,1,1],backgroundColor:'#3D5C60',stack:'s'}
]},options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,beginAtZero:true,ticks:{maxTicksLimit:4}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_line",
            "type": "line",
            "caption": "MRR и ответы",
            "html": """
<canvas id="c_line" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('c_line'),{type:'line',data:{labels:['Июл','Авг','Сен'],datasets:[
{label:'MRR',data:[412,428,451],borderColor:'#0B4F8C',backgroundColor:'rgba(86,180,233,0.34)',fill:true,tension:0.3,borderWidth:3,pointRadius:4},
{label:'Ответы',data:[1050,1190,1280],borderColor:'#009E73',fill:false,tension:0.25,borderWidth:3,pointRadius:4}
]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:false}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_area",
            "type": "area",
            "caption": "Трафик по дням",
            "html": """
<canvas id="c_area" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('c_area'),{type:'line',data:{labels:['Пн','Вт','Ср','Чт','Пт'],datasets:[
{label:'Сессии',data:[420,510,480,620,590],borderColor:'#0072B2',backgroundColor:'rgba(86,180,233,0.34)',fill:true,tension:0.35,borderWidth:3,pointRadius:3}
]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_hbar",
            "type": "horizontal_bar",
            "caption": "Топ городов",
            "html": """
<canvas id="c_hbar" width="1100" height="400"></canvas><script>
new Chart(document.getElementById('c_hbar'),{type:'bar',data:{labels:['Минск','Брест','Гродно','Витебск','Гомель'],datasets:[
{label:'Заказы, тыс.',data:[86,41,33,29,27],backgroundColor:'rgba(0,119,187,0.18)',borderColor:'#0077BB',borderWidth:1,borderRadius:6}
]},options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_donut",
            "type": "donut",
            "caption": "Сегменты клиентов",
            # Messy labels like the live bug — polish must clean.
            "html": """
<canvas id="c_donut" width="520" height="520"></canvas><script>
new Chart(document.getElementById('c_donut'),{type:'doughnut',data:{
labels:['Retail 42% (210)','Food 28% (140)','Pharma 18% (90)','Other 12% (60)'],
datasets:[{data:[210,140,90,60],backgroundColor:['#2E4208','#4F6B14','#7A9A28','#B8D45A'],borderWidth:2,borderColor:'#ffffff'}]
},options:{plugins:{legend:{display:true}},cutout:'60%',animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_scatter",
            "type": "scatter",
            "caption": "NPS vs churn",
            "html": """
<canvas id="c_scat" width="1100" height="520"></canvas><script>
new Chart(document.getElementById('c_scat'),{type:'scatter',data:{datasets:[
{label:'Месяцы',data:[{x:3.1,y:41},{x:2.8,y:44},{x:2.4,y:48}],backgroundColor:'#004D47',borderColor:'#0077BB',pointRadius:3}
]},options:{plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'Churn %'}},y:{title:{display:true,text:'NPS'}}},animation:false}});
window.__CASE3_CHART_READY=true;</script>
""",
        },
        {
            "id": "cht_kpi",
            "type": "kpi",
            "caption": "Ключевые цифры",
            "html": """
<div class="kpi-row">
  <div class="kpi"><div class="value">451</div><div class="label">MRR сен, тыс. BYN</div></div>
  <div class="kpi"><div class="value">95%</div><div class="label">SLA on-time</div></div>
  <div class="kpi"><div class="value">48</div><div class="label">NPS</div></div>
</div>
<script>window.__CASE3_CHART_READY=true;</script>
""",
        },
    ]


def _assert_polished(chart: dict, palette: str) -> list[str]:
    """Return list of assertion failures for one polished chart."""
    errs: list[str] = []
    cid = chart["id"]
    ctype = chart["type"]
    html = chart.get("html") or ""
    up = html.upper()

    if ctype == "kpi":
        if "kpi" not in html.lower():
            errs.append(f"{cid}: missing kpi markup")
        return errs

    if "tooltip" in html.lower() and not re.search(
        r"tooltip\s*:\s*\{[^}]*enabled\s*:\s*true", html, flags=re.I | re.S
    ):
        # ensure should inject; soft warn if plugins block missing entirely on exotic html
        if "plugins" in html.lower() and "tooltip" not in html.lower():
            errs.append(f"{cid}: no tooltip.enabled")

    if ctype == "donut":
        if "valued-legend" not in html:
            errs.append(f"{cid}: no valued-legend")
        if re.search(r"Retail\s+42%", html, flags=re.I):
            errs.append(f"{cid}: dirty label still in HTML")
        if re.search(r"legend\s*:\s*\{[^}]*display\s*:\s*true", html, flags=re.I | re.S):
            errs.append(f"{cid}: Chart.js legend should stay off with valued-legend")
        # After palette remap, old olive ladder should be gone for chromatic palettes
        if palette != "mono" and "#7A9A28" in up and "#B8D45A" in up:
            errs.append(f"{cid}: old olive ladder survived palette={palette}")

    if ctype in {"grouped_bar", "stacked_bar", "line"}:
        if not re.search(r"legend\s*:\s*\{[^}]*display\s*:\s*true", html, flags=re.I | re.S):
            errs.append(f"{cid}: legend not enabled")

    if ctype == "scatter":
        m = re.search(r"pointRadius\s*:\s*([\d.]+)", html, flags=re.I)
        if not m or float(m.group(1)) < 8:
            errs.append(f"{cid}: scatter pointRadius too small ({m.group(1) if m else 'missing'})")
        if re.search(r"legend\s*:\s*\{[^}]*display\s*:\s*true", html, flags=re.I | re.S):
            errs.append(f"{cid}: single-series scatter should hide Chart.js legend")

    if ctype in {"line", "area"}:
        radii = [float(x) for x in re.findall(r"pointRadius\s*:\s*([\d.]+)", html, flags=re.I)]
        if radii and min(radii) < 5:
            errs.append(f"{cid}: line/area pointRadius < 5 ({radii})")

    if ctype == "horizontal_bar":
        if not re.search(r"backgroundColor\s*:\s*\[", html, flags=re.I):
            errs.append(f"{cid}: hbar should use per-category color array")

    if ctype == "horizontal_bar":
        if "0.18" in html and "rgba" in html.lower():
            # harden should solidify pale fills
            if re.search(r"backgroundColor\s*:\s*'rgba\([^']+0\.18\)'", html, flags=re.I):
                errs.append(f"{cid}: pale hbar fill not solidified")

    # Palette accents from catalog should appear after polish (non-auto)
    p = _PALETTES.get(palette) or {}
    accents = [str(a).upper() for a in p.get("accents", [])[:2]]
    primary = str(p.get("primary", "")).upper()
    if ctype != "kpi" and primary and primary not in up and not any(a in up for a in accents):
        # KPI uses CSS vars; scatter/bar should pick up remap
        if ctype not in {"kpi"}:
            errs.append(f"{cid}: palette {palette} inks not found in HTML")

    return errs


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    specs = _specs()
    covered = {c["type"] for c in specs}
    missing = CHART_TYPES - covered
    if missing:
        print(f"FAIL: specs missing types {sorted(missing)}")
        return 2

    manifest: dict = {"ok": 0, "fail": 0, "assert_fail": 0, "palettes": {}}
    all_errs: list[str] = []

    for palette in PALETTES:
        pdir = OUT / palette
        pdir.mkdir(parents=True, exist_ok=True)
        work = pdir / "work"
        charts = polish_charts([dict(c) for c in specs], palette_id=palette)
        status: dict = {}
        for ch in charts:
            cid = ch["id"]
            dest = pdir / f"{cid}.png"
            for err in _assert_polished(ch, palette):
                all_errs.append(f"{palette}/{err}")
                manifest["assert_fail"] += 1
            try:
                render_chart_png(ch, dest, work_dir=work / cid)
                status[cid] = {"ok": True, "path": str(dest), "bytes": dest.stat().st_size}
                manifest["ok"] += 1
                print(f"OK  {palette}/{cid}.png ({dest.stat().st_size} B)")
            except Exception as exc:  # noqa: BLE001
                status[cid] = {"ok": False, "error": str(exc)[:400]}
                manifest["fail"] += 1
                all_errs.append(f"{palette}/{cid}: RENDER {exc}")
                print(f"FAIL {palette}/{cid}: {exc}")
        (pdir / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (pdir / "charts.json").write_text(
            json.dumps(charts, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifest["palettes"][palette] = status

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "assert_errors.txt").write_text("\n".join(all_errs) + ("\n" if all_errs else ""), encoding="utf-8")
    print(
        f"\n→ {OUT}  render_ok={manifest['ok']} render_fail={manifest['fail']} "
        f"assert_fail={manifest['assert_fail']}"
    )
    if all_errs:
        print("ASSERTIONS:")
        for e in all_errs[:40]:
            print(" ", e)
    return 0 if manifest["fail"] == 0 and manifest["assert_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
