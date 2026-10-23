/** Liber deck viewer: Julius-like live twin + filmstrip + fullscreen. */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { DeckCanvas } from "./DeckCanvas";
import { DeckExportSheet } from "./DeckExportSheet";
import { DeckGallery } from "./DeckGallery";
import type { DeckIR, DeckSlide } from "./deckTypes";
import { ExportMenu } from "./ExportMenu";
import { PresentationFullscreen } from "./PresentationFullscreen";

function useElapsedSeconds(active: boolean): number {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    if (!active) {
      setSec(0);
      return;
    }
    setSec(0);
    const t0 = Date.now();
    const id = window.setInterval(() => {
      setSec(Math.floor((Date.now() - t0) / 1000));
    }, 500);
    return () => window.clearInterval(id);
  }, [active]);
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
  onMakePresentation?: () => void;
  making?: boolean;
  onDeckUpdated?: (deck: DeckIR, slidePngs: string[]) => void;
};

export function PresentationPane({
  runId,
  slidePngs,
  deck: deckProp = null,
  status,
  stage,
  error,
  downloads,
  deckPdfMode = null,
  onMakePresentation,
  making = false,
  onDeckUpdated,
}: Props) {
  const reduce = useReducedMotion();
  const [idx, setIdx] = useState(0);
  const [dir, setDir] = useState(0);
  const [full, setFull] = useState(false);
  /** Julius: open in Slide view; Edit is explicit. */
  const [editing, setEditing] = useState(false);
  const [view, setView] = useState<"grid" | "slide">("grid");
  const [deck, setDeck] = useState<DeckIR | null>(deckProp);
  const [saving, setSaving] = useState(false);
  const [saveFlash, setSaveFlash] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
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
  }, [runId]);

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
      // Space advances only in Present (fullscreen) — Julius-like.
      if (e.key === "f" || e.key === "F") setFull(true);
      if (e.key === "e" || e.key === "E") {
        setView("slide");
        setEditing((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [full, go, editing]);

  const patchSlides = useCallback(
    async (slides: (Partial<DeckSlide> & { id: string })[]) => {
      setSaving(true);
      setSaveError(null);
      try {
        const r = await fetch(
          `/api/runs/${encodeURIComponent(runId)}/slides/ir`,
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
        let done = false;
        for (let i = 0; i < 40; i++) {
          await new Promise((res) => setTimeout(res, 500));
          const g = await fetch(`/api/runs/${encodeURIComponent(runId)}/slides`);
          const gBody = await g.json().catch(() => ({}));
          if (gBody.slides_status === "ok") {
            const pngs = (gBody.slide_pngs as string[]) || [];
            if (gBody.deck) setDeck(gBody.deck as DeckIR);
            onDeckUpdated?.(gBody.deck as DeckIR, pngs);
            setSaveFlash(true);
            window.setTimeout(() => setSaveFlash(false), 1600);
            done = true;
            break;
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
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    },
    [onDeckUpdated, runId],
  );

  const pending = status === "running" || status === "queued" || making;
  const elapsed = useElapsedSeconds(pending);
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
              Working · {elapsedLabel}
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
            Обычно 30–90 с (Julius board update ~1–2 мин). Вкладка остаётся
            открытой — Export появится, когда готово.
          </p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="presentation-pane is-error">
        <p className="presentation-error">{error || "Не удалось собрать деку"}</p>
        {onMakePresentation ? (
          <button
            type="button"
            className="presentation-cta"
            onClick={onMakePresentation}
          >
            Повторить
          </button>
        ) : null}
      </div>
    );
  }

  if (!n && !live) {
    return (
      <div className="presentation-pane is-empty">
        <p className="presentation-empty-kicker">Liber deck</p>
        <h3 className="presentation-empty-title">Презентация 16:9</h3>
        <p className="presentation-empty-copy">
          Живой twin, editable PPTX и PDF. Стиль (Atelier · Relay · Botanical) —
          в ⚙ рядом с кнопкой.
        </p>
        <ul className="presentation-empty-points" aria-hidden>
          <li>Preview-сетка всех слайдов</li>
          <li>Edit текста → сразу в PPTX</li>
          <li>Export PPTX / deck PDF</li>
        </ul>
        {onMakePresentation ? (
          <button
            type="button"
            className="presentation-cta"
            onClick={onMakePresentation}
            disabled={making}
          >
            Сделать презентацию
          </button>
        ) : null}
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
    <div className="presentation-pane is-ready">
      <header className="presentation-chrome">
        <div className="presentation-chrome-left">
          <span className="presentation-chrome-kicker">
            {editing && view === "slide" ? "Live edit · PPTX" : "Editable PowerPoint"}
          </span>
          <span className="presentation-chrome-title" title={slideTitle}>
            {slideTitle}
          </span>
          {n > 0 ? (
            <span className="presentation-chrome-meta">
              {safeIdx + 1}/{n}
              {deck?.style?.pack_id ? ` · ${deck.style.pack_id}` : ""}
            </span>
          ) : null}
        </div>
        <div className="presentation-chrome-tools">
          <div className="presentation-seg" role="group" aria-label="Режим">
            {slidePngs.length > 0 ? (
              <button
                type="button"
                className={`presentation-seg-btn${view === "grid" ? " is-on" : ""}`}
                onClick={() => setView("grid")}
              >
                Preview
              </button>
            ) : null}
            <button
              type="button"
              className={`presentation-seg-btn${view === "slide" && !editing ? " is-on" : ""}`}
              onClick={() => {
                setView("slide");
                setEditing(false);
              }}
            >
              Slide
            </button>
            {live ? (
              <button
                type="button"
                className={`presentation-seg-btn${view === "slide" && editing ? " is-on" : ""}`}
                onClick={() => {
                  setView("slide");
                  setEditing(true);
                }}
                title="E"
              >
                Edit
              </button>
            ) : null}
          </div>
          <button
            type="button"
            className="presentation-tool"
            onClick={() => setFull(true)}
            title="F — fullscreen"
          >
            Present
          </button>
          {downloads?.pptx || downloads?.deck_pdf ? (
            <button
              type="button"
              className="presentation-tool is-export"
              onClick={() => setExportOpen(true)}
            >
              Export
            </button>
          ) : (
            <ExportMenu
              downloads={downloads}
              label="Export"
              deckPdfMode={deckPdfMode}
            />
          )}
        </div>
      </header>

      <DeckExportSheet
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        downloads={downloads}
        previewUrl={slidePngs[0] || null}
        deckPdfMode={deckPdfMode}
        slideCount={n}
      />

      {view === "grid" && slidePngs.length > 0 ? (
        <DeckGallery
          slidePngs={slidePngs}
          activeIndex={safeIdx}
          titles={(deck?.slides || []).map((s) => s.title || "")}
          onSelect={(i) => {
            setDir(i > safeIdx ? 1 : -1);
            setIdx(i);
            setView("slide");
            setEditing(false);
          }}
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
                {live && deck ? (
                  <DeckCanvas
                    runId={runId}
                    deck={deck}
                    index={safeIdx}
                    editing={editing}
                    saving={saving}
                    onDeckChange={setDeck}
                    onPatch={patchSlides}
                  />
                ) : currentPng ? (
                  <img
                    className="presentation-slide-img"
                    src={currentPng}
                    alt={`Слайд ${safeIdx + 1} из ${n}`}
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
                    key={url}
                    type="button"
                    role="tab"
                    aria-selected={i === safeIdx}
                    className={`presentation-thumb${i === safeIdx ? " is-active" : ""}`}
                    title={t || `Слайд ${i + 1}`}
                    onClick={() => {
                      setDir(i > safeIdx ? 1 : -1);
                      setIdx(i);
                    }}
                  >
                    <img src={url} alt="" />
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
          <span className="presentation-hint">← → · E edit · F present</span>
        </div>
      ) : (
        <p className="presentation-hint presentation-hint--grid">
          Клик по слайду → Slide · Edit для правок · Export PPTX / PDF
        </p>
      )}

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
        />
      ) : null}
    </div>
  );
}
