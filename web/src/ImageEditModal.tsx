/** Liber desk: regenerate or img2img-edit one photo — inline sheet (как графики). */

import { useEffect, useRef, useState } from "react";
import { useFocusTrap } from "./useFocusTrap";

export type ImageEditMode = "generate" | "edit";

export type ImageEditRequest = {
  figureId: string;
  mode: ImageEditMode;
  prompt: string;
  caption: string;
};

type Props = {
  open: boolean;
  /** When false, skip focus trap (multi-open edit desk). */
  trapFocus?: boolean;
  figureId: string;
  caption?: string;
  /** @deprecated Kept for callers; preview stays on the figure above (как графики). */
  previewUrl?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onSubmit: (req: ImageEditRequest) => void;
};

export function ImageEditModal({
  open,
  trapFocus = true,
  figureId,
  caption: initialCaption,
  busy,
  error,
  onCancel,
  onSubmit,
}: Props) {
  const [mode, setMode] = useState<ImageEditMode>("generate");
  const [prompt, setPrompt] = useState("");
  const [caption, setCaption] = useState("");
  const sheetRef = useRef<HTMLDivElement>(null);
  useFocusTrap(sheetRef, { active: open && trapFocus });

  useEffect(() => {
    if (!open) return;
    setMode("generate");
    setPrompt("");
    setCaption((initialCaption || "").trim());
  }, [open, figureId, initialCaption]);

  if (!open) return null;

  function apply() {
    const p = prompt.trim();
    const cap = caption.trim();
    if (!p || !cap || busy) return;
    onSubmit({ figureId, mode, prompt: p, caption: cap });
  }

  const canApply = Boolean(prompt.trim() && caption.trim()) && !busy;

  return (
    <div
      ref={sheetRef}
      className="chart-edit-sheet img-edit-sheet"
      role="region"
      aria-label="Изменить фото"
    >
      <header className="chart-edit-head">
        <div>
          <p className="chart-edit-eyebrow">живая правка · фото</p>
          <h3 className="chart-edit-title">{(initialCaption || "").trim() || figureId}</h3>
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
        <label className="field">Режим</label>
        <div className="chips img-edit-modes" role="group" aria-label="Режим">
          <button
            type="button"
            className={`chip${mode === "generate" ? " on" : ""}`}
            disabled={busy}
            onClick={() => setMode("generate")}
          >
            Новая генерация
          </button>
          <button
            type="button"
            className={`chip${mode === "edit" ? " on" : ""}`}
            disabled={busy}
            onClick={() => setMode("edit")}
          >
            Внести изменения
          </button>
        </div>
        <p className="chart-edit-foot-hint" style={{ marginTop: "0.45rem" }}>
          {mode === "generate"
            ? "Новое фото по вашему описанию"
            : "Правки поверх текущего кадра"}
        </p>
      </section>

      <section className="chart-edit-block">
        <label className="field" htmlFor={`img-cap-${figureId}`}>
          Подпись в отчёте
        </label>
        <input
          id={`img-cap-${figureId}`}
          type="text"
          placeholder="короткая подпись на русском…"
          value={caption}
          disabled={busy}
          onChange={(e) => setCaption(e.target.value)}
        />
      </section>

      <section className="chart-edit-block">
        <label className="field" htmlFor={`img-prompt-${figureId}`}>
          {mode === "generate" ? "Описание нового фото" : "Что изменить"}
        </label>
        <textarea
          id={`img-prompt-${figureId}`}
          rows={3}
          className="img-edit-textarea"
          placeholder={
            mode === "generate"
              ? "современный офисный холл, дневной свет, без текста на кадре…"
              : "сделай свет теплее, убери лишнее со стола…"
          }
          value={prompt}
          disabled={busy}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && canApply) {
              e.preventDefault();
              apply();
            }
          }}
        />
      </section>

      {error && <p className="err">{error}</p>}

      <footer className="chart-edit-foot">
        <p className="chart-edit-foot-hint">
          Подпись и PNG обновятся в чате, PDF и DOCX после «Сохранить в отчёт».
        </p>
        <div className="chart-edit-actions">
          <button
            type="button"
            className="chart-edit-apply"
            disabled={!canApply}
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
