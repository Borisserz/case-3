/** Liber deck build: POST /slides + SSE/poll until terminal. */

import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useCallback } from "react";
import { openRunEvents } from "../api/runEvents";
import {
  craftParentId,
  formatCraftRecap,
  upsertCraftFilm,
  upsertCraftSubstep,
} from "../domain/craftSteps";
import {
  appendBotThinking,
  slidesJobInFlight,
  slidesJobNeedsKick,
} from "../domain/runHelpers";
import type { Msg, RunResult } from "../domain/liberTypes";
import {
  deckStyleToApiPayload,
  type DeckStyle,
} from "../deckStyle";
import type { ActiveArtifact } from "../ArtifactRail";

type Args = {
  deckStyle: DeckStyle;
  setMsgs: Dispatch<SetStateAction<Msg[]>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setRailExiting: Dispatch<SetStateAction<boolean>>;
  setActiveArtifact: Dispatch<SetStateAction<ActiveArtifact | null>>;
  setDownloadsPulseMsgId: Dispatch<SetStateAction<string | null>>;
  cancelRequestedRef: MutableRefObject<boolean>;
  activeRunIdRef: MutableRefObject<string | null>;
  pendingBotIdRef: MutableRefObject<string | null>;
};

export function useMakePresentation({
  deckStyle,
  setMsgs,
  setBusy,
  setRailExiting,
  setActiveArtifact,
  setDownloadsPulseMsgId,
  cancelRequestedRef,
  activeRunIdRef,
  pendingBotIdRef,
}: Args) {
  return useCallback(
async (msgId: string, result: RunResult) => {
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
  ,
    [
      deckStyle,
      setMsgs,
      setBusy,
      setRailExiting,
      setActiveArtifact,
      setDownloadsPulseMsgId,
      cancelRequestedRef,
      activeRunIdRef,
      pendingBotIdRef,
    ],
  );
}
