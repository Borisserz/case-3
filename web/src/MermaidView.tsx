/** Render Mermaid source → SVG (Liber soft-premium theme). */

import { useEffect, useId, useRef, useState } from "react";
import mermaid from "mermaid";

type Props = {
  source: string;
  className?: string;
  onSvgReady?: (svg: SVGSVGElement | null) => void;
};

let mermaidReady = false;

function ensureMermaid() {
  if (mermaidReady) return;
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "base",
    themeVariables: {
      primaryColor: "#dce8df",
      primaryTextColor: "#1a2e22",
      primaryBorderColor: "#6b8f76",
      secondaryColor: "#f4f7f4",
      tertiaryColor: "#eef3ef",
      lineColor: "#5a7a64",
      fontFamily: "Georgia, 'Times New Roman', serif",
      fontSize: "15px",
    },
  });
  mermaidReady = true;
}

export function MermaidView({ source, className, onSvgReady }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const onReadyRef = useRef(onSvgReady);
  onReadyRef.current = onSvgReady;
  const reactId = useId().replace(/:/g, "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [rawOpen, setRawOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const host = hostRef.current;
    if (!host) return;
    const src = (source || "").trim();
    setLoading(true);
    if (!src) {
      host.innerHTML = "";
      onReadyRef.current?.(null);
      setError("Пустая схема");
      setLoading(false);
      return;
    }
    ensureMermaid();
    const renderId = `mmd_${reactId}_${Math.random().toString(36).slice(2, 8)}`;
    (async () => {
      try {
        const { svg } = await mermaid.render(renderId, src);
        if (cancelled || !hostRef.current) return;
        hostRef.current.innerHTML = svg;
        setError(null);
        const el = hostRef.current.querySelector("svg");
        onReadyRef.current?.(el);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        if (hostRef.current) hostRef.current.innerHTML = "";
        onReadyRef.current?.(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source, reactId]);

  return (
    <div className={`mermaid-view${className ? ` ${className}` : ""}`}>
      {loading && !error ? (
        <p className="mermaid-view-loading" aria-live="polite">
          Рисую схему…
        </p>
      ) : null}
      {error ? (
        <div className="mermaid-view-error" role="alert">
          <p>Не удалось отрисовать схему</p>
          <button
            type="button"
            className="btn ghost"
            onClick={() => setRawOpen((v) => !v)}
          >
            {rawOpen ? "Скрыть исходник" : "Показать Mermaid"}
          </button>
          {rawOpen ? <pre className="mermaid-view-raw">{source}</pre> : null}
        </div>
      ) : null}
      <div
        ref={hostRef}
        className={`mermaid-view-svg${loading && !error ? " is-loading" : ""}`}
        aria-hidden={Boolean(error) || loading}
      />
    </div>
  );
}
