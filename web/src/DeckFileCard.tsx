/** Julius-style deck file card: header Export/Edit|View + large slide preview. */

type Kind = "pptx" | "deck_pdf";

type Props = {
  kind: Kind;
  href: string;
  previewUrl?: string | null;
  fileLabel?: string;
  onPrimary?: () => void;
  primaryLabel?: string;
};

export function DeckFileCard({
  kind,
  href,
  previewUrl = null,
  fileLabel,
  onPrimary,
  primaryLabel,
}: Props) {
  const isPptx = kind === "pptx";
  const title = fileLabel || (isPptx ? "deck_slides.pptx" : "deck.pdf");
  const badge = isPptx ? "PPTX" : "PDF";
  const secondary = isPptx ? "Edit" : "View";
  const actionLabel = primaryLabel || secondary;

  return (
    <article className={`deck-file-card${isPptx ? " is-pptx" : " is-pdf"}`}>
      <header className="deck-file-card-head">
        <span className="deck-file-card-badge" aria-hidden>
          {badge}
        </span>
        <span className="deck-file-card-path" title={title}>
          {title}
        </span>
        <span className="deck-file-card-actions">
          <a href={href} download className="deck-file-card-action">
            Export
          </a>
          {onPrimary ? (
            <button
              type="button"
              className="deck-file-card-action is-strong"
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
          onPrimary
            ? `${actionLabel}: ${title}`
            : `Превью ${title}`
        }
      >
        {previewUrl ? (
          <img src={previewUrl} alt="" />
        ) : (
          <span className="deck-file-card-preview-empty">
            {isPptx ? "Editable PowerPoint" : "PDF twin"}
          </span>
        )}
      </button>
    </article>
  );
}
