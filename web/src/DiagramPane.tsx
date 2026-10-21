/** Diagram body: Mermaid + toolbar (fullscreen / PNG) + zoom. */

import { useCallback, useRef, useState } from "react";
import {
  DiagramFullscreen,
  type DiagramInfo,
} from "./DiagramFullscreen";
import { DiagramZoomView } from "./DiagramZoomView";
import {
  downloadDiagramPng,
  slugDiagramFilename,
} from "./downloadDiagramPng";

type Props = {
  diagram: DiagramInfo;
  /** When several diagrams exist — chip switcher inside the pane. */
  siblings?: DiagramInfo[];
  onSelectSibling?: (id: string) => void;
};

export function DiagramPane({ diagram, siblings, onSelectSibling }: Props) {
  const paneSvgRef = useRef<SVGSVGElement | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onPaneSvg = useCallback((el: SVGSVGElement | null) => {
    paneSvgRef.current = el;
  }, []);

  const doDownload = useCallback(
    async (el: SVGSVGElement | null) => {
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
    },
    [diagram.id, diagram.title],
  );

  return (
    <div className="diagram-pane">
      <p className="diagram-pane-liber-hint">
        Только в Liber · не в PDF · можно скачать PNG
      </p>
      {siblings && siblings.length > 1 && onSelectSibling ? (
        <div className="diagram-pane-siblings" role="tablist" aria-label="Схемы">
          {siblings.map((d) => (
            <button
              key={d.id}
              type="button"
              role="tab"
              aria-selected={d.id === diagram.id}
              className={`diagram-pane-sib${d.id === diagram.id ? " is-active" : ""}`}
              onClick={() => onSelectSibling(d.id)}
            >
              {d.title || d.id}
            </button>
          ))}
        </div>
      ) : null}
      <div className="diagram-pane-toolbar">
        <h3 className="diagram-pane-title">{diagram.title}</h3>
        <div className="diagram-pane-actions">
          <button
            type="button"
            className="btn ghost"
            onClick={() => setFullscreen(true)}
          >
            На весь экран
          </button>
          <button
            type="button"
            className="btn ghost"
            disabled={busy}
            onClick={() => void doDownload(paneSvgRef.current)}
          >
            {busy ? "…" : "Скачать PNG"}
          </button>
        </div>
      </div>
      {err ? (
        <p className="diagram-pane-err" role="alert">
          {err}
        </p>
      ) : null}
      <div className="diagram-pane-canvas">
        <DiagramZoomView source={diagram.mermaid} onSvgReady={onPaneSvg} />
      </div>
      {fullscreen ? (
        <DiagramFullscreen
          diagram={diagram}
          onClose={() => setFullscreen(false)}
        />
      ) : null}
    </div>
  );
}
