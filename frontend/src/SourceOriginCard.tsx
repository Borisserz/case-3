/** Rectangular original-document card. Click opens the markdown modal. */

import type { SourceAttachment } from "./domain/liberTypes";
import { sourceDocBadge } from "./domain/sourceRead";

type Props = {
  doc: SourceAttachment;
  onOpen: () => void;
};

function DocGlyph() {
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

export function SourceOriginCard({ doc, onOpen }: Props) {
  const badge = sourceDocBadge(doc);
  const title = (doc.title || doc.fileName || "Документ").trim();
  const fileName = (doc.fileName || title).trim();
  return (
    <article className="deck-file-card is-pdf is-report-pdf is-compact source-origin-card">
      <button
        type="button"
        className="deck-file-card-compact"
        onClick={onOpen}
        aria-label={`Открыть текст: ${title}`}
      >
        <span className="deck-file-card-compact-mark" aria-hidden>
          <DocGlyph />
          <span className="deck-file-card-compact-badge">{badge}</span>
        </span>
        <span className="deck-file-card-compact-copy">
          <span className="deck-file-card-compact-eyebrow">Документ · {badge}</span>
          <span className="deck-file-card-compact-title">{title}</span>
          <span className="deck-file-card-compact-file" title={fileName}>
            {fileName}
          </span>
        </span>
        <span className="deck-file-card-compact-actions">
          <span className="deck-file-card-compact-go">
            Открыть
            <span>→</span>
          </span>
        </span>
      </button>
    </article>
  );
}
