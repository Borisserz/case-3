/** PDF page slider (pdf.js). Supports controlled page for figure→PDF jump. */

import { useCallback, useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import type { PDFDocumentProxy } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

type Props = {
  url: string;
  /** Jump to this page when it changes (1-based). */
  page?: number;
  onPageChange?: (page: number, pageCount: number) => void;
};

export function PdfFirstPage({ url, page: pageProp, onPageChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const docRef = useRef<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const renderGen = useRef(0);

  const renderPage = useCallback(async (doc: PDFDocumentProxy, n: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gen = ++renderGen.current;
    setDrawing(true);
    try {
      const pdfPage = await doc.getPage(n);
      if (gen !== renderGen.current) return;
      const base = pdfPage.getViewport({ scale: 1 });
      const maxW = Math.min(720, canvas.parentElement?.clientWidth || 720);
      const scale = maxW / base.width;
      const viewport = pdfPage.getViewport({ scale: Math.max(0.8, scale) });
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("no canvas");
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      await pdfPage.render({ canvasContext: ctx, viewport }).promise;
      if (gen !== renderGen.current) return;
      setReady(true);
      setErr(null);
    } finally {
      if (gen === renderGen.current) setDrawing(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    setReady(false);
    setPage(1);
    setPageCount(0);
    const prev = docRef.current;
    docRef.current = null;
    if (prev) void prev.destroy();
    if (!url) return;

    (async () => {
      try {
        const doc = await pdfjs
          .getDocument({ url, withCredentials: false })
          .promise;
        if (cancelled) {
          void doc.destroy();
          return;
        }
        docRef.current = doc;
        setPageCount(doc.numPages);
        const start =
          pageProp && pageProp >= 1
            ? Math.min(pageProp, doc.numPages)
            : 1;
        setPage(start);
        onPageChange?.(start, doc.numPages);
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "PDF preview failed");
        }
      }
    })();

    return () => {
      cancelled = true;
      const d = docRef.current;
      docRef.current = null;
      if (d) void d.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only on url
  }, [url]);

  useEffect(() => {
    if (pageProp == null || pageCount < 1) return;
    const next = Math.min(pageCount, Math.max(1, pageProp));
    setPage((p) => (p === next ? p : next));
  }, [pageProp, pageCount]);

  useEffect(() => {
    const doc = docRef.current;
    if (!doc || pageCount < 1) return;
    let cancelled = false;
    (async () => {
      try {
        await renderPage(doc, page);
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "PDF page failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page, pageCount, renderPage]);

  const go = useCallback(
    (delta: number) => {
      setPage((p) => {
        if (pageCount < 1) return p;
        const next = Math.min(pageCount, Math.max(1, p + delta));
        onPageChange?.(next, pageCount);
        return next;
      });
    },
    [pageCount, onPageChange],
  );

  useEffect(() => {
    if (pageCount < 2) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.isContentEditable)
      ) {
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        go(1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, pageCount]);

  const multi = pageCount > 1;

  return (
    <figure className={`report-pdf-page${ready ? " is-ready" : ""}`}>
      <div className="report-pdf-stage">
        {!ready && !err && (
          <div className="pdf-skeleton" aria-hidden>
            <div className="pdf-skeleton-shine" />
            <div className="pdf-skeleton-lines">
              <i style={{ width: "48%" }} />
              <i style={{ width: "92%" }} />
              <i style={{ width: "78%" }} />
              <i style={{ width: "86%" }} />
              <i style={{ width: "64%" }} />
            </div>
          </div>
        )}
        {multi && (
          <button
            type="button"
            className="report-pdf-nav prev"
            onClick={() => go(-1)}
            disabled={page <= 1 || drawing}
            aria-label="Предыдущая страница"
          >
            ‹
          </button>
        )}
        <canvas
          ref={canvasRef}
          className={ready ? "is-shown" : "is-hidden"}
          aria-label={`Страница ${page} из ${pageCount || "…"} PDF`}
        />
        {multi && (
          <button
            type="button"
            className="report-pdf-nav next"
            onClick={() => go(1)}
            disabled={page >= pageCount || drawing}
            aria-label="Следующая страница"
          >
            ›
          </button>
        )}
      </div>
      <figcaption className="report-pdf-cap">
        {err
          ? "Превью PDF недоступно — скачайте файл"
          : pageCount
            ? `Стр. ${page} / ${pageCount} · как в PDF`
            : "Загрузка PDF…"}
      </figcaption>
    </figure>
  );
}
