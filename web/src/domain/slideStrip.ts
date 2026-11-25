/** Filmstrip and fullscreen follow slide ids.

Positional PNG files (`slide_01.png` …) stay in the old order until «Готово».
Duplicate, insert, delete, and drag change `deck.json` immediately, so the
pictures have to travel with the slide id or the strip shows the wrong slide.
*/

export type SlideRef = { id: string };

export function bindSlidePngs(
  slides: SlideRef[],
  pngs: string[],
): Record<string, string | null> {
  // Same length: each file belongs to that slide. A shorter file list (a new
  // slide was added, PNGs not rebuilt yet) still keeps the pictures we have.
  // Wiping every thumb made the grid and the bottom strip look empty on return.
  const map: Record<string, string | null> = {};
  for (let i = 0; i < slides.length; i++) {
    map[slides[i].id] = i < pngs.length && pngs[i] ? pngs[i] : null;
  }
  return map;
}

const PNG_MAP_PREFIX = "liber-deck-png-map:";

export function rememberDeckPngMap(
  runId: string,
  key: string,
  map: Record<string, string | null>,
): void {
  if (typeof sessionStorage === "undefined" || !runId) return;
  try {
    sessionStorage.setItem(
      PNG_MAP_PREFIX + runId,
      JSON.stringify({ key, map }),
    );
  } catch {
    /* quota */
  }
}

export function recallDeckPngMap(
  runId: string,
): { key: string; map: Record<string, string | null> } | null {
  if (typeof sessionStorage === "undefined" || !runId) return null;
  try {
    const raw = sessionStorage.getItem(PNG_MAP_PREFIX + runId);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as {
      key?: unknown;
      map?: unknown;
    };
    if (
      !parsed ||
      typeof parsed.key !== "string" ||
      !parsed.map ||
      typeof parsed.map !== "object"
    ) {
      return null;
    }
    return {
      key: parsed.key,
      map: parsed.map as Record<string, string | null>,
    };
  } catch {
    return null;
  }
}

export function retargetSlidePngs(
  prev: Record<string, string | null>,
  before: SlideRef[],
  after: SlideRef[],
  op: "reorder" | "duplicate" | "delete" | "insert",
): Record<string, string | null> {
  const beforeIds = new Set(before.map((s) => s.id));
  const next: Record<string, string | null> = {};
  for (let i = 0; i < after.length; i++) {
    const id = after[i].id;
    if (beforeIds.has(id)) {
      next[id] = prev[id] ?? null;
      continue;
    }
    if (op === "duplicate" && i > 0 && beforeIds.has(after[i - 1].id)) {
      next[id] = prev[after[i - 1].id] ?? null;
    } else {
      next[id] = null;
    }
  }
  return next;
}

/** Index of the first slide that the structure op added. -1 if none. */
export function addedSlideIndex(before: SlideRef[], after: SlideRef[]): number {
  const beforeIds = new Set(before.map((s) => s.id));
  return after.findIndex((s) => !beforeIds.has(s.id));
}

/** Live deck wins over leftover PNG files, which lag structure edits. */
export function fullscreenCount(opts: {
  liveSlides: number;
  pngs: number;
}): { n: number; useDeck: boolean } {
  if (opts.liveSlides > 0) return { n: opts.liveSlides, useDeck: true };
  return { n: opts.pngs, useDeck: false };
}
