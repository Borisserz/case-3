/** Liber Atelier — chat-first desk shell (orchestration only). */

/* premium-home-bust */
import {
  lazy,
  Suspense,
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
import { ChatComposer } from "../ChatComposer";
import { ChatMessages } from "../ChatMessages";
import { useLiberEdits } from "./useLiberEdits";
import { useMakePresentation } from "./useMakePresentation";
import { useResumeFailedRun } from "./useResumeFailedRun";
import { useLiberRun } from "./useLiberRun";

const ChartsQa = lazy(() =>
  import("../ChartsQa").then((m) => ({ default: m.ChartsQa })),
);
import { type CraftFilmFrame } from "../domain/craftSteps";
import {
  FALLBACK_PALETTES,
  FALLBACK_TYPES,
  LONG_TEXT_CHARS,
} from "../domain/liberConstants";
import { type LiberWorkMode } from "../domain/liberModes";
import {
  appendBotThinking,
  formatBytes,
  imageChipFromHealth,
  paradeHintFromHealth,
  readTextFile,
  reportReadyText,
  reportTitle,
  stageLabel,
  uid,
} from "../domain/runHelpers";
import type {
  Health,
  Msg,
  PaletteInfo,
  RunResult,
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
  // Chart type/style/title: model + ChartEditSheet (not Settings).
  const chartPalette = "atelier";
  const [maxCharts, setMaxCharts] = useState(2);
  const [maxDiagrams, setMaxDiagrams] = useState(2);
  const [maxImages, setMaxImages] = useState(2);
  const [forbidCharts, setForbidCharts] = useState(false);
  /** Photos on by default; health may raise budget / confirm Image API. */
  const [forbidImages, setForbidImages] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [chat, setChat] = useState("");
  /** Liber-attached photos for document figure slots. */
  const [attachPhotos, setAttachPhotos] = useState<File[]>([]);
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

  const { editFigure, editImage, editTable, editParagraph, undoLastEdit } =
    useLiberEdits({
      applyEditPayload,
      setEditBusy,
      setEditError,
      setUndoOffer,
      setToast,
      undoOffer,
      undoBusyRef,
    });

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

  const makePresentation = useMakePresentation({
    deckStyle,
    setMsgs,
    setBusy,
    setRailExiting,
    setActiveArtifact,
    setDownloadsPulseMsgId,
    cancelRequestedRef,
    activeRunIdRef,
    pendingBotIdRef,
  });
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

  const resumeFailedRun = useResumeFailedRun({
    busy,
    setBusy,
    setStopping,
    setMsgs,
    setChatTitle,
    setHasStoredReport,
    cancelRequestedRef,
    activeRunIdRef,
    rememberRun,
    openReportArtifact,
  });

  const paradeHint = paradeHintFromHealth(health);
  const imageChip = imageChipFromHealth(health);

  const canSend = useMemo(() => {
    if (busy) return false;
    const hasSource = Boolean(file) || Boolean(sourceDraft?.text);
    const chatTrim = chat.trim();
    // Any scale brief is fine — do not gate presentation/diagram on Source length.
    return hasSource || chatTrim.length > 0;
  }, [file, busy, chat, sourceDraft]);

  const send = useLiberRun({
    canSend,
    chat,
    sourceDraft,
    file,
    health,
    imageChip,
    workMode,
    deckStyle,
    attachPhotos,
    forbidCharts,
    forbidImages,
    maxCharts,
    maxImages,
    maxDiagrams,
    dryRun,
    setMsgs,
    setBusy,
    setStopping,
    setChat,
    setChatTitle,
    setSourceDraft,
    setAttachPhotos,
    setHasStoredReport,
    setToast,
    setDeckApplyHint,
    setRailExiting,
    setActiveArtifact,
    chatRef,
    cancelRequestedRef,
    activeRunIdRef,
    pendingBotIdRef,
    rememberRun,
    openReportArtifact,
    openDiagramArtifact,
    makePresentation,
  });

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
    return (
      <Suspense fallback={<div className="app chat-app">Charts QA…</div>}>
        <ChartsQa />
      </Suspense>
    );
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
                  onResumeRun={resumeFailedRun}
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
