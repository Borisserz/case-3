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
  ChartEditSheet,
  type ChartEditDraft,
  type ChartEditRequest,
  type PaletteInfo,
} from "./ChartEditSheet";
import { ChartCard } from "./ChartCard";
import { ChartLivePane } from "./ChartLivePane";
import { chartTypeChipLabel } from "./ChartTypePreview";
import {
  ImageEditModal,
  type ImageEditRequest,
} from "./ImageEditModal";
import {
  TableEditSheet,
  type TableEditDraft,
  type TableEditRequest,
} from "./TableEditSheet";
import { type ParagraphEditRequest } from "./ParagraphEditSheet";
import { InlineBlockEditor } from "./InlineBlockEditor";
import type { HeadingEditRequest } from "./HeadingEditTypes";
import type { ListEditRequest } from "./ListEditTypes";
import { PipelineFlow } from "./PipelineFlow";
import {
  blockEditVisible,
  collapseSetForEditMode,
  reportEditModeHint,
  reportEditToggleVisible,
} from "./domain/reportEditMode";
import {
  isBlockHiddenByCollapse,
  loadCollapsedIds,
  saveCollapsedIds,
} from "./reportSections";

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

function bustFromUrl(url?: string): string {
  if (!url) return "";
  const m = /[?&]v=([^&]+)/.exec(url);
  return m?.[1] || "";
}

function looksNumeric(s: string): boolean {
  const t = (s || "").trim().replace(/\s/g, "").replace(",", ".");
  if (!t) return false;
  return /^-?\d+(\.\d+)?%?$/.test(t) || /^-?\d{1,3}([. ]\d{3})+(,\d+)?%?$/.test(t);
}

function colIsNumeric(headers: string[], rows: string[][], ci: number): boolean {
  let n = 0;
  let total = 0;
  for (const row of rows) {
    const cell = row[ci];
    if (cell == null || !String(cell).trim()) continue;
    total += 1;
    if (looksNumeric(String(cell))) n += 1;
  }
  if (total === 0) return false;
  if (n / total >= 0.6) return true;
  const h = (headers[ci] || "").toLowerCase();
  return /\d|%|год|года|шт|руб|млн|тыс|доля|рост/.test(h) && n / total >= 0.35;
}

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
  let figN = 0;
  let tabN = 0;
  let headN = 0;
  let paraN = 0;
  let listN = 0;
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

      <div className="report-body">
        {blocks.length === 0 && (
          <div
            className={`report-empty-warn${downloads?.pdf ? " has-pdf" : ""}`}
            role="status"
          >
            <p className="report-p muted" style={{ margin: 0 }}>
              Превью пустое
              {downloads?.pdf
                ? " — PDF есть. Откройте вкладку PDF (истина печати)."
                : " — тело отчёта не разобралось."}
            </p>
            {downloads?.pdf && onOpenPdf ? (
              <button
                type="button"
                className="report-empty-warn-btn"
                onClick={onOpenPdf}
              >
                Открыть PDF
              </button>
            ) : null}
          </div>
        )}
        {blocks.map((b, i) => {
          const delayStyle = {
            animationDelay: `${Math.min(i * 0.045, 0.55)}s`,
          } as const;
          const hiddenByCollapse = isBlockHiddenByCollapse(
            blocks,
            i,
            collapsed,
          );

          if (b.type === "heading") {
            headN += 1;
            const headingIndex = headN;
            const headingId = `rail-h-${headingIndex}`;
            const headEditId = `heading:${headingIndex}`;
            // Nested under a collapsed ancestor — hide (parent heading stays).
            if (hiddenByCollapse) return null;
            const Tag = b.level >= 2 ? "h3" : "h2";
            const expanded = !collapsed.has(headingId);
            const isEditingHead = editingFigureId === headEditId;
            const headError =
              isEditingHead || editErrorFigureId === headEditId
                ? editError
                : null;
            return (
              <div
                key={i}
                className={`report-h-row report-block report-h${b.level}${canEditHeading ? " is-editing-open" : ""}${isEditingHead ? " is-editing" : ""}`}
                style={delayStyle}
              >
                <button
                  type="button"
                  className="report-h-toggle"
                  aria-expanded={expanded}
                  aria-label={
                    expanded ? `Свернуть «${b.text}»` : `Развернуть «${b.text}»`
                  }
                  onClick={() => toggleSection(headingId)}
                  disabled={editMode}
                >
                  <span className="report-h-toggle-chevron" aria-hidden>
                    ▸
                  </span>
                </button>
                {canEditHeading ? (
                  <div className="report-h-edit" id={headingId}>
                    <InlineBlockEditor
                      kind="heading"
                      initialText={b.text}
                      busy={isEditingHead}
                      error={headError}
                      onSave={(text) => {
                        void onEditHeading?.({ headingIndex, text });
                      }}
                    />
                  </div>
                ) : (
                  <Tag
                    id={headingId}
                    className={`report-h report-h${b.level}`}
                  >
                    {b.text}
                  </Tag>
                )}
              </div>
            );
          }

          if (hiddenByCollapse) {
            // Keep fig/tab/para counters stable when section is collapsed.
            if (b.type === "figure") figN += 1;
            if (b.type === "table") tabN += 1;
            if (b.type === "paragraph") paraN += 1;
            if (b.type === "list") {
              const idMatch = b.id ? /^list-(\d+)$/.exec(b.id) : null;
              if (idMatch) listN = Math.max(listN, Number(idMatch[1]));
              else listN += 1;
            }
            return null;
          }

          if (b.type === "paragraph") {
            paraN += 1;
            const idMatch = b.id ? /^para-(\d+)$/.exec(b.id) : null;
            const n = idMatch ? Number(idMatch[1]) : paraN;
            if (idMatch) paraN = Math.max(paraN, n);
            const paraId = `para:${n}`;
            const isEditingPara = editingFigureId === paraId;
            const sheetError =
              editErrorFigureId === paraId ? editError : null;
            return (
              <div
                key={i}
                className={`report-para-wrap report-block${canEditPara ? " is-tuning" : ""}${isEditingPara ? " is-editing" : ""}`}
                style={delayStyle}
              >
                <div className="report-para-frame">
                  {canEditPara ? (
                    <InlineBlockEditor
                      kind="paragraph"
                      initialText={b.text}
                      busy={isEditingPara}
                      error={sheetError}
                      onSave={(text) => {
                        void onEditParagraph?.({ paragraphIndex: n, text });
                      }}
                    />
                  ) : b.html ? (
                    <p
                      className="report-p"
                      dangerouslySetInnerHTML={{ __html: b.html }}
                    />
                  ) : (
                    <p className="report-p">{b.text}</p>
                  )}
                  {isEditingPara && (
                    <div className="report-fig-busy" aria-live="polite">
                      <p className="fig-press-label">Пересобираю абзац…</p>
                    </div>
                  )}
                </div>
              </div>
            );
          }
          if (b.type === "list") {
            listN += 1;
            const idMatch = b.id ? /^list-(\d+)$/.exec(b.id) : null;
            const n = idMatch ? Number(idMatch[1]) : listN;
            if (idMatch) listN = Math.max(listN, n);
            const listId = `list:${n}`;
            const isEditingList = editingFigureId === listId;
            const listError =
              editErrorFigureId === listId ? editError : null;
            const Tag = b.ordered ? "ol" : "ul";
            if (canEditList) {
              return (
                <div
                  key={i}
                  className={`report-list-wrap report-block${isEditingList ? " is-editing" : ""}`}
                  style={delayStyle}
                >
                  <InlineBlockEditor
                    kind="list"
                    ordered={Boolean(b.ordered)}
                    initialItems={(b.items || []).map((it) => it.text)}
                    busy={isEditingList}
                    error={listError}
                    onSave={(items) => {
                      void onEditList?.({
                        listIndex: n,
                        items,
                        ordered: Boolean(b.ordered),
                      });
                    }}
                  />
                </div>
              );
            }
            return (
              <Tag
                key={i}
                className={`report-list report-block${b.ordered ? " is-ol" : ""}`}
                style={delayStyle}
              >
                {(b.items || []).map((it, j) =>
                  it.html ? (
                    <li
                      key={j}
                      dangerouslySetInnerHTML={{ __html: it.html }}
                    />
                  ) : (
                    <li key={j}>{it.text}</li>
                  ),
                )}
              </Tag>
            );
          }
          if (b.type === "table") {
            tabN += 1;
            const n = tabN;
            const tableId = `tab:${n}`;
            const tableOpen = canEditTable;
            const isEditingTable = editingFigureId === tableId;
            const tableError =
              tableOpen && editErrorFigureId === tableId ? editError : null;
            const live =
              tableOpen && tableDraftByN[n]
                ? tableDraftByN[n]
                : {
                    caption: b.caption || "",
                    headers: b.headers || [],
                    rows: b.rows || [],
                  };
            const numericCols = live.headers.map((_, ci) =>
              colIsNumeric(live.headers, live.rows, ci),
            );
            const capText = live.caption.trim()
              ? `Таблица ${n}: ${live.caption.trim()}`
              : `Таблица ${n}`;
            return (
              <figure
                key={i}
                className={`report-table-wrap report-block${isEditingTable ? " is-editing" : ""}${tableOpen ? " is-tuning" : ""}`}
                style={delayStyle}
              >
                <div className="report-table-toolbar">
                  <figcaption
                    className={`report-caption${live.caption.trim() ? "" : " muted"}${tableOpen ? " is-draft" : ""}`}
                  >
                    {capText}
                    {tableOpen && !isEditingTable ? (
                      <span className="report-table-draft-tag"> черновик</span>
                    ) : null}
                  </figcaption>
                </div>
                <div className="report-table-scroll">
                  <table className="report-table">
                    <thead>
                      <tr>
                        {live.headers.map((h, hi) => (
                          <th
                            key={hi}
                            className={numericCols[hi] ? "num" : undefined}
                          >
                            {h || (
                              <span className="report-table-ph">Столбец {hi + 1}</span>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {live.rows.map((row, ri) => (
                        <tr key={ri}>
                          {row.map((cell, ci) => (
                            <td
                              key={ci}
                              className={numericCols[ci] ? "num" : undefined}
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {isEditingTable && (
                  <div className="report-table-busy" aria-live="polite">
                    <p className="fig-press-label">Пересобираю таблицу в отчёте…</p>
                    <p className="fig-press-hint">TeX · PDF · DOCX</p>
                  </div>
                )}
                {tableOpen && onEditTable && (
                  <TableEditSheet
                    open
                    trapFocus={false}
                    tableIndex={n}
                    initialCaption={b.caption || ""}
                    initialHeaders={b.headers || []}
                    initialRows={b.rows || []}
                    busy={isEditingTable}
                    error={tableError}
                    onDraftChange={(d) =>
                      setTableDraftByN((prev) => ({ ...prev, [n]: d }))
                    }
                    onCancel={() => {
                      setTableDraftByN((prev) => {
                        const next = { ...prev };
                        delete next[n];
                        return next;
                      });
                    }}
                    onSubmit={(req) => {
                      void onEditTable(req);
                    }}
                  />
                )}
              </figure>
            );
          }
          if (b.type === "figure") {
            figN += 1;
            const n = figN;
            const label = b.kind === "chart" ? "Рис." : "Илл.";
            const caption = b.caption
              ? `${label} ${n}: ${b.caption}`
              : `${label} ${n}`;
            const isChart = b.kind === "chart";
            const isPhoto = !isChart;
            const isEditing = editingFigureId === b.id;
            const sheetOpen = isChart && canEditFigure;
            const imageOpen = isPhoto && canEditImage;
            const sheetError =
              (sheetOpen || imageOpen) && editErrorFigureId === b.id
                ? editError
                : null;
            const intent =
              sheetOpen && draftById[b.id] && !isEditing
                ? draftById[b.id]
                : null;
            const jumpPdf = () => {
              onJumpToPdf?.({
                id: b.id,
                figureIndex: n,
                pdfPage: b.pdfPage,
                caption,
              });
            };
            const figInner = (
              <>
                <div className="report-fig-frame">
                  {isChart && runId ? (
                    <ChartLivePane
                      runId={runId}
                      chartId={b.id}
                      caption={b.caption || caption}
                      fallbackUrl={b.url}
                      version={bustFromUrl(b.url)}
                      htmlOverride={
                        sheetOpen ? sheetPreviewHtmlById[b.id] ?? null : null
                      }
                      disabled={isEditing}
                      onJumpToPdf={onJumpToPdf ? jumpPdf : undefined}
                    />
                  ) : b.url ? (
                    <button
                      type="button"
                      className="report-fig-link"
                      onClick={() => {
                        if (onJumpToPdf) jumpPdf();
                        else setLightbox({ url: b.url!, caption });
                      }}
                      aria-label={
                        onJumpToPdf
                          ? `Показать ${caption} в PDF`
                          : `Открыть ${caption}`
                      }
                      disabled={isEditing}
                    >
                      <img src={b.url} alt={b.caption || b.id} loading="lazy" />
                    </button>
                  ) : (
                    <div className="report-fig-missing">
                      {b.id} — изображение недоступно
                    </div>
                  )}
                  {intent && (
                    <div
                      className="report-fig-intent"
                      style={
                        intent.wash
                          ? {
                              background: `linear-gradient(135deg, ${intent.wash}33, transparent 65%)`,
                            }
                          : undefined
                      }
                      aria-hidden
                    >
                      <span className="report-fig-intent-badge">
                        будет:{" "}
                        {chartTypeChipLabel(intent.chartType) || intent.chartType}
                        {intent.paletteLabel
                          ? ` · ${intent.paletteLabel}`
                          : ""}
                      </span>
                      <span className="report-fig-intent-note">
                        после сохранения
                      </span>
                    </div>
                  )}
                  {isPhoto && b.url && !isEditing && (
                    <button
                      type="button"
                      className="report-fig-zoom"
                      title="Увеличить"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setLightbox({ url: b.url!, caption });
                      }}
                    >
                      ↗
                    </button>
                  )}
                  {isEditing && (
                    <div
                      className={`report-fig-busy${isPhoto ? " is-photo" : ""}`}
                      aria-live="polite"
                    >
                      {isPhoto ? (
                        <div className="fig-photo-spin" aria-hidden>
                          <div className="fig-photo-frame">
                            <div className="fig-photo-shutter" />
                            <div className="fig-photo-grain" />
                          </div>
                        </div>
                      ) : (
                        <div className="fig-press" aria-hidden>
                          <div className="fig-press-sheet">
                            <i className="fig-press-bar" style={{ width: "72%" }} />
                            <i className="fig-press-bar" style={{ width: "88%" }} />
                            <i
                              className="fig-press-bar short"
                              style={{ width: "54%" }}
                            />
                            <div className="fig-press-plot">
                              <span />
                              <span />
                              <span />
                              <span />
                              <span />
                            </div>
                          </div>
                          <div className="fig-press-roller" />
                        </div>
                      )}
                      <p className="fig-press-label">
                        {isPhoto
                          ? "Генерирую фото на столе…"
                          : "Пересобираю рисунок на столе…"}
                      </p>
                      <p className="fig-press-hint">
                        {isPhoto ? "Image API · PDF" : "тип · палитра · PDF"}
                      </p>
                    </div>
                  )}
                </div>

                <figcaption
                  className={`report-caption report-fig-cap${onJumpToPdf ? " is-jump" : ""}`}
                  title={
                    b.chartType
                      ? `Тип: ${b.chartType}${onJumpToPdf ? " · клик → PDF" : ""}`
                      : onJumpToPdf
                        ? "Клик → страница PDF"
                        : undefined
                  }
                  onClick={
                    onJumpToPdf && !isEditing
                      ? (e) => {
                          e.preventDefault();
                          jumpPdf();
                        }
                      : undefined
                  }
                  role={onJumpToPdf ? "link" : undefined}
                  tabIndex={onJumpToPdf ? 0 : undefined}
                  onKeyDown={
                    onJumpToPdf
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            jumpPdf();
                          }
                        }
                      : undefined
                  }
                >
                  {caption}
                </figcaption>

                {sheetOpen && onEditFigure && (
                  <ChartEditSheet
                    open
                    trapFocus={false}
                    figureId={b.id}
                    runId={runId}
                    caption={b.caption || caption}
                    palettes={palettes}
                    catalogTypes={catalogTypes}
                    initialPalette={
                      (b.palette && b.palette !== "auto"
                        ? b.palette
                        : defaultPalette) || "atelier"
                    }
                    initialType={b.chartType || ""}
                    busy={isEditing}
                    error={sheetError}
                    onDraftChange={(d) =>
                      setDraftById((prev) => ({ ...prev, [b.id]: d }))
                    }
                    onPreviewHtml={(html) =>
                      setSheetPreviewHtmlById((prev) => ({
                        ...prev,
                        [b.id]: html,
                      }))
                    }
                    onCancel={() => {
                      setDraftById((prev) => {
                        const next = { ...prev };
                        delete next[b.id];
                        return next;
                      });
                      setSheetPreviewHtmlById((prev) => {
                        const next = { ...prev };
                        delete next[b.id];
                        return next;
                      });
                    }}
                    onSubmit={(req) => {
                      void onEditFigure(req);
                    }}
                  />
                )}
                {imageOpen && onEditImage && (
                  <ImageEditModal
                    open
                    trapFocus={false}
                    figureId={b.id}
                    caption={b.caption || caption}
                    previewUrl={b.url}
                    busy={isEditing}
                    error={sheetError}
                    onCancel={() => {}}
                    onSubmit={(req) => {
                      void onEditImage(req);
                    }}
                  />
                )}
              </>
            );
            return (
              <figure
                key={i}
                className={`report-fig report-block${isEditing ? " is-editing" : ""}${sheetOpen || imageOpen ? " is-tuning" : ""}`}
                style={delayStyle}
              >
                {isChart ? (
                  <ChartCard
                    insight={b.insight}
                    highlights={b.highlights}
                    chartType={b.chartType}
                  >
                    {figInner}
                  </ChartCard>
                ) : (
                  figInner
                )}
              </figure>
            );
          }
          return null;
        })}
      </div>

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

/** Soft atelier node-flow while the pipeline runs. */
export function ReportPending({
  label = "Набираю отчёт на столе…",
  stage,
  detail,
  mode = "report",
}: {
  label?: string;
  stage?: string | null;
  detail?: string | null;
  mode?: "report" | "diagram" | "presentation" | string | null;
}) {
  return (
    <div className="report-pending">
      <PipelineFlow stage={stage} label={label} detail={detail} mode={mode} />
    </div>
  );
}
