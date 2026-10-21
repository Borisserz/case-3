/** G12: fetch chart HTML and render live Chart.js with hover (PNG/PDF remain print truth). */

import { useEffect, useState } from "react";
import { LiveChart } from "./LiveChart";

type Props = {
  runId: string;
  chartId: string;
  caption?: string;
  /** Static PNG fallback while loading / on error. */
  fallbackUrl?: string;
  /** Cache-bust from preview URL (?v=) — refetch HTML after Apply. */
  version?: string | number | null;
  onJumpToPdf?: () => void;
  disabled?: boolean;
};

function bustFromUrl(url?: string): string {
  if (!url) return "";
  try {
    const u = new URL(url, window.location.origin);
    return u.searchParams.get("v") || "";
  } catch {
    const m = /[?&]v=([^&]+)/.exec(url);
    return m?.[1] || "";
  }
}

export function ChartLivePane({
  runId,
  chartId,
  caption,
  fallbackUrl,
  version,
  onJumpToPdf,
  disabled,
}: Props) {
  const [html, setHtml] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const rev = version ?? bustFromUrl(fallbackUrl);

  useEffect(() => {
    let cancelled = false;
    setHtml(null);
    setErr(null);
    void (async () => {
      try {
        const r = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/charts/${encodeURIComponent(chartId)}`,
        );
        if (!r.ok) throw new Error(`chart ${r.status}`);
        const data = (await r.json()) as { html?: string; type?: string };
        if (cancelled) return;
        if (!data.html) throw new Error("empty html");
        setHtml(data.html);
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "load failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId, chartId, rev]);

  if (html) {
    return (
      <div className="chart-live-pane">
        <LiveChart
          html={html}
          title={caption || chartId}
          showBadge={false}
        />
        <div className="chart-live-chrome">
          <span className="live-chart-badge" aria-hidden>
            <span>live Chart.js</span>
            <span className="live-chart-badge-sep">·</span>
            <span>наведение = значения</span>
          </span>
          {onJumpToPdf ? (
            <button
              type="button"
              className="chart-live-pdf"
              disabled={disabled}
              onClick={onJumpToPdf}
              title="Страница рисунка в PDF (истина печати)"
            >
              открыть в PDF
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  if (fallbackUrl) {
    return (
      <button
        type="button"
        className="report-fig-link"
        onClick={() => onJumpToPdf?.()}
        aria-label={caption ? `Открыть ${caption} в PDF` : "Открыть в PDF"}
        disabled={disabled}
        title={err ? `PNG · ${err}` : "PNG · переход в PDF"}
      >
        <img src={fallbackUrl} alt={caption || chartId} loading="lazy" />
      </button>
    );
  }

  return (
    <div className="report-fig-missing">
      {chartId} — {err || "загрузка…"}
    </div>
  );
}
