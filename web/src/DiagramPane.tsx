/** Diagram body: premium Mermaid frame + legend + edit/PNG. */

import { useCallback, useMemo, useRef, useState } from "react";
import {
  DiagramFullscreen,
  type DiagramInfo,
} from "./DiagramFullscreen";
import { DiagramEditSheet } from "./DiagramEditSheet";
import { DiagramVisualEditor } from "./DiagramVisualEditor";
import { DiagramZoomView } from "./DiagramZoomView";
import { isSupportedFlowchartSubset } from "./diagramIr";
import { diagramTypeLabel } from "./diagramLabels";
import { nodeIdsForRole, parseDiagramLegend } from "./diagramLegend";
import { formatMetricChip, parseDiagramMetrics } from "./diagramMetrics";
import {
  downloadDiagramPng,
  slugDiagramFilename,
} from "./downloadDiagramPng";

type Props = {
  diagram: DiagramInfo;
  siblings?: DiagramInfo[];
  onSelectSibling?: (id: string) => void;
  runId?: string | null;
  onDiagramsUpdated?: (diagrams: DiagramInfo[]) => void;
};

export function DiagramPane({
  diagram,
  siblings,
  onSelectSibling,
  runId,
  onDiagramsUpdated,
}: Props) {
  const paneSvgRef = useRef<SVGSVGElement | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);
  const visualOk = isSupportedFlowchartSubset(diagram.mermaid || "");
  const [err, setErr] = useState<string | null>(null);
  const [activeRole, setActiveRole] = useState<string | null>(null);

  const legend = useMemo(
    () => parseDiagramLegend(diagram.mermaid || ""),
    [diagram.mermaid],
  );
  const metrics = useMemo(
    () => parseDiagramMetrics(diagram.mermaid || ""),
    [diagram.mermaid],
  );
  const typeRu = diagramTypeLabel(diagram.type);

  const highlightNodeIds = useMemo(() => {
    if (!activeRole) return null;
    return nodeIdsForRole(diagram.mermaid || "", activeRole);
  }, [activeRole, diagram.mermaid]);

  const onPaneSvg = useCallback((el: SVGSVGElement | null) => {
    paneSvgRef.current = el;
  }, []);

  const openEditor = useCallback(
    (nodeId?: string | null) => {
      setFocusNodeId(nodeId || null);
      setEditOpen(true);
      setErr(null);
    },
    [],
  );

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

  const doApplyEdit = useCallback(
    async (mermaid: string, title: string) => {
      if (!runId) {
        setErr("Нет run_id");
        return;
      }
      setEditBusy(true);
      setErr(null);
      try {
        const res = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/diagrams/${encodeURIComponent(diagram.id)}/edit`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mermaid, title }),
          },
        );
        const data = await res.json();
        if (!res.ok) {
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : data.error || res.statusText,
          );
        }
        const next = Array.isArray(data.diagrams) ? data.diagrams : [];
        onDiagramsUpdated?.(next);
        setEditOpen(false);
        setFocusNodeId(null);
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setEditBusy(false);
      }
    },
    [diagram.id, onDiagramsUpdated, runId],
  );

  return (
    <div className="diagram-pane is-premium">
      {siblings && siblings.length > 1 && onSelectSibling ? (
        <div className="diagram-pane-siblings" role="tablist" aria-label="Схемы">
          {siblings.map((d) => (
            <button
              key={d.id}
              type="button"
              role="tab"
              aria-selected={d.id === diagram.id}
              className={`diagram-pane-sib${d.id === diagram.id ? " is-active" : ""}`}
              onClick={() => {
                setActiveRole(null);
                onSelectSibling(d.id);
              }}
              onDoubleClick={() => {
                onSelectSibling(d.id);
                openEditor(null);
              }}
              title="Двойной клик — открыть редактор"
            >
              {d.title || d.id}
            </button>
          ))}
        </div>
      ) : null}

      <header className="diagram-pane-hero">
        <div className="diagram-pane-hero-text">
          <p className="diagram-pane-eyebrow">
            <span className="diagram-pane-type">{typeRu}</span>
            <span className="diagram-pane-dot" aria-hidden>
              ·
            </span>
            <span>
              {metrics.length > 0 ? "с метриками · PNG" : "Liber · PNG"}
            </span>
          </p>
          <h3 className="diagram-pane-title">{diagram.title}</h3>
        </div>
        <div className="diagram-pane-actions">
          <button
            type="button"
            className="btn ghost"
            disabled={busy}
            onClick={() => openEditor(null)}
          >
            Изменить
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={() => setFullscreen(true)}
          >
            На весь экран
          </button>
          <button
            type="button"
            className="btn primary diagram-pane-png"
            disabled={busy}
            onClick={() => void doDownload(paneSvgRef.current)}
          >
            {busy ? "…" : "Скачать PNG"}
          </button>
        </div>
      </header>

      {err ? (
        <p className="diagram-pane-err" role="alert">
          {err}
        </p>
      ) : null}

      <div className="diagram-pane-canvas">
        <p className="diagram-pane-canvas-hint">
          Двойной клик по блоку — редактор · клик по легенде — подсветка роли
        </p>
        <DiagramZoomView
          source={diagram.mermaid}
          onSvgReady={onPaneSvg}
          className="is-premium"
          highlightNodeIds={highlightNodeIds}
          onNodeDblClick={(id) => openEditor(id)}
        />
      </div>

      {metrics.length > 0 ? (
        <div className="diagram-metrics" aria-label="Метрики из Source">
          <p className="diagram-metrics-eyebrow">Числа на схеме</p>
          <p className="diagram-metrics-hint">
            В блоке — сколько на этапе (шт). На стрелке — доля (%) или отвал
            (шт). Только из Source.
          </p>
          <ul className="diagram-metrics-list">
            {metrics.map((m) => {
              const chip = formatMetricChip(m);
              return (
                <li key={`${m.entity}-${m.metric}-${m.fromEdge ? "e" : "n"}`}>
                  <button
                    type="button"
                    className={`diagram-metrics-chip${m.fromEdge ? " is-edge" : ""}`}
                    title={
                      m.fromEdge
                        ? "Метрика на стрелке"
                        : m.nodeId
                          ? "Открыть блок в редакторе"
                          : undefined
                    }
                    onClick={() => {
                      if (m.nodeId) openEditor(m.nodeId);
                    }}
                  >
                    <span className="diagram-metrics-entity">{chip.entity}</span>
                    <span className="diagram-metrics-value">{chip.metric}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {legend.length > 0 ? (
        <ul className="diagram-legend is-interactive" aria-label="Легенда ролей">
          {legend.map((item) => {
            const on = activeRole === item.role;
            return (
              <li key={item.role}>
                <button
                  type="button"
                  className={`diagram-legend-item${on ? " is-active" : ""}`}
                  aria-pressed={on}
                  title={
                    on
                      ? "Снять подсветку"
                      : `Подсветить: ${item.label}`
                  }
                  onClick={() =>
                    setActiveRole((r) => (r === item.role ? null : item.role))
                  }
                >
                  <span
                    className="diagram-legend-swatch"
                    style={{ background: item.fill }}
                    aria-hidden
                  />
                  <span className="diagram-legend-label">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}

      {fullscreen ? (
        <DiagramFullscreen
          diagram={diagram}
          onClose={() => setFullscreen(false)}
        />
      ) : null}

      {visualOk ? (
        <DiagramVisualEditor
          open={editOpen}
          diagramId={diagram.id}
          title={diagram.title}
          mermaid={diagram.mermaid}
          busy={editBusy}
          error={err}
          focusNodeId={focusNodeId}
          onCancel={() => {
            setEditOpen(false);
            setFocusNodeId(null);
            setErr(null);
          }}
          onSave={(m, t) => void doApplyEdit(m, t)}
        />
      ) : (
        <DiagramEditSheet
          open={editOpen}
          title={diagram.title}
          mermaid={diagram.mermaid}
          busy={editBusy}
          error={err}
          onCancel={() => {
            setEditOpen(false);
            setFocusNodeId(null);
            setErr(null);
          }}
          onApply={(m, t) => void doApplyEdit(m, t)}
        />
      )}
    </div>
  );
}
