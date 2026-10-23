/** View-only deck PDF twin — slides as images, no download. */

import { useEffect, useId, useState } from "react";

type Props = {
  slides: string[];
  /** Optional: open full presentation pane (editor/viewer). */
  onOpenViewer?: () => void;
};

export function DeckPdfGallery({ slides, onOpenViewer }: Props) {
  const labelId = useId();
  const urls = slides.filter(Boolean);
  const [active, setActive] = useState(0);
  const safeIndex = urls.length ? Math.min(active, urls.length - 1) : 0;
  const hero = urls[safeIndex] || null;

  useEffect(() => {
    setActive(0);
  }, [urls.join("|")]);

  useEffect(() => {
    if (urls.length < 2) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
        return;
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        setActive((i) => Math.min(urls.length - 1, i + 1));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setActive((i) => Math.max(0, i - 1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [urls.length]);

  if (!urls.length) {
    return (
      <article className="deck-pdf-gallery is-empty" aria-labelledby={labelId}>
        <header className="deck-pdf-gallery-head">
          <h3 id={labelId} className="deck-pdf-gallery-title">
            Просмотр слайдов
          </h3>
          <p className="deck-pdf-gallery-sub">Превью ещё не готово</p>
        </header>
      </article>
    );
  }

  return (
    <article className="deck-pdf-gallery" aria-labelledby={labelId}>
      <header className="deck-pdf-gallery-head">
        <div className="deck-pdf-gallery-titles">
          <p className="deck-pdf-gallery-eyebrow">Только просмотр</p>
          <h3 id={labelId} className="deck-pdf-gallery-title">
            Слайды
          </h3>
        </div>
        <div className="deck-pdf-gallery-meta" aria-live="polite">
          <span className="deck-pdf-gallery-count">
            {safeIndex + 1}
            <span aria-hidden> / </span>
            {urls.length}
          </span>
          {urls.length > 1 ? (
            <span className="deck-pdf-gallery-keys" aria-hidden>
              ← →
            </span>
          ) : null}
        </div>
      </header>

      <div className="deck-pdf-gallery-stage">
        <figure className="deck-pdf-gallery-frame">
          {hero ? (
            <img
              key={hero}
              src={hero}
              alt={`Слайд ${safeIndex + 1} из ${urls.length}`}
              className="deck-pdf-gallery-hero"
            />
          ) : null}
        </figure>
        {urls.length > 1 ? (
          <div className="deck-pdf-gallery-nav" role="group" aria-label="Навигация">
            <button
              type="button"
              className="deck-pdf-gallery-nav-btn"
              disabled={safeIndex <= 0}
              onClick={() => setActive((i) => Math.max(0, i - 1))}
              aria-label="Предыдущий слайд"
            >
              ‹
            </button>
            <button
              type="button"
              className="deck-pdf-gallery-nav-btn"
              disabled={safeIndex >= urls.length - 1}
              onClick={() => setActive((i) => Math.min(urls.length - 1, i + 1))}
              aria-label="Следующий слайд"
            >
              ›
            </button>
          </div>
        ) : null}
      </div>

      {urls.length > 1 ? (
        <div
          className="deck-pdf-gallery-strip"
          role="listbox"
          aria-label="Все слайды"
          aria-activedescendant={`deck-pdf-thumb-${safeIndex}`}
        >
          {urls.map((src, i) => (
            <button
              key={`${src}-${i}`}
              id={`deck-pdf-thumb-${i}`}
              type="button"
              role="option"
              aria-selected={i === safeIndex}
              className={`deck-pdf-gallery-thumb${i === safeIndex ? " is-active" : ""}`}
              onClick={() => setActive(i)}
            >
              <img src={src} alt="" />
              <span className="deck-pdf-gallery-thumb-n">{i + 1}</span>
            </button>
          ))}
        </div>
      ) : null}

      {onOpenViewer ? (
        <footer className="deck-pdf-gallery-foot">
          <button
            type="button"
            className="deck-pdf-gallery-open"
            onClick={onOpenViewer}
          >
            Открыть в панели
            <span aria-hidden>→</span>
          </button>
        </footer>
      ) : null}
    </article>
  );
}
