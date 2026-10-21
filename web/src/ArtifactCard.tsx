/** Compact chat card for a finished report — opens the Artifact rail. */

import { ExportMenu } from "./ExportMenu";
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
  onView: () => void;
  onOpenDiagram?: (id: string) => void;
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
  onView,
  onOpenDiagram,
}: Props) {
  return (
    <div
      className={`artifact-card${pulse ? " is-pulse" : ""}${updated ? " is-updated" : ""}`}
    >
      <button
        type="button"
        className="artifact-card-body"
        onClick={onView}
        aria-label={`Смотреть ${title}`}
      >
        <div className="artifact-card-thumb" aria-hidden>
          <PdfThumb
            pdfUrl={pdfUrl || downloads?.pdf}
            fallbackUrl={thumbUrl}
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
      <div className="artifact-card-actions">
        <button type="button" className="artifact-card-view" onClick={onView}>
          Смотреть
        </button>
        <ExportMenu downloads={downloads} label="Export" pulse={pulse} />
      </div>
    </div>
  );
}
