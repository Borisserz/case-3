/** Edit Mermaid source with live preview — Apply persists via API. */

import { useEffect, useRef, useState } from "react";
import { MermaidView } from "./MermaidView";
import { useFocusTrap } from "./useFocusTrap";

type Props = {
  open: boolean;
  title: string;
  mermaid: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onApply: (mermaid: string, title: string) => void;
};

export function DiagramEditSheet({
  open,
  title: initialTitle,
  mermaid: initialMermaid,
  busy,
  error,
  onCancel,
  onApply,
}: Props) {
  const [title, setTitle] = useState(initialTitle);
  const [src, setSrc] = useState(initialMermaid);
  const sheetRef = useRef<HTMLDivElement>(null);
  useFocusTrap(sheetRef, { active: open });

  useEffect(() => {
    if (!open) return;
    setTitle(initialTitle);
    setSrc(initialMermaid);
  }, [open, initialTitle, initialMermaid]);

  if (!open) return null;

  return (
    <div className="diagram-edit-backdrop" role="presentation" onClick={onCancel}>
      <div
        ref={sheetRef}
        className="diagram-edit-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Редактировать схему"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="diagram-edit-head">
          <h3 className="diagram-edit-title">Правка Mermaid</h3>
          <button
            type="button"
            className="diagram-edit-close"
            aria-label="Закрыть"
            onClick={onCancel}
          >
            ×
          </button>
        </header>

        <label className="diagram-edit-field">
          <span>Заголовок</span>
          <input
            type="text"
            value={title}
            maxLength={80}
            onChange={(e) => setTitle(e.target.value)}
            disabled={busy}
          />
        </label>

        <label className="diagram-edit-field">
          <span>Исходник</span>
          <textarea
            value={src}
            onChange={(e) => setSrc(e.target.value)}
            rows={12}
            spellCheck={false}
            disabled={busy}
          />
        </label>

        <div className="diagram-edit-preview" aria-label="Превью">
          <MermaidView source={src} className="is-edit-preview" />
        </div>

        {error ? (
          <p className="diagram-edit-err" role="alert">
            {error}
          </p>
        ) : null}

        <footer className="diagram-edit-actions">
          <button type="button" className="btn ghost" onClick={onCancel} disabled={busy}>
            Отмена
          </button>
          <button
            type="button"
            className="btn primary diagram-pane-png"
            disabled={busy || !src.trim()}
            onClick={() => onApply(src, title)}
          >
            {busy ? "…" : "Применить"}
          </button>
        </footer>
      </div>
    </div>
  );
}
