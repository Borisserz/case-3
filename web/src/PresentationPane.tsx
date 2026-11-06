/** Liber deck viewer: Julius-like live twin + filmstrip + fullscreen. */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import {
  ChartEditSheet,
  type ChartEditRequest,
  type PaletteInfo,
} from "./ChartEditSheet";
import { DeckCanvas, type DeckMediaKind } from "./DeckCanvas";
import { DeckGallery } from "./DeckGallery";
import type { DeckIR, DeckSlide } from "./deckTypes";
import {
  parseEditHistory,
  type EditHistoryDesc,
} from "./domain/reportEditMode";
import {
  ImageEditModal,
  type ImageEditRequest,
} from "./ImageEditModal";
import { DiagramVisualEditor } from "./DiagramVisualEditor";
import type { DiagramResult } from "./domain/liberTypes";
import { PresentationFullscreen } from "./PresentationFullscreen";

/** Survive tab switches: PresentationPane unmounts on Preview/PDF. */
const slidesTimerStartedAt = new Map<string, number>();

function useElapsedSeconds(active: boolean, runId: string): number {
  const [sec, setSec] = useState(() => {
    if (!active || !runId) return 0;
    const t0 = slidesTimerStartedAt.get(runId);
    return t0 ? Math.floor((Date.now() - t0) / 1000) : 0;
  });
  useEffect(() => {
    if (!active || !runId) {
      if (runId) slidesTimerStartedAt.delete(runId);
      setSec(0);
      return;
    }
    let t0 = slidesTimerStartedAt.get(runId);
    if (t0 == null) {
      t0 = Date.now();
      slidesTimerStartedAt.set(runId, t0);
    }
    const tick = () => setSec(Math.floor((Date.now() - t0!) / 1000));
    tick();
    const id = window.setInterval(tick, 500);
    return () => window.clearInterval(id);
  }, [active, runId]);
  return sec;
}

type Props = {
  runId: string;
  slidePngs: string[];
  deck?: DeckIR | null;
  status?: string | null;
  stage?: string | null;
  error?: string | null;
  downloads?: Record<string, string>;
  deckPdfMode?: string | null;
  making?: boolean;
  onDeckUpdated?: (
    deck: DeckIR,
    slidePngs: string[],
    extras?: { downloads?: Record<string, string>; diagrams?: DiagramResult[] },
  ) => void;
  palettes?: PaletteInfo[];
  catalogTypes?: string[];
  defaultPalette?: string;
  editingFigureId?: string | null;
  editError?: string | null;
  editErrorFigureId?: string | null;
  editHistory?: EditHistoryDesc | null;
  onEditFigure?: (req: ChartEditRequest) => Promise<boolean> | boolean;
  onEditImage?: (req: ImageEditRequest) => Promise<boolean> | boolean;
  /** Mermaid specs for dia_* slides. Save writes figures.json, then rebuilds the deck. */
  diagrams?: DiagramResult[];
  onHistoryUndo?: () => void | Promise<void>;
  onHistoryRedo?: () => void | Promise<void>;
  onClearEditHistory?: () => void | Promise<void>;
  onEditHistory?: (h: EditHistoryDesc) => void;
  /** Controlled edit mode when chrome lives in ArtifactRail. */
  editing?: boolean;
  onEditingChange?: (on: boolean) => void;
  /** Hide in-pane Edit / history when rail owns chrome. */
  showEditChrome?: boolean;
  /** Notify parent that twin/PPTX need flush on Готово. */
  onDocsDirtyChange?: (dirty: boolean) => void;
};

export function PresentationPane({
  runId,
  slidePngs,
  deck: deckProp = null,
  status,
  stage,
  error,
  downloads: _downloads,
  deckPdfMode: _deckPdfMode = null,
  making = false,
  onDeckUpdated,
  palettes = [],
  catalogTypes = [],
  defaultPalette = "atelier",
  editingFigureId = null,
  editError = null,
  editErrorFigureId = null,
  editHistory = null,
  onEditFigure,
  onEditImage,
  diagrams: diagramsProp,
  onHistoryUndo,
  onHistoryRedo,
  onClearEditHistory,
  onEditHistory,
  editing: editingProp,
  onEditingChange,
  showEditChrome = true,
  onDocsDirtyChange,
}: Props) {
  const reduce = useReducedMotion();
  const [idx, setIdx] = useState(0);
  const [dir, setDir] = useState(0);
  const [full, setFull] = useState(false);
  /**
   * Julius gallery contract (lock):
   * - mount / run change → grid, editing=false
   * - gallery thumbnail click → Slide + editing=false (never Edit)
   * - Edit only via Edit segment or E key
   * - leaving Edit → Slide turns editing off
   */
  const [editingLocal, setEditingLocal] = useState(false);
  const controlledEdit = editingProp !== undefined;
  const editing = controlledEdit ? Boolean(editingProp) : editingLocal;
  const setEditing = useCallback(
    (on: boolean) => {
      if (!controlledEdit) setEditingLocal(on);
      onEditingChange?.(on);
    },
    [controlledEdit, onEditingChange],
  );
  const [view, setView] = useState<"grid" | "slide">("grid");
  const [deck, setDeck] = useState<DeckIR | null>(deckProp);
  const [saving, setSaving] = useState(false);
  const [saveFlash, setSaveFlash] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [docsDirty, setDocsDirty] = useState(false);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [openMediaId, setOpenMediaId] = useState<string | null>(null);
  const [openMediaKind, setOpenMediaKind] = useState<DeckMediaKind | null>(
    null,
  );
  const [diagrams, setDiagrams] = useState<DiagramResult[]>(diagramsProp ?? []);
  const [diagramError, setDiagramError] = useState<string | null>(null);
  const [mediaVersion, setMediaVersion] = useState(0);
  const [chartIndex, setChartIndex] = useState<
    Record<string, { type?: string; palette?: string; style_user?: boolean }>
  >({});
  const [chartPreview, setChartPreview] = useState<string | null>(null);
  const n = Math.max(slidePngs.length, deck?.slides?.length || 0);
  const safeIdx = n ? Math.min(idx, n - 1) : 0;
  const currentPng = slidePngs.length ? slidePngs[safeIdx] : null;
  const live = Boolean(deck?.slides?.length);
  const slideTitle =
    deck?.slides?.[safeIdx]?.title ||
    (n ? `Слайд ${safeIdx + 1}` : "Презентация");

  useEffect(() => {
    setDeck(deckProp);
  }, [deckProp]);

  useEffect(() => {
    setIdx(0);
    setDir(0);
    setEditing(false);
    setView("grid");
    setSaveError(null);
    setDocsDirty(false);
    onDocsDirtyChange?.(false);
    setOpenMediaId(null);
    setOpenMediaKind(null);
    setChartPreview(null);
    setChartIndex({});
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset on run only
  }, [runId]);

  useEffect(() => {
    setDiagrams(diagramsProp ?? []);
  }, [diagramsProp]);

  useEffect(() => {
    let cancelled = false;
    void fetch(`/api/runs/${encodeURIComponent(runId)}/slides`)
      .then((r) => r.json())
      .then((body: { charts?: Record<string, { type?: string; palette?: string }> }) => {
        if (!cancelled && body?.charts && typeof body.charts === "object") {
          setChartIndex(body.charts);
        }
      })
      .catch(() => {
        /* sheet falls back to the default palette */
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const refreshSlidesNow = useCallback(async () => {
    const g = await fetch(`/api/runs/${encodeURIComponent(runId)}/slides`);
    const gBody = await g.json().catch(() => ({}));
    if (!g.ok) return;
    const pngs = Array.isArray(gBody.slide_pngs)
      ? (gBody.slide_pngs as string[])
      : [];
    if (gBody.deck) setDeck(gBody.deck as DeckIR);
    if (gBody.charts && typeof gBody.charts === "object") {
      setChartIndex(gBody.charts);
    }
    if (pngs.length || gBody.deck) {
      const dl =
        gBody.downloads && typeof gBody.downloads === "object"
          ? (gBody.downloads as Record<string, string>)
          : undefined;
      onDeckUpdated?.(gBody.deck as DeckIR, pngs, {
        downloads: dl,
        diagrams,
      });
    }
    setMediaVersion(Date.now());
  }, [diagrams, onDeckUpdated, runId]);

  const historyUndo = useCallback(async () => {
    await onHistoryUndo?.();
    await refreshSlidesNow();
  }, [onHistoryUndo, refreshSlidesNow]);

  const historyRedo = useCallback(async () => {
    await onHistoryRedo?.();
    await refreshSlidesNow();
  }, [onHistoryRedo, refreshSlidesNow]);

  // Safety net: rail opened with pptx downloads but empty twin/deck (old status).
  useEffect(() => {
    if (deckProp?.slides?.length) return;
    if (status !== "ok" && slidePngs.length === 0) return;
    let cancelled = false;
    void (async () => {
      try {
        const g = await fetch(`/api/runs/${encodeURIComponent(runId)}/slides`);
        const gBody = await g.json().catch(() => ({}));
        if (cancelled || !g.ok) return;
        const pngs = Array.isArray(gBody.slide_pngs)
          ? (gBody.slide_pngs as string[])
          : [];
        if (gBody.deck) setDeck(gBody.deck as DeckIR);
        if (gBody.charts && typeof gBody.charts === "object") {
          setChartIndex(gBody.charts);
        }
        if (pngs.length || gBody.deck) {
          onDeckUpdated?.(gBody.deck as DeckIR, pngs);
        }
      } catch {
        /* keep empty */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId, status, slidePngs.length, deckProp, onDeckUpdated]);

  useEffect(() => {
    const el = document.querySelector(
      `.presentation-thumb:nth-child(${safeIdx + 1})`,
    );
    el?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  }, [safeIdx]);

  const go = useCallback(
    (delta: number) => {
      if (!n) return;
      setDir(delta);
      setIdx((i) => (i + delta + n) % n);
    },
    [n],
  );

  const waitPatchRebuild = useCallback(
    async (optimisticDeck?: DeckIR) => {
      if (optimisticDeck) setDeck(optimisticDeck);
      let done = false;
      for (let i = 0; i < 40; i++) {
        await new Promise((res) => setTimeout(res, 500));
        const g = await fetch(`/api/runs/${encodeURIComponent(runId)}/slides`);
        const gBody = await g.json().catch(() => ({}));
        if (gBody.slides_status === "ok") {
          const pngs = (gBody.slide_pngs as string[]) || [];
          if (gBody.deck) setDeck(gBody.deck as DeckIR);
          const dl =
            gBody.downloads && typeof gBody.downloads === "object"
              ? (gBody.downloads as Record<string, string>)
              : undefined;
          onDeckUpdated?.(gBody.deck as DeckIR, pngs, {
            downloads: dl,
            diagrams,
          });
          setMediaVersion(Date.now());
          setSaveFlash(true);
          window.setTimeout(() => setSaveFlash(false), 1600);
          done = true;
          break;
        }
        if (gBody.slides_status === "cancelled") {
          throw new Error("Остановлено");
        }
        if (gBody.slides_status === "error") {
          throw new Error(
            String(gBody.slides_error || "Не удалось сохранить слайды"),
          );
        }
      }
      if (!done) {
        throw new Error("Сохранение заняло слишком долго — попробуйте ещё раз");
      }
    },
    [diagrams, onDeckUpdated, runId],
  );

  const markDirty = useCallback(() => {
    setDocsDirty(true);
    onDocsDirtyChange?.(true);
  }, [onDocsDirtyChange]);

  const flushDeckRebuild = useCallback(async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const r = await fetch(
        `/api/runs/${encodeURIComponent(runId)}/slides/rebuild`,
        { method: "POST" },
      );
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        throw new Error(
          typeof body.detail === "string" ? body.detail : `rebuild ${r.status}`,
        );
      }
      await waitPatchRebuild(body.deck as DeckIR | undefined);
      setDocsDirty(false);
      onDocsDirtyChange?.(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
      throw err;
    } finally {
      setSaving(false);
    }
  }, [onDocsDirtyChange, runId, waitPatchRebuild]);

  const leaveEdit = useCallback(async () => {
    try {
      if (docsDirty) await flushDeckRebuild();
      void onClearEditHistory?.();
      setOpenMediaId(null);
      setOpenMediaKind(null);
      setChartPreview(null);
      setEditing(false);
    } catch {
      /* stay in edit — error already shown */
    }
  }, [docsDirty, flushDeckRebuild, onClearEditHistory, setEditing]);

  useEffect(() => {
    if (full) return;
    const onKey = (e: KeyboardEvent) => {
      if (editing && e.target instanceof HTMLElement && e.target.isContentEditable)
        return;
      if (e.key === "ArrowLeft") go(-1);
      if (e.key === "ArrowRight") {
        e.preventDefault();
        go(1);
      }
      if (e.metaKey || e.ctrlKey || e.altKey) {
        // fall through to undo/redo below; no plain-letter shortcuts with modifiers
      } else if ((e.key === "g" || e.key === "G") && slidePngs.length > 0) {
        setView("grid");
        if (editing) void leaveEdit();
        return;
      } else if (e.key === "s" || e.key === "S") {
        setView("slide");
        if (editing) void leaveEdit();
        return;
      }
      if (e.key === "f" || e.key === "F") setFull(true);
      if (e.key === "e" || e.key === "E") {
        setView("slide");
        if (editing) void leaveEdit();
        else setEditing(true);
      }
      if (editing && (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) void historyRedo();
        else void historyUndo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [full, go, editing, leaveEdit, historyUndo, historyRedo, setEditing, slidePngs.length]);

  const patchSlides = useCallback(
    async (slides: (Partial<DeckSlide> & { id: string })[]) => {
      setSaving(true);
      setSaveError(null);
      try {
        const r = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/slides/ir?rebuild=0`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slides }),
          },
        );
        const body = await r.json().catch(() => ({}));
        if (!r.ok) {
          throw new Error(
            typeof body.detail === "string" ? body.detail : `patch ${r.status}`,
          );
        }
        if (body.deck) setDeck(body.deck as DeckIR);
        if (body.undo) {
          onEditHistory?.(
            parseEditHistory(
              body.undo as Parameters<typeof parseEditHistory>[0],
            ),
          );
        }
        markDirty();
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    },
    [markDirty, onEditHistory, runId],
  );

  const onMediaClick = useCallback((id: string, kind: DeckMediaKind) => {
    setOpenMediaId(id);
    setOpenMediaKind(kind);
  }, []);

  const closeMediaSheet = useCallback(() => {
    setOpenMediaId(null);
    setOpenMediaKind(null);
    setChartPreview(null);
  }, []);

  const submitChart = useCallback(
    async (req: ChartEditRequest) => {
      const ok = await onEditFigure?.(req);
      if (ok) {
        // Chart path already soft-rebuilds twin+PPTX; refresh film cache-bust.
        await refreshSlidesNow();
        closeMediaSheet();
      }
    },
    [closeMediaSheet, onEditFigure, refreshSlidesNow],
  );

  const submitImage = useCallback(
    async (req: ImageEditRequest) => {
      const ok = await onEditImage?.(req);
      if (ok) {
        await refreshSlidesNow();
        closeMediaSheet();
      }
    },
    [closeMediaSheet, onEditImage, refreshSlidesNow],
  );

  const openDiagram = diagrams.find((d) => d.id === openMediaId) || null;

  useEffect(() => {
    if (openMediaKind !== "diagram" || !openMediaId || openDiagram) return;
    let cancelled = false;
    void fetch(`/api/runs/${encodeURIComponent(runId)}/status`)
      .then((r) => r.json())
      .then((body: { diagrams?: DiagramResult[] }) => {
        if (cancelled || !Array.isArray(body.diagrams)) return;
        setDiagrams(body.diagrams);
      })
      .catch(() => {
        if (!cancelled) setDiagramError("Не удалось открыть схему");
      });
    return () => {
      cancelled = true;
    };
  }, [openDiagram, openMediaId, openMediaKind, runId]);

  const saveDiagram = useCallback(
    async (mermaid: string, title: string) => {
      if (!openMediaId) return;
      setSaving(true);
      setDiagramError(null);
      setSaveError(null);
      try {
        const res = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/diagrams/${encodeURIComponent(openMediaId)}/edit`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mermaid, title }),
          },
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(
            typeof data.detail === "string" ? data.detail : `edit ${res.status}`,
          );
        }
        if (data.diagram && typeof data.diagram === "object") {
          const saved = data.diagram as DiagramResult;
          setDiagrams((prev) => {
            const rest = prev.filter((d) => d.id !== saved.id);
            return [...rest, saved];
          });
        }
        const reb = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/slides/rebuild`,
          { method: "POST" },
        );
        if (!reb.ok) {
          const body = await reb.json().catch(() => ({}));
          throw new Error(
            typeof body.detail === "string"
              ? body.detail
              : `rebuild ${reb.status}`,
          );
        }
        await waitPatchRebuild();
        closeMediaSheet();
      } catch (err) {
        setDiagramError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    },
    [closeMediaSheet, openMediaId, runId, waitPatchRebuild],
  );

  const structureOp = useCallback(
    async (payload: {
      op: "reorder" | "duplicate" | "delete";
      id?: string;
      order?: string[];
    }) => {
      if (!deck?.slides?.length) {
        setSaveError("Нет IR деки — соберите презентацию");
        return;
      }
      setSaving(true);
      setSaveError(null);
      try {
        const r = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/slides/structure`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          },
        );
        const body = await r.json().catch(() => ({}));
        if (!r.ok) {
          throw new Error(
            typeof body.detail === "string"
              ? body.detail
              : `structure ${r.status}`,
          );
        }
        const next = body.deck as DeckIR | undefined;
        if (next?.slides && payload.op === "delete") {
          setIdx((i) => Math.min(i, Math.max(0, next.slides.length - 1)));
        }
        if (next?.slides && payload.op === "duplicate" && payload.id) {
          const at = next.slides.findIndex((s) => s.id === payload.id);
          if (at >= 0) setIdx(Math.min(at + 1, next.slides.length - 1));
        }
        if (body.undo) {
          onEditHistory?.(
            parseEditHistory(
              body.undo as Parameters<typeof parseEditHistory>[0],
            ),
          );
        }
        await waitPatchRebuild(next);
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    },
    [deck, onEditHistory, runId, waitPatchRebuild],
  );

  const onReorderIndices = useCallback(
    (from: number, to: number) => {
      if (!deck?.slides?.length || from === to || saving) return;
      const ids = deck.slides.map((s) => s.id);
      if (from < 0 || to < 0 || from >= ids.length || to >= ids.length) return;
      const next = [...ids];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      setIdx(to);
      void structureOp({ op: "reorder", order: next });
    },
    [deck, saving, structureOp],
  );

  const pending =
    status === "running" ||
    status === "queued" ||
    status === "starting" ||
    making;
  const elapsed = useElapsedSeconds(pending, runId);
  const elapsedLabel = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  if (pending) {
    const stageLabel = (() => {
      switch (stage) {
        case "patch":
          return "Сохраняю правки в PPTX";
        case "queued":
          return "В очереди";
        case "llm":
        case "llm_retry":
        case "plan":
        case "ir":
          return "Пишу структуру слайдов";
        case "diagrams":
        case "media":
        case "charts":
          return "Готовлю графики и медиа";
        case "render":
          return "Рисую twin-превью";
        case "pptx":
        case "pdf":
          return "Собираю editable PPTX";
        default:
          return making && !stage ? "Запускаю сборку" : "Собираю презентацию";
      }
    })();
    const stepKey =
      stage === "llm" ||
      stage === "llm_retry" ||
      stage === "plan" ||
      stage === "ir" ||
      stage === "queued" ||
      !stage
        ? "ir"
        : stage === "diagrams" || stage === "media" || stage === "charts"
          ? "media"
          : stage === "render"
            ? "render"
            : "pptx";
    const stages = ["ir", "media", "render", "pptx"] as const;
    const stageIdx = Math.max(0, stages.indexOf(stepKey));
    return (
      <div className="presentation-pane is-pending">
        <div className="presentation-pending-card" aria-busy="true">
          <div className="presentation-pending-pulse" />
          <p className="presentation-pending">
            <span className="presentation-pending-working" aria-live="polite">
              Собираю
              <span className="presentation-pending-time">{elapsedLabel}</span>
            </span>
            <span className="presentation-pending-stage">{stageLabel}</span>
          </p>
          <ol className="presentation-pending-steps" aria-label="Этапы">
            {["IR", "Media", "Twin", "PPTX"].map((label, i) => (
              <li
                key={label}
                className={
                  i < stageIdx ? "is-done" : i === stageIdx ? "is-now" : ""
                }
              >
                {label}
              </li>
            ))}
          </ol>
          <p className="presentation-pending-hint">
            Обычно полторы–две минуты. Вкладка остаётся открытой — превью
            появится, когда готово.
          </p>
        </div>
      </div>
    );
  }

  if (status === "cancelled") {
    return (
      <div className="presentation-pane is-cancelled">
        <p className="presentation-empty-kicker">Презентация</p>
        <h3 className="presentation-empty-title">Остановлено</h3>
        <p className="presentation-empty-copy">
          Сборку прервали. Отправьте запрос снова в режиме Презентация.
        </p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="presentation-pane is-error">
        <p className="presentation-error">{error || "Не удалось собрать деку"}</p>
        <p className="presentation-empty-copy">
          Отправьте запрос снова — сборка стартует сама, без кнопки.
        </p>
      </div>
    );
  }

  if (!n && !live) {
    // No «Сделать презентацию» — deck kicks on send; wait or open chat cards.
    return (
      <div className="presentation-pane is-empty">
        <p className="presentation-empty-kicker">Презентация</p>
        <h3 className="presentation-empty-title">Превью появится здесь</h3>
        <p className="presentation-empty-copy">
          После сборки в чате два файла — PPTX и PDF. Нажмите карточку:
          сразу twin / film, без «Собрать».
        </p>
      </div>
    );
  }

  const slideVariants = reduce
    ? { enter: { opacity: 1 }, center: { opacity: 1 }, exit: { opacity: 1 } }
    : {
        enter: (d: number) => ({
          x: d >= 0 ? 28 : -28,
          opacity: 0,
          scale: 0.985,
        }),
        center: { x: 0, opacity: 1, scale: 1 },
        exit: (d: number) => ({
          x: d >= 0 ? -22 : 22,
          opacity: 0,
          scale: 0.985,
        }),
      };

  return (
    <div
      className={`presentation-pane is-ready${editing ? " is-editing" : ""}${
        openMediaId ? " has-media-sheet" : ""
      }`}
    >
      <header className="presentation-chrome">
        <div className="presentation-chrome-left">
          <span className="presentation-chrome-kicker">
            {editing && view === "slide" ? "Редактирование" : "Презентация"}
          </span>
          <span className="presentation-chrome-title" title={slideTitle}>
            {slideTitle}
          </span>
        </div>
        <div className="presentation-chrome-tools">
          <div className="presentation-seg" role="group" aria-label="Режим">
            {slidePngs.length > 0 ? (
              <button
                type="button"
                className={`presentation-seg-btn${view === "grid" ? " is-on" : ""}`}
                onClick={() => {
                  setView("grid");
                  if (editing) void leaveEdit();
                  else setEditing(false);
                }}
                title="Сетка слайдов (G)"
              >
                Сетка
              </button>
            ) : null}
            <button
              type="button"
              className={`presentation-seg-btn${view === "slide" && !editing ? " is-on" : ""}`}
              onClick={() => {
                setView("slide");
                if (editing) void leaveEdit();
                else setEditing(false);
              }}
              title="Просмотр слайда (S)"
            >
              Слайд
            </button>
            {live && showEditChrome ? (
              <button
                type="button"
                className={`presentation-seg-btn presentation-seg-edit${
                  view === "slide" && editing ? " is-on" : ""
                }`}
                disabled={saving}
                onClick={() => {
                  if (editing) {
                    void leaveEdit();
                    setView("slide");
                  } else {
                    setView("slide");
                    setEditing(true);
                  }
                }}
                title={editing ? "Завершить редактирование (E)" : "Редактировать слайд (E)"}
              >
                {saving && editing
                  ? "Сохраняю…"
                  : editing
                    ? "Готово"
                    : "Редактировать"}
              </button>
            ) : null}
          </div>
          {editing && showEditChrome ? (
            <div className="presentation-history" role="group" aria-label="История">
              <button
                type="button"
                className="presentation-history-btn"
                aria-label="Отменить"
                title="Отменить (⌘Z)"
                disabled={!editHistory?.canUndo || saving}
                onClick={() => void historyUndo()}
              >
                ←
              </button>
              <button
                type="button"
                className="presentation-history-btn"
                aria-label="Вернуть"
                title="Вернуть (⌘⇧Z)"
                disabled={!editHistory?.canRedo || saving}
                onClick={() => void historyRedo()}
              >
                →
              </button>
            </div>
          ) : null}
          <button
            type="button"
            className="presentation-tool"
            onClick={() => setFull(true)}
            title="F — на весь экран"
          >
            Предпросмотр
          </button>
        </div>
        <div className="presentation-chrome-actions">
          {n > 0 ? (
            <span className="deck-slides-film-count" aria-live="polite">
              {safeIdx + 1}
              <span aria-hidden> / </span>
              {n}
            </span>
          ) : null}
        </div>
      </header>

      {view === "grid" && slidePngs.length > 0 ? (
        <DeckGallery
          slidePngs={slidePngs}
          activeIndex={safeIdx}
          titles={(deck?.slides || []).map((s) => s.title || "")}
          canStructure={Boolean(live) && !saving}
          onSelect={(i) => {
            // Gallery → Slide only (never Edit). Edit is the Edit segment.
            setDir(i > safeIdx ? 1 : -1);
            setIdx(i);
            setView("slide");
            setEditing(false);
          }}
          onReorder={onReorderIndices}
          onDuplicate={
            live
              ? (i) => {
                  const id = deck?.slides?.[i]?.id;
                  if (id) void structureOp({ op: "duplicate", id });
                }
              : undefined
          }
          onDelete={
            live
              ? (i) => {
                  const id = deck?.slides?.[i]?.id;
                  if (!id) return;
                  if (deck!.slides.length <= 1) {
                    setSaveError("Нельзя удалить единственный слайд");
                    return;
                  }
                  const title = deck?.slides?.[i]?.title || `Слайд ${i + 1}`;
                  if (
                    !window.confirm(
                      `Удалить слайд «${title}»? PPTX и превью пересоберутся.`,
                    )
                  ) {
                    return;
                  }
                  void structureOp({ op: "delete", id });
                }
              : undefined
          }
        />
      ) : (
        <>
          <div className="presentation-stage">
            <AnimatePresence mode="wait" custom={dir}>
              <motion.div
                key={
                  live
                    ? `live-${safeIdx}-${deck?.slides?.[safeIdx]?.id}`
                    : `png-${currentPng}`
                }
                className="presentation-stage-frame"
                custom={dir}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              >
                {editing && live && deck ? (
                  <DeckCanvas
                    runId={runId}
                    deck={deck}
                    index={safeIdx}
                    editing={editing}
                    saving={saving}
                    mediaVersion={mediaVersion}
                    openMediaId={openMediaId}
                    onMediaClick={
                      onEditFigure || onEditImage ? onMediaClick : undefined
                    }
                    onDeckChange={setDeck}
                    onPatch={patchSlides}
                    previewHtml={chartPreview}
                    diagramMermaid={
                      diagrams.find((d) => d.id === deck?.slides?.[safeIdx]?.media_id)
                        ?.mermaid ||
                      diagrams.find((d) => d.id === deck?.slides?.[safeIdx]?.chart_id)
                        ?.mermaid ||
                      null
                    }
                    diagramPalette={defaultPalette}
                  />
                ) : currentPng ? (
                  <img
                    className="presentation-slide-img"
                    src={
                      mediaVersion
                        ? `${currentPng}${currentPng.includes("?") ? "&" : "?"}mv=${mediaVersion}`
                        : currentPng
                    }
                    alt={`Слайд ${safeIdx + 1} из ${n}`}
                  />
                ) : live && deck ? (
                  <DeckCanvas
                    runId={runId}
                    deck={deck}
                    index={safeIdx}
                    editing={editing}
                    saving={saving}
                    mediaVersion={mediaVersion}
                    openMediaId={openMediaId}
                    onMediaClick={
                      onEditFigure || onEditImage ? onMediaClick : undefined
                    }
                    onDeckChange={setDeck}
                    onPatch={patchSlides}
                    previewHtml={chartPreview}
                    diagramMermaid={
                      diagrams.find((d) => d.id === deck?.slides?.[safeIdx]?.media_id)
                        ?.mermaid ||
                      diagrams.find((d) => d.id === deck?.slides?.[safeIdx]?.chart_id)
                        ?.mermaid ||
                      null
                    }
                    diagramPalette={defaultPalette}
                  />
                ) : null}
              </motion.div>
            </AnimatePresence>
            <AnimatePresence>
              {(saving || saveFlash) && !saveError && (
                <motion.div
                  className={`presentation-save-pill${saving ? " is-busy" : " is-ok"}`}
                  initial={reduce ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  transition={{ duration: 0.2 }}
                >
                  {saving ? "Сохраняю в PPTX…" : "Сохранено · twin + PPTX"}
                </motion.div>
              )}
              {saveError ? (
                <motion.div
                  className="presentation-save-pill is-err"
                  initial={reduce ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  role="alert"
                >
                  {saveError}
                  <button
                    type="button"
                    className="presentation-save-dismiss"
                    onClick={() => setSaveError(null)}
                  >
                    OK
                  </button>
                </motion.div>
              ) : null}
            </AnimatePresence>
            {live ? (
              <p className="presentation-font-honesty">
                PPTX использует шрифты темы; twin в Liber может отличаться (как у
                Julius).
              </p>
            ) : null}
          </div>

          <div
            className="presentation-progress"
            role="progressbar"
            aria-valuenow={safeIdx + 1}
            aria-valuemin={1}
            aria-valuemax={Math.max(n, 1)}
          >
            <span
              style={{
                width: n ? `${((safeIdx + 1) / n) * 100}%` : "0%",
              }}
            />
          </div>

          {slidePngs.length > 0 ? (
            <div
              className="presentation-filmstrip"
              role="tablist"
              aria-label="Слайды"
            >
              {slidePngs.map((url, i) => {
                const t = (deck?.slides?.[i]?.title || "").trim();
                return (
                  <button
                    key={deck?.slides?.[i]?.id || url}
                    type="button"
                    role="tab"
                    draggable={live && !saving}
                    aria-selected={i === safeIdx}
                    className={`presentation-thumb${i === safeIdx ? " is-active" : ""}${dragFrom === i ? " is-dragging" : ""}`}
                    title={
                      live
                        ? `${t || `Слайд ${i + 1}`} · перетащите для порядка`
                        : t || `Слайд ${i + 1}`
                    }
                    onDragStart={() => setDragFrom(i)}
                    onDragEnd={() => setDragFrom(null)}
                    onDragOver={(e) => {
                      if (live) e.preventDefault();
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (dragFrom != null) onReorderIndices(dragFrom, i);
                      setDragFrom(null);
                    }}
                    onClick={() => {
                      setDir(i > safeIdx ? 1 : -1);
                      setIdx(i);
                    }}
                  >
                    <img
                      src={
                        mediaVersion
                          ? `${url}${url.includes("?") ? "&" : "?"}mv=${mediaVersion}`
                          : url
                      }
                      alt=""
                      draggable={false}
                    />
                    <span>{String(i + 1).padStart(2, "0")}</span>
                  </button>
                );
              })}
            </div>
          ) : live && deck ? (
            <div
              className="presentation-filmstrip"
              role="tablist"
              aria-label="Слайды"
            >
              {deck.slides.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  role="tab"
                  aria-selected={i === safeIdx}
                  className={`presentation-thumb is-ghost${i === safeIdx ? " is-active" : ""}`}
                  onClick={() => {
                    setDir(i > safeIdx ? 1 : -1);
                    setIdx(i);
                  }}
                >
                  <span className="presentation-thumb-ghost">{s.layout}</span>
                  <span>{i + 1}</span>
                </button>
              ))}
            </div>
          ) : null}
        </>
      )}

      {view === "slide" ? (
        <div className="presentation-toolbar">
          <button
            type="button"
            className="presentation-nav"
            onClick={() => go(-1)}
            aria-label="Назад"
          >
            ←
          </button>
          <span className="presentation-count">
            {safeIdx + 1} / {n}
          </span>
          <button
            type="button"
            className="presentation-nav"
            onClick={() => go(1)}
            aria-label="Вперёд"
          >
            →
          </button>
          <button
            type="button"
            className="presentation-nav"
            onClick={() => setView("grid")}
          >
            Все слайды
          </button>
          {live ? (
            <>
              <button
                type="button"
                className="presentation-nav"
                disabled={saving}
                onClick={() => {
                  const id = deck?.slides?.[safeIdx]?.id;
                  if (id) void structureOp({ op: "duplicate", id });
                }}
              >
                Дублировать
              </button>
              <button
                type="button"
                className="presentation-nav is-danger"
                disabled={saving || (deck?.slides?.length || 0) <= 1}
                onClick={() => {
                  const id = deck?.slides?.[safeIdx]?.id;
                  if (!id) return;
                  const title =
                    deck?.slides?.[safeIdx]?.title || `Слайд ${safeIdx + 1}`;
                  if (
                    !window.confirm(
                      `Удалить слайд «${title}»? PPTX и превью пересоберутся.`,
                    )
                  ) {
                    return;
                  }
                  void structureOp({ op: "delete", id });
                }}
              >
                Удалить
              </button>
            </>
          ) : null}
        </div>
      ) : null}

      {editing &&
      view === "slide" &&
      openMediaId &&
      openMediaKind === "chart" &&
      onEditFigure ? (
        <div className="presentation-media-sheet is-below-film">
          <ChartEditSheet
            open
            trapFocus
            figureId={openMediaId}
            runId={runId}
            palettes={palettes}
            catalogTypes={catalogTypes}
            initialPalette={
              (openMediaId && chartIndex[openMediaId]?.palette) || defaultPalette
            }
            initialType={(openMediaId && chartIndex[openMediaId]?.type) || ""}
            busy={editingFigureId === openMediaId}
            onPreviewHtml={setChartPreview}
            error={editErrorFigureId === openMediaId ? editError : null}
            onCancel={closeMediaSheet}
            onSubmit={(req) => void submitChart(req)}
          />
        </div>
      ) : null}
      {editing &&
      view === "slide" &&
      openMediaId &&
      openMediaKind === "diagram" &&
      !openDiagram ? (
        <p className="presentation-media-wait">Открываю схему…</p>
      ) : null}
      {editing &&
      view === "slide" &&
      openMediaId &&
      openMediaKind === "diagram" &&
      openDiagram ? (
        <DiagramVisualEditor
          open
          diagramId={openDiagram.id}
          title={openDiagram.title}
          mermaid={openDiagram.mermaid}
          busy={saving}
          error={diagramError}
          onCancel={closeMediaSheet}
          onSave={(mermaid, title) => void saveDiagram(mermaid, title)}
        />
      ) : null}
      {editing &&
      view === "slide" &&
      openMediaId &&
      openMediaKind === "photo" &&
      onEditImage ? (
        <div className="presentation-media-sheet is-below-film">
          <ImageEditModal
            open
            trapFocus
            figureId={openMediaId}
            busy={editingFigureId === openMediaId}
            error={editErrorFigureId === openMediaId ? editError : null}
            onCancel={closeMediaSheet}
            onSubmit={(req) => void submitImage(req)}
          />
        </div>
      ) : null}

      {full ? (
        <PresentationFullscreen
          slides={slidePngs.length ? slidePngs : []}
          index={safeIdx}
          onIndex={(i) => {
            setDir(i > safeIdx ? 1 : -1);
            setIdx(i);
          }}
          onClose={() => setFull(false)}
          deck={live ? deck : null}
          runId={runId}
          diagramMermaid={
            diagrams.find((d) => d.id === deck?.slides?.[safeIdx]?.media_id)
              ?.mermaid || null
          }
          diagramPalette={defaultPalette}
        />
      ) : null}
    </div>
  );
}
