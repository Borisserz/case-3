import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from "react";

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
  charts_ok: number;
  figures_ok: number;
  charts_planned: string[];
  figures_planned: string[];
  warnings: string[];
  error?: string;
  detail?: string;
};

type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "bot"; text: string; result?: RunResult; pending?: boolean; error?: string };

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sourceText, setSourceText] = useState("");
  const [drag, setDrag] = useState(false);
  /** true = model picks type from catalog by Source context */
  const [chartAuto, setChartAuto] = useState(true);
  const [types, setTypes] = useState<string[]>([]);
  const [chartHints, setChartHints] = useState("");
  const [chartPalette, setChartPalette] = useState("editorial");
  const [chartStyle, setChartStyle] = useState("");
  const [maxCharts, setMaxCharts] = useState(2);
  const [maxImages, setMaxImages] = useState(0);
  const [forbidCharts, setForbidCharts] = useState(false);
  const [forbidImages, setForbidImages] = useState(true);
  const [dryRun, setDryRun] = useState(false);
  const [chat, setChat] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const catalog = useMemo(() => {
    const fromApi = health?.chart_types?.filter(Boolean);
    return fromApi && fromApi.length > 0 ? fromApi : [...FALLBACK_TYPES];
  }, [health]);

  const palettes = useMemo<PaletteInfo[]>(() => {
    if (health?.chart_palettes?.length) return health.chart_palettes;
    return [
      { id: "auto", label: "Auto", swatches: ["#0F3D3E", "#E85D04", "#0077B6", "#F77F00"] },
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
        if (!cancelled) setHealth(data);
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
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  const canSend = useMemo(() => {
    const hasSource = Boolean(file) || sourceText.trim().length > 0;
    return hasSource && !busy;
  }, [file, sourceText, busy]);

  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f && /\.(txt|md)$/i.test(f.name)) {
      setFile(f);
      setSourceText("");
    }
  }, []);

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
    const intentText =
      chat.trim() ||
      "Оформи понятный русскоязычный отчёт: структура, таблицы где уместны числа.";
    const userLabel = [
      intentText,
      chartsLabel(),
      forbidImages ? "картинки: выкл" : `картинки: ≤${maxImages}`,
      dryRun ? "dry-run" : null,
      file ? `файл: ${file.name}` : "текст из поля Source",
    ]
      .filter(Boolean)
      .join(" · ");

    const pendingId = uid();
    setMsgs((m) => [
      ...m,
      { id: uid(), role: "user", text: userLabel },
      { id: pendingId, role: "bot", text: "Генерирую документ…", pending: true },
    ]);
    setBusy(true);
    setChat("");

    const fd = new FormData();
    if (file) fd.append("source", file);
    else fd.append("source_text", sourceText);
    fd.append("intent", intentText);
    fd.append("max_charts", String(forbidCharts ? 0 : maxCharts));
    fd.append("max_images", String(forbidImages ? 0 : maxImages));
    fd.append("chart_types", chartAuto ? "" : types.join(","));
    fd.append("chart_hints", chartHints.trim());
    fd.append("chart_auto", String(chartAuto));
    fd.append("chart_palette", chartPalette);
    fd.append("chart_style", chartStyle.trim());
    fd.append("forbid_charts", String(forbidCharts));
    fd.append("forbid_images", String(forbidImages));
    fd.append("formats", "both");
    fd.append("dry_run", String(dryRun));

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
      const result = data as RunResult;
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
        health.kandinsky_configured ? "Kandinsky" : null,
      ]
        .filter(Boolean)
        .join(" · ") || "сервисы не готовы"
    : "проверка…";

  return (
    <div className="app">
      <aside className="panel">
        <header className="brand-block">
          <p className="eyebrow">документ · студия</p>
          <h1 className="brand">case-3</h1>
          <p className="tagline">
            Текст и цифры → отчёт с графиками в PDF и DOCX
          </p>
        </header>

        <section className="section" aria-labelledby="sec-source">
          <h2 className="section-title" id="sec-source">
            Source
          </h2>
          <label className="field">Файл</label>
          <div
            className={`dropzone${drag ? " active" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
          >
            <strong>{file ? file.name : "Перетащи .txt / .md"}</strong>
            или кликни, чтобы выбрать
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  setFile(f);
                  setSourceText("");
                }
              }}
            />
          </div>

          <label className="field">Или вставь текст</label>
          <textarea
            rows={5}
            placeholder="Цифры, разделы, факты…"
            value={sourceText}
            onChange={(e) => {
              setSourceText(e.target.value);
              if (e.target.value) setFile(null);
            }}
          />
        </section>

        <section className="section" aria-labelledby="sec-charts">
          <h2 className="section-title" id="sec-charts">
            Графики
          </h2>
          <label className="field">Тип</label>
          <div className="chips">
            <button
              type="button"
              className={`chip auto${chartAuto ? " on" : ""}`}
              onClick={enableAuto}
              disabled={forbidCharts}
              title="Модель сама выберет тип из каталога по данным Source"
            >
              на усмотрение модели
            </button>
            {catalog.map((t) => (
              <button
                key={t}
                type="button"
                className={`chip${!chartAuto && types.includes(t) ? " on" : ""}`}
                onClick={() => toggleType(t)}
                disabled={forbidCharts}
              >
                {t}
              </button>
            ))}
          </div>

          <label className="field">Свой тип / пожелание</label>
          <input
            type="text"
            placeholder="pie, воронка, сравнение долей…"
            value={chartHints}
            disabled={forbidCharts}
            onChange={(e) => {
              setChartHints(e.target.value);
              if (e.target.value.trim()) setChartAuto(false);
            }}
          />
          <p className="hint">Сведём к Chart.js-каталогу. Бюджет — потолок, не план.</p>

          <label className="field">Палитра</label>
          <div className="chips palettes">
            {palettes.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`chip palette${chartPalette === p.id ? " on" : ""}`}
                disabled={forbidCharts}
                onClick={() => setChartPalette(p.id)}
                title={p.label}
              >
                <span className="swatches" aria-hidden>
                  {p.swatches.slice(0, 4).map((c) => (
                    <span key={c} className="swatch" style={{ background: c }} />
                  ))}
                </span>
                {p.label}
              </button>
            ))}
          </div>

          <label className="field">Стиль / нюансы</label>
          <input
            type="text"
            placeholder="без сетки, толще линии, легенда снизу…"
            value={chartStyle}
            disabled={forbidCharts}
            onChange={(e) => setChartStyle(e.target.value)}
          />
          <p className="hint">Цвета из палитры; поле уточняет оформление.</p>

          <div className="row">
            <div>
              <label className="field">Графиков ≤</label>
              <input
                type="number"
                min={0}
                max={8}
                value={maxCharts}
                disabled={forbidCharts}
                onChange={(e) => setMaxCharts(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="field">Картинок ≤</label>
              <input
                type="number"
                min={0}
                max={8}
                value={maxImages}
                disabled={forbidImages}
                onChange={(e) => setMaxImages(Number(e.target.value))}
              />
            </div>
          </div>

          <label className="check">
            <input
              type="checkbox"
              checked={forbidCharts}
              onChange={(e) => setForbidCharts(e.target.checked)}
            />
            Без графиков
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={forbidImages}
              onChange={(e) => setForbidImages(e.target.checked)}
            />
            Без картинок Kandinsky
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            Dry-run (без LLM, проверка Docker/TeX)
          </label>
        </section>

        <div className="health">
          <p className="health-title">Статус</p>
          {!health && <div className="health-grid">Проверка API…</div>}
          {health && (
            <>
              <div className="health-grid">
                <div className="health-row">
                  <span>Docker</span>
                  <span className={`val${health.docker_ok ? "" : " bad"}`}>
                    {health.docker_ok ? "ok" : health.docker_error || "fail"}
                  </span>
                </div>
                <div className="health-row">
                  <span>Vision</span>
                  <span className={`val${health.vision_configured ? "" : " bad"}`}>
                    {health.vision_configured ? "ok" : "нет URL"}
                  </span>
                </div>
                <div className="health-row">
                  <span>Playwright</span>
                  <span className={`val${health.playwright_ok ? "" : " bad"}`}>
                    {health.playwright_ok ? "ok" : "нет Chromium"}
                  </span>
                </div>
                <div className="health-row">
                  <span>Kandinsky</span>
                  <span className={`val${health.kandinsky_configured ? "" : " bad"}`}>
                    {health.kandinsky_configured ? "ok" : "нет URL"}
                  </span>
                </div>
              </div>
              <p className="health-foot">
                {health.vision_configured && health.docker_ok
                  ? `Готово: ${paradeHint}`
                  : `Нужны Vision + Docker · сейчас: ${paradeHint}`}
              </p>
            </>
          )}
        </div>
      </aside>

      <main className="main">
        <div className="desk">
          <div className="desk-head">
            <h2>Сборка</h2>
            <span className="desk-meta">{busy ? "генерация…" : "intent → pdf"}</span>
          </div>

          <div className="messages">
            {msgs.length === 0 && (
              <div className="empty">
                <h2>Собери отчёт на столе</h2>
                <p>
                  Слева — исходник и оформление графиков. Здесь пишешь Intent и
                  забираешь PDF с DOCX.
                </p>
                <ol>
                  <li>Загрузи Source или вставь текст с числами</li>
                  <li>Выбери палитру и типы (или «на усмотрение»)</li>
                  <li>Напиши Intent и нажми «Собрать»</li>
                </ol>
              </div>
            )}
            {msgs.map((m) => (
              <div key={m.id} className={`msg ${m.role}`}>
                <div className="meta">{m.role === "user" ? "запрос" : "отчёт"}</div>
                <div className="msg-body">{m.text}</div>
                {m.role === "bot" && m.error && <p className="err">{m.error}</p>}
                {m.role === "bot" && m.result && (
                  <>
                    <p className="stats">
                      charts {m.result.charts_ok}/{m.result.charts_planned?.length || 0}
                      {" · "}
                      figures {m.result.figures_ok}/{m.result.figures_planned?.length || 0}
                    </p>
                    {m.result.warnings?.length > 0 && (
                      <div className="warns">{m.result.warnings.join(" · ")}</div>
                    )}
                    <div className="downloads">
                      {m.result.downloads?.pdf && (
                        <a href={m.result.downloads.pdf} download>
                          PDF
                        </a>
                      )}
                      {m.result.downloads?.docx && (
                        <a className="secondary" href={m.result.downloads.docx} download>
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
                            <img src={p.url} alt={`${p.kind} ${p.id}`} />
                            <span>{p.id}</span>
                          </a>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="composer">
            <input
              type="text"
              placeholder="Intent: с таблицами, короткий отчёт…"
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
            <button className="send" type="button" disabled={!canSend} onClick={() => void send()}>
              {busy ? "…" : "Собрать"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
