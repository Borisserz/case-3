/** Compact chat card for a finished report — opens the Artifact rail. */

import { ExportMenu } from "./ExportMenu";
import { PdfThumb } from "./PdfThumb";

type Props = {
  title: string;
  subtitle?: string;
  thumbUrl?: string | null;
  pdfUrl?: string | null;
  downloads?: Record<string, string>;
  pulse?: boolean;
  updated?: boolean;
  onView: () => void;
};

export function ArtifactCard({
  title,
  subtitle,
  thumbUrl,
  pdfUrl,
  downloads,
  pulse = false,
  updated = false,
  onView,
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
      <div className="artifact-card-actions">
        <button type="button" className="artifact-card-view" onClick={onView}>
          Смотреть
        </button>
        <ExportMenu downloads={downloads} label="Export" pulse={pulse} />
      </div>
    </div>
  );
}
