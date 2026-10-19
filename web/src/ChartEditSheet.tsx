/** Liber desk: tune one chart — type chips, palette, notes. Applies only on save. */

import { useEffect, useState } from "react";
import { ChartTypeChip, type ChartTypeId } from "./ChartTypePreview";

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
  caption,
  palettes,
  catalogTypes,
  initialPalette = "editorial",
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

  useEffect(() => {
    if (!open) return;
    setPalette(
      usable.some((p) => p.id === initialPalette)
        ? initialPalette
        : usable[0]?.id || "editorial",
    );
    const t =
      initialType && types.includes(initialType)
        ? initialType
        : types[0] || "bar";
    setChartType(t);
    setStyleNotes("");
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
          Пока виден текущий рисунок. Тип, палитра и текст применятся после
          «Сохранить в отчёт» — обновятся PNG и PDF/DOCX.
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
