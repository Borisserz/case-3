/** Liber Atelier — chat-first desk shell (orchestration only). */

/* premium-home-bust */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from "react";
import { useReducedMotion } from "framer-motion";
import {
  ArtifactRail,
  type ActiveArtifact,
  type ArtifactTab,
} from "../ArtifactRail";
import type { ChartEditRequest } from "../ChartEditSheet";
import type { ImageEditRequest } from "../ImageEditModal";
import type { TableEditRequest } from "../TableEditSheet";
import type { ParagraphEditRequest } from "../ParagraphEditSheet";
import { ChatComposer } from "../ChatComposer";
import { ChatMessages } from "../ChatMessages";
import { ChartsQa } from "../ChartsQa";
import { openRunEvents } from "../api/runEvents";
import { openSummaryStream } from "../api/summaryStream";
import {
  craftParentId,
  formatCraftRecap,
  hydrateCraftFromSteps,
  upsertCraftFilm,
  upsertCraftSubstep,
  type CraftFilmFrame,
  type CraftStepLogEntry,
} from "../domain/craftSteps";
import {
  DEFAULT_INTENT,
  FALLBACK_PALETTES,
  FALLBACK_TYPES,
  LONG_TEXT_CHARS,
} from "../domain/liberConstants";
import { modeToOutputMode, type LiberWorkMode } from "../domain/liberModes";
import {
  appendBotThinking,
  asDownloads,
  asString,
  formatApiDetailError,
  formatBytes,
  formatRunStatusError,
  imageChipFromHealth,
  paradeHintFromHealth,
  provisionalSessionTitle,
  readTextFile,
  reportReadyText,
  reportTitle,
  slidesJobInFlight,
  slidesJobNeedsKick,
  slidesJobTerminal,
  stageLabel,
  uid,
} from "../domain/runHelpers";
import type {
  Health,
  Msg,
  PaletteInfo,
  RunResult,
  SourceAttachment,
  SourceDraft,
} from "../domain/liberTypes";
import {
  createFolder,
  deleteFolder,
  loadFolders,
  loadHistory,
  loadHistoryPayload,
  moveHistoryToFolder,
  pushHistory,
  renameFolder,
  saveRunPayload,
  togglePinHistory,
  type HistoryFolder,
  type HistoryItem,
} from "../domain/reportHistory";
import { loadRailWidth } from "../domain/railWidth";
import { DeckStyleSheet } from "../DeckStyleSheet";
import {
  deckStyleToApiPayload,
  loadDeckStyle,
  saveDeckStyle,
  type DeckStyle,
  type DeckThemePackInfo,
  FALLBACK_DECK_PACKS,
} from "../deckStyle";
import { starterPromptForStructure } from "../deckTemplates";
import { SettingsModal } from "../SettingsModal";
import { Sidebar } from "../Sidebar";
import { useLiberDevPreviews } from "../useLiberDevPreviews";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  // Chart type/style/title: model + ChartEditSheet (not Settings). Fixed run defaults:
  const chartAuto = true;
  const types: string[] = [];
  const chartHints = "";
  const chartPalette = "atelier";
  const chartStyle = "";
  const docTitle = "";
  const [maxCharts, setMaxCharts] = useState(2);
  const [maxDiagrams, setMaxDiagrams] = useState(2);
  const [maxImages, setMaxImages] = useState(2);
  const [forbidCharts, setForbidCharts] = useState(false);
  /** Photos on by default; health may raise budget / confirm Image API. */
  const [forbidImages, setForbidImages] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [chat, setChat] = useState("");
  /** Liber-attached photos for document slots or chat-only /edit */
  const [attachPhotos, setAttachPhotos] = useState<File[]>([]);
  /** Photo-edit mode UI parked; keep document pipeline. */
  const [photoMode] = useState<"document" | "edit">("document");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  /** Stop pressed — waiting for meta cancelled. */
  const [stopping, setStopping] = useState(false);
  const [editBusy, setEditBusy] = useState<{
    msgId: string;
    figureId: string;
  } | null>(null);
  /** Keeps fail message until success / cancel / new submit. */
  const [editError, setEditError] = useState<{
    msgId: string;
    figureId: string;
    message: string;
  } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  /** B21: one-shot undo after last Liber edit */
  const [undoOffer, setUndoOffer] = useState<{
    msgId: string;
    runId: string;
  } | null>(null);
  const undoBusyRef = useRef(false);
  const [downloadsPulseMsgId, setDownloadsPulseMsgId] = useState<string | null>(
    null,
  );
  const [deckStyle, setDeckStyle] = useState<DeckStyle>(() => loadDeckStyle());
  const [deckStyleOpen, setDeckStyleOpen] = useState(false);
  const [workMode, setWorkMode] = useState<LiberWorkMode>("report");
  /** Julius chat rename — column head only; seeded then → preview.title */
  const [chatTitle, setChatTitle] = useState<string | null>(null);
  const [deckApplyHint, setDeckApplyHint] = useState<string | null>(null);
  const [deckPacks, setDeckPacks] =
    useState<DeckThemePackInfo[]>(FALLBACK_DECK_PACKS);
  const [hasStoredReport, setHasStoredReport] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(() => loadHistory());
  const [folders, setFolders] = useState<HistoryFolder[]>(() => loadFolders());
  const [activeArtifact, setActiveArtifact] = useState<ActiveArtifact | null>(
    null,
  );
  /** Text of attached .txt/.md for Source tab / plaque. */
  const [sourceDraft, setSourceDraft] = useState<SourceDraft | null>(null);
  const [plaqueDismissed, setPlaqueDismissed] = useState(false);
  const [narrowRail, setNarrowRail] = useState(false);
  const [railWidthPct, setRailWidthPct] = useState(() => loadRailWidth());
  /** Keep rail mounted + desk layout until width→0 finishes (avoids bubble snap). */
  const [railExiting, setRailExiting] = useState(false);
  const lastArtifactRef = useRef<ActiveArtifact | null>(null);
  const chatRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const stickBottom = useRef(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const photoRef = useRef<HTMLInputElement>(null);
  const editLock = useRef(false);
  /** Active pipeline/slides run for Stop → POST /cancel. */
  const activeRunIdRef = useRef<string | null>(null);
  const cancelRequestedRef = useRef(false);
  const pendingBotIdRef = useRef<string | null>(null);

  const catalog = useMemo(() => {
    const fromApi = health?.chart_types?.filter(Boolean);
    return fromApi && fromApi.length > 0 ? fromApi : [...FALLBACK_TYPES];
  }, [health]);

  const reduceMotion = useReducedMotion();

  const palettes = useMemo<PaletteInfo[]>(() => {
    if (health?.chart_palettes?.length) return health.chart_palettes;
    return FALLBACK_PALETTES;
  }, [health]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then(async (r) => {
        if (!r.ok) throw new Error(`health ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        setHealth(data);
        const d = data?.defaults;
        if (d && typeof d.max_charts === "number") setMaxCharts(d.max_charts);
        if (d && typeof d.max_diagrams === "number") setMaxDiagrams(d.max_diagrams);
        if (d && typeof d.max_images === "number") {
          setMaxImages(d.max_images);
          // Office Image API ready → allow photos by default when budget > 0
          if (
            d.max_images > 0 &&
            (data.image_api_configured || data.kandinsky_configured)
          ) {
            setForbidImages(false);
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth({
            ok: false,
            docker_ok: false,
            playwright_ok: false,
            vision_configured: false,
            kandinsky_configured: false,
            docker_error: "API unreachable — scripts\\api.cmd на :8000",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    document.title = chatTitle ? `${chatTitle} · Liber` : "Liber";
  }, [chatTitle]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/deck-themes")
      .then(async (r) => {
        if (!r.ok) throw new Error(`deck-themes ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        const packs = data?.packs;
        if (Array.isArray(packs) && packs.length) {
          setDeckPacks(packs as DeckThemePackInfo[]);
        }
      })
      .catch(() => {
        /* keep FALLBACK_DECK_PACKS */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    const onScroll = () => {
      const gap = el.scrollHeight - el.scrollTop - el.clientHeight;
      stickBottom.current = gap < 96;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const jumpBottom = (smooth: boolean) => {
      const el = messagesRef.current;
      if (el) el.scrollTop = el.scrollHeight;
      bottomRef.current?.scrollIntoView({
        behavior: smooth ? "smooth" : "auto",
        block: "end",
      });
    };
    // Dev previews: land on the card (retry after PDF thumb layout).
    if (/preview=(artifact|deck)/.test(window.location.search)) {
      stickBottom.current = true;
      jumpBottom(false);
      const t1 = window.setTimeout(() => jumpBottom(false), 120);
      const t2 = window.setTimeout(() => jumpBottom(false), 480);
      return () => {
        window.clearTimeout(t1);
        window.clearTimeout(t2);
      };
    }
    // Don't yank the chat while the user is reading earlier messages.
    if (!stickBottom.current) return;
    jumpBottom(true);
  }, [msgs]);

  useEffect(() => {
    const el = chatRef.current;
    if (!el) return;
    el.style.height = "0px";
    // Standard chat composer: ~1–4 lines, then internal scroll (not a tall slab).
    const next = Math.min(Math.max(el.scrollHeight, 44), 112);
    el.style.height = `${next}px`;
  }, [chat]);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("liber-last-report");
      if (!raw) {
        setHasStoredReport(false);
        return;
      }
      const result = JSON.parse(raw) as RunResult;
      setHasStoredReport(Boolean(result?.preview?.blocks?.length));
    } catch {
      setHasStoredReport(false);
    }
  }, [msgs]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 899px)");
    const sync = () => setNarrowRail(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  useLiberDevPreviews({
    setMsgs,
    setBusy,
    setSourceDraft,
    setActiveArtifact,
  });

  function applyEditPayload(
    msgId: string,
    runId: string,
    data: {
      preview?: RunResult["preview"];
      downloads?: RunResult["downloads"];
      warnings?: string[];
      media_status?: RunResult["media_status"];
      diagrams?: RunResult["diagrams"];
      undo?: { kind?: string; target?: string } | null;
    },
    toastText: string,
  ) {
    setMsgs((list) =>
      list.map((msg) => {
        if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
        const next = {
          ...msg,
          result: {
            ...msg.result,
            preview: data.preview ?? msg.result.preview,
            downloads: data.downloads ?? msg.result.downloads,
            warnings:
              Array.isArray(data.warnings) && data.warnings.length
                ? data.warnings
                : msg.result.warnings,
            media_status: data.media_status ?? msg.result.media_status,
            diagrams: data.diagrams ?? msg.result.diagrams,
          },
        };
        if (next.result) rememberRun(next.result);
        return next;
      }),
    );
    if (data.undo && data.undo.kind) {
      setUndoOffer({ msgId, runId });
    } else {
      setUndoOffer(null);
    }
    setToast(toastText);
    setDownloadsPulseMsgId(msgId);
    window.setTimeout(() => setToast(null), 4200);
    window.setTimeout(() => setDownloadsPulseMsgId(null), 2200);
  }

  async function undoLastEdit() {
    if (!undoOffer || undoBusyRef.current) return;
    undoBusyRef.current = true;
    const { msgId, runId } = undoOffer;
    try {
      const res = await fetch(
        `/api/runs/${encodeURIComponent(runId)}/undo`,
        { method: "POST" },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.error || res.statusText || "undo failed",
        );
      }
      applyEditPayload(msgId, runId, { ...data, undo: null }, "Правка отменена");
      setUndoOffer(null);
    } catch (err) {
      setToast(err instanceof Error ? err.message : String(err));
      window.setTimeout(() => setToast(null), 3200);
    } finally {
      undoBusyRef.current = false;
    }
  }

  async function editFigure(
    msgId: string,
    runId: string,
    req: ChartEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    editLock.current = true;
    setEditError(null);
    setEditBusy({ msgId, figureId: req.figureId });
    try {
      const res = await fetch(
        `/api/runs/${encodeURIComponent(runId)}/charts/${encodeURIComponent(req.figureId)}/edit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            palette: req.palette,
            style: req.styleNotes,
            chart_type: req.chartType,
            formats: "both",
          }),
        },
      );
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : data.error || res.statusText || "edit failed",
        );
      }
      applyEditPayload(msgId, runId, data, "Отчёт обновлён");
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: req.figureId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  async function editImage(
    msgId: string,
    runId: string,
    req: ImageEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    editLock.current = true;
    setEditError(null);
    setEditBusy({ msgId, figureId: req.figureId });
    try {
      const res = await fetch(
        `/api/runs/${encodeURIComponent(runId)}/figures/${encodeURIComponent(req.figureId)}/edit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: req.mode,
            prompt: req.prompt,
            caption: req.caption,
            formats: "both",
          }),
        },
      );
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string"
            ? detail
            : data.error || res.statusText || "image edit failed",
        );
      }
      applyEditPayload(
        msgId,
        runId,
        data,
        req.mode === "edit" ? "Фото изменено" : "Фото сгенерировано заново",
      );
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: req.figureId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  async function editTable(
    msgId: string,
    runId: string,
    req: TableEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    const rid = (runId || "").trim();
    if (!rid) {
      setEditError({
        msgId,
        figureId: `tab:${req.tableIndex}`,
        message: "Нет run_id — открой отчёт из свежего запуска, не из пустой сессии",
      });
      return false;
    }
    editLock.current = true;
    const tableId = `tab:${req.tableIndex}`;
    setEditError(null);
    setEditBusy({ msgId, figureId: tableId });
    try {
      const res = await fetch(
        `/api/runs/${encodeURIComponent(rid)}/tables/${req.tableIndex}/edit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            caption: req.caption,
            headers: req.headers,
            rows: req.rows,
            formats: "both",
          }),
        },
      );
      let data: Record<string, unknown> = {};
      try {
        data = (await res.json()) as Record<string, unknown>;
      } catch {
        data = {};
      }
      if (!res.ok) {
        const detail = data.detail;
        const raw =
          typeof detail === "string"
            ? detail
            : typeof data.error === "string"
              ? data.error
              : res.statusText || "table edit failed";
        // FastAPI unmatched route (often empty run_id → /runs//tables/…)
        if (raw === "Not Found" || res.status === 404) {
          throw new Error(
            raw === "run not found"
              ? "Run не найден на диске — нужен свежий отчёт с этого API"
              : "API не нашёл правку таблицы (404). Перезапусти api.cmd и сохрани ещё раз",
          );
        }
        throw new Error(raw);
      }
      applyEditPayload(
        msgId,
        rid,
        {
          preview: data.preview as RunResult["preview"],
          downloads: asDownloads(data.downloads, {}),
          warnings: Array.isArray(data.warnings)
            ? data.warnings.filter((w): w is string => typeof w === "string")
            : undefined,
          media_status: data.media_status as RunResult["media_status"],
          undo: data.undo as { kind?: string; target?: string } | null,
        },
        "Таблица обновлена",
      );
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: tableId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  async function editParagraph(
    msgId: string,
    runId: string,
    req: ParagraphEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    const rid = (runId || "").trim();
    if (!rid) {
      setEditError({
        msgId,
        figureId: `para:${req.paragraphIndex}`,
        message: "Нет run_id — открой отчёт из свежего запуска",
      });
      return false;
    }
    editLock.current = true;
    const paraId = `para:${req.paragraphIndex}`;
    setEditError(null);
    setEditBusy({ msgId, figureId: paraId });
    try {
      const res = await fetch(
        `/api/runs/${encodeURIComponent(rid)}/paragraphs/${req.paragraphIndex}/edit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: req.text, formats: "both" }),
        },
      );
      let data: Record<string, unknown> = {};
      try {
        data = (await res.json()) as Record<string, unknown>;
      } catch {
        data = {};
      }
      if (!res.ok) {
        const detail = data.detail;
        const raw =
          typeof detail === "string"
            ? detail
            : typeof data.error === "string"
              ? data.error
              : res.statusText || "paragraph edit failed";
        throw new Error(raw);
      }
      applyEditPayload(
        msgId,
        rid,
        {
          preview: data.preview as RunResult["preview"],
          downloads: asDownloads(data.downloads, {}),
          warnings: Array.isArray(data.warnings)
            ? data.warnings.filter((w): w is string => typeof w === "string")
            : undefined,
          media_status: data.media_status as RunResult["media_status"],
          undo: data.undo as { kind?: string; target?: string } | null,
        },
        "Абзац обновлён",
      );
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: paraId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  function openReportArtifact(msgId: string, result: RunResult, tab?: ArtifactTab) {
    const mode = result.output_mode || "auto";
    const preferPreview = Boolean(result.preview?.blocks?.length);
    const preferPdf = Boolean(result.downloads?.pdf);
    let nextTab: ArtifactTab =
      tab ??
      (preferPreview ? "preview" : preferPdf ? "pdf" : "source");
    // Mode-locked defaults (report → preview; diagram → schema; presentation → deck).
    if (!tab) {
      if (mode === "diagram" && result.diagrams?.[0]) nextTab = "diagram";
      else if (mode === "presentation") nextTab = "presentation";
      else if (mode === "report" && preferPreview) nextTab = "preview";
    }
    setRailExiting(false);
    setActiveArtifact({
      kind: "report",
      msgId,
      tab: nextTab,
      title: reportTitle(result),
      activeDiagramId: result.diagrams?.[0]?.id ?? null,
    });
  }

  function openDiagramArtifact(
    msgId: string,
    result: RunResult,
    diagramId: string,
  ) {
    setRailExiting(false);
    setActiveArtifact({
      kind: "report",
      msgId,
      tab: "diagram",
      title: reportTitle(result),
      activeDiagramId: diagramId,
    });
  }

  function openPresentationArtifact(msgId: string, result: RunResult) {
    openReportArtifact(msgId, result, "presentation");
  }

  function openDeckSlidesArtifact(msgId: string, result: RunResult) {
    openReportArtifact(msgId, result, "slides");
  }

  function openFilmFrame(msgId: string, frame: CraftFilmFrame, runId?: string) {
    const bot = msgs.find((m) => m.id === msgId && m.role === "bot");
    const rid =
      runId ||
      (bot && bot.role === "bot" ? bot.result?.run_id : undefined) ||
      activeRunIdRef.current ||
      "";
    setRailExiting(false);
    setActiveArtifact({
      kind: "media",
      msgId,
      tab: "preview",
      runId: rid,
      mediaId: frame.id,
      url: frame.url,
      title: frame.id,
    });
  }

  function stopGeneration() {
    if (stopping) return;
    cancelRequestedRef.current = true;
    const runId = activeRunIdRef.current;
    const pendingId = pendingBotIdRef.current;
    setStopping(true);
    if (pendingId) {
      setMsgs((m) =>
        m.map((msg) => {
          if (msg.id !== pendingId || msg.role !== "bot") return msg;
          return {
            ...msg,
            pending: true,
            text: "Останавливаю…",
            error: undefined,
          };
        }),
      );
    }
    void (async () => {
      if (runId) {
        try {
          await fetch(`/api/runs/${encodeURIComponent(runId)}/cancel`, {
            method: "POST",
          });
        } catch {
          /* UI still finishes below */
        }
        const deadline = Date.now() + 20_000;
        while (Date.now() < deadline) {
          try {
            const st = await fetch(
              `/api/runs/${encodeURIComponent(runId)}/status`,
            );
            const body = await st.json().catch(() => ({}));
            const pipe = body.status as string | undefined;
            const slides = body.slides_status as string | undefined;
            if (
              pipe === "cancelled" ||
              slides === "cancelled" ||
              (pipe !== "running" &&
                slides !== "running" &&
                slides !== "queued")
            ) {
              break;
            }
          } catch {
            break;
          }
          await new Promise((r) => setTimeout(r, 400));
        }
      }
      if (pendingId) {
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== pendingId || msg.role !== "bot") return msg;
            return {
              ...msg,
              pending: false,
              text: "Остановлено",
              error: undefined,
              result: msg.result
                ? {
                    ...msg.result,
                    slides_status:
                      msg.result.slides_status === "running" ||
                      msg.result.slides_status === "queued"
                        ? "cancelled"
                        : msg.result.slides_status,
                    slides_error: "Остановлено",
                  }
                : msg.result,
            };
          }),
        );
      }
      setStopping(false);
      setBusy(false);
      activeRunIdRef.current = null;
    })();
  }

  async function makePresentation(msgId: string, result: RunResult) {
    const runId = result.run_id;
    if (!runId) return;
    // Julius: deck builds on the main chat — never park progress in the rail.
    setRailExiting(false);
    setActiveArtifact(null);
    cancelRequestedRef.current = false;
    activeRunIdRef.current = runId;
    pendingBotIdRef.current = msgId;
    setBusy(true);
    const alreadyInFlight = slidesJobInFlight(result.slides_status);
    const kick = slidesJobNeedsKick(result);
    setMsgs((m) =>
      m.map((msg) => {
        if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
        const stageKey = alreadyInFlight
          ? result.slides_stage?.startsWith("slides_")
            ? result.slides_stage
            : `slides_${result.slides_stage || "starting"}`
          : "slides_queued";
        const next = appendBotThinking(
          {
            ...msg,
            thinkingMode: "presentation",
            pending: true,
            pendingStage: stageKey,
            pendingDetail: null,
            text: msg.text?.trim()
              ? msg.text
              : "Собираю презентацию…",
            result: {
              ...msg.result,
              slides_status: alreadyInFlight
                ? result.slides_status || "running"
                : "queued",
              slides_stage: alreadyInFlight
                ? result.slides_stage || "starting"
                : "queued",
              slides_error: null,
            },
          },
          stageKey,
          null,
        );
        return next;
      }),
    );
    try {
      // Windows path was POST /slides twice (SSE kick + makePresentation) → double LLM/scrub.
      if (kick) {
        const res = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/slides`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(deckStyleToApiPayload(deckStyle)),
          },
        );
        const body = await res.json().catch(() => ({}));
        if (!res.ok && res.status !== 202) {
          throw new Error(
            typeof body.detail === "string"
              ? body.detail
              : body.error || res.statusText,
          );
        }
      }
      const applySlideStage = (slidesStage: string | null) => {
        const slideKey = slidesStage
          ? slidesStage.startsWith("slides_")
            ? slidesStage
            : `slides_${slidesStage}`
          : "slides_queued";
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== msgId || msg.role !== "bot" || !msg.result)
              return msg;
            return appendBotThinking(
              {
                ...msg,
                thinkingMode: "presentation",
                pending: true,
                pendingStage: slideKey,
                result: {
                  ...msg.result,
                  slides_status: "running",
                  slides_stage: slidesStage,
                },
              },
              slideKey,
              null,
            );
          }),
        );
      };

      const finishSlidesFromStatus = async () => {
        const st = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/status`,
        );
        const stBody = await st.json().catch(() => ({}));
        if (!st.ok) {
          throw new Error(
            typeof stBody.detail === "string"
              ? stBody.detail
              : stBody.error || st.statusText,
          );
        }
        const slidesStatus = (stBody.slides_status as string) || "idle";
        const slidesStage = (stBody.slides_stage as string) || null;
        const slidesError = (stBody.slides_error as string) || null;
        const downloads = (stBody.downloads || {}) as Record<string, string>;
        let slidePngs: string[] = [];
        let deckIr: RunResult["deck"] = null;
        let deckPdfMode: string | null = null;
        if (slidesStatus === "ok") {
          const g = await fetch(
            `/api/runs/${encodeURIComponent(runId)}/slides`,
          );
          const gBody = await g.json().catch(() => ({}));
          if (g.ok && Array.isArray(gBody.slide_pngs)) {
            slidePngs = gBody.slide_pngs as string[];
          }
          if (g.ok && gBody.deck) deckIr = gBody.deck;
          if (g.ok && typeof gBody.deck_pdf_mode === "string") {
            deckPdfMode = gBody.deck_pdf_mode;
          }
        }
        if (!deckPdfMode) {
          const art = stBody.slides_artifacts as
            | { deck_pdf_mode?: string }
            | undefined;
          if (art && typeof art.deck_pdf_mode === "string") {
            deckPdfMode = art.deck_pdf_mode;
          }
        }
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== msgId || msg.role !== "bot" || !msg.result)
              return msg;
            return {
              ...msg,
              pending: false,
              thinkingElapsedSec: msg.thinkingStartedAt
                ? Math.max(
                    0,
                    Math.round((Date.now() - msg.thinkingStartedAt) / 1000),
                  )
                : msg.thinkingElapsedSec,
              result: {
                ...msg.result,
                downloads: { ...msg.result.downloads, ...downloads },
                slides_status: slidesStatus,
                slides_stage: slidesStage,
                slides_error: slidesError,
                slide_pngs: slidePngs,
                deck: deckIr ?? msg.result.deck,
                deck_pdf_mode: deckPdfMode ?? msg.result.deck_pdf_mode,
              },
            };
          }),
        );
        if (slidesStatus === "ok") {
          setDownloadsPulseMsgId(msgId);
          window.setTimeout(() => setDownloadsPulseMsgId(null), 2400);
        }
      };

      const deadline = Date.now() + 10 * 60 * 1000;
      const slideCloser = { stop: null as null | (() => void) };
      const terminal = await new Promise<
        "done" | "error" | "cancelled" | "fallback"
      >((resolve) => {
        let settled = false;
        const settle = (v: "done" | "error" | "cancelled" | "fallback") => {
          if (settled) return;
          settled = true;
          resolve(v);
        };
        slideCloser.stop = openRunEvents(runId, {
          onStage: (stage, detail, scope, etaSec) => {
            void detail;
            if (scope === "slides" || stage.startsWith("slides_")) {
              applySlideStage(stage);
              if (etaSec != null && etaSec > 0) {
                setMsgs((m) =>
                  m.map((msg) =>
                    msg.id === msgId && msg.role === "bot"
                      ? { ...msg, etaSec }
                      : msg,
                  ),
                );
              }
            }
          },
          onStep: (step) => {
            setMsgs((m) =>
              m.map((msg) => {
                if (msg.id !== msgId || msg.role !== "bot") return msg;
                const parent = craftParentId(step.parent);
                const nextSubs = upsertCraftSubstep(
                  msg.craftSubsteps || [],
                  step,
                );
                let craftSkipped = msg.craftSkipped;
                if (step.status === "skipped" && parent) {
                  craftSkipped = {
                    ...(craftSkipped || {}),
                    [parent]: step.reason || "пропущено",
                  };
                }
                return {
                  ...msg,
                  craftSubsteps: nextSubs,
                  craftSkipped,
                };
              }),
            );
          },
          onFilm: (frame) => {
            setMsgs((m) =>
              m.map((msg) =>
                msg.id === msgId && msg.role === "bot"
                  ? {
                      ...msg,
                      craftFilm: upsertCraftFilm(msg.craftFilm || [], frame),
                    }
                  : msg,
              ),
            );
          },
          onTerminal: (kind, _err, hint, recap) => {
            if (kind === "cancelled") {
              setMsgs((m) =>
                m.map((msg) =>
                  msg.id === msgId && msg.role === "bot"
                    ? { ...msg, craftFrozen: true, pending: false }
                    : msg,
                ),
              );
            }
            if (kind === "error" && hint) {
              setMsgs((m) =>
                m.map((msg) =>
                  msg.id === msgId && msg.role === "bot"
                    ? { ...msg, errorHint: hint }
                    : msg,
                ),
              );
            }
            if (kind === "done" && recap) {
              const line = formatCraftRecap(recap);
              if (line) {
                setMsgs((m) =>
                  m.map((msg) =>
                    msg.id === msgId && msg.role === "bot"
                      ? { ...msg, craftRecap: line }
                      : msg,
                  ),
                );
              }
            }
            settle(kind);
          },
          onFallback: () => settle("fallback"),
        });
        const cancelWatch = window.setInterval(() => {
          if (cancelRequestedRef.current) {
            window.clearInterval(cancelWatch);
            setMsgs((m) =>
              m.map((msg) =>
                msg.id === msgId && msg.role === "bot"
                  ? { ...msg, craftFrozen: true }
                  : msg,
              ),
            );
            settle("cancelled");
          }
        }, 400);
        window.setTimeout(() => window.clearInterval(cancelWatch), 10 * 60 * 1000);
      });
      slideCloser.stop?.();

      if (terminal === "fallback") {
        for (;;) {
          if (cancelRequestedRef.current) break;
          if (Date.now() > deadline) {
            throw new Error("таймаут сборки презентации (10 мин)");
          }
          await new Promise((r) => setTimeout(r, 500));
          if (cancelRequestedRef.current) break;
          const st = await fetch(
            `/api/runs/${encodeURIComponent(runId)}/status`,
          );
          const stBody = await st.json().catch(() => ({}));
          if (!st.ok) {
            throw new Error(
              typeof stBody.detail === "string"
                ? stBody.detail
                : stBody.error || st.statusText,
            );
          }
          const slidesStatus = (stBody.slides_status as string) || "idle";
          const slidesStage = (stBody.slides_stage as string) || null;
          if (
            slidesStatus === "ok" ||
            slidesStatus === "error" ||
            slidesStatus === "cancelled"
          ) {
            await finishSlidesFromStatus();
            break;
          }
          applySlideStage(slidesStage);
        }
      } else if (terminal !== "cancelled") {
        await finishSlidesFromStatus();
      }
    } catch (err) {
      if (!cancelRequestedRef.current) {
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
            return {
              ...msg,
              pending: false,
              result: {
                ...msg.result,
                slides_status: "error",
                slides_error:
                  err instanceof Error ? err.message : String(err),
              },
            };
          }),
        );
      }
    } finally {
      if (activeRunIdRef.current === runId) activeRunIdRef.current = null;
      setBusy(false);
    }
  }

  function openSourceArtifact(draft: {
    title: string;
    text: string;
    fileName?: string;
  }) {
    setRailExiting(false);
    setActiveArtifact({
      kind: "source",
      tab: "source",
      title: draft.title,
      text: draft.text,
      fileName: draft.fileName,
    });
  }

  function openIntentArtifact(text: string) {
    setRailExiting(false);
    setActiveArtifact({
      kind: "intent",
      tab: "source",
      title: "Текст запроса",
      text,
    });
  }

  function closeArtifact() {
    if (!activeArtifact || railExiting) return;
    lastArtifactRef.current = activeArtifact;
    // Keep activeArtifact until width→0 finishes — nulling early dropped
    // `closing`/`has-rail` and snapped the user bubble after a long stall.
    setRailExiting(true);
  }

  function finishArtifactClose() {
    setRailExiting(false);
    setActiveArtifact(null);
  }

  useEffect(() => {
    if (activeArtifact && !railExiting) {
      lastArtifactRef.current = activeArtifact;
    }
  }, [activeArtifact, railExiting]);

  function setArtifactTab(tab: ArtifactTab) {
    setActiveArtifact((prev) => {
      if (!prev) return prev;
      if (prev.kind === "report") return { ...prev, tab };
      if (prev.kind === "media") return { ...prev, tab: "preview" };
      // source / intent only expose the Source tab
      return { ...prev, tab: "source" as const };
    });
  }

  function selectDiagram(id: string) {
    setActiveArtifact((prev) => {
      if (!prev || prev.kind !== "report") return prev;
      return { ...prev, tab: "diagram", activeDiagramId: id };
    });
  }

  function restoreLastReport() {
    try {
      const raw = sessionStorage.getItem("liber-last-report");
      if (!raw) return;
      const result = JSON.parse(raw) as RunResult;
      if (!result?.preview?.blocks?.length) return;
      const id = uid();
      setChatTitle(reportTitle(result));
      setMsgs([
        {
          id,
          role: "bot",
          text: reportReadyText(result),
          result,
        },
      ]);
      // Julius: card in chat; rail only on «Открыть»
    } catch {
      /* ignore */
    }
  }

  function startNewReport() {
    setMsgs([]);
    setChatTitle(null);
    setChat("");
    setFile(null);
    setSourceDraft(null);
    setAttachPhotos([]);
    setRailExiting(false);
    setActiveArtifact(null);
    setPlaqueDismissed(false);
    setEditError(null);
    chatRef.current?.focus();
  }

  function openHistoryItem(item: HistoryItem) {
    if (busy) return;
    const stored = loadHistoryPayload(item.runId);
    if (!stored?.preview?.blocks?.length) {
      setToast("Отчёт недоступен в этой сессии");
      window.setTimeout(() => setToast(null), 2800);
      return;
    }
    const result = stored as RunResult;
    const id = uid();
    setChatTitle(item.title || reportTitle(result));
    setMsgs([
      {
        id,
        role: "bot",
        text: reportReadyText(result),
        result,
      },
    ]);
  }

  function rememberRun(result: RunResult) {
    saveRunPayload(result);
    const title = reportTitle(result);
    setChatTitle(title);
    setHistory(
      pushHistory({
        id: result.run_id,
        title,
        runId: result.run_id,
        savedAt: Date.now(),
      }),
    );
  }

  const canSend = useMemo(() => {
    if (busy) return false;
    if (photoMode === "edit") {
      return attachPhotos.length > 0 && chat.trim().length > 0;
    }
    const hasSource = Boolean(file) || Boolean(sourceDraft?.text);
    const chatTrim = chat.trim();
    // Any scale brief is fine — do not gate presentation/diagram on Source length.
    return hasSource || chatTrim.length > 0;
  }, [file, busy, photoMode, attachPhotos, chat, sourceDraft]);

  const capturePastedSource = useCallback((text: string) => {
    const trimmed = text.trim();
    if (trimmed.length <= LONG_TEXT_CHARS) return false;
    const draft = {
      title: "Текст",
      text: trimmed,
    };
    setFile(null);
    setSourceDraft(draft);
    setPlaqueDismissed(false);
    setDeckApplyHint(null);
    setActiveArtifact({
      kind: "source",
      tab: "source",
      title: draft.title,
      text: draft.text,
    });
    return true;
  }, []);

  const ingestFiles = useCallback((list: FileList | File[]) => {
    const arr = Array.from(list);
    for (const f of arr) {
      if (
        /\.(txt|md)$/i.test(f.name) ||
        f.type === "text/plain" ||
        f.type === "text/markdown"
      ) {
        setFile(f);
        setPlaqueDismissed(false);
        setDeckApplyHint(null);
        void (async () => {
          try {
            const text = await readTextFile(f);
            const draft = {
              title: f.name,
              text,
              fileName: f.name,
            };
            setSourceDraft(draft);
            setActiveArtifact({
              kind: "source",
              tab: "source",
              title: draft.title,
              text: draft.text,
              fileName: draft.fileName,
            });
          } catch (err) {
            setToast(
              err instanceof Error ? err.message : "Не удалось прочитать файл",
            );
            window.setTimeout(() => setToast(null), 2800);
          }
        })();
        continue;
      }
      if (/^image\//.test(f.type) || /\.(png|jpe?g)$/i.test(f.name)) {
        setAttachPhotos((prev) => [...prev, f].slice(0, 2));
        setForbidImages(false);
        setMaxImages((n) => Math.max(n, 2));
      }
    }
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDrag(false);
      if (e.dataTransfer.files?.length) ingestFiles(e.dataTransfer.files);
    },
    [ingestFiles],
  );

  async function send() {
    if (!canSend) return;
    const chatTrim = chat.trim();
    const draftSnap = sourceDraft;
    const hasSource = Boolean(file) || Boolean(draftSnap?.text);
    const intentText =
      photoMode === "edit"
        ? chatTrim
        : hasSource
          ? chatTrim || DEFAULT_INTENT
          : chatTrim;
    if (photoMode === "edit" && !intentText) return;
    if (photoMode === "document" && !hasSource && !chatTrim) return;
    setDeckApplyHint(null);

    // Soft warn: Image down + photos wanted — run still proceeds (fig_* may skip)
    const wantsPhotos =
      photoMode === "edit" ||
      (photoMode === "document" &&
        !forbidImages &&
        maxImages > 0 &&
        modeToOutputMode(workMode) !== "diagram");
    if (wantsPhotos && health && !imageChip.ok) {
      setToast(
        health.image_api_configured || health.kandinsky_configured
          ? "Image API не отвечает — отчёт соберу, фото fig_* могут пропуститься"
          : "Image API не настроен — слоты fig_* будут пропущены",
      );
      window.setTimeout(() => setToast(null), 5200);
    }

    const attachment: SourceAttachment | undefined = draftSnap?.text
      ? {
          title: draftSnap.title,
          text: draftSnap.text,
          fileName: draftSnap.fileName,
        }
      : undefined;
    const userBody =
      photoMode === "edit"
        ? intentText
        : chatTrim
          ? chatTrim
          : attachment
            ? "Собрать отчёт"
            : file
              ? `Файл: ${file.name}`
              : chatTrim;
    const outMode = modeToOutputMode(workMode);
    const userChips = [
      photoMode === "edit" ? "только правка фото" : null,
      outMode === "diagram"
        ? "схема"
        : outMode === "presentation"
          ? `презентация · ${deckStyle.themePack}`
          : outMode === "report"
            ? "отчёт"
            : null,
      attachPhotos.length ? `фото ×${attachPhotos.length}` : null,
      photoMode === "document" && outMode !== "diagram" && forbidCharts
        ? "без графиков"
        : photoMode === "document" && outMode !== "diagram"
          ? `≤${maxCharts} гр.`
          : null,
      photoMode === "document" && outMode !== "diagram"
        ? forbidImages && !attachPhotos.length
          ? "без фото"
          : `≤${Math.max(maxImages, attachPhotos.length)} фото`
        : null,
      photoMode === "document"
        ? `≤${outMode === "diagram" ? Math.max(maxDiagrams, 1) : maxDiagrams} схем`
        : null,
      dryRun ? "dry-run" : null,
    ].filter((x): x is string => Boolean(x));

    const thinkingMode =
      outMode === "diagram"
        ? ("diagram" as const)
        : outMode === "presentation"
          ? ("presentation" as const)
          : ("report" as const);
    const pendingId = uid();
    cancelRequestedRef.current = false;
    pendingBotIdRef.current = pendingId;
    activeRunIdRef.current = null;
    // Presentation builds stay on the chat sheet — close rail if open.
    if (outMode === "presentation") {
      setRailExiting(false);
      setActiveArtifact(null);
    }
    setMsgs((m) => [
      ...m,
      {
        id: uid(),
        role: "user",
        text: userBody,
        chips: userChips.length ? userChips : undefined,
        attachment,
      },
      appendBotThinking(
        {
          id: pendingId,
          role: "bot",
          text:
            photoMode === "edit"
              ? "Править фото…"
              : outMode === "diagram"
                ? "Собираю схему…"
                : outMode === "presentation"
                  ? "Собираю презентацию…"
                  : "Генерирую документ…",
          pending: true,
          pendingStage: "queued",
          pendingDetail: null,
          thinkingStartedAt: Date.now(),
          thinkingMode,
        },
        "queued",
        null,
      ),
    ]);
    setBusy(true);
    setStopping(false);
    setChatTitle(provisionalSessionTitle(workMode));
    setChat("");
    if (chatRef.current) chatRef.current.style.height = "44px";
    const photosSnapshot = [...attachPhotos];
    setAttachPhotos([]);
    // Paste-source consumed; keep attached File for re-send until user clears.
    if (!file && draftSnap) {
      setSourceDraft(null);
      setActiveArtifact((a) =>
        a?.kind === "source" || a?.kind === "intent" ? null : a,
      );
    }

    const fd = new FormData();
    fd.append("photo_mode", photoMode);
    for (const p of photosSnapshot) fd.append("photos", p);
    if (photoMode === "edit") {
      fd.append("intent", intentText);
    } else {
      if (file) {
        fd.append("source", file);
        fd.append("intent", intentText);
      } else if (draftSnap?.text) {
        fd.append("source_text", draftSnap.text);
        fd.append("intent", intentText);
      } else {
        // Chat-only: same text is Source + Intent
        fd.append("source_text", chatTrim);
        fd.append("intent", intentText);
      }
      fd.append("max_charts", String(forbidCharts ? 0 : maxCharts));
      fd.append("max_diagrams", String(maxDiagrams));
      fd.append(
        "max_images",
        String(
          forbidImages && !photosSnapshot.length
            ? 0
            : Math.max(maxImages, photosSnapshot.length),
        ),
      );
      fd.append("chart_types", chartAuto ? "" : types.join(","));
      fd.append("chart_hints", chartHints.trim());
      fd.append("chart_auto", String(chartAuto));
      fd.append("chart_palette", chartPalette);
      fd.append("chart_style", chartStyle.trim());
      fd.append("doc_title", docTitle.trim().slice(0, 200));
      fd.append("forbid_charts", String(forbidCharts));
      fd.append(
        "forbid_images",
        String(forbidImages && photosSnapshot.length === 0),
      );
      fd.append("output_mode", outMode);
      fd.append("deck_pack", deckStyle.themePack || "atelier");
      fd.append(
        "formats",
        outMode === "diagram" || outMode === "presentation" ? "none" : "both",
      );
      fd.append("dry_run", String(dryRun));
      if (outMode === "diagram") {
        fd.set("max_charts", "0");
        fd.set("max_images", "0");
        fd.set("forbid_charts", "true");
        fd.set("forbid_images", "true");
        fd.set("max_diagrams", String(Math.max(maxDiagrams, 1)));
      }
      if (outMode === "presentation") {
        // Liber Mermaid UI schemas off — deck only (PPTX + PDF twin).
        fd.set("max_diagrams", "0");
      }
    }

    try {
      const res = await fetch("/api/run", { method: "POST", body: fd });
      const data = (await res.json().catch(() => ({}))) as Record<
        string,
        unknown
      >;
      if (!res.ok) {
        const fallback =
          res.status === 500 || res.status === 502 || res.status === 503
            ? "API недоступен — проверь :8000 (прокси Vite)"
            : res.statusText;
        throw new Error(formatApiDetailError(data, fallback));
      }

      // Sync photo-edit response (no poll)
      if (data.mode === "photo_edit" && data.status === "ok") {
        const result = data as unknown as RunResult;
        const caption = asString(data.caption, "Фото изменено");
        setChatTitle(caption.trim() || "Правка фото");
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== pendingId || msg.role !== "bot") return msg;
            return {
              ...msg,
              text: caption,
              pending: false,
              result,
            };
          }),
        );
        setToast("Фото изменено");
        window.setTimeout(() => setToast(null), 2800);
        setBusy(false);
        return;
      }

      let result = data as unknown as RunResult;

      // 202 async job: poll until ok/error
      if (res.status === 202 || data.status === "started" || data.status === "running") {
        const runId = asString(data.run_id);
        if (!runId) throw new Error("server did not return run_id");
        activeRunIdRef.current = runId;
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== pendingId || msg.role !== "bot") return msg;
            const stage = asString(data.stage, "queued");
            const mode = msg.thinkingMode || "report";
            return appendBotThinking(
              {
                ...msg,
                text: stageLabel(stage, null, mode),
                pending: true,
                pendingStage: stage,
                pendingDetail: null,
              },
              stage,
              null,
            );
          }),
        );
        const pollDeadlineMs = 20 * 60 * 1000;
        const runCloser = {
          summary: null as null | (() => void),
          events: null as null | (() => void),
        };
        let streamedSummary = "";
        let summaryStreamStarted = false;
        let cancelled = false;
        let slidesKicked = false;

        const applyStage = (
          stage: string | undefined,
          detail: string | null,
          etaSec?: number | null,
        ) => {
          setMsgs((m) =>
            m.map((msg) => {
              if (msg.id !== pendingId || msg.role !== "bot") return msg;
              const mode = msg.thinkingMode || "report";
              return appendBotThinking(
                {
                  ...msg,
                  pending: true,
                  pendingStage: stage,
                  pendingDetail: detail,
                  etaSec:
                    etaSec != null && etaSec > 0 ? etaSec : msg.etaSec ?? null,
                  text:
                    msg.streamingSummary && msg.text.trim()
                      ? msg.text
                      : stageLabel(stage || "queued", detail, mode),
                },
                stage,
                detail,
              );
            }),
          );
          const shouldStream =
            !summaryStreamStarted &&
            outMode !== "diagram" &&
            (stage === "latex" ||
              stage === "docx" ||
              stage === "summary");
          if (shouldStream) {
            summaryStreamStarted = true;
            runCloser.summary = openSummaryStream(
              runId,
              (full) => {
                streamedSummary = full;
                setMsgs((m) =>
                  m.map((msg) => {
                    if (msg.id !== pendingId || msg.role !== "bot") return msg;
                    return {
                      ...msg,
                      text: full,
                      pending: true,
                      streamingSummary: true,
                      pendingStage: stage || msg.pendingStage,
                      pendingDetail: detail,
                    };
                  }),
                );
              },
              (full) => {
                streamedSummary = full || streamedSummary;
              },
            );
          }
        };

        const applyFilm = (frame: CraftFilmFrame) => {
          setMsgs((m) =>
            m.map((msg) =>
              msg.id === pendingId && msg.role === "bot"
                ? {
                    ...msg,
                    craftFilm: upsertCraftFilm(msg.craftFilm || [], frame),
                  }
                : msg,
            ),
          );
        };

        const fetchFinalStatus = async (): Promise<RunResult> => {
          const st = await fetch(
            `/api/runs/${encodeURIComponent(runId)}/status`,
          );
          const body = await st.json().catch(() => ({}));
          if (!st.ok) {
            throw new Error(
              typeof body.detail === "string"
                ? body.detail
                : body.error || st.statusText,
            );
          }
          if (body.status === "cancelled") {
            cancelled = true;
            return body as RunResult;
          }
          if (body.status === "error") {
            throw new Error(
              formatRunStatusError(body as Record<string, unknown>, runId),
            );
          }
          return body as RunResult;
        };

        /** Status poll — used as SSE fallback (Windows proxies). */
        const pollUntilDone = async (): Promise<RunResult | null> => {
          const pollStarted = Date.now();
          let soft404 = 0;
          for (;;) {
            if (cancelRequestedRef.current) {
              cancelled = true;
              return null;
            }
            if (Date.now() - pollStarted > pollDeadlineMs) {
              throw new Error(
                `таймаут ожидания run ${runId} (20 мин) — смотри runs/logs/${runId}`,
              );
            }
            await new Promise((r) => setTimeout(r, 400));
            if (cancelRequestedRef.current) {
              cancelled = true;
              return null;
            }
            const st = await fetch(
              `/api/runs/${encodeURIComponent(runId)}/status`,
            );
            const body = await st.json().catch(() => ({}));
            if (st.status === 404) {
              soft404 += 1;
              if (soft404 > 8) {
                throw new Error(`run ${runId} не найден (status 404)`);
              }
              continue;
            }
            soft404 = 0;
            if (!st.ok) {
              throw new Error(
                typeof body.detail === "string"
                  ? body.detail
                  : body.error || st.statusText,
              );
            }
            const stage = body.stage as string | undefined;
            const detail = (body.stage_detail as string | null) || null;
            if (body.status === "cancelled") {
              cancelled = true;
              return null;
            }
            if (body.status === "running" || body.status === "started") {
              const rawSteps = body.steps;
              if (Array.isArray(rawSteps) && rawSteps.length) {
                const hydrated = hydrateCraftFromSteps(
                  rawSteps as CraftStepLogEntry[],
                );
                applyStage(hydrated.stage || stage, detail);
                if (hydrated.substeps.length || Object.keys(hydrated.skipped).length) {
                  setMsgs((m) =>
                    m.map((msg) => {
                      if (msg.id !== pendingId || msg.role !== "bot") return msg;
                      return {
                        ...msg,
                        craftSubsteps: hydrated.substeps.length
                          ? hydrated.substeps
                          : msg.craftSubsteps,
                        craftSkipped: {
                          ...(msg.craftSkipped || {}),
                          ...hydrated.skipped,
                        },
                      };
                    }),
                  );
                }
              } else {
                applyStage(stage, detail);
              }
              continue;
            }
            if (body.status === "error") {
              throw new Error(
                formatRunStatusError(body as Record<string, unknown>, runId),
              );
            }
            // Presentation: pipeline status=ok early — wait for slides job (Windows poll path).
            if (outMode === "presentation") {
              const slidesSt = (body.slides_status as string) || "idle";
              if (slidesJobInFlight(slidesSt)) {
                const ss = (body.slides_stage as string) || "starting";
                applyStage(
                  ss.startsWith("slides_") ? ss : `slides_${ss}`,
                  null,
                );
                continue;
              }
              if (slidesJobTerminal(slidesSt)) {
                return body as RunResult;
              }
              // idle — return so caller can kick once (do not spin forever)
            }
            return body as RunResult;
          }
        };

        try {
          const terminal = await new Promise<
            "done" | "error" | "cancelled" | "fallback"
          >((resolve) => {
            let settled = false;
            const settle = (v: "done" | "error" | "cancelled" | "fallback") => {
              if (settled) return;
              settled = true;
              resolve(v);
            };
            runCloser.events = openRunEvents(runId, {
              onStage: (stage, detail, scope, etaSec) => {
                const uiStage =
                  scope === "slides" && !stage.startsWith("slides_")
                    ? `slides_${stage}`
                    : stage;
                applyStage(uiStage, detail, etaSec);
                // Presentation: after pipeline_ok, kick slides while SSE stays open
                if (
                  outMode === "presentation" &&
                  (stage === "pipeline_ok" || stage === "ok") &&
                  scope === "pipeline" &&
                  !slidesKicked
                ) {
                  slidesKicked = true;
                  void fetch(
                    `/api/runs/${encodeURIComponent(runId)}/slides`,
                    {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify(deckStyleToApiPayload(deckStyle)),
                    },
                  ).catch(() => {
                    /* makePresentation path still runs if needed */
                  });
                }
              },
              onStep: (step) => {
                setMsgs((m) =>
                  m.map((msg) => {
                    if (msg.id !== pendingId || msg.role !== "bot") return msg;
                    const parent = craftParentId(step.parent);
                    const nextSubs = upsertCraftSubstep(
                      msg.craftSubsteps || [],
                      step,
                    );
                    let craftSkipped = msg.craftSkipped;
                    if (step.status === "skipped" && parent) {
                      craftSkipped = {
                        ...(craftSkipped || {}),
                        [parent]: step.reason || "пропущено",
                      };
                    }
                    return {
                      ...msg,
                      craftSubsteps: nextSubs,
                      craftSkipped,
                    };
                  }),
                );
              },
              onFilm: applyFilm,
              onTerminal: (kind, _err, hint, recap) => {
                if (kind === "cancelled") {
                  setMsgs((m) =>
                    m.map((msg) =>
                      msg.id === pendingId && msg.role === "bot"
                        ? { ...msg, craftFrozen: true, pending: false }
                        : msg,
                    ),
                  );
                }
                if (kind === "error" && hint) {
                  setMsgs((m) =>
                    m.map((msg) =>
                      msg.id === pendingId && msg.role === "bot"
                        ? { ...msg, errorHint: hint }
                        : msg,
                    ),
                  );
                }
                if (kind === "done" && recap) {
                  const line = formatCraftRecap(recap);
                  if (line) {
                    setMsgs((m) =>
                      m.map((msg) =>
                        msg.id === pendingId && msg.role === "bot"
                          ? { ...msg, craftRecap: line }
                          : msg,
                      ),
                    );
                  }
                }
                settle(kind);
              },
              onFallback: () => settle("fallback"),
            });
            // Safety: if cancel while waiting SSE
            const cancelWatch = window.setInterval(() => {
              if (cancelRequestedRef.current) {
                window.clearInterval(cancelWatch);
                setMsgs((m) =>
                  m.map((msg) =>
                    msg.id === pendingId && msg.role === "bot"
                      ? { ...msg, craftFrozen: true }
                      : msg,
                  ),
                );
                settle("cancelled");
              }
            }, 400);
            window.setTimeout(() => window.clearInterval(cancelWatch), pollDeadlineMs);
          });

          if (terminal === "fallback") {
            runCloser.events?.();
            runCloser.events = null;
            const polled = await pollUntilDone();
            if (polled) result = polled;
          } else if (terminal === "cancelled") {
            cancelled = true;
          } else if (terminal === "error") {
            result = await fetchFinalStatus();
          } else {
            result = await fetchFinalStatus();
          }
        } finally {
          runCloser.events?.();
          runCloser.summary?.();
        }
        if (cancelled || cancelRequestedRef.current) {
          setBusy(false);
          return;
        }
      }

      // Pipeline may omit output_mode if an older worker rewrote meta — stamp from send.
      result = {
        ...result,
        output_mode: result.output_mode || outMode || "auto",
      };

      const isPresentationOnly =
        outMode === "presentation" || result.output_mode === "presentation";
      const slidesAlreadyDone =
        result.slides_status === "ok" || Boolean(result.downloads?.pptx);
      const slidesStillBuilding =
        isPresentationOnly &&
        Boolean(result.run_id) &&
        !slidesAlreadyDone;

      try {
        setChatTitle(reportTitle(result));
        if (
          result.preview?.blocks?.length ||
          result.downloads?.pdf ||
          result.downloads?.pptx ||
          (result.diagrams && result.diagrams.length > 0)
        ) {
          rememberRun(result);
          setHasStoredReport(true);
        }
      } catch {
        /* quota */
      }
      setMsgs((m) =>
        m.map((msg) => {
          if (msg.id !== pendingId || msg.role !== "bot") return msg;
          const streamed =
            msg.streamingSummary && msg.text.trim() ? msg.text : "";
          if (slidesStillBuilding) {
            // Keep pending — never flash empty PPTX/PDF cards + «Сделать».
            const ss = result.slides_stage || "starting";
            const stageKey = ss.startsWith("slides_")
              ? ss
              : slidesJobInFlight(result.slides_status)
                ? `slides_${ss}`
                : "slides_queued";
            return appendBotThinking(
              {
                ...msg,
                thinkingMode: "presentation",
                pending: true,
                pendingStage: stageKey,
                pendingDetail: null,
                text: streamed || msg.text?.trim() || "Собираю презентацию…",
                result: {
                  ...result,
                  slides_status: slidesJobInFlight(result.slides_status)
                    ? result.slides_status
                    : "queued",
                  slides_stage: result.slides_stage || "queued",
                },
              },
              stageKey,
              null,
            );
          }
          return {
            id: pendingId,
            role: "bot" as const,
            text: reportReadyText(result, streamed),
            result,
            thinking: msg.thinking,
            thinkingStartedAt: msg.thinkingStartedAt,
            thinkingMode: msg.thinkingMode,
            craftFilm: msg.craftFilm,
            craftRecap: msg.craftRecap,
            craftSubsteps: msg.craftSubsteps,
            craftSkipped: msg.craftSkipped,
            errorHint: msg.errorHint,
            craftFrozen: msg.craftFrozen,
            pendingStage: msg.pendingStage,
            thinkingElapsedSec: msg.thinkingStartedAt
              ? Math.max(
                  0,
                  Math.round((Date.now() - msg.thinkingStartedAt) / 1000),
                )
              : undefined,
          };
        }),
      );
      if (cancelRequestedRef.current) {
        setBusy(false);
        return;
      }
      if (slidesStillBuilding) {
        // Attach or kick once — never second POST when SSE already got 202.
        void makePresentation(pendingId, result);
      } else {
        activeRunIdRef.current = null;
        setBusy(false);
        if (isPresentationOnly && slidesAlreadyDone) {
          openReportArtifact(pendingId, result, "presentation");
        } else if (result.output_mode === "diagram" && result.diagrams?.[0]) {
          openDiagramArtifact(pendingId, result, result.diagrams[0].id);
        } else if (
          result.output_mode === "report" ||
          result.output_mode === "auto" ||
          !result.output_mode
        ) {
          openReportArtifact(pendingId, result);
        }
      }
    } catch (err) {
      if (!cancelRequestedRef.current) {
        const message = err instanceof Error ? err.message : String(err);
        setMsgs((m) =>
          m.map((msg) =>
            msg.id === pendingId
              ? { id: pendingId, role: "bot", text: "Ошибка", error: message }
              : msg,
          ),
        );
      }
      activeRunIdRef.current = null;
      setBusy(false);
    }
  }

  const paradeHint = paradeHintFromHealth(health);
  const imageChip = imageChipFromHealth(health);

  const healthReady = Boolean(
    health?.vision_configured && health?.docker_ok && health?.playwright_ok,
  );

  const plaqueDraft = sourceDraft
    ? {
        title: sourceDraft.title,
        subtitle: file
          ? formatBytes(file.size)
          : `${sourceDraft.text.length.toLocaleString("ru-RU")} символов`,
        fileName: sourceDraft.fileName,
      }
    : null;
  const showPlaque = Boolean(plaqueDraft && !plaqueDismissed);

  const railOpen = Boolean(activeArtifact);
  const railLayout = railOpen || railExiting;
  const railArtifact = activeArtifact ?? (railExiting ? lastArtifactRef.current : null);
  const pendingBot = msgs.find((m) => m.role === "bot" && m.pending);
  const thinkingLabel =
    pendingBot && pendingBot.role === "bot"
      ? stageLabel(
          pendingBot.pendingStage,
          pendingBot.pendingDetail,
          pendingBot.thinkingMode || "report",
        )
      : busy
        ? "Генерирую документ…"
        : undefined;

  // Micro-beats while a stage dwells — more varied phrases in the fold
  useEffect(() => {
    if (!busy || !pendingBot || pendingBot.role !== "bot") return;
    const id = pendingBot.id;
    const t = window.setInterval(() => {
      setMsgs((list) =>
        list.map((msg) => {
          if (msg.id !== id || msg.role !== "bot" || !msg.pending) return msg;
          return appendBotThinking(
            msg,
            msg.pendingStage,
            msg.pendingDetail,
            true,
          );
        }),
      );
    }, 3200);
    return () => window.clearInterval(t);
  }, [
    busy,
    pendingBot && pendingBot.role === "bot" ? pendingBot.id : null,
    pendingBot && pendingBot.role === "bot" ? pendingBot.pendingStage : null,
    pendingBot && pendingBot.role === "bot" ? pendingBot.pendingDetail : null,
  ]);

  // Use railArtifact (not activeArtifact) so preview stays mounted while closing.
  const activeReportMsg =
    railArtifact?.kind === "report"
      ? msgs.find(
          (m) =>
            m.id === railArtifact.msgId && m.role === "bot" && m.result,
        )
      : null;
  const activeReport =
    activeReportMsg && activeReportMsg.role === "bot" && activeReportMsg.result
      ? activeReportMsg.result
      : null;

  const railSourceText =
    activeArtifact?.kind === "source" || activeArtifact?.kind === "intent"
      ? activeArtifact.text
      : sourceDraft?.text ?? null;
  const railSourceTitle =
    activeArtifact?.kind === "source" || activeArtifact?.kind === "intent"
      ? activeArtifact.title
      : sourceDraft?.title ?? null;

  // Visual QA all chart types: http://127.0.0.1:5173/?preview=charts-qa
  if (/preview=charts-qa/.test(window.location.search)) {
    return <ChartsQa />;
  }

  return (
    <div
      className={`app chat-app${drag ? " is-drag" : ""}${railLayout && !narrowRail ? " has-rail" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDrag(false);
      }}
      onDrop={onDrop}
    >
      {toast && (
        <div className="liber-toast" role="status" aria-live="polite">
          <span>{toast}</span>
          {undoOffer ? (
            <button
              type="button"
              className="liber-toast-undo"
              onClick={() => void undoLastEdit()}
            >
              Отменить
            </button>
          ) : null}
        </div>
      )}

      <div className="app-shell">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((c) => !c)}
          healthReady={healthReady}
          healthLabel={healthReady ? "готово" : health ? "сервисы" : "…"}
          healthHint={paradeHint}
          imageChipLabel={imageChip.label}
          imageChipOk={imageChip.ok}
          imageChipHint={imageChip.hint}
          history={history}
          folders={folders}
          onNew={startNewReport}
          onOpenHistory={openHistoryItem}
          onTogglePin={(runId) => setHistory(togglePinHistory(runId))}
          onMoveToFolder={(runId, folderId) =>
            setHistory(moveHistoryToFolder(runId, folderId))
          }
          onCreateFolder={(name) => setFolders(createFolder(name))}
          onRenameFolder={(id, name) => setFolders(renameFolder(id, name))}
          onDeleteFolder={(id) => {
            const next = deleteFolder(id);
            setFolders(next.folders);
            setHistory(next.history);
          }}
          onSettings={() => setSettingsOpen(true)}
          busy={busy}
        />

        <div className="shell-column">
          <main className="main chat-main">
            <div
              className={`desk-split${railLayout && !narrowRail ? " is-open" : ""}`}
            >
              <div
                className={`desk chat-desk${msgs.length === 0 ? " is-empty-home" : ""}`}
              >
                <ChatMessages
                  msgs={msgs}
                  reduceMotion={reduceMotion}
                  hasStoredReport={hasStoredReport}
                  sessionTitle={chatTitle}
                  thinkingLabel={thinkingLabel}
                  workMode={workMode}
                  downloadsPulseMsgId={downloadsPulseMsgId}
                  messagesRef={messagesRef}
                  bottomRef={bottomRef}
                  onRestore={restoreLastReport}
                  onOpenSource={openSourceArtifact}
                  onOpenIntent={openIntentArtifact}
                  onOpenReport={openReportArtifact}
                  onOpenDiagram={openDiagramArtifact}
                  onOpenPresentation={openPresentationArtifact}
                  onOpenDeckSlides={openDeckSlidesArtifact}
                  onOpenFilm={(msgId, frame) => openFilmFrame(msgId, frame)}
                />

                <ChatComposer
                  busy={busy}
                  stopping={stopping}
                  canSend={canSend}
                  onStop={stopGeneration}
                  chat={chat}
                  attachPhotos={attachPhotos}
                  showPlaque={showPlaque}
                  plaqueDraft={plaqueDraft}
                  sourceDraft={sourceDraft}
                  file={file}
                  chatRef={chatRef}
                  fileRef={fileRef}
                  photoRef={photoRef}
                  workMode={workMode}
                  onWorkMode={(mode) => {
                    setWorkMode(mode);
                    if (mode !== "presentation") setDeckApplyHint(null);
                  }}
                  showModes={msgs.length === 0 && !busy}
                  showPackPresets={
                    msgs.length === 0 &&
                    !busy &&
                    workMode === "presentation"
                  }
                  showDeckStyleBtn={
                    msgs.length === 0 &&
                    !busy &&
                    workMode === "presentation"
                  }
                  deckStyle={deckStyle}
                  deckPacks={deckPacks}
                  deckApplyHint={deckApplyHint}
                  onDismissDeckApplyHint={() => setDeckApplyHint(null)}
                  onUseDeckTemplate={(next, meta) => {
                    setDeckStyle(next);
                    saveDeckStyle(next);
                    const prompt =
                      meta.starterPrompt ||
                      starterPromptForStructure(next.structureId);
                    const chatEmpty = !chat.trim();
                    if (chatEmpty) {
                      setChat(prompt);
                    }
                    setDeckApplyHint(null);
                    setToast(
                      chatEmpty
                        ? `Шаблон «${meta.title}» — правьте текст и отправьте`
                        : `Шаблон «${meta.title}» · стиль применён, текст в чате не трогали`,
                    );
                    window.setTimeout(() => setToast(null), 2800);
                    window.setTimeout(() => {
                      const el = chatRef.current;
                      if (!el) return;
                      el.focus();
                      if (chatEmpty) {
                        el.style.height = "auto";
                        el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
                      }
                    }, 0);
                  }}
                  onOpenDeckStyle={() => setDeckStyleOpen(true)}
                  deckStyleOpen={deckStyleOpen}
                  onChatChange={setChat}
                  onPasteCapture={capturePastedSource}
                  onSend={() => void send()}
                  onIngestFiles={ingestFiles}
                  onRemovePhoto={(i) =>
                    setAttachPhotos((list) => list.filter((_, j) => j !== i))
                  }
                  onOpenSource={() => {
                    if (sourceDraft) openSourceArtifact(sourceDraft);
                  }}
                  onDismissPlaque={() => {
                    setPlaqueDismissed(true);
                    setSourceDraft(null);
                    setFile(null);
                    setActiveArtifact((a) =>
                      a?.kind === "source" || a?.kind === "intent" ? null : a,
                    );
                  }}
                  onPickStarter={(prompt) => {
                    setChat(prompt);
                    chatRef.current?.focus();
                  }}
                />
              </div>

              {railArtifact && (
              <ArtifactRail
                key="artifact-rail"
                artifact={railArtifact}
                closing={railExiting}
                onClosed={finishArtifactClose}
                report={
                  activeReport
                    ? {
                        preview: activeReport.preview,
                        downloads: activeReport.downloads,
                        runId: activeReport.run_id,
                        warnings: activeReport.warnings,
                        diagrams: activeReport.diagrams,
                        slidesStatus: activeReport.slides_status,
                        slidesStage: activeReport.slides_stage,
                        slidesError: activeReport.slides_error,
                        slidePngs: activeReport.slide_pngs,
                        deck: activeReport.deck,
                        deckPdfMode: activeReport.deck_pdf_mode,
                        outputMode: activeReport.output_mode,
                        onDeckUpdated: (deck, pngs) => {
                          if (!activeReportMsg || activeReportMsg.role !== "bot")
                            return;
                          const mid = activeReportMsg.id;
                          setMsgs((m) =>
                            m.map((msg) => {
                              if (msg.id !== mid || msg.role !== "bot" || !msg.result)
                                return msg;
                              return {
                                ...msg,
                                result: {
                                  ...msg.result,
                                  deck,
                                  slide_pngs: pngs,
                                  slides_status: "ok",
                                },
                              };
                            }),
                          );
                        },
                      }
                    : null
                }
                sourceText={railSourceText}
                sourceTitle={railSourceTitle}
                palettes={palettes}
                catalogTypes={catalog}
                defaultPalette={chartPalette}
                editingFigureId={
                  railArtifact.kind === "report" &&
                  editBusy?.msgId === railArtifact.msgId
                    ? editBusy.figureId
                    : null
                }
                editError={
                  railArtifact.kind === "report" &&
                  editError?.msgId === railArtifact.msgId
                    ? editError.message
                    : null
                }
                editErrorFigureId={
                  railArtifact.kind === "report" &&
                  editError?.msgId === railArtifact.msgId
                    ? editError.figureId
                    : null
                }
                downloadsPulse={
                  railArtifact.kind === "report" &&
                  downloadsPulseMsgId === railArtifact.msgId
                }
                narrow={narrowRail}
                widthPct={railWidthPct}
                onWidthChange={setRailWidthPct}
                onTab={setArtifactTab}
                onSelectDiagram={
                  railArtifact.kind === "report" ? selectDiagram : undefined
                }
                makingPresentation={
                  activeReport?.slides_status === "queued" ||
                  activeReport?.slides_status === "running" ||
                  activeReport?.slides_status === "starting"
                }
                onClose={closeArtifact}
                onEditCancel={() => {
                  if (
                    railArtifact.kind === "report" &&
                    editError?.msgId === railArtifact.msgId
                  ) {
                    setEditError(null);
                  }
                }}
                onEditFigure={
                  railArtifact.kind === "report" && activeReport
                    ? (req) =>
                        editFigure(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onEditImage={
                  railArtifact.kind === "report" && activeReport
                    ? (req) =>
                        editImage(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onEditTable={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (req) =>
                        editTable(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onEditParagraph={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (req) =>
                        editParagraph(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onDiagramsUpdated={
                  railArtifact.kind === "report" && activeReportMsg
                    ? (diagrams) => {
                        const mid = activeReportMsg.id;
                        setMsgs((list) =>
                          list.map((msg) => {
                            if (
                              msg.id !== mid ||
                              msg.role !== "bot" ||
                              !msg.result
                            )
                              return msg;
                            const next = {
                              ...msg,
                              result: { ...msg.result, diagrams },
                            };
                            if (next.result) rememberRun(next.result);
                            return next;
                          }),
                        );
                        setActiveArtifact((prev) => {
                          if (!prev || prev.kind !== "report") return prev;
                          const keep =
                            diagrams.find((d) => d.id === prev.activeDiagramId)
                              ?.id ??
                            diagrams[0]?.id ??
                            null;
                          return { ...prev, activeDiagramId: keep };
                        });
                        setToast("Схема обновлена");
                        window.setTimeout(() => setToast(null), 2200);
                      }
                    : undefined
                }
              />
              )}
            </div>
          </main>
        </div>
      </div>

      <DeckStyleSheet
        open={deckStyleOpen}
        style={deckStyle}
        packs={deckPacks}
        onChange={setDeckStyle}
        onClose={() => setDeckStyleOpen(false)}
        onSave={(s) => {
          setDeckStyle(s);
          saveDeckStyle(s);
          setToast("Стиль презентации сохранён");
          window.setTimeout(() => setToast(null), 2200);
        }}
      />

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        maxCharts={maxCharts}
        onMaxCharts={setMaxCharts}
        maxImages={maxImages}
        onMaxImages={setMaxImages}
        maxDiagrams={maxDiagrams}
        onMaxDiagrams={setMaxDiagrams}
        forbidCharts={forbidCharts}
        onForbidCharts={setForbidCharts}
        forbidImages={forbidImages}
        onForbidImages={setForbidImages}
        dryRun={dryRun}
        onDryRun={setDryRun}
        health={health}
        paradeHint={
          health?.vision_configured && health?.docker_ok
            ? `Готово: ${paradeHint}`
            : `Сейчас: ${paradeHint}`
        }
      />
    </div>
  );
}
