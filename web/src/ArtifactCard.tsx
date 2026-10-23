/** Compact chat card for a finished report — opens the Artifact rail.

When deck ready: Julius-style PPTX/PDF preview cards (Export · Edit/View).
*/

import { DeckFileCard } from "./DeckFileCard";
import { DeckMakeSplit } from "./DeckMakeSplit";
import { PdfThumb } from "./PdfThumb";

type DiagramChip = { id: string; title: string };

type Props = {
  title: string;
  subtitle?: string;
  thumbUrl?: string | null;
  pdfUrl?: string | null;
  downloads?: Record<string, string>;
  pulse?: boolean;
  updated?: boolean;
  diagrams?: DiagramChip[];
  slidesStatus?: string | null;
  /** Twin preview thumbs (HTML→PNG); same tokens as PPTX. */
  slidePngs?: string[];
  onView: () => void;
  onOpenDiagram?: (id: string) => void;
  onMakePresentation?: () => void;
  onOpenPresentation?: () => void;
  onDeckStyle?: () => void;
};

export function ArtifactCard({
  title,
  subtitle,
  thumbUrl,
  pdfUrl,
  downloads,
  pulse = false,
  updated = false,
  diagrams = [],
  slidesStatus = null,
  slidePngs = [],
  onView,
  onOpenDiagram,
  onMakePresentation,
  onOpenPresentation,
  onDeckStyle,
}: Props) {
  const slidesBusy =
    slidesStatus === "running" || slidesStatus === "queued";
  const slidesReady = slidesStatus === "ok";
  const hero = slidesReady && slidePngs.length > 0 ? slidePngs[0] : null;
  const strip =
    slidesReady && slidePngs.length > 1 ? slidePngs.slice(1, 9) : [];
  const hasDeck =
    Boolean(onMakePresentation) || (slidesReady && Boolean(onOpenPresentation));
  const pptxName = downloads?.pptx
    ? decodeURIComponent(downloads.pptx.split("/").pop() || "deck.pptx")
    : "deck.pptx";
  const deckPdfName = downloads?.deck_pdf
    ? decodeURIComponent(downloads.deck_pdf.split("/").pop() || "deck.pdf")
    : "deck.pdf";

  return (
    <div
      className={`artifact-card${pulse ? " is-pulse" : ""}${updated ? " is-updated" : ""}${slidesReady ? " has-deck" : ""}`}
    >
      <button
        type="button"
        className="artifact-card-body"
        onClick={onView}
        aria-label={`Открыть ${title}`}
      >
        <div className="artifact-card-thumb" aria-hidden>
          <PdfThumb
            pdfUrl={pdfUrl || downloads?.pdf}
            fallbackUrl={thumbUrl || hero}
          />
        </div>
        <div className="artifact-card-meta">
          <span className="artifact-card-title-row">
            <span className="artifact-card-title">{title}</span>
            {updated ? (
              <span className="artifact-card-badge">обновлено</span>
            ) : null}
          </span>
          {subtitle ? (
            <span className="artifact-card-sub">{subtitle}</span>
          ) : null}
          {slidesReady ? (
            <span className="artifact-card-sub">
              Презентация готова · {slidePngs.length || "—"} слайдов
            </span>
          ) : null}
        </div>
      </button>
      {diagrams.length > 0 && onOpenDiagram ? (
        <div className="artifact-card-diagrams" role="group" aria-label="Схемы">
          {diagrams.map((d) => (
            <button
              key={d.id}
              type="button"
              className="artifact-card-diagram-chip"
              onClick={() => onOpenDiagram(d.id)}
            >
              Схема: {d.title || d.id}
            </button>
          ))}
        </div>
      ) : null}

      {slidesReady && (downloads?.pptx || downloads?.deck_pdf) ? (
        <div className="artifact-card-deck-stack" role="group" aria-label="Дека">
          {downloads.pptx ? (
            <DeckFileCard
              kind="pptx"
              href={downloads.pptx}
              previewUrl={hero}
              fileLabel={pptxName}
              onPrimary={onOpenPresentation}
              primaryLabel="Edit"
            />
          ) : null}
          {downloads.deck_pdf ? (
            <DeckFileCard
              kind="deck_pdf"
              href={downloads.deck_pdf}
              previewUrl={hero}
              fileLabel={deckPdfName}
              onPrimary={onOpenPresentation}
              primaryLabel="View"
            />
          ) : null}
          {strip.length > 0 ? (
            <div
              className="artifact-card-filmstrip"
              role="group"
              aria-label="Остальные слайды"
            >
              {strip.map((url, i) => (
                <button
                  key={`${url}-${i}`}
                  type="button"
                  className="artifact-card-slide-thumb"
                  onClick={() => onOpenPresentation?.()}
                  title={`Слайд ${i + 2}`}
                >
                  <img src={url} alt="" />
                  <span>{i + 2}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="artifact-card-actions">
        {hasDeck ? (
          <DeckMakeSplit
            busy={slidesBusy}
            ready={slidesReady}
            onMake={() => onMakePresentation?.()}
            onOpen={onOpenPresentation}
            onStyle={() => onDeckStyle?.()}
          />
        ) : null}
        <button
          type="button"
          className={`artifact-card-view${hasDeck ? " secondary" : ""}`}
          onClick={onView}
        >
          Открыть
        </button>
      </div>
    </div>
  );
}
