/** Liber Atelier — report limits + desk health (chart type/style live in edit sheet). */

import { useEffect, useId, useRef } from "react";
import { useFocusTrap } from "./useFocusTrap";

export type DeskProbeSnapshot = {
  id: string;
  label: string;
  status: string;
  hint?: string | null;
};

export type HealthSnapshot = {
  docker_ok: boolean;
  playwright_ok: boolean;
  vision_configured: boolean;
  vision_ok?: boolean;
  image_api_configured?: boolean;
  kandinsky_configured?: boolean;
  image_api_ok?: boolean;
  image_api_error?: string | null;
  docker_error?: string | null;
  soffice_ok?: boolean;
  soffice_hint?: string | null;
  probes?: DeskProbeSnapshot[];
};

type Props = {
  open: boolean;
  onClose: () => void;
  maxCharts: number;
  onMaxCharts: (n: number) => void;
  maxImages: number;
  onMaxImages: (n: number) => void;
  maxDiagrams: number;
  onMaxDiagrams: (n: number) => void;
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
  maxCharts,
  onMaxCharts,
  maxImages,
  onMaxImages,
  maxDiagrams,
  onMaxDiagrams,
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
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, { active: open });

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={dialogRef}
      className="settings-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="settings-modal-sheet">
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
          <section className="settings-block" aria-labelledby="set-limits">
            <h3 className="settings-block-title" id="set-limits">
              Лимиты
            </h3>
            <div className="row settings-limits-row">
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
              <div>
                <label className="field" htmlFor="set-max-d">
                  Схем ≤
                </label>
                <input
                  id="set-max-d"
                  type="number"
                  min={0}
                  max={3}
                  value={maxDiagrams}
                  onChange={(e) => onMaxDiagrams(Number(e.target.value))}
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

          <section
            className="settings-block settings-health"
            aria-labelledby="set-health"
          >
            <h3 className="settings-block-title" id="set-health">
              Desk
            </h3>
            {!health && <p className="hint">Проверка API…</p>}
            {health && (
              <ul className="desk-health-list">
                {(
                  health.probes || [
                    {
                      id: "vision",
                      label: "Qwen / Vision",
                      status: health.vision_ok
                        ? "green"
                        : health.vision_configured
                          ? "amber"
                          : "red",
                      hint: health.vision_configured
                        ? null
                        : "VISION_API_BASE_URL",
                    },
                    {
                      id: "image",
                      label: "Image API",
                      status: health.image_api_ok
                        ? "green"
                        : health.image_api_configured ||
                            health.kandinsky_configured
                          ? "amber"
                          : "amber",
                      hint: health.image_api_error,
                    },
                    {
                      id: "docker",
                      label: "Docker TeX",
                      status: health.docker_ok ? "green" : "red",
                      hint: health.docker_error,
                    },
                    {
                      id: "soffice",
                      label: "LibreOffice",
                      status: health.soffice_ok ? "green" : "amber",
                      hint: health.soffice_hint,
                    },
                    {
                      id: "playwright",
                      label: "Playwright",
                      status: health.playwright_ok ? "green" : "red",
                      hint: null,
                    },
                  ]
                ).map((p) => (
                  <li key={p.id} className="desk-health-row">
                    <span
                      className={`desk-health-dot is-${p.status}`}
                      aria-hidden
                    />
                    <span className="desk-health-label">{p.label}</span>
                    <span className={`desk-health-val is-${p.status}`}>
                      {p.status === "green"
                        ? "ok"
                        : p.status === "amber"
                          ? "внимание"
                          : "нет"}
                    </span>
                    {p.hint ? (
                      <span className="desk-health-hint">{p.hint}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
            <p className="health-foot">{paradeHint}</p>
          </section>
        </div>

        <footer className="settings-modal-foot">
          <button
            type="button"
            className="settings-modal-done"
            onClick={onClose}
          >
            Готово
          </button>
        </footer>
      </div>
    </div>
  );
}
