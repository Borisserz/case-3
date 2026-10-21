/** Liber Atelier — advanced report settings (chat-first). */

import { useEffect, useId, useRef } from "react";
import { ChartTypeChip, type ChartTypeId } from "./ChartTypePreview";

export type PaletteInfo = {
  id: string;
  label: string;
  swatches: string[];
};

export type HealthSnapshot = {
  docker_ok: boolean;
  playwright_ok: boolean;
  vision_configured: boolean;
  image_api_configured?: boolean;
  kandinsky_configured?: boolean;
  docker_error?: string | null;
};

type Props = {
  open: boolean;
  onClose: () => void;
  docTitle: string;
  onDocTitle: (v: string) => void;
  chartAuto: boolean;
  onEnableAuto: () => void;
  types: string[];
  catalog: string[];
  onToggleType: (t: string) => void;
  chartHints: string;
  onChartHints: (v: string) => void;
  chartPalette: string;
  palettes: PaletteInfo[];
  onPalette: (id: string) => void;
  chartStyle: string;
  onChartStyle: (v: string) => void;
  maxCharts: number;
  onMaxCharts: (n: number) => void;
  maxImages: number;
  onMaxImages: (n: number) => void;
  forbidCharts: boolean;
  onForbidCharts: (v: boolean) => void;
  forbidImages: boolean;
  onForbidImages: (v: boolean) => void;
  dryRun: boolean;
  onDryRun: (v: boolean) => void;
  health: HealthSnapshot | null;
  paradeHint: string;
};

export function SettingsModal({
  open,
  onClose,
  docTitle,
  onDocTitle,
  chartAuto,
  onEnableAuto,
  types,
  catalog,
  onToggleType,
  chartHints,
  onChartHints,
  chartPalette,
  palettes,
  onPalette,
  chartStyle,
  onChartStyle,
  maxCharts,
  onMaxCharts,
  maxImages,
  onMaxImages,
  forbidCharts,
  onForbidCharts,
  forbidImages,
  onForbidImages,
  dryRun,
  onDryRun,
  health,
  paradeHint,
}: Props) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panelRef.current?.querySelector<HTMLElement>("input,button")?.focus();
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="settings-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="settings-modal-sheet" ref={panelRef}>
        <header className="settings-modal-head">
          <div>
            <p className="settings-modal-eyebrow">atelier · настройки</p>
            <h2 id={titleId} className="settings-modal-title">
              Как собрать отчёт
            </h2>
          </div>
          <button
            type="button"
            className="settings-modal-x"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </header>

        <div className="settings-modal-body">
          <section className="settings-block" aria-labelledby="set-doc">
            <h3 className="settings-block-title" id="set-doc">
              Документ
            </h3>
            <label className="field" htmlFor="set-doc-title">
              Название
            </label>
            <input
              id="set-doc-title"
              type="text"
              maxLength={200}
              placeholder="Титул PDF/DOCX — пусто, модель придумает"
              value={docTitle}
              onChange={(e) => onDocTitle(e.target.value)}
            />
          </section>

          <section className="settings-block" aria-labelledby="set-charts">
            <h3 className="settings-block-title" id="set-charts">
              Графики
            </h3>
            <label className="field">Тип</label>
            <div className="chips">
              <ChartTypeChip
                typeId="auto"
                className={`chip auto${chartAuto ? " on" : ""}`}
                onClick={onEnableAuto}
                disabled={forbidCharts}
              >
                на усмотрение модели
              </ChartTypeChip>
              {catalog.map((t) => (
                <ChartTypeChip
                  key={t}
                  typeId={t as ChartTypeId}
                  className={`chip${!chartAuto && types.includes(t) ? " on" : ""}`}
                  onClick={() => onToggleType(t)}
                  disabled={forbidCharts}
                >
                  {t}
                </ChartTypeChip>
              ))}
            </div>

            <label className="field" htmlFor="set-hints">
              Свой тип / пожелание
            </label>
            <input
              id="set-hints"
              type="text"
              placeholder="pie, воронка, сравнение долей…"
              value={chartHints}
              disabled={forbidCharts}
              onChange={(e) => onChartHints(e.target.value)}
            />

            <label className="field">Палитра</label>
            <div className="chips palettes">
              {palettes.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`chip palette${chartPalette === p.id ? " on" : ""}`}
                  disabled={forbidCharts}
                  onClick={() => onPalette(p.id)}
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

            <label className="field" htmlFor="set-style">
              Стиль / нюансы
            </label>
            <input
              id="set-style"
              type="text"
              placeholder="без сетки, толще линии, легенда снизу…"
              value={chartStyle}
              disabled={forbidCharts}
              onChange={(e) => onChartStyle(e.target.value)}
            />
          </section>

          <section className="settings-block" aria-labelledby="set-limits">
            <h3 className="settings-block-title" id="set-limits">
              Лимиты
            </h3>
            <div className="row">
              <div>
                <label className="field" htmlFor="set-max-c">
                  Графиков ≤
                </label>
                <input
                  id="set-max-c"
                  type="number"
                  min={0}
                  max={8}
                  value={maxCharts}
                  disabled={forbidCharts}
                  onChange={(e) => onMaxCharts(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="field" htmlFor="set-max-i">
                  Картинок ≤
                </label>
                <input
                  id="set-max-i"
                  type="number"
                  min={0}
                  max={8}
                  value={maxImages}
                  disabled={forbidImages}
                  onChange={(e) => onMaxImages(Number(e.target.value))}
                />
              </div>
            </div>
            <label className="check">
              <input
                type="checkbox"
                checked={forbidCharts}
                onChange={(e) => onForbidCharts(e.target.checked)}
              />
              Без графиков
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={forbidImages}
                onChange={(e) => onForbidImages(e.target.checked)}
              />
              Без фото (Image API)
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => onDryRun(e.target.checked)}
              />
              Dry-run (без LLM)
            </label>
          </section>

          <section className="settings-block settings-health" aria-labelledby="set-health">
            <h3 className="settings-block-title" id="set-health">
              Статус
            </h3>
            {!health && <p className="hint">Проверка API…</p>}
            {health && (
              <div className="health-grid">
                <div className="health-row">
                  <span>Docker</span>
                  <span className={`val${health.docker_ok ? "" : " bad"}`}>
                    {health.docker_ok ? "ok" : health.docker_error || "fail"}
                  </span>
                </div>
                <div className="health-row">
                  <span>Vision</span>
                  <span className={`val${health.vision_configured ? "" : " bad"}`}>
                    {health.vision_configured ? "ok" : "нет"}
                  </span>
                </div>
                <div className="health-row">
                  <span>Playwright</span>
                  <span className={`val${health.playwright_ok ? "" : " bad"}`}>
                    {health.playwright_ok ? "ok" : "нет"}
                  </span>
                </div>
                <div className="health-row">
                  <span>Image API</span>
                  <span
                    className={`val${
                      health.image_api_configured || health.kandinsky_configured
                        ? ""
                        : " bad"
                    }`}
                  >
                    {health.image_api_configured || health.kandinsky_configured
                      ? "ok"
                      : "нет"}
                  </span>
                </div>
              </div>
            )}
            <p className="health-foot">{paradeHint}</p>
          </section>
        </div>

        <footer className="settings-modal-foot">
          <button type="button" className="settings-modal-done" onClick={onClose}>
            Готово
          </button>
        </footer>
      </div>
    </div>
  );
}
