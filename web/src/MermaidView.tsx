/** Render Mermaid source → SVG (Liber soft-premium theme). */

import { useEffect, useId, useRef, useState } from "react";
import type { Mermaid } from "mermaid";
import {
  applyMermaidRoleHighlight,
  mermaidNodeIdFromElement,
} from "./mermaidSvgInteract";
import { repairMermaidSource } from "./repairMermaidSource";
import { softenMermaidSvg } from "./softenMermaidSvg";

type Props = {
  source: string;
  className?: string;
  onSvgReady?: (svg: SVGSVGElement | null) => void;
  onError?: (err: string | null) => void;
  /** Highlight these Mermaid node ids; others dim. null = clear. */
  highlightNodeIds?: Set<string> | null;
  /** Double-click a flowchart node → id */
  onNodeDblClick?: (nodeId: string) => void;
};

let mermaidReady = false;
let mermaidMod: Mermaid | null = null;

async function loadMermaid(): Promise<Mermaid> {
  if (mermaidMod) return mermaidMod;
  const mod = await import("mermaid");
  const mermaid = mod.default;
  if (!mermaidReady) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      // Match Liber visual editor: soft curves, not sharp orthogonal edges.
      flowchart: {
        curve: "basis",
        padding: 18,
        nodeSpacing: 48,
        rankSpacing: 52,
        htmlLabels: true,
        useMaxWidth: true,
      },
      themeVariables: {
        primaryColor: "#dce8df",
        primaryTextColor: "#1a2e22",
        primaryBorderColor: "#6b8f76",
        secondaryColor: "#f4f7f4",
        tertiaryColor: "#eef3ef",
        lineColor: "#5a7a64",
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontSize: "15px",
        nodeBorder: "#6b8f76",
        mainBkg: "#eef3ef",
        clusterBkg: "#f4f7f4",
        edgeLabelBackground: "#f7faf7",
      },
    });
    mermaidReady = true;
  }
  mermaidMod = mermaid;
  return mermaid;
}

export function MermaidView({
  source,
  className,
  onSvgReady,
  onError,
  highlightNodeIds = null,
  onNodeDblClick,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const onReadyRef = useRef(onSvgReady);
  onReadyRef.current = onSvgReady;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const dblRef = useRef(onNodeDblClick);
  dblRef.current = onNodeDblClick;
  const reactId = useId().replace(/:/g, "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    const host = hostRef.current;
    if (!host) return;
    const src = repairMermaidSource(source || "");
    setLoading(true);
    if (!src) {
      host.innerHTML = "";
      svgRef.current = null;
      onReadyRef.current?.(null);
      setError("Пустая схема");
      onErrorRef.current?.("Пустая схема");
      setLoading(false);
      return;
    }
    const renderId = `mmd_${reactId}_${Math.random().toString(36).slice(2, 8)}`;
    (async () => {
      try {
        const mermaid = await loadMermaid();
        if (cancelled || !hostRef.current) return;
        const { svg } = await mermaid.render(renderId, src);
        if (cancelled || !hostRef.current) return;
        hostRef.current.innerHTML = svg;
        setError(null);
        onErrorRef.current?.(null);
        const el = hostRef.current.querySelector("svg");
        svgRef.current = el;
        if (el) {
          softenMermaidSvg(el);
          el.querySelectorAll("g.node").forEach((g) => {
            (g as SVGElement).style.cursor = dblRef.current
              ? "pointer"
              : "";
          });
        }
        onReadyRef.current?.(el);
        applyMermaidRoleHighlight(el, highlightNodeIds);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        onErrorRef.current?.(msg);
        if (hostRef.current) hostRef.current.innerHTML = "";
        svgRef.current = null;
        onReadyRef.current?.(null);
        const stray =
          document.getElementById("d" + renderId) ||
          document.getElementById(renderId);
        if (stray) stray.remove();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source, reactId]); // eslint-disable-line react-hooks/exhaustive-deps -- highlight applied below

  useEffect(() => {
    applyMermaidRoleHighlight(svgRef.current, highlightNodeIds ?? null);
  }, [highlightNodeIds]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !onNodeDblClick) return;
    const onDbl = (e: MouseEvent) => {
      const id = mermaidNodeIdFromElement(e.target as Element);
      if (id) {
        e.preventDefault();
        e.stopPropagation();
        dblRef.current?.(id);
      }
    };
    host.addEventListener("dblclick", onDbl);
    return () => host.removeEventListener("dblclick", onDbl);
  }, [onNodeDblClick, loading, source]);

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
          {error !== "Пустая схема" ? (
            <p className="mermaid-view-error-detail">{error}</p>
          ) : null}
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
