/** In-chat Julius artifact previews — large DeckFileCards; rail opens on click. */

import { DeckFileCard } from "./DeckFileCard";
import { DeckMakeSplit } from "./DeckMakeSplit";

type DiagramChip = { id: string; title: string; type?: string };

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
  onView: () => void;
  onOpenDiagram?: (id: string) => void;
  onMakePresentation?: () => void;
  onOpenPresentation?: () => void;
  onDeckStyle?: () => void;
};

function fileNameFromUrl(url: string, fallback: string): string {
  try {
    return decodeURIComponent(url.split("/").pop() || fallback);
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
      <p className="deck-build-card-hint">
        Обычно 1–2 минуты. Остаёмся в чате — карточки появятся здесь.
      </p>
    </div>
  );
}

function DiagramSketch() {
  return (
    <svg
      className="deck-file-card-diagram-sketch"
      viewBox="0 0 280 160"
      width="280"
      height="160"
      aria-hidden
    >
      <rect x="88" y="10" width="104" height="28" rx="7" className="dsk-node" />
      <path d="M140 38v14" className="dsk-edge" />
      <rect x="72" y="52" width="136" height="28" rx="7" className="dsk-node is-mid" />
      <path d="M140 80v12" className="dsk-edge" />
      <path d="M140 92l28 20H112l28-20Z" className="dsk-diamond" />
      <path d="M112 112l-36 14" className="dsk-edge" />
      <path d="M168 112l36 14" className="dsk-edge" />
      <rect x="36" y="126" width="72" height="24" rx="6" className="dsk-node is-warn" />
      <rect x="172" y="126" width="72" height="24" rx="6" className="dsk-node is-ok" />
    </svg>
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
  const hasDeckCta =
    Boolean(onMakePresentation) || (slidesReady && Boolean(onOpenPresentation));
  const reportPdfHref = pdfUrl || downloads?.pdf || null;
  const hasDeckFiles =
    slidesReady && Boolean(downloads?.pptx || downloads?.deck_pdf);
  const pptxName = downloads?.pptx
    ? fileNameFromUrl(downloads.pptx, "deck.pptx")
    : "deck.pptx";
  const deckPdfName = downloads?.deck_pdf
    ? fileNameFromUrl(downloads.deck_pdf, "deck.pdf")
    : "deck.pdf";
  const reportPdfName = reportPdfHref
    ? fileNameFromUrl(reportPdfHref, "report.pdf")
    : "report.pdf";

  const showDeckMake =
    hasDeckCta && (slidesBusy || !hasDeckFiles || Boolean(onMakePresentation));

  const shellClass = [
    "artifact-card",
    "is-julius",
    pulse ? "is-pulse" : "",
    updated ? "is-updated" : "",
    hasDeckFiles || reportPdfHref ? "has-deck" : "",
  ]
    .filter(Boolean)
    .join(" ");

  /* 1) Deck ready → large PPTX / deck PDF stack only */
  if (hasDeckFiles) {
    return (
      <div className={shellClass}>
        <div className="artifact-card-deck-stack" role="group" aria-label="Дека">
          {downloads?.pptx ? (
            <section className="artifact-card-block">
              <p className="artifact-card-quiet-label">
                Презентация
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
                onPrimary={onOpenPresentation}
                primaryLabel="Изменить"
                filmstrip={slidePngs}
                footerHint="Открыть редактор слайдов →"
              />
            </section>
          ) : null}
          {downloads?.deck_pdf ? (
            <section className="artifact-card-block">
              <p className="artifact-card-quiet-label">PDF twin</p>
              <DeckFileCard
                kind="deck_pdf"
                href={downloads.deck_pdf}
                previewUrl={hero}
                pdfUrl={downloads.deck_pdf}
                fileLabel={deckPdfName}
                onPrimary={onOpenPresentation}
                primaryLabel="Открыть"
                footerHint="Открыть PDF twin →"
              />
            </section>
          ) : null}
        </div>
        {slidesBusy ? <DeckBuildCard stage={slidesStage} /> : null}
      </div>
    );
  }

  /* 2) Report PDF → one large preview card */
  if (reportPdfHref) {
    return (
      <div className={shellClass}>
        <div
          className="artifact-card-deck-stack"
          role="group"
          aria-label="Отчёт PDF"
        >
          <section className="artifact-card-block">
            {updated || subtitle ? (
              <p className="artifact-card-quiet-label">
                {updated ? "Обновлено" : null}
                {updated && subtitle ? " · " : null}
                {subtitle || null}
              </p>
            ) : null}
            <DeckFileCard
              kind="pdf"
              href={reportPdfHref}
              docTitle={title}
              fileLabel={reportPdfName}
              onPrimary={onView}
              primaryLabel="Открыть"
            />
          </section>
        </div>
        {diagrams.length > 1 && onOpenDiagram ? (
          <div
            className="artifact-card-diagrams is-quiet"
            role="group"
            aria-label="Схемы"
          >
            {diagrams.map((d) => (
              <button
                key={d.id}
                type="button"
                className="artifact-card-diagram-chip"
                onClick={() => onOpenDiagram(d.id)}
              >
                {d.title || d.id}
              </button>
            ))}
          </div>
        ) : diagrams.length === 1 && onOpenDiagram ? (
          <button
            type="button"
            className="artifact-card-diagram-link"
            onClick={() => onOpenDiagram(diagrams[0].id)}
          >
            Схема: {diagrams[0].title || diagrams[0].id}
          </button>
        ) : null}
        {slidesBusy ? (
          <DeckBuildCard stage={slidesStage} />
        ) : showDeckMake ? (
          <div className="artifact-card-actions is-quiet-cta">
            <DeckMakeSplit
              busy={false}
              ready={slidesReady}
              quiet
              onMake={() => onMakePresentation?.()}
              onOpen={onOpenPresentation}
              onStyle={() => onDeckStyle?.()}
            />
          </div>
        ) : null}
      </div>
    );
  }

  /* 3) Diagrams only — one primary card + quiet list if many */
  if (diagrams.length > 0 && onOpenDiagram) {
    const primary = diagrams[0];
    const rest = diagrams.slice(1);
    return (
      <div className={shellClass}>
        <div
          className="artifact-card-deck-stack"
          role="group"
          aria-label="Схемы"
        >
          <section className="artifact-card-block">
            <p className="artifact-card-quiet-label">Схема</p>
            <article className="deck-file-card is-diagram">
              <header className="deck-file-card-head">
                <span className="deck-file-card-mark" aria-hidden>
                  <svg
                    className="deck-file-card-glyph"
                    width="22"
                    height="22"
                    viewBox="0 0 22 22"
                  >
                    <rect
                      x="3"
                      y="3"
                      width="7"
                      height="5"
                      rx="1.4"
                      fill="currentColor"
                      opacity="0.18"
                    />
                    <rect
                      x="12"
                      y="8"
                      width="7"
                      height="5"
                      rx="1.4"
                      fill="currentColor"
                      opacity="0.18"
                    />
                    <rect
                      x="3"
                      y="14"
                      width="7"
                      height="5"
                      rx="1.4"
                      fill="currentColor"
                      opacity="0.18"
                    />
                    <path
                      d="M6.5 8v3.5h5.5M6.5 14v-2.5"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="deck-file-card-badge">Схема</span>
                </span>
                <span className="deck-file-card-meta">
                  <span className="deck-file-card-path" title={primary.title}>
                    {primary.title || primary.id}
                  </span>
                  <span className="deck-file-card-hint">
                    {primary.type || "flowchart"}
                  </span>
                </span>
                <span className="deck-file-card-actions">
                  <button
                    type="button"
                    className="deck-file-card-action is-strong is-pill"
                    onClick={() => onOpenDiagram(primary.id)}
                  >
                    Открыть
                  </button>
                </span>
              </header>
              <button
                type="button"
                className="deck-file-card-preview is-diagram"
                onClick={() => onOpenDiagram(primary.id)}
                aria-label={`Открыть схему: ${primary.title || primary.id}`}
              >
                <span className="deck-file-card-mat">
                  <span className="deck-file-card-sheet is-diagram-sheet">
                    <span className="deck-file-card-diagram-hero">
                      <DiagramSketch />
                      <span className="deck-file-card-diagram-title">
                        {primary.title || title || "Схема"}
                      </span>
                    </span>
                  </span>
                </span>
                <span className="deck-file-card-veil" aria-hidden>
                  <span className="deck-file-card-veil-label">
                    Открыть
                    <span className="deck-file-card-veil-arrow">→</span>
                  </span>
                </span>
              </button>
              <footer className="deck-file-card-foot">
                <button
                  type="button"
                  className="deck-file-card-foot-link"
                  onClick={() => onOpenDiagram(primary.id)}
                >
                  Открыть схему в панели →
                </button>
              </footer>
            </article>
          </section>
        </div>
        {rest.length > 0 ? (
          <div
            className="artifact-card-diagrams is-quiet"
            role="group"
            aria-label="Другие схемы"
          >
            {rest.map((d) => (
              <button
                key={d.id}
                type="button"
                className="artifact-card-diagram-chip"
                onClick={() => onOpenDiagram(d.id)}
              >
                {d.title || d.id}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  /* 4) Slides busy / make CTA — never empty; progress stays in chat */
  if (slidesBusy || hasDeckCta) {
    return (
      <div className={shellClass}>
        {slidesBusy ? (
          <>
            <p className="artifact-card-quiet-label">Презентация</p>
            <DeckBuildCard stage={slidesStage} />
          </>
        ) : (
          <>
            <p className="artifact-card-quiet-label">{title}</p>
            <div className="artifact-card-actions is-quiet-cta">
              <DeckMakeSplit
                busy={false}
                ready={slidesReady}
                quiet
                onMake={() => onMakePresentation?.()}
                onOpen={onOpenPresentation}
                onStyle={() => onDeckStyle?.()}
              />
            </div>
          </>
        )}
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
