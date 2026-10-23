#!/usr/bin/env python3
"""Render pack-colored premium bar/line PNGs for gallery deck previews."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from case3.charts import render_chart_png  # noqa: E402
from case3.deck_theme import PACK_IDS, resolve_deck_theme  # noqa: E402

OUT = ROOT / "runs" / "atelier_visual" / "gallery_charts"
WORK = ROOT / "runs" / "atelier_visual" / "gallery_charts_work"


def _is_dark(pack: str, tok) -> bool:
    motif = tok.motif if isinstance(getattr(tok, "motif", None), dict) else {}
    if str(motif.get("atmosphere") or "") == "dark":
        return True
    return pack in ("signal", "ink", "voltage", "botanical")


def _fragment(
    *,
    kind: str,
    series: list[str],
    dark: bool,
    ink: str,
    muted: str,
    foil: str,
) -> str:
    c0 = series[0] if series else foil
    c1 = series[1] if len(series) > 1 else c0
    bg = "#161618" if dark else "#FFFcf7"
    grid = "rgba(255,255,255,0.10)" if dark else "rgba(20,22,26,0.10)"
    tick = muted if dark else ink
    cats = json.dumps(["Jan", "Feb", "Mar", "Apr", "May", "Jun"])
    if kind == "line":
        datasets = f"""[{{
          label: 'Return',
          data: [100, 112, 108, 128, 136, 151],
          borderColor: '{c0}',
          backgroundColor: '{c0}33',
          borderWidth: 4,
          tension: 0.35,
          fill: true,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: '{c0}',
          pointBorderColor: '{bg}',
          pointBorderWidth: 2
        }}]"""
        chart_type = "line"
    else:
        datasets = f"""[{{
          label: 'Spend',
          data: [42, 48, 45, 55, 52, 61],
          backgroundColor: '{c0}',
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 48
        }}, {{
          label: 'Return',
          data: [58, 64, 70, 78, 82, 94],
          backgroundColor: '{c1}',
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 48
        }}]"""
        chart_type = "bar"

    return f"""
<style>
  html, body, #mount {{ background: {bg} !important; }}
  #mount {{ padding: 0 !important; min-height: 0 !important; }}
</style>
<div class="chart-root" style="width:1120px;height:640px;padding:16px 20px 12px;box-sizing:border-box;background:{bg};">
  <canvas id="c" width="1080" height="600"></canvas>
</div>
<script>
(function() {{
  const ctx = document.getElementById('c').getContext('2d');
  new Chart(ctx, {{
    type: '{chart_type}',
    data: {{ labels: {cats}, datasets: {datasets} }},
    options: {{
      responsive: false,
      animation: false,
      layout: {{ padding: {{ top: 8, right: 12, bottom: 4, left: 4 }} }},
      plugins: {{
        legend: {{
          display: true,
          position: 'top',
          align: 'end',
          labels: {{
            color: '{tick}',
            boxWidth: 14,
            boxHeight: 14,
            padding: 16,
            font: {{ size: 15, weight: '600' }},
            usePointStyle: true
          }}
        }},
        tooltip: {{ enabled: false }}
      }},
      scales: {{
        x: {{
          grid: {{ display: false, drawBorder: false }},
          border: {{ display: true, width: 2, color: '{grid}' }},
          ticks: {{
            color: '{tick}',
            font: {{ size: 15, weight: '600' }},
            padding: 10
          }}
        }},
        y: {{
          beginAtZero: true,
          grid: {{
            color: '{grid}',
            lineWidth: 1.5,
            drawBorder: false
          }},
          border: {{ display: true, width: 2, color: '{grid}' }},
          ticks: {{
            color: '{tick}',
            font: {{ size: 14, weight: '600' }},
            padding: 10
          }}
        }}
      }}
    }}
  }});
  window.__CASE3_CHART_READY = true;
}})();
</script>
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    packs = list(PACK_IDS) if PACK_IDS else [
        "atelier", "board", "signal", "relay", "ink", "voltage", "botanical", "studio"
    ]
    for pack in packs:
        tok = resolve_deck_theme(pack)
        series = list(tok.chart_series or [])
        colors = tok.colors
        dark = _is_dark(pack, tok)
        ink = str(colors.get("ink") or "#14161a")
        muted = str(colors.get("muted") or "#6A7160")
        foil = str(colors.get("foil") or colors.get("accent") or "#4F6B14")
        for kind in ("bar", "line"):
            dest = OUT / f"{pack}_{kind}.png"
            work = WORK / f"{pack}_{kind}"
            if work.exists():
                import shutil
                shutil.rmtree(work)
            work.mkdir(parents=True)
            html = _fragment(
                kind=kind,
                series=series,
                dark=dark,
                ink=ink,
                muted=muted,
                foil=foil,
            )
            render_chart_png({"html": html}, dest, work_dir=work)
            print(f"  wrote {dest.relative_to(ROOT)} ({dest.stat().st_size // 1024}kb)")
    print("done →", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
