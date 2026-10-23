/** Liber Atelier — chat-first desk shell (orchestration only). */

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
} from "./ArtifactRail";
import type { ChartEditRequest } from "./ChartEditSheet";
import type { ImageEditRequest } from "./ImageEditModal";
import { ChatComposer } from "./ChatComposer";
import { ChatMessages } from "./ChatMessages";
import { ChartsQa } from "./ChartsQa";
import {
  DEFAULT_INTENT,
  FALLBACK_PALETTES,
  FALLBACK_TYPES,
  LONG_TEXT_CHARS,
} from "./liberConstants";
import { modeToOutputMode, type LiberWorkMode } from "./liberModes";
import {
  appendBotThinking,
  formatApiDetailError,
  formatBytes,
  formatRunStatusError,
  openSummaryStream,
  paradeHintFromHealth,
  readTextFile,
  reportReadyText,
  reportTitle,
  stageLabel,
  uid,
} from "./liberRunHelpers";
import type {
  Health,
  Msg,
  PaletteInfo,
  RunResult,
  SourceAttachment,
  SourceDraft,
} from "./liberTypes";
import {
  loadHistory,
  loadHistoryPayload,
  pushHistory,
  saveRunPayload,
} from "./reportHistory";
import { DeckStyleSheet } from "./DeckStyleSheet";
import {
  deckStyleToApiPayload,
  loadDeckStyle,
  saveDeckStyle,
  type DeckStyle,
  type DeckThemePackInfo,
  FALLBACK_DECK_PACKS,
} from "./deckStyle";
import { starterPromptForStructure } from "./deckTemplates";
import { SettingsModal } from "./SettingsModal";
import { Sidebar, type HistoryItem } from "./Sidebar";
import { loadRailWidth } from "./railWidth";
import { useLiberDevPreviews } from "./useLiberDevPreviews";

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
  const [downloadsPulseMsgId, setDownloadsPulseMsgId] = useState<string | null>(
    null,
  );
  const [deckStyle, setDeckStyle] = useState<DeckStyle>(() => loadDeckStyle());
  const [deckStyleOpen, setDeckStyleOpen] = useState(false);
  const [workMode, setWorkMode] = useState<LiberWorkMode>(null);
  const [deckApplyHint, setDeckApplyHint] = useState<string | null>(null);
  const [deckPacks, setDeckPacks] =
    useState<DeckThemePackInfo[]>(FALLBACK_DECK_PACKS);
  const [hasStoredReport, setHasStoredReport] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(() => loadHistory());
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
    // Don't yank the chat while the user is reading earlier messages.
    if (!stickBottom.current) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
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
      setMsgs((list) =>
        list.map((msg) => {
          if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
          const next = {
            ...msg,
            // Keep chat summary — only refresh artifacts (toast signals edit).
            result: {
              ...msg.result,
              preview: data.preview ?? msg.result.preview,
              downloads: data.downloads ?? msg.result.downloads,
              warnings:
                Array.isArray(data.warnings) && data.warnings.length
                  ? data.warnings
                  : msg.result.warnings,
              media_status: data.media_status ?? msg.result.media_status,
            },
          };
          if (next.result) rememberRun(next.result);
          return next;
        }),
      );
      setToast("Отчёт обновлён");
      setDownloadsPulseMsgId(msgId);
      window.setTimeout(() => setToast(null), 2800);
      window.setTimeout(() => setDownloadsPulseMsgId(null), 2200);
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
      setMsgs((list) =>
        list.map((msg) => {
          if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
          const next = {
            ...msg,
            // Keep chat summary — only refresh artifacts (как правка графика).
            result: {
              ...msg.result,
              preview: data.preview ?? msg.result.preview,
              downloads: data.downloads ?? msg.result.downloads,
              warnings:
                Array.isArray(data.warnings) && data.warnings.length
                  ? data.warnings
                  : msg.result.warnings,
              media_status: data.media_status ?? msg.result.media_status,
            },
          };
          if (next.result) rememberRun(next.result);
          return next;
        }),
      );
      setToast(
        req.mode === "edit" ? "Фото изменено" : "Фото сгенерировано заново",
      );
      setDownloadsPulseMsgId(msgId);
      window.setTimeout(() => setToast(null), 2800);
      window.setTimeout(() => setDownloadsPulseMsgId(null), 2200);
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

  function openReportArtifact(msgId: string, result: RunResult, tab?: ArtifactTab) {
    const preferPdf = Boolean(result.downloads?.pdf);
    const preferPreview = Boolean(result.preview?.blocks?.length);
    const nextTab: ArtifactTab =
      tab ??
      (preferPdf ? "pdf" : preferPreview ? "preview" : "source");
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

  async function makePresentation(msgId: string, result: RunResult) {
    const runId = result.run_id;
    if (!runId) return;
    openReportArtifact(msgId, result, "presentation");
    setMsgs((m) =>
      m.map((msg) => {
        if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
        return {
          ...msg,
          result: {
            ...msg.result,
            slides_status: "queued",
            slides_stage: "queued",
            slides_error: null,
          },
        };
      }),
    );
    try {
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
      const deadline = Date.now() + 10 * 60 * 1000;
      for (;;) {
        if (Date.now() > deadline) {
          throw new Error("таймаут сборки презентации (10 мин)");
        }
        await new Promise((r) => setTimeout(r, 500));
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
        if (slidesStatus === "ok" || slidesStatus === "error") {
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
            // Always surface the deck in the side rail when ready.
            openReportArtifact(
              msgId,
              {
                ...result,
                downloads: { ...result.downloads, ...downloads },
                slides_status: slidesStatus,
                slides_stage: slidesStage,
                slides_error: slidesError,
                slide_pngs: slidePngs,
                deck: deckIr,
                deck_pdf_mode: deckPdfMode,
              },
              "presentation",
            );
          }
          break;
        }
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== msgId || msg.role !== "bot" || !msg.result)
              return msg;
            return {
              ...msg,
              result: {
                ...msg.result,
                slides_status: slidesStatus,
                slides_stage: slidesStage,
              },
            };
          }),
        );
      }
    } catch (err) {
      setMsgs((m) =>
        m.map((msg) => {
          if (msg.id !== msgId || msg.role !== "bot" || !msg.result) return msg;
          return {
            ...msg,
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
      // source / intent only expose the Source tab
      return { ...prev, tab: "source" };
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
      setMsgs([
        {
          id,
          role: "bot",
          text: reportReadyText(result),
          result,
        },
      ]);
      openReportArtifact(id, result);
    } catch {
      /* ignore */
    }
  }

  function startNewReport() {
    setMsgs([]);
    setChat("");
    setFile(null);
    setSourceDraft(null);
    setAttachPhotos([]);
    setRailExiting(false);
    setActiveArtifact(null);
    setPlaqueDismissed(false);
    setEditError(null);
    setHistoryOpen(false);
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
    setMsgs([
      {
        id,
        role: "bot",
        text: reportReadyText(result),
        result,
      },
    ]);
    openReportArtifact(id, result);
    setHistoryOpen(false);
  }

  function rememberRun(result: RunResult) {
    saveRunPayload(result);
    const title = reportTitle(result);
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

    const pendingId = uid();
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
        },
        "queued",
        null,
      ),
    ]);
    setBusy(true);
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
    }

    try {
      const res = await fetch("/api/run", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          formatApiDetailError(data as Record<string, unknown>, res.statusText),
        );
      }

      // Sync photo-edit response (no poll)
      if (data.mode === "photo_edit" && data.status === "ok") {
        const result = data as RunResult;
        setMsgs((m) =>
          m.map((msg) =>
            msg.id === pendingId
              ? {
                  ...msg,
                  text: data.caption || "Фото изменено",
                  pending: false,
                  result,
                }
              : msg,
          ),
        );
        setToast("Фото изменено");
        window.setTimeout(() => setToast(null), 2800);
        return;
      }

      let result = data as RunResult;

      // 202 async job: poll until ok/error
      if (res.status === 202 || data.status === "started" || data.status === "running") {
        const runId = data.run_id as string;
        if (!runId) throw new Error("server did not return run_id");
        setMsgs((m) =>
          m.map((msg) => {
            if (msg.id !== pendingId || msg.role !== "bot") return msg;
            const stage = data.stage || "queued";
            return appendBotThinking(
              {
                ...msg,
                text: stageLabel(stage),
                pending: true,
                pendingStage: stage,
                pendingDetail: null,
              },
              stage,
              null,
            );
          }),
        );
        const pollStarted = Date.now();
        const pollDeadlineMs = 20 * 60 * 1000;
        let soft404 = 0;
        let stopSummary: (() => void) | null = null;
        let streamedSummary = "";
        let summaryStreamStarted = false;
        try {
          for (;;) {
            if (Date.now() - pollStarted > pollDeadlineMs) {
              throw new Error(
                `таймаут ожидания run ${runId} (20 мин) — смотри runs/logs/${runId}`,
              );
            }
            await new Promise((r) => setTimeout(r, 400));
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
            const summaryStatus = body.summary_status as string | undefined;
            const shouldStream =
              !summaryStreamStarted &&
              (stage === "latex" ||
                stage === "docx" ||
                summaryStatus === "streaming" ||
                summaryStatus === "ok");
            if (shouldStream) {
              summaryStreamStarted = true;
              stopSummary = openSummaryStream(
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
            if (body.status === "running" || body.status === "started") {
              setMsgs((m) =>
                m.map((msg) => {
                  if (msg.id !== pendingId || msg.role !== "bot") return msg;
                  const next = appendBotThinking(
                    {
                      ...msg,
                      pending: true,
                      pendingStage: stage,
                      pendingDetail: detail,
                      text:
                        msg.streamingSummary && msg.text.trim()
                          ? msg.text
                          : stageLabel(stage || "queued", detail),
                    },
                    stage,
                    detail,
                  );
                  return next;
                }),
              );
              continue;
            }
            if (body.status === "error") {
              throw new Error(
                formatRunStatusError(body as Record<string, unknown>, runId),
              );
            }
            result = body as RunResult;
            break;
          }
        } finally {
          stopSummary?.();
        }
      }

      try {
        if (
          result.preview?.blocks?.length ||
          result.downloads?.pdf ||
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
          return {
            id: pendingId,
            role: "bot" as const,
            text: reportReadyText(result, streamed),
            result,
            thinking: msg.thinking,
            thinkingStartedAt: msg.thinkingStartedAt,
            thinkingElapsedSec: msg.thinkingStartedAt
              ? Math.max(
                  0,
                  Math.round((Date.now() - msg.thinkingStartedAt) / 1000),
                )
              : undefined,
          };
        }),
      );
      const isDiagramOnly =
        result.output_mode === "diagram" ||
        (workMode === "diagram" &&
          Boolean(result.diagrams?.length) &&
          !result.downloads?.pdf);
      const isPresentationOnly =
        outMode === "presentation" || result.output_mode === "presentation";
      if (isPresentationOnly && result.run_id) {
        openPresentationArtifact(pendingId, result);
        void makePresentation(pendingId, result);
      } else if (isDiagramOnly && result.diagrams?.length) {
        openDiagramArtifact(pendingId, result, result.diagrams[0].id);
      } else if (result.preview?.blocks?.length || result.downloads?.pdf) {
        openReportArtifact(pendingId, result);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setMsgs((m) =>
        m.map((msg) =>
          msg.id === pendingId
            ? { id: pendingId, role: "bot", text: "Ошибка", error: message }
            : msg,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  const paradeHint = paradeHintFromHealth(health);

  const healthReady = Boolean(
    health?.vision_configured && health?.docker_ok && health?.playwright_ok,
  );

  const plaqueDraft = sourceDraft
    ? {
        title: sourceDraft.title,
        subtitle: file
          ? formatBytes(file.size)
          : `${sourceDraft.text.length} символов`,
      }
    : null;
  const showPlaque = Boolean(plaqueDraft && !plaqueDismissed);

  const railOpen = Boolean(activeArtifact);
  const railLayout = railOpen || railExiting;
  const railArtifact = activeArtifact ?? (railExiting ? lastArtifactRef.current : null);
  const pendingBot = msgs.find((m) => m.role === "bot" && m.pending);
  const thinkingLabel =
    pendingBot && pendingBot.role === "bot"
      ? stageLabel(pendingBot.pendingStage, pendingBot.pendingDetail)
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
          {toast}
        </div>
      )}

      <div className="app-shell">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((c) => !c)}
          healthReady={healthReady}
          healthLabel={healthReady ? "готово" : health ? "сервисы" : "…"}
          healthHint={paradeHint}
          history={history}
          historyOpen={historyOpen}
          onHistoryOpen={setHistoryOpen}
          onNew={startNewReport}
          onOpenHistory={openHistoryItem}
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
                  onMakePresentation={makePresentation}
                  onOpenPresentation={openPresentationArtifact}
                  onDeckStyle={() => setDeckStyleOpen(true)}
                />

                <ChatComposer
                  busy={busy}
                  canSend={canSend}
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
                  showModes
                  showPackPresets={
                    msgs.length === 0 && workMode === "presentation"
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
                onMakePresentation={
                  railArtifact.kind === "report" && activeReport
                    ? () =>
                        void makePresentation(
                          railArtifact.msgId,
                          activeReport,
                        )
                    : undefined
                }
                makingPresentation={
                  activeReport?.slides_status === "queued" ||
                  activeReport?.slides_status === "running"
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
