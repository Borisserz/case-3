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
  primary: "#2E4208",
  accent: "#4F6B14",
  background: "#FFFCF7",
  text: "#14161A",
  fontTitle: "Georgia",
  fontBody: "Segoe UI",
  presetId: "atelier",
};

export const FALLBACK_DECK_PACKS: DeckThemePackInfo[] = [
  {
    id: "atelier",
    label: "Atelier",
    swatches: ["#2E4208", "#4F6B14", "#FFFCF7", "#14161A"],
  },
  {
    id: "board",
    label: "Board",
    swatches: ["#142C40", "#087F8C", "#FFFFFF", "#142C40"],
  },
  {
    id: "signal",
    label: "Bold Signal",
    swatches: ["#202020", "#FF5B23", "#202020", "#F7F5F0"],
  },
  {
    id: "relay",
    label: "Split Pastel",
    swatches: ["#416650", "#E8E0F2", "#FBF9F4", "#29352F"],
  },
  {
    id: "ink",
    label: "Relay Ink",
    swatches: ["#2448FF", "#2448FF", "#111118", "#FFFFFF"],
  },
  {
    id: "voltage",
    label: "Creative Voltage",
    swatches: ["#2438EB", "#E8FF35", "#11121A", "#F6F5F0"],
  },
  {
    id: "studio",
    label: "Workshop Studio",
    swatches: ["#1B1F3B", "#4F5BD5", "#F7F8FC", "#1B1F3B"],
  },
  {
    id: "botanical",
    label: "Dark Botanical",
    swatches: ["#101F19", "#C4AD7A", "#1A3026", "#EEE9DB"],
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
