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

export type CraftSubstep = {
  id: string;
  label: string;
  status: "active" | "done" | "skipped";
  reason?: string;
};

export type CraftStepState = CraftStep & {
  /** done | active | upcoming | skipped */
  state: "done" | "active" | "upcoming" | "skipped";
  reason?: string;
  substeps?: CraftSubstep[];
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

const PARENT_TO_CRAFT: Record<string, CraftStepId> = {
  charts: "charts",
  photos: "photos",
  images: "photos",
  figures: "photos",
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

export type CraftProgressOpts = {
  live?: boolean;
  /** parent craft id → skip reason */
  skipped?: Partial<Record<CraftStepId, string>>;
  /** nested beats under charts/photos */
  substeps?: CraftSubstep[];
  /** freeze checklist (cancel) — active becomes done-looking muted */
  frozen?: boolean;
};

/** Build checklist states from current stage. */
export function craftProgress(
  stage?: string | null,
  mode: ThinkingMode = "report",
  opts: CraftProgressOpts = {},
): CraftStepState[] {
  const live = opts.live !== false;
  const steps = craftTemplate(mode);
  const skipped = opts.skipped || {};
  const activeId = craftStepForStage(stage, mode);
  const subByParent = new Map<CraftStepId, CraftSubstep[]>();
  for (const s of opts.substeps || []) {
    // Heuristic: cht_* → charts, fig_/usr_ → photos, else use first matching active
    const parent: CraftStepId =
      s.id.startsWith("cht_")
        ? "charts"
        : s.id.startsWith("fig_") || s.id.startsWith("usr_")
          ? "photos"
          : s.id === "photos"
            ? "photos"
            : activeId === "charts" || activeId === "photos"
              ? activeId
              : "charts";
    const list = subByParent.get(parent) || [];
    const prev = list.findIndex((x) => x.id === s.id);
    if (prev >= 0) list[prev] = s;
    else list.push(s);
    subByParent.set(parent, list);
  }

  if (!activeId) {
    return steps.map((s) => ({
      ...s,
      state: skipped[s.id]
        ? ("skipped" as const)
        : live
          ? ("upcoming" as const)
          : ("done" as const),
      reason: skipped[s.id],
      substeps: subByParent.get(s.id),
    }));
  }
  const idx = steps.findIndex((s) => s.id === activeId);
  return steps.map((s, i) => {
    if (skipped[s.id]) {
      return {
        ...s,
        state: "skipped" as const,
        reason: skipped[s.id],
        substeps: subByParent.get(s.id),
      };
    }
    if (idx < 0) return { ...s, state: "upcoming" as const };
    if (i < idx)
      return {
        ...s,
        state: "done" as const,
        substeps: subByParent.get(s.id),
      };
    if (i === idx) {
      // Cancel freeze: keep mid-step (not a false ✓). Finished ok → done.
      const state = opts.frozen
        ? ("active" as const)
        : !live
          ? ("done" as const)
          : ("active" as const);
      return {
        ...s,
        state,
        substeps: subByParent.get(s.id),
      };
    }
    return { ...s, state: "upcoming" as const };
  });
}

/** Merge an SSE step into the running substep list. */
export function upsertCraftSubstep(
  list: CraftSubstep[],
  step: {
    parent: string;
    id: string;
    status: string;
    reason?: string | null;
    label?: string | null;
  },
): CraftSubstep[] {
  const status =
    step.status === "done" || step.status === "skipped"
      ? step.status
      : "active";
  const row: CraftSubstep = {
    id: step.id,
    label: (step.label || step.id).trim() || step.id,
    status,
    reason: step.reason || undefined,
  };
  const out = [...list];
  const i = out.findIndex((x) => x.id === row.id);
  if (i >= 0) out[i] = row;
  else out.push(row);
  return out;
}

export function craftParentId(parent: string): CraftStepId | null {
  return PARENT_TO_CRAFT[(parent || "").toLowerCase()] || null;
}

export function formatMmSs(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/** Title suffix when ETA is confident. */
export function formatEtaSuffix(etaSec?: number | null): string {
  if (etaSec == null || !Number.isFinite(etaSec) || etaSec < 5) return "";
  const n = Math.round(etaSec);
  if (n > 600) return "";
  return ` · ещё ~${n} с`;
}

export type CraftFilmFrame = {
  id: string;
  kind: "chart" | "figure" | string;
  url: string;
};

export type CraftRecap = {
  elapsed_s?: number;
  charts?: number;
  figures?: number;
  formats?: string[];
};

const FORMAT_LABEL: Record<string, string> = {
  pdf: "PDF",
  docx: "DOCX",
  pptx: "PPTX",
  slides_pdf: "Deck PDF",
};

function pluralRu(n: number, one: string, few: string, many: string): string {
  const abs = Math.abs(n) % 100;
  const d = abs % 10;
  if (abs > 10 && abs < 20) return many;
  if (d === 1) return one;
  if (d >= 2 && d <= 4) return few;
  return many;
}

/** Post-run one-liner under ThinkingFold (success only). */
export function formatCraftRecap(recap?: CraftRecap | null): string {
  if (!recap) return "";
  const parts: string[] = [];
  const sec = Number(recap.elapsed_s);
  if (Number.isFinite(sec) && sec >= 0) {
    parts.push(`Собрано за ${formatMmSs(sec)}`);
  } else {
    parts.push("Собрано");
  }
  for (const f of recap.formats || []) {
    const lab = FORMAT_LABEL[f] || f.toUpperCase();
    if (lab) parts.push(lab);
  }
  const charts = Number(recap.charts) || 0;
  const figures = Number(recap.figures) || 0;
  if (charts > 0) {
    parts.push(
      `${charts} ${pluralRu(charts, "график", "графика", "графиков")}`,
    );
  }
  if (figures > 0) {
    parts.push(
      `${figures} ${pluralRu(figures, "фото", "фото", "фото")}`,
    );
  }
  return parts.join(" · ");
}

export function upsertCraftFilm(
  list: CraftFilmFrame[],
  frame: CraftFilmFrame,
): CraftFilmFrame[] {
  if (!frame?.id || !frame.url) return list;
  const out = [...list];
  const i = out.findIndex((x) => x.id === frame.id);
  if (i >= 0) out[i] = frame;
  else out.push(frame);
  return out.slice(-12);
}
