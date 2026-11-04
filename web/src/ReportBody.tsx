/** Report preview body: empty state + block list (headings/tables/figures). */

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
import { isBlockHiddenByCollapse } from "./reportSections";
import { bustFromUrl, colIsNumeric } from "./reportTableNumeric";
import type { PreviewBlock } from "./domain/reportPreview";
import type { Dispatch, SetStateAction } from "react";

export type ReportBodyProps = {
  blocks: PreviewBlock[];
  downloads?: Record<string, string>;
  runId?: string;
  palettes: PaletteInfo[];
  catalogTypes: string[];
  defaultPalette: string;
  editingFigureId: string | null;
  editError: string | null;
  editErrorFigureId: string | null;
  collapsed: Set<string>;
  editMode: boolean;
  canEditPara: boolean;
  canEditHeading: boolean;
  canEditList: boolean;
  canEditTable: boolean;
  canEditFigure: boolean;
  canEditImage: boolean;
  tableDraftByN: Record<number, TableEditDraft>;
  draftById: Record<string, ChartEditDraft>;
  sheetPreviewHtmlById: Record<string, string | null>;
  setTableDraftByN: Dispatch<SetStateAction<Record<number, TableEditDraft>>>;
  setDraftById: Dispatch<SetStateAction<Record<string, ChartEditDraft>>>;
  setSheetPreviewHtmlById: Dispatch<
    SetStateAction<Record<string, string | null>>
  >;
  setLightbox: (v: { url: string; caption: string } | null) => void;
  toggleSection: (headingId: string) => void;
  onJumpToPdf?: (info: {
    id: string;
    figureIndex: number;
    pdfPage?: number;
    caption?: string;
  }) => void;
  onOpenPdf?: () => void;
  onEditFigure?: (req: ChartEditRequest) => Promise<boolean> | boolean;
  onEditImage?: (req: ImageEditRequest) => Promise<boolean> | boolean;
  onEditTable?: (req: TableEditRequest) => Promise<boolean> | boolean;
  onEditParagraph?: (req: ParagraphEditRequest) => Promise<boolean> | boolean;
  onEditHeading?: (req: HeadingEditRequest) => Promise<boolean> | boolean;
  onEditList?: (req: ListEditRequest) => Promise<boolean> | boolean;
  /** Exactly one prose/list block open at a time (document click-to-edit). */
  activeBlockId?: string | null;
  onActiveBlockId?: (id: string | null) => void;
  /** On-demand chart/table/image sheet id (`tab:N` / figure id). */
  openMediaId?: string | null;
  onOpenMediaId?: (id: string | null) => void;
};

export function ReportBody({
  blocks,
  downloads,
  runId,
  palettes,
  catalogTypes,
  defaultPalette,
  editingFigureId,
  editError,
  editErrorFigureId,
  collapsed,
  editMode,
  canEditPara,
  canEditHeading,
  canEditList,
  canEditTable,
  canEditFigure,
  canEditImage,
  tableDraftByN,
  draftById,
  sheetPreviewHtmlById,
  setTableDraftByN,
  setDraftById,
  setSheetPreviewHtmlById,
  setLightbox,
  toggleSection,
  onJumpToPdf,
  onOpenPdf,
  onEditFigure,
  onEditImage,
  onEditTable,
  onEditParagraph,
  onEditHeading,
  onEditList,
  activeBlockId = null,
  onActiveBlockId,
  openMediaId = null,
  onOpenMediaId,
}: ReportBodyProps) {
  let figN = 0;
  let tabN = 0;
  let headN = 0;
  let paraN = 0;
  let listN = 0;

  return (
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
            const headActive = canEditHeading && activeBlockId === headEditId;
            const headError =
              isEditingHead || editErrorFigureId === headEditId
                ? editError
                : null;
            return (
              <div
                key={i}
                className={`report-h-row report-block${headActive || isEditingHead ? " is-editing" : ""}${canEditHeading && !headActive ? " is-editable-idle" : ""}`}
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
                {headActive ? (
                  <div className="report-h-edit" id={headingId}>
                    <InlineBlockEditor
                      hideActions
                      kind="heading"
                      initialText={b.text}
                      busy={isEditingHead}
                      error={headError}
                      onCancel={() => onActiveBlockId?.(null)}
                      onSave={(text) => {
                        void (async () => {
                          const ok = await onEditHeading?.({
                            headingIndex,
                            text,
                          });
                          if (ok !== false) onActiveBlockId?.(null);
                        })();
                      }}
                    />
                  </div>
                ) : (
                  <Tag
                    id={headingId}
                    className={`report-h report-h${b.level}${canEditHeading ? " is-click-edit" : ""}`}
                    role={canEditHeading ? "button" : undefined}
                    tabIndex={canEditHeading ? 0 : undefined}
                    onClick={
                      canEditHeading
                        ? () => {
                            onOpenMediaId?.(null);
                            onActiveBlockId?.(headEditId);
                          }
                        : undefined
                    }
                    onKeyDown={
                      canEditHeading
                        ? (e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              onOpenMediaId?.(null);
                              onActiveBlockId?.(headEditId);
                            }
                          }
                        : undefined
                    }
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
            const paraActive = canEditPara && activeBlockId === paraId;
            const sheetError =
              editErrorFigureId === paraId ? editError : null;
            return (
              <div
                key={i}
                className={`report-para-wrap report-block${paraActive || isEditingPara ? " is-editing" : ""}${canEditPara && !paraActive ? " is-editable-idle" : ""}`}
                style={delayStyle}
              >
                <div className="report-para-frame">
                  {paraActive ? (
                    <InlineBlockEditor
                      hideActions
                      kind="paragraph"
                      initialText={b.text}
                      busy={isEditingPara}
                      error={sheetError}
                      onCancel={() => onActiveBlockId?.(null)}
                      onSave={(text) => {
                        void (async () => {
                          const ok = await onEditParagraph?.({
                            paragraphIndex: n,
                            text,
                          });
                          if (ok !== false) onActiveBlockId?.(null);
                        })();
                      }}
                    />
                  ) : b.html ? (
                    <p
                      className={`report-p${canEditPara ? " is-click-edit" : ""}`}
                      role={canEditPara ? "button" : undefined}
                      tabIndex={canEditPara ? 0 : undefined}
                      onClick={
                        canEditPara
                          ? () => {
                              onOpenMediaId?.(null);
                              onActiveBlockId?.(paraId);
                            }
                          : undefined
                      }
                      onKeyDown={
                        canEditPara
                          ? (e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                onOpenMediaId?.(null);
                                onActiveBlockId?.(paraId);
                              }
                            }
                          : undefined
                      }
                      dangerouslySetInnerHTML={{ __html: b.html }}
                    />
                  ) : (
                    <p
                      className={`report-p${canEditPara ? " is-click-edit" : ""}`}
                      role={canEditPara ? "button" : undefined}
                      tabIndex={canEditPara ? 0 : undefined}
                      onClick={
                        canEditPara
                          ? () => {
                              onOpenMediaId?.(null);
                              onActiveBlockId?.(paraId);
                            }
                          : undefined
                      }
                      onKeyDown={
                        canEditPara
                          ? (e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                onOpenMediaId?.(null);
                                onActiveBlockId?.(paraId);
                              }
                            }
                          : undefined
                      }
                    >
                      {b.text}
                    </p>
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
            const listActive = canEditList && activeBlockId === listId;
            const listError =
              editErrorFigureId === listId ? editError : null;
            const Tag = b.ordered ? "ol" : "ul";
            if (listActive) {
              return (
                <div
                  key={i}
                  className={`report-list-wrap report-block is-editing`}
                  style={delayStyle}
                >
                  <InlineBlockEditor
                    hideActions
                    kind="list"
                    ordered={Boolean(b.ordered)}
                    initialItems={(b.items || []).map((it) => it.text)}
                    busy={isEditingList}
                    error={listError}
                    onCancel={() => onActiveBlockId?.(null)}
                    onSave={(items) => {
                      void (async () => {
                        const ok = await onEditList?.({
                          listIndex: n,
                          items,
                          ordered: Boolean(b.ordered),
                        });
                        if (ok !== false) onActiveBlockId?.(null);
                      })();
                    }}
                  />
                </div>
              );
            }
            return (
              <Tag
                key={i}
                className={`report-list report-block${b.ordered ? " is-ol" : ""}${canEditList ? " is-editable-idle is-click-edit" : ""}`}
                style={delayStyle}
                role={canEditList ? "button" : undefined}
                tabIndex={canEditList ? 0 : undefined}
                onClick={
                  canEditList
                    ? () => {
                        onOpenMediaId?.(null);
                        onActiveBlockId?.(listId);
                      }
                    : undefined
                }
                onKeyDown={
                  canEditList
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onOpenMediaId?.(null);
                          onActiveBlockId?.(listId);
                        }
                      }
                    : undefined
                }
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
            const tableOpen = canEditTable && openMediaId === tableId;
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
                className={`report-table-wrap report-block${isEditingTable ? " is-editing" : ""}${tableOpen ? " is-tuning" : ""}${canEditTable && !tableOpen ? " is-editable-idle" : ""}`}
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
                  {canEditTable && !tableOpen ? (
                    <button
                      type="button"
                      className="report-media-edit-btn"
                      onClick={() => {
                        onActiveBlockId?.(null);
                        onOpenMediaId?.(tableId);
                      }}
                    >
                      Править
                    </button>
                  ) : null}
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
                      onOpenMediaId?.(null);
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
            const sheetOpen =
              isChart && canEditFigure && openMediaId === b.id;
            const imageOpen =
              isPhoto && canEditImage && openMediaId === b.id;
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

                <div className="report-fig-cap-row">
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
                  {((isChart && canEditFigure) || (isPhoto && canEditImage)) &&
                  !sheetOpen &&
                  !imageOpen ? (
                    <button
                      type="button"
                      className="report-media-edit-btn"
                      onClick={() => {
                        onActiveBlockId?.(null);
                        onOpenMediaId?.(b.id);
                      }}
                    >
                      Править
                    </button>
                  ) : null}
                </div>

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
                      onOpenMediaId?.(null);
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
                    onCancel={() => onOpenMediaId?.(null)}
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
                className={`report-fig report-block${isEditing ? " is-editing" : ""}${sheetOpen || imageOpen ? " is-tuning" : ""}${(canEditFigure || canEditImage) && !sheetOpen && !imageOpen ? " is-editable-idle" : ""}`}
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
  );
}
