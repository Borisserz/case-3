/** In-chat Julius artifact previews — large DeckFileCards; rail opens on click. */

import { DeckFileCard } from "./DeckFileCard";
import { DiagramChatCard, type DiagramChatItem } from "./DiagramChatCard";
import type { DeckIR } from "./deckTypes";
import { reportDownloadLinks } from "./domain/reportDownloads";
import { modeSurfaces } from "./domain/liberModes";

type DiagramChip = DiagramChatItem;

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
  slidesStage?: string | null;
  /** Twin preview thumbs (HTML→PNG); same tokens as PPTX. */
  slidePngs?: string[];
  /** Live deck IR for crisp chat hero (vs PNG downscale). */
  deck?: DeckIR | null;
  runId?: string | null;
  /** Liber run mode — gates which cards/CTAs appear. */
  outputMode?: string | null;
  onView: () => void;
  onOpenDiagram?: (id: string) => void;
  onOpenPresentation?: () => void;
  /** Open vertical Слайды film (deck PDF twin). */
  onOpenDeckSlides?: () => void;
};

function fileNameFromUrl(url: string, fallback: string): string {
  try {
    const raw = (url.split("/").pop() || fallback).split("?")[0] || fallback;
    const name = decodeURIComponent(raw);
    // Pipeline stems uploads as source.txt → source.pdf; show a human label.
    if (/^source\.pdf$/i.test(name)) return "Отчёт.pdf";
    if (/^source\.docx$/i.test(name)) return "Отчёт.docx";
    return name || fallback;
  } catch {
    return fallback;
  }
}

function slideWord(n: number): string {
  if (n === 1) return "слайд";
  if (n > 1 && n < 5) return "слайда";
  return "слайдов";
}

function deckStageLabel(stage?: string | null): string {
  switch (stage) {
    case "queued":
      return "В очереди";
    case "starting":
      return "Запускаю сборку";
    case "llm":
    case "llm_retry":
    case "plan":
    case "ir":
      return "Пишу структуру слайдов";
    case "diagrams":
    case "media":
    case "charts":
      return "Готовлю графики и медиа";
    case "render":
      return "Рисую twin-превью";
    case "pptx":
    case "pdf":
      return "Собираю editable PPTX";
    case "patch":
      return "Сохраняю правки";
    default:
      return "Собираю презентацию";
  }
}

function deckStepIndex(stage?: string | null): number {
  if (
    !stage ||
    stage === "queued" ||
    stage === "starting" ||
    stage === "llm" ||
    stage === "llm_retry" ||
    stage === "plan" ||
    stage === "ir"
  ) {
    return 0;
  }
  if (stage === "diagrams" || stage === "media" || stage === "charts") return 1;
  if (stage === "render") return 2;
  return 3;
}

function DeckBuildCard({ stage }: { stage?: string | null }) {
  const steps = ["Структура", "Медиа", "Twin", "PPTX"] as const;
  const idx = deckStepIndex(stage);
  return (
    <div className="deck-build-card" aria-busy="true">
      <p className="deck-build-card-label">{deckStageLabel(stage)}</p>
      <ol className="deck-build-card-steps" aria-label="Этапы сборки">
        {steps.map((label, i) => (
          <li
            key={label}
            className={
              i < idx ? "is-done" : i === idx ? "is-now" : ""
            }
          >
            {label}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ArtifactCard({
  title,
  subtitle,
  pdfUrl,
  downloads,
  pulse = false,
  updated = false,
  diagrams = [],
  slidesStatus = null,
  slidesStage = null,
  slidePngs = [],
  deck = null,
  runId = null,
  outputMode = null,
  onView,
  onOpenDiagram,
  onOpenPresentation,
  onOpenDeckSlides,
}: Props) {
  const surfaces = modeSurfaces(outputMode);
  const slidesBusy =
    surfaces.showPresentation &&
    (slidesStatus === "running" ||
      slidesStatus === "queued" ||
      slidesStatus === "starting");
  const slidesReady = surfaces.showPresentation && slidesStatus === "ok";
  const hero = slidesReady && slidePngs.length > 0 ? slidePngs[0] : null;
  const reportPdfHref = surfaces.showReportPdf
    ? pdfUrl || downloads?.pdf || null
    : null;
  const reportPrintLinks = reportDownloadLinks(downloads, {
    enabled: surfaces.showReportPdf,
  });
  const reportDocxHref =
    reportPrintLinks.find((l) => l.kind === "docx")?.href ?? null;
  const visibleDiagrams = surfaces.showDiagram ? diagrams : [];
  const hasDeckFiles =
    slidesReady && Boolean(downloads?.pptx || downloads?.deck_pdf);
  const pptxName = downloads?.pptx
    ? fileNameFromUrl(downloads.pptx, "deck.pptx")
    : "deck.pptx";
  const reportPdfName = reportPdfHref
    ? fileNameFromUrl(reportPdfHref, "report.pdf")
    : "report.pdf";
  const reportDocxName = reportDocxHref
    ? fileNameFromUrl(reportDocxHref, "report.docx")
    : "report.docx";
  const reportCardHref = reportPdfHref || reportDocxHref;
  const showPdfGallery =
    surfaces.showPresentation &&
    (Boolean(downloads?.deck_pdf) || slidePngs.length > 0);

  const shellClass = [
    "artifact-card",
    "is-julius",
    pulse ? "is-pulse" : "",
    updated ? "is-updated" : "",
    hasDeckFiles || reportPdfHref || reportDocxHref ? "has-deck" : "",
  ]
    .filter(Boolean)
    .join(" ");

  /* 0) Diagram mode — Julius: live Mermaid + snippet (never PDF/report card) */
  if (
    surfaces.mode === "diagram" &&
    visibleDiagrams.length > 0 &&
    onOpenDiagram
  ) {
    return (
      <div className={shellClass}>
        <DiagramChatCard
          diagram={visibleDiagrams[0]}
          siblings={visibleDiagrams}
          onOpen={onOpenDiagram}
        />
      </div>
    );
  }

  /* 1) Deck ready → large PPTX / deck PDF stack only */
  if (hasDeckFiles) {
    return (
      <div className={shellClass}>
        <div className="artifact-card-deck-stack" role="group" aria-label="Дека">
          {downloads?.pptx ? (
            <section className="artifact-card-block">
              <p className="artifact-card-quiet-label">
                Презентация · PPTX
                {slidePngs.length > 0
                  ? ` · ${slidePngs.length}\u00a0${slideWord(slidePngs.length)}`
                  : ""}
                {updated ? " · обновлено" : ""}
              </p>
              <DeckFileCard
                kind="pptx"
                href={downloads.pptx}
                previewUrl={hero}
                fileLabel={pptxName}
                filmstrip={slidePngs}
                deck={deck}
                runId={runId}
                onPrimary={onOpenPresentation}
                primaryLabel="Просмотр"
              />
            </section>
          ) : null}
          {showPdfGallery && (downloads?.deck_pdf || hero || deck) ? (
            <section className="artifact-card-block">
              <p className="artifact-card-quiet-label">
                Презентация · PDF
                {slidePngs.length > 0
                  ? ` · ${slidePngs.length}\u00a0${slideWord(slidePngs.length)}`
                  : ""}
              </p>
              <DeckFileCard
                kind="deck_pdf"
                href={downloads?.deck_pdf || downloads?.pptx || "#"}
                previewUrl={hero}
                fileLabel={
                  downloads?.deck_pdf
                    ? fileNameFromUrl(downloads.deck_pdf, "deck.pdf")
                    : "deck.pdf"
                }
                filmstrip={slidePngs}
                deck={deck}
                runId={runId}
                onPrimary={onOpenDeckSlides || onOpenPresentation}
                primaryLabel="Просмотр"
              />
            </section>
          ) : null}
        </div>
        {slidesBusy ? <DeckBuildCard stage={slidesStage} /> : null}
      </div>
    );
  }

  /* 2) One report card (Source → PDF + DOCX); schema is peer when present */
  if (reportCardHref) {
    const formatsLabel = reportPdfHref
      ? reportDocxHref
        ? "Отчёт · PDF · DOCX"
        : "Отчёт · PDF"
      : "Отчёт · DOCX";
    return (
      <div className={shellClass}>
        <div
          className="artifact-card-deck-stack"
          role="group"
          aria-label="Артефакты отчёта"
        >
          <section className="artifact-card-block">
            {updated || subtitle ? (
              <p className="artifact-card-quiet-label">
                {updated ? "Обновлено" : null}
                {updated && subtitle ? " · " : null}
                {subtitle || null}
              </p>
            ) : (
              <p className="artifact-card-quiet-label">{formatsLabel}</p>
            )}
            {reportPdfHref ? (
              <DeckFileCard
                kind="pdf"
                href={reportPdfHref}
                docxHref={reportDocxHref}
                docTitle={title}
                fileLabel={reportPdfName}
                onPrimary={onView}
                primaryLabel="Открыть"
              />
            ) : (
              <DeckFileCard
                kind="docx"
                href={reportDocxHref!}
                docTitle={title}
                fileLabel={reportDocxName}
              />
            )}
          </section>
          {visibleDiagrams.length > 0 && onOpenDiagram ? (
            <section className="artifact-card-block is-diagram-peer">
              <p className="artifact-card-quiet-label">
                Схема
                {visibleDiagrams.length > 1
                  ? ` · ${visibleDiagrams.length}`
                  : ""}
              </p>
              <DiagramChatCard
                diagram={visibleDiagrams[0]}
                siblings={visibleDiagrams}
                onOpen={onOpenDiagram}
              />
            </section>
          ) : null}
        </div>
        {slidesBusy ? <DeckBuildCard stage={slidesStage} /> : null}
      </div>
    );
  }

  /* 3) Diagrams only (or report with schemas, no PDF) — live Mermaid + snippet */
  if (visibleDiagrams.length > 0 && onOpenDiagram) {
    return (
      <div className={shellClass}>
        <DiagramChatCard
          diagram={visibleDiagrams[0]}
          siblings={visibleDiagrams}
          onOpen={onOpenDiagram}
        />
      </div>
    );
  }

  /* 4) Slides busy — progress in chat; no «Сделать презентацию» */
  if (slidesBusy) {
    return (
      <div className={shellClass}>
        <p className="artifact-card-quiet-label">Презентация</p>
        <DeckBuildCard stage={slidesStage} />
      </div>
    );
  }

  /* 4b) Ready but files not mapped yet — open twin on click */
  if (slidesReady && onOpenPresentation) {
    return (
      <div className={shellClass}>
        <p className="artifact-card-quiet-label">{title}</p>
        <button
          type="button"
          className="artifact-card-view deck-make-primary is-ghost"
          onClick={onOpenPresentation}
        >
          Открыть презентацию
        </button>
      </div>
    );
  }

  /* Fallback compact (rare: no pdf / diagrams / deck) */
  return (
    <div
      className={`artifact-card${pulse ? " is-pulse" : ""}${updated ? " is-updated" : ""}`}
    >
      <button
        type="button"
        className="artifact-card-body"
        onClick={onView}
        aria-label={`Открыть ${title}`}
      >
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
          Открыть
        </button>
      </div>
    </div>
  );
}
