import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { ChartEditRequest } from "./ChartEditSheet";
import type { ImageEditRequest } from "./ImageEditModal";
import {
  ReportPending,
  ReportView,
  type ReportPreview,
} from "./ReportView";
import { SettingsModal } from "./SettingsModal";

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
  error?: string;
  detail?: string;
};

type Msg =
  | { id: string; role: "user"; text: string; tags?: string }
  | {
      id: string;
      role: "bot";
      text: string;
      result?: RunResult;
      pending?: boolean;
      pendingStage?: string;
      pendingDetail?: string | null;
      error?: string;
    };

/** Classic gear — readable at 16–18px */
function SettingsIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden fill="none">
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.75" />
      <path
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
      />
    </svg>
  );
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
  const [photoMode, setPhotoMode] = useState<"document" | "edit">("document");
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
      { id: "auto", label: "Auto", swatches: ["#0F3D3E", "#E85D04", "#0077B6", "#F77F00"] },
      { id: "atelier", label: "Atelier", swatches: ["#2C3A14", "#3F5210", "#6B7F2A", "#D5DEC0"] },
      { id: "editorial", label: "Editorial", swatches: ["#0F3D3E", "#E85D04", "#2A9D8F", "#E9C46A"] },
      { id: "ocean", label: "Ocean", swatches: ["#023E8A", "#0077B6", "#00B4D8", "#48CAE4"] },
      { id: "sunset", label: "Sunset", swatches: ["#6D2E46", "#D62828", "#F77F00", "#FCBF49"] },
      { id: "mono", label: "Mono", swatches: ["#111827", "#374151", "#6B7280", "#9CA3AF"] },
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
    const next = Math.min(Math.max(el.scrollHeight, 44), 240);
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
    const tick = () => {
      const stage = stages[i % stages.length];
      setBusy(stage !== "ok");
      setMsgs([
        {
          id: "preview-user",
          role: "user",
          text: "Intent · preview flow",
        },
        {
          id,
          role: "bot",
          text: stageLabel(stage, stage === "charts" ? "cht_01" : null),
          pending: stage !== "ok",
          pendingStage: stage,
          pendingDetail: stage === "charts" ? "cht_01" : null,
          ...(stage === "ok"
            ? { text: "Готово · preview", pending: false }
            : {}),
        },
      ]);
      i += 1;
    };
    tick();
    const t = window.setInterval(tick, 1600);
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
            text: `Обновлено · ${req.figureId}`,
            result: {
              ...msg.result,
              preview: data.preview ?? msg.result.preview,
              downloads: data.downloads ?? msg.result.downloads,
              warnings: data.warnings ?? msg.result.warnings,
              media_status: data.media_status ?? msg.result.media_status,
            },
          };
          try {
            sessionStorage.setItem(
              "liber-last-report",
              JSON.stringify(next.result),
            );
          } catch {
            /* quota */
          }
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
            text: `Фото обновлено · ${req.figureId}`,
            result: {
              ...msg.result,
              preview: data.preview ?? msg.result.preview,
              downloads: data.downloads ?? msg.result.downloads,
              warnings: data.warnings ?? msg.result.warnings,
              media_status: data.media_status ?? msg.result.media_status,
            },
          };
          try {
            sessionStorage.setItem(
              "liber-last-report",
              JSON.stringify(next.result),
            );
          } catch {
            /* quota */
          }
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

  function restoreLastReport() {
    try {
      const raw = sessionStorage.getItem("liber-last-report");
      if (!raw) return;
      const result = JSON.parse(raw) as RunResult;
      if (!result?.preview?.blocks?.length) return;
      setMsgs([
        {
          id: uid(),
          role: "bot",
          text: `Готово · run ${result.run_id}`,
          result,
        },
      ]);
    } catch {
      /* ignore */
    }
  }

  const canSend = useMemo(() => {
    if (busy) return false;
    if (photoMode === "edit") {
      return attachPhotos.length > 0 && chat.trim().length > 0;
    }
    return Boolean(file) || chat.trim().length > 0;
  }, [file, busy, photoMode, attachPhotos, chat]);

  const ingestFiles = useCallback((list: FileList | File[]) => {
    const arr = Array.from(list);
    for (const f of arr) {
      if (/\.(txt|md)$/i.test(f.name) || f.type === "text/plain" || f.type === "text/markdown") {
        setFile(f);
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

  const settingsSummary = useMemo(() => {
    const bits: string[] = [];
    if (docTitle.trim()) bits.push(docTitle.trim().slice(0, 28));
    if (forbidCharts) bits.push("без графиков");
    else {
      bits.push(chartPalette === "auto" ? "Auto" : chartPalette);
      bits.push(`≤${maxCharts} гр.`);
      if (!chartAuto && types.length) bits.push(types.slice(0, 2).join("+"));
    }
    if (forbidImages && !attachPhotos.length) bits.push("без фото");
    else bits.push(`≤${Math.max(maxImages, attachPhotos.length)} фото`);
    if (dryRun) bits.push("dry-run");
    return bits.join(" · ");
  }, [
    docTitle,
    forbidCharts,
    chartPalette,
    maxCharts,
    chartAuto,
    types,
    forbidImages,
    attachPhotos.length,
    maxImages,
    dryRun,
  ]);

  function enableAuto() {
    setChartAuto(true);
    setTypes([]);
  }

  function toggleType(t: string) {
    setChartAuto(false);
    setTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

  function chartsLabel(): string {
    if (forbidCharts) return "графики: выкл";
    const bits = [`≤${maxCharts}`, `палитра:${chartPalette}`];
    if (chartAuto) bits.push("на усмотрение модели");
    else if (types.length) bits.push(types.join(", "));
    if (chartHints.trim()) bits.push(`тип: ${chartHints.trim()}`);
    if (chartStyle.trim()) bits.push(`стиль: ${chartStyle.trim()}`);
    return `графики: ${bits.join(" · ")}`;
  }

  async function send() {
    if (!canSend) return;
    const chatTrim = chat.trim();
    const intentText =
      photoMode === "edit"
        ? chatTrim
        : file
          ? chatTrim || DEFAULT_INTENT
          : chatTrim;
    if (photoMode === "edit" && !intentText) return;
    if (photoMode === "document" && !file && !chatTrim) return;

    const userBody =
      photoMode === "edit"
        ? intentText
        : file
          ? chatTrim
            ? chatTrim
            : `Файл: ${file.name}`
          : chatTrim;
    const userTags = [
      photoMode === "edit" ? "только правка фото" : null,
      attachPhotos.length
        ? `фото: ${attachPhotos.map((f) => f.name).join(", ")}`
        : null,
      photoMode === "document" && docTitle.trim()
        ? `название: ${docTitle.trim()}`
        : null,
      photoMode === "document" ? chartsLabel() : null,
      photoMode === "document"
        ? forbidImages && !attachPhotos.length
          ? "картинки: выкл"
          : `картинки: ≤${Math.max(maxImages, attachPhotos.length)}`
        : null,
      photoMode === "document"
        ? file
          ? `файл: ${file.name}`
          : null
        : null,
    ]
      .filter(Boolean)
      .join(" · ");

    const pendingId = uid();
    setMsgs((m) => [
      ...m,
      { id: uid(), role: "user", text: userBody, tags: userTags || undefined },
      {
        id: pendingId,
        role: "bot",
        text:
          photoMode === "edit" ? "Править фото…" : "Генерирую документ…",
        pending: true,
        pendingStage: "queued",
        pendingDetail: null,
      },
    ]);
    setBusy(true);
    setChat("");
    if (chatRef.current) chatRef.current.style.height = "44px";
    const photosSnapshot = [...attachPhotos];
    setAttachPhotos([]);

    const fd = new FormData();
    fd.append("photo_mode", photoMode);
    for (const p of photosSnapshot) fd.append("photos", p);
    if (photoMode === "edit") {
      fd.append("intent", intentText);
    } else {
      if (file) {
        fd.append("source", file);
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
          m.map((msg) =>
            msg.id === pendingId
              ? {
                  ...msg,
                  text: stageLabel(data.stage || "queued"),
                  pending: true,
                  pendingStage: data.stage || "queued",
                  pendingDetail: null,
                }
              : msg,
          ),
        );
        const pollStarted = Date.now();
        const pollDeadlineMs = 20 * 60 * 1000;
        let soft404 = 0;
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
          if (body.status === "running" || body.status === "started") {
            setMsgs((m) =>
              m.map((msg) =>
                msg.id === pendingId
                  ? {
                      ...msg,
                      text: stageLabel(stage || "queued", detail),
                      pending: true,
                      pendingStage: stage,
                      pendingDetail: detail,
                    }
                  : msg,
              ),
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
      }

      try {
        if (result.preview?.blocks?.length) {
          sessionStorage.setItem("liber-last-report", JSON.stringify(result));
          setHasStoredReport(true);
        }
      } catch {
        /* quota */
      }
      setMsgs((m) =>
        m.map((msg) =>
          msg.id === pendingId
            ? {
                id: pendingId,
                role: "bot",
                text: `Готово · run ${result.run_id}`,
                result,
              }
            : msg,
        ),
      );
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

  return (
    <div
      className={`app chat-app${drag ? " is-drag" : ""}`}
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

      <header className="topbar">
        <div className="topbar-brand">
          <p className="eyebrow">
            atelier · печатный стол
            <span
              className={`topbar-live${healthReady ? " ok" : health ? " warn" : ""}`}
              title={paradeHint}
            >
              <span className="health-dot" aria-hidden />
              {healthReady ? "готово" : health ? "сервисы" : "…"}
            </span>
          </p>
          <h1 className="brand">Liber</h1>
        </div>
        <button
          type="button"
          className="topbar-settings"
          onClick={() => setSettingsOpen(true)}
          aria-label="Настройки отчёта"
          title="Палитра, типы графиков, лимиты"
        >
          <SettingsIcon size={17} />
          <span>Настройки</span>
        </button>
      </header>

      <main className="main chat-main">
        <div className="desk chat-desk">
          <div className="messages" ref={messagesRef}>
            <AnimatePresence mode="popLayout">
              {msgs.length === 0 && (
                <motion.div
                  className="empty"
                  key="empty"
                  initial={reduceMotion ? false : { opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
                >
                  <p className="empty-kicker">печатный стол</p>
                  <h2>Напиши или прикрепи .txt</h2>
                  <p>
                    Как в чате: запрос с цифрами — или файл + короткая просьба.
                    Отчёт с графиками появится здесь; PDF и DOCX — внизу карточки.
                  </p>
                  <ol>
                    <li>Вставь текст или перетащи .txt / .md</li>
                    <li>При желании открой ⚙ — палитра и лимиты</li>
                    <li>Нажми «Собрать»</li>
                  </ol>
                  {hasStoredReport && (
                    <button
                      type="button"
                      className="empty-restore"
                      onClick={restoreLastReport}
                    >
                      Открыть последний отчёт
                    </button>
                  )}
                </motion.div>
              )}
              {msgs.map((m, mi) => {
                const hasReport =
                  m.role === "bot" &&
                  m.result?.preview &&
                  (m.result.preview.blocks?.length ?? 0) > 0;
                return (
                  <motion.div
                    key={m.id}
                    className={`msg ${m.role}${hasReport ? " has-report" : ""}`}
                    layout={!reduceMotion}
                    initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.4,
                      delay: Math.min(mi * 0.04, 0.24),
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  >
                    <div className="meta">
                      {m.role === "user" ? "запрос" : "отчёт"}
                    </div>
                    {m.role === "user" ? (
                      <>
                        <div className="msg-body msg-pre">{m.text}</div>
                        {m.tags ? (
                          <p className="msg-tags">{m.tags}</p>
                        ) : null}
                      </>
                    ) : m.role === "bot" && hasReport && m.result?.preview ? (
                      <ReportView
                        preview={m.result.preview}
                        downloads={m.result.downloads}
                        runId={m.result.run_id}
                        stats={`charts ${m.result.charts_ok}/${m.result.charts_planned?.length || 0} · figures ${m.result.figures_ok}/${m.result.figures_planned?.length || 0}`}
                        warnings={m.result.warnings}
                        palettes={palettes}
                        catalogTypes={catalog}
                        defaultPalette={
                          chartPalette === "auto" ? "atelier" : chartPalette
                        }
                        editingFigureId={
                          editBusy?.msgId === m.id ? editBusy.figureId : null
                        }
                        editError={
                          editError?.msgId === m.id ? editError.message : null
                        }
                        editErrorFigureId={
                          editError?.msgId === m.id ? editError.figureId : null
                        }
                        downloadsPulse={downloadsPulseMsgId === m.id}
                        onEditCancel={() => {
                          if (editError?.msgId === m.id) setEditError(null);
                        }}
                        onEditFigure={(req) =>
                          editFigure(m.id, m.result!.run_id, req)
                        }
                        onEditImage={(req) =>
                          editImage(m.id, m.result!.run_id, req)
                        }
                      />
                    ) : m.role === "bot" && m.pending ? (
                      <ReportPending
                        label={m.text || undefined}
                        stage={m.pendingStage || "queued"}
                        detail={m.pendingDetail}
                      />
                    ) : (
                      <>
                        <div className="msg-body">{m.text}</div>
                        {m.role === "bot" && m.error && (
                          <p className="err">{m.error}</p>
                        )}
                        {m.role === "bot" && m.result && (
                          <>
                            <p className="stats">
                              charts {m.result.charts_ok}/
                              {m.result.charts_planned?.length || 0}
                              {" · "}
                              figures {m.result.figures_ok}/
                              {m.result.figures_planned?.length || 0}
                            </p>
                            {m.result.warnings?.length > 0 && (
                              <div className="warns">
                                {m.result.warnings.join(" · ")}
                              </div>
                            )}
                            <div className="downloads">
                              {m.result.downloads?.pdf && (
                                <a href={m.result.downloads.pdf} download>
                                  PDF
                                </a>
                              )}
                              {m.result.downloads?.docx && (
                                <a
                                  className="secondary"
                                  href={m.result.downloads.docx}
                                  download
                                >
                                  DOCX
                                </a>
                              )}
                            </div>
                            {m.result.previews && m.result.previews.length > 0 && (
                              <div className="previews">
                                {m.result.previews.map((p) => (
                                  <a
                                    key={p.id}
                                    className="preview"
                                    href={p.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    title={`${p.kind} ${p.id}`}
                                  >
                                    <img
                                      src={p.url}
                                      alt={`${p.kind} ${p.id}`}
                                    />
                                    <span>{p.id}</span>
                                  </a>
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>

          <div className="composer-wrap">
            {(file || attachPhotos.length > 0) && (
              <div className="composer-attach-row">
                {file && (
                  <div className="composer-file-chip">
                    <span className="composer-file-name" title={file.name}>
                      {file.name}
                    </span>
                    <button
                      type="button"
                      className="composer-photo-x"
                      aria-label="Убрать файл"
                      disabled={busy}
                      onClick={() => setFile(null)}
                    >
                      ×
                    </button>
                  </div>
                )}
                {attachPhotos.length > 0 && (
                  <ComposerPhotoChips
                    files={attachPhotos}
                    busy={busy}
                    onRemove={(i) =>
                      setAttachPhotos((list) => list.filter((_, j) => j !== i))
                    }
                  />
                )}
              </div>
            )}
            <div className="composer-modes" role="group" aria-label="Режим">
              <button
                type="button"
                className={`chip${photoMode === "document" ? " on" : ""}`}
                disabled={busy}
                onClick={() => setPhotoMode("document")}
              >
                В отчёт
              </button>
              <button
                type="button"
                className={`chip${photoMode === "edit" ? " on" : ""}`}
                disabled={busy}
                onClick={() => setPhotoMode("edit")}
                title="Фото + текст правки"
              >
                Только правка
              </button>
            </div>
            <p className="composer-summary" title={settingsSummary}>
              {settingsSummary}
            </p>
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
              <input ref={photoRef} type="file" accept="image/*" multiple hidden />
              <button
                type="button"
                className="composer-attach"
                disabled={busy}
                title="Прикрепить .txt / .md или фото"
                onClick={() => fileRef.current?.click()}
              >
                📎
              </button>
              <button
                type="button"
                className="composer-attach composer-gear"
                disabled={busy}
                title="Настройки: палитра, типы, лимиты"
                aria-label="Настройки отчёта"
                onClick={() => setSettingsOpen(true)}
              >
                <SettingsIcon size={16} />
              </button>
              <textarea
                ref={chatRef}
                className="composer-input"
                rows={1}
                placeholder={
                  photoMode === "edit"
                    ? "Что изменить на фото…"
                    : file
                      ? "Что сделать с файлом (можно пусто)…"
                      : "Напиши отчёт с цифрами или прикрепи .txt…"
                }
                value={chat}
                disabled={busy}
                onChange={(e) => setChat(e.target.value)}
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
              >
                {busy ? "…" : photoMode === "edit" ? "Править" : "Собрать"}
              </button>
            </div>
          </div>
        </div>
      </main>

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
