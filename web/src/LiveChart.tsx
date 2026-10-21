/** Live Chart.js iframe — hover tooltips (G12) + sheet preview (G9). PDF remains print truth. */

import { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  html: string;
  /** Optional title for iframe a11y. */
  title?: string;
  className?: string;
  /** Show soft “live · PDF истина” badge. */
  showBadge?: boolean;
  /** Compact height for edit sheet. */
  compact?: boolean;
};

/** Frame CSS aligned with `chart_frame.html` so donut/KPI/legend match print PNG. */
const LIVE_CSS = `
html, body { margin: 0; padding: 0; background: #ffffff; overflow: hidden; }
#mount {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  min-height: 0;
  padding: 16px 18px;
  box-sizing: border-box;
  font-family: "Segoe UI", "DejaVu Sans", sans-serif;
  color: var(--chart-ink, #1A4A4B);
  --kpi-value: var(--chart-accent, #5A6E28);
  --kpi-label: var(--chart-muted, #6A7160);
  --kpi-ink: var(--chart-ink, #3F5210);
  --chart-ink: #3F5210;
  --chart-accent: #5A6E28;
  --chart-muted: #6A7160;
}
canvas { max-width: 100%; height: auto !important; display: block; margin: 0 auto; }
.chart-card { display: flex; flex-direction: column; gap: 14px; width: 100%; }
.chart-kpi-header { display: flex; flex-direction: column; gap: 4px; padding: 0 4px 8px; }
.chart-kpi-header .eyebrow {
  font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--chart-muted, #6A7160);
}
.chart-kpi-header .big {
  font-size: 34px; font-weight: 700; letter-spacing: -0.03em; line-height: 1.05;
  color: var(--kpi-value, var(--chart-accent, #5A6E28));
}
.chart-kpi-header .context {
  font-size: 14px; font-weight: 500; color: var(--kpi-label, var(--chart-muted, #6A7160));
}
.donut-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(160px, 0.85fr);
  gap: 16px 20px;
  align-items: center;
  width: 100%;
}
.donut-viz {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}
.donut-viz canvas { margin: 0 auto; max-width: 100%; }
.donut-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  pointer-events: none; text-align: center; z-index: 1;
}
.donut-center .pct {
  font-size: 32px; font-weight: 700; letter-spacing: -0.03em; line-height: 1;
  color: var(--kpi-ink, var(--chart-ink, #3F5210));
}
.donut-center .lbl {
  margin-top: 6px; font-size: 13px; font-weight: 600;
  color: var(--kpi-label, var(--chart-muted, #6A7160)); max-width: 120px;
}
.valued-legend {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 8px;
}
.valued-legend li, .valued-legend__row {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr) auto auto;
  gap: 6px 10px; align-items: center;
  font-size: 13px; font-weight: 500; color: var(--chart-ink, #1A4A4B);
}
.valued-legend__swatch {
  width: 10px; height: 10px; border-radius: 999px; flex-shrink: 0;
}
.valued-legend__label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.valued-legend__pct {
  font-variant-numeric: tabular-nums; font-weight: 700;
  color: var(--kpi-ink, var(--chart-ink, #3F5210)); min-width: 2.8em; text-align: right;
}
.valued-legend__abs {
  font-variant-numeric: tabular-nums; color: var(--chart-muted, #6A7160);
  min-width: 2.6em; text-align: right;
}
.kpi {
  display: flex; flex-direction: column; justify-content: center;
  min-height: 200px; text-align: center; gap: 8px; padding: 12px 8px;
}
.kpi .value {
  font-size: 56px; font-weight: 700;
  color: var(--kpi-value, var(--chart-accent, #5A6E28));
  letter-spacing: -0.03em; line-height: 1;
}
.kpi .label {
  font-size: 16px; color: var(--kpi-label, var(--chart-muted, #3D5C60));
  margin-top: 4px; font-weight: 600;
}
.kpi-row {
  display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; align-items: stretch;
}
.kpi-row .kpi { min-height: 160px; flex: 1 1 140px; }
.kpi-card, .kpi-grid .kpi-card {
  padding: 12px 14px; border-radius: 12px; background: #f6f8f2;
}
@media (max-width: 520px) {
  .donut-layout { grid-template-columns: 1fr; }
}
`;

function escapeForSrcDoc(fragment: string): string {
  // Prevent breaking out of #mount / script injection via </script> in LLM HTML
  return (fragment || "").replace(/<\/(script)/gi, "<\\/$1");
}

function buildSrcDoc(fragment: string): string {
  const safe = escapeForSrcDoc(fragment);
  return `<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<meta http-equiv="Content-Security-Policy"
  content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"/>
<style>${LIVE_CSS}</style>
<script src="/vendor/chart.umd.min.js"><\/script>
<script>
  if (window.Chart) {
    Chart.defaults.animation = false;
    Chart.defaults.responsive = false;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.devicePixelRatio = Math.max(2, window.devicePixelRatio || 2);
    Chart.defaults.font.family = '"Segoe UI", "DejaVu Sans", sans-serif';
    Chart.defaults.font.size = 13;
    Chart.defaults.font.weight = "500";
    Chart.defaults.color = "#3D5C60";
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.plugins.legend.labels.padding = 14;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.tooltip.enabled = true;
    Chart.defaults.plugins.tooltip.backgroundColor = "rgba(26,52,48,0.92)";
    Chart.defaults.plugins.tooltip.titleFont = { weight: "600", size: 13 };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.elements.bar.borderRadius = 6;
    Chart.defaults.elements.bar.borderSkipped = false;
    Chart.defaults.elements.line.borderWidth = 3;
    Chart.defaults.elements.point.radius = 4;
    Chart.defaults.elements.point.hoverRadius = 6;
    Chart.defaults.interaction = { mode: "nearest", intersect: true };
    Chart.defaults.scale.grid.color = "rgba(26,74,75,0.08)";
    Chart.defaults.scale.grid.drawBorder = false;
  }
<\/script>
</head>
<body><div id="mount">${safe}</div>
<script>
  (function(){
    function fit(){
      var mount = document.getElementById("mount");
      if (!mount) return;
      // Shrink canvas CSS size to container — keeps Chart.js hit-testing (no CSS scale).
      var avail = Math.max(document.documentElement.clientWidth - 8, 120);
      mount.querySelectorAll("canvas").forEach(function(c){
        var nw = c.width || c.offsetWidth || 1;
        if (nw > avail) {
          c.style.width = avail + "px";
          c.style.height = "auto";
        } else {
          c.style.width = "";
          c.style.height = "";
        }
      });
      var h = Math.ceil(mount.getBoundingClientRect().height);
      document.documentElement.style.height = h + "px";
      document.body.style.height = h + "px";
      if (window.parent !== window) {
        window.parent.postMessage({ type: "liber-livechart-h", h: h }, "*");
      }
    }
    requestAnimationFrame(function(){
      requestAnimationFrame(function(){
        window.__CASE3_CHART_READY = true;
        fit();
        setTimeout(fit, 60);
        setTimeout(fit, 200);
      });
    });
    window.addEventListener("resize", fit);
  })();
<\/script>
</body></html>`;
}

export function LiveChart({
  html,
  title = "Живой график",
  className = "",
  showBadge = true,
  compact = false,
}: Props) {
  const [height, setHeight] = useState(compact ? 220 : 320);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const srcDoc = useMemo(() => buildSrcDoc(html), [html]);

  useEffect(() => {
    function onMsg(e: MessageEvent) {
      const d = e.data;
      if (!d || d.type !== "liber-livechart-h") return;
      if (typeof d.h !== "number" || d.h < 80) return;
      const max = compact ? 380 : 560;
      setHeight(Math.min(max, Math.max(compact ? 160 : 200, d.h)));
    }
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, [compact]);

  if (!html.trim()) {
    return (
      <div className={`live-chart is-empty ${className}`.trim()}>
        <p className="live-chart-empty">Нет HTML графика</p>
      </div>
    );
  }

  return (
    <div className={`live-chart${compact ? " is-compact" : ""} ${className}`.trim()}>
      {showBadge ? (
        <div className="live-chart-badge" aria-hidden>
          <span>live Chart.js</span>
          <span className="live-chart-badge-sep">·</span>
          <span>PDF — истина печати</span>
        </div>
      ) : null}
      <iframe
        ref={frameRef}
        className="live-chart-frame"
        title={title}
        srcDoc={srcDoc}
        sandbox="allow-scripts allow-same-origin"
        style={{ height }}
      />
    </div>
  );
}
