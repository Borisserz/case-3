/** Liber deck viewer: Julius-like live twin + filmstrip + fullscreen. */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { DeckCanvas } from "./DeckCanvas";
import { DeckGallery } from "./DeckGallery";
import type { DeckIR, DeckSlide } from "./deckTypes";
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
  deckPdfMode: _deckPdfMode = null,
  making = false,
  onDeckUpdated,
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
  const [editing, setEditing] = useState(false);
  const [view, setView] = useState<"grid" | "slide">("grid");
  const [deck, setDeck] = useState<DeckIR | null>(deckProp);
  const [saving, setSaving] = useState(false);
  const [saveFlash, setSaveFlash] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
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

  // Safety net: rail opened with pptx downloads but empty twin/deck (old status).
  useEffect(() => {
    if (status !== "ok") return;
    if (slidePngs.length > 0 || deckProp) return;
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
          onDeckUpdated?.(gBody.deck as DeckIR, pngs);
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
    [onDeckUpdated, runId],
  );

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
        await waitPatchRebuild(body.deck as DeckIR | undefined);
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    },
    [runId, waitPatchRebuild],
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
        await waitPatchRebuild(next);
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : String(err));
      } finally {
        setSaving(false);
      }
    },
    [deck, runId, waitPatchRebuild],
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
    <div className="presentation-pane is-ready">
      <header className="presentation-chrome">
        <div className="presentation-chrome-left">
          <span className="presentation-chrome-kicker">
            {editing && view === "slide"
              ? "Презентация · правки"
              : "Презентация · PPTX"}
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
                  setEditing(false);
                }}
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
        </div>
        <div className="presentation-chrome-actions">
          {n > 0 ? (
            <span className="deck-slides-film-count" aria-live="polite">
              {safeIdx + 1}
              <span aria-hidden> / </span>
              {n}
            </span>
          ) : null}
          {downloads?.pptx ? (
            <a href={downloads.pptx} download className="deck-slides-film-dl">
              Скачать
            </a>
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
                    <img src={url} alt="" draggable={false} />
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
