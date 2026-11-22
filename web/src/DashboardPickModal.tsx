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
  onReady: (docs: Doc[]) => void;
  /** His /open URL. The button path leaves this empty and uses /viewer. */
  viewerUrl?: string | null;
};

async function parseFiles(files: CaptureFile[]): Promise<Doc[]> {
  const docs: Doc[] = [];
  for (const file of files) {
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
  onReady,
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
      onReady(docs);
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
          onReady(docs);
        })
        .catch((exc: unknown) => {
          setError(exc instanceof Error ? exc.message : "Не удалось разобрать.");
        })
        .finally(() => setBusy(false));
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [busy, onReady, viewerUrl]);

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
              В данные
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
            ? "Жду снимок сервиса. Это до полутора минут."
            : "Дойди до нужного экрана и нажми «В данные». Сниму его и прикреплю документ."}
        </p>
        {error ? <p className="dash-viewer-error">{error}</p> : null}
        <iframe
          className="dash-viewer-frame"
          title="Превью Stimulsoft"
          src={viewerUrl}
        />
      </div>
    </div>
  );
}
