/** Portal fullscreen overlay for a Mermaid diagram. */

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DiagramZoomView } from "./DiagramZoomView";
import {
  downloadDiagramPng,
  slugDiagramFilename,
} from "./downloadDiagramPng";

export type DiagramInfo = {
  id: string;
  title: string;
  type?: string;
  mermaid: string;
};

type Props = {
  diagram: DiagramInfo;
  onClose: () => void;
};

export function DiagramFullscreen({ diagram, onClose }: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onSvgReady = useCallback((el: SVGSVGElement | null) => {
    svgRef.current = el;
  }, []);

  const onDownload = useCallback(async () => {
    const el = svgRef.current;
    if (!el) {
      setErr("Схема ещё не готова");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await downloadDiagramPng(
        el,
        slugDiagramFilename(diagram.title, diagram.id),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [diagram.id, diagram.title]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  return createPortal(
    <div
      className="diagram-fullscreen"
      role="dialog"
      aria-modal="true"
      aria-label={diagram.title}
      onClick={onClose}
    >
      <div
        className="diagram-fullscreen-sheet"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="diagram-fullscreen-head">
          <div>
            <h2 className="diagram-fullscreen-title">{diagram.title}</h2>
            <p className="diagram-fullscreen-sub">
              Только в Liber · не в PDF
            </p>
          </div>
          <div className="diagram-fullscreen-actions">
            <button
              type="button"
              className="btn ghost"
              disabled={busy}
              onClick={() => void onDownload()}
            >
              {busy ? "…" : "Скачать PNG"}
            </button>
            <button
              type="button"
              className="diagram-fullscreen-close"
              aria-label="Закрыть"
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </header>
        {err ? (
          <p className="diagram-pane-err" role="alert" style={{ margin: "0 1rem" }}>
            {err}
          </p>
        ) : null}
        <div className="diagram-fullscreen-body">
          <DiagramZoomView source={diagram.mermaid} onSvgReady={onSvgReady} />
        </div>
      </div>
    </div>,
    document.body,
  );
}
