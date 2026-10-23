/** Shared Liber desk types (chat + run payload). */

import type { ThinkingLine, ThinkingMode } from "./pipelinePhrases";
import type { ReportPreview } from "./ReportView";

export type PaletteInfo = {
  id: string;
  label: string;
  swatches: string[];
};

export type Health = {
  ok: boolean;
  docker_ok: boolean;
  playwright_ok: boolean;
  vision_configured: boolean;
  kandinsky_configured: boolean;
  image_api_configured?: boolean;
  docker_error?: string | null;
  chart_types?: string[];
  chart_palettes?: PaletteInfo[];
  defaults?: {
    max_charts?: number;
    max_diagrams?: number;
    max_images?: number;
  };
};

export type MediaPreview = {
  id: string;
  kind: string;
  url: string;
};

export type DiagramResult = {
  id: string;
  title: string;
  type?: string;
  mermaid: string;
};

export type RunResult = {
  run_id: string;
  status: string;
  downloads: Record<string, string>;
  previews?: MediaPreview[];
  preview?: ReportPreview;
  charts_ok: number;
  figures_ok: number;
  charts_planned: string[];
  figures_planned: string[];
  diagrams?: DiagramResult[];
  diagrams_ok?: number;
  diagrams_planned?: string[];
  warnings: string[];
  media_status?: Record<string, unknown>;
  chat_summary?: string;
  summary_status?: string | null;
  slides_status?: string | null;
  slides_stage?: string | null;
  slides_error?: string | null;
  slide_pngs?: string[];
  /** How deck PDF was built: `lo` (LibreOffice) or `png_stitch`. */
  deck_pdf_mode?: string | null;
  /** Live deck IR for editable twin canvas */
  deck?: import("./deckTypes").DeckIR | null;
  /** Liber composer mode that produced this run */
  output_mode?: string;
  error?: string;
  detail?: string;
};

export type SourceAttachment = {
  title: string;
  text: string;
  fileName?: string;
};

export type SourceDraft = {
  title: string;
  text: string;
  fileName?: string;
};

export type UserMsg = {
  id: string;
  role: "user";
  text: string;
  /** @deprecated prefer chips — kept for session history */
  tags?: string;
  /** C6: settings as chips under collapsed Intent. */
  chips?: string[];
  /** Pasted / attached source shown as doc plaque on the bubble. */
  attachment?: SourceAttachment;
};

export type BotMsg = {
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
  /** Phrase pool: report / diagram / presentation */
  thinkingMode?: ThinkingMode;
  error?: string;
};

export type Msg = UserMsg | BotMsg;
