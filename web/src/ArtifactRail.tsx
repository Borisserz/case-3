/** Right-side Artifact rail: Preview · PDF · Source — resize, TOC, polish. */

import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type RefObject,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { ChartEditRequest, PaletteInfo } from "./ChartEditSheet";
import type { ImageEditRequest } from "./ImageEditModal";
import { ExportMenu } from "./ExportMenu";
import { ReportView, type ReportPreview } from "./ReportView";
import { RailToc, buildToc } from "./RailToc";
import { SourcePane } from "./SourcePane";
import {
  RAIL_WIDTH_DEFAULT,
  clampRailWidth,
  saveRailWidth,
} from "./railWidth";

const PdfFirstPage = lazy(() =>
  import("./PdfFirstPage").then((m) => ({ default: m.PdfFirstPage })),
);

export type ArtifactTab = "preview" | "pdf" | "source";

export type ActiveArtifact =
  | {
      kind: "report";
      msgId: string;
      tab: ArtifactTab;
      title?: string;
    }
  | {
      kind: "source";
      tab: "source";
      title: string;
      text: string;
      fileName?: string;
    }
  | {
      kind: "intent";
      tab: "source";
      title: string;
      text: string;
    };

type ReportBundle = {
  preview?: ReportPreview;
  downloads?: Record<string, string>;
  runId?: string;
  stats?: string;
  warnings?: string[];
};

type Props = {
  artifact: ActiveArtifact;
  report: ReportBundle | null;
  sourceText?: string | null;
  sourceTitle?: string | null;
  palettes?: PaletteInfo[];
  catalogTypes?: string[];
  defaultPalette?: string;
  editingFigureId?: string | null;
  editError?: string | null;
  editErrorFigureId?: string | null;
  downloadsPulse?: boolean;
  narrow?: boolean;
  widthPct?: number;
  onWidthChange?: (pct: number) => void;
  onTab: (tab: ArtifactTab) => void;
  onClose: () => void;
  onEditFigure?: (req: ChartEditRequest) => Promise<boolean> | boolean;
  onEditImage?: (req: ImageEditRequest) => Promise<boolean> | boolean;
  onEditCancel?: () => void;
};

export function ArtifactRail({
  artifact,
  report,
  sourceText,
  sourceTitle,
  palettes = [],
  catalogTypes = [],
  defaultPalette = "atelier",
  editingFigureId = null,
  editError = null,
  editErrorFigureId = null,
  downloadsPulse = false,
  narrow = false,
  widthPct = RAIL_WIDTH_DEFAULT,
  onWidthChange,
  onTab,
  onClose,
  onEditFigure,
  onEditImage,
  onEditCancel,
}: Props) {
  const reduceMotion = useReducedMotion();
  const tab = artifact.tab;
  const isReport = artifact.kind === "report";
  const hasPreview = Boolean(report?.preview?.blocks?.length);
  const hasPdf = Boolean(report?.downloads?.pdf);
  const hasSource = Boolean(
    (sourceText && sourceText.length > 0) ||
      artifact.kind === "source" ||
      artifact.kind === "intent",
  );

  const displaySource =
    artifact.kind === "source" || artifact.kind === "intent"
      ? artifact.text
      : sourceText || "";
  const displaySourceTitle =
    artifact.kind === "source" || artifact.kind === "intent"
      ? artifact.title
      : sourceTitle || "Source";
  const sourceFileName =
    artifact.kind === "source" ? artifact.fileName : undefined;

  const [pdfPage, setPdfPage] = useState(1);
  const [tocActive, setTocActive] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [bodyEl, setBodyEl] = useState<HTMLDivElement | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLElement>(null);
  const titleId = useId();
  const setBodyRef = useCallback((el: HTMLDivElement | null) => {
    bodyRef.current = el;
    setBodyEl(el);
  }, []);

  const toc = useMemo(
    () => buildToc(report?.preview?.blocks),
    [report?.preview?.blocks],
  );

  const visibleTabs = useMemo(() => {
    const all: { id: ArtifactTab; label: string; show: boolean }[] = [
      { id: "preview", label: "Превью", show: isReport && hasPreview },
      { id: "pdf", label: "PDF", show: isReport && hasPdf },
      { id: "source", label: "Source", show: hasSource },
    ];
    return all.filter((t) => t.show);
  }, [isReport, hasPreview, hasPdf, hasSource]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  /* Focus trap when overlay */
  useEffect(() => {
    if (!narrow || !panelRef.current) return;
    const root = panelRef.current;
    const focusables = root.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    first?.focus();
    const onTabKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || focusables.length === 0) return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };
    root.addEventListener("keydown", onTabKey);
    return () => root.removeEventListener("keydown", onTabKey);
  }, [narrow, tab]);

  const jumpToc = useCallback((id: string) => {
    setTocActive(id);
    const el = bodyRef.current?.querySelector(`#${CSS.escape(id)}`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const jumpFigureToPdf = useCallback(
    (info: { id: string; figureIndex: number; pdfPage?: number }) => {
      // Prefer TeX page hint (C10); else figureIndex heuristic
      const guess = Math.max(1, info.pdfPage ?? info.figureIndex);
      setPdfPage(guess);
      onTab("pdf");
    },
    [onTab],
  );

  const onResizePointerDown = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      if (narrow || !onWidthChange) return;
      e.preventDefault();
      const handle = e.currentTarget;
      handle.setPointerCapture(e.pointerId);
      setDragging(true);
      const split = handle.closest(".desk-split") as HTMLElement | null;
      const startX = e.clientX;
      const startPct = widthPct;
      let latest = startPct;

      const onMove = (ev: PointerEvent) => {
        if (!split) return;
        const rect = split.getBoundingClientRect();
        if (rect.width < 1) return;
        const dx = startX - ev.clientX;
        latest = clampRailWidth(startPct + (dx / rect.width) * 100);
        onWidthChange(latest);
      };
      const onUp = (ev: PointerEvent) => {
        try {
          handle.releasePointerCapture(ev.pointerId);
        } catch {
          /* already released */
        }
        setDragging(false);
        saveRailWidth(latest);
        handle.removeEventListener("pointermove", onMove);
        handle.removeEventListener("pointerup", onUp);
      };
      handle.addEventListener("pointermove", onMove);
      handle.addEventListener("pointerup", onUp);
    },
    [narrow, onWidthChange, widthPct],
  );

  const resetWidth = useCallback(() => {
    onWidthChange?.(RAIL_WIDTH_DEFAULT);
    saveRailWidth(RAIL_WIDTH_DEFAULT);
  }, [onWidthChange]);

  const panel = (
    <motion.aside
      ref={panelRef as RefObject<HTMLElement>}
      className={`artifact-rail${narrow ? " is-overlay" : ""}${dragging ? " is-dragging" : ""}`}
      role="complementary"
      aria-label="Артефакт"
      aria-labelledby={titleId}
      {...(narrow ? { "aria-modal": true as const } : {})}
      style={
        narrow
          ? undefined
          : {
              flex: `0 0 ${widthPct}%`,
              maxWidth: "min(780px, 72vw)",
              width: `${widthPct}%`,
            }
      }
      initial={
        reduceMotion ? false : { opacity: 0, x: narrow ? 36 : 20 }
      }
      animate={{ opacity: 1, x: 0 }}
      exit={
        reduceMotion ? undefined : { opacity: 0, x: narrow ? 28 : 12 }
      }
      transition={
        reduceMotion
          ? { duration: 0 }
          : { type: "spring", stiffness: 420, damping: 36, mass: 0.75 }
      }
    >
      {!narrow && (
        <div
          className="artifact-rail-resize"
          role="separator"
          aria-orientation="vertical"
          aria-valuenow={widthPct}
          aria-valuemin={34}
          aria-valuemax={70}
          aria-label="Ширина панели. Двойной клик — сброс"
          onPointerDown={onResizePointerDown}
          onDoubleClick={resetWidth}
        >
          <span className="artifact-rail-resize-grip" aria-hidden>
            <i />
            <i />
            <i />
          </span>
        </div>
      )}

      <div className="artifact-rail-inner">
        {isReport ? (
          <p className="rail-print-hint">
            PDF — истина печати · превью ≈ блоки TeX
          </p>
        ) : null}
        <header className="artifact-rail-head">
          <span id={titleId} className="sr-only">
            {artifact.kind === "report"
              ? artifact.title || "Отчёт"
              : displaySourceTitle}
          </span>
          <nav
            className="artifact-rail-tabs"
            aria-label="Вкладки артефакта"
            onKeyDown={(e) => {
              const ids = visibleTabs.map((t) => t.id);
              const i = ids.indexOf(tab);
              if (i < 0) return;
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                e.preventDefault();
                const next =
                  e.key === "ArrowRight"
                    ? ids[(i + 1) % ids.length]
                    : ids[(i - 1 + ids.length) % ids.length];
                onTab(next);
              }
            }}
          >
            {visibleTabs.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`artifact-rail-tab${tab === t.id ? " is-active" : ""}`}
                aria-selected={tab === t.id}
                onClick={() => onTab(t.id)}
              >
                {tab === t.id && !reduceMotion && (
                  <motion.span
                    className="artifact-rail-tab-ink"
                    layoutId="rail-tab-ink"
                    transition={{
                      type: "spring",
                      stiffness: 480,
                      damping: 38,
                    }}
                  />
                )}
                <span className="artifact-rail-tab-label">{t.label}</span>
              </button>
            ))}
          </nav>
          <div className="artifact-rail-actions">
            {isReport && (
              <ExportMenu
                downloads={report?.downloads}
                label="Export"
                pulse={downloadsPulse}
              />
            )}
            <button
              type="button"
              className="artifact-rail-close"
              aria-label="Закрыть панель"
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </header>

        <div className="artifact-rail-body" ref={setBodyRef}>
          {tab === "preview" && toc.length >= 2 ? (
            <RailToc
              items={toc}
              activeId={tocActive}
              onJump={jumpToc}
              onActiveChange={setTocActive}
              root={bodyEl}
            />
          ) : null}

          <AnimatePresence mode="wait">
            <motion.div
              key={`${artifact.kind}-${tab}`}
              className="artifact-rail-pane"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              {tab === "preview" && report?.preview ? (
                <ReportView
                  preview={report.preview}
                  downloads={report.downloads}
                  runId={report.runId}
                  stats={report.stats}
                  warnings={report.warnings}
                  palettes={palettes}
                  catalogTypes={catalogTypes}
                  defaultPalette={defaultPalette}
                  editingFigureId={editingFigureId}
                  editError={editError}
                  editErrorFigureId={editErrorFigureId}
                  downloadsPulse={downloadsPulse}
                  showPdf={false}
                  showDownloads={false}
                  onJumpToPdf={hasPdf ? jumpFigureToPdf : undefined}
                  onOpenPdf={hasPdf ? () => onTab("pdf") : undefined}
                  onEditFigure={onEditFigure}
                  onEditImage={onEditImage}
                  onEditCancel={onEditCancel}
                />
              ) : null}

              {tab === "pdf" && report?.downloads?.pdf ? (
                <Suspense
                  fallback={
                    <div className="pdf-skeleton pdf-skeleton-solo" aria-busy>
                      <div className="pdf-skeleton-shine" />
                      <p className="artifact-rail-loading">Загружаю PDF…</p>
                    </div>
                  }
                >
                  <PdfFirstPage
                    key={report.downloads.pdf}
                    url={report.downloads.pdf}
                    page={pdfPage}
                    onPageChange={(p) => setPdfPage(p)}
                  />
                </Suspense>
              ) : null}

              {tab === "source" ? (
                <SourcePane
                  title={displaySourceTitle}
                  text={displaySource || "Нет текста источника."}
                  fileName={sourceFileName}
                />
              ) : null}

              {tab === "preview" && !hasPreview ? (
                <p className="artifact-rail-loading muted">
                  Превью пустое — откройте вкладку PDF.
                </p>
              ) : null}
              {tab === "pdf" && !hasPdf ? (
                <p className="artifact-rail-loading muted">PDF ещё нет.</p>
              ) : null}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </motion.aside>
  );

  if (narrow) {
    return (
      <motion.div
        className="artifact-rail-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        initial={reduceMotion ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={reduceMotion ? undefined : { opacity: 0 }}
        onClick={onClose}
      >
        <div
          className="artifact-rail-overlay-slot"
          onClick={(e) => e.stopPropagation()}
        >
          {panel}
        </div>
      </motion.div>
    );
  }

  return panel;
}
