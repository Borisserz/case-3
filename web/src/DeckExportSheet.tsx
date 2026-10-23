/** Julius-like Export sheet for Liber deck (PPTX truth + deck PDF). */

import { useEffect } from "react";
import { createPortal } from "react-dom";

type Props = {
  open: boolean;
  onClose: () => void;
  downloads?: Record<string, string>;
  previewUrl?: string | null;
  deckPdfMode?: string | null;
  slideCount?: number;
};

export function DeckExportSheet({
  open,
  onClose,
  downloads,
  previewUrl = null,
  deckPdfMode = null,
  slideCount = 0,
}: Props) {
  const pptx = downloads?.pptx;
  const deckPdf = downloads?.deck_pdf;
  const pptxName = pptx
    ? decodeURIComponent(pptx.split("/").pop() || "deck.pptx")
    : null;
  const pdfName = deckPdf
    ? decodeURIComponent(deckPdf.split("/").pop() || "deck.pdf")
    : null;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="deck-export-sheet-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="deck-export-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="deck-export-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="deck-export-sheet-head">
          <h2 id="deck-export-title">Скачать презентацию</h2>
          <button
            type="button"
            className="deck-export-sheet-close"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </header>

        {previewUrl ? (
          <div className="deck-export-sheet-preview">
            <img src={previewUrl} alt="" />
            {slideCount > 0 ? (
              <span className="deck-export-sheet-count">
                {slideCount} слайдов
              </span>
            ) : null}
          </div>
        ) : null}

        <div className="deck-export-sheet-list">
          {pptx ? (
            <a href={pptx} download className="deck-export-sheet-item is-primary">
              <span className="deck-export-sheet-item-kicker">PPTX</span>
              <span className="deck-export-sheet-item-title">
                Скачать PowerPoint
              </span>
              <span className="deck-export-sheet-item-meta">
                {pptxName} · editable · визуальная истина
              </span>
            </a>
          ) : null}
          {deckPdf ? (
            <a href={deckPdf} download className="deck-export-sheet-item">
              <span className="deck-export-sheet-item-kicker">PDF</span>
              <span className="deck-export-sheet-item-title">
                Скачать PDF презентации
              </span>
              <span className="deck-export-sheet-item-meta">
                {pdfName}
                {deckPdfMode === "lo"
                  ? " · LibreOffice"
                  : deckPdfMode === "png_stitch"
                    ? " · PNG stitch"
                    : " · twin"}
              </span>
            </a>
          ) : null}
          {downloads?.pdf ? (
            <a
              href={downloads.pdf}
              download
              className="deck-export-sheet-item"
            >
              <span className="deck-export-sheet-item-kicker">Отчёт</span>
              <span className="deck-export-sheet-item-title">PDF отчёта</span>
              <span className="deck-export-sheet-item-meta">печатная истина</span>
            </a>
          ) : null}
          {downloads?.docx ? (
            <a
              href={downloads.docx}
              download
              className="deck-export-sheet-item"
            >
              <span className="deck-export-sheet-item-kicker">DOCX</span>
              <span className="deck-export-sheet-item-title">Скачать DOCX</span>
            </a>
          ) : null}
          {!pptx && !deckPdf && !downloads?.pdf && !downloads?.docx ? (
            <p className="deck-export-sheet-empty">Файлы ещё не готовы.</p>
          ) : null}
        </div>
      </div>
    </div>,
    document.body,
  );
}
