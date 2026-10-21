/** Liber desk: tune one chart — type chips, palette, notes. Live preview before Apply (G9). */

import { useEffect, useRef, useState } from "react";
import { ChartTypeChip, type ChartTypeId } from "./ChartTypePreview";
import { LiveChart } from "./LiveChart";

export type PaletteInfo = {
  id: string;
  label: string;
  swatches: string[];
};

export type ChartEditRequest = {
  figureId: string;
  palette: string;
  styleNotes: string;
  chartType: string;
};

export type ChartEditDraft = {
  palette: string;
  chartType: string;
  paletteLabel?: string;
  wash?: string;
};

type Props = {
  open: boolean;
  figureId: string;
  runId?: string;
  caption?: string;
  palettes: PaletteInfo[];
  catalogTypes: string[];
  initialPalette?: string;
  initialType?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onSubmit: (req: ChartEditRequest) => void;
  onDraftChange?: (draft: ChartEditDraft) => void;
};

export function ChartEditSheet({
  open,
  figureId,
  runId,
  caption,
  palettes,
  catalogTypes,
  initialPalette = "atelier",
  initialType = "",
  busy,
  error,
  onCancel,
  onSubmit,
  onDraftChange,
}: Props) {
  const usable = palettes.filter((p) => p.id !== "auto");
  const types = catalogTypes.filter(Boolean);
  const [palette, setPalette] = useState(initialPalette);
  const [chartType, setChartType] = useState(initialType || types[0] || "bar");
  const [styleNotes, setStyleNotes] = useState("");
  const [liveHtml, setLiveHtml] = useState<string | null>(null);
  const [liveErr, setLiveErr] = useState<string | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const previewSeq = useRef(0);

  useEffect(() => {
    if (!open) return;
    setPalette(
      usable.some((p) => p.id === initialPalette)
        ? initialPalette
        : usable[0]?.id || "atelier",
    );
    const t =
      initialType && types.includes(initialType)
        ? initialType
        : types[0] || "bar";
    setChartType(t);
    setStyleNotes("");
    setLiveHtml(null);
    setLiveErr(null);
  }, [open, figureId, initialPalette, initialType]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open || !onDraftChange) return;
    const info = usable.find((p) => p.id === palette);
    onDraftChange({
      palette,
      chartType,
      paletteLabel: info?.label || palette,
      wash: info?.swatches?.[0],
    });
  }, [open, palette, chartType, onDraftChange]); // eslint-disable-line react-hooks/exhaustive-deps

  // G9: debounce local preview (palette + type) — style notes wait for Apply
  useEffect(() => {
    if (!open || !runId || !figureId) return;
    const seq = ++previewSeq.current;
    setLiveLoading(true);
    setLiveErr(null);
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const r = await fetch(
            `/api/runs/${encodeURIComponent(runId)}/charts/${encodeURIComponent(figureId)}/preview`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ palette, chart_type: chartType }),
            },
          );
          if (seq !== previewSeq.current) return;
          if (!r.ok) {
            const detail = await r.text();
            throw new Error(detail.slice(0, 180) || `preview ${r.status}`);
          }
          const data = (await r.json()) as { html?: string };
          if (seq !== previewSeq.current) return;
          setLiveHtml(data.html || null);
          setLiveErr(null);
        } catch (e) {
          if (seq !== previewSeq.current) return;
          setLiveErr(e instanceof Error ? e.message : "Превью недоступно");
        } finally {
          if (seq === previewSeq.current) setLiveLoading(false);
        }
      })();
    }, 280);
    return () => window.clearTimeout(timer);
  }, [open, runId, figureId, palette, chartType]);

  if (!open) return null;

  const dirtyType = Boolean(initialType) && chartType !== initialType;
  const dirtyPalette =
    Boolean(initialPalette) && palette !== initialPalette && initialPalette !== "auto";

  function apply() {
    onSubmit({
      figureId,
      palette,
      styleNotes: styleNotes.trim(),
      chartType,
    });
  }

  return (
    <div className="chart-edit-sheet" role="region" aria-label="Изменить график">
      <header className="chart-edit-head">
        <div>
          <p className="chart-edit-eyebrow">живая правка · на столе</p>
          <h3 className="chart-edit-title">{caption?.trim() || figureId}</h3>
        </div>
        <button
          type="button"
          className="chart-edit-x"
          onClick={onCancel}
          disabled={busy}
          aria-label="Закрыть"
        >
          ×
        </button>
      </header>

      <section className="chart-edit-live" aria-live="polite">
        <div className="chart-edit-labelrow">
          <label className="field">Превью до сохранения</label>
          {liveLoading ? (
            <span className="chart-edit-badge">обновляю…</span>
          ) : dirtyType || dirtyPalette ? (
            <span className="chart-edit-badge">черновик</span>
          ) : null}
        </div>
        {liveHtml ? (
          <LiveChart
            html={liveHtml}
            title={`Превью ${caption || figureId}`}
            compact
            showBadge
          />
        ) : (
          <div className="chart-edit-live-fallback">
            {liveErr
              ? `Превью: ${liveErr}`
              : liveLoading
                ? "Строю live Chart.js…"
                : runId
                  ? "Жду превью…"
                  : "Нет runId — превью недоступно"}
          </div>
        )}
        {styleNotes.trim() ? (
          <p className="chart-edit-live-note">
            Текст «как изменить» применится только при сохранении (LLM).
          </p>
        ) : null}
      </section>

      <section className="chart-edit-block">
        <div className="chart-edit-labelrow">
          <label className="field">Тип графика</label>
          {dirtyType && <span className="chart-edit-badge">сменится при сохранении</span>}
        </div>
        <div className="chips chart-edit-types" role="group" aria-label="Тип графика">
          {types.map((t) => (
            <ChartTypeChip
              key={t}
              typeId={t as ChartTypeId}
              className={`chip${chartType === t ? " on" : ""}`}
              disabled={busy}
              onClick={() => setChartType(t)}
            >
              {t}
            </ChartTypeChip>
          ))}
        </div>
      </section>

      <section className="chart-edit-block">
        <div className="chart-edit-labelrow">
          <label className="field">Палитра</label>
          {dirtyPalette && (
            <span className="chart-edit-badge">сменится при сохранении</span>
          )}
        </div>
        <div className="chips palettes" role="group" aria-label="Палитра">
          {usable.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`chip palette${palette === p.id ? " on" : ""}`}
              disabled={busy}
              onClick={() => setPalette(p.id)}
              title={p.label}
            >
              <span className="swatches" aria-hidden>
                {p.swatches.slice(0, 4).map((c) => (
                  <span key={c} className="swatch" style={{ background: c }} />
                ))}
              </span>
              {p.label}
            </button>
          ))}
        </div>
      </section>

      <section className="chart-edit-block">
        <label className="field" htmlFor={`style-${figureId}`}>
          Как изменить
        </label>
        <input
          id={`style-${figureId}`}
          type="text"
          placeholder="толще линии, легенда снизу, без сетки…"
          value={styleNotes}
          disabled={busy}
          onChange={(e) => setStyleNotes(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !busy) {
              e.preventDefault();
              apply();
            }
          }}
        />
      </section>

      {error && <p className="err">{error}</p>}

      <footer className="chart-edit-foot">
        <p className="chart-edit-foot-hint">
          Live выше — черновик. «Сохранить в отчёт» пересоберёт PNG и PDF/DOCX
          (PDF остаётся истиной печати).
        </p>
        <div className="chart-edit-actions">
          <button
            type="button"
            className="chart-edit-apply"
            disabled={busy}
            onClick={apply}
          >
            {busy ? "Пересобираю…" : "Сохранить в отчёт"}
          </button>
          <button
            type="button"
            className="chart-edit-cancel"
            disabled={busy}
            onClick={onCancel}
          >
            Отмена
          </button>
        </div>
      </footer>
    </div>
  );
}
