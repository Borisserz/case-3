/** Liber Atelier — chat-first desk shell (orchestration only). */

/* premium-home-bust */
import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useReducedMotion } from "framer-motion";
import { ArtifactRail } from "../ArtifactRail";
import { ConfirmProvider } from "../ConfirmModal";
import { ChatComposer } from "../ChatComposer";
import { carriedArtifactId, memoryStripLine } from "../domain/memoryStrip";
import { LiberHelp } from "../LiberHelp";
import { ChatMessages } from "../ChatMessages";
import { ChartsQa } from "../lazyChartsQa";
import { IconPanelRight } from "../icons";
import { useLiberEdits } from "./useLiberEdits";
import { useMakePresentation } from "./useMakePresentation";
import { useResumeFailedRun } from "./useResumeFailedRun";
import { useLiberRun } from "./useLiberRun";
import {
  FALLBACK_PALETTES,
  FALLBACK_TYPES,
} from "../domain/liberConstants";
import { type LiberWorkMode } from "../domain/liberModes";
import {
  appendBotThinking,
  formatBytes,
  imageChipFromHealth,
  paradeHintFromHealth,
  stageLabel,
} from "../domain/runHelpers";
import type {
  Health,
  Msg,
  PaletteInfo,
  SourceAttachment,
  SourceDraft,
} from "../domain/liberTypes";
import { useArtifactHost } from "./useArtifactHost";
import { useDeskBootstrap } from "./useDeskBootstrap";
import { useChatChrome } from "./useChatChrome";
import { useReportSession } from "./useReportSession";
import { useSourceIngest } from "./useSourceIngest";
import { useStopGeneration } from "./useStopGeneration";
import { useLiberToast } from "./useLiberToast";
import { LiberToastBar } from "./LiberToastBar";
import { applyDiagramsUpdate } from "./applyDiagramsUpdate";
import { useReportHistory } from "./useReportHistory";
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
  const [chartPalette, setChartPalette] = useState<string>(() => {
    try {
      return localStorage.getItem("liber.chartPalette.v1") || "atelier";
    } catch {
      return "atelier";
    }
  });
  const [maxCharts, setMaxCharts] = useState(2);
  const [maxDiagrams, setMaxDiagrams] = useState(5);
  const [maxDiagramsCap, setMaxDiagramsCap] = useState(5);
  const [maxImages, setMaxImages] = useState(2);
  const [targetSlides, setTargetSlides] = useState(() => {
    try {
      const n = Number(localStorage.getItem("liber.slidesTarget.v1"));
      if (Number.isFinite(n) && n >= 6 && n <= 24) return Math.round(n);
    } catch {
      /* ignore */
    }
    return 12;
  });
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
  const { toast, toastTone, setToast, showToast } = useLiberToast();
  /** B21 / session stack: undo after Liber edit */
  const [undoOffer, setUndoOffer] = useState<{
    msgId: string;
    runId: string;
  } | null>(null);
  const undoBusyRef = useRef(false);
  const [editHistory, setEditHistory] = useState({
    canUndo: false,
    canRedo: false,
    depth: 0,
  });
  const [reportEditMode, setReportEditMode] = useState(false);
  const [deckDocsDirty, setDeckDocsDirty] = useState(false);
  const [downloadsPulseMsgId, setDownloadsPulseMsgId] = useState<string | null>(
    null,
  );
  const [deckStyle, setDeckStyle] = useState<DeckStyle>(() => loadDeckStyle());
  const [deckStyleOpen, setDeckStyleOpen] = useState(false);
  const [workMode, setWorkMode] = useState<LiberWorkMode>(null);
  /** Julius chat rename — column head only; seeded then → preview.title */
  const [chatTitle, setChatTitle] = useState<string | null>(null);
  const [deckApplyHint, setDeckApplyHint] = useState<string | null>(null);
  const [deckPacks, setDeckPacks] =
    useState<DeckThemePackInfo[]>(FALLBACK_DECK_PACKS);
  const [hasStoredReport, setHasStoredReport] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // history / folders / sidebar → useReportHistory (below, after busy)
  /** Text of attached .txt/.md for Source tab / plaque. */
  const [sourceDraft, setSourceDraft] = useState<SourceDraft | null>(null);
  const [plaqueDismissed, setPlaqueDismissed] = useState(false);
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

  const {
    activeArtifact,
    setActiveArtifact,
    narrowRail,
    railWidthPct,
    setRailWidthPct,
    railExiting,
    setRailExiting,
    railCollapsed,
    setRailCollapsed,
    railLayout,
    railArtifact,
    openReportArtifact,
    openDiagramArtifact,
    openPresentationArtifact,
    openDeckSlidesArtifact,
    openFilmFrame,
    openUserPhoto,
    openSourceArtifact,
    openIntentArtifact,
    closeArtifact,
    finishArtifactClose,
    reopenRail,
    setArtifactTab,
    selectDiagram,
  } = useArtifactHost({ msgs, activeRunIdRef });

  const resetSurfaceForHistory = useCallback(() => {
    setReportEditMode(false);
    setActiveArtifact(null);
    setRailCollapsed(false);
    setRailExiting(false);
  }, [setActiveArtifact, setRailCollapsed, setRailExiting]);

  const {
    sidebarCollapsed,
    setSidebarCollapsed,
    history,
    folders,
    rememberRun,
    openHistoryItem,
    onTogglePin,
    onMoveToFolder,
    onCreateFolder,
    onRenameFolder,
    onDeleteFolder,
  } = useReportHistory({
    busy,
    setMsgs,
    setChatTitle,
    showToast,
    openReportArtifact,
    onResetSurface: resetSurfaceForHistory,
    onRestoreSource: setSourceDraft,
  });

  const memoryLine = useMemo(() => {
    let turn = 0;
    let section = "";
    for (const msg of msgs) {
      if (msg.role !== "bot" || !msg.result || msg.result.isolated) continue;
      if (typeof msg.result.turn_count === "number") turn = msg.result.turn_count;
      if (msg.result.memory_section) section = msg.result.memory_section;
    }
    const documents = sourceDraft?.parts?.length || (sourceDraft?.text?.trim() ? 1 : 0);
    return memoryStripLine({ documents, section, turn });
  }, [msgs, sourceDraft]);

  const catalog = useMemo(() => {
    const fromApi = health?.chart_types?.filter(Boolean);
    return fromApi && fromApi.length > 0 ? fromApi : [...FALLBACK_TYPES];
  }, [health]);

  const reduceMotion = useReducedMotion();

  const palettes = useMemo<PaletteInfo[]>(() => {
    if (health?.chart_palettes?.length) return health.chart_palettes;
    return FALLBACK_PALETTES;
  }, [health]);

  useDeskBootstrap({
    setHealth,
    setMaxCharts,
    setMaxDiagrams,
    setMaxDiagramsCap,
    setMaxImages,
    setForbidImages,
    setDeckPacks,
  });

  useChatChrome({
    chatTitle,
    msgs,
    chat,
    messagesRef,
    bottomRef,
    chatRef,
    stickBottom,
    setHasStoredReport,
  });

  useLiberDevPreviews({
    setMsgs,
    setBusy,
    setSourceDraft,
    setActiveArtifact,
  });

  const {
    editFigure,
    recolorCharts,
    uploadFigure,
    deleteFigure,
    editImage,
    editTable,
    editParagraph,
    insertParagraph,
    editHeading,
    editTitle,
    editList,
    undoLastEdit,
    undoEdit,
    redoEdit,
    clearEditHistory,
    discardEdits,
    finishEditSession,
  } =
    useLiberEdits({
      setMsgs,
      rememberRun,
      setEditBusy,
      setEditError,
      setUndoOffer,
      setToast,
      setDownloadsPulseMsgId,
      setEditHistory,
      undoOffer,
      undoBusyRef,
    });
  const [finishEditBusy, setFinishEditBusy] = useState(false);


  const stopGeneration = useStopGeneration({
    stopping,
    setStopping,
    setBusy,
    setMsgs,
    cancelRequestedRef,
    activeRunIdRef,
    pendingBotIdRef,
  });

  const makePresentation = useMakePresentation({
    deckStyle,
    setMsgs,
    setBusy,
    setRailExiting,
    setRailCollapsed,
    setActiveArtifact,
    setDownloadsPulseMsgId,
    cancelRequestedRef,
    activeRunIdRef,
    pendingBotIdRef,
  });


  const { restoreLastReport, startNewReport } = useReportSession({
    setMsgs,
    setChatTitle,
    setChat,
    setFile,
    setSourceDraft,
    setAttachPhotos,
    setRailExiting,
    setRailCollapsed,
    setActiveArtifact,
    setPlaqueDismissed,
    setEditError,
    chatRef,
  });

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
    composer: {
      canSend,
      chat,
      sourceDraft,
      file,
      attachPhotos,
      forbidCharts,
      forbidImages,
      maxCharts,
      maxImages,
      maxDiagrams,
      targetSlides,
      dryRun,
      workMode,
      deckStyle,
      chartPalette,
      chatRef,
      setChat,
      setChatTitle,
      setSourceDraft,
      setAttachPhotos,
    },
    desk: {
      health,
      imageChip,
      msgs,
      setMsgs,
      setBusy,
      setStopping,
      setHasStoredReport,
      setToast,
      setDeckApplyHint,
      setRailExiting,
      setRailCollapsed,
      setActiveArtifact,
    },
    runRefs: {
      cancelRequestedRef,
      activeRunIdRef,
      pendingBotIdRef,
      rememberRun,
      openReportArtifact,
      openDiagramArtifact,
      makePresentation,
    },
  });

  const { capturePastedSource, ingestFiles, onDrop } = useSourceIngest({
    setFile,
    setSourceDraft,
    setPlaqueDismissed,
    setDeckApplyHint,
    setActiveArtifact,
    setAttachPhotos,
    setForbidImages,
    setMaxImages,
    setDrag,
    showToast,
  });

  const healthReady = Boolean(
    health?.vision_ok && health?.docker_ok && health?.playwright_ok,
  );

  const plaqueDraft = sourceDraft
    ? {
        title: sourceDraft.title,
        subtitle:
          sourceDraft.viewMode === "document"
            ? sourceDraft.previewUrl
              ? "Документ · просмотр"
              : "Документ · без PDF-превью"
            : file
              ? formatBytes(file.size)
              : `${sourceDraft.text.length.toLocaleString("ru-RU")} символов`,
        fileName: sourceDraft.fileName,
      }
    : null;
  const showPlaque = Boolean(plaqueDraft && !plaqueDismissed);

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
  useEffect(() => {
    setDeckDocsDirty(false);
  }, [activeReport?.run_id]);

  const railSourceText =
    activeArtifact?.kind === "source" || activeArtifact?.kind === "intent"
      ? activeArtifact.text
      : sourceDraft?.text ?? null;
  const railSourceTitle =
    activeArtifact?.kind === "source" || activeArtifact?.kind === "intent"
      ? activeArtifact.title
      : sourceDraft?.title ?? null;
  /** User Source plaque for this report — keep PDF on «Документ» tab after send. */
  const reportSourceAttachment = useMemo((): SourceAttachment | null => {
    if (railArtifact?.kind !== "report") return null;
    const idx = msgs.findIndex((m) => m.id === railArtifact.msgId);
    if (idx < 0) return null;
    for (let i = idx - 1; i >= 0; i--) {
      const m = msgs[i];
      if (m.role === "user" && m.attachment) return m.attachment;
      if (m.role === "bot") break;
    }
    return null;
  }, [railArtifact, msgs]);

  // Visual QA all chart types: http://127.0.0.1:5173/?preview=charts-qa
  if (/preview=charts-qa/.test(window.location.search)) {
    return (
      <Suspense fallback={<div className="app chat-app">Charts QA…</div>}>
        <ChartsQa />
      </Suspense>
    );
  }

  return (
    <ConfirmProvider>
      <div
        className={`app chat-app${drag ? " is-drag" : ""}${railLayout && !narrowRail ? " has-rail" : ""}`}
      onDragOver={(e) => {
        if (e.target instanceof Element && e.target.closest(".stimul-modal")) {
          return;
        }
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDrag(false);
      }}
      onDrop={(e) => {
        if (e.target instanceof Element && e.target.closest(".stimul-modal")) {
          return;
        }
        onDrop(e);
      }}
    >
      <LiberToastBar
        toast={toast}
        toastTone={toastTone}
        undoOffer={reportEditMode ? null : undoOffer}
        onUndo={() => void undoLastEdit()}
      />

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
          onNew={() => {
            startNewReport();
            setWorkMode(null);
            setDeckApplyHint(null);
          }}
          onOpenHistory={(item) => {
            setWorkMode(null);
            setDeckApplyHint(null);
            openHistoryItem(item);
          }}
          onTogglePin={onTogglePin}
          onMoveToFolder={onMoveToFolder}
          onCreateFolder={onCreateFolder}
          onRenameFolder={onRenameFolder}
          onDeleteFolder={onDeleteFolder}
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
                <LiberHelp />
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
                  onOpenPhoto={openUserPhoto}
                  onResumeRun={resumeFailedRun}
                  onNewChat={(kind) => {
                    startNewReport({
                      keepSource: kind === "documents",
                      carryRunId: kind === "documents" ? carriedArtifactId(msgs) : "",
                    });
                    setWorkMode(null);
                    setDeckApplyHint(null);
                  }}
                  deckDownloadsBlockedMsgId={
                    deckDocsDirty && activeReportMsg?.role === "bot"
                      ? activeReportMsg.id
                      : null
                  }
                />

                <ChatComposer
                  busy={busy}
                  stopping={stopping}
                  canSend={canSend}
                  onStop={stopGeneration}
                  chat={chat}
                  attachPhotos={attachPhotos}
                  onPreviewPhoto={openUserPhoto}
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
                  memoryLine={memoryLine}
                  showPackPresets={
                    msgs.length === 0 &&
                    !busy &&
                    workMode === "presentation"
                  }
                  showDeckStyleBtn={
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
                    showToast(
                      chatEmpty
                        ? `Шаблон «${meta.title}» — правьте текст и отправьте`
                        : `Шаблон «${meta.title}» · стиль применён, текст в чате не трогали`,
                    );
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
                        onDeckUpdated: (deck, pngs, extras) => {
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
                                  downloads: {
                                    ...(msg.result.downloads || {}),
                                    ...(extras?.downloads || {}),
                                  },
                                  ...(extras?.diagrams
                                    ? { diagrams: extras.diagrams }
                                    : {}),
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
                sourceAttachment={reportSourceAttachment}
                sourceEditable={
                  Boolean(sourceDraft) &&
                  railArtifact.kind !== "intent" &&
                  sourceDraft?.viewMode !== "document"
                }
                onSourceTextChange={(next) => {
                  setSourceDraft((d) =>
                    d && d.viewMode !== "document" ? { ...d, text: next } : d,
                  );
                  setActiveArtifact((a) =>
                    a?.kind === "source" && a.viewMode !== "document"
                      ? { ...a, text: next }
                      : a,
                  );
                }}
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
                deckDownloadsBlocked={deckDocsDirty}
                onDeckDownloadsBlockedChange={setDeckDocsDirty}
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
                onRecolorCharts={
                  railArtifact.kind === "report" && activeReport
                    ? (palette) =>
                        recolorCharts(
                          railArtifact.msgId,
                          activeReport.run_id,
                          palette,
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
                onUploadFigure={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (figureId, file, caption) =>
                        uploadFigure(
                          railArtifact.msgId,
                          activeReport.run_id,
                          figureId,
                          file,
                          caption,
                        )
                    : undefined
                }
                onDeleteFigure={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (figureId) =>
                        deleteFigure(
                          railArtifact.msgId,
                          activeReport.run_id,
                          figureId,
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
                onInsertParagraph={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (req) =>
                        insertParagraph(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onEditHeading={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (req) =>
                        editHeading(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onEditTitle={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (text) =>
                        editTitle(
                          railArtifact.msgId,
                          activeReport.run_id,
                          text,
                        )
                    : undefined
                }
                editHistory={editHistory}
                onHistoryUndo={
                  railArtifact.kind === "report" && activeReport?.run_id
                    ? () =>
                        undoEdit(railArtifact.msgId, activeReport.run_id)
                    : undefined
                }
                onHistoryRedo={
                  railArtifact.kind === "report" && activeReport?.run_id
                    ? () =>
                        redoEdit(railArtifact.msgId, activeReport.run_id)
                    : undefined
                }
                onClearEditHistory={
                  activeReport?.run_id
                    ? () => clearEditHistory(activeReport.run_id)
                    : undefined
                }
                onEditHistory={setEditHistory}
                reportEditMode={reportEditMode}
                finishReportEditBusy={finishEditBusy}
                onReportEditModeChange={setReportEditMode}
                onFinishReportEdit={
                  railArtifact.kind === "report" && activeReport?.run_id
                    ? async () => {
                        setFinishEditBusy(true);
                        try {
                          const ok = await finishEditSession(
                            railArtifact.msgId,
                            activeReport.run_id,
                            editHistory,
                          );
                          if (ok) setReportEditMode(false);
                        } finally {
                          setFinishEditBusy(false);
                        }
                      }
                    : undefined
                }
                onDiscardReportEdits={
                  railArtifact.kind === "report" && activeReport?.run_id
                    ? () =>
                        discardEdits(railArtifact.msgId, activeReport.run_id)
                    : undefined
                }
                onEditList={
                  railArtifact.kind === "report" &&
                  activeReport &&
                  activeReport.run_id
                    ? (req) =>
                        editList(
                          railArtifact.msgId,
                          activeReport.run_id,
                          req,
                        )
                    : undefined
                }
                onDiagramsUpdated={
                  railArtifact.kind === "report" &&
                  activeReportMsg?.role === "bot"
                    ? (diagrams, meta) =>
                        applyDiagramsUpdate({
                          msgId: activeReportMsg.id,
                          runId: activeReportMsg.result?.run_id,
                          diagrams,
                          meta,
                          setMsgs,
                          setActiveArtifact,
                          setUndoOffer,
                          rememberRun,
                          showToast,
                        })
                    : undefined
                }
              />
              )}
              {railCollapsed && !railArtifact && !narrowRail ? (
                <button
                  type="button"
                  className="artifact-rail-stub"
                  aria-label="Развернуть панель"
                  title="Развернуть панель"
                  onClick={reopenRail}
                >
                  <IconPanelRight size={16} />
                </button>
              ) : null}
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
          showToast("Стиль презентации сохранён", 2200);
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
        maxDiagramsCap={maxDiagramsCap}
        targetSlides={targetSlides}
        onTargetSlides={(n) => {
          const next = Math.max(6, Math.min(24, Math.round(Number(n)) || 12));
          setTargetSlides(next);
          try {
            localStorage.setItem("liber.slidesTarget.v1", String(next));
          } catch {
            /* ignore */
          }
        }}
        forbidCharts={forbidCharts}
        onForbidCharts={setForbidCharts}
        forbidImages={forbidImages}
        onForbidImages={setForbidImages}
        palettes={palettes}
        chartPalette={chartPalette}
        onChartPalette={(p) => {
          setChartPalette(p);
          try {
            localStorage.setItem("liber.chartPalette.v1", p);
          } catch {
            /* ignore */
          }
        }}
        dryRun={dryRun}
        onDryRun={setDryRun}
        health={health}
        paradeHint={
          health?.vision_ok && health?.docker_ok
            ? `Готово: ${paradeHint}`
            : `Сейчас: ${paradeHint}`
        }
      />
    </div>
  </ConfirmProvider>
  );
}
