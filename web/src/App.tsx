import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  ArtifactRail,
  type ActiveArtifact,
  type ArtifactTab,
} from "./ArtifactRail";
import { ArtifactCard } from "./ArtifactCard";
import { ContextPlaque } from "./ContextPlaque";
import type { ChartEditRequest } from "./ChartEditSheet";
import type { ImageEditRequest } from "./ImageEditModal";
import { EmptyState } from "./EmptyState";
import {
  IconCopy,
  IconLiberMark,
  IconPaperclip,
  IconSend,
} from "./icons";
import {
  ReportPending,
  type ReportPreview,
} from "./ReportView";
import {
  loadHistory,
  loadHistoryPayload,
  pushHistory,
  saveRunPayload,
} from "./reportHistory";
import { SettingsModal } from "./SettingsModal";
import { Sidebar, type HistoryItem } from "./Sidebar";
import { ThinkingFold } from "./ThinkingFold";
import {
  pushThinkingLine,
  stageKey as thinkingStageKey,
  type ThinkingLine,
} from "./pipelinePhrases";
import { loadRailWidth } from "./railWidth";
import { ChartsQa } from "./ChartsQa";
import { MsgMarkdown } from "./lightMd";

const LONG_TEXT_CHARS = 400;

const DEFAULT_INTENT =
  "Оформи понятный русскоязычный отчёт: структура, таблицы где уместны числа.";

const FALLBACK_TYPES = [
  "bar",
  "grouped_bar",
  "stacked_bar",
  "line",
  "horizontal_bar",
  "donut",
  "kpi",
  "area",
  "scatter",
] as const;

type PaletteInfo = {
  id: string;
  label: string;
  swatches: string[];
};

type Health = {
  ok: boolean;
  docker_ok: boolean;
  playwright_ok: boolean;
  vision_configured: boolean;
  kandinsky_configured: boolean;
  image_api_configured?: boolean;
  docker_error?: string | null;
  chart_types?: string[];
  chart_palettes?: PaletteInfo[];
};

type MediaPreview = {
  id: string;
  kind: string;
  url: string;
};

type RunResult = {
  run_id: string;
  status: string;
  downloads: Record<string, string>;
  previews?: MediaPreview[];
  preview?: ReportPreview;
  charts_ok: number;
  figures_ok: number;
  charts_planned: string[];
  figures_planned: string[];
  warnings: string[];
  media_status?: Record<string, unknown>;
  chat_summary?: string;
  summary_status?: string | null;
  error?: string;
  detail?: string;
};

type SourceAttachment = {
  title: string;
  text: string;
  fileName?: string;
};

type Msg =
  | {
      id: string;
      role: "user";
      text: string;
      /** @deprecated prefer chips — kept for session history */
      tags?: string;
      /** C6: settings as chips under collapsed Intent. */
      chips?: string[];
      /** Pasted / attached source shown as doc plaque on the bubble. */
      attachment?: SourceAttachment;
    }
  | {
      id: string;
      role: "bot";
      text: string;
      result?: RunResult;
      pending?: boolean;
      pendingStage?: string;
      pendingDetail?: string | null;
      /** LLM chat summary streaming into the bubble */
      streamingSummary?: boolean;
      /** Collapsible pipeline phrases in the bubble */
      thinking?: ThinkingLine[];
      thinkingStartedAt?: number;
      thinkingStageKey?: string;
      thinkingStageAt?: number;
      /** Frozen when run finishes (for collapsed fold meta). */
      thinkingElapsedSec?: number;
      error?: string;
    };

function appendBotThinking(
  msg: Extract<Msg, { role: "bot" }>,
  stage?: string | null,
  detail?: string | null,
  beat = false,
): Extract<Msg, { role: "bot" }> {
  const key = thinkingStageKey(stage, detail);
  const now = Date.now();
  const stageAt =
    msg.thinkingStageKey === key && msg.thinkingStageAt
      ? msg.thinkingStageAt
      : now;
  const dwellSec = (now - stageAt) / 1000;
  const startedAt = msg.thinkingStartedAt || now;
  const thinking = pushThinkingLine(msg.thinking || [], {
    stage,
    detail,
    dwellSec,
    beat,
    seed: startedAt,
  });
  return {
    ...msg,
    thinking,
    thinkingStartedAt: startedAt,
    thinkingStageKey: key,
    thinkingStageAt: stageAt,
  };
}

function reportReadyText(result?: RunResult, streamed?: string): string {
  const fromResult = (result?.chat_summary || "").trim();
  if (fromResult) return fromResult;
  const fromStream = (streamed || "").trim();
  if (fromStream) return fromStream;
  return "Отчёт готов";
}

/** Open SSE summary stream; returns closer. */
function openSummaryStream(
  runId: string,
  onDelta: (full: string) => void,
  onDone: (full: string, status: string) => void,
): () => void {
  const es = new EventSource(
    `/api/runs/${encodeURIComponent(runId)}/summary/stream`,
  );
  let acc = "";
  const onDeltaEv = (ev: Event) => {
    try {
      const data = JSON.parse((ev as MessageEvent).data) as { text?: string };
      acc += data.text || "";
      onDelta(acc);
    } catch {
      /* ignore */
    }
  };
  const onDoneEv = (ev: Event) => {
    try {
      const data = JSON.parse((ev as MessageEvent).data) as {
        text?: string;
        status?: string;
      };
      const final = (data.text || acc || "").trim();
      onDone(final, data.status || "ok");
    } catch {
      onDone(acc, "ok");
    }
    es.close();
  };
  es.addEventListener("delta", onDeltaEv);
  es.addEventListener("done", onDoneEv);
  es.onerror = () => {
    es.close();
  };
  return () => {
    es.removeEventListener("delta", onDeltaEv);
    es.removeEventListener("done", onDoneEv);
    es.close();
  };
}

const STAGE_LABELS: Record<string, string> = {
  queued: "В очереди…",
  llm: "Думаю над структурой…",
  charts: "Рисую графики…",
  images: "Готовлю иллюстрации…",
  inject: "Вставляю рисунки в текст…",
  latex: "Собираю PDF…",
  docx: "Собираю DOCX…",
  ok: "Готово",
  error: "Ошибка",
};

function stageLabel(stage?: string, detail?: string | null): string {
  if (detail && stage === "charts") return `Рисую ${detail}…`;
  if (stage && STAGE_LABELS[stage]) return STAGE_LABELS[stage];
  return "Генерирую документ…";
}

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function readTextFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () =>
      reject(reader.error ?? new Error("Не удалось прочитать файл"));
    reader.readAsText(file);
  });
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function reportThumb(result: RunResult): string | null {
  const blocks = result.preview?.blocks;
  if (blocks) {
    for (const b of blocks) {
      if (b.type === "figure" && b.url) return b.url;
    }
  }
  return result.previews?.[0]?.url ?? null;
}

function reportTitle(result: RunResult): string {
  const t = result.preview?.title?.trim();
  if (t) return t;
  return `Отчёт · ${result.run_id}`;
}

function ComposerPhotoChips({
  files,
  busy,
  onRemove,
}: {
  files: File[];
  busy: boolean;
  onRemove: (index: number) => void;
}) {
  const urls = useMemo(
    () => files.map((f) => URL.createObjectURL(f)),
    [files],
  );
  useEffect(() => {
    return () => {
      for (const u of urls) URL.revokeObjectURL(u);
    };
  }, [urls]);
  return (
    <div className="composer-photos" aria-label="Прикреплённые фото">
      {files.map((p, i) => (
        <div key={`${p.name}-${i}-${p.size}`} className="composer-photo-chip">
          <img src={urls[i]} alt="" />
          <button
            type="button"
            className="composer-photo-x"
            aria-label="Убрать фото"
            disabled={busy}
            onClick={() => onRemove(i)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  /** true = model picks type from catalog by Source context */
  const [chartAuto, setChartAuto] = useState(true);
  const [types, setTypes] = useState<string[]>([]);
  const [chartHints, setChartHints] = useState("");
  const [chartPalette, setChartPalette] = useState("atelier");
  const [chartStyle, setChartStyle] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [maxCharts, setMaxCharts] = useState(2);
  const [maxImages, setMaxImages] = useState(0);
  const [forbidCharts, setForbidCharts] = useState(false);
  const [forbidImages, setForbidImages] = useState(true);
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
  const [hasStoredReport, setHasStoredReport] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(() => loadHistory());
  const [activeArtifact, setActiveArtifact] = useState<ActiveArtifact | null>(
    null,
  );
  /** Text of attached .txt/.md for Source tab / plaque. */
  const [sourceDraft, setSourceDraft] = useState<{
    title: string;
    text: string;
    fileName?: string;
  } | null>(null);
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
    return [
      { id: "auto", label: "Auto", swatches: ["#2E4208", "#F07A3A", "#0B4F8C", "#FF8C2A"] },
      { id: "atelier", label: "Atelier", swatches: ["#2E4208", "#4F6B14", "#7A9A28", "#B8D45A"] },
      { id: "editorial", label: "Editorial", swatches: ["#0F3D3E", "#F07A3A", "#2EC4B6", "#E8B84A"] },
      { id: "ocean", label: "Ocean", swatches: ["#0B4F8C", "#1E8AD4", "#2EC4E0", "#5ED4F0"] },
      { id: "sunset", label: "Sunset", swatches: ["#8B2E4A", "#F04545", "#FF8C2A", "#F0C040"] },
      { id: "mono", label: "Mono", swatches: ["#1A1F28", "#3A4250", "#8B939E", "#B0B6BE"] },
    ];
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

  // Visual QA: http://127.0.0.1:5173/?preview=artifact
  useEffect(() => {
    if (!/preview=artifact/.test(window.location.search)) return;
    const id = "preview-artifact";
    const result: RunResult = {
      run_id: "source_20261021T082640Z",
      status: "ok",
      downloads: {
        pdf: "/api/runs/source_20261021T082640Z/files/source.pdf",
        docx: "/api/runs/source_20261021T082640Z/files/source.docx",
      },
      preview: {
        title: "Northstar Labs — демо",
        blocks: [
          { type: "heading", level: 1, text: "Итоги квартала" },
          {
            type: "paragraph",
            text: "Рост ускоряется, качество растёт вместе с ним. Это демо Artifact rail.",
          },
          { type: "heading", level: 2, text: "Ключевые метрики" },
          {
            type: "table",
            caption: "KPI",
            headers: ["Метрика", "Q2", "Q3"],
            rows: [
              ["Выручка", "12.4", "14.1"],
              ["NPS", "42", "51"],
            ],
          },
          { type: "heading", level: 2, text: "График" },
          {
            type: "figure",
            id: "cht_01",
            kind: "chart",
            caption: "Распределение бюджета по категориям, %",
            // Real run artifacts (live Chart.js + PDF jump)
            url: "/api/runs/source_20261021T082640Z/figures/cht_01.png",
            chartType: "donut",
            pdfPage: 1,
          },
          { type: "heading", level: 2, text: "Выводы" },
          {
            type: "paragraph",
            text: "Качество растёт вместе с объёмом — смотрите TOC и кнопку PDF на рисунке.",
          },
        ],
      },
      charts_ok: 1,
      figures_ok: 0,
      charts_planned: ["cht_01"],
      figures_planned: [],
      warnings: [],
    };
    setMsgs([
      {
        id: "preview-user",
        role: "user",
        text:
          "Собери отчёт по демо: таблица KPI, один line-график, спокойная палитра atelier, без лишней воды и без выдуманных цифр — только Source.",
        chips: ["демо", "палитра: atelier", "графики: ≤2"],
        attachment: {
          title: "northstar_demo.md",
          text: "# Source\n\nДемонстрационный файл для вкладки Source.\n",
          fileName: "northstar_demo.md",
        },
      },
      {
        id,
        role: "bot",
        text:
          "Собрал демо-отчёт: структура, таблица и график по числам из Source.\n\nПодробности — в полном документе справа.",
        result,
      },
    ]);
    setSourceDraft({
      title: "northstar_demo.md",
      text: "# Source\n\nДемонстрационный файл для вкладки Source.\n",
      fileName: "northstar_demo.md",
    });
    setActiveArtifact({
      kind: "report",
      msgId: id,
      tab: "preview",
      title: reportTitle(result),
    });
  }, []);

  // Visual QA: http://127.0.0.1:5173/?preview=flow
  useEffect(() => {
    if (!/preview=flow/.test(window.location.search)) return;
    const stages = [
      "queued",
      "llm",
      "charts",
      "inject",
      "latex",
      "docx",
      "ok",
    ] as const;
    const id = "preview-flow";
    let i = 0;
    let thinking: ThinkingLine[] = [];
    let thinkingStartedAt = Date.now();
    let thinkingStageKey: string | undefined;
    let thinkingStageAt = Date.now();
    const tick = () => {
      const idx = i % stages.length;
      if (idx === 0 && i > 0) {
        thinking = [];
        thinkingStartedAt = Date.now();
        thinkingStageKey = undefined;
        thinkingStageAt = Date.now();
      }
      const stage = stages[idx];
      const detail = stage === "charts" ? "cht_01" : null;
      setBusy(stage !== "ok");
      if (stage === "ok") {
        setMsgs([
          {
            id: "preview-user",
            role: "user",
            text: "Intent · preview flow",
          },
          {
            id,
            role: "bot",
            text: "Готово · preview — структура ясна, отчёт собран.",
            pending: false,
            thinking,
            thinkingStartedAt,
            thinkingElapsedSec: Math.max(
              0,
              Math.round((Date.now() - thinkingStartedAt) / 1000),
            ),
            result: {
              run_id: "preview-flow",
              status: "ok",
              downloads: {},
              charts_ok: 0,
              figures_ok: 0,
              charts_planned: [],
              figures_planned: [],
              warnings: [],
            },
          },
        ]);
      } else {
        const draft = appendBotThinking(
          {
            id,
            role: "bot",
            text: stageLabel(stage, detail),
            pending: true,
            pendingStage: stage,
            pendingDetail: detail,
            thinking,
            thinkingStartedAt,
            thinkingStageKey,
            thinkingStageAt,
          },
          stage,
          detail,
        );
        thinking = draft.thinking || [];
        thinkingStartedAt = draft.thinkingStartedAt || thinkingStartedAt;
        thinkingStageKey = draft.thinkingStageKey;
        thinkingStageAt = draft.thinkingStageAt || thinkingStageAt;
        setMsgs([
          {
            id: "preview-user",
            role: "user",
            text: "Intent · preview flow",
          },
          draft,
        ]);
      }
      i += 1;
    };
    tick();
    const t = window.setInterval(tick, 1400);
    return () => window.clearInterval(t);
  }, []);

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
    });
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
    return Boolean(file) || Boolean(sourceDraft?.text) || chat.trim().length > 0;
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

  function enableAuto() {
    setChartAuto(true);
    setTypes([]);
  }

  function toggleType(t: string) {
    setChartAuto(false);
    setTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

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
    const userChips = [
      photoMode === "edit" ? "только правка фото" : null,
      attachPhotos.length
        ? `фото ×${attachPhotos.length}`
        : null,
      photoMode === "document" && docTitle.trim()
        ? `«${docTitle.trim().slice(0, 24)}${docTitle.trim().length > 24 ? "…" : ""}»`
        : null,
      photoMode === "document" && forbidCharts
        ? "без графиков"
        : photoMode === "document"
          ? chartPalette === "auto"
            ? "палитра: Auto"
            : `палитра: ${chartPalette}`
          : null,
      photoMode === "document" && !forbidCharts
        ? `≤${maxCharts} гр.`
        : null,
      photoMode === "document" && !forbidCharts && !chartAuto && types.length
        ? types.slice(0, 3).join("+")
        : null,
      photoMode === "document" && !forbidCharts && chartHints.trim()
        ? `тип: ${chartHints.trim().slice(0, 28)}`
        : null,
      photoMode === "document" && !forbidCharts && chartStyle.trim()
        ? `стиль: ${chartStyle.trim().slice(0, 28)}`
        : null,
      photoMode === "document"
        ? forbidImages && !attachPhotos.length
          ? "без фото"
          : `≤${Math.max(maxImages, attachPhotos.length)} фото`
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
            photoMode === "edit" ? "Править фото…" : "Генерирую документ…",
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
      fd.append("formats", "both");
      fd.append("dry_run", String(dryRun));
    }

    try {
      const res = await fetch("/api/run", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        let msg: string;
        if (typeof detail === "string") {
          msg = detail;
        } else if (detail && typeof detail === "object" && !Array.isArray(detail)) {
          const d = detail as { message?: string; run_id?: string; hint?: string };
          msg = [d.message, d.run_id ? `run ${d.run_id}` : null, d.hint]
            .filter(Boolean)
            .join(" · ");
        } else if (Array.isArray(detail)) {
          msg = detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
        } else {
          msg = data.error || res.statusText;
        }
        throw new Error(msg);
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
                [body.error || body.message, runId ? `run ${runId}` : null]
                  .filter(Boolean)
                  .join(" · "),
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
        if (result.preview?.blocks?.length) {
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
      if (result.preview?.blocks?.length || result.downloads?.pdf) {
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

  const paradeHint = health
    ? [
        health.vision_configured ? "Vision" : null,
        health.docker_ok ? "Docker" : null,
        health.playwright_ok ? "Playwright" : null,
        health.image_api_configured || health.kandinsky_configured
          ? "Image API"
          : null,
      ]
        .filter(Boolean)
        .join(" · ") || "сервисы не готовы"
    : "проверка…";

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
        <div className={`desk-split${railLayout && !narrowRail ? " is-open" : ""}`}>
          <div className="desk chat-desk">
            <div className="messages" ref={messagesRef}>
              <AnimatePresence initial={false}>
                {msgs.length === 0 &&
                  !/preview=artifact/.test(window.location.search) && (
                  <EmptyState
                    hasStoredReport={hasStoredReport}
                    onRestore={restoreLastReport}
                    onPrompt={(text) => {
                      setChat(text);
                      window.setTimeout(() => chatRef.current?.focus(), 0);
                    }}
                  />
                )}
                {msgs.map((m, mi) => {
                  const hasArtifact =
                    m.role === "bot" &&
                    Boolean(
                      m.result?.preview?.blocks?.length ||
                        m.result?.downloads?.pdf,
                    );
                  const userLong =
                    m.role === "user" &&
                    !m.attachment &&
                    m.text.length > LONG_TEXT_CHARS;
                  const userCollapseIntent =
                    m.role === "user" &&
                    m.text.length > 140 &&
                    !m.attachment;
                  return (
                    <motion.div
                      key={m.id}
                      className={`msg ${m.role}${hasArtifact ? " has-artifact" : ""}`}
                      initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.35,
                        delay: Math.min(mi * 0.03, 0.18),
                        ease: [0.22, 1, 0.36, 1],
                      }}
                    >
                      {m.role === "user" ? (
                        <>
                          {m.attachment ? (
                            <div className="msg-attach-row">
                              <ContextPlaque
                                title={m.attachment.title}
                                subtitle={`${m.attachment.text.length} символов`}
                                onOpen={() =>
                                  openSourceArtifact(m.attachment!)
                                }
                              />
                            </div>
                          ) : null}
                          {userLong ? (
                            <button
                              type="button"
                              className="msg-body msg-plaque-trigger"
                              onClick={() => openIntentArtifact(m.text)}
                            >
                              Intent · {m.text.length} символов — открыть
                            </button>
                          ) : userCollapseIntent ? (
                            <details className="msg-intent-fold">
                              <summary className="msg-intent-summary">
                                <span className="msg-intent-label">Intent</span>
                                <span className="msg-intent-preview">
                                  {m.text.slice(0, 72).trim()}
                                  {m.text.length > 72 ? "…" : ""}
                                </span>
                              </summary>
                              <div className="msg-body msg-pre">{m.text}</div>
                            </details>
                          ) : (
                            <div className="msg-body msg-pre">{m.text}</div>
                          )}
                        </>
                      ) : m.role === "bot" && hasArtifact && m.result ? (
                        <div className="msg-row">
                          <span className="msg-avatar">
                            <IconLiberMark size={28} />
                          </span>
                          <div className="msg-bot-stack">
                          {m.thinking?.length ? (
                            <ThinkingFold
                              lines={m.thinking}
                              live={false}
                              elapsedSec={m.thinkingElapsedSec}
                            />
                          ) : null}
                          <MsgMarkdown text={m.text || "Отчёт готов"} />
                          <ArtifactCard
                            title={reportTitle(m.result)}
                            thumbUrl={reportThumb(m.result)}
                            pdfUrl={m.result.downloads?.pdf}
                            downloads={m.result.downloads}
                            pulse={downloadsPulseMsgId === m.id}
                            updated={downloadsPulseMsgId === m.id}
                            onView={() => openReportArtifact(m.id, m.result!)}
                          />
                          {m.result.warnings?.length ? (
                            <div className="warns">
                              {m.result.warnings.join(" · ")}
                            </div>
                          ) : null}
                          <div className="msg-actions">
                            <button
                              type="button"
                              className="msg-action"
                              title="Копировать"
                              aria-label="Копировать текст"
                              onClick={() => {
                                void navigator.clipboard?.writeText(
                                  m.text || "Отчёт готов",
                                );
                              }}
                            >
                              <IconCopy size={14} />
                            </button>
                          </div>
                          </div>
                        </div>
                      ) : m.role === "bot" && m.pending ? (
                        <div className="msg-row">
                          <span className="msg-avatar">
                            <IconLiberMark size={28} />
                          </span>
                          <div className="msg-bot-stack">
                            <ReportPending
                              label={thinkingLabel || m.text || undefined}
                              stage={m.pendingStage || "queued"}
                              detail={m.pendingDetail}
                            />
                            <ThinkingFold
                              lines={m.thinking || []}
                              live
                              elapsedSec={
                                m.thinkingStartedAt
                                  ? Math.max(
                                      0,
                                      Math.round(
                                        (Date.now() - m.thinkingStartedAt) /
                                          1000,
                                      ),
                                    )
                                  : undefined
                              }
                            />
                            {m.streamingSummary && m.text.trim() ? (
                              <div className="msg-stream-wrap">
                                <MsgMarkdown text={m.text} streaming />
                              </div>
                            ) : null}
                          </div>
                        </div>
                      ) : (
                        <div className="msg-row">
                          <span className="msg-avatar">
                            <IconLiberMark size={28} />
                          </span>
                          <div className="msg-bot-stack">
                          {m.role === "bot" && m.thinking?.length ? (
                            <ThinkingFold
                              lines={m.thinking}
                              live={false}
                              elapsedSec={m.thinkingElapsedSec}
                            />
                          ) : null}
                          {m.role === "bot" && !m.error ? (
                            <MsgMarkdown text={m.text} />
                          ) : (
                            <div className="msg-body">{m.text}</div>
                          )}
                          {m.role === "bot" && m.error && (
                            <p className="err">{m.error}</p>
                          )}
                          {m.role === "bot" &&
                            m.result &&
                            (m.result.downloads?.pdf ||
                              m.result.downloads?.docx) && (
                              <ArtifactCard
                                title={reportTitle(m.result)}
                                thumbUrl={reportThumb(m.result)}
                                pdfUrl={m.result.downloads?.pdf}
                                downloads={m.result.downloads}
                                pulse={downloadsPulseMsgId === m.id}
                                updated={downloadsPulseMsgId === m.id}
                                onView={() =>
                                  openReportArtifact(m.id, m.result!)
                                }
                              />
                            )}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              <div ref={bottomRef} />
            </div>

            <div className="composer-wrap">
              {attachPhotos.length > 0 && (
                <div className="composer-attach-row">
                  <ComposerPhotoChips
                    files={attachPhotos}
                    busy={busy}
                    onRemove={(i) =>
                      setAttachPhotos((list) =>
                        list.filter((_, j) => j !== i),
                      )
                    }
                  />
                </div>
              )}
              {showPlaque && plaqueDraft ? (
                <ContextPlaque
                  title={plaqueDraft.title}
                  subtitle={plaqueDraft.subtitle}
                  disabled={busy}
                  onOpen={() => {
                    if (sourceDraft) openSourceArtifact(sourceDraft);
                  }}
                  onDismiss={() => {
                    setPlaqueDismissed(true);
                    setSourceDraft(null);
                    setFile(null);
                    setActiveArtifact((a) =>
                      a?.kind === "source" || a?.kind === "intent" ? null : a,
                    );
                  }}
                />
              ) : null}
              <div className="composer">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".txt,.md,text/plain,text/markdown,image/png,image/jpeg,.png,.jpg,.jpeg"
                  multiple
                  hidden
                  onChange={(e) => {
                    const list = e.target.files;
                    e.target.value = "";
                    if (list?.length) ingestFiles(list);
                  }}
                />
                <input
                  ref={photoRef}
                  type="file"
                  accept="image/*"
                  multiple
                  hidden
                />
                <button
                  type="button"
                  className="composer-attach"
                  disabled={busy}
                  title="Прикрепить .txt / .md или фото"
                  aria-label="Прикрепить файл"
                  onClick={() => fileRef.current?.click()}
                >
                  <IconPaperclip size={18} />
                </button>
                <textarea
                  ref={chatRef}
                  className="composer-input"
                  rows={1}
                  placeholder={
                    sourceDraft || file
                      ? "Спросить Liber…"
                      : "Опишите отчёт или вставьте Source…"
                  }
                  value={chat}
                  disabled={busy}
                  onChange={(e) => setChat(e.target.value)}
                  onPaste={(e) => {
                    const pasted = e.clipboardData.getData("text/plain");
                    if (capturePastedSource(pasted)) {
                      e.preventDefault();
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void send();
                    }
                  }}
                />
                <button
                  className="send"
                  type="button"
                  disabled={!canSend}
                  onClick={() => void send()}
                  aria-label="Собрать отчёт"
                  title="Собрать"
                >
                  {busy ? "…" : <IconSend size={16} />}
                </button>
              </div>
            </div>
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
                      }
                    : null
                }
                sourceText={railSourceText}
                sourceTitle={railSourceTitle}
                palettes={palettes}
                catalogTypes={catalog}
                defaultPalette={
                  chartPalette === "auto" ? "atelier" : chartPalette
                }
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

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        docTitle={docTitle}
        onDocTitle={setDocTitle}
        chartAuto={chartAuto}
        onEnableAuto={enableAuto}
        types={types}
        catalog={catalog}
        onToggleType={toggleType}
        chartHints={chartHints}
        onChartHints={(v) => {
          setChartHints(v);
          if (v.trim()) setChartAuto(false);
        }}
        chartPalette={chartPalette}
        palettes={palettes}
        onPalette={setChartPalette}
        chartStyle={chartStyle}
        onChartStyle={setChartStyle}
        maxCharts={maxCharts}
        onMaxCharts={setMaxCharts}
        maxImages={maxImages}
        onMaxImages={setMaxImages}
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
