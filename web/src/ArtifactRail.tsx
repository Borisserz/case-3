/** Right-side Artifact rail: Preview · PDF · Source — resize, TOC, polish. */

import {
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
import type { TableEditRequest } from "./TableEditSheet";
import type { ParagraphEditRequest } from "./ParagraphEditSheet";
import type { HeadingEditRequest } from "./HeadingEditTypes";
import type { ListEditRequest } from "./ListEditTypes";
import { DiagramPane } from "./DiagramPane";
import type { DiagramInfo } from "./DiagramFullscreen";
import { DeckSlidesFilm } from "./DeckSlidesFilm";
import { PresentationPane } from "./PresentationPane";
import type { ReportPreview } from "./domain/reportPreview";
import { ReportView } from "./ReportView";
import { IconPanelRight } from "./icons";
import { reportDownloadLinks } from "./domain/reportDownloads";
import { modeSurfaces } from "./domain/liberModes";
import { SourcePane } from "./SourcePane";
import {
  RAIL_WIDTH_DEFAULT,
  clampRailWidth,
  saveRailWidth,
} from "./domain/railWidth";
import { pdfSearchNeedles } from "./pdfFindPage";
import { PdfFirstPage } from "./lazyPdfFirstPage";

export type ArtifactTab =
  | "preview"
  | "pdf"
  | "source"
  | "diagram"
  | "presentation"
  | "slides";

export type ActiveArtifact =
  | {
      kind: "report";
      msgId: string;
      tab: ArtifactTab;
      title?: string;
      /** Which Mermaid diagram is focused when tab === "diagram". */
      activeDiagramId?: string | null;
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
    }
  | {
      /** SSE 2B film click — PNG in rail */
      kind: "media";
      msgId: string;
      tab: "preview";
      runId: string;
      mediaId: string;
      url: string;
      title: string;
    };

type ReportBundle = {
  preview?: ReportPreview;
  downloads?: Record<string, string>;
  runId?: string;
  warnings?: string[];
  diagrams?: DiagramInfo[];
  slidesStatus?: string | null;
  slidesStage?: string | null;
  slidesError?: string | null;
  slidePngs?: string[];
  deck?: import("./deckTypes").DeckIR | null;
  deckPdfMode?: string | null;
  /** Liber composer mode for this run — gates rail tabs. */
  outputMode?: string | null;
  onDeckUpdated?: (
    deck: import("./deckTypes").DeckIR,
    slidePngs: string[],
  ) => void;
};

type Props = {
  artifact: ActiveArtifact;
  report: ReportBundle | null;
  sourceText?: string | null;
  sourceTitle?: string | null;
  /** Pre-run sourceDraft — Source tab click-to-edit. */
  sourceEditable?: boolean;
  onSourceTextChange?: (text: string) => void;
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
  onSelectDiagram?: (id: string) => void;
  onClose: () => void;
  /** Controlled close: keep mounted, animate width → 0, then onClosed. */
  closing?: boolean;
  onClosed?: () => void;
  onEditFigure?: (req: ChartEditRequest) => Promise<boolean> | boolean;
  onEditImage?: (req: ImageEditRequest) => Promise<boolean> | boolean;
  onEditTable?: (req: TableEditRequest) => Promise<boolean> | boolean;
  onEditParagraph?: (req: ParagraphEditRequest) => Promise<boolean> | boolean;
  onEditHeading?: (req: HeadingEditRequest) => Promise<boolean> | boolean;
  onEditList?: (req: ListEditRequest) => Promise<boolean> | boolean;
  onEditCancel?: () => void;
  editHistory?: import("./domain/reportEditMode").EditHistoryDesc | null;
  onHistoryUndo?: () => void | Promise<void>;
  onHistoryRedo?: () => void | Promise<void>;
  onClearEditHistory?: () => void | Promise<void>;
  onReportEditModeChange?: (on: boolean) => void;
  makingPresentation?: boolean;
  onDiagramsUpdated?: (
    diagrams: DiagramInfo[],
    meta?: import("./DiagramPane").DiagramUpdateMeta,
  ) => void;
};

export function ArtifactRail({
  artifact,
  report,
  sourceText,
  sourceTitle,
  sourceEditable = false,
  onSourceTextChange,
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
  onSelectDiagram,
  onClose,
  closing = false,
  onClosed,
  onEditFigure,
  onEditImage,
  onEditTable,
  onEditParagraph,
  onEditHeading,
  onEditList,
  onEditCancel,
  editHistory = null,
  onHistoryUndo,
  onHistoryRedo,
  onClearEditHistory,
  onReportEditModeChange,
  makingPresentation = false,
  onDiagramsUpdated,
}: Props) {
  const reduceMotion = useReducedMotion();
  const tab = artifact.tab;
  const openWidthRef = useRef<number | null>(null);
  const isMedia = artifact.kind === "media";
  const isReport = artifact.kind === "report";
  const diagrams = isReport ? report?.diagrams || [] : [];
  const activeDiagramId =
    isReport && artifact.kind === "report"
      ? artifact.activeDiagramId || diagrams[0]?.id || null
      : null;
  const activeDiagram =
    diagrams.find((d) => d.id === activeDiagramId) || diagrams[0] || null;
  const surfaces = modeSurfaces(report?.outputMode);
  const showDiagramEmpty =
    tab === "diagram" &&
    !activeDiagram &&
    surfaces.showDiagram &&
    Boolean(report?.runId);
  const showDiagramSurface =
    (tab === "diagram" && Boolean(activeDiagram)) || showDiagramEmpty;
  const hasPreview =
    surfaces.showReportPreview && Boolean(report?.preview?.blocks?.length);
  const hasPdf =
    surfaces.showReportPdf && Boolean(report?.downloads?.pdf);
  /** Diagram mode always keeps the tab — even when generation returned 0. */
  const hasDiagrams =
    surfaces.showDiagram &&
    (diagrams.length > 0 || report?.outputMode === "diagram");
  const slidesStatus = isReport ? report?.slidesStatus || null : null;
  /* Show tab only when deck exists or failed — never open rail mid-build. */
  const hasPresentationTab =
    surfaces.showPresentation &&
    isReport &&
    Boolean(
      slidesStatus === "ok" ||
        slidesStatus === "error" ||
        (report?.slidePngs && report.slidePngs.length > 0),
    );
  const hasSlidesFilmTab =
    surfaces.showPresentation &&
    isReport &&
    Boolean(
      (report?.slidePngs && report.slidePngs.length > 0) ||
        report?.downloads?.deck_pdf,
    );
  const hasSource =
    surfaces.showSource &&
    Boolean(
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
  /** Caption/id search after figure→PDF click (TeX page hints miss natural breaks). */
  const [pdfFind, setPdfFind] = useState<{
    needles: string[];
    token: number;
  } | null>(null);
  const [dragging, setDragging] = useState(false);
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLElement>(null);
  const titleId = useId();
  const setBodyRef = useCallback((el: HTMLDivElement | null) => {
    bodyRef.current = el;
  }, []);

  const visibleTabs = useMemo(() => {
    if (isMedia) {
      return [{ id: "preview" as ArtifactTab, label: "Кадр", show: true }];
    }
    // Peer order for documents: Превью · Схема · PDF (schema sits next to preview).
    const diagramLabel =
      diagrams.length > 1 ? `Схема · ${diagrams.length}` : "Схема";
    const all: { id: ArtifactTab; label: string; show: boolean }[] = [
      { id: "preview", label: "Превью", show: isReport && hasPreview },
      { id: "diagram", label: diagramLabel, show: isReport && hasDiagrams },
      { id: "pdf", label: "PDF", show: isReport && hasPdf },
      {
        id: "presentation",
        label: "PPTX",
        show: Boolean(hasPresentationTab),
      },
      {
        id: "slides",
        label: "PDF",
        show: Boolean(hasSlidesFilmTab),
      },
      { id: "source", label: "Source", show: hasSource },
    ];
    return all.filter((t) => t.show);
  }, [
    isMedia,
    isReport,
    hasPreview,
    hasPdf,
    hasDiagrams,
    hasPresentationTab,
    hasSlidesFilmTab,
    hasSource,
    diagrams.length,
  ]);

  /* If mode hid the active tab (e.g. presentation run opened on preview), snap. */
  useEffect(() => {
    if (!isReport || visibleTabs.length === 0) return;
    if (visibleTabs.some((t) => t.id === tab)) return;
    onTab(visibleTabs[0].id);
  }, [isReport, tab, visibleTabs, onTab]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Diagram fullscreen owns Esc while open.
      if (document.querySelector(".diagram-fullscreen")) return;
      if (document.querySelector(".presentation-fullscreen")) return;
      // Source draft click-to-edit: Esc exits editor first (not rail).
      if (document.querySelector(".artifact-source.is-editing")) return;
      onClose();
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

  const jumpFigureToPdf = useCallback(
    (info: {
      id: string;
      figureIndex: number;
      pdfPage?: number;
      caption?: string;
    }) => {
      // Don't seed pdfPage from TeX hints — without \\newpage they are almost
      // always «1» and fight pdf.js caption search (figure may be on p.2+).
      setPdfFind({
        needles: pdfSearchNeedles(info.caption, info.id),
        token: Date.now(),
      });
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

  const deskOpen = !narrow && !closing;
  /** Width-driven collapse — flexBasis % fought CSS `flex` shorthand and stalled. */
  const deskClosed = {
    width: 0,
    minWidth: 0,
    marginLeft: 0,
    opacity: 1,
  };
  const deskOpened = {
    opacity: 1,
    width: `${widthPct}%`,
    minWidth: 280,
    marginLeft: 6,
  };
  const onClosedRef = useRef(onClosed);
  onClosedRef.current = onClosed;
  const closedOnceRef = useRef(false);
  const closingRef = useRef(closing);
  closingRef.current = closing;

  const finishClose = useCallback(() => {
    if (closedOnceRef.current) return;
    closedOnceRef.current = true;
    onClosedRef.current?.();
  }, []);

  useEffect(() => {
    if (!closing) {
      closedOnceRef.current = false;
      return;
    }
    if (reduceMotion) {
      finishClose();
      return;
    }
    /* Fallback if onAnimationComplete misses (e.g. interrupted). */
    const t = window.setTimeout(finishClose, 520);
    return () => window.clearTimeout(t);
  }, [closing, reduceMotion, finishClose]);

  const panel = (
    <motion.aside
      ref={panelRef as RefObject<HTMLElement>}
      className={`artifact-rail${narrow ? " is-overlay" : ""}${dragging ? " is-dragging" : ""}${closing ? " is-closing" : ""}`}
      role="complementary"
      aria-label="Артефакт"
      aria-labelledby={titleId}
      {...(narrow ? { "aria-modal": true as const } : {})}
      style={
        narrow
          ? undefined
          : {
              flex: "0 0 auto",
              maxWidth: closing ? undefined : "min(780px, 72vw)",
              overflow: "hidden",
            }
      }
      initial={
        reduceMotion
          ? false
          : narrow
            ? { opacity: 0, x: 36 }
            : { ...deskClosed, opacity: 0 }
      }
      animate={
        narrow
          ? closing
            ? { opacity: 0, x: 28 }
            : { opacity: 1, x: 0 }
          : closing
            ? deskClosed
            : deskOpened
      }
      exit={
        reduceMotion
          ? undefined
          : narrow
            ? { opacity: 0, x: 28 }
            : deskClosed
      }
      transition={
        reduceMotion
          ? { duration: 0 }
          : narrow
            ? { type: "spring", stiffness: 420, damping: 36, mass: 0.75 }
            : {
                width: { duration: 0.42, ease: [0.22, 1, 0.36, 1] },
                minWidth: { duration: 0.42, ease: [0.22, 1, 0.36, 1] },
                marginLeft: { duration: 0.42, ease: [0.22, 1, 0.36, 1] },
                opacity: { duration: 0.28, ease: [0.22, 1, 0.36, 1] },
              }
      }
      onUpdate={() => {
        if (!narrow && panelRef.current && deskOpen) {
          openWidthRef.current = panelRef.current.getBoundingClientRect().width;
        }
      }}
      onAnimationComplete={() => {
        // Ignore completion of the *previous* open tween when `animate` flips
        // to closed — that used to call finishClose while width was still full,
        // unmounting the rail and snapping the chat bubble.
        if (!closingRef.current) return;
        const w = panelRef.current?.getBoundingClientRect().width ?? 0;
        if (w > 32) return;
        finishClose();
      }}
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
        <header className="artifact-rail-head">
          <span id={titleId} className="sr-only">
            {artifact.kind === "media"
              ? artifact.title
              : artifact.kind === "report"
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
            {isReport
              ? reportDownloadLinks(report?.downloads, {
                  enabled: surfaces.showReportPdf,
                }).map((link) => (
                  <a
                    key={link.kind}
                    href={link.href}
                    download
                    className={`artifact-rail-dl${downloadsPulse ? " is-pulse" : ""}`}
                  >
                    {link.label}
                  </a>
                ))
              : null}
            <button
              type="button"
              className="artifact-rail-close"
              aria-label="Свернуть панель"
              title="Свернуть"
              onClick={onClose}
            >
              <IconPanelRight size={16} />
            </button>
          </div>
        </header>

        <div className="artifact-rail-body" ref={setBodyRef}>
          <AnimatePresence mode="wait">
            <motion.div
              key={
                showDiagramSurface
                  ? `diagram-${activeDiagramId}`
                  : `${artifact.kind}-${tab}`
              }
              className="artifact-rail-pane"
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            >
              {isMedia && artifact.kind === "media" ? (
                <div className="artifact-rail-media">
                  <p className="artifact-rail-media-caption">{artifact.title}</p>
                  <img
                    className="artifact-rail-media-img"
                    src={artifact.url}
                    alt={artifact.title}
                  />
                </div>
              ) : null}

              {showDiagramSurface ? (
                <DiagramPane
                  diagram={activeDiagram}
                  emptyMode={showDiagramEmpty}
                  siblings={diagrams.length > 1 ? diagrams : undefined}
                  onSelectSibling={onSelectDiagram}
                  runId={report?.runId}
                  onDiagramsUpdated={onDiagramsUpdated}
                />
              ) : null}

              {!isMedia &&
              !showDiagramSurface &&
              tab === "preview" &&
              report?.preview ? (
                <ReportView
                  preview={report.preview}
                  downloads={report.downloads}
                  runId={report.runId}
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
                  onEditTable={onEditTable}
                  onEditParagraph={onEditParagraph}
                  onEditHeading={onEditHeading}
                  onEditList={onEditList}
                  onEditCancel={onEditCancel}
                  editHistory={editHistory}
                  onHistoryUndo={onHistoryUndo}
                  onHistoryRedo={onHistoryRedo}
                  onClearEditHistory={onClearEditHistory}
                  onEditModeChange={onReportEditModeChange}
                />
              ) : null}

              {!showDiagramSurface && tab === "pdf" && report?.downloads?.pdf ? (
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
                    findNeedles={pdfFind?.needles}
                    findToken={pdfFind?.token}
                    onPageChange={(p) => setPdfPage(p)}
                  />
                </Suspense>
              ) : null}

              {!showDiagramSurface && tab === "presentation" && report?.runId ? (
                <PresentationPane
                  runId={report.runId}
                  slidePngs={report.slidePngs || []}
                  deck={report.deck}
                  status={report.slidesStatus}
                  stage={report.slidesStage}
                  error={report.slidesError}
                  downloads={report.downloads}
                  deckPdfMode={report.deckPdfMode}
                  making={makingPresentation}
                  onDeckUpdated={report.onDeckUpdated}
                />
              ) : null}

              {!showDiagramSurface && tab === "slides" ? (
                <DeckSlidesFilm
                  slides={report?.slidePngs || []}
                  downloadHref={report?.downloads?.deck_pdf || null}
                />
              ) : null}

              {!showDiagramSurface && tab === "source" ? (
                <SourcePane
                  title={displaySourceTitle}
                  text={displaySource}
                  fileName={sourceFileName}
                  editable={sourceEditable}
                  onTextChange={onSourceTextChange}
                />
              ) : null}

              {!isMedia &&
              !showDiagramSurface &&
              tab === "preview" &&
              !hasPreview ? (
                <p className="artifact-rail-loading muted">
                  Превью пустое — откройте вкладку PDF.
                </p>
              ) : null}
              {!isMedia && !showDiagramSurface && tab === "pdf" && !hasPdf ? (
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
