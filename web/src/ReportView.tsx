/** Liber Print Desk — in-chat report: title, prose, tables, figure PNGs + chart edit. */

import {
  lazy,
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
import {
  ParagraphEditSheet,
  type ParagraphEditRequest,
} from "./ParagraphEditSheet";
import { PipelineFlow } from "./PipelineFlow";
import {
  isBlockHiddenByCollapse,
  loadCollapsedIds,
  saveCollapsedIds,
} from "./reportSections";

const PdfFirstPage = lazy(() =>
  import("./PdfFirstPage").then((m) => ({ default: m.PdfFirstPage })),
);

export type PreviewBlock =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; id?: string; text: string; html?: string }
  | {
      type: "list";
      ordered?: boolean;
      items: { text: string; html?: string }[];
    }
  | {
      type: "table";
      caption?: string;
      headers: string[];
      rows: string[][];
    }
  | {
      type: "figure";
      id: string;
      kind: string;
      caption?: string;
      url?: string;
      chartType?: string;
      /** G2: last applied / run palette id for edit sheet seed. */
      palette?: string;
      /** C10: 1-based PDF page hint from TeX breaks. */
      pdfPage?: number;
      insight?: string;
      highlights?: { label: string; value: string; pct?: string }[];
    };

export type ReportPreview = {
  title?: string;
  blocks: PreviewBlock[];
};

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
  onEditCancel,
}: Props) {
  const blocks = preview.blocks || [];
  let figN = 0;
  let tabN = 0;
  let headN = 0;
  let paraN = 0;
  const [lightbox, setLightbox] = useState<{
    url: string;
    caption: string;
  } | null>(null);
  const [sheetFor, setSheetFor] = useState<string | null>(null);
  const [imageFor, setImageFor] = useState<string | null>(null);
  const [tableFor, setTableFor] = useState<number | null>(null);
  const [tableDraft, setTableDraft] = useState<TableEditDraft | null>(null);
  const [paraFor, setParaFor] = useState<number | null>(null);
  const [draft, setDraft] = useState<ChartEditDraft | null>(null);
  const [sheetPreviewHtml, setSheetPreviewHtml] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(
    () => loadCollapsedIds(runId || ""),
  );
  const lbTitle = useId();

  useEffect(() => {
    setCollapsed(loadCollapsedIds(runId || ""));
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

  const closeSheet = useCallback(() => {
    setSheetFor(null);
    setDraft(null);
    setSheetPreviewHtml(null);
    onEditCancel?.();
  }, [onEditCancel]);

  const closeImage = useCallback(() => {
    setImageFor(null);
    onEditCancel?.();
  }, [onEditCancel]);

  const closeTable = useCallback(() => {
    setTableFor(null);
    setTableDraft(null);
    onEditCancel?.();
  }, [onEditCancel]);

  const closePara = useCallback(() => {
    setParaFor(null);
    onEditCancel?.();
  }, [onEditCancel]);

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

  useEffect(() => {
    if (editingFigureId) setSheetFor(editingFigureId);
  }, [editingFigureId]);
  return (
    <article className="report">
      <div className="report-rail" aria-hidden />

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
            const headingId = `rail-h-${headN}`;
            // Nested under a collapsed ancestor — hide (parent heading stays).
            if (hiddenByCollapse) return null;
            const Tag = b.level >= 2 ? "h3" : "h2";
            const expanded = !collapsed.has(headingId);
            return (
              <div
                key={i}
                className={`report-h-row report-block report-h${b.level}`}
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
                >
                  <span className="report-h-toggle-chevron" aria-hidden>
                    ▸
                  </span>
                </button>
                <Tag
                  id={headingId}
                  className={`report-h report-h${b.level}`}
                >
                  {b.text}
                </Tag>
              </div>
            );
          }

          if (hiddenByCollapse) {
            // Keep fig/tab/para counters stable when section is collapsed.
            if (b.type === "figure") figN += 1;
            if (b.type === "table") tabN += 1;
            if (b.type === "paragraph") paraN += 1;
            return null;
          }

          if (b.type === "paragraph") {
            paraN += 1;
            const idMatch = b.id ? /^para-(\d+)$/.exec(b.id) : null;
            const n = idMatch ? Number(idMatch[1]) : paraN;
            if (idMatch) paraN = Math.max(paraN, n);
            const paraId = `para:${n}`;
            const isEditingPara = editingFigureId === paraId;
            const sheetOpen = paraFor === n;
            const sheetError =
              sheetOpen && editErrorFigureId === paraId ? editError : null;
            return (
              <div
                key={i}
                className={`report-para-wrap report-block${sheetOpen ? " is-tuning" : ""}${isEditingPara ? " is-editing" : ""}`}
                style={delayStyle}
              >
                <div className="report-para-frame">
                  {b.html ? (
                    <p
                      className="report-p"
                      dangerouslySetInnerHTML={{ __html: b.html }}
                    />
                  ) : (
                    <p className="report-p">{b.text}</p>
                  )}
                  {onEditParagraph && !isEditingPara && (
                    <button
                      type="button"
                      className={`report-fig-edit report-para-edit${sheetOpen ? " is-open" : ""}`}
                      aria-expanded={sheetOpen}
                      onClick={() => {
                        if (sheetOpen) closePara();
                        else {
                          setSheetFor(null);
                          setImageFor(null);
                          setTableFor(null);
                          setParaFor(n);
                        }
                      }}
                    >
                      {sheetOpen ? "Закрыть" : "Изменить"}
                    </button>
                  )}
                  {isEditingPara && (
                    <div className="report-fig-busy" aria-live="polite">
                      <p className="fig-press-label">Пересобираю абзац…</p>
                    </div>
                  )}
                </div>
                {sheetOpen && onEditParagraph && (
                  <ParagraphEditSheet
                    open
                    paragraphIndex={n}
                    initialText={b.text}
                    busy={isEditingPara}
                    error={sheetError}
                    onCancel={() => {
                      if (!editingFigureId) closePara();
                    }}
                    onSubmit={(req) => {
                      void (async () => {
                        const ok = await onEditParagraph(req);
                        if (ok) closePara();
                      })();
                    }}
                  />
                )}
              </div>
            );
          }
          if (b.type === "list") {
            const Tag = b.ordered ? "ol" : "ul";
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
            const tableOpen = tableFor === n;
            const isEditingTable = editingFigureId === tableId;
            const tableError =
              tableOpen && editErrorFigureId === tableId ? editError : null;
            const live =
              tableOpen && tableDraft
                ? tableDraft
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
                  {onEditTable && !isEditingTable && (
                    <button
                      type="button"
                      className={`report-fig-edit${tableOpen ? " is-open" : ""}`}
                      aria-expanded={tableOpen}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        if (tableOpen) closeTable();
                        else {
                          setSheetFor(null);
                          setImageFor(null);
                          setParaFor(null);
                          setTableDraft(null);
                          setTableFor(n);
                        }
                      }}
                    >
                      {tableOpen ? "Закрыть" : "Изменить"}
                    </button>
                  )}
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
                    tableIndex={n}
                    initialCaption={b.caption || ""}
                    initialHeaders={b.headers || []}
                    initialRows={b.rows || []}
                    busy={isEditingTable}
                    error={tableError}
                    onDraftChange={setTableDraft}
                    onCancel={() => {
                      if (!editingFigureId) closeTable();
                    }}
                    onSubmit={(req) => {
                      void (async () => {
                        const ok = await onEditTable(req);
                        if (ok) closeTable();
                      })();
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
            const sheetOpen = sheetFor === b.id;
            const imageOpen = imageFor === b.id;
            const sheetError =
              (sheetOpen || imageOpen) && editErrorFigureId === b.id
                ? editError
                : null;
            const intent =
              sheetOpen && draft && !isEditing ? draft : null;
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
                        sheetOpen ? sheetPreviewHtml : null
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
                  {isChart && onEditFigure && !isEditing && (
                    <button
                      type="button"
                      className={`report-fig-edit${sheetOpen ? " is-open" : ""}`}
                      disabled={false}
                      aria-expanded={sheetOpen}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        if (sheetOpen) closeSheet();
                        else {
                          setImageFor(null);
                          setTableFor(null);
                          setParaFor(null);
                          setDraft(null);
                          setSheetFor(b.id);
                        }
                      }}
                    >
                      {sheetOpen ? "Закрыть" : "Изменить"}
                    </button>
                  )}
                  {isPhoto && onEditImage && !isEditing && (
                    <button
                      type="button"
                      className={`report-fig-edit${imageOpen ? " is-open" : ""}`}
                      disabled={false}
                      aria-expanded={imageOpen}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        if (imageOpen) closeImage();
                        else {
                          setSheetFor(null);
                          setTableFor(null);
                          setParaFor(null);
                          setImageFor(b.id);
                        }
                      }}
                    >
                      {imageOpen ? "Закрыть" : "Изменить"}
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

                {isChart && sheetOpen && onEditFigure && (
                  <ChartEditSheet
                    open
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
                    onDraftChange={setDraft}
                    onPreviewHtml={setSheetPreviewHtml}
                    onCancel={() => {
                      if (!editingFigureId) closeSheet();
                    }}
                    onSubmit={(req) => {
                      void (async () => {
                        const ok = await onEditFigure(req);
                        if (ok) closeSheet();
                      })();
                    }}
                  />
                )}
                {isPhoto && imageOpen && onEditImage && (
                  <ImageEditModal
                    open
                    figureId={b.id}
                    caption={b.caption || caption}
                    previewUrl={b.url}
                    busy={isEditing}
                    error={sheetError}
                    onCancel={() => {
                      if (!editingFigureId) closeImage();
                    }}
                    onSubmit={(req) => {
                      void (async () => {
                        const ok = await onEditImage(req);
                        if (ok) closeImage();
                      })();
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
