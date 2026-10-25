/** Named craft checklist for Liber ThinkingFold (RU, Quiet Mono). */

import type { ThinkingMode } from "./pipelinePhrases";

export type CraftStepId =
  | "source"
  | "layout"
  | "charts"
  | "photos"
  | "pdf"
  | "docx"
  | "slides_plan"
  | "slides_media"
  | "slides_render"
  | "slides_pack";

export type CraftStep = {
  id: CraftStepId;
  label: string;
};

export type CraftStepState = CraftStep & {
  /** done | active | upcoming | skipped */
  state: "done" | "active" | "upcoming" | "skipped";
};

const REPORT: CraftStep[] = [
  { id: "source", label: "Читаю Source" },
  { id: "layout", label: "Верстаю текст" },
  { id: "charts", label: "Рисую графики" },
  { id: "photos", label: "Собираю фото" },
  { id: "pdf", label: "Печатаю PDF" },
  { id: "docx", label: "Собираю DOCX" },
];

const DIAGRAM: CraftStep[] = [
  { id: "source", label: "Читаю Source" },
  { id: "layout", label: "Собираю схему" },
  { id: "pdf", label: "Кладу в чат" },
];

const PRESENTATION: CraftStep[] = [
  { id: "source", label: "Читаю Source" },
  { id: "layout", label: "Пишу каркас" },
  { id: "charts", label: "Рисую графики" },
  { id: "photos", label: "Собираю медиа" },
  { id: "slides_plan", label: "План слайдов" },
  { id: "slides_media", label: "Медиа на кадры" },
  { id: "slides_render", label: "Рисую превью" },
  { id: "slides_pack", label: "Собираю PPTX" },
];

const ARTIFACT_LABELS: Record<string, string> = {
  pdf: "PDF готов",
  docx: "DOCX готов",
  pptx: "PPTX готов",
  chart: "График готов",
  figure: "Фото готово",
  slides_pdf: "Deck PDF готов",
};

/** Map pipeline / slides_stage → craft step id. */
export function craftStepForStage(
  stage?: string | null,
  mode: ThinkingMode = "report",
): CraftStepId | null {
  const raw = (stage || "").toLowerCase();
  if (!raw || raw === "ok" || raw === "pipeline_ok" || raw === "slides_ok") {
    return null;
  }

  // Slides job stages (API may send "starting" or "slides_starting")
  const slidesBare = raw.startsWith("slides_")
    ? raw.slice("slides_".length)
    : mode === "presentation" &&
        [
          "starting",
          "llm",
          "llm_retry",
          "diagrams",
          "media",
          "charts",
          "render",
          "pptx",
          "patch",
          "plan",
        ].includes(raw)
      ? raw
      : null;

  if (slidesBare !== null && (raw.startsWith("slides_") || mode === "presentation")) {
    // Only treat bare names as slides when already in slides_* or after pipeline_ok
    if (raw.startsWith("slides_") || ["starting", "pptx", "render", "patch", "plan"].includes(raw)) {
      if (
        slidesBare === "queued" ||
        slidesBare === "starting" ||
        slidesBare === "llm" ||
        slidesBare === "llm_retry" ||
        slidesBare === "plan"
      ) {
        return "slides_plan";
      }
      if (
        slidesBare === "diagrams" ||
        slidesBare === "media" ||
        slidesBare === "charts"
      ) {
        return "slides_media";
      }
      if (slidesBare === "render") return "slides_render";
      if (slidesBare === "pptx" || slidesBare === "patch") return "slides_pack";
      return "slides_plan";
    }
  }

  if (mode === "presentation") {
    if (raw === "queued") return "source";
    if (raw === "llm") return "layout";
    if (raw === "charts") return "charts";
    if (raw === "images" || raw === "inject") return "photos";
    if (raw === "latex" || raw === "docx" || raw === "summary") return "slides_plan";
    return "layout";
  }

  if (mode === "diagram") {
    if (raw === "queued") return "source";
    if (raw === "llm" || raw === "diagram_repair") return "layout";
    return "pdf";
  }

  if (raw === "queued") return "source";
  if (raw === "llm") return "layout";
  if (raw === "charts") return "charts";
  if (raw === "images" || raw === "inject") return "photos";
  if (raw === "latex" || raw === "summary") return "pdf";
  if (raw === "docx") return "docx";
  return "layout";
}

export function craftTemplate(mode: ThinkingMode = "report"): CraftStep[] {
  if (mode === "diagram") return DIAGRAM;
  if (mode === "presentation") return PRESENTATION;
  return REPORT;
}

/** Build checklist states from current stage. */
export function craftProgress(
  stage?: string | null,
  mode: ThinkingMode = "report",
  opts: { live?: boolean } = {},
): CraftStepState[] {
  const live = opts.live !== false;
  const steps = craftTemplate(mode);
  const activeId = craftStepForStage(stage, mode);
  if (!activeId) {
    return steps.map((s) => ({
      ...s,
      state: live ? ("upcoming" as const) : ("done" as const),
    }));
  }
  const idx = steps.findIndex((s) => s.id === activeId);
  return steps.map((s, i) => {
    if (idx < 0) return { ...s, state: "upcoming" as const };
    if (i < idx) return { ...s, state: "done" as const };
    if (i === idx)
      return {
        ...s,
        state: live ? ("active" as const) : ("done" as const),
      };
    return { ...s, state: "upcoming" as const };
  });
}

export function artifactChipLabel(kind: string): string {
  return ARTIFACT_LABELS[kind] || `${kind} готов`;
}

export function formatMmSs(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}
