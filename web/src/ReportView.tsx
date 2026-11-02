/** Liber Print Desk — in-chat report: title, prose, tables, figure PNGs + chart edit. */

import {
  Suspense,
  useCallback,
  useEffect,
  useId,
  useState,
} from "react";
import { createPortal } from "react-dom";
import {
  type ChartEditDraft,
  type ChartEditRequest,
  type PaletteInfo,
} from "./ChartEditSheet";
import {
  type ImageEditRequest,
} from "./ImageEditModal";
import {
  type TableEditDraft,
  type TableEditRequest,
} from "./TableEditSheet";
import { type ParagraphEditRequest } from "./ParagraphEditSheet";
import type { HeadingEditRequest } from "./HeadingEditTypes";
import type { ListEditRequest } from "./ListEditTypes";
import {
  blockEditVisible,
  collapseSetForEditMode,
  reportEditModeHint,
  reportEditToggleVisible,
} from "./domain/reportEditMode";
import {
  loadCollapsedIds,
  saveCollapsedIds,
} from "./reportSections";
import { ReportBody } from "./ReportBody";
export { ReportPending } from "./ReportPending";

import { PdfFirstPage } from "./lazyPdfFirstPage";

import type { ReportPreview } from "./domain/reportPreview";
export type { PreviewBlock, ReportPreview } from "./domain/reportPreview";

type Downloads = Record<string, string>;

type Props = {
  preview: ReportPreview;
  downloads?: Downloads;
  runId?: string;
  warnings?: string[];
  palettes?: PaletteInfo[];
  catalogTypes?: string[];
  defaultPalette?: string;
  editingFigureId?: string | null;
  /** Durable error for the open sheet (not only while busy). */
  editError?: string | null;
  editErrorFigureId?: string | null;
  /** Pulse download links after a successful chart edit. */
  downloadsPulse?: boolean;
  /** Embed PDF slider (false when PDF lives in Artifact rail). */
  showPdf?: boolean;
  /** Footer download links (false when Export lives in rail header). */
  showDownloads?: boolean;
  /** Jump figure → PDF tab (rail). figureIndex is 1-based; pdfPage from TeX when known. */
  onJumpToPdf?: (info: {
    id: string;
    figureIndex: number;
    pdfPage?: number;
    caption?: string;
  }) => void;
  /** C3: open PDF tab when preview body is empty. */
  onOpenPdf?: () => void;
  /** Resolve true on success so the sheet can close. */
  onEditFigure?: (req: ChartEditRequest) => Promise<boolean> | boolean;
  onEditImage?: (req: ImageEditRequest) => Promise<boolean> | boolean;
  onEditTable?: (req: TableEditRequest) => Promise<boolean> | boolean;
  onEditParagraph?: (req: ParagraphEditRequest) => Promise<boolean> | boolean;
  onEditHeading?: (req: HeadingEditRequest) => Promise<boolean> | boolean;
  onEditList?: (req: ListEditRequest) => Promise<boolean> | boolean;
  onEditCancel?: () => void;
};

export function ReportView({
  preview,
  downloads,
  runId,
  warnings,
  palettes = [],
  catalogTypes = [],
  defaultPalette = "atelier",
  editingFigureId = null,
  editError = null,
  editErrorFigureId = null,
  downloadsPulse = false,
  showPdf = true,
  showDownloads = true,
  onJumpToPdf,
  onOpenPdf,
  onEditFigure,
  onEditImage,
  onEditTable,
  onEditParagraph,
  onEditHeading,
  onEditList,
  onEditCancel,
}: Props) {
  const blocks = preview.blocks || [];
  const [lightbox, setLightbox] = useState<{
    url: string;
    caption: string;
  } | null>(null);
  const [tableDraftByN, setTableDraftByN] = useState<
    Record<number, TableEditDraft>
  >({});
  const [draftById, setDraftById] = useState<Record<string, ChartEditDraft>>({});
  const [sheetPreviewHtmlById, setSheetPreviewHtmlById] = useState<
    Record<string, string | null>
  >({});
  const [editMode, setEditMode] = useState(false);
  const [collapsed, setCollapsed] = useState<Set<string>>(
    () => loadCollapsedIds(runId || ""),
  );
  const lbTitle = useId();
  const showEditToggle = reportEditToggleVisible({
    onEditFigure,
    onEditImage,
    onEditTable,
    onEditParagraph,
    onEditHeading,
    onEditList,
  });
  const canEditPara = blockEditVisible(editMode, Boolean(onEditParagraph));
  const canEditHeading = blockEditVisible(editMode, Boolean(onEditHeading));
  const canEditList = blockEditVisible(editMode, Boolean(onEditList));
  const canEditTable = blockEditVisible(editMode, Boolean(onEditTable));
  const canEditFigure = blockEditVisible(editMode, Boolean(onEditFigure));
  const canEditImage = blockEditVisible(editMode, Boolean(onEditImage));

  useEffect(() => {
    setCollapsed(loadCollapsedIds(runId || ""));
    setEditMode(false);
  }, [runId]);

  const leaveEditMode = useCallback(() => {
    setEditMode(false);
    setDraftById({});
    setSheetPreviewHtmlById({});
    setTableDraftByN({});
    onEditCancel?.();
  }, [onEditCancel]);

  const enterEditMode = useCallback(() => {
    const cleared = collapseSetForEditMode(true);
    if (cleared) {
      setCollapsed(cleared);
      saveCollapsedIds(runId || "", cleared);
    }
    setEditMode(true);
  }, [runId]);

  const toggleSection = useCallback(
    (headingId: string) => {
      setCollapsed((prev) => {
        const next = new Set(prev);
        if (next.has(headingId)) next.delete(headingId);
        else next.add(headingId);
        saveCollapsedIds(runId || "", next);
        return next;
      });
    },
    [runId],
  );

  const closeLb = useCallback(() => setLightbox(null), []);

  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeLb();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [lightbox, closeLb]);

  return (
    <article className={`report${editMode ? " is-editing-mode" : ""}`}>
      <div className="report-rail" aria-hidden />

      {showEditToggle ? (
        <div className="report-edit-bar">
          <p className="report-edit-bar-hint">
            {reportEditModeHint(editMode)}
          </p>
          <button
            type="button"
            className={`report-edit-toggle${editMode ? " is-on" : ""}`}
            aria-pressed={editMode}
            onClick={() => {
              if (editMode) leaveEditMode();
              else enterEditMode();
            }}
          >
            {editMode ? "Готово" : "Редактировать"}
          </button>
        </div>
      ) : null}

      {warnings && warnings.length > 0 ? (
        <header className="report-meta">
          <span className="report-warns">{warnings.join(" · ")}</span>
        </header>
      ) : null}

      {preview.title ? (
        <h1 className="report-title">{preview.title}</h1>
      ) : (
        <h1 className="report-title muted">Отчёт</h1>
      )}

      <ReportBody
        blocks={blocks}
        downloads={downloads}
        runId={runId}
        palettes={palettes}
        catalogTypes={catalogTypes}
        defaultPalette={defaultPalette}
        editingFigureId={editingFigureId}
        editError={editError}
        editErrorFigureId={editErrorFigureId}
        collapsed={collapsed}
        editMode={editMode}
        canEditPara={canEditPara}
        canEditHeading={canEditHeading}
        canEditList={canEditList}
        canEditTable={canEditTable}
        canEditFigure={canEditFigure}
        canEditImage={canEditImage}
        tableDraftByN={tableDraftByN}
        draftById={draftById}
        sheetPreviewHtmlById={sheetPreviewHtmlById}
        setTableDraftByN={setTableDraftByN}
        setDraftById={setDraftById}
        setSheetPreviewHtmlById={setSheetPreviewHtmlById}
        setLightbox={setLightbox}
        toggleSection={toggleSection}
        onJumpToPdf={onJumpToPdf}
        onOpenPdf={onOpenPdf}
        onEditFigure={onEditFigure}
        onEditImage={onEditImage}
        onEditTable={onEditTable}
        onEditParagraph={onEditParagraph}
        onEditHeading={onEditHeading}
        onEditList={onEditList}
      />

      {showPdf && downloads?.pdf ? (
        <Suspense fallback={<p className="report-pdf-cap">Загружаю стр. 1 PDF…</p>}>
          <PdfFirstPage key={downloads.pdf} url={downloads.pdf} />
        </Suspense>
      ) : null}

      {showDownloads &&
        downloads &&
        (downloads.pdf || downloads.docx) && (
        <footer
          className={`report-actions downloads${downloadsPulse ? " is-pulse" : ""}`}
        >
          {downloads.pdf && (
            <a href={downloads.pdf} download>
              Скачать PDF
            </a>
          )}
          {downloads.docx && (
            <a className="secondary" href={downloads.docx} download>
              Скачать DOCX
            </a>
          )}
        </footer>
      )}

      {lightbox &&
        createPortal(
          <div
            className="report-lightbox"
            role="dialog"
            aria-modal="true"
            aria-labelledby={lbTitle}
            onClick={closeLb}
          >
            <div
              className="report-lightbox-sheet"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                className="report-lightbox-close"
                onClick={closeLb}
                aria-label="Закрыть"
              >
                ×
              </button>
              <img src={lightbox.url} alt={lightbox.caption} />
              <p id={lbTitle} className="report-lightbox-cap">
                {lightbox.caption}
              </p>
            </div>
          </div>,
          document.body,
        )}
    </article>
  );
}
