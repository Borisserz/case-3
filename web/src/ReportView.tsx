/** Liber Print Desk — in-chat report: title, prose, tables, figure PNGs + chart edit. */

import { lazy, Suspense, useCallback, useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";
import {
  ChartEditSheet,
  type ChartEditDraft,
  type ChartEditRequest,
  type PaletteInfo,
} from "./ChartEditSheet";
import { ChartCard } from "./ChartCard";
import { ChartLivePane } from "./ChartLivePane";
import {
  ImageEditModal,
  type ImageEditRequest,
} from "./ImageEditModal";
import { PipelineFlow } from "./PipelineFlow";

const PdfFirstPage = lazy(() =>
  import("./PdfFirstPage").then((m) => ({ default: m.PdfFirstPage })),
);

export type PreviewBlock =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string; html?: string }
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
  stats?: string;
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
  }) => void;
  /** C3: open PDF tab when preview body is empty. */
  onOpenPdf?: () => void;
  /** Resolve true on success so the sheet can close. */
  onEditFigure?: (req: ChartEditRequest) => Promise<boolean> | boolean;
  onEditImage?: (req: ImageEditRequest) => Promise<boolean> | boolean;
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
  stats,
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
  onEditCancel,
}: Props) {
  const blocks = preview.blocks || [];
  let figN = 0;
  let tabN = 0;
  let headN = 0;
  const [lightbox, setLightbox] = useState<{
    url: string;
    caption: string;
  } | null>(null);
  const [sheetFor, setSheetFor] = useState<string | null>(null);
  const [imageFor, setImageFor] = useState<string | null>(null);
  const [draft, setDraft] = useState<ChartEditDraft | null>(null);
  const lbTitle = useId();

  const closeSheet = useCallback(() => {
    setSheetFor(null);
    setDraft(null);
    onEditCancel?.();
  }, [onEditCancel]);

  const closeImage = useCallback(() => {
    setImageFor(null);
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

      {(stats || (warnings && warnings.length > 0) || runId) && (
        <header className="report-meta">
          {runId && <span className="report-run">run {runId}</span>}
          {stats && <span className="report-stats">{stats}</span>}
          {warnings && warnings.length > 0 && (
            <span className="report-warns">{warnings.join(" · ")}</span>
          )}
        </header>
      )}

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

          if (b.type === "heading") {
            headN += 1;
            const Tag = b.level >= 2 ? "h3" : "h2";
            return (
              <Tag
                key={i}
                id={`rail-h-${headN}`}
                className={`report-h report-h${b.level} report-block`}
                style={delayStyle}
              >
                {b.text}
              </Tag>
            );
          }
          if (b.type === "paragraph") {
            if (b.html) {
              return (
                <p
                  key={i}
                  className="report-p report-block"
                  style={delayStyle}
                  dangerouslySetInnerHTML={{ __html: b.html }}
                />
              );
            }
            return (
              <p key={i} className="report-p report-block" style={delayStyle}>
                {b.text}
              </p>
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
            const numericCols = (b.headers || []).map((_, ci) =>
              colIsNumeric(b.headers, b.rows, ci),
            );
            return (
              <figure
                key={i}
                className="report-table-wrap report-block"
                style={delayStyle}
              >
                {b.caption ? (
                  <figcaption className="report-caption">
                    Таблица {n}: {b.caption}
                  </figcaption>
                ) : (
                  <figcaption className="report-caption muted">
                    Таблица {n}
                  </figcaption>
                )}
                <div className="report-table-scroll">
                  <table className="report-table">
                    <thead>
                      <tr>
                        {b.headers.map((h, hi) => (
                          <th
                            key={hi}
                            className={numericCols[hi] ? "num" : undefined}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {b.rows.map((row, ri) => (
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
                        будет: {intent.chartType}
                        {intent.paletteLabel
                          ? ` · ${intent.paletteLabel}`
                          : ""}
                      </span>
                      <span className="report-fig-intent-note">
                        после сохранения
                      </span>
                    </div>
                  )}
                  {onJumpToPdf && !isEditing && (
                    <button
                      type="button"
                      className="report-fig-pdf"
                      title="Показать в вкладке PDF"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        jumpPdf();
                      }}
                    >
                      в PDF
                      {b.pdfPage ? ` · с.${b.pdfPage}` : ""}
                    </button>
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
                    initialPalette={defaultPalette}
                    initialType={b.chartType || ""}
                    busy={isEditing}
                    error={sheetError}
                    onDraftChange={setDraft}
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
                className={`report-fig report-block${isEditing ? " is-editing" : ""}${sheetOpen ? " is-tuning" : ""}`}
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
}: {
  label?: string;
  stage?: string | null;
  detail?: string | null;
}) {
  return (
    <div className="report-pending">
      <PipelineFlow stage={stage} label={label} detail={detail} />
      <div className="report-pending-lines" aria-hidden>
        <i style={{ width: "92%" }} />
        <i style={{ width: "78%" }} />
        <i style={{ width: "64%" }} />
      </div>
    </div>
  );
}
