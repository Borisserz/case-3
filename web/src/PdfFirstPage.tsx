/** In-chat PDF page slider (pdf.js). Left/right through all pages. */

import { useCallback, useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import type { PDFDocumentProxy } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

type Props = {
  url: string;
};

export function PdfFirstPage({ url }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const docRef = useRef<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [drawing, setDrawing] = useState(false);

  const renderPage = useCallback(async (doc: PDFDocumentProxy, n: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    setDrawing(true);
    try {
      const pdfPage = await doc.getPage(n);
      const base = pdfPage.getViewport({ scale: 1 });
      const maxW = Math.min(720, canvas.parentElement?.clientWidth || 720);
      const scale = maxW / base.width;
      const viewport = pdfPage.getViewport({ scale: Math.max(0.8, scale) });
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("no canvas");
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      await pdfPage.render({ canvasContext: ctx, viewport }).promise;
      setReady(true);
      setErr(null);
    } finally {
      setDrawing(false);
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
        const doc = await pdfjs.getDocument({ url, withCredentials: false }).promise;
        if (cancelled) {
          void doc.destroy();
          return;
        }
        docRef.current = doc;
        setPageCount(doc.numPages);
        setPage(1);
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
  }, [url]);

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
        return Math.min(pageCount, Math.max(1, p + delta));
      });
    },
    [pageCount],
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
