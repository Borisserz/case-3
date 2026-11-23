/** Full-screen Stimulsoft preview. «В данные» in the viewer attaches markdown. */

import { useEffect, useId, useRef, useState } from "react";
import { parseDashboard } from "./domain/dashboardParse";
import {
  captureOriginOk,
  documentsFromService,
  fileFromCapture,
  filesFromCapture,
  viewerFrameUrl,
  type CaptureFile,
} from "./domain/dashboardCapture";
import { useFocusTrap } from "./useFocusTrap";

type Doc = { name: string; markdown: string; warnings?: string[] };

type Props = {
  onClose: () => void;
  onShot: (docs: Doc[]) => void;
  /** How many screens from this opening are already in the chat. */
  shotCount?: number;
  /** /open after the API POSTed the filter body. The button path leaves this empty. */
  viewerUrl?: string | null;
};

async function parseFiles(files: CaptureFile[]): Promise<Doc[]> {
  const pngFile = files.find((f) => f.ext === "png") ?? null;
  const pdfFiles = files.filter((f) => f.ext === "pdf");
  const restFiles = files.filter((f) => f !== pngFile && !pdfFiles.includes(f));
  const docs: Doc[] = [];
  if (pngFile || pdfFiles.length) {
    const pngBin = pngFile ? fileFromCapture(pngFile) : null;
    const firstPdf = pdfFiles[0] ? fileFromCapture(pdfFiles[0]) : null;
    const parsed = await parseDashboard(pngBin, firstPdf);
    docs.push({
      name: pngFile?.name || pdfFiles[0]!.name,
      markdown: parsed.markdown,
      warnings: parsed.warnings,
    });
    for (const extraPdf of pdfFiles.slice(1)) {
      const bin = fileFromCapture(extraPdf);
      const extraParsed = await parseDashboard(null, bin);
      docs.push({
        name: extraPdf.name,
        markdown: extraParsed.markdown,
        warnings: extraParsed.warnings,
      });
    }
  }
  for (const file of restFiles) {
    const bin = fileFromCapture(file);
    const parsed = await parseDashboard(
      file.ext === "png" ? bin : null,
      file.ext === "pdf" ? bin : null,
    );
    docs.push({
      name: file.name,
      markdown: parsed.markdown,
      warnings: parsed.warnings,
    });
  }
  return docs;
}

export function DashboardPickModal({
  onClose,
  onShot,
  shotCount = 0,
  viewerUrl: viewerOverride,
}: Props) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const [viewerUrl, setViewerUrl] = useState(
    () => viewerOverride || viewerFrameUrl(import.meta.env.VITE_DASHBOARD_VIEWER_URL),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useFocusTrap(dialogRef, { active: true });

  useEffect(() => {
    if (viewerOverride) {
      setViewerUrl(viewerOverride);
      return;
    }
    let cancelled = false;
    void fetch("/api/dashboard/service")
      .then((res) => (res.ok ? res.json() : null))
      .then((body: { viewer?: string } | null) => {
        if (cancelled || !body?.viewer) return;
        setViewerUrl(viewerFrameUrl(body.viewer));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [viewerOverride]);

  async function takeFromService() {
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/dashboard/service-capture", { method: "POST" });
      const body: unknown = await res.json().catch(() => null);
      if (!res.ok) {
        const detail =
          body && typeof body === "object" && typeof (body as { detail?: unknown }).detail === "string"
            ? (body as { detail: string }).detail
            : "Сервис снимка не ответил.";
        setError(detail);
        return;
      }
      const docs = documentsFromService(body);
      if (!docs.length) {
        setError("Сервис не вернул файлы.");
        return;
      }
      onShot(docs);
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "Сервис снимка недоступен.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (!captureOriginOk(event.origin, viewerUrl)) return;
      const files = filesFromCapture(event.data);
      if (!files.length || busy) return;
      setBusy(true);
      setError("");
      void parseFiles(files)
        .then((docs) => {
          if (!docs.length) {
            setError("Парсер вернул пустой текст.");
            return;
          }
          onShot(docs);
        })
        .catch((exc: unknown) => {
          setError(exc instanceof Error ? exc.message : "Не удалось разобрать.");
        })
        .finally(() => setBusy(false));
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [busy, onShot, viewerUrl]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      ref={dialogRef}
      className="stimul-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="stimul-sheet is-viewer">
        <header className="settings-modal-head">
          <div>
            <p className="settings-modal-eyebrow">данные · стимулсофт</p>
            <h2 id={titleId} className="settings-modal-title">
              Выбрать данные
            </h2>
          </div>
          <div className="dash-viewer-actions">
            <button
              type="button"
              className="dash-viewer-take"
              onClick={() => void takeFromService()}
              disabled={busy}
            >
              {busy ? "Снимаю…" : "В данные"}
            </button>
            <button
              type="button"
              className="settings-modal-x"
              onClick={onClose}
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
        </header>
        <p className="dash-viewer-note">
          {busy
            ? "Снимаю текущий экран. Окно не закроется."
            : shotCount
              ? `В чате уже ${shotCount}. Можно снять ещё экран.`
              : "Дойди до нужного экрана и нажми «В данные». Окно останется открытым."}
        </p>
        {error ? <p className="dash-viewer-error">{error}</p> : null}
        <div className="dash-viewer-frame-wrap">
          <iframe
            className="dash-viewer-frame"
            title="Превью Stimulsoft"
            src={viewerUrl}
          />
          {busy ? (
            <div className="dash-viewer-loader" role="status">
              <span className="dash-viewer-spinner" />
              <p>Снимаю экран</p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
