/** Liber deck style — localStorage + API payload (deck-only). */

export type DeckStyle = {
  themePack: string;
  /** Narrative structure id (board_update, investor, …) — not a color pack. */
  structureId?: string;
  primary: string;
  accent: string;
  background: string;
  text: string;
  fontTitle: string;
  fontBody: string;
  presetId?: string;
};

export type DeckThemePackInfo = {
  id: string;
  label: string;
  swatches: string[];
};

const STORAGE_KEY = "liber.deckStyle.v1";

export const DEFAULT_DECK_STYLE: DeckStyle = {
  themePack: "atelier",
  structureId: undefined,
  primary: "#2C3A22",
  accent: "#6B7F45",
  background: "#FBF8F1",
  text: "#2C3A22",
  fontTitle: "Georgia",
  fontBody: "Segoe UI",
  presetId: "atelier",
};

export const FALLBACK_DECK_PACKS: DeckThemePackInfo[] = [
  {
    id: "atelier",
    label: "Atelier",
    swatches: ["#2C3A22", "#6B7F45", "#FBF8F1", "#2C3A22"],
  },
  {
    id: "board",
    label: "Board",
    swatches: ["#1B3A4B", "#3D8B84", "#F4F8F7", "#1B3A4B"],
  },
  {
    id: "signal",
    label: "Bold Signal",
    swatches: ["#1E1C1A", "#C4785A", "#2A2724", "#F3EDE6"],
  },
  {
    id: "relay",
    label: "Split Pastel",
    swatches: ["#3A463C", "#7D9478", "#FBF8F2", "#3A463C"],
  },
  {
    id: "ink",
    label: "Relay Ink",
    swatches: ["#141A24", "#7F97B0", "#1C2430", "#E6E4DC"],
  },
  {
    id: "voltage",
    label: "Creative Voltage",
    swatches: ["#161B28", "#E4D48A", "#1E2433", "#F4F0E6"],
  },
  {
    id: "studio",
    label: "Workshop Studio",
    swatches: ["#3E342C", "#A6846A", "#FBF7F2", "#3E342C"],
  },
  {
    id: "botanical",
    label: "Dark Botanical",
    swatches: ["#101F19", "#C4AD7A", "#1C2E26", "#E8E2D4"],
  },
];

export const DECK_FONT_OPTIONS = [
  "Georgia",
  "Segoe UI",
  "Arial",
  "Calibri",
  "Times New Roman",
  "Helvetica",
] as const;

function isHex(v: unknown): v is string {
  return typeof v === "string" && /^#?[0-9A-Fa-f]{6}$/.test(v.trim());
}

function normHex(v: string): string {
  const t = v.trim();
  return t.startsWith("#") ? t.toUpperCase() : `#${t.toUpperCase()}`;
}

export function loadDeckStyle(): DeckStyle {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_DECK_STYLE };
    const parsed = JSON.parse(raw) as Partial<DeckStyle>;
    return {
      themePack: parsed.themePack || DEFAULT_DECK_STYLE.themePack,
      structureId: parsed.structureId || undefined,
      primary: isHex(parsed.primary)
        ? normHex(parsed.primary)
        : DEFAULT_DECK_STYLE.primary,
      accent: isHex(parsed.accent)
        ? normHex(parsed.accent)
        : DEFAULT_DECK_STYLE.accent,
      background: isHex(parsed.background)
        ? normHex(parsed.background)
        : DEFAULT_DECK_STYLE.background,
      text: isHex(parsed.text) ? normHex(parsed.text) : DEFAULT_DECK_STYLE.text,
      fontTitle: parsed.fontTitle || DEFAULT_DECK_STYLE.fontTitle,
      fontBody: parsed.fontBody || DEFAULT_DECK_STYLE.fontBody,
      presetId: parsed.presetId,
    };
  } catch {
    return { ...DEFAULT_DECK_STYLE };
  }
}

export function saveDeckStyle(style: DeckStyle): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(style));
  } catch {
    /* ignore quota */
  }
}

export function applyPackToStyle(
  pack: DeckThemePackInfo,
  prev: DeckStyle,
): DeckStyle {
  const [primary, accent, background, text] = pack.swatches;
  return {
    ...prev,
    themePack: pack.id,
    presetId: pack.id,
    primary: primary || prev.primary,
    accent: accent || prev.accent,
    background: background || prev.background,
    text: text || prev.text,
  };
}

/** Diagram legend strokes. Keep in sync with diagram_style._ROLE_MAP. */
const DIAGRAM_LEGEND_STROKES: Record<
  string,
  { start: string; decision: string; ok: string; warn: string }
> = {
  atelier: { start: "#1F6F66", decision: "#C47A3A", ok: "#2F7D4A", warn: "#C45A48" },
  editorial: { start: "#4E79A7", decision: "#F28E2B", ok: "#59A14F", warn: "#E15759" },
  ocean: { start: "#0072B2", decision: "#E69F00", ok: "#009E73", warn: "#D55E00" },
  sunset: { start: "#9A4A58", decision: "#A89830", ok: "#228833", warn: "#EE6677" },
  mono: { start: "#1A1F28", decision: "#8B7355", ok: "#2F4A38", warn: "#6B4038" },
};

export function diagramLegendStrokes(palette: string | undefined): {
  start: string;
  decision: string;
  ok: string;
  warn: string;
} {
  const key = (palette || "atelier").trim().toLowerCase();
  return DIAGRAM_LEGEND_STROKES[key] || DIAGRAM_LEGEND_STROKES.atelier;
}

/** Body for POST /api/runs/{id}/slides */
export function deckStyleToApiPayload(style: DeckStyle): {
  theme_pack: string;
  structure_id?: string;
  style_settings: Record<string, string>;
} {
  const payload: {
    theme_pack: string;
    structure_id?: string;
    style_settings: Record<string, string>;
  } = {
    theme_pack: style.themePack || "atelier",
    style_settings: {
      primary: style.primary,
      accent: style.accent,
      background: style.background,
      text: style.text,
      fontTitle: style.fontTitle,
      fontBody: style.fontBody,
    },
  };
  if (style.structureId) payload.structure_id = style.structureId;
  return payload;
}
