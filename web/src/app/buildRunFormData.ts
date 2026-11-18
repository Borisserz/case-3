/** Build multipart body for POST /api/run from Liber desk composer state. */

import { deckStyleToApiPayload, type DeckStyle } from "../deckStyle";
import type { LiberWorkMode } from "../domain/liberModes";
import type { SourceDraft } from "../domain/liberTypes";

/** Fixed run defaults — chart type/style/title come from model + ChartEditSheet. */
const CHART_AUTO = true;
const CHART_TYPES: string[] = [];
const CHART_HINTS = "";
const CHART_PALETTE = "atelier";
const CHART_STYLE = "";
const DOC_TITLE = "";

export type BuildRunFormDataArgs = {
  file: File | null;
  draftSnap: SourceDraft | null;
  chatTrim: string;
  intentText: string;
  photosSnapshot: File[];
  forbidCharts: boolean;
  forbidImages: boolean;
  maxCharts: number;
  maxImages: number;
  maxDiagrams: number;
  dryRun: boolean;
  workMode: LiberWorkMode;
  deckStyle: DeckStyle;
  /** Palette preset for generated charts (atelier, editorial, ocean, sunset, mono). */
  chartPalette?: string;
  /** Wish for deck length (6–24). Model may emit fewer if Source is thin. */
  targetSlides?: number;
  /** Previous bot run in this chat. Empty on the first send. */
  priorRunId?: string | null;
};

export function buildRunFormData(args: BuildRunFormDataArgs): FormData {
  const {
    file,
    draftSnap,
    chatTrim,
    intentText,
    photosSnapshot,
    forbidCharts,
    forbidImages,
    maxCharts,
    maxImages,
    maxDiagrams,
    dryRun,
    workMode,
    deckStyle,
    chartPalette,
    targetSlides,
    priorRunId,
  } = args;

  const fd = new FormData();
  // Photo-edit UI parked; Liber desk always posts document runs.
  // Standalone img2img remains POST /api/photo/edit.
  fd.append("photo_mode", "document");
  for (const p of photosSnapshot) fd.append("photos", p);
  if (
    file &&
    draftSnap?.text &&
    (Boolean(draftSnap.fileName) || /\.(txt|md)$/i.test(file.name || ""))
  ) {
    fd.append(
      "source",
      new File([draftSnap.text], file.name || draftSnap.fileName || "source.txt", {
        type: file.type || "text/plain",
      }),
    );
    fd.append("intent", intentText);
  } else if (file) {
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
  fd.append("max_diagrams", String(maxDiagrams));
  fd.append(
    "max_images",
    String(
      forbidImages && !photosSnapshot.length
        ? 0
        : Math.max(maxImages, photosSnapshot.length),
    ),
  );
  fd.append("chart_types", CHART_AUTO ? "" : CHART_TYPES.join(","));
  fd.append("chart_hints", CHART_HINTS.trim());
  fd.append("chart_auto", String(CHART_AUTO));
  fd.append(
    "chart_palette",
    (chartPalette || "").trim() ? (chartPalette || "").trim() : CHART_PALETTE,
  );
  fd.append("chart_style", CHART_STYLE.trim());
  fd.append("doc_title", DOC_TITLE.trim().slice(0, 200));
  fd.append("forbid_charts", String(forbidCharts));
  fd.append(
    "forbid_images",
    String(forbidImages && photosSnapshot.length === 0),
  );
  fd.append("output_mode", "auto");
  fd.append("artifact_bias", workMode ?? "");
  fd.append("deck_pack", deckStyle.themePack || "atelier");
  const deckPayload = deckStyleToApiPayload(deckStyle);
  if (deckPayload.structure_id) {
    fd.append("deck_structure_id", deckPayload.structure_id);
  }
  fd.append("deck_style_json", JSON.stringify(deckPayload.style_settings || {}));
  const slidesWish = Math.max(6, Math.min(24, Math.round(targetSlides || 12)));
  fd.append("target_slides", String(slidesWish));
  fd.append("formats", "both");
  fd.append("dry_run", String(dryRun));
  const prior = (priorRunId || "").trim();
  if (prior) fd.append("prior_run_id", prior);
  return fd;
}
