/** Zoom / pan wrapper around Mermaid SVG for Liber Schema tab. */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { MermaidView } from "./MermaidView";

const MIN = 0.5;
const MAX = 2.75;
const STEP = 0.15;

type Props = {
  source: string;
  onSvgReady?: (svg: SVGSVGElement | null) => void;
  className?: string;
};

export function DiagramZoomView({ source, onSvgReady, className }: Props) {
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{
    x: number;
    y: number;
    panX: number;
    panY: number;
  } | null>(null);

  useEffect(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }, [source]);

  const zoomBy = useCallback((delta: number) => {
    setScale((s) => Math.min(MAX, Math.max(MIN, Math.round((s + delta) * 100) / 100)));
  }, []);

  const fit = useCallback(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const onWheel = useCallback((e: ReactWheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      zoomBy(e.deltaY > 0 ? -STEP : STEP);
      return;
    }
    // Trackpad pinch often sends ctrl; plain wheel pans vertically via native scroll.
  }, [zoomBy]);

  const onPointerDown = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      if (e.button !== 0 || scale <= 1.01) return;
      e.currentTarget.setPointerCapture(e.pointerId);
      dragRef.current = {
        x: e.clientX,
        y: e.clientY,
        panX: pan.x,
        panY: pan.y,
      };
    },
    [pan.x, pan.y, scale],
  );

  const onPointerMove = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    const d = dragRef.current;
    if (!d) return;
    setPan({
      x: d.panX + (e.clientX - d.x),
      y: d.panY + (e.clientY - d.y),
    });
  }, []);

  const onPointerUp = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
    if (dragRef.current) {
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        /* already released */
      }
    }
    dragRef.current = null;
  }, []);

  return (
    <div className={`diagram-zoom${className ? ` ${className}` : ""}`}>
      <div className="diagram-zoom-bar" role="toolbar" aria-label="Масштаб схемы">
        <button
          type="button"
          className="diagram-zoom-btn"
          aria-label="Уменьшить"
          onClick={() => zoomBy(-STEP)}
          disabled={scale <= MIN}
        >
          −
        </button>
        <button
          type="button"
          className="diagram-zoom-btn"
          aria-label="Вписать"
          onClick={fit}
        >
          {Math.round(scale * 100)}%
        </button>
        <button
          type="button"
          className="diagram-zoom-btn"
          aria-label="Увеличить"
          onClick={() => zoomBy(STEP)}
          disabled={scale >= MAX}
        >
          +
        </button>
        <span className="diagram-zoom-hint">Ctrl+колёсико · перетаскивание при zoom</span>
      </div>
      <div
        className={`diagram-zoom-viewport${scale > 1.01 ? " is-pannable" : ""}`}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className="diagram-zoom-stage"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
          }}
        >
          <MermaidView source={source} onSvgReady={onSvgReady} />
        </div>
      </div>
    </div>
  );
}
