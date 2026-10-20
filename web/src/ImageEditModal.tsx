/** Liber: regenerate or img2img-edit one photo figure. */

import { useEffect, useState } from "react";

export type ImageEditMode = "generate" | "edit";

export type ImageEditRequest = {
  figureId: string;
  mode: ImageEditMode;
  prompt: string;
};

type Props = {
  open: boolean;
  figureId: string;
  caption?: string;
  previewUrl?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onSubmit: (req: ImageEditRequest) => void;
};

export function ImageEditModal({
  open,
  figureId,
  caption,
  previewUrl,
  busy,
  error,
  onCancel,
  onSubmit,
}: Props) {
  const [mode, setMode] = useState<ImageEditMode>("generate");
  const [prompt, setPrompt] = useState("");

  useEffect(() => {
    if (!open) return;
    setMode("generate");
    setPrompt("");
  }, [open, figureId]);

  if (!open) return null;

  function apply() {
    const p = prompt.trim();
    if (!p || busy) return;
    onSubmit({ figureId, mode, prompt: p });
  }

  return (
    <div className="img-edit-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="img-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Изменить фото"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="img-edit-head">
          <div>
            <p className="img-edit-eyebrow">фото · Image API</p>
            <h3 className="img-edit-title">{caption?.trim() || figureId}</h3>
          </div>
          <button
            type="button"
            className="img-edit-x"
            onClick={onCancel}
            disabled={busy}
            aria-label="Закрыть"
          >
            ×
          </button>
        </header>

        {previewUrl && (
          <div className="img-edit-preview">
            <img src={previewUrl} alt="" />
          </div>
        )}

        <div className="img-edit-modes" role="group" aria-label="Режим">
          <button
            type="button"
            className={`img-edit-mode${mode === "generate" ? " on" : ""}`}
            disabled={busy}
            onClick={() => setMode("generate")}
          >
            Новая генерация
            <span>с нуля по промпту → /generate</span>
          </button>
          <button
            type="button"
            className={`img-edit-mode${mode === "edit" ? " on" : ""}`}
            disabled={busy}
            onClick={() => setMode("edit")}
          >
            Внести изменения
            <span>текущее фото + правки → /edit</span>
          </button>
        </div>

        <label className="field" htmlFor={`img-prompt-${figureId}`}>
          {mode === "generate" ? "Описание нового фото" : "Что изменить"}
        </label>
        <textarea
          id={`img-prompt-${figureId}`}
          rows={3}
          placeholder={
            mode === "generate"
              ? "sharp photo of a modern office lobby, daylight, no text…"
              : "make lighting warmer, remove clutter on the desk…"
          }
          value={prompt}
          disabled={busy}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !busy) {
              e.preventDefault();
              apply();
            }
          }}
        />

        {error && <p className="err">{error}</p>}

        <footer className="img-edit-foot">
          <p className="img-edit-hint">
            PNG обновится в чате, PDF и DOCX после применения.
          </p>
          <div className="img-edit-actions">
            <button
              type="button"
              className="img-edit-apply"
              disabled={busy || !prompt.trim()}
              onClick={apply}
            >
              {busy ? "Генерирую…" : "Применить"}
            </button>
            <button
              type="button"
              className="img-edit-cancel"
              disabled={busy}
              onClick={onCancel}
            >
              Отмена
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
