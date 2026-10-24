/** Julius-style file card: matte stage, icon, hover CTA, footer. */

import { PdfThumb } from "./PdfThumb";

type Kind = "pptx" | "deck_pdf" | "pdf";

type Props = {
  kind: Kind;
  href: string;
  previewUrl?: string | null;
  /** Deck twin / legacy: first-page render. Report PDF uses compact teaser only. */
  pdfUrl?: string | null;
  fileLabel?: string;
  /** Human report title for the compact PDF teaser. */
  docTitle?: string | null;
  onPrimary?: () => void;
  primaryLabel?: string;
  /** Extra slide thumbs under the hero (deck). */
  filmstrip?: string[];
};

function FileGlyph({ kind }: { kind: Kind }) {
  if (kind === "pptx") {
    return (
      <svg
        className="deck-file-card-glyph"
        width="22"
        height="22"
        viewBox="0 0 22 22"
        aria-hidden
      >
        <rect
          x="2.5"
          y="4"
          width="17"
          height="13"
          rx="2.2"
          fill="currentColor"
          opacity="0.14"
        />
        <rect
          x="2.5"
          y="4"
          width="17"
          height="13"
          rx="2.2"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
        />
        <path
          d="M6 8.2h10M6 11h7.5M6 13.8h5"
          stroke="currentColor"
          strokeWidth="1.35"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  return (
    <svg
      className="deck-file-card-glyph"
      width="22"
      height="22"
      viewBox="0 0 22 22"
      aria-hidden
    >
      <path
        d="M6 2.8h7.2L17.2 7v12.2a1.6 1.6 0 0 1-1.6 1.6H6A1.6 1.6 0 0 1 4.4 19.2V4.4A1.6 1.6 0 0 1 6 2.8Z"
        fill="currentColor"
        opacity="0.12"
      />
      <path
        d="M6 2.8h7.2L17.2 7v12.2a1.6 1.6 0 0 1-1.6 1.6H6A1.6 1.6 0 0 1 4.4 19.2V4.4A1.6 1.6 0 0 1 6 2.8Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinejoin="round"
      />
      <path
        d="M13.1 2.9V7h4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.35"
        strokeLinejoin="round"
      />
      <path
        d="M7.4 11.2h7.2M7.4 14h5.4"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function DeckFileCard({
  kind,
  href,
  previewUrl = null,
  pdfUrl = null,
  fileLabel,
  docTitle = null,
  onPrimary,
  primaryLabel,
  filmstrip = [],
}: Props) {
  const isPptx = kind === "pptx";
  const isReportPdf = kind === "pdf";
  const title =
    fileLabel ||
    (isPptx ? "deck_slides.pptx" : isReportPdf ? "report.pdf" : "deck.pdf");
  const badge = isPptx ? "PPTX" : "PDF";
  const isDeckPdf = kind === "deck_pdf";
  const kindHint = isPptx
    ? "Презентация · PowerPoint"
    : isReportPdf
      ? "PDF отчёта"
      : "Презентация · PDF";
  const defaultPrimary = isPptx || isDeckPdf ? "Просмотр" : "Открыть";
  const actionLabel = primaryLabel || defaultPrimary;
  const kindClass = isPptx
    ? "is-pptx"
    : isReportPdf
      ? "is-pdf is-report-pdf"
      : "is-pdf is-deck-pdf";
  const emptyHint = isPptx
    ? "Презентация · PPTX"
    : isReportPdf
      ? "PDF отчёта"
      : "Презентация · PDF";
  const strip = filmstrip.filter(Boolean).slice(0, 6);
  const teaserTitle = (docTitle || "").trim() || title;

  /* Report PDF: compact file row — no page/chart dump, one primary CTA */
  if (isReportPdf) {
    return (
      <article className={`deck-file-card ${kindClass} is-compact`}>
        <button
          type="button"
          className="deck-file-card-compact"
          onClick={onPrimary}
          disabled={!onPrimary}
          aria-label={
            onPrimary ? `${actionLabel}: ${teaserTitle}` : teaserTitle
          }
        >
          <span className="deck-file-card-compact-mark" aria-hidden>
            <FileGlyph kind="pdf" />
            <span className="deck-file-card-compact-badge">PDF</span>
          </span>
          <span className="deck-file-card-compact-copy">
            <span className="deck-file-card-compact-eyebrow">Отчёт · PDF</span>
            <span className="deck-file-card-compact-title">{teaserTitle}</span>
            <span className="deck-file-card-compact-file" title={title}>
              {title}
            </span>
          </span>
          <span className="deck-file-card-compact-actions">
            <a
              href={href}
              download
              className="deck-file-card-compact-dl"
              onClick={(e) => e.stopPropagation()}
            >
              Скачать
            </a>
            {onPrimary ? (
              <span className="deck-file-card-compact-go" aria-hidden>
                {actionLabel}
                <span>→</span>
              </span>
            ) : null}
          </span>
        </button>
      </article>
    );
  }

  return (
    <article className={`deck-file-card ${kindClass}`}>
      <header className="deck-file-card-head">
        <span className="deck-file-card-mark" aria-hidden>
          <FileGlyph kind={kind} />
          <span className="deck-file-card-badge">{badge}</span>
        </span>
        <span className="deck-file-card-meta">
          <span className="deck-file-card-path" title={title}>
            {title}
          </span>
          <span className="deck-file-card-hint">{kindHint}</span>
        </span>
        <span className="deck-file-card-actions">
          {href && href !== "#" ? (
            <a href={href} download className="deck-file-card-action">
              Скачать
            </a>
          ) : null}
          {onPrimary ? (
            <button
              type="button"
              className="deck-file-card-action is-strong is-pill"
              onClick={onPrimary}
            >
              {actionLabel}
            </button>
          ) : null}
        </span>
      </header>

      <button
        type="button"
        className="deck-file-card-preview"
        onClick={onPrimary}
        disabled={!onPrimary}
        aria-label={
          onPrimary ? `${actionLabel}: ${title}` : `Превью ${title}`
        }
      >
        <span
          className="deck-file-card-mat"
          aria-hidden={!previewUrl && !pdfUrl}
        >
          <span className="deck-file-card-sheet">
            {previewUrl ? (
              <img src={previewUrl} alt="" />
            ) : pdfUrl ? (
              <PdfThumb
                pdfUrl={pdfUrl}
                className="deck-file-card-preview-img"
                targetWidth={920}
              />
            ) : (
              <span className="deck-file-card-preview-empty">{emptyHint}</span>
            )}
          </span>
        </span>
        {onPrimary ? (
          <span className="deck-file-card-veil" aria-hidden>
            <span className="deck-file-card-veil-label">
              {actionLabel}
              <span className="deck-file-card-veil-arrow">→</span>
            </span>
          </span>
        ) : null}
      </button>

      {strip.length > 1 ? (
        <div className="deck-file-card-filmstrip" role="list" aria-label="Слайды">
          {strip.map((src, i) => (
            <button
              key={`${src}-${i}`}
              type="button"
              className={`deck-file-card-film-thumb${i === 0 ? " is-active" : ""}`}
              onClick={onPrimary}
              aria-label={`Слайд ${i + 1}`}
            >
              <img src={src} alt="" />
              <span>{i + 1}</span>
            </button>
          ))}
        </div>
      ) : null}

    </article>
  );
}
