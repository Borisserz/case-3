/** Liber desk: tune one chart — type chips, palette, notes. Preview swaps the figure above (G9). */

import { useEffect, useRef, useState } from "react";
import {
  ChartTypeChip,
  chartTypeChipLabel,
  type ChartTypeId,
} from "./ChartTypePreview";
import { useFocusTrap } from "./useFocusTrap";

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
  /** Live HTML for the figure above — do not render a second chart here. */
  onPreviewHtml?: (html: string | null) => void;
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
  onPreviewHtml,
}: Props) {
  const usable = palettes.filter((p) => p.id !== "auto");
  const types = catalogTypes.filter(Boolean);
  const [palette, setPalette] = useState(initialPalette);
  const [chartType, setChartType] = useState(initialType || types[0] || "bar");
  const [styleNotes, setStyleNotes] = useState("");
  const [liveLoading, setLiveLoading] = useState(false);
  /** Local preview failure — keep last good HTML above; do not blank forever. */
  const [previewError, setPreviewError] = useState<string | null>(null);
  const previewSeq = useRef(0);
  const sheetRef = useRef<HTMLDivElement>(null);
  useFocusTrap(sheetRef, { active: open });

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
    setPreviewError(null);
    onPreviewHtml?.(null);
  }, [open, figureId, initialPalette, initialType]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) {
      setPreviewError(null);
      onPreviewHtml?.(null);
      return;
    }
    return () => {
      setPreviewError(null);
      onPreviewHtml?.(null);
    };
  }, [open, onPreviewHtml]);

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

  // G9: debounce preview → swap figure above (no second chart); style notes deferred to Apply
  useEffect(() => {
    if (!open || !runId || !figureId) return;
    const seq = ++previewSeq.current;
    setLiveLoading(true);
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
          setPreviewError(null);
          onPreviewHtml?.(data.html || null);
        } catch (exc) {
          if (seq !== previewSeq.current) return;
          // Keep last good preview (or original when still null) — never blank forever.
          const msg =
            exc instanceof Error
              ? exc.message.slice(0, 160)
              : "не удалось обновить превью";
          setPreviewError(msg || "не удалось обновить превью");
        } finally {
          if (seq === previewSeq.current) setLiveLoading(false);
        }
      })();
    }, 280);
    return () => window.clearTimeout(timer);
  }, [open, runId, figureId, palette, chartType, onPreviewHtml]);

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
    <div
      ref={sheetRef}
      className="chart-edit-sheet"
      role="region"
      aria-label="Изменить график"
    >
      <header className="chart-edit-head">
        <div>
          <p className="chart-edit-eyebrow">
            правка на столе
            {liveLoading
              ? " · обновляю превью…"
              : dirtyType || dirtyPalette
                ? " · черновик на рисунке выше"
                : ""}
          </p>
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
              preview={false}
              onClick={() => setChartType(t)}
            >
              {chartTypeChipLabel(t)}
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
        <p className="chart-edit-style-hint">
          превью без текста стиля; текст применится при сохранении
        </p>
      </section>

      {previewError && (
        <p className="err chart-edit-preview-err" role="status">
          Превью: {previewError}
        </p>
      )}
      {error && <p className="err">{error}</p>}

      <footer className="chart-edit-foot">
        <p className="chart-edit-foot-hint">
          Рисунок выше — черновик. «Сохранить в отчёт» пересоберёт PNG и PDF/DOCX
          (PDF — истина печати).
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
