/** First PDF page → data URL thumb for ArtifactCard (cached, lazy pdf.js). */

import { useEffect, useState } from "react";

const cache = new Map<string, string>();

async function renderThumb(url: string): Promise<string> {
  const hit = cache.get(url);
  if (hit) return hit;
  const pdfjs = await import("pdfjs-dist");
  const pdfWorker = (
    await import("pdfjs-dist/build/pdf.worker.min.mjs?url")
  ).default;
  pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;
  const doc = await pdfjs.getDocument({ url, withCredentials: false }).promise;
  try {
    const page = await doc.getPage(1);
    const base = page.getViewport({ scale: 1 });
    const targetW = 160;
    const scale = targetW / base.width;
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("no canvas");
    await page.render({ canvasContext: ctx, viewport }).promise;
    const data = canvas.toDataURL("image/jpeg", 0.82);
    cache.set(url, data);
    return data;
  } finally {
    void doc.destroy();
  }
}

type Props = {
  pdfUrl?: string | null;
  fallbackUrl?: string | null;
  className?: string;
};

export function PdfThumb({ pdfUrl, fallbackUrl, className = "" }: Props) {
  const [src, setSrc] = useState<string | null>(
    () => (pdfUrl && cache.get(pdfUrl)) || fallbackUrl || null,
  );
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!pdfUrl) {
      setSrc(fallbackUrl || null);
      return;
    }
    const cached = cache.get(pdfUrl);
    if (cached) {
      setSrc(cached);
      return;
    }
    setFailed(false);
    void (async () => {
      try {
        const data = await renderThumb(pdfUrl);
        if (!cancelled) setSrc(data);
      } catch {
        if (!cancelled) {
          setFailed(true);
          setSrc(fallbackUrl || null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pdfUrl, fallbackUrl]);

  if (src) {
    return <img className={className} src={src} alt="" />;
  }
  return (
    <span className={`artifact-card-thumb-fallback${failed ? " is-soft" : ""}`}>
      PDF
    </span>
  );
}
